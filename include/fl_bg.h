#ifndef FL_BG_H
#define FL_BG_H

#include "bn_regular_bg_ptr.h"

namespace fl::bg
{

enum class phase
{
    day,     // 08..17
    dusk,    // 05..07 and 18..20
    night,   // 21..04, and whenever the RTC is unavailable
};

[[nodiscard]] phase current_phase();

// Time-of-day variant of the soft backdrop (home/focus/confirm/stats).
[[nodiscard]] bn::regular_bg_ptr create_soft();

// Time-of-day variant of the mood pad backdrop.
[[nodiscard]] bn::regular_bg_ptr create_pad();

}

#endif
