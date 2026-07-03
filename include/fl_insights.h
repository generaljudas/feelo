#ifndef FL_INSIGHTS_H
#define FL_INSIGHTS_H

#include "fl_checkin.h"

namespace fl::insights
{

struct summary
{
    int n = 0;                // records considered
    int avg_valence = 0;
    int avg_energy = 0;
    int focus_n = 0;          // records with a focus answer
    int avg_focus = 0;        // 0..200, valid when focus_n > 0
};

// Average over the last `days` calendar days when the RTC is available,
// otherwise over the newest `days` records (a check-in-per-day approximation).
[[nodiscard]] summary window_summary(int days);

// Consecutive days with at least one check-in, anchored at today (RTC) or at
// the newest dated record. Undated records can't extend a streak.
[[nodiscard]] int streak_days();

// Best 4-hour bucket by average valence: 0 = 00-04h .. 5 = 20-24h.
// Returns -1 when no bucket has at least min_records dated records.
[[nodiscard]] int best_time_bucket(int min_records);

inline constexpr bn::string_view bucket_words[6] = {
    "SMALL HOURS", "EARLY MORNS", "MORNINGS", "AFTERNOONS", "EVENINGS", "LATE NIGHTS",
};

}

#endif
