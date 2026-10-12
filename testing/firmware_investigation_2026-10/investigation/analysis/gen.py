import json, hashlib, os, re
H=r"C:\Users\RadarDemo\Documents\Jetson_Radar_Sync_Capture_Handover_Firmware_Investigation"
F=H+r"\firmware"
c=299792458.0; LSB=0.0482797623
HPF1={0:175e3,1:235e3,2:350e3,3:700e3}
HPF2={0:350e3,1:700e3,2:1.4e6,3:2.8e6,4:5e6,5:7.5e6,6:10e6,7:15e6}
m=json.load(open(F+r"\firmware_map.json"))
def derive(v):
    s=v["freq_slope_const"]*LSB            # MHz/us
    S=s*1e12
    mr=c*v["sample_rate_ksps"]*1e3/(2*S)
    k=c/(2*S)
    lam=c/(v["start_freq_ghz"]*1e9)
    vmax=lam/(4*v["num_chirps"]*(v["idle_time_us"]+v["ramp_end_time_us"])*1e-6)
    d=dict(slope_mhz_us=round(s,4),max_range_m=round(mr,2),range_res_m=round(mr/v["num_adc_samples"],4),
           hpf1_floor_m=round(HPF1[v["hpf1_reg"]]*k,2),hpf_floor_m=round(HPF2[v["hpf2_reg"]]*k,2))
    d["usable_window_m"]=[d["hpf_floor_m"],d["max_range_m"]]
    d.update(v_max_mps=round(vmax,4),v_res_mps=round(vmax/(v["num_loops"]/2),4),
             fps=round(1000/v["frame_periodicity_ms"],3),
             frame_bytes=v["num_adc_samples"]*v["num_chirps"]*v["num_loops"]*8*4)
    return d
# report differences in existing derived fields
for name,v in m["variants"].items():
    d=derive(v)
    diffs={k:(v.get(k),d[k]) for k in d if v.get(k)!=d[k]}
    print(name,"derived diffs:",diffs)

def md5(p): return hashlib.md5(open(p,"rb").read()).hexdigest()
base=dict(m["variants"]["r075m"])
new={}
for name,define,per,bdir in [("r075m_v2","CASCADE_CFG_R075M_V2",250,"build_r075m_v2_inf"),
                             ("r075m_v2_8fps","CASCADE_CFG_R075M_V2_8FPS",125,"build_r075m_v2_8fps_inf")]:
    v=dict(base); v.update(config_define=define,build_dir=bdir,appimage=f"am273x_cascade_{name}.appimage",
        appimage_md5=md5(rf"{F}\{name}\am273x_cascade_{name}.appimage"),
        rprc_md5=md5(rf"{F}\_build_record\{name}\{name}.rprc"),
        processing_cfg=f"cascade_{name}.cfg",flash_cfg=f"flash_{name}.cfg",
        hpf1_reg=0,hpf2_reg=0,frame_periodicity_ms=per)
    new[name]=v
assert md5(rf"{F}\r075m\am273x_cascade_r075m.appimage")==m["variants"]["r075m"]["appimage_md5"]
assert md5(rf"{F}\_build_record\r075m\r075m.rprc")==m["variants"]["r075m"]["rprc_md5"]
m["variants"].update(new)
for name,v in m["variants"].items():
    v.update(derive(v))
    v["compression"]="off"
    fixed=name in new
    v["dss_l3_meminit"]=fixed
    v["data_valid"]=("yes" if fixed else
        "NO when booted from QSPI: ~50% of every chirp is stale DSS-L3 words (no DSS L3 MEMINIT). Valid only when loaded through CCS (GEL runs MEMINIT).")
m["generated"]="2026-10-10"
m["conventions"]["derived"]+=" hpf1_floor_m = f_hpf1 x c/(2.slope). fps = 1000/frame_periodicity_ms. frame_bytes = num_adc_samples x num_chirps x num_loops x 8 RX x 4 B."
m["conventions"]["hpf_registers"]="HPF1 reg 0/1/2/3 = 175/235/350/700 kHz; HPF2 reg 0/1/2/3/4/5/6/7 = 0.35/0.7/1.4/2.8/5/7.5/10/15 MHz (rl_sensor.h / common.c CHIRP_HPF*_CORNER_FREQ_*). Before 2026-10-10 hpf1_floor_m was computed with 700 kHz for reg 2 and was 2x too large; corrected for every variant."
m["conventions"]["compression"]="The cascade firmware never configures compression (no compression call in common.c / main_mss.c / mmwave control). 'off' for every image. The 'compressionCfg ... 1 ...' line in older .cfg files was inert and wrong."
m["conventions"]["dss_l3_meminit"]="true = image runs SOC_rcmStartMemInitDSSL3 at boot (main_mss.c). Images with false stream ~50% stale words per chirp when booted from QSPI; see investigation/REPORT.md."
m["conventions"]["iq_order"]="Every image: int16 little-endian, I then Q (rlDevDataFmtCfg iqSwapSel=0, main_mss.c). adcbufCfg SampleSwap must be 0 in every processing .cfg."
json.dump(m,open(F+r"\firmware_map.json","w"),indent=2); print("map written")

# ---------------- .cfg files ----------------
TPL=open(F+r"\r075m\cascade_r075m.cfg").read()
calib="\n".join(l for l in TPL.splitlines() if l.startswith("antennaCalibParams"))
def cfg(name,v,extra_note):
    d=v; k=c/(2*d["slope_mhz_us"]*1e12)
    return f"""% AWR2243-2X-CAS-EVM  {name}  ({v['config_define']})
% 2-chip cascade, 6TX TDM MIMO, 8RX, 48 virtual channels.
% Firmware image: {v['appimage']}  md5 {v['appimage_md5']}
%
% Generated 2026-10-10 from cascade_config.h ({v['config_define']}) and the
% fixed register settings in common.c / main_mss.c. Every value below matches
% the firmware; this file is NOT sent to the device.
{extra_note}%
%   freqSlopeConst {v['freq_slope_const']} -> slope {v['slope_mhz_us']} MHz/us
%   Sampled BW {v['slope_mhz_us']*25.6:.1f} MHz (slope x N/fs = {v['slope_mhz_us']} x 25.6 us)
%   Range resolution : {v['range_res_m']} m
%   Max range        : {v['max_range_m']} m      (= range_res x 256, forced by the FFT)
%   Max velocity     : +/-{v['v_max_mps']} m/s
%   Velocity res     : {v['v_res_mps']} m/s  (= 2 x v_max / 64, forced by the FFT)
%   Frame period     : {v['frame_periodicity_ms']} ms ({v['fps']:g} fps), infinite frames
%   Frame size       : {v['frame_bytes']:,} B = 384 chirps x 2 dev x 4 RX x 256 x (I,Q) int16
%
% USABLE WINDOW {v['hpf_floor_m']} - {v['max_range_m']} m.
%   RX high-pass corners: HPF1 reg {v['hpf1_reg']} ({HPF1[v['hpf1_reg']]/1e3:g} kHz) -> {v['hpf1_floor_m']} m,
%   HPF2 reg {v['hpf2_reg']} ({HPF2[v['hpf2_reg']]/1e3:g} kHz) -> {v['hpf_floor_m']} m. Analogue, not a processing gate.
%
% DATA FORMAT (see investigation/JETSON_DATA_FORMAT.md):
%   int16 LE, I then Q (iqSwapSel=0 -> adcbufCfg SampleSwap 0),
%   per chirp: [dev0 RX0..3][dev1 RX0..3], each RX = 256 contiguous (I,Q)
%   pairs (non-interleaved, chInterleave=1), chirp = loop*6 + tx.
%   No compression (the firmware never configures it), no headers.
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
profileCfg 0 {v['start_freq_ghz']} {v['idle_time_us']} {v['adc_start_time_us']} {v['ramp_end_time_us']} 0 0 {v['slope_mhz_us']} 0 {v['num_adc_samples']} {v['sample_rate_ksps']} {v['hpf1_reg']} {v['hpf2_reg']} {v['rx_gain_db']}
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
old_note="""% CORRECTED 2026-10-10. The previous version of this file was wrong in:
%   adcbufCfg SampleSwap 1 -> 0 (data is I-first; Q-first mirrors the spectrum),
%   frameCfg period 50 -> 250 ms, compressionCfg enabled 1 -> 0 (never active),
%   dataPathConfig CQ sizes. Data from this image booted from QSPI is ~50%
%   stale words per chirp (no DSS L3 MEMINIT) - use r075m_v2 instead.
"""
new_note="""% Carries the DSS L3 MEMINIT fix (main_mss.c): no stale words.
"""
for name in ["r075m","r075m_v2","r075m_v2_8fps"]:
    v=m["variants"][name]; os.makedirs(rf"{F}\{name}",exist_ok=True)
    open(rf"{F}\{name}\cascade_{name}.cfg","w",newline="\n").write(cfg(name,v,old_note if name=="r075m" else new_note))
    if name!="r075m":
        fl=open(rf"{F}\r075m\flash_r075m.cfg").read().replace("r075m",name)
        open(rf"{F}\{name}\flash_{name}.cfg","w",newline="\n").write(fl)
print("cfgs written")
