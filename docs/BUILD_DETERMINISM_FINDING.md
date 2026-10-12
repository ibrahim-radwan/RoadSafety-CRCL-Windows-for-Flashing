# Build Determinism — AM273x Cascade Firmware

Established 2026-10-04/05 by experiment. Gate verified and full chain
confirmed 2026-10-05. Supersedes the `.xer5f` hash gate in
`Range_Variants_Build_Spec.md` W2 step 7, and settles the provenance scheme
in §6 of that document.

---

## 0. Summary — the chain, as verified

| stage | determinism | what to use it for |
|---|---|---|
| `.xer5f` | **non-deterministic** — 3–4 images per variant from identical source | nothing. Do not hash it |
| `.rprc` | **deterministic** ✓ | fingerprint of the compiled parameters |
| `.appimage` | **deterministic** ✓ | identifies the artifact written to QSPI |

Everything below is the evidence.

---

## 1. The finding

Six runs of `build_inf_custom.bat` with no source changes produced, per
variant, **3–4 distinct `.xer5f` images** out of 6 builds:

| variant | distinct images / 6 runs | multiplicities |
|---|---|---|
| longrange | 4 | `95FABB7F`×2, `2E5CA317`×2, `A2404726`×1, `EAEC286C`×1 |
| r050m | 3 | `9CB9EAE8`×3, `4A0C23EE`×2, `FEB1E9B5`×1 |
| r075m | 4 | `D4AC5705`×2, `27066A08`×2, `F4D21D59`×1, `CA4939BF`×1 |
| r100m | 3 | `83909606`×3, `35AD6B2B`×2, `F7197E5F`×1 |
| shortrange_calib | 3 | `587223E1`×2, `C74BEB6C`×2, `76D432D6`×2 |
| shortrange | 4 | `E903F5FC`×3, `662B494E`×1, `2EE0BDBD`×1, `9A65145E`×1 |
| verylongrange | 3 | `72CE51B0`×3, `7A7B812A`×2, `5132305E`×1 |

**Not a timestamp.** A build timestamp or counter would give six distinct
hashes per variant, never repeating. Instead each variant draws from a small
pool and the same hash recurs across runs. A finite, repeating outcome set
means the linker lands in one of a few states — symbol or object iteration
order, or alignment padding left uninitialised. File sizes are constant per
variant, so section layout is stable; only byte content inside it moves.

**The drift does not reach the device.** Two different `.xer5f` for r075m —
`27066A08…` and `F4D21D59…` — both converted to the same `.rprc`:

```
965d89a0b5fe16e7c44468acfeedd2d0
```

`elf2rprc` keeps only loadable segments (address + data) and discards symbol
tables, section headers, debug and comment sections. **The loadable image is
bit-identical, so the firmware is deterministic.**

### Why the ELF hash is so unstable

| | bytes | share |
|---|---|---|
| `.xer5f` (full ELF) | 1,174,744 | 100% |
| `.rprc` (loadable only) | 156,264 | **13.3%** |
| discarded by `elf2rprc` | 1,018,480 | **86.7%** |

A megabyte of symbol tables, debug info and section headers for the linker to
be non-deterministic in, against 156 KB of loadable image that never varied.

---

## 2. Consequence: the W2 gate was invalid

The gate in `Range_Variants_Build_Spec.md` W2 step 7 was:

> Hash all `.xer5f`. If any two hash identically the define did not take
> effect.

**That inference does not hold.** If a `-D` define silently failed and two
variants compiled to identical loadable content, their `.xer5f` files would
*still* differ, because the metadata noise differs between any two builds.
Distinct hashes are near-guaranteed regardless of whether the defines
applied. The check passes while the defect it exists to catch is present.

The 2026-10-04 result — "7 variants, 7 distinct hashes, OK: all variants
distinct" — therefore proved only that seven builds ran. It was **not**
evidence that all seven defines took effect.

### The corrected gate

Hash the **`.rprc`**, not the `.xer5f`. It is deterministic and contains only
loadable content, so two variants with the same compiled parameters produce
*identical* `.rprc` hashes — which is the signal wanted.

*(2026-10-12: the `cascade - Copy` path below is archived. The source is now
`firmware/am273x_cascade/`, built through the SDK junction `ti\utils\test\cascade_radar`.
`firmware/am273x_cascade/tools/build_v2_variants.ps1` does this conversion with
uniquely named intermediates; see §7.)*

```powershell
cd C:\ti\mmwave_mcuplus_sdk_04_04_00_01\mcu_plus_sdk_am273x_08_05_00_24\tools\boot
$base = 'C:\...\ti\utils\test\cascade - Copy\am273x'
$node = 'C:\ti\ccs2050\ccs\tools\node\node.exe'

foreach ($v in 'shortrange','shortrange_calib','longrange','verylongrange','r050m','r075m','r100m') {
    & $node '.\out2rprc\elf2rprc.js' "$base\build_${v}_inf\am273x_cascade_mss.xer5f"
    Move-Item -Force am273x_cascade_mss.rprc "$v.rprc"
}
Get-ChildItem *.rprc | ForEach-Object {
    '{0,-20} {1,9:N0} B  {2}' -f $_.BaseName, $_.Length, (Get-FileHash $_ -Algorithm MD5).Hash
}
```

**Pass: seven distinct `.rprc` hashes.** Any two matching means those two
variants carry the same compiled parameters and one `-D` did not apply.

The `Move-Item -Force` also removes the overwrite hazard: `elf2rprc` names its
output from the input basename, and all seven inputs are
`am273x_cascade_mss.xer5f`, so without the rename each conversion clobbers
the last. It also leaves the `.rprc` files uniquely named, which removes the
same hazard from stage 3.

This moves the verification gate from **W2 to W3**, after stage-2 conversion.

---

## 3. Gate result — PASS, 2026-10-05

Seven distinct `.rprc` hashes. All seven `-D` defines took effect.

| variant | `.rprc` size | MD5 |
|---|---|---|
| longrange | 156,264 | `F4963D21C07D7EC4523F638979A66788` |
| r050m | 156,264 | `07327B4C7D5D7CAB6C5C2EB57D6F1CC8` |
| r075m | 156,264 | `965D89A0B5FE16E7C44468ACFEEDD2D0` |
| r100m | 156,264 | `2AA932C5015A831387B5EB3CAB4EDF9A` |
| shortrange | 156,264 | `C30A69DAA87942690E2B9F4DA7D599C0` |
| shortrange_calib | 156,264 | `368533103BF636CCBDE9E0DC788D0B29` |
| verylongrange | 156,264 | `3B3E3FA843A4F9FC20EF76742BD94777` |

**These are the canonical fingerprints of each variant's compiled
parameters.** Because the `.rprc` is deterministic, any future rebuild from
unchanged source must reproduce these exact values. That makes this table a
real regression check — something the `.xer5f` hashes could never provide.

Two details confirming the result is sound rather than merely green:

- **r075m `965D89A0…` is its third occurrence** — both conversions in the
  determinism test, plus this run.
- **All seven are exactly 156,264 B.** Identical size with differing hashes is
  precisely the right signature: only immediate constants differ between
  variants, so code size cannot move, but the constant values do. Any two
  hashes matching at identical size would have meant two variants carrying
  the same parameters.

---

## 4. `.appimage` determinism — CONFIRMED, 2026-10-05

`multicoreImageGen --devID 55` run twice on the same `r075m.rprc` produced
the same output both times:

```
f0e6a73d4c7d35d92e2128305f0b1867
```

So stage 3 adds no non-determinism of its own. The full chain from `.rprc`
onward is reproducible.

### Provenance scheme — settled

Record **both** per variant:

- the **`.rprc`** hash — reproducible fingerprint of the compiled parameters
  (§3). Use it to verify a rebuild matches a known-good build.
- the **`.appimage`** hash — identifies the artifact written to QSPI. Log it
  in the flashing script and in every capture manifest.

`Range_Variants_Build_Spec.md` §6 works as written with the `.xer5f` swapped
for these two. Never record an `.xer5f` hash: the same source yields three or
four of them, so it identifies nothing and verifies nothing.

---

## 5. What this does not change

- The firmware is correct. All seven variants' registers were audited against
  the file and recomputed; both forced identities hold, the ADC window fits
  inside the ramp with 2.4–2.8 µs slack, and every swept band sits inside
  76–81 GHz.
- `cascade_config.h` is ruled out as the cause. Every functional value in the
  four pre-existing variants is byte-for-byte what it was before the comment
  rewrite; only comment text, three new `#elif` branches and the default
  guard changed.
- Non-deterministic builds are common in vendor toolchains and benign here.
  The reason it mattered was that a provenance scheme was about to be built
  on these hashes.

---

## 6. Correction recorded

I claimed, from a single comparison, that shortrange rebuilding to
`2EE0BDBD…` byte-for-byte was "a stronger provenance result than anything in
the logs." It was a coincidence — shortrange produces four distinct images
across six runs and `2EE0BDBD…` appears once. One matching pair read as
reproducibility.

The six-run experiment is what a single comparison could not show, and it
inverted the conclusion: the one variant I called reproducible is among the
least stable of the seven. The genuine reproducibility result is the `.rprc`
table in §3.

### Method note

The pattern worth reusing: when a hash is going to be load-bearing, test what
it actually varies with before building anything on it. Two runs would have
shown non-determinism but not that the outcome set is small and repeating —
which is what ruled out a timestamp and pointed at the linker. Six runs cost
an hour of build time and turned a plausible story into a mechanism.
---

## 7. October 2026: the gate held through the v2 rebuild

The `.rprc` / `.appimage` scheme carried the whole October rebuild without a single false result.

| Date | Check | Result |
|---|---|---|
| 2026-10-10 | Rebuild `CASCADE_CFG_R075M` from the unmodified source | `.rprc` `965d89a0…` and `.appimage` `f0e6a73d…`, **bit-exact with the flashed image**. Proved the SDK source was what the radar ran, before any fix was made |
| 2026-10-10 | Rebuild r075m_v2 twice from clean | identical `.rprc` `c17eaa9b…` / `.appimage` `b4ac5b97…` |
| 2026-10-10 | Rebuild r075m_v2 and r075m_v2_8fps after adding the `_V2` mapping for the other 11 variants to `cascade_config.h` | unchanged: `c17eaa9b…/b4ac5b97…` and `e9a61839…/8f5eb30a…` |
| 2026-10-10 | 11 new v2 images | 11 new distinct `.rprc`; all 20 `.appimage` hashes in the release distinct |
| 2026-10-12 | All 13 v2 images rebuilt from the **repository** through the SDK junction | **13 / 13 bit-exact** with the deployed release |

**`.rprc` sizes changed in v2.** Every v2 `.rprc` is 156,456 B, against 156,264 B for every pre-v2 image. The extra 192 B is the DSS L3 MEMINIT code (two SoC functions and the calls). So the "identical size, different hash" signature of §3 holds within a family, not across the fix.

**A stronger gate than distinct hashes.** `firmware/am273x_cascade/tools/fdiff.py` diffs two images function by function. It masks addresses, branch targets and literal-pool pointers, and keeps every other immediate. Against each base image, every v2 image differed only in:

- the two added MEMINIT calls in `main`;
- the removed HPF 2/2 store;
- for `_8fps`, the frame-period immediate (`0x02FAF080` → `0x017D7840`).

Distinct hashes only show that *something* changed. This shows *what* changed. Output: `testing/firmware_investigation_2026-10/rebuild_all_variants/disassembly_diff_vs_base.txt`.
