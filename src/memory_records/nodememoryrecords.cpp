/* Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
 * You may use, distribute and modify this code under the
 * terms of the BSD-3 license.
 *
 * You should have received a copy of the BSD-3 license with
 * this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
 */

// nodememoryrecords.cpp
#include <iostream>
#include "nodememoryrecords.h"
using namespace std;


NodeMemoryRecords::NodeMemoryRecords() {}

NodeMemoryRecords::NodeMemoryRecords(int nodeID, string name, map<int, vector<int>> MCsPerSocket,bool perSocket,
                                     string memorySystem, string pmuType, string cpuMicroArch, string cpuModel,
                                     double cpuFreqGHz, int cacheLineBytes, int displayWarnings) {
    this->nodeID = nodeID;
    this->name = name;
    // Memory controler ID vectors in each socket ID are already sorted
    this->MCsPerSocket = MCsPerSocket;
    this->perSocket = perSocket;
    this->memorySystem = memorySystem;
    this->pmuType = pmuType;
    this->cpuMicroArch = cpuMicroArch;
    this->cpuModel = cpuModel;
    this->cpuFreqGHz = cpuFreqGHz;
    this->cacheLineBytes = cacheLineBytes;
    this->displayWarnings = displayWarnings;
  
    // Initialize SocketMemoryRecords objects for each socket
    // Sum all the metric values in each socket for computing the averages at the end
    map<string, map<string, double>> sumMetrics;
    for (const auto &[socketID, memoryControllerIDs] : MCsPerSocket) {
        sockets[socketID] = SocketMemoryRecords(socketID, memoryControllerIDs, displayWarnings);
        if (perSocket) {
            string id = to_string(socketID);
            lastWrittenMetrics[id] = unordered_map<string, double>();
            initSumMetrics(id);
        } else {
            for (int mcID : memoryControllerIDs) {
                string id = getFullMCID(socketID, mcID);
                lastWrittenMetrics[id] = unordered_map<string, double>();
                initSumMetrics(id);
            }
        }
    }
    
}

void NodeMemoryRecords::addRead(int socketID, int mcID, MemoryRecord record) {
    sockets[socketID].addRead(mcID, record);
}

void NodeMemoryRecords::addWrite(int socketID, int mcID, MemoryRecord record) {
    sockets[socketID].addWrite(mcID, record);
}

unordered_map<string, double> NodeMemoryRecords::getLastWrittenMetrics(int socketID, int mcID) {
  string id = getFullID(socketID, mcID);
  return lastWrittenMetrics[id];
}

void NodeMemoryRecords::setLastWrittenMetrics(int socketID, int mcID, unordered_map<string, double> metrics) {
  string id = getFullID(socketID, mcID);
  lastWrittenMetrics[id] = metrics;
}

bool NodeMemoryRecords::areAllSocketsEmpty() {
  // Check that all queues in the sockets are empty
  for (auto &[socketID, socket] : sockets) {
    // sockets[socketID].printQueues();
    if (!socket.areAllQueuesEmpty()) {
      return false;
    }
  }
  return true;
}

tuple<bool, unsigned long long, int, int> NodeMemoryRecords::isProcessableData(bool allowEmptyQueues) {
    // Bandwidth is processable when the smallest time in sockets (or MCs) is processable
    unsigned long long smallestMCTime = numeric_limits<unsigned long long>::max();
    int smallestTimeSocketID = numeric_limits<int>::max();
    int smallestTimeMCID = numeric_limits<int>::max();
    for (auto &[socketID, socket] : sockets) {
        auto [smallestMCTime2, smallestTimeMC2] = socket.getSmallestTime();
        if (smallestMCTime2 < smallestMCTime) {
            smallestMCTime = smallestMCTime2;
            smallestTimeMCID = smallestTimeMC2;
            smallestTimeSocketID = socketID;
        }
    }

    if (smallestMCTime != numeric_limits<unsigned long long>::max()) {
        // cout << perSocket << " " << to_string(smallestTimeSocket) << " " << to_string(smallestTimeMCID) << " " << sockets[smallestTimeSocket].isSocketProcessable() << endl;
        if (perSocket && (allowEmptyQueues || sockets[smallestTimeSocketID].isSocketProcessable())) {
            // Socket is processable if the socket with the lowest time is processable
            // cout << "Process " << to_string(smallestTimeSocketID) << " " << to_string(smallestTimeMCID) << " (" << to_string(smallestMCTime) << ")" << endl;
            return {true, smallestMCTime, smallestTimeSocketID, -1};
        } else if (!perSocket && (allowEmptyQueues || sockets[smallestTimeSocketID].isMCProcessable(smallestTimeMCID))) {
            // MC is processable if the smallest time in MC is processable (in order to assure writing data in ascending timestamp)
            // cout << "Process " << to_string(smallestTimeSocketID) << " " << to_string(smallestTimeMCID) << " (" << to_string(smallestMCTime) << ", " << allowEmptyQueues << ")" << endl;
            return {true, smallestMCTime, smallestTimeSocketID, smallestTimeMCID};
        }
    }

    return {false, smallestMCTime, -1, -1};
}


unordered_map<string, double>NodeMemoryRecords::processMemoryMetrics(ProfetPyAdapter &profetPyAdapter, int socketID, int mcID, bool allowEmptyQueues, bool groupMCs) {
  // Compute the necessary memory stress metrics and write them in the output file.
  // Pre: bandwidths have to be processable (there is the function "isProcessableData" for checking it before calling this method)
  
  // sockets[socketID].printQueues();

  // Calculates read and write bandwidths and pops the smaller (t1) record for saving memory
  auto [readBW, writeBW, meanReads, meanWrites] = sockets[socketID].processBandwidths(mcID, cacheLineBytes, allowEmptyQueues);

  unordered_map<string, double> metrics;
  metrics["writeRatio"] = -1;
  metrics["bandwidth"] = -1;
  metrics["maxBandwidth"] = -1;
  metrics["latency"] = -1;
  metrics["leadOffLatency"] = -1;
  metrics["maxLatency"] = -1;
  metrics["stressScore"] = -1;
  metrics["meanReads"] = -1;
  metrics["meanWrites"] = -1;

  if (readBW == -1 || writeBW == -1) {
    return metrics;
  }

  if (readBW + writeBW == 0) {
    metrics["bandwidth"] = 0;
    return metrics;
  }

  metrics["writeRatio"] = writeBW / (readBW + writeBW);
  //cout << writeBW << " " << readBW << " " << writeRatio << endl;
  metrics["bandwidth"] = readBW + writeBW;
  // cout << socketID << " " << readBW << " " << writeBW << " " << writeRatio << " " << bandwidth << endl;

  // Get computed memory metrics
  auto [maxBandwidth, latency, leadOffLatency, maxLatency, stressScore, newBW] = profetPyAdapter.computeMemoryMetrics(cpuFreqGHz, metrics["writeRatio"],
                                                                                                               metrics["bandwidth"], groupMCs, this->MCsPerSocket[socketID].size());
  // cout << maxBandwidth << " " << latency << " " << leadOffLatency << " " << maxLatency << endl;
  if (newBW != metrics["bandwidth"]) {
    // If the computed bandwidth is different from the one calculated with the read and write bandwidths, return negative metrics
    if (displayWarnings) {
      //Show message showing the difference between BW print newBw and metrics bandwidth
      // cout << "Warning: Computed bandwidth is different from the one calculated with the read and write bandwidths." << endl;
      // cout << "Computed bandwidth: " << newBW << " GB/s" << endl;
      // cout << "Calculated bandwidth: " << metrics["bandwidth"] << " GB/s" << endl;
    }

    metrics["writeRatio"] = -metrics["writeRatio"];
    metrics["bandwidth"] = newBW;
    meanReads = -meanReads;
    meanWrites = -meanWrites;
  }

  if(latency > maxLatency || newBW > maxBandwidth) {
    // If latency is greater than maxLatency, return negative metrics
    if (displayWarnings) {
      cerr << "Warning: Latency is greater than maxLatency. Setting write ratio to " << metrics["writeRatio"] * 100 << "% and bandwidth to " << round(metrics["bandwidth"]) << " GB/s" << endl;
    }

    metrics["latency"] = maxLatency;
    metrics["bandwidth"] = maxBandwidth;
    metrics["stressScore"] = 1;

    return metrics;
  }
  
  // if (latency <= 0) {
  //   // If latency is -1, it means that bandwidth was off the charts, return negative metrics
  //   if (displayWarnings) {
  //     cerr << "Warning: Erroneous recorded bandwidth. Setting write ratio to " << -metrics["writeRatio"] * 100 << "% and bandwidth to " << round(-metrics["bandwidth"]) << " GB/s" << endl;
  //   }
  //   metrics["writeRatio"] = -metrics["writeRatio"] * 100;
  //   metrics["bandwidth"] = -metrics["bandwidth"];
  //   return metrics;
  // }

  metrics["writeRatio"] = metrics["writeRatio"] * 100;
  metrics["maxBandwidth"] = maxBandwidth;
  metrics["latency"] = latency;
  metrics["leadOffLatency"] = leadOffLatency;
  metrics["maxLatency"] = maxLatency;
  metrics["stressScore"] = stressScore;
  metrics["meanReads"] = meanReads;
  metrics["meanWrites"] = meanWrites;

  // sumMetrics is used for computing the average metrics at the end of the execution
  string id = getFullID(socketID, mcID);
  sumMetrics[id]["n"] += 1;
  sumMetrics[id]["writeRatio"] += metrics["writeRatio"];
  sumMetrics[id]["bandwidth"] += metrics["bandwidth"];
  sumMetrics[id]["maxBandwidth"] += metrics["maxBandwidth"];
  sumMetrics[id]["latency"] += metrics["latency"];
  sumMetrics[id]["leadOffLatency"] += metrics["leadOffLatency"];
  sumMetrics[id]["maxLatency"] += metrics["maxLatency"];
  sumMetrics[id]["stressScore"] += metrics["stressScore"];
  
  return metrics;
}

void NodeMemoryRecords::printSocketsQueues() {
  // Check that all queues in the sockets are empty
  for (auto &[socketID, socket] : sockets) {
    sockets[socketID].printQueues();
    cout << endl;
  }
  cout << endl;
}

void NodeMemoryRecords::printFinalMessage() {
    cout << "======================" << endl;
    cout << "      " << name << endl;
    cout << "======================" << endl;
    for (auto [socketID, metricsSum] : sumMetrics) {
        // Round each metric to 2 decimal points
        cout << "Socket " << socketID << endl;
        cout << "----------------------" << endl;
        cout << "Average Write Ratio: " << round(metricsSum["writeRatio"] * 100 / metricsSum["n"]) / 100 << " %" << endl;
        cout << "Average Bandwidth: " << round(metricsSum["bandwidth"] * 100 / metricsSum["n"]) / 100 << " GB/s" << endl;
        cout << "Average Max. Bandwidth: " << round(metricsSum["maxBandwidth"] * 100 / metricsSum["n"]) / 100 << " GB/s" << endl;
        cout << "Average Latency: " << round(metricsSum["latency"] * 100 / metricsSum["n"]) / 100 << " ns" << endl;
        cout << "Average Lead-off latency: " << round(metricsSum["leadOffLatency"] * 100 / metricsSum["n"]) / 100 << " ns" << endl;
        cout << "Average Max. Latency: " << round(metricsSum["maxLatency"] * 100 / metricsSum["n"]) / 100 << " ns" << endl;
        cout << "Average Stress Score: " << round(metricsSum["stressScore"] * 100 / metricsSum["n"]) / 100 << endl << endl;
    }
}


void NodeMemoryRecords::initSumMetrics(string id) {
    sumMetrics[id] = map<string, double>();
    sumMetrics[id]["n"] = 0;
    sumMetrics[id]["writeRatio"] = 0;
    sumMetrics[id]["bandwidth"] = 0;
    sumMetrics[id]["maxBandwidth"] = 0;
    sumMetrics[id]["latency"] = 0;
    sumMetrics[id]["leadOffLatency"] = 0;
    sumMetrics[id]["maxLatency"] = 0;
    sumMetrics[id]["stressScore"] = 0;
}

string NodeMemoryRecords::getFullID(int socketID, int mcID) {
  if (perSocket) {
    return to_string(socketID);
  }
  return getFullMCID(socketID, mcID);
}

string NodeMemoryRecords::getFullMCID(int socketID, int mcID) {
  return to_string(socketID) + "-" + to_string(mcID);
}

bool NodeMemoryRecords::isSmallestMCTime(int socketID, int mcID) {
  // If the given socket is processable, check that it has the smallest timestamp.
  // This is checked because PRV standard is to have all timestamps ascendingly sorted.
  auto [smallestTime, smallestTimeMC] = sockets[socketID].getSmallestTime();

  if (smallestTimeMC != mcID) {
    // There is a smaller time MC in the same socket
    return false;
  }

  for (auto [socketID_2, socket] : sockets) {
    if (socketID_2 != socketID) {
      auto [smallestTime_2, smallestMCTime_2] = socket.getSmallestTime();
      if (smallestTime_2 < smallestTime) {
        return false;
      }
    }
  }
  return true;
}

bool NodeMemoryRecords::isSmallestSocketTime(int socketID) {
  // If the given socket is processable, check that it has the smallest timestamp.
  // This is checked because PRV standard is to have all timestamps ascendingly sorted.
  auto [smallestTime, _] = sockets[socketID].getSmallestTime();
  for (auto [socketID_2, socket] : sockets) {
    if (socketID_2 != socketID) {
      auto [smallestTime_2, _] = socket.getSmallestTime();
      if (smallestTime_2 < smallestTime) {
        return false;
      }
    }
  }
  return true;
}