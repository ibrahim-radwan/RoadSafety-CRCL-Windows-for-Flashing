# Control exchange analysis

The short UDP exchanges on the 4096/1024 pair are the strongest evidence for low-volume control/configuration traffic. They are distinguished by small packets, alternating directions, and regular request/response timing.

| Group | Request frame | Response frame(s) | Request payload | Response payload | RTT | Pattern | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Short request/response pair | 1 | 2 | 08 00 00 00 00 00 00 00 | 08 00 00 00 00 00 00 00 | ~0.468 s | Alternating 8-byte exchange on 4096/1024 | High |
| Repeated command bursts | 3, 5, 7, 9, 11, 13 | 4, 6, 8, 10, 12, 14 | 14-byte or 8-byte payloads | 8-byte payloads | ~0.063–0.56 s | Repeated short exchange pattern with small directional alternation | High |

Observed pattern: the higher-rate control traffic is bidirectional, small, and roughly periodic. The payloads are not long enough to be raw ADC data and do not show the 1466-byte raw-data pattern. The repeated request/response cadence is consistent with configuration, trigger, or status traffic; however, the capture does not provide a packet log sufficient to assign a definitive protocol label such as 'sensorStart' or 'sensorStop'.

Required validation: confirm with sender-side logs, protocol docs, or a repeated capture that isolates the 4096/1024 flow before assigning exact command names to the payload bytes.
