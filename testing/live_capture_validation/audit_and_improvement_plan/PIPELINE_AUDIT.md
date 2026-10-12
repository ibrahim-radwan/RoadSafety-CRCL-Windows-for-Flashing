# AWR2243-2X Pipeline — Comprehensive Technical Audit

**Date:** 2026-07-27
**Scope:** ~7,000 lines of active pipeline code + 13 recorded sessions + measured latency benchmark
**Method:** static analysis, code path tracing, numerical verification against recorded data

---

## 0. Scope and Method

**Audited (read directly, not from summary):**

| File | Lines | Role |
|---|---|---|
| `streaming.py` | 1,949 | Live viewer, 5 panels |
| `radar_processing.py` | 1,448 | Stateless per-frame DSP |
| `gpu_accel.py` | 1,224 | CuPy GPU stages |
| `radar_plots.py` | 1,286 | Offline viewer |
| `analyse_sessions.py` | 891 | Cross-session analysis |
| `radar_config.py` | 826 | Config dataclass |
| `processing/accumulate.py` | 573 | Phases 2–6 temporal layer |
| `diag_pipeline_audit.py` | 438 | Batch audit |
| `processing/microdoppler.py` | 234 | Spectrogram + cadence |

**Evidence base:** `benchmark_summary.txt` (58-frame staged latency), `session_analysis.txt`
(13 sessions), `frames.csv` / `points.csv`.

**Headline result:** the pipeline is structurally sound and Phase 3 tracking is genuinely
stable (0 centroid jumps across 5,476 frames). However this audit found **four defects that
invalidate shipped conclusions or ship dead features**, **two latency defects worth ~60% of
frame time**, and **one architectural gap that fully explains the stakeholder feedback**.

Two of the P0 defects were introduced during this project's own analysis and are corrected here.

---

## 1. P0 — Critical Defects

### P0-1 · The multi-subject discriminator is mathematically impossible — dead code shipped

**Where:** `streaming.py` `_update_pointcloud`, and `PIPELINE_STATUS.md` §9

```python
_multi_subj = (_cluster_pts_count > _accum_pts_count) and _cluster_pts_count > 0
```

**Why it can never be true** — `processing/accumulate.py::_cluster()`:

```python
labels   = DBSCAN(...).fit_predict(xy)   # xy derived from pts
mask     = labels == best_label
n_pts    = int(mask.sum())               # subset count of pts
```

`n_pts` counts a **subset** of the input cloud. Therefore `cluster_pts ≤ accum_pts` holds on
every frame without exception. The red oval and the `⚠ MULTI-SUBJECT` banner **can never render**.

**Where the false signal came from** — `diag_pipeline_audit.py` summary block uses two
different denominators:

```python
avg accum_pts/frame = total_accum_pts / len(frame_rows)        # ALL frames, incl. zero-detection
avg cluster_pts     = cluster_pts[cluster_pts > 0].mean()      # ONLY frames with a cluster
```

**Numerical proof (outdoor session):**

| Quantity | Value |
|---|---|
| frames total | 1,447 |
| frames detected (88.9%) | 1,286 |
| reported avg accum (÷ all frames) | 36.5 |
| total accum pts | 52,816 |
| **avg accum on detected frames** | **41.1** ← correct comparator |
| reported avg cluster (÷ detected) | 40.2 |

41.1 ≥ 40.2 — fully consistent with cluster ⊆ accum. The "cluster > accum" observation was a
**denominator artifact**, not physics.

**Impact:** `PIPELINE_STATUS.md` §9 must be retracted. The viewer feature must be reimplemented
on a real signal (see P0-2 and §4).

---

### P0-2 · Multi-subject data is discarded inside the clustering function

**Where:** `processing/accumulate.py::_cluster()`

```python
unique     = [l for l in np.unique(labels) if l >= 0]      # ALL clusters DBSCAN found
best_label = max(unique, key=lambda l: (labels == l).sum())# keep only the largest
body_pts   = pts[labels == best_label]                     # every other cluster dropped
```

DBSCAN **already separates people correctly**. The label array contains the full segmentation.
The code then discards every cluster except the largest, and `ClusterResult` has no field to
carry the others. Person B is destroyed one function call before the display layer.

**This is the root cause of the stakeholder feedback.** The viewer cannot show "person A vs
person B" because the data structure deletes person B upstream. Panel 2 draws one oval; Panel 4
colours cyan/grey by distance to that one centroid; nothing anywhere encodes cluster identity.

It also explains the *oval snapping*: when two people separate beyond `eps`, DBSCAN splits them,
the code keeps whichever has more points, and the oval jumps to the other person with no visual
indication that the tracked target changed.

**Confirmed corroborating evidence** (these metrics are per-frame with consistent denominators,
so they remain valid):

| Metric | Single-subject | Outdoor 2-subject |
|---|---|---|
| `rx_median` | 0.146–0.153 m | **0.257 m** |
| `rx_std` | 0.017 m (A_S02) | **0.098 m** |

`rx_std = 0.098 m` is the fingerprint of the merge/split cycle.

---

### P0-3 · Cadence estimator fails on the strongest gait signals (saturation)

**Where:** `processing/microdoppler.py::_estimate_cadence()`

```python
lf_zm = lf_clean - lf_clean.mean()
if lf_zm.std() < 1e-4:
    return float('nan')
```

`limb_frac` is the fraction of cluster points with `|dop| ≥ dop_limb_thr` where
`dop_limb_thr = 0.30 m/s`. But:

- minimum non-zero Doppler the MTI gate passes = **0.234 m/s**
- normal walking radial Doppler = **0.4–0.8 m/s**

So nearly every point exceeds 0.30 m/s during radial walking → `limb_frac` saturates at 1.0 →
variance collapses → NaN.

**Executed test against real distributions:**

| limb_frac distribution | Session | Cadence result |
|---|---|---|
| pinned at 1.00 | A_S01 (100%) | **FAIL — NaN** |
| 0.96–1.00 | D_S01 (96.2%) | **FAIL — NaN** |
| 0.85–0.92 | A_S02 (87.9%) | 0.44 Hz (implausible; true ≈0.9–1.1 Hz) |
| ideal 1 Hz square wave | design assumption | 1.0 Hz ✓ |

The estimator fails **precisely on the cleanest sessions**, and where it does return a number
the value is not gait — it is noise. This is why Panel 5 showed "no clear peak" during good
walking. **Every cadence figure produced so far should be treated as unvalidated.**

---

### P0-4 · Two runtime defects in the visualization code added last session

Both are in `streaming.py` and have never been executed.

**(a) Qt font construction will raise on Qt6 — crashes viewer at startup**

```python
multi_subj_text.setFont(
    __import__('pyqtgraph', fromlist=['Qt']).Qt.QtGui.QFont('Monospace', 10, 75))
```

`QFont(family, pointSize, weight)` with `weight` as `int` is Qt5 API. On PyQt6/PySide6 the
weight parameter is `QFont.Weight` enum and an int raises `TypeError`. This sits in
`_build_pointcloud_window()` **outside any try/except**, so it aborts window construction.

**(b) Centroid trail fade is scrambled after 24 frames**

```python
valid  = ~(np.isnan(self._trail_x) | np.isnan(self._trail_y))
tx     = self._trail_x[valid]                    # ARRAY order, not TIME order
alphas = np.linspace(30, 200, n_valid)           # assumes oldest→newest
```

The trail is a ring buffer. Once it wraps, array index 0 holds the **newest** sample. The alpha
ramp is applied in array order, so the fade is randomised — the trail reads as scattered
bright/dim dots rather than a direction-revealing gradient. `MicroDopplerBuffer` solves the same
problem correctly with `np.roll`; this code does not.

**(c) Related:** trail state (`self._trail_x/_y/_ptr`) is initialised inside
`_build_pointcloud_window()` rather than `__init__`, so it does not exist in heatmap mode.

---

## 2. P1 — Latency

Measured baseline (`benchmark_summary.txt`, 58 frames, GPU, cfar_margin=5.0):
**mean 68.4 ms · median 59.4 ms · p90 87.8 ms · p99 148.2 ms**

| Stage | mean ms | % total |
|---|---|---|
| **S7 Az FFT full-cube** | **26.13** | **38.2%** |
| **S4 Doppler FFT + MTI** | **13.22** | **19.3%** |
| S2 Range FFT | 4.57 | 6.7% |
| S9 Elevation FFT | 4.09 | 6.0% |
| S3 Virtual array | 3.09 | 4.5% |
| S1 Calibration | 2.31 | 3.4% |
| S5 RD power | 2.00 | 2.9% |
| S6 RD CFAR | 1.62 | 2.4% |
| S8 Per-target az FFT | 0.19 | 0.3% |
| S10 Extract xyz | 0.20 | 0.3% |

### L-1 · The 38% bottleneck computes 98% wasted work in pointcloud mode

**Where:** `radar_processing.py` ~line 1072

```python
ra_focus_mask = _focus_mask_fn(RD_mti, rd_det, cfg)          # computed...
if   cfg.aoa_method == "capon":    RA = _az_capon(...,  ra_focus_mask)   # uses it
elif cfg.aoa_method == "music":    RA = _az_music(...,  ra_focus_mask)   # uses it
elif cfg.aoa_method == "bartlett": RA = _az_bartlett(..., ra_focus_mask) # uses it
else:                                                        # DEFAULT FFT PATH
    az_cube = _az_fft_fn(virt_pos, cfg)                      # IGNORES the mask
    RA = _collapse_ra_fn(az_cube, RD_mti, rd_det, cfg)[:N_r, :]
```

The **default** AoA path is the only one that ignores the focus mask. It computes the full
`[64 dop × 256 range × 256 az]` cube — **4.19 M complex64 = 33.6 MB per frame, 134 MB/s at 4 fps**.

Downstream, `RA` is consumed only at detected coordinates:
- `extract_xyz` reads `RA[ri, ai]` at detections
- `_prune_ra_sidelobes` needs `max(RA, axis=1)` per detected row
- `_restrict_ra_candidates` reads `RA[ri]` per detected row

With **2.2 detections/frame** across ~256 range bins, **≈2% of the computed cube is used.**

Verified: `_update_pointcloud` reads only `result.xyz_cloud` and the accumulator result.
`result.RA` / `result.RE` are referenced **only** in the heatmap update path (lines 959–971).
**All 13 data-collection sessions ran in `--display pointcloud` mode.**

**Fix:** apply the already-computed `ra_focus_mask` to the FFT path — restrict the azimuth FFT
to range rows carrying RD detections.
**Estimated saving: 26.1 ms → ~1–2 ms ⇒ ~24 ms/frame (35% of total).**
Secondary benefit: eliminates 33.6 MB/frame of GPU allocation, which is the most likely driver
of the p99 = 148 ms tail.

### L-2 · Eleven blocking GPU round-trips per frame

**Where:** `gpu_accel.py` — 11 occurrences of `cp.asnumpy(...)`

Each stage follows `cp.asarray(host) → kernel → cp.asnumpy(device)`. Every `asnumpy` is a
blocking device→host copy that forces a full sync. Data never stays resident on the GPU
across stages, so the pipeline pays PCIe latency plus a sync stall eleven times per frame.

On Windows this interacts badly with WDDM scheduling and is consistent with the documented
trimodal 185/280/380 ms behaviour and the p99 tail.

Additionally, **constant** window functions are re-uploaded every frame:

```python
win_g = cp.asarray(win,  dtype=cp.float32)   # same values every frame
w_g   = cp.asarray(w,    dtype=cp.float32)
```

**Fix (staged):**
1. Cache constant windows/steering matrices on device — trivial, low risk.
2. Keep `RD_mti` / `virt_pos` resident on GPU between S3→S7 — removes ~6 of 11 sync points.
**Estimated saving: 8–15 ms/frame, plus materially reduced p99 variance.**

### L-3 · Benchmark is not representative

`benchmark_summary.txt` reports `Avg confirmed range bins per frame : 0.0`. The benchmark ran
with **zero detections**, so S8 (per-target az FFT = 0.19 ms) is measured on an empty workload,
and it used `cfar_margin=5.0` while sessions used `10.0`. Real session `proc_ms` was
**84–202 ms**, well above the 68.4 ms benchmark mean.

**Action:** re-run the benchmark on a recorded session with real detections before and after
each optimisation, otherwise savings cannot be verified.

### Projected latency after L-1 + L-2

| | now | after L-1 | after L-1+L-2 |
|---|---|---|---|
| mean | 68.4 ms | ~44 ms | ~32 ms |
| p99 | 148.2 ms | ~90 ms | ~55 ms |
| headroom vs 256 ms frame period | 3.7× | 5.8× | 8× |

---

## 3. P2 — Algorithm and Parameter Defects

### A-1 · `dbscan_eps = 0.80 m` is over-sized, derived from a bad measurement

Measured single-subject medians across sessions: **rx = 0.146 m, ry = 0.259 m**
⇒ body footprint ≈ **0.29 m lateral × 0.52 m range**.

`eps = 0.80 m` is 1.5× the widest body dimension. **Any two people closer than 0.80 m merge
into one cluster.** Typical side-by-side walking separation is 0.6–1.2 m, so merging is
frequent — exactly what the outdoor session shows.

`eps` was originally sized to span a claimed `ry = 0.739 m` body depth. Measured `ry` for real
single subjects is **0.216–0.292 m**. The 0.739 m figure came from a degenerate/merged cluster,
so the parameter was tuned from a corrupted measurement.

**Recommendation:** `eps = 0.45–0.55 m` — still ≈0.9× single-body depth (safe against splitting
one body) while separating people beyond 0.55 m instead of 0.80 m. Must be re-validated against
A_S01/A_S02/D_S01 before adoption.

### A-2 · `max_cluster_radius = 0.65 m` silently drops informative frames

```python
if self._max_radius > 0 and rx > self._max_radius:
    return ClusterResult(n_pts=0, n_noise=len(pts), cluster_found=False)
```

The **entire frame** is dropped from Phases 3–6. In multi-subject scenes wide clusters are the
informative ones. There is **no counter** recording how often this fires, so the loss is
invisible in `frames.csv`. Add a `wide_cluster_rej` column before changing the threshold.

### A-3 · `dop_limb_thr = 0.30 m/s` is below the noise floor of the gate

Root cause of P0-3. The MTI gate's minimum passed Doppler is 0.234 m/s, so a 0.30 m/s threshold
sits inside the passband rather than between torso and limb returns.

**Recommendation:** make the threshold **adaptive per frame**, e.g.
`thr = |dop_centroid| + k·dop_spread`, so "limb" means *faster than this subject's own torso*
rather than a fixed absolute. This also fixes the Scenario B invalidity noted earlier
(lateral walking produced limb_frac 68–89% because all oblique components exceeded 0.30 m/s).

### A-4 · Doppler direction check is invalid for multi-cycle sessions

`analyse_sessions.py` splits frames at `fi_mid` and assumes first half = outbound. Sessions
contain 3–4 out-and-back cycles, so both halves hold mixed directions. Only 1 of 6 A/D sessions
"passed" despite the underlying Doppler data being correct (A_S01 spans −1.951…+1.717 m/s).

**Fix:** count zero-crossings of the `dop_centroid` time series; expect ≈ 2 × cycles.

### A-5 · Elevation offset is a real, unexplained calibration defect

| Radar height | Expected z_mean | Observed | Error |
|---|---|---|---|
| 0.75 m (S01, 164 cm) | +0.07 m | −0.334 m | −0.40 m |
| 0.75 m (S02, 180 cm) | +0.15 m | −0.498 m | −0.65 m |
| 0.45 m (outdoor, 175 cm) | +0.425 m | −0.588 m | **−1.01 m** |

The error **grows as the radar is lowered** — the opposite of a height-bookkeeping mistake.
Combined with `z_std = 1.2–2.1 m` (larger than any subject's height), this indicates an
elevation phase-calibration defect, not geometry.

Excluding z from features is the correct short-term call, but the **cause should be found**:
if the same calibration table feeds azimuth, x may carry a smaller undetected bias.

---

## 4. P3 — Visualization Architecture

The stakeholder feedback — *"cannot tell if points are one person or multiple; cannot tell if
the two people moved together or apart"* — is **not a rendering problem**. It is P0-2: the data
structure discards every cluster but one.

Point-level fixes (colours, sizes, banners) cannot solve it. The fix must start in
`accumulate.py`.

### Required change — carry all clusters through

```python
@dataclass
class SubjectCluster:
    cluster_id:  int          # stable ID from frame-to-frame association
    cloud:       np.ndarray
    centroid_x:  float
    centroid_y:  float
    radius_x:    float
    radius_y:    float
    n_pts:       int

@dataclass
class ClusterResult:
    subjects:    list[SubjectCluster]   # ALL clusters, not just the largest
    primary_idx: int                    # index of largest (back-compat)
    n_noise:     int
    cluster_found: bool
```

Identity is maintained by nearest-centroid association between consecutive frames with the
existing 0.6 m jump gate. This is a ~120-line change and it unlocks every downstream visual.

### Then — and only then — these become possible

| Feature | Panel | What the stakeholder sees |
|---|---|---|
| One coloured oval per subject | 2 | Two ovals = two people, unambiguously |
| Persistent colour per `cluster_id` | 1, 2, 4 | Person A always cyan, person B always magenta |
| Per-subject centroid trail | 2 | Two trails converging = together; diverging = apart |
| Live subject count | status bar | `SUBJECTS: 2` |
| Inter-subject separation readout | 2 | `separation: 1.4 m` with a connecting line |
| Merge state annotation | 2 | `MERGED (<0.55 m)` only when DBSCAN actually merges |

The "moving together vs apart" question is then answered directly by the **separation distance
time series** — a scalar the pipeline can already compute once clusters are retained.

### Elevation visualisation

Given A-5, z is not trustworthy enough for a dedicated view. The point-size-by-height encoding
added last session is reasonable **but should be labelled as indicative**, and should be driven
by a z value that has passed a validity gate (e.g. `|z − median(z)| < 2σ`), not raw z.

---

## 5. P4 — Code Quality and Maintainability

| Finding | Detail | Risk |
|---|---|---|
| 18 stale variant files | `radar_processing_mod1..5b.py`, `radar_config_mod*.py`, `gpu_accel_mod1.py`, `streaming_step1_xz.py` — ~14,000 lines of dead code alongside active files | Wrong file edited/deployed |
| 5 silent exception handlers | `streaming.py` 1218, 1761; `gpu_accel.py` 1208; `radar_plots.py` 554, 1248 — `except Exception: pass` | Failures invisible in field |
| 2 bare `except:` | `radar_processing.py` 595; `diag_pipeline_audit.py` 320 | Catches `KeyboardInterrupt` |
| 5 unwired config fields | `strict_object_filtering`, `require_rd_confirmation`, `ra_sidelobe_db`, `filter_high_moving`, `moving_objects_only` | Config implies behaviour that does not exist |
| No automated tests | All validation is manual replay | Regressions undetected |
| No GPU/CPU parity test | Plan requires it; never created | Silent GPU divergence |
| Kalman tracker absent | `tracking.py` never created | Documented as deliberate skip — acceptable, but P0-2 now needs the association logic anyway |

---

## 6. Sequenced Action Plan

Ordered so that each step de-risks the next. Effort assumes one engineer.

### Stage 1 — Stop the bleeding (½ day)

| # | Action | File | Effort |
|---|---|---|---|
| 1.1 | Remove the dead `_multi_subj` detector and its banner/red-oval | `streaming.py` | 20 min |
| 1.2 | Fix `QFont` construction (use `pg.QtGui.QFont`, Qt6-safe weight) | `streaming.py` | 15 min |
| 1.3 | Fix trail ring-buffer ordering with `np.roll`; move state to `__init__` | `streaming.py` | 30 min |
| 1.4 | Fix audit denominators — report both `/all` and `/detected` | `diag_pipeline_audit.py` | 30 min |
| 1.5 | Retract §9 of `PIPELINE_STATUS.md`; mark all cadence figures unvalidated | docs | 30 min |
| 1.6 | Add `wide_cluster_rej` counter column | `accumulate.py`, `diag_pipeline_audit.py` | 45 min |

**Exit criterion:** viewer launches cleanly; no feature claims a signal it cannot produce.

### Stage 2 — Latency (2 days)

| # | Action | Expected | Effort |
|---|---|---|---|
| 2.1 | Re-run benchmark on a real session (with detections) to set a true baseline | — | 2 h |
| 2.2 | Apply `ra_focus_mask` to the FFT AoA path | **−24 ms/frame** | 1 day |
| 2.3 | Cache constant windows/steering matrices on device | −2–3 ms | 2 h |
| 2.4 | Keep `RD_mti`/`virt_pos` GPU-resident S3→S7 | −6–12 ms, lower p99 | 1 day |
| 2.5 | Re-run benchmark; verify mean ≤ 35 ms, p99 ≤ 60 ms | — | 2 h |

**Guard:** after each change, replay A_S01 and D_S01 and confirm `frames.csv` is bit-comparable
on `cloud_pts`, `cluster_pts`, `dop_centroid`.

### Stage 3 — Multi-subject support (3 days) — unblocks the stakeholder request

| # | Action | File | Effort |
|---|---|---|---|
| 3.1 | Introduce `SubjectCluster`; retain all DBSCAN clusters | `accumulate.py` | 1 day |
| 3.2 | Frame-to-frame ID association (nearest centroid, 0.6 m gate, ≤3-frame coast) | `accumulate.py` | 1 day |
| 3.3 | Per-subject ovals, persistent colours, per-subject trails | `streaming.py` | ½ day |
| 3.4 | `SUBJECTS: n`, separation readout, connecting line, true merge annotation | `streaming.py` | ½ day |
| 3.5 | Add `n_subjects`, `separation_m` columns | `diag_pipeline_audit.py` | 2 h |

**Validation:** replay the outdoor session; confirm two ovals with stable IDs, and that
`separation_m` shows the together/apart pattern the operators observed.

### Stage 4 — Algorithm correctness (2 days)

| # | Action | Effort |
|---|---|---|
| 4.1 | Re-tune `dbscan_eps` 0.80 → 0.45–0.55; validate no body-splitting on A_S01/A_S02/D_S01 | ½ day |
| 4.2 | Adaptive `dop_limb_thr = f(dop_centroid, dop_spread)`; re-validate limb_frac is unsaturated | ½ day |
| 4.3 | Rebuild cadence on the de-saturated `limb_frac`; validate against stopwatch-timed speeds | ½ day |
| 4.4 | Replace Doppler direction check with zero-crossing count | 2 h |
| 4.5 | Investigate elevation phase-calibration offset; confirm azimuth is unaffected | ½ day |

**Note:** 4.3 cannot be validated without ground-truth walking speeds. If none were recorded,
one short session with stopwatch-timed 6 m segments is required.

### Stage 5 — Production hardening (2 days)

| # | Action | Effort |
|---|---|---|
| 5.1 | Move `*_mod*.py` variants to `archive/`; single source of truth | 2 h |
| 5.2 | Replace 5 silent handlers with logged warnings; fix 2 bare `except:` | 2 h |
| 5.3 | Delete or wire the 5 unwired config fields | 2 h |
| 5.4 | GPU/CPU parity test (assert xyz agreement within tolerance) | ½ day |
| 5.5 | Regression harness: replay 3 sessions, assert key `frames.csv` columns unchanged | ½ day |

### Stage 6 — Data gaps (schedule when feasible)

- Re-record **A_S03** and **D_S02** (zero detections; subject S03 currently has no valid
  Scenario A or D session, leaving only 2 subjects for inter-subject comparison).
- One session with **stopwatch ground-truth speeds** to validate cadence (blocks 4.3).
- Re-run the outdoor multi-subject session after Stage 3 to validate ID tracking with a known
  together/apart script.

---

## 7. Phase 7 Gate

Phase 7 (pose descriptors / gait identification) should **not** start until:

| Gate | Status |
|---|---|
| Cadence validated against ground truth | ✗ blocked by P0-3 + missing ground truth |
| Multi-subject scenes handled | ✗ blocked by P0-2 (Stage 3) |
| `dbscan_eps` validated on real body dimensions | ✗ blocked by A-1 (Stage 4.1) |
| ≥3 subjects with valid A + D sessions | ✗ S03 has none |
| Latency headroom for added feature extraction | ⚠ improves after Stage 2 |
| Stable tracking (0 centroid jumps) | ✓ confirmed, 5,476 frames |
| Range-independent body spread (M5) | ⚠ holds for D_S01 (r=−0.035); range-dependent elsewhere |

**Recommended feature set once gates clear:** `rx`, `ry`, `dx_std` (restricted to 3–6 m range),
`dop_centroid`, `dop_spread`, and re-validated `cadence_hz`. **Exclude z** pending A-5.

---

## 8. Summary

| Severity | Count | Headline |
|---|---|---|
| **P0 Critical** | 4 | Dead multi-subject detector; multi-subject data discarded in clustering; cadence fails on strongest signals; 2 unexecuted runtime bugs |
| **P1 Latency** | 3 | 38% of frame time is 98% wasted work; 11 blocking GPU syncs; benchmark unrepresentative |
| **P2 Algorithm** | 5 | eps over-sized from bad measurement; silent frame drops; limb threshold below noise floor; broken direction check; elevation calibration defect |
| **P3 Visualization** | 1 | Architectural — fixed only by P0-2 |
| **P4 Quality** | 7 | 14k lines dead code; silent handlers; no tests |

**What is genuinely solid:** Phase 3 tracking stability (0 jumps / 5,476 frames), detection rate
(97–99% where the radar was active), Doppler dynamic range (full ±2.498 m/s captured), and the
overall stateless-DSP / stateful-temporal architectural separation.

**Total estimated effort to production-ready:** ~10 engineering days across Stages 1–5, plus
data collection in Stage 6.

**Highest-value single change:** Stage 2.2 — applying the existing focus mask to the FFT AoA
path removes ~35% of frame latency for roughly one day of work.

**Highest-stakeholder-impact change:** Stage 3 — retaining all DBSCAN clusters directly answers
"how many people, and are they together?"

---

## Appendix A — Stage 1 Completion Log (2026-07-27)

### Delivered

| # | Item | Verification |
|---|---|---|
| 1.1 | Dead `_multi_subj` detector, red oval, banner, fake MERGING/MERGED labels removed | 0 residual references; 40-frame test → 0 violations of `cluster_pts ≤ accum_pts` |
| 1.2 | `QFont` crash removed with the widget | 0 `__import__` references remain |
| 1.3 | Trail ring buffer read time-ordered via `np.roll`; state moved to `__init__` | Unit test: old `[24,25,26,27]…[20,21,22,23]` (non-monotonic) → new `[16..39]` strictly increasing |
| 1.4 | Audit prints all four denominator combinations | Confirmed on A_S01 (see below) |
| 1.5 | `PIPELINE_STATUS.md` §9 retracted; cadence marked BLOCKED; Phase 6 → ⚠ Partial | Banner added, history updated, 0 stale claims |
| 1.6 | `wide_cluster_rej` counter added end-to-end | T2 fires on wide cluster, T3 stays clear on genuine no-cluster, T4 back-compat default `False` |

### P0-1 confirmed empirically on real data

A_S01 re-audit, like-for-like comparison:

| Denominator | accum_pts | cluster_pts |
|---|---|---|
| ÷ all frames (333) | 21.6 | — |
| **÷ detected (326)** | **22.0** | **21.0** |
| ÷ has-cluster | — | 21.1 |

`22.0 ≥ 21.0` — cluster is a subset, as the code guarantees.
Predicted `21.6 × 333/326 = 22.1` vs reported `22.0` ✓

**Artifact magnitude scales with the zero-detection rate:**

| Session | detection | dilution | accum ÷all → ÷detected | inverted? |
|---|---|---|---|---|
| A_S01 | 97.9% | ×1.021 | 21.6 → 22.1 | no |
| outdoor | 88.9% | ×1.125 | 36.5 → 41.1 | **yes** (fell below cluster 40.2) |

This explains why the false signal appeared only on the outdoor session and
confirms the diagnosis independently on two datasets.

### Two additional defects found during Stage 1 verification

**S1-a · Audit hardcoded a 400-frame dataset**

```python
"  STAGE ATTRIBUTION (totals over 400 frames):"                       # header lie
f"[{'PASS' if len(frame_rows)==400 else 'FAIL'}] frames.csv has 400 rows"
```

A_S01 has 333 frames, so the acceptance criterion reported a **spurious FAIL**
and the stage-attribution header claimed 400. Every session that is not exactly
400 frames was affected — i.e. all 13.

**Fixed:** header now uses `len(frame_rows)`; the criterion compares against
`n_input_files` (actual `.bin` count), so it now genuinely detects dropped frames
instead of dataset length.

**S1-b · "pass-through rate" was dimensionally invalid**

```python
pass-through = 1 - (grating_rej + cc_rej + fov_rej) / rd_cfar
```

`rd_cfar` counts **RD-domain detections**; `grating/fov/cc` count **azimuth-peak**
rejections. Each RD detection spawns up to `az_peak_max_n = 6` azimuth candidates,
so the az-peak population is several times larger. Subtracting one from the other
produced negative values: **−42.2%** (outdoor), **−5.7%** (A_S01: 766 − 810).

**Fixed:** `analyse_sessions.py` now reports `az peaks raw`, `cloud pts emitted`,
`az-peak survival = cloud_pts / az_peaks_raw`, and `rejected by gates` against the
same denominator, with an explicit note not to mix the two populations.

### Finding that feeds Stage 4.1

`wide_cluster_rej = 0` on A_S01 — the `max_cluster_radius = 0.65 m` gate (A-2)
costs **no data** in single-subject radial walking, as expected given
`rx_median = 0.153 m`.

**Still unmeasured:** the outdoor session and B_S01 (`rx = 0.398 m`, closest to the
limit). Run the audit on those two before changing `eps` in Stage 4.1 — if
`wide_cluster_rej > 0` there, lowering `eps` will *reduce* rejections (smaller
clusters) and the two changes must be evaluated together.

### Files changed

| File | MD5 |
|---|---|
| `streaming.py` | `60a4b4da150014d9b2accbec19c8831b` |
| `processing/accumulate.py` | `f7a203e4be1330e9af1fc8154b3272c4` |
| `diag_pipeline_audit.py` | `b2ab238cd5c91a304429ca9b840aa2b1` |
| `analyse_sessions.py` | `7b14a802daf815515a00309c6ffd0c50` |

**Stage 1 exit criterion met:** the viewer launches cleanly, the trail renders as a
correct gradient (operator-confirmed), and no shipped feature claims a signal it
cannot produce.

---

## Appendix B — B_S01 Re-audit: A-2 Is Costing 46% of Lateral Data (2026-07-27)

### Two runs, one operator error

The first "B_S01" run returned **byte-identical** statistics to A_S01 across all
17 metrics (333 frames, 326 detected, 766 RD-CFAR, centroid `+0.064 ± 0.368`).
`--out-dir` had been updated but `--folder` had not, so A_S01 was reprocessed
into the B_S01 directory.

**Root cause of the invisibility:** the summary printed only OUTPUT paths.
**Fixed:** the summary now leads with `INPUT folder`, `INPUT .bin files` with
first/last filenames, and `OUTPUT folder`. A session-mismatch guard warns when
the output session id does not appear in the input path (tested: correct
pairings pass, the exact mistake made warns).

### The real B_S01 result

| Quantity | Value |
|---|---|
| frames total / detected | 309 / 305 (98.7%) |
| avg cluster_pts ÷ detected | 14.1 |
| avg cluster_pts ÷ has-cluster | 26.7 |
| **frames WITH a cluster** | **161 (52.8% of detected)** |
| frames WITHOUT a cluster | 144 (47.2%) |
| **`wide_cluster_rej`** | **141** |
| genuine DBSCAN failures | 3 |

**141 of 144 missing clusters were wide-rejected.** `max_cluster_radius = 0.65 m`
discards **46% of B_S01's detected frames**. Phase 4/5/6 outputs for this session
exist for only ~53% of frames.

This was completely invisible before Stage 1.6 — `cluster_found=False` looked
identical whether DBSCAN found nothing or the cluster was thrown away.

### The rx statistics were right-censored

The reported `B_S01 rx_median = 0.398 m` was computed **only over surviving
frames** — i.e. frames where `rx` happened to fall below 0.65 m. The 141 frames
above the threshold were excluded by the very gate that dropped them.

**B_S01's true rx median is materially higher than 0.398 m.**

This *strengthens* the P0-1 counter-example: a single subject walking laterally
produces `rx` that not only exceeds the two-subject outdoor session (0.257 m) but
routinely exceeds 0.65 m outright. `rx` is definitively not a subject-count
discriminator.

**Fixed:** `rx`/`ry` are now recorded on wide-rejected frames, and the summary
prints the kept and rejected distributions separately:

```
    wide_cluster_rej   : 141  (frames dropped: rx > max_cluster_radius)
      rx kept     n= 161  median=0.399 m  max=0.649 m
      rx REJECTED n= 141  median=?.??? m  max=?.??? m   <-- censored above 0.65 m
```

### Leading hypothesis for the smearing — needs confirmation

Motion compensation aligns each buffered frame by
`pts_x += (ref_cx − frame.centroid_x)`. This is mathematically correct *provided
each frame's centroid is an unbiased estimate of the body centre*.

In a lateral crossing at 3 m standoff over ±3 m, the **aspect angle sweeps ~90°**
(−45° to +45°). Different body parts dominate the return at different aspect
angles, so `frame.centroid_x` wanders relative to the true body centre. With only
**2.36 pts/frame**, that bias is not averaged out, frames misalign, and the
accumulated cloud smears in X.

In a radial walk the aspect angle stays near 0° throughout — no sweep, no
wandering bias.

**Corroborating evidence:**

| | A_S01 (radial) | B_S01 (lateral) | ratio |
|---|---|---|---|
| centroid x std | 0.368 m | **1.165 m** | 3.2× |
| `fov_rej` | 13 | **92** | 7.1× |
| `cc_rej` | 94 | 146 | 1.6× |
| pts/frame | 1.83 | 2.36 | — |

The 7× rise in `fov_rej` confirms the subject spends significant time near the
±60° FOV limits, where azimuth estimation degrades — consistent with the
aspect-sweep hypothesis.

**Confirmation diagnostic (before any parameter change):** plot per-frame
`centroid_x` against frame index for B_S01, fit a smooth trajectory, and examine
the residual. If the residual correlates with aspect angle, the hypothesis holds.
The newly recorded rejected-`rx` values give the magnitude directly.

### Impact on Stage 4 — do not simply raise the threshold

Raising `max_cluster_radius` would admit clusters whose `rx`/`ry` are smearing
artifacts, not body geometry. Phase 5 ellipses fitted to them would be
meaningless. The options are:

1. **Fix compensation for lateral motion** — correct but the largest change.
2. **Shorten `accum_window` when lateral speed is high** — 8 frames halves the
   travel distance and the smear.
3. **Gate Phase 4/5 on a compensation-quality metric** — keep the frame for
   Doppler/gait, suppress body-shape features when alignment is poor.
4. **Raise the threshold** — papers over the problem. Not recommended alone.

This must be resolved **before** the `eps` retune in Stage 4.1, because `eps` and
`max_cluster_radius` interact: a smaller `eps` produces smaller clusters, which
would reduce the rejection rate without addressing the underlying smearing.

### Sessions requiring re-audit with the new counter

`C_S03` and `D_S03` were previously recorded as "detections present but
`cluster_pts` below threshold". Given the B_S01 result, those are plausibly
wide-rejections too rather than genuinely weak clusters. **All 13 sessions should
be re-audited** now that `wide_cluster_rej` and rejected-`rx` are recorded.

| File | MD5 |
|---|---|
| `diag_pipeline_audit.py` | `59bd7104325245453b13c534c1093554` |

---

## Appendix C — P0-5: Ghost-Gate Deadlock (2026-07-29)

**Severity: highest of the audit. Invalidates Phase 2–6 output across all sessions.**

### Discovery

The 13-session re-audit showed `rx` with `median == max` to 3 dp across hundreds
of frames — physically impossible for a moving subject:

| Session | set | n | median | max |
|---|---|---|---|---|
| B_S03 | kept | 365 | 0.186 | **0.186** |
| C_S03 | kept | 329 | 0.060 | **0.060** |
| D_S03 | kept | 389 | 0.193 | **0.193** |
| C_S01 | rejected | 37 | 0.991 | **0.991** |

C_S03 and D_S03 also showed `accum_pts == cluster_pts` pinned constant
(12.0 and 10.0), implying zero DBSCAN noise on every frame.

### Root cause — `processing/accumulate.py::update()`

```python
# Ghost gate
if abs(cur_cy - self._cy) > self._max_jump:
    return self._build_result(compensated=True)     # early return
```

Two defects:

**(a) Wrong reference.** The gate compared the current raw centroid against
`self._cy`, the **EMA**, which lags the true position by
`(v/fps)·(1−α)/α`. At `α=0.3`, `fps=4`:

| speed | EMA lag | vs gate 0.6 m |
|---|---|---|
| 0.70 m/s | 0.408 m | ok |
| 1.00 m/s | 0.583 m | ok |
| **1.03 m/s** | **0.601 m** | **trips** |
| 1.20 m/s | 0.700 m | trips |
| 1.40 m/s | 0.817 m | trips |

**Critical speed = `gate·fps·α/(1−α)` = 1.03 m/s.** Normal human walking is
1.2–1.4 m/s, so **steady walking tripped the gate with no ghost present**.

**(b) No recovery.** `self._cy` was not updated on the reject path, so once
tripped while the subject moved away, `|cur_cy − _cy|` only grew and the gate
fired forever. Reproduced: buffer froze at frame 3 of a clean 1.2 m/s walk and
returned the identical stale cloud for every subsequent frame.

### Why some sessions survived

Recovery required the subject to move **back** toward the frozen `_cy`:

- **A / D (out-and-back)** — each turnaround released the gate. Partial
  operation: `accum_pts` 22–27 instead of the expected ~35.
- **B (lateral)** — `y` roughly constant, so the y-gate rarely fired.
  B_S03 still froze.
- **C_S03 / D_S03** — froze early, never returned, **fully stale**.

### This reframes the "0 centroid jumps" result

"0 centroid jumps across 5,476 frames" was previously reported as the pipeline's
strongest result. A **frozen** centroid cannot jump. The metric is satisfied
trivially by the bug, so it is necessary-but-not-sufficient evidence of good
tracking and should not be cited as validation until re-measured post-fix.

### Fix applied

```python
ref_raw = self._last_raw_cy if self._last_raw_cy is not None else self._cy
if abs(cur_cy - ref_raw) > self._max_jump:
    self._coast += 1
    if self._coast <= self._max_coast:      # coast at most 3 frames
        return self._build_result(compensated=True)
    # persistent -> re-seed rather than stay frozen
    ...clear buffer, reseed on cur_cx/cur_cy...
self._coast = 0
self._last_raw_cy = cur_cy
```

Gating against the last **accepted raw** centroid makes `max_jump = 0.6 m` mean
what it was always documented to mean: 0.6 m per frame at 4 fps = 2.4 m/s max
plausible speed. The coast counter guarantees the accumulator can never lock
permanently. Added diagnostics: `n_ghost_gated`, `n_reseeds`.

### Validation

| Test | Result |
|---|---|
| T1 steady 1.2 m/s, 30 frames | accum 3→**48** (window full). Pre-fix froze at 9. **PASS** |
| T2 fast 1.8 m/s | accum **48**, `ghost_gated=0`. Pre-fix deadlocked. **PASS** |
| T3 single +5 m ghost | rejected, buffer unchanged at 10 frames. **PASS** |
| T4 persistent +5 m relocation | `[30,30,30,3,6,9,12,15,18,21]` — coasts 3, re-seeds, regrows. Pre-fix: frozen forever. **PASS** |
| T5 rx variability | 8 unique values vs 1 pre-fix. **PASS** |

### Consequences — data must be re-derived

Every Phase 2–6 number in this project was produced by a partially or fully
frozen accumulator. The following are **invalidated pending re-audit**:

- `accum_pts`, `cluster_pts`, `cluster_noise`
- `rx` / `ry` and every body-shape comparison built on them
- `dx_std` / M5 range-independence
- all gait features (`dop_centroid`, `dop_spread`, `limb_frac`)
- the "0 centroid jumps" result
- `wide_cluster_rej` counts from Appendix B (the smearing may be partly
  frozen-buffer artefact rather than genuine lateral smearing)

**The A-2 / eps analysis in Appendix B must be re-run before any Stage 4
parameter change.** The lateral-smearing hypothesis remains plausible but its
supporting numbers were measured on corrupted output.

| File | MD5 |
|---|---|
| `processing/accumulate.py` | `7a374e498b27deb5e440ab95e1c2f3c2` |

---

## Appendix D — Post-P0-5 Re-audit: Results and Two Corrections (2026-08-02)

All 13 sessions re-audited (13 audited, 0 skipped, 0 failed), including
`outdoor_long` via the new path-override mechanism.

### Confirmed: the frozen-buffer signature is eliminated

| Session | pre-fix rx med/max | post-fix rx med/max | spread |
|---|---|---|---|
| B_S03 | 0.186 / **0.186** | 0.324 / 0.608 | 1.9× |
| C_S03 | 0.060 / **0.060** | 0.150 / 0.626 | 4.2× |
| D_S03 | 0.193 / **0.193** | 0.148 / 0.522 | 3.5× |

`median == max` is gone everywhere. The accumulator is live.

### Correction 1 — my prediction that `accum_pts` would RISE was wrong

Mean `accum_pts/detected` **fell** 22.7 → 16.9 (−25.5%), down in 9 of 10 sessions.

The reasoning error: I focused on the deadlock releasing and overlooked which
branch dominates. Pre-fix, a tripped gate returned the stale buffer and **never
cleared it** — so the buffer sat *full* (16 frames) indefinitely and reported a
high but meaningless `accum_pts`. Post-fix, a persistent break **clears and
re-seeds**, so the count restarts and regrows.

**A frozen-full buffer reports more points than a correctly re-seeding one.**
The drop is the expected consequence of the fix, not a regression. Verified: the
post-fix sequence is a saw-tooth (`3,6,9…33,36,3,6,9…`), the correct signature of
a live accumulator; a flat maximum would indicate it is stuck.

**However**, mean `accum_pts` of ~17 against a window capacity of ~35 means the
gate still fires often. With only 1.4–2.4 pts/frame, the median centroid is
computed from ~2 points, where one spurious point swings it by half the point
separation. `max_jump = 0.6 m` may be too tight for such a noisy estimator —
a measurement-noise problem, not subject motion. Requires investigation.

### Correction 2 — I overstated the DBSCAN-chaining diagnosis

My first chaining test printed a conclusion its own output contradicted: every
`eps` from 0.80 down to 0.35 produced **one** cluster spanning 3.40 m. The test
used a 0.22 m/frame residual, so every consecutive pair was inside even the
smallest `eps` — nothing could break. The test was invalid.

Corrected sweep (largest-cluster `rx` in metres):

| residual step | eps 0.80 | 0.65 | 0.55 | 0.45 | 0.35 |
|---|---|---|---|---|---|
| 0.10 m | 0.80 | 0.80 | 0.80 | 0.80 | 0.80 |
| 0.22 m | 1.64 | 1.64 | 1.64 | 1.64 | 1.64 |
| 0.40 m | 3.05 | 3.05 | 3.05 | 1.97 | 0.45 |
| 0.55 m | 4.14 | 4.14 | 1.10 | 0.31 | 0.23 |
| 0.70 m | 5.20 | 1.74 | — | — | — |

**Lowering `eps` only helps if the residual step exceeds the new `eps`.** For a
smooth dense trail (step 0.10–0.40 m — what 1.2 m/s at 4 fps with partial
compensation produces) dropping `eps` to 0.45 changes **nothing**.

Revised statement: wide clusters arise when the merged cloud's x-extent exceeds
`2 × max_cluster_radius`; chaining binds it into one cluster. The controlling
variable is the **residual trail**, not `eps`.

### Wide clusters are not a multi-subject phenomenon

| session | rejected rx max | implied x-span | subjects |
|---|---|---|---|
| outdoor_long | **2.087 m** | 4.17 m | 2 |
| D_S03 | 1.548 m | 3.10 m | **1** |
| C_S02 | 1.299 m | 2.60 m | **1** |
| B_S03 | 1.264 m | 2.53 m | **1** |
| A_S01 | 1.061 m | 2.12 m | **1** |

Single subjects produce clusters spanning up to 3.1 m. A person cannot span 3 m,
so these are compensation/chaining artefacts affecting **every** scenario.
`outdoor_long` is the extreme case, not a distinct mechanism. This further
undermines any attempt to use `rx` as a subject-count discriminator (cf. P0-1).

### New diagnostic added — and a false start

First attempt measured the spread of *compensated centroids*. That is
identically zero by construction: compensation maps every centroid onto
`ref_cx` exactly. Caught when the test printed `0.000` for both radial and
lateral.

Corrected metric measures the merged **point cloud**:

- `comp_residual_x` — full x-extent of the merged cloud (trail length)
- `comp_step_x` — largest gap between consecutive sorted x values
  (DBSCAN chains the cloud into one cluster iff every gap ≤ `eps`)
- `comp_residual_y` — y-extent

Comparing `comp_step_x` against `eps` on real sessions is the evidence needed to
choose `eps`. It did not previously exist. Synthetic clouds are too well-behaved
to reproduce the wide clusters (`gap_x` 0.04–0.11 m), which is precisely why
measurement on recorded data is required.

### Revised Stage 4 plan

The earlier ordering — retune `eps` first — is **wrong**, for two reasons:

1. `eps` may be irrelevant if the residual step is small (table above).
2. Lowering `eps` splits one subject into fragments, and P0-2 keeps only the
   largest, so `cluster_pts` would fall further. It is already 3.9–18.0.

Correct order:

| # | Action | Rationale |
|---|---|---|
| 4.0 | Re-audit with `comp_step_x` / `comp_residual_x` | Establishes whether `eps` can help at all |
| 4.1 | Fix compensation residual (or shorten window when speed is high) | Attacks the root cause |
| 4.2 | Multi-cluster retention (Stage 3 / P0-2) | Must precede `eps` reduction |
| 4.3 | Retune `eps` — only if `comp_step_x` shows it will act | Evidence-driven |
| 4.4 | Revisit `max_cluster_radius` | Meaningful only once clusters are real |

### Data status

Post-fix values are the **first trustworthy Phase 2–6 measurements** in the
project. Pre-fix numbers throughout earlier appendices are void.
`outdoor_long` now has clean numbers for the first time: 88.9% detection,
`accum/det` 17.7, `cluster/det` 12.0, 182 wide rejections (17% of clustered
frames), `y_std` 4.184 m (≈2× any other session — open-space walking).

| File | MD5 |
|---|---|
| `processing/accumulate.py` | `4cb8bca6c2ebbcb660cc3fa8be0aff8f` |
| `diag_pipeline_audit.py` | `3b7f87f461223ba164d0f05f99395299` |

---

## Appendix E — Post-Fix Data Quality: Buffer Fill Is 52% (2026-08-02)

### Run validity

The 21:08 re-audit returned **byte-identical** numbers to the 20:35 run across
all 13 sessions. The residual diagnostics are pure measurement with no
behavioural change, so this is the expected result and confirms determinism.

### Reporting defect — the new metrics never reached the summary

`comp_residual_x` / `comp_step_x` were added to `FRAME_COLS` (written to
`frames.csv`) but **no summary line was added**, and the `reaudit_all.ps1`
filter did not match them. The decisive measurement was being written to disk
and never displayed. Both fixed.

### Cluster availability across all sessions

| session | detected | has cluster | cluster % | wide-rej % | DBSCAN-fail % |
|---|---|---|---|---|---|
| A_S01 | 326 | 292 | 89.6% | 4.3% | 6.2% |
| A_S02 | 302 | 226 | 75.0% | 1.3% | 23.7% |
| B_S01 | 305 | 200 | 65.6% | 22.3% | 12.1% |
| B_S02 | 261 | 232 | 88.9% | 8.4% | 2.7% |
| B_S03 | 374 | 195 | 52.1% | 29.1% | 18.8% |
| C_S01 | 177 | 145 | 81.9% | 2.3% | 15.9% |
| C_S02 | 190 | 95 | **50.0%** | 15.3% | 34.7% |
| C_S03 | 330 | 269 | 81.5% | 1.2% | 17.3% |
| D_S01 | 331 | 268 | 81.1% | 3.9% | 15.0% |
| D_S03 | 391 | 247 | 63.1% | 25.1% | 11.8% |
| outdoor_long | 1286 | 887 | 69.0% | 14.1% | 16.9% |
| **TOTAL** | **4274** | **3057** | **71.5%** | **12.8%** | **15.7%** |

**Only 72% of detected frames yield a usable cluster.** 13% are wide-rejected;
16% fail DBSCAN outright (`min_samples=3` unmet on a sparse cloud).

The worst session is **C_S02 (stand+walk, 50%)** — *not* a lateral session. This
weakens the earlier framing that wide clusters are primarily a lateral-motion
problem; the failure is broader.

### Buffer fill fraction — the accumulator holds half its window

A full 16-frame buffer should hold `16 × pts_per_frame` points.

| session | pts/frame | expected | actual | fill % | effective window |
|---|---|---|---|---|---|
| B_S02 | 1.39 | 22.2 | 19.6 | 88.1% | 14.1 / 16 |
| A_S01 | 1.83 | 29.3 | 20.0 | 68.3% | 10.9 / 16 |
| B_S01 | 2.36 | 37.8 | 23.9 | 63.3% | 10.1 / 16 |
| B_S03 | 2.16 | 34.6 | 20.3 | 58.7% | 9.4 / 16 |
| D_S03 | 2.22 | 35.5 | 19.2 | 54.1% | 8.6 / 16 |
| C_S01 | 2.02 | 32.3 | 15.3 | 47.3% | 7.6 / 16 |
| outdoor_long | 2.37 | 37.9 | 17.7 | 46.7% | 7.5 / 16 |
| C_S03 | 2.07 | 33.1 | 15.4 | 46.5% | 7.4 / 16 |
| D_S01 | 1.98 | 31.7 | 13.1 | 41.4% | 6.6 / 16 |
| C_S02 | 2.30 | 36.8 | 11.4 | 31.0% | 5.0 / 16 |
| A_S02 | 2.26 | 36.2 | 10.9 | **30.1%** | **4.8 / 16** |
| **MEAN** | | | | **52.3%** | **~8 / 16** |

**Phase 4/5/6 features assume 4 s of accumulated geometry but are computed on
~2 s.** Every `rx` / `ry` / `dx_std` in the dataset reflects a partial window.
A_S02 re-seeds roughly every 5 frames — a track break every 1.2 s.

### Why the gate still fires — a 2-point median

`cur_cy = median(cloud[:, 1])` with **1.4–2.4 pts/frame**. With two points the
median is their midpoint; with one it *is* that point. Body depth spans
~0.3–0.5 m in range, so a 2-point median can swing ~0.25 m frame-to-frame from
geometry alone. Add real motion (0.30 m/frame at 1.2 m/s) and `max_jump = 0.6 m`
is marginal by construction.

This is **measurement noise**, not subject motion. Candidate mitigations:

1. Gate on a **predicted** position (constant-velocity) rather than the last
   accepted one — motion is subtracted before thresholding.
2. Adaptive `max_jump = k × observed frame-to-frame velocity`.
3. Power-weighted centroid instead of unweighted median.
4. Raise `max_jump` — crude, weakens genuine ghost rejection.

**None should be selected before measuring the actual displacement
distribution.**

### New tool: `analyse_gate.py` — no re-run required

`centroid_x` / `centroid_y` have been `frames.csv` columns since Phase 0, so the
frame-to-frame displacement distribution — exactly what the gate thresholds —
is computable from the CSVs already on disk.

Reports per session: displacement median / p90 / p99 / max, gate-trip count and
rate, and (when present) `comp_step_x` percentiles against `dbscan_eps`.

Decision rules encoded in the output:

| Question | Evidence |
|---|---|
| Is `max_jump` too tight? | Is displacement p90 close to 0.6 m? |
| Can lowering `eps` reduce wide `rx`? | Is `comp_step_x` p90 close to `eps`? |
| Motion or noise? | Displacement median vs 0.30 m expected at 1.2 m/s |

| File | MD5 |
|---|---|
| `analyse_gate.py` | `bff933b60a1b0386f8e8b8c238d98e1f` |
| `diag_pipeline_audit.py` | `c93aed6f18555c4f99018881930f9fdd` |
| `reaudit_all.ps1` | `481cc4dd275878d875af9f6d8d3dd124` |

---

## Appendix F — P0-6: Root Cause Found — Per-Frame Cloud Contamination (2026-08-02)

The gate analysis settles both open questions, and **both of my predictions were
wrong**. It also identifies a single upstream defect that explains every Phase
2/3 symptom recorded in this audit.

### Q1 — Is `max_jump = 0.6 m` too tight? **No.**

I hypothesised the gate was over-tight for a noisy 2-point median. The data
refutes it. Frame-to-frame raw-centroid displacement:

| session | median | → m/s | p99 | max | → km/h | trip % |
|---|---|---|---|---|---|---|
| A_S01 | 0.279 | 1.12 | 1.605 | 2.399 | 34.5 | 9.7 |
| A_S02 | 0.379 | 1.52 | 3.202 | 4.276 | 61.6 | 37.5 |
| B_S01 | 0.742 | 2.97 | 5.948 | 6.717 | **96.7** | 53.8 |
| B_S03 | 0.425 | 1.70 | 6.783 | 8.118 | **116.9** | 40.4 |
| outdoor_long | 0.327 | 1.31 | 4.888 | 7.079 | **101.9** | 26.9 |

**Mean trip rate 32.2%.**

The **median** (0.15–0.74 m) is consistent with real walking. The **tail** is
not: maxima imply 10–32 m/s, i.e. 38–117 km/h. Usain Bolt peaks at 12.3 m/s.
These are not subject motion — the centroid is landing on a different scatterer.

The distribution is **bimodal**: ~68% of frames track the subject, ~32% do not.
Raising `max_jump` would admit 2–8 m jumps that are unambiguously garbage.
**The gate is behaving correctly. 32% of frames are bad.**

### Q2 — Can lowering `eps` reduce wide clusters? **No.**

I predicted `step_p90 << eps`, making `eps` inert. Observed:

| session | step_med | step_p90 | % > eps |
|---|---|---|---|
| A_S01 | 0.367 | 2.722 | 25.9% |
| B_S01 | 1.640 | 4.538 | **73.9%** |
| B_S03 | 1.504 | 3.102 | 67.1% |
| outdoor_long | 0.411 | 1.835 | 27.6% |

`step_p90` is **1.5–4.5 m against `eps = 0.80 m`**. DBSCAN is **already
splitting** the cloud in 26–74% of frames; the code keeps only the largest
fragment (P0-2), which is precisely why `cluster_pts << accum_pts`.

- **Lower `eps`** → fragments further, `cluster_pts` falls. Worse.
- **Raise `eps`** → chains contamination into a multi-metre cluster that
  `max_cluster_radius` then rejects. Also worse.

**`eps` is not the lever. Stage 4.3 should be dropped** until cloud quality is
fixed.

### What `comp_residual_x` actually measures

Algebraically, for point *p* in frame *f*:

```
compensated x = x_p + (ref_cx − c_f) = (x_p − c_f) + ref_cx
```

`ref_cx` is constant across frames and cancels in an extent. So

```
comp_residual_x = extent over all (p,f) of (x_p − c_f)
```

— the union of **within-frame** deviations from each frame's own centroid. It is
**not** a compensation-error metric (compensation cancels exactly); it is a
**per-frame cloud quality** metric.

**Precision:** it is a union across up to 16 frames, so it is set by the *worst*
frame in the buffer, not the typical one. Correct reading: *the median buffer
contains at least one frame whose points span X metres about its own centroid.*

| session | median residual | worst-frame half-spread | vs body 0.225 m |
|---|---|---|---|
| A_S01 | 0.733 | 0.366 | 1.6× |
| outdoor_long | 0.983 | 0.491 | 2.2× |
| D_S03 | 2.523 | 1.262 | 5.6× |
| A_S02 | 2.788 | 1.394 | 6.2× |
| B_S01 | 3.983 | 1.992 | **8.9×** |

DBSCAN runs on the merged cloud, so **one contaminated frame in sixteen is
enough** to fragment the cluster or stretch it past `max_cluster_radius`.

### Single root cause confirmed

| correlation | r |
|---|---|
| trip % vs `comp_residual_x` | **+0.826** |
| trip % vs `comp_step_x` | **+0.889** |
| trip % vs % > eps | **+0.850** |
| cluster availability vs `comp_residual_x` | **−0.670** |

Gate trips, cluster fragmentation and wide rejections are **not three defects**.
They are three symptoms of one upstream problem.

### P0-6 — The cross-cluster filter cannot see off-range contamination

`radar_processing.py`, cross-cluster coherence gate:

```python
if abs(y_j - y_i) < _cc_range_m and abs(x_j - x_i) > _body_hw_m:
    keep_mask[j] = False
    cc_rej += 1
```

with `_cc_range_m = 0.35 m`, `_body_hw_m = 0.30 m`.

The condition is **conjunctive**. Cluster *j* is rejected only if it is *both*
within 0.35 m in range *and* beyond 0.30 m in azimuth. **A return at a different
range is never rejected, however far away it is** — `|y_j − y_i| ≥ 0.35 m`
short-circuits the test.

Subject at (x=0, y=5.0):

| contaminant | \|dy\| | \|dx\| | distance | rejected? |
|---|---|---|---|---|
| grating lobe, same range | 0.10 | 2.50 | 2.50 | yes |
| second person beside | 0.05 | 1.20 | 1.20 | yes |
| wall return, 2 m further | 2.00 | 0.40 | 2.04 | **no** |
| fence post, 3 m further | 3.00 | 2.50 | 3.91 | **no** |
| second person, offset range | 1.00 | 1.20 | 1.56 | **no** |
| parked car, 4 m nearer | 4.00 | 3.00 | 5.00 | **no** |

The filter removes same-range azimuth ambiguities (grating lobes) — its original
purpose — but is structurally blind to everything else.

**This also reframes an earlier "improvement".** Reducing `cross_cluster_range_m`
from 1.0 → 0.35 cut `cc_rej` by 71%, previously recorded as improved precision.
It actually **narrowed the only window in which the filter can act at all**.

### Proposed fix — needs design review before implementation

Add a **subject-proximity gate**: reject clusters beyond a radius *R* of the
tracked subject in Euclidean distance, rather than only same-range pairs.

`radar_config.py` already contains `anchor_mode = 'power_continuity'` with the
comment *"will use track centroid in Phase 3"* — the intended feedback path that
was never wired (listed as an open item in §8.2). This is that item.

Design considerations:

- **Bootstrapping** — no track exists on frame 1; fall back to boresight-nearest.
- **Radius** — must accommodate body extent plus one frame of motion:
  `R ≈ body_half_width + v_max/fps ≈ 0.3 + 0.6 = 0.9 m` as a starting point.
- **Failure mode** — too tight and the track cannot recover after a real break;
  needs the same coast logic as P0-5.
- **Validation** — `comp_residual_x` must fall toward ~0.45 m and the gate-trip
  rate toward single digits. Both are now measurable.

### Revised plan

| # | Action | Status |
|---|---|---|
| ~~4.3~~ | ~~Retune `eps`~~ | **Dropped** — data shows no useful direction |
| ~~—~~ | ~~Raise `max_jump`~~ | **Dropped** — gate is correct |
| **6.1** | Subject-proximity gate wired to the Phase 3 track | **New — highest priority** |
| 6.2 | Re-audit; verify `comp_residual_x` → ~0.45 m, trip rate → <10% | after 6.1 |
| 6.3 | Multi-cluster retention (P0-2) | after 6.2 |
| 6.4 | Revisit `max_cluster_radius` | only once clusters are clean |

Phase 4/5/6 features remain **unreliable** until 6.1–6.2 land: they are computed
on ~52% buffer fill from clouds where roughly one frame in three carries a
multi-metre contaminant.

---

## Appendix G — P0-6 Fix Implemented: Subject-Proximity Gate (2026-08-02)

### Design

A Euclidean-distance gate against the tracked subject position, replacing
nothing — it runs **after** the existing cross-cluster filter, which continues
to handle same-range grating lobes.

```python
if _sg_en and track_hint is not None and len(cluster_results) > 0:
    near = [c for c in cluster_results
            if (cx(c) - tx)**2 + (cy(c) - ty)**2 <= _sg_radius**2]
    if near:
        sg_rej = len(cluster_results) - len(near)
        cluster_results = near
    else:
        sg_bypass = 1          # pass frame UNGATED
```

**Radius** `subject_gate_radius_m = 0.90 m` = body half-width (0.30) + one
frame of motion at the `max_jump` ceiling (0.60 m at 4 fps = 2.4 m/s).

**Track source.** `process_frame(track_hint=(x, y))` — an *input*, not retained
state, so `process_frame` stays stateless. The hint is the **DBSCAN cluster
centroid** where available, falling back to the accumulator centroid. Using the
cluster centroid matters: the accumulator centroid is computed from the raw
cloud and is therefore contaminated by exactly the returns the gate exists to
remove.

**Threading.** The accumulator lives in the GUI thread, `process_frame` in the
worker thread. The hint is published as a plain tuple assignment — atomic under
the GIL, no lock. One frame of staleness is immaterial: 0.30 m of motion against
a 0.90 m radius.

### The safety bypass — why it is not optional

Gating the cloud by the track creates a **positive-feedback loop**: if the track
drifts onto a ghost, the real subject falls outside the radius, gets filtered
out, and the track can never recover because the evidence needed to correct it
has been deleted.

The bypass breaks the loop. When *every* cluster falls outside the radius the
frame is passed through **ungated** and `sg_bypass` is incremented, letting the
P0-5 ghost gate coast and re-seed onto the true position. Verified by test T3.

`sg_bypass` is also the health metric: a persistently high rate means the track
is unreliable or the radius is too tight.

### Tests

| # | Scenario | Result |
|---|---|---|
| T1 | 6 contaminants + subject, hint at subject | kept **1**, rejected **6** — only the subject survives |
| T2 | Same input through the *old* cc filter | kept 5 of 7 — **4 contaminants survive** |
| T3 | Track stale on a ghost, only real subject present | `sg_bypass=1`, both clusters kept — **track can re-seed** |
| T4 | Bootstrap, `hint=None` | all 7 kept — **identical to pre-fix** |
| T5 | 3 real body cross-sections spanning 0.28 m | 0 rejected — **body not fragmented** |

T1 vs T2 is the headline: on identical input the old filter passed 4 contaminants
that the new gate removes.

### Backward compatibility

`track_hint` is the **last** parameter and **optional**. Verified by AST:
required args remain `cube, cfg`. `diag_xyz.py`, `main.py`,
`benchmark_pipeline.py` and `radar_plots.py` are unmodified and unaffected —
with no hint the gate is inert and behaviour is bit-identical to pre-fix.

The gate requires `subject_gate_en` **and** a non-None hint **and** clusters
present; any one false leaves `cluster_results` untouched.

### Known interaction with future multi-subject work

T1 shows the gate rejects a second person 1.2 m away. That is **correct for the
current single-subject design** but directly conflicts with Stage 3
(multi-cluster retention, P0-2). When multi-subject support lands the gate must
become per-track rather than single-track. Noted so it is not discovered later
as a regression.

### New instrumentation

`sg_rej` and `sg_bypass` per frame, in the `process_frame` audit CSV, the
`frames.csv` schema (38 columns, alignment AST-verified), the summary block, and
the `reaudit_all.ps1` filter.

### Expected effect — the falsifiable prediction

| metric | before | expected after |
|---|---|---|
| `comp_residual_x` median | 0.73–3.98 m | → ~0.45 m (body width) |
| gate-trip rate | 32.2% mean | → <10% |
| `comp_step_x` p90 | 1.5–4.5 m | → < eps (0.80 m) |
| buffer fill | 52% | → >80% |
| cluster availability | 71.5% | → >90% |
| `wide_cluster_rej` | 547 total | → near zero |

If `comp_residual_x` does **not** fall toward 0.45 m, the contamination is not
off-range clusters and this diagnosis is wrong.

`sg_bypass` should be low. A high rate means the radius is too tight or the
track is unreliable — check before interpreting anything else.

| File | MD5 |
|---|---|
| `radar_config.py` | `7cd0383bfabcd852110a34b9cb1c2a2c` |
| `radar_processing.py` | `e0f4a0df230d88d71c2d85004a08ad5f` |
| `streaming.py` | `327faf196c9eeb70e6b209f73b16b6a4` |
| `diag_pipeline_audit.py` | `9379e69ab6426d5137f1ca3d2f43e2b4` |
| `reaudit_all.ps1` | `6935a6f031785c0b0523b844bf18bf60` |

---

## Appendix H — P0-6 Results: 4/6 Predictions Met, 1 Failed by My Design Error (2026-08-03)

### Scorecard

| metric | before | predicted | actual | verdict |
|---|---|---|---|---|
| `comp_residual_x` median | 0.73–3.98 m | ~0.45 m | **0.11–1.14 m** (med ~0.28) | **PASS** — better than predicted |
| `wide_cluster_rej` total | 547 | near zero | **69** | **PASS** — 87% reduction |
| cluster availability | 71.5% | >90% | **~95%** | **PASS** |
| buffer fill | 52% | >80% | **~77%** | close |
| `comp_step_x` p90 | 1.5–4.5 m | <0.80 m | 0.12–4.37 m | partial — 4/11 sessions |
| gate-trip rate | 32.2% | <10% | **19.1%** | **FAIL** |

Supporting evidence that the gate removed contamination and not body:

- `pts/frame` fell 13–27% (A_S01 1.83→1.51, B_S01 2.36→1.72)
- `rx kept` median moved **toward** body half-width: B_S01 0.281→**0.154**,
  B_S03 0.324→**0.229**, A_S01 0.117→**0.103**
- A_S01 and B_S02 now have `comp_step_x` p90 of **0.118 m** and **0.275 m**
  against `eps` 0.80 — the trail is dense and contiguous, as a single body
  should be

### The failure — and it was my design error

I wrote: *"Check `sg_bypass` first — if it's high, the radius is too tight and
nothing else in the run is meaningful."* It is high.

| session | `sg_bypass` | detected | bypass % |
|---|---|---|---|
| D_S03 | 81 | 391 | 20.7% |
| B_S03 | 78 | 374 | 20.9% |
| A_S01 | 100 | 326 | 30.7% |
| A_S02 | 112 | 302 | 37.1% |
| D_S01 | 142 | 331 | 42.9% |
| C_S01 | 82 | 177 | 46.3% |
| outdoor_long | 577 | 1286 | 44.9% |
| **TOTAL** | **1477** | **4273** | **34.6%** |

**The gate was inactive on 34.6% of frames.** The improvements above were
achieved with the gate acting on only two-thirds of the data.

**Root cause — I sized the radius without counting the hint's own lag.**

The hint was `accum_result.cluster.centroid_{x,y}`, the centroid of the
motion-compensated accumulated cloud, aligned to `ref_cy = self._cy` — the
**EMA**, which trails by `(1-α)/α = 2.33` frames.

| v (m/s) | m/frame | EMA lag | radius left of 0.90 m |
|---|---|---|---|
| 0.5 | 0.125 | 0.292 | 0.608 |
| 1.0 | 0.250 | 0.583 | 0.317 |
| **1.2** | 0.300 | **0.700** | **0.200** |
| 1.5 | 0.375 | 0.875 | 0.025 |

I sized `radius = body(0.30) + one frame of motion(0.60) = 0.90 m` and **did not
account for the hint being 2.33 frames stale**. At the measured ~0.25 m/frame
the lag alone consumes 0.58 m, leaving 0.32 m for body extent (0.225 m half-width)
plus noise. The budget was exhausted by construction.

**Confirmed:** correlation between median frame-to-frame displacement and bypass
rate is **r = +0.855**. Faster subject → more bypass, exactly as a stale hint
predicts.

### Fix — correct the hint, do not widen the gate

Widening the radius would weaken the gate to compensate for a fixable error.
Instead the accumulator now exposes a **lag-corrected prediction**:

```python
lag_s      = ((1 - alpha) / alpha) / fps     # 0.583 s at alpha=0.3, 4 fps
predicted_x = cx_out + vel_x * lag_s
predicted_y = cy_out + vel_y * lag_s
```

`velocity_x` added alongside the existing `velocity_y` (`_prev_cx` tracked
through init, EMA update, and re-seed paths). Both callers now use
`predicted_x/y`.

**Validation:**

| test | result |
|---|---|
| Steady 1.2 m/s, 30 frames | centroid error **0.700 m** → predicted error **0.000 m** |
| `alpha=1.0` (no smoothing) | prediction ≡ centroid — degenerate case correct |
| Stationary subject | no drift, `vel=0.000` |
| Budget at 1.2 m/s | usable radius **0.200 m → 0.600 m (3×)** |

One implementation note: the first attempt computed the prediction before
`cx_out`/`cy_out` were assigned — `UnboundLocalError` caught immediately by the
test, not by inspection. Reordered.

### Still open after this fix

**`comp_step_x` p90 remains high on B_S01 (4.369 m), B_S03 (3.283 m),
C_S02 (2.895 m).** These are the sessions with the highest bypass rates, so the
next run should improve them. If they persist, a second contamination mechanism
exists that the proximity gate does not address.

**`outdoor_long` max displacement rose 7.079 → 13.087 m.** Unexplained. A 13 m
frame-to-frame jump is far outside anything physical. Worth isolating in the
next run — it may be a two-subject handover the single-track gate cannot express.

**Do not read the current Phase 4/5/6 numbers as final.** They were produced
with the gate inactive on a third of frames.

| File | MD5 |
|---|---|
| `processing/accumulate.py` | `2a0ed14a68a12274d692a280ac964e40` |
| `streaming.py` | `da70d82556d2a350a4c04c79abe96863` |
| `diag_pipeline_audit.py` | `0c34457335f4058017c87aaa0a7246cf` |

---

## Appendix I — Lag Fix Results: Large Gains, Residual Unexplained (2026-08-03)

### Three-run trajectory

| session | bypass v1 | bypass v2 | trip v0 | v1 | v2 | fill | clustered |
|---|---|---|---|---|---|---|---|
| A_S01 | 30.7% | **4.9%** | 9.7% | 4.7% | **2.5%** | 87.9% | 99.6% |
| A_S02 | 37.1% | 16.2% | 37.5% | 26.9% | 17.9% | 66.7% | 93.8% |
| B_S01 | 30.2% | 18.7% | 53.8% | 21.1% | 13.2% | 94.9% | 87.7% |
| B_S02 | 21.1% | 18.0% | 13.5% | 6.9% | 5.0% | 93.8% | 99.5% |
| B_S03 | 20.9% | 19.8% | 40.4% | 19.1% | 18.1% | 90.5% | 98.7% |
| C_S01 | 46.3% | 23.7% | 30.4% | 24.4% | 16.7% | 60.1% | 96.1% |
| C_S02 | 37.4% | 25.3% | 45.6% | 28.0% | 21.4% | 71.1% | 84.0% |
| C_S03 | 26.4% | 13.6% | 31.7% | 16.6% | 12.9% | 74.9% | 98.4% |
| D_S01 | 42.9% | 18.4% | 31.7% | 25.9% | 11.6% | 72.2% | 96.1% |
| D_S03 | 20.7% | 12.8% | 32.8% | 13.1% | 7.7% | 78.5% | 97.1% |
| outdoor_long | 44.9% | 28.8% | 26.9% | 23.0% | 19.7% | 59.0% | 94.1% |
| **MEAN** | **34.6%** | **20.1%** | **32.2%** | **19.1%** | **13.3%** | **77.2%** | **95.0%** |

### Scorecard against the original P0-6 predictions

| metric | v0 | target | now | verdict |
|---|---|---|---|---|
| `comp_residual_x` median | 0.73–3.98 m | ~0.45 m | 0.13–0.71 m | **PASS** |
| `wide_cluster_rej` | 547 | near zero | **57** | **PASS** (−90%) |
| cluster availability | 71.5% | >90% | **95%** of accum pts clustered | **PASS** |
| buffer fill | 52% | >80% | 77.2% | close |
| gate-trip rate | 32.2% | <10% | 13.3% | near miss |
| `sg_bypass` | — | low | 20.1% | still high |

`cluster_pts` now nearly equals `accum_pts` on most sessions (A_S01 23.1/23.2,
B_S02 19.1/19.2, B_S03 23.3/23.6) — the cloud is clean enough that DBSCAN
clusters almost everything, instead of picking one fragment of a contaminated
scatter.

### The lag fix is confirmed

Bypass 34.6% → 20.1%, trip 19.1% → 13.3%. The mechanism was verified before the
fix (r = +0.855 between subject speed and bypass rate) and the predicted
direction and rough magnitude both materialised.

### My reversal hypothesis was wrong — retracted

I proposed the residual bypass was concentrated at direction reversals, where
EMA velocity still points the old way. **My own test refuted it**: error was
0.000 m through the turnaround.

The reason is that on a *noiseless linear ramp* `EMA + velocity × lag` recovers
the true position exactly — the standard lag-compensation identity — so a test
with 3 clean points per frame cannot exhibit the failure mode at all. The test
was incapable of testing the hypothesis.

Re-run with realistic conditions (2 pts/frame, 30% contamination):

| condition | err median | p90 | max | >0.90 m |
|---|---|---|---|---|
| clean, 3 pts | 0.018 | 0.055 | 0.083 | 0% |
| realistic, 2 pts, 30% contam | 0.082 | 0.498 | 1.108 | **3%** |

Noise does produce bypass — but only ~3%, against 20.1% observed.

### Honest position on the residual

**The remaining 20.1% is not explained.** Correlations are weak: detection rate
r = −0.478, trip rate r = +0.791, `step_p90` r = +0.277, `resid_med` r = +0.013.
No single driver.

What *is* established:
- the EMA-lag component is fixed and quantified
- it is **not** reversals (my test refuted that)
- it is **not** simple cloud noise at the simulated level (3% vs 20%)

### Likely structural ceiling — a bootstrap loop

The gate needs a clean track; the track needs a clean cloud; the cloud is
cleaned by the gate. A_S01 — the cleanest session — has the lowest bypass
(4.9%), lowest trip (2.5%) and lowest `step_p90` (0.327). Dirtier sessions
struggle to converge.

Breaking the circularity requires a tracker with its own motion model that does
**not** depend on the current frame's cloud being clean — i.e. the **Kalman
filter recorded in the original plan as "deliberately skipped"**. That decision
should be revisited. It is a Stage 3 design choice, not a tweak to this gate.

### Recommendation — stop tuning the gate

Further gate tuning has poor expected value:

1. `sg_bypass` is a **safety valve**. When it fires, behaviour reverts to
   pre-fix — degraded but safe, never worse than the previous baseline.
2. The largest single remaining win is untouched and independent:
   **Stage 2.2, applying the existing `ra_focus_mask` to the FFT AoA path,
   ≈24 ms/frame (35% of latency), ~1 day.**
3. `outdoor_long` has the worst bypass (28.8%) for a reason the gate cannot
   address: two subjects, one track. That is **Stage 3**.

### Still unexplained and worth isolating

`outdoor_long` max frame-to-frame displacement is **13.087 m**, unchanged across
all three runs. At 4 fps that implies 52 m/s. It is not affected by any fix so
far, which suggests a distinct mechanism — plausibly a two-subject handover the
single-track model cannot express. Worth isolating the specific frames.

### Data status

Phase 4/5/6 numbers are now the **most trustworthy in the project**, but carry
the caveat that the gate is inactive on ~20% of frames. Suitable for relative
comparison between sessions; not yet for absolute body-shape claims.

---

## Appendix J — Stage 2.2 Implemented: Focused Azimuth FFT (2026-08-03)

### What was wrong

The default FFT AoA path was the **only** one ignoring `ra_focus_mask`:

```python
if   cfg.aoa_method == "capon":    RA = _az_capon(...,  ra_focus_mask)   # uses it
elif cfg.aoa_method == "music":    RA = _az_music(...,  ra_focus_mask)   # uses it
elif cfg.aoa_method == "bartlett": RA = _az_bartlett(..., ra_focus_mask) # uses it
else:
    az_cube = _az_fft_fn(virt_pos, cfg)                    # IGNORES the mask
    RA = _collapse_ra_fn(az_cube, RD_mti, rd_det, cfg)
```

It built the full `[64, 256, 256]` cube — 4.19 M complex64, **33.6 MB per
frame** — and `_collapse_ra_from_fft` then read only the masked cells.

### Correction to my own audit

**Audit L-1 claimed "≈2% of the computed cube is used". That was wrong.**

I assumed only detected *range* bins mattered. But `_ra_focus_mask_from_rd` has
a fallback that marks doppler bins in **every** range column, so no range is
ever fully excluded. Measured with the real mask algorithm on a realistic RD
map: **17.9%** of cells are used, not 2%.

The reduction is therefore **≈5.6×, not ≈50×**. Revised expectation for S7
(26.13 ms measured): 26.13 → ~5–9 ms, saving **~17–21 ms**. Still the largest
single latency win available, but the earlier figure overstated it.

### Implementation

New `_az_fft_focused_ra(virt_rd, focus_mask, cfg, az_fft_fn)`:

1. `np.nonzero(focus_mask)` → the selected (doppler, range) pairs
2. ranges with an **empty** mask column get all doppler bins appended,
   reproducing the `else` branch of `_collapse_ra_from_fft` exactly
3. gather → `[1, N_sel, n_va]`, so the **existing** GPU/CPU az FFT is reused
   unchanged (no new GPU kernel)
4. scatter-average per range via `argsort` + `np.add.reduceat`
   (`np.add.at` is correct but an order of magnitude slower here)

Dispatch keeps the old path when the full cube is genuinely needed:

```python
_need_full_cube = bool(getattr(cfg, 'save_drea_path', None))
```

### Second finding — `arr_drea` was computed and discarded

`res.arr_drea` is built **every frame** on the FFT path, but `streaming.py` has
**zero** references to it and it is only written when `cfg.save_drea_path` is
set. `build_arr_drea` reduces the whole cube (`(|az_cube|²).sum(axis=0)`), so
that work was also wasted in live and audit operation. It is now skipped unless
the output is actually requested.

### Third finding — the focus mask was computed twice

`collapse_ra_from_fft_gpu` calls `ra_focus_mask_gpu(RD_mti, rd_det, cfg)`
internally — the same function, with the same inputs, already called at the
dispatch site. The fast path reuses the existing mask instead.

Verified safe: same function, same arguments, therefore an identical mask.
Saves ~0.5 ms/frame on GPU and **~30 ms/frame on CPU-only machines**, where
`_ra_focus_mask_from_rd` is a 256-iteration Python loop.

### Equivalence testing

Focused RA vs full-cube RA, five configurations including the empty-column
fallback branch:

| trial | dop × rng | mask density | empty cols | max abs err |
|---|---|---|---|---|
| 0 | 64 × 256 | 8% | 1 | 3.8e-06 |
| 1 | 64 × 256 | 15% | 5 | 1.9e-06 |
| 2 | 32 × 128 | 5% | 16 | 1.9e-06 |
| 3 | 64 × 64 | 100% | 0 | 3.8e-06 |
| 4 | 64 × 64 | 3% | 13 | 3.8e-06 |

All differences are at float32 rounding level. Trial 3 (density 1.0) confirms
the degenerate case, trials 2 and 4 exercise the fallback heavily.

### Measured speedup (CPU, realistic mask)

Mask built by the real algorithm on a synthetic RD map with 3 targets:
**17.9% density, 0 empty columns.**

| path | time | peak cube |
|---|---|---|
| full cube | 111.19 ms | 33.6 MB |
| focused | 15.61 ms | 6.0 MB |
| **speedup** | **7.12×** | **−82% memory** |

The CPU figure includes the doubled mask computation the old path performed, so
it exceeds the pure 5.6× work reduction. The GPU figure must be measured on
hardware.

### Verification required before accepting

1. Re-run `benchmark_pipeline.py` **on a session with real detections** — the
   existing `benchmark_summary.txt` reports `0.0 confirmed range bins`, so it
   measured an empty workload and is not a valid baseline.
2. Replay A_S01 and D_S01 and confirm `frames.csv` is unchanged on `cloud_pts`,
   `cluster_pts`, `dop_centroid`. **Any change means the RA map differs and the
   optimisation is wrong.**
3. Confirm `res.arr_drea` is `None` in live mode and still produced when
   `save_drea_path` is set.

| File | MD5 |
|---|---|
| `radar_processing.py` | `efead0b9ec86a06e6abca430ae77f081` |

---

## Appendix K — Stage 2.2 ACCEPTED + a Duplicate-Column Bug Found (2026-08-03)

### Acceptance test: PASS

All 13 sessions run through **both** code paths from the same binary
(`--full-az-cube` selects the original), then diffed column by column:

| session | rows | diffs | session | rows | diffs |
|---|---|---|---|---|---|
| A_S01 | 333 | **0** | C_S02 | 309 | **0** |
| A_S02 | 309 | **0** | C_S03 | 421 | **0** |
| A_S03 | 71 | **0** | D_S01 | 333 | **0** |
| B_S01 | 309 | **0** | D_S02 | 309 | **0** |
| B_S02 | 262 | **0** | D_S03 | 391 | **0** |
| B_S03 | 381 | **0** | outdoor_long | 1447 | **0** |
| C_S01 | 262 | **0** | | | |

**4,137 frames, zero differences on 23 critical columns.** This includes
A_S03 and D_S02 (0% detection — the only sessions exercising the empty-mask
guard) and C_S01/C_S02 (61–68% detection — heaviest fallback-branch use).

**Stage 2.2 is accepted.** The focused azimuth FFT is numerically equivalent.

### Two script bugs found along the way — both mine

**K-1 · `UnicodeEncodeError` under redirection**

`radar_config.py` prints `→` (U+2192) and `×` (U+00D7). Python selects
stdout's encoding at startup: a **console** usually copes, a **pipe** falls back
to the locale codec (`cp1252` here), which cannot represent them. My script's
`| Out-Null` made stdout a pipe.

30 printed lines contain non-ASCII (16 in `radar_processing.py`, 11 in
`radar_config.py`, 2 in the audit, 1 in streaming). Editing all 30 in the DSP
core to satisfy a console codec is invasive and regression-prone;
`PYTHONIOENCODING=utf-8` fixes every one, in every redirection context, with
zero pipeline risk.

The same failure also revealed that the script **never checked
`$LASTEXITCODE`** — both audits "completed", produced no `frames.csv`, and the
comparison would have run on missing or stale files. Exit codes are now checked,
output is captured to `verify\logs\`, and the script aborts with exit 2 before
comparing if any run failed.

**K-2 · Duplicate column name in `frames.csv` — a data-integrity bug**

`Import-Csv` refused the file: *"The member dop_max is already present."*
`FRAME_COLS` declared **`dop_max` twice**:

| position | meaning | added by |
|---|---|---|
| 28 | max \|Doppler\| in the **DBSCAN cluster** | Phase 6 gait (mine) |
| 36 | max \|dop\| in the **raw per-frame cloud** | Phase 0 (original) |

`csv.DictReader` silently keeps only the **last** duplicate. Demonstrated:
header `a,dop_max,b,dop_max` with row `1,0.55,2,1.33` yields `dop_max = 1.33`
— the first value is unrecoverable.

**Consequence:** `analyse_sessions.py` read `dop_max` intending the Phase 6
cluster metric and received the Phase 0 raw-cloud value. Every figure previously
reported as gait `dop_max` (e.g. 2.498, 1.327 m/s) was actually a raw-cloud
maximum over a different point set. Those specific numbers are **withdrawn**.

**Not affected:** `dop_centroid`, `dop_spread`, `limb_frac`, `n_torso_pts`,
`n_limb_pts` are uniquely named. The Phase 6 conclusions resting on `limb_frac`
and `dop_centroid` stand. P0-3 (cadence non-functional) is unaffected — it
depends on `limb_frac`.

**Fixed:** the Phase 6 column is renamed `gait_dop_max`. AST-verified: 38
columns, 38 unique, no duplicates. `analyse_sessions.py` reads `gait_dop_max`
with a fallback to the old name for CSVs written before the fix.

`Import-Csv` was also removed from the verification script — it throws on *any*
duplicate header, which let a schema bug silently kill the timing report. The
timing summary now uses python's tolerant `csv` module and cannot fail the run.

### Process note

The `analyse_sessions.py` patch initially **failed silently** — my patch script
printed "updated" without checking the anchor matched, and the checksum was
unchanged. Caught by verifying the checksum rather than trusting the message.
Re-applied with an `assert` on the anchor.

### Outstanding

The `proc_ms` speedup table did not print because of K-2. Re-run
`verify_stage22.ps1` to obtain it — the equivalence result above already stands
and does not need repeating.

| File | MD5 |
|---|---|
| `diag_pipeline_audit.py` | `aef9d13d1d0473828a0fb942fcb75481` |
| `analyse_sessions.py` | `f3c43508a6ec4e844d8a3ac9fc0975cc` |
| `verify_stage22.py` | `a9064cee54ed8afd45be3e3c998608c6` |
| `verify_stage22.ps1` | `ce457fbfe843fdbb95eeefa927b35295` |

---

## Appendix L — Stage 2.2 Measured: 63 ms/frame (37%), and a Bigger Lead (2026-08-03)

### Result

Per-session `proc_ms` A/B on identical input, same binary, 13 sessions:

| session | det% | full-cube | focused | saved | speedup |
|---|---|---|---|---|---|
| A_S01 | 97.9% | 182.8 | 113.9 | 68.9 | 1.60× |
| A_S02 | 97.7% | 184.1 | 113.4 | 70.7 | 1.62× |
| A_S03 | 0.0% | 92.4 | 55.6 | 36.8 | 1.66× |
| B_S01 | 98.7% | 184.3 | 114.0 | 70.3 | 1.62× |
| B_S02 | 99.6% | 183.7 | 112.5 | 71.1 | 1.63× |
| B_S03 | 98.2% | 190.2 | 116.6 | 73.6 | 1.63× |
| C_S01 | 67.6% | 167.9 | 103.2 | 64.7 | 1.63× |
| C_S02 | 61.5% | 178.2 | 103.6 | 74.6 | **1.72×** |
| C_S03 | 78.4% | 182.7 | 113.2 | 69.5 | 1.61× |
| D_S01 | 99.4% | 190.5 | 115.8 | 74.7 | 1.65× |
| D_S02 | 0.0% | 101.1 | 99.8 | 1.3 | 1.01× ⚠ |
| D_S03 | 100.0% | 190.7 | 116.6 | 74.1 | 1.64× |
| outdoor_long | 88.9% | 185.6 | 115.9 | 69.7 | 1.60× |
| **MEAN** | | **170.3** | **107.2** | **63.1** | **1.59×** |

Excluding the disturbed D_S02 run: **68.2 ms saved, 1.63×**.

Combined with the 13/13 equivalence result, **Stage 2.2 is accepted**:
identical output, ~37% less frame time.

### Correction — my 26.13 ms S7 baseline was invalid

The interpretation line printed `Implied S7 now: 26.13 - 63.1 = -37.0 ms`,
which is impossible and exposed the error.

I flagged that `benchmark_summary.txt` measured an empty workload
(`0.0 confirmed range bins`, `cfar_margin 5.0`) and then used its S7 figure
anyway. That was inconsistent. Measured full-cube frames are **167–191 ms**,
2.7× the benchmark's 68.4 ms mean.

Deriving S7 from the measurement instead:

```
saving = S7_full x (1 - 1/5.6)   ->   S7_full = 63.1 / 0.821 = 76.8 ms
                                      S7_focused          = 13.7 ms
```

**S7 was ~77 ms, not 26 ms** — about 42% of the frame. The 5.6× work
reduction predicted from the 17.9% mask density holds; only the absolute
baseline was wrong.

### D_S02 is a disturbed run, not a data property

Every session has `p90/median` of 1.03–1.13. **D_S02 is 1.73** (median 101.1,
p90 174.9) while its focused run is clean (99.8 / 105.0). Its full-cube median
also sits far below every other session.

That is an externally disturbed run — thermal, GPU contention, or another
process — not a property of the frames. **A_S03, the other 0%-detection
session, saved 36.8 ms at 1.66×**, in line with everything else. D_S02 should
be re-measured before being used in any timing claim.

### Scene independence confirmed

Excluding D_S02, the zero-detection session (A_S03, 1.66×) matches the
detecting sessions (1.60–1.72×). The saving does **not** depend on scene
complexity, so it should hold in deployment.

Note the absolute frame times differ sharply — A_S03 runs at 92 ms versus
~185 ms for detecting sessions — because the downstream az multi-peak and xyz
extraction stages do nothing with no detections. The *ratio* is what transfers.

### The bigger lead this uncovered

~77 ms for a `[64, 256, 48] -> 256` FFT is far above the 26.13 ms recorded on
GPU. For reference, plain numpy on a CPU-only sandbox measures **58 ms** for
exactly that shape — the right order for 77 ms including surrounding work.

**Hypothesis: the audit path is not GPU-accelerated.** If confirmed, enabling
it is a larger win than Stage 2.2 delivered and needs no algorithm change.

`check_gpu.py` added: reports whether CuPy imports, whether a CUDA device is
visible, which GPU/CPU implementations `radar_processing` bound, and times the
azimuth FFT both ways.

Two outcomes:

- **bindings say CPU** → enable GPU; expect S7 77 → ~26 ms even before the
  focused path, and ~5 ms with it
- **bindings say GPU and the GPU is fast** → the ~77 ms is host↔device copy and
  allocation churn, making **audit L-2 (11 blocking transfers per frame)** the
  next target

### Tooling fixed

`timing_report.py` no longer assumes the reference benchmark. It derives
`S7_full` from the measured saving, warns when the implied cost exceeds 45 ms
(pointing at `check_gpu.py`), and flags disturbed runs via `p90/median > 1.3`
so they are excluded from means rather than silently averaged in.

| File | MD5 |
|---|---|
| `timing_report.py` | `4229b8d645870aeb9e2d708fcb39666b` |
| `check_gpu.py` | `b1fc891183569e1bc66d131198c52497` |

---

## Appendix M — P0-7: A Cosmetic `.decode()` Silently Disabled the GPU (2026-08-03)

**Likely the single most expensive defect in the project.**

### How it surfaced

Stage 2.2 saved 63 ms/frame, implying `S7_full ≈ 77 ms`. A GPU FFT of that
shape takes **0.7 ms**. If the GPU path were live there would have been almost
nothing to save. That contradiction led here.

Hardware check on the target machine:

```
cupy 14.1.0                    OK
NVIDIA GeForce RTX 3080 Ti     visible, 16.0 GB free
azimuth FFT  CPU  40.3 ms  |  GPU  0.7 ms      61.9x
```

A working GPU, sitting idle.

### Retraction — my first `check_gpu.py` binding report was invalid

It inferred bindings by grepping source lines for a prefix. The GPU bindings
read `az_fft_gpu as _az_fft_fn`, so a prefix match on `_az_fft_fn` only ever
matched the **CPU fallback branch** and reported CPU unconditionally — for any
machine, regardless of what actually ran. The conclusion happened to be right;
the evidence for it was not. Rewritten to import and inspect at runtime.

### Root cause — `gpu_accel.py`

```python
try:
    import cupy as cp
    import cupy.fft as cp_fft
    from cupyx.scipy.ndimage import convolve, maximum_filter
    _test = cp.zeros(1, dtype=cp.float32); del _test
    GPU_AVAILABLE = True
    _GPU_DEVICE = cp.cuda.Device().id
    _GPU_NAME   = cp.cuda.runtime.getDeviceProperties(_GPU_DEVICE)["name"].decode()
    print(f"[GPU] CuPy available ...")
except Exception as _e:
    GPU_AVAILABLE = False          # <-- reached by a COSMETIC failure
```

Older CuPy returned device-property strings as **bytes**; CuPy 14 returns
**str**, so `.decode()` raises `AttributeError`. The handler catches bare
`Exception`, so a **device-name lookup** — used only for a log line — sets
`GPU_AVAILABLE = False`.

`radar_processing.py` then imports **eight** names in one statement, and its
handler also catches broadly, so *every* accelerated stage reverts to CPU:
range FFT, doppler FFT, azimuth FFT, power reduce, elevation FFT, CFAR, focus
mask, RA collapse.

Corroboration: my own `check_gpu.py` needed
`nm.decode() if isinstance(nm, bytes) else nm` to print that device name — the
str-vs-bytes difference is real and current on this CuPy version.

### Why it went unnoticed

The fallback is **by design silent** — it prints one line at import and then
degrades gracefully. Everything worked, just ~3× slower than the hardware
allows. Audit item P4 flagged "5 silent exception handlers" as a maintainability
concern; this is that concern materialising as the project's largest
performance defect.

### Fix

Functional capability and cosmetic reporting are now separated. A name-lookup
failure prints a warning and **cannot** disable acceleration:

```python
try:
    import cupy ...; _test = cp.zeros(1); del _test
    GPU_AVAILABLE = True                      # functional only
except Exception as _e:
    GPU_AVAILABLE = False
    print(f"[GPU] CuPy not available ({type(_e).__name__}: {_e}) ...")

if GPU_AVAILABLE:
    try:                                       # cosmetic only
        _raw = cp.cuda.runtime.getDeviceProperties(dev)["name"]
        _GPU_NAME = _raw.decode() if isinstance(_raw, (bytes, bytearray)) else str(_raw)
    except Exception as _e:
        print(f"[GPU] device name unavailable ({_e}) - acceleration still ENABLED")
```

Exception types are now printed alongside messages, so the next silent
fallback is diagnosable from one log line.

### Expected impact — to be measured, not assumed

Eight stages return to GPU. From the reference benchmark, the GPU-accelerated
stages totalled ~58 ms of a 68.4 ms frame. Current measured frames are
107–116 ms **with** the Stage 2.2 optimisation already applied.

The azimuth FFT alone should go **40.3 → 0.7 ms**. Predicting the total is
unwise given how wrong the 26.13 ms baseline proved; measure it.

**Note the interaction with Stage 2.2:** once the GPU is live, the focused
azimuth FFT saves far less in absolute terms — 5.6× of 0.7 ms rather than 5.6×
of 40 ms. Stage 2.2 remains correct and worth keeping (it also removes a
duplicated mask computation and 33.6 MB/frame of allocation), but its headline
63 ms saving was largely a symptom of this defect. **Re-measure Stage 2.2 with
the GPU enabled before quoting its benefit.**

### Verification required

1. `python check_gpu.py` — expect `GPU_AVAILABLE: True`
2. Watch for `[GPU] CuPy available — device 0: NVIDIA GeForce RTX 3080 Ti`
   at pipeline start; the old build printed `[GPU] CuPy not available (...)`
3. Re-run `verify_stage22.ps1` — equivalence must still hold, and both paths
   should drop sharply in absolute time
4. Confirm `frames.csv` is unchanged: GPU/CPU numerical parity has **never been
   tested** (audit Stage 5.4, still open). This change makes that test
   load-bearing rather than theoretical.

| File | MD5 |
|---|---|
| `gpu_accel.py` | `4ae75de36ab58452c94b090c1ed858bc` |
| `check_gpu.py` | `e8d552e795374528c09649553beaef45` |

---

## Appendix N — P0-7 Fixed and Confirmed; Everything Must Be Re-measured (2026-08-03)

### Fix confirmed on target hardware

```
cupy 14.1.0                                          OK
NVIDIA GeForce RTX 3080 Ti Laptop GPU                visible
[GPU] CuPy available - device 0: NVIDIA ... 3080 Ti  <- NEW (was "not available")
import processing.gpu_accel                          OK
GPU_AVAILABLE                                        True   <- was False
all 8 required names present                         YES
azimuth FFT   CPU 40.0 ms  |  GPU 0.6 ms             66x
```

The eight accelerated stages are live again: range FFT, doppler FFT, azimuth
FFT, power reduce, elevation FFT, CFAR, focus mask, RA collapse.

### A second defect in my own diagnostic

The VERDICT block still read *"The pipeline is running this stage on CPU"*
**after** the fix. It compared live timings against a **hardcoded**
`S7_IMPLIED = 76.8` captured before the fix — a stale constant, so it could
only ever conclude CPU.

Fixed: the verdict is now driven by the runtime `GPU_AVAILABLE` value and the
import result, not a baked-in number. This is the second time in this appendix
sequence that a *diagnostic* rather than the pipeline was wrong; both were
caught by output contradicting known state.

### What is now invalidated

**Every measurement in this project was produced on the CPU path.** All 13
sessions, every Phase 2-6 metric, every latency figure, and Stage 2.2's
headline saving.

Specifically obsolete:

| figure | why |
|---|---|
| Stage 2.2 saving 63.1 ms/frame (1.59x) | Measured with a 40 ms CPU FFT. On GPU the FFT is 0.6 ms, so the focused path saves ~5.6x of 0.6 ms, not of 40 ms |
| `S7_full ~= 77 ms` | Derived from the CPU-path saving |
| all `proc_ms` values (92-191 ms) | CPU path throughout |
| benchmark_summary.txt 68.4 ms / 26.13 ms | Already suspect (0 detections, wrong CFAR margin), now doubly so |

**Stage 2.2 remains correct and worth keeping** — it is numerically equivalent
(13/13 sessions), removes a duplicated focus-mask computation, and avoids
33.6 MB/frame of allocation. But its *benefit* must be re-measured; the headline
number was largely a symptom of P0-7.

### What is NOT invalidated

All **correctness** findings are decision-level, not timing-level, and stand:

- P0-1 dead multi-subject detector (unreachable by construction)
- P0-2 multi-cluster data discarded in `_cluster()`
- P0-3 cadence saturation (`limb_frac` pinned at ~1.0)
- P0-5 ghost-gate deadlock (EMA lag vs `max_jump`)
- P0-6 off-range contamination (conjunctive cross-cluster test)
- K-2 duplicate `dop_max` column

...**provided** GPU and CPU produce the same point clouds. Which has never been
tested.

### New: `check_parity.py` — audit Stage 5.4, finally load-bearing

The original plan required a GPU/CPU parity test. It was never written, and
until now it did not matter because the GPU was never running. It now decides
whether ~2,000 lines of audit findings carry forward.

Runs the same frames through both paths, forcing CPU by monkey-patching
`gpu_accel.GPU_AVAILABLE` — the same flag every `*_gpu` entry point guards on,
so it is a faithful switch. Samples frames across the session rather than taking
the first N, and sorts by power before comparing so ordering cannot create false
differences.

The distinction it enforces:

- **float differences are expected** — GPU and CPU reduce in different orders
- **different `cloud_pts` is a failure** — that is CFAR or a gate resolving
  differently, i.e. a different pipeline, not noise

### Required sequence

1. `python check_gpu.py` — confirm `GPU_AVAILABLE: True`
2. `python check_parity.py --folder <A_S01 frames> --cfg <cfg>` — **must pass
   before anything else is trusted**
3. `.\verify_stage22.ps1` — Stage 2.2 equivalence must still hold on GPU
4. `python timing_report.py` — re-measure; expect both paths far faster and the
   gap between them much smaller
5. Re-run `reaudit_all.ps1` and `analyse_gate.py` — restate Phase 2-6 metrics on
   the GPU path

If step 2 fails, stop. Prior CPU-derived results would not carry forward and
that becomes the priority over any further optimisation.

| File | MD5 |
|---|---|
| `check_gpu.py` | `e5950c2b1c1cf5de5fe7dfc363187a1b` |
| `check_parity.py` | `7e47513dc7a4f236b46465dbe3995bd0` |

---

## Appendix O — GPU/CPU Divergence Localised to the FFT Stages (2026-08-03)

### `check_parity.py` result — the backends are NOT interchangeable

30 frames of A_S01, GPU vs CPU:

| metric | value |
|---|---|
| frames with different `cloud_pts` | **6 of 30 (20%)** |
| direction | **GPU < CPU in every case** |
| worst position difference | 0.144 m = **2.2 range bins** / 3.7 az bins |
| worst power difference | 2.72 dB (~10⁵× float32 rounding) |

These are different bins being selected, not the same bin computed slightly
differently.

### `check_parity_stages.py` — where it starts

Each stage fed **identical input**, so differences are per-stage, not inherited:

| stage | verdict |
|---|---|
| S2 range FFT | **DIFFERS** |
| S4 doppler FFT + MTI | **DIFFERS** |
| S5 power dB reduce | OK (1.53e-05) |
| S6 CFAR detections | **OK — 0 of 16384 cells differ** |
| RA focus mask | **OK — 0 of 16384 cells differ** |
| S7 azimuth FFT | **DIFFERS** |

**Every FFT stage differs; every non-FFT stage agrees exactly.**

This reframes the problem. It is **not** "GPU CFAR is wrong" — CFAR and the
focus mask are bit-identical on identical input. cuFFT and numpy's pocketfft use
different algorithms and summation orders, so float32 disagreement between them
is expected.

**Ruled out earlier:** `cfar_2d_gpu` returns `_cfar_2d_cpu` when
`cfar_method == 'os'` (the pipeline default), so both paths already run
identical CFAR code.

### Mechanism explaining the point-count differences

In the stage test each stage got identical input, so CFAR agreed. In the *real*
pipeline, GPU CFAR consumes a GPU-computed RD map that differs slightly. A
detection sitting within float noise of its threshold then flips.

The observed size fits: 6 of 30 frames differing by only 1–2 points — marginal
detections. It also compounds with the audit's own finding that the cloud is
extremely sparse (1.4–2.4 pts/frame), so one flipped detection is a large
fractional change.

### A bug in my comparator — the FFT numbers were understated

`np.asarray(x, np.float64)` on a **complex** array silently discards the
imaginary part (the `ComplexWarning` in the log). The reported max differences
for S2/S4/S7 were **real-part only**.

Fixed, and extended to report **relative** error and detect scale factors —
absolute error alone cannot distinguish rounding from an algorithmic bug:

| relative error | meaning |
|---|---|
| ~1e-6 | float32 epsilon — benign rounding |
| ≫1e-6 | different algorithm, window or normalisation |
| near-constant ratio | a scale factor — a real bug |

Self-tested against injected faults: 0.1% scale factor → `SCALE=1.001000`,
window difference → `SCALE=0.496920`, pure rounding → `rel=1.15e-05` OK.

### Unresolved — do not close this yet

**All 6 count differences had GPU < CPU.** Under symmetric rounding that is a
1-in-64 outcome (p = 0.016). Suggestive of a small systematic bias, but 6
samples cannot settle it. The corrected relative-error output will.

Two possible conclusions, with different consequences:

1. **`rel ≈ 1e-6`, no SCALE flag** → benign float32 divergence. The pipeline is
   simply threshold-sensitive on a sparse cloud. Then the question becomes a
   policy one: accept small run-to-run variation for a large speedup, or keep
   CPU for reproducibility. Detection counts would need re-measuring on GPU
   either way.
2. **`rel ≫ 1e-6` or a SCALE flag** → a genuine algorithmic defect in the GPU
   FFT wrappers (window, normalisation, or zero-padding), which must be fixed
   before the GPU is used at all.

**Until this is resolved, the GPU path must not be used to produce results.**
The CPU path remains the reference: every finding in this audit derives from it
and is internally consistent.

### Note

This divergence has existed for the entire project. It was invisible only
because P0-7 kept the GPU switched off. The correctness findings (P0-1…P0-6)
are logic defects demonstrated from code and CPU data and do not depend on the
backend — they stand regardless of how this resolves.

| File | MD5 |
|---|---|
| `check_parity.py` | `7e47513dc7a4f236b46465dbe3995bd0` |
| `check_parity_stages.py` | `5829e3707885d95ca61dcd506fa7ae23` |

---

## Appendix P — GPU FFT Is Not Defective; The Pipeline Is Ill-Conditioned (2026-08-03)

### Result: both backends are float32-correct

Measured against a **float64** reference (the only way to judge which of two
float32 implementations is right):

| | L2 rel | peak rel | rel @40 dB |
|---|---|---|---|
| **S2 range FFT — GPU** | 1.344e-07 | 1.138e-07 | 5.93e-06 |
| **S2 range FFT — CPU** | 4.122e-08 | 5.116e-08 | 2.14e-06 |
| **isolated cuFFT** | 1.324e-07 | 1.807e-07 | 1.09e-05 |
| **isolated pocketfft** | 4.729e-08 | 6.936e-08 | 2.70e-06 |

float32 epsilon = 1.19e-07. **Both sit at epsilon level.** GPU is ~3× further
but still float32-accurate; cuFFT and pocketfft use different algorithms and
summation orders. The isolated synthetic test matches the in-pipeline result
almost exactly, confirming this is the FFT libraries, **not** the wrappers.

**No defect. `SCALE` was not flagged on any stage** — no window, normalisation
or scale-factor error.

### But my "CFAR threshold flip" explanation does not survive arithmetic

| quantity | value |
|---|---|
| GPU FFT relative error | 1.34e-07 |
| in power | ~2.7e-07 |
| in dB | ~1.2e-06 dB |
| cells tested (16384 × 30 frames) | 491,520 |
| **expected flips at that tolerance** | **~0.5** |
| **observed frames with count differences** | **6** |

Roughly **100× more divergence than FFT rounding alone predicts.** The
explanation I gave in Appendix O was incomplete.

### Likely amplifier — MTI clutter removal (catastrophic cancellation)

Measured absolute error:

```
S2 range FFT         absmax = 1.99e-03
S4 doppler FFT + MTI absmax = 4.68e-02      <- 23x larger
```

MTI subtracts the mean across chirps to cancel static clutter. For a static
scatterer the subtracted values are nearly equal, so the result is a **small
difference of large numbers**. Absolute error survives the subtraction while
the signal shrinks, amplifying relative error. The 23× jump from S2 to S4 is
that signature; later stages compound it before CFAR sees the map.

**This is a conditioning property of the pipeline, not a GPU bug.** The CPU path
has identical sensitivity — it simply rounds the other way. It also means the
pipeline would show run-to-run variation under *any* perturbation at this level
(different BLAS, different CPU, compiler flags).

### Correction — my position-difference figures are upper bounds

`check_parity.py` sorted both clouds by power and compared index-by-index. With
1–3 points of similar power, the two backends can order two points differently,
and I would then difference point A against point B — reporting 0.144 m when
both clouds contain both points.

**Treat 0.144 m and 2.72 dB as upper bounds, not measurements.** A
nearest-neighbour match is needed to separate "different points" from "same
points, different order". The **count** differences (6/30) are not an ordering
artefact and stand.

### Recommendation — stay on CPU for the remainder of the audit

Not because the GPU is wrong, but for sequencing:

1. **Every finding in this audit derives from CPU-path data.** Stages 3–5
   (multi-cluster retention, adaptive `dop_limb_thr`, cadence rebuild) are
   corrections whose effect is judged by comparison against those CPU results.
   Switching backend mid-audit adds a second variable to every comparison.
2. **The remaining work is correctness, not throughput.** P0-2, P0-3 and the
   Stage 5 hardening items are logic changes; a 66× FFT speedup does not help
   land them and the current ~110 ms/frame is well inside the 250 ms budget.
3. **Switching is cheap and reversible later** — `GPU_AVAILABLE` is the single
   switch, and P0-7 is already fixed, so the option is banked.

**Then, after Stage 5:** switch to GPU, re-baseline all 13 sessions in one pass,
and treat the GPU numbers as the new reference. Do not mix.

**Separately worth doing regardless of backend:** the MTI conditioning issue
means detection counts are sensitive to numerical noise from any source. If
reproducibility matters in deployment, raising `cfar_margin_db` so marginal
detections are not decided at the rounding level is the structural fix — at a
cost in sensitivity that should be measured, not assumed.

### Tooling note

Three of my own diagnostics were wrong before this converged: the source-grep
binding report, the complex→real cast, and the dynamic-range-inflated `rel`
metric. Each was caught by output contradicting known state rather than by
inspection. The float64-reference method was the first that could actually
answer the question, because comparing two float32 implementations to each
other cannot establish which is correct.

| File | MD5 |
|---|---|
| `check_fft_truth.py` | `f306dfbb63866268e285ef64103c113a` |

---

## Appendix Q — Stage 3 Part 1: Multi-Cluster Retention (P0-2) (2026-08-03)

### Delivered

**3.1 `SubjectCluster` + all clusters retained.** `_cluster()` previously did

```python
best_label = max(unique, key=lambda l: (labels == l).sum())
body_pts   = pts[labels == best_label]      # every other cluster discarded
```

DBSCAN's segmentation was already correct; the code destroyed it. Now every
cluster is built and carried in `ClusterResult.subjects`, with the largest
still exposed through the existing `centroid_*` / `n_pts` / `radius_*` fields
so **no existing caller changes** (verified by test T3).

**3.2 Frame-to-frame identity.** Greedy nearest-centroid association gated by
`max_jump` (0.6 m at 4 fps = 2.4 m/s — the same physical bound the ghost gate
uses). Unmatched tracks coast for `_max_coast` frames before being dropped, so
a subject briefly missed by DBSCAN keeps its id instead of being reissued one.

Greedy is adequate here: clusters are few (1–3) and well separated relative to
the gate, so greedy and optimal assignment coincide outside contrived cases.

| test | result |
|---|---|
| T1 two separated subjects | **2 clusters retained** (was always 1) |
| T2 identity while converging, 12 frames | id-set constant `{0,1}` — **PASS** |
| T3 single subject, backward compatibility | `cluster_found`, `n_pts`, `rx` unchanged; `subjects=1`, `primary_idx=0` — **PASS** |
| T4 coast through a 2-frame dropout | **initially FAILED — 3 ids for 2 subjects** |

### T4 exposed an architectural defect — motion compensation is single-subject

Not a tracker bug. Traced by instrumenting the merged cloud:

```
f0  present=[-1.0, +1.0]   frame centroid_x = +0.00   clusters: id0@-1.00, id1@+1.00
f3  present=[-1.0]         frame centroid_x = -1.00   clusters: id2@-2.00, id3@+0.00, id0@-1.00
```

The compensation shift is `(ref_cx - frame.centroid_x)`. With two subjects the
frame centroid sits **between** them — a point belonging to neither — and jumps
whenever either appears, disappears, or moves relative to the other. Buffered
frames are then shifted by **different amounts**, so one physical person is
smeared across several x positions and DBSCAN correctly reports them as
separate clusters.

**Phase 2 accumulation assumes exactly one moving body whose median position is
meaningful.** That assumption fails silently in every multi-subject scene — and
`outdoor_long`, the only multi-subject session, was accumulated this way
throughout.

### Mitigation applied

While **more than one confirmed track** (`age >= 2`) is present, accumulation
runs **uncompensated**: positions stay true at the cost of the intra-body
coherence gain compensation gives a single subject. The `age >= 2` requirement
prevents a one-frame DBSCAN fragment from flipping the mode.

Re-tested: 2 stable ids through the dropout; single-subject behaviour
unchanged (`compensated=True`).

This is a **mitigation, not a solution**. The principled fix is per-subject
accumulation — each track keeping its own buffer and its own compensation
reference — which is a larger change and should be scoped separately.

### Consequence for existing results

`outdoor_long` metrics were produced with single-subject compensation applied
to a two-subject scene. Its `rx = 0.257 m`, `rx_std = 0.098 m`, `comp_step_x`
and `wide_cluster_rej = 182` are all suspect: part of the "merge/split" pattern
attributed in Appendix B to subjects converging may in fact be compensation
smearing. **Re-audit `outdoor_long` before drawing conclusions from it.**

### Remaining in Stage 3

| # | Work | Status |
|---|---|---|
| 3.3 | Make the P0-6 subject gate **per-track** | **not started — blocking** |
| 3.4 | Per-subject ovals, persistent colours, per-subject trails | not started |
| 3.5 | `n_subjects`, `separation_m` audit columns | not started |

**3.3 is blocking.** The P0-6 gate keeps only clusters within 0.90 m of a
single track hint, so it will actively delete the second subject that 3.1/3.2
now retain. Until it is per-track, multi-subject support is inert end-to-end —
the clusters exist in `AccumResult` but the cloud reaching the accumulator has
already been filtered to one subject.

| File | MD5 |
|---|---|
| `processing/accumulate.py` | `a595a960cf27c47815715399f5786a59` |

---

## Appendix R — Stage 3 Part 2: Multi-Track Gate and Observables (2026-08-03)

### 3.3 — the P0-6 gate is now multi-track (was blocking)

The gate kept only clusters within `subject_gate_radius_m` of a **single** hint,
so it would have deleted the second subject that 3.1/3.2 retain — the clusters
would exist in `AccumResult` while the cloud reaching the accumulator had
already been filtered to one person. Multi-subject support would have been inert
end-to-end.

`track_hint` now accepts a **list** of positions and keeps a cluster if it is
within radius of **any** track. A scalar `(x, y)` is still accepted.

| test | single-track | multi-track |
|---|---|---|
| subject A | KEEP | KEEP |
| **subject B** | **reject** | **KEEP** |
| fence +3 m | reject | reject |
| car −3 m | reject | reject |
| wall +2.2 m | reject | reject |

Contamination rejection is unchanged; only the deletion of the second subject
is fixed. Backward compatibility, the stale-track bypass and the bootstrap
(`hint=None`) path all still pass.

`AccumResult.track_hints` carries one entry per **confirmed** track (`age >= 2`),
each with the same EMA-lag correction as `predicted_x/y` — without it the hints
would trail ~2.3 frames and re-open the 34.6% bypass rate found in Appendix I.
Verified: two subjects → 2 hints, one subject → 1 hint.

### 3.5 — observables

Five columns, `frames.csv` now 43 columns, AST-verified unique:

| column | meaning |
|---|---|
| `n_subjects` | confirmed tracks this frame (`age >= 2`) |
| `n_clusters_kept` | all DBSCAN clusters retained |
| `separation_m` | distance between the two largest subjects |
| `track_ids` | e.g. `0\|1` — exposes identity churn |
| `compensated` | 0 = suppressed (multi-subject), 1 = applied |

`separation_m` is the quantity that answers the stakeholder question directly:
falling → converging, rising → separating. `compensated` shows how often the
Appendix Q mitigation engages.

### Not done — 3.4 viewer rendering

`streaming.py` passes the hint list but still draws **one** oval from the
primary cluster. Per-subject ovals, persistent per-id colours and per-subject
trails remain outstanding. The data is now available to the viewer; only the
drawing is missing.

### Regression

Single-subject path verified unchanged end-to-end: `cluster_found`, `n_pts`,
`rx`, `subjects=1`, `primary_idx=0`, `compensated=True`, one track hint,
subject-frame and gait features all intact.

### Next

Re-audit `outdoor_long`. Per Appendix Q its previous metrics were produced with
single-subject compensation applied to a two-subject scene, so `rx = 0.257 m`,
`rx_std = 0.098 m` and `wide_cluster_rej = 182` are suspect. The new columns
make the question answerable: if `n_subjects = 2` for a substantial fraction of
frames and `separation_m` tracks the observed together/apart pattern, the
multi-subject path works. If `track_ids` churns, association needs tightening.

| File | MD5 |
|---|---|
| `processing/accumulate.py` | `cae2d6848adf0797e7bea08bbbfee842` |
| `radar_processing.py` | `7f11a0fa8626c72e104ee3c59e03267e` |
| `streaming.py` | `a1d6942288d2660df06c0d69704c0bab` |
| `diag_pipeline_audit.py` | `a44ca9963f763277f71e9d006f8935e7` |
| `reaudit_all.ps1` | `9a500c645dd594d937c91f92b432ec48` |

---

## Appendix S — outdoor_long Re-audit: Stage 3 Works, But Two Subjects Are Rarely Seen (2026-08-04)

### Confirmed improvements

| metric | before Stage 3 | after | change |
|---|---|---|---|
| `wide_cluster_rej` | 182 | **22** | **−88%** |
| `rx` REJECTED max | 2.087 m | **0.832 m** | **−60%** |
| `rx` kept max | 0.633 m | 0.531 m | −16% |
| `comp_residual_x` median | 0.439 m | 0.386 m | −12% |
| `comp_step_x` p90 | 1.807 m | 1.535 m | −15% |
| cluster ÷ has-cluster | 17.4 | 20.2 | +16% |

The headline is `rx` REJECTED max falling from 2.087 m to 0.832 m. Appendix D
recorded a 4.17 m cluster span that no single body could produce; it is gone.
`comp_residual_x` at 0.386 m is now close to the 0.45 m body width. **The
Appendix Q compensation defect was real and the mitigation works.**

### But `n_subjects > 1` in only 22 of 1447 frames (1.5%)

For a 6-minute session recorded with **two** subjects. The multi-subject path
is essentially never engaging on the one dataset that needs it.

### An ordering bug found while checking this

`compensated` shows 1167/1447, i.e. **280 frames uncompensated**, while only
**22** report `n_subjects > 1`. Compensation is suppressed only when
`_multi_subject` is true, so those should match.

Traced in `_build_result`:

```
offset  233 : if self._multi_subject: compensated = False
offset 1403 : merged = concatenate(shifted frames)     <- uses `compensated`
offset 1901 : cluster = self._cluster(merged)          <- SETS _multi_subject
```

Each frame decides compensation from the **previous** frame's subject count,
then updates the flag. The audit samples `n_subjects` *after* `_cluster` ran, so
it reads the current count while `compensated` reflects the previous one.

**The lag is not trivially fixable — the dependency is circular:** compensating
needs the subject count → counting needs a cluster → clustering needs the merged
cloud → merging needs the compensation decision. Options are (a) accept one
frame of lag, (b) cluster the uncompensated cloud first, doubling DBSCAN cost,
or (c) per-subject accumulation, which removes the circularity and is the
principled fix already flagged in Appendix Q.

(a) is defensible but must be **reported honestly** rather than silently
producing a 22-vs-280 discrepancy. `AccumResult.multi_used` now records the flag
actually used for each frame's decision, and the audit logs it.

### Why so few multi-subject frames — two candidates

With 18.8 accumulated points split between two subjects, each would hold ~9.4 —
well above `min_samples = 3`. At the observed 2.601 m median separation they are
3× `eps` apart, so DBSCAN would separate them trivially. **Both subjects should
cluster.** They do not, so the accumulated cloud probably contains only one at a
time.

**(1) Sparse detection.** 1.99 points/frame is barely one per subject. CFAR
keeps the strongest returns, which will usually come from whichever subject is
nearer or better-aspected. Fix would be upstream — CFAR sensitivity, not
clustering.

**(2) Subject-gate lock-in.** The gate keeps clusters near *any* track, but
tracks derive from the accumulator's clusters. With one subject tracked,
`track_hints` has one entry, the gate rejects the second subject, so it never
forms a cluster and never becomes a track. Circular. `sg_rej = 475` is
consistent.

### Distinguishing experiment — added `--no-subject-gate`

```powershell
.\reaudit_all.ps1 -Sessions outdoor_long        # baseline, already have it
python diag_pipeline_audit.py --folder <outdoor frames> --cfg <cfg> `
    --temporal-accum --accum-window 16 --subject-frame --gait-features `
    --no-subject-gate --out-dir verify\outdoor_nogate
```

| outcome | cause | fix |
|---|---|---|
| `n_subjects` rises substantially | gate lock-in | seed tracks from the ungated cloud, or relax the gate until a track confirms |
| `n_subjects` stays ~1.5% | sparse detection | upstream CFAR sensitivity; Stage 3 is correct but cannot help |

The new `n_raw_clusters` column settles a sub-question: if raw clusters are
routinely >1 while `n_subjects` stays 1, tracks are forming and dying before
`age >= 2` confirmation, making the association/confirmation logic the
bottleneck rather than either cause above.

### Also unresolved

`sg_bypass = 367/1286 (28.5%)` remains high, essentially unchanged from the
Appendix I figure. Multi-track hints did not reduce it, which is itself weak
evidence for cause (1) — if the second subject were present and merely gated
out, supplying its position should have cut bypasses.

| File | MD5 |
|---|---|
| `processing/accumulate.py` | `7058ce75b5c2e0cc7a1ef224a052f2fc` |
| `diag_pipeline_audit.py` | `5292cbcf89723b951c98a8304b10d395` |
| `reaudit_all.ps1` | `7f4f86dcbdf2bf560a2a1062cbf16688` |

---

## Appendix T — Stage 3.6: Two-Tier Subject Gate (2026-08-04)

### The experiment settled it — both causes were real

`--no-subject-gate` on outdoor_long, 1447 frames:

| metric | gate ON | gate OFF | change |
|---|---|---|---|
| `n_subjects` > 1 | 22 (1.5%) | **115 (7.9%)** | **5.2× more** |
| `n_subjects` max | 2 | 3 | |
| `n_raw_clusters` > 1 | — | 144 | |
| avg pts/frame | 1.99 | 2.37 | +19% |
| **`wide_cluster_rej`** | **22** | **169** | **7.7× worse** |
| **`rx` REJECTED max** | **0.832 m** | **2.087 m** | back to pre-P0-6 |
| `comp_residual_x` med | 0.386 m | 0.534 m | +38% worse |

**Gate lock-in confirmed and dominant** — removing the gate raised
multi-subject frames 5.2×. The gate *was* filtering out the second subject
before it could form a track, exactly the circular failure predicted.

**Sparse detection is also real** — even ungated, only 7.9% of frames show two
subjects across a 6-minute two-person session.

**But the gate cannot simply be disabled**: every contamination metric regressed
to its pre-P0-6 value, including `rx` REJECTED max returning to exactly 2.087 m
— the 4.17 m cluster span no single body can produce.

### The discriminator in the data

| population | distance from tracked subject |
|---|---|
| second **person** | 1.085 – 2.99 m (median 2.859) |
| **contamination** | `comp_residual_x` to 6.633 m; "separation" to 11.548 m |

Cleanly separated at ~3 m. The existing 0.90 m radius (body + one frame of
motion) is sized for **tracking** an established subject, not for **admitting**
a new one — a second person 2.86 m away can never get in.

### Implementation

```python
# Tier 1 - tracking: close to an existing track
if best_d2 <= r2:            keep
# Tier 2 - admit: far enough to be a DIFFERENT subject, near enough to be
#                 in the same scene, substantial enough to be a body
elif best_d2 <= admit_r2 and len(c[1]) >= admit_min_pts:   keep
else:                        reject
```

```python
subject_gate_radius_m  = 0.90   # tier 1, unchanged
subject_admit_radius_m = 3.00   # tier 2
subject_admit_min_pts  = 1
```

**`admit_min_pts` defaulted to 1, not 2.** outdoor_long averages 4335 RD
clusters against 3045 surviving cloud points — **0.70 az peaks per range
cluster**. Requiring 2 would reject most legitimate second-subject clusters and
make the admit tier inert. The parameter stays configurable.

All 7 logic cases pass against measured distances: tracked subject → tier 1;
second person at 1.09 / 2.86 / 2.96 m → tier 2; contamination at 6.6 / 11.5 m →
rejected; zero-peak speck → rejected.

### The trade-off, stated plainly

The admit tier **cannot distinguish a second person from contamination at the
same distance**. Same-range grating lobes at 2.50 m and a wall at 2.04 m now
fall inside the admit radius, where the single-tier gate rejected them.

It relies on two existing defences: the cross-cluster coherence gate (which runs
*before* this point and removes same-range grating lobes) and the `age >= 2`
confirmation, which discards transient admissions before they become tracks.

### Risk I cannot rule out from current data

`separation_m` reached **11.548 m** with the gate off. If some of those
"subjects" were contamination, the 115-frame count is itself inflated and the
real gain will be smaller than 22 → 115 implies.

**The re-run distinguishes this directly:** if `n_subjects` lands well below 115
*and* `separation_m` max drops toward ~3 m, the admit radius is correctly
excluding contamination the fully-open gate admitted.

**Rollback criterion:** if `wide_cluster_rej` climbs back toward 169 or
`rx` REJECTED max toward 2.087 m, the admit radius is too wide — reduce toward
~2.0 m, still above the 1.085 m minimum measured separation.

| File | MD5 |
|---|---|
| `radar_config.py` | `343e0a5329b6ed3c6d8dbdfa2722e950` |
| `radar_processing.py` | `123526c6aa95f053684e9d230edad19c` |

---

## Appendix U — Two-Tier Gate Result: Sparsity Is the Binding Constraint (2026-08-17)

### Three-way comparison, outdoor_long

| metric | 1-tier ON | gate OFF | **2-tier** | |
|---|---|---|---|---|
| `n_subjects` > 1 | 22 (1.5%) | 115 (7.9%) | **29 (2.0%)** | modest gain |
| `separation_m` median | 2.601 | 2.859 | 2.003 | |
| **`separation_m` MAX** | — | **11.548** | **3.229** | contamination excluded |
| **`sg_bypass`** | **367 (28.5%)** | 0 | **48 (3.7%)** | **big win** |
| `sg_rej` | 475 | 0 | 327 | |
| **`comp_step_x` p90** | 1.535 | 1.595 | **0.844** | **big win** |
| `comp_step_x` median | — | 0.203 | **0.100** | |
| `comp_residual_x` med | 0.386 | 0.534 | **0.367** | best of all three |
| `wide_cluster_rej` | 22 | 169 | **178** | rollback trigger |
| `rx` REJECTED max | 0.832 | 2.087 | 1.741 | |

### Prediction confirmed

I stated: *"if `n_subjects` lands well below 115 **and** `separation_m` max
drops toward ~3 m, the admit radius is correctly excluding contamination."*
Both happened — 29 frames, max 3.229 m. **Most of the 115 ungated "subjects"
were contamination.**

### Unpredicted win — `sg_bypass` 28.5% → 3.7%

Clusters that previously fell outside the 0.90 m radius triggered a **full
bypass** (frame passed ungated). They now land inside the 3.0 m admit radius, so
the gate stays **active on 96.3% of frames instead of 71.5%**. That also
explains `comp_step_x` p90 collapsing 1.535 → 0.844 and `comp_residual_x`
reaching its best recorded value, 0.367 m against a 0.45 m body width.

This resolves the residual bypass rate left open in Appendix I.

### The rollback trigger, re-examined — and not acted on

`wide_cluster_rej` reached 178, above my stated threshold. On inspection the
**criterion itself was wrong**.

The single-tier figure of 22 was achieved by *discarding the second subject*:
only clusters within 0.90 m of one track survived, so the merged cloud was tight
by construction. A low `wide_cluster_rej` there was a symptom of over-filtering,
not of quality.

With the second subject admitted, two people closer than `eps = 0.80 m` merge
into one DBSCAN cluster whose `rx` legitimately exceeds
`max_cluster_radius = 0.65 m`. **Rejecting that as a single body cluster is
correct — it is not one body.**

Crucially, the wide-rejection path returns `subjects=subs, primary_idx=...`, so
**multi-subject tracking is not lost** on those frames; only `cluster_pts` is
zeroed, costing single-body Phase 4/5 features.

| config | frames losing body-shape output |
|---|---|
| 1-tier | 22 / 1286 = 1.7% |
| 2-tier | 178 / 1286 = 13.8% |

The trade is +12% of frames losing Phase 4/5 output for +7 multi-subject frames.
Poor for a single-subject session; defensible for this one. **`max_cluster_radius`
should probably be relaxed when multiple confirmed tracks exist** — a wide
cluster is expected then — but that needs its own validation and is not
implemented.

### The decisive finding

| gate configuration | `n_subjects` > 1 |
|---|---|
| single-tier | 22 / 1447 (1.5%) |
| fully OFF | 115 / 1447 (7.9%) — mostly contamination |
| **two-tier (tuned)** | **29 / 1447 (2.0%)** |

**With the gate optimally tuned, a 6-minute two-person session resolves two
subjects in 2% of frames.**

Cloud density is 2.11 pts/frame. The accumulator holds 19.1 points — in
principle enough for two separable bodies — but they are not *split* between the
subjects, because CFAR keeps only the strongest returns and those come from
whichever subject is nearer or better-aspected.

**Multi-subject perception is limited by detection sparsity, not by clustering
or gating.** Stage 3's logic is correct and complete; it cannot manufacture
points CFAR never produced.

### Consequence for Stage 3.4

Per-subject ovals, colours and trails would render **one** oval on 98% of
frames. Building 3.4 now cannot answer the stakeholder question, because the
pipeline does not resolve two subjects often enough for the rendering to have
anything to show. **3.4 is deferred, not cancelled** — it becomes worthwhile
only if detection density improves.

| File | MD5 |
|---|---|
| `radar_config.py` | `343e0a5329b6ed3c6d8dbdfa2722e950` |
| `radar_processing.py` | `123526c6aa95f053684e9d230edad19c` |

---

## Appendix V — Stage 4: Algorithm Corrections (2026-08-17)

### 4.2 / P0-3 — adaptive limb classification

**Two failed attempts before the working one.** Recording both, because the
second looked like a fix and was not.

**Attempt 1 — relative offset (fixed 0.35 m/s).** Replacing
`|dop| >= 0.30` with `|dop - dop_centroid| >= 0.35` reasoned correctly that the
question is *"does this scatterer move differently from the torso?"*, not
*"is it moving fast?"*. But tested on the A_S01 condition it **failed in the
mirror direction**:

| mode | limb_frac | std | cadence |
|---|---|---|---|
| absolute 0.30 | **1.0000** | 0.00000 | **NaN** — reproduces P0-3 |
| relative 0.35 | **0.0109** | 0.02572 | 0.33 Hz (2.0 expected) |

Both saturated. Any **fixed** threshold fails, because the limb velocity
distribution's width varies with walking speed and range: too large and
`limb_frac → 0`, too small and `limb_frac → 1`. Swapping one constant for
another was not a fix.

**Attempt 2 — adaptive (shipped).**

```
scale_t  = EMA( median |dop - dop_centroid| ),  alpha = 0.15
offset_t = dop_limb_k * scale_t                 k = 1.0
is_limb  = |dop - dop_centroid| >= offset_t
```

The reference is **smoothed across frames** while the instantaneous deviation
oscillates with the gait cycle, so `limb_frac` sits near 0.5 and swings with
stance/swing — the variation the autocorrelation consumes. `alpha = 0.15`
(~6-frame memory) is deliberately slower than the gait cycle; a faster EMA would
track the cycle and cancel the very oscillation being measured. The scale is
updated **after** classification so each frame is judged against history, not
itself.

| condition | limb_frac | std | verdict |
|---|---|---|---|
| A_S01-like v=0.50 amp=0.30 | 0.528 | 0.0380 | unsaturated |
| slow walk v=0.30 amp=0.20 | 0.521 | 0.0476 | unsaturated |
| fast walk v=0.80 amp=0.55 | 0.517 | 0.0757 | unsaturated |
| lateral v=0.05 amp=0.15 | 0.522 | 0.0392 | unsaturated |

**P0-3 (saturation) is fixed** at every speed, with no per-session tuning.

### A separate finding — `cadence_hz` is the STEP rate, not the stride rate

`limb_frac` peaks once per **leg** swing, i.e. **twice per gait cycle**. A 1.0 Hz
stride produces a 2.0 Hz `limb_frac` oscillation, and the estimator correctly
reports 2.0.

```
stride_hz = cadence_hz / 2
```

The **name is misleading, not the algorithm**. This matters directly for
validation: stopwatch ground truth must be compared against the **step** rate.
Any earlier interpretation of `cadence_hz` as a stride rate was wrong by 2×.

**Cadence accuracy remains unvalidated.** It was correct in 2 of 4 synthetic
conditions (A_S01-like 2.0 ✓, lateral 2.0 ✓; slow walk 0.8 vs 1.6, fast walk 2.0
vs 2.6). At 4 fps over 64 frames the autocorrelation resolution is coarse.
**Stage 4.3 stays blocked on ground-truth walking speeds.**

### 4.4 — Doppler direction check replaced

The old test split at the session midpoint and required
`median(first half) > 0` and `median(second half) < 0` — valid only for a single
out-and-back. Real sessions contain 3–4 cycles, so both halves hold mixed
directions and only 1 of 6 A/D sessions "passed" despite demonstrably correct
Doppler (A_S01 spans −1.951 to +1.717 m/s).

Replaced with a **zero-crossing count** on `dop_centroid`, with a 0.15 m/s
deadband to suppress chatter where the sign of a near-zero centroid is noise.

An out-and-back produces **one** crossing, so *n* cycles give **2n − 1**
(my first threshold of `>= 2` was wrong and failed the single-cycle case):

| scenario | old | new | crossings | expected 2n−1 |
|---|---|---|---|---|
| 1 out-and-back | PASS | **PASS** | 1 | 1 |
| 3 cycles (A_S01) | PASS | **PASS** | 5 | 5 |
| 4 cycles | **FAIL** | **PASS** | 7 | 7 |
| single traverse | FAIL | FAIL | 0 | n/a |

The old test passed only the single-cycle case — precisely the artefact that
failed five real sessions. New columns: `n_dir_cross`, `frac_pos_dop`.

### Status

| item | state |
|---|---|
| 4.2 adaptive `dop_limb_thr` | done — P0-3 saturation fixed |
| 4.3 cadence rebuild | **blocked** — needs stopwatch ground truth |
| 4.4 Doppler direction check | done |
| 4.5 elevation calibration offset | not started |

Legacy `absolute` and `relative` modes remain selectable via `dop_limb_mode`
for comparison against historical results.

| File | MD5 |
|---|---|
| `processing/accumulate.py` | `c00df879b7c6b86d9a369daa15d7e999` |
| `radar_config.py` | `01dd965cea637a9a2440691c535cc3a8` |
| `analyse_sessions.py` | `4868ae3ac5c32fc36ab68c6a063e96d7` |

---

## Appendix W — Stage 4 Verified on Real Data; Sparsity Confirmed as the Limit (2026-08-19)

### First trustworthy session analysis in the project

Two plumbing bugs had to be fixed before any of this could be read:

1. **Path mismatch.** `reaudit_all.ps1` wrote to `.../frames/<session>/` while
   `analyse_sessions.py` defaulted to `.../logs/`. They had **never** pointed at
   the same place, so every report in this project was built from stale CSVs.
   That is why `limb%` was byte-identical across three consecutive runs while
   the re-audit numbers changed underneath it. Fixed; the report now prints
   `Source : <abs path>`.
2. **`NameError` on `root`**, and the audit **never passed `dop_limb_mode`** to
   `TemporalAccumulator` — it relied on dataclass defaults, so changing the mode
   in `radar_config.py` had no effect. A config that lied about what ran.

### 4.2 — split verdict

| session | before | k=1.0 | k=1.75 |
|---|---|---|---|
| A_S01 | 100.0% | 49.0% | 27.5% |
| C_S03 | 100.0% | 54.2% | 32.1% |
| D_S03 | 100.0% | 50.0% | 29.6% |

**k=1.0 was itself a saturation.** A threshold set *at* the median deviation has
~50% of points above it **by definition**. Measured: all 12 sessions 46.3–57.1%,
scenario means A 53.1% / B 55.0% / C 50.6% / D 50.0%. The statistic measured
nothing. Corrected to **k = 1.75**, moving the threshold into the tail.

**P0-3 is fixed** — `limb_frac` has frame-to-frame variance again, which is what
the cadence autocorrelation consumes.

**But my discrimination prediction failed.** I predicted A and D would read
~16.5% above B. Actual: **A−B = 3.0%, D−B = 4.8%**, with overlapping ranges
(B_S03 29.6% > A_S01 27.5%). I had also stated the falsification condition:
*"if all four scenarios still cluster within a few percent, the shape
discrimination isn't there."* They span 26.1–30.9%. **By my own criterion,
`limb%` does not work as a session-level scenario discriminator.**

My simulation modelled radial walking as strongly bimodal (torso cluster + limbs
at ±0.55 m/s). Real data has 1.8–2.0 pts/frame — too sparse to resolve bimodal
structure, and 16-frame accumulation mixes gait phases. **Detection sparsity is
the binding constraint**, the same conclusion reached independently for
multi-subject perception in Appendix U.

### 4.4 — works, but broke another check

Direction validation went from 1/6 to **4 of 4 sessions with data**
(A_S01 +1.056/−0.986, A_S02 +0.746/−0.888, D_S01 +0.792/−0.968,
D_S03 +0.526/−0.670).

**Regression I introduced:** 4.4 redefined `dop_fwd` as the median of the
*positive tail* after a 0.15 m/s deadband, so `|dop_fwd| >= 0.15` by
construction. The Scenario B check still tested `max|dop_fwd| < 0.20` — **it
could never pass**. One of the six Phase 7 failures was an artefact of my own
edit. Corrected to per-point mean Doppler: B_S01 −0.061, B_S02 +0.011,
B_S03 −0.006 → **passes at 0.061**.

### Phase 7 checklist — two more artefacts removed

`A_S03` and `D_S02` have **zero detections**. The checklist took a MIN across all
sessions, so two dead recordings vetoed ten good ones — that alone produced both
*"Min detection rate 0.0%"* and *"Doppler sign 4/6"*.

Zero-detection sessions are now excluded and **named** in the report. **No
threshold was relaxed** — the sessions are excluded because there is nothing to
evaluate.

**Centroid stability deliberately left failing.** The target of 0 dates from when
the accumulator was frozen (P0-5): a frozen centroid cannot jump, so 0 was
guaranteed and meaningless. 82 jumps is the first real stability measurement in
this project. The check now reports the jump **rate** so a target can be derived
from evidence — but the target has not been moved to make it pass.

### Honest scorecard

| check | verdict |
|---|---|
| Scenario B near-zero Doppler | ✓ passes (0.061) |
| Min detection rate | artefact — resolved by excluding empty sessions |
| Doppler sign | artefact — 4/4 on sessions with data |
| Centroid stability (82 jumps) | **real**, target needs re-deriving |
| M5 range-independence (max r=0.652) | **real** |
| Inter-subject `dx_std` (0.0037 m) | **real, but n=2** — S03 has no valid Scenario A |

### What this establishes

Three independent lines now converge on the same conclusion: **the point cloud
at 1.8–2.4 pts/frame is the limiting factor**, not the clustering, gating or
gait algorithms.

- multi-subject resolution: 2.0% of frames even with a tuned gate (Appendix U)
- `limb%` scenario discrimination: 3–5% gap against a predicted 16.5%
- inter-subject `dx_std`: 0.0037 m, below the stated 0.005 m detectability

Further algorithm work on this dataset has low expected value. The productive
directions are **CFAR sensitivity** (more points per frame) or **re-collection**
with the two empty sessions replaced and S03's Scenario A recovered.

| File | MD5 |
|---|---|
| `analyse_sessions.py` | `052689806f92fe39e58188f8c8132b48` |
| `radar_config.py` | `cdd74cf6bda084d74d7b68732ff0deed` |

---

## Appendix X — GPU Status: Enabled but Starved by Transfers (2026-08-21)

Two direct questions, answered from code state rather than memory.

### Q1 — Is the pipeline running on GPU?  **Yes.**

P0-7 is fixed and confirmed on the target machine: `GPU_AVAILABLE: True`,
`import processing.gpu_accel: OK`, RTX 3080 Ti visible. The import binds all
eight GPU implementations — range FFT, doppler FFT, azimuth FFT, power reduce,
elevation FFT, CFAR, focus mask, RA collapse.

**One caveat:** `cfar_2d_gpu` returns `_cfar_2d_cpu` when
`cfg.cfar_method == 'os'`. The config uses OS-CFAR, so **CFAR runs on CPU on
both paths** — by design, and the reason GPU and CPU produced bit-identical
CFAR output in the parity test. Not a defect, but not accelerated either.

### Q2 — Are the GPU↔CPU copies handled properly?  **No.**

**Audit item L-2 was identified, written up, and never implemented.** I went
from documenting it to Stage 3/4 without doing the work.

Still present in `gpu_accel.py`:

| | count |
|---|---|
| `cp.asnumpy()` — device→host, **blocking** | **11** |
| `cp.asarray()` — host→device | 24 |

Per stage: `range_fft_gpu` 1, `doppler_fft_gpu` 1, `power_db_reduce_gpu` 1,
`az_fft_gpu` 1, `cfar_2d_gpu` 2, `ra_focus_mask_gpu` 1,
`collapse_ra_from_fft_gpu` 1, `elevation_fft_gpu` 1.

Every stage follows `cp.asarray(host) → kernel → cp.asnumpy(device)`. Data goes
**GPU → CPU → GPU between every stage** and is never resident on the device.
Each `cp.asnumpy()` forces a full synchronisation, so kernel launches cannot
overlap with transfers and the GPU idles between stages.

### The measured evidence

| configuration | proc_ms | backend |
|---|---|---|
| full-cube az FFT, GPU import broken | 182–190 | CPU |
| focused az FFT, GPU import broken | 110–116 | CPU |
| **focused az FFT, GPU import fixed** | **110–143** | **GPU** |

**Enabling eight GPU stages changed frame time by essentially nothing, and the
upper bound got worse.** Yet the isolated azimuth FFT measures 40.0 ms CPU vs
0.6 ms GPU on this machine (66×). That ~39 ms is not reaching the pipeline.

Transfer volume per frame, summing the stage outputs, is ~19 MB each way —
~38 MB round trip, roughly **6 ms** of pure PCIe at ~6 GB/s. That accounts for
only about a sixth of the gap. **The remainder is synchronisation stalls,
kernel launch latency and WDDM scheduling, which cannot be derived and must be
measured.**

### `profile_gpu_transfers.py` added

Measures, per stage on real frame data: kernel time with data already resident,
the full `asarray → kernel → asnumpy` round trip, and the difference — which is
exactly what L-2 would recover. Also times a bare round trip with no compute, to
separate bandwidth from synchronisation.

### Honest position

The **correctness** work is done and verified. The **latency** work is not:
Stage 2.2 landed, but L-2 — the larger of the two latency items — is still open,
and the P0-7 fix that should have delivered a 66× azimuth FFT speedup delivered
approximately zero at the pipeline level because of it.

Frame time of 110–143 ms is still comfortably inside the 250 ms budget at 4 fps,
so this is not blocking the demo. It is blocking any claim that the pipeline is
GPU-accelerated in a meaningful sense.

| File | MD5 |
|---|---|
| `profile_gpu_transfers.py` | `647dd139992c688c0444b067652cce1d` |
