# Step-by-Step Debugging Plan — Isolate Root Cause of Frame Corruption

Each step is an actionable experiment with: **goal · setup · run · pass/fail criterion · next action**. Stop branches mark when a step's outcome dictates a different path.

---

## E1 — Confirm or refute on-chip compression as the cause
**Goal:** Test H9. The cfg edit `compressionCfg -1 1 ...` → `... -1 0 ...` is already applied.

**Setup:** Same physical scene as previous run. No other cfg changes.

**Run (Windows host):**
```powershell
python capture\test.py --uart COM20 --frames 30 --warmup-frames 60 --frame-stats --sync-wait 90
python processing\diag_frame_stationarity.py --folder capture\frames --cfg config\build_shortrange_inf\cascade_shortrange.cfg
```

**Pass criterion (E1-PASS):**
- `static_dB` span < 2 dB **AND** `slow_var_dB` span < 2 dB
- `raw_mean max/min` < 1.3
- Diagnostic verdict prints `STABLE`

**Fail criterion (E1-FAIL):**
- Either span > 5 dB → compression was not the cause; proceed to E2.

**Action on PASS:** Skip directly to E5 (reflector test).
**Action on FAIL:** Proceed to E2.

---

## E2 — Localize the amplitude cycle in time
**Goal:** Determine whether the ~10-frame oscillation is locked to a firmware clock (deterministic period) or stochastic. Discriminates H10 (firmware re-cal cycle) from H11 (AGC) from a still-unknown noise source.

**Setup:** Capture a long, uninterrupted run.

**Run:**
```powershell
python capture\test.py --uart COM20 --frames 200 --warmup-frames 60 --frame-stats --sync-wait 120
python processing\diag_frame_stationarity.py --folder capture\frames --cfg config\build_shortrange_inf\cascade_shortrange.cfg > diag_200.txt
```

Then on any host:
```bash
python3 - <<'PY'
import numpy as np, re
vals = []
for ln in open('diag_200.txt'):
    m = re.match(r'^\s*\d+\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)', ln)
    if m: vals.append(float(m.group(2)))   # static_dB
x = np.asarray(vals) - np.mean(vals)
acf = np.correlate(x, x, 'full')[len(x)-1:]
acf /= acf[0]
peaks = [(i, acf[i]) for i in range(2, min(40,len(acf))) if acf[i] > 0.4]
print('static_dB ACF peaks (lag, acf):', peaks[:6])
print('span (dB):', float(x.max()-x.min()))
PY
```

**Pass criterion (E2-PERIODIC):**
- A single dominant ACF peak at lag N with `acf[N] > 0.5` → **deterministic period N frames**. → H10 confirmed (firmware re-cal cycle).

**Fail criterion (E2-RANDOM):**
- ACF decays to noise within 2 lags, no peak > 0.4 → stochastic. → H10 rejected; consider H11 / H14.

**Action on E2-PERIODIC:** Proceed to E3 to identify which frames in the cycle are usable.
**Action on E2-RANDOM:** Skip to E6.

---

## E3 — Identify "clean" vs "calibration" frames within the cycle
**Goal:** Determine if every N-th frame is the disturbed one, or every (N−1) frames are clean and 1 frame is disturbed. Lets us either discard a known phase or accept periodic processing.

**Setup:** Same 200-frame capture from E2.

**Run:**
```bash
python3 - <<'PY'
import numpy as np, re
vals = [float(re.match(r'^\s*\d+\s+([\d.]+)\s+([\d.-]+)', ln).group(2))
        for ln in open('diag_200.txt')
        if re.match(r'^\s*\d+\s+[\d.]+\s+[\d.-]+', ln)]
x = np.asarray(vals)
N = int(input("period N from E2: "))
phases = [x[k::N] for k in range(N)]
for k, ph in enumerate(phases):
    print(f"phase {k}: n={len(ph):3d}  mean={ph.mean():7.2f}  std={ph.std():5.2f}  min={ph.min():7.2f}  max={ph.max():7.2f}")
PY
```

**Pass criterion (E3):** One phase shows std > 3× the others → that phase is the calibration glitch.

**Action:** Add `--decimate-mod N --decimate-keep-phases p1,p2,...` to capture or processing — discard the disturbed phase. Re-run E1's diagnostic on the decimated subset; expect spans < 2 dB.

---

## E4 — Cross-check via RX power sanity (only run if E3 doesn't clean it up)
**Goal:** Test H11 (intra-frame AGC) vs H14 (Dev0/Dev1 incoherence).

**Setup:** Same frames, but measure per-device and per-chirp statistics.

**Run:** Extend diag_frame_stationarity.py with a `--per-rx` mode that reports `mean|x|` separately for Dev0 RX[0:4] and Dev1 RX[4:8].

**Pass / discriminate:**
- Dev0 mean and Dev1 mean track each other → both devices see the same input gain → suggests H11 (shared AGC) or H10 (shared calibration).
- Dev0 and Dev1 diverge frame-to-frame → **inter-chip incoherence** → H14.

---

## E5 — Positive falsifier: corner reflector
**Goal:** Only test that distinguishes "noise + fallback" from "real signal". Run **as soon as E1 or E3 yields a stable input**.

**Setup:** Corner reflector at 3.00 m, 0° azimuth, 0° elevation. RCS ≈ 10 dBsm or use any metallic plate ≥ 20 × 20 cm. Mounting height matches radar.

**Run:**
```powershell
python capture\test.py --uart COM20 --frames 30 --warmup-frames 60 --frame-stats --sync-wait 90
python -m processing.main --folder capture\frames --cfg config\build_shortrange_inf\cascade_shortrange.cfg --no-show --save out.png
```

**Pass criterion (E5-PASS, real signal):**
- `xyz_cloud` non-empty with `src=cfar-mask` (not fallback) on ≥ 80% of frames.
- Reported range ∈ [2.85, 3.15] m, azimuth ∈ [−4°, +4°].
- RD peak ≥ 20 dB above local RD median.
- Reported range stable across frames within 1 range bin (±6.6 cm).

**Fail criterion (E5-FAIL):**
- Range outside ±15 cm of truth → range axis or calibration wrong.
- Azimuth ≠ 0° → virtual-array geometry mismatch (test H13).
- `src=power-fallback` only → CFAR still cannot detect a strong reflector → DSP gain or `cfar_min_power_db` setting wrong.
- Cloud empty entirely → input still corrupted; return to E1.

---

## E6 — Verify IQ ordering (H4)
**Goal:** Confirm that `--raw-iq-order=i-first` is actually correct.

**Setup:** Single-tone source pointed at the radar at ~3 m, OR the corner reflector from E5.

**Run:** Read one frame, FFT along range, compare bin of positive peak vs bin of negative peak. Easiest: tweak diag_frame_stationarity.py temporarily to print `argmax(|R_fft|)` per TX, RX, loop. Or:
```bash
python3 - <<'PY'
import numpy as np, importlib.util, sys
spec = importlib.util.spec_from_file_location("rc","processing/radar_config.py")
rc = importlib.util.module_from_spec(spec); sys.modules["rc"]=rc; spec.loader.exec_module(rc)
cfg = rc.parse_cfg_file("config/build_shortrange_inf/cascade_shortrange.cfg")
N = cfg.num_samples
a = np.fromfile("capture/frames/frame_000005.bin", dtype=np.int16).reshape(-1,2)
# Try both IQ orders
for swap, lbl in [(False,"I,Q"),(True,"Q,I")]:
    i,q = (a[:,0],a[:,1]) if not swap else (a[:,1],a[:,0])
    z = (i + 1j*q).reshape(-1, N)[:32]   # 32 chirps
    R = np.fft.fft(z, axis=-1)
    print(f"{lbl}: peak bin distribution top5 -> "
          f"{np.bincount(np.argmax(np.abs(R),axis=-1), minlength=N).argsort()[-5:][::-1]}")
PY
```

**Pass:** Peak bins concentrate at **low positive** bin (< N/2) → I,Q is correct → keep `i-first`.
**Fail:** Peaks concentrate at **high bins** (close to N) → Q,I is correct → change default to `q-first`.

---

## E7 — Range alias verification (H7)
**Goal:** Confirm range bins > N/2 are aliases, not real signal.

**Setup:** Place reflector at known position 6 m, 0°. Then move it to 12 m, 0° (just past Nyquist 8.44 m).

**Run:** Same processing. Inspect RD peak location.

**Pass:** 6 m reflector → peak at bin ≈ 91; 12 m reflector → peak at bin ≈ 91 (alias 16.8 − 12 = 4.8 m) **or** no peak at all if anti-alias filter is sharp.
**Action:** Confirms the recommendation `n_range = N_fft / 2` is necessary. Implement P4 from the prior plan.

---

## E8 — DCA file-rotation latent bug (deferred until needed)
**Goal:** Verify `FileMonitor` handles `Raw_0.bin` → `Raw_1.bin` boundary.

**Run:** Capture > 340 frames in a single run (passes 1 GB rotation point):
```powershell
python capture\test.py --uart COM20 --frames 400 --warmup-frames 60 --frame-stats --sync-wait 120
python processing\diag_frame_stationarity.py --folder capture\frames ...
```
**Pass:** Diagnostic shows no statistical discontinuity around frame index ≈ 340.
**Fail:** Frames 340–342 show anomalous `static_dB` → split was misaligned at the rotation boundary → implement the FileMonitor drain-then-switch fix.

Run only when capture campaigns exceed 340 frames.

---

## Decision Tree (summary)

```
E1 (compression off)
 ├─ PASS  → E5 (reflector)
 │           ├─ PASS → E6 + E7 (validation) → pipeline trustworthy after P3+P4 code edits
 │           └─ FAIL → debug DSP gain/CFAR; geometry (H13); calibration vs cfg (H1)
 │
 └─ FAIL  → E2 (autocorr 200 frames)
             ├─ PERIODIC (H10) → E3 (identify clean phase) → decimate → E5
             └─ RANDOM         → E4 (per-device split)
                                 ├─ Dev0/Dev1 coupled → H11 AGC → firmware/hardware escalation
                                 └─ Dev0/Dev1 split   → H14 LO incoherence → cascade sync issue
```

---

## What to NOT do
- Do not re-tune `cfar_min_power_db`, `cfar_margin_db`, `gaussian_sigma`, or `db_span` until E1 + E2 + E5 are complete. Knob-tuning before input is stationary is the most common source of false-confirmation in this audit.
- Do not enable Capon or MUSIC AoA for diagnostic runs. They amplify whatever covariance structure exists in noise. Keep FFT AoA throughout E1–E7.
- Do not run `--all-frames --save-dir ...` for plot generation until E5 passes. The fallback paths in radar_plots.py will produce convincing-looking output regardless of input validity.

---

## Single first action
Run **E1** on the Windows host. The cfg change is committed; everything downstream branches from that one diagnostic line:

```
[diag] verdict heuristic:
  STABLE / STATIC VARIES / NOISE VARIES / BOTH VARY
```

Send that block back and I'll route to E2 or E5.