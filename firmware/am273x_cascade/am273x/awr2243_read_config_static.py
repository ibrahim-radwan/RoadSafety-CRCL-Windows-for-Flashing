"""
Static AWR2243_read_config for AM273x cascade (cascade_config.h: shortrange, 250 ms frame).

config_file_name is ignored (kept for API compatibility). ADC_PARAMS['rx'] = 8 for
2-chip merged raw frames (8 virtual RX); CFG_* channel counts stay per-device (4 RX, 3 TX).
"""

import math


def AWR2243_read_config(config_file_name):
    _ = config_file_name  # not used; values match firmware / cascade_config.h (shortrange)
    global CFG_PARAMS
    global ADC_PARAMS

    chirpStartIdxFCF = 0
    chirpEndIdxFCF = 5
    loopCount = 64
    chirpStartIdx_buf = [0]
    chirpEndIdx_buf = [5]
    txEnable_buf = [0x7]

    # --- static: same keys as parsed .cfg (channelTx / channelRx / openCfg) ---
    CFG_PARAMS = {}
    ADC_PARAMS = {}

    CFG_PARAMS["txAntMask"] = 0x7
    numTxChan = 0
    for chanIdx in range(3):
        if (CFG_PARAMS["txAntMask"] >> chanIdx) & 1 == 1:
            numTxChan = numTxChan + 1
    CFG_PARAMS["numTxChan"] = numTxChan

    CFG_PARAMS["rxAntMask"] = 0xF
    numRxChan = 0
    for chanIdx in range(4):
        if (CFG_PARAMS["rxAntMask"] >> chanIdx) & 1 == 1:
            numRxChan = numRxChan + 1
    CFG_PARAMS["numRxChan"] = numRxChan
    # merged cascade frame (master+slave); use 4 for single-chip LVDS line only
    ADC_PARAMS["rx"] = 8

    ADC_PARAMS["bytes"] = 2
    ADC_PARAMS["IQ"] = 2

    dataRate = 0b0001
    if dataRate == 0b0001:
        CFG_PARAMS["lvdsBW"] = 600
    if dataRate == 0b0010:
        CFG_PARAMS["lvdsBW"] = 450
    if dataRate == 0b0011:
        CFG_PARAMS["lvdsBW"] = 400
    if dataRate == 0b0100:
        CFG_PARAMS["lvdsBW"] = 300
    if dataRate == 0b0101:
        CFG_PARAMS["lvdsBW"] = 225
    if dataRate == 0b0110:
        CFG_PARAMS["lvdsBW"] = 150

    laneEnVal = 0xF
    numlaneEn = 0
    for laneIdx in range(4):
        if (laneEnVal >> laneIdx) & 1 == 1:
            numlaneEn = numlaneEn + 1
    CFG_PARAMS["numlaneEn"] = numlaneEn

    # profile 0 — CASCADE_CFG_SHORTRANGE (cascade_config.h)
    startFreqConst = int(round(77.0 * (1 << 26) / 3.6))
    ADC_PARAMS["startFreq"] = startFreqConst * (3.6 / (1 << 26))
    ADC_PARAMS["idleTime"] = 500 / 100.0
    ADC_PARAMS["adc_valid_start_time"] = 600 / 100.0
    ADC_PARAMS["rampEndTime"] = 6000 / 100.0
    ADC_PARAMS["freq_slope"] = 925 * (3.6e3 * 900 / (1 << 26))
    ADC_PARAMS["txStartTime"] = 0 / 100.0
    ADC_PARAMS["samples"] = 256
    ADC_PARAMS["sample_rate"] = 5000

    # frameCfg periodicity: 250 ms -> 50_000_000 (5 ns LSB)
    ADC_PARAMS["frame_periodicity"] = (250 * 200000) / 200000.0

    ADC_PARAMS["tx"] = len(txEnable_buf)

    if ADC_PARAMS["tx"] > CFG_PARAMS["numTxChan"]:
        raise ValueError(
            "exceed max tx num, check channelTx(%d) and chirp cfg(%d)."
            % (CFG_PARAMS["numTxChan"], ADC_PARAMS["tx"])
        )
    tmp_chirpNum = chirpEndIdx_buf[0] - chirpStartIdx_buf[0] + 1
    all_chirpNum = tmp_chirpNum
    for i in range(ADC_PARAMS["tx"] - 1):
        all_chirpNum += chirpEndIdx_buf[i + 1] - chirpStartIdx_buf[i + 1] + 1
        if tmp_chirpNum != chirpEndIdx_buf[i + 1] - chirpStartIdx_buf[i + 1] + 1:
            raise ValueError(
                "AWR2243_read_config does not support different chirp number in different tx ant yet."
            )
    if all_chirpNum != chirpEndIdxFCF - chirpStartIdxFCF + 1:
        raise ValueError("chirp number in frame cfg and all chirp cfgs mismatched")
    ADC_PARAMS["chirps"] = loopCount * tmp_chirpNum

    LVDSDataSizePerChirp = (
        ADC_PARAMS["samples"] * ADC_PARAMS["rx"] * ADC_PARAMS["IQ"] * ADC_PARAMS["bytes"] + 52
    )
    LVDSDataSizePerChirp = math.ceil(LVDSDataSizePerChirp / 256) * 256
    maxSendBytesPerChirp = (
        (ADC_PARAMS["idleTime"] + ADC_PARAMS["rampEndTime"])
        * CFG_PARAMS["numlaneEn"]
        * CFG_PARAMS["lvdsBW"]
        / 8
    )

    print(f"ADC_PARAMS: {ADC_PARAMS}")

    return (LVDSDataSizePerChirp, maxSendBytesPerChirp, ADC_PARAMS, CFG_PARAMS)
