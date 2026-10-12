"""
radar_config.py - AWR2243-CAS-2X-EVM cascade geometry and processing defaults.

The virtual array follows the 38+8 layout used by the cascaded EVM:
  - bottom row: 40 azimuth channels with 38 independent positions
  - top row:    8 elevation channels
  - azimuth spacing: 0.5 lambda
  - elevation spacing: 0.8 lambda

The bottom-row overlaps occur at virtual azimuth positions 7 and 26, so angle
estimation should treat the aperture as 38 independent azimuth channels plus a
matched 8-channel elevation row.
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np

C = 3e8  # speed of light (m/s)

_TX_AZ  = [0,  4,  7, 11, 15,  2]   # az position per chirp (λ/2)
_TX_EL  = [0,  0,  0,  0,  0,  1]   # chirp 5 = elevation TX
_RX_AZ  = [0,  1,  2,  3, 19, 20, 21, 22]
_RX_EL  = [0,  0,  0,  0,  0,  0,  0,  0]
_D_EL   = 0.8    # elevation spacing in λ units
_EL_TX  = 5      # chirp index of elevation TX


@dataclass
class RadarConfig:
    # ── Hardware ──────────────────────────────────────────────────────────────
    num_devices:      int   = 2
    num_rx_per_dev:   int   = 4
    num_tx:           int   = 6

    # ── Waveform (shortrange defaults matching cascade_shortrange.cfg) ────────
    start_freq_ghz:   float = 77.0
    slope_mhz_us:     float = 44.41
    sample_rate_ksps: float = 5000.0
    num_samples:      int   = 256
    idle_time_us:     float = 5.0
    ramp_end_us:      float = 60.0
    num_loops:        int   = 64
    iq_swap:          bool  = False  # Default raw capture is [I,Q]; SampleSwap=1 / q-first sets this True

    # ── Virtual array ─────────────────────────────────────────────────────────
    tx_az:       List[int] = field(default_factory=lambda: list(_TX_AZ))
    tx_el:       List[int] = field(default_factory=lambda: list(_TX_EL))
    rx_az:       List[int] = field(default_factory=lambda: list(_RX_AZ))
    rx_el:       List[int] = field(default_factory=lambda: list(_RX_EL))
    d_el_lambda: float     = _D_EL
    elev_tx_idx: int       = _EL_TX

    # ── FFT sizes ─────────────────────────────────────────────────────────────
    range_fft_size:   int = 256
    doppler_fft_size: int = 64
    az_fft_size:      int = 256
    el_fft_size:      int = 64

    # ── Windowing ─────────────────────────────────────────────────────────────
    range_window:       str   = "hann"
    doppler_window:     str   = "hann"
    az_window:          str   = "chebyshev"
    el_window:          str   = "hann"
    chebyshev_atten_db: float = 60.0

    # ── Calibration ───────────────────────────────────────────────────────────
    apply_calibration:  bool          = True
    calib_cfg_path:     Optional[str] = "config\cascade_shortrange.cfg"

    # ── Clutter / static removal ──────────────────────────────────────────────
    clutter_removal:  bool  = True   # MTI: subtract slow-time mean
    zero_dc_bins:     int   = 2      # ±N Doppler bins zeroed around DC

    # ── DSP mode ─────────────────────────────────────────────────────────────
    dsp_mode: str = "cascade"

    # ── AoA beamforming ───────────────────────────────────────────────────────
    aoa_method:        str = "fft"   # fft | capon | music | bartlett
    music_num_sources: int = 3
    music_diag_load:   float = 0.01
    music_forward_backward_avg: bool = True
    music_use_unique_aperture: bool = True

    # ── CFAR (K-Radar style) ──────────────────────────────────────────────────
    cfar_method:   str        = "os"
    cfar_guard:    List[int]  = field(default_factory=lambda: [4, 6])
    cfar_train:    List[int]  = field(default_factory=lambda: [8, 16])
    cfar_fa_rate:  float      = 3e-5
    cfar_os_rank:  float      = 0.75
    cfar_margin_db:float      = 10.0
    cfar_min_power_db: float  = 12.0

    # ── NMS / range gate ──────────────────────────────────────────────────────
    nms_size:    List[int] = field(default_factory=lambda: [3, 3])
    min_range_m: float     = 0.1
    max_range_m: float     = 16.0   # 0 = full axis
    roi_x_m: Optional[tuple[float, float]] = None
    roi_y_m: Optional[tuple[float, float]] = None
    roi_z_m: Optional[tuple[float, float]] = None

    # ── Gaussian smoothing ────────────────────────────────────────────────────
    gaussian_sigma: float = 0.0   # 0 = disabled

    # ── Moving-objects gate ───────────────────────────────────────────────────
    moving_objects_only:    bool  = False  # show only moving returns
    min_abs_doppler_mps:    float = 0.0    # 0 = auto (0.5 × dop_res)
    require_rd_confirmation:bool  = True

    # ── High-reflection moving-object filter ──────────────────────────────────
    # When enabled, the CFAR detection mask is additionally filtered to keep
    # only cells that are BOTH moving (|Doppler| > min) AND high-power
    # (power > local noise floor + high_moving_db_above).
    # Use this to isolate strong, moving reflectors (vehicles, metal objects).
    filter_high_moving:      bool  = False  # master enable
    high_moving_min_dop:     float = 0.0    # min |Doppler| (m/s); 0 = auto
    high_moving_db_above:    float = 8.0    # dB above local noise floor

    # Additional post-CFAR peak cleanup to suppress sidelobes around the
    # strongest object return in each range bin / azimuth row.
    apply_sidelobe_filters: bool  = True
    rd_sidelobe_db:         float = 8.0
    ra_sidelobe_db:         float = 8.0
    doppler_stripe_removal: bool  = True
    strict_object_filtering: bool = True
    max_az_detections_per_range: int = 4
    ra_peak_prominence_db: float = 3.0
    el_peak_prominence_db: float = 2.0

    # ── Display / colour scale ────────────────────────────────────────────────
    # use_fixed_db = False  → adaptive per-frame (RECOMMENDED — always shows
    #   the strongest moving return in red, noise floor in dark blue)
    # use_fixed_db = True   → fixed limits (good for multi-frame comparison)
    use_fixed_db:  bool  = False
    db_vmin:       float = 55.0   # fixed-mode minimum (dB)
    db_vmax:       float = 90.0   # fixed-mode maximum (dB)
    db_span:       float = 24.0   # adaptive window width (dB)
    cmap_pct_high: float = 99.7   # percentile for adaptive vmax
    ra_display_snr_db: float = 4.0
    ra_display_floor_db: float = 6.0
    pc2d_dynamic_db: bool = True
    pc2d_db_vmin: Optional[float] = None
    pc2d_db_vmax: Optional[float] = None
    pc2d_db_span: float = 18.0
    pc2d_cmap_pct_low: float = 12.0
    pc2d_cmap_pct_high: float = 99.5
    point_cloud_max_points: int = 50000
    pc2d_ranges_to_show: int = 40
    pc2d_points_per_range: int = 8
    pc2d_min_points: int = 320

    # ── Colormap ──────────────────────────────────────────────────────────────
    cmap_pct_low:  float = 8.0    # adaptive floor percentile to suppress noise

    # ── Save outputs ──────────────────────────────────────────────────────────
    save_drea_path: Optional[str] = r"C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\drea.npy"
    save_xyz_path:  Optional[str] = r"C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\xyz_cloud.npy"
    # =========================================================================
    # Derived properties
    # =========================================================================

    @property
    def num_rx(self) -> int:
        return self.num_rx_per_dev * self.num_devices

    @property
    def chirps_per_frame(self) -> int:
        return self.num_tx * self.num_loops

    @property
    def bytes_per_frame(self) -> int:
        return self.chirps_per_frame * self.num_rx * self.num_samples * 2 * 2

    @property
    def lambda_m(self) -> float:
        return C / (self.start_freq_ghz * 1e9)

    @property
    def range_res_m(self) -> float:
        bw = self.slope_mhz_us * 1e12 * self.num_samples / (self.sample_rate_ksps * 1e3)
        return C / (2.0 * bw)

    @property
    def n_range(self) -> int:
        return self.range_fft_size or self.num_samples

    @property
    def range_axis(self) -> np.ndarray:
        return np.arange(self.n_range) * self.range_res_m

    @property
    def tdm_period_s(self) -> float:
        return self.num_tx * (self.idle_time_us + self.ramp_end_us) * 1e-6

    @property
    def dop_max(self) -> float:
        """Max unambiguous Doppler speed (m/s) — calculated from waveform."""
        return self.lambda_m / (4.0 * self.tdm_period_s)

    @property
    def dop_res(self) -> float:
        """Doppler resolution (m/s) — calculated from waveform."""
        return self.lambda_m / (2.0 * self.num_loops * self.tdm_period_s)

    @property
    def doppler_axis(self) -> np.ndarray:
        """
        Doppler axis in m/s, zero-centred.
        Limits ±dop_max are physically derived from the waveform config:
          dop_max = λ / (4 × N_TX × T_chirp)
        """
        n = self.doppler_fft_size or self.num_loops
        return np.linspace(-self.dop_max, self.dop_max, n, endpoint=False)

    @property
    def az_axis_deg(self) -> np.ndarray:
        sin_v = np.linspace(-1.0, 1.0, self.az_fft_size, endpoint=False)
        return np.degrees(np.arcsin(np.clip(sin_v, -1, 1)))

    @property
    def el_axis_deg(self) -> np.ndarray:
        lim = min(1.0 / (2.0 * self.d_el_lambda), 1.0)
        sin_v = np.linspace(-lim, lim, self.el_fft_size, endpoint=False)
        return np.degrees(np.arcsin(np.clip(sin_v, -1, 1)))

    def build_channel_table(self):
        from collections import Counter
        ch_az, ch_el = [], []
        for t in range(self.num_tx):
            for r in range(self.num_rx):
                ch = dict(az=self.tx_az[t]+self.rx_az[r], tx=t, rx=r,
                          cal_idx=t*self.num_rx+r)
                (ch_el if self.tx_el[t] else ch_az).append(ch)
        ch_az.sort(key=lambda c: c["az"])
        ch_el.sort(key=lambda c: c["az"])
        pos_to_idx: dict = {}
        for i, c in enumerate(ch_az):
            pos_to_idx.setdefault(c["az"], []).append(i)
        overlaps = [tuple(v[:2]) for v in pos_to_idx.values() if len(v) > 1]
        return ch_az, ch_el, overlaps

    def print_summary(self):
        print(f"  CFAR cfg    : guard={self.cfar_guard} train={self.cfar_train}  "
              f"fa={self.cfar_fa_rate:g} margin={self.cfar_margin_db:g} dB  "
              f"nms={self.nms_size}")
        print(f"  Filters     : clutter={'ON' if self.clutter_removal else 'OFF'}  "
              f"zeroDC=±{self.zero_dc_bins}  "
              f"sidelobes={'ON' if self.apply_sidelobe_filters else 'OFF'}")
        print("=" * 62)
        print(f"  AWR2243-2X  |  {self.num_tx}TX / {self.num_rx}RX  |  "
              f"{self.chirps_per_frame} chirps/frame")
        print(f"  Range res   : {self.range_res_m*100:.2f} cm   "
              f"Max range : {self.range_axis[-1]:.1f} m")
        print(f"  Doppler max : ±{self.dop_max:.3f} m/s  "
              f"(calc. from waveform)")
        print(f"  Doppler res : {self.dop_res:.4f} m/s")
        print(f"  dB scale    : {'fixed' if self.use_fixed_db else 'adaptive'}  "
              f"({'%g–%g' % (self.db_vmin,self.db_vmax) if self.use_fixed_db else 'span=%g dB' % self.db_span})")
        print(f"  AoA method  : {self.aoa_method.upper()}  "
              f"CFAR: {self.cfar_method.upper()}  "
              f"Moving gate: {'ON' if self.moving_objects_only else 'OFF'}")
        print("=" * 62)


# ---------------------------------------------------------------------------
# .cfg parser
# ---------------------------------------------------------------------------

def _tok(text: str, kw: str):
    for raw in text.splitlines():
        line = raw.split('%')[0].strip()
        if line and line.split()[0].lower() == kw.lower():
            return [float(x) for x in line.split()[1:]]
    return None


def parse_cfg_file(cfg_path: str) -> RadarConfig:
    if not os.path.isfile(cfg_path):
        raise FileNotFoundError(cfg_path)
    with open(cfg_path, 'r', errors='replace') as f:
        text = f.read()
    cfg = RadarConfig()
    cfg.calib_cfg_path = cfg_path
    prof = _tok(text, "profileCfg")
    frm  = _tok(text, "frameCfg")
    buf  = _tok(text, "adcbufCfg")
    if not prof or len(prof) < 11: raise ValueError("profileCfg missing")
    if not frm  or len(frm)  < 3:  raise ValueError("frameCfg missing")
    if not buf  or len(buf)  < 3:  raise ValueError("adcbufCfg missing")
    cfg.start_freq_ghz   = float(prof[1])
    cfg.idle_time_us     = float(prof[2])
    cfg.ramp_end_us      = float(prof[4])
    cfg.slope_mhz_us     = float(prof[7])
    cfg.num_samples      = int(prof[9])
    cfg.sample_rate_ksps = float(prof[10])
    cfg.num_tx           = int(frm[1]) - int(frm[0]) + 1
    cfg.num_loops        = int(frm[2])
    # Match capture/test.py semantics exactly:
    # SampleSwap=1 -> raw [Q, I], SampleSwap=0 -> raw [I, Q].
    cfg.iq_swap          = bool(int(buf[2]))
    cfg.range_fft_size   = _next_pow2(cfg.num_samples)
    cfg.doppler_fft_size = _next_pow2(cfg.num_loops)
    print(f"[CFG] {os.path.basename(cfg_path)}: "
          f"slope={cfg.slope_mhz_us:.3f} MHz/µs  fs={cfg.sample_rate_ksps:.0f} ksps  "
          f"N={cfg.num_samples}  loops={cfg.num_loops}  "
          f"dop_max=±{cfg.dop_max:.3f} m/s")
    return cfg


def apply_raw_iq_order_override(cfg: RadarConfig, mode: str) -> RadarConfig:
    """
    Match capture/test.py raw IQ override semantics.

    "cfg"     -- keep iq_swap as parsed from adcbufCfg SampleSwap
    "i-first" -- raw pairs are [I, Q]
    "q-first" -- raw pairs are [Q, I]
    """
    mode = str(mode).lower()
    if mode == "cfg":
        return cfg
    if mode == "i-first":
        cfg.iq_swap = False
        return cfg
    if mode == "q-first":
        cfg.iq_swap = True
        return cfg
    raise ValueError(f"Unknown raw IQ order override: {mode!r}")


def parse_calibration(cfg_path: str, num_tx: int = 6, num_rx: int = 8,
                      enabled: bool = True) -> np.ndarray:
    identity = np.ones((num_tx, num_rx), dtype=np.complex64)
    if not enabled:
        return identity
    if not os.path.isfile(cfg_path):
        return identity
    with open(cfg_path, 'r', errors='replace') as f:
        text = f.read()
    flat = []
    for cmd in ('antennacalibparams1', 'antennacalibparams2', 'antennacalibparams3'):
        t = _tok(text, cmd)
        flat.extend(t if (t and len(t) == 32) else [1.0, 0.0] * 16)
    if len(flat) != 96:
        return identity
    corr = identity.copy()
    for k in range(num_tx * num_rx):
        tx, rx = k // num_rx, k % num_rx
        corr[tx, rx] = float(flat[2*k]) * np.exp(1j * np.deg2rad(float(flat[2*k+1])))
    return corr


def _next_pow2(n: int) -> int:
    p = 1
    while p < n: p <<= 1
    return p


def shortrange_config() -> RadarConfig:
    return RadarConfig()
