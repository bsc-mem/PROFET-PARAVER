/* Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
 * You may use, distribute and modify this code under the
 * terms of the BSD-3 license.
 *
 * You should have received a copy of the BSD-3 license with
 * this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
 */

// pcfmemoryparser.cpp
#include "pcfmemoryparser.h"

PCFMemoryParser::PCFMemoryParser() {}

PCFMemoryParser::PCFMemoryParser(string inPCFFilePath, int base_event_type) {
    this->inPCFFilePath = inPCFFilePath;
    this->base_event_type = base_event_type;
}

void PCFMemoryParser::writeOutput(string outPCFFilePath, vector<string> memoryMetricsLabels, int precision) {
  PCFFileParser<> inPCFFile(inPCFFilePath);
  inPCFFile.openPCFFileParser(inPCFFilePath, inPCFFile);

  PCFFileParser<> outPCFFile(outPCFFilePath);

  // Copy part of the original pcf
  string level = inPCFFile.getLevel();
  outPCFFile.setLevel(level);
  string units = inPCFFile.getUnits();
  outPCFFile.setUnits(units);
  string lookback = inPCFFile.getLookBack();
  outPCFFile.setLookBack(lookback);
  string speed = inPCFFile.getSpeed();
  outPCFFile.setSpeed(speed);
  string flagIcs = inPCFFile.getFlagIcons();
  outPCFFile.setFlagIcons(flagIcs);
  string ymaxScale = inPCFFile.getYmaxScale();
  outPCFFile.setYmaxScale(ymaxScale);
  string threadFunc = inPCFFile.getThreadFunc();
  outPCFFile.setThreadFunc(threadFunc);
  for (auto const &[state, label] : inPCFFile.getStates()) {
    outPCFFile.setState(state, label);
  }
  for (auto const &[semanticValue, color] : inPCFFile.getSemanticColors()) {
    outPCFFile.setSemanticColor(semanticValue, color);
  }

  // Define new event types for memory metrics
  for (long unsigned int i = 0; i < memoryMetricsLabels.size(); i++) {
    outPCFFile.setEventType(base_event_type + 1, precision, memoryMetricsLabels[i], {});
  }

  outPCFFile.dumpToFile(outPCFFilePath);
}