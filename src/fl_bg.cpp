#include "fl_bg.h"

#include "bn_regular_bg_items_bg_home_day.h"
#include "bn_regular_bg_items_bg_home_dusk.h"
#include "bn_regular_bg_items_bg_home_night.h"
#include "bn_regular_bg_items_bg_pad_day.h"
#include "bn_regular_bg_items_bg_pad_dusk.h"
#include "bn_regular_bg_items_bg_pad_night.h"

#include "fl_checkin.h"
#include "fl_rtc.h"

namespace fl::bg
{

phase current_phase()
{
    uint32_t now = rtc::now_packed();

    if(! now)
    {
        return phase::night;
    }

    int hour = dt_hour(now);

    if(hour >= 8 && hour < 18)
    {
        return phase::day;
    }

    if((hour >= 5 && hour < 8) || (hour >= 18 && hour < 21))
    {
        return phase::dusk;
    }

    return phase::night;
}

bn::regular_bg_ptr create_soft()
{
    switch(current_phase())
    {

    case phase::day:
        return bn::regular_bg_items::bg_home_day.create_bg(0, 0);

    case phase::dusk:
        return bn::regular_bg_items::bg_home_dusk.create_bg(0, 0);

    default:
        return bn::regular_bg_items::bg_home_night.create_bg(0, 0);
    }
}

bn::regular_bg_ptr create_pad()
{
    switch(current_phase())
    {

    case phase::day:
        return bn::regular_bg_items::bg_pad_day.create_bg(0, 0);

    case phase::dusk:
        return bn::regular_bg_items::bg_pad_dusk.create_bg(0, 0);

    default:
        return bn::regular_bg_items::bg_pad_night.create_bg(0, 0);
    }
}

}
