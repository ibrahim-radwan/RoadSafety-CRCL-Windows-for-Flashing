# Linux receiver requirements

This estimate is based only on the measured UDP packet stream in the capture and does not assume any undocumented protocol semantics.

- Average UDP payload rate: 90.287799 Mbit/s (using all UDP application payload bytes over capture duration)
- Peak 10 ms payload rate: 213.627625 Mbit/s (measured by the maximum 10 ms payload aggregate)
- Peak 100 ms payload rate: 179.849854 Mbit/s (measured by the maximum 100 ms payload aggregate)
- Peak packet rate: 8644 packets/s in the highest 1 s bucket, measured from the dominant flow
- Dominant payload size: 1474 bytes UDP length (approximately 1466 bytes application payload)
- Maximum observed burst duration: approximately 67.178 s over the sustained stream; observed regular intervals and no long idle period in the main data flow
- Largest normal inter-packet gap: 1.540142 s, from packet-timing data

## Socket receive-buffer recommendation
- Evidence-based minimum: 560012 bytes, based on the maximum payload observed in a 10 ms burst with no cushion.
- Conservative engineering recommendation: 2240048 bytes, using a 4x safety factor for jitter and OS scheduling variability.
- Assumptions: single active receive thread, no additional application buffering ahead of the socket, and a requirement to absorb at least one short burst without dropping packets.

## Likely receiver implications
- SO_RCVBUF: allocate a buffer sized for at least one peak 10 ms burst, with a conservative margin above the minimum. The measured burst profile supports a socket buffer in the tens of megabytes range if the transfer pattern remains steady.
- receive batching: beneficial for the dominant 1474-byte datagrams; batching reduces per-packet overhead and matches the sustained UDP stream.
- dedicated receive thread: justified for a continuous high-rate stream, because the capture shows compact, steady packet bursts that should not share a UI or control path.
- producer/consumer queue: recommended to decouple socket receive from downstream processing and file writes.
- buffered file writes: recommended to absorb bursty episodes and avoid small, fragmented disk writes.
- packet sequence validation: recommended once a sequence or cumulative-byte field is available from sender logs or application data; without it, loss detection from UDP/IP fields alone is not reliable.
- graceful stop and trailing-packet drain: necessary because the capture shows a final short control exchange after the main data burst; receive logic should drain the socket at shutdown.
- real-time scheduling: not justified by the measured data alone unless the downstream processing cannot keep up with the measured peak payload rate.

Minimum recommendation: a dedicated UDP socket, a queue, and a receive-thread + buffered write path sized for bursty arrivals and a conservative buffer margin.
