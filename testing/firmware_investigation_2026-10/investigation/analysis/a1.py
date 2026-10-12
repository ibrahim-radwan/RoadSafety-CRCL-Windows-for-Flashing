import numpy as np, glob
H=r"C:\Users\RadarDemo\Documents\Jetson_Radar_Sync_Capture_Handover_Firmware_Investigation\sessions"
files=sorted(glob.glob(H+r"\stage3_01\radar\frame_*.bin"))
F=np.stack([np.fromfile(f,dtype=np.int16) for f in files])
print(F.shape)
const=(F==F[0]).all(axis=0)
print("const %.2f%%"%(100*const.mean()))
np.save("const_mask.npy",const)
C=const.reshape(384,4096)
print("per-chirp const frac: min %.3f max %.3f"%(C.mean(1).min(),C.mean(1).max()))
print("first 12 chirp fracs",np.round(C.mean(1)[:12],3))
# per device half within a chirp
D=const.reshape(384,2,2048)
print("dev0 frac %.3f dev1 frac %.3f"%(D[:,0].mean(),D[:,1].mean()))
# offset-within-chirp profile
off=C.mean(0)
print("offset profile (per 16 int16 block) first 64 blocks:",np.round(off.reshape(-1,16).mean(1)[:64],2))
# is mask identical across chirps?
same=(C==C[0]).all(1)
print("chirps with mask identical to chirp0:",same.sum())
# 32-byte alignment of runs
edges=np.flatnonzero(np.diff(np.r_[0,const.astype(np.int8),0]))
st=edges[0::2]; ln=edges[1::2]-st
print("runs",len(st),"start%16==0: %.3f  len%16==0: %.3f"%((st%16==0).mean(),(ln%16==0).mean()))
print("len hist",np.unique(ln,return_counts=True))
