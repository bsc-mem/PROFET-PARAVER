/* Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
 * You may use, distribute and modify this code under the
 * terms of the BSD-3 license.
 *
 * You should have received a copy of the BSD-3 license with
 * this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
 */

// pcfmemoryparser_intel.h
#ifndef PCFMMEMORYPARSERINTEL_H
#define PCFMMEMORYPARSERINTEL_H

#include <string>

using namespace std;

#include "pcfmemoryparser.h"

class PCFMemoryParserIntel : public PCFMemoryParser {
  public:
    PCFMemoryParserIntel(string inPCFFilePath, int base_event_type);

    // Returns a map with the event type as key and memoryEvent as value
    map<int, MemoryEvent> getMemoryEventTypes();

};

#endif
