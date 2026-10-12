# Firmware Packaging — Windows Build Station

*Rewritten 2026-10-12. The previous version described a manual, one-variant-at-a-time procedure with output in `config\build_*_inf\` and the source in the SDK's `cascade - Copy` folder. Both are obsolete: the source now lives in this repository, and one script builds and packages any set of variants. That version was never committed, so it is not in git history. Its commands (`elf2rprc.js`, `multicoreImageGen.js --devID 55 … @0`) and its overwrite hazard are carried into §3 and §4 below.*

**Audience:** an engineer producing a flash package without having done it before. For what the folders are and why, read `firmware/README.md` first.

---

## 1. What a flash package is

One directory per variant, plus shared files, laid out exactly like the Jetson's `cascaded_radar_capture_pipeline/firmware/`:

| File | Produced by | Role on the Jetson |
|---|---|---|
| `<v>/am273x_cascade_<v>.appimage` | `multicoreImageGen` | **written to QSPI at 0xA0000**: this is the firmware |
| `<v>/cascade_<v>.cfg` | generated from the registers | read by processing and replay to label axes and I/Q order |
| `<v>/flash_<v>.cfg` | generated | read by `uart_uniflash.py` through `flash_variant.sh`; writes only 0xA0000 |
| `_build_record/<v>/<v>.rprc` | `elf2rprc` | reproducible fingerprint, checked by `fill_firmware_map.py` |
| `_build_record/<v>/<v>.xer5f`, `am273x_cascade_mss.map` | compiler / linker | provenance only; never hashed |
| `firmware_map.json` | generated, verified by `fill_firmware_map.py` | ties image, md5s, `.cfg` and derived radar parameters together |

The `.cfg` is not flashed and does not affect capture, but an image flashed without its matching `.cfg` produces data nobody can interpret. That is why both travel in one tree and the map binds them.

## 2. One-time setup

1. **Toolchain** (already installed on this machine): see `firmware/README.md` §2. The paths are set in `firmware/am273x_cascade/build_one_inf.bat`.
2. **SDK junction**, so the makefile's `../../../common/mmwave_sdk.mak` resolves:
   ```powershell
   powershell -ExecutionPolicy Bypass -File firmware\am273x_cascade\tools\setup_sdk_junction.ps1
   ```
   This creates `C:\ti\…\ti\utils\test\cascade_radar` → `<repo>\firmware\am273x_cascade`.

## 3. Procedure for a new or changed variant

1. **Edit the parameters** in `firmware/am273x_cascade/am273x/cascade_config.h`:
   - **Change only what the variant needs.** Either add a base block, or add a `_V2` mapping that reuses a base block and overrides fields.
   - **Keep the forced identities true:** `max_range = range_res × 256` and `v_max / v_res = 32`.
   - **Read `docs/RANGE_EQUATION_LEDGER.md`** before touching a slope.
   - **Add the variant to the `makefile` `mssTestInf` target** as well, so the build-all path stays complete.

2. **Start from a copy of the current release**, so the new tree is a complete drop-in:
   ```powershell
   Copy-Item -Recurse firmware\releases\2026-10-10_v2 C:\temp\fw_new
   ```

3. **Build and package** straight into that tree:
   ```powershell
   cd firmware\am273x_cascade\tools
   .\build_v2_variants.ps1 -Out C:\temp\fw_new -Variants 'r060m_v2=CASCADE_CFG_R060M_V2','r060m_v2_8fps=CASCADE_CFG_R060M_V2_8FPS'
   ```
   Per variant, this:
   - compiles;
   - copies the `.xer5f` / `.map` into `am273x\build_<v>_inf\`;
   - runs `elf2rprc` on a **uniquely named** `.xer5f` inside `_build_record\<v>\`;
   - runs `multicoreImageGen --devID 55 … @0` into `<v>\am273x_cascade_<v>.appimage`.

   Then it prints both md5s.

4. **Generate the metadata** (map entries, `.cfg`, flash config): edit the `NEW` list in `tools\gen_v2_release_metadata.py` (name, base, define, period), then run:
   ```powershell
   python tools\gen_v2_release_metadata.py C:\temp\fw_new
   ```

5. **Verify. All of these must pass before anything leaves this machine:**
   1. **Determinism:**
      - rebuild one existing variant and confirm its `.rprc` / `.appimage` md5s are unchanged;
      - confirm the new variants' `.rprc` hashes are distinct from every other variant's.
   2. **Only the intended change:**
      ```powershell
      python tools\fdiff.py <base image .xer5f> C:\temp\fw_new\_build_record\<v>\<v>.xer5f
      ```
      The output must show only the immediates you meant to change (see `testing/firmware_investigation_2026-10/rebuild_all_variants/disassembly_diff_vs_base.txt` for what a clean result looks like).
   3. **Map and files:** `python C:\temp\fw_new\fill_firmware_map.py --root C:\temp\fw_new`. `derived`, `appimage`, `cfg` and `rprc` must be `ok` for every variant. `flash` reports `NOFILE` here because flash configs carry Jetson paths; it is re-checked on the Jetson.
   4. **Parsers:** the new `.cfg` parses in the Jetson's `radar_config.parse_cfg_file` and `capture.config.parse_cascade_cfg` with no mismatches and `iq_swap = False`.
   5. **Timing:** for an 8 fps image, chirping time (384 × (idle + ramp)) plus the DCA1000 transfer (~80 ms at 25 µs) must fit in 125 ms. The CBUFF needs 27.3 µs per chirp, so the chirp (idle + ramp) must be longer than that.

6. **Manifest and release:**
   ```bash
   cd /c/temp/fw_new && find . -type f | LC_ALL=C sort | xargs md5sum | sed 's/ \*/  /' > ../MANIFEST.txt
   ```
   Diff it against the previous release's manifest. The only differences should be the new variant files and `firmware_map.json`. Then copy the tree into `firmware/releases/<date>_<tag>/`, with its manifest beside it, and commit.

7. **Hand over** the release folder to the Jetson. It diffs the manifest, copies the tree over `cascaded_radar_capture_pipeline/firmware/`, re-runs `fill_firmware_map.py --root .` (where `flash` now resolves) and flashes with `flashing/boot/flash_variant.sh <variant> <port>`. Flashing is never done from Windows.

## 4. Hazards this procedure exists to prevent

| Hazard | How it bit, or nearly bit, this project | Prevention |
|---|---|---|
| A `-D` define that silently fails builds the wrong sweep | `build_all_configs.bat` produced 2 of 4 variants without an error | distinct `.rprc` per variant; `fdiff.py` against the base |
| Hashing the `.xer5f` | 3–4 different `.xer5f` per variant from identical source | hash only the `.rprc` and `.appimage` (`BUILD_DETERMINISM_FINDING.md`) |
| Shared intermediate names | every build emits `am273x_cascade_mss.*`; a second `elf2rprc` overwrote the first | `build_v2_variants.ps1` renames before converting |
| `.cfg` not matching the image | the old `.cfg` files said Q-first, 50 ms frames and compression on, all false | `.cfg` generated from the registers; `fill_firmware_map.py` compares every `profileCfg` field |
| Image booted from QSPI without DSS L3 init | ~50% stale words per chirp in every pre-v2 image | MEMINIT in `main_mss.c`; acceptance test `check_radar_frames.py` = 0.00% |
| Regenerating `mssgenerated/` by accident | it would change driver config away from the released images | never run `make syscfg` unless intended; the files are committed as built |
