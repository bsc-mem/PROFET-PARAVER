/* Copyright (C) 2023 Isaac Boixaderas - All Rights Reserved
 * You may use, distribute and modify this code under the
 * terms of the BSD-3 license.
 *
 * You should have received a copy of the BSD-3 license with
 * this file. If not, please visit: https://opensource.org/licenses/BSD-3-Clause
 */

// memoryrecord.h
#ifndef MEMORYRECORD_H
#define MEMORYRECORD_H

class MemoryRecord {
  public:
    unsigned long long t0, t1; // Start and end times of the memory event
    unsigned long long n; // Total number of reads and writes between t0 and t1

    MemoryRecord();
};

#endif