/**
 *   @file  cascade_enet_stream.h
 *
 *   @brief
 *      Ethernet (UDP) streaming header for cascade ADC data.
 *
 *  \par
 *  NOTE:
 *      (C) Copyright 2024 Texas Instruments, Inc.
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
#ifndef CASCADE_ENET_STREAM_H
#define CASCADE_ENET_STREAM_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <kernel/dpl/SemaphoreP.h>

/* -------------------------------------------------------------------------- */
/*  UDP packet header prepended to each ADC data chunk                        */
/* -------------------------------------------------------------------------- */
#define ENET_STREAM_UDP_MAGIC       (0xADC12345U)
#define ENET_STREAM_UDP_PORT        (5001U)
#define ENET_STREAM_MAX_PAYLOAD     (4096U)

typedef struct __attribute__((packed)) CascadeUdpAdcHeader_s
{
    uint32_t magic;
    uint32_t frameNum;
    uint16_t deviceIdx;
    uint16_t chirpLineIdx;
    uint16_t numSamples;
    uint16_t numRx;
    uint16_t bytesPerSample;
    uint16_t totalChirpLines;
} CascadeUdpAdcHeader;

/* -------------------------------------------------------------------------- */
/*  Public API                                                                */
/* -------------------------------------------------------------------------- */

/**
 *  @brief  Initialise ENET CPSW + lwIP with a static IP, then spawn
 *          the UDP streaming task.  Must be called from a FreeRTOS task
 *          context (not main / ISR).
 *
 *  @param  frameSem   Binary semaphore that the ISR posts when a full
 *                     frame has been accumulated.
 */
int32_t CascadeEnet_init(SemaphoreP_Object *frameSem);

/**
 *  @brief  Send one complete frame's ADC data over UDP.
 *          Called from the streaming task after the frame semaphore is posted.
 *
 *  @param  devBuf         Pointer to the frame accumulation buffer for one device
 *  @param  devBufBytes    Total bytes in that buffer
 *  @param  deviceIdx      0 or 1
 *  @param  frameNum       Monotonically increasing frame counter
 *  @param  chirpLines     Number of chirp lines in this frame
 *  @param  numSamples     ADC samples per chirp line
 *  @param  numRx          Number of RX channels
 *  @param  bytesPerSample Bytes per ADC sample (complex)
 */
int32_t CascadeEnet_sendFrame(const uint8_t *devBuf,
                              uint32_t       devBufBytes,
                              uint16_t       deviceIdx,
                              uint32_t       frameNum,
                              uint16_t       chirpLines,
                              uint16_t       numSamples,
                              uint16_t       numRx,
                              uint16_t       bytesPerSample);

#ifdef __cplusplus
}
#endif

#endif /* CASCADE_ENET_STREAM_H */
