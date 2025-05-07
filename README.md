# Mess-Paraver

The [Mess Benchmark](https://github.com/bsc-mem/Mess-benchmark) profiles memory system performance and helps quantify the application pressure to the memory system This is a tool for integrating some of the Mess functionalities with the Paraver tool (https://github.com/bsc-performance-tools/paraver-kernel) in order to help users understand memory system performance and quantify the pressure their applications put to that system.



## Prerequisites

- C++17 compatible compiler
- Python 3.10
- pip (Python package installer)



# Installation

Follow the steps below to install Mess-Paraver:

1. Clone the repository and enter the directory, ensuring you install submodules with the --recursive-submodules flag:

	```
	git clone --recurse-submodules https://github.com/bsc-mem/Mess-Paraver.git
	cd Mess-Paraver/
	```

2. In case you've cloned the directory without the `--recursive-submodules` flag, you can still install the submodules by running:

	```
	git submodule update --init --recursive
	```

3. Install the Python dependencies specified in the `requirements.txt` file:

	```
	pip install -r requirements.txt
	```


Compile the source code to create a binary `mess-prv` file in the `bin` folder:

	make

To use the `mess-prv` binary with Paraver (https://github.com/bsc-performance-tools/paraver-kernel), add the `bin` folder (where the `mess-prv` binary is located) to your PATH. Refer to https://www.baeldung.com/linux/path-variable for instructions on modifying the Linux PATH variable. Future versions of Mess-Paraver will streamline this step.


# Usage

	./bin/mess-prv [OPTION] <input_trace_file.prv> <output_trace_file.prv> <configuration_file.json>

Parameters:

 - `input_trace_file.prv`: The input `.prv` file containing read and write memory counters. Ensure the corresponding `.pcf` and `.row` files are in the same directory.
 - `output_trace_file.prv`: The output path for the generated `.prv` file. If only a directory is specified without an explicit file name, the output will have the same name as the input file. The `.pcf` and `.row` files will also be created in the specified output directory.
 - `configuration_file.json`: A configuration file that primarily indicates the memory and CPU types of the system where the traces were computed. The [`configs`](configs/) folder contains examples. Use the `--supported_systems` flag to view supported configuration options.


# Options

	-m, --memory-channel
		Calculate memory stress metrics per memory channel, rather than per socket (default).

	-e, --expert
		Enables expert mode for interactive plotting. If --plot-interactive is not set, --expert is ignored.
	
	-k, --keep-original
		Keeps the first application of the original trace in the output trace file.
		
	-w, --no-warnings
		Suppress warning messages.
		
	-q, --quiet
		Suppress informational text messages.
		
	-I, --plot-interactive
		Run interactive plots.
		
	-p, --print-supported-systems
		Show supported systems.
		
	-h, --help, ?
		Show help.

# Creating Traces

To generate compatible memory traces, use **EXTRAE** to collect uncore (off-core) counters that capture memory controller activity. These counters provide insights into memory stress and data movement across channels. For instance:

- **CAS_COUNT_RD / CAS_COUNT_WR**: Measures the count of read/write operations by the memory controller.
  
**Required Counters**: At minimum, gather `CAS_COUNT_RD` and `CAS_COUNT_WR` from each Integrated Memory Controller (IMC) per socket. Collecting these counters provides the detailed memory metrics that Mess-Paraver requires.

### Using EXTRAE with Different Architectures

EXTRAE utilizes the **PAPI** library to access performance counters, which provides compatibility with multiple architectures. The necessary counters for memory profiling are automatically expanded by PAPI, allowing you to:

- Provide `CAS_COUNT_RD` and `CAS_COUNT_WR` counters directly accessible through IMCs.
  
However, PAPI’s automatic expansion is generally limited to CPU architectures. For other types of hardware, like **GPUs**, these uncore counters are currently not unsupported through this integration. Thus, profiling with EXTRAE and PAPI currently applies only to CPU-based memory systems.

### Allocating Processes for Uncore Monitoring

EXTRAE requires additional processes to handle uncore counter monitoring, beyond those used for the main application. This ensures sufficient resources for gathering memory activity data without impacting application performance. To allocate these processes, adjust your job script as follows:

1. **Define Counters in XML**:
    Add the `<uncore>` tag in your EXTRAE configuration file (`extrae.xml`) to specify required counters:

    ```
    <counters enabled="yes">
      <uncore enabled="yes">
        UNC_M_CAS_COUNT:RD,UNC_M_CAS_COUNT:WR
      </uncore>
    </counters>
    ```

2. **Allocate Extra Processes in the Job Script**:
   Request additional processes per node dedicated to reading uncore counters. This ensures EXTRAE has the resources needed to handle the uncore data collection separately from your application’s main processes.

    ```
    #SBATCH --ntasks=<app_tasks + (uncore_processes x node)>
    #SBATCH --constraint=perfparanoid
	
    module load gcc extrae
    $EXTRAE_HOME/bin/extrae-uncore ./extrae.xml libseqtrace.so ./application
    ```



# Tests

For running tests, execute the following command:

	./tests/run_tests.py

This command first compiles the source code to ensure the latest version is being tested.


# License

The Mess-Paraver code is released under the BSD-3 [License](LICENSE.txt).
