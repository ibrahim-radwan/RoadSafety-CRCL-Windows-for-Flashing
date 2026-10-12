# AWR2243-2X Radar — Data Collection Plan

**Purpose:** build the multi-subject, multi-scenario dataset required to
begin Phase 7 (pose descriptors and gait-based identification) of
`09_action_plan_outdoor_body_shape_data_collection.md`.

**Minimum viable dataset:** 20–30 sequences across ≥ 3 subjects before
Phase 7 work begins. All four scenarios below must be represented.

---

## Hardware and Environment Constraints

| Parameter | Value | Implication |
|---|---|---|
| Max Doppler | ±2.498 m/s | Max walking speed ≈ 2.5 m/s (9 km/h); covers all human gaits |
| Max range | 16.8 m | Keep subjects within 10 m for reliable SNR |
| Range resolution | 6.6 cm | Body depth (30 cm) spans ~5 range bins |
| Az resolution at 3 m | 2.3 cm/bin | Shoulder width (45 cm) spans ~20 az bins |
| Az resolution at 8 m | 6.3 cm/bin | Shoulder width spans ~7 az bins |
| Frame rate | 4 fps | 16-frame accumulation window = 4 seconds of history |
| Accumulator warm-up | 16 frames = 4 s | First 4 s of each run produces a partial cloud |
| Cadence detection | ≥ 4 gait cycles | At 1 Hz cadence: need ≥ 4 s continuous walking after warm-up |

### Minimum space required

All scenarios fit in a standard outdoor car park lane or open courtyard:

```
← 12 m →
┌─────────────────────────────┐  ↑
│  [RADAR]                    │  6 m
│  3m  5m  7m  9m             │  ↓
└─────────────────────────────┘
  P1   P2  P3   P4
```

Mark positions P1–P4 with cones or tape before each session.

---

## Scenario A — Radial Walk (Out and Back)

**Purpose:** primary body-shape dataset. Captures how the radar body
envelope (`cluster_radius_x`, `subject_spread_x`) and gait signature
(`dop_centroid`, `cadence_hz`) vary across different individuals under
identical controlled conditions.

**Priority:** 1 — collect first.

**Design principle:** every variable except the person is held constant.
Speed, axis, and range are the same for every session. Any differences
observed between sessions are attributable to inter-subject body shape
and natural gait variation. Speed variation is covered by Scenario D,
which every subject also completes.

### Session parameters

| Parameter | Value |
|---|---|
| Subjects per session | 1 — **one subject per session, 3 subjects to start** |
| Sessions total | 3 initial (S01–S03); expand to 5 if inter-subject variation is confirmed |
| Runs per session | 1 continuous 90 s run (add a 2nd run for redundancy if time allows) |
| Duration per run | 90 s |
| Session duration   | 90 s |

### Walking pattern

```
RADAR
  ║
  ║   ← 6 m walk corridor →
  ║
  ↓
[P1]───────────────────[P4]
 3m                     9m
 START / RETURN          TURN POINT

Per 90 s run:
  1. Subject stands at P1 (3 m from radar), facing away from radar.
  2. Walks away at their natural normal pace to P4 (9 m).        ~7 s
  3. Pauses at P4 for 2–3 s, turns around naturally.
  4. Walks back toward radar to P1 (3 m).                        ~7 s
  5. Pauses at P1 for 2–3 s, turns around.
  6. Repeats continuously for the full 90 s.
     → Expected: ~5 full out-and-back cycles per 90 s run.
  7. Operator calls "stop" at 90 s and saves the recording.
```

**Direction:** out-and-back, repeated continuously. NOT forward-only.
Both directions are required to:
- Validate positive Doppler (walking away) and negative Doppler (returning)
- Produce the spectrogram sign-flip at each turnaround
- Give the cadence autocorrelation multiple complete gait cycles

**Speed:** each subject walks at their own natural comfortable pace — do
NOT instruct a target speed. Natural cadence varies between people and
that variation is part of the inter-subject data. Record the actual
speed by timing a 6 m segment with a stopwatch during the run.

### Session table

| Session | Subject | Height | Build | Notes |
|---|---|---|---|---|
| A-S01 | S01 | record cm | record | Baseline — same subject as existing 400-frame clip |
| A-S02 | S02 | record cm | record | Inter-subject comparison |
| A-S03 | S03 | record cm | record | Inter-subject comparison |
| A-S04 | S04 | record cm | record | Add if S01–S03 show clear inter-subject variation |
| A-S05 | S05 | record cm | record | Add if S01–S03 show clear inter-subject variation |

Aim for visible height/build variation across the 3 subjects. At minimum:
one subject above 180 cm and one below 170 cm.

### Expected pipeline output

| Metric | Expected range |
|---|---|
| `dop_centroid` | +0.3 to +0.5 m/s (walking away), −0.4 to −0.6 m/s (returning) |
| `limb_frac` | 0.6–1.0 during radial walk |
| `cadence_hz` | 0.8–1.1 Hz — varies naturally by subject |
| `cluster_radius_x` | 0.40–0.50 m |
| `subject_spread_x` | 0.12–0.18 m — the body-width signature, compare across subjects |
| Spectrogram | Clear sign-flip in amber torso line at each turnaround |

### Notes

- The 2–3 s pause at each end is important. It allows the 16-frame
  accumulator window to begin flushing the previous direction's Doppler
  before the new direction dominates the centroid.
- At natural pace (~1.2 m/s), one 6 m leg takes ~5 s = 20 frames.
  The accumulator fills within the first two legs, so the spectrogram
  and body-frame panel are fully active from ~frame 32 onward.
- Scenario D handles speed variation — there is no need to ask
  subjects to walk slow or fast in Scenario A.

---

## Scenario B — Lateral Walk (Perpendicular to Boresight)

**Purpose:** test the body-shape pipeline without the Doppler velocity
signal, and capture the body's side profile. Lateral walking produces
near-zero radial Doppler — the body envelope, subject-frame spread, and
DBSCAN cluster must work on geometry alone.

**Priority:** 3 — collect after Scenarios A and D.

### Your understanding — confirmed

> Subject stands 3 metres from the radar, then moves right and left
> across a 6 metre wide corridor.

That is exactly right. The radar looks straight ahead (boresight). The
subject walks across that line of sight at a fixed 3 m distance, going
right and left repeatedly across a 6 m wide corridor.

### Session parameters

| Parameter | Value |
|---|---|
| Subjects per session | 1 — one subject per session |
| Sessions total | 3 — **same 3 subjects as Scenarios A and D** (B-S01, B-S02, B-S03) |
| Runs per session | 1 continuous run |
| Duration per run | 90 s (~7 full left-right cycles) |
| Session duration   | 90 s |

90 s is recommended because the accumulator warm-up consumes the first 4 s
and lateral Doppler is weak, so more cycles give a more robust geometric
sample. 60 s is the minimum acceptable (gives ~5 full cycles).

### Walking pattern

```
  Subject always stays at 3 m from radar — never moves closer or further

                ← 6 m corridor (±3 m from boresight) →

  RADAR ════════════════╦════════════════ (boresight)
    │                   │
    │ 3 m               │
    │                   ↓
    │         [CENTRE — boresight crossing]
    │
    subject walks ←LEFT    RIGHT→ along this line

  [LEFT CONE]──────────[CENTRE]──────────[RIGHT CONE]
     −3 m                 0                  +3 m

Per 90 s run:
  1. Subject stands at LEFT CONE (−3 m from boresight, 3 m from radar).
  2. Walks RIGHT at normal pace to RIGHT CONE (+3 m).              ~5 s
  3. Pauses 1–2 s at RIGHT CONE, turns around.
  4. Walks LEFT back to LEFT CONE.                                  ~5 s
  5. Pauses 1–2 s at LEFT CONE, turns around.
  6. Repeats continuously for the full 90 s.
     → Expected: ~7 full left-right cycles per 90 s run.
  7. Operator calls "stop" at 90 s.
```

**Direction:** left-right-left, repeated at a fixed 3 m distance from
the radar. The subject does NOT move toward or away from the radar.

**Speed:** natural comfortable pace — same instruction as Scenario A.

### FOV check

The radar's azimuth FOV at 3 m range is ±5.2 m (±60°). The 6 m corridor
(±3 m) sits comfortably within this. Do not extend the corridor beyond
±4 m — the subject may begin to exit the FOV at the extremes.

### Session table

| Session | Subject | Purpose |
|---|---|---|
| B-S01 | Same as A-S01 | Frontal vs lateral body shape comparison — known subject |
| B-S02 | Same as A-S02 | Inter-subject lateral body shape variation |
| B-S03 | Same as A-S03 | Inter-subject lateral body shape variation |

If time allows after all Scenario A and D sessions, extend to B-S03
All 3 subjects run Scenario B so every subject has frontal (A) and lateral (B) data.

### Expected pipeline output

| Metric | Expected |
|---|---|
| `dop_centroid` | Near zero (±0.05–0.10 m/s) throughout |
| `limb_frac` | Low (0.0–0.2) — limb Doppler also near-zero for lateral walk |
| `cadence_hz` | NaN — limb_frac too low for autocorrelation (expected, not a failure) |
| `cluster_cx` | Should drift smoothly from −3 m to +3 m and back, tracking the subject |
| `cluster_radius_x` | May differ from Scenario A — radar sees side profile, not frontal |
| `subject_spread_x` | Compare to A-S01 to quantify frontal vs side profile difference |
| Spectrogram | Flat amber torso line near zero; blank waterfall; no sign-flip |

### Notes

- The `cluster_cx` column in `frames.csv` is the key diagnostic for this
  scenario. It should show the centroid drifting smoothly left and right
  as the subject crosses the FOV, confirming the DBSCAN cluster is
  tracking correctly across azimuth.
- The near-zero Doppler means cadence will return NaN every run. This
  is expected and correct — do not attempt to interpret it.
- Place cones or tape at three positions: LEFT CONE (−3 m from boresight),
  CENTRE (0), RIGHT CONE (+3 m), all at the same 3 m distance from the
  radar. The subject walks between cones without looking at the radar.
- The radar sees the subject's side profile here. The body envelope may
  appear different to Scenario A because the body is thinner front-to-back
  than shoulder-to-shoulder. This difference is the scientific output of
  the scenario.

---


## Scenario C — Stand Still, Then Walk

**Purpose:** test track initialisation from stationary and the pipeline's
behaviour at the stationary-to-walking transition. Validates that the
moving-target gate, DBSCAN, and EMA centroid all initialise correctly from
a cold start each time the subject begins moving.

**Priority:** 4 — collect last.

### Session parameters

| Parameter | Value |
|---|---|
| Subjects per session | 1 — one subject per session |
| Sessions total | 3 — **same 3 subjects as Scenarios A and D** (C-S01, C-S02, C-S03) |
| Runs per session | 1 continuous run (add a 2nd for redundancy if time allows) |
| Duration per run | 60 s (3 complete cycles) |
| Session duration   | 60 s |

**Why 60 s and not 90 s:** each cycle is ~18 s (8 s standing still at 4m
+ 4 s walk out to 9m + 2 s turn + 4 s walk back to 4m). At 60 s you get
3 complete stationary-to-walking transitions — the minimum for a reliable
average of the pipeline initialisation lag. Going to 90 s adds only one
more cycle at the cost of an extra 30 s, 8 s of which is standing still.
60 s is the efficient choice for this scenario.

### Walking pattern

```
RADAR
  ║
  ║  ← 4 m → [STAND POINT]
  ║
  ↓

Timeline per cycle (repeat 3–4 times per run):

  [0s]    Subject arrives at STAND POINT (4 m from radar)
           Arms at sides. No fidgeting. No talking.
  [0–8s]  Stands completely still
  [8s]    Begins walking away toward 9 m (P4)
  [20s]   Reaches 9 m, turns around, walks back
  [32s]   Returns to STAND POINT
  [32–40s] Stands still again (arms at sides)
  [40s]   Next cycle begins
```

**Direction:** stationary → away → toward → stationary, repeated.
The still phases are as important as the walking phases.

### Variations across sessions

| Session | Subject | Stand duration | Purpose |
|---|---|---|---|
| C1 | Any | 8 s | Standard — tests nominal initialisation time |
| C2 | Any | 4 s | Short still phase — tests rapid start/stop |

### Expected pipeline output

| Metric | Stationary phase | Walking phase |
|---|---|---|
| `cloud_pts` | 0 or very low (< 2) | 2–5 per frame |
| `accum_pts` | 0 | Builds to 25+ over first 16 frames |
| `dop_centroid` | NaN (no cluster) | ±0.3–0.5 m/s |
| `cluster_pts` | 0 | 25+ once accumulator fills |
| Spectrogram | Blank columns | Populates from left to right |

### Notes

- The key analysis metric is the **initialisation lag**: how many frames
  after the subject starts walking does the DBSCAN cluster first appear?
  This should be ≤ 16 frames (one accumulator window).
- Note the exact frame number when walking begins (visible in the viewer
  status bar) for each cycle. Record in the session log.
- A stationary person may still produce occasional false detections. The
  audit CSV `cluster_pts` column should show 0 for > 90% of stationary
  frames. If it shows regular detections during the still phase, the
  CFAR margin or the moving-Doppler gate may need adjustment.

---

## Scenario D — Multi-Leg Mixed Speed

**Purpose:** produce the maximum number of Doppler sign-flips and speed
transitions in one recording. Designed to stress-test the spectrogram
direction-change behaviour and give the cadence autocorrelation the richest
possible signal.

**Priority:** 2 — collect second, immediately after Scenario A.

### Session parameters

| Parameter | Value |
|---|---|
| Subjects per session | 1 — one subject per session, **same 3 subjects as Scenario A** |
| Sessions total | 3 initial (D-S01 through D-S03); expand to 5 alongside Scenario A expansion |
| Runs per session | 1 continuous run (add a 2nd for redundancy if time allows) |
| Duration per run | 90 s (~2 full speed sequences + partial third) |
| Session duration   | 90 s |

### Walking pattern

```
RADAR
  ║
  ║   ← 6 m →
  ║
  ↓
[P1]──────────[P4]
 3m            9m

One speed sequence (6 legs, ~40 s):

  Leg 1: P1→P4  NORMAL speed  (~1.2 m/s,  ~5 s)
  Leg 2: P4→P1  NORMAL speed  (~1.2 m/s,  ~5 s)
  Leg 3: P1→P4  SLOW speed    (~0.7 m/s,  ~9 s)
  Leg 4: P4→P1  SLOW speed    (~0.7 m/s,  ~9 s)
  Leg 5: P1→P4  FAST speed    (~1.8 m/s,  ~3 s)
  Leg 6: P4→P1  FAST speed    (~1.8 m/s,  ~3 s)

In a 90 s run: repeat the full sequence continuously until the
operator calls "stop". This gives ~2 complete sequences plus a
partial third (~13–15 direction changes total).

1 s pause at each end to turn around. No long stationary phases.
```

**Direction:** continuous out-and-back. Each speed is done in both
directions (out AND back) before moving to the next speed. The subject
does NOT stop walking except for the 1 s turn at each end.

**Speed:** the subject sets their own natural slow/normal/fast paces.
Do not prescribe exact speeds. Record the actual speed per leg by timing
a 6 m segment with a stopwatch during the first sequence, then log it.

### Session table

| Session | Subject | Purpose |
|---|---|---|
| D-S01 | Same as A-S01 | Spectrogram validation — known subject, compare cadence to Scenario A |
| D-S02 | Same as A-S02 | Inter-subject cadence at matched speeds |
| D-S03 | Same as A-S03 | Inter-subject cadence at matched speeds |
| D-S04 | Same as A-S04 | Add when A-S04 session is collected |
| D-S05 | Same as A-S05 | Add when A-S05 session is collected |

### Expected pipeline output

| Metric | Expected |
|---|---|
| `dop_centroid` sign-flips | 6 per sequence (one per leg transition) |
| `cadence_hz` at normal | ~0.9 Hz |
| `cadence_hz` at slow | ~0.5 Hz |
| `cadence_hz` at fast | ~1.3 Hz |
| Spectrogram | Clear oscillating torso line; three distinct Doppler amplitude levels |
| `limb_frac` | 0.7–1.0 throughout — all walking phases are radial |

### Notes

- The speed transitions (normal → slow → fast → repeat) should be
  visible in the spectrogram as changes in the torso-line amplitude.
- The cadence estimate changes with speed. Because the autocorrelation
  operates over the last 64 frames (16 s), it takes ~8 s after a speed
  change for the cadence estimate to reflect the new speed.
- This scenario produces the most sign-flips per minute of any scenario —
  12 turnarounds per 100 s run — which is the best signal for the
  cadence autocorrelation.

---

## Cross-Scenario Research Questions

After completing the dataset, the following questions can be answered
from `frames.csv` using the `diag_pipeline_audit.py` output:

| Question | Columns to compare | Scenario |
|---|---|---|
| Does body envelope width vary by subject height? | `cluster_radius_x` across A2, A3 | A |
| Does `subject_spread_x` scale with range? | `subject_spread_x` vs `cluster_cy` | A, D |
| Does cadence estimate match known walking speed? | `cadence_hz` vs manually timed speed | A, D |
| Does the side profile (lateral walk) differ from frontal? | `cluster_radius_x` in B1 vs A1, same subject | A, B |
| How many frames after walking begins does the cluster appear? | `cluster_pts` > 0 frame index in C1 | C |
| Is cadence reproducible across sessions for the same subject? | `cadence_hz` across A1 and D1 | A, D |

---

## Session Log Template

Fill in for every session before analysis.

```
Session ID    : ___________          (e.g. A2_2026-07-01)
Date / Time   : ___________
Location      : ___________          (e.g. car park west, open courtyard)
Scenario      : A / B / C / D
Subject ID    : ___________          (e.g. S01, S02 — do not use real names)
Subject height: ___ cm
Build         : slim / medium / heavy
Speed         : slow / normal / fast / mixed
Axis offset   : boresight / +15° / +30°
Radar height  : ___ cm               (measure from ground to antenna centre)
Temperature   : ___ °C
Weather       : ___________          (clear / overcast / light wind / etc.)
Frame range   : fr ___ to fr ___     (from live_capture.py status bar)
n_runs        : ___
Notes         : ___________          (interference, missed passes, etc.)
```

---

## Per-Session Checklist

### Before recording

- [ ] Mark P1 (3 m), P2 (5 m), P3 (7 m), P4 (9 m) from radar with cones/tape
- [ ] Measure and record radar mounting height (cm)
- [ ] Confirm no moving vehicles or pedestrians in background arc ±60°
- [ ] Confirm clear line of sight from radar to P4 (9 m)
- [ ] Run 5-frame test capture: `python live_capture.py --replay ... --frames 5`
- [ ] Confirm viewer shows detections during a brief test walk
- [ ] Set `--radar-height` in config or CLI to the measured mounting height
- [ ] Confirm recording output directory is empty or correctly named

### During recording

- [ ] Operator watches live viewer status bar during each run
- [ ] Note frame number when subject begins first walk (Scenario C only)
- [ ] Call out if subject accidentally walks outside P1–P4 corridor
- [ ] 1 s verbal cue to subject before each speed change (Scenario D)

### Immediately after recording

```powershell
python diag_pipeline_audit.py `
    --folder  capture\frames `
    --cfg     config\build_shortrange_inf\cascade_shortrange.cfg `
    --temporal-accum --accum-window 16 --subject-frame --gait-features `
    --out-dir debug_context\SESSION_ID
```

- [ ] Review `summary.txt`: confirm `Frames with cloud>0` ≥ 75%
- [ ] Review `cluster_pts` column: confirm median ≥ 20 in active segments
- [ ] Review `dop_centroid` column: confirm sign matches walking direction (Scenario A, D)
- [ ] If any check fails: identify cause before packing up hardware

---

## Subject Recruitment

### Minimum requirements

- ≥ 3 different subjects total across the full dataset
- At least one subject taller than 180 cm, one shorter than 170 cm
- Subjects should be able to walk at a controlled slow/normal/fast pace
  without significant gait irregularity

### Subject information to record (no identifiers)

- Subject ID (S01, S02, …)
- Height (cm)
- Build category (slim / medium / heavy)
- Approximate age band (18–30 / 31–50 / 51+)
- Any gait aid or notable gait pattern (e.g. leg prosthetic, limp)

### Privacy

- Do not record names or any personally identifying information
- Subject IDs are internal project labels only
- Inform all subjects that radar data (not video) is being recorded

---

## Dataset Target Summary

| Scenario | Min sessions | Subjects | Total runs | Total duration |
|---|---|---|---|---|
| A — Radial walk | 3 initial (up to 5) | **3 subjects, 1 session each** | 3–5 runs | ~35 min |
| B — Lateral walk | 3 | **same 3 subjects as A** | 3 runs | ~30 min |
| C — Stand + walk | 3 | **same 3 subjects as A** | 3 runs | ~30 min |
| D — Multi-leg | 3 initial (up to 5) | **same 3 subjects as A** | 3–5 runs | ~35 min |
| **Total** | **12** | **3 subjects, all 4 scenarios** | **12 runs** | **16.5 min total recording** |

Total recording time: 16.5 min (990 s across 12 runs).
Setup (cones, radar check, log) happens once before all sessions, not per session.

At 4 fps and 90 s per run: each run ≈ 360 frames.
Total dataset with 3 subjects across all 4 scenarios:
~12 runs × 360 frames = **~4 320 frames** (A+D) + ~540 frames (B+C) = **~4 860 frames total**.
Expand to 5 subjects for ~8 100 frames if Phase 7 needs more data.

Each of the 3 subjects does both Scenario A (normal pace, boresight) and
Scenario D (slow/normal/fast mixed legs). This gives clean within-subject
speed variation (Scenario D) and clean between-subject shape comparison
(Scenario A), without confounding the two.

---

## File Naming Convention

```
capture\sessions\SCENARIO_SESSIONID_SUBJECTID\frames\frame_NNNNNN.bin
capture\sessions\A1_2026-07-01_S01\frames\frame_000000.bin
capture\sessions\A1_2026-07-01_S01\frames\frame_000001.bin
...

Audit outputs:
debug_context\A1_2026-07-01_S01\frames.csv
debug_context\A1_2026-07-01_S01\points.csv
debug_context\A1_2026-07-01_S01\summary.txt
```

---

## Replay for Verification

Any recorded session can be replayed through the full pipeline:

```powershell
python live_capture.py `
    --replay capture\sessions\A2_2026-07-01_S02\frames `
    --cfg    config\build_shortrange_inf\cascade_shortrange.cfg `
    --display pointcloud --replay-fps 0.5 --quiet
```

Use `--replay-fps 0.5` for detailed frame-by-frame inspection of the
accumulator filling, cluster formation, and spectrogram populating.
Use `--replay-fps 4.0` for real-time playback.

---

*This plan is a living document. Update session entries as recordings
are completed and add new scenarios as Phase 7 research questions emerge.*