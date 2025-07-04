##############################################################################
#  Mess-Paraver portable Makefile
#  – works with system Python, virtualenv, conda, pyenv, Homebrew …
##############################################################################

# -------- user-tweakables ---------------------------------------------------
PYTHON      ?= python3          # interpreter to embed
REQ_FILE    ?= requirements.txt# pip requirements to bundle
##############################################################################

# We need bash features later ( [[ … ]] )
SHELL := /bin/bash

# --- 1. Verify we have an interpreter ≥ 3.7 --------------------------------
PY_OK := $(shell $(PYTHON) -c 'import sys; print("ok" if sys.version_info>=(3,7) else "bad")' 2>/dev/null || echo bad)

ifeq ($(PY_OK),bad)
  $(error "$(PYTHON) is missing or < 3.7 – run 'make PYTHON=/path/to/python3.12'")
endif

# --- 2. Locate the matching python-config script ---------------------------
PY_VER := $(shell $(PYTHON) -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')

PY_CONFIG := $(shell command -v "$(PYTHON)-config" 2>/dev/null || \
                      command -v "python$(PY_VER)-config" 2>/dev/null)

ifeq ($(PY_CONFIG),)
  $(error "Cannot find python-config for $(PYTHON). Install python$(PY_VER)-dev.")
endif

# --- 3. Compiler & linker flags -------------------------------------------
PY_CFLAGS  := $(shell $(PY_CONFIG) --includes)

# ≥ 3.8: --embed adds -lpython… ; older: plain --ldflags
PY_LDFLAGS := $(shell $(PY_CONFIG) --ldflags --embed 2>/dev/null || $(PY_CONFIG) --ldflags)

# Fallback: if still no -lpython… try pkg-config
ifeq ($(findstring -lpython,$(PY_LDFLAGS)),)
  PKG_LIBS  := $(shell pkg-config --libs python-$(PY_VER)-embed 2>/dev/null || \
                          pkg-config --libs python-$(PY_VER) 2>/dev/null)
  ifneq ($(PKG_LIBS),)
    PY_LDFLAGS := $(PKG_LIBS)
  endif
endif

# --- 4. Source lists -------------------------------------------------------
SRC_CPP_FILES := $(shell find src/ -name '*.cpp')
SRC_CC_FILES  := $(shell find src/ -name '*.cc')

# --- 5. Paths --------------------------------------------------------------
BIN_DIR  := bin
MESS_PATH := libs/PROFET

ifeq ($(shell uname -m),x86_64)
  WHEEL_DIR := $(BIN_DIR)/python_libs_x86_64
else
  WHEEL_DIR := $(BIN_DIR)/python_libs_arm64
endif

# --- 6. Targets ------------------------------------------------------------
all: install_mess compile_cpp bundle_python_libs

$(BIN_DIR):
	@mkdir -p $@

compile_cpp: | $(BIN_DIR)
	g++ -Wall -Wno-c++11-narrowing -std=c++17 -fPIE \
	    $(PY_CFLAGS) \
	    -I libs/paraver-kernel/utils/traceparser \
	    -I libs/boost_1_79_0 \
	    -I libs/json-develop \
	    -o $(BIN_DIR)/mess-prv $(SRC_CPP_FILES) $(SRC_CC_FILES) \
	    $(PY_LDFLAGS) \
	    $(shell if [[ $$(uname) == Linux ]] && [[ $$(g++ -dumpversion | cut -d. -f1) -lt 8 ]]; then echo -lstdc++fs; fi)

install_mess:
	@command -v pip >/dev/null 2>&1 || { echo "pip is required but not installed."; exit 1; }
	@echo "Installing Python dependencies from $(MESS_PATH)…"
	@$(PYTHON) -m pip install -e $(MESS_PATH)

bundle_python_libs: | $(BIN_DIR)
	@echo "Bundling wheels into $(WHEEL_DIR)"
	@rm -rf "$(WHEEL_DIR)"
	@mkdir -p "$(WHEEL_DIR)"
	@$(PYTHON) -m pip install --upgrade --no-compile --no-cache-dir --target="$(WHEEL_DIR)" -r $(REQ_FILE)
	@echo "Installing MESS into $(WHEEL_DIR)…"
	@$(PYTHON) -m pip install --upgrade --no-compile --no-cache-dir --no-deps --target="$(WHEEL_DIR)" "$(MESS_PATH)"


clean:
	@echo "Cleaning up…"
	@rm -rf $(BIN_DIR)/
	@echo "Done."

.PHONY: all compile_cpp install_mess bundle_python_libs clean
