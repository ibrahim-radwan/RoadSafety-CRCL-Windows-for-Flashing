# Data index: recordings and archives that are not in git

Raw recordings are excluded from this repository (`.gitignore`: `*.bin`, `*.pcap*`, `*.svo2`, `*.mp4`, `*.npz`, `*.npy`). They are too large for GitHub, and the camera and LiDAR recordings show people. Their documentation (logs, summaries, CSV results, plots) **is** in git, next to where the data would be.

**Current storage: the Windows build station only**, as of 2026-10-12. All raw data sits inside this repository's working tree, git-ignored, at the paths below (`C:\Users\RadarDemo\Documents\cascaded_radar_win_dev\`). The team has not yet chosen a shared data store. When the data moves, update this section and verify the copy with the md5 manifests.

## Verifying a copy

Every excluded file is listed with its md5 in `data_manifests/`. The format is `<md5>  <path>`, the same as `firmware/releases/*.MANIFEST.txt`.

```bash
# from the repository root
md5sum -c data_manifests/repo_testing_excluded.md5        # §1  (5,729 files)
md5sum -c data_manifests/legacy_capture_5d9982b.md5       # §1b (32 files)
# from testing/firmware_investigation_2026-10/ (paths start with sessions/)
cd testing/firmware_investigation_2026-10
md5sum -c ../../data_manifests/handover_sessions_raw.md5  # §2  (368 files)
```

All 6,129 files were verified at these locations on 2026-10-12.

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

### 1b. Capture from the original repository commit

Location: `testing/legacy_capture_5d9982b/capture/` (git-ignored). Manifest: `data_manifests/legacy_capture_5d9982b.md5` (32 files, 1.2 GB).

| Path | Files | Size | Content |
|---|---|---|---|
| `testing/legacy_capture_5d9982b/capture/data/` | `am273x_capture_Raw_0.bin`, `am273x_capture_Raw_1.bin` | 1.17 GB | Raw DCA1000 recording committed in the original local repository (commit `5d9982b`, "Initial project state") |
| `testing/legacy_capture_5d9982b/capture/frames/` | `frame_000000.bin` … `frame_000029.bin` | 94 MB | 30 frames split from it |

This capture existed only inside the old repository history. It was extracted byte-exact (git blob ids verified) on 2026-10-12, before that history was deleted. Its capture log CSV and the code that recorded it are on the `archive/history-before-2026-10-12` branch (`old_repo_snapshot_5d9982b/capture/`). Like §1, it was recorded with CCS-loaded shortrange firmware.

## 2. Jetson sessions from the firmware investigation

Location: `testing/firmware_investigation_2026-10/sessions/` (git-ignored raw files, next to the session metadata that **is** in git). Manifest: `data_manifests/handover_sessions_raw.md5` (368 files, 1.90 GB; paths relative to `testing/firmware_investigation_2026-10/`). Moved on 2026-10-12 from the handover folder `C:\Users\RadarDemo\Documents\Jetson_Radar_Sync_Capture_Handover_Firmware_Investigation\sessions\`, keeping the same layout, and verified identical. The raw IMU logs (`camera/capture/imu/`) are git-ignored too.

| Session | Raw files | Size | Content | Firmware |
|---|---|---|---|---|
| `stage3_01` | 239 radar `.bin`, `lidar/lidar.pcap`, `camera/camera.svo2`, 2 IMU `.csv` | 1.25 GB | Outdoors at night, one person walking with a metal plate at 12–14 m; LiDAR ground truth in git (`sync/lidar_target_truth.csv`) | r075m, QSPI: **~53.5% stale words** |
| `ipad_test_01` | 120 radar `.bin`, `lidar/lidar.pcap`, `camera/camera.svo2`, `sync/lidar_pcap_index.npz`, 2 IMU `.csv` | 0.65 GB | Indoors, radar facing a wall | r075m, QSPI: **~50.6% stale words** |

These two sessions are the evidence for the root cause (`testing/firmware_investigation_2026-10/investigation/REPORT.md` §2, §4). Keep them.

## 3. History and archives

**In git:** the orphan branch **`archive/history-before-2026-10-12`** (not part of `main`) holds three things that used to exist only on this machine:

- the text content of the original repository commit `5d9982b`;
- the unique source and config history of the four TI SDK cascade folders (`cascade`, `cascade - Copy` including its April 2026 backup, `cascade - Copy (2)`, `cascade - Copy (3)`);
- the Jetson's pre-rebuild firmware map and `.cfg` files.

Its `README.md` describes each folder. All 104 files were verified byte-identical to their originals.

**Deleted on 2026-10-12, after that branch and §1b were verified:**

- `C:\Users\RadarDemo\Documents\_git_backups\` (the pre-GitHub `.git`, 1 GB);
- `C:\ti\_archive_cascade_sdk_folders_20261012\` (46 MB).

What they held beyond the branch was reproducible build output only: object files and old `.xer5f`/`.map`.

**The handover folder** `C:\Users\RadarDemo\Documents\Jetson_Radar_Sync_Capture_Handover_Firmware_Investigation\` holds nothing unique any more:

- **Documents, code and firmware** are in git: `testing/firmware_investigation_2026-10/`, `firmware/releases/` and the archive branch.
- **Raw sessions** are in §2.
- **Superseded files** are its own pre-edit copies of three files that git has in updated form, plus Python bytecode.

## 4. Third-party documents kept locally (copyright)

| Location (working tree, git-ignored) | Reference | Why not in git |
|---|---|---|
| `testing/live_capture_validation/03_indoor_moving_subject_within_3m/logs/A_Hybrid_TDMA_DDMA_Approach_for_High_Resolution_Cascaded_Automotive_Radar_Systems_04-2025.pdf` | D. Kumlu, T. Vincon, M. Arsalan, E. Horne, "A Novel Hybrid TDMA-DDMA Approach for Imaging Automotive Radar Systems", IEEE Sensors Letters (manuscript 2025) | © IEEE: redistribution requires IEEE permission |

The AE-CFAR preprint in the same folder (`v1_covered_cced052c-….pdf`; Y. He et al., "AE-CFAR Multi-Target Detection for 24GHz Cascaded Automotive mmWave Radar", Research Square, doi:10.21203/rs.3.rs-9047454/v1) is CC BY 4.0 and **is** committed.
