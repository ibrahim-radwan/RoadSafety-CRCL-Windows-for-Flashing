# Firmware investigation and rebuild: October 2026

This folder records how the cascade radar's raw-data defect was found, proven, fixed, confirmed on hardware, and rolled out to every range variant. It is the knowledge base the Jetson capture pipeline's firmware rests on. It was imported on 2026-10-12 from the handover folder `C:\Users\RadarDemo\Documents\Jetson_Radar_Sync_Capture_Handover_Firmware_Investigation\`, without the raw recordings (see `DATA_INDEX.md` at the repo root).

## Outcome in one paragraph

About **50% of every radar frame was stale data**: bit-identical across frames, in 32-byte blocks. The cause was not compression or a DCA1000 setting.

- **Root cause:** the AM273x receives each chirp into CSI-RX ping/pong buffers in DSS L3 RAM. When the image boots from QSPI, the bootloader never initialises that RAM (MEMINIT), and about half of its lines then never take the CSI-2 data. CCS loading had hidden this, because the CCS GEL script runs MEMINIT on connect.
- **Fix:** one call at the top of `main()`, `SOC_rcmStartMemInitDSSL3/WaitMemInitDSSL3(ALL)`.
- **Hardware confirmation (2026-10-10):** 0.00% stale words on r075m_v2, holding across power cycles.
- **Rebuild:** every range variant was rebuilt with the fix and HPF 0/0, at 4 and 8 fps, and deployed to the Jetson on 2026-10-12.
- **Two more corrections came out of the same work:**
  - **I/Q order:** the data is **I first**. The old `.cfg` files said Q-first, which mirrored the range spectrum.
  - **DCA1000 packet delay:** it must be **25 µs**. 50 µs silently loses data at 8 fps.

## Reading order

1. `investigation/REPORT.md`: the full analysis, with source references. §0 summary, §2 root-cause proof, §3 hypothesis verdicts, §8 hardware results, §10 the rebuild.
2. `rebuild_all_variants/REBUILD_SUMMARY.md`: all variants, md5s, timing feasibility, clipping headroom, calibration caveat, disassembly check, manifest differences.
3. `investigation/JETSON_DATA_FORMAT.md`: the byte layout, I/Q order, virtual-channel order, packet rates and DCA1000 settings the Jetson uses.
4. `investigation/FLASH_PROCEDURE.md`: how the Jetson flashes a variant (`flash_variant.sh`) and accepts it.
5. `briefs/`: the two task briefs from the Jetson team that started each phase. They are the requirements as stated at the time; some of their assumptions were later disproved (see REPORT §3).

## Contents

| Path | What it is |
|---|---|
| `briefs/` | The investigation brief (2026-10-10) and the rebuild-all-variants brief |
| `investigation/` | Report, data-format spec, flash procedure, `check_radar_session.py` (stale-word test and range-time / LiDAR check), the stage3_01 decode figure, `analysis/` (every script behind the report's numbers), `source_backup_before_fix/` (the firmware source and map as they were before the fix) |
| `rebuild_all_variants/` | `REBUILD_SUMMARY.md`, `MANIFEST.txt` of the delivered tree, `fill_firmware_map_output.txt`, `disassembly_diff_vs_base.txt` |
| `jetson_baseline_20261010/MANIFEST.txt` | md5 list of the Jetson's firmware tree before the rebuild, which the delivery was diffed against |
| `jetson_updates_20261010/` | Jetson-side code at the time of the hardware confirmation: `check_radar_frames.py`, `dca_capture_radar_sync.py` (25 µs default), `fill_firmware_map.py` (HPF1 fix), `flash_variant.sh`, `radar_config.py`, `radar_firmware.py`, and two range-time plots from the confirmation sessions |
| `jetson_snapshot_20261009/` | Jetson capture/processing code as it was when the investigation started (the decoding assumptions under test) |
| `sessions/stage3_01/`, `sessions/ipad_test_01/` | Session metadata only: logs, `session.json`, timelines, the LiDAR ground truth `sync/lidar_target_truth.csv`. The radar frames, LiDAR pcap and camera video are listed in `DATA_INDEX.md`. |

## Where things moved (the documents use the handover-folder paths)

| Path written in the documents | Where it is now |
|---|---|
| `rebuild_all_variants/firmware/` | `firmware/releases/2026-10-10_v2/` (repo root) |
| `rebuild_all_variants/MANIFEST.txt` | `firmware/releases/2026-10-10_v2.MANIFEST.txt` (copy also here) |
| `rebuild_all_variants/source/` (`cascade_config.h`, `main_mss.c`, `makefile`, `build_one_inf.bat`, `build_v2_variants.ps1`, `gen2.py`, `fdiff.py`) | `firmware/am273x_cascade/` and `firmware/am273x_cascade/tools/` (`gen2.py` → `gen_v2_release_metadata.py`) |
| `FW/` = `C:\ti\…\ti\utils\test\cascade - Copy\am273x\` (REPORT.md) | `firmware/am273x_cascade/am273x/`. Same files. Line numbers still match for `main_mss.c`, `common.c`, `cascade_csirx.c` and `cascade_lvds_stream.c`. In `cascade_config.h` they moved ~45 lines down when the `_V2` table was added at the top, so search for the block name instead. In the SDK the folder is reached through the `cascade_radar` junction (`firmware/README.md` §1). |
| `firmware/` (the first r075m_v2 delivery) | superseded by the release; identical images |
| `jetson_firmware_current/` | identical subset of the release; only its manifest is kept, in `jetson_baseline_20261010/` |
| `sessions/*/radar/frame_*.bin`, `lidar/*.pcap`, `camera/*.svo2` | not in git; see `DATA_INDEX.md` |
| `processing/`, `capture/`, `dca_capture_radar_sync.py` (handover root) | `jetson_snapshot_20261009/` |

## Still open (from REPORT §8 and REBUILD_SUMMARY)

- **Antenna calibration:** repeat it with the HPF 0/0 images, using `r017m_calib_v2` for 77 GHz and a 76 GHz v2 image for the others. The provenance of the inherited coefficients is unknown.
- **TX/RX → azimuth geometry:** unverified; check it with a corner reflector.
- **Finding B** (the ~908 packets/s episode): instrumentation recommended, not implemented.
- **Per-variant acceptance** on the Jetson: stale-word test, peak sample (tightest headroom r050m_v2, ~17 dB) and a range-time map near each new floor.
