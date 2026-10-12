"""
Diagnostic: per-frame stationarity report.

Reads each frame_*.bin in a folder, computes the range-FFT, and reports:
  - static_dB    : 10*log10(sum |mean_over_loops(R_fft)|^2)
                    -> energy of the part of the scene that is coherent across loops
                       (true static reflectors + DC offsets + persistent firmware state)
  - slow_var_dB  : 10*log10(sum var_over_loops(|R_fft|^2))
                    -> energy of the part that varies frame-to-frame within a frame
                       (thermal noise + moving targets + intra-frame calibration jitter)
  - raw_mean     : mean |IQ| in ADC LSBs (sanity vs capture --frame-stats)

Interpretation guide:
  * Stable static_dB, stable slow_var_dB
        -> input is stationary; CFAR=0 in static scene is meaningful.
  * Varying static_dB, stable slow_var_dB
        -> RF/TX gain is wandering frame-to-frame. Firmware-side calibration.
  * Stable static_dB, varying slow_var_dB
        -> noise figure / AGC wandering inside the frame.
  * Both varying together
        -> input-power scaling drift (clock/data-path scaling) or compressionCfg
           reaching LVDS.

This script does NOT use the DSP pipeline (no MTI, no Doppler FFT, no CFAR,
no AoA, no calibration, no fallbacks). It reads bytes, reshapes, range-FFTs,
and reduces. That is all.

Usage:
    python -m processing.diag_frame_stationarity --folder capture/frames
    python -m processing.diag_frame_stationarity --folder capture/frames --cfg config/build_shortrange_inf/cascade_shortrange.cfg
"""
from __future__ import annotations

import argparse
import os
import sys
import importlib.util
from pathlib import Path

import numpy as np

# Load processing/radar_config.py directly without triggering processing/__init__.py
# (which eagerly imports matplotlib via radar_plots). This script is a pure-numpy
# diagnostic and must not depend on the plotting stack.
_HERE = Path(__file__).resolve().parent
_RC_PATH = _HERE / "radar_config.py"
_spec = importlib.util.spec_from_file_location("_diag_radar_config", _RC_PATH)
_rc = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["_diag_radar_config"] = _rc
_spec.loader.exec_module(_rc)
RadarConfig = _rc.RadarConfig
parse_cfg_file = _rc.parse_cfg_file


def _load_geom(cfg_path: str | None) -> RadarConfig:
    if cfg_path and os.path.isfile(cfg_path):
        return parse_cfg_file(cfg_path)
    return RadarConfig()


def _read_frame_int16(path: Path, cfg: RadarConfig) -> np.ndarray:
    """Return raw int16 array shaped [chirps, num_rx, num_samples, 2]."""
    num_rx = cfg.num_rx
    num_samples = cfg.num_samples
    chirps_per_frame = cfg.chirps_per_frame
    n_int16 = chirps_per_frame * num_rx * num_samples * 2
    raw = np.fromfile(path, dtype=np.int16, count=n_int16)
    if raw.size != n_int16:
        raise RuntimeError(f"{path.name}: short read ({raw.size} vs {n_int16})")
    return raw.reshape(chirps_per_frame, cfg.num_devices, cfg.num_rx_per_dev,
                       num_samples, 2)


def _frame_complex(path: Path, cfg: RadarConfig) -> np.ndarray:
    """Return complex64 cube [num_tx, num_loops, num_rx, num_samples] (no calib)."""
    raw = _read_frame_int16(path, cfg)
    if cfg.iq_swap:
        i_ch = raw[..., 1].astype(np.float32)
        q_ch = raw[..., 0].astype(np.float32)
    else:
        i_ch = raw[..., 0].astype(np.float32)
        q_ch = raw[..., 1].astype(np.float32)
    cdata = (i_ch + 1j * q_ch).astype(np.complex64)
    cdata = cdata.reshape(cfg.chirps_per_frame, cfg.num_rx, cfg.num_samples)
    return np.stack([cdata[t::cfg.num_tx] for t in range(cfg.num_tx)], axis=0)


def _stationarity_metrics(cube: np.ndarray) -> tuple[float, float, float, float, float]:
    """
    cube: complex64 [num_tx, num_loops, num_rx, num_samples]

    Returns (raw_mean, static_dB, slow_var_dB, static_minus_slow_dB, frac_dc_bin)

    static_dB and slow_var_dB are reduced over (tx, rx, range-bin) to a single
    scalar per frame. The reduction is a sum so absolute magnitudes are comparable
    across frames captured with the same waveform.
    """
    raw_mean = float(np.mean(np.abs(cube)))

    # Range FFT along ADC axis (no window, no FFT shift -> compare apples to apples)
    R = np.fft.fft(cube, axis=-1).astype(np.complex64)

    # Static energy: coherent average across slow time (loops), then power
    static_complex = R.mean(axis=1)                     # [tx, rx, range]
    static_pwr = np.abs(static_complex) ** 2            # [tx, rx, range]
    static_total = float(static_pwr.sum())

    # Slow-time variance energy: variance of |R|^2 across loops, then sum
    pwr_per_loop = np.abs(R) ** 2                       # [tx, loops, rx, range]
    slow_var = pwr_per_loop.var(axis=1)                 # [tx, rx, range]
    slow_var_total = float(slow_var.sum())

    static_db = 10.0 * np.log10(max(static_total, 1e-12))
    slow_db = 10.0 * np.log10(max(slow_var_total, 1e-12))

    # Fraction of static energy in the DC range bin (bin 0). High -> dominated
    # by IQ DC offset / coupling rather than reflectors.
    dc_frac = float(static_pwr[..., 0].sum() / max(static_total, 1e-12))

    return raw_mean, static_db, slow_db, static_db - slow_db, dc_frac


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--folder", required=True, type=Path)
    parser.add_argument("--cfg", default=None,
                        help="Optional cascade cfg; defaults to shortrange RadarConfig().")
    parser.add_argument("--limit", type=int, default=0,
                        help="Process only the first N frames (0 = all).")
    args = parser.parse_args()

    if not args.folder.is_dir():
        print(f"ERROR: folder not found: {args.folder}", file=sys.stderr)
        return 2

    cfg = _load_geom(args.cfg)
    print(f"[diag] cfg: N={cfg.num_samples}  loops={cfg.num_loops}  "
          f"TX={cfg.num_tx}  RX={cfg.num_rx}  iq_swap={cfg.iq_swap}")
    print(f"[diag] frame_bytes = {cfg.bytes_per_frame:,}")

    frames = sorted(args.folder.glob("frame_*.bin"))
    if args.limit > 0:
        frames = frames[: args.limit]
    if not frames:
        print(f"ERROR: no frame_*.bin in {args.folder}", file=sys.stderr)
        return 2

    print()
    print(f"{'frame':>5} {'raw_mean':>9} {'static_dB':>10} {'slow_var_dB':>12} "
          f"{'static-slow':>12} {'dc_frac':>8}")
    static_vals = []
    slow_vals = []
    raw_vals = []
    for path in frames:
        try:
            cube = _frame_complex(path, cfg)
        except Exception as exc:
            print(f"{path.name}: read error: {exc}", file=sys.stderr)
            continue
        raw_mean, static_db, slow_db, diff_db, dc_frac = _stationarity_metrics(cube)
        idx_str = path.stem.split("_")[-1]
        print(f"{idx_str:>5} {raw_mean:9.2f} {static_db:10.2f} {slow_db:12.2f} "
              f"{diff_db:+12.2f} {dc_frac:8.4f}")
        static_vals.append(static_db)
        slow_vals.append(slow_db)
        raw_vals.append(raw_mean)

    if static_vals:
        sv = np.asarray(static_vals)
        ll = np.asarray(slow_vals)
        rv = np.asarray(raw_vals)
        print()
        print("[diag] summary (over saved frames)")
        print(f"  raw_mean    : min={rv.min():8.2f}  max={rv.max():8.2f}  "
              f"max/min={rv.max() / max(rv.min(), 1e-6):5.2f}")
        print(f"  static_dB   : min={sv.min():8.2f}  max={sv.max():8.2f}  "
              f"span={sv.max() - sv.min():5.2f} dB")
        print(f"  slow_var_dB : min={ll.min():8.2f}  max={ll.max():8.2f}  "
              f"span={ll.max() - ll.min():5.2f} dB")
        static_span = float(sv.max() - sv.min())
        slow_span = float(ll.max() - ll.min())
        print()
        print("[diag] verdict heuristic:")
        if static_span < 2.0 and slow_span < 2.0:
            print("  STABLE  -> input is stationary; CFAR=0 in static scene is meaningful.")
        elif static_span >= 2.0 and slow_span < 2.0:
            print("  STATIC VARIES, NOISE STABLE -> firmware RF/TX gain wandering between frames.")
        elif static_span < 2.0 and slow_span >= 2.0:
            print("  STATIC STABLE, NOISE VARIES -> noise figure / AGC wandering within frames.")
        else:
            print("  BOTH VARY -> input-power scaling drift; suspect compressionCfg or clock/data-path.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
