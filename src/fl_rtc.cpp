#include "fl_rtc.h"

#include "bn_date.h"
#include "bn_optional.h"
#include "bn_sstream.h"
#include "bn_time.h"

#include "fl_checkin.h"

namespace fl::rtc
{

namespace
{
    constexpr bn::string_view week_days[7] = {"SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"};

    void append_hour_minute(bn::istring_base& text, int hour, int minute)
    {
        bn::ostringstream stream(text);
        int hour_12 = hour % 12;

        if(hour_12 == 0)
        {
            hour_12 = 12;
        }

        stream.append(hour_12);
        stream.append(':');

        if(minute < 10)
        {
            stream.append('0');
        }

        stream.append(minute);
        stream.append(hour < 12 ? 'A' : 'P');
    }
}

bool present()
{
    return bn::date::active() && bn::time::active();
}

uint32_t now_packed()
{
    if(! present())
    {
        return 0;
    }

    bn::optional<bn::date> date = bn::date::current();
    bn::optional<bn::time> time = bn::time::current();

    if(! date || ! time)
    {
        return 0;
    }

    // The S-3511 RTC stores a two-digit year; Butano reports it raw.
    int year = date->year();

    if(year < 100)
    {
        year += 2000;
    }

    if(year < 2000 || year > 2063)
    {
        return 0;
    }

    // Derive the week day from the date: the RTC's week-day register is
    // app-defined and differs between cartridges.
    int week_day = int((day_number(year, date->month(), date->month_day()) + 3) % 7);

    return pack_datetime(year, date->month(), date->month_day(), time->hour(), time->minute(),
                         week_day);
}

bn::string<20> clock_text()
{
    bn::string<20> result;
    uint32_t now = now_packed();

    if(! now)
    {
        return result;
    }

    bn::ostringstream stream(result);
    int week_day = dt_week_day(now);

    if(week_day >= 0 && week_day < 7)
    {
        stream.append(week_days[week_day]);
        stream.append(' ');
    }

    stream.append(dt_month(now));
    stream.append('/');
    stream.append(dt_day(now));
    stream.append(' ');
    append_hour_minute(result, dt_hour(now), dt_minute(now));
    return result;
}

bn::string<8> time_text(uint32_t dt)
{
    bn::string<8> result;

    if(dt)
    {
        append_hour_minute(result, dt_hour(dt), dt_minute(dt));
    }

    return result;
}

}
