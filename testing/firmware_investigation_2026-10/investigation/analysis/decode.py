import numpy as np, glob, csv, sys
H=r"C:\Users\RadarDemo\Documents\Jetson_Radar_Sync_Capture_Handover_Firmware_Investigation\sessions\stage3_01"
files=sorted(glob.glob(H+r"\radar\frame_*.bin"))
const=np.load("const_mask.npy").reshape(384,2,4,256,2)
NS=256; RBIN=299792458*10e6/(2*19.9878e12*NS)
print("range bin m",RBIN)
# valid mask per (tx,dev,rx,sample): from chirps 0..5
valid=~const[:6].any(-1)          # [6,2,4,256]
print("valid frac per tx:",valid.mean(axis=(1,2,3)).round(3))
win=np.hanning(NS).astype(np.float32)
def frame_profiles(f, iq_first=True):
    x=np.fromfile(f,dtype=np.int16).astype(np.float32).reshape(64,6,2,4,NS,2)
    z=(x[...,0]+1j*x[...,1]) if iq_first else (x[...,1]+1j*x[...,0])
    z=z-z.mean(axis=0,keepdims=True)          # MTI: removes static clutter AND stale words (exact zeros)
    z=z*valid[None]                            # explicit
    Z=np.fft.fft(z*win,axis=-1)
    p=(np.abs(Z)**2).sum(axis=(0,1,2,3))       # [NS]
    # static (no MTI) profile on valid samples, for comparison
    return p
P=np.array([frame_profiles(f) for f in files]); np.save("prof_I.npy",P)
Pq=np.array([frame_profiles(f,False) for f in files]); np.save("prof_Q.npy",Pq)
# energy split halves
print("pos/neg half energy I-first: %.2f   Q-first: %.2f"%(P[:,1:128].sum()/P[:,129:].sum(), Pq[:,1:128].sum()/Pq[:,129:].sum()))
