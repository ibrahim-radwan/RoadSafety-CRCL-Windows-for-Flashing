# Session 3 Logs: Indoor Moving Subject Within ~3m

**Session ID:** s03  
**Purpose:** Intensive debugging, optimization, and GPU acceleration validation phase targeting human motion capture and processing refinement.

**Session Objective:**
- Debug pipeline behavior with moving human subject within 3m range
- Validate and optimize GPU acceleration (CuPy, RTX 3080 Ti)
- Develop and test 5 modular algorithm iterations (mod1–mod5b)
- Explore human body-shape geometry perception (diag_xyz diagnostic)
- Establish baseline for outdoor validation (S04)

---

## Renamed Logs (20 files)

### CFAR Parameter Sweep (2 files)
| Original Filename | New Filename | Category | Description |
|---|---|---|---|
| cfar_margin_3.txt | 20260607_185337_s03_pipeline_cfar_margin_tuning_3db.txt | pipeline | CFAR margin=3dB parameter exploration |
| cfar_margin_5.txt | 20260607_184728_s03_pipeline_cfar_margin_tuning_5db.txt | pipeline | CFAR margin=5dB parameter exploration |

### Body-Shape Diagnostics (3 files)
| Original Filename | New Filename | Category | Description |
|---|---|---|---|
| diag_xyz_detail.txt | 20260613_215223_s03_debug_diag_xyz_body_shape_detailed.txt | debug | Body-shape geometry diagnostic with verbose output |
| diag_xyz_output.txt | 20260613_215015_s03_debug_diag_xyz_body_shape_standard.txt | debug | Body-shape geometry diagnostic standard output |
| diag_xyz_output_height_0.8.txt | 20260613_215109_s03_debug_diag_xyz_body_shape_height_0_8m.txt | debug | Body-shape geometry with radar mount height offset 0.8m |

### GPU Benchmarking & Acceleration (4 files)
| Original Filename | New Filename | Category | Description |
|---|---|---|---|
| gpu_benchmark_and_offline_initial_run_logs.txt | 20260524_161441_s03_gpu_benchmark_cupy_initial_test.txt | gpu | Initial GPU benchmark: CuPy detection, RTX 3080 Ti device initialization |
| gpu_benchmark_results.txt | 20260610_234854_s03_benchmark_gpu_latency_stage_timing.txt | benchmark | Per-stage pipeline latency on GPU (58 frames, CFAR margin 5dB) |
| gpu_benchmark_summary.txt | 20260610_234854_s03_benchmark_gpu_latency_summary.txt | benchmark | GPU pipeline performance summary and aggregate statistics |
| gpu_benchmark_with_full_gpu_offload_logs.txt | 20260524_164558_s03_gpu_benchmark_full_offload_test.txt | gpu | Full GPU computation offload test (all FFTs on device) |

### Live Streaming Tests (2 files)
| Original Filename | New Filename | Category | Description |
|---|---|---|---|
| live_streaming_logs_with_desk_save.txt | 20260523_211300_s03_processing_live_streaming_desk_save_enabled.txt | processing | Live streaming with file recording enabled |
| live_streaming_logs_without_desk_save.txt | 20260523_231216_s03_processing_live_streaming_no_save.txt | processing | Live streaming without file recording (stream-only mode) |

### Modular Algorithm Variants (7 files: mod1–mod5b)
| Original Filename | New Filename | Category | Description |
|---|---|---|---|
| mod1_integration.txt | 20260608_223944_s03_pipeline_mod1_integration_test.txt | pipeline | Mod1: baseline modular pipeline integration |
| mod2_consistency.txt | 20260608_230847_s03_pipeline_mod2_consistency_validation.txt | pipeline | Mod2: cross-channel/cross-slot consistency fusion |
| mod3_no_racfar.txt | 20260610_203226_s03_pipeline_mod3_no_racfar_variant.txt | pipeline | Mod3: Range-Azimuth CFAR disabled (RD-only detection branch) |
| mod4_pertarget.txt | 20260610_205408_s03_pipeline_mod4_pertarget_beamforming.txt | pipeline | Mod4: per-target beamforming after RD detection |
| mod5_multipeak.txt | 20260611_202913_s03_pipeline_mod5_multipeak_detection.txt | pipeline | Mod5: multi-peak cluster detection algorithm |
| mod5b_bodyshape.txt | 20260611_210758_s03_pipeline_mod5b_body_shape_perception.txt | pipeline | Mod5b: human body-shape geometry perception (final indoor variant) |

### Live Capture with GPU (2 files)
| Original Filename | New Filename | Category | Description |
|---|---|---|---|
| recent_live_capture_run_logs_GPU.txt | 20260524_195855_s03_capture_live_capture_stream_gpu_enabled.txt | capture | Live capture + streaming with GPU acceleration |
| recent_live_capture_run_logs_GPU_spike_elimination.txt | 20260525_002816_s03_processing_spike_elimination_gpu_test.txt | processing | GPU spike elimination algorithm testing |

---

## Skipped Files (1 file — Manual Review Required)

| Filename | Reason | Status |
|---|---|---|
| summary_prompt.txt | **Medium confidence:** Purpose unclear (context artifact? prompt injection? summary?). Classification as log requires stakeholder review. | ⚠️ Pending manual review |

---

## Files NOT Renamed

- Reference PDFs: `A_Hybrid_TDMA_DDMA_Approach...pdf`, `v1_covered_cced052c...pdf`
- Test/diagnostic scripts: `detect_cupy_gpu.py`, `fft_gpu_load_test.py`, `test_gpu_offload_benchmark.py`

---

## Timestamp Timeline

| Date Range | Activity | Count |
|---|---|---|
| 2026-05-23 to 2026-05-25 | GPU benchmarking and live streaming experiments | 4 files |
| 2026-06-07 to 2026-06-08 | CFAR parameter tuning and Mod1–Mod2 algorithm exploration | 9 files |
| 2026-06-10 to 2026-06-11 | Mod3–Mod5b development and GPU latency benchmarking | 6 files |
| 2026-06-13 | Body-shape geometry diagnostics | 3 files |

**Total span:** ~3 weeks of intensive algorithm development and validation

---

## Relationship to Testing Sequence

| Development Phase | Logs | Outcome |
|---|---|---|
| **GPU Validation** | GPU benchmark files (4) | Confirmed GPU acceleration effective; RTX 3080 Ti ≥3.7× speedup |
| **Algorithm Iteration** | Mod1–Mod5b (7 files) | Developed 6 algorithm variants; Mod5b selected for outdoor validation |
| **Parameter Optimization** | CFAR margin sweep (2) | Tested margin=3dB and 5dB configurations |
| **Body-Shape Research** | diag_xyz (3 files) | Geometric modeling of human body-shape representation |
| **Integration Validation** | Live streaming (2) + capture (2) | Confirmed streaming + GPU integration ready for outdoor test |

---

## Architecture Evolution

```
Mod1 (baseline)
  ↓
Mod2 (+ consistency fusion)
  ↓
Mod3 (RA-CFAR disabled)
  ↓
Mod4 (per-target beamforming)
  ↓
Mod5 (multi-peak detection)
  ↓
Mod5b (body-shape perception) ← SELECTED FOR S04
```

---

## Critical Findings

1. **GPU Acceleration:** CuPy enables 3.7–59.8× speedup (elevation FFT on GPU vs CPU)
2. **Algorithm:** Per-target beamforming (Mod4) reduces complexity; multi-peak detection (Mod5/5b) improves human body representation
3. **Body-Shape:** diag_xyz.py validates geometric modeling framework
4. **Ready State:** Mod5b + GPU acceleration + mod parameters ready for outdoor field trial

---

**Rename execution date:** 2026-06-20  
**Total files in session:** 25 (20 renamed + 1 skipped + 4 reference/script files not renamed)
