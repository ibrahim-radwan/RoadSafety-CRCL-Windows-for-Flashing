# Range Variants — Build Spec and Execution Plan

Created 2026-10-02. Phase W corrected 2026-10-03; W1 corrected again after a
dry run caught a rounding error and a missed file; **J2 redesigned 2026-10-03
after the HPF range floor was discovered — the original indoor test could not
have worked.** **§1 naming and Phase J1 rewritten 2026-10-06**: Phase W is
complete, seven variants are packaged and on the Jetson, and J1 now covers
the uniflash configs.

> **Status 2026-10-12: superseded in three places by the October investigation.** Read `testing/firmware_investigation_2026-10/README.md` first.
>
> 1. **The seven images packaged in Phase W stream ~50% stale words when booted from QSPI.** The DSS L3 MEMINIT was missing; CCS loading had hidden it. Every variant was rebuilt with the fix as `<v>_v2` (250 ms) and `<v>_v2_8fps` (125 ms), plus `r017m_calib_v2` (1000 ms). These were deployed to the Jetson on 2026-10-12 (`firmware/releases/2026-10-10_v2/`). Do not flash the Phase W images.
> 2. **HPF is 0/0 (175/350 kHz) on every v2 image**, by operator decision. That reverses this document's "do not lower HPF2" guidance (§3b) for the vehicle dataset, where near targets matter. New windows are in the §3b addendum.
> 3. **J1b / J2 used r075m.** Those steps now apply to r075m_v2. r075m_v2 has been confirmed on hardware (0.00% stale words, a person tracked down to ~2 m).
>
> Two further corrections:
> - **I/Q order:** the data is I-first.
> - **DCA1000 packet delay:** it must be 25 µs for 8 fps.
>
> Both are in `testing/firmware_investigation_2026-10/investigation/JETSON_DATA_FORMAT.md`. The `docs/` file names below are now upper-case (`RANGE_EQUATION_LEDGER.md`, `FIRMWARE_PACKAGING_WINDOWS.md`, `BUILD_DETERMINISM_FINDING.md`). The Jetson tree is `cascaded_radar_capture_pipeline/firmware/`, not `cascaded_radar_linux_dev/firmware/`.

Companions: `Range_Equation_Ledger.md` holds the evidence behind these
numbers; `Firmware_Packaging_Windows.md` holds the mechanics of turning a
build into a flash package; `Build_Determinism_Finding.md` explains why the
`.xer5f` hash must never be used as an identity check.

Goal: 50 / 75 / 100 m firmware packages, flashed and capturing on Jetson,
with processing and replay consistent with whichever config is live. Radar
only. Camera, sync and Lidar come after.

---

## 1. Environment split

| | Windows | Jetson AGX Orin |
|---|---|---|
| role | **build only** | **flash, capture, process, replay** |
| why | the AM273x SDK + CCS toolchain live here | target deployment platform |
| produces | `.xer5f`, `.rprc`, `.appimage`, `.cfg` | session data |
| consumes | `cascade_config.h`, `mssTestInf` | the firmware tree below |

The handoff is one directory per variant. Keep it that narrow — nothing else
should need to cross.

**Status 2026-10-06: seven variants built, packaged and on the Jetson.** The
scheme below replaces the three-variant naming this section originally
proposed; the short names are the **actual** max range, zero-padded, so a
directory listing sorts by real reach and the VERYLONGRANGE-is-shorter-than-
LONGRANGE inversion is self-evident without a document.

| short name | config define | slope reg | max range |
|---|---|---|---|
| `r017m` | `CASCADE_CFG_SHORTRANGE` | 925 | 16.78 m |
| `r017m_calib` | `CASCADE_CFG_SHORTRANGE_CALIB` | 925 | 16.78 m |
| `r050m` | `CASCADE_CFG_R050M` | 621 | 50.00 m |
| `r075m` | `CASCADE_CFG_R075M` | 414 | 74.99 m |
| `r100m` | `CASCADE_CFG_R100M` | 310 | 100.15 m |
| `r142m` | `CASCADE_CFG_VERYLONGRANGE` | 109 | 142.42 m |
| `r168m` | `CASCADE_CFG_LONGRANGE` | 185 | 167.82 m |

Per-variant directory on the Jetson, under
`cascaded_radar_linux_dev/firmware/<variant>/`:

```
am273x_cascade_<v>.xer5f      build output   (provenance only, never hashed)
am273x_cascade_<v>.map        link map       (provenance only)
am273x_cascade_<v>.rprc       intermediate   (the deterministic fingerprint)
am273x_cascade_<v>.appimage   flashed image
cascade_<v>.cfg               read by processing and replay
flash_<v>.cfg                 read by uart_uniflash.py
```

`firmware_map.json` at the root ties them together and records the derived
radar parameters per variant. **Never use the `.xer5f` hash as an identity
check** — it is non-deterministic (86.7% metadata); the `.rprc` and
`.appimage` are reproducible. See `Build_Determinism_Finding.md`.

---

## 2. Parameters

All three new variants hold the LONGRANGE values and change **only** the
slope register.

| target | `CFG_PROFILE_FREQ_SLOPE_CONST` | slope MHz/µs | actual max | range res |
|---|---|---|---|---|
| 50 m | **621** | 29.9817 | 50.00 m | 0.195 m |
| 75 m | **414** | 19.9878 | 74.99 m | 0.293 m |
| 100 m | **310** | 14.9667 | 100.15 m | 0.391 m |

Common to all three:

| field | value | note |
|---|---|---|
| start freq | 76 GHz | |
| idle time | 400 (4 µs) | |
| ADC start | 300 (3 µs) | |
| ramp end | 3100 (31 µs) | holds 3 + 25.6 = 28.6 µs ✓ |
| sample rate | 10000 ksps | |
| ADC samples | 256 | **do not change** — see §3 |
| loops | 64 | **do not change** |
| chirps | 6 | **do not change** |
| HPF1 / HPF2 | 2 / 2 | 350 kHz / 1.4 MHz — **sets a minimum range**, see §3b |
| RX gain | 42 dB | |
| periodicity | 250 ms (4 fps) | |

Derived, identical across all three: `T_loop` 210 µs, **v_max 4.696 m/s**,
v_res 0.1467 m/s. Top of swept band 76.93 GHz at the 50 m config — inside
76–81. Max slope 30.0 MHz/µs against 44.7 already proven by SHORTRANGE.

Slope register uses the **correct** TI LSB of 48.27976 kHz/µs
(`3.6e6 × 900 / 2²⁶`), not the 48 kHz/µs that the existing four variants use.
See the ledger, §2.

---

## 3. Two properties that follow from the maths

**Frame size is unchanged: 3,145,728 B.** Because N, loops and chirps are
fixed, `256 × 384 chirps × 8 RX × 4 B` is identical to SHORTRANGE. **The
capture, split and DCA scripts need no changes whatsoever.** This is why fs
stays at 10000 rather than being raised — it keeps the handoff to Jetson at
"drop in one directory".

**Range resolution is exactly `max_range / 256`, regardless of fs.** Since
`B_sampled = slope × N/fs` and `slope = c·fs/(2R)`, the fs cancels:
`B_sampled = c·N/(2R)`, so `res = R/N`. Raising the sample rate cannot buy
resolution back at a given max range. The only levers are shorter range or
more samples — and more samples changes the frame size, which breaks the
first property.

---

## 3b. The HPF range floor — each config has a usable WINDOW, not just a max

The receiver high-pass corners impose a **minimum** range, because beat
frequency is proportional to range:

```
f_beat = 2 × slope × R / c      so      R_min = f_corner × c / (2 × slope)
```

Nothing in this project had recorded this. It changes the test design.

| variant | slope | HPF1 → floor | HPF2 → floor | max range | **usable window** |
|---|---|---|---|---|---|
| SHORTRANGE | 44.6588 | 175 kHz → 0.59 m | 350 kHz → **1.17 m** | 16.78 m | 1.2 – 16.8 m |
| LONGRANGE | 8.9318 | 350 kHz → 5.87 m | 1.4 MHz → **23.50 m** | 167.82 m | 23.5 – 167.8 m |
| VERYLONGRANGE | 5.2625 | 350 kHz → 9.97 m | 1.4 MHz → **39.88 m** | 142.42 m | 39.9 – 142.4 m |
| 50 m | 29.9817 | 350 kHz → 1.75 m | 1.4 MHz → **7.00 m** | 50.00 m | 7.0 – 50.0 m |
| 75 m | 19.9878 | 350 kHz → 2.62 m | 1.4 MHz → **10.50 m** | 74.99 m | 10.5 – 75.0 m |
| 100 m | 14.9667 | 350 kHz → 3.51 m | 1.4 MHz → **14.02 m** | 100.15 m | 14.0 – 100.2 m |

Two consequences worth stating to the end user before the campaign:

- **The long-range builds are blind close in.** The 75 m build sees nothing
  inside 10.5 m. For vehicle-mounted collection that is usually desirable —
  the corner suppresses strong near-field returns that would otherwise eat
  the dynamic range — but it must not come as a surprise.
- **SHORTRANGE's near-field blind spot is analogue, not algorithmic.** The
  collected sessions show no detection closer than 1.583 m against a 1.175 m
  HPF2 floor. Anyone trying to pull detections closer should be looking at
  `HPF2`, not at `dbscan_eps` or `cfar_margin`.

**Do not lower HPF2 on the new variants to make a test convenient.** The
1.4 MHz corner is deliberate on a long-range profile; changing it means
testing a config you do not intend to ship.

### §3b addendum (2026-10-10): the v2 images ship with HPF 0/0

The operator chose HPF 0/0 (175 kHz / 350 kHz) for every variant, because a
two-wheeler dataset needs near targets. The guidance above still applies to
testing: do not change HPF just to make a test convenient. But the shipped
configuration is now 0/0, and windows are:

| variant | HPF1 175 kHz → | HPF2 350 kHz → floor | max range | **usable window (v2)** | was (HPF 2/2) |
|---|---|---|---|---|---|
| r017m (SHORTRANGE) | 0.59 m | **1.17 m** | 16.78 m | 1.17 – 16.78 m | unchanged (already 0/0) |
| r017m_calib | 0.59 m | **1.17 m** | 16.78 m | 1.17 – 16.78 m | 4.70 m floor |
| r050m | 0.87 m | **1.75 m** | 50.00 m | 1.75 – 50.00 m | 7.00 m floor |
| r075m | 1.31 m | **2.62 m** | 74.99 m | 2.62 – 74.99 m | 10.50 m floor |
| r100m | 1.75 m | **3.51 m** | 100.15 m | 3.51 – 100.15 m | 14.02 m floor |
| r168m (LONGRANGE) | 2.94 m | **5.87 m** | 167.82 m | 5.87 – 167.82 m | 23.50 m floor |
| r142m (VERYLONGRANGE) | 4.98 m | **9.97 m** | 142.42 m | 9.97 – 142.42 m | 39.88 m floor |

**Headroom.** The lower corners admit stronger near returns. On r075m_v2_8fps
the measured peak was 2,155 of 32,767 counts (23.6 dB headroom). Expected
headroom scales from ~17 dB on r050m_v2 to ~47 dB on r142m_v2; see
`testing/firmware_investigation_2026-10/rebuild_all_variants/REBUILD_SUMMARY.md`.

**Overlap windows (J2).** These are now much wider. For example, r017m ↔ r075m_v2 overlap
2.62–16.78 m, so the cross-config range check can be done indoors.

**HPF1 floors in the table above.** The "HPF1 → floor" column of the main
table uses 350 kHz for register 2, which is correct. `firmware_map.json` had
used 700 kHz (2× too large) until 2026-10-10; it is fixed there and in the
Jetson's `fill_firmware_map.py`.

---

## 4. Does the `.cfg` slope affect capture?

**No. Processing and replay only.**

| stage | source of truth | role of the slope |
|---|---|---|
| radar hardware | register compiled into `.xer5f` | **sets the actual sweep** |
| capture / split | `cascade_csirx.h` geometry → 3,145,728 B | none — byte layout only |
| processing / replay | `.cfg` field `prof[7]` | **labels the range axis** |

The DCA1000 records bytes; the `.cfg` is read only when something interprets
them. Consequences:

- **Every frame already collected is recoverable.** The LSB error is a label
  error, fixed by re-processing. No recapture needed, ever.
- **But the failure mode changes with seven variants.** Processing SHORTRANGE
  data against the 75 m `.cfg` would report ranges 4.5× wrong and nothing
  would warn. With one variant this was impossible. See §6.

---

## 5. Phases

### Phase W — Windows, build and package — **COMPLETE 2026-10-06**

Mechanics, exact commands and toolchain paths are in
`Firmware_Packaging_Windows.md`. This is the ordering.

**W1 — correct the existing baseline first, as its own change**

1. Fix the LSB in `cascade_config.h`: rewrite the four existing variant
   comments from their registers, leave the registers alone. Firmware
   behaviour is unaffected — only comments move. Correct values:

   | variant | slope | B_samp | res | max R | T_loop | v_max | v_res |
   |---|---|---|---|---|---|---|---|
   | LONGRANGE | 8.9318 | 228.7 M | 0.6556 | 167.82 m | 210 µs | 4.6960 | 0.1467 |
   | SHORTRANGE | 44.6588 | 2286.5 M | 0.0656 | 16.78 m | 390 µs | 2.4958 | 0.0780 |
   | SHORTRANGE_CALIB | 44.6588 | 2286.5 M | 0.0656 | 16.78 m | 984 µs | 0.9892 | 0.0309 |
   | VERYLONGRANGE | 5.2625 | 269.4 M | 0.5563 | 142.42 m | 366 µs | 2.6944 | 0.0842 |

   Delete the `≈ 8883/48` style annotations — that `/48` *is* the bug, in a
   form that looked like a helpful sanity check, which is why it survived
   four variants and every session.

   Also add the two forced identities to each block, as free self-checks for
   the next editor: `max_range = range_res × 256` and `v_max / v_res = 32`.
   The old comments violated both, which is how they were proven wrong
   without having to pick a convention.

   Note the existing `Max Velocity` figures are not merely rounded — they are
   **~4.2× too high** in every block, because they omit the 6-chirp TDM
   factor from `T_loop` and so describe a single-TX radar. Someone sizing a
   scenario from `19.78 m/s` would believe the radar handles highway speeds
   when the real limit is 4.70 m/s.

   **Outstanding:** line 197 still reads `/* 44.41 MHz/us */` for
   SHORTRANGE_CALIB, and the header's config list (lines 9–12) still names
   only four configs. Both deliberately deferred.

2. Fix the slope field (`profileCfg` token 7) in the `.cfg` files. Use **four
   decimal places**, matching the ledger's corrected-values table exactly:

   | variant | current | → | residual error |
   |---|---|---|---|
   | SHORTRANGE | `44.41` | **`44.6588`** | 0.0000% |
   | LONGRANGE | `8.883` | **`8.9318`** | 0.0005% |
   | VERYLONGRANGE | `5.23` | **`5.2625`** | 0.0001% |

   Three decimals is not enough for VERYLONGRANGE: `109 × 0.0482797623 =
   5.2624941`, whose fourth digit is a 4, so it rounds **down** to 5.262 —
   and 5.262 still leaves a 0.0094% residual, twenty times the others. Four
   decimals removes the question for all three.

   **There are four files, not three.** Two copies of
   `cascade_shortrange.cfg` exist and **both are live, in different entry
   points**:

   | file | read by |
   |---|---|
   | `config/cascade_shortrange.cfg` | `main.py:63` — processing CLI default |
   | `config/build_shortrange_inf/cascade_shortrange.cfg` | `config.py:26` `CASCADE_CFG_PATH` — live capture and replay |
   | `config/build_longrange_inf/cascade_longrange.cfg` | — |
   | `config/build_verylongrange_inf/cascade_verylongrange.cfg` | — |

   Edit only one shortrange copy and offline processing and live capture will
   silently disagree about the range axis. `radar_config.py:71`,
   `diag_pipeline_audit.py:604` and `diag_xyz.py:64` each carry their own
   shortrange default as well — check which copy each resolves to before
   comparing results between two tools.

3. Re-process one existing SHORTRANGE session and confirm the shift. Ranges
   get **smaller**, because range is inversely proportional to slope:

   | variant | new/old | shift |
   |---|---|---|
   | SHORTRANGE | 0.994429 | **−0.5571%** |
   | LONGRANGE | 0.994536 | −0.5464% |
   | VERYLONGRANGE | 0.993824 | −0.6176% |

   A 5.0000 m detection becomes 4.9721 m.

   Detection happens in **bin** space — the FFT is untouched and only the
   axis label changes — so every `rng_m` scales by the same factor, **to
   within the CSV's stored precision**. `points.csv` writes `rng_m` to 4 dp,
   so each value carries ±5e-5 m of rounding and the per-point ratio
   inherits a scatter of `(e_a − e_b)/r` — about 2e-5 at 5 m. Normalise each
   residual by its own range and it must sit inside one quantisation step;
   the scatter should also fall as 1/range, which is the positive signature
   of rounding. `verify_lsb_fix.py` implements exactly this.

   Expect **zero** frames with a changed point count. A few gates are in
   metres (`dbscan_eps = 0.80`, `cross_cluster_range_m = 0.35`,
   `max_range_m`), so a flip is possible in principle — but the 2026-10-03
   run over 326 frames produced none. If a future config change *does*
   produce flips, that means a detection sits within 0.56% of a gate
   boundary and is worth looking at, not shrugging off.

   This check is only available while nothing else has changed, which is why
   W1 is its own step.

   **Status 2026-10-03: PASS.** 326 frames, 576 points, mean ratio
   0.99442958 against 0.994429 expected — deviation 7.09e-07, zero count
   changes.

**W2 — add the new variants — COMPLETE**

4. Add `CASCADE_CFG_R050M`, `CASCADE_CFG_R075M`, `CASCADE_CFG_R100M`
   branches to `cascade_config.h`.
5. Add the matching `build_*_inf` blocks to `mssTestInf` in `makefile`,
   copying the existing `build_longrange_inf` block and changing only the
   `-D` define and the output directory. `mssTestInf` already runs
   `mssTestClean` before every variant, so stale objects are not a risk —
   an earlier version of this spec claimed otherwise and was wrong.
6. Build all seven **in one session**, while the environment is known-good.
7. ~~**Hash all seven `.xer5f`.**~~ **This gate was logically invalid and has
   been moved.** Two builds of the *same* variant produce different `.xer5f`
   hashes — the file is 86.7% non-deterministic metadata — so distinct
   hashes prove nothing about whether a `-D` define took effect. **Gate on
   the `.rprc` instead**, which is reproducible: same `.xer5f` → same
   `.rprc`, and seven variants → seven distinct `.rprc`. Verified
   2026-10-06. See `Build_Determinism_Finding.md`.

**W3 — package each variant — COMPLETE**

8. `elf2rprc.js` on the variant's `.xer5f`.
9. `multicoreImageGen.js --devID 55 ... @0`, output named for the variant.
10. **Move or rename the `.rprc` before starting the next variant.** Every
    `.xer5f` emerges as `am273x_cascade_mss.xer5f`, so every conversion
    writes the same `am273x_cascade_mss.rprc` into the SDK's `tools\boot`.
    Build two in sequence without moving it and the second silently
    overwrites the first, and the `.appimage` may not hold the sweep you
    think. Nothing warns.
11. **Verified 2026-10-06:** seven distinct `.rprc`, seven distinct
    `.appimage`, and r075m's `.appimage` reproduced the hand-typed control
    value `f0e6a73d4c7d35d92e2128305f0b1867` — confirming the batch
    `multicoreImageGen` loop matches the manual command.

**W4 — the processing configs — COMPLETE**

12. Seven `.cfg` files, each differing from its source by exactly three
    lines (`profileCfg` slope, `appSceneryParams` y_max, `gtrack` range
    gate). Sources: r017m/r017m_calib from shortrange (77 GHz, own
    calibration set); r142m from verylongrange; r050m/r075m/r100m/r168m from
    longrange (76 GHz calibration set). All tuned parameters — `cfarCfg`,
    `compressionCfg`, `antennaCalibParams1–3`, `appGatingParams`,
    `aoaFovCfg`, `hsi*`, `dataPath*` — carried over untouched.
    `appSceneryParams` y_min deliberately left alone: raising a floor could
    gate real detections.

**Exit criterion — met:** seven complete per-variant directories on the
Jetson, `firmware_map.json` filled and self-consistent, all `.appimage` and
`.rprc` hashes mutually distinct.

### Phase J1 — Jetson, flash and capture one variant

**J1a — write the flash configs.** `uart_uniflash.py` reads a config file
naming what to write where. Two offsets matter on AM273x:

| offset | content | varies by variant? |
|---|---|---|
| `0x0` | `sbl_qspi.release.tiimage` | **no** — identical for all seven |
| `0xA0000` | that variant's `.appimage` | **yes — the only thing that varies** |

`--flash-writer=sbl_uart_uniflash.release.tiimage` is the UART bootstrap, not
a flash write. It appears in every config and never changes. The `0xA0000`
application slot is the MCU+ SDK default and is already proven correct by the
board's working QSPI boot — stronger evidence than the documentation.

**Keep the bootloader out of the per-variant configs.** The obvious pattern
is one config per variant that writes both offsets. Don't: variant switching
happens repeatedly across J1–J3, and re-writing the SBL each time buys
nothing while risking something. A corrupted write to `0x0` leaves the board
unbootable; a corrupted write to `0xA0000` leaves the SBL intact and the
board still recoverable over the same UART. So:

```
firmware/flash_provision.cfg        SBL at 0x0        — run ONCE
firmware/<variant>/flash_<v>.cfg    appimage 0xA0000  — every variant switch
```

**Generate them, don't copy-paste them.** Seven configs each naming their
variant twice and differing by one line is the same shape as the three
identically-named `.xer5f` files (§1) and the two live copies of
`cascade_shortrange.cfg` (W1 step 2) — a class of error this project has
already been bitten by twice. `make_flash_cfgs.py` derives all eight from
`firmware_map.json`, so the variant name has a single source and a wrong
pairing cannot be written in the first place. Run it, then verify:

```
python3 make_flash_cfgs.py --write
python3 fill_firmware_map.py          # check 5 covers the flash configs
```

Check 5 confirms, per variant, that `flash_<v>.cfg` writes exactly one file
to `0xA0000`, that it is this variant's `.appimage`, that it resolves inside
this variant's own directory, that it hashes to the recorded `appimage_md5`,
and that the config does not also write `0x0`. **This closes the last
unverified link in the chain** — until now nothing connected the flash config
to the image whose provenance the rest of the map establishes. A config
pointing at a sibling's image would flash the wrong sweep with no symptom
other than every range being wrong by a clean ratio.

Both scripts default to the Jetson tree
(`~/dev/CascadedRadarRoadSafetyOnTwoWheelers/cascaded_radar_linux_dev/firmware`),
so no `--root` is needed there. Running them anywhere else — a staging USB,
for instance — does need it.

Worth checking once: whether this SDK's `uart_uniflash.py` supports
`--operation=flash-verify`. If it does, it reads the image back and compares,
which would turn "the command returned 0" into actual evidence the write
landed.

**J1b — flash and capture.**

1. Flash `r075m` over QSPI using `firmware/r075m/flash_r075m.cfg`.
2. **Log the source `.appimage` path and hash in the flashing script
   output**, and write it to `~/.radar_flashed` — see §6.
3. Capture 100+ frames. Confirm 3,145,728 B per frame, 0.00% loss, and that
   the frame count and rate match 4 fps.

**Exit criterion:** a clean capture at the r075m config,
`fill_firmware_map.py` reporting `ok` in all five columns, and
`~/.radar_flashed` naming the image that is actually in flash.

### Phase J2 — acceptance test, in the overlap window

**This test cannot be done at 4–6 m.** An earlier version of this spec said
it could, which was wrong: the 75 m build's HPF2 corner puts its floor at
10.50 m (§3b), so a 5 m target produces a 667 kHz beat that the analogue
filter attenuates before the ADC. The 75 m run would see nothing and the
obvious reading would be that the build is broken.

**Use the overlap window instead.** Consecutive configs share a band where
both can see:

| pair | overlap | usable for |
|---|---|---|
| SHORTRANGE ↔ 50 m | **7.0 – 16.8 m** | validating 50 m |
| SHORTRANGE ↔ 75 m | **10.5 – 16.8 m** | validating 75 m |
| 50 m ↔ 75 m | 10.5 – 50.0 m | either |
| 75 m ↔ 100 m | 14.0 – 75.0 m | validating 100 m |

A 20 m corridor or a car park covers the first two. Validate by chaining:
shortrange → 50 m → 75 m → 100 m, each pair measured where both configs see
the target. **Do not validate 100 m against shortrange** — they overlap only
14.0–16.8 m, under 3 m of usable window.

**Cross-config range check.** Tape-measured target at three distances inside
the overlap (12, 14 and 16 m for the shortrange ↔ 75 m pair). The two
configs derive range from different registers and slopes, so physics requires
them to report the same distance. Agreement means both axes are right;
disagreement gives a ratio that identifies which one is wrong. **This detects
an error without a tape measure at all** — the tape then says which config is
off.

**Static targets need the filters off.** Run with `clutter=OFF` and
`zeroDC=0` for a stationary reflector, or MTI deletes it and you get zero
detections — exactly what sank the May reflector attempt (ledger §5). For a
walking subject the defaults are fine. Do both: static with filters off for
range, moving with filters on for Doppler.

**Doppler cross-check.** Walk toward and away. `v_res` differs between the
configs (0.078 vs 0.147 m/s) but measured walking speed must match.

**What this test cannot show.** A 0.5 m-deep person spans 7.6 range bins at
SHORTRANGE but **1.7 at 75 m**, so the multi-point body cloud will not
reproduce on a long-range profile — expect roughly one point per subject.
That is geometry, not a defect, and the end user should be told before they
see it, since multi-point detection is what they value about the cascade.

**Exit criterion:** reported range agrees between configs and with the tape
to better than 1%; walking speed agrees between configs.

### Phase J3 — repeat for 50 m and 100 m

Same as J1–J2, following the chain in the table above. Then outdoor range
validation, where the long profiles can actually be exercised.

### Phase S — sensors (after the above)

Sync review, camera script version, Lidar integration.

---

## 6. The one addition this plan needs

Flashing moved to Jetson and there are now seven variants in rotation.
Nothing currently records which image is in flash, and QSPI boot removes the
loader log line that identified it for the May–June sessions.

Three small changes prevent a provenance hole that would be expensive later:

1. **Flashing script:** log the source `.appimage` path and hash, and write
   it to a file on the Jetson (e.g. `~/.radar_flashed`) that survives
   reboots.
2. **Capture manifest:** record the `.cfg` filename and hash used, plus the
   contents of that flashed-image record.
3. **Processing interlock:** read `~/.radar_flashed`, look the variant up in
   `firmware_map.json`, and **refuse to run if `--cfg` disagrees**. This is
   the change that makes the §4 failure mode impossible rather than merely
   documented. Before building it, grep the Jetson for hardcoded
   `cascade_shortrange.cfg` defaults — W1 step 2 found five of them, and any
   one still in place would make the interlock trivially bypassable.

This is the cheapest item in the plan and it directly prevents repeating the
work that was needed to attribute the May data.

---

## 7. One thing worth doing out of order

Everything camera-related is correctly deferred — except a five-minute smoke
test. Confirm `pyrealsense2` imports and the current D455 script opens a
stream on the Jetson, today.

Not the sync review, not the version reconciliation. Just: does it run. On
ARM, `pyrealsense2` frequently needs building from source, and if that build
is not already in place it is a multi-hour task with its own failure modes.
Discovering that during the sensor phase costs days; discovering it now costs
nothing. Fail fast on the thing with the longest lead time.

While in that file: `capture_d455_v2.py:146` enables only
`rs.stream.color`. Turning on depth is one line and gives independent
per-frame range on every future session — which would make the J2 axis check
permanent rather than a one-off.

---

## 8. Mixed-scale CSVs — decided 2026-10-03

Every preserved analysis CSV from the thirteen sessions is on the **old**
range scale; runs after the W1 fix are on the new one. Decision: leave the
old ones in place rather than re-processing. The error is uniform and no
conclusion in the project depends on absolute range, so they remain valid for
everything they were used for.

Put a one-line marker in each old output directory —
`SCALE.txt` containing `slope 44.41, ranges 0.56% long, pre-2026-10-03` — so
a future comparison does not read the shift as a finding. This is the same
failure mode as the earlier `frames/` vs `logs/` mix-up, where a batch of
session analyses turned out to be built from stale CSVs.
