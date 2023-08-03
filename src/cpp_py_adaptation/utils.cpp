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
        return 0.0f;
    }

    auto iter_geq = std::lower_bound(
        values.begin(), 
        values.end(), 
        target
    );

    if (iter_geq == values.begin()) {
        return values[0];
    }

    double a = *(iter_geq - 1);
    double b = *(iter_geq);

    int idx;
    if (fabs(target - a) < fabs(target - b)) {
        idx = iter_geq - values.begin() - 1;
    } else {
        idx = iter_geq - values.begin();
    }

    return values[idx];
}

PyObject* cppVectorToPythonList(vector<double> vec) {
    PyObject* pyList = PyList_New(vec.size());
    for (size_t i = 0; i < vec.size(); ++i) {
        PyObject* item = PyFloat_FromDouble(vec[i]);
        PyList_SetItem(pyList, i, item);
    }
    return pyList;
}