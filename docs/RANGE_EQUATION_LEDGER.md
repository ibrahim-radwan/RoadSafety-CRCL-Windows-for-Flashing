# Range Equation Ledger — AWR2243 Cascade

Updated 2026-10-02 (third revision) after reading the May corner-reflector
diagnostic. Supersedes earlier versions.

> **Status 2026-10-12.** The equations below are unchanged and still hold. The October firmware investigation (`testing/firmware_investigation_2026-10/`) settled five items here:
> - **I/Q order = I first.** This is now proven three ways: the §3 regression; the firmware (`iqSwapSel = 0`, `main_mss.c`); and a decode against LiDAR ground truth (median range error 7.5 cm; Q-first lands in the mirrored half). Every released `.cfg` now says `adcbufCfg -1 0 0 1 1`.
> - **Frame period 250 ms** is in every released `.cfg` (`frameCfg 0 5 64 0 250 1 0`). The 9-token form (§6) is retired.
> - **`cascade_config.h` is in the repository** (`firmware/am273x_cascade/am273x/`) and is the single source (§6 and §10 items 14 and 11–12).
> - **HPF floors:** HPF1 register 2 is 350 kHz. All v2 images use HPF 0/0 (`docs/RANGE_VARIANTS_BUILD_SPEC.md` §3b addendum).
> - **Calibration (§6, §10 item 9) is still open, and now more pressing.** The 76 GHz set came from an HPF 2/2 profile, and every image now runs 0/0. Recalibrate with `r017m_calib_v2` (77 GHz) and a 76 GHz v2 image.
>
> Data recorded on QSPI-booted pre-v2 images is ~50% stale words, which is unrelated to the equations here. The May–June CCS-loaded sessions that §3 used are not affected.

---

## 1. Where we are

**The ask:** a firmware variant with ~75 m max range, because the LONGRANGE
build "says 150 m" and 150 m is not reliable.

**What happened:** the 150 m came from a wrong comment. Chasing which
equations were trustworthy found a slope-conversion defect, exposed several
provenance gaps, produced the first empirical validation of the pipeline's
physical scales from existing data, and explained why an earlier attempt at
exactly this validation had failed.

**Current state:** the equations are settled. One defect confirmed, small and
systematic. Range and Doppler axes cross-validated. Angle remains
unvalidated and is now the weakest link.

---

## 2. The defect — CONFIRMED

All three `.cfg` files carry the slope in engineering units computed with
**48 kHz/µs** per LSB. TI documents **48.279 kHz/µs** for 76–81 GHz parts.

| variant | `.cfg` slope | register | reg × 48.279 | cfg error | max R believed | actual |
|---|---|---|---|---|---|---|
| SHORTRANGE | 44.41 | 925 | 44.6588 | −0.56% | 16.88 m | **16.78 m** |
| LONGRANGE | 8.883 | 185 | 8.9318 | −0.55% | 168.75 m | **167.82 m** |
| VERYLONGRANGE | 5.23 | 109 | 5.2625 | −0.62% | 143.30 m | **142.42 m** |

Evidence: `profileCfg 0 77 5 6 60 0 0 44.41 0 256 5000 0 0 30` and siblings;
`radar_config.py:605` reads `prof[7]`, with `_tok` returning tokens after the
command word.

**Every range reported in this project is ~0.58% long.** Uniform, so no
conclusion about sparsity, clustering or gating changes. Affects reported
distances and the new variant's arithmetic.

The Doppler axis is **not** affected — it depends on λ, `n_tx` and
`idle + ramp`, none of which involve the chirp slope.

### Corrected values

| variant | slope MHz/µs | range res | max range | T_loop | v_max | v_res |
|---|---|---|---|---|---|---|
| SHORTRANGE | 44.6588 | 0.0656 m | 16.78 m | 390 µs | 2.496 | 0.0780 |
| LONGRANGE | 8.9318 | 0.6556 m | 167.82 m | 210 µs | 4.696 | 0.1467 |
| VERYLONGRANGE | 5.2625 | 0.5563 m | 142.42 m | 366 µs | 2.694 | 0.0842 |

---

## 3. Empirical cross-validation — the most important result here

A moving target's range rate and its Doppler measure the same physical
quantity through **two disjoint parameter sets**: `dR/dt` depends on (chirp
slope, `fs`, c); Doppler depends on (λ, `n_tx`, `idle + ramp`). They share no
parameters. Regressing one on the other validates both, with no ground truth.

Run on `points.csv` (320 populated frames, 4 fps). Range rate by
least-squares fit over a sliding window; Doppler by the median over the same
window.

| estimator | window | n | sign agreement | r | slope |
|---|---|---|---|---|---|
| power-weighted | 12 (3.0 s) | 155 | 98.7% | **+0.981** | **+0.987** |
| strongest point | 12 (3.0 s) | 151 | 99.3% | +0.973 | +0.963 |
| median | 12 (3.0 s) | 150 | 99.3% | +0.969 | +0.857 |
| power-weighted | 8 (2.0 s) | 204 | 96.6% | +0.943 | +0.929 |
| power-weighted | 4 (1.0 s) | 238 | 92.4% | +0.729 | +0.560 |

Short windows degrade because the centroid jitters at ~2 points/frame; the
3-second window suppresses that. Results converge on slope ≈ 1.

**Establishes:**

- **I/Q order is correct.** Swapped I/Q conjugates the signal and inverts the
  Doppler sign → slope ≈ −1, ~35% sign agreement. Measured +0.987, 98.7%.
- **`n_tx = 6`, empirically.** `v_max = λ/(4·n_tx·(idle+ramp))`, so assuming
  6 when the truth is 3 would halve every velocity → slope ≈ 0.5. Measured
  0.987. **This was Test B; it is done, from existing data.**
- **Range and Doppler agree to ~1.3%**, independently derived.

**Does not establish.** The regression gives the *ratio* of the two scale
factors, not either absolutely. A common error would cancel — implausible
with no shared parameters, but worth stating. Precision ~1–3%, so it cannot
resolve the 0.58% defect: predicted ratio with the defect present is 0.9942,
measured 0.987 ± ~0.02. Consistent, not confirmatory.

---

## 4. Equation ledger

### Confirmed

| Equation | Basis |
|---|---|
| `max_range = range_res × N_adc` | Forced by the FFT — 256 complex samples → 256 bins |
| `v_res = 2·v_max / N_loops` | Forced by the 64-bin Doppler FFT |
| `frame_bytes = N·loops·ch·4 = 3,145,728` | Measured against DCA1000 byte counts |
| `B_sampled = slope × N_adc/fs` — **not** `slope × ramp_end` | TI applications engineer, E2E |
| `range_res = c/(2·B_sampled)` | Standard FMCW, consistent with the forced identities |
| `max_range = c·fs/(2·slope)` | Follows from the above; full `fs` because sampling is complex |
| `T_loop = 6 × (idle + ramp)`, `n_tx = 6` | Chirp table, §3 regression, **and** the capture tool's explicit chirp→TX map |
| I/Q order = I first | §3 regression; `radar_reader.py:155` on DCA1000 repacking |
| Register LSBs: slope 48.279 kHz/µs · ramp/idle/adcStart 10 ns · fs 1 ksps | TI `rlProfileCfg_t` |

The chirp→TX map, printed by `capture/test.py`, is a third independent
confirmation of `n_tx = 6`:

```
chirp 0 -> Dev0 TX1 (global TX1, txEnable=1)   chirp 3 -> Dev1 TX1 (global TX4, txEnable=1)
chirp 1 -> Dev0 TX2 (global TX2, txEnable=2)   chirp 4 -> Dev1 TX2 (global TX5, txEnable=2)
chirp 2 -> Dev0 TX3 (global TX3, txEnable=4)   chirp 5 -> Dev1 TX3 (global TX6, txEnable=4)
Linear chirp index: loop*6 + chirp_in_loop (0 .. 383)
```

### Still open

| Item | Status | Impact if wrong |
|---|---|---|
| **Azimuth axis** `sin_v = linspace(-1,1,N_az)` | Assumes uniform 0.5λ spacing; the code's own comments (lines 217, 231) acknowledge the array is **non-uniform**. §3 says nothing about angle. **Now the weakest link** | All azimuth angles, hence all x |
| Elevation spacing `_D_EL = 0.8` λ | Provenance unknown, never calibrated (open Stage 4.5) | All z values scale |
| Absolute range scale | Bounded to ~1–3% by §3. Not validated against a tape measure; the 0.58% defect sits below §3's resolving power | Reported distances only |
| λ from **start** frequency | Code uses `C/(start_freq·1e9)`. ADC-window centre differs −1.80% (short), −0.19% (long). Note `adcStartTime` (`prof[3]`) is **never read** by the parser | Doppler ~2% high |

### Why the header comments fail

`max_range = range_res × N` is forced. The comments violate it in
inconsistent directions, so no single convention explains them:

| variant | comment res | × 256 | comment max | error |
|---|---|---|---|---|
| LONGRANGE | 0.54 m | 138.2 | 192 m | −28.0% |
| SHORTRANGE | 0.056 m | 14.3 | 19.2 m | −25.3% |
| VERYLONGRANGE | 0.87 m | 222.7 | 151 m | +47.5% |

Velocity fails the same way: `v_max/v_res` must be 32; the comments give
128.0, 127.9, 128.0 — exactly 4× out. VERYLONGRANGE's stated "BW ≈ 172 MHz"
also contradicts its own registers (`109 × 5700` = 298 MHz).

---

## 5. Why the May reflector test produced nothing — and the redesign

`testing\live_capture_validation\01_indoor_empty_scene_live_capture\logs\20260516_005114_s01_debug_e5_corner_reflector_diagnostic.txt` is a clean,
well-instrumented 30-frame capture. Every frame reports **0 cloud pts,
0 CFAR**. The reflector was never detected.

**Root cause, from the log's own header (line 209):**

```
Filters : clutter=ON  zeroDC=±2  sidelobes=ON
```

A corner reflector is static, so it sits at zero Doppler. MTI clutter removal
subtracts the across-chirp mean and the zero-DC notch then zeroes bins ±2 of
DC. **The reflector was removed by the filters designed to remove static
clutter.** This is not a sensitivity failure — the pipeline architecturally
cannot see a stationary target. Correct behaviour for a people-tracking
system; fatal for a static calibration target.

**Test A, redesigned.** Any range validation must give the reference target
non-zero Doppler, or disable the filters:

1. **Preferred:** re-run the May capture through `main.py` with clutter
   removal and the zero-DC notch disabled. The frames may still exist — this
   costs nothing but a re-process, and the reflector distance would need to
   be recovered from notes.
2. Otherwise: reflector on a slider or trolley, moved slowly through the
   measured distance; range and Doppler both validate in one run.
3. Or: reflector hand-oscillated at a tape-measured distance — small motion
   gives it Doppler while range stays fixed.

Predicted result either way: reported range should read **1.006×** true if
the LSB defect is the only scale error.

### A tempting fix that does not work

The same log shows ADC peak 1056 of 32767 — **3.2% of full scale, ~30 dB of
unused headroom** — while SHORTRANGE uses `rxGain = 30 dB` against 42 dB for
the other two variants. Raising the gain looks like an obvious way to attack
the detection sparsity that has limited every result in this project.

It is not. The measured noise floor is 174.9 LSB rms; int16 quantisation
noise is 0.289 LSB rms. The noise floor sits **55.6 dB above** the
quantisation floor, so the system is thermal/receiver-noise limited, not ADC
limited. `rxGain` is IF/baseband gain, downstream of the LNA and mixer that
set the noise figure, so raising it scales signal and noise together for
**zero SNR change**. The headroom is clipping margin, not sensitivity margin.
Ruled out — recorded here so nobody tries it.

**Where the sparsity limit actually sits:** the scene spans 41–58 dB (17 dB)
against a CFAR margin of 10 dB, so a detection must clear 10 of the 17 dB
available. That is a threshold choice, not an instrumentation limit.
`cfar_margin_3.txt` and `cfar_margin_5.txt` already exist — the sweep was
run. Those are the files to revisit.

### A real performance bug in the processing loop

Every frame writes a full data cube outside the project:

```
[SAVE] arrDREA (256, 64, 256) → C:\ti\mmwave_studio_03_00_00_14\mmWaveStudio\PostProc\drea.npy
```

4,194,304 elements — **33.6 MB per frame as complex64, 134 MB/s at 4 fps**,
overwritten each time, to a path in the mmWave Studio install. This is a
debug artifact left enabled. It should be behind a flag and default off, and
it is a candidate explanation for part of the live-path latency.

---

## 6. Provenance — mostly resolved

**Firmware identified.** All six dated logs carrying a loader line name the
same image:

```
Loading Cortex_R5_0: C:\Users\RadarDemo\Documents\cascaded_radar_win_dev\config\build_shortrange_inf\am273x_cascade_mss.xer5f
```

Spanning 2026-05-14 to 2026-06-04. The collected sessions are **SHORTRANGE**,
consistent with the measured 16.8 m / 6.60 cm / ±2.498 m/s and with
`points.csv` topping out at 14.25 m.

**Post-QSPI sessions have no loader line.** Autonomous boot removes the load
step, so nothing records which image is in flash. The QSPI write operation
needs to log the source `.xer5f` path.

**A third parameter source exists.** `capture/test.py` reports
`Config : cascade_csirx.h (header)` and derives frame geometry from it —
"From firmware header: 8 RX x 256 samp x 384 chirps x 4 B". So capture
geometry comes from a header, not from the `.cfg`. That makes three sources
of truth: `cascade_config.h` (firmware, not in repo), `cascade_csirx.h`
(capture geometry), and the `.cfg` files (processing). All three currently
agree, but nothing enforces it.

**No firmware-to-pipeline drift.** Every timing field in all three `.cfg`
matches `cascade_config.h` exactly once the 10 ns LSB is applied. The `.cfg`
files are faithful transcriptions. The only error is the slope conversion,
present in both sources, which is why nothing caught it.

**Calibration shared between two variants.** The `antennaCalibParams1–3`
lines are byte-identical between `cascade_longrange.cfg` and
`cascade_verylongrange.cfg`; `cascade_shortrange.cfg` differs. Both shared
variants start at 76 GHz and shortrange at 77 GHz, so keying calibration to
start frequency is defensible — but the evidence cannot distinguish that from
copy-paste, and the two share nothing else (slopes differ 1.7×, sample rates
2×, ramp times 1.8×). **Open:** are those coefficients real measurements or
placeholders? Needs the numbers, not hashes.

**Still unaddressed** *(resolved 2026-10-12: `cascade_config.h` and the full
firmware source are in `firmware/am273x_cascade/`; images are identified by
`.rprc` / `.appimage` md5 in `firmware_map.json`)*. `cascade_config.h` is not in the repository. All three
`.xer5f` are named `am273x_cascade_mss.xer5f`, distinguished only by build
directory; two have identical size, so size cannot identify a variant.

**`frameCfg` has nine tokens** where the standard form has seven. The parser
reads only `frm[0..2]`. `frm[3]=0` is consistent with infinite frames
(`CASCADE_INF`), but no reading of the rest yields
`CFG_FRAME_PERIODICITY_MS = 250`. Frame periodicity is not recorded anywhere
the pipeline reads it; 4 fps is measured and matches the header.

---

## 7. A latent bug worth fixing

Two different functions share the name `apply_raw_iq_order_override`:
`radar_config.py:797` on `RadarConfig`, `config.py:340` on
`CascadeFrameGeometry`. Seventeen call sites between them.

The `.cfg` value is dead in practice: `adcbufCfg -1 0 1 0 1` sets
`iq_swap = True`, but `main.py:63` and `live_capture.py:147` both default
`--raw-iq-order` to `i-first`, forcing it False. That default is *correct*,
and §3 confirms it. But **`config.py:275` initialises capture geometry with
`iq_swap = False` without ever reading the `adcbufCfg` swap field**, so its
`"cfg"` mode returns False while claiming to preserve the parsed value.
Harmless today; a trap the moment the hardware setting changes.

---

## 8. Open measurements

**Test A — range scale.** See §5 for why the May attempt failed and how to
redesign it. Priority remains moderate: §3 bounds the error at ~1–3%, so this
is about tightening to <0.5%, not about discovering whether the pipeline
works.

**Test C — angle scale. Now the highest-value measurement.** §3 validates
range and Doppler but says nothing about azimuth or elevation, and the
azimuth axis rests on a uniform-array assumption the code itself flags as
false. A reflector at a known bearing, or the camera-synced sessions used
quantitatively rather than visually.

**~~Test B — Doppler scale~~ — done, §3.**

**Free improvement:** `capture_d455_v2.py:146` enables only
`rs.stream.color`. Enabling depth gives per-frame independent range *and*
cross-range on every future session at no cost — which would make Test C
nearly free.

**Possible §3 analogue for angle:** compare a target's cross-range rate
(`dx/dt`, from the azimuth axis) against its tangential velocity inferred
from range and Doppler geometry. If a disjoint-parameter pair can be
constructed, angle could be validated the same way, without any new
collection.

---

## 9. The 75 m variant

With the corrected LSB, `fs = 10000` ksps and `ramp_end = 3100`:

| target | `freqSlopeConst` | slope MHz/µs | actual max | range res |
|---|---|---|---|---|
| 70 m | 444 | 21.4362 | 69.93 m | 0.273 m |
| **75 m** | **414** | **19.9878** | **74.99 m** | **0.293 m** |
| 80 m | 388 | 18.7325 | 80.02 m | 0.313 m |

Constraints checked for 75 m:
- `ramp_end` 31 µs must hold `adc_start` 3 µs + 25.6 µs = **28.6 µs** → fits
- ADC-window sweep 511.7 MHz; full ramp 620 MHz → 76.000–76.620 GHz, in band

With the file's incorrect 48 kHz/µs this would be 416 — the defect in
miniature.

Still to hand-write: the matching `.cfg`. Nothing generates it. Its slope
field must read **19.988**.

**No longer blocked on measurement.** §3 validates the range axis against an
independent axis to ~1–3%, adequate for a 75 m specification. Note the
variant is for long-range *detection*, where the filters that defeated the
May reflector test are the right behaviour for moving targets — but it also
means a static target at 75 m will not appear, which is worth stating to the
end user explicitly.

---

## 10. Action list

1. ~~Confirm the 0.58% in the active `.cfg`~~ — **done, all three**
2. ~~Identify which firmware produced the sessions~~ — **done, shortrange_inf**
3. ~~Resolve the I/Q order conflict~~ — **done, `i-first` correct and confirmed**
4. ~~Test B, Doppler scale~~ — **done, §3**
5. ~~Read the May reflector log~~ — **done; test failed, see §5**
6. Check whether the May reflector frames still exist; if so re-process with
   `clutter=OFF`, `zeroDC=0` and recover the reflector distance from notes
7. Gate the `drea.npy` write behind a flag, default off — 134 MB/s in the loop
8. Revisit `cfar_margin_3.txt` / `cfar_margin_5.txt` — the real sparsity lever
9. Get the actual long/verylong calibration coefficients — real or placeholder?
   **Still open (2026-10-12)**, and now also needed because every image runs HPF
   0/0 while the 76 GHz set came from an HPF 2/2 profile. Recalibrate.
10. Fix `config.py:275` — read `adcbufCfg` field 2, or delete the `"cfg"` mode.
    *Windows copy frozen; the released `.cfg` files now carry SampleSwap 0, so the
    Jetson's `radar_config.py`, which reads it, decodes I-first correctly.*
11. ~~Correct the LSB in `cascade_config.h` and all `.cfg` files~~ — **done**
12. ~~Rewrite the four variant comments from the registers~~ — **done**
13. ~~Log the source `.xer5f` path when writing QSPI~~ — **done differently:**
    `flash_variant.sh` on the Jetson checks the `.appimage` md5 against the map
    and writes `~/.radar_flashed`
14. ~~Bring `cascade_config.h` and `cascade_csirx.h` into the repo; record which
    `.xer5f` is which~~ — **done 2026-10-12**: `firmware/am273x_cascade/` (single
    source, SDK junction); identity by `.rprc`/`.appimage` md5
15. Enable the D455 depth stream
16. Test C — angle scale
17. Add `CASCADE_CFG_MIDRANGE` + `build_midrange_inf`, hand-write its `.cfg`

### Parked, not forgotten

- Stage 4.5 elevation calibration — same root cause as `_D_EL = 0.8`
- Azimuth non-uniform array correction — promoted by §4; Test C addresses it
- Stage 3.4 per-subject viewer (deferred: multi-subject resolves in 2% of frames)
- L-2 GPU transfer consolidation
- Stage 4.3 cadence (blocked on ground truth)
- Stage 5 hardening; remote triggering service
- `DATA_COLLECTION_GUIDE.md`: steps 1–2 obsolete after QSPI boot; add SOP jumper

---

## 11. Note on method

My first pass claimed the equations were verified because the pipeline
reports 16.8 m / 6.60 cm / 2.498 m/s. That was circular —
`radar_config.py:490` computes those with the formula under test.

Two patterns from this thread worth reusing:

**Disjoint-parameter regression (§3).** Find two quantities the pipeline
derives from parameter sets that share nothing, which physics requires to be
equal, and regress one on the other. No ground truth, no new collection, and
the result is quantitative rather than a plausibility check.

**Check whether a fix is exploitable before recommending it (§5).** The 30 dB
of ADC headroom looked like a direct attack on the sparsity that has
constrained every result here. Two lines of arithmetic showed the system is
noise-limited, not quantisation-limited, and the gain change would do
nothing. The attractive inference and the correct one pointed opposite ways.

## 12. Refrences
https://e2e.ti.com/support/sensors-group/sensors/f/sensors-forum/680540/iwr1642-constant-48279762268-06641-in-range-resolution-formula 
https://e2e.ti.com/support/sensors-group/sensors/f/sensors-forum/947483/iwr6843aop-how-to-calculate-bandwidth-chirp-from-configuration 
https://astroa.net/fmcw-RADAR/mmwave_sdk/packages/ti/control/mmwavelink/docs/doxygen/html/structrl_profile_cfg__t.html 
https://e2e.ti.com/support/sensors-group/sensors/f/sensors-forum/947483/iwr6843aop-how-to-calculate-bandwidth-chirp-from-configuration 
https://dev.ti.com/gallery/view/mmwave/mmWaveSensingEstimator/ver/2.5.1/ 
