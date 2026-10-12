"""Generate firmware_map.json entries, new-variant .cfg/flash cfgs and the
corrected old-variant .cfg files for a Jetson-layout firmware tree.

This is the generator used for the 2026-10-10 v2 release
(firmware/releases/2026-10-10_v2). It is run ONCE on a tree that already holds
the built images and the previous firmware_map.json; re-running it on the
finished release would add nothing. For a new variant, copy the NEW list
pattern, build the images with build_v2_variants.ps1, then run this against
the new tree and verify with fill_firmware_map.py.

Usage: python gen_v2_release_metadata.py <firmware tree root>
"""
import json, hashlib, os, sys

R = sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__)
c = 299792458.0
LSB = 0.0482797623
HPF1 = {0: 175e3, 1: 235e3, 2: 350e3, 3: 700e3}
HPF2 = {0: 350e3, 1: 700e3, 2: 1.4e6, 3: 2.8e6}
PKT = 2160.53          # packets per frame (3,145,728 / 1456)
PKT_TX_US = 12.2       # per-packet wire time besides the delay (Jetson: 134.4 ms at 50 us)


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


m = json.load(open(rf"{R}\firmware_map.json", encoding="utf-8"))
V = m["variants"]


def derive(v):
    S = v["freq_slope_const"] * LSB * 1e12
    k = c / (2 * S)
    mr = c * v["sample_rate_ksps"] * 1e3 / (2 * S)
    vmax = (c / (v["start_freq_ghz"] * 1e9)) / (
        4 * v["num_chirps"] * (v["idle_time_us"] + v["ramp_end_time_us"]) * 1e-6)
    d = dict(slope_mhz_us=round(v["freq_slope_const"] * LSB, 4),
             max_range_m=round(mr, 2),
             range_res_m=round(mr / v["num_adc_samples"], 4),
             hpf1_floor_m=round(HPF1[v["hpf1_reg"]] * k, 2),
             hpf_floor_m=round(HPF2[v["hpf2_reg"]] * k, 2))
    d["usable_window_m"] = [d["hpf_floor_m"], d["max_range_m"]]
    d.update(v_max_mps=round(vmax, 4), v_res_mps=round(vmax / (v["num_loops"] / 2), 4),
             fps=round(1000 / v["frame_periodicity_ms"], 2),
             frame_bytes=v["num_adc_samples"] * v["num_chirps"] * v["num_loops"] * 8 * 4)
    return d


NEW = [("r017m_v2", "r017m", "CASCADE_CFG_R017M_V2", 250),
       ("r017m_v2_8fps", "r017m", "CASCADE_CFG_R017M_V2_8FPS", 125),
       ("r017m_calib_v2", "r017m_calib", "CASCADE_CFG_R017M_CALIB_V2", 1000),
       ("r050m_v2", "r050m", "CASCADE_CFG_R050M_V2", 250),
       ("r050m_v2_8fps", "r050m", "CASCADE_CFG_R050M_V2_8FPS", 125),
       ("r100m_v2", "r100m", "CASCADE_CFG_R100M_V2", 250),
       ("r100m_v2_8fps", "r100m", "CASCADE_CFG_R100M_V2_8FPS", 125),
       ("r142m_v2", "r142m", "CASCADE_CFG_R142M_V2", 250),
       ("r142m_v2_8fps", "r142m", "CASCADE_CFG_R142M_V2_8FPS", 125),
       ("r168m_v2", "r168m", "CASCADE_CFG_R168M_V2", 250),
       ("r168m_v2_8fps", "r168m", "CASCADE_CFG_R168M_V2_8FPS", 125)]
OLD = ["r017m", "r017m_calib", "r050m", "r100m", "r142m", "r168m"]

# ---------------- map ----------------
ORDER = list(V["r075m_v2"].keys())
for name, base, define, per in NEW:
    v = dict(V[base])
    v.update(config_define=define, build_dir=f"build_{name}_inf",
             appimage=f"am273x_cascade_{name}.appimage",
             appimage_md5=md5(rf"{R}\{name}\am273x_cascade_{name}.appimage"),
             rprc_md5=md5(rf"{R}\_build_record\{name}\{name}.rprc"),
             processing_cfg=f"cascade_{name}.cfg", flash_cfg=f"flash_{name}.cfg",
             hpf1_reg=0, hpf2_reg=0, frame_periodicity_ms=per)
    v.update(derive(v))
    v.update(compression="off", dss_l3_meminit=True, data_valid="yes")
    V[name] = {k: v[k] for k in ORDER}

for n, v in V.items():                      # every entry must derive to itself
    d = derive(v)
    bad = {k: (v[k], d[k]) for k in d if v[k] != d[k]}
    assert not bad, (n, bad)

m["generated"] = "2026-10-10"
cv = m["conventions"]
cv["dca_wire_time"] = (
    "The frame's time on the wire at the DCA1000 packet delay must be shorter than "
    "frame_periodicity_ms, or the DCA streams back-to-back and drops LVDS data internally "
    "(invisible to sequence-number and byte-count checks). CONFIG_PACKET_DATA delay is in 8 ns "
    "ticks; each packet takes ~delay + 12.2 us; frame_bytes/1456 = 2160.5 packets. "
    "50 us (6250): 134.4 ms per frame -> max 7.44 fps. 25 us (3125): ~80 ms per frame -> 8 fps OK. "
    "Use 25 us for every 8 fps image.")
cv["v2_family"] = (
    "*_v2 images (2026-10-10): the base variant's cascade_config.h block unchanged except "
    "HPF1/HPF2 = 0/0 (175/350 kHz) and, for *_8fps, frame_periodicity_ms = 125. All carry the "
    "DSS L3 MEMINIT fix. r017m_calib_v2 keeps 1000 ms. Each image disassembly-diffed against its "
    "base image: only MEMINIT, the HPF store and the frame-period immediate differ.")
cv["antenna_calibration"] = (
    "antennaCalibParams are inherited unchanged from the original shortrange .cfg (77 GHz set: "
    "r017m*) and longrange .cfg (76 GHz set: every other variant). Their provenance and the HPF "
    "they were measured with are not recorded; the 76 GHz set came from a profile with HPF 2/2. "
    "Repeat the calibration with the HPF 0/0 images before trusting angle estimates: "
    "r017m_calib_v2 for 77 GHz, a 76 GHz v2 image for the 76 GHz variants.")
with open(rf"{R}\firmware_map.json", "w", encoding="utf-8", newline="\n") as f:
    json.dump(m, f, indent=2)
    f.write("\n")
print("map:", len(V), "variants")


# ---------------- .cfg text ----------------
def tok(text, kw):
    for line in text.splitlines():
        line = line.split('%')[0].strip()
        if line.split()[:1] == [kw]:
            return " ".join(line.split()[1:])


def calib_lines(text):
    return "\n".join(l for l in text.splitlines() if l.startswith("antennaCalibParams"))


def cfg_text(name, v, note, calib):
    S = v["slope_mhz_us"]
    tadc = v["num_adc_samples"] / (v["sample_rate_ksps"] / 1e3)
    tc = v["idle_time_us"] + v["ramp_end_time_us"]
    act = 384 * tc / 1e3
    wire = PKT * (25 + PKT_TX_US) / 1e3
    band = "77 GHz shortrange set" if v["start_freq_ghz"] == 77 else "76 GHz longrange set"
    return f"""% AWR2243-2X-CAS-EVM  {name}  ({v['config_define']})
% 2-chip cascade, 6TX TDM MIMO, 8RX, 48 virtual channels.
% Firmware image: {v['appimage']}  md5 {v['appimage_md5']}
%
% Generated 2026-10-10 from cascade_config.h ({v['config_define']}) and the
% fixed register settings in common.c / main_mss.c. Every value below matches
% the firmware; this file is NOT sent to the device.
{note}%
%   freqSlopeConst {v['freq_slope_const']} -> slope {S} MHz/us
%   Sampled BW {S * tadc:.1f} MHz (slope x N/fs = {S} x {tadc:g} us)
%   Range resolution : {v['range_res_m']} m
%   Max range        : {v['max_range_m']} m      (= range_res x 256, forced by the FFT)
%   Max velocity     : +/-{v['v_max_mps']} m/s
%   Velocity res     : {v['v_res_mps']} m/s  (= 2 x v_max / 64, forced by the FFT)
%   Frame period     : {v['frame_periodicity_ms']} ms ({v['fps']:g} fps), infinite frames
%   Chirping         : 384 x {tc:g} us = {act:.2f} ms per frame
%   DCA1000          : ~{wire:.0f} ms per frame on the wire at 25 us packet delay
%                      (50 us gives 134 ms, too slow for 8 fps)
%   Frame size       : {v['frame_bytes']:,} B = 384 chirps x 2 dev x 4 RX x 256 x (I,Q) int16
%
% USABLE WINDOW {v['hpf_floor_m']} - {v['max_range_m']} m.
%   RX high-pass corners: HPF1 reg {v['hpf1_reg']} ({HPF1[v['hpf1_reg']] / 1e3:g} kHz) -> {v['hpf1_floor_m']} m,
%   HPF2 reg {v['hpf2_reg']} ({HPF2[v['hpf2_reg']] / 1e3:g} kHz) -> {v['hpf_floor_m']} m. Analogue, not a processing gate.
%
% DATA FORMAT (see investigation/JETSON_DATA_FORMAT.md):
%   int16 LE, I then Q (iqSwapSel=0 -> adcbufCfg SampleSwap 0),
%   per chirp: [dev0 RX0..3][dev1 RX0..3], each RX = 256 contiguous (I,Q)
%   pairs (non-interleaved, chInterleave=1), chirp = loop*6 + tx.
%   No compression (the firmware never configures it), no headers.
%
% ANTENNA CALIBRATION: antennaCalibParams below are inherited ({band});
%   their provenance and the HPF they were measured with are not recorded.
%   Repeat the calibration before trusting angle estimates.
%
% WHAT THE PYTHON PIPELINE READS: profileCfg, frameCfg (fields 0-2),
%   adcbufCfg (SampleSwap, field 2), channelCfg, adcCfg, chirpCfg.
%   The remaining commands are inert but kept correct.
%
% Identity checks: max_range = range_res x 256, and v_max / v_res = 32.
sensorStop
flushCfg
dfeDataOutputMode 1
channelCfg 15 7 1 15 7
adcCfg 2 1
adcbufCfg -1 0 0 1 1
lowPower 0 0
dataPathClkCfg 1 1
profileCfg 0 {v['start_freq_ghz']} {v['idle_time_us']} {v['adc_start_time_us']} {v['ramp_end_time_us']} 0 0 {S} 0 {v['num_adc_samples']} {v['sample_rate_ksps']} {v['hpf1_reg']} {v['hpf2_reg']} {v['rx_gain_db']}
dataPathConfig 0 1 0 2 132 132 72 0
hsiClockConfig 9 0
hsiLaneConfig 15 1 0 2 0 4 0 5 0 3 0 0
dataFormatConfig 0 1
chirpCfg 0 0 0 0 0 0 0 1
chirpCfg 1 1 0 0 0 0 0 2
chirpCfg 2 2 0 0 0 0 0 4
chirpCfg 3 3 0 0 0 0 0 1
chirpCfg 4 4 0 0 0 0 0 2
chirpCfg 5 5 0 0 0 0 0 4
frameCfg 0 5 {v['num_loops']} 0 {v['frame_periodicity_ms']} 1 0
compressionCfg -1 0 0 0.5 8
{calib}
sensorStart
"""


CAL = {}
for old in OLD:
    p = rf"{R}\{old}\cascade_{old}.cfg"
    t = open(p, encoding="utf-8-sig").read()
    CAL[old] = calib_lines(t)
    assert CAL[old].count("antennaCalibParams") == 3, old
    changes = []
    for kw, new in [("adcbufCfg", "-1 0 0 1 1"),
                    ("frameCfg", f"0 5 64 0 {V[old]['frame_periodicity_ms']} 1 0"),
                    ("compressionCfg", "-1 0 0 0.5 8"),
                    ("dataPathConfig", "0 1 0 2 132 132 72 0")]:
        o = tok(t, kw)
        if o != new:
            changes.append(f"%   {kw} '{o}' -> '{new}'")
    if not changes:          # already corrected by an earlier run: leave it byte-identical
        continue
    note = ("% CORRECTED 2026-10-10. Changed from the previous version of this file:\n"
            + "\n".join(changes) + "\n"
            "%   (SampleSwap 1 decoded the data Q-first, which mirrors the range spectrum.)\n"
            "%   DATA FROM THIS IMAGE BOOTED FROM QSPI IS ~50% STALE WORDS PER CHIRP\n"
            f"%   (no DSS L3 MEMINIT). Use {old}_v2 for new recordings.\n")
    with open(p, "w", encoding="ascii", newline="\n") as f:
        f.write(cfg_text(old, V[old], note, CAL[old]))

flash_tpl = open(rf"{R}\r075m_v2\flash_r075m_v2.cfg", encoding="ascii").read()
for name, base, define, per in NEW:
    os.makedirs(rf"{R}\{name}", exist_ok=True)
    note = f"% {base} chirp unchanged; HPF 0/0 and the DSS L3 MEMINIT fix (v2 family).\n"
    with open(rf"{R}\{name}\cascade_{name}.cfg", "w", encoding="ascii", newline="\n") as f:
        f.write(cfg_text(name, V[name], note, CAL[base]))
    with open(rf"{R}\{name}\flash_{name}.cfg", "w", encoding="ascii", newline="\n") as f:
        f.write(flash_tpl.replace("r075m_v2", name))
print("cfgs written")
