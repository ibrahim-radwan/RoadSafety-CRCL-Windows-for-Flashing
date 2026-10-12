# Flash procedure: v2 images (all range variants)

**Do not start until the operator has approved flashing.** This rewrites only the application slot (QSPI `0xA0000`). The SBL at `0x0` is not touched, so a failed write is recoverable over the same UART.

*Revised 2026-10-10: flashing now goes through `flashing/boot/flash_variant.sh` on the Jetson, and the whole firmware tree is replaced from `rebuild_all_variants/firmware/`.*

## 1. Transfer the firmware tree (once per delivery)

1. Copy `rebuild_all_variants/` to the Jetson.
2. **Diff before replacing.** Compare `rebuild_all_variants/MANIFEST.txt` with the current tree's manifest (`jetson_firmware_current/MANIFEST.txt`). The only differences should be:
   - `firmware_map.json`;
   - the six corrected old `.cfg` files (r017m, r017m_calib, r050m, r100m, r142m, r168m);
   - 66 added files (11 new variants × 6).

   The complete expected list is in `REBUILD_SUMMARY.md`. Stop if anything else differs.
3. Copy `rebuild_all_variants/firmware/` over `~/dev/CascadedRadarRoadSafetyOnTwoWheelers/cascaded_radar_capture_pipeline/firmware/`.
4. Verify on the Jetson, where the flash-config paths resolve:
   ```
   cd ~/dev/CascadedRadarRoadSafetyOnTwoWheelers/cascaded_radar_capture_pipeline/firmware
   md5sum -c ../../path/to/rebuild_all_variants/MANIFEST.txt      # all OK
   python3 fill_firmware_map.py --root .                           # all columns ok, 20/20 rprc verified
   ```

## 2. Flash one variant

| Variant | `.appimage` md5 | Period | Window |
|---|---|---|---|
| r017m_v2 / _8fps | `6bfaa6a9…` / `29f8a801…` | 250 / 125 ms | 1.17–16.78 m |
| r017m_calib_v2 | `bb3c9c87…` | 1000 ms | 1.17–16.78 m |
| r050m_v2 / _8fps | `d580a23d…` / `1f5565e7…` | 250 / 125 ms | 1.75–50.00 m |
| r075m_v2 / _8fps | `b4ac5b97…` / `8f5eb30a…` | 250 / 125 ms | 2.62–74.99 m |
| r100m_v2 / _8fps | `e734b66d…` / `a9051ed3…` | 250 / 125 ms | 3.51–100.15 m |
| r142m_v2 / _8fps | `c50685f1…` / `a5f6f226…` | 250 / 125 ms | 9.97–142.42 m |
| r168m_v2 / _8fps | `edaed929…` / `af4677d4…` | 250 / 125 ms | 5.87–167.82 m |

`flash_variant.sh` checks the full md5 against `firmware_map.json`.

1. Power down the radar and the DCA1000.
2. Open a shell in the conda env that has pyserial. Plain `python` has none.
   ```
   conda activate rel_1_py_3_8
   cd ~/dev/CascadedRadarRoadSafetyOnTwoWheelers/flashing/boot
   ```
3. Run the wrapper with the variant name, exactly as in the table (lower case), and the serial port:
   ```
   ./flash_variant.sh r050m_v2 /dev/ttyACM0
   ```
   Before writing anything, the script:
   - checks the `.appimage` md5 against `firmware_map.json`;
   - checks that `flash_<v>.cfg` points at this variant's own image, at `0xA0000`, and does not write `0x0`;
   - prints the window, including the near floor.
4. When prompted, **put the board in UART boot mode** (boot jumper ON), power it up, then press Enter. `uart_uniflash.py` writes the image.
5. The script writes `~/.radar_flashed`: variant, image, md5, processing `.cfg`, slope, max range and floor. The capture pipeline copies this into `session.json["radar_firmware"]` (`radar_firmware.py`). **Never flash without the wrapper**, or sessions will be attributed to the wrong image.
6. **Move the boot jumper back to QSPI boot and power-cycle** the radar. Boot mode is sampled at reset, so moving the jumper alone does nothing. Then power up the DCA1000 and run `sudo sysctl -w net.core.rmem_max=33554432`.

## 3. Accept or reject (per variant)

1. Record a **30 s radar-only session**. Use `dca_capture_radar_sync.py` with `--packet-delay-us 25`, the default. **50 µs silently loses data at 8 fps.**
2. `python3 check_radar_frames.py <session>` (add `--period-s 0.125` for `_8fps`):

   | Check | Pass |
   |---|---|
   | Packets/s | ~8,640 (4 fps) / ~17,280 (8 fps) / ~2,160 (r017m_calib_v2) |
   | Loss, size, alignment | 0 lost, 3,145,728 B, every burst separate (idle gap) and aligned. No "no idle gap" warning. |
   | "identical in every frame" | **0.00%** |
   | Peak \|sample\| | well below 32,767; investigate above ~16,000. Tightest expected headroom: r050m_v2, ~17 dB. |
   | Range-time map | walking person tracked inside the window, including near the new floor |
3. **Power-cycle and repeat once.**

## If it fails

- **The wrapper aborts:** md5 mismatch, a flash config pointing at a sibling's image, or a write to `0x0`. Re-copy the tree and re-run `fill_firmware_map.py`. Do not edit the map by hand.
- **No packets after QSPI boot:** the image did not start. Reflash the previous variant with `flash_variant.sh` and report.
- **"identical" not 0.00%:** report the number and the variant. r075m_v2 proved the fix, and every v2 image carries the identical MEMINIT code.
- **Rate below 8 fps with no idle gap:** the DCA packet delay is too long (see `JETSON_DATA_FORMAT.md`).
- **~908 packets/s** (old Finding B): power-cycle and note it in the session log.

**Rollback:** `./flash_variant.sh <previous variant> <port>`. Old images are still in the tree but are marked `data_valid: NO`, so use a `_v2` image.
