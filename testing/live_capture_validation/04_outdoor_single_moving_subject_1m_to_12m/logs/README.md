# Session 4 Logs: Outdoor Moving Single Subject 1m–12m Range

**Session ID:** s04  
**Purpose:** Outdoor field validation with extended range (1–12m) and iterative algorithm refinement using 400 selected frames for body-shape perception development.

**Session Objective:**
- Conduct outdoor validation testing with realistic subject motion and range variation
- Apply Mod5b + GPU acceleration from S03 to captured frames
- Execute 11 multi-phase audit iterations (phase1–phase6, stage4) to optimize detection and clustering
- Select 400 high-quality frames for body-shape perception training and validation

---

## Renamed Root Logs (2 files)

| Original Filename | New Filename | Category | Description |
|---|---|---|---|
| outdoor_heatmap_log.txt | 20260604_175629_s04_capture_live_display_heatmap_outdoor.txt | capture | Live capture with Range-Doppler heatmap real-time display |
| outdoor_pointcloud_log.txt | 20260604_174843_s04_capture_live_display_pointcloud_outdoor.txt | capture | Live capture with 3D point cloud real-time display |

---

## Renamed Audit Folders (11 folders with 33 internal files)

Each audit folder contains: `frames.csv`, `points.csv`, `summary.txt`

### Phase 1 Audit Iterations (3 folders)
| Original Name | New Name | Description |
|---|---|---|
| stage4_audit | 20260615_205855_s04_validation_stage4_audit | **Baseline:** Initial outdoor validation audit (earliest timestamp) |
| phase1_audit | 20260615_211556_s04_validation_phase1_audit | **Phase 1:** RD-CFAR with emit_all_cluster_bins=ON; 400 frames, 80% with detections, 704 total points |
| phase1_step2_audit | 20260615_213520_s04_validation_phase1_step2_audit | **Phase 1 Step 2:** Consistency refinement after cluster bin emission tuning |

### Phase 2 Audit (1 folder)
| Original Name | New Name | Description |
|---|---|---|
| phase2_audit | 20260616_004647_s04_validation_phase2_audit | **Phase 2:** Algorithm modulation testing on full 400-frame dataset |

### Phase 3 Audit Iterations (5 folders)
| Original Name | New Name | Description |
|---|---|---|
| phase3_audit | 20260616_222142_s04_validation_phase3_audit | **Phase 3:** Per-target processing after RD detection |
| phase3_final | 20260616_222934_s04_validation_phase3_final | **Phase 3 Final:** Optimized per-target variant after phase3_audit |
| phase3_v2 | 20260616_223528_s04_validation_phase3_v2_optimization | **Phase 3 v2:** First optimization iteration; variant A |
| phase3_v3 | 20260616_224019_s04_validation_phase3_v3_refinement | **Phase 3 v3:** Parameter refinement iteration; variant B |
| phase3_v4 | 20260617_194551_s04_validation_phase3_v4_final_tuning | **Phase 3 v4:** Final tuning iteration; variant C |

### Phase 4 Audit (1 folder)
| Original Name | New Name | Description |
|---|---|---|
| phase4_audit | 20260618_213713_s04_validation_phase4_audit | **Phase 4:** Multi-peak cluster detection algorithm; from Mod5 |

### Phase 6 Audit (1 folder)
| Original Name | New Name | Description |
|---|---|---|
| phase6_audit | 20260619_225710_s04_validation_phase6_audit | **Phase 6:** Human body-shape geometry perception (latest, most refined) |

---

## Audit Progression Timeline

```
Stage 4 (2026-06-15 20:58)
  ↓
Phase 1 (2026-06-15 21:15) ← RD-CFAR baseline
  ↓
Phase 1 Step 2 (2026-06-15 21:35) ← Consistency refinement
  ↓
Phase 2 (2026-06-16 00:46) ← Algorithm modulation
  ↓
Phase 3 (2026-06-16 22:21) ← Per-target processing
  ├─ Phase 3 Final (2026-06-16 22:29)
  ├─ Phase 3 v2 (2026-06-16 23:35)
  ├─ Phase 3 v3 (2026-06-16 22:40)
  └─ Phase 3 v4 (2026-06-17 19:45)
  ↓
Phase 4 (2026-06-18 21:37) ← Multi-peak detection
  ↓
Phase 6 (2026-06-19 22:57) ← Body-shape perception ← FINAL
```

**Total span:** 5 days of iterative auditing and optimization

---

## Audit Metrics (from phase1_audit summary.txt)

| Metric | Value | Notes |
|---|---|---|
| **Total frames** | 400 | Selected outdoor capture sequence |
| **Detection rate** | 80.0% (320 frames) | Frames with cloud points > 0 |
| **Cloud density** | 704 total points | 2.20 pts/frame average |
| **Max points/frame** | 5 | Sparse cloud representation |
| **Centroid X** | +0.175 ± 0.918 m | Radar-centric coordinates |
| **Centroid Y** | +5.800 ± 2.593 m | Subject range variation 1–12m |
| **RD-CFAR survivors** | 882 | After primary detection |
| **Rejections** | 403 total | Grating (273) + FOV (8) + CC (122) |
| **Processing time** | ~46s total (115ms/frame) | Real-time capable |

---

## File Structure

```
04_outdoor_single_moving_subject_1m_to_12m/logs/
├── 20260604_175629_s04_capture_live_display_heatmap_outdoor.txt
├── 20260604_174843_s04_capture_live_display_pointcloud_outdoor.txt
├── 20260615_205855_s04_validation_stage4_audit/
│   ├── frames.csv
│   ├── points.csv
│   └── summary.txt
├── 20260615_211556_s04_validation_phase1_audit/
│   ├── frames.csv (400 frames + statistics)
│   ├── points.csv (704 detection events)
│   └── summary.txt (audit summary)
├── 20260615_213520_s04_validation_phase1_step2_audit/
├── 20260616_004647_s04_validation_phase2_audit/
├── 20260616_222142_s04_validation_phase3_audit/
├── 20260616_222934_s04_validation_phase3_final/
├── 20260616_223528_s04_validation_phase3_v2_optimization/
├── 20260616_224019_s04_validation_phase3_v3_refinement/
├── 20260617_194551_s04_validation_phase3_v4_final_tuning/
├── 20260618_213713_s04_validation_phase4_audit/
├── 20260619_225710_s04_validation_phase6_audit/  ← FINAL RESULTS
└── README.md (this file)
```

---

## Skipped Files (0 files)

No files skipped in this session — all audit folders and root logs are High confidence.

---

## CSV Structure (All Audit Folders)

### frames.csv columns:
- `frame_idx`, `filename`, `rd_cfar`, `after_consistency`, `n_clusters`, `az_peaks_raw`, `fov_rej`, `grating_rej`, `cc_rej`, `ra_det`, `cloud_pts`, `centroid_x`, `centroid_y`, `centroid_z`, `dop_zero_pts`, `dop_max`, `proc_ms`

### points.csv columns:
- Point cloud detections with range, azimuth, elevation, velocity, and quality metrics per detection event

### summary.txt:
- High-level audit statistics (detection rate, cloud density, centroid statistics, stage attribution, acceptance criteria)

---

## Relationship to Testing Sequence

| Phase | Purpose | Key Finding |
|---|---|---|
| **Outdoor capture** | Real-world validation with range 1–12m | 400 frames selected from extended capture |
| **Stage 4 baseline** | Initial audit of captured frames | Establishes detection baseline |
| **Phase 1–3 iterations** | Algorithm optimization for outdoor environment | Per-target beamforming + parameter tuning |
| **Phase 4** | Multi-peak clustering validation | Improved human target separation |
| **Phase 6 final** | Body-shape perception validation | Selected frames used for ML training |

---

## Relationship to Audit Documents

These audit logs correlate with the analysis in:
- [08_generated_plan_human_body_shape_perception_implementation.md](../audit_and_improvement_plan/08_generated_plan_human_body_shape_perception_implementation.md)
- Phases 1–6 represent 7-phase implementation plan execution steps

---

## Next Steps

1. Use phase6_audit results (400 selected frames) for body-shape perception model training
2. Validate frame selections against captured raw binaries
3. Compare phase progression metrics (detection rate, cloud density) across phases
4. Cross-reference with audit_and_improvement_plan documents for detailed technical analysis

---

**Rename execution date:** 2026-06-20  
**Total files in session:** 35 (2 root files renamed + 11 folders renamed with 33 internal files not renamed)
