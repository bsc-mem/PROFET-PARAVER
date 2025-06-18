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
#include <regex>
#include <fstream>
#include <sys/stat.h>
#if (defined(__GNUC__) && __GNUC__ < 8 && !defined(__clang__))
  #include <experimental/filesystem>
  namespace fs = std::experimental::filesystem;
#else
  #include <filesystem>
  #ifdef __APPLE__
    namespace fs = std::__fs::filesystem;
  #else
    namespace fs = std::filesystem;
  #endif
#endif

#include <Python.h>
// #include "curves.h"
#include "utils.h"
#include "single_include/nlohmann/json.hpp"

using namespace std;
using json = nlohmann::json;


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
    map<int, pair<vector<double>, vector<double>>> curves;
    // Same as previous curves but bws and lats are python list objects
    map<int, pair<PyObject*, PyObject*>> pyCurves;
    vector<double> availableReadRatios;
    string projectSrcPath;
    string profetIntegrationPath;
    string projectDataPath;
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
    void setCurvesBwsLats(string curvesPath, map<int, pair<vector<double>, vector<double>>> &curves, map<int, pair<PyObject*, PyObject*>> &pyCurves);
    void checkSystemSupported();

    void printSupportedSystems();

    tuple<double, double, double, double, double, double> computeMemoryMetrics(double cpuFreqGHz, double writeRatio, double bandwidth, bool groupMCs, int MCsPerSocket);

    void runDashApp(string traceFilePath, double precision, double cpuFreq, bool expertMode, bool keepOriginalTraceFile);

  private:
    PyObject* getFunctionFromProfetIntegration(string fnName);
    void setDisplayWarnings(bool displayWarnings);
    void setCurves(string projectDataPath, string cpuModel, string memorySystem);

};

#endif