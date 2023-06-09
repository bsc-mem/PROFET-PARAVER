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
    // curves = Curves(curvesPath, displayWarnings);
    setCurvesBwsLats(curvesPath, curves, pyCurves);
}

ProfetPyAdapter::~ProfetPyAdapter() {
    // Stop python interpreter
    Py_Finalize();
}

void ProfetPyAdapter::setPathVariables(string projectPath) {
    this->projectPath = projectPath;
    projectSrcPath = projectPath + "src/";
    profetIntegrationPath = projectSrcPath + "cpp_py_adaptation/";
    pyProfetPath = projectSrcPath + "py_profet/";
}

void ProfetPyAdapter::loadProfetIntegrationModule() {
    // profetIntegrationPath must be initialized

    // Set relative path (current directory) for importing modules
    sysPath = PySys_GetObject((char*)"path");
    PyList_Append(sysPath, PyUnicode_FromString(profetIntegrationPath.c_str()));

    // Load PROFET integration module
    profetIntegrationModule = PyImport_ImportModule("profet_integration");
    raisePyErrorIfNull(profetIntegrationModule, "ERROR when importing \"profet_integration\" module.");
}

PyObject* ProfetPyAdapter::getRowFromDB() {
    PyObject* rowDbFn = getFunctionFromProfetIntegration("get_row_from_db");
    // Get curves path
    // Make sure string arguments are built with .c_str()
    PyObject* pArgs = Py_BuildValue("(sss)", pyProfetPath.c_str(), cpuModel.c_str(), memorySystem.c_str());
    PyObject* row = PyObject_CallObject(rowDbFn, pArgs);
    raisePyErrorIfNull(row, "ERROR getting Python dictionary with memory values.");

    return row;
}

string ProfetPyAdapter::getCurvesPath() {
    // Get curves path
    PyObject* curvesFn = getFunctionFromProfetIntegration("get_curves_path");
    // Make sure string arguments are built with .c_str()
    PyObject* pArgs = Py_BuildValue("(sssss)", pyProfetPath.c_str(), cpuModel.c_str(), memorySystem.c_str(), pmuType.c_str(), cpuMicroarch.c_str());
    PyObject* curvesPath = PyObject_CallObject(curvesFn, pArgs);
    raisePyErrorIfNull(curvesPath, "ERROR getting Python dictionary with memory values.");

    // Return PyObject as string
    return _PyUnicode_AsString(curvesPath);
}

 void ProfetPyAdapter::setCurvesBwsLats(string curvesPath, map<int, pair<vector<float>, vector<float>>> &curves, map<int, pair<PyObject*, PyObject*>> &pyCurves) {
    // Get available read ratios for the given curves
    PyObject* readRatiosFn = getFunctionFromProfetIntegration("get_curves_available_read_ratios");
    // Make sure string arguments are built with .c_str()
    PyObject* pArgs = Py_BuildValue("(s)", curvesPath.c_str());
    PyObject* readRatios = PyObject_CallObject(readRatiosFn, pArgs);
    raisePyErrorIfNull(readRatios, "ERROR getting available read ratios.");

    // Get bandwidths and latencies for each read ratio
    Py_ssize_t size = PyList_Size(readRatios);
    for (Py_ssize_t i = 0; i < size; ++i) {
        // Get read ratio
        PyObject* pItem = PyList_GetItem(readRatios, i);
        float readRatio = PyFloat_AsDouble(pItem);
        availableReadRatios.push_back(readRatio);

        PyObject* curveFn = getFunctionFromProfetIntegration("get_curve");
        // Make sure string arguments are built with .c_str()
        PyObject* pArgs = Py_BuildValue("(sf)", curvesPath.c_str(), readRatio);
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
        vector<float> bwsVector(bwSize);
        vector<float> latsVector(latSize);
        PyObject* pyBws = PyList_New(bwSize);
        PyObject* pyLats = PyList_New(latSize);

        for (Py_ssize_t i = 0; i < bwSize; ++i) {
            PyObject* bwItem = PyList_GetItem(bws, i);
            PyObject* latItem = PyList_GetItem(lats, i);

            PyList_SetItem(pyBws, i, bwItem);
            if (PyFloat_Check(bwItem)) {
                float bw = PyFloat_AsDouble(bwItem);
                bwsVector[i] = bw;
            }

            PyList_SetItem(pyLats, i, latItem);
            if (PyFloat_Check(latItem)) {
                float lat = PyFloat_AsDouble(latItem);
                latsVector[i] = lat;
            }
        }

        curves.insert({readRatio, {bwsVector, latsVector}});
        pyCurves.insert({readRatio, {pyBws, pyLats}});
    }
}

void ProfetPyAdapter::checkSystemSupported() {
    PyObject* checkSystemSupportedFn = getFunctionFromProfetIntegration("check_curves_exist");
    // Make sure string arguments are built with .c_str()
    PyObject* pArgs = Py_BuildValue("(sss)", pyProfetPath.c_str(), cpuModel.c_str(), memorySystem.c_str());
    PyObject_CallObject(checkSystemSupportedFn, pArgs);
    // raisePyErrorIfNull(curvesPath, "ERROR checking  values.");
}

void ProfetPyAdapter::printSupportedSystems() {
    PyObject* printSupportedSystemsFn = getFunctionFromProfetIntegration("print_supported_systems");
    PyObject* pArgs = Py_BuildValue("(s)", pyProfetPath.c_str());
    PyObject_CallObject(printSupportedSystemsFn, pArgs);
}

tuple<float, float, float, float, float> ProfetPyAdapter::computeMemoryMetrics(float cpuFreqGHz, float writeRatio, float bandwidth, bool displayWarnings) {
    // Get dictionary with computed memory values
    PyObject* memoryMetricsFn = getFunctionFromProfetIntegration("get_memory_properties_from_bw");
    // Make sure string arguments are built with .c_str()
    float readRatio = 100 - writeRatio * 100;
    float closestReadRatio = getClosestValue(availableReadRatios, readRatio);
    PyObject* bws = pyCurves[closestReadRatio].first;
    PyObject* lats = pyCurves[closestReadRatio].second;
    PyObject* pArgs = PyTuple_Pack(6, bws, lats, PyFloat_FromDouble(cpuFreqGHz), PyFloat_FromDouble(writeRatio),
                                   PyFloat_FromDouble(bandwidth), PyBool_FromLong(displayWarnings ? 1 : 0));
    PyObject* memDict = PyObject_CallObject(memoryMetricsFn, pArgs);
    raisePyErrorIfNull(memDict, "ERROR getting Python dictionary with memory values.");

    // Get values of dictionary elements
    // float returnedBandwidth = getPyDictFloat(memDict, "bandwidth");
    float maxBandwidth = getPyDictFloat(memDict, "max_bandwidth");
    float latency = getPyDictFloat(memDict, "latency");
    float leadOffLatency = getPyDictFloat(memDict, "lead_off_latency");
    float maxLatency = getPyDictFloat(memDict, "max_latency");
    float stressScore = getPyDictFloat(memDict, "stress_score");

    return {maxBandwidth, latency, leadOffLatency, maxLatency, stressScore};
}

void ProfetPyAdapter::runDashApp(string traceFilePath, float precision, float cpuFreq, bool keepOriginalTraceFile) {
    string dashPlotsPath = pyProfetPath + "dash_plots.py";
    string traceFileFlag = " --trace-file " + traceFilePath;
    string curvesDirFlag = " --bw-lat-curves-dir " + curvesPath;
    string precisionFlag = " --precision " + to_string(int(precision));
    string cpuFreqFlag = " --cpufreq " + to_string(cpuFreq);
    string pythonCall = "python3 " + dashPlotsPath + traceFileFlag + curvesDirFlag + precisionFlag + cpuFreqFlag;
    if (!keepOriginalTraceFile) {
        pythonCall += " --excluded-original";
    }

    // Create dashboard execution script for running it later
    string dashScriptFile = regex_replace(traceFilePath, regex(".prv"), ".dashboard.sh");
    // Create and open a file
    ofstream scriptContent(dashScriptFile);
    string featherTraceFileFlag = " --trace-file " + regex_replace(traceFilePath, regex(".prv"), ".feather");
    string scriptPyCall = "python3 " + dashPlotsPath + featherTraceFileFlag + curvesDirFlag + precisionFlag + cpuFreqFlag;
    if (!keepOriginalTraceFile) {
        scriptPyCall += " --excluded-original";
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
    string pythonCallPDF = pythonCall + " --pdf --save-feather";
    // Run dash
    system(pythonCallPDF.c_str());
}

PyObject* ProfetPyAdapter::getFunctionFromProfetIntegration(string fnName) {
    // Get function from module
    PyObject* pyFn = PyObject_GetAttrString(profetIntegrationModule, fnName.c_str());
    raisePyErrorIfNull(pyFn, "ERROR getting \"" + fnName + "\" attribute.");
    return pyFn;
}
