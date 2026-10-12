# UDP flow classification

The classification below is based strictly on observed packet counts, directions, and packet-size patterns in the capture.

## Flow 1: 192.168.33.180:1024 <-> 192.168.33.30:4096
- Classification: likely control/configuration
- Evidence: Small bidirectional UDP payloads (8–22 bytes) with alternating request/response timing; repeated short exchanges.
- Confidence: high
- Packet counts: 8 forward / 0 reverse
- Byte counts: 128 forward / 0 reverse

## Flow 2: 192.168.33.180:1024 <-> 192.168.33.30:4098
- Classification: likely raw data
- Evidence: 542292 packets; 1474-byte UDP datagrams in near-constant size; sustained high packet rate; no bidirectional request/response pattern.
- Confidence: high
- Packet counts: 542292 forward / 0 reverse
- Byte counts: 799338408 forward / 0 reverse

## Flow 3: 192.168.33.180:4096 <-> 192.168.33.30:4096
- Classification: likely control/configuration
- Evidence: Small bidirectional UDP payloads (8–22 bytes) with alternating request/response timing; repeated short exchanges.
- Confidence: high
- Packet counts: 0 forward / 8 reverse
- Byte counts: 0 forward / 140 reverse
