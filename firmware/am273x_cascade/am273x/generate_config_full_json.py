"""
Merge each build_*_inf/config.json with PostProc + raw-layout fields -> config_full.json.
Keeps config.json unchanged. Run after editing config.json (e.g. compiledSettings).

  python generate_config_full_json.py              # build_*_inf only (default)
  python generate_config_full_json.py --1frame     # also build_*_1frame

Firmware for *_inf: from parent folder, gmake testInf MMWAVE_SDK_DEVICE_TYPE=am273x
"""

import argparse
import json
from pathlib import Path
from typing import List

# From matching cascade_*.cfg (32 coeffs each); same across profiles in this tree.
_ANTENNA_CALIB_1 = [
    -0.44086, -0.37671, -0.27167, -0.61047, -0.13922, -0.62286, 0.02533, -0.60785,
    -0.38330, 0.56158, -0.59875, 0.36621, -0.73328, 0.08215, -0.64923, 0.01227,
    -0.01538, -0.58875, 0.27704, -0.62524, 0.38312, -0.52728, 0.47943, -0.37726,
    -0.66345, 0.09552, -0.67474, -0.19995, -0.54498, -0.49585, -0.42108, -0.48193,
]
_ANTENNA_CALIB_2 = [
    0.52539, -0.28143, 0.69080, -0.06561, 0.65625, 0.08118, 0.57855, 0.26385,
    -0.37817, -0.53223, -0.14532, -0.67084, 0.16516, -0.73163, 0.23608, -0.61774,
    0.58875, 0.13110, 0.56549, 0.39886, 0.45013, 0.48950, 0.27313, 0.57507,
    0.06879, -0.65051, 0.32404, -0.59290, 0.58905, -0.44318, 0.57373, -0.32166,
]
_ANTENNA_CALIB_3 = [
    -0.02155, 0.61859, -0.30334, 0.63727, -0.40479, 0.53766, -0.51367, 0.38599,
    0.66302, -0.05438, 0.63898, 0.22076, 0.54443, 0.48260, 1.00000, 0.00140,
    -0.38184, -0.48633, -0.18005, -0.69617, -0.04089, -0.68475, 0.15771, -0.64050,
    -0.48895, 0.48785, -0.66699, 0.26941, -0.77966, -0.04065, -0.69421, -0.13177,
]


def extension_block(cfg_name: str) -> dict:
    return {
        "schema": "cascade_config_full_v1",
        "extendsConfigJson": "config.json",
        "postProc_mmWaveStudio": {
            "source": "Matching cascade_*.cfg CLI lines; used by mmWave Studio PostProc for AoA / array processing.",
            "antennaCalibParams1": _ANTENNA_CALIB_1,
            "antennaCalibParams2": _ANTENNA_CALIB_2,
            "antennaCalibParams3": _ANTENNA_CALIB_3,
            "analogMonitor": [0, 0],
            "calibrationNote": (
                "Example / template coefficients — not guaranteed for your EVM serial. "
                "Run OTA calibration on your 2-chip hardware and replace these for accurate AoA."
            ),
        },
        "rawCaptureLayout": {
            "description": "Logical layout of merged DCA1000 frame (8 virtual RX); C-order last index fastest.",
            "shape_loop_chirp_rx_sample_iq": [64, 6, 8, 256, 2],
            "shape_chirpStep_rx_sample_iq": [384, 8, 256, 2],
            "chirp_step": "chirp_step = loop * 6 + chirp_idx  (0..383)",
            "virtual_rx": "0..3 master AWR2243 RX0..3; 4..7 slave AWR2243 RX0..3",
            "bytes_per_complex_sample": 4,
            "int16_IQ_order": "I then Q, little-endian per sample",
            "firmware_openCfg": {"iqSwapSel": 0, "chInterleave": 1},
            "frame_bytes_merged_8rx": 3145728,
            "formula": "8 * 256 * (6 * 64) * 4",
        },
        "firmwareNotes": {
            "awr2243_numFrames": (
                "Frame config sent to radar uses numFrames=0 (infinite); MSS may stop after N EOF for _1frame builds."
            ),
            "mssInfBuild": (
                "For *_inf folders: build with CASCADE_INF=1 (adds -DCASCADE_INF). "
                "From ti/utils/test/cascade - Copy: gmake testInf MMWAVE_SDK_DEVICE_TYPE=am273x "
                "(or gmake mssTestInf after syscfg). compiledSettings.CASCADE_CONFIG_MACRO must match CASCADE_CONFIG=."
            ),
            "rlFrameCfg_numAdcSamples": (
                "Firmware sets rlFrameCfg.numAdcSamples to TEST_NUM_ADC_SAMPLES (256 here), same as profileCfg.numAdcSamples."
            ),
            "matching_cli_cfg": "See cascade_*.cfg in the same build folder as this file.",
        },
    }


def _config_paths(root: Path, include_1frame: bool) -> List[Path]:
    paths = sorted(root.glob("build_*_inf/config.json"))
    if include_1frame:
        paths = sorted({*paths, *root.glob("build_*_1frame/config.json")})
    return paths


def main() -> None:
    ap = argparse.ArgumentParser(description="Write config_full.json next to config.json")
    ap.add_argument(
        "--1frame",
        dest="include_1frame",
        action="store_true",
        help="Also process build_*_1frame (default is build_*_inf only)",
    )
    args = ap.parse_args()

    root = Path(__file__).resolve().parent
    for path in _config_paths(root, args.include_1frame):
        with open(path, encoding="utf-8") as f:
            base = json.load(f)
        out = dict(base)
        out["configFullVersion"] = "v1"
        out.update(extension_block(base.get("configName", "")))
        dest = path.parent / "config_full.json"
        with open(dest, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, indent=2)
            f.write("\n")
        print("Wrote", dest)


if __name__ == "__main__":
    main()
