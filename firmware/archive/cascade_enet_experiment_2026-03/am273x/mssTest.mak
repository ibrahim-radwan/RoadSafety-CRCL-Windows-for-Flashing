###################################################################################
# Cascade Unit Test on MSS Makefile
#
# Build targets:
#   mssTest      – LVDS streaming (DCA1000)       [default]
#   mssTestEnet  – Ethernet UDP streaming (lwIP)
###################################################################################
.PHONY: mssTest mssTestEnet mssTestClean

###################################################################################
# Setup the VPATH:
###################################################################################
vpath %.c $(MMWAVE_SDK_DEVICE_TYPE)

MSS_CPU := R5F

###################################################################################
# Base libraries (used by both LVDS and ENET builds)
###################################################################################
CASCADE_MSS_BASE_STD_LIBS = $($(MSS_CPU)_COMMON_STD_LIB) \
								-llibtestlogger_$(MMWAVE_SDK_DEVICE_TYPE).$($(MSS_CPU)_LIB_EXT) \
								-llibmmwavelink_cascade_$(MMWAVE_SDK_DEVICE_TYPE).$($(MSS_CPU)_LIB_EXT) \
								-llibmmwave_cascade_$(MMWAVE_SDK_DEVICE_TYPE).$($(MSS_CPU)_LIB_EXT)
CASCADE_MSS_BASE_LOC_LIBS = $($(MSS_CPU)_COMMON_LOC_LIB) \
								-Wl,-i$(MMWAVE_SDK_INSTALL_PATH)/ti/utils/testlogger/lib \
								-Wl,-i$(MMWAVE_SDK_INSTALL_PATH)/ti/control/mmwavelink/lib \
								-Wl,-i$(MMWAVE_SDK_INSTALL_PATH)/ti/control/mmwave/lib

###################################################################################
# Additional ENET / lwIP libraries (only for mssTestEnet)
###################################################################################
CASCADE_MSS_ENET_STD_LIBS = $(CASCADE_MSS_BASE_STD_LIBS) \
								-lenet-cpsw.am273x.r5f.ti-arm-clang.$(LIB_TYPE).lib \
								-llwip-contrib-freertos.am273x.r5f.ti-arm-clang.$(LIB_TYPE).lib \
								-llwipif-cpsw-freertos.am273x.r5f.ti-arm-clang.$(LIB_TYPE).lib \
								-llwip-freertos.am273x.r5f.ti-arm-clang.$(LIB_TYPE).lib
CASCADE_MSS_ENET_LOC_LIBS = $(CASCADE_MSS_BASE_LOC_LIBS) \
								-Wl,-i$(MCU_PLUS_INSTALL_PATH)/source/networking/enet/lib \
								-Wl,-i$(MCU_PLUS_INSTALL_PATH)/source/networking/lwip/lib

###################################################################################
# Additional include paths for ENET / lwIP (only for mssTestEnet)
###################################################################################
ENET_R5F_INCLUDE = -I$(MCU_PLUS_INSTALL_PATH)/source/networking/enet \
               -I$(MCU_PLUS_INSTALL_PATH)/source/networking/enet/utils/include \
               -I$(MCU_PLUS_INSTALL_PATH)/source/networking/enet/core \
               -I$(MCU_PLUS_INSTALL_PATH)/source/networking/enet/core/include \
               -I$(MCU_PLUS_INSTALL_PATH)/source/networking/enet/core/include/phy \
               -I$(MCU_PLUS_INSTALL_PATH)/source/networking/enet/core/include/core \
               -I$(MCU_PLUS_INSTALL_PATH)/source/networking/enet/soc/am273x \
               -I$(MCU_PLUS_INSTALL_PATH)/source/networking/enet/hw_include \
               -I$(MCU_PLUS_INSTALL_PATH)/source/networking/enet/hw_include/mdio/V4 \
               -I$(MCU_PLUS_INSTALL_PATH)/source/networking/lwip/lwip-stack/src/include \
               -I$(MCU_PLUS_INSTALL_PATH)/source/networking/lwip/lwip-port/include \
               -I$(MCU_PLUS_INSTALL_PATH)/source/networking/lwip/lwip-port/freertos/include \
               -I$(MCU_PLUS_INSTALL_PATH)/source/networking/enet/core/lwipif/inc \
               -I$(MCU_PLUS_INSTALL_PATH)/source/networking/lwip/lwip-contrib \
               -I$(MCU_PLUS_INSTALL_PATH)/source/networking/lwip/lwip-config/am273x


###################################################################################
# Unit Test Files
###################################################################################
CASCADE_MSS_UNIT_TEST_CMD		 = $(MMWAVE_SDK_INSTALL_PATH)/ti/platform/$(MMWAVE_SDK_DEVICE_TYPE)
CASCADE_MSS_UNIT_TEST_MAP		 = $(MMWAVE_SDK_DEVICE_TYPE)/$(MMWAVE_SDK_DEVICE_TYPE)_cascade_mss.map
CASCADE_MSS_UNIT_TEST_OUT		 = $(MMWAVE_SDK_DEVICE_TYPE)/$(MMWAVE_SDK_DEVICE_TYPE)_cascade_mss.$($(MSS_CPU)_EXE_EXT)
CASCADE_MSS_UNIT_TEST_BIN		 = $(MMWAVE_SDK_DEVICE_TYPE)/$(MMWAVE_SDK_DEVICE_TYPE)_cascade_mss.bin
CASCADE_MSS_UNIT_TEST_APP_CMD	 = $(MMWAVE_SDK_DEVICE_TYPE)/mss_linker.cmd
CASCADE_MSS_ENET_APP_CMD         = $(MMWAVE_SDK_DEVICE_TYPE)/mss_linker_enet.cmd

CASCADE_MSS_UNIT_TEST_SOURCES	 = main_mss.c \
								   common.c \
								   cascade_lvds_stream.c \
								   cascade_csirx.c

CASCADE_MSS_ENET_SOURCES         = $(CASCADE_MSS_UNIT_TEST_SOURCES) \
								   cascade_enet_stream.c

CASCADE_MSS_UNIT_TEST_SOURCES_GEN = ti_board_config.c	\
									ti_board_open_close.c	\
									ti_dpl_config.c	\
									ti_drivers_config.c	\
									ti_pinmux_config.c	\
									ti_power_clock_config.c	\
									ti_drivers_open_close.c

CASCADE_MSS_UNIT_TEST_SOURCES_GEN_ENET = ti_enet_config.c \
                                         ti_enet_open_close.c \
                                         ti_enet_soc.c \
                                         ti_enet_lwipif.c

CASCADE_MSS_UNIT_TEST_DEPENDS	 = $(addprefix $(PLATFORM_OBJDIR)/, $(CASCADE_MSS_UNIT_TEST_SOURCES:.c=.$($(MSS_CPU)_DEP_EXT)))
CASCADE_MSS_UNIT_TEST_OBJECTS	 = $(addprefix $(PLATFORM_OBJDIR)/, $(CASCADE_MSS_UNIT_TEST_SOURCES:.c=.$($(MSS_CPU)_OBJ_EXT)))

CASCADE_MSS_ENET_OBJECTS         = $(addprefix $(PLATFORM_OBJDIR)/, $(CASCADE_MSS_ENET_SOURCES:.c=.$($(MSS_CPU)_OBJ_EXT)))
CASCADE_MSS_UNIT_TEST_OBJECTS_GEN     = $(addprefix $(PLATFORM_OBJDIR)/mssgenerated/, $(CASCADE_MSS_UNIT_TEST_SOURCES_GEN:.c=.$($(MSS_CPU)_OBJ_EXT)))
CASCADE_MSS_UNIT_TEST_OBJECTS_GEN_ENET = $(addprefix $(PLATFORM_OBJDIR)/mssgenerated/, $(CASCADE_MSS_UNIT_TEST_SOURCES_GEN_ENET:.c=.$($(MSS_CPU)_OBJ_EXT)))

###################################################################################
# Build LVDS target (DCA1000):        gmake mssTest
###################################################################################
mssTest: R5F_CFLAGS  += -DCASCADE_EVM
mssTest: buildDirectories mssbuildDirectories $(CASCADE_MSS_UNIT_TEST_OBJECTS) $(CASCADE_MSS_UNIT_TEST_OBJECTS_GEN)
	$($(MSS_CPU)_LD) $($(MSS_CPU)_LDFLAGS) $(CASCADE_MSS_BASE_LOC_LIBS) -Wl,-m=$(CASCADE_MSS_UNIT_TEST_MAP) \
	-o $(CASCADE_MSS_UNIT_TEST_OUT) $(CASCADE_MSS_UNIT_TEST_OBJECTS) $(CASCADE_MSS_UNIT_TEST_OBJECTS_GEN) $(CASCADE_MSS_BASE_STD_LIBS) \
	$(PLATFORM_$(MSS_CPU)_LINK_CMD) $(CASCADE_MSS_UNIT_TEST_APP_CMD)
	@echo '******************************************************************************'
	@echo 'Built the mmWave Cascade MSS – LVDS (DCA1000) '
	@echo '******************************************************************************'

###################################################################################
# Build Ethernet target (UDP/lwIP):   gmake mssTestEnet
###################################################################################
mssTestEnet: R5F_CFLAGS  += -DCASCADE_EVM -DENET_STREAM
mssTestEnet: R5F_INCLUDE += $(ENET_R5F_INCLUDE)
mssTestEnet: buildDirectories mssbuildDirectories $(CASCADE_MSS_ENET_OBJECTS) $(CASCADE_MSS_UNIT_TEST_OBJECTS_GEN) $(CASCADE_MSS_UNIT_TEST_OBJECTS_GEN_ENET)
	$($(MSS_CPU)_LD) $($(MSS_CPU)_LDFLAGS) $(CASCADE_MSS_ENET_LOC_LIBS) -Wl,-m=$(CASCADE_MSS_UNIT_TEST_MAP) \
	-o $(CASCADE_MSS_UNIT_TEST_OUT) $(CASCADE_MSS_ENET_OBJECTS) $(CASCADE_MSS_UNIT_TEST_OBJECTS_GEN) $(CASCADE_MSS_UNIT_TEST_OBJECTS_GEN_ENET) $(CASCADE_MSS_ENET_STD_LIBS) \
	$(PLATFORM_$(MSS_CPU)_LINK_CMD) $(CASCADE_MSS_ENET_APP_CMD)
	@echo '******************************************************************************'
	@echo 'Built the mmWave Cascade MSS – Ethernet (UDP) '
	@echo '******************************************************************************'

###################################################################################
# Cleanup Unit Test:
###################################################################################
mssTestClean:
	@echo 'Cleaning the mmWave Cascade MSS Unit Test objects'
	@$(DEL) $(CASCADE_MSS_UNIT_TEST_OBJECTS) $(CASCADE_MSS_UNIT_TEST_OUT) $(CASCADE_MSS_UNIT_TEST_BIN)
	@$(DEL) $(CASCADE_MSS_UNIT_TEST_MAP) $(CASCADE_MSS_UNIT_TEST_DEPENDS)
	@$(DEL) $(PLATFORM_OBJDIR)

###################################################################################
# Dependency handling
###################################################################################
-include $(CASCADE_MSS_UNIT_TEST_DEPENDS)
