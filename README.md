# Archive branch: history before 2026-10-12

This orphan branch is **not part of `main`**. It keeps the history that existed only in local folders on the Windows build station, so those folders could be deleted on 2026-10-12. Nothing here is built or maintained; for current work, use `main`.

| Folder | Origin | What it is |
|---|---|---|
| `old_repo_snapshot_5d9982b/` | The original local repository, commit `5d9982b` "Initial project state" | Every text file of that commit: earlier versions of the frozen capture/processing code and `config/`, `debug_context/` notes, the capture log CSV. Its raw `.bin` captures (1.2 GB) could not go to GitHub; they are on the build station under `testing/legacy_capture_5d9982b/` (git-ignored), listed in `main`'s `DATA_INDEX.md` with md5s. |
| `sdk_history/` | The TI SDK folders `ti\utils\test\cascade`, `cascade - Copy`, `cascade - Copy (2)`, `cascade - Copy (3)` (Mar–Oct 2026) | Source and config files that differ from everything on `main`. Includes: `cascade - Copy/am273x_backup_April_2026/` (the pre-correction `cascade_config.h` with the 48 kHz/µs slope comments, its `.history/` edits, the `.cfg`/JSON configs of the original four variants and their `_1frame` builds); the March snapshots `Copy (2)` / `Copy (3)`; the Ethernet experiment's `mssgenerated/`; and the retired build scripts (`build_all_configs.bat` and `build_two_variants.bat` are known to build wrong images). Build outputs were not kept; they are reproducible or superseded. |
| `handover_history/` | The Jetson handover folder | The Jetson's firmware map and the six old-variant `.cfg` files **before** the 2026-10-10 rebuild (Q-first `adcbufCfg`, `frameCfg … 50 …`, compression on), the map of the first r075m_v2 delivery, and REPORT.md as delivered. |

The current firmware source is `main:firmware/am273x_cascade/`, built through the SDK junction `ti\utils\test\cascade_radar`. The investigation that explains why these versions were superseded is `main:testing/firmware_investigation_2026-10/`.
