/* Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
 * You may use, distribute and modify this code under the
 * terms of the BSD-3 license.
 *
 * You should have received a copy of the BSD-3 license with
 * this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
 */

// memoryevent.h
#ifndef MEMORYEVENT_H
#define MEMORYEVENT_H

class MemoryEvent {
  public:
    int mc; // memory controler ID
    int socket;
    bool isRead; // if is read or write

    MemoryEvent();
};

#endif