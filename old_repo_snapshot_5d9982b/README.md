# Cascaded Radar Project

This project contains a small Windows-based capture and processing workflow for the fixed shortrange cascade radar setup under `cascaded_radar`.

It is organized into two main parts:

- `capture`: firmware load, DCA1000 control, raw recording, frame splitting, and offline extraction
- `processing`: offline radar processing and visualization for captured frames

## Project Layout

- [capture\test.py](C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\cascaded_radar\capture\test.py): main entrypoint for capture, stop, geometry print, cfg validation, and offline extraction
- [capture\config.py](C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\cascaded_radar\capture\config.py): fixed paths and `cascade_shortrange.cfg` parsing
- [capture\dca.py](C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\cascaded_radar\capture\dca.py): DCA1000 control, raw file monitoring, and frame splitting
- [capture\radar.py](C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\cascaded_radar\capture\radar.py): DSS firmware load and UART stop helper
- [processing\main.py](C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\cascaded_radar\processing\main.py): offline processing and plotting CLI
- [config\build_shortrange_inf\cascade_shortrange.cfg](C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\cascaded_radar\config\build_shortrange_inf\cascade_shortrange.cfg): fixed radar config used by this project

Runtime output folders:

- [capture\data](C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\cascaded_radar\capture\data): raw DCA1000 `.bin` capture files and log CSVs
- [capture\frames](C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\cascaded_radar\capture\frames): per-frame split `.bin` files

## Software Requirements

This project is Windows-only in its current form because it depends on TI Windows tools and PowerShell.

Required software:

- Windows 10 or Windows 11
- Python 3.10 or newer
- NumPy
- SciPy
- Matplotlib
- TI Code Composer Studio with DSS support
- TI mmWave Studio PostProc environment containing `DCA1000EVM_CLI_Control.exe`


Python packages used by the current code:

- `numpy`
- `scipy`
- `matplotlib`

Install the Python packages in your environment with:

```powershell
pip install numpy scipy matplotlib
```

## Fixed Tool Paths Used By The Project

The code currently expects these Windows tool paths:

- CCS DSS batch file:
  `C:\ti\ccs2050\ccs\ccs_base\scripting\bin\dss.bat`
- DCA1000 CLI:
  `C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\DCA1000EVM_CLI_Control.exe`

The project-local config files it uses are:

- [config\AM273X_Capture_fixed.json](C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\cascaded_radar\config\AM273X_Capture_fixed.json)
- [config\AM273x_XDS110.ccxml](C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\cascaded_radar\config\AM273x_XDS110.ccxml)
- [config\reset_load_run_dualcore_reset.js](C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\cascaded_radar\config\reset_load_run_dualcore_reset.js)
- [config\build_shortrange_inf\am273x_cascade_mss.xer5f](C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\cascaded_radar\config\build_shortrange_inf\am273x_cascade_mss.xer5f)
- [config\build_shortrange_inf\cascade_csirx.h](C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\cascaded_radar\config\build_shortrange_inf\cascade_csirx.h)
- [config\build_shortrange_inf\cascade_shortrange.cfg](C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\cascaded_radar\config\build_shortrange_inf\cascade_shortrange.cfg)

## Hardware Requirements

Required hardware:

- TI cascaded radar hardware matching the provided firmware/config set
- DCA1000 capture board
- XDS110 debugger connection
- Ethernet connection from the PC to the DCA1000
- UART connection from the PC to the radar board
- Power supply for the radar hardware and DCA1000
- LVDS/cascade interconnects required by your radar setup

PC network requirements:

- The PC Ethernet adapter connected to DCA1000 must use a static IP compatible with the capture JSON
- The current capture JSON expects:
  - PC IP: `192.168.33.30`
  - DCA1000 IP: `192.168.33.180`
  - Config port: `4096`
  - Data port: `4098`

Current UART default:

- COM port: `COM20`

You can override the UART port on the command line with `--uart COMx`.

## Before First Run

1. Open a terminal in:

```powershell
C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\cascaded_radar
```

2. Confirm the fixed waveform/config exists:

```powershell
python capture\test.py --print-geometry
```

3. Run the built-in cfg smoke test:

```powershell
python capture\test.py --validate-cfg
```

4. Confirm your PC NIC uses the static DCA network expected by the JSON.

5. Confirm no other application is holding the DCA1000:

- close mmWave Studio capture sessions
- close other DCA1000 CLI windows
- stop any previous capture still using UDP ports

## How To Run Capture

Run from the `cascaded_radar` folder:

```powershell
python capture\test.py
```

Useful options:

- `--uart COM20`: choose the UART port used for stop
- `--frames 100`: stop automatically after saving 100 split frames
- `--sync-wait 90`: wait longer for the radar to start producing data
- `--diag`: keep the debugger attached longer during firmware load
- `--skip-load`: skip firmware load if the firmware is already running
- `--out-dir capture\frames`: override the split-frame output folder

Examples:

```powershell
python capture\test.py --uart COM20 --sync-wait 90
python capture\test.py --frames 50
python capture\test.py --skip-load --uart COM20
```

To stop a running capture:

```powershell
python capture\test.py --stop --uart COM20
```

## Capture Outputs

Raw DCA outputs are written to:

- [capture\data](C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\cascaded_radar\capture\data)

Typical raw files:

- `am273x_capture_Raw_0.bin`
- `am273x_capture_Raw_LogFile.csv`

Split frame outputs are written to:

- [capture\frames](C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\cascaded_radar\capture\frames)

Typical frame files:

- `frame_000000.bin`
- `frame_000001.bin`

## How To Extract Frames Offline

You can extract frames from a raw DCA `.bin` into compressed `.npz` files:

```powershell
python capture\test.py --extract --bin-file capture\data\am273x_capture_Raw_0.bin
```

Useful options:

- `--frames 10`: extract only the first 10 frames
- `--out-dir extracted_npz`: choose output folder
- `--extract-time-order loop_chirp`
- `--extract-time-order chirp_loop`
- `--raw-iq-order cfg`
- `--raw-iq-order i-first`
- `--raw-iq-order q-first`

Example:

```powershell
python capture\test.py --extract --bin-file capture\data\am273x_capture_Raw_0.bin --frames 10 --out-dir extracted_npz
```

## How To Run Processing

The processing pipeline can operate on a raw `.bin` file or on a folder of split frames.

Example using the split frame folder:

```powershell
python -m processing.main --folder capture\frames --cfg config\build_shortrange_inf\cascade_shortrange.cfg
```

Example using one raw DCA `.bin`:

```powershell
python -m processing.main --bin capture\data\am273x_capture_Raw_0.bin --cfg config\build_shortrange_inf\cascade_shortrange.cfg
```

Example without opening plots:

```powershell
python -m processing.main --folder capture\frames --cfg config\build_shortrange_inf\cascade_shortrange.cfg --no-show
```

Example saving a plot:

```powershell
python -m processing.main --folder capture\frames --cfg config\build_shortrange_inf\cascade_shortrange.cfg --save output.png --no-show
```

## Important Notes

- This project is fixed to the shortrange configuration at [config\build_shortrange_inf\cascade_shortrange.cfg](C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\cascaded_radar\config\build_shortrange_inf\cascade_shortrange.cfg).
- The DCA1000 capture JSON currently writes raw data into `capture\data`.
- The frame splitter writes per-frame payload files into `capture\frames`.
- `capture\test.py` supports geometry print, cfg validation, capture, stop, and offline extraction from one entrypoint.
- The current capture code loads firmware, configures the DCA1000, and records/splits incoming raw data.

## Troubleshooting

If DCA1000 configuration fails:

- verify the PC NIC static IP is `192.168.33.30`
- verify the DCA1000 IP is `192.168.33.180`
- ping the DCA1000
- close mmWave Studio if it is holding the DCA board
- power-cycle the DCA1000

If raw files appear in the wrong folder:

- check both JSON files point to `capture\data`
- check the active TI CLI JSON beside `DCA1000EVM_CLI_Control.exe`

If `raw_stream=0 B` remains at zero:

- verify radar firmware actually started LVDS output
- verify the UART connection and configured COM port
- try `--sync-wait 90`
- check `capture\data\am273x_capture_Raw_LogFile.csv` for packet counts
- verify LVDS and Ethernet cables are connected correctly

