import numpy as np, glob
H=r"C:\Users\RadarDemo\Documents\Jetson_Radar_Sync_Capture_Handover_Firmware_Investigation\sessions"
const=np.load("const_mask.npy")
C=const.reshape(384,4096)
f0=np.fromfile(H+r"\stage3_01\radar\frame_000000.bin",dtype=np.int16).reshape(384,4096)
# even/odd masks
me,mo=C[0],C[1]
print("even mask frac %.3f odd %.3f overlap %.3f"%(me.mean(),mo.mean(),(me&mo).mean()))
print("all even same:",(C[0::2]==me).all(),"all odd same:",(C[1::2]==mo).all())
# values at const offsets identical across even chirps?
ve=f0[0::2][:,me]; vo=f0[1::2][:,mo]
print("even const values identical across all 192 even chirps:",(ve==ve[0]).all())
print("odd const values identical across all odd chirps:",(vo==vo[0]).all())
# Block structure: 16-int16 blocks fully const or fully varying?
b=me.reshape(-1,16); print("even: blocks all-or-none:",((b.all(1))|(~b.any(1))).all(), "frac const blocks %.3f"%b.all(1).mean())
b=mo.reshape(-1,16); print("odd: blocks all-or-none:",((b.all(1))|(~b.any(1))).all(), "frac const blocks %.3f"%b.all(1).mean())
# variation: are varying positions ever equal to another chirp? (i.e. delayed copy)
# stats of constant values
v=ve[0].astype(np.int64); print("const vals: mean|v| %.0f std %.0f  min %d max %d"%(np.abs(v).mean(),v.std(),v.min(),v.max()))
print("byte histogram uniformity: unique bytes",len(np.unique(np.ascontiguousarray(ve[0]).view(np.uint8))))
# 2nd session
files=sorted(glob.glob(H+r"\ipad_test_01\radar\frame_*.bin"))
print(len(files))
G=np.stack([np.fromfile(f,dtype=np.int16) for f in files[:120]])
cg=(G==G[0]).all(0)
print("ipad const %.2f%%"%(100*cg.mean()))
Cg=cg.reshape(384,4096)
print("ipad masks period2:",(Cg[0::2]==Cg[0]).all(),(Cg[1::2]==Cg[1]).all())
print("ipad even mask == stage3 even mask:",(Cg[0]==me).mean(), " odd:",(Cg[1]==mo).mean())
g0=G[0].reshape(384,4096)
both=Cg[0]&me
print("positions const in both (even): ",both.sum()," values equal:",(g0[0][both]==f0[0][both]).mean())
both=Cg[1]&mo
print("positions const in both (odd): ",both.sum()," values equal:",(g0[1][both]==f0[1][both]).mean())
# also check even vs odd: which pattern for chirp 0 in ipad might be swapped
print("ipad even vs stage3 odd:",(Cg[0]==mo).mean())
