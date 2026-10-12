import numpy as np, csv
H=r"C:\Users\RadarDemo\Documents\Jetson_Radar_Sync_Capture_Handover_Firmware_Investigation\sessions\stage3_01"
RB=0.2929447685744554
rows=list(csv.DictReader(open(H+r"\sync\lidar_target_truth.csv")))
t=np.array([float(r["t_from_radar_start_s"]) for r in rows])
tr=np.array([float(r["target_range_m"]) if r["target_range_m"] else np.nan for r in rows])
ph=[r["phase"] for r in rows]
print("phases",sorted(set(ph)),"known",np.isfinite(tr).sum())
for name in ["prof_I.npy","prof_Q.npy"]:
    P=np.load(name)
    if "Q" in name: pass
    rng=np.arange(256)*RB
    # search 8..20 m on positive half
    sel=(rng>8)&(rng<20)
    pk=rng[sel][np.argmax(P[:,sel],axis=1)]
    # parabolic refinement
    err=pk-tr; ok=np.isfinite(err)
    print(name,"peak 8-20 m: median|err| %.3f m, within 0.6 m: %.1f%%, corr %.3f"%(np.nanmedian(np.abs(err)),100*np.mean(np.abs(err[ok])<0.6),np.corrcoef(pk[ok],tr[ok])[0,1]))
    # negative half mirror for Q-first
    seln=np.zeros(256,bool); idx=np.arange(256); m=(idx>128); rr=(256-idx)*RB; seln=m&(rr>8)&(rr<20)
    pkn=rr[seln][np.argmax(P[:,seln],axis=1)]; e2=pkn-tr
    print(name,"  mirrored half: median|err| %.3f, within 0.6 m %.1f%%"%(np.nanmedian(np.abs(e2)),100*np.mean(np.abs(e2[ok])<0.6)))
P=np.load("prof_I.npy"); rng=np.arange(256)*RB; sel=(rng>8)&(rng<20)
# refined peak
pkb=np.argmax(np.where(sel,P,0),axis=1)
y0,y1,y2=[np.log(P[np.arange(len(P)),pkb+d]) for d in (-1,0,1)]
pkr=(pkb+0.5*(y0-y2)/(y0-2*y1+y2))*RB
e=pkr-tr; ok=np.isfinite(e)
print("refined: bias %.3f m, median|err| %.3f, rms %.3f, p90 %.3f"%(np.nanmean(e),np.nanmedian(np.abs(e)),np.sqrt(np.nanmean(e**2)),np.nanpercentile(np.abs(e),90)))
for a,b in [(0,30),(30,50),(50,61)]:
    s=(t>=a)&(t<b)&ok
    print(f"  {a}-{b}s: n={s.sum()} truth {np.nanmin(tr[s]):.2f}-{np.nanmax(tr[s]):.2f} radar {pkr[s].min():.2f}-{pkr[s].max():.2f} med|err| {np.median(np.abs(e[s])):.3f}")
np.save("track.npy",np.c_[t,tr,pkr])
# Streaks: broadband power per frame
bb=P[:,5:250].sum(1); med=np.median(bb)
z=bb/med
print("broadband/median top frames:",[(int(i),round(t[i],2),round(z[i],1)) for i in np.argsort(z)[::-1][:10]])
