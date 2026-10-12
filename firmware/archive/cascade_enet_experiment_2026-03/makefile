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

.PHONY: all clean test testClean mssTest mssTestClean help

ifeq ($(MMWAVE_SDK_DEVICE_TYPE),am273x)
testClean: 	syscfgclean mssTestClean
test: 		syscfg mssTest
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
	@echo '****************************************************************************************'


