/* Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
 * You may use, distribute and modify this code under the
 * terms of the BSD-3 license.
 *
 * You should have received a copy of the BSD-3 license with
 * this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
 */

// pcfmemoryparser_kunpeng.cpp
#include "pcfmemoryparser_kunpeng.h"

PCFMemoryParserKunpeng::PCFMemoryParserKunpeng(string inPCFFilePath, int base_event_type) {
    this->inPCFFilePath = inPCFFilePath;
    this->base_event_type = base_event_type;
}

map<int, MemoryEvent> PCFMemoryParserKunpeng::getMemoryEventTypes() {
  // Returns a map with the event type as key and memoryEvent as value
  map<int, MemoryEvent> memEventTypes;

  // Memory events regexs
  regex memEventMCRegex("^.*_ddrc(\\d+).*$"); // extract MC
  regex memEventSCCLRegex("^.*hisi_sccl(\\d+).*$$"); // extract Socket
  regex memReadEventRegex("^\\d+ +(\\d+).*hisi_sccl.*::flux_rd:.*$"); // extract event type of a read
  regex memWriteEventRegex("^\\d+ +(\\d+).*hisi_sccl.*::flux_wr:.*$"); // extract event type of a write
  vector<int> uniqueCPUs;

  ifstream input(inPCFFilePath);

  if (!input.good()) {
    cerr << "ERROR: pcf file not found: " << inPCFFilePath << endl;
    exit(1);
  }

  string line;
  smatch scclMatch, mcMatch, rdMatch, wrMatch;

  while (getline(input, line)) {
    if (regex_search(line, scclMatch, memEventSCCLRegex)) {
      MemoryEvent memEvt;

      // TODO: HARDCODED socket and MC extraction, make it general

      // Extract socket value value if it's a memory event
      int sccl = stoi(scclMatch[1].str());
      if (sccl == 1 || sccl == 3) {
        memEvt.socket = 0;
      }
      else if (sccl == 5 || sccl == 7) {
        memEvt.socket = 1;
      }
      else {
        cerr << "ERROR: unknown SCCL " << sccl << ", check PCF file" << endl;
        exit(1);
      }

      // Get MC
      if (regex_search(line, mcMatch, memEventMCRegex)) {
        if (sccl == 3 || sccl == 7) {
          memEvt.mc = stoi(mcMatch[1].str()) + 4;
        } else {
          memEvt.mc = stoi(mcMatch[1].str());
        }
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
