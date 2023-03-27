/* Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
 * You may use, distribute and modify this code under the
 * terms of the BSD-3 license.
 *
 * You should have received a copy of the BSD-3 license with
 * this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
 */

// profetpyadapter.cpp
#include <iostream>
#include "profetpyadapter.h"
using namespace std;


ProfetPyAdapter::ProfetPyAdapter() {}

ProfetPyAdapter::ProfetPyAdapter(string projectPath, string cpuModel, string memorySystem) {
    Py_Initialize();  // initialize Python

    this->projectPath = projectPath;
    projectSrcPath = projectPath + "src/";
    profetIntegrationPath = projectSrcPath + "cpp_py_adaptation/";
    pyProfetPath = projectSrcPath + "py_profet/";
    // Set relative path (current directory) for importing modules
    sysPath = PySys_GetObject((char*)"path");
    PyList_Append(sysPath, PyUnicode_FromString(profetIntegrationPath.c_str()));

    // Load PROFET integration module
    profetIntegrationModule = PyImport_ImportModule("profet_integration");
    raisePyErrorIfNull(profetIntegrationModule, "ERROR when importing \"profet_integration\" module.");

    this->cpuModel = cpuModel;
    this->memorySystem = memorySystem;
    PyObject* row = getRowFromDB();
    pmuType = getPyDictString(row, "pmu_type");
    cpuMicroarch = getPyDictString(row, "cpu_microarchitecture");

    curvesPath = getCurvesPath();
}

ProfetPyAdapter::~ProfetPyAdapter() {
    // Stop python interpreter
    Py_Finalize();
}

int ProfetPyAdapter::getPyDictInt(PyObject* pyDict, string attribute) {
    PyObject* itemValue = PyDict_GetItemString(pyDict, attribute.c_str());
    return (int)PyLong_AsLong(itemValue);
}

float ProfetPyAdapter::getPyDictFloat(PyObject* pyDict, string attribute) {
    PyObject* itemValue = PyDict_GetItemString(pyDict, attribute.c_str());
    return PyFloat_AsDouble(itemValue);
}

string ProfetPyAdapter::getPyDictString(PyObject* pyDict, string attribute) {
    PyObject* itemValue = PyDict_GetItemString(pyDict, attribute.c_str());
    return _PyUnicode_AsString(itemValue);
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

void ProfetPyAdapter::checkSystemSupported() {
    PyObject* checkSystemSupportedFn = getFunctionFromProfetIntegration("check_curves_exist");
    // Make sure string arguments are built with .c_str()
    PyObject* pArgs = Py_BuildValue("(sss)", pyProfetPath.c_str(), cpuModel.c_str(), memorySystem.c_str());
    PyObject_CallObject(checkSystemSupportedFn, pArgs);
    // raisePyErrorIfNull(curvesPath, "ERROR checking  values.");
}

tuple<float, float, float, float> ProfetPyAdapter::computeMemoryMetrics(float cpuFreqGHz, float writeRatio, float bandwidth, bool displayWarnings) {
    // Get dictionary with computed memory values

    PyObject* memoryMetricsFn = getFunctionFromProfetIntegration("get_memory_properties_from_bw");
    // Make sure string arguments are built with .c_str()
    PyObject* pArgs = Py_BuildValue("(sfffi)", curvesPath.c_str(), cpuFreqGHz, writeRatio, bandwidth, displayWarnings);
    PyObject* memDict = PyObject_CallObject(memoryMetricsFn, pArgs);
    raisePyErrorIfNull(memDict, "ERROR getting Python dictionary with memory values.");

    // Get values of dictionary elements
    // float returnedBandwidth = getPyDictFloat(memDict, "bandwidth");
    float maxBandwidth = getPyDictFloat(memDict, "max_bandwidth");
    float latency = getPyDictFloat(memDict, "latency");
    float leadOffLatency = getPyDictFloat(memDict, "lead_off_latency");
    float maxLatency = getPyDictFloat(memDict, "max_latency");

    return {maxBandwidth, latency, leadOffLatency, maxLatency};
}

void ProfetPyAdapter::runDashApp(string traceFilePath, float precision, float cpuFreq) {
    string dashPlotsPath = pyProfetPath + "dash_plots.py";
    string pythonCall = "python3 " + dashPlotsPath + " --trace-file " + traceFilePath + " --bw-lat-curves-dir " + curvesPath + " -precision " + to_string(int(precision)) + " -cpufreq " + to_string(cpuFreq);
    system(pythonCall.c_str());
}

void ProfetPyAdapter::raisePyErrorIfNull(PyObject* obj, string errText) {
    if (obj == NULL) {
        if (!errText.empty()) {
            // Append endline to non-empty error text
            errText.append("\n");
        }
        cerr << errText;
        PyErr_Print();
        exit(1);
    }
}

PyObject* ProfetPyAdapter::getFunctionFromProfetIntegration(string fnName) {
    // Get function from module
    PyObject* pyFn = PyObject_GetAttrString(profetIntegrationModule, fnName.c_str());
    raisePyErrorIfNull(pyFn, "ERROR getting \"" + fnName + "\" attribute.");
    return pyFn;
}
