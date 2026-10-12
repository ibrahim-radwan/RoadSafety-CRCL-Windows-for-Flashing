/**
 *   @file  cascade_enet_stream.c
 *
 *   @brief
 *      Ethernet (UDP) streaming of cascade ADC data.
 *      Brings up CPSW + lwIP with a static IP and sends each completed
 *      frame as a burst of UDP packets (one per chirp line per device).
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

/* ========================================================================== */
/*                             Include Files                                  */
/* ========================================================================== */
#include <stdint.h>
#include <string.h>
#include <stdio.h>

#include "FreeRTOS.h"
#include "task.h"

#include "lwip/opt.h"
#include "lwip/sys.h"
#include "lwip/tcpip.h"
#include "lwip/api.h"
#include "lwip/netbuf.h"

#include <kernel/dpl/ClockP.h>
#include <kernel/dpl/DebugP.h>

#include "ti_enet_config.h"
#include "ti_enet_lwipif.h"

#include <ti/utils/test/cascade/am273x/cascade_enet_stream.h>

/* ========================================================================== */
/*                           Macros & Typedefs                                */
/* ========================================================================== */

/*
 * Static IP configuration.
 * Change these to match your lab network.
 */
#define ENET_LOCAL_IP0   192
#define ENET_LOCAL_IP1   168
#define ENET_LOCAL_IP2   1
#define ENET_LOCAL_IP3   100

#define ENET_NETMASK0    255
#define ENET_NETMASK1    255
#define ENET_NETMASK2    255
#define ENET_NETMASK3    0

#define ENET_GW0         192
#define ENET_GW1         168
#define ENET_GW2         1
#define ENET_GW3         1

/* Broadcast destination – receiver listens on any host in the subnet */
#define ENET_DEST_IP0    192
#define ENET_DEST_IP1    168
#define ENET_DEST_IP2    1
#define ENET_DEST_IP3    255

static const uint8_t BROADCAST_MAC_ADDRESS[6] =
    { 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF };

/* ========================================================================== */
/*                            Global Variables                                */
/* ========================================================================== */
static struct netif *gNetif = NULL;
static struct netconn *gUdpConn = NULL;

/* ========================================================================== */
/*                     Local Function Declarations                            */
/* ========================================================================== */
static void     Enet_tcpipInitCb(void *arg);
static void     Enet_setupNetif(void);
static int32_t  Enet_isNetworkUp(struct netif *nif);

/* ========================================================================== */
/*                          Function Definitions                              */
/* ========================================================================== */

int32_t CascadeEnet_init(SemaphoreP_Object *frameSem)
{
    Enet_Type  enetType;
    uint32_t   instId;
    int32_t    status;
    sys_sem_t  initSem;

    (void)frameSem;

    /* ---- Bring up CPSW driver ---- */
    EnetApp_getEnetInstInfo(&enetType, &instId);
    EnetAppUtils_enableClocks(enetType, instId);

    status = EnetApp_driverOpen(enetType, instId);
    if (ENET_SOK != status)
    {
        DebugP_log("ENET: driver open failed %d\r\n", status);
        return -1;
    }

    EnetApp_addMCastEntry(enetType, instId, EnetSoc_getCoreId(),
                          BROADCAST_MAC_ADDRESS, CPSW_ALE_ALL_PORTS_MASK);

    /* ---- lwIP TCP/IP thread init ---- */
    if (sys_sem_new(&initSem, 0) != ERR_OK)
    {
        DebugP_log("ENET: sem create failed\r\n");
        return -1;
    }

    tcpip_init(Enet_tcpipInitCb, &initSem);
    sys_sem_wait(&initSem);
    sys_sem_free(&initSem);

    /* ---- Wait for link up ---- */
    while (!Enet_isNetworkUp(gNetif))
    {
        DebugP_log("ENET: waiting for link …\r\n");
        ClockP_sleep(2);
    }
    DebugP_log("ENET: network is UP  IP=%d.%d.%d.%d\r\n",
               ENET_LOCAL_IP0, ENET_LOCAL_IP1, ENET_LOCAL_IP2, ENET_LOCAL_IP3);

    /* ---- Create UDP socket ---- */
    gUdpConn = netconn_new(NETCONN_UDP);
    if (gUdpConn == NULL)
    {
        DebugP_log("ENET: netconn_new failed\r\n");
        return -1;
    }

    netconn_bind(gUdpConn, IP_ADDR_ANY, ENET_STREAM_UDP_PORT);

    ip_addr_t destAddr;
    IP4_ADDR(&destAddr, ENET_DEST_IP0, ENET_DEST_IP1,
             ENET_DEST_IP2, ENET_DEST_IP3);
    netconn_connect(gUdpConn, &destAddr, ENET_STREAM_UDP_PORT);

    DebugP_log("ENET: UDP ready on port %u\r\n", ENET_STREAM_UDP_PORT);
    return 0;
}

/* -------------------------------------------------------------------------- */
int32_t CascadeEnet_sendFrame(const uint8_t *devBuf,
                              uint32_t       devBufBytes,
                              uint16_t       deviceIdx,
                              uint32_t       frameNum,
                              uint16_t       chirpLines,
                              uint16_t       numSamples,
                              uint16_t       numRx,
                              uint16_t       bytesPerSample)
{
    if (gUdpConn == NULL)
        return -1;

    const uint32_t lineBytes = (uint32_t)numSamples * bytesPerSample * numRx;
    CascadeUdpAdcHeader hdr;

    hdr.magic          = ENET_STREAM_UDP_MAGIC;
    hdr.frameNum       = frameNum;
    hdr.deviceIdx      = deviceIdx;
    hdr.numSamples     = numSamples;
    hdr.numRx          = numRx;
    hdr.bytesPerSample = bytesPerSample;
    hdr.totalChirpLines = chirpLines;

    for (uint16_t line = 0U; line < chirpLines; line++)
    {
        hdr.chirpLineIdx = line;

        struct netbuf *buf = netbuf_new();
        if (buf == NULL)
            continue;

        void *payload = netbuf_alloc(buf, sizeof(CascadeUdpAdcHeader) + lineBytes);
        if (payload == NULL)
        {
            netbuf_delete(buf);
            continue;
        }

        memcpy(payload, &hdr, sizeof(CascadeUdpAdcHeader));
        memcpy((uint8_t *)payload + sizeof(CascadeUdpAdcHeader),
               devBuf + (uint32_t)line * lineBytes,
               lineBytes);

        netconn_send(gUdpConn, buf);
        netbuf_delete(buf);
    }

    return 0;
}

/* ========================================================================== */
/*                       Local (static) helpers                               */
/* ========================================================================== */
static void Enet_tcpipInitCb(void *arg)
{
    sys_sem_t *sem = (sys_sem_t *)arg;

    srand((unsigned int)sys_now() / 1000);
    Enet_setupNetif();

    sys_sem_signal(sem);
}

static void Enet_setupNetif(void)
{
    ip4_addr_t ipaddr, netmask, gw;

    IP4_ADDR(&ipaddr,  ENET_LOCAL_IP0,  ENET_LOCAL_IP1,
                        ENET_LOCAL_IP2,  ENET_LOCAL_IP3);
    IP4_ADDR(&netmask, ENET_NETMASK0,   ENET_NETMASK1,
                        ENET_NETMASK2,   ENET_NETMASK3);
    IP4_ADDR(&gw,      ENET_GW0,        ENET_GW1,
                        ENET_GW2,        ENET_GW3);

    LwipifEnetApp_netifOpen(NETIF_INST_ID0, &ipaddr, &netmask, &gw);
    gNetif = LwipifEnetApp_getNetifFromId(NETIF_INST_ID0);

    netif_set_up(gNetif);

    LwipifEnetApp_startSchedule(gNetif);
}

static int32_t Enet_isNetworkUp(struct netif *nif)
{
    if (nif == NULL)
        return 0;
    return (netif_is_up(nif) && netif_is_link_up(nif) &&
            !ip4_addr_isany_val(*netif_ip4_addr(nif)));
}
