This is exactly the right inflection point. Here is a structured outdoor test plan you can take directly to the end users.

---

## Outdoor Test Plan — AWR2243-2X Cascade Radar

### Pre-Test Checklist

**Hardware**
- Laptop (RTX 3080 Ti) + radar mount at a fixed height (recommend 1.0–1.5 m above ground, level)
- DCA1000EVM connected via Ethernet, COM20 UART confirmed
- Power bank or mains supply — outdoor sessions drain battery fast with GPU load
- Measuring tape or laser measure for ground truth distances
- Reflective vest or corner reflector for controlled target tests

**Software — confirm before leaving the lab**
```bash
python live_capture.py --display pointcloud   # 3D cloud, confirm detections visible
python live_capture.py                         # heatmap mode, confirm RD/RA plots render
python live_capture.py --skip-load             # quick restart without firmware reload
```
Confirm `avg_latency ≈ 200 ms` and `cloud:N > 0` when a person walks past.

---

### Test Scenarios

**Scenario 1 — Single person, known range**
Walk a person toward the radar along boresight (0° azimuth) from 15 m to 1 m. Stop at 2 m, 5 m, 10 m and hold for 5 seconds. Record whether the point cloud correctly shows range and whether velocity sign is correct (approaching = blue dot).

*What to validate:* range accuracy vs tape measure, Doppler colour coding, minimum detectable range.

**Scenario 2 — Multiple people, crossing paths**
Two people walk toward each other from opposite sides of the field of view (approximately ±30° azimuth). They pass through the centre and continue.

*What to validate:* can the system resolve two simultaneous targets? Do the point clouds split correctly in azimuth? Do they merge and separate cleanly?

**Scenario 3 — Slow and stationary targets**
One person stands still at 5 m. A second person walks slowly (< 0.5 m/s) at 8 m. A bicycle passes at 10 m.

*What to validate:* CFAR sensitivity at low velocity. The `dop_max = ±2.498 m/s` waveform config means a walking person at 1.5 m/s uses roughly 60% of the unambiguous Doppler range — check that slow walkers are not missed. Stationary clutter rejection.

**Scenario 4 — Oblique angle and azimuth coverage**
Person walks perpendicular to boresight (pure lateral motion) at 5 m range. Pure lateral motion has near-zero radial Doppler — this is the hardest case for the pipeline.

*What to validate:* does the RA heatmap still show the target even when Doppler is near zero? Does CFAR detect them? The `moving_objects_only` gate may suppress these — note it for post-test tuning.

**Scenario 5 — Clutter and false alarm rate**
No people in the scene. Swaying trees, parked cars, fences in the field of view. Run for 2 minutes and count `cloud:N` events.

*What to validate:* false alarm rate in a realistic outdoor environment. If `cloud:N > 0` frequently with no people present, CFAR thresholds need tightening for this environment.

**Scenario 6 — Range stress test**
Single person at maximum range — walk from 16 m toward the radar. Note the range at which they first appear reliably in the point cloud.

*What to validate:* effective detection range vs the theoretical 16.8 m maximum. Outdoor path loss and ground multipath typically reduce this by 20–40%.

---

### Metrics to Record Per Scenario

For each scenario, note:

| Metric | How to measure |
|---|---|
| Detection range (first/last) | Visual from display + tape measure |
| False cloud points with no target | Count `cloud:N` events on terminal |
| Point cloud stability | Does the dot hold position or jitter? |
| Azimuth accuracy | Compare display azimuth to physical angle |
| Velocity sign correctness | Blue = approaching, red = receding |
| Display update feel | Does the 3D view feel responsive to users? |
| Missing detections | Target visible in heatmap but cloud:0 |
| Avg latency | Terminal `avg_latency=` at session end |

---

### End-User Feedback Questions

Structure the feedback session around five questions. Written answers preferred over verbal.

**1. Detection usefulness** — When a person appeared in the 3D view, was the position information (range + left/right) accurate enough for your intended application?

**2. Update rate** — At ~200 ms latency (approximately 5 frames per second on the display), does the system feel fast enough? Or does it feel like it is lagging behind real movement?

**3. Range requirement** — The current config covers up to ~16 m. Is this sufficient, or do you need 30 m, 50 m, or longer range? (This drives a waveform reconfiguration.)

**4. Multi-target** — In the crossing-paths scenario, was it useful to see both people simultaneously? Would tracking (assigning IDs and trajectories to each dot) be required, or is raw point cloud enough?

**5. Platform preference** — Seeing the system running on a laptop, would the application require this to be embedded (small box, battery powered, no screen) or is a workstation form factor acceptable?

---

### What the Answers Drive

| Feedback | Next development phase |
|---|---|
| Latency feels too slow | Jetson Orin migration — Linux removes WDDM bottleneck, targets < 80 ms |
| Range insufficient | Waveform redesign — longer chirp, slower slope, trade Doppler for range |
| Multi-target tracking needed | Add point cloud tracker (simple Kalman or SORT algorithm) |
| Embedded deployment needed | Jetson Orin + C++ rewrite begins |
| Workstation is acceptable | Stay on Windows, optimise CFAR parameters for outdoor environment |
| False alarm rate too high | Tune `cfar_margin_db`, `el_peak_prominence_db`, add velocity gate |
| False alarm rate too low | Lower `cfar_margin_db`, reduce `cfar_fa_rate` |

---

### Quick Parameter Adjustments Available On-Site

If the outdoor environment shows obvious issues during the test, these can be tuned live by editing `cascade_shortrange.cfg` or the CLI flags — no code changes required:

```bash
# Stricter CFAR if too many false alarms from foliage/clutter
python live_capture.py --cfar-margin 15

# Match firmware CFAR exactly (CASO, no guard, 16-cell window)
python live_capture.py --cfar caso --cfar-guard 0 0 --cfar-train 16 16

# If slow walkers are missed — disable velocity gate
# (edit cfg: moving_objects_only = false, or add --no-vel-gate if wired)
```

Good luck with the outdoor test — the feedback from this session will give you everything needed to write a concrete specification for the next phase.