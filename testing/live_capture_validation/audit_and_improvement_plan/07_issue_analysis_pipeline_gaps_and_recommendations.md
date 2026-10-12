## Section A — What Is Now Confirmed and Should Be Treated as Stable

These findings are closed. They should not be re-examined without new contradicting evidence.

**A1. Capture transport is clean.** Byte math is exact, frame sizes are consistent across all captures, zero read errors, zero UDP loss. The DCA1000EVM → host byte path is reliable.

**A2. Warm-up exclusion is correct and necessary.** The capture software discards 60 frames before saving. Early frames contain settling transients. The boundary is enforced by the capture software, not inferred from data. This is validated and should not change.

**A3. compressionCfg disabled restores input stationarity.** The 50-frame empty-scene diagnostic showed static_dB span of 0.04 dB and raw_mean max/min of 1.01× with compression off, versus 11 dB span and 3.08× ratio with compression on. H9 is confirmed as the dominant prior cause of instability. This is closed.

**A4. The pipeline correctly processes moving targets.** The RA map visually shows a walking person with physically plausible range and azimuth evolution. MTI, Doppler FFT, and virtual array formation are functioning coherently. The DSP chain up to and including RA beamforming is working.

**A5. CFAR=0 and empty cloud are expected in the current state.** The end user confirmed CFAR and xyz cloud outputs are not currently wired into the active processing path. This is a software integration gap, not a detection failure. All prior interpretations of CFAR=0 as a DSP or hardware anomaly are retracted.

**A6. Frame rate is correct.** 4 fps actual matches the 256 ms framePeriodicity in the cfg exactly. The earlier "20 fps implied by cfg" assumption was wrong. H14 timing incoherence is closed.

**A7. IQ ordering is correct.** Positive-frequency FFT bins are populated correctly. The capture software enforces i-first order, consistent with iq_swap=False in the pipeline. This is stable.

**A8. TX chirp ordering is correct.** The chirpCfg sequence (TX0, TX1, TX2 per device, two devices) matches the pipeline's TDM striding (`cdata[t::num_tx]`). Virtual array geometry is correctly formed.

---

## Section B — Software Pipeline Gaps and Missing Hookups

These are the specific places where the pipeline is incomplete, disconnected, or silently bypassed.

**B1. CFAR results are computed but not connected to any output path.**

`process_frame()` computes `rd_det`, `ra_det`, `rd_thresh`, `ra_thresh` and stores them in `ProcessingResult`. The viewer loop in `run_folder_viewer` prints only cloud point count and a dB range string. It never reads `rd_det.sum()` or `ra_det.sum()` from the result object. The CFAR computation runs but its output is discarded before it reaches any display, log line, or downstream consumer. This is a wiring gap, not a logic bug — the computation is correct, the connection is missing.

**B2. xyz cloud generation depends on ra_det, which is gated by rd_det via require_rd_confirmation.**

`extract_xyz()` is only called when `ra_det.sum() > 0`. `ra_det` is filtered by `require_rd_confirmation`, which requires `rd_det.sum() > 0` at the same range bin. If RD CFAR produces zero detections for any reason, the entire cloud is suppressed regardless of what the RA map contains. This double-gate means a single CFAR failure at the RD stage silently empties the cloud with no diagnostic output indicating why.

**B3. The verbose pipeline log does not distinguish between "CFAR found nothing" and "CFAR was not run".**

`process_frame()` prints `[PROC] 6. RD CFAR → 0 detections` and `[PROC] 8. RA CFAR → 0 detections` but both of these could mean the algorithm ran and found nothing, or that an upstream guard condition caused early exit. There is no print statement that distinguishes these cases. A reader of the log cannot determine whether CFAR was actually executed on real data.

**B4. `_ra_focus_mask_from_rd` fabricates Doppler structure when RD CFAR is empty.**

When `rd_det` has no detections for a range bin, this function falls back to selecting the top-3 Doppler bins by power. This fallback runs silently with no log entry. RA beamforming is then driven by noise-selected Doppler bins rather than confirmed detections. The RA map produced in this fallback state is not meaningless — it still contains real RA energy — but its Doppler weighting is arbitrary. This is documented in the code but not flagged at runtime.

**B5. `parse_cfg_file` does not parse `cfarCfg`, `chirpCfg`, `channelCfg`, or `compressionCfg`.**

The pipeline's CFAR parameters are always the `RadarConfig` defaults regardless of what the cfg file specifies. There is no mechanism to detect a mismatch between the firmware configuration and the pipeline configuration. A user who changes cfarCfg in the cfg file will see no change in pipeline behaviour and receive no warning.

**B6. Calibration format is unverified.**

`parse_calibration()` interprets `antennaCalibParams` values as `[magnitude, phase_deg]` pairs. If TI mmWave Studio exports them as `[Re, Im]` pairs, every channel receives a wrong phase correction silently. The calibration is applied before range FFT and affects all downstream stages. No runtime check verifies that calibration values are in the expected format or within a physically plausible range.

**B7. The RA focus mask fallback path is not guarded by a minimum SNR check.**

In `_ra_focus_mask_from_rd`, the fallback threshold is `max(med + 6.0, peak - 8.0)`. In a low-SNR frame (person at walk-away aspect, oblique angle), the median and peak may both be close to the noise floor. The 6 dB and 8 dB offsets may select bins that are noise rather than signal, silently degrading RA quality for those frames with no indication.

**B8. `save_drea_path` and `save_xyz_path` default to hardcoded TI mmWave Studio PostProc paths.**

These paths are Windows-specific and assume a TI installation at `C:\ti\mmwave_studio_03_00_00_14`. On any other machine these saves silently fail or raise an unhandled exception depending on OS and filesystem state. The auto-save runs unconditionally unless the paths are explicitly cleared, meaning every processing run attempts a write to a path that may not exist.

---

## Section C — Recommended Fixes (Conceptual, Not Code-Level)

**C1. Wire CFAR detection counts into the viewer output line.**

The per-frame viewer line currently prints:
```
Frame N | filename | 0 cloud pts | 0 CFAR | dB–dB dB
```
The `0 CFAR` field should be populated from `result.rd_det.sum()` and `result.ra_det.sum()` explicitly — one count for RD, one for RA. These values are already in the `ProcessingResult` object. The connection is a one-line fix per field. Without this, the end user has no runtime visibility into whether CFAR is producing any output at all.

**C2. Add a diagnostic print when require_rd_confirmation suppresses RA detections.**

When `ra_det` is non-zero before the RD confirmation gate and zero after, print a line:
```
[PROC] 8d. RD confirmation suppressed N RA detections (rd_det=0 at those range bins)
```
This converts a silent suppression into a visible diagnostic that tells the operator exactly what happened and why the cloud is empty.

**C3. Add a diagnostic print when the RA focus mask fallback fires.**

When `_ra_focus_mask_from_rd` uses the fallback path for any range bin, log it at the frame level:
```
[PROC] RA focus: fallback to top-k Doppler selection for M range bins (no RD detections)
```
This makes the fabrication-from-noise path visible rather than silent.

**C4. Extend `parse_cfg_file` to parse `cfarCfg` and apply it to `RadarConfig`.**

The cfg file already contains the correct CFAR parameters for this hardware configuration. Parsing them and applying them to the pipeline removes the gap between firmware configuration and offline processing configuration. At minimum, print a warning at startup if the pipeline's CFAR parameters differ from what the cfg file specifies — this catches silent mismatches without requiring the parser to be extended immediately.

**C5. Add a calibration sanity check.**

After `parse_calibration()` runs, check that all calibration magnitudes are within a physically plausible range (e.g. 0.1 to 10.0) and all phases are within ±180°. If any value falls outside these bounds, print a warning identifying the specific TX/RX channel and the suspect value. This costs nothing and catches a silent format mismatch.

**C6. Replace hardcoded save paths with None defaults and explicit opt-in.**

`save_drea_path` and `save_xyz_path` should default to `None` in `RadarConfig`. Auto-save should only run when a path is explicitly provided via `--save-drea` or `--save-xyz`. The current behaviour of silently attempting writes to a TI-specific Windows path on every run is a portability defect.

**C7. Add a per-frame CFAR margin report.**

For the range bin with the highest RA power in each frame, print the CUT power, the CFAR noise estimate, the threshold, and the margin `(CUT - threshold)` in dB. This single line per frame tells the operator exactly how far below or above detection threshold the strongest signal is, without requiring a full debug run. It is the minimum diagnostic needed to distinguish "signal is present but below threshold" from "signal is absent."

---

## Section D — Visualization and Usability Improvements

**D1. Add a CFAR overlay to the RA map plot.**

The RA map already shows the person clearly. Adding CFAR detection markers (e.g. white crosses or circles) at detected cells would make the gap between "visible in RA" and "detected by CFAR" immediately apparent to any observer. Currently the RA map and CFAR detections are shown in separate contexts with no visual link between them.

**D2. Add a per-frame status bar to the viewer.**

The viewer title line should include: frame index, RD detections, RA detections, cloud points, dB range, and a flag indicating whether the RA focus mask used the fallback path. All of these are already computed — they just need to be routed to the title string.

**D3. Add a range-Doppler map with CFAR threshold overlay.**

A second subplot showing `RD_mti - rd_thresh` (the margin map, in dB) immediately shows which cells are above and below threshold across the full RD space. Cells above zero are detections. This makes the CFAR operating point visible without requiring any code changes to the detection logic itself.

**D4. Separate the "diagnostic" viewer from the "operational" viewer.**

The current viewer mixes visualisation and processing into a single loop. A `--debug` mode should produce the full diagnostic set (margin maps, fallback indicators, calibration summary, per-frame CFAR report) while the default mode produces only the clean operational display. This separation prevents diagnostic overhead from affecting normal operational use.

**D5. Add a frame-level dB floor indicator to the RD map.**

The adaptive dB scale adjusts per frame, making it difficult to compare energy levels across frames. Adding a fixed reference line at the current `cfar_min_power_db` level and at the estimated noise floor (median of the RD map in dB) gives the operator an absolute reference that does not move between frames.

**D6. Stabilise the adaptive colour scale across a rolling window.**

The current adaptive scale is computed per-frame from the top percentile of that frame's data. For a walking person whose RCS changes frame-to-frame, this causes the colour scale to jump, making motion appear as flickering rather than smooth movement. Computing the scale from a rolling window of the last N frames stabilises the display without changing any detection logic.

---

## Section E — Live Streaming Transition Plan

The current architecture is:

```
Firmware → DCA1000EVM → UDP → capture/test.py → frame_*.bin → main.py → plots
```

The target architecture is:

```
Firmware → DCA1000EVM → UDP → frame buffer → process_frame() → live plots
```

The transition has three layers of work with different complexity and risk.

**E1. What can remain unchanged**

`radar_config.py` — no changes needed. Config loading is stateless and fast.

`radar_processing.py` — no changes needed to the DSP logic. `process_frame()` takes a numpy array and returns a `ProcessingResult`. It is already stateless with respect to the frame source.

`radar_reader.py` — no changes needed for the frame-reading logic itself. The `read_frame()` function is file-based but its output format (complex64 `[TX, loops, RX, samples]`) is the same shape that a streaming buffer would produce.

**E2. What needs a new module: the frame assembler**

The current capture tool writes complete frames to disk and the reader reads them back. In streaming mode, raw UDP packets arrive from the DCA1000EVM in 1466-byte chunks with sequence numbers. A new `FrameAssembler` module is needed that:

- Receives raw UDP datagrams
- Validates sequence numbers and detects dropped packets
- Accumulates bytes into a frame buffer of exactly `bytes_per_frame` bytes
- Signals frame completion to the processing thread
- Handles partial frames at capture start and dropped-packet recovery

This module is the highest-risk component of the streaming transition. The DCA1000EVM UDP protocol has specific packet format details (sequence number position, payload offset, endianness) that must be verified against the DCA1000EVM firmware documentation before implementation. The current `capture/test.py` already does this — its logic should be extracted into a reusable `FrameAssembler` class rather than re-implemented.

**E3. What needs refactoring: the processing loop**

The current `run_folder_viewer()` loop is synchronous and file-driven. For streaming it needs to become a producer-consumer architecture:

- **Producer thread:** `FrameAssembler` pushes completed frame buffers into a thread-safe queue.
- **Consumer thread:** Reads from the queue, calls `process_frame()`, updates the display.
- **Queue depth:** 2–3 frames maximum. If the consumer falls behind, the oldest unprocessed frame is dropped and a drop counter is incremented. Frames are never accumulated indefinitely.

The matplotlib display must move to a non-blocking update model (`plt.pause()` or a `FuncAnimation` loop) rather than the current `plt.show(block=True)` which freezes the consumer thread.

**E4. What needs new infrastructure: the warm-up gate**

The current warm-up is handled by the capture software discarding frames before saving. In streaming mode there is no file write to skip. The warm-up gate must move into the `FrameAssembler` or the processing loop as a frame counter that discards the first 60 assembled frames before passing any to the processing queue. This counter must reset on every firmware restart.

**E5. Sequencing of the transition**

The transition should be done in three stages, not all at once:

Stage 1 — extract `FrameAssembler` from `capture/test.py` as a reusable class, validate it produces identical byte output to the current file-based capture for the same input stream. This stage has zero risk to the processing pipeline.

Stage 2 — replace the file-based reader in the viewer loop with a live queue fed by `FrameAssembler`. Keep the file-write path active in parallel as a ground truth comparison. Validate that live-processed frames produce identical `ProcessingResult` objects as offline-processed frames from the same capture.

Stage 3 — disable the file-write path, enable the non-blocking display loop, tune the queue depth for the actual processing latency on the deployment machine.

Do not attempt all three stages in one step. The parallel validation in Stage 2 is the critical safety gate.

---

## Section F — Final Capture Module Audit Checklist (Datasheet-Based)

This is a confidence-building audit. Each item states the assumption being made, the document that should verify it, and what a failure looks like.

**F1. LVDS interleave order**
Assumption: Cascade capture packs samples in device-major, rx-within-device-minor order, so the reshape `[chirps, devices, rx_per_dev, samples, 2]` correctly separates channels.
Document to verify: DCA1000EVM User Guide (SPRUIJ4), section on cascade capture data format and lane mapping.
Failure mode: If the actual interleave is rx-interleaved across devices (i.e. RX0_Dev0, RX0_Dev1, RX1_Dev0, RX1_Dev1...) the reshape silently assigns samples to wrong channels, corrupting virtual array formation without any error.

**F2. Packet sequence numbering and dropped-packet detection**
Assumption: UDP sequence numbers are monotonically increasing 32-bit integers with no wrap-around within a 70-frame capture.
Document to verify: DCA1000EVM CLI Software User Guide, section on raw data packet format.
Failure mode: If sequence numbers wrap (they are 32-bit so wrap is unlikely in short captures but possible in long streaming runs) the drop detector gives false positives and may discard valid frame boundaries.

**F3. FPGA packet header size and payload offset**
Assumption: The capture software correctly identifies where the LVDS payload begins within each UDP datagram, stripping the FPGA sequence number and any header bytes.
Document to verify: DCA1000EVM firmware documentation or CLI guide, packet structure section.
Failure mode: If the header offset is wrong by even 2 bytes, every IQ sample is misaligned, producing a scrambled complex array that still has the correct total byte count and passes all size checks.

**F4. antennaCalibParams format**
Assumption: TI mmWave Studio exports calibration coefficients as `[magnitude, phase_deg]` pairs, and `parse_calibration()` interprets them correctly as `mag * exp(j * deg2rad(phase))`.
Document to verify: mmWave Studio User Guide, antenna calibration export section, or the cascade demo documentation describing the antennaCalibParams command format.
Failure mode: If the format is `[Re, Im]` pairs, the pipeline applies `|Re| * exp(j * arcsin(Im))` which is wrong in both magnitude and phase for most channels, corrupting beamforming silently.

**F5. chirpCfg TX enable mask bit ordering**
Assumption: txEnable bitmask bit 0 = TX0, bit 1 = TX1, bit 2 = TX2, matching the pipeline's TDM assignment `cdata[t::num_tx]` where t=0 maps to chirp 0 (txEnable=1).
Document to verify: AWR2243 mmWave SDK API guide, `rlChirpCfg_t` struct, `txEnable` field definition.
Failure mode: If bit ordering is reversed (bit 0 = TX2) the TX-to-chirp assignment is mirrored, rotating the virtual array and producing a horizontally flipped azimuth map that still looks plausible.

**F6. SampleSwap / IQ ordering under DCA1000 repacking**
Assumption: The DCA1000 FPGA repacks data to I,Q order regardless of the SampleSwap setting in adcbufCfg, so `iq_swap=False` (i-first) is always correct for DCA1000 captures.
Document to verify: DCA1000EVM firmware release notes or the capture format note in `radar_reader.py` which already flags this uncertainty explicitly.
Failure mode: If SampleSwap=1 and the DCA1000 does NOT repack, the IQ order is inverted, conjugating every sample and mirroring the Doppler spectrum. This is detectable: Doppler sign would be reversed (approach appears as recession).

**F7. Frame boundary alignment after FPGA reset**
Assumption: After `reset_fpga` and `start_record`, the first byte of the first UDP datagram is the first byte of a new chirp, and frame boundaries computed from `bytes_per_frame` are correctly aligned from the start.
Document to verify: DCA1000EVM CLI guide, startup sequence section.
Failure mode: If the FPGA buffer contains residual bytes from a previous session before reset, the first frame boundary is offset, causing every frame to be misaligned by a fixed byte count. This produces frames that pass size checks but contain data from two consecutive radar frames interleaved.

**F8. Cascade synchronisation — inter-device timing**
Assumption: The master device (Dev0) synchronises Dev1 via the SYNC_IN/SYNC_OUT lines before capture begins, so all chirps from both devices are time-aligned within the TDM frame.
Document to verify: AWR2243 cascade EVM hardware user guide, synchronisation section.
Failure mode: If synchronisation is incomplete, chirps from Dev1 are offset by one or more chirp periods relative to Dev0. The virtual array formed from misaligned chirps has phase errors that appear as azimuth resolution loss or spurious grating lobes, not as an obvious failure.