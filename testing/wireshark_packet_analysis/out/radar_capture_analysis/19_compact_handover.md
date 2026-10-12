# Compact handover

## 1. Capture context
- File: radar_full_capture_2026-08-31.pcapng
- Size: 835131964 bytes; format: PCAPNG; duration ~67.178 s.
- Dominant traffic: a single high-rate UDP stream from 192.168.33.180:1024 to 192.168.33.30:4098 with 542292 packets and 817 MB captured bytes.
- Supporting evidence: [01_capture_metadata.txt](radar_capture_analysis/01_capture_metadata.txt), [02_protocol_hierarchy.txt](radar_capture_analysis/02_protocol_hierarchy.txt), [03_udp_conversations.txt](radar_capture_analysis/03_udp_conversations.txt).

## 2. Confirmed endpoint and port map
| Endpoint | Observed role | Evidence |
| --- | --- | --- |
| 192.168.33.180:1024 -> 192.168.33.30:4098 | Dominant UDP data stream | 542292 packets, near-constant 1474-byte UDP datagrams |
| 192.168.33.30:4096 <-> 192.168.33.180:1024 | Small bidirectional control/configuration traffic | 8-22 byte UDP payloads, alternating request/response |

## 3. Traffic-flow classification
- F01: likely raw data flow on 1024->4098; high packet count, steady packet size, continuous stream.
- F02: likely control/configuration on 4096/1024; low-volume bidirectional exchange.
- F03: unrelated/background traffic is minimal; no major additional UDP conversations beyond these pairings.

## 4. Packet size distribution
- Dominant UDP length: 1474 bytes (payload approx. 1466 bytes) in the high-rate stream.
- Short control packets: 8–22 bytes UDP length in the low-volume flow.
- Most common sizes align with a clean data stream plus a separate control stream, not a mixed application protocol.

## 5. Average and peak load
| Metric | Value |
| --- | --- |
| Whole capture UDP packet count | 542308 |
| Whole capture UDP payload bytes | ~793 MB |
| Avg payload rate | about 100 Mbit/s over ~67 s |
| Peak 10 ms payload rate | measured as the largest 10 ms payload aggregate in the interval CSV |
| Peak packet burst | dominated by the 1024->4098 flow |

## 6. Timing and pipeline phases
- Initial discovery/ARP: very early frames, small ARP activity and the first small UDP exchanges.
- Device/configuration phase: 0.0–4.4 s, short bidirectional packets on port 4096/1024.
- Delay before first large data packet: roughly 4.4 s after start of capture.
- Sustained raw UDP streaming: from first 1024->4098 datagram to the final streaming burst; near-constant cadence and packet size.
- Final short exchange: last low-volume packets after the main burst, consistent with stop/status traffic.

## 7. Control exchange patterns
- Repeated short back-and-forth messages on 4096/1024 with payload sizes that remain far below the main raw-data payload size.
- This is consistent with configuration or status traffic but not enough to assert specific command names without sender-side logs.

## 8. Raw-data header findings
- No fixed magic number or obvious 32/64-bit counter was found in the leading bytes of representative payloads.
- The first bytes appear varied and do not preserve a simple sequence relation to packet length.
- Conclusion: header hypothesis remains unconfirmed without a sender-side reference.

## 9. Packet loss/reordering findings
- No credible sequence/cumulative field was found; therefore loss/reordering cannot be determined reliably from UDP/IP fields alone.
- No strong evidence of fragmentation or ICMP errors was observed for the dominant stream.

## 10. Linux receiver implications
- The receive path should budget for a sustained high-rate UDP stream and a separate short control flow.
- Recommended: dedicated UDP socket, receive thread, queue, and buffered writes; allocate SO_RCVBUF for at least one measured burst with a safety margin.

## 11. Unknowns and next smallest validation experiments
- Validate whether the 4096/1024 short messages represent configuration or status commands.
- Confirm whether a sender-side counter exists in the first payload bytes of the 1024->4098 stream.
- Validate whether the first packet after control phase is the start of the actual radar burst.

## 12. Relevant artifact filenames
- [radar_capture_analysis/01_capture_metadata.txt](radar_capture_analysis/01_capture_metadata.txt)
- [radar_capture_analysis/02_protocol_hierarchy.txt](radar_capture_analysis/02_protocol_hierarchy.txt)
- [radar_capture_analysis/03_udp_conversations.txt](radar_capture_analysis/03_udp_conversations.txt)
- [radar_capture_analysis/04_udp_endpoints.txt](radar_capture_analysis/04_udp_endpoints.txt)
- [radar_capture_analysis/05_flow_classification.md](radar_capture_analysis/05_flow_classification.md)
- [radar_capture_analysis/06_udp_packet_index.csv](radar_capture_analysis/06_udp_packet_index.csv)
- [radar_capture_analysis/07_udp_length_distribution.csv](radar_capture_analysis/07_udp_length_distribution.csv)
- [radar_capture_analysis/08_load_10ms.csv](radar_capture_analysis/08_load_10ms.csv)
- [radar_capture_analysis/09_load_100ms.csv](radar_capture_analysis/09_load_100ms.csv)
- [radar_capture_analysis/10_load_1s.csv](radar_capture_analysis/10_load_1s.csv)
- [radar_capture_analysis/11_load_summary.md](radar_capture_analysis/11_load_summary.md)
- [radar_capture_analysis/12_timeline.md](radar_capture_analysis/12_timeline.md)
- [radar_capture_analysis/13_control_packets.csv](radar_capture_analysis/13_control_packets.csv)
- [radar_capture_analysis/14_control_exchange_analysis.md](radar_capture_analysis/14_control_exchange_analysis.md)
- [radar_capture_analysis/15_representative_data_packets.csv](radar_capture_analysis/15_representative_data_packets.csv)
- [radar_capture_analysis/16_data_header_hypotheses.md](radar_capture_analysis/16_data_header_hypotheses.md)
- [radar_capture_analysis/17_integrity_analysis.md](radar_capture_analysis/17_integrity_analysis.md)
- [radar_capture_analysis/18_linux_receiver_requirements.md](radar_capture_analysis/18_linux_receiver_requirements.md)
- [radar_capture_analysis/19_compact_handover.md](radar_capture_analysis/19_compact_handover.md)
- [radar_capture_analysis/20_evidence_ledger.csv](radar_capture_analysis/20_evidence_ledger.csv)
