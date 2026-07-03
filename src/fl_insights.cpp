#include "fl_insights.h"

#include "fl_rtc.h"
#include "fl_storage.h"

namespace fl::insights
{

namespace
{
    // Newest dated record's day, or today when the RTC works. INT32_MIN when
    // neither exists.
    [[nodiscard]] int32_t anchor_day()
    {
        if(uint32_t now = rtc::now_packed())
        {
            return day_number(now);
        }

        int n = storage::count();

        for(int age = 0; age < n; ++age)
        {
            check_in record = storage::get(age);

            if(record.datetime)
            {
                return day_number(record.datetime);
            }
        }

        return INT32_MIN;
    }
}

summary window_summary(int days)
{
    summary result;
    int n = storage::count();

    if(! n)
    {
        return result;
    }

    int32_t anchor = anchor_day();
    bool dated = anchor != INT32_MIN && rtc::present();
    int valence_sum = 0;
    int energy_sum = 0;
    int focus_sum = 0;

    for(int age = 0; age < n; ++age)
    {
        check_in record = storage::get(age);

        if(dated)
        {
            if(! record.datetime)
            {
                continue;
            }

            if(anchor - day_number(record.datetime) >= days)
            {
                break;
            }
        }
        else if(result.n >= days)
        {
            break;
        }

        ++result.n;
        valence_sum += record.valence;
        energy_sum += record.energy;

        if(record.focus != focus_skipped)
        {
            ++result.focus_n;
            focus_sum += record.focus;
        }
    }

    if(result.n)
    {
        result.avg_valence = valence_sum / result.n;
        result.avg_energy = energy_sum / result.n;
    }

    if(result.focus_n)
    {
        result.avg_focus = focus_sum / result.focus_n;
    }

    return result;
}

int streak_days()
{
    int32_t anchor = anchor_day();

    if(anchor == INT32_MIN)
    {
        return 0;
    }

    // Walk newest -> oldest counting consecutive distinct days. A streak is
    // still alive when its newest day is today or yesterday.
    int n = storage::count();
    int streak = 0;
    int32_t next_expected = 0;

    for(int age = 0; age < n; ++age)
    {
        check_in record = storage::get(age);

        if(! record.datetime)
        {
            continue;
        }

        int32_t record_day = day_number(record.datetime);

        if(! streak)
        {
            if(record_day == anchor || record_day == anchor - 1)
            {
                streak = 1;
                next_expected = record_day - 1;
            }
            else
            {
                break;
            }
        }
        else if(record_day == next_expected)
        {
            ++streak;
            next_expected = record_day - 1;
        }
        else if(record_day < next_expected)
        {
            break;
        }
        // record_day > next_expected: same day as one already counted; skip.
    }

    return streak;
}

int best_time_bucket(int min_records)
{
    if(! rtc::present())
    {
        return -1;
    }

    int sums[6] = {};
    int counts[6] = {};
    int n = storage::count();

    for(int age = 0; age < n; ++age)
    {
        check_in record = storage::get(age);

        if(! record.datetime)
        {
            continue;
        }

        int bucket = dt_hour(record.datetime) / 4;
        sums[bucket] += record.valence;
        ++counts[bucket];
    }

    int best = -1;
    int best_avg = -1000;

    for(int bucket = 0; bucket < 6; ++bucket)
    {
        if(counts[bucket] >= min_records)
        {
            int avg = sums[bucket] / counts[bucket];

            if(avg > best_avg)
            {
                best_avg = avg;
                best = bucket;
            }
        }
    }

    return best;
}

}
