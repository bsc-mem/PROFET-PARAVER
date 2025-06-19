PYTHON ?= python3

# Validate Python version
PYTHON_VERSION_OK := $(shell "$(PYTHON)" -c 'import sys; print("ok" if sys.version_info >= (3,7) else "bad")' 2>/dev/null || echo "bad")

ifeq ($(PYTHON_VERSION_OK),bad)
$(error "$(PYTHON)" is missing or too old. Use 'make PYTHON=/path/to/python3.11' to specify manually)
endif


# extract python flags for compilation
PY_VERSION_FULL := $(wordlist 2, 4, $(subst ., ,$(shell "$(PYTHON)" --version 2>&1)))
PY_VERSION_MAJOR := $(word 1, ${PY_VERSION_FULL})
PY_VERSION_MINOR := $(word 2, ${PY_VERSION_FULL})
# PY_VERSION_PATCH := $(word 3, ${PY_VERSION_FULL})

PY_CFLAGS  := $(shell "$(PYTHON)-config" --cflags)

# use libs or embed depending on python version
ifeq ($(shell expr $(PY_VERSION_MINOR) \<= 6), 1)
	PY_LDFLAGS := $(shell "$(PYTHON)-config" --ldflags --libs)
else
	PY_LDFLAGS := $(shell "$(PYTHON)-config" --ldflags --embed)
endif

# create bin directory if it does not exist
$(shell mkdir -p bin/)

# get all cpp files in src/ folder and its subdirectories
SRC_CPP_FILES := $(shell find src/ -name '*.cpp')
SRC_CC_FILES := $(shell find src/ -name '*.cc')

# path to the MESS submodule in the libs folder
MESS_PATH := libs/PROFET
MESS_WHEEL_BUILD_DIR := $(MESS_PATH)/dist # Temporary directory for mess wheel

all: install_mess compile_cpp bundle_python_libs

clean:
	@echo "Cleaning up..."
	@rm -rf bin/
	@echo "Cleaned up."

install_mess:
	@command -v pip > /dev/null 2>&1 || { echo >&2 "pip is required but not installed. Please install pip and try again."; exit 1; }
	@echo "Installing Python dependencies from ${MESS_PATH}..."
	@$(PYTHON) -m pip install -e ${MESS_PATH}

compile_cpp:
	g++ -Wall -Wno-c++11-narrowing -fPIE -std=c++17 \
	$(PY_CFLAGS) \
	-I libs/paraver-kernel/utils/traceparser \
	-I libs/boost_1_79_0 \
	-I libs/json-develop/ \
	-o bin/mess-prv $(SRC_CPP_FILES) $(SRC_CC_FILES) $(PY_LDFLAGS) $(shell if [ `uname` = "Linux" ] && [ `g++ -dumpversion | cut -f1 -d.` -lt 8 ]; then echo -lstdc++fs; fi)

REQ_FILE    ?= requirements.txt

ifeq ($(shell arch),x86_64)
    WHEEL_DIR = bin/python_libs_x86_64
else
    WHEEL_DIR = bin/python_libs_arm64
endif

bundle_python_libs:
	@echo "Bundling wheels into $(WHEEL_DIR)"
	@rm -rf "$(WHEEL_DIR)"
	@mkdir -p "$(WHEEL_DIR)"
	
	# Install dependencies from main requirements.txt
	@$(PYTHON) -m pip install --no-compile --no-cache-dir \
		--target="$(WHEEL_DIR)" -r "$(REQ_FILE)"
	
	# Install MESS directly into WHEEL_DIR
	@echo "Installing MESS into $(WHEEL_DIR)..."
	@$(PYTHON) -m pip install --no-compile --no-cache-dir --no-deps \
		--target="$(WHEEL_DIR)" "$(MESS_PATH)"
	
.PHONY: all install_mess compile_cpp bundle_python_libs


