/*
 *   @file  cascade_config.h
 *
 *   @brief
 *      Selectable radar configuration for the AWR2243-2X-CAS-EVM
 *      (2-chip cascaded radar, 6TX/8RX, 48 virtual channels).
 *
 *      Select ONE configuration mode at build time by defining one of:
 *        CASCADE_CFG_LONGRANGE
 *        CASCADE_CFG_SHORTRANGE
 *        CASCADE_CFG_SHORTRANGE_CALIB
 *        CASCADE_CFG_VERYLONGRANGE
 *
 *      This can be done here or via compiler -D flag in the makefile.
 *      If none is defined, CASCADE_CFG_LONGRANGE is selected by default.
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
    !defined(CASCADE_CFG_VERYLONGRANGE)
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
#define CFG_NUM_FRAMES                (1U)

/* ADC output format: 16-bit complex */
#define CFG_ADC_BITS                  (2U)  /* 0:12bit, 1:14bit, 2:16bit */
#define CFG_ADC_FORMAT                (1U)  /* 0:real, 1:complex, 2:complex with img band */

/* ============================================================
 * Long Range Configuration
 *   Profile: 76 GHz, 256 ADC @ 10 Msps, ramp 31 us
 *   BW ≈ 275 MHz → Range Res: 0.54 m, Max Range: 192 m
 *   Max Velocity: 19.78 m/s, Velocity Resolution: 0.1545 m/s
 * ============================================================ */
#if defined(CASCADE_CFG_LONGRANGE)

#define CFG_PROFILE_START_FREQ_GHZ        (76U)
#define CFG_PROFILE_IDLE_TIME_VAL         (400U)      /* 4 us  (unit: 10 ns) */
#define CFG_PROFILE_ADC_START_TIME_VAL    (300U)      /* 3 us  (unit: 10 ns) */
#define CFG_PROFILE_RAMP_END_TIME_VAL     (3100U)     /* 31 us — fits 256 samples @ 10 Msps */
#define CFG_PROFILE_FREQ_SLOPE_CONST      (185)       /* 8.883 MHz/us ≈ 8883/48 */
#define CFG_PROFILE_TX_START_TIME_VAL     (0)         /* 0 us */
#define CFG_PROFILE_SAMPLE_RATE           (10000U)    /* 10 Msps */
#define CFG_PROFILE_HPF1                  (2U)        /* RL_RX_HPF1_350_KHz */
#define CFG_PROFILE_HPF2                  (2U)        /* RL_RX_HPF2_1_4M */
#define CFG_PROFILE_RX_GAIN              (42U)        /* dB */
#define CFG_FRAME_NUM_LOOPS               (64U)
#define CFG_FRAME_PERIODICITY_MS          (250U)      /* 4 fps — matches original SDK */

/* ============================================================
 * Short Range Configuration
 *   Profile: 77 GHz, 256 ADC @ 5 Msps, ramp 60 us
 *   BW ≈ 2665 MHz → Range Res: 0.056 m, Max Range: 19.2 m
 *   Max Velocity: 10.09 m/s, Velocity Resolution: 0.0789 m/s
 * ============================================================ */
#elif defined(CASCADE_CFG_SHORTRANGE)

#define CFG_PROFILE_START_FREQ_GHZ        (77U)
#define CFG_PROFILE_IDLE_TIME_VAL         (500U)      /* 5 us */
#define CFG_PROFILE_ADC_START_TIME_VAL    (600U)      /* 6 us */
#define CFG_PROFILE_RAMP_END_TIME_VAL     (6000U)     /* 60 us — fits 256 samples @ 5 Msps */
#define CFG_PROFILE_FREQ_SLOPE_CONST      (925)       /* 44.41 MHz/us ≈ 44410/48 */
#define CFG_PROFILE_TX_START_TIME_VAL     (0)
#define CFG_PROFILE_SAMPLE_RATE           (5000U)     /* 5 Msps */
#define CFG_PROFILE_HPF1                  (0U)        /* RL_RX_HPF1_175_KHz */
#define CFG_PROFILE_HPF2                  (0U)        /* RL_RX_HPF2_350_KHz */
#define CFG_PROFILE_RX_GAIN              (30U)
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
#define CFG_PROFILE_FREQ_SLOPE_CONST      (925)       /* 44.41 MHz/us */
#define CFG_PROFILE_TX_START_TIME_VAL     (0)
#define CFG_PROFILE_SAMPLE_RATE           (5000U)
#define CFG_PROFILE_HPF1                  (2U)
#define CFG_PROFILE_HPF2                  (2U)
#define CFG_PROFILE_RX_GAIN              (30U)
#define CFG_FRAME_NUM_LOOPS               (64U)
#define CFG_FRAME_PERIODICITY_MS          (1000U)     /* 1 fps — slow for calibration */

/* ============================================================
 * Very Long Range Configuration
 *   Profile: 76 GHz, BW ≈ 172 MHz, 192 ADC samples
 *   Narrower slope for higher SNR at distance.
 *   Max Range: 151 m, Range Resolution: 0.87 m
 *   Max Velocity: 19.48 m/s, Velocity Resolution: 0.1522 m/s
 * ============================================================ */
#elif defined(CASCADE_CFG_VERYLONGRANGE)

#define CFG_PROFILE_START_FREQ_GHZ        (76U)
#define CFG_PROFILE_IDLE_TIME_VAL         (400U)      /* 4 us */
#define CFG_PROFILE_ADC_START_TIME_VAL    (300U)      /* 3 us */
#define CFG_PROFILE_RAMP_END_TIME_VAL     (5700U)     /* 57 us — fits 256 samples @ 5 Msps */
#define CFG_PROFILE_FREQ_SLOPE_CONST      (109)       /* 5.23 MHz/us ≈ 5230/48 */
#define CFG_PROFILE_TX_START_TIME_VAL     (0)
#define CFG_PROFILE_SAMPLE_RATE           (5000U)     /* 5 Msps */
#define CFG_PROFILE_HPF1                  (2U)
#define CFG_PROFILE_HPF2                  (2U)
#define CFG_PROFILE_RX_GAIN              (42U)
#define CFG_FRAME_NUM_LOOPS               (64U)
#define CFG_FRAME_PERIODICITY_MS          (250U)      /* 4 fps — matches original SDK */

#endif /* config selection */

/* ============================================================
 * Derived constants (do not modify)
 * ============================================================ */

/* Frame periodicity in rlFrameCfg_t units (1 LSB = 5 ns) */
#define CFG_FRAME_PERIODICITY_5NS    ((uint32_t)CFG_FRAME_PERIODICITY_MS * 200000U)

#endif /* CASCADE_CONFIG_H */
