import numpy as np, glob, csv, sys
sys.path.insert(0,r"C:\Users\RadarDemo\Documents\Jetson_Radar_Sync_Capture_Handover_Firmware_Investigation\processing")
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    import radar_config as rc
    corr=rc.parse_calibration(r"C:\Users\RadarDemo\Documents\Jetson_Radar_Sync_Capture_Handover_Firmware_Investigation\firmware\r075m\cascade_r075m.cfg")
H=r"C:\Users\RadarDemo\Documents\Jetson_Radar_Sync_Capture_Handover_Firmware_Investigation\sessions\stage3_01"
files=sorted(glob.glob(H+r"\radar\frame_*.bin"))
rows=list(csv.DictReader(open(H+r"\sync\lidar_target_truth.csv")))
tr=np.array([float(r["target_range_m"]) if r["target_range_m"] else np.nan for r in rows])
ta=np.array([float(r["target_azimuth_deg"]) if r["target_azimuth_deg"] else np.nan for r in rows])
print("truth az range %.1f..%.1f deg"%(np.nanmin(ta),np.nanmax(ta)))
const=np.load("const_mask.npy").reshape(384,2,4,256,2)
valid=~const[:6].any(-1)
RB=0.2929447685744554; N=256; w=np.hanning(N)
TXAZ=[0,4,7,11,15,2]; TXEL=[0,0,0,0,0,1]; RXAZ=[0,1,2,3,19,20,21,22]
vecs=[];idx=[]
for i,f in enumerate(files):
    if not np.isfinite(tr[i]): continue
    x=np.fromfile(f,dtype=np.int16).astype(np.float32).reshape(64,6,2,4,N,2)
    z=x[...,0]+1j*x[...,1]; z=z-z.mean(0,keepdims=True); z*=valid[None]
    b=int(round(tr[i]/RB))
    bins=np.arange(b-1,b+2)
    k=np.exp(-2j*np.pi*np.outer(bins,np.arange(N))/N)*w   # DFT at 3 bins
    R=np.einsum('ltdrn,bn->ltdrb',z,k).reshape(64,6,8,3)     # [loop,tx,rx8,bin]
    D=np.fft.fft(R*np.hanning(64)[:,None,None,None],axis=0)
    p=(np.abs(D)**2).sum((1,2)); p[0]=0; p[[1,63]]*=0.5
    dl,bb=np.unravel_index(np.argmax(p),p.shape)
    vecs.append(D[dl,:,:,bb]); idx.append(i)
V=np.array(vecs); idx=np.array(idx)          # [n,6,8]
def est(V,cal,sign):
    out=[]
    for v in V:
        v=v*cal if cal is not None else v
        a=np.zeros(64,complex)
        for t in range(5):
            for r in range(8):
                a[TXAZ[t]+RXAZ[r]]+=v[t,r]/ (np.abs(v[t,r])+1e-9)
        A=np.fft.fftshift(np.fft.fft(a,1024)); s=np.fft.fftshift(np.fft.fftfreq(1024))*2
        out.append(np.degrees(np.arcsin(np.clip(sign*s[np.argmax(np.abs(A))],-1,1))))
    return np.array(out)
for cal,cn in [(None,"no calib"),(corr,"calib x"),(np.conj(corr),"calib conj")]:
    for sg in (1,-1):
        e=est(V,cal,sg); t=ta[idx]; ok=np.isfinite(t)
        d=e[ok]-t[ok]
        print(f"{cn:10s} sign{sg:+d}: corr {np.corrcoef(e[ok],t[ok])[0,1]:+.2f}  median|err| {np.median(np.abs(d)):.1f} deg  bias {np.median(d):+.1f}")
