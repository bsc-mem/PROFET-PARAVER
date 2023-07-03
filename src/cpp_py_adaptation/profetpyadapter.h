/* Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
 * You may use, distribute and modify this code under the
 * terms of the BSD-3 license.
 *
 * You should have received a copy of the BSD-3 license with
 * this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
 */

// profetpyadapter.h
#ifndef PROFETPYADAPTER_H
#define PROFETPYADAPTER_H

#include <iostream>
#include <string>
#include <vector>
#include <tuple>
#include <map>
#include <cmath>
#include <queue>
#include <limits>
#include <Python.h>
// #include "curves.h"
#include "utils.h"

using namespace std;


class ProfetPyAdapter {
  public:
    string projectPath;
    string pmuType;
    string cpuModel;
    string cpuMicroarch;
    string memorySystem;
    string curvesPath;
    // Curves curves;
    // map with read ratios as keys and pairs of vectors of bandwidths and latencies as values
    map<int, pair<vector<float>, vector<float>>> curves;
    // Same as previous curves but bws and lats are python list objects
    map<int, pair<PyObject*, PyObject*>> pyCurves;
    vector<float> availableReadRatios;
    string projectSrcPath;
    string profetIntegrationPath;
    string pyProfetPath;
    PyObject* sysPath;
    PyObject* profetIntegrationModule;

    ProfetPyAdapter();
    ProfetPyAdapter(string projectPath);
    ProfetPyAdapter(string projectPath, string cpuModel, string memorySystem, bool displayWarnings);
    ~ProfetPyAdapter();

    void setPathVariables(string projectPath);
    void loadProfetIntegrationModule();

    PyObject* getRowFromDB();
    string getCurvesPath();
    void setCurvesBwsLats(string curvesPath, map<int, pair<vector<float>, vector<float>>> &curves, map<int, pair<PyObject*, PyObject*>> &pyCurves);
    void checkSystemSupported();

    void printSupportedSystems();

    tuple<float, float, float, float, float> computeMemoryMetrics(float cpuFreqGHz, float writeRatio, float bandwidth, bool displayWarnings);

    void runDashApp(string traceFilePath, float precision, float cpuFreq, bool keepOriginalTraceFile);

  private:
    PyObject* getFunctionFromProfetIntegration(string fnName);

};

#endif