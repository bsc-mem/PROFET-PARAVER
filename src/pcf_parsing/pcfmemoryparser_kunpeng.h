/* Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
 * You may use, distribute and modify this code under the
 * terms of the BSD-3 license.
 *
 * You should have received a copy of the BSD-3 license with
 * this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
 */

// pcfmemoryparser_kunpeng.h
#ifndef PCFMMEMORYPARSERKUNPENG_H
#define PCFMMEMORYPARSERKUNPENG_H

#include <string>

using namespace std;
#include "pcfmemoryparser.h"

class PCFMemoryParserKunpeng : public PCFMemoryParser {
  public:
    PCFMemoryParserKunpeng(string inPCFFilePath, int base_event_type);

    // Returns a map with the event type as key and memoryEvent as value
    map<int, MemoryEvent> getMemoryEventTypes();

};

#endif
