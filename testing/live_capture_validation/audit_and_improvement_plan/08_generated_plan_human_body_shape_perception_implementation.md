# Implementation Plan — Toward Human-Body-Shape Radar Perception

**Audience:** autonomous implementer agents (Claude Opus 4.8) running on the
target Windows machine with the AWR2243-2X cascade radar, GPU, and the
400-frame outdoor dataset in `capture/frames/`.

**Status of this document:** forward-looking engineering plan. It was written
from a code audit (verified 2026-06-13) and is the authoritative roadmap. The
README describes *current* behaviour; this file describes *what to build next*.

---

## 0. How to use this plan

1. **Work phase by phase, in order.** Each phase has an explicit *Goal*,
   *Files*, *Steps*, *New config*, *Diagnostics*, *Acceptance criteria*,
   *Risks/rollback*, and *Do NOT do yet*. Do not start a phase until the
   previous phase's acceptance criteria pass.
2. **One phase = one reviewable change set.** Keep edits minimal and
   reversible. Add new config fields *disabled by default* (or behind a flag)
   unless the phase says otherwise, so existing behaviour is preserved.
3. **Diagnostics before algorithm changes.** Phase 0 must be completed and its
   CSVs collected before tuning any detection parameter.
4. **Evidence source = the 400-frame outdoor sequence** in `capture/frames/`
   (`frame_000000.bin` … `frame_000399.bin`), one moving human subject walking
   forward/backward. Never judge success from a single frame.
5. **Update memory + this file** as you complete phases: append a short
   "DONE — <phase> — <date> — <result>" line to the changelog at the bottom.

### Hard constraints (do not violate)

- Do **not** revisit capture instability, compression, firmware loading,
  DCA1000 transport, or warm-up — those are validated and frozen.
- Do **not** propose a broad rewrite. Extend `process_frame()`; do not replace it.
- Do **not** make CFAR re-tuning the first move. Phase 0 diagnostics decide
  whether any parameter is actually the bottleneck.
- Do **not** break the live/replay viewers or the offline CLI.
- Preserve the GPU→CPU silent-fallback contract in `processing/gpu_accel.py`.

---

## 1. Verified current state (code-grounded facts)

These are confirmed from the code; build on them, don't re-derive them.

- **Pipeline is per-frame and stateless.** `process_frame()` in
  `processing/radar_processing.py` (orchestrator starts ~L902) does:
  calibration → range FFT → Doppler FFT (+MTI, +zero-DC notch) → non-coherent
  integration RD map (`_power_db_reduce`, ~L78) → **RD-domain CFAR**
  (`cfar_2d`, ~L645) → **cross-channel consistency fusion**
  (`_cross_channel_consistency_mask`, ~L130) → RA map → **RD-confirmed
  multi-peak azimuth** (`_az_multi_peak`, ~L266; cluster loop ~L1140) →
  elevation FFT (+ shared median el bin) → arrDREA → **xyz extraction**
  (`extract_xyz`, ~L799).
- **There is NO RA-CFAR, NO RD-confirmation gate, NO strict-object filter in
  the executed path.** `_restrict_ra_candidates` (~L362) and
  `_prune_ra_sidelobes` (~L190) are defined but **never called**.
  `strict_object_filtering`, `require_rd_confirmation`, `ra_sidelobe_db`,
  `filter_high_moving`, `moving_objects_only` are config fields with **no
  consumer**.
- **Detection is sparse.** ~2–4 cloud points/frame typical; many frames yield
  `cloud:0`. Evidence:
  `debug_context/stage3-processing-pipeline-improvements/proposed_modifications_testing_logs/diag_xyz_output.txt`
  (17 frames → 62 points).
- **`x` spread is dominated by ghosts/grating, not body width.** Same log:
  `x range [-3.67, +5.40] m`, `std=1.89 m`. The `diag_xyz.py` "body-width ✓"
  verdict (threshold 0.30 m) is therefore unreliable.
- **`z` (elevation) is unreliable:** 16 elevation VA → ~19 cm/bin at 3 m;
  `z std≈1.08 m`; unknown radar-height offset. (Acknowledged in
  `processing/streaming.py` `_build_pointcloud_window` docstring.)
- **Display "accumulation" is naive:** `LiveViewer._update_pointcloud`
  (`processing/streaming.py`, concat ~L853) concatenates the last
  `pointcloud_history_frames` (default 5) *processed* frames with **no
  registration / no motion compensation**, and those frames are
  non-consecutive because ~20 are dropped between processed frames.
- **The `testing/live_outdoor/*` logs and the old README pipeline diagram are
  STALE** (they show RA-CFAR / `8d. RD confirmation`). Ignore them as evidence.
- **Label drift:** `_det_label()` in `processing/radar_plots.py` (~L1193)
  prints `RA-CFAR:N` but N is now `ra_det.sum()` (multi-peak az points).

### Key config defaults (in `processing/radar_config.py`)

| Field | Default | Role |
|---|---|---|
| `cfar_method` | `"os"` | RD CFAR variant |
| `cfar_margin_db` | `10.0` | extra dB above CFAR threshold |
| `cfar_min_power_db` | `12.0` | absolute floor before a cell can survive |
| `consistency_k` | `2` | min RX channels above 99.9-pct floor |
| `rd_range_cluster_bins` | `2` | merge adjacent confirmed range bins |
| `az_multi_peak_en` | `True` | multi-peak az on/off |
| `az_peak_max_n` | `6` | max az peaks per cluster |
| `az_peak_min_prom_db` | `10.0` | az peak prominence floor |
| `az_peak_min_gap_bins` | `6` | min az peak separation |
| `el_shared_across_range_bins` | `True` | one el bin per frame |
| `body_az_half_width_m` | `0.30` | grating-lobe lateral gate |
| `max_az_sin` | `0.866` | ±60° FoV gate |
| `cross_cluster_range_m` | `1.0` | cross-cluster coherence gate |
| `min_abs_doppler_mps` | `0.0` | 0 ⇒ auto 0.5·dop_res |
| `point_cloud_max_points` | `50000` | non-binding cap |

### XYZ schema (do not change without updating all consumers)

`xyz_cloud[i] = [x_m, y_m, z_m, pwr_db, dop_mps, rng_m, az_deg]`, sorted by
power descending. Coordinates: `x = r·cos(el)·sin(az)` (lateral, +right),
`y = r·cos(el)·cos(az)` (forward/range), `z = r·sin(el)` (up, radar-relative).

---

## 2. Target & global success metrics

**Goal:** detect a moving human subject and produce a temporally stable,
physically meaningful point cloud whose shape is increasingly human-body-like
(coherent width/depth, consistent forward/backward motion, temporal
persistence), progressing toward micro-Doppler/gait and later pose descriptors.

**Global metrics (measured over the full 400-frame sequence):**

- **M1 Track continuity:** a single subject track persists across ≥ 80% of the
  frames where the subject is present, with no identity gaps > 3 frames.
- **M2 Motion plausibility:** tracked centroid `y(t)` is smooth and monotonic
  within each forward/backward leg; `|Δy|` between consecutive processed
  frames < 0.6 m (≈ max human speed / frame rate).
- **M3 Ghost rejection:** after clustering/tracking, ≤ 10% of accumulated
  points lie > `body_az_half_width_m + margin` from the track centroid in x.
- **M4 Density:** accumulated (windowed) representation has ≥ 30 points around
  the subject, vs ~2–4/frame raw.
- **M5 Body extent (subject-centric):** normalized lateral spread converges
  toward ~0.3–0.5 m (shoulder scale), not metres.

Each phase below also has local acceptance criteria.

---

## 3. Phase 0 — Observability & evidence base *(do first, no behaviour change)*

**Goal:** make the 400-frame sequence measurable. Produce machine-readable
per-frame, per-stage, and per-point data so every later decision is evidence-led.

**Files:**
- `processing/radar_processing.py` — add optional structured logging in
  `process_frame()` (no algorithm change).
- New: `diag_pipeline_audit.py` (repo root) — batch runner over a folder.
- `processing/radar_plots.py` — fix `_det_label` naming (cosmetic).

**Steps:**
1. **Stage-attribution counters.** In `process_frame()`, the counts already
   exist locally (`rd_det.sum()` before/after consistency; `grating_rej`,
   `fov_rej`, `cc_rej`; cluster count; final cloud len). Aggregate them into a
   per-frame dict and, when `cfg.audit_csv_path` is set, append one CSV row:
   `frame, rd_cfar, after_consistency, n_clusters, az_peaks_raw,
   fov_rej, grating_rej, cc_rej, ra_det, cloud_pts`.
   - Add `audit_csv_path: Optional[str] = None` to `RadarConfig`. Default
     `None` ⇒ feature off ⇒ zero behaviour change.
   - Write the header once if the file does not exist.
2. **Per-point dump.** New `diag_pipeline_audit.py` iterates
   `capture/frames/frame_*.bin` in order, runs `process_frame`, and writes
   `points.csv`: one row per cloud point with `frame, x, y, z, pwr_db,
   dop_mps, rng_m, az_deg`. Also writes `frames.csv`: per-frame centroid
   (`median x/y/z`), point count, and the stage-attribution row from step 1.
   - Reuse the config/calibration setup pattern from `diag_xyz.py`
     (`parse_cfg_file`, `parse_calibration`, `apply_raw_iq_order_override`,
     `read_frame`). Use `cfg.quiet_mode=True`.
   - CLI: `--folder`, `--cfg`, `--out-dir`, `--cfar-margin`.
3. **Fix label drift.** In `processing/radar_plots.py` `_det_label`, rename the
   middle field from `RA-CFAR` to `az-pts` (keep `RD-CFAR` and `cloud`). Update
   any string assertions in tests/logs that depend on it.

**New config:** `audit_csv_path` (default `None`).

**Diagnostics / what to run:**
```powershell
python diag_pipeline_audit.py --folder capture\frames --cfg config\build_shortrange_inf\cascade_shortrange.cfg --out-dir debug_context\stage4_audit
```
Produces `frames.csv`, `points.csv` over all 400 frames.

**Acceptance criteria:**
- `frames.csv` has 400 rows; `points.csv` has one row per emitted point.
- You can answer, from the CSVs alone: (a) how many frames have `cloud:0`,
  (b) which stage drops the most candidates (consistency vs grating vs cc),
  (c) the per-frame centroid trajectory `y(t)` and `x(t)`.
- No change to any detection count vs current behaviour when `audit_csv_path`
  is unset (verify on 5 frames).

**Risks/rollback:** logging only; risk near zero. Rollback = leave
`audit_csv_path=None`.

**Do NOT do yet:** do not change any detection threshold based on a hunch;
collect the CSVs first.

---

## 4. Phase 1 — Per-frame cloud correctness

**Goal:** ensure every emitted point is physically meaningful before
accumulating. Fix the two structural issues the audit identified: (a) the
range-cluster collapse discards body depth; (b) the grating/cross-cluster gates
use a fragile boresight-nearest anchor that can keep a ghost and drop the
subject.

**Files:** `processing/radar_processing.py` (cluster loop ~L1140, gates
~L1228–L1290, `extract_xyz` ~L799), `processing/radar_config.py`.

**Steps:**
1. **Preserve body depth (config-gated).** Today each cluster collapses to one
   representative range bin (`rep`). Add `emit_all_cluster_bins: bool = False`.
   When `True`, emit az peaks for **each confirmed range bin** in the cluster
   (cap at `az_peak_max_n` per bin and a new `cluster_max_points` cap), so a
   30 cm-deep torso spanning ~4–5 bins contributes depth. Keep `False` default
   so existing behaviour is unchanged until validated.
2. **Robust grating/cross-cluster anchor (config-gated).** Add
   `anchor_mode: str = "boresight"` with options `"boresight"` (current) and
   `"power_continuity"`. In `"power_continuity"`, choose the cluster/peak
   anchor by combining peak power with proximity to the **previous frame's
   track centroid** if available (Phase 3 provides it; until then fall back to
   power-rank). This removes the "subject must be at x≈0" assumption.
   - Until Phase 3 exists, `"power_continuity"` = pure power-rank anchor.
3. **Verify Doppler assignment** in `extract_xyz`: confirm the moving-bin
   selection (`min_abs_doppler` auto path) does not zero out a genuinely
   slow tangential subject. Add an assertion-free debug counter (frames where
   all points got `dop=0`) to `frames.csv`.

**New config:** `emit_all_cluster_bins` (False), `cluster_max_points` (e.g. 8),
`anchor_mode` ("boresight").

**Diagnostics:** rerun `diag_pipeline_audit.py` with the new flags enabled;
compare `frames.csv`/`points.csv` against the Phase 0 baseline.

**Acceptance criteria:**
- With `emit_all_cluster_bins=True`: median per-frame `y_span` for
  detected frames rises toward ~0.2–0.35 m (real torso depth) **without**
  blowing up `x` spread.
- With `anchor_mode="power_continuity"`: number of frames whose centroid `x`
  jumps > 1 m between consecutive detected frames drops vs baseline.
- No regression in frame count with detections.

**Risks/rollback:** medium. Emitting all cluster bins can readmit clutter;
mitigate with `cluster_max_points` and the Phase 2/3 gates. Rollback = set new
flags to defaults.

**Do NOT do yet:** no tracking, no body model, no CFAR tuning.

---

## 5. Phase 2 — Temporal accumulation over the 400-frame sequence

**Goal:** build a denser representation of the moving subject by accumulating
points over a short sliding window **with motion compensation**, replacing the
naive un-registered display concat.

**Files:** new `processing/accumulate.py`; integrate into
`processing/streaming.py` (`_update_pointcloud`) and `diag_pipeline_audit.py`.

**Steps:**
1. **New module `TemporalAccumulator`** (stateful, lives outside
   `process_frame` to keep it stateless):
   - Ring buffer of the last `N` frames' clouds (`N = accum_window`, default 8).
   - Maintain a running **centroid estimate** (median x,y of recent clouds).
   - **Motion compensation:** before merging, translate each frame's points by
     the centroid delta so the subject's points overlap instead of smearing
     along the walk path. (Translation-only is sufficient for a walking
     subject; do not attempt rotation.)
   - Output: a merged `[M,7]` cloud plus the current centroid + velocity.
2. **Wire into the live/replay viewer.** Replace the raw concat in
   `LiveViewer._update_pointcloud` with the accumulator output when
   `cfg.temporal_accum_en` is True. Keep the existing 5-frame concat as the
   fallback.
3. **Offline accumulation path** in `diag_pipeline_audit.py`: emit
   `accumulated_points.csv` (windowed, motion-compensated) for inspection.

**New config:** `temporal_accum_en` (False), `accum_window` (8),
`accum_max_centroid_jump_m` (0.6, reject frames that violate M2).

**Diagnostics:** plot accumulated point count per window and the centroid
trajectory `y(t)`/`x(t)` from `accumulated_points.csv`.

**Acceptance criteria:**
- M4: windowed accumulation yields ≥ 30 points around the subject in active
  segments.
- Centroid `y(t)` is visibly smoother than per-frame; M2 satisfied within legs.
- Live viewer shows a coherent moving blob, not a smear along the path.

**Risks/rollback:** medium. Over-long windows smear during direction changes;
keep `accum_window` small and reset on large centroid jumps. Rollback =
`temporal_accum_en=False`.

**Do NOT do yet:** multi-target handling; assume exactly one subject.

---

## 6. Phase 3 — Single-subject clustering / track stabilization

**Goal:** associate accumulated points to one subject, reject ghosts/outliers
with a motion model, and feed the track centroid back to Phase 1's anchor.

**Files:** new `processing/tracking.py`; consumed by `accumulate.py` and the
viewers.

**Steps:**
1. **Spatial clustering** on accumulated (x,y) per window: DBSCAN
   (`eps≈body_az_half_width_m`, `min_samples≈3`) or a simple grid-cluster if
   you want to avoid a scikit-learn dependency. Pick the cluster nearest the
   predicted track position; others are ghosts.
2. **Constant-velocity Kalman** (state = [x, y, vx, vy]) on the chosen
   cluster centroid. Gate associations by Mahalanobis distance; coast through
   gaps ≤ 3 frames.
3. **Feed back:** expose `tracker.predicted_centroid` so Phase 1
   `anchor_mode="power_continuity"` uses it (closes the loop on ghost drops).

**New config:** `tracking_en` (False), `track_gate_m` (0.8),
`track_max_coast_frames` (3), DBSCAN params.

**Diagnostics:** overlay track centroid on `points.csv` scatter; compute M1/M3
from the CSVs.

**Acceptance criteria:** M1 (≥80% continuity, no >3-frame gaps), M3 (≤10%
off-track points). Track survives the forward→backward direction change.

**Risks/rollback:** medium. A single bad init can lock onto a wall; add a
re-init rule when the track has no supporting cluster for > coast frames.
Rollback = `tracking_en=False`.

**Do NOT do yet:** multiple simultaneous people; pose.

---

## 7. Phase 4 — Subject-centric coordinate normalization

**Goal:** express points relative to the tracked centroid/torso proxy so body
extent is comparable across range and frames.

**Files:** `processing/tracking.py` (provide centroid), a small transform in
`accumulate.py` or a new `subject_frame()` helper; viewers add a "body-frame"
toggle.

**Steps:**
1. Subtract track centroid from each accumulated point → `(dx, dy, dz)`.
2. Optionally align `dy` to the radial axis (already radial) and keep `dx`
   lateral. Do **not** rotate by heading yet (walking toward/away ⇒ heading is
   ~radial; rotation adds noise).
3. Add a viewer panel showing the body-frame cloud with a fixed ±0.5 m extent.

**New config:** `subject_frame_en` (False).

**Acceptance criteria:** M5 — normalized lateral spread converges toward
~0.3–0.5 m in active segments; spread no longer scales with range.

**Risks/rollback:** low. Rollback = `subject_frame_en=False`.

**Do NOT do yet:** body envelope fitting (Phase 5).

---

## 8. Phase 5 — Human-body envelope visualization

**Goal:** show a rough human-like spatial extent instead of loose points.

**Files:** `processing/streaming.py` viewer (the static reference oval at
`_build_pointcloud_window` becomes a fitted envelope).

**Steps:**
1. Fit a simple envelope to the subject-frame cloud: 2D convex hull or an
   ellipse (PCA) in (dx, dz) for a front view, and (dx, dy) for top-down.
2. Draw it as an overlay; keep raw points visible.
3. Clamp envelope size to plausible human bounds to avoid ghost-driven
   stretching.

**New config:** `body_envelope_en` (False).

**Acceptance criteria:** envelope tracks the subject smoothly and stays within
human bounds (≈ 0.5 m wide, ≈ 1.7 m tall once enough vertical points exist).

**Risks/rollback:** low (display only). Rollback = `body_envelope_en=False`.

**Do NOT do yet:** skeletal pose.

---

## 9. Phase 6 — Micro-Doppler / gait / limb-motion features

**Goal:** use temporal Doppler signatures to separate trunk vs limb motion.

**Files:** new `processing/microdoppler.py`; consumes `RD_mti` slices at the
track range from the tracker.

**Steps:**
1. For the tracked range bin(s), collect the Doppler spectrum each frame and
   build a **Doppler-time spectrogram** (range-gated to the track).
2. Extract simple gait features: torso Doppler (spectral centroid), limb
   spread (bandwidth), cadence (periodicity via autocorrelation).
3. Add a spectrogram panel; the existing X–Doppler panel already hints at
   trunk-vs-limb separation.

**New config:** `microdoppler_en` (False), spectrogram window length.

**Acceptance criteria:** spectrogram shows a periodic limb pattern around a
slowly varying torso line during walking segments.

**Risks/rollback:** low. Requires the subject to move radially for usable
Doppler; tangential walking gives weak signatures (physics).

**Do NOT do yet:** mapping micro-Doppler to joints.

---

## 10. Phase 7 — Pose-like representation (future)

**Goal:** move from a point cloud to pose-like descriptors.

**Preconditions (all must hold):** stable single-subject track (Phase 3),
subject-centric frame (Phase 4), body envelope (Phase 5), and usable
micro-Doppler (Phase 6) over many sequences.

**Steps (research-level, do not start early):** accumulate body-frame clouds +
micro-Doppler into a feature tensor; explore a lightweight learned mapping to
coarse pose descriptors (e.g. torso orientation, limb-swing phase). Treat as a
separate research track with its own data collection.

**Do NOT** attempt before a continuous, ghost-free, body-normalized track and
multi-sequence data exist. A single 400-frame clip is insufficient.

---

## 11. Cross-cutting engineering requirements

- **Config hygiene (do in Phase 0 or 1):** decide, per unwired field
  (`strict_object_filtering`, `require_rd_confirmation`, `ra_sidelobe_db`,
  `filter_high_moving`, `moving_objects_only`), either to *delete* it or *wire*
  it. Do not leave config that implies non-existent behaviour. Update
  `RadarConfig.print_summary` accordingly.
- **GPU/CPU parity test:** add a small script that runs one frame through the
  CPU path (force `gpu_accel.GPU_AVAILABLE=False`) and the GPU path, and
  asserts RD/RA/cloud agree within tolerance. Run once per phase that touches
  numeric stages. Document any divergence.
- **Determinism:** seed any stochastic step (DBSCAN is deterministic; Kalman is
  deterministic). Keep diagnostics reproducible.
- **Backward compatibility:** every new behaviour is behind a default-off
  config flag until its phase's acceptance criteria pass on the 400-frame set.
- **No new disk writes in the live path** unless `--record`; diagnostics write
  only under an explicit `--out-dir`.
- **Tests:** where a `test.py`/unit harness exists, add a minimal regression
  (e.g. cloud count on `frame_000000.bin` unchanged when flags are default).

---

## 12. Phase dependency graph

```
Phase 0 (diagnostics)  ──► Phase 1 (per-frame correctness)
                              │
                              ▼
                        Phase 2 (temporal accumulation)
                              │
                              ▼
                        Phase 3 (clustering/tracking) ──┐ feedback to P1 anchor
                              │                          │
                              ▼                          ▼
                        Phase 4 (subject-centric) ── Phase 6 (micro-Doppler)
                              │
                              ▼
                        Phase 5 (body envelope)
                              │
                              ▼
                        Phase 7 (pose, future / gated)
```

---

## 13. Reference: where to touch what

| Need | Location |
|---|---|
| Add per-frame audit row | `process_frame()` in `processing/radar_processing.py` |
| Cluster collapse / depth | cluster loop ~L1140 in `radar_processing.py` |
| Grating / cross-cluster anchor | gates ~L1228–L1290 in `radar_processing.py` |
| Doppler assignment to points | `extract_xyz` ~L799 in `radar_processing.py` |
| New config flags | `RadarConfig` in `processing/radar_config.py` (+ `print_summary`) |
| Live/replay 3D viewer | `LiveViewer` in `processing/streaming.py` (~L382, `_update_pointcloud` ~L916) |
| Offline CLI flags | `_build_parser`/`_apply` in `processing/main.py` |
| Per-frame reviewer | `diag_xyz.py` (repo root) |
| Detection label | `_det_label` in `processing/radar_plots.py` (~L1193) |
| GPU stage parity | `processing/gpu_accel.py` |

---

## 14. Changelog (implementer agents append here)

- 2026-06-13 — Plan created from code audit. No code changed yet.
<!-- Append: "DONE — Phase N — YYYY-MM-DD — <result + acceptance status>" -->
