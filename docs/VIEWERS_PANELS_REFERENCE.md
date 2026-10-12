# AWR2243-2X Live Viewer — Five-Panel Reference

> ## Status: historical reference
>
> This document describes the **five-panel live viewer from the Windows-era
> pipeline**. The end user subsequently accepted a single focused view in its
> place, and the Jetson repository holds the current implementation. Nothing
> here should be taken as a description of what the viewer shows today.
>
> It is retained because the per-panel accounts of each DSP stage, the
> acceptance criteria, and above all the failure-mode tables remain the
> clearest written explanation of what the pipeline computes and why. Those
> parts are still accurate about the *processing*, whatever the UI now looks
> like.
>
> ### Numbers in this document are superseded
>
> The hardware reference values below were computed with a slope-register
> conversion that is now known to be wrong by 0.58%. See
> `RANGE_EQUATION_LEDGER.md` §2 for the correction. In short:
>
> | quantity | stated here | actual |
> |---|---|---|
> | range resolution | 6.6 cm/bin | **6.56 cm/bin** |
> | max range | 16.8 m | **16.78 m** |
> | frame period | 256 ms | **250 ms** (4 fps exactly) |
>
> The derived timings in this document (16 frames = 4 s, 64 frames = 16 s)
> assume 250 ms and are therefore correct; only the stated period is wrong.
>
> **The azimuth resolution figures carry a larger caveat.** Every
> `cm/bin` azimuth value here — 2.34 cm at 3 m, 6.25 cm at 8 m, and the
> `Δx = R × 0.0078` relation in Panel 3 — assumes a **uniformly spaced
> 0.5λ array**. The virtual array formed by 6-TX TDM MIMO is not uniform,
> which the pipeline source itself acknowledges. The ledger lists this as
> an open item, unvalidated and unquantified. Treat the azimuth numbers as
> the design intent, not as measured performance.
>
> Range and Doppler axes *have* since been cross-validated against each
> other to ~1.3% (ledger §3). Azimuth has not been validated at all.

---


**Audience:** radar engineers and computer vision researchers working
with the AWR2243-2X cascaded body-shape perception pipeline.

This document describes each of the five live viewer panels in depth:
what signal processing stage each one represents, what is rendered and
how, what the correct appearance is for each scenario, what failure modes
look like, and how the panels relate to each other diagnostically.

---

## System context

The viewer sits at the end of a two-stage pipeline:

```
Raw IQ (3,145,728 B/frame)
  └─ process_frame()      — stateless DSP per frame
       range FFT → Doppler FFT → MTI → RD-CFAR → az multi-peak → xyz cloud
  └─ TemporalAccumulator  — stateful, 16-frame ring buffer
       motion compensation → DBSCAN → subject_frame() → gait_features()
  └─ MicroDopplerBuffer   — stateful, 64-frame ring buffer
       Doppler histogram → spectrogram → cadence (autocorrelation)
  └─ LiveViewer           — 5 panels updated at 4 fps
```

All five panels consume the output of the stateful layer, not the
per-frame output directly. The 16-frame accumulation window is the
fundamental temporal unit: features extracted from fewer than 16 frames
(the warm-up period at the start of each recording) are statistically
incomplete.

### Hardware reference values

| Parameter | Value |
|---|---|
| Frame rate | 4 fps (256 ms per frame) |
| Range resolution | 6.6 cm/bin |
| Doppler resolution | 0.078 m/s per bin |
| Doppler range | ±2.498 m/s |
| Az resolution at 3 m | 2.34 cm/bin → shoulder (0.45 m) spans 19 bins |
| Az resolution at 8 m | 6.25 cm/bin → shoulder spans 7 bins |
| Accumulation window | 16 frames = 4 s |
| EMA centroid lag | 2.3 frames = 0.6 s (α = 0.3) |
| Spectrogram window | 64 frames = 16 s |

---

## Panel 1 — 3D accumulated cloud

**Processing stage:** Phase 2 (temporal accumulation with motion compensation)

**Position in viewer:** leftmost, largest, OpenGL 3D scatter

### What is rendered

All points from the current 16-frame accumulator buffer after Y+X EMA
motion compensation, displayed in world-frame coordinates:

```
x  = lateral (azimuth), positive = right of boresight
y  = range (forward), positive = away from radar
z  = elevation + radar_height_offset
```

Each point is coloured by its radial Doppler value using a three-way
diverging colormap:

- Red — receding (positive radial velocity, walking away)
- White — stationary (|dop| near zero, tangential motion)
- Blue — approaching (negative radial velocity, walking toward radar)

Point size scales linearly with SNR (power_dB), so strong returns are
larger and visually dominant.

### Why this panel exists

Panel 1 provides the unfiltered ground truth of what the radar sees
across the current 4-second accumulation window. Every upstream decision
in the pipeline — grating lobe rejection, FoV gate, cross-cluster filter,
DBSCAN noise labelling — is visible here as the presence or absence of
points. It is the diagnostic entry point: if the downstream panels show
no tracking, the first question is whether Panel 1 shows any points at
all.

The Doppler colouring serves two specific purposes:

1. **Sign convention verification.** During radial walking, all points
should shift from white through red (walking away) or blue (walking
toward) as the subject moves. A subject walking away who produces blue
points indicates a sign flip somewhere in the Doppler FFT output.

2. **Clutter discrimination.** Stationary infrastructure (walls, poles,
vehicles not yet rejected by MTI) appears white regardless of frame.
Body returns appear coloured. This separation is immediate and requires
no numerical analysis.

### Motion compensation behaviour

The EMA centroid (α = 0.3, lag ≈ 2.3 frames = 0.6 s) tracks the
subject's range position and translates all historical frames to align
with the current centroid estimate. X compensation uses the most recent
frame's raw centroid (not the EMA) to avoid ghost-position lock-on.

During a direction reversal, the accumulated cloud shows a temporal
smear: points from the previous direction (old colour) persist for up
to 16 frames while new-direction points accumulate. The smear length in
the range axis equals the EMA lag × walking speed:

```
smear_length ≈ lag_frames × v_walk × (1/fps)
             ≈ 2.3 × 1.2 × 0.25 ≈ 0.69 m
```

This is not a pipeline failure. It is the expected transient before the
ring buffer flushes. The smear disappears after one full 16-frame window
(4 seconds).

### What correct output looks like

During radial walking: a compact elongated cloud aligned with the range
axis, shifting between red (outward leg) and blue (return leg) at each
direction reversal. The cloud should span approximately 0.3–0.5 m in x
(lateral) and 0.3–0.6 m in y (range depth of body). The elevation extent
(z) is typically 0.3–0.6 m and is less reliable due to the coarser
elevation resolution (48 virtual aperture channels vs 256 azimuth).

During lateral walking: the cloud moves horizontally (in x) while y
and z remain roughly constant. All points appear near-white (near-zero
Doppler) regardless of lateral speed.

### Failure modes

| Symptom | Cause | Check |
|---|---|---|
| No points visible | No detections passing CFAR | `cloud_pts` in audit CSV; try `--cfar-margin 5` |
| Points visible but wrong colour | Doppler sign flip | `dop_centroid` sign in gait features vs walk direction |
| Persistent white cloud at fixed position | MTI clutter not rejected | Is the target actually moving? Check MTI filter threshold |
| Cloud explodes to large spatial extent | Ghost return survived all filters | `cc_rej` count in audit — if zero, cross-cluster gate may need tightening |
| z values far from zero | Radar height offset not applied | Adjust `h_radar` slider in viewer or measure mounting height |

---

## Panel 2 — X-Y top-down footprint

**Processing stage:** Phase 3 (DBSCAN single-subject clustering and
centroid tracking)

**Position in viewer:** centre, 2D scatter, boresight looking down

### What is rendered

The projection of the accumulated cloud onto the horizontal plane:
x (lateral azimuth) on the horizontal axis, y (range) on the vertical
axis, with the radar at the top and range increasing downward.

Over this scatter an oval is drawn at the DBSCAN cluster centroid
(cluster_cx, cluster_cy) with fixed semi-axes:

```
semi-axis x:  ±0.225 m  (nominal human shoulder half-width)
semi-axis y:  ±0.150 m  (nominal human body half-depth, front-to-back)
```

The oval semi-axes are a fixed reference standard, not fitted to the
data. They show where the body should be relative to the centroid, not
where the cluster points actually are (that is the role of Panel 4).

### Why this panel exists

The top-down view is the canonical radar surveillance plane and the
primary track continuity diagnostic. It answers two questions that no
other panel makes as immediately visible:

**Is the centroid tracking the correct target?** If the oval locks onto
a wall reflection or grating lobe instead of the walking subject, the
oval will sit at a fixed position in y while the subject moves — visible
immediately as a stationary oval during an active recording.

**Is the track stable?** Each frame, the centroid is updated via the
EMA. Any centroid jump greater than 0.6 m between consecutive frames
(the ghost gate, corresponding to a speed of 2.4 m/s — faster than any
realistic walking speed) causes the accumulator to freeze the centroid
for that frame. A jump visible in the top-down view that exceeds the
oval diameter in one frame is a track failure event.

### DBSCAN parameters

```
eps            = 0.80 m    neighbourhood radius
min_samples    = 3         minimum points to form a cluster
max_cluster_radius = 0.65 m  reject implausibly wide clusters
jump_gate      = 0.60 m/frame = 2.4 m/s max allowed speed
```

The eps value of 0.80 m was calibrated to span the full body depth
(0.389 m measured radius, 0.778 m diameter) within a single DBSCAN
neighbourhood, so the body does not split into two depth sub-clusters
at far range.

### What correct output looks like

During radial walking: the oval moves smoothly along the y axis (range),
advancing during the outward leg and retreating during the return leg.
Lateral position (x) stays near boresight (±0.3 m) unless the subject
walks at an angle. The transition from outward to return should be a
smooth curve, not a step change.

During lateral walking (Scenario B): the oval moves horizontally (in x)
at fixed y = 3 m. The lateral drift should be smooth and continuous as
the subject crosses the ±3 m corridor.

### Failure modes

| Symptom | Cause | Check |
|---|---|---|
| Oval locks to fixed position while subject walks | Ghost return (wall/vehicle) captured by DBSCAN | `cc_rej` in audit; tighten `cross_cluster_range_m` |
| Oval jumps > 0.5 m between frames | Ghost point shifted cluster centroid | `cluster_noise` column; check if a second target is present |
| Oval absent (no oval drawn) | DBSCAN found no cluster this frame | `cluster_pts = 0` in audit; subject may be outside P1–P4 corridor |
| Oval oscillates at wrong range | EMA centroid lag during fast walking | Expected at high replay fps; occurs in production if actual speed > 1.8 m/s |

---

## Panel 3 — X-Doppler lateral velocity profile

**Processing stage:** Phase 1 (azimuth multi-peak detection — the
per-frame cloud structure diagnostic)

**Position in viewer:** right side, 2D scatter, x axis = lateral
azimuth, y axis = radial velocity

### What is rendered

Each accumulated point plotted as (x, dop_mps):

```
x axis:   lateral azimuth position (metres from boresight)
y axis:   radial Doppler velocity (m/s), positive = receding
colour:   same Doppler diverging map as Panel 1
```

No fitting or smoothing is applied. This is the raw (azimuth,
velocity) scatter of every point in the 16-frame accumulator buffer,
in world-frame coordinates.

### Why this panel exists

Panel 3 is the azimuth multi-peak diagnostic and the per-point
micro-Doppler cross-section. It answers a question that no other panel
addresses directly: **is the pipeline resolving lateral body width
within a single frame, or is every frame producing only a single azimuth
peak?**

When az multi-peak fires correctly (prominence threshold 6.0 dB met),
multiple peaks are detected across the shoulder width in a single frame.
These peaks appear at different x positions in Panel 3. When multi-peak
fails (prominence threshold too high, or subject too far for the az
resolution to separate shoulder returns), all points from a frame
collapse to a single x value — Panel 3 shows a vertical stripe at
x = centroid_x with no lateral spread.

The (x, v_r) structure also makes limb-torso separation visible in a
way that per-frame gait scalars cannot. During radial walking:

- Torso returns: x near centroid_x, |dop| near walking speed (~0.4 m/s)
- Limb returns: x at centroid_x ± limb_offset, |dop| > 0.30 m/s
  (the dop_limb_thr boundary)

The two dashed horizontal lines at ±0.30 m/s mark the boundary between
the torso and limb Doppler regimes. Points above/below these lines count
as limb returns (n_limb_pts) and contribute to limb_frac.

### Azimuth resolution and multi-peak detectability

```
az bin size at range R:  Δx = R × (2 / az_fft_size)
                              = R × 0.0078 m/bin

At 3 m:  Δx = 0.023 m/bin → shoulder (0.45 m) spans 19 bins
At 8 m:  Δx = 0.063 m/bin → shoulder spans 7 bins
```

At 8 m range with 7 bins across the shoulder, the peak prominence
between adjacent shoulder returns drops significantly. This is why
multi-peak is more likely to fire at close range and the lateral scatter
in Panel 3 is wider at 3 m than at 8 m for the same subject. This is
not a pipeline bug — it is a fundamental resolution constraint.

### What correct output looks like

During radial walking at 3–5 m range: a compact cluster centred near
(centroid_x, walking_speed), with some points displaced ±0.05–0.15 m
laterally at matching Doppler (shoulder returns from the same range bin).
Occasionally points appear at higher |dop| (limb returns). The cluster
should not span more than ±0.3 m in x in a single frame.

During lateral walking: all points collapse toward dop ≈ 0 across the
full x range of the subject's corridor. This produces a flat horizontal
band near v_r = 0, which is the correct signature for tangential motion.
The absence of Doppler spread in this scenario is expected and correct.

### The az/RD ratio diagnostic

```
az/RD ratio = cloud_pts / rd_cfar_survivors
```

This ratio is the per-frame measure of multi-peak activity. A ratio of
1.0 means every RD detection produced exactly one azimuth peak — no
multi-peak fired. A ratio of 2.5 means 2.5 az peaks per RD detection on
average — multi-peak is resolving lateral structure. Values consistently
above 1.5 indicate the pipeline is capturing body width. This ratio is
computed in `analysis_utils/diag_xyz.py` and is the numerical complement of the lateral
scatter visible in Panel 3.

### Failure modes

| Symptom | Cause | Check |
|---|---|---|
| Single vertical stripe, no lateral spread | Multi-peak not firing | `az_peak_min_prom_db` — reduce from 10 to 6 dB if still at old value |
| All points near v_r = 0 during radial walk | Doppler sign not being detected | MTI filter too aggressive; check Doppler FFT stage |
| Wide lateral spread > ±0.5 m | Grating lobe not rejected | `grating_rej` count in audit; check `body_az_half_width_m` |
| Points at extreme Doppler (> 1.5 m/s) | Vehicle or other fast-moving object | `max_az_sin` gate may not be rejecting it; check FoV |

---

## Panel 4 — Body-frame panel

**Processing stages:** Phase 4 (subject-centric coordinate
normalisation) and Phase 5 (PCA body envelope fitting)

**Position in viewer:** 4th from left, 2D scatter, fixed ±0.5 m extent
in both axes

### What is rendered

The full 16-frame accumulated cloud translated to body-local
coordinates by subtracting the DBSCAN cluster centroid:

```
dx = x - cluster_cx    (lateral offset from body centre, m)
dy = y - cluster_cy    (range offset from body centre, m)
dz = z - cluster_cz    (elevation offset from body centre, m)
```

After translation, the display is fixed at ±0.5 m in both dx and dy.
A crosshair at (0, 0) marks the cluster centroid (the body centre).

**Point colouring:**
- Cyan (RGBA 80, 180, 255, 160) — DBSCAN body-cluster inlier points
  (within 1.5 × eps = 1.2 m of centroid)
- Dim grey (RGBA 80, 80, 80, 100) — noise-labelled points (outliers
  beyond the cluster boundary, visible but subdued)

Semi-transparent rendering (α = 160/255 ≈ 63%) allows density to be
inferred from point overlap in the tight body-width region.

**Reference overlays:**
- Dashed blue box at ±0.225 m × ±0.15 m — nominal human body footprint
  (shoulder width × body depth), fixed reference scale
- Crosshair at (0, 0) — body centroid
- Amber PCA ellipse — 2σ boundary fitted to body-cluster points in
  (dx, dy), clamped to ±0.50 m semi-axes

**Status annotation (top left of panel):**

```
accum=64 pts  cluster=58  noise=6  env 0.28×0.43m  θ=12°
```

### Why this panel exists

Panel 4 is the primary body-shape output panel and the deliverable of
Phases 4 and 5. By translating to subject-centric coordinates, the body
footprint becomes range-independent: the same physical body produces the
same (dx, dy) distribution at 3 m and at 9 m. This is the M5 criterion
(dx_std = 0.141 m, confirmed range-independent across 4.19–5.17 m in the
Phase 4 audit).

The PCA ellipse encodes two body-shape descriptors per frame that are
the primary Phase 7 feature candidates:

- `rx` — lateral semi-axis (lateral half-width of body footprint)
- `ry` — range semi-axis (range half-depth of body footprint)
- `θ` — orientation of the major axis (aspect angle relative to boresight)

### PCA ellipse fitting

The ellipse is fitted to the body-cluster points only (not noise points)
using PCA on the 2×2 covariance matrix of (dx, dy):

```
cov = [[var(dx), cov(dx,dy)],
       [cov(dx,dy), var(dy)]]

eigenvalues  → 2σ radii:    rx = 2√λ_major,  ry = 2√λ_minor
eigenvectors → orientation: θ = atan2(v_major)
```

The 2σ boundary encloses approximately 86% of a 2D Gaussian
distribution. Outliers (points beyond 2.5σ of the median distance from
the centroid) are excluded from the fit before computing the covariance,
to prevent a single ghost point from stretching the ellipse.

Both semi-axes are clamped to a maximum of 0.50 m before drawing, per
the plan's requirement that the envelope stays within human body bounds.

### The dx_std metric (M5 acceptance criterion)

```
dx_std = std(dx across all cluster points in current buffer)
       = 0.141 m  (measured, full 16-frame window)
```

This value is the normalised lateral spread — the radar's effective
measurement of body half-width after accumulation. It is range-independent
because the subject-centric translation removes the range-proportional az
bin size effect. The theoretical expectation for a shoulder width of
0.45 m sampled uniformly is 0.45 / (2√3) = 0.130 m; the observed 0.141 m
is consistent with body slightly wider than pure shoulder span (arms,
clothing) and az FFT bin-level quantisation.

### What correct output looks like

During radial walking with a full 16-frame buffer: a compact cyan cluster
centred near (0, 0), spanning approximately ±0.14 m in dx and ±0.22 m
in dy. The amber ellipse should be stable frame-to-frame and orient with
its major axis aligned with dy (range direction) for frontal radial
walking — the body is deeper front-to-back than it is wide in this
aspect. The grey noise points (if any) should appear at larger |dx| or
|dy|, clearly separated from the cyan cluster.

During lateral walking (Scenario B): the cluster may appear narrower in
dx (body is seen side-on, presenting its front-to-back depth into the
range axis rather than its shoulder width). The ellipse should rotate:
θ shifts from ~0° (radial walk, major axis in dy) toward ~90° (lateral
walk, major axis in dx).

### Why overlapping points look like few points

The body footprint in subject-centric coordinates spans approximately
±0.14 m in dx and ±0.22 m in dy — a total area of 0.28 m × 0.44 m.
At a ±0.5 m panel extent with a typical display width of ~400 px, this
region occupies approximately 112 px × 176 px. With 58 cyan points at
8 px each, the overlap is heavy. The semi-transparent rendering (α = 160)
means overlapping points accumulate brightness, giving a density
impression rather than individual dot counting. This is not missing
data — every point is rendered.

### Failure modes

| Symptom | Cause | Check |
|---|---|---|
| Ellipse rx > 0.50 m (clamped at boundary) | Ghost point survived cluster gate, or rapid lateral motion during EMA lag | `cluster_noise` count; check if `max_cluster_radius` is being respected |
| Cluster not centred at (0, 0) | Centroid offset — EMA not yet converged | Expected in first 4–8 frames; check if persists beyond warm-up |
| Ellipse orientation does not change between radial and lateral | Subject-frame translation using wrong centroid | Verify `subject_frame_en = True` in config |
| Only grey points, no cyan | DBSCAN found no cluster (cluster_pts = 0) | Subject may be outside range, or DBSCAN eps too small |
| Panel blank | `subject_frame_en = False` | Enable in radar_config.py |

---

## Panel 5 — Doppler-time spectrogram

**Processing stage:** Phase 6 (micro-Doppler extraction and cadence
estimation via MicroDopplerBuffer)

**Position in viewer:** rightmost (5th panel), 2D image + overlay curves

### What is rendered

A Doppler-time spectrogram rendered as a `pyqtgraph.ImageItem`:

```
Horizontal axis:  time, 64 frames = 16 s, oldest left → newest right
Vertical axis:    Doppler velocity, −1.5 to +1.5 m/s
Cell value:       count of cluster points in that (Doppler bin, frame),
                  normalised to [0, 1] per column
Bin resolution:   75 mm/s per bin  (40 bins across ±1.5 m/s)
```

Each column is the Doppler histogram of the DBSCAN body-cluster for
that frame — how many cluster points fell into each 75 mm/s Doppler
bin. Column-wise normalisation (each column divided by its maximum) means
the display shows relative Doppler distribution per frame rather than
absolute point counts. This prevents a high-point-count frame from
visually dominating.

**Overlays:**
- Amber curve — `torso_line`: the power-weighted Doppler centroid
  (`dop_centroid`) plotted across all 64 time columns. This is the
  first moment of the column's Doppler distribution, equivalent to the
  spectral centroid of the marginal Doppler density per frame.
- Two dashed blue lines at ±0.30 m/s — the `dop_limb_thr` boundary
  separating torso returns (|dop| < 0.30 m/s) from limb returns
  (|dop| ≥ 0.30 m/s).
- Zero line at 0 m/s — stationary reference.

**Cadence annotation (top left):**
```
cadence ≈ 1.0 Hz  (1.0s/stride)
```
or
```
filling… (24/64 frames)
```
or
```
cadence: no clear peak
```

### Why this panel exists

The Doppler-time spectrogram is the canonical micro-Doppler feature in
radar-based gait analysis, introduced by Chen and Ling (2002). It
externalises the temporal Doppler structure that is invisible in
per-frame scalar statistics. Three specific properties are readable
directly from the waterfall that no single-frame metric captures:

**1. Direction reversal.** At each turnaround the amber torso line
crosses zero — from positive (walking away) to negative (returning) or
vice versa. The time between successive zero-crossings is half the
out-and-back period. This is the most direct visual confirmation that
the Doppler sign convention is correct end-to-end.

**2. Speed change.** When the subject changes pace (Scenario D), the
torso line shifts to a new Doppler level and the spectrogram column
distribution changes width. The transition is visible as a gradual
shift because the 16-frame EMA centroid takes ~2.3 frames (0.6 s) to
track a step change in speed.

**3. Limb-swing periodicity.** During steady-state walking, the
spectrogram shows a periodic brightening above the 0.30 m/s limb
boundary as the swinging arm or leg produces a high-Doppler return every
stride. This periodicity is what the cadence estimator quantifies.

### Cadence estimation

The cadence is estimated from the normalised autocorrelation of the
`limb_frac` time series — the fraction of cluster points with
|dop| ≥ 0.30 m/s per frame, sampled at 4 fps across the 64-frame buffer:

```
limb_frac[t] = n_limb_pts[t] / cluster_pts[t]

AC[lag] = corr(limb_frac, shifted limb_frac by lag frames) / AC[0]

peak_lag = argmax(AC[lag_min : lag_max])
         where lag_min = fps / cadence_max = 4/3.0 ≈ 1 frame
               lag_max = fps / cadence_min = 4/0.3 ≈ 13 frames

cadence_hz = fps / peak_lag
```

The limb_frac signal has a period equal to the stride cycle because limb
Doppler peaks twice per stride (once per swinging limb, for a biped with
two limbs) — but the practical detection is of the dominant periodicity
in the autocorrelation, which at 4 fps with a 64-frame window can
resolve cadences from 0.3 Hz (one stride every 3.3 s) to 3.0 Hz (three
strides per second, above any human walking rate).

The estimate updates every 8 frames (2 s). A minimum autocorrelation
peak height of 0.20 is required — below this the signal is treated as
aperiodic and NaN is returned.

### Minimum frames required for cadence

```
n_cycles_needed  = 4  (minimum for reliable periodicity detection)
At 1.0 Hz cadence:  4 cycles × 4 frames/cycle = 16 frames = 4 s
At 0.5 Hz cadence:  4 cycles × 8 frames/cycle = 32 frames = 8 s
```

The cadence annotation shows `filling…` until 16 frames are available.
After that, if no clear peak is found, it shows `no clear peak` rather
than a potentially spurious value.

### What correct output looks like

**Scenario A (radial walk, forward and back):** The waterfall shows a
bright band centred on the walking speed (~0.4–0.5 m/s) during the
outward leg, and the amber torso line traces through that band. At each
turnaround the torso line crosses zero and the bright band flips sign.
After ~16 s (64 frames), the cadence annotation stabilises at
approximately 0.8–1.1 Hz depending on the subject's natural pace.

**Scenario B (lateral walk):** The waterfall is nearly blank — nearly all
cluster points have Doppler near zero. The torso line sits near 0 m/s
throughout. The cadence annotation returns NaN. This is the correct
output for tangential motion and confirms the Doppler sign convention.

**Scenario D (multi-leg mixed speed):** The torso line oscillates between
positive and negative values at the walking speed, with the amplitude
shifting when the subject changes speed (normal → slow → fast). The
bright band in the waterfall changes its Doppler level with each speed
change. The cadence estimate changes with speed but lags the actual
change by approximately one autocorrelation update period (8 frames = 2s).

### Failure modes

| Symptom | Cause | Check |
|---|---|---|
| Waterfall blank, torso line at zero | No cluster detections or lateral walk | Panel 2 for cluster oval; is subject in radial or lateral scenario? |
| Cadence = NaN after 30+ active frames | `limb_frac` consistently low (< 0.1) | Subject walking tangentially; cadence unreliable for non-radial motion |
| Torso line does not cross zero at turnarounds | EMA lag smearing direction reversal | Expected — smear duration is ~2.3 frames (0.6 s) around each reversal |
| Cadence estimate unstable (changing each update) | Insufficient gait cycles in 64-frame window | Occurs at slow speeds (<0.5 Hz cadence, needs 32+ frames of steady walk) |
| Panel blank / not visible | `microdoppler_en = False` | Enable in radar_config.py |

---

## Cross-panel interpretation guide

The five panels are designed to be read together. A failure or anomaly
that appears in one panel usually has a complementary signature in one
or more others.

| Observation | Panel(s) | Diagnosis |
|---|---|---|
| Panel 1 has points, Panel 2 oval absent | 1, 2 | DBSCAN found no cluster — cluster_pts = 0. Subject may be outside corridor or eps too small for the cloud density |
| Panel 2 oval stationary while subject walks | 1, 2 | Centroid locked to a ghost return. Check cc_rej in audit; verify cross_cluster_range_m = 0.35m |
| Panel 3 single vertical stripe, no lateral spread | 3 | Az multi-peak not firing. Verify az_peak_min_prom_db = 6.0 dB (not 10.0 dB) |
| Panel 4 ellipse rx > 0.50 m (clamped) | 2, 4 | Ghost point survived DBSCAN or max_cluster_radius gate. Check cluster_noise in audit |
| Panel 4 cluster not at (0, 0) | 4 | EMA not yet converged — expected in first 8 frames of each run |
| Panel 5 blank waterfall during Scenario A | 1, 5 | No cluster detections — no Doppler data to histogram. Check cloud_pts > 0 first |
| Panel 5 cadence = NaN, Scenario A | 5 | limb_frac too low (subject walking tangentially or dop_limb_thr too high). For Scenario B this is expected |
| All panels populated but Panel 4 ellipse wrong shape | 4, 5 | Subject not walking radially — check orientation from Panel 3 and gait from Panel 5 |
| Temporal smear in Panel 1 at every turnaround | 1, 5 | Normal — direction reversal flush takes 16 frames. Torso line zero-crossing in Panel 5 is the precise marker |
| z values far from zero in Panel 1 | 1 | Radar height not applied. Adjust h_radar slider; use diag_xyz.py --radar-height to find correct value |

---

## Panel-to-pipeline-stage mapping

| Panel | Phase | Module | Key config fields |
|---|---|---|---|
| 1 — 3D cloud | Phase 2 | `accumulate.py` → `TemporalAccumulator` | `accum_window=16`, `accum_alpha=0.3` |
| 2 — X-Y footprint | Phase 3 | `accumulate.py` → `TemporalAccumulator._cluster()` | `dbscan_eps=0.80`, `dbscan_min_samples=3`, `max_cluster_radius=0.65` |
| 3 — X-Doppler | Phase 1 | `radar_processing.py` → `process_frame()` az multi-peak | `az_peak_min_prom_db=6.0`, `emit_all_cluster_bins=True` |
| 4 — Body-frame | Phase 4+5 | `accumulate.py` → `subject_frame()` + `fit_body_ellipse()` | `subject_frame_en=True`, `body_envelope_en=True` |
| 5 — Spectrogram | Phase 6 | `microdoppler.py` → `MicroDopplerBuffer` | `microdoppler_en=True`, `spectrogram_frames=64`, `spectrogram_v_max=1.5`, `dop_limb_thr=0.30` |

---

## Status bar

The status bar below the panels shows per-frame gait scalars from
`GaitFeatures` when `gait_features_en = True`:

```
Frame 142  |  pts (accum×16(motion-comp)): 64  vy=+0.42m/s
           |  vc=+0.42m/s  σ=0.18  limb=65%
           |  radar h: 0.33m  |  dropped: 0
```

| Field | Source | Meaning |
|---|---|---|
| `pts` | `len(accum_result.cloud)` | Total accumulated cloud size (all 16 frames) |
| `vy` | `accum_result.velocity_y` | EMA-derived radial velocity estimate (m/s) |
| `vc` | `gait.dop_centroid` | Power-weighted Doppler centroid of body cluster (trunk velocity, m/s) |
| `σ` | `gait.dop_spread` | Std of cluster Doppler values (velocity diversity, m/s) |
| `limb%` | `gait.limb_frac` | Fraction of cluster pts with \|dop\| ≥ 0.30 m/s |

`vc` and `vy` should agree in sign during steady radial walking and
both cross zero at the same direction reversal. A discrepancy between
`vc` and `vy` indicates the EMA centroid is lagging the actual speed —
the power-weighted Doppler centroid (`vc`) responds instantaneously,
while the EMA velocity (`vy`) lags by ~2.3 frames.

---

*For the processing pipeline implementation see `processing/accumulate.py`,
`processing/microdoppler.py`, and `processing/streaming.py`.
For the full phase development roadmap see `testing\live_capture_validation\audit_and_improvement_plan/08_generated_plan_human_body_shape_perception_implementation.md`.*
