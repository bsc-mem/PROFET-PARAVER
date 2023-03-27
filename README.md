# PROFET-PARAVER

The PROFiling-based EsTimation of performance and energy (PROFET) tool (https://github.com/bsc-mem/PROFET) profiles memory system performance, quantifies the application pressure to the memory system and estimates application performance on hardware platforms with novel memory systems. This is a tool for integrating some of the PROFET functionalities with the Paraver tool (https://github.com/bsc-performance-tools/paraver-kernel) in order to help users understand memory system performance and quantify the pressure their applications put to that system.


# Installation

Clone the repository and go into the directory. Use the `--recursive-submodules` flag for installing submodules.

	git clone --recurse-submodules https://gitlab.bsc.es/isaac.boixaderas/extrae-profet-paraver-internal.git
	cd profet/

In case you cloned the directory without using `--recursive-submodules`, you can still install them by running:

	git submodule update --init --recursive

Install Python requirements according to the configuration file `requirements.txt`.

	pip install -r requirements.txt

Compile, creating a binary `profet` file in the `bin` folder.

	make

For being able to use this binary from Paraver (https://github.com/bsc-performance-tools/paraver-kernel), include the `bin` folder (where the `profet` binary was installed) to your PATH. See https://www.baeldung.com/linux/path-variable for more information on how to change the Linux PATH variable. In future versions we will improve the installation of PROFET so you do not need to modify your PATH.


# Usage

	./bin/profet [OPTION] <input_trace_file.prv> <output_trace_file.prv> <configuration_file.json>

Where:

 - `input_trace_file.prv` is the `.prv` file containing read and write memory counters. It must contain `.pcf` and `.row` files in the same directory.
 - `output_trace_file.prv` is the path where the output `.prv` file will be written. If only the directory is specified without an explicit file name, the output will have the same name as the input file. `.pcf` and `.row` files are also created in the same output directory.
 - `configuration_file.json` is a configuration file mainly for indicating the type of memory and CPU of the system where the traces were computed. There are some examples in [`configs`](configs/) folder. You can check the supported configuration options with the `--supported_systems` flag.


# Options

	-s, --socket
		Compute memory stress metrics per socket instead of per memory channel (by default).
		
	-w, --no_warnings
		Do not show warning messages.
		
	-t, --no_text
		Do not show info text messages.
		
	-d, --no_dash
		Do not run dash (interactive plots).
		
	--supported_systems
		Show currently supported memory systems.
		
	-h, --help, ?
		Show help.


# Tests

For running tests, execute the following command:

	./tests/run_tests.py

First it compiles the source code in order to make sure to test the last version of the code.


# License

The PROFET code is released under the BSD-3 [License](LICENSE.txt).