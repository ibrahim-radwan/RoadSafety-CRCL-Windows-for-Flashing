#include "ti_enet_config.h"

/*----------------------------------------------------------------------------*/
/* Linker Settings                                                            */
--retain="*(.intvecs)"

--stack_size=8192
--heap_size=34000
-e_vectors

__IRQ_STACK_SIZE = 256;
__FIQ_STACK_SIZE = 256;
__SVC_STACK_SIZE = 4096;
__ABORT_STACK_SIZE = 256;
__UNDEFINED_STACK_SIZE = 256;

/*----------------------------------------------------------------------------*/
/* Section Configuration                                                      */
SECTIONS
{
    .vectors:{} palign(8) > R5F_VECS

    GROUP {
        .text.hwi: palign(8)
        .text.cache: palign(8)
        .text.mpu: palign(8)
        .text.boot: palign(8)
        .text:abort: palign(8)
    } > MSS_L2

    GROUP {
        .text:   {} palign(8)
        .rodata: {} palign(8)
    } > MSS_L2

    GROUP {
        .data:   {} palign(8)
    } > MSS_L2

    /* lwIP memory pools – placed in DSS_L3 to save MSS_L2 space */
    GROUP {
        .bss:.common:memp_memory_POOL_1792_base:  (NOLOAD)  {} palign(128)
        .bss:.common:memp_memory_POOL_1024_base:  (NOLOAD)  {} palign(128)
        .bss:.common:memp_memory_POOL_256_base:   (NOLOAD)  {} palign(128)
        .bss:.common:memp_memory_POOL_512_base:   (NOLOAD)  {} palign(128)
        .bss:.common:memp_memory_POOL_4096_base:  (NOLOAD)  {} palign(128)
        .bss:.common:memp_memory_POOL_128_base:   (NOLOAD)  {} palign(128)
        .bss:.common:memp_memory_PBUF_POOL_base:  (NOLOAD)  {} palign(128)
    } > DSS_L3

    GROUP {
        .bss:    {} palign(8)
        RUN_START(__BSS_START)
        RUN_END(__BSS_END)
    } > SBL_RESERVED_L2_RAM | MSS_L2

    .sysmem: {} palign(8) > SBL_RESERVED_L2_RAM | MSS_L2
    .stack:  {} palign(8) > SBL_RESERVED_L2_RAM | MSS_L2

    GROUP {
        .irqstack: {. = . + __IRQ_STACK_SIZE;} align(8)
        RUN_START(__IRQ_STACK_START)
        RUN_END(__IRQ_STACK_END)
        .fiqstack: {. = . + __FIQ_STACK_SIZE;} align(8)
        RUN_START(__FIQ_STACK_START)
        RUN_END(__FIQ_STACK_END)
        .svcstack: {. = . + __SVC_STACK_SIZE;} align(8)
        RUN_START(__SVC_STACK_START)
        RUN_END(__SVC_STACK_END)
        .abortstack: {. = . + __ABORT_STACK_SIZE;} align(8)
        RUN_START(__ABORT_STACK_START)
        RUN_END(__ABORT_STACK_END)
        .undefinedstack: {. = . + __UNDEFINED_STACK_SIZE;} align(8)
        RUN_START(__UNDEFINED_STACK_START)
        RUN_END(__UNDEFINED_STACK_END)
    } > MSS_L2

    systemHeap      : { } > DSS_L3
    .MCPILogBuffer  : { } > DSS_L3
    .l2ram          : { } > DSS_L3
    .l3ram          : { } > DSS_L3
    .hwaram         : { } > HWA_RAM

    .bss.ipc_vring_mem   (NOLOAD) : {} > RTOS_NORTOS_IPC_SHM_MEM

    /* ENET CPSW CPPI descriptor ring */
    .bss:ENET_CPPI_DESC  (NOLOAD) {} ALIGN (128) > CPPI_DESC

    /* ENET DMA packet pool */
    .enet_dma_mem {
#if (ENET_SYSCFG_PKT_POOL_ENABLE == 1)
        *(*ENET_DMA_PKT_MEMPOOL)
#endif
    } (NOLOAD) {} ALIGN (128) > DSS_L3
}

/*----------------------------------------------------------------------------*/
MEMORY
{
    R5F_VECS  : ORIGIN = 0x00000000 , LENGTH = 0x00000040
    R5F_TCMA  : ORIGIN = 0x00000040 , LENGTH = 0x00003FC0
    R5F_TCMB  : ORIGIN = 0x00080000 , LENGTH = 0x00004000

    SBL_RESERVED_L2_RAM (RW) : origin=0x10200000 length=0x00020000

    MSS_L2     : ORIGIN = 0x10220000 , LENGTH = 0x000CC000

    /* CPPI descriptor memory (non-cached via MPU region 5) */
    CPPI_DESC  : ORIGIN = 0x102EC000 , LENGTH = 0x00004000

    /*
     * DSS L3 – holds frame accumulation buffers (~3 MB), ping/pong,
     * lwIP pools, and ENET DMA packets.
     */
    DSS_L3     : ORIGIN = 0x88000000 , LENGTH = 0x00390000

    HWA_RAM (RW) : origin=0x82000000 length=0x00020000

    RTOS_NORTOS_IPC_SHM_MEM : ORIGIN = 0xC5000000, LENGTH = 0x1F40
}
/*----------------------------------------------------------------------------*/
