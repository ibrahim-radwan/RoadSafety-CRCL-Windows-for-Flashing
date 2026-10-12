import numpy as np
const=np.load("const_mask.npy").reshape(384,2,4,256,2)
valid=~const[:6].any(-1)  # [6,2,4,256]
N=256; w=np.hanning(N); k0=45.3
s=np.exp(2j*np.pi*k0*np.arange(N)/N)
full=np.abs(np.fft.fft(s*w))**2
far=np.r_[0:30,60:256]
print("clean (no mask): far-sidelobe level rel. peak %.1f dB"%(10*np.log10(full[far].mean()/full.max())))
lv=[]
for m in valid.reshape(-1,N):
    p=np.abs(np.fft.fft(s*w*m))**2
    lv.append(p[far].mean()/p.max())
print("with r075m stale-block mask (48 channels): far-sidelobe floor rel. peak, median %.1f dB, worst %.1f dB"%(10*np.log10(np.median(lv)),10*np.log10(max(lv))))
P=np.load("prof_I.npy"); RB=0.29294
for i in [25,29,126,158,207]:
    r=P[i]; b=np.argmax(r[20:120])+20
    print(f"f{i}: strongest return {b*RB:.2f} m; profile floor 30-75 m rel. that peak {10*np.log10(r[102:250].mean()/r[b]):.1f} dB")
