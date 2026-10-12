# Compact Brief — Cascaded Radar Pipeline Audit

## System
- AWR2243-2X cascade (6 TX TDM, 8 RX) → DCA1000 UDP → Python DSP.
- Repo: `cascaded_radar_win_dev`. Windows-only capture; processing portable.
- Frame = 6 TX × 64 loops × 8 RX × 256 samples × 4 B = **3,145,728 B**.
- Cfg in use: cascade_shortrange.cfg (slope 44.41 MHz/µs, fs 5 Msps, λ/2 cascade aperture).
- Intended: range/Doppler/AoA → CFAR → xyz cloud of real reflectors.
- Suspicion: 0-CFAR results may be masking either real failure or fabricated structure from fallbacks.

## Symptoms (static indoor scene, 60-frame warmup applied)
- `mean|x|` 333–1025 LSB across 30 saved frames → **3.08× peak-to-peak**, ~10-frame cyclic period.
- Actual frame rate ≈ **4 fps** (not the 20 fps implied by `frameCfg ... 50 ...`).
- Processing dB-span swings 40+ dB across same-scene frames (24 dB cfg `db_span` saturates).
- CFAR=0 in every frame; cannot be trusted as a clean negative (input non-stationary).
- Diagnostic diag_frame_stationarity.py: `static_dB span=11.38`, `slow_var_dB span=20.84`, `dc_frac≈1e-4` → **input-power rescaling signature**.

## Environment
- Win 10/11 + TI mmWave Studio 03.00.00.14 + CCS 20.5.0 + XDS110.
- Python 3.10+ (analysis 3.13), numpy/scipy/matplotlib.
- DCA1000: PC 192.168.33.30, DCA 192.168.33.180, UDP 4096/4098; UART COM20.
- DCA splits raw at 1024 MB → multiple `Raw_*.bin`.

## Pipeline (one line per stage)
- ADC → LVDS → DCA → UDP → `Raw_*.bin`
- `FileMonitor` tails raw, slices into `frame_NNNNNN.bin`
- `read_frame` → complex64 `[TX,loops,RX,N]`
- calib → range FFT → MTI (slow-time mean sub) → virt-array → Doppler FFT + ±2-bin DC notch → RD CFAR (OS, fa=3e-5, margin 10 dB, abs floor 12 dB) → AoA (FFT default) → RA CFAR → elevation FFT → arrDREA → xyz cloud → plots

## Hypotheses
| # | Hypothesis | Status |
|---|---|---|
| H1 | Cfg mismatch capture vs process | **Resolved** (both shortrange) |
| H2 | FPGA preamble shifts splits | **Rejected** (packets×1456 = bin size; clean) |
| H3 | Firmware warmup contaminates first N frames | **Partial** (`--warmup-frames 60` helps but doesn't fix cycle) |
| H4 | DCA repacks IQ ignoring SampleSwap | **Open** (hardcoded `i-first` override, untested) |
| H5 | Real fps ≠ cfg periodicity | **Confirmed** (≈4 fps) |
| H6 | TDM Doppler-az coupling biases moving AoA | **Confirmed (code)** — no compensation |
| H7 | Range axis upper half is alias | **Confirmed** — N_r=256 vs Nyquist beat 8.44 m |
| H8 | Fallback paths fabricate structure | **Confirmed (code)** — 3 unguarded branches |
| H9 | `compressionCfg` reaches LVDS → amplitude rescaling | **Leading; cfg edit applied, awaiting re-capture** |
| H10 | Firmware inter-frame TX/phase calibration cycle | **Open** (active if H9 fails) |
| H11 | Intra-frame AGC drift | **Open** |
| H12 | FileMonitor mishandles Raw_0→Raw_1 rotation | **Confirmed latent** (>340 frames; deferred) |
| H13 | Hardcoded TX/RX virt-array positions vs actual cfg | **Open** |
| H14 | Dev0/Dev1 LO incoherence | **Open** (needs corner reflector) |

## Confirmed findings
- Byte transport clean: 0 out-of-seq; pkt count × 1456 B = bin size exactly.
- Frame splitting byte-correct ≤ ~340 frames.
- `static_dB` & `slow_var_dB` co-vary proportionally → input rescaling, not scene dynamics.
- `dc_frac≈1e-4` → IQ DC offset is **not** the artifact.
- Three explicit fallback paths in code: `_ra_focus_mask_from_rd` (top-K Doppler peaks when CFAR empty), `_fallback_from_ra_power` (top-K RA percentile cloud), `plot_pc3d` 99.5-pctl branch.
- Range axis 16.8 m configured vs 8.44 m physical Nyquist → bins 96–255 alias.
- No input-power normalization anywhere → CFAR abs floor 12 dB is gain-sensitive.
- Cfg `gtrack`/`ransac`/`appGatingParams` lines are **ignored** by codebase.
- Virt-array hardcoded: `_TX_AZ=[0,4,7,11,15,2]`, `_RX_AZ=[0,1,2,3,19,20,21,22]`, never validated vs cfg.

## Key insights
- Every layer has graceful-degradation that hides upstream failure → "works without being correct."
- Amplitude cycle ~2.5 s @ 4 fps → matches a firmware periodic re-cal pattern.
- Co-variation of static and slow-var in dB-space at slope ratio ~2 in dB ↔ linear in power = amplitude rescaling, distinguishable from real scene change.

## Known unknowns
- Will `compressionCfg=0` stabilize amplitude?
- Does DCA1000 firmware silently repack IQ?
- Is cascade firmware doing inter-frame phase-shifter calibration?
- Are Dev0/Dev1 LO-coherent under current firmware?
- Range bins > 96 ever contain real signal vs aliased duplicates?
- Internal AWR2243 AGC settings (not exposed in cfg).

## Files modified in this investigation
| File | Change |
|---|---|
| dca.py | `_frame_stat_str`; `FileMonitor` + `run_capture` get `warmup_frames`, `frame_stats` kwargs |
| test.py | `--warmup-frames N`, `--frame-stats` CLI flags |
| cascade_shortrange.cfg | `compressionCfg -1 1 ...` → `... -1 0 ...` |
| diag_frame_stationarity.py | **NEW**. numpy-only diagnostic, `static_dB`/`slow_var_dB`/`dc_frac` + verdict. Bypasses __init__.py via importlib (matplotlib-free). |

## Next steps (prioritized)
1. **Re-capture with compression off + run diag** (cfg already edited; needs Windows host):
   ```
   python capture\test.py --uart COM20 --frames 30 --warmup-frames 60 --frame-stats --sync-wait 90
   python processing\diag_frame_stationarity.py --folder capture\frames --cfg config\build_shortrange_inf\cascade_shortrange.cfg
   ```
   Decision: both spans <2 dB → H9 confirmed; >5 dB → H10, escalate to firmware.
2. Corner reflector @ 3 m / 0° / 0° → only positive falsifier. Expect RD peak bin ≈45, RA peak az=0°, ≥20 dB above median, `src=cfar-mask`.
3. Gate fallbacks behind `--show-noise-fallback`; in `_ra_focus_mask_from_rd` leave RA at floor when `rd_det[:, ri].sum()==0`.
4. Clamp `n_range = floor(N_fft/2)`; assert `range_axis[-1] ≤ nyquist_beat`.
5. Add TDM-Doppler phase comp: per Doppler bin k and TX t, multiply by `exp(-j 2π k τ_t / T_loop)`.
6. Write `frames/_capture_meta.json` with cfg SHA-256; processing refuses on mismatch.
7. Fix `FileMonitor.find_latest_bin` to drain prior file before switching to Raw_1.
8. One-time IQ-order verification with known reflector.
9. If H10 confirmed: identify cal-cycle period via `mean|x|` autocorr, discard those frames.

## Verdict (unchanged)
**❌ Pipeline can plausibly generate false detections.** Gated on P1+P2 + P3 implementation.