// socketmemoryrecords.h
#ifndef SOCKETMEMORYRECORDS_H
#define SOCKETMEMORYRECORDS_H

#include <iostream>
#include <vector>
#include <tuple>
#include <map>
/* Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
 * You may use, distribute and modify this code under the
 * terms of the BSD-3 license.
 *
 * You should have received a copy of the BSD-3 license with
 * this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
 */

#include <cmath>
#include <queue>
#include <limits>
#include "memoryrecord.h"

using namespace std;


class SocketMemoryRecords {
  // Memory records in a single socket
  public:
    int socketID;
    vector<int> memoryControllerIDs;
    int displayWarnings;
    map<int, int> memoryControllerIDsCorrespondence;
    map<int, queue<MemoryRecord>> reads;
    map<int, queue<MemoryRecord>> writes;
    // Keep track of the last written events (the last ones popped) in each MC
    map<int, unsigned long long> lastPoppedTimePerMC;
    unsigned long long lastPoppedTime;

    SocketMemoryRecords();
    SocketMemoryRecords(int socketID, vector<int> memoryControllerIDs, int displayWarnings);

    void addRead(int mcID, MemoryRecord record);
    void addWrite(int mcID, MemoryRecord record);

    unsigned long long getLastReadTime(int mcID);
    unsigned long long getLastWriteTime(int mcID);
    unsigned long long getLastPoppedTime();
    pair<unsigned long long, int> getSmallestTime();

    bool isMCProcessable(int mcID);
    bool isSocketProcessable();
    bool areQueuesEmpty(int mcID);
    bool areAllQueuesEmpty();

    pair<float, float> processBandwidths(int mcID, uint cacheLineBytes, bool allowEmptyQueues);

    void printQueueSizes();
    void printQueues();

  private:

    pair<float, float> processBW(queue<MemoryRecord> readQ, queue<MemoryRecord> writeQ, uint cacheLineBytes);
    unsigned long long getLast(queue<MemoryRecord> q, unsigned long long lastPoppedMCTime);
    tuple<unsigned long long, int, int> getSmallestElement();
    float getMRBandwidth(MemoryRecord mr, uint cacheLineBytes);
    bool areAllQueuesFull(map<int, queue<MemoryRecord>> m);
    void popOldestMCRecord(int mcID);
    void popOldestRecords();
    void printMapQueues(map<int, queue<MemoryRecord>> m);
};

#endif