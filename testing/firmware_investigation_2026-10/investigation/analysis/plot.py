import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
OUT=r"C:\Users\RadarDemo\Documents\Jetson_Radar_Sync_Capture_Handover_Firmware_Investigation\investigation\stage3_01_range_time.png"
P=np.load("prof_I.npy"); t,tr,pk=np.load("track.npy").T; RB=0.29294
rng=np.arange(256)*RB; sel=rng<30
db=10*np.log10(P[:,sel]/np.median(P[:,sel],0))
fig,ax=plt.subplots(2,1,figsize=(10,7),sharex=True,gridspec_kw=dict(height_ratios=[3,1.2]))
im=ax[0].imshow(db.T,origin="lower",aspect="auto",cmap="Greys",vmin=0,vmax=20,extent=[t[0]-.125,t[-1]+.125,0,rng[sel][-1]+RB])
ax[0].plot(t,tr,".",ms=4,color="#d55e00",label="LiDAR target range (truth)")
ax[0].set_ylabel("Range (m)"); ax[0].set_ylim(5,30)
ax[0].set_title("stage3_01: radar range-time map (I-first decode, per-frame clutter removal) vs LiDAR truth",fontsize=10,loc="left")
ax[0].legend(loc="upper left",fontsize=8,frameon=False)
cax=ax[0].inset_axes([0.70,0.80,0.25,0.04]); cb=fig.colorbar(im,cax=cax,orientation="horizontal"); cb.set_label("dB over per-bin median",fontsize=8); cb.ax.tick_params(labelsize=7)
for s in ("top","right"): ax[0].spines[s].set_visible(False); ax[1].spines[s].set_visible(False)
e=pk-tr
ax[1].axhline(0,color="#999",lw=.8)
ax[1].plot(t,e,".",ms=4,color="#333")
ax[1].set_ylim(-1.5,1.5); ax[1].set_ylabel("Radar peak − LiDAR (m)"); ax[1].set_xlabel("Time from radar start (s)")
ok=np.isfinite(e); ax[1].text(0.01,0.92,f"median |error| {np.median(np.abs(e[ok]))*100:.1f} cm · {100*np.mean(np.abs(e[ok])<0.6):.0f}% of {ok.sum()} frames within 0.6 m (2 bins)",transform=ax[1].transAxes,fontsize=8,va="top")
ax[1].grid(axis="y",color="#eee")
plt.tight_layout(); plt.savefig(OUT,dpi=130); print(OUT)
