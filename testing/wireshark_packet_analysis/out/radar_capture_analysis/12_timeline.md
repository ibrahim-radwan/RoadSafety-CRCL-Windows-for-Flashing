# Timing-phase analysis

This timing view is inferred strictly from packet timestamps, direction, packet sizes, and the observed port pairings in the capture.

## initial discovery and control exchange
- Start: 2026-08-31T08:41:42.052579Z
- End: 2026-08-31T08:42:49.230762Z
- Duration: 67.178183 s
- Frame range: 1 to 542311
- Relevant flow: 192.168.33.30:4096 <-> 192.168.33.180:1024
- Evidence: Short bidirectional UDP packets with payloads at 8-22 bytes and a repeated request/response cadence.
- Confidence: high

## sustained raw data stream
- Start: 2026-08-31T08:41:46.491516Z
- End: 2026-08-31T08:42:49.125433Z
- Duration: 62.633917 s
- Frame range: 15 to 542309
- Relevant flow: 192.168.33.180:1024 -> 192.168.33.30:4098
- Evidence: Steady high-rate UDP traffic with a dominant 1474-byte packet size and a stable period across the main burst.
- Confidence: high

## startup and early handshake
- Start: 2026-08-31T08:41:42.052579Z
- End: 2026-08-31T08:41:46.491516Z
- Duration: 4.438937 s
- Frame range: 1 to 15
- Relevant flow: control and initial discovery
- Evidence: Early frames include ARP, startup activity, and initial low-volume exchanges before the large stream begins.
- Confidence: medium

## final short status or stop exchange
- Start: 2026-08-31T08:42:49.230693Z
- End: 2026-08-31T08:42:49.230762Z
- Duration: 0.000069 s
- Frame range: 542310 to 542311
- Relevant flow: 192.168.33.30:4096 <-> 192.168.33.180:1024
- Evidence: A short, low-volume bidirectional exchange appears at the end of the capture after the main streaming burst.
- Confidence: medium
