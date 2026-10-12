/*
 *   @file  cascade_config.h
 *
 *   @brief
 *      Selectable radar configuration for the AWR2243-2X-CAS-EVM
 *      (2-chip cascaded radar, 6TX/8RX, 48 virtual channels).
 *
 *      Select ONE configuration mode at build time by defining one of:
 *        CASCADE_CFG_LONGRANGE  (R167.82M)
 *        CASCADE_CFG_SHORTRANGE (R16.78M)
 *        CASCADE_CFG_SHORTRANGE_CALIB (R16.78M)
 *        CASCADE_CFG_VERYLONGRANGE (R142.42M)
 *        CASCADE_CFG_R050M (R50.00M)
 *        CASCADE_CFG_R075M (R75.00M)
 *        CASCADE_CFG_R100M (R100.00M)
 *
 *      This can be done here or via compiler -D flag in the makefile.
 *      If none is defined, CASCADE_CFG_LONGRANGE is selected by default.
 *
 *      Infinite-frame MSS behavior (matches build_*_inf / rlFrameCfg numFrames 0):
 *        Build with CASCADE_INF=1 in mssTest.mak (adds -DCASCADE_INF).
 *      Single-frame test loop: build with default CASCADE_INF=0 (CFG_NUM_FRAMES = 1).
 *
 *  \par
 *  NOTE:
 *      (C) Copyright 2021-2025 Texas Instruments, Inc.
 *
 *  Redistribution and use in source and binary forms, with or without
 *  modification, are permitted provided that the following conditions
 *  are met:
 *
 *    Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 *    Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the
 *    distribution.
 *
 *    Neither the name of Texas Instruments Incorporated nor the names of
 *    its contributors may be used to endorse or promote products derived
 *    from this software without specific prior written permission.
 *
 *  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 *  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 *  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 *  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 *  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 *  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 *  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 *  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 *  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 *  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 *  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#ifndef CASCADE_CONFIG_H
#define CASCADE_CONFIG_H

/* ============================================================
 * Default selection: Long Range if nothing is defined
 * ============================================================ */
#if !defined(CASCADE_CFG_LONGRANGE)        && \
    !defined(CASCADE_CFG_SHORTRANGE)       && \
    !defined(CASCADE_CFG_SHORTRANGE_CALIB) && \
    !defined(CASCADE_CFG_VERYLONGRANGE)    && \
    !defined(CASCADE_CFG_R050M)            && \
    !defined(CASCADE_CFG_R075M)            && \
    !defined(CASCADE_CFG_R100M)
#define CASCADE_CFG_LONGRANGE
#endif

/* ============================================================
 * Common parameters for all configurations
 * AWR2243-2X-CAS-EVM: 2 × AWR2243 + AM2732R
 *   - 6 TX total (3 per device), 8 RX total (4 per device)
 *   - 48 virtual channels in MIMO virtual array
 *   - 6-chirp TDM MIMO pattern across 2 cascade devices
 * ============================================================ */
#define CFG_NUM_ADC_SAMPLES           (256U)
#define CFG_NUM_RX_PER_DEVICE         (4U)
#define CFG_NUM_TX_PER_DEVICE         (3U)
#define CFG_NUM_DEVICES               (2U)
#define CFG_NUM_CHIRPS                (6U)
#define CFG_CHIRP_END_INDEX           (CFG_NUM_CHIRPS - 1U)
#define CFG_BYTES_PER_ADC_SAMPLE      (4U)  /* complex: 2 bytes I + 2 bytes Q */
#define CFG_NUM_PHASE_SHIFT_CHIRPS    (1U)
/* 0 = infinite MSS wait loop (matches *_inf JSON / rlFrameCfg numFrames 0). */
#if defined(CASCADE_INF)
#define CFG_NUM_FRAMES                (0U)
#else
#define CFG_NUM_FRAMES                (1U)
#endif

/* ADC output format: 16-bit complex */
#define CFG_ADC_BITS                  (2U)  /* 0:12bit, 1:14bit, 2:16bit */
#define CFG_ADC_FORMAT                (1U)  /* 0:real, 1:complex, 2:complex with img band */

/* ============================================================
 * Long Range Configuration
 *   Profile: 76 GHz, 256 ADC @ 10 Msps, ramp 31 us, idle 4 us
 *
 *   Sampled BW: 228.7 MHz  (slope x N/fs = 8.9318 x 25.6 us)
 *     -> Range Res: 0.6556 m,  Max Range: 167.82 m
 *   Full ramp BW: 276.9 MHz  (slope x ramp_end) -- NOT the figure that
 *     sets range resolution; only the digitised part of the ramp counts.
 *
 *   T_loop = 6 TX x (idle + ramp) = 210 us
 *     -> Max Velocity: +/-4.6960 m/s,  Velocity Res: 0.1467 m/s
 *
 *   USABLE WINDOW: 23.50 - 167.82 m, NOT 0 - 167.82 m.
 *     The RX high-pass corners impose a minimum range, because beat
 *     frequency f = 2 x slope x R / c:
 *       HPF1 350 kHz -> 5.87 m    HPF2 1.4 MHz -> 23.50 m
 *     This profile is BLIND inside ~23.5 m. On a long-range build that is
 *     normally what you want — the corner suppresses strong near-field
 *     returns that would otherwise consume the dynamic range — but it must
 *     not be read as a processing limitation.
 *
 *   Identity check: max_range = range_res x 256 (the range FFT has 256
 *   bins), and v_max / v_res = 32 (64 Doppler bins, +/- span). Any edit to
 *   this block must keep both true.
 * ============================================================ */
#if defined(CASCADE_CFG_LONGRANGE)

#define CFG_PROFILE_START_FREQ_GHZ        (76U)
#define CFG_PROFILE_IDLE_TIME_VAL         (400U)      /* 4 us  (unit: 10 ns) */
#define CFG_PROFILE_ADC_START_TIME_VAL    (300U)      /* 3 us  (unit: 10 ns) */
#define CFG_PROFILE_RAMP_END_TIME_VAL     (3100U)     /* 31 us — fits 256 samples @ 10 Msps */
#define CFG_PROFILE_FREQ_SLOPE_CONST      (185)       /* 8.9318 MHz/us = 185 x 48.27976 kHz/us */
#define CFG_PROFILE_TX_START_TIME_VAL     (0)         /* 0 us */
#define CFG_PROFILE_SAMPLE_RATE           (10000U)    /* 10 Msps */
#define CFG_PROFILE_HPF1                  (2U)        /* RL_RX_HPF1_350_KHz -> ~5.87 m range floor */
#define CFG_PROFILE_HPF2                  (2U)        /* RL_RX_HPF2_1_4M   -> ~23.50 m range floor */
#define CFG_PROFILE_RX_GAIN              (42U)        /* dB */
#define CFG_FRAME_NUM_LOOPS               (64U)
#define CFG_FRAME_PERIODICITY_MS          (250U)      /* 4 fps — matches original SDK */

/* ============================================================
 * Short Range Configuration  —  the validated baseline
 *   Every session collected 2026-05 to 2026-06 used this profile. The range
 *   and Doppler axes were cross-validated against each other to ~1.3% by the
 *   range-rate/Doppler regression (see Range_Equation_Ledger.md §3).
 *
 *   Profile: 77 GHz, 256 ADC @ 5 Msps, ramp 60 us, idle 5 us, ADC start 6 us
 *
 *   Sampled BW: 2286.5 MHz  (slope x N/fs = 44.6588 x 51.2 us)
 *     -> Range Res: 0.0656 m,  Max Range: 16.78 m
 *   Full ramp BW: 2679.5 MHz  (slope x ramp_end) -- NOT the figure that sets
 *     range resolution; only the digitised part of the ramp contributes.
 *   Swept band 77.000 -> 79.680 GHz; ADC window 77.268 -> 79.554 GHz.
 *
 *   T_loop = 6 TX x (idle + ramp) = 390 us
 *     -> Max Velocity: +/-2.4958 m/s,  Velocity Res: 0.0780 m/s
 *
 *   MINIMUM RANGE is set by the RX high-pass corners, not by geometry:
 *     beat freq f = 2 x slope x R / c, so HPF1 175 kHz -> 0.587 m floor,
 *     HPF2 350 kHz -> 1.175 m floor. Returns inside ~1.2 m are attenuated.
 *     Collected sessions show no detection closer than 1.583 m, consistent
 *     with this rather than with a processing gate.
 *
 *   ADC window 6 + 51.2 = 57.2 us fits inside the 60 us ramp (2.8 us slack).
 *   Beat frequency at max range is 5.000 MHz, exactly fs — by construction.
 *
 *   RX gain is 30 dB here against 42 dB in the long-range profiles. Raising
 *   it does NOT improve detection: the noise floor sits ~56 dB above the ADC
 *   quantisation floor, so the system is receiver-noise limited and rxGain is
 *   IF gain downstream of the LNA. See the ledger §5 before changing it.
 *
 *   Identity check: max_range = range_res x 256 (256 range-FFT bins) and
 *   v_max / v_res = 32 (64 Doppler bins, +/- span). Both hold. Any edit to
 *   this block must keep them true.
 * ============================================================ */
#elif defined(CASCADE_CFG_SHORTRANGE)

#define CFG_PROFILE_START_FREQ_GHZ        (77U)
#define CFG_PROFILE_IDLE_TIME_VAL         (500U)      /* 5 us */
#define CFG_PROFILE_ADC_START_TIME_VAL    (600U)      /* 6 us */
#define CFG_PROFILE_RAMP_END_TIME_VAL     (6000U)     /* 60 us — fits 256 samples @ 5 Msps */
#define CFG_PROFILE_FREQ_SLOPE_CONST      (925)       /* 44.6588 MHz/us = 925 x 48.27976 kHz/us */
#define CFG_PROFILE_TX_START_TIME_VAL     (0)
#define CFG_PROFILE_SAMPLE_RATE           (5000U)     /* 5 Msps */
#define CFG_PROFILE_HPF1                  (0U)        /* RL_RX_HPF1_175_KHz -> ~0.59 m range floor */
#define CFG_PROFILE_HPF2                  (0U)        /* RL_RX_HPF2_350_KHz -> ~1.18 m range floor */
#define CFG_PROFILE_RX_GAIN              (30U)        /* dB — see note above before raising */
#define CFG_FRAME_NUM_LOOPS               (64U)
#define CFG_FRAME_PERIODICITY_MS          (250U)      /* 4 fps — matches original SDK */

/* ============================================================
 * Short Range Calibration Configuration
 *   Same bandwidth as short range with extended idle time
 *   for over-the-air calibration measurement.
 * ============================================================ */
#elif defined(CASCADE_CFG_SHORTRANGE_CALIB)

#define CFG_PROFILE_START_FREQ_GHZ        (77U)
#define CFG_PROFILE_IDLE_TIME_VAL         (10400U)    /* 104 us */
#define CFG_PROFILE_ADC_START_TIME_VAL    (600U)      /* 6 us */
#define CFG_PROFILE_RAMP_END_TIME_VAL     (6000U)     /* 60 us — fits 256 samples @ 5 Msps */
#define CFG_PROFILE_FREQ_SLOPE_CONST      (925)       /* 44.6588 MHz/us = 925 x 48.27976 kHz/us */
#define CFG_PROFILE_TX_START_TIME_VAL     (0)
#define CFG_PROFILE_SAMPLE_RATE           (5000U)
#define CFG_PROFILE_HPF1                  (2U)
#define CFG_PROFILE_HPF2                  (2U)
#define CFG_PROFILE_RX_GAIN              (30U)
#define CFG_FRAME_NUM_LOOPS               (64U)
#define CFG_FRAME_PERIODICITY_MS          (1000U)     /* 1 fps — slow for calibration */

/* ============================================================
 * Very Long Range Configuration
 *   Profile: 76 GHz, 256 ADC @ 5 Msps, ramp 57 us, idle 4 us
 *
 *   Sampled BW: 269.4 MHz  (slope x N/fs = 5.2625 x 51.2 us)
 *     -> Range Res: 0.5563 m,  Max Range: 142.42 m
 *   Full ramp BW: 300.0 MHz  (slope x ramp_end) -- NOT the figure that
 *     sets range resolution; only the digitised part of the ramp counts.
 *   Swept band 76.000 -> 76.300 GHz.
 *
 *   T_loop = 6 TX x (idle + ramp) = 366 us
 *     -> Max Velocity: +/-2.6944 m/s,  Velocity Res: 0.0842 m/s
 *
 *   USABLE WINDOW: 39.88 - 142.42 m, NOT 0 - 142.42 m.
 *     The RX high-pass corners impose a minimum range, because beat
 *     frequency f = 2 x slope x R / c:
 *       HPF1 350 kHz -> 9.97 m    HPF2 1.4 MHz -> 39.88 m
 *     This is the narrowest-slope profile, so it has the HIGHEST floor of
 *     any variant. It is blind inside ~40 m and cannot be exercised or
 *     validated indoors at all.
 *
 *   "Narrower slope for higher SNR at distance" -- true, but not for the
 *     reason it suggests. fs and N are identical to SHORTRANGE (5 Msps,
 *     256 samples), so the ADC dwell is the same 51.2 us, the noise
 *     bandwidth is the same, and point-target SNR is UNCHANGED by the
 *     slope. The real gain is range-cell concentration on an EXTENDED
 *     target: a 0.5 m-deep body spans 7.6 range bins at SHORTRANGE but
 *     0.9 bins here, concentrating its energy by ~8.8 dB per bin. That
 *     buys detection range and costs the multi-point body cloud.
 *
 *   ADC window 3 + 51.2 = 54.2 us fits inside the 57 us ramp (2.8 us slack).
 *
 *   Identity check: max_range = range_res x 256 (256 range-FFT bins) and
 *   v_max / v_res = 32 (64 Doppler bins, +/- span). Both hold. Any edit to
 *   this block must keep them true.
 *
 *   NAMING: this variant does NOT reach further than LONGRANGE. 142.42 m
 *     against 167.82 m. The slope is 1.70x narrower (more range) but fs is
 *     halved (less range), and the fs term wins: 1.70 x 0.5 = 0.85. The name
 *     was chosen from the slope alone. Setting fs to 10000 would give 284.8 m
 *     at 1.113 m resolution and make the name accurate, but nothing requires
 *     that. The 50/75/100 m variants cover the real requirement with finer
 *     resolution and lower HPF floors.
 * ============================================================ */
#elif defined(CASCADE_CFG_VERYLONGRANGE)

#define CFG_PROFILE_START_FREQ_GHZ        (76U)
#define CFG_PROFILE_IDLE_TIME_VAL         (400U)      /* 4 us */
#define CFG_PROFILE_ADC_START_TIME_VAL    (300U)      /* 3 us */
#define CFG_PROFILE_RAMP_END_TIME_VAL     (5700U)     /* 57 us — fits 256 samples @ 5 Msps */
#define CFG_PROFILE_FREQ_SLOPE_CONST      (109)       /* 5.2625 MHz/us = 109 x 48.27976 kHz/us */
#define CFG_PROFILE_TX_START_TIME_VAL     (0)
#define CFG_PROFILE_SAMPLE_RATE           (5000U)     /* 5 Msps */
#define CFG_PROFILE_HPF1                  (2U)        /* RL_RX_HPF1_350_KHz -> ~9.97 m range floor */
#define CFG_PROFILE_HPF2                  (2U)        /* RL_RX_HPF2_1_4M   -> ~39.88 m range floor */
#define CFG_PROFILE_RX_GAIN              (42U)        /* dB */
#define CFG_FRAME_NUM_LOOPS               (64U)
#define CFG_FRAME_PERIODICITY_MS          (250U)      /* 4 fps — matches original SDK */

/* ============================================================
 * R050M / R075M / R100M — the data-collection family
 * ============================================================
 * Added 2026-10-04 for vehicle-mounted collection. All three hold the
 * LONGRANGE timing and change ONLY CFG_PROFILE_FREQ_SLOPE_CONST, because
 * max_range = c * fs / (2 * slope).
 *
 * Why N, loops and chirps are fixed at 256 / 64 / 6:
 *   frame size stays 256 x 384 chirps x 8 RX x 4 B = 3,145,728 B, identical
 *   to every existing variant, so the capture, split and DCA scripts need no
 *   change. Altering any of the three breaks that and is not worth it.
 *
 * Why fs stays at 10000 ksps:
 *   range_res = max_range / 256 REGARDLESS of fs. Since B_sampled =
 *   slope x N/fs and slope = c x fs / (2R), the fs cancels: B_sampled =
 *   c x N / (2R). Raising the sample rate cannot buy resolution back at a
 *   given max range. The only levers are shorter range or more samples.
 *
 * Common to all three:
 *   76 GHz, idle 4 us, ADC start 3 us, ramp 31 us, 10 Msps, 256 ADC,
 *   64 loops, 6 chirps, HPF 2/2, RX gain 42 dB, 250 ms (4 fps).
 *   ADC window 3 + 25.6 = 28.6 us inside the 31 us ramp (2.4 us slack).
 *   T_loop = 6 TX x 35 us = 210 us -> v_max +/-4.6960 m/s, v_res 0.1467 m/s.
 *   Vehicles WILL alias: 4.70 m/s is 16.9 km/h.
 *
 * Slope registers use the correct TI LSB of 48.27976 kHz/us
 * (3.6e6 x 900 / 2^26). NOT 48 kHz/us — that approximation was the defect
 * corrected across this file on 2026-10-03.
 *
 * Identity checks, forced by the FFT sizes and true for all three:
 *   max_range = range_res x 256      v_max / v_res = 32
 * ============================================================ */

/* ============================================================
 * R050M — 50 m
 *   slope 29.9817 MHz/us (621 x 48.27976 kHz/us)
 *   Sampled BW 767.5 MHz -> Range Res 0.1953 m, Max Range 50.00 m
 *   Swept band 76.000 -> 76.929 GHz
 *   USABLE WINDOW 7.00 - 50.00 m  (HPF1 350 kHz -> 1.75 m,
 *                                  HPF2 1.4 MHz -> 7.00 m floor)
 * ============================================================ */
#elif defined(CASCADE_CFG_R050M)

#define CFG_PROFILE_START_FREQ_GHZ        (76U)
#define CFG_PROFILE_IDLE_TIME_VAL         (400U)      /* 4 us */
#define CFG_PROFILE_ADC_START_TIME_VAL    (300U)      /* 3 us */
#define CFG_PROFILE_RAMP_END_TIME_VAL     (3100U)     /* 31 us — fits 256 samples @ 10 Msps */
#define CFG_PROFILE_FREQ_SLOPE_CONST      (621)       /* 29.9817 MHz/us = 621 x 48.27976 kHz/us */
#define CFG_PROFILE_TX_START_TIME_VAL     (0)
#define CFG_PROFILE_SAMPLE_RATE           (10000U)    /* 10 Msps */
#define CFG_PROFILE_HPF1                  (2U)        /* RL_RX_HPF1_350_KHz -> ~1.75 m range floor */
#define CFG_PROFILE_HPF2                  (2U)        /* RL_RX_HPF2_1_4M   -> ~7.00 m range floor */
#define CFG_PROFILE_RX_GAIN              (42U)        /* dB */
#define CFG_FRAME_NUM_LOOPS               (64U)
#define CFG_FRAME_PERIODICITY_MS          (250U)      /* 4 fps */

/* ============================================================
 * R075M — 75 m  (the primary data-collection target)
 *   slope 19.9878 MHz/us (414 x 48.27976 kHz/us)
 *   Sampled BW 511.7 MHz -> Range Res 0.2929 m, Max Range 74.99 m
 *   Swept band 76.000 -> 76.620 GHz
 *   USABLE WINDOW 10.50 - 74.99 m  (HPF1 350 kHz -> 2.62 m,
 *                                   HPF2 1.4 MHz -> 10.50 m floor)
 *   NOTE: blind inside 10.5 m, so this profile cannot be validated at
 *   4-6 m indoors. Cross-check it against SHORTRANGE in their 10.5-16.8 m
 *   overlap. See Range_Variants_Build_Spec.md J2.
 * ============================================================ */
#elif defined(CASCADE_CFG_R075M)

#define CFG_PROFILE_START_FREQ_GHZ        (76U)
#define CFG_PROFILE_IDLE_TIME_VAL         (400U)      /* 4 us */
#define CFG_PROFILE_ADC_START_TIME_VAL    (300U)      /* 3 us */
#define CFG_PROFILE_RAMP_END_TIME_VAL     (3100U)     /* 31 us — fits 256 samples @ 10 Msps */
#define CFG_PROFILE_FREQ_SLOPE_CONST      (414)       /* 19.9878 MHz/us = 414 x 48.27976 kHz/us */
#define CFG_PROFILE_TX_START_TIME_VAL     (0)
#define CFG_PROFILE_SAMPLE_RATE           (10000U)    /* 10 Msps */
#define CFG_PROFILE_HPF1                  (2U)        /* RL_RX_HPF1_350_KHz -> ~2.62 m range floor */
#define CFG_PROFILE_HPF2                  (2U)        /* RL_RX_HPF2_1_4M   -> ~10.50 m range floor */
#define CFG_PROFILE_RX_GAIN              (42U)        /* dB */
#define CFG_FRAME_NUM_LOOPS               (64U)
#define CFG_FRAME_PERIODICITY_MS          (250U)      /* 4 fps */

/* ============================================================
 * R100M — 100 m
 *   slope 14.9667 MHz/us (310 x 48.27976 kHz/us)
 *   Sampled BW 383.1 MHz -> Range Res 0.3912 m, Max Range 100.15 m
 *   Swept band 76.000 -> 76.464 GHz
 *   USABLE WINDOW 14.02 - 100.15 m  (HPF1 350 kHz -> 3.51 m,
 *                                    HPF2 1.4 MHz -> 14.02 m floor)
 *   NOTE: overlaps SHORTRANGE only 14.0-16.8 m, under 3 m of usable
 *   window. Validate this one against R075M, not against SHORTRANGE.
 * ============================================================ */
#elif defined(CASCADE_CFG_R100M)

#define CFG_PROFILE_START_FREQ_GHZ        (76U)
#define CFG_PROFILE_IDLE_TIME_VAL         (400U)      /* 4 us */
#define CFG_PROFILE_ADC_START_TIME_VAL    (300U)      /* 3 us */
#define CFG_PROFILE_RAMP_END_TIME_VAL     (3100U)     /* 31 us — fits 256 samples @ 10 Msps */
#define CFG_PROFILE_FREQ_SLOPE_CONST      (310)       /* 14.9667 MHz/us = 310 x 48.27976 kHz/us */
#define CFG_PROFILE_TX_START_TIME_VAL     (0)
#define CFG_PROFILE_SAMPLE_RATE           (10000U)    /* 10 Msps */
#define CFG_PROFILE_HPF1                  (2U)        /* RL_RX_HPF1_350_KHz -> ~3.51 m range floor */
#define CFG_PROFILE_HPF2                  (2U)        /* RL_RX_HPF2_1_4M   -> ~14.02 m range floor */
#define CFG_PROFILE_RX_GAIN              (42U)        /* dB */
#define CFG_FRAME_NUM_LOOPS               (64U)
#define CFG_FRAME_PERIODICITY_MS          (250U)      /* 4 fps */

#endif /* config selection */

/* ============================================================
 * Derived constants (do not modify)
 * ============================================================ */

/* Frame periodicity in rlFrameCfg_t units (1 LSB = 5 ns) */
#define CFG_FRAME_PERIODICITY_5NS    ((uint32_t)CFG_FRAME_PERIODICITY_MS * 200000U)

#endif /* CASCADE_CONFIG_H */
