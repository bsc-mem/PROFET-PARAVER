/* Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
 * You may use, distribute and modify this code under the
 * terms of the BSD-3 license.
 *
 * You should have received a copy of the BSD-3 license with
 * this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
 */

// pcfmemoryparser.h
#ifndef PCFMMEMORYPARSER_H
#define PCFMMEMORYPARSER_H

#include <iostream>
#include <map>
#include <string>
#include <regex>
#include <fstream>
#include "../memory_records/memoryevent.h"

using namespace std;

#include "pcffileparser.h"

class PCFMemoryParser {
  public:
    string inPCFFilePath;
    int base_event_type;
    string memoryEventIdentifier;

    PCFMemoryParser();
    PCFMemoryParser(string inPCFFilePath, int base_event_type);

    // Returns a map with the event type as key and memoryEvent as value
    virtual map<int, MemoryEvent> getMemoryEventTypes() = 0;

    void writeOutput(string outPCFFilePath, vector<string> memoryMetricsLabels,
                     int precision, bool keepOriginalTraceFile);

  private:
    void writeEventsOriginalTrace(PCFFileParser<> inPCFFile, PCFFileParser<>& outPCFFile);

};

#endif