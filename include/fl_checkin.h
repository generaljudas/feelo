#ifndef FL_CHECKIN_H
#define FL_CHECKIN_H

#include <cstdint>

#include "bn_string_view.h"

namespace fl
{

// One check-in record: 8 bytes, packed, trivially copyable (bn::sram requirement).
// Full binary layout documented in docs/DATA_FORMAT.md — keep them in sync.
struct check_in
{
    // Packed local timestamp, 0 when the RTC was unavailable:
    //   bits 26-28: week day + 1 (1 = Sunday .. 7 = Saturday), 0 = unknown
    //   bits 20-25: year - 2000 (0..63)
    //   bits 16-19: month (1..12)
    //   bits 11-15: day of month (1..31)
    //   bits  6-10: hour (0..23)
    //   bits  0-5:  minute (0..59)
    uint32_t datetime;

    int8_t valence;   // -100 (awful) .. +100 (great)
    int8_t energy;    // -100 (drained) .. +100 (wired)
    uint8_t focus;    // 0 (lost) .. 200 (locked in); 0xFF = skipped
    uint8_t flags;    // see flag_* below
};

static_assert(sizeof(check_in) == 8);

constexpr uint8_t flag_focus_present = 0x01;
constexpr uint8_t flag_rtc_valid = 0x02;

constexpr uint8_t focus_skipped = 0xFF;

[[nodiscard]] constexpr uint32_t pack_datetime(int year, int month, int day, int hour, int minute,
                                               int week_day)
{
    return (uint32_t(week_day + 1) << 26) | (uint32_t(year - 2000) << 20) | (uint32_t(month) << 16) |
            (uint32_t(day) << 11) | (uint32_t(hour) << 6) | uint32_t(minute);
}

[[nodiscard]] constexpr int dt_week_day(uint32_t dt) { return int((dt >> 26) & 0x7) - 1; }
[[nodiscard]] constexpr int dt_year(uint32_t dt)     { return int((dt >> 20) & 0x3F) + 2000; }
[[nodiscard]] constexpr int dt_month(uint32_t dt)    { return int((dt >> 16) & 0xF); }
[[nodiscard]] constexpr int dt_day(uint32_t dt)      { return int((dt >> 11) & 0x1F); }
[[nodiscard]] constexpr int dt_hour(uint32_t dt)     { return int((dt >> 6) & 0x1F); }
[[nodiscard]] constexpr int dt_minute(uint32_t dt)   { return int(dt & 0x3F); }

// Days since 2000-03-01-based civil epoch; only relative differences are used.
[[nodiscard]] constexpr int32_t day_number(int year, int month, int day)
{
    int y = year;
    if(month <= 2)
    {
        --y;
    }

    int era = y / 400;
    int yoe = y - era * 400;
    int doy = (153 * (month + (month > 2 ? -3 : 9)) + 2) / 5 + day - 1;
    int doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return int32_t(era) * 146097 + doe;
}

[[nodiscard]] constexpr int32_t day_number(uint32_t dt)
{
    return day_number(dt_year(dt), dt_month(dt), dt_day(dt));
}

// The 3x3 mood-pad zone: row 0 = high energy, col 0 = negative valence.
// Matches the mascot sprite frame order.
[[nodiscard]] constexpr int mood_zone(int valence, int energy)
{
    int col = valence < -33 ? 0 : (valence > 33 ? 2 : 1);
    int row = energy > 33 ? 0 : (energy < -33 ? 2 : 1);
    return row * 3 + col;
}

inline constexpr bn::string_view mood_words[9] = {
    "STRESSED", "WIRED", "PUMPED",
    "DOWN", "OKAY", "HAPPY",
    "DRAINED", "SLEEPY", "COZY",
};

inline constexpr bn::string_view focus_words[5] = {
    "LOCKED IN", "STEADY", "SO-SO", "SCATTERED", "LOST",
};

// Focus option index (0..4, 0 = locked in) <-> stored 0..200 scale (200 = locked in).
[[nodiscard]] constexpr uint8_t focus_value(int option) { return uint8_t((4 - option) * 50); }
[[nodiscard]] constexpr int focus_option(int value) { return 4 - ((value + 25) / 50); }

}

#endif
