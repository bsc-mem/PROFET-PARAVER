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

    // TODO we should first check if the submodule profet has the curves available. If not, get the path from DB
    // TODO or viceversa, first check on DB and, if not, then check in profet.
    PyObject* row = getRowFromDB();
    pmuType = getPyDictString(row, "pmu_type");
    cpuMicroarch = getPyDictString(row, "cpu_microarchitecture");

    string curvesDBPath = getPyDictString(row, "curves_path");
    curvesPath = getCurvesPath(curvesDBPath);

    // Set display warnings in Python module
    setDisplayWarnings(displayWarnings);
    // Set the curves in the Python module
    setCurves(projectPath, cpuModel, memorySystem);
    availableReadRatios = getCurvesReadRatios();
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
    PyObject* pArgs = Py_BuildValue("(sss)", projectPath.c_str(), cpuModel.c_str(), memorySystem.c_str());
    PyObject* row = PyObject_CallObject(rowDbFn, pArgs);
    raisePyErrorIfNull(row, "ERROR getting Python dictionary with memory values.");

    return row;
}

string ProfetPyAdapter::getCurvesPath(string dbRowCurvesPath) {
    // Get curves path
    fs::path project (projectPath);
    fs::path curves (dbRowCurvesPath);
    fs::path full_path = project / curves;
    return full_path.u8string();
}

void ProfetPyAdapter::checkSystemSupported() {
    PyObject* checkSystemSupportedFn = getFunctionFromProfetIntegration("check_curves_exist");
    // Make sure string arguments are built with .c_str()
    PyObject* pArgs = Py_BuildValue("(sss)", projectPath.c_str(), cpuModel.c_str(), memorySystem.c_str());
    PyObject_CallObject(checkSystemSupportedFn, pArgs);
    // raisePyErrorIfNull(curvesPath, "ERROR checking  values.");
}

void ProfetPyAdapter::printSupportedSystems() {
    PyObject* printSupportedSystemsFn = getFunctionFromProfetIntegration("print_supported_systems");
    PyObject* pArgs = Py_BuildValue("(s)", projectPath.c_str());
    PyObject_CallObject(printSupportedSystemsFn, pArgs);
}

tuple<double, double, double, double, double> ProfetPyAdapter::computeMemoryMetrics(double cpuFreqGHz, double writeRatio, double bandwidth) {
    // Get dictionary with computed memory values
    PyObject* memoryMetricsFn = getFunctionFromProfetIntegration("get_memory_properties_from_bw");
    // Make sure string arguments are built with .c_str()
    double readRatio = 100 - writeRatio * 100;
    double closestReadRatio = getClosestValue(availableReadRatios, readRatio);
    PyObject* pArgs = PyTuple_Pack(4, PyFloat_FromDouble(cpuFreqGHz), PyFloat_FromDouble(writeRatio),
                                   PyFloat_FromDouble(closestReadRatio), PyFloat_FromDouble(bandwidth));
    PyObject* memDict = PyObject_CallObject(memoryMetricsFn, pArgs);
    raisePyErrorIfNull(memDict, "ERROR getting Python dictionary with memory values.");

    // Get values of dictionary elements
    // double returnedBandwidth = getPyDictDouble(memDict, "bandwidth");
    double maxBandwidth = getPyDictDouble(memDict, "max_bandwidth");
    double latency = getPyDictDouble(memDict, "latency");
    double leadOffLatency = getPyDictDouble(memDict, "lead_off_latency");
    double maxLatency = getPyDictDouble(memDict, "max_latency");
    double stressScore = getPyDictDouble(memDict, "stress_score");

    return {maxBandwidth, latency, leadOffLatency, maxLatency, stressScore};
}

void ProfetPyAdapter::runDashApp(string traceFilePath, double precision, double cpuFreq, bool keepOriginalTraceFile) {
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

void ProfetPyAdapter::setDisplayWarnings(bool displayWarnings) {
    // Set display warnings in Python module
    PyObject* setDisplayWarningsFn = getFunctionFromProfetIntegration("set_display_warnings");
    // Make sure string arguments are built with .c_str()
    PyObject* pArgs = Py_BuildValue("(i)", displayWarnings ? 1 : 0);
    PyObject* status = PyObject_CallObject(setDisplayWarningsFn, pArgs);
    raisePyErrorIfNull(status, "ERROR setting display_warnings in Python module.");
}

void ProfetPyAdapter::setCurves(string projectPath, string cpuModel, string memorySystem) {
    PyObject* setCurvesFn = getFunctionFromProfetIntegration("set_curves");
    // Make sure string arguments are built with .c_str()
    PyObject* pArgs = Py_BuildValue("(sss)", projectPath.c_str(), cpuModel.c_str(), memorySystem.c_str());
    PyObject* status = PyObject_CallObject(setCurvesFn, pArgs);
    raisePyErrorIfNull(status, "ERROR setting curves in Python module.");
}

vector<double> ProfetPyAdapter::getCurvesReadRatios() {
    // Get available read ratios for the given curves
    PyObject* readRatiosFn = getFunctionFromProfetIntegration("get_curves_available_read_ratios");
    // Make sure string arguments are built with .c_str()
    PyObject* pArgs = Py_BuildValue("()");
    PyObject* pyReadRatios = PyObject_CallObject(readRatiosFn, pArgs);
    raisePyErrorIfNull(pyReadRatios, "ERROR getting available read ratios.");

    Py_ssize_t size = PyList_Size(pyReadRatios);
    vector<double> curvesReadRatios(size);
    for (Py_ssize_t i = 0; i < size; ++i) {
        // Get read ratio
        PyObject* pItem = PyList_GetItem(pyReadRatios, i);
        double readRatio = PyFloat_AsDouble(pItem);
        curvesReadRatios[i] = readRatio;
    }

    // Sort available read ratios
    sort(curvesReadRatios.begin(), curvesReadRatios.end());
    return curvesReadRatios;
}