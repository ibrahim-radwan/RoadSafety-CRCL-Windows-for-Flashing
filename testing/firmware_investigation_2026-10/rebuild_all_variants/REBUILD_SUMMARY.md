# Rebuild of every range variant with the DSS L3 MEMINIT fix

Windows build station, 2026-10-10. **Nothing has been flashed.**

`firmware/` is a complete drop-in replacement for the Jetson's `cascaded_radar_capture_pipeline/firmware/`. It was built from `jetson_firmware_current/` (copied byte for byte, without its `MANIFEST.txt`), with 11 new variants added.

**Operator decisions applied:**

- DSS L3 MEMINIT in every new image.
- HPF 0/0 (175 kHz / 350 kHz) for all variants.
- Each variant at 250 ms and at 125 ms, except `r017m_calib_v2`, which is built only at 1000 ms.
- Everything else is unchanged from each variant's `cascade_config.h` block.

## Variants

| Variant | Base | Period | Window (m) | HPF1 knee | HPF reg | `.appimage` md5 | `.rprc` md5 | 125 ms feasible | Headroom* |
|---|---|---|---|---|---|---|---|---|---|
| r017m_v2 | r017m | 250 ms | 1.17 – 16.78 | 0.59 m | 0/0 | `6bfaa6a95e6813458d126ecbde5503f3` | `ea0113a2c507d42221c959ebbfbe1253` | — | ~22 dB |
| r017m_v2_8fps | r017m | 125 ms | 1.17 – 16.78 | 0.59 m | 0/0 | `29f8a8019260d98c2a9bf7d1a05f07cb` | `83e1d0f1d9cb8099ebca933e8735697e` | yes, 44.6 ms spare | ~22 dB |
| r017m_calib_v2 | r017m_calib | 1000 ms | 1.17 – 16.78 | 0.59 m | 0/0 | `bb3c9c87886d7813ecaf1f88c1ea51f3` | `3fdf1cef357ea2c379a72c634dee97f6` | n/a (1 fps) | ~22 dB |
| r050m_v2 | r050m | 250 ms | 1.75 – 50.00 | 0.87 m | 0/0 | `d580a23d0369e85e9b3762956be56481` | `1e693325f83a38098a40413413fcf2c2` | — | ~17 dB |
| r050m_v2_8fps | r050m | 125 ms | 1.75 – 50.00 | 0.87 m | 0/0 | `1f5565e75e3e2e03e4aa2c59ff0c2412` | `1cedb89a37e192e8bcb9e4da64ae7777` | yes, 44.6 ms spare | ~17 dB |
| r075m_v2 (unchanged) | r075m | 250 ms | 2.62 – 74.99 | 1.31 m | 0/0 | `b4ac5b97c468f93db27fef7915db7803` | `c17eaa9bb2c3ae28f539ef3e748c4025` | — | 23.6 dB (measured) |
| r075m_v2_8fps (unchanged) | r075m | 125 ms | 2.62 – 74.99 | 1.31 m | 0/0 | `8f5eb30afa4df1a1009d34868a3c9979` | `e9a61839ae92d923f39686b1426e0b57` | yes (proven on HW) | 23.6 dB (measured) |
| r100m_v2 | r100m | 250 ms | 3.51 – 100.15 | 1.75 m | 0/0 | `e734b66d721724e61691351f3ebe645b` | `5a01c4e8377cfe01f491c13f2a7ba3f9` | — | ~29 dB |
| r100m_v2_8fps | r100m | 125 ms | 3.51 – 100.15 | 1.75 m | 0/0 | `a9051ed3e3b2121780d8b9932026630a` | `fd3265dbc46c654b11032810d334da49` | yes, 44.6 ms spare | ~29 dB |
| r142m_v2 | r142m | 250 ms | 9.97 – 142.42 | 4.98 m | 0/0 | `c50685f13e0e67a1c655c4976b495ccd` | `034ab0fe1ad96d5a2f61b6315974f5c4` | — | ~47 dB |
| r142m_v2_8fps | r142m | 125 ms | 9.97 – 142.42 | 4.98 m | 0/0 | `a5f6f2268b3facc9d62cfd1967fcdca8` | `513a40b9484daae6816e68f894804130` | yes, 44.6 ms spare | ~47 dB |
| r168m_v2 | r168m | 250 ms | 5.87 – 167.82 | 2.94 m | 0/0 | `edaed92930677cbd0691e198ddb8553d` | `f8449e69fc2d948f31b76597deec3d33` | — | ~38 dB |
| r168m_v2_8fps | r168m | 125 ms | 5.87 – 167.82 | 2.94 m | 0/0 | `af4677d477265db9a7433a193ab426ce` | `2c6488ceddac002bac6e9b785ca4d55d` | yes, 44.6 ms spare | ~38 dB |

\* Headroom is an estimate; the derivation is under "Clipping risk" below. All 20 `.appimage` hashes in the map are distinct.

**Determinism.** `r075m_v2` and `r075m_v2_8fps` were rebuilt from the current source, which has the new `_V2` mapping in `cascade_config.h`. Both reproduced exactly: `c17eaa9b…/b4ac5b97…` and `e9a61839…/8f5eb30a…`.

## Timing feasibility

| Variant | Chirp (idle + ramp) | Chirping per frame | CBUFF time per chirp (8192 B, 4 × 600 Mbps = 27.3 µs) |
|---|---|---|---|
| r050m, r075m, r100m, r168m | 35 µs | 13.44 ms | 78% busy, 7.7 µs spare (proven on r075m_v2 at 8 fps) |
| r142m | 61 µs | 23.42 ms | 45% |
| r017m | 65 µs | 24.96 ms | 42% |
| r017m_calib | 164 µs | 62.98 ms | 17% |

**DCA1000 time on the wire:** 2160.5 packets × (delay + 12.2 µs).

- At **25 µs** (3125 ticks): **80.4 ms per frame**. For every 125 ms image the frame is busy for max(chirping, 80.4 ms) = 80.4 ms, leaving **44.6 ms spare**.
- At **50 µs** (6250 ticks): 134.4 ms per frame. **None of the 8 fps images works at 50 µs.** All 250 ms and 1000 ms images do.

**DCA buffering:** the worst case is the 35 µs chirp, where data arrives at 234 MB/s while the DCA drains at ~39 MB/s. That case is r075m_v2_8fps, already proven with 0 loss and 240 of 240 bursts aligned. Every other variant has a longer chirp and therefore needs less buffering.

**Thermal:** at 8 fps the transmit duty cycle doubles, up to 20% on r017m (25 ms of every 125 ms). No device limit is exceeded, but watch the board temperature on long 8 fps runs.

## Clipping risk

The HPF 0/0 corners let strong near returns through. My estimate scales from the one measurement available: a peak of 2,155 of 32,767 counts on r075m_v2_8fps (23.6 dB headroom), with returns down to its 2.62 m floor at 42 dB gain. For a point target at each variant's own floor, amplitude goes as 1/R² plus the RX-gain difference:

| Variant | Floor | RX gain | Δ vs r075m_v2 | Expected headroom |
|---|---|---|---|---|
| r050m_v2 | 1.75 m | 42 dB | +7.0 dB | **~17 dB, the tightest.** A car bumper or rider at ~2 m is the case to watch. |
| r017m_v2 / r017m_calib_v2 | 1.17 m | 30 dB | +14 dB (1/R²) − 12 dB (gain) | ~22 dB. r017m already ran HPF 0/0 at 30 dB in the May–June CCS sessions. |
| r100m_v2 | 3.51 m | 42 dB | −5.1 dB | ~29 dB |
| r168m_v2 | 5.87 m | 42 dB | −14 dB | ~38 dB |
| r142m_v2 | 9.97 m | 42 dB | −23 dB | ~47 dB |

This is a first-order guide, not a guarantee: it covers point targets only and ignores the HPF skirts. **Jetson check:** record the peak |sample| per session. Anything above ~16,000 counts deserves a look, and anything at 32,767 is clipping.

## Antenna calibration

- **Two inherited calibration sets.** The `antennaCalibParams` lines are unchanged from the original configs:
  - the **77 GHz shortrange set** in r017m, r017m_calib and their v2 images;
  - the **76 GHz longrange set** in every other variant.
- **How they were measured is not recorded.** `docs/RANGE_EQUATION_LEDGER.md` §6 lists "real measurements or placeholders?" as open. The 76 GHz set came from the longrange profile, which ran **HPF 2/2**, so if it was measured at all, it was measured at 2/2. The 77 GHz set came from shortrange, which was already 0/0.
- **Recalibration needed.** Repeat the calibration with the 0/0 images before trusting angle estimates:
  - **77 GHz:** use `r017m_calib_v2`, built for this purpose.
  - **76 GHz:** calibration depends on frequency, so the 77 GHz calib image cannot calibrate the 76 GHz variants. Use any 76 GHz v2 image (e.g. r050m_v2) with a corner reflector beyond its floor.
- **Geometry still unverified.** The TX/RX → azimuth table is unconfirmed (REPORT §4). Check it in the same session.

## Disassembly check vs each base image

**Method.** `source/fdiff.py` compares each pair function by function. It masks address operands, branch targets and literal-pool addresses, and keeps all other immediates. Full output is in `source/fdiff_all.txt`; the only lines filtered out are `__LINE__` assert arguments in `MmwCascade_initTask`, which shift by +1 because `main_mss.c` gained one `#include`. The same method on r075m → r075m_v2 reproduces the earlier manual finding.

**Result for every new image:**

- **Added functions:** `SOC_rcmStartMemInitDSSL3` and `SOC_rcmWaitMemInitDSSL3`.
- **`main`:** gains `2× bl` and `2× movs r0,#0xf`, i.e. MEMINIT start and wait on bank mask ALL.
- **`Mmwave_populateDefaultChirpControlCfg`:**
  - `movw r0,#0x202; strh.w r0,[sp,#0x84]` is removed (HPF1/HPF2 = 2/2 → stay 0). Exceptions: r017m_v2 and r017m_v2_8fps, where the base was already 0/0, so there is no change.
  - For `_8fps` images, `movw/movt 0xF080/0x02FA` (250 ms) becomes `0x7840/0x017D` (125 ms). For r017m_calib_v2 the period is unchanged (1000 ms).
- **Noise:** alignment padding (`movs r0,r0`, `.word 0`, `nop`) and one mis-disassembled data word in `CacheP_enable`.

No other function differs in any image.

## `fill_firmware_map.py --root .` on Windows

`derived`, `appimage`, `cfg` and `rprc` are **ok for all 20 variants**, with **20/20 `.rprc` fingerprints verified**. `flash` is `NOFILE` for all 20, as expected: the configs carry absolute Jetson paths. Full output: `fill_firmware_map_output.txt`.

```
  variant       derived  appimage     cfg  rprc   flash  appimage_md5
  r017m              ok        ok   ok/10    ok  NOFILE  871ae3071e6636604531ea7ab8118470
  r017m_calib        ok        ok   ok/10    ok  NOFILE  1db2106479044f03d071b39da5cfab05
  r050m              ok        ok   ok/10    ok  NOFILE  c2c7f2980469d41831b6ce5527d50fbd
  r075m              ok        ok   ok/10    ok  NOFILE  f0e6a73d4c7d35d92e2128305f0b1867
  r100m              ok        ok   ok/10    ok  NOFILE  c68bd941c1d83959575eb5efd09365ae
  r142m              ok        ok   ok/10    ok  NOFILE  47a0f48f95a267f758b99a9f7e9faeb7
  r168m              ok        ok   ok/10    ok  NOFILE  d6792001e15e4c202232373a92fb2d2d
  r075m_v2           ok        ok   ok/10    ok  NOFILE  b4ac5b97c468f93db27fef7915db7803
  r075m_v2_8fps      ok        ok   ok/10    ok  NOFILE  8f5eb30afa4df1a1009d34868a3c9979
  r017m_v2           ok        ok   ok/10    ok  NOFILE  6bfaa6a95e6813458d126ecbde5503f3
  r017m_v2_8fps      ok        ok   ok/10    ok  NOFILE  29f8a8019260d98c2a9bf7d1a05f07cb
  r017m_calib_v2      ok        ok   ok/10    ok  NOFILE  bb3c9c87886d7813ecaf1f88c1ea51f3
  r050m_v2           ok        ok   ok/10    ok  NOFILE  d580a23d0369e85e9b3762956be56481
  r050m_v2_8fps      ok        ok   ok/10    ok  NOFILE  1f5565e75e3e2e03e4aa2c59ff0c2412
  r100m_v2           ok        ok   ok/10    ok  NOFILE  e734b66d721724e61691351f3ebe645b
  r100m_v2_8fps      ok        ok   ok/10    ok  NOFILE  a9051ed3e3b2121780d8b9932026630a
  r142m_v2           ok        ok   ok/10    ok  NOFILE  c50685f13e0e67a1c655c4976b495ccd
  r142m_v2_8fps      ok        ok   ok/10    ok  NOFILE  a5f6f2268b3facc9d62cfd1967fcdca8
  r168m_v2           ok        ok   ok/10    ok  NOFILE  edaed92930677cbd0691e198ddb8553d
  r168m_v2_8fps      ok        ok   ok/10    ok  NOFILE  af4677d477265db9a7433a193ab426ce
  (PROBLEMS: 20 x "flash_<v>.cfg points at /home/jetson/..., which does not exist")
  20/20 variants have an appimage hash
  20/20 variants had their .rprc fingerprint VERIFIED
```

**Flash column checked anyway.** On a throwaway copy with the Jetson prefix rewritten to the local path, all **20/20 variants are `ok` in every column, including `flash`**, with no problems reported and exit code 0.

**Parser check.** All 20 `.cfg` files also parse cleanly in the Jetson's updated `radar_config.parse_cfg_file` and in `capture.config.parse_cascade_cfg`. Each gives `iq_swap = False`, a slope matching the map, and "no pipeline/firmware mismatches detected".

## Expected `MANIFEST.txt` differences vs `jetson_firmware_current/MANIFEST.txt`

`MANIFEST.txt` has 124 lines, against 58 in the baseline; it uses the same `<md5>  ./<path>` format. Verified by diffing the two:

- **Changed (7):**
  - `./firmware_map.json`: 11 new entries, `generated`, and `conventions.dca_wire_time` / `v2_family` / `antenna_calibration`.
  - The six corrected old `.cfg` files: `./r017m/cascade_r017m.cfg`, `./r017m_calib/cascade_r017m_calib.cfg`, `./r050m/cascade_r050m.cfg`, `./r100m/cascade_r100m.cfg`, `./r142m/cascade_r142m.cfg` and `./r168m/cascade_r168m.cfg`.
- **Added (66):** six files for each of the 11 new variants: `<v>/am273x_cascade_<v>.appimage`, `<v>/cascade_<v>.cfg`, `<v>/flash_<v>.cfg`, `_build_record/<v>/<v>.rprc`, `_build_record/<v>/<v>.xer5f` and `_build_record/<v>/am273x_cascade_mss.map`.
- **Removed:** none.
- **Unchanged:** every old `.appimage`, `.rprc`, `.xer5f`, `.map`, flash config and helper script is byte-identical. That covers `flash_provision.cfg`, `fill_firmware_map.py` and `make_flash_cfgs.py`. `make_flash_cfgs.py` is unchanged and was not used: run here it would rewrite every flash config with Windows paths. The new flash configs are the r075m_v2 template with the variant name substituted, in the identical format, writing only `0xA0000`.

**Corrections to the old `.cfg` files.** The images themselves are unchanged. These are the edits already made to `cascade_r075m.cfg`, now applied to the others:

- `adcbufCfg` → `-1 0 0 1 1`.
- `frameCfg` → `0 5 64 0 <250|1000> 1 0`.
- `compressionCfg` → `-1 0 0 0.5 8` (r050m, r100m, r142m and r168m had enabled = 1; r017m and r017m_calib were already 0).
- `dataPathConfig` → `… 132 132 72 0`.
- A regenerated header that lists exactly what changed and warns that QSPI-booted data from these images is ~50% stale.
- `antennaCalibParams` copied verbatim. Inert commands (`cfarCfg`, `gtrack`, `app*`, …) are dropped, as in the r075m files.

## Windows-side DCA1000 packet delay

| File | `packetDelay_us` |
|---|---|
| `cascaded_radar_win_dev/config/AM273X_Capture_fixed.json`, **used by the project's Windows capture** (`capture/config.py:27`) | **50** |
| `mmwave_studio_03_00_00_14/mmWaveStudio/PostProc/AM273X_Capture{,_fixed,_updated}.json`, `…/capture/…`, `…/cascaded_radar/config/…` | **50** |
| `…/ti/utils/test/cascade/am273x/cf_cascade.json`, mmWave Studio 03.01 `PostProc/cf.json`, `JSONSampleFiles/22xx/22xx.setup.json` | 25 |

**Any 8 fps capture made on Windows with the project's config would lose data silently.** Recommendation: set `packetDelay_us` to 25 in `config/AM273X_Capture_fixed.json`, and in the mmWave Studio PostProc copies if they are still used. I did not change these, because the Windows capture path is frozen; say if you want it done.

## Source (`source/`)

| File | Content |
|---|---|
| `cascade_config.h` | `_V2` mapping at the top (each define selects its base block); HPF and period overrides after the selection. The `R075M_V2` block is untouched. |
| `main_mss.c` | MEMINIT, the same as for r075m_v2 |
| `makefile` | `mssTestInf` also builds the 11 new variants |
| `build_one_inf.bat` | builds one variant without disturbing the other build directories |
| `build_v2_variants.ps1` | build + `elf2rprc` + `multicoreImageGen` straight into the Jetson-layout tree, with uniquely named intermediates |
| `gen2.py` | map entries, `.cfg` files and flash configs, generated from the registers |
| `fdiff.py`, `fdiff_all.txt` | disassembly diff tool and its output |
