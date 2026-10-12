# Archive: cascade Ethernet-streaming experiment (March 2026)

A source-only snapshot of the `ti\utils\test\cascade\` folder as it stood in the TI SDK on 2026-03-25. Its generated driver files (`mssgenerated/`) are on the `archive/history-before-2026-10-12` branch (`sdk_history/cascade/`). The build outputs were not kept.

It is an earlier branch of the cascade test application. Its `ENET_STREAM` build option sent each frame from the AM273x over Ethernet (`cascade_enet_stream.c`, `mss_linker_enet.cmd`, `udp_adc_receiver.py`), instead of over LVDS to the DCA1000. It also adds a UART "s" stop command. The two guides (`DCA1000_CAPTURE_GUIDE.md`, `ETHERNET_STREAMING_GUIDE.md`) describe how it was used.

**Status:** not built, not deployed, not maintained. The production firmware is `firmware/am273x_cascade/`. This copy lacks:

- the DSS L3 MEMINIT fix, so a QSPI-booted build streams ~50% stale words;
- the corrected chirp parameters;
- `cascade_config.h`. Its chirp parameters are hard-coded in `common.c`.

Kept so that the Ethernet-streaming approach and its DCA1000 notes are not lost.
