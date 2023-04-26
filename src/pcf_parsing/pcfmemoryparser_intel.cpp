/* Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
 * You may use, distribute and modify this code under the
 * terms of the BSD-3 license.
 *
 * You should have received a copy of the BSD-3 license with
 * this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
 */

// pcfmemoryparser_intel.cpp
#include "pcfmemoryparser_intel.h"

PCFMemoryParserIntel::PCFMemoryParserIntel(string inPCFFilePath, int base_event_type) {
    this->inPCFFilePath = inPCFFilePath;
    this->base_event_type = base_event_type;
}

map<int, MemoryEvent> PCFMemoryParserIntel::getMemoryEventTypes() {
  // Returns a map with the event type as key and memoryEvent as value
  map<int, MemoryEvent> memEventTypes;
  // Memory events regexs
  
  regex memEventMCRegex("^.*unc_imc(\\d+)::UNC_M_CAS_COUNT.*$$"); // extract MC
  regex memEventCPURegex("^.*UNC_M_CAS_COUNT.*:cpu=(\\d+) .*$"); // extract CPU
  regex memReadEventRegex("^\\d+ +(\\d+).*UNC_M_CAS_COUNT:RD:.*$"); // extract event type of a read
  regex memWriteEventRegex("^\\d+ +(\\d+).*UNC_M_CAS_COUNT:WR:.*$"); // extract event type of a write
  vector<int> uniqueCPUs;

  ifstream input(inPCFFilePath);

  if (!input.good()) {
    cerr << "ERROR: pcf file not found: " << inPCFFilePath << endl;
    exit(1);
  }

  string line;
  smatch cpuMatch, mcMatch, rdMatch, wrMatch;

  while (getline(input, line)) {
    if (regex_search(line, cpuMatch, memEventCPURegex)) {
      // Extract CPU value if it's a memory event
      int cpu = stoi(cpuMatch[1].str());
      if (find(uniqueCPUs.begin(), uniqueCPUs.end(), cpu) == uniqueCPUs.end()) {
        // Add CPU if not already included
        uniqueCPUs.push_back(cpu);
      }

      MemoryEvent memEvt;

      // Get socket index based on CPU value
      auto it = find(uniqueCPUs.begin(), uniqueCPUs.end(), cpu);
      if (it != uniqueCPUs.end()) {
        memEvt.socket = it - uniqueCPUs.begin();
      }
      else {
        cerr << "ERROR when getting CPU in uniqueCPUs vector: cpu=" << cpu << endl;
        exit(1);
      }

      // Get MC
      if (regex_search(line, mcMatch, memEventMCRegex)) {
        memEvt.mc = stoi(mcMatch[1].str());
      }

      // Set if event type is read or write in the socket 
      if (regex_search(line, rdMatch, memReadEventRegex)) {
        memEvt.isRead = true;
        memEventTypes.insert( {stoi(rdMatch[1].str()), memEvt} );
      }
      else if (regex_search(line, wrMatch, memWriteEventRegex)) {
        memEvt.isRead = false;
        memEventTypes.insert( {stoi(wrMatch[1].str()), memEvt} );
      }
      else {
        cerr << "ERROR: unrecognized memory event " << line << endl;
        exit(1);
      }
    }
  }

  if (memEventTypes.empty()) {
    cerr << "ERROR: no memory event types found in pcf file: " << inPCFFilePath << endl;
    exit(1);
  }
  
  return memEventTypes;
}
