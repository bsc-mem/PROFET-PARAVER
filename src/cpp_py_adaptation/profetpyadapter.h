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

#include <string>
#include <vector>
#include <tuple>
#include <map>
#include <cmath>
#include <queue>
#include <limits>
#include <Python.h>

using namespace std;


class ProfetPyAdapter {
  public:
    string projectPath;
    string pmuType;
    string cpuModel;
    string cpuMicroarch;
    string memorySystem;
    string curvesPath;
    string projectSrcPath;
    string profetIntegrationPath;
    string pyProfetPath;
    PyObject* sysPath;
    PyObject* profetIntegrationModule;

    ProfetPyAdapter();
    ProfetPyAdapter(string projectPath, string cpuModel, string memorySystem);
    ~ProfetPyAdapter();

    int getPyDictInt(PyObject* pyDict, string attribute);
    float getPyDictFloat(PyObject* pyDict, string attribute);
    string getPyDictString(PyObject* pyDict, string attribute);

    PyObject* getRowFromDB();
    string getCurvesPath();
    void checkSystemSupported();

    tuple<float, float, float, float> computeMemoryMetrics(float cpuFreqGHz, float writeRatio, float bandwidth, bool displayWarnings);

    void runDashApp(string traceFilePath, float precision, float cpuFreq);

  private:
    void raisePyErrorIfNull(PyObject* obj, string errText = "");
    PyObject* getFunctionFromProfetIntegration(string fnName);


};

#endif