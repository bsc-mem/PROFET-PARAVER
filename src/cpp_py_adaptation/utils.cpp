#include "utils.h"
using namespace std;

void raisePyErrorIfNull(PyObject* obj, string errText) {
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

int getPyDictInt(PyObject* pyDict, string attribute) {
    PyObject* itemValue = PyDict_GetItemString(pyDict, attribute.c_str());
    return (int)PyLong_AsLong(itemValue);
}

float getPyDictFloat(PyObject* pyDict, string attribute) {
    PyObject* itemValue = PyDict_GetItemString(pyDict, attribute.c_str());
    return PyFloat_AsDouble(itemValue);
}

string getPyDictString(PyObject* pyDict, string attribute) {
    PyObject* itemValue = PyDict_GetItemString(pyDict, attribute.c_str());
    return _PyUnicode_AsString(itemValue);
}

float getClosestValue(vector<float> values, float target) {
    if (values.empty()) {
        // Handle the case when the vector is empty
        return 0.0f; // or any appropriate value
    }

    float closestValue = values[0]; // Assume the first element is the closest initially
    float minDifference = abs(target - closestValue);

    for (size_t i = 1; i < values.size(); ++i) {
        float difference = abs(target - values[i]);
        if (difference < minDifference) {
            closestValue = values[i];
            minDifference = difference;
        }
    }

    return closestValue;
}

PyObject* cppVectorToPythonList(vector<float> vec) {
    PyObject* pyList = PyList_New(vec.size());
    for (size_t i = 0; i < vec.size(); ++i) {
        PyObject* item = PyFloat_FromDouble(vec[i]);
        PyList_SetItem(pyList, i, item);
    }
    return pyList;
}