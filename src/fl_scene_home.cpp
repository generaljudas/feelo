#include "fl_scenes.h"

#include "bn_core.h"
#include "bn_keypad.h"
#include "bn_regular_bg_ptr.h"
#include "bn_sprite_ptr.h"
#include "bn_string.h"
#include "bn_vector.h"

#include "bn_regular_bg_items_bg_soft.h"
#include "bn_sprite_items_mascot.h"

#include "fl_insights.h"
#include "fl_rtc.h"
#include "fl_storage.h"

namespace fl
{

scene_id scene_home(context& ctx)
{
    bn::regular_bg_ptr bg = bn::regular_bg_items::bg_soft.create_bg(0, 0);

    // Mascot mirrors the recent average mood (neutral on a fresh log).
    insights::summary week = insights::window_summary(7);
    int frame = week.n ? mood_zone(week.avg_valence, week.avg_energy) : 4;
    bn::sprite_ptr mascot = bn::sprite_items::mascot.create_sprite(0, -14, frame);
    mascot.set_scale(2);

    bn::vector<bn::sprite_ptr, 24> title_sprites;
    ctx.big_text->set_center_alignment();
    ctx.big_text->generate(0, -66, "FEELO", title_sprites);

    bn::vector<bn::sprite_ptr, 32> info_sprites;
    ctx.small_text->set_center_alignment();

    int streak = insights::streak_days();

    if(streak > 0)
    {
        bn::string<32> text("STREAK ");
        text += bn::to_string<8>(streak);
        text += streak == 1 ? " DAY" : " DAYS";
        ctx.small_text->generate(0, 34, text, info_sprites);
    }
    else if(storage::count())
    {
        ctx.small_text->generate(0, 34, "WELCOME BACK", info_sprites);
    }
    else
    {
        ctx.small_text->generate(0, 34, "HOW DO YOU FEEL?", info_sprites);
    }

    ctx.small_text->generate(0, 62, "A: CHECK IN    SELECT: STATS", info_sprites);

    bn::vector<bn::sprite_ptr, 12> clock_sprites;
    int frames_to_clock_refresh = 0;

    while(true)
    {
        if(! frames_to_clock_refresh)
        {
            frames_to_clock_refresh = 60;
            clock_sprites.clear();

            bn::string<20> clock = rtc::clock_text();

            if(! clock.empty())
            {
                ctx.small_text->generate(0, -50, clock, clock_sprites);
            }
        }

        --frames_to_clock_refresh;

        if(bn::keypad::a_pressed())
        {
            return scene_id::pad;
        }

        if(bn::keypad::select_pressed())
        {
            return scene_id::stats;
        }

        bn::core::update();
    }
}

}
