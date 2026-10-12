# Investigation Snapshot — Cascaded mmWave Radar Pipeline Audit

## 1. Problem Description

**System:** AWR2243-2X cascaded mmWave radar (2-chip, 6 TX TDM MIMO, 8 RX) on a TI AM273x carrier, captured via DCA1000EVM over UDP, processed by a Python offline DSP pipeline.

**Repo:** `cascaded_radar_win_dev` (Windows-only capture; processing portable).

**Key code paths:**
- Capture: test.py, dca.py, radar.py, config.py
- Processing: main.py, radar_reader.py, radar_processing.py, radar_plots.py, radar_config.py
- Diagnostic added during this investigation: diag_frame_stationarity.py
- Radar cfg used: cascade_shortrange.cfg
- DCA JSON: AM273X_Capture_fixed.json
- Firmware header: cascade_csirx.h

**Intended behavior:** Capture coherent ADC IQ frames, run range-FFT → MTI → Doppler FFT → CFAR → AoA (FFT/Capon/MUSIC) → elevation FFT → produce a physically meaningful 3D point cloud of real reflectors.

**Operator suspicion:** Output point cloud may be noise/artifact rather than real targets. A static indoor scene currently yields **0 CFAR detections across all frames**, which is physically expected with MTI on, but multiple non-crashing failure modes have been demonstrated that would make any positive result equally suspect.

---

## 2. Observed Symptoms

### Frame-to-frame amplitude oscillation (primary symptom)
After firmware load + 60-frame warmup (well past TI calibration time), saved frames show:
- `mean|x|` swings between **333 and 1025 LSB** over 30 consecutive frames → **3.08× peak-to-peak**.
- Pattern is cyclical (~10-frame period at the actual ~4 fps capture rate), not monotonic settling.
- `I_dc` drifts ±2 LSB, `Q_dc` drifts ±3 LSB (small but coherent with amplitude cycle).

### Pipeline output instability
Processing dB-span moves 40+ dB across consecutive frames in the **same static scene**:
- frame 13 (mean|x|=956) → 92–116 dB
- frame 17 (mean|x|=388) → 48–72 dB
- 24 dB span tracks raw amplitude 1:1 (this is the cfg `db_span=24` adaptive window saturating).

### Diagnostic (diag_frame_stationarity.py) on current data
```
static_dB   span = 11.38 dB   (coherent-across-loops energy)
slow_var_dB span = 20.84 dB   (variance-across-loops energy)
dc_frac     ≈ 1e-4            (IQ DC offset negligible)
raw_mean    max/min = 3.08
Verdict: BOTH VARY -> input-power scaling drift
```

`static` and `slow_var` move proportionally (slope ratio ~2 in dB-space, i.e. linear in power) → consistent with an **input-amplitude rescaling** rather than scene dynamics.

### Capture rate anomaly
- `frameCfg ... 50 ...` in cfg implies 50 ms (20 fps) but **actual capture rate ≈ 4 fps** (251 frames in 63 s in earlier run; 30 frames in ~10 s most recent). TI cascade firmware appears to interpret periodicity differently or inserts per-frame calibration cycles.

### CFAR always zero
- 0 detections in every frame of every run with MTI on. Cannot be interpreted as a clean negative because the input is non-stationary.

---

## 3. Environment

- **OS:** Windows 10/11 for capture (requires TI Code Composer Studio, DCA1000EVM_CLI_Control.exe, PowerShell, XDS110 debugger). Analysis/investigation done on Linux (this conversation).
- **Python:** 3.10+ (this analysis used 3.13); numpy, scipy, matplotlib.
- **TI tools:** mmWave Studio 03.00.00.14, CCS 20.5.0.
- **Network:** PC `192.168.33.30`, DCA1000 `192.168.33.180`, UDP 4096 (config), 4098 (data).
- **Serial:** UART on COM20 for `sensorStop`.
- **Hardware:** AWR2243-2X-CAS-EVM + DCA1000 + XDS110.
- **Constraints:**
  - Cannot modify cascade firmware binary (`am273x_cascade_mss.xer5f`) from this codebase.
  - Cannot reproduce capture on the Linux analysis host — Linux side has raw bins + logs only.
  - The DCA recorder splits files at 1024 MB (`maxRecFileSize_MB`) → multiple `Raw_*.bin` files for long captures.

---

## 4. Current Understanding of the Pipeline

```
Radar physics (FMCW 77 GHz)
  → AWR2243 ADC (256 samples @ 5 Msps, slope 44.41 MHz/µs)
  → LVDS to DCA1000 FPGA
  → UDP packets (1456 B payload each) over Ethernet
  → DCA1000EVM_CLI_Record.exe writes raw stream to am273x_capture_Raw_*.bin
  → FileMonitor thread tails Raw_*.bin, slices into 3,145,728 B frame_NNNNNN.bin
  → processing.radar_reader.read_frame() reshapes int16 IQ into
       complex64 cube [num_tx, num_loops, num_rx, num_samples] = (6, 64, 8, 256)
  → DSP: calibration → range FFT → MTI → virtual-array form
         → Doppler FFT + zero-DC notch → RD CFAR
         → AoA (FFT default; Capon/MUSIC available) → RA CFAR
         → elevation FFT → arrDREA tensor → xyz point cloud
  → radar_plots renders 5-panel figure (RD, RE, RA rect, RA polar, 3D/2D cloud)
```

**Frame geometry (matches both sides):** 6 TX × 64 loops × 8 RX × 256 samples × 4 B = 3,145,728 B / frame.

**Critical pipeline-internal behaviors (relevant to non-crashing failure modes):**
- `_ra_focus_mask_from_rd` selects top-K Doppler bins when CFAR is empty for a range → can build coherent-looking RA from noise.
- `_fallback_from_ra_power` in radar_plots.py generates a "cloud" from top-percentile RA when `xyz_cloud` is empty.
- Range axis extends to 22.5 m but Nyquist beat range is **8.44 m** → bins 96–255 are aliases.
- No TDM-Doppler phase compensation across TX → moving targets get biased azimuth.
- No input-power normalization → CFAR's absolute floor `cfar_min_power_db=12` is amplitude-sensitive.

---

## 5. Hypotheses Considered

| # | Hypothesis | Status |
|---|---|---|
| H1 | Capture and processing using mismatched cfgs (shortrange vs longrange) destroys coherence | **Confirmed (initial run); Resolved** |
| H2 | FPGA preamble at start of Raw_*.bin shifts all frame splits | **Rejected** (byte arithmetic: 542,832 pkts × 1456 = bin size exactly; preamble does not exist) |
| H3 | First N frames after sensorStart are firmware warm-up and should be discarded | **Confirmed contributes; insufficient by itself** (--warmup-frames=60 still leaves cyclical instability) |
| H4 | DCA1000 silently swaps IQ regardless of SampleSwap | **Still open** (codebase hard-overrides to `i-first` without verification) |
| H5 | Effective frame rate ≠ cfg periodicity; actual ~4 fps | **Confirmed** (251 frames / 63 s) |
| H6 | TDM Doppler-azimuth coupling biases moving-target AoA | **Confirmed (code review)** — no compensation present |
| H7 | Range axis upper half is alias content, not real range | **Confirmed (code review)** — `N_r = range_fft_size = 256`, but Nyquist beat range only covers half |
| H8 | RA / cloud fallback paths fabricate structure from noise | **Confirmed (code review)** — explicit fallback branches in radar_plots and radar_processing |
| H9 | On-chip `compressionCfg` reaching LVDS causes amplitude rescaling | **Currently leading hypothesis — pending physical verification.** Cfg now changed `compressionCfg -1 1 0 0.5 8` → `... -1 0 ...`. Awaiting new capture. |
| H10 | Firmware-level inter-frame calibration / phase-shifter cycling causes amplitude oscillation | **Still open** — will be confirmed if H9 fix does not stabilize the diagnostic |
| H11 | AGC drift within frames | **Still open** — would manifest as `slow_var_dB` varying while `static_dB` is stable; not seen yet |
| H12 | FileMonitor mis-handles file rotation when DCA rolls Raw_0→Raw_1 at 1 GB | **Confirmed latent bug** — irrelevant for ≤340-frame runs; deferred |
| H13 | Hardcoded virtual-array TX/RX positions in `_TX_AZ`, `_RX_AZ` vs actual cfg chirp→TX map | **Still open** — capture-side warns on mismatch; processing-side never checks |
| H14 | Inter-chip LO phase drift between Dev0 and Dev1 corrupts cascade aperture | **Still open** — would not be visible in the current diagnostic; needs a corner-reflector test |

---

## 6. Confirmed Findings

1. **Byte transport is clean.** DCA `Out of sequence count = 0`. Packet count × 1456 B exactly equals raw bin size. No preamble, no headers in Raw mode.
2. **Frame splitting is byte-correct for ≤340 frames** (single Raw_*.bin). All 30 saved frames are exactly 3,145,728 B.
3. **Steady-state amplitude oscillates 3.08× peak-to-peak** in a static indoor scene with 60-frame warmup applied.
4. **`static_dB` and `slow_var_dB` move proportionally** (11.4 dB and 20.8 dB span respectively) — signature of input-power rescaling, not scene dynamics.
5. **`dc_frac ≈ 1e-4`** → IQ DC offsets are not the dominant artifact; the variation is in real signal energy.
6. **CFAR=0 is unreliable as a negative**: input non-stationarity defeats the CFAR stationary-noise assumption.
7. **Processing pipeline contains three explicit, unguarded fallback paths** that can synthesize structured output from noise: `_ra_focus_mask_from_rd`, `_fallback_from_ra_power`, and the 99.5-percentile branch in `plot_pc3d`.
8. **Range axis extends 2.7× past the Nyquist beat range** (16.8 m configured vs 8.44 m physical). Range bins above 8.44 m are aliases.
9. **No input-power normalization anywhere** in the DSP chain → absolute-dB CFAR floor is gain-sensitive.
10. **Capture-side warm-up discard (`--warmup-frames`) works correctly.** Frames are skipped at the FileMonitor level before disk write, without incrementing `frame_idx`.
11. **`--frame-stats` diagnostic at capture time matches the post-hoc diagnostic** on saved frames — confirms the on-disk frames represent what the FileMonitor saw.

---

## 7. Rejected Hypotheses (with reason)

- **H1 (cfg mismatch):** Initially demonstrated by user running shortrange capture + longrange processing. Resolved by aligning both to shortrange cfg. Not the current symptom.
- **H2 (FPGA preamble):** Byte arithmetic falsifies it. `Raw_0.bin = packets × 1456 B` exactly. The `raw_stream=74,997,760 B` snapshot identical between two runs was just the FileMonitor's read-pointer at `--frames` stop, not a fixed preamble.

---

## 8. Key Insights / Patterns

1. **The pipeline can be "successful" without being correct.** Every layer has a graceful-degradation path that hides upstream failure. Specifically: cfg mismatch → no crash; byte misalignment → no crash; non-stationary input → CFAR=0 (looks like correct rejection); CFAR empty → fallback fabricates a cloud.

2. **Amplitude cycling is ~2.5 s period at 4 fps capture** — consistent with TI cascade firmware running a periodic re-calibration routine that perturbs the active TX/RX state.

3. **`static_dB` and `slow_var_dB` co-varying linearly in power** is the discriminating signature. Real scene dynamics would change one without the other.

4. **The cfg file contains tracker/RANSAC lines (`gtrack`, `ransac`, `appGatingParams`) that this codebase does not implement.** Operators may believe a tracker is filtering the output when none exists.

5. **TX/RX virtual-array geometry is hardcoded in radar_config.py** (`_TX_AZ = [0,4,7,11,15,2]`, `_RX_AZ = [0,1,2,3,19,20,21,22]`) — does not get re-validated against the capture-side chirp→TX map. Silent inconsistency risk.

6. **Cascade firmware's actual frame rate cannot be derived from the cfg alone**; it must be measured from capture log timestamps.

---

## 9. Known Unknowns

1. **Whether disabling `compressionCfg` will stabilize the amplitude cycling** — change is committed, capture not yet re-run.
2. **Whether DCA1000 firmware repacks IQ regardless of `SampleSwap`** — codebase comments admit uncertainty; current `--raw-iq-order=i-first` override coincidentally matches `SampleSwap=0` so the symptom would be invisible.
3. **Whether the cascade firmware does inter-frame phase-shifter / TX calibration** that fundamentally cannot be defeated from this codebase.
4. **Whether Dev0 and Dev1 share a coherent LO** under the current firmware configuration — affects 8-RX cascade aperture validity.
5. **What the cascade firmware actually does between frames** — no echo-back over UART; no `MMWave_open → config → calibrate → start` confirmation is parsed even though the log claims that sequence runs.
6. **Whether range bin > 96 contains any real return** — never tested with a known reflector beyond 8.44 m (and physically should not be possible without aliasing).
7. **AGC behavior** — TI AWR2243 has internal RF gain stages; cfg does not show explicit AGC settings.

---

## 10. Recommended Next Steps (Prioritized)

### Priority 1 — Verify the compression hypothesis (already-prepared experiment)
**Status:** cfg edit applied; needs Windows-side capture run.
```powershell
python capture\test.py --uart COM20 --frames 30 --warmup-frames 60 --frame-stats --sync-wait 90
python processing\diag_frame_stationarity.py --folder capture\frames --cfg config\build_shortrange_inf\cascade_shortrange.cfg
```
**Decision rule:**
- `static_dB` span < 2 dB **and** `slow_var_dB` span < 2 dB → H9 confirmed; proceed to P2.
- Either span still > 5 dB → H9 rejected; H10 (firmware calibration) is the cause; escalate to firmware rebuild.

### Priority 2 — Place a corner reflector at 3 m, 0° azimuth, repeat capture
Once amplitude is stable, this is the only positive falsification test. Expected:
- Range bin at 3.0 / 0.066 ≈ 45 should peak ≥ 20 dB above local median in the RD map.
- RA peak at az bin 128 (0°), ≥ 6 dB above flanking azimuth.
- `xyz_cloud` non-empty with `src=cfar-mask` (not fallback).

### Priority 3 — Eliminate fallback paths so any observed cloud is meaningful
In radar_plots.py: gate `_fallback_from_ra_power` and the 99.5-percentile branch behind an explicit `--show-noise-fallback` flag. In radar_processing.py `_ra_focus_mask_from_rd`: when `rd_det[:, ri].sum() == 0`, leave RA at floor for that range instead of selecting top-K noise peaks.

### Priority 4 — Truncate range axis to the Nyquist beat range
In radar_config.py `n_range` property: clamp to `floor(N_fft / 2)` (i.e. 128 for N=256). Add assertion that `range_axis[-1] ≤ nyquist_beat_range_m`.

### Priority 5 — TDM Doppler phase compensation
For each Doppler bin k and TX index t, multiply the per-TX slice by `exp(-j 2π k τ_t / T_loop)`. Add in `form_virtual_arrays` or just after `doppler_fft` in radar_processing.py.

### Priority 6 — Add capture-cfg fingerprint to frame metadata
Write a sibling `frames/_capture_meta.json` containing the SHA-256 and key waveform fields of the cfg used at capture time. Have main.py compare on load and **refuse to process on mismatch**.

### Priority 7 — Fix latent FileMonitor file-rotation bug
In dca.py `FileMonitor.find_latest_bin()`: when a new file appears, drain the previous file's tail bytes before switching. Currently only relevant beyond ~340 frames (1 GB / 3.15 MB), but will silently mis-split otherwise.

### Priority 8 — Verify IQ ordering once
One-time test: capture a single tone (signal generator) or a corner reflector at known range. The range-FFT peak should appear at positive frequency. If it appears at the negative-frequency bin (FFT bin N-k instead of k), IQ is swapped — adjust `--raw-iq-order` default accordingly.

### Priority 9 — TI cascade phase-shifter calibration audit
Read `cascade_csirx.h` and the cascade firmware sources (outside this repo) for `MMWAVE_LINK_PROFILE_CHIRP_CONF_IDX` and BPM / phase-shifter calibration period. If calibration cannot be disabled in firmware, the only workaround is **discard every Nth frame** that falls on the calibration cycle — measure N from the next stable-`compression-off` capture by checking the `mean|x|` autocorrelation.

### Verdict held over from previous turns
**❌ Pipeline can plausibly generate false detections.** Unchanged. Verdict is gated on P1+P2 results and P3 implementation.

---

## Appendix — Files modified in this investigation

| File | Change |
|---|---|
| dca.py | Added `_frame_stat_str`, `warmup_frames`/`frame_stats` kwargs on `FileMonitor` and `run_capture`. Per-frame stat line + warm-up discard counter. |
| test.py | Added `--warmup-frames N` and `--frame-stats` CLI flags; threaded into `run_capture`. |
| cascade_shortrange.cfg | `compressionCfg -1 1 0 0.5 8` → `compressionCfg -1 0 0 0.5 8` (disable ADC compression). |
| diag_frame_stationarity.py | **New**. Standalone numpy-only diagnostic: per-frame `static_dB`, `slow_var_dB`, `dc_frac`, verdict heuristic. Bypasses __init__.py via direct `importlib` load of `radar_config` to avoid matplotlib dependency. |

No other DSP behavior was modified — the priorities P3–P5 are still pending and constitute the most consequential code changes if the system is to be trusted.