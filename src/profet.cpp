/* Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
 * You may use, distribute and modify this code under the
 * terms of the BSD-3 license.
 *
 * You should have received a copy of the BSD-3 license with
 * this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
 */

#include <string>
#include <vector>
#include <tuple>
#include <map>
#include <cmath>
#include <queue>
#include <algorithm>
#include <filesystem>
#include <libgen.h>
#include <unistd.h>
#include <getopt.h>
#include <boost/property_tree/ptree.hpp>
#include <boost/property_tree/json_parser.hpp>

using namespace std;
namespace pt = boost::property_tree;
namespace fs = std::filesystem;

#include "prvparse.h"
#include "pcf_parsing/pcfmemoryparser_factory.h"
#include "memory_records/memoryevent.h"
#include "memory_records/memoryrecord.h"
#include "memory_records/socketmemoryrecords.h"
#include "memory_records/nodememoryrecords.h"
#include "cpp_py_adaptation/profetpyadapter.h"
#include "rowfileparser.h"



string getProjectPath() {
  // Returns home path of current project
  char result[PATH_MAX];
  ssize_t count = readlink("/proc/self/exe", result, PATH_MAX);
  string exec_path;
  if (count != -1) {
      exec_path = dirname(result);
      exec_path.replace(exec_path.find("bin"), 3, "");
  }
  else {
    cerr << "Unable to locate current execution path." << endl;
    exit(1);
  }
  return exec_path;
}

string PROJECT_PATH = getProjectPath();
int PRECISION = 2; // Decimal precision for memory metrics
int PROFET_BASE_EVENT_TYPE = 94000000; // Base event type for Profet events in Paraver


void printHelp() {
  cout << "Usage: profet [OPTION] <input_trace_file.prv> <output_trace_file.prv> <configuration_file.json>\n\n";
  // cout << "-i, --input=FILE\n"
  //         "\t\tInput prv file\n"
  //         "-o, --output=FILE\n"
  //         "\t\tOutput prv file\n"
  //         "-c, --config=FILE\n"
  //         "\t\tConfiguration file\n"
  cout << "-s, --socket\n"
          "\t\tCompute memory stress metrics per socket instead of per memory [DIMM/channel/controller]\n"
          "-w, --no_warnings\n"
          "\t\tDo not show warning messages\n"
          "-t, --no_text\n"
          "\t\tDo not show info text messages\n"
          "-d, --no_dash\n"
          "\t\tDo not run dash (interactive plots)\n"
          "-h, --help, ?\n"
          "\t\tShow help\n";
  exit(1);
}

tuple<string, string, string, bool, int, int, int> processArgs(int argc, char** argv) {
  if (argc < 3) {
    printHelp();
  }

  // const char* const short_opts = "i:o:c:w";
  const char* const short_opts = "swtdh";
  const option long_opts[] = {
          // {"input", required_argument, nullptr, 'i'},
          // {"output", required_argument, nullptr, 'o'},
          // {"config", required_argument, nullptr, 'c'},
          {"socket", no_argument, nullptr, 's'},
          {"no_warnings", no_argument, nullptr, 'w'},
          {"no_text", no_argument, nullptr, 't'},
          {"no_dash", no_argument, nullptr, 'd'},
          {"help", no_argument, nullptr, 'h'},
          {nullptr, no_argument, nullptr, 0}
  };
  
  int displayText = 1; // whether to display info text or not (it need to be an integer for sending it to python (booleans don't work))
  int displayWarnings = 1; // whether to display warnings or not (it need to be an integer for sending it to python (booleans don't work))
  int runDash = 1; // whether to run dash or not (it need to be an integer for sending it to python (booleans don't work))
  bool perSocket = false;
  int opt;

  while ((opt = getopt_long(argc, argv, short_opts, long_opts, nullptr)) != -1) {
    switch (opt) {
      case 's':
          perSocket = true;
          break;

      case 'w':
          displayWarnings = 0;
          break;

      case 't':
          displayText = 0;
          break;

      case 'd':
          runDash = 0;
          break;

      case 'h': // -h or --help
      case '?': // Unrecognized option
      default:
          printHelp();
          break;
    }
  }

  if (optind != argc - 3) {
    // There must be 3 non-option arguments to process (in, out and config files)
    // Show usage if it is not the case
    printHelp();
  }

  // Get all of the non-option arguments
  string inFile = argv[optind];
  optind++;
  string outFile = argv[optind];
  if (fs::is_directory(outFile)) {
    // If the output file argument is specified as a directory, use the same file name as the input name
    string inFileName = inFile.substr(inFile.find_last_of("/\\") + 1);
    fs::path dir (outFile);
    fs::path file (inFileName);
    outFile = (dir / file).u8string();
  }
  optind++;
  string configFile = argv[optind];

  return {inFile, outFile, configFile, perSocket, displayWarnings, displayText, runDash};
}

tuple<string, string, float, int> readConfigFile(string configFile) {
  pt::ptree root;
  pt::read_json(configFile, root);
  // Read values
  string memorySystem = root.get<string>("memory_system");
  string cpuModel = root.get<string>("cpu_model");
  float cpuFreqGHz = root.get<float>("cpu_freq_ghz");
  int cacheLineBytes = root.get<int>("cache_line_bytes");

  return {memorySystem, cpuModel, cpuFreqGHz, cacheLineBytes};
}

vector<string> getNodeNames(string rowInputFile, int nNodes) {
  // TODO should use rowfileparser instead of custom read
  // RowFileParser<> inRowFile;
  ifstream input(rowInputFile);

  if (!input.good()) {
    cerr << "ERROR: row file not found: " << rowInputFile << endl;
    exit(1);
  }

  bool readingNodes = false;
  int readCount = 0;
  vector<string> nodeNames(nNodes);
  string line;
  while (readCount < nNodes) {
    getline(input, line);
    if (readingNodes) {
      nodeNames[readCount] = line;
      readCount++;
    }
    else if (line.find("LEVEL NODE") != std::string::npos) {
      readingNodes = true;
    }
  }

  return nodeNames;
}

bool isMemoryEvent(map<int, MemoryEvent> memEventTypes, TEventValue evtValue) {
  if (memEventTypes.find(evtValue) != memEventTypes.end()) {
    // Key not in map
    return true;
  }
  return false;
}

void addProcessModelHierarchy(map<int, vector<int>> MCsPerSocket, int nNodes, ProcessModel <> &originalProcessModel,
                              ProcessModel<> &outputProcessModel, bool perSocket) {
  // Keep hierarchy of the original process model (only the 1st app, we  can ignore the second (memory counters))
  // We can assume we always have 2 apps.
  auto originalFirstApplIt = originalProcessModel.cbegin();
  outputProcessModel.addApplication();
  // auto taskIt = originalFirstApplIt.cbegin();
  int iTask = 0;
  for (auto taskIt = originalFirstApplIt->cbegin(); taskIt != originalFirstApplIt->cend(); taskIt++, iTask++) {
    // Add task to application 0
    outputProcessModel.addTask(0);
    TNodeOrder execNode = taskIt->getNodeExecution();
    for (long unsigned int iThread = 0; iThread < taskIt->size(); iThread++) {
      // Add thread to application 0, task iTask
      outputProcessModel.addThread(0, iTask, execNode);
    }
  }

  // Add application, task, thread hierarchy to output process model
  for (int iNode = 0; iNode < nNodes; iNode++) {
    outputProcessModel.addApplication();
    int appID = iNode + 1;
    if (perSocket) {
      // app=node, task=, thread=
      for (const auto &[socketID, memoryControllerIDs] : MCsPerSocket) {
        outputProcessModel.addTask(appID);
        outputProcessModel.addThread(appID, socketID, iNode);
      }
    } else {
      // app=node, task=socket, thread=mem. controller
      for (const auto &[socketID, memoryControllerIDs] : MCsPerSocket) {
        outputProcessModel.addTask(appID);
        for (long unsigned int mcID = 0; mcID < memoryControllerIDs.size(); mcID++) {
          // cout << appID << " " << mcID << endl;
          outputProcessModel.addThread(appID, socketID, iNode);
          // cout << to_string(outputProcessModel.totalApplications()) << " " << to_string(outputProcessModel.totalTasks()) << " " << to_string(outputProcessModel.totalThreads()) << endl;
        }
      }
    }
  }
}

void writePreviousRecords(multimap<TRecordTime, MyRecord> &outputRecords,
                          unsigned long long smallestTime,
                          ProcessModel<> outputProcessModel,
                          ResourceModel<> outputResourceModel,
                          TraceBodyIO_v1< fstream, MyRecordContainer, ProcessModel<>, ResourceModel<>, TState, TEventType, MyMetadataManager, TTime, MyRecord > &outputTraceBody,
                          fstream &outputTraceFile) {
  // Write outputRecords previous or at the same time as smallestTime to the output trace file
  while (!outputRecords.empty() && outputRecords.begin()->first <= smallestTime) {
    outputTraceBody.write(outputTraceFile, outputProcessModel, outputResourceModel, &outputRecords.begin()->second);
    outputRecords.erase(outputRecords.begin());
  }
}

void writeMemoryMetricsRecord(vector<int> metrics,
                              int nodeID,
                              int socketID,
                              int mcIDcorrespondence,
                              unsigned long long lastPoppedTime,
                              vector<float> lastWrittenMetrics,
                              ProcessModel<> outputProcessModel,
                              ResourceModel<> outputResourceModel,
                              TraceBodyIO_v1< fstream, MyRecordContainer, ProcessModel<>, ResourceModel<>, TState, TEventType, MyMetadataManager, TTime, MyRecord > &outputTraceBody,
                              fstream &outputTraceFile) {
  // Write metrics record to the prv
  int thread;
  // appID is nodeID + 1, because app 0 is preserved for the original process model
  // The rest of apps are added for PROFET based on the number of nodes
  int appID = nodeID + 1;
  if (mcIDcorrespondence == -1) {
    thread = outputProcessModel.getGlobalThread(appID, socketID, 0);
  } else {
    thread = outputProcessModel.getGlobalThread(appID, socketID, mcIDcorrespondence);
  }
  // cout << "Node: " << nodeID << " Socket: " << socketID << " MC: " << mcIDcorrespondence << endl;
  // cout << "Global Thread: " << thread << endl;
  // cout << "Last popped time: " << lastPoppedTime << "; metrics size: " << metrics.size() << endl;
  // cout << endl;
  for (long unsigned int iMetric = 0; iMetric < metrics.size(); ++iMetric) {
    MyRecord tmpRecord;
    if (lastWrittenMetrics.empty() || lastWrittenMetrics[iMetric] != metrics[iMetric]) {
      // Write new record only if the metric is different from the last written value in the same socket
      tmpRecord.type = EVENT;
      tmpRecord.time = lastPoppedTime;
      tmpRecord.thread = thread;
      tmpRecord.CPU = 0;
      tmpRecord.URecordInfo.eventRecord.type = PROFET_BASE_EVENT_TYPE + iMetric + 1;
      tmpRecord.URecordInfo.eventRecord.value = metrics[iMetric];
      // Write new record to output trace
      outputTraceBody.write(outputTraceFile, outputProcessModel, outputResourceModel, &tmpRecord);
    }
  }
}

// TODO could maybe be optimized by tracking smallest time per nodes? we still would need to know if it's processable every time...
bool processAndWriteMemoryMetricsIfPossible(vector<NodeMemoryRecords> &nodes,
                                            ProfetPyAdapter &profetPyAdapter,
                                            bool allowEmptyQueues,
                                            multimap<TRecordTime, MyRecord> &outputRecords,
                                            ProcessModel<> outputProcessModel,
                                            ResourceModel<> outputResourceModel,
                                            TraceBodyIO_v1< fstream, MyRecordContainer, ProcessModel<>, ResourceModel<>, TState, TEventType, MyMetadataManager, TTime, MyRecord > &outputTraceBody,
                                            fstream &outputTraceFile) {
  // Returns if any node has been processed
  bool isSmallestTimeProcessable = false;
  unsigned long long smallestMCTime = numeric_limits<unsigned long long>::max();
  int smallestTimeINode = numeric_limits<int>::max();
  int smallestTimeSocketID = numeric_limits<int>::max();
  int smallestTimeMCID = numeric_limits<int>::max();
  int i = 0;
  for (NodeMemoryRecords &node : nodes) {
    auto [isProcessable, smallestMCTime2, smallestTimeSocketID2, smallestTimeMCID2] = node.isProcessableData(allowEmptyQueues);
    if (smallestMCTime2 < smallestMCTime) {
      isSmallestTimeProcessable = isProcessable;
      smallestMCTime = smallestMCTime2;
      smallestTimeINode = i;
      smallestTimeSocketID = smallestTimeSocketID2;
      smallestTimeMCID = smallestTimeMCID2;
    }
    i++;
  }

  if (isSmallestTimeProcessable) {
    // Write output trace file with memory metrics
    NodeMemoryRecords &node = nodes[smallestTimeINode];
    // cout << "Process " << smallestMCTime << " " << smallestTimeSocketID << " " << smallestTimeMCID << endl;
    vector<float> lastWrittenMetrics = node.getLastWrittenMetrics(smallestTimeSocketID, smallestTimeMCID);
    vector<float> metrics = node.processMemoryMetrics(profetPyAdapter, smallestTimeSocketID, smallestTimeMCID, allowEmptyQueues);
    // cout << "Example metrics: " << metrics[0] << " " << metrics[1] << endl;

    // Convert metrics to int because prv files do not accept decimals. The number of decimal places is specified in the pcf file
    // and it is stored in the PRECISION variable
    vector<int> metrics_int(metrics.size());
    for (long unsigned int i = 0; i < metrics.size(); i++) {
      // Do not allow negative metric values, they mean the calculated bandwidth is not theoretically possible.
      // Warnings are already printed in these cases
      if (metrics[i] >= 0) {
        // Round metric value to the closest int times 10^precision, paraver will then put the decimals properly
        float pow_10 = pow(10.0f, (float)PRECISION);
        metrics_int[i] = round(metrics[i] * pow_10);
      }
    }

    // Write all trace records that occurred before or at the same time as the current smallest time
    writePreviousRecords(outputRecords, smallestMCTime, outputProcessModel, outputResourceModel, outputTraceBody, outputTraceFile);

    SocketMemoryRecords &socket = node.sockets[smallestTimeSocketID];
    writeMemoryMetricsRecord(metrics_int, smallestTimeINode, smallestTimeSocketID, socket.memoryControllerIDsCorrespondence[smallestTimeMCID],
                             socket.getLastPoppedTime(), lastWrittenMetrics, outputProcessModel, outputResourceModel, outputTraceBody, outputTraceFile);
    node.setLastWrittenMetrics(smallestTimeSocketID, smallestTimeMCID, metrics);
    return true;
  }

  return false;
}

void writeRowFile(ProcessModel<> &originalProcessModel, RowFileParser<> inRowParser,
                  string rowOutputFile, vector<NodeMemoryRecords> &nodes, bool perSocket) {
  RowFileParser<> outRowFile;

  // Copy row file from original file (only app 0)
  auto originalFirstApplIt = originalProcessModel.cbegin();
  outRowFile.pushBack(TTraceLevel::APPLICATION, inRowParser.getRowLabel(TTraceLevel::APPLICATION, 0));
  int iTask = 0;
  for (auto taskIt = originalFirstApplIt->cbegin(); taskIt != originalFirstApplIt->cend(); taskIt++, iTask++) {
    // Add task to application 0
    outRowFile.pushBack(TTraceLevel::TASK, inRowParser.getRowLabel(TTraceLevel::TASK, iTask));
    for (long unsigned int iThread = 0; iThread < taskIt->size(); iThread++) {
      // Add thread to application 0, task iTask
      outRowFile.pushBack(TTraceLevel::THREAD, inRowParser.getRowLabel(TTraceLevel::THREAD, iThread));
    }
  }

  // Add custom PROFET row
  for (NodeMemoryRecords &node : nodes) {
    string nodeLabel = node.name;
    // Start at 2nd application
    outRowFile.pushBack(TTraceLevel::APPLICATION, nodeLabel);
    for (const auto &[socketID, memoryControllerIDs] : node.MCsPerSocket) {
      string socketLabel = nodeLabel + ".Skt" + to_string(socketID);
      outRowFile.pushBack(TTraceLevel::TASK, socketLabel);
      if (perSocket) {
        // Write metrics for each socket
        outRowFile.pushBack(TTraceLevel::THREAD, socketLabel);
      } else {
        for (long unsigned int mcID = 0; mcID < memoryControllerIDs.size(); mcID++) {
          // Write metrics for each socket and MC
          string mcLabel = socketLabel + ".MC" + to_string(mcID);
          outRowFile.pushBack(TTraceLevel::THREAD, mcLabel);
        }
      }
    }
  }

  outRowFile.dumpToFile(rowOutputFile);
}

void printFinalMessage(vector<NodeMemoryRecords> nodes, string prvOutputFile) {
  cout << "Processing complete!" << endl << endl;
  for (NodeMemoryRecords node : nodes) {
    node.printFinalMessage();
    cout << endl;
  }
  cout << "Output trace: " << prvOutputFile << endl;
}

int main(int argc, char *argv[]) {
  // Process arguments
  auto [inFile, outFile, configFile, perSocket, displayWarnings, displayText, runDash] = processArgs(argc, argv);
  auto [memorySystem, cpuModel, cpuFreqGHz, cacheLineBytes] = readConfigFile(configFile);

  cout << "Running PROFET..." << endl << endl;

  // Open input trace file
  fstream traceFile(inFile);
  if (!traceFile.good()) {
    cerr << "Error Opening File: " << inFile << endl;
    exit(1);
  }

  ProfetPyAdapter profetPyAdapter(PROJECT_PATH, cpuModel, memorySystem);

  // Check if given memory system and cpu are supported (i.e. we have the curves). It raises an error if it is not the case.
  profetPyAdapter.checkSystemSupported();

  // Get info from DB using profetPyAdapter
  string pmuType = profetPyAdapter.pmuType;
  string cpuMicroarch = profetPyAdapter.cpuMicroarch;

  // Set .pcf and .row file names based on the same path and name as the PRV file given as first argument
  string rowInputFile = regex_replace(inFile, regex(".prv"), ".row");
  string pcfInputFile = regex_replace(inFile, regex(".prv"), ".pcf");

  RowFileParser<> inRowFile(rowInputFile);

  // Map with event type as key and for each type the socket involved and if it is a read or not (thus a write)
  PCFMemoryParserFactory pcfMemParserFactory(pcfInputFile, pmuType, PROFET_BASE_EVENT_TYPE);
  PCFMemoryParser* pcfMemParser = pcfMemParserFactory.getPCFMemoryParser();
  map<int, MemoryEvent> memEventTypes = pcfMemParser->getMemoryEventTypes();

  // Mandatory variables needed by parsing classes
  ProcessModel<> processModel;
  ResourceModel<> resourceModel;
  unordered_set<TState> loadedStates;
  unordered_set<TEventType> loadedEvents;
  MyMetadataManager metadataManager;
  TTime traceEndTime;
  MyRecordContainer records(processModel);

  std::string traceDate;
  TTimeUnit traceTimeUnit;
  std::vector< std::string > communicators;

  // Trace header parsing. Initialize previous variables
  parseTraceHeader(traceFile, traceDate, traceTimeUnit, traceEndTime, resourceModel, processModel, communicators);
                    
  // Open output file to write trace
  string prvOutputFile(outFile);
  fstream outputTraceFile(prvOutputFile, ios_base::out);
  if (!outputTraceFile.good()) {
    cerr << "Error opening output file " << prvOutputFile << endl << endl;
    exit(1);
  }

  // Set .pcf and .row output file names
  string pcfOutputFile = prvOutputFile;
  string rowOutputFile = prvOutputFile;
  pcfOutputFile.replace(prvOutputFile.find(".prv"), 4, ".pcf");
  rowOutputFile.replace(prvOutputFile.find(".prv"), 4, ".row");

  // Object with read/write functions for records
  TraceBodyIO_v1< fstream, MyRecordContainer, ProcessModel<>, ResourceModel<>, TState, TEventType, MyMetadataManager, TTime, MyRecord > myTraceBody;
  TraceBodyIO_v1< fstream, MyRecordContainer, ProcessModel<>, ResourceModel<>, TState, TEventType, MyMetadataManager, TTime, MyRecord > outputTraceBody;

  ProcessModel<> outputProcessModel;

  // Keep track of the sockets and their MCs in each node
  map<int, vector<int>> MCsPerSocket;
  for (const auto [memEvtID, memEvt] : memEventTypes) {
    if (memEvt.isRead) {
      // Take only reads into account (writes are going to have the same socket-mc values)
      MCsPerSocket[memEvt.socket].push_back(memEvt.mc);
    }
  }
  // Sort MCs per socket by ID (sockets are already sorted as map keys)
  for (const auto &[socketID, memoryControllerIDs] : MCsPerSocket) {
    vector<int> sortedMCs = memoryControllerIDs;
    sort(sortedMCs.begin(), sortedMCs.end());
    MCsPerSocket[socketID] = sortedMCs;
  }

  int nNodes = resourceModel.totalNodes();
  vector<string> nodeNames = getNodeNames(rowInputFile, nNodes);
  vector<NodeMemoryRecords> nodes(nNodes);
  for (int iNode = 0; iNode < nNodes; iNode++) {
    // string nodeID = ; // TODO get ID from row
    int nodeID = iNode;
    nodes[iNode] = NodeMemoryRecords(nodeID, nodeNames[iNode], MCsPerSocket, perSocket, memorySystem,
                                     pmuType, cpuMicroarch, cpuModel, cpuFreqGHz, cacheLineBytes, displayWarnings);
  }

  addProcessModelHierarchy(MCsPerSocket, nNodes, processModel, outputProcessModel, perSocket);

  dumpTraceHeader(outputTraceFile, traceDate, traceEndTime, traceTimeUnit, resourceModel, outputProcessModel, communicators);

  // Records to be written to the output trace sorted ascendingly by time
  multimap<TRecordTime, MyRecord> outputRecords;

  // Loop that reads the trace file to the end
  while (!traceFile.eof()) {
    // Read one line and store records
    long unsigned int oldMetadataSize = metadataManager.metadata.size();
    myTraceBody.read(traceFile, records, processModel, resourceModel, loadedStates, loadedEvents, metadataManager, traceEndTime);
    
    bool isMetadata = oldMetadataSize < metadataManager.metadata.size();
    if (isMetadata) {
      // If the read line is a metadata, just write it to the output trace
      outputTraceFile << metadataManager.metadata.back() << endl;
      continue;
    }
    
    vector<MyRecord> &loadedRecords = records.getLoadedRecords();
    // Loop over stored records
    for (auto record : loadedRecords) {
      // TODO is this a global thread???
      auto globalThread = record.getThread();
      TApplOrder app;
      TTaskOrder task;
      TThreadOrder thread;
      processModel.getThreadLocation(globalThread, app, task, thread);
      // Ignore App 2 (zero-based) records (memory counters)
      if (app != 1) {
        outputRecords.insert(pair<TRecordTime, MyRecord>(record.getTime(), record));
      }

      TEventType evtType = record.getEventType();
      // Only consider memory events
      if (record.getType() != EVENT || !isMemoryEvent(memEventTypes, evtType)) {
        continue;
      }

      int iNode = processModel.getNode(record.getThread());
      int socketID = memEventTypes[evtType].socket;
      int mcID = memEventTypes[evtType].mc;
      NodeMemoryRecords &node = nodes[iNode];

      // Create new memory read record
      MemoryRecord mcRecord;
      if (memEventTypes[evtType].isRead) {
        mcRecord.t0 = node.sockets[socketID].getLastReadTime(mcID);
      } else {
        mcRecord.t0 = node.sockets[socketID].getLastWriteTime(mcID);
      }
      mcRecord.t1 = record.getTime();
      mcRecord.n = record.getEventValue();
      // Add memory record to its corresponding socket and MC
      memEventTypes[evtType].isRead ? node.addRead(socketID, mcID, mcRecord) : node.addWrite(socketID, mcID, mcRecord);

      // string readOrWrite = memEventTypes[evtType].isRead ? "R" : "W";
      // cout << readOrWrite << " " << iNode << " " << socketID << " " << mcID << " " << mcRecord.t0 << " " << mcRecord.t1 << " " << mcRecord.n << endl;
      // node.printSocketsQueues();
      // cout << endl;

      // Process socket queues while it's processable
      bool allowEmptyQueues = false;
      bool processed;
      do {
        processed = processAndWriteMemoryMetricsIfPossible(nodes, profetPyAdapter, allowEmptyQueues, outputRecords,
                                                            outputProcessModel, resourceModel, outputTraceBody, outputTraceFile);
      } while (processed);
    }

    // Need to clear the currently stored records
    loadedRecords.clear();
  }

  // Write data still in the queues that represent the final timestamps for which there is information
  bool allowEmptyQueues = true;
  bool processed;
  do {
    processed = processAndWriteMemoryMetricsIfPossible(nodes, profetPyAdapter, allowEmptyQueues, outputRecords,
                                                       outputProcessModel, resourceModel, outputTraceBody, outputTraceFile);
  } while (processed);

  // Write remaining records (if any)
  unsigned long long maxTime = numeric_limits<unsigned long long>::max();
  writePreviousRecords(outputRecords, maxTime, outputProcessModel, resourceModel, outputTraceBody, outputTraceFile);
  
  // Final write if pending event records
  outputTraceBody.writePendingMultiEvent(outputProcessModel);

  // Write new .row file for memory metrics
  writeRowFile(processModel, inRowFile, rowOutputFile, nodes, perSocket);

  // Write new .pcf file for memory metrics. Metric labels are the same in each node
  pcfMemParser->writeOutput(pcfOutputFile, nodes[0].getMetricLabels(), PRECISION);

  if (displayText) {
    printFinalMessage(nodes, prvOutputFile);
  }

  // Initialize dash app
  if (runDash) {
    cout << "\nLoading interactive plot..." << endl;
    profetPyAdapter.runDashApp(outFile, PRECISION, cpuFreqGHz);
  }

  traceFile.close();
  outputTraceFile.close();

  return 0;
}