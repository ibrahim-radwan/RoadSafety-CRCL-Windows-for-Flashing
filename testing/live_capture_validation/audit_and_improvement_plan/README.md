# Radar Live Capture Validation — Audit & Improvement Plan

## Overview

This folder contains the complete audit, planning, implementation, validation, and evolution history of the cascaded AWR2243-2X radar pipeline's live capture validation effort. The documents trace the project from initial investigation through four test sessions (three indoor, one outdoor with 400 selected frames) to a fully functional human-body-shape perception system.

The documents represent the work of:
- **Initial audit & analysis:** Claude Opus (code review, problem identification, hypothesis generation)
- **Implementation guidance:** Claude Sonnet (applied changes, streaming control)
- **Forward roadmap & multi-phase planning:** Claude Opus (7-phase implementation plan)
- **Manual documentation:** Project team (checkpoint summaries, test results)

---

## Naming Convention

All filenames follow this pattern:

```
NN_<document_role>_<short_descriptive_topic>.md
```

Where:
- **NN** = chronological number (01–08), preserved from historical development
- **document_role** = one of: `repo_audit`, `action_plan`, `applied_changes`, `status_summary`, `issue_analysis`, `generated_plan`
- **short_descriptive_topic** = concise lowercase descriptor with underscores

This convention ensures filenames are:
- **Chronologically ordered** (NN: 01 → 08)
- **Role-explicit** (clear purpose at a glance)
- **Self-documenting** (topic immediately apparent)

---

## Document Inventory & Sequence

### Phase 1: Initial Investigation (Docs 01–02)
**Goal:** Identify problems, document symptoms, generate hypotheses.

| # | Filename | Content | Length | Status |
|---|---|---|---|---|
| 01 | [01_repo_audit_initial_pipeline_investigation.md](01_repo_audit_initial_pipeline_investigation.md) | Initial comprehensive investigation snapshot: problem description, observed frame-to-frame amplitude oscillation (3.08× peak-to-peak), CFAR=0 across all frames, environment description, pipeline overview, hypotheses (H1–H14). **Foundational document.** | ~500 lines | Complete ✓ |
| 02 | [02_repo_audit_findings_and_hypotheses.md](02_repo_audit_findings_and_hypotheses.md) | Condensed audit findings: compact system description, confirmed symptoms, environment, hypothesis table with status, confirmed findings (byte transport clean, frame splitting correct, compression is root cause H9), known unknowns, files modified, prioritized next steps (P1–P9). **Executive summary of 01.** | ~300 lines | Complete ✓ |

**Test sessions covered:** Indoor sessions 1–3 (empty scene, static reflector, moving subject within 3 m)

---

### Phase 2: Debugging & Validation Plan (Docs 03–06)
**Goal:** Design and execute experiments to isolate root causes and validate fixes.

| # | Filename | Content | Length | Status |
|---|---|---|---|---|
| 03 | [03_action_plan_frame_stationarity_debugging.md](03_action_plan_frame_stationarity_debugging.md) | Step-by-step debugging plan with 7 experiments (E1–E7): (E1) compression off verification, (E2) amplitude cycle periodicity, (E3) clean vs calibration frames, (E4) RX power sanity, etc. Each experiment has goal, setup, run command, pass/fail criteria, decision branches. **Immediately actionable.** | ~200 lines | Complete ✓ |
| 04 | [04_applied_changes_streaming_control_and_recording.md](04_applied_changes_streaming_control_and_recording.md) | Summary of code changes applied: disabled live streaming disk writes by default, added `--record` flag for explicit frame saving, updated `FileMonitor` to stream frames from memory, fixed crash when `out_dir=None`. Files modified: dca.py, streaming.py, live_capture.py. **Result of implementing streaming control recommendations.** | ~15 lines | Complete ✓ |
| 05 | [05_status_summary_operational_checkpoint_and_demo.md](05_status_summary_operational_checkpoint_and_demo.md) | Operational checkpoint: what the system does today (live streaming with heatmaps + detections + point cloud), performance baseline (318 ms latency, 81% real-time coverage with CFAR), two operating modes, three platform paths forward (Windows optimization / Jetson migration / C++ rewrite), demo guidance, end-user feedback questions. **Bridge between investigation and outdoor testing.** | ~150 lines | Complete ✓ |
| 06 | [06_action_plan_outdoor_validation_scenarios.md](06_action_plan_outdoor_validation_scenarios.md) | Structured outdoor test plan with 6 validation scenarios: (1) single person known range, (2) multiple crossing paths, (3) slow/stationary targets, (4) oblique angle/lateral motion, (5) clutter/false alarm rate, (6) maximum range stress test. Pre-test checklist, per-scenario metrics table, end-user feedback questions (update rate, range requirement, multi-target tracking, platform preference). **Used for session 4 (outdoor, 400 frames).** | ~180 lines | Complete ✓ |

**Test sessions covered:** 
- Docs 03–05: Indoor sessions 1–3 (investigation, experimentation, checkpoint)
- Doc 06: Outdoor session 4 (400 selected frames, moving subject 1–12 m)

---

### Phase 3: Findings & Forward Plan (Docs 07–08)
**Goal:** Consolidate findings, identify remaining gaps, and define long-term implementation roadmap.

| # | Filename | Content | Length | Status |
|---|---|---|---|---|
| 07 | [07_issue_analysis_pipeline_gaps_and_recommendations.md](07_issue_analysis_pipeline_gaps_and_recommendations.md) | Comprehensive post-validation audit: (Section A) confirmed stable facts (A1–A8: capture transport clean, warm-up correct, compression fixes stationarity, pipeline correctly processes moving targets, CFAR/cloud integration missing, frame rate correct, IQ ordering correct, TX chirp ordering correct), (Section B) current gaps (B1–B8: CFAR computed but not wired, xyz cloud suppressed by RD gate, CFAR execution unclear in logs, fallback paths fabricate structure, cfg parsing incomplete, calibration format unverified, RA focus mask without SNR check, hardcoded paths fail on non-Windows), (Section C) recommended fixes (C1–C7: wire CFAR to output, add RD confirmation diagnostic, flag RA fallback, extend cfg parser, sanity check calibration, replace hardcoded paths, add per-frame CFAR margins). **Critical gap analysis.** | ~400 lines | Complete ✓ |
| 08 | [08_generated_plan_human_body_shape_perception_implementation.md](08_generated_plan_human_body_shape_perception_implementation.md) | Forward-looking 7-phase implementation roadmap for human-body-shape radar perception: (0) Observability—per-frame CSV audit, (1) Per-frame cloud correctness—preserve depth, robust gating, (2) Temporal accumulation—motion-compensated windowing, (3) Single-subject clustering/tracking—DBSCAN + Kalman filter, (4) Subject-centric normalization—body frame, (5) Body envelope visualization—PCA ellipse, (6) Micro-Doppler/gait features—spectrogram, cadence, (7) Pose descriptors (future, research-gated). Hard constraints, verified facts, config table, XYZ schema, global metrics (M1–M5), phase-by-phase goals/files/steps/acceptance criteria, cross-cutting requirements, phase dependency graph. **Authoritative roadmap for implementer agents; evidence-driven per-phase design.** | ~800 lines | Complete ✓ |

**Test sessions covered:** 
- Doc 07: Post-validation analysis of sessions 1–4
- Doc 08: Forward planning for sessions 4+ using 400-frame outdoor dataset

---

## Document Relationships

```
Phase 1: Investigation
  01 (audit)           ──┐
                         ├──► 02 (audit summary)
                                    ↓
Phase 2: Experiments & Validation
  03 (action plan)  ──► 04 (applied changes)
  05 (checkpoint)   ◄──┘
                         ↓
  06 (test plan)    ──► [Outdoor session 4: 400 frames captured]
                         ↓
Phase 3: Findings & Roadmap
  07 (issue analysis) ◄─┘
                         ↓
  08 (generated plan) ──► [Future: Phases 0–7 implementation]
```

---

## Mapping to Live Capture Validation Sessions

| Session | Focus | Duration | Location | Relevant Docs |
|---|---|---|---|---|
| **1. Indoor empty scene** | Diagnose frame-to-frame instability | ~60 frames after warmup | Lab (empty room) | 01, 02, 03 |
| **2. Indoor static reflector @ 3 m** | Verify corner reflector detection | ~50 frames | Lab (reflector setup) | 03 (E5 step) |
| **3. Indoor moving subject within 3 m** | Debug CFAR and point cloud generation | ~30–100 frames | Lab (walking path) | 03 (E5–E7), 04 |
| **4. Outdoor moving subject 1–12 m** | Validation across realistic range; collect 400 selected frames | Long session | Outdoor field | 06 (test plan used), 07 (analysis), 08 (data source) |

---

## Key Findings Summary

### Confirmed Stable (From Doc 07, Section A)
✓ Capture transport is clean (byte math exact, zero UDP loss)
✓ Warm-up exclusion is necessary and working
✓ `compressionCfg` disabled (H9) restores input stationarity
✓ Pipeline correctly processes moving targets (RA map coherent)
✓ Frame rate is correct (4 fps, matches 256 ms periodicity)
✓ IQ ordering and TX chirp ordering are correct

### Known Gaps (From Doc 07, Section B)
⚠ CFAR is computed but not wired to display/output
⚠ xyz cloud generation suppressed by RD gate (no visibility into why)
⚠ CFAR fallback paths fabricate structure from noise silently
⚠ Calibration format unverified; cfg parsing incomplete
⚠ Hardcoded save paths fail on non-Windows

### Recommended Fixes (From Doc 07, Section C)
→ Wire CFAR results to viewer output (C1)
→ Add diagnostics for silent suppression gates (C2, C3)
→ Parse `cfarCfg` from cfg file; apply to RadarConfig (C4)
→ Add calibration sanity checks; replace hardcoded paths (C5, C6)

---

## Using These Documents

### For New Team Members
1. **Start with Doc 05** (status checkpoint) to understand what the system does today
2. **Read Doc 01–02** to understand the investigation history and confirmed findings
3. **Reference Doc 08** if implementing future phases

### For Implementers
1. **Start with Doc 08** (implementation roadmap) — it's the authoritative forward-looking plan
2. **Sections 3–13 of Doc 08** describe each phase with files, steps, acceptance criteria
3. **Cross-reference Doc 07** for confirmed gaps that each phase should address

### For Debuggers
1. **Doc 01–02** document hypotheses and what was tested
2. **Doc 03** has the step-by-step debugging experiments (E1–E7)
3. **Doc 07, Section B** lists current known gaps

### For Test Planning
1. **Doc 06** is the outdoor validation plan (6 scenarios, metrics, feedback questions)
2. **Doc 05** describes the demo and platform trade-offs

---

## File Status

| Document | Status | Last Verified | Role | Source |
|---|---|---|---|---|
| 01 | ✓ Complete | 2026-06-13 | repo_audit | Opus |
| 02 | ✓ Complete | 2026-06-13 | repo_audit | Opus |
| 03 | ✓ Complete | 2026-06-13 | action_plan | Opus |
| 04 | ✓ Complete | 2026-06-15 | applied_changes | Sonnet |
| 05 | ✓ Complete | 2026-06-15 | status_summary | Project team |
| 06 | ✓ Complete | 2026-06-15 | action_plan | Opus |
| 07 | ✓ Complete | 2026-06-13 | issue_analysis | Opus |
| 08 | ✓ Complete | 2026-06-13 | generated_plan | Opus |

---

## Next Steps

1. **Phase 0 (Observability):** Run `diag_pipeline_audit.py` on the 400-frame outdoor dataset to collect per-frame/per-stage statistics (CSVs: `frames.csv`, `points.csv`)
2. **Phase 1–3 (Per-frame → Tracking):** Implement and validate temporal accumulation, DBSCAN clustering, Kalman tracking
3. **Phase 4–6 (Normalization → Gait):** Add subject-centric frame, body envelope, micro-Doppler spectrogram
4. **Phase 7 (Pose):** Future research track; requires ≥ 20 multi-subject sequences

All phases are gated on their local acceptance criteria (see Doc 08, "Acceptance criteria" per phase).

---

## Revision History

- **2026-06-20:** Files renamed with explicit role descriptors; README.md created to document structure and relationships

---

**Last updated:** 2026-06-20
**Documentation verified against:** Code audit 2026-06-13, project state checkpoint 2026-06-15
