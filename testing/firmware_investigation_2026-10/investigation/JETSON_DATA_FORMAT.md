# Cascade radar raw data format: all variants (v2 family)

Applies to every image in `rebuild_all_variants/firmware/` (r017m … r168m, `_v2`, `_v2_8fps`, `r017m_calib_v2`). The byte layout is identical for all variants, old and new. Only the chirp parameters (range axis), the frame period and the near floor differ, so read those from `firmware_map.json` and the variant's `.cfg`.

Every item below comes from the firmware source. I/Q order and chirp order were confirmed by decoding stage3_01 against the LiDAR range (median error 7.5 cm). The fix was confirmed on hardware with r075m_v2 and r075m_v2_8fps: 0.00% stale words.

*Revised 2026-10-10: the DCA1000 packet delay and the burst duration were wrong in the first version. See "DCA1000 settings".*

## Frame

| | |
|---|---|
| Bytes per frame | **3,145,728** = 384 chirps × 2 devices × 4 RX × 256 samples × 4 B. The same for every variant. |
| Sample | complex, **int16 little-endian, I then Q** (`iqSwapSel = 0`). No header, no padding, no compression. |
| Frame period | `_v2`: **250 ms (4 fps)**; `_v2_8fps`: **125 ms (8 fps)**; `r017m_calib_v2`: 1000 ms. Frames are infinite and start at power-on. |
| Chirping per frame | 384 × (idle + ramp): 13.44 ms (r050m/r075m/r100m/r168m), 23.42 ms (r142m), 24.96 ms (r017m), 62.98 ms (r017m_calib) |

## Exact byte layout

```
frame  = chirp[384]                 chirp  = loop*6 + tx      (loop 0..63, tx 0..5)
chirp  = dev[2]  (8192 B)           dev 0 = master AWR2243, dev 1 = slave
dev    = rx[4]   (4096 B)           channels are NOT interleaved: each RX is contiguous
rx     = sample[256] (1024 B)
sample = int16 I, int16 Q

numpy:  x = np.fromfile(f, '<i2').reshape(64, 6, 2, 4, 256, 2)   # [loop, tx, dev, rx, sample, IQ]
        iq = x[..., 0] + 1j * x[..., 1]
```

Byte offset of the I word: `((((loop*6 + tx)*2 + dev)*4 + rx)*256 + n)*4`. Q follows at +2.

**I/Q:** I first. Every `.cfg` in the tree, old variants included, now has `adcbufCfg -1 0 0 1 1` (SampleSwap 0). The pre-2026-10-10 files had SampleSwap 1, which mirrors the range spectrum in `radar_config.py`.

## Virtual channels (TX/RX → array position)

| tx (chirp in loop) | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| Transmitter | dev0 TX0 | dev0 TX1 | dev0 TX2 | dev1 TX0 | dev1 TX1 | dev1 TX2 |
| Azimuth offset (λ/2) | 0 | 4 | 7 | 11 | 15 | 2, **elevation row** (+0.8 λ) |

RX index `r8 = dev*4 + rx` (0..7) has azimuth offsets `[0, 1, 2, 3, 19, 20, 21, 22]` λ/2. Virtual channel `v = tx*8 + r8`; its calibration value is complex pair `v` of `antennaCalibParams1..3`, as (Re, Im).

> **Not yet verified:**
> - **Physical positions.** The TX/RX timing order comes from the firmware (`common.c:525-547`). The physical positions come from `radar_config.py` and are a board property. Check them with a corner reflector.
> - **Calibration values.** The `antennaCalibParams` were inherited with unrecorded provenance; the 76 GHz set came from an HPF 2/2 profile. Repeat the calibration with HPF 0/0 images: `r017m_calib_v2` for 77 GHz, any 76 GHz v2 image for the others.

## Rates

A DCA1000 packet is a 4 B sequence number + 6 B byte count + 1456 B payload. A frame is 2,160.53 packets, so frame boundaries fall mid-packet on alternate frames.

| | 4 fps (`_v2`) | 8 fps (`_v2_8fps`) | 1 fps (`r017m_calib_v2`) |
|---|---|---|---|
| Packets/s | **8,642** (8,640–8,670 counted per 1 s window) | **17,284** | 2,161 |
| ADC payload | 12.58 MB/s | 25.17 MB/s | 3.15 MB/s |
| On the wire (1536 B per packet incl. UDP/IP/Ethernet) | ~13.3 MB/s, 106 Mbit/s | ~26.5 MB/s, 212 Mbit/s | ~3.3 MB/s |
| Burst per frame at **25 µs** delay | **~80 ms**, idle gap ~170 ms | **~80 ms**, idle gap **~45 ms** | ~80 ms |
| Burst per frame at 50 µs delay | 134 ms, gap ~116 ms | **134 ms > 125 ms: back to back, silent internal loss** | 134 ms |

These rates are the same for every variant at a given frame rate, because the frame size is the same.

## DCA1000 settings

- **`CONFIG_FPGA = 01 01 01 02 03 1E`: unchanged.** Raw mode, 4-lane LVDS, LVDS capture, Ethernet streaming, 16-bit, 30 s timer. This matches the AM273x CBUFF output: 4 lanes, 16-bit, DDR, no header (`cascade_lvds_stream.c:187-194`).
- **`CONFIG_PACKET_DATA` = 1470 B / delay 3125 (25 µs): required for 8 fps.**
  - The delay field is in **8 ns FPGA ticks**: 6250 = 50 µs and 3125 = 25 µs.
  - Each packet costs the delay + ~12.2 µs to send, so a frame takes ~80 ms at 25 µs and **134.4 ms at 50 µs**. 50 µs caps the stream at **7.44 fps**.
  - At 8 fps with 50 µs, the DCA streams back to back and **drops LVDS data internally**. Sequence numbers and byte counts still look perfect, because the loss happens before the DCA counts bytes. The only symptom is no idle gap between bursts, and a received rate of 7.43 fps instead of 8.00.
  - `dca_capture_radar_sync.py` now defaults to `--packet-delay-us 25` and warns when there is no gap.
- **Rule** (also in `firmware_map.json` `conventions.dca_wire_time`): the frame time on the wire at the configured delay must be shorter than `frame_periodicity_ms`, with margin. At 25 µs every image passes, with ~45 ms spare at 8 fps.
- **Windows capture (frozen path).** The project's `cascaded_radar_win_dev/config/AM273X_Capture_fixed.json` and the mmWave Studio 03.00 PostProc `AM273X_Capture*.json` files use **`packetDelay_us` 50**. They are fine at 4 fps and silently lossy at 8 fps; set them to 25 before any 8 fps capture on Windows. The TI samples (`cf_cascade.json`, mmWave Studio 03.01 `cf.json`) use 25.
- **Receiver:** `FRAME_BYTES` is unchanged, and so are the frame-boundary and alignment logic.

## `.cfg` files

Use `firmware/<variant>/cascade_<variant>.cfg`. Every one parses in `radar_config.parse_cfg_file` and `capture.config.parse_cascade_cfg` with no mismatches. Each contains:

- `profileCfg` with the variant's chirp and HPF fields (0 0 for v2);
- `frameCfg 0 5 64 0 <period> 1 0`;
- `compressionCfg -1 0 …`;
- `adcbufCfg -1 0 0 1 1`;
- a header giving the image md5, period, window, HPF, chirping time and DCA time.

Cosmetic issue: `capture/config.py:276` labels `adcbufCfg[3] = 1` as "interleaved". In TI's convention 1 means *non*-interleaved, which is what the firmware sends; the flag is display-only.

## Acceptance check (per variant, after flashing)

`python3 check_radar_frames.py <session>` (Jetson copy of `check_radar_session.py`; `--period-s 0.125` for 8 fps).

| Check | Pass |
|---|---|
| Packets/s | ~8,640 at 4 fps / ~17,280 at 8 fps, from the first full second |
| Loss, frame size, alignment | 0 lost; 3,145,728 B; every burst separate (idle gap present) and aligned |
| "identical in every frame" | **0.00%** (old images: ~50%) |
| Peak \|sample\| | well below 32,767; investigate above ~16,000 |
| Range-time map | walking person tracked inside the variant's window, including near the new floor |
