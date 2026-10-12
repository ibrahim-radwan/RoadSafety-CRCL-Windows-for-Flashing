# Frame-by-Frame Capture via DCA1000EVM (LVDS Path)

## Overview

The LVDS capture path streams raw ADC data from the AM273x through CBUFF
over LVDS lanes to the DCA1000EVM FPGA, which forwards the data as raw UDP
packets to the host PC.  The DCA1000 CLI tool receives these packets and
writes them to a `.bin` file.

```
AWR2243 → CSI-2 → AM273x CSIRX → CBUFF → LVDS → DCA1000 FPGA → Ethernet → PC
                                                   (writes to .bin)
```

## 1. Build the LVDS Firmware

The makefile now supports two targets:

| Target         | Command           | Description                |
|---------------|-------------------|----------------------------|
| `mssTest`     | `gmake mssTest`   | LVDS streaming (DCA1000)   |
| `mssTestEnet` | `gmake mssTestEnet` | Ethernet streaming (UDP) |

Build the LVDS target:

```powershell
gmake mssTest
```

This builds **without** `-DENET_STREAM`, so:
- The original CBUFF/EDMA ping-pong LVDS streaming path is active
- The `configureTransfer()` function handles EDMA channel switching
- The `Cascade_LVDSStreamInit()` and `Cascade_LVDSStreamSwConfig()` calls
  initialize the LVDS streaming subsystem
- The DCA1000 warm-up delay (`HSI_DCA_MIN_DELAY_MSEC`) is included

## 2. DCA1000 Hardware Setup

### Cable connections

```
AM273x EVM                    DCA1000EVM
    J8 (LVDS-A) ───────────── J1 (LVDS data input)
    J5 (5V power) ────────── J3 (power supply)

DCA1000EVM                    Host PC
    J4 (Ethernet) ────────── Ethernet port (dedicated NIC)
```

### DCA1000 DIP switches (S1)

| Switch | Position | Meaning          |
|--------|----------|------------------|
| 1      | OFF      | LVDS mode        |
| 2      | ON       | 14-bit ADC       |
| 3      | OFF      | No playback      |
| 4      | OFF      | ARM mode         |
| 5      | OFF      | Reserved         |

## 3. Host PC Network Setup

Configure a **dedicated** Ethernet NIC (not your main network):

| Setting     | Value            |
|------------|------------------|
| IP Address | `192.168.33.30`  |
| Subnet     | `255.255.255.0`  |
| Gateway    | (leave empty)    |

## 4. DCA1000 Configuration (`cf_cascade.json`)

A ready-to-use configuration file is provided as `cf_cascade.json`.
Copy it to the DCA1000 CLI tool directory:

```powershell
copy cf_cascade.json C:\ti\radar_toolbox_4_00_00_05\radar_toolbox_4_00_00_05\tools\Adc_Data_Capture_Tool_DCA1000_CLI\cf.json
```

### Key settings explained

```json
{
  "dataTransferMode": "LVDSCapture",
  "lvdsMode": 1,
  "dataFormatMode": 3,
  "captureConfig": {
    "filePrefix": "am273x_cascade",
    "captureStopMode": "infinite",
    "maxRecFileSize_MB": 1024
  }
}
```

| Field              | Value           | Why                                               |
|-------------------|-----------------|----------------------------------------------------|
| `lvdsMode`        | `1`             | 2-lane LVDS (matches AM273x CBUFF config)          |
| `dataFormatMode`  | `3`             | 16-bit + complex (I/Q interleaved)                 |
| `captureStopMode` | `"infinite"`    | Capture runs until you manually send stop_record   |
| `reorderEnable`   | `1`             | DCA1000 reorders bytes into correct sample order   |
| `packetDelay_us`  | `25`            | 25 µs between DCA1000 Ethernet packets to host     |

## 5. Capture Procedure

Open a terminal in the DCA1000 CLI tool directory:

```powershell
cd C:\ti\radar_toolbox_4_00_00_05\radar_toolbox_4_00_00_05\tools\Adc_Data_Capture_Tool_DCA1000_CLI
```

### Step-by-step

```powershell
# 1) Reset the DCA1000
DCA1000EVM_CLI_Control.exe fpga_reset cf.json

# 2) Configure the DCA1000
DCA1000EVM_CLI_Control.exe fpga cf.json

# 3) Arm the DCA1000 for recording
DCA1000EVM_CLI_Control.exe start_record cf.json

# 4) Now start radar frames (via UniFlash / CCS / UART trigger)
#    The firmware sends frames continuously.

# 5) When done, stop recording
DCA1000EVM_CLI_Control.exe stop_record cf.json
```

The captured data is saved to:
```
C:\ti\radar_captures\am273x_cascade_Raw_0.bin
```

## 6. Frame Data Layout

### Per chirp line (one CBUFF transfer)

Each CBUFF SW session transfer sends **both** cascade devices back-to-back:

```
[ Device 0: 4096 bytes ][ Device 1: 4096 bytes ] = 8192 bytes total
```

Where each device's data is:
```
256 samples × 4 RX × 4 bytes (complex int16 I+Q) = 4096 bytes
```

### Per frame

```
384 chirp lines × 8192 bytes = 3,145,728 bytes per frame
```

Where `384 chirp lines = 6 chirps (TDM) × 64 loops`.

### Memory layout within the .bin file

```
Offset 0:        Frame 0, Chirp-Line 0, Dev0 (4096 B)
Offset 4096:     Frame 0, Chirp-Line 0, Dev1 (4096 B)
Offset 8192:     Frame 0, Chirp-Line 1, Dev0 (4096 B)
Offset 12288:    Frame 0, Chirp-Line 1, Dev1 (4096 B)
...
Offset 3145728:  Frame 1, Chirp-Line 0, Dev0 (4096 B)
...
```

### Sample ordering within each 4096-byte line

Samples are complex int16 (I, Q) interleaved across RX channels:

```
RX0_S0_I, RX0_S0_Q, RX1_S0_I, RX1_S0_Q, RX2_S0_I, RX2_S0_Q, RX3_S0_I, RX3_S0_Q,
RX0_S1_I, RX0_S1_Q, RX1_S1_I, RX1_S1_Q, ...
```

## 7. Parsing Frames with Python

Use the provided `dca_frame_parser.py` to split a `.bin` capture into
individual per-device per-frame files:

```powershell
python dca_frame_parser.py C:\ti\radar_captures\am273x_cascade_Raw_0.bin --out ./frames --numpy
```

### Output

```
frames/
  frame_0000_dev0.bin     # 1,572,864 bytes (384 lines × 4096)
  frame_0000_dev0.npy     # NumPy array: (384, 4, 256, 2) int16
  frame_0000_dev1.bin
  frame_0000_dev1.npy
  frame_0001_dev0.bin
  ...
```

### NumPy array shape

When `--numpy` is used, each `.npy` file is shaped:

```python
(chirp_lines, num_rx, num_samples, 2)  →  (384, 4, 256, 2)
```

Where the last dimension is `[I, Q]`.

### Loading in Python

```python
import numpy as np

data = np.load('frames/frame_0000_dev0.npy')
print(data.shape)  # (384, 4, 256, 2)

# Convert to complex
iq = data[..., 0] + 1j * data[..., 1]
print(iq.shape)  # (384, 4, 256)

# Reshape to (chirps, loops, rx, samples) for processing
iq_4d = iq.reshape(6, 64, 4, 256)
print(iq_4d.shape)  # (6, 64, 4, 256)
```

## 8. Real-Time Frame-by-Frame Processing

The DCA1000 CLI writes a single continuous `.bin` file. For real-time
per-frame access, you have two options:

### Option A: Poll the file size

```python
import os, time

BIN_PATH = r'C:\ti\radar_captures\am273x_cascade_Raw_0.bin'
FRAME_SIZE = 3_145_728  # bytes per frame (both devices)
frames_read = 0

while True:
    file_size = os.path.getsize(BIN_PATH)
    available_frames = file_size // FRAME_SIZE

    while frames_read < available_frames:
        with open(BIN_PATH, 'rb') as f:
            f.seek(frames_read * FRAME_SIZE)
            frame_data = f.read(FRAME_SIZE)
        # Process frame_data here ...
        frames_read += 1

    time.sleep(0.05)  # poll at 20 Hz
```

### Option B: Custom DCA1000 UDP listener

Instead of using the DCA1000 CLI, write your own UDP listener on
port 4098 that captures the DCA1000's raw Ethernet packets and
reassembles frames in real time.  Each DCA1000 UDP packet contains
a 4-byte sequence number followed by raw ADC data:

```python
import socket, struct

FRAME_BYTES = 3_145_728
DCA_PORT = 4098
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('192.168.33.30', DCA_PORT))

buf = bytearray()
frame_num = 0

while True:
    pkt, _ = sock.recvfrom(1500)
    seq_num = struct.unpack('<I', pkt[:4])[0]
    buf.extend(pkt[10:])  # skip 10-byte DCA header

    while len(buf) >= FRAME_BYTES:
        frame = bytes(buf[:FRAME_BYTES])
        buf = buf[FRAME_BYTES:]
        # Process frame here ...
        frame_num += 1
```

> **Note**: The DCA1000 UDP data packet header is 10 bytes:
> `[4B sequence_number][6B reserved/byte_count]` before the ADC payload.
> Adjust the header offset based on your DCA1000 firmware version.

## 9. Switching Between LVDS and Ethernet

Both paths coexist in the same source code:

| What              | LVDS (DCA1000)      | Ethernet (UDP)      |
|-------------------|---------------------|---------------------|
| Build target      | `gmake mssTest`     | `gmake mssTestEnet` |
| Linker file       | `mss_linker.cmd`    | `mss_linker_enet.cmd` |
| Compile flag      | (none)              | `-DENET_STREAM`     |
| Data capture tool | DCA1000 CLI         | `udp_adc_receiver.py` |
| Host connection   | DCA1000 Ethernet    | AM273x CPSW Ethernet |

## 10. Troubleshooting

| Symptom                          | Cause / Fix                                      |
|----------------------------------|--------------------------------------------------|
| DCA1000 CLI says "FPGA not found" | Check J4 Ethernet cable and NIC IP = 192.168.33.30 |
| .bin file stays at 0 bytes       | LVDS cable not connected or wrong DIP switches   |
| .bin file has wrong size          | Check `lvdsMode` matches CBUFF lane config        |
| Data looks like noise             | Check `reorderEnable: 1` in cf.json              |
| Parser says "0 complete frames"   | File too small; capture more frames first         |
| Garbled samples                   | Check `dataFormatMode: 3` (16-bit complex)        |
