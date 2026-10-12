#!/usr/bin/env python3
"""
check_radar_session.py - data-integrity and decode check for cascade radar sessions.

Usage:
    python3 check_radar_session.py <session_dir> [--png out.png]

<session_dir> contains radar/frame_*.bin (3,145,728 B each) and optionally
sync/lidar_target_truth.csv. Needs numpy; matplotlib only for --png.

Checks
  1. Stale-word test: fraction of int16 identical in every frame. A healthy
     stream is ~0 %. The r075m defect gives ~50 %, in 32-byte blocks, with a
     mask that repeats every 2 chirps (CSI-RX ping/pong buffers).
  2. Range-time decode (I-first, chirp = loop*6 + tx, per-frame clutter
     removal) and, if the truth file exists, radar peak vs LiDAR range.

Frame layout (see JETSON_DATA_FORMAT.md):
  int16 LE [chirp 0..383][dev 0..1][rx 0..3][sample 0..255][I, Q]
"""
import argparse, csv, glob, os, sys
import numpy as np

N_CHIRP, N_DEV, N_RX, N_S = 384, 2, 4, 256
FRAME_I16 = N_CHIRP * N_DEV * N_RX * N_S * 2
C = 299792458.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("--slope-mhz-us", type=float, default=19.9878)
    ap.add_argument("--fs-ksps", type=float, default=10000.0)
    ap.add_argument("--period-s", type=float, default=0.25, help="0.125 for 8 fps")
    ap.add_argument("--png", default=None)
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(a.session, "radar", "frame_*.bin")))
    if len(files) < 3:
        sys.exit("need at least 3 frames")
    bad = [f for f in files if os.path.getsize(f) != FRAME_I16 * 2]
    print(f"frames: {len(files)}   wrong size: {len(bad)}")

    # ---- 1. stale-word test (streamed, low memory) ----
    f0 = np.fromfile(files[0], dtype=np.int16)
    const = np.ones(FRAME_I16, bool)
    for f in files[1:]:
        const &= (np.fromfile(f, dtype=np.int16) == f0)
    frac = const.mean()
    m = const.reshape(N_CHIRP, -1)
    period2 = bool((m[0::2] == m[0]).all() and (m[1::2] == m[1]).all())
    print(f"identical in every frame: {100 * frac:.2f} %   "
          f"(healthy ~0 %; r075m defect ~50 %)   period-2 chirp mask: {period2}")
    if frac > 0.01:
        b = const.reshape(-1, 16)
        print(f"  32-byte block aligned: {bool(((b.all(1)) | (~b.any(1))).all())}   "
              f"mean |stale value| {np.abs(f0[const].astype(np.int32)).mean():.0f} "
              f"(uniform garbage ~16384)")
        print("  VERDICT: STALE BUFFER WORDS PRESENT - data degraded (~half the samples per channel missing)")
    else:
        print("  VERDICT: no stale words")

    # ---- 2. range-time decode ----
    rbin = C * a.fs_ksps * 1e3 / (2 * a.slope_mhz_us * 1e12 * N_S)
    win = np.hanning(N_S).astype(np.float32)
    prof = []
    for f in files:
        x = np.fromfile(f, dtype=np.int16).astype(np.float32).reshape(64, 6, N_DEV, N_RX, N_S, 2)
        z = x[..., 0] + 1j * x[..., 1]                 # I first
        z -= z.mean(axis=0, keepdims=True)             # per-frame clutter removal
        prof.append((np.abs(np.fft.fft(z * win, axis=-1)) ** 2).sum(axis=(0, 1, 2, 3)))
    P = np.array(prof)
    rng = np.arange(N_S) * rbin
    print(f"range bin {rbin:.4f} m, max range {rng[-1] + rbin:.2f} m")

    truth = os.path.join(a.session, "sync", "lidar_target_truth.csv")
    tr = None
    if os.path.isfile(truth):
        rows = list(csv.DictReader(open(truth)))
        tr = np.array([float(r["target_range_m"]) if r["target_range_m"] else np.nan
                       for r in rows])[:len(P)]
        ok = np.isfinite(tr)
        if ok.any():
            lo, hi = max(np.nanmin(tr) - 4, 1.0), np.nanmax(tr) + 4
            sel = (rng > lo) & (rng < hi)
            pk = rng[sel][np.argmax(P[:, sel], axis=1)]
            e = pk[ok] - tr[ok]
            print(f"radar peak vs LiDAR ({ok.sum()} frames): median |err| "
                  f"{np.median(np.abs(e)):.3f} m, within 2 bins: "
                  f"{100 * np.mean(np.abs(e) < 2 * rbin):.1f} %")

    if a.png:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        t = np.arange(len(P)) * a.period_s
        db = 10 * np.log10(P / np.median(P, axis=0))
        plt.figure(figsize=(10, 5))
        plt.imshow(db.T, origin="lower", aspect="auto", cmap="Greys", vmin=0, vmax=20,
                   extent=[t[0], t[-1], 0, rng[-1]])
        if tr is not None:
            plt.plot(t[:len(tr)], tr, ".", ms=3, color="#d55e00", label="LiDAR")
            plt.legend(frameon=False)
        plt.ylim(0, 40); plt.xlabel("time (s)"); plt.ylabel("range (m)")
        plt.tight_layout(); plt.savefig(a.png, dpi=120); print("wrote", a.png)


if __name__ == "__main__":
    main()
