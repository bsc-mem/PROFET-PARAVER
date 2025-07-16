/* Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
 * You may use, distribute and modify this code under the
 * terms of the BSD-3 license.
 *
 * You should have received a copy of the BSD-3 license with
 * this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
 */

// profetpyadapter.cpp
#include "profetpyadapter.h"
using namespace std;


ProfetPyAdapter::ProfetPyAdapter() {}


ProfetPyAdapter::ProfetPyAdapter(string projectPath) {
    Py_Initialize();  // initialize Python
    setPathVariables(projectPath);
    loadProfetIntegrationModule();
}

ProfetPyAdapter::ProfetPyAdapter(string projectPath, string cpuModel, string memorySystem, bool displayWarnings = true) {
    Py_Initialize();  // initialize Python
    setPathVariables(projectPath);
    loadProfetIntegrationModule();

    this->cpuModel = cpuModel;
    this->memorySystem = memorySystem;
    PyObject* row = getRowFromDB();
    pmuType = getPyDictString(row, "pmu_type");
    cpuMicroarch = getPyDictString(row, "cpu_microarchitecture");

    curvesPath = getCurvesPath();
    // Set display warnings in Python module
    setDisplayWarnings(displayWarnings);
    // Set the curves in the Python module
    setCurves(projectDataPath, cpuModel, memorySystem);
    // Set the curves in C++ maps
    setCurvesBwsLats(curvesPath, curves, pyCurves);
}

ProfetPyAdapter::~ProfetPyAdapter() {
    // Stop python interpreter
    Py_Finalize();
}

void ProfetPyAdapter::setPathVariables(string projectPath) {
    this->projectPath = projectPath;
    projectSrcPath = projectPath + "src/";
    projectDataPath = projectPath + "data/";
    profetIntegrationPath = projectSrcPath + "cpp_py_adaptation/";
}

void ProfetPyAdapter::loadProfetIntegrationModule() {
    // profetIntegrationPath must be initialized
    
    // Set relative path (current directory) for importing modules
    sysPath = PySys_GetObject((char*)"path");
    PyList_Append(sysPath, PyUnicode_FromString(profetIntegrationPath.c_str()));

    // Load PROFET integration module
    profetIntegrationModule = PyImport_ImportModule("profet_integration");
    raisePyErrorIfNull(profetIntegrationModule, "ERROR when importing \"mess_integration\" module.");
}

PyObject* ProfetPyAdapter::getRowFromDB() {
    PyObject* rowDbFn = getFunctionFromProfetIntegration("get_row_from_db");
    // Get curves path
    // Make sure string arguments are built with .c_str()
    PyObject* pArgs = Py_BuildValue("(sss)", projectDataPath.c_str(), cpuModel.c_str(), memorySystem.c_str());
    PyObject* row = PyObject_CallObject(rowDbFn, pArgs);
    raisePyErrorIfNull(row, "ERROR getting Python dictionary with memory values.");

    return row;
}

string ProfetPyAdapter::getCurvesPath() {
    // Get curves path
    PyObject* curvesFn = getFunctionFromProfetIntegration("get_curves_path");
    // Make sure string arguments are built with .c_str()
    PyObject* pArgs = Py_BuildValue("(sssss)", projectDataPath.c_str(), cpuModel.c_str(), memorySystem.c_str(), pmuType.c_str(), cpuMicroarch.c_str());
    PyObject* curvesPath = PyObject_CallObject(curvesFn, pArgs);
    raisePyErrorIfNull(curvesPath, "ERROR getting Python dictionary with memory values.");

    // Return PyObject as string
    return _PyUnicode_AsString(curvesPath);
}

 void ProfetPyAdapter::setCurvesBwsLats(string curvesPath, map<int, pair<vector<double>, vector<double>>> &curves, map<int, pair<PyObject*, PyObject*>> &pyCurves) {
    // Get available read ratios for the given curves
    PyObject* readRatiosFn = getFunctionFromProfetIntegration("get_curves_available_read_ratios");
    PyObject* pArgs = Py_BuildValue("()");
    PyObject* readRatios = PyObject_CallObject(readRatiosFn, pArgs);
    raisePyErrorIfNull(readRatios, "ERROR getting available read ratios.");

    // Get bandwidths and latencies for each read ratio
    Py_ssize_t size = PyList_Size(readRatios);
    for (Py_ssize_t i = 0; i < size; ++i) {
        // Get read ratio
        PyObject* pItem = PyList_GetItem(readRatios, i);
        double readRatio = PyFloat_AsDouble(pItem);
        availableReadRatios.push_back(readRatio);

        PyObject* curveFn = getFunctionFromProfetIntegration("get_curve");
        PyObject* pArgs = Py_BuildValue("(f)", readRatio);
        PyObject* curve = PyObject_CallObject(curveFn, pArgs);
        raisePyErrorIfNull(curve, "ERROR getting curve.");

        // Get bandwidths and latencies
        PyObject* bws = PyObject_GetAttrString(curve, "bws");
        PyObject* lats = PyObject_GetAttrString(curve, "lats");

        // Convert the Python lists to C++ vectors
        Py_ssize_t bwSize = PyList_Size(bws);
        Py_ssize_t latSize = PyList_Size(lats);
        if (bwSize != latSize) {
            cerr << "ERROR: bandwidths and latencies lists have different sizes." << endl;
            exit(1);
        }
        vector<double> bwsVector(bwSize);
        vector<double> latsVector(latSize);
        PyObject* pyBws = PyList_New(bwSize);
        PyObject* pyLats = PyList_New(latSize);

        for (Py_ssize_t i = 0; i < bwSize; ++i) {
            PyObject* bwItem = PyList_GetItem(bws, i);
            PyObject* latItem = PyList_GetItem(lats, i);

            PyList_SetItem(pyBws, i, bwItem);
            if (PyFloat_Check(bwItem)) {
                double bw = PyFloat_AsDouble(bwItem);
                bwsVector[i] = bw;
            }

            PyList_SetItem(pyLats, i, latItem);
            if (PyFloat_Check(latItem)) {
                double lat = PyFloat_AsDouble(latItem);
                latsVector[i] = lat;
            }
        }

        curves.insert({readRatio, {bwsVector, latsVector}});
        pyCurves.insert({readRatio, {pyBws, pyLats}});
    }

    // Sort available read ratios
    sort(availableReadRatios.begin(), availableReadRatios.end());
}

void ProfetPyAdapter::checkSystemSupported() {
    PyObject* checkSystemSupportedFn = getFunctionFromProfetIntegration("check_curves_exist");
    // Make sure string arguments are built with .c_str()
    PyObject* pArgs = Py_BuildValue("(sss)", projectDataPath.c_str(), cpuModel.c_str(), memorySystem.c_str());
    PyObject_CallObject(checkSystemSupportedFn, pArgs);
    // raisePyErrorIfNull(curvesPath, "ERROR checking  values.");
}

void ProfetPyAdapter::printSupportedSystems() {
    PyObject* printSupportedSystemsFn = getFunctionFromProfetIntegration("print_supported_systems");
    PyObject* pArgs = Py_BuildValue("(s)", projectDataPath.c_str());
    PyObject_CallObject(printSupportedSystemsFn, pArgs);
}

tuple<double, double, double, double, double, double> ProfetPyAdapter::computeMemoryMetrics(double cpuFreqGHz, double writeRatio, double bandwidth, bool groupMCs, int MCsPerSocket) {
    // Get dictionary with computed memory values
    PyObject* memoryMetricsFn = getFunctionFromProfetIntegration("get_memory_properties_from_bw");
    // Make sure string arguments are built with .c_str()
    double readRatio = 1 - writeRatio;
    double closestReadRatio = getClosestValue(availableReadRatios, readRatio);
    PyObject* pArgs = PyTuple_Pack(6, PyFloat_FromDouble(cpuFreqGHz), PyFloat_FromDouble(writeRatio),
                                   PyFloat_FromDouble(closestReadRatio), PyFloat_FromDouble(bandwidth), PyBool_FromLong(static_cast<long>(groupMCs)),
                                   PyLong_FromLong(MCsPerSocket));
    PyObject* memDict = PyObject_CallObject(memoryMetricsFn, pArgs);
    raisePyErrorIfNull(memDict, "ERROR getting Python dictionary with memory values.");

    // Get values of dictionary elements
    // double returnedBandwidth = getPyDictDouble(memDict, "bandwidth");
    double maxBandwidth = getPyDictDouble(memDict, "max_bandwidth");
    double latency = getPyDictDouble(memDict, "latency");
    double leadOffLatency = getPyDictDouble(memDict, "lead_off_latency");
    double maxLatency = getPyDictDouble(memDict, "max_latency");
    double stressScore = getPyDictDouble(memDict, "stress_score");
    double bw = getPyDictDouble(memDict, "bandwidth");

    return {maxBandwidth, latency, leadOffLatency, maxLatency, stressScore, bw};
}

void ProfetPyAdapter::runDashApp(string traceFilePath, double precision, double cpuFreq, bool expertMode, bool keepOriginalTraceFile) {
    // Make sure the trace file path is a canonical absolute path
    string traceFileAbsPath = fs::canonical(traceFilePath).string();

    // Write dash config JSON file
    json dashConfig = {
        {"precision", int(precision)},
        {"cpu_freq", cpuFreq},
    };
    string dashConfigFile = regex_replace(traceFileAbsPath, regex(".prv"), ".dashboard.config.json");
    ofstream o(dashConfigFile);
    o << setw(4) << dashConfig << endl;

    if (!projectPath.empty() && projectPath.back() == '/')
    {
        projectPath.pop_back();
    }

    //Mess-Paraver/bin/src --> 

    
    // The path we start with, before any corrections
    std::string originalPath = projectPath;
    fs::path basePath;
    
    // First attempt - handle the double slash issue if present
    std::string initialCorrectedPath = projectPath;
    size_t doubleSlashPos = initialCorrectedPath.find("//");
    if (doubleSlashPos != std::string::npos) {
        // Simple replacement of double slash with single slash
        initialCorrectedPath = initialCorrectedPath.substr(0, doubleSlashPos) + "/" + initialCorrectedPath.substr(doubleSlashPos + 2);
        std::cerr << "Fixed double slash: " << initialCorrectedPath << std::endl;
    }
    
    try {
        basePath = fs::path(initialCorrectedPath);
    } catch(const std::exception& e) {
        std::cerr << "Error creating path from " << initialCorrectedPath << ": " << e.what() << std::endl;
        basePath = fs::current_path();
    }
    
    // Find the Mess-Paraver directory using an algorithm similar to _find_mp_root in Python
    fs::path messParaverRoot;
    bool found = false;
    
    // 1. Check if the base path or any ancestor is named "Mess-Paraver"
    fs::path currentPath = basePath;
    while (!found && !currentPath.empty()) {
        if (fs::exists(currentPath) && fs::is_directory(currentPath)) {
            if (currentPath.filename().string().find("Mess-Paraver") != std::string::npos) {
                messParaverRoot = currentPath;
                found = true;
                std::cerr << "Found Mess-Paraver at ancestor: " << messParaverRoot.string() << std::endl;
                break;
            }
        }
        if (currentPath.has_parent_path() && currentPath != currentPath.parent_path()) {
            currentPath = currentPath.parent_path();
        } else {
            break;
        }
    }
    
    // 2. If not found, try to locate it with limited BFS under existing directories
    if (!found) {
        // Find the first existing parent directory to start search from
        fs::path searchRoot = basePath;
        while (!searchRoot.empty() && !fs::exists(searchRoot)) {
            if (searchRoot.has_parent_path() && searchRoot != searchRoot.parent_path()) {
                searchRoot = searchRoot.parent_path();
            } else {
                break;
            }
        }
        
        if (fs::exists(searchRoot)) {
            std::cerr << "Searching for Mess-Paraver under " << searchRoot.string() << std::endl;
            try {
                // Recursive search with depth limit
                int maxDepth = 3;
                std::function<bool(const fs::path&, int)> searchDir = [&](const fs::path& dir, int depth) {
                    if (depth > maxDepth) return false;
                    
                    try {
                        for (const auto& entry : fs::directory_iterator(dir)) {
                            if (fs::is_directory(entry.path())) {
                                if (entry.path().filename().string().find("Mess-Paraver") != std::string::npos) {
                                    messParaverRoot = entry.path();
                                    found = true;
                                    std::cerr << "Found Mess-Paraver at: " << messParaverRoot.string() << std::endl;
                                    return true;
                                }
                                if (searchDir(entry.path(), depth + 1)) {
                                    return true;
                                }
                            }
                        }
                    } catch (const std::exception& e) {
                        std::cerr << "Error searching directory " << dir.string() << ": " << e.what() << std::endl;
                    }
                    return false;
                };
                
                searchDir(searchRoot, 0);
            } catch (const std::exception& e) {
                std::cerr << "Error during directory search: " << e.what() << std::endl;
            }
        }
    }
    
    // Generate the path to dash_plots.py
    std::string dashPlotsPath;
    if (found) {
        // Check different possible locations for interactive_plots directory
        std::vector<fs::path> possiblePaths = {
            messParaverRoot / "src" / "interactive_plots" / "dash_plots.py",
            messParaverRoot / "bin" / "src" / "interactive_plots" / "dash_plots.py",
            messParaverRoot / ".." / "bin" / "src" / "interactive_plots" / "dash_plots.py"
        };
        
        for (const auto& path : possiblePaths) {
            if (fs::exists(path)) {
                dashPlotsPath = "'" + path.string() + "'";
                std::cerr << "Found dash_plots.py at: " << path.string() << std::endl;
                break;
            }
        }
    }
    
    // If still not found, fall back to original path with a warning
    if (dashPlotsPath.empty()) {
        std::cerr << "Warning: Could not find dash_plots.py, falling back to original path" << std::endl;
        dashPlotsPath = "'" + projectPath + "/src/interactive_plots/dash_plots.py'";
    }
    

    string expert = "";
    if (expertMode) {
        expert = "--expert";
    }
    string pythonCall = "python3 " + dashPlotsPath + " " + expert + " \'"  + traceFileAbsPath + "\' \'"  + curvesPath + "\' \'" + dashConfigFile + "\'";
    if (keepOriginalTraceFile) {
        pythonCall += " --keep-original";
    }

    // Create dashboard execution script for running it later
    string dashScriptFile = regex_replace(traceFileAbsPath, regex(".prv"), ".dashboard.sh");
    // Create and open a file
    ofstream scriptContent(dashScriptFile);
    string featherTraceFile = regex_replace(traceFileAbsPath, regex(".prv"), ".feather");
    string scriptPyCall = "python3 " + dashPlotsPath + " " + expert + " \'"  + featherTraceFile + "\' \'"  + curvesPath + "\' \'" + dashConfigFile + "\'";
    if (keepOriginalTraceFile) {
        scriptPyCall += " --keep-original";
    }
    // Write to the file
    scriptContent << "#!/bin/bash\n\n";
    scriptContent << scriptPyCall;
    // Close the file
    scriptContent.close();
    // Set file permissions
    int permissions = S_IRUSR | S_IWUSR | S_IXUSR | S_IRGRP | S_IROTH;
    int result = chmod(dashScriptFile.c_str(), permissions);
    if (result != 0) {
        cerr << "Failed to set file permissions." << endl;
    }

    // Generate PDF image and save feather DF by default when running dash from here
    string pythonCallPDF = pythonCall + " --save-feather";
    // Run dash
    system(pythonCallPDF.c_str());
}

PyObject* ProfetPyAdapter::getFunctionFromProfetIntegration(string fnName) {
    // Get function from module
    PyObject* pyFn = PyObject_GetAttrString(profetIntegrationModule, fnName.c_str());
    raisePyErrorIfNull(pyFn, "ERROR getting \"" + fnName + "\" attribute.");
    return pyFn;
}

void ProfetPyAdapter::setDisplayWarnings(bool displayWarnings) {
    // Set display warnings in Python module
    PyObject* setDisplayWarningsFn = getFunctionFromProfetIntegration("set_display_warnings");
    // Make sure string arguments are built with .c_str()
    PyObject* pArgs = Py_BuildValue("(i)", displayWarnings ? 1 : 0);
    PyObject* status = PyObject_CallObject(setDisplayWarningsFn, pArgs);
    raisePyErrorIfNull(status, "ERROR setting display_warnings in Python module.");
}

void ProfetPyAdapter::setCurves(string projectDataPath, string cpuModel, string memorySystem) {
    PyObject* setCurvesFn = getFunctionFromProfetIntegration("set_curves");
    // Make sure string arguments are built with .c_str()
    PyObject* pArgs = Py_BuildValue("(sss)", projectDataPath.c_str(), cpuModel.c_str(), memorySystem.c_str());
    PyObject* status = PyObject_CallObject(setCurvesFn, pArgs);
    raisePyErrorIfNull(status, "ERROR setting curves in Python module.");
}
