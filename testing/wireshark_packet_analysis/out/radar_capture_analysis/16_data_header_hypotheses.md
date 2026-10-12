# Data-header hypotheses

The representative raw data packets show a large, steady UDP payload stream with a near-constant 1466-byte payload, but the first bytes do not support a fixed magic number or simple monotonic sequence field at a fixed offset. The following checks were run against the first payload bytes of representative packets.

| Candidate field | Byte offset | Width | Endianness | Example values | Consecutive delta | Matches payload size? | Notes | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 16-bit little-endian | 0 | 16 | little | 0x0000, 0x8eff, 0x3301, ... | No stable progression | No | Values vary irregularly and are not monotonic by packet | Low |
| 16-bit big-endian | 0 | 16 | big | 0x0000, 0xff8e, 0x0133, ... | No stable progression | No | Same irregularity; no fixed leading magic/stamp | Low |
| 32-bit little-endian | 0 | 32 | little | 0x00000000, 0x01338eff, ... | Not monotonic across packets | No | No evidence of a sequence/counter field | Low |
| 32-bit big-endian | 0 | 32 | big | 0x00000000, 0xff8e3301, ... | Not monotonic across packets | No | No repeated fixed header field | Low |
| 64-bit little-endian | 0 | 64 | little | Mixed high/low values | Not monotonic | No | No credible cumulative counter | Low |
| 64-bit big-endian | 0 | 64 | big | Mixed high/low values | Not monotonic | No | No credible cumulative counter | Low |

Candidate interpretation: the stream appears to be raw ADC or sample data without an obvious application-level packet sequence field in the first several bytes. The first payload bytes may contain a sample block descriptor or other structure, but the capture is not sufficient to assert this without a reference implementation or explicit documentation.

Required validation: compare with sender-side code or a captured packet trace from a known-good acquisition session; verify whether the first payload byte pattern is constant per frame block or per radar burst.
