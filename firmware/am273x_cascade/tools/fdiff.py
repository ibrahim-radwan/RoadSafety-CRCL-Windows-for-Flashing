"""Function-level semantic diff of two TI ARM ELF images.
Prints the functions whose normalized instruction multiset differs, plus the
added/removed instructions. Address operands are masked; immediates kept."""
import re, subprocess, sys
from collections import Counter
OD=r"C:\ti\ccs2050\ccs\tools\compiler\ti-cgt-armllvm_4.0.4.LTS\bin\tiarmobjdump.exe"
ADDR_HI=re.compile(r"#0x(10[2-2][0-9a-f]|102[0-9a-f]|880[0-9a-f])$")
def funcs(elf):
    out=subprocess.run([OD,"-d","--no-show-raw-insn",elf],capture_output=True,text=True).stdout
    F={};cur=None;body=[]
    for ln in out.splitlines():
        m=re.match(r"^[0-9a-f]{8} <(.+)>:$",ln)
        if m:
            if cur: F[cur]=body
            cur,body=m.group(1),[]; continue
        m=re.match(r"^\s*[0-9a-f]+:\s+(.*)$",ln)
        if m and cur: body.append(m.group(1))
    if cur: F[cur]=body
    return F
def norm(body):
    res=[];lastmovw={}
    for ins in body:
        mw=re.search(r"\.(word|short|byte)\s+0x([0-9a-f]+)",ins)
        if mw:
            val=int(mw.group(2),16)
            if 0x10200000<=val<0x10300000 or 0x88000000<=val<0x88400000: res.append(".word ADDR"); continue
            res.append(f".{mw.group(1)} 0x{val:x}"); continue
        ins=re.sub(r"\s*@.*$","",ins); ins=re.sub(r"<[^>]*>","",ins).strip()
        ins=re.sub(r"\s+"," ",ins)
        op=ins.split(" ")[0]
        if re.match(r"^(b|bl|blx|b\.w|cbz|cbnz|b[a-z]{2}(\.w)?)$",op):
            ins=re.sub(r"0x[0-9a-f]+","T",ins)
        if "[pc" in ins or ", pc" in ins: ins=re.sub(r"#-?0x[0-9a-f]+|#-?\d+","#PC",ins)
        if op=="movw":
            r=ins.split()[1].rstrip(","); lastmovw[r]=len(res)
        if op=="movt":
            r=ins.split()[1].rstrip(",")
            if ADDR_HI.search(ins):
                ins=op+" "+r+", #ADDRHI"
                if r in lastmovw: res[lastmovw[r]]=re.sub(r"#0x[0-9a-f]+","#ADDRLO",res[lastmovw[r]])
        res.append(ins)
    return Counter(res)
a,b=funcs(sys.argv[1]),funcs(sys.argv[2])
only_a=sorted(set(a)-set(b)); only_b=sorted(set(b)-set(a))
print("functions only in base :",only_a)
print("functions only in new  :",only_b)
for f in sorted(set(a)&set(b)):
    na,nb=norm(a[f]),norm(b[f])
    if na!=nb:
        rem=na-nb; add=nb-na
        print(f"  ~ {f}: -{sum(rem.values())} +{sum(add.values())}")
        for k,v in rem.items(): print(f"      - {v}x {k}")
        for k,v in add.items(): print(f"      + {v}x {k}")
