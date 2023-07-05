/* Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
 * You may use, distribute and modify this code under the
 * terms of the BSD-3 license.
 *
 * You should have received a copy of the BSD-3 license with
 * this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
 */

// nodememoryrecords.h
#ifndef NODEMEMORYRECORDS_H
#define NODEMEMORYRECORDS_H

#include <string>
#include <vector>
#include <tuple>
#include <map>
#include <cmath>
#include <queue>
#include <limits>
#include "socketmemoryrecords.h"
#include "memoryrecord.h"
#include "../cpp_py_adaptation/profetpyadapter.h"

using namespace std;


class NodeMemoryRecords {
  // Memory records in a single node
  public:
    int nodeID;
    string name;
    // Keep track of the sockets and their MCs
    map<int, vector<int>> MCsPerSocket;
    map<int, SocketMemoryRecords> sockets;
    // Keep track of the last metric values written in the prv file for each socket
    map<string, unordered_map<string, float>> lastWrittenMetrics;
    // Sum all the metric values in each socket for computing the averages at the end
    map<string, map<string, float>> sumMetrics;
    // If memory metrics are computed per socket or per MC
    bool perSocket;
    string memorySystem;
    string pmuType;
    string cpuMicroArch;
    string cpuModel;
    float cpuFreqGHz;
    int cacheLineBytes;
    int displayWarnings;

    NodeMemoryRecords();
    NodeMemoryRecords(int nodeID, string name, map<int, vector<int>> MCsPerSocket, bool perSocket,
                      string memorySystem, string pmuType, string cpuMicroArch, string cpuModel,
                      float cpuFreqGHz, int cacheLineBytes, int displayWarnings);

    void addRead(int socketID, int mcID, MemoryRecord record);
    void addWrite(int socketID, int mcID, MemoryRecord record);

    unordered_map<string, float> getLastWrittenMetrics(int socketID, int mcID);
    void setLastWrittenMetrics(int socketID, int mcID, unordered_map<string, float> metrics);
    
    bool areAllSocketsEmpty();

    tuple<bool, unsigned long long, int, int> isProcessableData(bool allowEmptyQueues);
    unordered_map<string, float> processMemoryMetrics(ProfetPyAdapter &profetPyAdapter, int socketID, int mcID, bool allowEmptyQueues);

    void printSocketsQueues();
    void printFinalMessage();

  private:
    void initSumMetrics(string id);
    string getFullID(int socketID, int mcID);
    string getFullMCID(int socketID, int mcID);
    bool isSmallestMCTime(int socketID, int mcID);
    bool isSmallestSocketTime(int socketID);

};

#endif