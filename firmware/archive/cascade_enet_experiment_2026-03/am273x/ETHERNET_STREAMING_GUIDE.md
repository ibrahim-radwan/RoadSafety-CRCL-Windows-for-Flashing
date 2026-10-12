# AM273x Cascade Radar — Ethernet (UDP) Streaming Guide

## 1. Overview

This document describes the modifications made to the AM273x cascade radar
application to replace LVDS streaming (via CBUFF → DCA1000EVM) with Ethernet
streaming (via CPSW → lwIP → UDP).

The AM273x SoC includes an integrated CPSW (Common Platform Switch) Ethernet
MAC with RGMII interface.  The MCU+ SDK ships with an lwIP TCP/IP stack and
ENET CPSW driver that are already proven on the AM273x EVM.

### Previous data path (LVDS)

```
AWR2243 ──CSI-2──▶ AM273x CSIRX ──EDMA──▶ CBUFF ──LVDS──▶ DCA1000EVM ──USB──▶ Host PC
```

### New data path (Ethernet)

```
AWR2243 ──CSI-2──▶ AM273x CSIRX ──memcpy──▶ Frame buffer ──UDP──▶ Ethernet ──▶ Host PC
```

---

## 2. Radar Configuration Recap

| Parameter              | Value                        |
|------------------------|------------------------------|
| Devices                | 2 × AWR2243 (cascade)        |
| RX channels per device | 4                            |
| TX antennas per device | 3 (TDM MIMO)                 |
| Total virtual antennas | 48 (2 × 4 RX × 6 TX)        |
| ADC samples per chirp  | 256                          |
| Chirps per frame       | 6 (TDM: 3 TX × 2 devices)   |
| Loops per frame        | 64                           |
| Total chirp lines/frame| 384 (6 × 64)                |
| Bytes per chirp line   | 4096 (256 × 4 bytes × 4 RX) |
| Frame data per device  | 1,572,864 bytes (~1.5 MB)    |
| Frame data total       | 3,145,728 bytes (~3.0 MB)    |
| Frame period           | 250 ms                       |
| Data rate              | ~12 MB/s (96 Mbps)           |

---

## 3. Files Changed

### 3.1 New files

| File                     | Description                                      |
|--------------------------|--------------------------------------------------|
| `cascade_enet_stream.h`  | Header: UDP packet structure, public API          |
| `cascade_enet_stream.c`  | CPSW + lwIP initialisation, static IP, UDP sender |
| `udp_adc_receiver.py`    | Host-side Python script to capture frames         |

### 3.2 Modified files

| File               | Summary of changes                                            |
|--------------------|---------------------------------------------------------------|
| `test.syscfg`      | Added `enet_cpsw` module, RGMII/MDIO pinmux, MPU region #5   |
| `cascade_csirx.h`  | Added frame-buffer macros, included `cascade_enet_stream.h`   |
| `cascade_csirx.c`  | EOL callback → memcpy to frame buffer; EOF callback → post semaphore |
| `main_mss.c`       | Removed LVDS init/config; added frame buffers, Enet task      |
| `mss_linker.cmd`   | Enet memory layout (CPPI_DESC, lwIP pools, enet DMA sections) |
| `mssTest.mak`      | Added enet/lwIP libs, include paths, new source files         |

---

## 4. Detailed Change Descriptions

### 4.1 SysConfig (`test.syscfg`)

**Product version** updated from `08.02.00` to `08.05.00` to match the
installed MCU+ SDK that includes ENET CPSW support.

**Ethernet CPSW module** added:

```javascript
const enet_cpsw  = scripting.addModule("/networking/enet_cpsw/enet_cpsw", {}, false);
const enet_cpsw1 = enet_cpsw.addInstance();

enet_cpsw1.$name                           = "CONFIG_ENET_CPSW0";
enet_cpsw1.LargePoolPktCount               = 32;
enet_cpsw1.PktInfoOnlyEnable               = true;
enet_cpsw1.AppLinkUpPortMask               = "ALL_PORTS";
enet_cpsw1.pinmux[0].phyToMacInterfaceMode = "MSS_RGMII";
enet_cpsw1.netifInstance.create(1);
enet_cpsw1.netifInstance[0].$name           = "NETIF_INST_ID0";
```

**MPU region 5** added for CPPI descriptor memory (non-cached):

```javascript
mpu_armv76.baseAddr   = 0x102EC000;
mpu_armv76.size       = 14;           // 16 KB
mpu_armv76.attributes = "NonCached";
```

**RGMII / MDIO pinmux** added with explicit ball assignments matching the
AM273x EVM schematic.

### 4.2 Frame Accumulation (`cascade_csirx.h`, `cascade_csirx.c`)

New macros in the header:

```c
#define BOARD_DIAG_TEST_NUM_BYTES_PER_CHIRP_LINE \
    (TEST_NUM_ADC_SAMPLES * TEST_BYTES_PER_ADC_SAMPLE * TEST_NUM_RX)

#define TEST_CHIRP_LINES_PER_FRAME  (TEST_NUM_CHIRPS * TEST_NUM_LOOPS)

#define FRAME_ACCUM_BUF_SIZE_PER_DEV \
    ((uint32_t)TEST_CHIRP_LINES_PER_FRAME * BOARD_DIAG_TEST_NUM_BYTES_PER_CHIRP_LINE)
```

**EOL callback** (`MmwCascade_combinedEOLcallback`):

Previously triggered CBUFF to stream the chirp line over LVDS.
Now copies the chirp line from the CSIRX ping/pong buffer into a large
frame accumulation buffer, tracking the ping/pong alternation:

```c
if (pingPongFlag)
{
    memcpy(&gFrameAccumDev0[offset], CSIA_PingBuf, lineBytes);
    memcpy(&gFrameAccumDev1[offset], CSIB_PingBuf, lineBytes);
}
else
{
    memcpy(&gFrameAccumDev0[offset], CSIA_PongBuf, lineBytes);
    memcpy(&gFrameAccumDev1[offset], CSIB_PongBuf, lineBytes);
}
```

Each `memcpy` is 4096 bytes — small enough to complete within a chirp
interval (~46 µs) on the R5F core.

**EOF callback** (`MmwCascade_csirxCombinedEOFcallback`):

When device 0 signals end-of-frame, the accumulated chirp line index is
reset and a binary semaphore is posted to wake the Ethernet streaming task:

```c
gFrameAccumLineIdx = 0U;
SemaphoreP_post(&gFrameReadySem);
```

### 4.3 Ethernet Streaming (`cascade_enet_stream.c`)

**Initialisation** (`CascadeEnet_init`):

1. Opens the CPSW driver via `EnetApp_driverOpen`.
2. Starts the lwIP TCP/IP thread via `tcpip_init`.
3. Creates a netif with a **static IP** (default `192.168.1.100/24`,
   gateway `192.168.1.1`).
4. Waits for the Ethernet link to come up.
5. Creates a `NETCONN_UDP` socket connected to the broadcast address
   `192.168.1.255` on port `5001`.

**Frame sending** (`CascadeEnet_sendFrame`):

Iterates over all chirp lines in the frame.  For each line, allocates an
lwIP `netbuf`, copies a 20-byte header + 4096-byte payload into it, and
calls `netconn_send`.  The IP layer handles fragmentation into Ethernet
MTU-sized frames.

### 4.4 Main Application (`main_mss.c`)

**Removed:**
- `Cascade_LVDSStreamInit()` call
- `Cascade_LVDSStreamSwConfig()` call
- `configureTransfer()` function (CBUFF EDMA ping/pong switch)
- `HSI_DCA_MIN_DELAY_MSEC` delay (DCA1000 PLL lock delay)
- EDMA handle population for CBUFF (`gMmwCascadeMCB.lvdsStreamcfg.edmaHandle`)

**Added:**
- Frame accumulation buffers (placed in `.l3ram` → DSS_L3):
  ```c
  uint8_t gFrameAccumDev0[FRAME_ACCUM_BUF_SIZE_PER_DEV]   // ~1.5 MB
  uint8_t gFrameAccumDev1[FRAME_ACCUM_BUF_SIZE_PER_DEV]   // ~1.5 MB
  ```
- `gFrameReadySem` binary semaphore
- `MmwCascade_EnetStreamTask` — waits on `gFrameReadySem`, then calls
  `CascadeEnet_sendFrame` for device 0 and device 1

### 4.5 Linker Command (`mss_linker.cmd`)

Key changes from the original linker:

| Aspect              | Original                 | New (Ethernet)              |
|----------------------|--------------------------|-----------------------------|
| `#include`           | (none)                   | `"ti_enet_config.h"`        |
| Stack size           | 0x2000                   | 8192                        |
| Heap size            | 0x1000                   | 34000 (lwIP needs more)     |
| MSS_L2 length        | 0xC8000 (800 KB)         | 0xCC000 (816 KB)            |
| CPPI_DESC region      | (none)                   | 0x102EC000, 16 KB           |
| lwIP pool sections   | (none)                   | `.bss:.common:memp_*` → DSS_L3 |
| `.enet_dma_mem`      | (none)                   | DMA packet pool → DSS_L3   |
| DSS_L3 usage         | ping/pong + general      | + frame buffers + lwIP + ENET DMA |

### 4.6 Makefile (`mssTest.mak`)

**New libraries linked:**

```makefile
-lenet-cpsw.am273x.r5f.ti-arm-clang.$(LIB_TYPE).lib
-llwip-contrib-freertos.am273x.r5f.ti-arm-clang.$(LIB_TYPE).lib
-llwipif-cpsw-freertos.am273x.r5f.ti-arm-clang.$(LIB_TYPE).lib
-llwip-freertos.am273x.r5f.ti-arm-clang.$(LIB_TYPE).lib
```

**New library search paths:**

```makefile
-Wl,-i$(MCU_PLUS_INSTALL_PATH)/source/networking/enet/lib
-Wl,-i$(MCU_PLUS_INSTALL_PATH)/source/networking/lwip/lib
```

**New include paths:** 13 directories under the MCU+ SDK `networking/`
tree for ENET, lwIP stack, lwIP port, lwIP contrib, and lwIP AM273x
configuration.

**New source files:**
- `cascade_enet_stream.c` (application source)
- SysConfig-generated: `ti_enet_config.c`, `ti_enet_open_close.c`,
  `ti_enet_soc.c`, `ti_enet_lwipif.c`

**New compiler define:** `-DENET_STREAM`

---

## 5. UDP Packet Format

Each chirp line is transmitted as a single UDP datagram.

```
Offset  Size  Field             Description
------  ----  ----------------  ------------------------------------
0       4     magic             0xADC12345 — packet identifier
4       4     frameNum          Monotonically increasing frame counter
8       2     deviceIdx         0 = master AWR2243, 1 = slave AWR2243
10      2     chirpLineIdx      0 .. 383 (index within the frame)
12      2     numSamples        256 (ADC samples per chirp)
14      2     numRx             4 (receive channels)
16      2     bytesPerSample    4 (complex: 2 × int16)
18      2     totalChirpLines   384 (total lines in this frame)
20      4096  payload           Raw ADC data (I/Q interleaved, int16)
------  ----
Total:  4116 bytes per UDP datagram
```

Per frame:  384 lines × 2 devices = 768 UDP datagrams ≈ 3.08 MB.

Each 4116-byte UDP datagram is fragmented into 3 Ethernet frames at the
IP layer (MTU = 1500).

---

## 6. Memory Layout

```
Address         Size      Contents
-----------     --------  -------------------------------------------
0x00000000      64 B      R5F vector table
0x10200000      128 KB    SBL reserved L2 (BSS overflow, stack, heap)
0x10220000      816 KB    MSS_L2 (code, rodata, data, BSS, stacks)
0x102EC000      16 KB     CPPI_DESC (non-cached, MPU region 5)
0x82000000      128 KB    HWA_RAM
0x88000000      3.5 MB    DSS_L3:
                            ├── gFrameAccumDev0    ~1.5 MB
                            ├── gFrameAccumDev1    ~1.5 MB
                            ├── CSIA Ping/Pong     8 KB
                            ├── CSIB Ping/Pong     8 KB
                            ├── lwIP memory pools  ~120 KB
                            ├── ENET DMA packets   ~50 KB
                            └── MCPI log, misc     ~50 KB
0xC5000000      8 KB      IPC shared memory
```

---

## 7. Build Instructions

### 7.1 Prerequisites

- TI ARM Clang compiler (`tiarmclang`)
- SysConfig tool (version ≥ 1.14)
- MCU+ SDK AM273x 08.05.00 (or matching version)
- mmWave MCU+ SDK 04.04.00.01
- GNU Make (`gmake`)

### 7.2 Environment variables

Set these before building (adjust paths to your installation):

```bat
set MMWAVE_SDK_INSTALL_PATH=c:\ti\mmwave_mcuplus_sdk_04_04_00_01\mmwave_mcuplus_sdk_04_04_00_01
set MMWAVE_SDK_DEVICE=am273x
set MCU_PLUS_INSTALL_PATH=c:\ti\mmwave_mcuplus_sdk_04_04_00_01\mcu_plus_sdk_am273x_08_05_00_24
set CCS_INSTALL_PATH=c:\ti\ccs
set R5F_CLANG_INSTALL_PATH=c:\ti\ti-cgt-armllvm_4.0.4.LTS
set SYSCONFIG_INSTALL_PATH=c:\ti\sysconfig_1.14.0
```

### 7.3 Regenerate SysConfig outputs

```bat
cd %MMWAVE_SDK_INSTALL_PATH%
gmake -s -C ti/utils/test/cascade syscfg
```

This regenerates `mssgenerated/` and now produces additional files:
- `ti_enet_config.c` / `ti_enet_config.h`
- `ti_enet_open_close.c` / `ti_enet_open_close.h`
- `ti_enet_soc.c` / `ti_enet_soc.h`
- `ti_enet_lwipif.c` / `ti_enet_lwipif.h`

### 7.4 Build

```bat
gmake -s -C ti/utils/test/cascade mssTest
```

Output: `am273x/am273x_cascade_mss.xer5f`

### 7.5 Deploy

Flash or load the `.xer5f` binary via CCS / UniFlash onto the AM273x EVM.

---

## 8. Host PC Setup

### 8.1 Network configuration

| Setting       | EVM (AM273x)    | Host PC           |
|---------------|-----------------|-------------------|
| IP address    | 192.168.1.100   | 192.168.1.1       |
| Subnet mask   | 255.255.255.0   | 255.255.255.0     |
| UDP port      | 5001 (source)   | 5001 (listen)     |

Connect the EVM and PC with a standard Ethernet cable (direct or via
switch).  No DHCP server is needed — the EVM uses a static IP.

### 8.2 Running the receiver

```bash
python udp_adc_receiver.py --port 5001 --out ./captures
```

Options:
- `--max-frames N` — stop after N frames (0 = unlimited)
- `--numpy` — also save `.npy` files (requires `numpy`)

Output files per frame:
```
captures/
  frame_0000_dev0.bin    # Device 0 raw ADC (1,572,864 bytes)
  frame_0000_dev1.bin    # Device 1 raw ADC (1,572,864 bytes)
  frame_0001_dev0.bin
  frame_0001_dev1.bin
  ...
```

### 8.3 Data format

Each `.bin` file contains the concatenation of all chirp lines for one
device, in transmission order:

```
[chirp 0, loop 0] [chirp 1, loop 0] ... [chirp 5, loop 0]
[chirp 0, loop 1] [chirp 1, loop 1] ... [chirp 5, loop 1]
...
[chirp 0, loop 63] [chirp 1, loop 63] ... [chirp 5, loop 63]
```

Each chirp line is 4096 bytes:
- 256 ADC samples × 4 RX channels
- Each sample is 4 bytes: int16 I, int16 Q (complex)

To load in Python / NumPy:

```python
import numpy as np

data = np.fromfile('frame_0000_dev0.bin', dtype=np.int16)
# Reshape: (384 chirp lines, 4 RX, 256 samples, 2 for I/Q)
data = data.reshape(384, 4, 256, 2)
complex_data = data[..., 0] + 1j * data[..., 1]
# complex_data shape: (384, 4, 256)
```

---

## 9. Bandwidth Budget

| Metric                        | Value              |
|-------------------------------|---------------------|
| Frame size (both devices)     | 3,145,728 bytes     |
| Frame period                  | 250 ms              |
| Required throughput           | 12.6 MB/s (101 Mbps)|
| Ethernet link speed (RGMII)   | 1 Gbps              |
| Practical UDP throughput      | ~80 MB/s            |
| Utilisation                   | ~16%                |
| UDP packets per frame         | 768                 |
| Ethernet frames per frame     | ~2304 (with IP frag)|
| Estimated send time           | ~30–50 ms           |
| Available margin              | ~200 ms per frame   |

The Gigabit Ethernet link provides ample headroom.

---

## 10. Changing the IP Address

Edit `cascade_enet_stream.c` and modify these defines:

```c
#define ENET_LOCAL_IP0   192
#define ENET_LOCAL_IP1   168
#define ENET_LOCAL_IP2   1
#define ENET_LOCAL_IP3   100

#define ENET_DEST_IP0    192
#define ENET_DEST_IP1    168
#define ENET_DEST_IP2    1
#define ENET_DEST_IP3    255   // broadcast
```

To send to a specific host instead of broadcast, change `ENET_DEST_IP3`
to the host's last octet (e.g., `1` for `192.168.1.1`).

---

## 11. Reverting to LVDS

To revert to the original LVDS streaming path:

1. Restore `test.syscfg` — remove the `enet_cpsw` module and MPU region 5.
2. Restore `cascade_csirx.c` — put back the CBUFF activation and
   `configureTransfer()` calls in the EOL callback.
3. Restore `main_mss.c` — reinstate `Cascade_LVDSStreamInit()`,
   `Cascade_LVDSStreamSwConfig()`, `configureTransfer()`, and the
   DCA1000 delay.  Remove the Ethernet task and frame buffers.
4. Restore `mss_linker.cmd` — use the original linker without ENET
   sections.
5. Restore `mssTest.mak` — remove ENET libraries, includes, and source
   files.

The original files can be recovered from the SDK distribution archive or
from the backup `.xer5f` binary.

---

## 12. Troubleshooting

| Symptom                             | Likely Cause                              | Fix                                                |
|-------------------------------------|-------------------------------------------|-----------------------------------------------------|
| "ENET: driver open failed"          | CPSW clock not enabled or SysConfig error | Re-run SysConfig; check `ti_enet_config.h` exists   |
| "ENET: waiting for link …" forever  | No cable, PHY not present on board        | Verify RJ45 cable; confirm EVM has RGMII PHY        |
| Receiver gets no packets            | Firewall blocking UDP 5001                | Disable firewall or add exception for port 5001     |
| Frames have missing chirp lines     | UDP packets dropped (buffer overflow)     | Increase PC socket buffer: `--recv-buf 16M`         |
| Build error: `ti_enet_config.h` missing | SysConfig not regenerated              | Run `gmake syscfg` after modifying `test.syscfg`    |
| Linker error: enet library not found | `MCU_PLUS_INSTALL_PATH` not set          | Set env var to MCU+ SDK root                        |
| Assert in EOL callback              | Frame buffer overflow                     | Verify `TEST_CHIRP_LINES_PER_FRAME` matches config  |
