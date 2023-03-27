/* Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
 * You may use, distribute and modify this code under the
 * terms of the BSD-3 license.
 *
 * You should have received a copy of the BSD-3 license with
 * this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
 */

// pcfmemoryparser_factory.h
#ifndef PCFMMEMORYPARSERFACTORY_H
#define PCFMMEMORYPARSERFACTORY_H

#include <iostream>

using namespace std;

#include "pcfmemoryparser.h"


class PCFMemoryParserFactory {
  public:
    PCFMemoryParser* pcfMemParser;

    PCFMemoryParserFactory(string inPCFFilePath, string pmuType);

    PCFMemoryParser* getPCFMemoryParser();
};

#endif
