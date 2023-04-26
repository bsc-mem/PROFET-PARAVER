/*****************************************************************************\
 *                        ANALYSIS PERFORMANCE TOOLS                         *
 *                               prv parse example                           *
 *                       Paraver Main Computing Library                      *
 *****************************************************************************
 *     ___     This library is free software; you can redistribute it and/or *
 *    /  __         modify it under the terms of the GNU LGPL as published   *
 *   /  /  _____    by the Free Software Foundation; either version 2.1      *
 *  /  /  /     \   of the License, or (at your option) any later version.   *
 * (  (  ( B S C )                                                           *
 *  \  \  \_____/   This library is distributed in hope that it will be      *
 *   \  \__         useful but WITHOUT ANY WARRANTY; without even the        *
 *    \___          implied warranty of MERCHANTABILITY or FITNESS FOR A     *
 *                  PARTICULAR PURPOSE. See the GNU LGPL for more details.   *
 *                                                                           *
 * You should have received a copy of the GNU Lesser General Public License  *
 * along with this library; if not, write to the Free Software Foundation,   *
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA          *
 * The GNU LEsser General Public License is contained in the file COPYING.   *
 *                                 ---------                                 *
 *   Barcelona Supercomputing Center - Centro Nacional de Supercomputacion   *
\*****************************************************************************/

#pragma once

#include "traceheader.h"
#include "tracebodyio_v1.h"
#include "processmodel.h"
#include "resourcemodel.h"
#include "tracetypes.h"


class MyRecord
{
  public:
    MyRecord() = default;
    MyRecord( TThreadOrder whichThread ) : thread( whichThread ) {}
    ~MyRecord() = default;

    TRecordType    getType() const            { return type; }
    TRecordTime    getTime() const            { return time; }
    TThreadOrder   getThread() const          { return thread; }
    TCPUOrder      getCPU() const             { return CPU; }
    TObjectOrder   getOrder() const           { return thread; }
    TEventType     getEventType() const       { return URecordInfo.eventRecord.type; }
    TSemanticValue getEventValue() const      { return URecordInfo.eventRecord.value; }
    TEventValue    getEventValueAsIs() const  { return URecordInfo.eventRecord.value; }
    TState         getState() const           { return URecordInfo.stateRecord.state; }
    TRecordTime    getStateEndTime() const    { return URecordInfo.stateRecord.endTime; }
    TThreadOrder   getSenderThread() const    { return thread; }
    TCPUOrder      getSenderCPU() const       { return CPU; }
    TThreadOrder   getReceiverThread() const  { return URecordInfo.commRecord.receiverThread; }
    TCPUOrder      getReceiverCPU() const     { return URecordInfo.commRecord.receiverCPU; }
    TCommTag       getCommTag() const         { return URecordInfo.commRecord.tag; }
    TCommSize      getCommSize() const        { return URecordInfo.commRecord.size; }
    TRecordTime    getLogicalSend() const     { return time; }
    TRecordTime    getLogicalReceive() const  { return URecordInfo.commRecord.logicalReceiveTime; }
    TRecordTime    getPhysicalSend() const    { return URecordInfo.commRecord.physicalSendTime; }
    TRecordTime    getPhysicalReceive() const { return URecordInfo.commRecord.physicalReceiveTime; }
    typedef struct TEventRecord
    {
      TEventType  type;
      TEventValue value;
    }
    TEventRecord;

    typedef struct TStateRecord
    {
      TState      state;
      TRecordTime endTime;
    }
    TStateRecord;

    typedef struct TCommRecord
    {
      TCommTag     tag;
      TCommSize    size;
      TCPUOrder    receiverCPU;
      TThreadOrder receiverThread;
      TRecordTime  physicalSendTime;
      TRecordTime  logicalReceiveTime;
      TRecordTime  physicalReceiveTime;
    }
    TCommRecord;

    TRecordType  type;
    TRecordTime  time;
    TThreadOrder thread;
    TCPUOrder    CPU;
    union
    {
      TStateRecord stateRecord;
      TEventRecord eventRecord;
      TCommRecord  commRecord;
    } URecordInfo;

};

class MyRecordContainer
{
  public:
    MyRecordContainer( ProcessModel<>& whichProcessModel ) : processModel( whichProcessModel ) {}
    ~MyRecordContainer() = default;

    void newRecord()                              { loadedRecords.emplace_back( ); }
    void newRecord( TThreadOrder whichThread )    { loadedRecords.emplace_back( whichThread ); }
    void setType( TRecordType whichType )         { loadedRecords.back().type = whichType; }
    void setTime( TRecordTime whichTime )         { loadedRecords.back().time = whichTime; }
    void setThread( TThreadOrder whichThread )    { loadedRecords.back().thread = whichThread; }
    void setThread( TApplOrder whichAppl,
                    TTaskOrder whichTask,
                    TThreadOrder whichThread )    { loadedRecords.back().thread = processModel.getGlobalThread( whichAppl, whichTask, whichThread ); }
    void setCPU( TCPUOrder whichCPU )             { loadedRecords.back().CPU = whichCPU; }
    void setEventType( TEventType whichType )     { loadedRecords.back().URecordInfo.eventRecord.type = whichType; }
    void setEventValue( TEventValue whichValue )  { loadedRecords.back().URecordInfo.eventRecord.value = whichValue; }
    void setState( TState whichState )            { loadedRecords.back().URecordInfo.stateRecord.state = whichState; }
    void setStateEndTime( TRecordTime whichTime ) { loadedRecords.back().URecordInfo.stateRecord.endTime = whichTime; }

    void newComm( bool createRecords = true )          { newRecord(); loadedRecords.back().type = COMM + LOG + SEND; }
    void newComm( TThreadOrder whichThread,  TThreadOrder whichRemoteThread ) {
      newRecord( whichThread );
      loadedRecords.back().type = COMM + LOG + SEND;
      loadedRecords.back().URecordInfo.commRecord.receiverThread = whichRemoteThread;
    }
    void setSenderThread( TThreadOrder whichThread )   { loadedRecords.back().thread = whichThread; }
    void setSenderThread( TApplOrder whichAppl,
                          TTaskOrder whichTask,
                          TThreadOrder whichThread )   { loadedRecords.back().thread = processModel.getGlobalThread( whichAppl, whichTask, whichThread ); }
    void setSenderCPU( TCPUOrder whichCPU )            { loadedRecords.back().CPU = whichCPU; }
    void setReceiverThread( TThreadOrder whichThread ) { loadedRecords.back().URecordInfo.commRecord.receiverThread = whichThread; }
    void setReceiverThread( TApplOrder whichAppl,
                          TTaskOrder whichTask,
                          TThreadOrder whichThread )   { loadedRecords.back().URecordInfo.commRecord.receiverThread = processModel.getGlobalThread( whichAppl, whichTask, whichThread ); }
    void setReceiverCPU( TCPUOrder whichCPU )          { loadedRecords.back().URecordInfo.commRecord.receiverCPU = whichCPU; }
    void setCommTag( TCommTag whichTag )               { loadedRecords.back().URecordInfo.commRecord.tag = whichTag; }
    void setCommSize( TCommSize whichSize )            { loadedRecords.back().URecordInfo.commRecord.size = whichSize; }
    void setLogicalSend( TRecordTime whichTime )       { loadedRecords.back().time = whichTime; }
    void setLogicalReceive( TRecordTime whichTime )    { loadedRecords.back().URecordInfo.commRecord.logicalReceiveTime = whichTime;}
    void setPhysicalSend( TRecordTime whichTime )      { loadedRecords.back().URecordInfo.commRecord.physicalSendTime = whichTime; }
    void setPhysicalReceive( TRecordTime whichTime )   { loadedRecords.back().URecordInfo.commRecord.physicalReceiveTime = whichTime;  }

    vector<MyRecord>& getLoadedRecords() { return loadedRecords; }
    
  private:
    vector<MyRecord> loadedRecords;
    ProcessModel<>& processModel;
};


class MyMetadataManager
{
  public:
    MyMetadataManager() = default;
    ~MyMetadataManager() = default;

    vector<string> metadata;

    bool NewMetadata( string MetadataStr ) {
      metadata.push_back( MetadataStr );
      return true;
    }
};

