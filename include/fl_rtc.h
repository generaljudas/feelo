#ifndef FL_RTC_H
#define FL_RTC_H

#include <cstdint>

#include "bn_string.h"

namespace fl::rtc
{

// True when the cartridge exposes a working real-time clock.
[[nodiscard]] bool present();

// Packed current local time (see fl::check_in::datetime), 0 when unavailable.
[[nodiscard]] uint32_t now_packed();

// "SAT 7/04 9:41P" style clock line; empty when the RTC is unavailable.
[[nodiscard]] bn::string<20> clock_text();

// "9:41P" style time for a packed datetime.
[[nodiscard]] bn::string<8> time_text(uint32_t dt);

}

#endif
