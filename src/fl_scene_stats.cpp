#include "fl_scenes.h"

#include "bn_core.h"
#include "bn_keypad.h"
#include "bn_math.h"
#include "bn_regular_bg_ptr.h"
#include "bn_sprite_ptr.h"
#include "bn_string.h"
#include "bn_vector.h"

#include "bn_regular_bg_items_bg_soft.h"
#include "bn_sprite_items_dot.h"
#include "bn_sprite_items_mascot.h"

#include "fl_insights.h"
#include "fl_storage.h"

namespace fl
{

namespace
{
    void append_signed(bn::string<48>& text, int value)
    {
        text += value >= 0 ? '+' : '-';
        text += bn::to_string<4>(value >= 0 ? value : -value);
    }
}

scene_id scene_stats(context& ctx)
{
    bn::regular_bg_ptr bg = bn::regular_bg_items::bg_soft.create_bg(0, 0);

    bn::vector<bn::sprite_ptr, 16> title_sprites;
    ctx.big_text->set_center_alignment();
    ctx.big_text->generate(0, -70, "STATS", title_sprites);

    bn::vector<bn::sprite_ptr, 96> text_sprites;
    ctx.small_text->set_left_alignment();

    int y = -50;
    int n = storage::count();

    {
        bn::string<48> line("TOTAL ");
        line += bn::to_string<12>(storage::total_written());

        int streak = insights::streak_days();

        if(streak)
        {
            line += "   STREAK ";
            line += bn::to_string<8>(streak);
            line += streak == 1 ? " DAY" : " DAYS";
        }

        ctx.small_text->generate(-104, y, line, text_sprites);
        y += 14;
    }

    insights::summary week = insights::window_summary(7);
    insights::summary month = insights::window_summary(30);

    const insights::summary* summaries[2] = {&week, &month};
    const bn::string_view labels[2] = {"7D:  ", "30D: "};

    for(int row = 0; row < 2; ++row)
    {
        const insights::summary& s = *summaries[row];
        bn::string<48> line(labels[row]);

        if(s.n)
        {
            line += mood_words[mood_zone(s.avg_valence, s.avg_energy)];
            line += "  V";
            append_signed(line, s.avg_valence);
            line += " E";
            append_signed(line, s.avg_energy);
            line += " (";
            line += bn::to_string<8>(s.n);
            line += ')';
        }
        else
        {
            line += "NO DATA YET";
        }

        ctx.small_text->generate(-104, y, line, text_sprites);
        y += 14;
    }

    if(week.focus_n)
    {
        bn::string<48> line("FOCUS 7D: ");
        line += focus_words[focus_option(week.avg_focus)];
        ctx.small_text->generate(-104, y, line, text_sprites);
    }

    y += 14;

    if(int bucket = insights::best_time_bucket(3); bucket >= 0)
    {
        bn::string<48> line("BEST: ");
        line += insights::bucket_words[bucket];
        ctx.small_text->generate(-104, y, line, text_sprites);
    }

    // Sparkline of the last 32 check-ins (oldest -> newest), valence as height.
    bn::vector<bn::sprite_ptr, 70> spark_sprites;

    {
        constexpr int max_points = 32;
        constexpr int base_y = 46;
        int points = bn::min(n, max_points);

        for(int i = 0; i < max_points; ++i)
        {
            spark_sprites.push_back(bn::sprite_items::dot.create_sprite(-96 + i * 6, base_y, 1));
        }

        for(int i = 0; i < points; ++i)
        {
            check_in record = storage::get(points - 1 - i);
            int dy = -record.valence * 22 / 100;
            spark_sprites.push_back(bn::sprite_items::dot.create_sprite(-96 + i * 6, base_y + dy, 0));
        }
    }

    bn::vector<bn::sprite_ptr, 24> hint_sprites;
    ctx.small_text->set_center_alignment();
    ctx.small_text->generate(0, 70, "B: BACK", hint_sprites);

    while(true)
    {
        if(bn::keypad::b_pressed() || bn::keypad::select_pressed() || bn::keypad::start_pressed())
        {
            return scene_id::home;
        }

        bn::core::update();
    }
}

}
