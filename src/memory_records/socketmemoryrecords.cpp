/* Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
 * You may use, distribute and modify this code under the
 * terms of the BSD-3 license.
 *
 * You should have received a copy of the BSD-3 license with
 * this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
 */

// socketmemoryrecords.cpp
#include <iostream>
#include <iomanip>
#include "socketmemoryrecords.h"
using namespace std;


SocketMemoryRecords::SocketMemoryRecords() {}

SocketMemoryRecords::SocketMemoryRecords(int socketID, vector<int> memoryControllerIDs, int displayWarnings) {
    this->socketID = socketID;
    this->memoryControllerIDs = memoryControllerIDs;
    this->displayWarnings = displayWarnings;
    // The MC IDs don't need to be consecutive and start with 0, with this correspondence we have also this ennumeration (needed for the PRV API)
    // Pre: MC IDs have to be sorted
    int i = 0;
    for (int mcID : memoryControllerIDs) {
        reads[mcID] = queue<MemoryRecord>();
        writes[mcID] = queue<MemoryRecord>();
        memoryControllerIDsCorrespondence[mcID] = i;
        lastPoppedTimePerMC[mcID] = numeric_limits<unsigned long long>::max();
        lastPoppedTime = numeric_limits<unsigned long long>::max();
        i += 1;
    }
}

void SocketMemoryRecords::addRead(int mcID, MemoryRecord record) {
    // cout << "Push " << to_string(record.n) << " reads to " << to_string(mcID) << "." << endl;
    reads[mcID].push(record);
}

void SocketMemoryRecords::addWrite(int mcID, MemoryRecord record) {
    // cout << "Push " << to_string(record.n) << " writes to " << to_string(mcID) << "." << endl;
    writes[mcID].push(record);
}

unsigned long long SocketMemoryRecords::getLastReadTime(int mcID) {
    // return getLast(reads[mcID]);
    return getLast(reads[mcID], lastPoppedTimePerMC[mcID]);
}

unsigned long long SocketMemoryRecords::getLastWriteTime(int mcID) {
    // return getLast(writes[mcID]);
    return getLast(writes[mcID], lastPoppedTimePerMC[mcID]);
}

unsigned long long SocketMemoryRecords::getLastPoppedTime() {
    // cout << "Last popped time: " << lastPoppedTime << endl;
    return lastPoppedTime;
}

pair<unsigned long long, int> SocketMemoryRecords::getSmallestTime() {
    // Return the smallest time in read and write queues
    if (areAllQueuesEmpty()) {
        return {numeric_limits<unsigned long long>::max(), numeric_limits<int>::max()};
    }

    unsigned long long smallestMCTime = numeric_limits<unsigned long long>::max();
    int smallestTimeMC = numeric_limits<int>::max();
    for (int mcID : memoryControllerIDs) {
        if (!reads[mcID].empty() && reads[mcID].front().t1 < smallestMCTime) {
            smallestMCTime = reads[mcID].front().t1;
            smallestTimeMC = mcID;
        }
        if (!writes[mcID].empty() && writes[mcID].front().t1 < smallestMCTime) {
            smallestMCTime = writes[mcID].front().t1;
            smallestTimeMC = mcID;
        }
    }
    return {smallestMCTime, smallestTimeMC};
}

bool SocketMemoryRecords::isMCProcessable(int mcID) {
    return !(reads[mcID].empty() || writes[mcID].empty());
}

bool SocketMemoryRecords::isSocketProcessable() {
    // cout << areAllQueuesFull(reads) << endl;
    // cout << areAllQueuesFull(writes) << endl;
    // The socket is going to be processable when there is at least one element per queue
    return areAllQueuesFull(reads) && areAllQueuesFull(writes);
}

bool SocketMemoryRecords::areQueuesEmpty(int mcID) {
    return reads[mcID].empty() && writes[mcID].empty();
}

bool SocketMemoryRecords::areAllQueuesEmpty() {
    for (auto it = reads.begin(); it != reads.end(); it++) {
        if (!it->second.empty()) {
            return false;
        }
    }
    for (auto it = writes.begin(); it != writes.end(); it++) {
        if (!it->second.empty()) {
            return false;
        }
    }
    return true;
}

tuple<double, double, double, double> SocketMemoryRecords::processBandwidths(int mcID, uint cacheLineBytes, bool allowEmptyQueues) {
    // Add all bandwidths, reads and writes for each subsequent MC in the socket
    double readBW = 0;
    double writeBW = 0;
    // Mean reads and writes per second
    double meanReads = 0;
    double meanWrites = 0;

    // cout << "PROCESS BWS " << mcID << endl;

    if (mcID == -1) {
        // Process bandwidths per socket if there is no specified MC
        if (!allowEmptyQueues) {
            if (!isSocketProcessable()) {
                throw runtime_error("Cannot process bandwidth because there is at least one empty queue.");
            }
            if (areAllQueuesEmpty()) {
                throw runtime_error("Cannot process bandwidth because all socket's queues are empty.");
            }
        }

        bool invalidBW = false;
        for (int id : memoryControllerIDs) {
            if (reads[id].empty() && writes[id].empty()) {
                continue;
            }

            pair<double, double> bws = processBW(reads[id], writes[id], cacheLineBytes);
            if (bws.first == -1 || bws.second == -1) {
                invalidBW = true;
                break;
            }
            readBW += bws.first;
            writeBW += bws.second;
            
            pair<double, double> meanAccesses = processMeanAccesses(reads[id], writes[id]);
            meanReads += meanAccesses.first;
            meanWrites += meanAccesses.second;
            // cout << "reads: " << to_string(reads[mcID].front().n) << "; writes: " << to_string(writes[mcID].front().n) << endl;
            // cout << "reads t0: " << to_string(reads[mcID].front().t0) << "; writes t0: " << to_string(writes[mcID].front().t0) << endl;
            // cout << "reads t1: " << to_string(reads[mcID].front().t1) << "; writes t1: " << to_string(writes[mcID].front().t1) << endl;
            // cout << id << " read BW: " << getMRBandwidth(reads[id].front()) << "; write BW: " << getMRBandwidth(writes[id].front()) << endl;
        }

        if (invalidBW) {
            // Set bandwidths to -1 if they could not be calculated because there was at least one invalid
            readBW = -1;
            writeBW = -1;
        }

        // cout << "read BW: " << to_string(readBW) << "; write BW: " << to_string(writeBW) << endl;
        popOldestRecords();
    } else {
        // Process bandwidths for the given MC
        if (!allowEmptyQueues) {
            if (!isMCProcessable(mcID)) {
                throw runtime_error("Cannot process bandwidth, there is at least one empty queue.");
            }
        }

        // Structured binding not working I don't know why...
        // cout << "reads: " << to_string(reads[mcID].front().n) << "; writes: " << to_string(writes[mcID].front().n) << endl;
        // cout << "reads t0: " << to_string(reads[mcID].front().t0) << "; writes t0: " << to_string(writes[mcID].front().t0) << endl;
        // cout << "reads t1: " << to_string(reads[mcID].front().t1) << "; writes t1: " << to_string(writes[mcID].front().t1) << endl;

        pair<double, double> bws = processBW(reads[mcID], writes[mcID], cacheLineBytes);
        readBW = bws.first;
        writeBW = bws.second;

        pair<double, double> meanAccesses = processMeanAccesses(reads[mcID], writes[mcID]);
        meanReads = meanAccesses.first;
        meanWrites = meanAccesses.second;
        // cout << "read BW: " << to_string(readBW) << "; write BW: " << to_string(writeBW) << endl;
        popOldestMCRecord(mcID);
    }

    return {readBW, writeBW, meanReads, meanWrites};
}

void SocketMemoryRecords::printQueueSizes() {
    // Print for debugging purposes
    cout << "Socket ID: " << socketID << endl;
    for (int mcID : memoryControllerIDs) {
        cout << "MC ID: " << mcID << endl;
        cout << "Reads: " << reads[mcID].size() << endl;
        cout << "Writes: " << writes[mcID].size() << endl;
    }
}

void SocketMemoryRecords::printQueues() {
    // Print for debugging purposes
    cout << "Socket ID: " << socketID << endl;
    cout << "\tReads:" << endl;
    printMapQueues(reads);
    cout << "\tWrites:" << endl;
    printMapQueues(writes);
}

pair<double, double> SocketMemoryRecords::processBW(queue<MemoryRecord> readQ, queue<MemoryRecord> writeQ, uint cacheLineBytes) {
    if (readQ.empty() && writeQ.empty()) {
        return {0, 0};
    } else if (writeQ.empty()) {
        return {getMRBandwidth(readQ.front(), cacheLineBytes), 0};
    } else if (readQ.empty()) {
        return {0, getMRBandwidth(writeQ.front(), cacheLineBytes)};
    }
    return {getMRBandwidth(readQ.front(), cacheLineBytes), getMRBandwidth(writeQ.front(), cacheLineBytes)};
}

pair<double, double> SocketMemoryRecords::processMeanAccesses(queue<MemoryRecord> readQ, queue<MemoryRecord> writeQ) {
    // Process mean read and write accesses per second
    if (readQ.empty() && writeQ.empty()) {
        return {0, 0};
    } else if (writeQ.empty()) {
        return {getMeanAccesses(readQ.front()), 0};
    } else if (readQ.empty()) {
        return {0, getMeanAccesses(writeQ.front())};
    }
    return {getMeanAccesses(readQ.front()), getMeanAccesses(writeQ.front())};
}

unsigned long long SocketMemoryRecords::getLast(queue<MemoryRecord> q, unsigned long long lastPoppedMCTime) {
    if (q.empty()) {
        if (lastPoppedMCTime == numeric_limits<unsigned long long>::max()) {
            // No popped elements yet
            return 0;
        }
        return lastPoppedMCTime;
    }
    return q.back().t1;
}

tuple<unsigned long long, int, int> SocketMemoryRecords::getSmallestElement() {
    // Return the smaller time in read and write queues, its MC key and if it is a read or write
    unsigned long long smallerMCTime = numeric_limits<unsigned long long>::max();
    int smallerMCkey = -1;
    int state = -1; // 0: read is smaller, 1: write is smaller

    for (int mcID : memoryControllerIDs) {
        if (!reads[mcID].empty() && reads[mcID].front().t1 < smallerMCTime) {
            smallerMCTime = reads[mcID].front().t1;
            smallerMCkey = mcID;
            state = 0;
        }
        if (!writes[mcID].empty() && writes[mcID].front().t1 < smallerMCTime) {
            smallerMCTime = writes[mcID].front().t1;
            smallerMCkey = mcID;
            state = 1;
        }
    }

    // cout << "Smaller: " << smallerMCTime << " " << smallerMCkey << " " << state << endl;
    return {smallerMCTime, smallerMCkey, state};
}

int SocketMemoryRecords::checkMRTime(MemoryRecord mr) {
    if (mr.t0 < mr.t1) {
        return 1;
    } else if (mr.t0 > mr.t1) {
        throw runtime_error("Cannot process bandwidth because the given time interval has t0 > t1.");
    }
    // Case when t0 == t1
    if (mr.n > 0) {
        if (mr.t0 == 0) {
            if (displayWarnings) {
                cerr << "Warning: Ignoring the first time interval with a given value of 0." << endl;
            }
            return -1;
        } else {
            throw runtime_error("Cannot process bandwidth because the given time interval is 0 (t0 = t1 = " + to_string(mr.t0) + ").");
        }
    }
    return 0;
}

double SocketMemoryRecords::getMRBandwidth(MemoryRecord mr, uint cacheLineBytes) {
    int check = checkMRTime(mr);
    if (check == -1)  return -1;
    else if (check == 0) return 0;

    if (mr.n == 0) return 0;

    // Calculate total "load" in GB
    double load = cacheLineBytes * mr.n / pow(10, 9);
    // Calculate elapsed times in seconds
    double elapsedSeconds = (mr.t1 - mr.t0) / pow(10, 9);
    // Calculate read and write bandwidths in GB/s
    // cout << "Calc BW " << mr.n << " " << load << " " << elapsedSeconds << endl;
    return load / elapsedSeconds;
}

double SocketMemoryRecords::getMeanAccesses(MemoryRecord mr) {
    int check = checkMRTime(mr);
    if (check == -1)  return -1;
    else if (check == 0) return 0;

    if (mr.n == 0) return 0;

    // Calculate elapsed times in seconds
    double elapsedSeconds = (mr.t1 - mr.t0) / pow(10, 9);
    // Calculate mean read or write accesses per second
    return mr.n / elapsedSeconds;
}

bool SocketMemoryRecords::areAllQueuesFull(map<int, queue<MemoryRecord>> m) {
    for (auto it = m.begin(); it != m.end(); it++) {
        if (it->second.empty()) {
            return false;
        }
    }
    return true;
}

void SocketMemoryRecords::popOldestMCRecord(int mcID) {
    // cout << "Pop " << socketID << " " << mcID << " " << reads[mcID].front().t1 << " " << writes[mcID].front().t1 << " " << reads[mcID].empty() << " " << writes[mcID].empty() << endl;
    // Take care! If, instead of using these 2 variabes, we use directly reads/writes[mcID].front().t1,
    // we'll have a bug at the 3rd "if" after popping reads in the 2nd "if", because reads[mcID].front() would have changed after the pop
    unsigned long long readsT = reads[mcID].front().t1;
    unsigned long long writesT = writes[mcID].front().t1;
    if (!reads[mcID].empty() && !writes[mcID].empty()) {
        if (readsT <= writesT) {
            lastPoppedTimePerMC[mcID] = readsT;
            lastPoppedTime = readsT;
            reads[mcID].pop();
        }
        // Keep it as a separate "if" because reads and writes could have the same t1 and, in this case, we want to pop both
        if (writesT <= readsT) {
            lastPoppedTimePerMC[mcID] = writesT;
            lastPoppedTime = writesT;
            writes[mcID].pop();
        }
    } else if (!reads[mcID].empty() && writes[mcID].empty()) {
        lastPoppedTimePerMC[mcID] = readsT;
        lastPoppedTime = readsT;
        reads[mcID].pop();
    } else if (!writes[mcID].empty() && reads[mcID].empty()) {
        lastPoppedTimePerMC[mcID] = writesT;
        lastPoppedTime = writesT;
        writes[mcID].pop();
    } else {
        throw runtime_error("Cannot pop an element from empty read and writes queues.");
    }
    // cout << "Last popped time: " << lastPoppedTime << endl;
}

void SocketMemoryRecords::popOldestRecords() {
    // Remove oldest read and/or write records from the queues and save their last 't1' values.
    // If there are multiple entires with the same timestamp, remove all of them.
    // unsigned long long lastSmaller = numeric_limits<unsigned long long>::max();
    auto [smallerMCt1, smallerMCkey, state] = getSmallestElement();
    // cout << lastPoppedTime << " " << smallerMCt1 << " " << smallerMCkey << " " << state << endl;

    // Pop all MCs that have the same smallest time
    do {
        if (state == -1) {
            // If there are no elements in the queues, return
            return;
        }

        if (state == 0) {
            reads[smallerMCkey].pop();
        } else if (state == 1) {
            writes[smallerMCkey].pop();
        }
        // cout << "POP " << to_string(smallerMCkey) << " " << to_string(smallerMCt1) << endl;
        lastPoppedTimePerMC[smallerMCkey] = smallerMCt1;
        lastPoppedTime = smallerMCt1;

        auto [smallerMCt1_2, smallerMCkey_2, state_2] = getSmallestElement();
        smallerMCt1 = smallerMCt1_2;
        smallerMCkey = smallerMCkey_2;
        state = state_2;
    }
    while (smallerMCt1 <= lastPoppedTime);
}

void SocketMemoryRecords::printMapQueues(map<int, queue<MemoryRecord>> m) {
    for (int mcID : memoryControllerIDs) {
        if (!m[mcID].empty()) {
            cout << "\t\t" << mcID << ":" << endl;
            while (!m[mcID].empty()) {
                cout << "\t\t\t" << m[mcID].front().t0 << " " << m[mcID].front().t1 << " " << m[mcID].front().n << endl;
                m[mcID].pop();
            }
        }
    }
}