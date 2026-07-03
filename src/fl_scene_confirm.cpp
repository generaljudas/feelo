#include "fl_scenes.h"

#include "bn_core.h"
#include "bn_keypad.h"
#include "bn_regular_bg_ptr.h"
#include "bn_sound_items.h"
#include "bn_sprite_ptr.h"
#include "bn_sprite_tiles_ptr.h"
#include "bn_vector.h"

#include "bn_regular_bg_items_bg_soft.h"
#include "bn_sprite_items_mascot.h"

#include "fl_insights.h"
#include "fl_rtc.h"
#include "fl_storage.h"

namespace fl
{

scene_id scene_confirm(context& ctx)
{
    // Stamp and persist the record; this is the single point where a
    // check-in is committed to SRAM.
    uint32_t now = rtc::now_packed();
    ctx.pending.datetime = now;

    if(now)
    {
        ctx.pending.flags |= flag_rtc_valid;
    }

    storage::append(ctx.pending);

    bn::regular_bg_ptr bg = bn::regular_bg_items::bg_soft.create_bg(0, 0);
    bn::sprite_ptr mascot = bn::sprite_items::mascot.create_sprite(0, -14, 9);
    mascot.set_scale(2);

    bn::vector<bn::sprite_ptr, 16> title_sprites;
    ctx.big_text->set_center_alignment();
    ctx.big_text->generate(0, -62, "LOGGED!", title_sprites);

    bn::vector<bn::sprite_ptr, 32> info_sprites;
    ctx.small_text->set_center_alignment();

    bn::string<32> line("CHECK-IN #");
    line += bn::to_string<12>(storage::total_written());
    bn::string<8> time = rtc::time_text(now);

    if(! time.empty())
    {
        line += "  ";
        line += time;
    }

    ctx.small_text->generate(0, 34, line, info_sprites);

    int streak = insights::streak_days();

    if(streak > 1)
    {
        bn::string<32> streak_line("STREAK ");
        streak_line += bn::to_string<8>(streak);
        streak_line += " DAYS!";
        ctx.small_text->generate(0, 48, streak_line, info_sprites);
    }

    bn::sound_items::sfx_tada.play(bn::fixed(0.7));

    for(int frame = 0; frame < 180; ++frame)
    {
        // Celebration bounce between the two YAY frames.
        bool up = (frame >> 4) & 1;
        mascot.set_tiles(bn::sprite_items::mascot.tiles_item().create_tiles(up ? 9 : 10));
        mascot.set_y(up ? -16 : -12);

        if(bn::keypad::a_pressed() || bn::keypad::b_pressed() || bn::keypad::start_pressed())
        {
            break;
        }

        bn::core::update();
    }

    return scene_id::home;
}

}
