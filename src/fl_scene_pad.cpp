#include "fl_scenes.h"

#include "bn_bg_palettes.h"
#include "bn_color.h"
#include "bn_core.h"
#include "bn_fixed.h"
#include "bn_keypad.h"
#include "bn_math.h"
#include "bn_string.h"
#include "bn_regular_bg_ptr.h"
#include "bn_sound_items.h"
#include "bn_sprite_ptr.h"
#include "bn_sprite_tiles_ptr.h"
#include "bn_vector.h"

#include "bn_regular_bg_items_bg_pad.h"
#include "bn_sprite_items_cursor.h"
#include "bn_sprite_items_mascot.h"

namespace fl
{

namespace
{
    // The pad's play area in pixels; matches the frame drawn in bg_pad.bmp.
    constexpr int pad_half = 60;

    // Quadrant tint colors: [energy>=0][valence>=0]
    constexpr bn::color quadrant_colors[2][2] = {
        {bn::color(9, 11, 24), bn::color(9, 22, 19)},    // low energy: blue / teal
        {bn::color(28, 10, 13), bn::color(31, 27, 17)},  // high energy: red / warm yellow
    };
}

scene_id scene_pad(context& ctx)
{
    bn::regular_bg_ptr bg = bn::regular_bg_items::bg_pad.create_bg(0, 0);

    // Start from the previous position for quick "same as before" check-ins.
    bn::fixed x = bn::fixed(ctx.pending.valence) * pad_half / 100;
    bn::fixed y = bn::fixed(-ctx.pending.energy) * pad_half / 100;

    bn::sprite_ptr cursor = bn::sprite_items::cursor.create_sprite(x, y);
    bn::sprite_ptr mascot = bn::sprite_items::mascot.create_sprite(x, y - 26);

    bn::vector<bn::sprite_ptr, 16> label_sprites;
    bn::vector<bn::sprite_ptr, 24> hint_sprites;
    ctx.small_text->set_center_alignment();
    ctx.small_text->generate(0, -74, "WIRED", hint_sprites);
    ctx.small_text->generate(0, 70, "DRAINED", hint_sprites);
    ctx.small_text->generate(-96, -2, "ROUGH", hint_sprites);
    ctx.small_text->generate(96, -2, "GREAT", hint_sprites);

    bn::vector<bn::sprite_ptr, 12> value_sprites;

    int last_zone = -1;
    int last_valence = 999;
    int last_energy = 999;
    int pulse = 0;

    while(true)
    {
        bn::fixed speed = 1.25;

        if(bn::keypad::left_held())
        {
            x -= speed;
        }

        if(bn::keypad::right_held())
        {
            x += speed;
        }

        if(bn::keypad::up_held())
        {
            y -= speed;
        }

        if(bn::keypad::down_held())
        {
            y += speed;
        }

        x = bn::clamp(x, bn::fixed(-pad_half), bn::fixed(pad_half));
        y = bn::clamp(y, bn::fixed(-pad_half), bn::fixed(pad_half));

        int valence = (x * 100 / pad_half).round_integer();
        int energy = (-y * 100 / pad_half).round_integer();

        cursor.set_position(x, y);
        mascot.set_position(x, y - 26);

        // Pulse the cursor ring.
        ++pulse;
        cursor.set_tiles(bn::sprite_items::cursor.tiles_item().create_tiles((pulse >> 4) & 1));

        int zone = mood_zone(valence, energy);

        if(zone != last_zone)
        {
            last_zone = zone;
            mascot.set_tiles(bn::sprite_items::mascot.tiles_item().create_tiles(zone));

            label_sprites.clear();
            ctx.big_text->set_center_alignment();
            ctx.big_text->generate(0, -58, mood_words[zone], label_sprites);
        }

        if(valence != last_valence || energy != last_energy)
        {
            last_valence = valence;
            last_energy = energy;

            // Tint towards the quadrant color, stronger away from the center.
            bn::color tint = quadrant_colors[energy >= 0][valence >= 0];
            int intensity = bn::max(bn::abs(valence), bn::abs(energy));
            bn::bg_palettes::set_fade(tint, bn::fixed(intensity) * 35 / 10000);

            value_sprites.clear();
            bn::string<24> values;
            values += 'V';
            values += valence >= 0 ? '+' : '-';
            values += bn::to_string<4>(bn::abs(valence));
            values += "  E";
            values += energy >= 0 ? '+' : '-';
            values += bn::to_string<4>(bn::abs(energy));
            ctx.small_text->generate(0, 58, values, value_sprites);
        }

        if(bn::keypad::a_pressed())
        {
            ctx.pending = check_in{};
            ctx.pending.valence = int8_t(valence);
            ctx.pending.energy = int8_t(energy);
            ctx.pending.focus = focus_skipped;
            bn::sound_items::sfx_blip.play(bn::fixed(0.6));
            return scene_id::focus;
        }

        if(bn::keypad::b_pressed())
        {
            return scene_id::home;
        }

        bn::core::update();
    }
}

}
