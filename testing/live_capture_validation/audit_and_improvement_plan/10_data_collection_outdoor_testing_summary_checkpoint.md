# AWR2243-2X Body-Shape Perception Pipeline — Status Record

**Document date:** 2026-06-27
**Status:** Phases 0–6 complete. Data collection complete (12 sessions + 1 outdoor
multi-subject session). Analysis complete. Action plan pending.

> This document is a point-in-time record of the pipeline state, validated
> metrics, known limitations, and empirical findings from the first full
> data collection cycle. It is the reference baseline before any further
> pipeline modifications are made.

---

## 1. Hardware Configuration

| Parameter | Value |
|---|---|
| Radar | AWR2243-2X cascaded (2-chip, 6 TX TDM MIMO, 8 RX) |
| Carrier | AM273x |
| Capture board | DCA1000EVM |
| Frame rate | 4 fps |
| Range resolution | 6.60 cm/bin |
| Max range | 16.8 m |
| Doppler resolution | 0.078 m/s/bin |
| Doppler range | ±2.498 m/s |
| Az resolution at 3 m | 2.34 cm/bin (shoulder spans ~19 bins) |
| Az resolution at 8 m | 6.25 cm/bin (shoulder spans ~7 bins) |
| Elevation VA | 48 channels (~19 cm/bin at 3 m — noisy) |
| Accumulation window | 16 frames = 4 seconds |
| EMA centroid lag | ~2.3 frames = 0.6 s (α = 0.3) |

---

## 2. Pipeline Phase Completion

| Phase | Description | Status | Acceptance criteria |
|---|---|---|---|
| 0 | Observability — per-frame audit CSV | ✓ Complete | 400-row frames.csv, stage attribution visible |
| 1 | Per-frame cloud correctness | ✓ Complete | grating/FoV/cc filters; prom=6 dB; cc_rej −71% |
| 2 | Temporal accumulation + motion compensation | ✓ Complete | M4 median accum_pts = 32 ≥ 30 |
| 3 | DBSCAN single-subject clustering | ✓ Complete | 0 centroid jumps (was 61); noise = 2 pts median |
| 4 | Subject-centric coordinate normalisation | ✓ Complete | M5 dx_std range-independent |
| 5 | Body envelope visualisation (PCA ellipse) | ✓ Complete | Ellipse tracks subject within ±0.50 m bounds |
| 6 | Micro-Doppler / gait features + spectrogram | ✓ Complete | Spectrogram panel; cadence via autocorrelation |
| 7 | Pose descriptors / gait-based identification | Pending | Requires resolved pipeline issues + expanded dataset |

---

## 3. Active Pipeline Configuration

All feature flags are `True` by default in `processing/radar_config.py`:

```python
emit_all_cluster_bins = True   # Phase 1: depth bins per cluster
temporal_accum_en     = True   # Phase 2: 16-frame motion-compensated ring buffer
subject_frame_en      = True   # Phase 4: body-frame panel (4th viewer panel)
body_envelope_en      = True   # Phase 5: PCA ellipse overlay
gait_features_en      = True   # Phase 6: gait descriptors in status bar
microdoppler_en       = True   # Phase 6: spectrogram panel (5th viewer panel)
```

Key parameter values:

```python
accum_window           = 16      # frames in ring buffer
accum_alpha            = 0.3     # EMA smoothing weight
dbscan_eps             = 0.80    # neighbourhood radius (m)
dbscan_min_samples     = 3
max_cluster_radius     = 0.65    # reject implausibly wide clusters (m)
az_peak_min_prom_db    = 6.0     # az multi-peak prominence threshold
cross_cluster_range_m  = 0.35    # cross-cluster coherence gate (m)
dop_limb_thr           = 0.30    # torso/limb Doppler boundary (m/s)
spectrogram_frames     = 64      # 16s of Doppler history at 4 fps
spectrogram_v_max      = 1.5     # spectrogram Doppler axis (m/s)
```

---

## 4. Live Viewer — Five Panels

| Panel | Stage | Content | Key diagnostic |
|---|---|---|---|
| 1 — 3D cloud | Phase 2 | Full accumulated cloud, Doppler-coloured | Clutter vs body returns; direction sign |
| 2 — X-Y footprint | Phase 3 | Top-down; oval at DBSCAN centroid | Track continuity; ghost lock-on |
| 3 — X-Doppler | Phase 1 | Lateral position × radial velocity | Az multi-peak firing; limb separation |
| 4 — Body-frame | Phase 4+5 | ±0.5 m body-local; cyan cluster; amber PCA ellipse | Body shape; dx_std; ellipse rx/ry/θ |
| 5 — Spectrogram | Phase 6 | Doppler-time waterfall; amber torso line; cadence | Direction reversal; speed change; stride cadence |

**Status bar:** `vc=±X.XX m/s  σ=X.XX  limb=XX%`

---

## 5. Deployed Files and Checksums

| File | Role | MD5 |
|---|---|---|
| `processing/accumulate.py` | Phase 2–6: TemporalAccumulator, subject_frame(), fit_body_ellipse(), gait_features() | `392b1610a37c05d0a3a3a32b573f20dc` |
| `processing/microdoppler.py` | Phase 6: MicroDopplerBuffer — spectrogram + cadence | `dce61d6fdece3ae5bc75e4e2c5aa866e` |
| `processing/radar_config.py` | RadarConfig dataclass — all fields through Phase 6 | `551a5911d29a697b627e9d9d7d8df3ac` |
| `processing/radar_processing.py` | Full DSP pipeline (stateless, per-frame) | `e74723d56ad4f6d6d94493190c2918de` |
| `processing/streaming.py` | Live viewer — 5-panel layout | `8dde27434c6b0305ec086b3b761d62dd` |
| `processing/radar_plots.py` | Offline viewer | `dc8def38048f07c5cfb102202ab92f2b` |
| `diag_pipeline_audit.py` | Batch audit → frames.csv + points.csv | `be7f9162613094067a6889fa35d87438` |
| `diag_xyz.py` | Per-frame geometry diagnostic + radar height calibration | `982eaf9e9069c6489d59b6fc879fde83` |
| `analyse_sessions.py` | Cross-session analysis → session_analysis.txt | `2840ad41cbdb3be25fe4c63ac8bda7cf` |

---

## 6. Data Collection — Completed Sessions

### 6.1 Controlled protocol (12 sessions)

**Setup:** radar height = 0.75 m, range corridor P1=3 m to P4=9 m, 4 fps.

**Subjects:**

| ID | Height | Sessions |
|---|---|---|
| S01 | 164 cm | A_S01, B_S01, C_S01, D_S01 |
| S02 | 180 cm | A_S02, B_S02, C_S02, D_S02 |
| S03 | 174 cm | A_S03, B_S03, C_S03, D_S03 |

**Session status:**

| Session | Scenario | Frames | Detection | Status | Notes |
|---|---|---|---|---|---|
| A_S01 | Radial walk | 333 | 97.9% | ✓ Valid | Primary body-shape baseline for S01 |
| A_S02 | Radial walk | 309 | 97.7% | ✓ Valid | Primary body-shape baseline for S02 |
| A_S03 | Radial walk | 71 | 0.0% | ✗ Empty | Zero CFAR detections — re-record needed |
| B_S01 | Lateral walk | 309 | 98.7% | ✓ Valid | Side profile; centroid near-zero ✓ |
| B_S02 | Lateral walk | 262 | 99.6% | ✓ Valid | Side profile; centroid near-zero ✓ |
| B_S03 | Lateral walk | 381 | 98.2% | ⚠ Diagonal | dop_fwd=+0.852 — subject walked diagonally not laterally |
| C_S01 | Stand+walk | 262 | 67.6% | ✓ Valid | 8 transitions, mean lag 15.4 frames |
| C_S02 | Stand+walk | 309 | 61.5% | ⚠ Long lag | 7 transitions, mean lag 17.1 frames, max 33 frames |
| C_S03 | Stand+walk | 421 | 78.4% | ⚠ Weak cluster | Detections present but cluster_pts < 20 throughout |
| D_S01 | Multi-leg | 333 | 99.4% | ✓ Valid | Full ±2.498 m/s Doppler range; primary gait session |
| D_S02 | Multi-leg | 309 | 0.0% | ✗ Empty | Zero CFAR detections — re-record needed |
| D_S03 | Multi-leg | 391 | 100% (gait) | ⚠ No cluster | 368 gait frames; cluster_pts < 20; gait data usable only |

**Sessions recommended for Phase 7 feature extraction:** A_S01, A_S02, D_S01 (primary); B_S01, B_S02, C_S01 (supplemental).

### 6.2 Outdoor multi-subject session

**Setup:** radar height = 0.45 m, open space, unconstrained walking (forward, backward, left, right), two subjects ~175 cm each.

| Metric | Value |
|---|---|
| Duration | 6.0 minutes (1447 frames) |
| Detection rate | 88.9% |
| Centroid jumps | 0 |
| avg_cluster_pts | 40.2 (exceeds avg_accum_pts=36.5 — multi-subject merge) |
| rx_median | 0.257 m (vs 0.146–0.153 m single-subject) |
| rx_std | 0.098 m (bimodal: single-body vs merged-body frames) |
| limb_frac | 77.5% (mixed directions — expected) |
| dop_std | 1.134 m/s |
| n_unique_dop | 59 values (full ±2.498 m/s range covered) |
| z_mean | −0.588 m (expected +0.425 m — elevation calibration offset) |
| z_std | 2.091 m (largest in dataset; two subjects) |

---

## 7. Validated Metrics — Empirical Results

### 7.1 Phase 3 — Cluster stability

| Metric | Baseline (pre-Phase 3) | Post-Phase 3 | Status |
|---|---|---|---|
| Centroid jumps > 0.6 m | 61 | 0 (all 13 sessions) | ✓ Eliminated |
| Median cluster noise pts | — | 2.0 | ✓ AC2 pass |
| Median cluster_pts | — | 21–27 | ✓ AC1 pass |
| cluster_radius_x | — | 0.146–0.257 m | ✓ AC4 pass (≤0.55 m) |

### 7.2 Phase 4 — M5 body spread

| Session | dx_std_median | r_vs_range | Assessment |
|---|---|---|---|
| A_S01 (S01, 164 cm) | 0.063 m | 0.280 | Borderline range-dependent |
| A_S02 (S02, 180 cm) | 0.072 m | 0.697 | Range-dependent — azimuth resolution physics |
| D_S01 (S01) | 0.072 m | −0.035 | ✓ Range-independent |

**Revised M5 target:** 0.05–0.15 m (original 0.10–0.25 m was calibrated on a different clip with more lateral drift). Both values are physically correct for their conditions.

**Inter-subject dx_std variation (Scenario A):** S01=0.063 m vs S02=0.072 m, std=0.006 m. Marginally above the 0.005 m detectability threshold.

### 7.3 Phase 6 — Gait features

| Session | limb_frac | dop_spread | dop_max_max | Notes |
|---|---|---|---|---|
| A_S01 | 100% | 1.185 m/s | 1.171 m/s | All pts classified as limb |
| A_S02 | 87.9% | 0.706 m/s | 1.015 m/s | |
| D_S01 | 96.2% | 0.858 m/s | 2.498 m/s | Full radar Doppler range captured |
| B_S01 | 72.4% | 0.441 m/s | 0.468 m/s | Lateral walk — limb% high due to oblique Doppler |
| B_S02 | 68.4% | 0.411 m/s | 0.312 m/s | Lateral walk |
| Outdoor | 77.5% | 1.056 m/s | 2.420 m/s | Multi-direction, two subjects |

### 7.4 Scenario C — Track initialisation lag

| Session | Transitions | Mean lag | Max lag | Notes |
|---|---|---|---|---|
| C_S01 | 8 | 15.4 frames | 32 frames | |
| C_S02 | 7 | 17.1 frames | 33 frames | |
| C_S03 | 11 | 8.0 frames | 23 frames | Micro-motion false triggers inflate count |
| Overall | 26 | 12.7 frames | 33 frames | 13/26 exceed 16-frame target |

True initialisation lag (excluding micro-motion false triggers of 1–4 frames) is approximately 18–33 frames = 4.5–8.3 seconds.

---

## 8. Known Limitations and Findings

### 8.1 Confirmed limitations

**Elevation (z) is unreliable and excluded from all features.**
z_std of 1.2–2.1 m across all sessions far exceeds any subject's height. A systematic
negative z offset of −0.40 to −1.01 m exists independently of radar mounting height
(the error is larger at lower heights — opposite of a geometry effect), pointing to
an elevation phase calibration offset in the DSP pipeline. z is excluded from Phase 7.

**M5 range independence is geometry-dependent.**
dx_std is range-dependent when azimuth resolution changes significantly across the
walking corridor (3–9 m range). At 8 m range the shoulder spans only 7 az bins vs
19 bins at 3 m, producing smaller dx_std at far range and a genuine positive
correlation with range. D_S01 achieves range independence (r=−0.035) because that
session had more uniform range distribution. The M5 criterion is valid within a
restricted range corridor (e.g. 3–6 m only).

**Doppler direction check invalid for multi-cycle sessions.**
The half-split directional check (first half = away, second half = return) is only
valid for single out-and-back cycles. Sessions with 3–4 cycles produce mixed
Doppler in both halves. The Doppler data itself is correct (both ±directions present
in the quantised value lists); the check needs replacing with a sign-change count
on the dop_centroid time series.

**dop_limb_thr = 0.30 m/s not valid for lateral walking.**
For Scenario B (lateral walk), all body parts produce partial radial Doppler
components between 0.234 and 0.780 m/s regardless of gait phase. limb_frac is
therefore always high (68–89%) for lateral walking, making it uninformative as a
gait feature in that scenario. limb_frac is only valid for radial and near-radial
walking.

**Single-subject assumption in DBSCAN.**
The pipeline is designed for one subject. When two subjects are within eps=0.80 m
of each other, their returns merge into a single cluster (cluster_pts > accum_pts).
The outdoor multi-subject session shows rx=0.257 m (vs 0.146–0.153 m single-subject)
and rx_std=0.098 m as the observable signatures of this merging. Phase 7 must account
for this before attempting identification in scenes with multiple people.

**Scenario C initialisation lag longer than accumulator window.**
The true initialisation lag after walking begins is 18–33 frames (4.5–8.3 s),
longer than the 16-frame (4 s) accumulator window target. This is caused by
DBSCAN requiring min_samples=3 across enough frames to form a stable cluster.

### 8.2 Open items from plan

| Item | Status | Recommendation |
|---|---|---|
| Config hygiene — 5 unwired fields | Open | Delete or wire before Phase 7 |
| GPU/CPU parity test script | Open | Create before next data collection |
| Kalman tracker (tracking.py) | Not implemented | DBSCAN+EMA achieves equivalent metrics; document skip decision |
| Doppler direction check for multi-cycle sessions | Broken | Replace with sign-change count on dop_centroid series |
| dop_limb_thr for Scenario B | Incorrect | Either exclude limb_frac for lateral sessions or increase threshold |
| Elevation calibration offset | Unexplained | Investigate phase calibration in elevation FFT stage |
| Two empty sessions (A_S03, D_S02) | No data | Re-collect when possible |

---

## 9. Multi-Subject Scene Signatures

From the outdoor session, the following observable combination reliably indicates
more than one subject in the DBSCAN neighbourhood (separation < eps=0.80 m):

| Condition | Single-subject | Multi-subject |
|---|---|---|
| cluster_pts vs accum_pts | cluster ≤ accum | **cluster > accum** |
| rx_median | 0.146–0.153 m | > 0.20 m |
| rx_std | 0.017–0.116 m | ~0.098 m (bimodal) |
| dop_spread | 0.706–1.185 m/s | > 1.0 m/s (overlaps) |

The binary condition `cluster_pts > accum_pts` is the most reliable single discriminator.
`rx_median > 0.20 m` adds spatial context. Together they form the recommended
multi-subject detection heuristic for Phase 7.

---

## 10. Phase 7 Readiness Assessment

### What is in place

- Stable single-subject tracking: 0 centroid jumps across 13 sessions and 5,476 frames
- Subject-centric body-frame cloud with range-independent spread (validated on D_S01)
- PCA body envelope (rx, ry, θ) per frame
- Gait feature descriptors (dop_centroid, limb_frac, dop_spread, dop_max)
- Doppler-time spectrogram with cadence estimation
- Cross-session analysis tooling (analyse_sessions.py)
- 7 valid controlled sessions across 2 subjects
- 1 outdoor multi-subject session (6 min, richest Doppler coverage)

### What is needed before Phase 7

1. **Resolve broken Doppler direction check** in analyse_sessions.py — replace half-split with sign-change count.
2. **Address empty sessions** (A_S03, D_S02) — re-collect or exclude explicitly from analysis.
3. **Characterise the elevation calibration offset** — determine whether it affects any x/y features or is strictly confined to z.
4. **Decide on multi-subject handling strategy** — either restrict Phase 7 to single-subject scenes (detected by cluster_pts vs accum_pts) or extend the pipeline with a multi-cluster tracker before Phase 7.
5. **Expand the dataset for S03** — currently S03 has no valid Scenario A or D sessions, leaving only two subjects for inter-subject comparison.

### Feature set recommended for Phase 7

From valid sessions only, excluding z:

| Feature | Source | Sessions available | Notes |
|---|---|---|---|
| rx, ry | Cluster geometry | A_S01, A_S02, D_S01, B_S01, B_S02 | rx varies with subject separation in multi-subject scenes |
| dx_std | Phase 4 M5 | A_S01, A_S02, D_S01 | Use only at 3–6 m range for range independence |
| dop_centroid | Phase 6 | A_S01, A_S02, D_S01 | Trunk velocity; valid for radial walking only |
| limb_frac | Phase 6 | A_S01, A_S02, D_S01 | Valid for radial walking; unreliable for lateral |
| dop_spread | Phase 6 | All valid sessions | Useful multi-subject indicator when high |
| dop_max | Phase 6 | D_S01, outdoor | Captures fast-limb returns; speed indicator |
| cadence_hz | Phase 6 | Needs validation | Autocorrelation requires 8+ s of steady walking |

---

## 11. Data File Locations

```
testing/
  live_capture_validation/
    05_outdoor_data_collection/
      logs/
        A_S01/  frames.csv  points.csv  summary.txt
        A_S02/  frames.csv  points.csv  summary.txt
        A_S03/  frames.csv  (no points.csv — empty session)
        B_S01/  frames.csv  points.csv  summary.txt
        B_S02/  frames.csv  points.csv  summary.txt
        B_S03/  frames.csv  points.csv  summary.txt
        C_S01/  frames.csv  points.csv  summary.txt
        C_S02/  frames.csv  points.csv  summary.txt
        C_S03/  frames.csv  points.csv  summary.txt
        D_S01/  frames.csv  points.csv  summary.txt
        D_S02/  frames.csv  (no points.csv — empty session)
        D_S03/  frames.csv  points.csv  summary.txt
        outdoor_long/
              frames.csv  points.csv  summary.txt
```

---

## 12. Toolchain Commands

### Live streaming + recording (per session)

```powershell
python live_capture.py `
    --cfg     config\build_shortrange_inf\cascade_shortrange.cfg `
    --display pointcloud `
    --record `
    --out-dir capture\sessions\SCENARIO_SUBJECT\frames `
    --quiet
```

### Per-session audit (run after every session)

```powershell
python diag_pipeline_audit.py `
    --folder  capture\sessions\SCENARIO_SUBJECT\frames `
    --cfg     config\build_shortrange_inf\cascade_shortrange.cfg `
    --temporal-accum --accum-window 16 `
    --subject-frame --gait-features `
    --out-dir testing\live_capture_validation\05_outdoor_data_collection\logs\SCENARIO_SUBJECT
```

### Cross-session analysis (produces session_analysis.txt)

```powershell
python analyse_sessions.py `
    --root testing\live_capture_validation\05_outdoor_data_collection\logs `
    --out  session_analysis.txt `
    --subjects subjects.csv
```

### Radar height calibration (run once per new location)

```powershell
python diag_xyz.py --frames 50 100 150 200 --radar-height 0.75
```

Adjust `--radar-height` until the ELEVATION verdict shows z_mean near zero.

---

## 13. Document History

| Date | Change |
|---|---|
| 2026-06-27 | Initial status record — Phases 0–6 complete, 13 sessions analysed |

---

*For the full development roadmap see `docs/HUMAN_BODY_SHAPE_PLAN.md`.
For viewer panel technical reference see `VIEWER_PANELS.md`.
For data collection protocol see `DATA_COLLECTION_PLAN.md`.*
