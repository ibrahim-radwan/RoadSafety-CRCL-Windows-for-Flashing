# config/: Windows capture configuration (frozen capture path)

These files belong to the original Windows capture pipeline (`capture/`, `live_capture.py`, `analysis_utils/`). That pipeline loaded firmware through CCS/JTAG and captured with the DCA1000 CLI. It is frozen: operational capture runs on the Jetson. The current firmware and its processing `.cfg` files are in `firmware/releases/`.

| File | Used by | Notes |
|---|---|---|
| `AM273X_Capture_fixed.json` | `capture/config.py:27` → DCA1000 CLI | DCA1000 settings: raw mode, 4-lane LVDS, 16-bit, Ethernet. **`packetDelay_us` = 25** (see below). |
| `AM273x_XDS110.ccxml` | `capture/config.py:28` | XDS110 debugger target for CCS loading |
| `reset_load_run_dualcore_reset.js` | `capture/config.py:29` | CCS DSS script: reset, load the `.xer5f`, run |
| `build_shortrange_inf/` | `capture/config.py:22-26`, `analysis_utils/*` defaults | The May–June 2026 shortrange image (`am273x_cascade_mss.xer5f`, loaded through CCS) and its `.cfg` |
| `build_longrange_inf/`, `build_verylongrange_inf/` | none by default | The matching long-range images and `.cfg` files from the same period |
| `cascade_shortrange.cfg` | `processing/main.py` default | A second copy of the shortrange `.cfg` (see `docs/RANGE_VARIANTS_BUILD_SPEC.md` W1 step 2) |

## Notes on these files

**DCA1000 packet delay: 25 µs (changed from 50 µs on 2026-10-12).**
- **The rule.** The delay is applied after every packet, and a frame is 2,160.5 packets. At 50 µs a frame takes **134.4 ms** on the wire. Any frame rate above 7.44 fps (any 8 fps image) makes the DCA1000 stream back to back and drop LVDS data internally. Sequence numbers and byte counts still look perfect, because the loss happens before the DCA counts bytes. At 25 µs a frame takes ~80 ms, which suits 4 fps and 8 fps.
- **Where it applies.** The same rule is used on the Jetson (`dca_capture_radar_sync.py --packet-delay-us 25`) and recorded in `firmware_map.json` `conventions.dca_wire_time`.
- **Other copies changed.** The five mmWave Studio 03.00 PostProc copies (`C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\AM273X_Capture*.json`, `capture\…`, `cascaded_radar\config\…`) were changed from 50 to 25 µs on the same day.

**The CCS-loaded images here do not have the DSS L3 fix.** That never mattered when they were loaded through CCS, because the CCS GEL script initialises DSS L3 on connect. Booted from QSPI, they would stream ~50% stale words.

**The `.cfg` files here use `adcbufCfg -1 0 1 0 1` (SampleSwap 1, i.e. Q-first).**
- **Windows tools are unaffected.** They force I-first (`--raw-iq-order i-first`), which is correct.
- **Elsewhere this decodes wrongly.** Any other reader that takes the I/Q order from these files mirrors the range spectrum.
- **They were left unchanged** to keep the frozen pipeline byte-identical to its validated state. The corrected `.cfg` files are in `firmware/releases/2026-10-10_v2/<variant>/`.
