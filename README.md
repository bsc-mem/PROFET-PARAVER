# PROFET-PARAVER

The PROFiling-based EsTimation of performance and energy (PROFET) tool (https://github.com/bsc-mem/PROFET) profiles memory system performance, quantifies the application pressure to the memory system and estimates application performance on hardware platforms with novel memory systems. This is a tool for integrating some of the PROFET functionalities with the Paraver tool (https://github.com/bsc-performance-tools/paraver-kernel) in order to help users understand memory system performance and quantify the pressure their applications put to that system.


# Installation

Follow the steps below to install PROFET-PARAVER:

1. Clone the repository and enter the directory, ensuring you install submodules with the --recursive-submodules flag:

	```
	git clone --recurse-submodules https://github.com/bsc-mem/PROFET-PARAVER.git
	cd PROFET-PARAVER/
	```

2. In case you've cloned the directory without the --recursive-submodules flag, you can still install the submodules by running:

	```git submodule update --init --recursive```

3. Install the Python dependencies specified in the `requirements.txt` file:

	```pip install -r requirements.txt```

Compile the source code to create a binary `profet` file in the `bin` folder:

	make

To use the `profet` binary with Paraver (https://github.com/bsc-performance-tools/paraver-kernel), add the `bin` folder (where the `profet` binary is located) to your PATH. Refer to https://www.baeldung.com/linux/path-variable for instructions on modifying the Linux PATH variable. Future versions of PROFET-PARAVER will streamline this step.


# Usage

	./bin/profet [OPTION] <input_trace_file.prv> <output_trace_file.prv> <configuration_file.json>

Parameters:

 - `input_trace_file.prv`: The input `.prv` file containing read and write memory counters. Ensure the corresponding `.pcf` and `.row` files are in the same directory.
 - `output_trace_file.prv`: The output path for the generated `.prv` file. If only a directory is specified without an explicit file name, the output will have the same name as the input file. The `.pcf` and `.row` files will also be created in the specified output directory.
 - `configuration_file.json`: A configuration file that primarily indicates the memory and CPU types of the system where the traces were computed. The [`configs`](configs/) folder contains examples. Use the `--supported_systems` flag to view supported configuration options.


# Options

	-s, --socket
		Calculate memory stress metrics per socket, rather than per memory channel (default).
		
	-w, --no_warnings
		Suppress warning messages.
		
	-t, --no_text
		Suppress informational text messages.
		
	-d, --no_dash
		Do not run dash (interactive plots).
		
	--supported_systems
		Show supported memory systems.
		
	-h, --help, ?
		Show help.


# Tests

For running tests, execute the following command:

	./tests/run_tests.py

This command first compiles the source code to ensure the latest version is being tested.


# License

The PROFET-PARAVER code is released under the BSD-3 [License](LICENSE.txt).