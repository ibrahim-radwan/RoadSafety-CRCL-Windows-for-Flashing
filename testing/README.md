# testing/: validation history

| Folder | Period | What it holds |
|---|---|---|
| `firmware_investigation_2026-10/` | Oct 2026 | **Start here for the current firmware.** The stale-data defect (missing DSS L3 MEMINIT), its proof from recorded frames, the fix and its hardware confirmation, the rebuild of every range variant, the Jetson data-format spec and flash procedure. See its `README.md`. |
| `live_capture_validation/` | May–Jun 2026 | Windows-era capture validation, scenarios 01–06 (indoor empty / reflector / moving subject, outdoor single and multiple subjects, data collection), plus `audit_and_improvement_plan/` (pipeline audits and the body-shape implementation plan). Logs, summaries and CSV results are in git. The radar frames and videos are not (`DATA_INDEX.md` §1). |
| `wireshark_packet_analysis/` | Aug 2026 | Analysis of a full DCA1000 Ethernet capture: the protocol work that made pure-Python capture on the Jetson possible. The `.pcapng` and the derived per-packet index are not in git (`DATA_INDEX.md` §1). |

These sessions were recorded with CCS-loaded firmware, so they are not affected by the stale-data defect. The defect only appears when a pre-v2 image boots from QSPI. Their range values carry the 0.56% slope-label error documented in `docs/RANGE_EQUATION_LEDGER.md` §2.
