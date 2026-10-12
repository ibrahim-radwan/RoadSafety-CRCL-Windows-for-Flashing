import numpy as np, glob, csv
H=r"C:\Users\RadarDemo\Documents\Jetson_Radar_Sync_Capture_Handover_Firmware_Investigation\sessions\stage3_01"
files=sorted(glob.glob(H+r"\radar\frame_*.bin"))
const=np.load("const_mask.npy")
rows=list(csv.DictReader(open(H+r"\sync\lidar_target_truth.csv"))); ph=[r["phase"] for r in rows]
P=np.load("prof_I.npy"); RB=0.29294
out=[]
for i,f in enumerate(files):
    x=np.fromfile(f,dtype=np.int16)
    v=np.abs(x[~const].astype(np.int32))
    out.append((v.max(), (v>=32000).sum(), v.mean()))
out=np.array(out,float)
bb=P[:,5:250].sum(1)/np.median(P[:,5:250].sum(1))
print("median of maxabs %.0f, frames with any |x|>=32000: %d"%(np.median(out[:,0]),(out[:,1]>0).sum()))
for i in [10,24,25,29,85,124,126,158,207]:
    # where is the extra energy? ratio profile vs median profile
    r=P[i]/np.median(P,0)
    print(f"f{i} t={i*0.25:.2f}s phase={ph[i]} bb={bb[i]:.1f} maxabs={out[i,0]:.0f} clipped={int(out[i,1])} mean|x|={out[i,2]:.1f} | ratio by range band: 0-5m {r[1:17].mean():.1f} 5-10m {r[17:34].mean():.1f} 10-15m {r[34:51].mean():.1f} 15-30m {r[51:102].mean():.1f} 30-75m {r[102:250].mean():.1f}")
print("corr(bb, mean|x|) = %.2f"%np.corrcoef(bb,out[:,2])[0,1])
