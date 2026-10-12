import numpy as np, glob
H=r"C:\Users\RadarDemo\Documents\Jetson_Radar_Sync_Capture_Handover_Firmware_Investigation\sessions\stage3_01"
files=sorted(glob.glob(H+r"\radar\frame_*.bin"))
const=np.load("const_mask.npy").reshape(384,2,4,256,2)
valid=~const.any(-1)   # [384,2,4,256]
def chirp_stats(i):
    x=np.fromfile(files[i],dtype=np.int16).astype(np.float32).reshape(384,2,4,256,2)
    z=x[...,0]+1j*x[...,1]
    zz=z.reshape(64,6,2,4,256); zz=zz-np.median(zz.real,0)-1j*np.median(zz.imag,0)
    zz=zz.reshape(384,2,4,256)*valid
    # time-domain residual power per chirp per device; and per-sample max
    pw=(np.abs(zz)**2).sum(-1).sum(-1)/np.maximum(valid.sum(-1).sum(-1),1)   # [384,2]
    return pw, zz
for i in [10,25,29,126,158,207]:
    pw,zz=chirp_stats(i)
    base=np.median(pw)
    hot=np.argwhere(pw>20*base)
    print(f"frame {i}: median chirp pw {base:.0f}; #hot (chirp,dev) {len(hot)}; dev0 hot {np.sum(hot[:,1]==0) if len(hot) else 0}, dev1 hot {np.sum(hot[:,1]==1) if len(hot) else 0}")
    if len(hot):
        ch=np.unique(hot[:,0]); print("   hot chirps:",ch[:30].tolist(), "tx:",np.unique(ch%6).tolist())
        c,d=hot[np.argmax(pw[hot[:,0],hot[:,1]])]
        a=np.abs(zz[c,d]).max(0)  # over rx
        idx=np.flatnonzero(a>5*np.median(a[a>0]))
        print(f"   worst chirp {c} dev {d}: per-rx pw",np.round((np.abs(zz[c,d])**2).mean(-1)/base,1).tolist()," burst samples",idx.min() if len(idx) else None,"-",idx.max() if len(idx) else None, "n",len(idx))
