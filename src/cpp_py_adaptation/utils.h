// utils.h
#ifndef UTILS_H
#define UTILS_H

#include<iostream>
#include <vector>
#include <cmath>
#include "Python.h"
using namespace std;

void raisePyErrorIfNull(PyObject* obj, string errText);
int getPyDictInt(PyObject* pyDict, string attribute);
float getPyDictFloat(PyObject* pyDict, string attribute);
string getPyDictString(PyObject* pyDict, string attribute);
float getClosestValue(vector<float> values, float target);
PyObject* cppVectorToPythonList(vector<float> vec);

#endif