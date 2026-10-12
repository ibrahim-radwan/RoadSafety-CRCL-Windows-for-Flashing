# Data index: recordings and archives that are not in git

Raw recordings are excluded from this repository (`.gitignore`: `*.bin`, `*.pcap*`, `*.svo2`, `*.mp4`, `*.npz`, `*.npy`). They are too large for GitHub, and the camera and LiDAR recordings show people. Their documentation (logs, summaries, CSV results, plots) **is** in git, next to where the data would be.

**Current storage: the Windows build station only** (`RadarDemo` user, this machine), as of 2026-10-12. The team has not yet chosen a shared data store. When the data moves, update the "Location" column below and verify the copy with the md5 manifests.

## Verifying a copy

Every excluded file is listed with its md5 in `data_manifests/`. The format is `<md5>  <path>`, the same as `firmware/releases/*.MANIFEST.txt`.

```bash
# from the repository root (paths are relative to it)
md5sum -c data_manifests/repo_testing_excluded.md5
# from the handover folder root
cd /c/Users/RadarDemo/Documents/Jetson_Radar_Sync_Capture_Handover_Firmware_Investigation
md5sum -c /path/to/repo/data_manifests/handover_sessions_raw.md5
```

## 1. Capture validation recordings (in this repo's working tree, git-ignored)

Location: `C:\Users\RadarDemo\Documents\cascaded_radar_win_dev\testing\…`. Manifest: `data_manifests/repo_testing_excluded.md5` (5,729 files, 41.0 GB).

| Folder | Files | Size | Content | Firmware / config at capture |
|---|---|---|---|---|
| `testing/live_capture_validation/01_indoor_empty_scene_live_capture` | 52 `.bin`, 2 `.mp4` | 1.55 GB | Empty indoor scene | shortrange, CCS-loaded (valid: CCS initialised DSS L3) |
| `testing/live_capture_validation/02_indoor_static_reflector_3m` | 32 `.bin`, 1 `.mp4` | 1.30 GB | Static corner reflector at 3 m | same |
| `testing/live_capture_validation/03_indoor_moving_subject_within_3m` | 72 `.bin`, 1 `.mp4` | 1.57 GB | Person moving within 3 m | same |
| `testing/live_capture_validation/04_outdoor_single_moving_subject_1m_to_12m` | 402 `.bin`, 2 `.mp4` | 2.59 GB | One person, 1–12 m outdoors | same |
| `testing/live_capture_validation/05_outdoor_data_collection` | 3,707 `.bin`, 3 `.mp4` | 23.95 GB | Outdoor collection, scenarios A–D | same |
| `testing/live_capture_validation/06_outdoor_multiple_subjects` | 1,452 `.bin`, 1 `.mp4` | 9.14 GB | Several people outdoors | same |
| `testing/wireshark_packet_analysis/radar_full_capture_2026-08-31.pcapng` | 1 | 0.84 GB | Full DCA1000 Ethernet capture used to reverse-engineer the protocol for the Jetson | shortrange |
| `testing/wireshark_packet_analysis/out/radar_capture_analysis/06_udp_packet_index.csv` | 1 | 0.08 GB | Per-packet index derived from the `.pcapng` (regenerable) | — |

The `.bin` files are DCA1000 recordings, either raw (`data/am273x_capture_Raw_*.bin`) or split into 3,145,728 B frames (`frames/frame_*.bin`). They are int16, I-first (see `testing/firmware_investigation_2026-10/investigation/JETSON_DATA_FORMAT.md`). The `.mp4` files are reference video recorded alongside.

These sessions predate QSPI boot. The firmware was loaded through CCS, whose GEL script runs DSS L3 MEMINIT, so they are **not** affected by the stale-data defect. Their range values carry the documented 0.56% slope-label error (`docs/RANGE_EQUATION_LEDGER.md` §2). It is fixed by re-processing with a corrected `.cfg`.

## 2. Jetson sessions from the firmware investigation (handover folder)

Location: `C:\Users\RadarDemo\Documents\Jetson_Radar_Sync_Capture_Handover_Firmware_Investigation\sessions\`. Manifest: `data_manifests/handover_sessions_raw.md5` (368 files, 1.90 GB). Metadata for both sessions is in git under `testing/firmware_investigation_2026-10/sessions/`.

| Session | Raw files | Size | Content | Firmware |
|---|---|---|---|---|
| `stage3_01` | 239 radar `.bin`, `lidar/lidar.pcap`, `camera/camera.svo2`, 2 IMU `.csv` | 1.25 GB | Outdoors at night, one person walking with a metal plate at 12–14 m; LiDAR ground truth in git (`sync/lidar_target_truth.csv`) | r075m, QSPI: **~53.5% stale words** |
| `ipad_test_01` | 120 radar `.bin`, `lidar/lidar.pcap`, `camera/camera.svo2`, `sync/lidar_pcap_index.npz`, 2 IMU `.csv` | 0.65 GB | Indoors, radar facing a wall | r075m, QSPI: **~50.6% stale words** |

These two sessions are the evidence for the root cause (`testing/firmware_investigation_2026-10/investigation/REPORT.md` §2, §4). Keep them.

## 3. Archives and backups on this machine (not data, but not in git either)

| Location | What it is | Why kept |
|---|---|---|
| `C:\Users\RadarDemo\Documents\_git_backups\cascaded_radar_win_dev_pre-github_20261012\.git` | The repository's history before the GitHub reset: one commit, `5d9982b`, "Initial project state" (1 GB, containing `capture/data/*.bin`) | Original history; could not be pushed (a 1 GB file exceeds GitHub's limit) |
| `C:\ti\_archive_cascade_sdk_folders_20261012\` | The four firmware folders formerly in the SDK: `cascade - Copy` (source of `firmware/am273x_cascade/`, with old build outputs and the April 2026 backup), `cascade` (Ethernet experiment, source also in `firmware/archive/`), `cascade - Copy (2)`, `cascade - Copy (3)` (March 2026 snapshots) | Provenance of the pre-junction builds |
| `C:\Users\RadarDemo\Documents\Jetson_Radar_Sync_Capture_Handover_Firmware_Investigation\` | The original handover folder from the Jetson. Its documents, code and firmware are now in git (`testing/firmware_investigation_2026-10/`, `firmware/releases/`); only `sessions/` raw data is unique | Raw sessions in §2 |

## 4. Third-party documents kept locally (copyright)

| Location (working tree, git-ignored) | Reference | Why not in git |
|---|---|---|
| `testing/live_capture_validation/03_indoor_moving_subject_within_3m/logs/A_Hybrid_TDMA_DDMA_Approach_for_High_Resolution_Cascaded_Automotive_Radar_Systems_04-2025.pdf` | D. Kumlu, T. Vincon, M. Arsalan, E. Horne, "A Novel Hybrid TDMA-DDMA Approach for Imaging Automotive Radar Systems", IEEE Sensors Letters (manuscript 2025) | © IEEE: redistribution requires IEEE permission |

The AE-CFAR preprint in the same folder (`v1_covered_cced052c-….pdf`; Y. He et al., "AE-CFAR Multi-Target Detection for 24GHz Cascaded Automotive mmWave Radar", Research Square, doi:10.21203/rs.3.rs-9047454/v1) is CC BY 4.0 and **is** committed.
