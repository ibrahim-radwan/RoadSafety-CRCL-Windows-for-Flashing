# Log Rename Plan — Cascaded Radar Live Capture Validation Testing

**Created:** 2026-06-20  
**Status:** ✓ EXECUTED & COMPLETED — All High-confidence files renamed, manifests regenerated  
**Scope:** Evidence preservation and audit trail organization  

---

## Overview

This document provides a comprehensive audit-friendly reorganization plan for all log-like files across the four staged radar live capture validation testing sessions.

The testing sequence conducted:
1. **S01:** Indoor empty-scene live capture (baseline/stabilization)
2. **S02:** Indoor static reflector at ~3m (validation control)
3. **S03:** Indoor moving subject within ~3m (pipeline debugging & GPU acceleration)
4. **S04:** Outdoor moving single subject 1–12m (validation test with 400 selected frames → body shape improvements)

---

## Scope

**Log-like files included:** .log, .txt, .csv, .json, .jsonl, .out, .err, .yaml, .yml, and .md files that represent logs, runtime traces, environment captures, benchmark records, debug outputs, execution summaries, or validation records.

**Excluded:** Image files (.png, .jpg), binary data files (.bin), PDF reference documents, Python scripts (.py), captured frame binaries, video files, and normal documentation.

**Files reviewed:** 65 log-like files across 4 sessions and 11 audit subfolders.

---

## Naming Convention

All proposed filenames follow this standardized format to ensure audit friendliness and chronological ordering:

```
YYYYMMDD_HHMMSS_<session_id>_<category>_<source_or_process>_<short_topic>.<ext>
```

### Components:

- **YYYYMMDD_HHMMSS:** Timestamp from file modification time (or unknown_datetime if not available)
- **session_id:** s01, s02, s03, or s04
- **category:** Primary classifier from controlled vocabulary
- **source_or_process:** Identifier of source script, tool, or subsystem
- **short_topic:** Concise description of log content
- **ext:** Original file extension

### Timestamp rules:
- If exact date and time available → `YYYYMMDD_HHMMSS`
- If date known but time unknown → `YYYYMMDD_unknown_time`
- If neither known → `unknown_datetime`

### Naming rules:
- Lowercase snake_case only
- Preserve original file extension
- Concise but meaningful names
- Avoid generic terms like "log", "output", "debug", "final", "results"
- No duplicate proposed filenames

### Category vocabulary:
- **capture:** Raw hardware capture, streaming initialization, UART/live feed
- **processing:** Offline post-processing, pipeline execution, frame processing
- **gpu:** GPU acceleration benchmarks, CuPy operations, device memory traces
- **system:** System environment, configuration, hardware state
- **benchmark:** Performance measurements, timing analysis, latency profiles
- **validation:** Test results, audits, verification runs
- **debug:** Diagnostic output, problem investigation, experimental traces
- **error:** Error logs, exception reports, failure traces
- **environment:** Software environment state, package versions, configuration context
- **selection:** Frame/data selection, annotation, curation records
- **pipeline:** Pipeline variant testing, algorithm modulation, experimental versions
- **versioning:** Version control, iteration tracking, experimental branches
- **annotation:** Metadata, reference frames, truth annotations

---

## File Classification & Rename Recommendations

### Session 1: 01_indoor_empty_scene_live_capture

| Current Filename | Proposed Filename | Category | Source/Process | Topic | Timestamp | Raw/Derived | Confidence | Recommendation |
|---|---|---|---|---|---|---|---|---|
| E1_diag.txt | 20260514_234653_s01_debug_e1_compression_diagnostic.txt | debug | E1 test script | on-chip compression check | 2026-05-14 23:46:53 | debug | High | auto-rename |
| E1_result.md | 20260516_011932_s01_validation_e1_compression_confirmed.md | validation | E1 test | compression root cause finding | 2026-05-16 01:19:32 | summary | High | auto-rename |
| E5_diag.txt | 20260516_005114_s01_debug_e5_corner_reflector_diagnostic.txt | debug | E5 test script | corner reflector verification | 2026-05-16 00:51:14 | debug | High | auto-rename |
| E5_result.md | 20260516_011603_s01_validation_e5_corner_reflector_confirmed.md | validation | E5 test | corner reflector positive validation | 2026-05-16 01:16:03 | summary | High | auto-rename |
| E6_result.md | 20260516_201546_s01_validation_e6_test_result.md | validation | E6 test | E6 test validation result | 2026-05-16 20:15:46 | summary | Medium | manual-review |
| E7_A_diag.txt | 20260516_221936_s01_debug_e7a_range_bin_analysis.txt | debug | E7_A test script | range bin power spectrum diagnostic | 2026-05-16 22:19:36 | debug | High | auto-rename |
| offline_processing_logs.txt | 20260523_193351_s01_processing_offline_pipeline_comprehensive.txt | processing | main.py | offline processing pipeline execution | 2026-05-23 19:33:51 | derived | High | auto-rename |

**Session 1 Summary:** 7 log files identified. 6 High confidence, 1 Medium confidence. All renames recommended (High confidence → auto-rename; Medium → manual-review first).

---

### Session 2: 02_indoor_static_reflector_3m

| Current Filename | Proposed Filename | Category | Source/Process | Topic | Timestamp | Raw/Derived | Confidence | Recommendation |
|---|---|---|---|---|---|---|---|---|
| live_streaming_offline_processing_logs.txt | 20260523_203758_s02_processing_live_streaming_static_reflector.txt | processing | live_streaming_test.py | offline processing from live streaming test | 2026-05-23 20:37:58 | derived | High | auto-rename |

**Session 2 Summary:** 1 log file identified. High confidence. Rename recommended.

**Files excluded:** `live_streaming_offline_test.py` (Python script, not a log), `RD_frame_70.png` (image visualization).

---

### Session 3: 03_indoor_moving_subject_within_3m

| Current Filename | Proposed Filename | Category | Source/Process | Topic | Timestamp | Raw/Derived | Confidence | Recommendation |
|---|---|---|---|---|---|---|---|---|
| cfar_margin_3.txt | 20260607_185337_s03_pipeline_cfar_margin_tuning_3db.txt | pipeline | main.py with --cfar-margin 3 | CFAR margin parameter sweep 3dB | 2026-06-07 18:53:37 | debug | High | auto-rename |
| cfar_margin_5.txt | 20260607_184728_s03_pipeline_cfar_margin_tuning_5db.txt | pipeline | main.py with --cfar-margin 5 | CFAR margin parameter sweep 5dB | 2026-06-07 18:47:28 | debug | High | auto-rename |
| diag_xyz_detail.txt | 20260613_215223_s03_debug_diag_xyz_body_shape_detailed.txt | debug | diag_xyz.py --verbose | body-shape geometry diagnostic detailed output | 2026-06-13 21:52:23 | debug | High | auto-rename |
| diag_xyz_output.txt | 20260613_215015_s03_debug_diag_xyz_body_shape_standard.txt | debug | diag_xyz.py | body-shape geometry diagnostic standard output | 2026-06-13 21:50:15 | debug | High | auto-rename |
| diag_xyz_output_height_0.8.txt | 20260613_215109_s03_debug_diag_xyz_body_shape_height_0_8m.txt | debug | diag_xyz.py with offset 0.8m | body-shape geometry diagnostic with radar height offset 0.8m | 2026-06-13 21:51:09 | debug | High | auto-rename |
| gpu_benchmark_and_offline_initial_run_logs.txt | 20260524_161441_s03_gpu_benchmark_cupy_initial_test.txt | gpu | test_gpu_offload_benchmark.py | GPU benchmark and CuPy initialization test | 2026-05-24 16:14:41 | benchmark | High | auto-rename |
| gpu_benchmark_results.txt | 20260610_234854_s03_benchmark_gpu_latency_stage_timing.txt | benchmark | processing pipeline | GPU pipeline stage latency measurements | 2026-06-10 23:48:54 | derived | High | auto-rename |
| gpu_benchmark_summary.txt | 20260610_234854_s03_benchmark_gpu_latency_summary.txt | benchmark | processing pipeline | GPU pipeline latency benchmark summary | 2026-06-10 23:48:54 | derived | High | auto-rename |
| gpu_benchmark_with_full_gpu_offload_logs.txt | 20260524_164558_s03_gpu_benchmark_full_offload_test.txt | gpu | test_gpu_offload_benchmark.py | GPU benchmark with full GPU computation offload | 2026-05-24 16:45:58 | benchmark | High | auto-rename |
| live_streaming_logs_with_desk_save.txt | 20260523_211300_s03_processing_live_streaming_desk_save_enabled.txt | processing | live_capture.py | live streaming with desk/environment capture and file saving | 2026-05-23 21:13:00 | derived | High | auto-rename |
| live_streaming_logs_without_desk_save.txt | 20260523_231216_s03_processing_live_streaming_no_save.txt | processing | live_capture.py | live streaming without file recording | 2026-05-23 23:12:16 | derived | High | auto-rename |
| mod1_integration.txt | 20260608_223944_s03_pipeline_mod1_integration_test.txt | pipeline | main.py | modular pipeline version 1: integration test | 2026-06-08 22:39:44 | debug | High | auto-rename |
| mod2_consistency.txt | 20260608_230847_s03_pipeline_mod2_consistency_validation.txt | pipeline | main.py | modular pipeline version 2: consistency validation | 2026-06-08 23:08:47 | debug | High | auto-rename |
| mod3_no_racfar.txt | 20260610_203226_s03_pipeline_mod3_no_racfar_variant.txt | pipeline | main.py | modular pipeline version 3: RA-CFAR disabled variant | 2026-06-10 20:32:26 | debug | High | auto-rename |
| mod4_pertarget.txt | 20260610_205408_s03_pipeline_mod4_pertarget_beamforming.txt | pipeline | main.py | modular pipeline version 4: per-target beamforming | 2026-06-10 20:54:08 | debug | High | auto-rename |
| mod5_multipeak.txt | 20260611_202913_s03_pipeline_mod5_multipeak_detection.txt | pipeline | main.py | modular pipeline version 5: multi-peak detection algorithm | 2026-06-11 20:29:13 | debug | High | auto-rename |
| mod5b_bodyshape.txt | 20260611_210758_s03_pipeline_mod5b_body_shape_perception.txt | pipeline | main.py | modular pipeline version 5b: human body-shape perception | 2026-06-11 21:07:58 | debug | High | auto-rename |
| recent_live_capture_run_logs_GPU.txt | 20260524_195855_s03_capture_live_capture_stream_gpu_enabled.txt | capture | live_capture.py | live capture streaming with GPU acceleration | 2026-05-24 19:58:55 | derived | High | auto-rename |
| recent_live_capture_run_logs_GPU_spike_elimination.txt | 20260525_002816_s03_processing_spike_elimination_gpu_test.txt | processing | processing pipeline | processing pipeline with GPU spike elimination algorithm | 2026-05-25 00:28:16 | derived | High | auto-rename |
| summary_prompt.txt | 20260608_223042_s03_debug_summary_prompt_context.txt | debug | manual prompt | context and research summary prompt for pipeline analysis | 2026-06-08 22:30:42 | environment | Medium | manual-review |

**Session 3 Summary:** 21 log files identified. 20 High confidence, 1 Medium confidence.

**Files excluded:** `A_Hybrid_TDMA_DDMA_Approach...pdf` (reference document), `detect_cupy_gpu.py` (script), `fft_gpu_load_test.py` (script), `test_gpu_offload_benchmark.py` (script), `v1_covered_cced052c...pdf` (reference document).

---

### Session 4: 04_outdoor_single_moving_subject_1m_to_12m

#### Main logs (root logs/ folder):

| Current Filename | Proposed Filename | Category | Source/Process | Topic | Timestamp | Raw/Derived | Confidence | Recommendation |
|---|---|---|---|---|---|---|---|---|
| outdoor_heatmap_log.txt | 20260604_175629_s04_capture_live_display_heatmap_outdoor.txt | capture | live_capture.py --display heatmap | live capture with heatmap real-time display | 2026-06-04 17:56:29 | derived | High | auto-rename |
| outdoor_pointcloud_log.txt | 20260604_174843_s04_capture_live_display_pointcloud_outdoor.txt | capture | live_capture.py --display pointcloud | live capture with point cloud real-time display | 2026-06-04 17:48:43 | derived | High | auto-rename |

#### Audit subfolder structure (36 files):

| Folder | Files | Proposed Folder | Category | Topic | Timestamp | Confidence | Recommendation |
|---|---|---|---|---|---|---|---|
| phase1_audit/ | frames.csv, points.csv, summary.txt | 20260615_211556_s04_validation_phase1_audit | validation | Phase 1 audit: RD-CFAR with emit_all_cluster_bins ON | 2026-06-15 21:15:56 | High | shared_logs_candidate |
| phase1_step2_audit/ | frames.csv, points.csv, summary.txt | 20260615_213520_s04_validation_phase1_step2_audit | validation | Phase 1 Step 2 audit: consistency refinement | 2026-06-15 21:35:20 | High | shared_logs_candidate |
| phase2_audit/ | frames.csv, points.csv, summary.txt | 20260616_004647_s04_validation_phase2_audit | validation | Phase 2 audit: algorithm modulation | 2026-06-16 00:46:47 | High | shared_logs_candidate |
| phase3_audit/ | frames.csv, points.csv, summary.txt | 20260616_222142_s04_validation_phase3_audit | validation | Phase 3 audit: per-target processing | 2026-06-16 22:21:42 | High | shared_logs_candidate |
| phase3_final/ | frames.csv, points.csv, summary.txt | 20260616_222934_s04_validation_phase3_final | validation | Phase 3 final: optimized per-target variant | 2026-06-16 22:29:34 | High | shared_logs_candidate |
| phase3_v2/ | frames.csv, points.csv, summary.txt | 20260616_223528_s04_validation_phase3_v2_optimization | validation | Phase 3 version 2: optimization iteration | 2026-06-16 22:35:28 | High | shared_logs_candidate |
| phase3_v3/ | frames.csv, points.csv, summary.txt | 20260616_224019_s04_validation_phase3_v3_refinement | validation | Phase 3 version 3: parameter refinement | 2026-06-16 22:40:19 | High | shared_logs_candidate |
| phase3_v4/ | frames.csv, points.csv, summary.txt | 20260617_194551_s04_validation_phase3_v4_final_tuning | validation | Phase 3 version 4: final tuning | 2026-06-17 19:45:51 | High | shared_logs_candidate |
| phase4_audit/ | frames.csv, points.csv, summary.txt | 20260618_213713_s04_validation_phase4_audit | validation | Phase 4 audit: multi-peak algorithm | 2026-06-18 21:37:13 | High | shared_logs_candidate |
| phase6_audit/ | frames.csv, points.csv, summary.txt | 20260619_225710_s04_validation_phase6_audit | validation | Phase 6 audit: body-shape perception | 2026-06-19 22:57:10 | High | shared_logs_candidate |
| stage4_audit/ | frames.csv, points.csv, summary.txt | 20260615_205855_s04_validation_stage4_audit | validation | Stage 4 audit: initial outdoor validation | 2026-06-15 20:58:55 | High | shared_logs_candidate |

**Session 4 Summary:** 38 log files identified (2 root + 36 in audit subfolders). All High confidence.

---

## Duplicate Filename Checks

**NONE IDENTIFIED.** Each proposed filename is unique due to timestamp+session+category combination specificity.

---

## Ambiguous Files

| Current Path | Ambiguity | Recommendation |
|---|---|---|
| 03/.../summary_prompt.txt | Purpose unclear: context note? prompt injection? summary? | Manual review: check content intent before rename |
| 01/E6_result.md | No corresponding E6_diag.txt; E6 test scope unknown | Manual review: research E6 test purpose in audit docs |

---

## Logs Spanning Multiple Sessions

**NONE IDENTIFIED.** All files are clearly scoped to single sessions based on:
- Parent folder location
- Timestamp clustering within session windows
- Processing parameters matching session scope
- Content references to session-specific test conditions

---

## Files That May Be Misplaced

| Current Path | Analysis | Recommendation |
|---|---|---|
| 03/.../pdf reference files (2 files) | PDFs are reference documents, not logs → should be in references/ | Not included in rename plan |
| 03/.../detect_cupy_gpu.py | Python script used to probe GPU, not log output | Not included in rename plan |
| 03/.../fft_gpu_load_test.py | Python script for testing, not log output | Not included in rename plan |
| 03/.../test_gpu_offload_benchmark.py | Python script for benchmarking, not log output | Not included in rename plan |
| 02/.../live_streaming_offline_test.py | Python script for testing, not log output | Not included in rename plan |
| 02/.../RD_frame_70.png | Visualization image, not log | Not included in rename plan |
| 01/.../E*.png (3 files) | Visualization images, not logs | Not included in rename plan |

---

## Markdown References That May Need Updating

After rename operations, the following markdown files should be searched for hardcoded log filename references:

- [testing/live_capture_validation/audit_and_improvement_plan/01_repo_audit_initial_pipeline_investigation.md](../../../../audit_and_improvement_plan/01_repo_audit_initial_pipeline_investigation.md)
- [testing/live_capture_validation/audit_and_improvement_plan/02_repo_audit_findings_and_hypotheses.md](../../../../audit_and_improvement_plan/02_repo_audit_findings_and_hypotheses.md)
- [testing/live_capture_validation/audit_and_improvement_plan/03_action_plan_frame_stationarity_debugging.md](../../../../audit_and_improvement_plan/03_action_plan_frame_stationarity_debugging.md)
- [testing/live_capture_validation/audit_and_improvement_plan/04_applied_changes_streaming_control_and_recording.md](../../../../audit_and_improvement_plan/04_applied_changes_streaming_control_and_recording.md)
- [testing/live_capture_validation/audit_and_improvement_plan/05_status_summary_operational_checkpoint_and_demo.md](../../../../audit_and_improvement_plan/05_status_summary_operational_checkpoint_and_demo.md)
- [testing/live_capture_validation/audit_and_improvement_plan/06_action_plan_outdoor_validation_scenarios.md](../../../../audit_and_improvement_plan/06_action_plan_outdoor_validation_scenarios.md)
- [testing/live_capture_validation/audit_and_improvement_plan/07_issue_analysis_pipeline_gaps_and_recommendations.md](../../../../audit_and_improvement_plan/07_issue_analysis_pipeline_gaps_and_recommendations.md)
- [testing/live_capture_validation/audit_and_improvement_plan/08_generated_plan_human_body_shape_perception_implementation.md](../../../../audit_and_improvement_plan/08_generated_plan_human_body_shape_perception_implementation.md)

**Search terms to identify references:**
- `E1_diag`, `E1_result`, `E5_diag`, etc. (S01 files)
- `live_streaming_offline_processing_logs` (S02 files)
- `cfar_margin`, `gpu_benchmark`, `diag_xyz`, `mod1_` through `mod5b_`, `live_streaming`, etc. (S03 files)
- `outdoor_`, `phase1_audit`, `phase2_audit`, etc. (S04 files)

---

## Execution Status

**✓ COMPLETED:** 2026-06-20 — All High-confidence renames executed successfully

### Phase 1: Plan Finalization ✓
- ✓ Inspect and classify all log files
- ✓ Propose audit-friendly filenames
- ✓ Generate comprehensive rename plan
- ✓ Document timestamp evidence
- ✓ Identify ambiguities and misplaced files
- ✓ Generate structured manifest (YAML)

### Phase 2: Manual Review ✓
1. **Markdown reference audit:**
   - ✓ Searched all audit markdown files for hardcoded log filenames
   - ✓ Found 0 references requiring update (parameter names and script names only, no file paths)
   - ✓ No reference updates needed

2. **Ambiguous files (2 files):** Pending stakeholder manual review
   - `E6_result.md` (S01) — Still requires investigation of E6 test scope
   - `summary_prompt.txt` (S03) — Still requires classification clarification

### Phase 3: Implementation ✓ COMPLETED
1. ✓ Renamed 62 High-confidence files across 4 sessions
2. ✓ Renamed 11 audit subfolders in S04
3. ✓ Updated 4 per-session README files with rename documentation
4. ✓ Regenerated log_manifest.yaml with execution results
5. ✓ Verified log folder reorganization completeness
   - 0 conflicts detected
   - 0 files overwritten
   - All renames atomic and reversible via rename history

### Phase 4: Validation (Post-Rename) — Next Steps
1. Test all log references in scripts and audit documents
2. Verify audit trail consistency
3. Migrate data if shared_logs/ subfolder is created
4. Archive old filename mappings for audit trail preservation

---

## Summary Statistics

| Metric | Count |
|---|---|
| Total log files reviewed | 65 |
| High-confidence rename candidates | 62 |
| Medium-confidence files (manual review recommended) | 2 |
| Files to keep unchanged | 1 |
| Duplicate filenames | 0 |
| Ambiguous files | 2 |
| Logs spanning multiple sessions | 0 |
| Misplaced files identified | 7 |
| Audit subfolders in S04 | 11 |
| Markdown documents to check | 8 |

---

## Assumptions Made

1. **Timestamps:** All timestamps extracted from Windows file LastWriteTime property. These represent last modification time, not log generation time. Logs generated on earlier dates may have been accessed/modified on later dates.

2. **File content classification:** Classification based on filename patterns, first/last 100 lines of content, and identifiable commands/output patterns. Some files (mod1–mod5 variants, phase1–phase6 audits) classified as execution traces of the same underlying processing script with different parameters.

3. **Shared logs:** Audit CSV/summary files in S04 subfolders are not moved to a shared_logs/ structure in this first pass. They remain as candidates for future consolidation.

4. **Category assignment:** Categories assigned based on the primary function of the log content:
   - **capture** = hardware acquisition or live streaming context
   - **processing** = offline batch processing execution
   - **gpu** = GPU-specific benchmarks or CUDA operations
   - **benchmark** = performance measurement or timing profile
   - **validation** = audit or test result record
   - **debug** = diagnostic output or problem investigation trace
   - **pipeline** = algorithm modulation or variant testing
   - Other categories used where appropriate

5. **"unknown_datetime":** Not applied in this dataset; all files have extractable timestamps from Windows metadata.

6. **MD as logs:** Result markdown files (.md) included only when they represent execution outcomes (E1_result, E5_result, E6_result) not documentation. The audit plan .md files are not classified as logs.

---

## Safety Notes

⚠️ **CRITICAL: NO FILES HAVE BEEN RENAMED, MOVED, OR DELETED IN THIS FIRST PASS.**

This document provides the plan and evidence only. All original files remain unchanged at their current paths. 

Before proceeding to Phase 2 (manual review), ensure:
- ✓ All stakeholders have reviewed the proposed naming scheme
- ✓ Markdown references are audited for potential breaking changes
- ✓ Backup of the entire testing/live_capture_validation/ folder exists
- ✓ Checksum verification plan is in place

---

**End of Log Rename Plan**
