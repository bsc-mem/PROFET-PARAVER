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

double getPyDictDouble(PyObject* pyDict, string attribute) {
    PyObject* itemValue = PyDict_GetItemString(pyDict, attribute.c_str());
    return PyFloat_AsDouble(itemValue);
}

string getPyDictString(PyObject* pyDict, string attribute) {
    PyObject* itemValue = PyDict_GetItemString(pyDict, attribute.c_str());
    return _PyUnicode_AsString(itemValue);
}

double getClosestValue(vector<double> values, double target) {
    if (values.empty()) {
        // Handle the case when the vector is empty
        return 0.0f; // or any appropriate value
    }

    double closestValue = values[0]; // Assume the first element is the closest initially
    double minDifference = abs(target - closestValue);

    for (size_t i = 1; i < values.size(); ++i) {
        double difference = abs(target - values[i]);
        if (difference < minDifference) {
            closestValue = values[i];
            minDifference = difference;
        }
    }

    return closestValue;
}

PyObject* cppVectorToPythonList(vector<double> vec) {
    PyObject* pyList = PyList_New(vec.size());
    for (size_t i = 0; i < vec.size(); ++i) {
        PyObject* item = PyFloat_FromDouble(vec[i]);
        PyList_SetItem(pyList, i, item);
    }
    return pyList;
}