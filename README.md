# RoadSafety-CRCL-Windows-for-Flashing

A dedicated project for flashing the Jetson with the required libraries and files to run the cascaded radar from the Jetson ARM system.

**Hardware:** TI AWR2243-2X cascaded radar (2 × AWR2243 + AM273x MSS, 6 TX / 8 RX, 48 virtual channels), captured through a DCA1000.

## Windows build station: firmware source of truth, plus a frozen capture reference

> **What this repository is for.** It holds the **AM273x cascade firmware source** (`firmware/am273x_cascade/`) and the **firmware packages released to the Jetson** (`firmware/releases/`). The TI AM273x SDK, the CCS toolchain and the Node-based boot-image tools are installed on this Windows machine and nowhere else, so new range configurations are built here.
>
> **What runs elsewhere.** Capture, processing, replay and flashing run on the Jetson AGX Orin, in a separate repository.
>
> **What is frozen:** the `capture/` and `processing/` trees, and everything this README describes about running them (from "Project Layout" onward).
> - They are the reference implementation the Jetson version was derived from.
> - They are not maintained, and have **not** received the corrections listed below.
> - Do not use them for data collection.

### Current firmware (2026-10-12)

| | |
|---|---|
| Release | `firmware/releases/2026-10-10_v2/`, deployed to the Jetson. 13 `_v2` images (every range variant at 4 and 8 fps, plus `r017m_calib_v2`) |
| Fix it carries | DSS L3 MEMINIT. Older images stream ~50% stale words per chirp when booted from QSPI. |
| Front end | HPF 0/0 (175/350 kHz) on every variant; near floors 1.17–9.97 m depending on range |
| Data format | int16, **I first**, 3,145,728 B per frame (`testing/firmware_investigation_2026-10/investigation/JETSON_DATA_FORMAT.md`) |
| Capture requirement | DCA1000 packet delay **25 µs** (50 µs silently loses data at 8 fps) |

---

## Where to go

| I need to… | Document |
|---|---|
| understand the firmware source, the SDK junction, variants and releases | **`firmware/README.md`** |
| build and package firmware for a new range | **`docs/FIRMWARE_PACKAGING_WINDOWS.md`** |
| know why the current firmware is what it is (stale-data defect, fix, rebuild) | **`testing/firmware_investigation_2026-10/README.md`** |
| decode the radar data on the Jetson (layout, I/Q, rates, DCA settings) | `testing/firmware_investigation_2026-10/investigation/JETSON_DATA_FORMAT.md` |
| flash a variant on the Jetson | `testing/firmware_investigation_2026-10/investigation/FLASH_PROCEDURE.md` |
| know which parameters to use, and the original execution plan | `docs/RANGE_VARIANTS_BUILD_SPEC.md` |
| understand where the range equations come from, and what is proven vs assumed | **`docs/RANGE_EQUATION_LEDGER.md`** |
| trust a firmware hash (which ones are reproducible) | `docs/BUILD_DETERMINISM_FINDING.md` |
| find a recording that is not in git | **`DATA_INDEX.md`** |
| understand the DSP pipeline, module by module | this file, below |
| interpret the five-panel viewer (historical) | `docs/VIEWERS_PANELS_REFERENCE.md` |
| see the algorithm development roadmap | `testing/live_capture_validation/audit_and_improvement_plan/08_generated_plan_human_body_shape_perception_implementation.md` |

Read the Ledger before changing any chirp parameter. It is the only document
that distinguishes what has been measured from what has merely been assumed
consistently.

### Repository layout

| Path | Content |
|---|---|
| `firmware/` | AM273x cascade firmware: source (`am273x_cascade/`), released packages (`releases/`), archive |
| `docs/` | Build, range-equation and determinism documentation |
| `testing/firmware_investigation_2026-10/` | The October 2026 investigation and rebuild: report, data-format spec, flash procedure, analysis scripts, Jetson code snapshots |
| `testing/live_capture_validation/`, `testing/wireshark_packet_analysis/` | May–August 2026 capture validation and DCA1000 protocol analysis (logs, summaries; raw recordings excluded) |
| `capture/`, `processing/`, `analysis_utils/`, `live_capture.py`, `config/` | Frozen Windows capture and processing pipeline |
| `DATA_INDEX.md`, `data_manifests/` | Where every excluded recording lives, with md5 manifests |
| `THIRD_PARTY_NOTICES.md` | Licences of the TI and other components in the source and firmware images (BSD-3-Clause, MIT, TI Text File License for the AWR2243 patch) |
| branch `archive/history-before-2026-10-12` | Not part of `main`. History that existed only on this machine before 2026-10-12: the original local repository snapshot, the TI SDK cascade folders' source history, and the Jetson's pre-rebuild firmware files |

---

## How the work got here

Useful context for anyone picking this up, because the repository layout no
longer reflects where the work happens.

1. **Windows-only origin.** The project began as this repo: capture and
   recording utilities driving a DCA1000 over Ethernet, with a fixed
   shortrange cascade configuration.
2. **Pipeline development.** Capture and processing were extended with
   validity checks, GPU acceleration, the live streaming path, and the
   body-shape phases documented below. Everything in `## Pipeline State`
   onward dates from this period.
3. **Jetson requirement.** The end user needs vehicle-mounted collection,
   which needs an embedded platform.
4. **Protocol reverse-engineering.** A full capture session was recorded here
   with Wireshark listening to every packet. Analysing that trace is what
   made a pure-Python DCA1000 capture possible on Linux — there is no
   Windows-only dependency in the protocol itself.
5. **Flashing proof of concept.** A load-only option was added to the capture
   script here. That established how flashing works, what the `.xer5f` and
   `.cfg` files each actually do, and led to the decision to boot from QSPI.
6. **Migration.** Camera capture, radar capture, their synchronisation, and
   the flashing step were built for the Jetson. Processing and replay now run
   on the Jetson GPU. QSPI boot removed Windows from the operational loop
   entirely.

Windows kept exactly one job, because the SDK lives here.

7. **Range variants (2026-10-02 to 10-06).** The slope-register LSB error was
   found and corrected, and r050m / r075m / r100m were added. Seven variants
   were packaged and flashed from the Jetson over QSPI (`docs/`).
8. **Stale-data defect and fix (2026-10-10).** QSPI-booted data was ~50%
   bit-identical stale words. The root cause was missing DSS L3 MEMINIT (CCS
   loading had hidden it). It was fixed in `main_mss.c` and confirmed on
   hardware. The same work proved the data is I-first and that the DCA1000
   needs a 25 µs packet delay at 8 fps.
9. **All variants rebuilt (2026-10-10, deployed 2026-10-12).** Every range now
   has `_v2` images at 4 and 8 fps, all with the fix and HPF 0/0. The firmware
   source moved into this repository and became the single source, reached
   from the SDK through a junction (`firmware/README.md`).

---

## Known corrections to the content below

The sections after this point were verified against code on **2026-06-20**,
before the Jetson migration, and have not been revised. These are the places
where they are now known to be wrong. Details in `docs/RANGE_EQUATION_LEDGER.md`.

| Where | States | Correction |
|---|---|---|
| Radar Geometry → range resolution | 6.60 cm | **6.56 cm** — slope-register LSB is 48.279 kHz/µs, not 48 |
| Radar Geometry → max range | 16.8 m | **16.78 m** — same cause |
| Radar Geometry → frame rate | 4 fps (256 ms period) | 4 fps is **250 ms**. The firmware sets 250 ms; `256` is the ADC sample count, not a period |
| Radar Geometry → az resolution | 2.3 cm/bin at 3 m | Design intent only. Assumes a uniform 0.5λ array; the 6-TX TDM virtual array is **not** uniform. Unvalidated |
| Limitations → GPU/CPU parity test | "Test script not created" | Created and run. Differences are float32 rounding, not a defect; they flip CFAR decisions on a sparse cloud, so backends must not be mixed within one result set |
| File Checksums | — | **Stale.** `radar_config.py` is listed as `551a5911…`; the version this project worked from is `39eb01c5…`. Retained as a dated record of the Windows-era deployment, not a verification target |
| Config → `.cfg` files | `adcbufCfg -1 0 1 0 1` (Q-first) | The data is **I first**. The Windows tools force `i-first` and are correct; the corrected `.cfg` files are in `firmware/releases/` |
| Hardware Requirements → firmware | `.xer5f` loaded through CCS | Current images boot from QSPI and are flashed from the Jetson. A pre-v2 image booted from QSPI streams ~50% stale words |
| Config → DCA1000 | `packetDelay_us` 50 | **25 µs** since 2026-10-12 (`config/README.md`) |

Every range figure in this repository, and in every session processed before
the correction, is **0.58% long**. It is a labelling error in the `.cfg`, not
a capture error — see `docs/RANGE_VARIANTS_BUILD_SPEC.md` §4. All collected data
is recoverable by re-processing; nothing needs recapturing.

---

## Project Layout

### Capture

| File | Purpose |
|---|---|
| `capture/test.py` | Main entry point: capture, stop, geometry print, cfg validation, offline extraction |
| `capture/config.py` | Fixed paths and `cascade_shortrange.cfg` parsing |
| `capture/dca.py` | DCA1000 control, raw file monitoring, frame splitting |
| `capture/radar.py` | DSS firmware load and UART stop helper |

### Processing

| File | Purpose |
|---|---|
| `processing/radar_config.py` | `RadarConfig` dataclass — all waveform parameters, CFAR settings, and pipeline flags |
| `processing/radar_processing.py` | Full DSP pipeline: range FFT → Doppler FFT → MTI → RD-CFAR → multi-peak azimuth → elevation → xyz cloud |
| `processing/radar_plots.py` | Offline viewer: RD/RE/RA heatmaps with CFAR markers. Label `az-pts` (was `RA-CFAR`) |
| `processing/streaming.py` | Live pipeline: `FrameQueue`, `StreamingProcessor`, `LiveViewer` (5-panel body-shape viewer) |
| `processing/gpu_accel.py` | CuPy GPU acceleration for all 8 DSP stages; persistent GPU buffers; CASO/OS CFAR |
| `processing/accumulate.py` | **Phase 2–6:** `TemporalAccumulator`, `subject_frame()`, `fit_body_ellipse()`, `gait_features()` |
| `processing/microdoppler.py` | **Phase 6:** `MicroDopplerBuffer` — Doppler-time spectrogram and cadence estimation |

### Diagnostics

| File | Purpose |
|---|---|
| `analysis_utils/diag_pipeline_audit.py` | Batch 400-frame audit → `frames.csv` + `points.csv` with all phase columns |
| `analysis_utils/diag_xyz.py` | Per-frame body-shape geometry: x/y/z spread, az/RD ratio, verdict |
| `analysis_utils/benchmark_pipeline.py` | End-to-end per-stage latency benchmark (CPU vs GPU) |

### Entry Points

| File | Purpose |
|---|---|
| `live_capture.py` | Primary live hardware entry point; also drives replay mode |

### Config

| File | Purpose |
|---|---|
| `config/build_shortrange_inf/cascade_shortrange.cfg` | Fixed radar waveform configuration |
| `config/build_shortrange_inf/am273x_cascade_mss.xer5f` | DSP firmware |
| `config/AM273X_Capture_fixed.json` | DCA1000 capture config |
| `config/AM273x_XDS110.ccxml` | XDS110 debugger config |
| `config/README.md` | What each config file is for, and the 25 µs DCA1000 packet delay |

---

## Pipeline State

Phases 0–6 of `testing\live_capture_validation\audit_and_improvement_plan/08_generated_plan_human_body_shape_perception_implementation.md` are complete. All acceptance
criteria pass. The system is ready for multi-session outdoor data collection.

| Phase | Description | Status | Key metric |
|---|---|---|---|
| 0 | Observability — per-frame CSV audit | ✓ Complete | 400-row `frames.csv`, stage attribution visible |
| 1 | Per-frame cloud correctness | ✓ Complete | grating/FoV/cc filters; prom=6 dB; cc_rej −71% |
| 2 | Temporal accumulation + motion comp | ✓ Complete | M4 median accum_pts = 32 ≥ 30 |
| 3 | DBSCAN single-subject clustering | ✓ Complete | 0 centroid jumps (was 61); noise = 2 pts median |
| 4 | Subject-centric coordinate normalisation | ✓ Complete | M5 dx_std = 0.141 m, range-independent |
| 5 | Body envelope visualisation | ✓ Complete | PCA ellipse tracks subject within ±0.50 m bounds |
| 6 | Micro-Doppler / gait features | ✓ Complete | Spectrogram panel; cadence via autocorrelation |
| 7 | Pose descriptors | Pending | Requires ≥ 20 multi-subject sequences |

### What the live viewer shows (5 panels)

| Panel | Content |
|---|---|
| LEFT (3D) | Full motion-compensated accumulated cloud, coloured by Doppler |
| CENTRE (X-Y) | Top-down body footprint; oval tracks DBSCAN cluster centroid |
| RIGHT (X-Doppler) | Lateral vs Doppler — trunk near zero, limbs extending outward |
| 4th (body-frame) | Subject-centric ±0.5 m; cyan cluster pts; amber PCA ellipse |
| 5th (spectrogram) | Doppler-time waterfall; amber torso line; cadence annotation |

Status bar: `vc=±X.XX m/s  σ=X.XX  limb=XX%  cadence=X.X Hz`

### Active pipeline flags (all True by default)

```python
emit_all_cluster_bins = True   # Phase 1: depth bins emitted
temporal_accum_en     = True   # Phase 2: motion-compensated accumulation
subject_frame_en      = True   # Phase 4: body-frame panel active
body_envelope_en      = True   # Phase 5: PCA ellipse overlay active
gait_features_en      = True   # Phase 6: gait descriptors in status bar
microdoppler_en       = True   # Phase 6: spectrogram panel active
```

---

## New Modules (Phases 2–6)

### `processing/accumulate.py`

Contains the full temporal pipeline from Phase 2 through Phase 6.

**`TemporalAccumulator`** — stateful ring buffer with motion compensation,
DBSCAN clustering, subject-frame normalisation, and gait feature extraction.

```python
acc = TemporalAccumulator(
    window=16,              # frames in ring buffer (4s at 4fps)
    max_jump_m=0.6,         # centroid jump gate (2.4 m/s max)
    alpha=0.3,              # EMA smoothing for centroid
    dbscan_eps=0.80,        # DBSCAN neighbourhood radius (m)
    dbscan_min_samples=3,   # minimum pts per cluster
    max_cluster_radius=0.65,# reject implausibly wide clusters (m)
    subject_frame_en=True,  # populate AccumResult.subject_cloud
    gait_features_en=True,  # populate AccumResult.gait
    dop_limb_thr=0.30,      # torso/limb Doppler boundary (m/s)
)

result = acc.update(xyz_cloud, frame_idx=fi)
# result.cloud          [M,7]   motion-compensated accumulated cloud
# result.cluster        ClusterResult — DBSCAN body cluster
# result.subject_cloud  [K,7]   body-local (dx,dy,dz,...) coords
# result.gait           GaitFeatures — dop_centroid, limb_frac, cadence
```

**`subject_frame(accum_result)`** — translates cluster cloud to body-local
coordinates centred on the cluster centroid. Used by Phase 4/5 viewer.

**`fit_body_ellipse(sf_cloud)`** — PCA ellipse fit to (dx, dy) body-frame
cloud. Returns cx, cy, rx, ry, angle_deg, and outline points. Clamped to
±0.50 m per plan requirement.

**`gait_features(cluster_cloud, dop_limb_thr=0.30)`** — per-frame
micro-Doppler descriptor. Returns `GaitFeatures`:
- `dop_centroid` — power-weighted trunk velocity (m/s)
- `dop_spread` — std of cluster Doppler values
- `dop_max` — fastest-moving scatterer (m/s)
- `n_torso_pts` / `n_limb_pts` — pts below/above `dop_limb_thr`
- `limb_frac` — gait activity index (0 = stance, 1 = all limbs)

### `processing/microdoppler.py`

**`MicroDopplerBuffer`** — Doppler-time spectrogram ring buffer.

```python
mdb = MicroDopplerBuffer(
    time_frames=64,     # columns (16s of history at 4fps)
    v_max=1.5,          # ±1.5 m/s Doppler axis
    n_dop_bins=40,      # rows in spectrogram
    frame_rate_hz=4.0,
)
mdb.update(cluster_dop_mps, limb_frac=lf, dop_centroid=dc)

mdb.spectrogram     # [40, 64] float32 — column-normalised heatmap
mdb.torso_line      # [64] float32 — dop_centroid history
mdb.cadence_hz      # float — gait cadence via autocorrelation
```

Cadence is estimated from the autocorrelation of `limb_frac` history.
Valid range: 0.3–3.0 Hz. Returns `nan` if no clear peak above 0.20.

---

## Diagnostic Scripts

### `analysis_utils/diag_pipeline_audit.py` — Phase 0–6 batch audit

Runs `process_frame()` over every `.bin` file and writes two CSVs with
all phase columns:

```powershell
# Full Phase 0–6 audit (recommended for each new recording session)
python analysis_utils/diag_pipeline_audit.py `
    --folder  capture\frames `
    --cfg     config\build_shortrange_inf\cascade_shortrange.cfg `
    --temporal-accum --accum-window 16 --subject-frame --gait-features `
    --out-dir debug_context\session_name

# Phase 0 only (fast, ~50s for 400 frames)
python analysis_utils/diag_pipeline_audit.py `
    --folder capture\frames --cfg ... --out-dir debug_context\p0
```

**`frames.csv` columns (26 total):**

| Group | Columns |
|---|---|
| Stage attribution | `rd_cfar`, `after_consistency`, `n_clusters`, `az_peaks_raw`, `fov_rej`, `grating_rej`, `cc_rej`, `ra_det` |
| Cloud | `cloud_pts`, `accum_pts`, `cluster_pts`, `cluster_noise` |
| Cluster geometry | `cluster_radius_x`, `cluster_radius_y`, `cluster_cx`, `cluster_cy` |
| Phase 4 | `subject_spread_x`, `subject_spread_y` |
| Phase 6 gait | `dop_centroid`, `dop_spread`, `dop_max`, `n_torso_pts`, `n_limb_pts`, `limb_frac` |
| Centroid | `centroid_x`, `centroid_y`, `centroid_z`, `dop_zero_pts`, `dop_max`, `proc_ms` |

### `analysis_utils/diag_xyz.py` — per-frame geometry diagnostic

```powershell
python diag_xyz.py                          # 15-frame diagnostic set
python diag_xyz.py --all                    # all detected frames
python diag_xyz.py --radar-height 0.33      # apply z offset (metres)
python diag_xyz.py --frames 9 24 301 --verbose 9 24 301
```

---

## Software Requirements

Windows 10 or 11, Python 3.10+.

```powershell
pip install numpy scipy matplotlib pyqtgraph cupy-cuda12x PyOpenGL scikit-learn colorcet
```

| Package | Purpose |
|---|---|
| `numpy` | Core array operations |
| `scipy` | CPU CFAR fallback; autocorrelation |
| `matplotlib` | Offline plots |
| `pyqtgraph` | Live display — all five viewer panels |
| `cupy-cuda12x` | GPU acceleration (CUDA 12; falls back to CPU if absent) |
| `PyOpenGL` | OpenGL for 3D scatter panel |
| `scikit-learn` | DBSCAN clustering (Phase 3) |
| `colorcet` | Perceptually uniform spectrogram colourmap (Phase 6) |

> **PyOpenGL:** install `PyOpenGL` only — do **not** install
> `PyOpenGL_accelerate`. If already present: `pip uninstall PyOpenGL_accelerate`

> **scikit-learn** is required for Phase 3 DBSCAN. Without it the accumulator
> falls back to raw median centroid (Phase 2 behaviour) with a warning.

---

## Hardware Requirements

- TI AWR2243-2X cascaded radar (2-chip, 6 TX / 8 RX, 384 chirps/frame)
- DCA1000 capture board
- XDS110 debugger connection
- Ethernet: PC static IP `192.168.33.30`, DCA1000 IP `192.168.33.180`
- UART connection (default COM20)
- NVIDIA GPU (RTX series recommended)

### Radar Geometry

| Parameter | Value |
|---|---|
| TX / RX | 6 TX TDM MIMO / 8 RX (4 per device × 2 devices) |
| Virtual aperture | 48 channels |
| Range resolution | 6.60 cm |
| Max range | 16.8 m |
| Doppler max | ±2.498 m/s |
| Doppler resolution | 0.078 m/s |
| Az resolution at 3 m | 2.3 cm/bin |
| Az resolution at 8 m | 6.2 cm/bin |
| Frame rate | 4 fps (256 ms period) |
| Frame size | 3,145,728 bytes |

---

## Live Capture — `live_capture.py`

### Typical live commands

```powershell
# Full body-shape pipeline (all phases active, 5-panel viewer)
python live_capture.py --display pointcloud --quiet

# Replay recorded frames at 0.5 fps for detailed inspection
python live_capture.py --replay capture\frames --display pointcloud --replay-fps 0.5 --quiet

# Skip firmware reload (radar already running)
python live_capture.py --skip-load --display pointcloud --quiet

# Record new session while streaming
python live_capture.py --record --out-dir capture\frames --display pointcloud --quiet
```

### All flags

| Flag | Default | Description |
|---|---|---|
| `--cfg` | `cascade_shortrange.cfg` | Radar configuration file |
| `--display` | `heatmap` | `heatmap` or `pointcloud` (5-panel body-shape) |
| `--no-cfar` | off | Skip CFAR — heatmap display only |
| `--quiet` | off | Suppress per-frame diagnostic logs |
| `--record` | off | Write `frame_*.bin` to disk while streaming |
| `--out-dir` | `capture\frames` | Output directory for `--record` |
| `--frames` | infinite | Stop after N frames |
| `--replay FOLDER` | off | Replay recorded frames (no hardware) |
| `--replay-fps` | 0 (auto) | Replay feed rate; 0 = pace to processing speed |
| `--loop` | off | Loop replay until window closes |
| `--skip-load` | off | Skip firmware load |
| `--uart` | `COM20` | UART port for firmware stop |
| `--warmup` | 0 | Frames to discard before display |

---

## DSP Pipeline (per-frame, stateless)

```
Raw IQ bytes (3,145,728 B)
  │
  ├─ 1.  IQ reorder (i-first)
  ├─ 2.  Antenna calibration (complex correction per virtual channel)
  ├─ 3.  Range FFT [6TX × 64loops × 8RX × 256samples] → [64, 256, 48 VA]
  ├─ 4.  Doppler FFT + MTI clutter removal + zero-Doppler notch
  ├─ 5.  Non-coherent integration (Σ|x|² over 48 VA → dB)
  │      + Doppler-stripe suppression
  ├─ 6.  RD-domain CFAR (CASO/OS, GPU) → rd_det [64×256 bool]
  │      + cfar_margin_db gate + cfar_min_power_db gate + NMS
  │      + RD-sidelobe prune + range gate
  ├─ 6b. Cross-channel consistency fusion (consistency_k)
  ├─ 7.  RA map for heatmap display
  ├─ 8.  RD-confirmed multi-peak azimuth → ra_det
  │      - cluster adjacent RD-confirmed range bins (rd_range_cluster_bins=2)
  │      - prominence-filtered local az peaks (az_peak_min_prom_db=6.0 dB)
  │      - FoV gate (|sin(az)| ≤ max_az_sin=0.866, ±60°)
  │      - grating-lobe gate (body_az_half_width_m=0.30 m, boresight-nearest)
  │      - cross-cluster coherence gate (cross_cluster_range_m=0.35 m)
  │      - CSV audit row appended when audit_csv_path is set
  ├─ 9.  Elevation FFT → RE map
  └─ 11. XYZ point-cloud extraction → xyz_cloud [N × 7]
         x(m), y(m), z(m), pwr_db, dop_mps, rng_m, az_deg
```

**`process_frame()` is strictly per-frame and stateless.** All temporal
reasoning (accumulation, clustering, tracking, gait) lives in
`processing/accumulate.py` and `processing/microdoppler.py`, which are
called by the live viewer and the audit script, not by the processing pipeline.

---

## Temporal Pipeline (stateful, in viewer and audit)

```
xyz_cloud (per frame)
  │
  ├─ TemporalAccumulator.update()
  │    ├─ Phase 2: Y+X EMA motion compensation → 16-frame merged cloud
  │    ├─ Phase 3: DBSCAN(eps=0.80, min_samples=3) → body cluster
  │    ├─ Phase 4: subject_frame() → body-local (dx, dy, dz) cloud
  │    └─ Phase 6: gait_features() → GaitFeatures descriptor
  │
  └─ MicroDopplerBuffer.update()
       └─ Phase 6: Doppler histogram → spectrogram column
                   limb_frac autocorrelation → cadence_hz
```

---

## Accepted Metrics (Phase 3 audit — 400 frames, single outdoor clip)

| Metric | Value | Target |
|---|---|---|
| Detected frames | 320 / 400 (80%) | — |
| avg cloud pts / det frame | 2.22 | — |
| avg accum_pts / frame | 25.1 | — |
| **M4** median cluster_pts (active) | 26 | ≥ 30 |
| **M4** median accum_pts (active) | 32 | ≥ 30 ✓ |
| Centroid jumps > 0.6 m | 0 | < 15 ✓ |
| Median noise pts | 2.0 | ≤ 3 ✓ |
| Cluster radius_x | 0.441 m | ≤ 0.55 m ✓ |
| **M5** dx_std (full window) | 0.141 m | 0.10–0.25 m ✓ |
| **M5** range independence | identical at 4.19–5.17 m | ✓ |
| grating_rej total | 1 275 | visible ✓ |
| cc_rej total | 119 | < 423 baseline ✓ |

---

## Key RadarConfig Fields (body-shape pipeline)

### Phase 1 — per-frame cloud

| Field | Default | Description |
|---|---|---|
| `az_multi_peak_en` | `True` | Enable multi-peak azimuth search |
| `az_peak_min_prom_db` | `6.0` | Minimum az peak prominence (dB) |
| `az_peak_min_gap_bins` | `6` | Minimum bin separation between peaks |
| `az_peak_max_n` | `6` | Maximum peaks per cluster |
| `emit_all_cluster_bins` | `True` | Emit az peaks for all depth bins |
| `body_az_half_width_m` | `0.30` | Grating-lobe gate: body half-width (m) |
| `max_az_sin` | `0.866` | FoV gate: ±60° |
| `cross_cluster_range_m` | `0.35` | Cross-cluster coherence window (m) |

### Phase 2–3 — accumulation and clustering

| Field | Default | Description |
|---|---|---|
| `temporal_accum_en` | `True` | Master switch for accumulator |
| `accum_window` | `16` | Ring buffer size (frames) |
| `accum_max_centroid_jump_m` | `0.6` | Ghost gate (m/frame) |
| `accum_alpha` | `0.3` | EMA smoothing weight |
| `dbscan_eps` | `0.80` | DBSCAN neighbourhood radius (m) |
| `dbscan_min_samples` | `3` | Minimum pts per cluster |
| `max_cluster_radius` | `0.65` | Reject implausibly wide clusters (m) |

### Phase 4–6 — body shape and gait

| Field | Default | Description |
|---|---|---|
| `subject_frame_en` | `True` | Enable body-frame panel |
| `body_envelope_en` | `True` | Enable PCA ellipse overlay |
| `gait_features_en` | `True` | Enable gait descriptors in status bar |
| `dop_limb_thr` | `0.30` | Torso/limb Doppler boundary (m/s) |
| `microdoppler_en` | `True` | Enable spectrogram panel |
| `spectrogram_frames` | `64` | Spectrogram time columns (16s at 4fps) |
| `spectrogram_v_max` | `1.5` | Spectrogram Doppler axis limit (m/s) |

### Phase 0 — audit

| Field | Default | Description |
|---|---|---|
| `audit_csv_path` | `None` | When set, appends one CSV row per frame |

---

## GPU Acceleration

All major DSP stages run on GPU via CuPy:

| Stage | Typical time |
|---|---|
| Range FFT | 4 ms |
| Doppler FFT × 4 | 14 ms |
| Power reduction | 3 ms |
| Azimuth FFT × 2 | 20 ms |
| RA collapse | 8 ms |
| RD CFAR (CASO) | 2 ms |
| Elevation FFT | 4 ms |

**Typical live performance (RTX 3080 Ti, Windows):**

| Mode | Avg latency |
|---|---|
| Full pipeline (CFAR on) | ~270 ms |
| `--no-cfar` | ~200 ms |

The temporal pipeline (accumulator, DBSCAN, spectrogram) adds ~40–60 ms
per frame on CPU. Total live latency with all phases active: ~310–330 ms.

---

## Current Limitations and Open Items

| Item | Status | Details |
|---|---|---|
| Config hygiene | Open | 5 unwired fields: `strict_object_filtering`, `require_rd_confirmation`, `ra_sidelobe_db`, `filter_high_moving`, `moving_objects_only` — plan says delete or wire |
| GPU/CPU parity test | Open | Test script not created; GPU path stable in practice |
| Kalman tracker | Not implemented | DBSCAN+EMA achieves equivalent metrics (0 jumps); Kalman would complete Phase 3 structurally |
| Phase 7 gated | Blocked on data | Requires ≥ 20 multi-subject sequences; single 400-frame clip is insufficient |
| Windows WDDM latency | Known | Trimodal ~185/280/380 ms cycle; driver-level, not fixable in Python |
| Sparse cloud (~2 pts/frame) | Expected | Body shape emerges only after 16-frame accumulation |
| Elevation (z) unreliable | Expected | 16 el VA → ~19 cm/bin at 3 m; z not used for body shape |
| Single-subject assumption | Known | DBSCAN selects one body cluster; multi-subject requires tracker |

---

## Next Steps (Data Collection — Phase 7 Prerequisite)

The pipeline is complete. The bottleneck for Phase 7 is data volume.

### Minimum viable dataset

20–30 sequences across multiple subjects before beginning Phase 7.

| Scenario | Pattern | Priority |
|---|---|---|
| A — Radial walk | Out-and-back 3–9 m, multiple speeds and subjects | 1st |
| D — Multi-leg | 6–8 direction changes per run, 3 speeds mixed | 2nd |
| B — Lateral walk | Perpendicular to boresight, 10 m corridor | 3rd |
| C — Stand then walk | 8 s stationary → walk → return → stationary | 4th |

### Per-session checklist

Before each session:
- Record radar mounting height (cm)
- Mark ground positions with tape/cones (3 m, 5 m, 7 m, 9 m from radar)
- Run 5-frame test capture, confirm viewer shows detections

After each session:
```powershell
python diag_pipeline_audit.py `
    --folder capture\frames `
    --cfg config\build_shortrange_inf\cascade_shortrange.cfg `
    --temporal-accum --accum-window 16 --subject-frame --gait-features `
    --out-dir debug_context\session_name
```

Review `summary.txt` before the next session to catch issues immediately.

---

## Troubleshooting

### No detections (`cloud:0`) despite target present

1. Check `[PROC] C7 RD-CFAR margin` lines — margin consistently `BELOW by 15+ dB` means target SNR is too low.
2. Try `--cfar-margin 5` for broader detection.
3. Match firmware CFAR: `--cfar caso --cfar-guard 0 0 --cfar-train 16 16`
4. ~2–4 pts/frame is **expected** for a single frame. Body shape only emerges after accumulation.

### DBSCAN cluster_pts = 0 in audit

- Confirm `scikit-learn` is installed: `pip install scikit-learn`
- Without sklearn, accumulator falls back to Phase 2 (no clustering)

### Spectrogram panel blank / no colourmap

- Confirm `colorcet` is installed: `pip install colorcet`
- Without colorcet, `ImageItem` uses a greyscale fallback — heatmap still renders

### Cadence shows `nan` in status bar

- Normal until 16+ frames with valid gait data accumulate
- Check `limb_frac` column in audit CSV — if always 0.0, `dop_limb_thr` may be too high

### 3D point cloud window crashes (OpenGL error)

```powershell
pip uninstall PyOpenGL_accelerate
pip install --upgrade PyOpenGL
```

### DCA1000 configuration fails

- PC NIC static IP: `192.168.33.30`
- DCA1000 IP: `192.168.33.180`
- Close mmWave Studio if holding the DCA board
- Power-cycle the DCA1000

### GPU not detected / CuPy import fails

```powershell
nvcc --version
python -c "import cupy; print(cupy.__version__)"
```

Pipeline falls back to CPU automatically (~3500 ms/frame vs ~270 ms/frame).

---

## File Checksums (current deployed versions)

| File | MD5 |
|---|---|
| `processing/accumulate.py` | `392b1610a37c05d0a3a3a32b573f20dc` |
| `processing/microdoppler.py` | `dce61d6fdece3ae5bc75e4e2c5aa866e` |
| `processing/radar_config.py` | `551a5911d29a697b627e9d9d7d8df3ac` |
| `processing/radar_processing.py` | `e74723d56ad4f6d6d94493190c2918de` |
| `processing/streaming.py` | `8dde27434c6b0305ec086b3b761d62dd` |
| `processing/radar_plots.py` | `dc8def38048f07c5cfb102202ab92f2b` |
| `analysis_utils/diag_pipeline_audit.py` | `be7f9162613094067a6889fa35d87438` |
| `analysis_utils/diag_xyz.py` | `982eaf9e9069c6489d59b6fc879fde83` |

---

*For the detailed step-by-step algorithm roadmap see
[`testing/live_capture_validation/audit_and_improvement_plan/08_generated_plan_human_body_shape_perception_implementation.md`](testing/live_capture_validation/audit_and_improvement_plan/08_generated_plan_human_body_shape_perception_implementation.md).*
