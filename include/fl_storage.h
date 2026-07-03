#ifndef FL_STORAGE_H
#define FL_STORAGE_H

#include "fl_checkin.h"

namespace fl::storage
{

// SRAM layout: two 32-byte header copies, then a ring buffer of 8-byte records.
constexpr int header_bytes = 32;
constexpr int log_offset = header_bytes * 2;
constexpr int capacity = (32768 - log_offset) / int(sizeof(check_in));   // 4088 records

// Loads the log from SRAM, recovering from the newest valid header copy.
// Formats a fresh log when no valid header exists (first boot / corrupt SRAM).
void init();

// True when init() had to format a fresh log.
[[nodiscard]] bool fresh_boot();

// Records currently readable (<= capacity).
[[nodiscard]] int count();

// Total records ever written (keeps growing after the ring wraps).
[[nodiscard]] uint32_t total_written();

[[nodiscard]] bool wrapped();

// age 0 = newest record, age count()-1 = oldest.
[[nodiscard]] check_in get(int age);

void append(const check_in& record);

}

#endif
