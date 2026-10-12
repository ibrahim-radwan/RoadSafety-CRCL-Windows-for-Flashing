###################################################################################
#
# LVDS Stream makefile
#
###################################################################################

include ../../../common/mmwave_sdk.mak

ifeq ($(MMWAVE_SDK_DEVICE_TYPE), am273x)
include ./$(MMWAVE_SDK_DEVICE_TYPE)/mssTest.mak
else
$(error Cascade application is applicable for only AM273X.)
endif

###################################################################################
# Standard Targets which need to be implemented by each mmWave SDK module. This
# plugs into the release scripts.
###################################################################################

.PHONY: all clean test testClean mssTest mssTestClean help mssTestInf mssTestInfClean testInf testInfClean

ifeq ($(MMWAVE_SDK_DEVICE_TYPE),am273x)
testClean: 	syscfgclean mssTestClean
test: 		syscfg mssTest

###################################################################################
# All *_inf firmware variants: CASCADE_INF=1, copy .xer5f + .map into am273x/build_*_inf/
###################################################################################
AM273_CASCADE_OUT	= $(MMWAVE_SDK_DEVICE_TYPE)/$(MMWAVE_SDK_DEVICE_TYPE)_cascade_mss.xer5f
AM273_CASCADE_MAP	= $(MMWAVE_SDK_DEVICE_TYPE)/$(MMWAVE_SDK_DEVICE_TYPE)_cascade_mss.map

mssTestInfClean: mssTestClean

mssTestInf: syscfg
	@echo '****** CASCADE_CFG_LONGRANGE -> build_longrange_inf ******'
	$(MAKE) mssTestClean MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_LONGRANGE CASCADE_INF=1
	$(MAKE) mssTest MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_LONGRANGE CASCADE_INF=1
	$(COPY_CMD) -f $(AM273_CASCADE_OUT) $(MMWAVE_SDK_DEVICE_TYPE)/build_longrange_inf/
	$(COPY_CMD) -f $(AM273_CASCADE_MAP) $(MMWAVE_SDK_DEVICE_TYPE)/build_longrange_inf/
	@echo '****** CASCADE_CFG_SHORTRANGE -> build_shortrange_inf ******'
	$(MAKE) mssTestClean MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_SHORTRANGE CASCADE_INF=1
	$(MAKE) mssTest MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_SHORTRANGE CASCADE_INF=1
	$(COPY_CMD) -f $(AM273_CASCADE_OUT) $(MMWAVE_SDK_DEVICE_TYPE)/build_shortrange_inf/
	$(COPY_CMD) -f $(AM273_CASCADE_MAP) $(MMWAVE_SDK_DEVICE_TYPE)/build_shortrange_inf/
	@echo '****** CASCADE_CFG_SHORTRANGE_CALIB -> build_shortrange_calib_inf ******'
	$(MAKE) mssTestClean MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_SHORTRANGE_CALIB CASCADE_INF=1
	$(MAKE) mssTest MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_SHORTRANGE_CALIB CASCADE_INF=1
	$(COPY_CMD) -f $(AM273_CASCADE_OUT) $(MMWAVE_SDK_DEVICE_TYPE)/build_shortrange_calib_inf/
	$(COPY_CMD) -f $(AM273_CASCADE_MAP) $(MMWAVE_SDK_DEVICE_TYPE)/build_shortrange_calib_inf/
	@echo '****** CASCADE_CFG_VERYLONGRANGE -> build_verylongrange_inf ******'
	$(MAKE) mssTestClean MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_VERYLONGRANGE CASCADE_INF=1
	$(MAKE) mssTest MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_VERYLONGRANGE CASCADE_INF=1
	$(COPY_CMD) -f $(AM273_CASCADE_OUT) $(MMWAVE_SDK_DEVICE_TYPE)/build_verylongrange_inf/
	$(COPY_CMD) -f $(AM273_CASCADE_MAP) $(MMWAVE_SDK_DEVICE_TYPE)/build_verylongrange_inf/
	@echo '****** CASCADE_CFG_R050M -> build_r050m_inf ******'
	$(MAKE) mssTestClean MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R050M CASCADE_INF=1
	$(MAKE) mssTest MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R050M CASCADE_INF=1
	$(COPY_CMD) -f $(AM273_CASCADE_OUT) $(MMWAVE_SDK_DEVICE_TYPE)/build_r050m_inf/
	$(COPY_CMD) -f $(AM273_CASCADE_MAP) $(MMWAVE_SDK_DEVICE_TYPE)/build_r050m_inf/
	@echo '****** CASCADE_CFG_R075M -> build_r075m_inf ******'
	$(MAKE) mssTestClean MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R075M CASCADE_INF=1
	$(MAKE) mssTest MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R075M CASCADE_INF=1
	$(COPY_CMD) -f $(AM273_CASCADE_OUT) $(MMWAVE_SDK_DEVICE_TYPE)/build_r075m_inf/
	$(COPY_CMD) -f $(AM273_CASCADE_MAP) $(MMWAVE_SDK_DEVICE_TYPE)/build_r075m_inf/
	@echo '****** CASCADE_CFG_R100M -> build_r100m_inf ******'
	$(MAKE) mssTestClean MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R100M CASCADE_INF=1
	$(MAKE) mssTest MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R100M CASCADE_INF=1
	$(COPY_CMD) -f $(AM273_CASCADE_OUT) $(MMWAVE_SDK_DEVICE_TYPE)/build_r100m_inf/
	$(COPY_CMD) -f $(AM273_CASCADE_MAP) $(MMWAVE_SDK_DEVICE_TYPE)/build_r100m_inf/
	@echo '****** CASCADE_CFG_R075M_V2 -> build_r075m_v2_inf ******'
	$(MAKE) mssTestClean MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R075M_V2 CASCADE_INF=1
	$(MAKE) mssTest MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R075M_V2 CASCADE_INF=1
	$(COPY_CMD) -f $(AM273_CASCADE_OUT) $(MMWAVE_SDK_DEVICE_TYPE)/build_r075m_v2_inf/
	$(COPY_CMD) -f $(AM273_CASCADE_MAP) $(MMWAVE_SDK_DEVICE_TYPE)/build_r075m_v2_inf/
	@echo '****** CASCADE_CFG_R075M_V2_8FPS -> build_r075m_v2_8fps_inf ******'
	$(MAKE) mssTestClean MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R075M_V2_8FPS CASCADE_INF=1
	$(MAKE) mssTest MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R075M_V2_8FPS CASCADE_INF=1
	$(COPY_CMD) -f $(AM273_CASCADE_OUT) $(MMWAVE_SDK_DEVICE_TYPE)/build_r075m_v2_8fps_inf/
	$(COPY_CMD) -f $(AM273_CASCADE_MAP) $(MMWAVE_SDK_DEVICE_TYPE)/build_r075m_v2_8fps_inf/
	@echo '****** CASCADE_CFG_R017M_V2 -> build_r017m_v2_inf ******'
	$(MAKE) mssTestClean MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R017M_V2 CASCADE_INF=1
	$(MAKE) mssTest MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R017M_V2 CASCADE_INF=1
	$(COPY_CMD) -f $(AM273_CASCADE_OUT) $(MMWAVE_SDK_DEVICE_TYPE)/build_r017m_v2_inf/
	$(COPY_CMD) -f $(AM273_CASCADE_MAP) $(MMWAVE_SDK_DEVICE_TYPE)/build_r017m_v2_inf/
	@echo '****** CASCADE_CFG_R017M_V2_8FPS -> build_r017m_v2_8fps_inf ******'
	$(MAKE) mssTestClean MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R017M_V2_8FPS CASCADE_INF=1
	$(MAKE) mssTest MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R017M_V2_8FPS CASCADE_INF=1
	$(COPY_CMD) -f $(AM273_CASCADE_OUT) $(MMWAVE_SDK_DEVICE_TYPE)/build_r017m_v2_8fps_inf/
	$(COPY_CMD) -f $(AM273_CASCADE_MAP) $(MMWAVE_SDK_DEVICE_TYPE)/build_r017m_v2_8fps_inf/
	@echo '****** CASCADE_CFG_R017M_CALIB_V2 -> build_r017m_calib_v2_inf ******'
	$(MAKE) mssTestClean MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R017M_CALIB_V2 CASCADE_INF=1
	$(MAKE) mssTest MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R017M_CALIB_V2 CASCADE_INF=1
	$(COPY_CMD) -f $(AM273_CASCADE_OUT) $(MMWAVE_SDK_DEVICE_TYPE)/build_r017m_calib_v2_inf/
	$(COPY_CMD) -f $(AM273_CASCADE_MAP) $(MMWAVE_SDK_DEVICE_TYPE)/build_r017m_calib_v2_inf/
	@echo '****** CASCADE_CFG_R050M_V2 -> build_r050m_v2_inf ******'
	$(MAKE) mssTestClean MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R050M_V2 CASCADE_INF=1
	$(MAKE) mssTest MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R050M_V2 CASCADE_INF=1
	$(COPY_CMD) -f $(AM273_CASCADE_OUT) $(MMWAVE_SDK_DEVICE_TYPE)/build_r050m_v2_inf/
	$(COPY_CMD) -f $(AM273_CASCADE_MAP) $(MMWAVE_SDK_DEVICE_TYPE)/build_r050m_v2_inf/
	@echo '****** CASCADE_CFG_R050M_V2_8FPS -> build_r050m_v2_8fps_inf ******'
	$(MAKE) mssTestClean MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R050M_V2_8FPS CASCADE_INF=1
	$(MAKE) mssTest MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R050M_V2_8FPS CASCADE_INF=1
	$(COPY_CMD) -f $(AM273_CASCADE_OUT) $(MMWAVE_SDK_DEVICE_TYPE)/build_r050m_v2_8fps_inf/
	$(COPY_CMD) -f $(AM273_CASCADE_MAP) $(MMWAVE_SDK_DEVICE_TYPE)/build_r050m_v2_8fps_inf/
	@echo '****** CASCADE_CFG_R100M_V2 -> build_r100m_v2_inf ******'
	$(MAKE) mssTestClean MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R100M_V2 CASCADE_INF=1
	$(MAKE) mssTest MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R100M_V2 CASCADE_INF=1
	$(COPY_CMD) -f $(AM273_CASCADE_OUT) $(MMWAVE_SDK_DEVICE_TYPE)/build_r100m_v2_inf/
	$(COPY_CMD) -f $(AM273_CASCADE_MAP) $(MMWAVE_SDK_DEVICE_TYPE)/build_r100m_v2_inf/
	@echo '****** CASCADE_CFG_R100M_V2_8FPS -> build_r100m_v2_8fps_inf ******'
	$(MAKE) mssTestClean MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R100M_V2_8FPS CASCADE_INF=1
	$(MAKE) mssTest MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R100M_V2_8FPS CASCADE_INF=1
	$(COPY_CMD) -f $(AM273_CASCADE_OUT) $(MMWAVE_SDK_DEVICE_TYPE)/build_r100m_v2_8fps_inf/
	$(COPY_CMD) -f $(AM273_CASCADE_MAP) $(MMWAVE_SDK_DEVICE_TYPE)/build_r100m_v2_8fps_inf/
	@echo '****** CASCADE_CFG_R142M_V2 -> build_r142m_v2_inf ******'
	$(MAKE) mssTestClean MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R142M_V2 CASCADE_INF=1
	$(MAKE) mssTest MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R142M_V2 CASCADE_INF=1
	$(COPY_CMD) -f $(AM273_CASCADE_OUT) $(MMWAVE_SDK_DEVICE_TYPE)/build_r142m_v2_inf/
	$(COPY_CMD) -f $(AM273_CASCADE_MAP) $(MMWAVE_SDK_DEVICE_TYPE)/build_r142m_v2_inf/
	@echo '****** CASCADE_CFG_R142M_V2_8FPS -> build_r142m_v2_8fps_inf ******'
	$(MAKE) mssTestClean MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R142M_V2_8FPS CASCADE_INF=1
	$(MAKE) mssTest MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R142M_V2_8FPS CASCADE_INF=1
	$(COPY_CMD) -f $(AM273_CASCADE_OUT) $(MMWAVE_SDK_DEVICE_TYPE)/build_r142m_v2_8fps_inf/
	$(COPY_CMD) -f $(AM273_CASCADE_MAP) $(MMWAVE_SDK_DEVICE_TYPE)/build_r142m_v2_8fps_inf/
	@echo '****** CASCADE_CFG_R168M_V2 -> build_r168m_v2_inf ******'
	$(MAKE) mssTestClean MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R168M_V2 CASCADE_INF=1
	$(MAKE) mssTest MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R168M_V2 CASCADE_INF=1
	$(COPY_CMD) -f $(AM273_CASCADE_OUT) $(MMWAVE_SDK_DEVICE_TYPE)/build_r168m_v2_inf/
	$(COPY_CMD) -f $(AM273_CASCADE_MAP) $(MMWAVE_SDK_DEVICE_TYPE)/build_r168m_v2_inf/
	@echo '****** CASCADE_CFG_R168M_V2_8FPS -> build_r168m_v2_8fps_inf ******'
	$(MAKE) mssTestClean MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R168M_V2_8FPS CASCADE_INF=1
	$(MAKE) mssTest MMWAVE_SDK_DEVICE_TYPE=am273x CASCADE_CONFIG=CASCADE_CFG_R168M_V2_8FPS CASCADE_INF=1
	$(COPY_CMD) -f $(AM273_CASCADE_OUT) $(MMWAVE_SDK_DEVICE_TYPE)/build_r168m_v2_8fps_inf/
	$(COPY_CMD) -f $(AM273_CASCADE_MAP) $(MMWAVE_SDK_DEVICE_TYPE)/build_r168m_v2_8fps_inf/
	@echo '****** All *_inf cascade MSS images built and copied ******'

testInfClean: syscfgclean mssTestInfClean
testInf: syscfg mssTestInf
endif

syscfg: $(MMWAVE_SDK_DEVICE_TYPE)/test.syscfg
	@echo Generating SysConfig files ...
	$(SYSCFG_NODE) $(SYSCFG_CLI_PATH)/dist/cli.js --product $(SYSCFG_SDKPRODUCT) --context r5fss0-0 --part Default --package ZCE --output $(MMWAVE_SDK_DEVICE_TYPE)/mssgenerated/ $(MMWAVE_SDK_DEVICE_TYPE)/test.syscfg

syscfg-gui:
	$(SYSCFG_NWJS) $(SYSCFG_CLI_PATH) --product $(SYSCFG_SDKPRODUCT) --device AM273x --context r5fss0-0 --part Default --package ZCE --output $(MMWAVE_SDK_DEVICE_TYPE)/mssgenerated/ $(MMWAVE_SDK_DEVICE_TYPE)/test.syscfg

# syscfg: This cleans syscfg files
syscfgclean:
	@echo 'Cleaning the syscfg files'
	@$(DEL) $(MMWAVE_SDK_DEVICE_TYPE)/mssgenerated/

# Clean: This cleans all the objects
clean: testClean

# This will build the test
all: test

# Help: This displays the MAKEFILE Usage.
help:
	@echo '****************************************************************************************'
	@echo '* Makefile Targets for the LVDS Stream test '
	@echo 'clean             -> Clean out all the objects'
	@echo 'test              -> Builds all the unit tests for the SOC'
	@echo 'testClean         -> Cleans all the Unit Tests for the SOC'
	@echo 'syscfg            -> Generates syscfg files for unit tests'
	@echo 'syscfgClean       -> Cleans syscfg files of unit tests'
	@echo 'syscfg-gui        -> Opens mss sysconfig gui'
	@echo 'mssTestInf        -> Builds all four *_inf images; copies to am273x/build_*_inf/'
	@echo 'testInf           -> syscfg + mssTestInf'
	@echo 'testInfClean      -> syscfgclean + mssTestInfClean'
	@echo '****************************************************************************************'


