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
double getPyDictDouble(PyObject* pyDict, string attribute);
string getPyDictString(PyObject* pyDict, string attribute);
double getClosestValue(vector<double> values, double target);
PyObject* cppVectorToPythonList(vector<double> vec);

#endif