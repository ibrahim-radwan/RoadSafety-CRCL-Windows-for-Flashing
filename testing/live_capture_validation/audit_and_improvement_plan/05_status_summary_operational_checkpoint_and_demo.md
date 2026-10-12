## Demo Checkpoint Summary

### What the System Does Today

The AWR2243-2X cascade radar pipeline is fully operational with live streaming display. A target in front of the radar appears as a bright region on three simultaneously updating heatmaps — Range-Doppler (showing velocity), Range-Azimuth (showing lateral position), and Range-Elevation (showing height). The system runs on a Windows laptop with a consumer GPU.

**Two operating modes:**

```bash
python live_capture.py              # Full pipeline — heatmaps + detection markers + point cloud
python live_capture.py --no-cfar   # Heatmap display only — faster, smoother
```

---

### Current Performance Baseline (Windows, RTX 3080 Ti)

| Metric | With CFAR | `--no-cfar` |
|---|---|---|
| Avg frame latency | 318 ms | 269 ms |
| Frame period budget | 256 ms | 256 ms |
| Real-time coverage | ~81% | ~96% |
| Drop rate | ~6.9/frame | ~6.9/frame |
| Max latency spike | ~580 ms | ~391 ms |
| Heatmap display | ✓ | ✓ |
| Detection markers | ✓ | ✗ |
| Point cloud output | ✓ | ✗ |

The pipeline processes roughly 1 in every 8 hardware frames. The remaining 7 are dropped while the processor handles the previous frame. All DSP stages (range FFT, Doppler FFT, azimuth beamforming, elevation beamforming, CFAR) are GPU-accelerated.

---

### What to Show End Users in the Demo

**Show `--no-cfar` first** — the heatmaps update visibly and smoothly at the display refresh rate. A person walking in front of the radar creates a clear moving bright region. This is the most intuitive demonstration of the sensor working.

**Then switch to full CFAR mode** — show the detection markers appearing over the target and point cloud coordinates being extracted. This demonstrates the detection capability even if the refresh feels slightly less smooth.

**Key things to ask end users:**

1. **Update rate** — does the display feel acceptably smooth, or does it need to be faster? Their answer determines whether 4 fps radar + partial processing is sufficient or whether a higher frame rate config is needed.

2. **Detection vs heatmap** — do they need real-time point cloud coordinates (requires CFAR), or is visual heatmap display sufficient for their use case?

3. **Range and field of view** — is the 16.8 m max range and ±60° azimuth coverage sufficient, or do they need to reconfigure the waveform?

4. **Deployment environment** — indoor lab, outdoor, vehicle-mounted, embedded edge? This directly determines the platform decision.

5. **Latency sensitivity** — does 250–400 ms end-to-end processing delay matter for their application, or is it acceptable?

---

### The Three Platform Paths Forward

The end-user feedback will map directly onto one of these:

**Path A — Stay on Windows, optimise further.** Suitable if: the demo feels fast enough, deployment is on a Windows workstation, and detection markers are not needed in real-time. Remaining work: suppress the WDDM period-3 pattern (requires a custom CUDA kernel bypassing CuPy), or accept current performance. Python codebase stays as-is.

**Path B — Migrate to NVIDIA Jetson (Orin).** Suitable if: the system needs to be embedded, portable, or power-constrained, and target latency is under 100 ms. Jetson runs Linux with CUDA in native mode — the WDDM scheduler issue disappears entirely. The existing Python/CuPy codebase is directly portable to Jetson with minimal changes (same CUDA APIs). Expected performance on Orin: sub-100 ms per frame, true real-time at 4 fps with headroom.

**Path C — C++ rewrite for production.** Suitable if: the system needs to be a certified, deployable product with deterministic real-time guarantees, minimal CPU overhead, and integration into a larger system (ROS, automotive stack, industrial PLC). Timeline is 3–6 months. The Python pipeline serves as the algorithm reference implementation — all DSP stages are already validated and can be ported stage-by-stage.

These paths are not mutually exclusive: B and C often go together (Jetson + C++ with CUDA).

---

### Recommendation for the Demo

Run `--no-cfar --quiet` so the terminal is clean, then switch to full CFAR with a live target to show detections. Record the session to compare display smoothness and detection quality across scenarios. Collect the five feedback questions above in writing — the answers will make the platform decision straightforward.