/* Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
 * You may use, distribute and modify this code under the
 * terms of the BSD-3 license.
 *
 * You should have received a copy of the BSD-3 license with
 * this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
 */

// pcfmemoryparser_factory.cpp
#include "pcfmemoryparser_factory.h"
#include "pcfmemoryparser_intel.h"
#include "pcfmemoryparser_kunpeng.h"


PCFMemoryParserFactory::PCFMemoryParserFactory(string inPCFFilePath, string pmuType, int base_event_type) {
  if (pmuType == "intel") {
    pcfMemParser = new PCFMemoryParserIntel(inPCFFilePath, base_event_type);
  }
  else if (pmuType == "kunpeng") {
    pcfMemParser = new PCFMemoryParserKunpeng(inPCFFilePath, base_event_type);
  }
  else {
    cerr << "ERROR: unknown PMU type " << pmuType << endl;
    exit(1);
  }
}

PCFMemoryParser* PCFMemoryParserFactory::getPCFMemoryParser() {
  return pcfMemParser;
}
