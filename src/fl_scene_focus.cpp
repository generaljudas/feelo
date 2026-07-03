#include "fl_scenes.h"

#include "bn_core.h"
#include "bn_keypad.h"
#include "bn_regular_bg_ptr.h"
#include "bn_sound_items.h"
#include "bn_sprite_ptr.h"
#include "bn_vector.h"

#include "bn_sprite_items_focus_icons.h"

#include "fl_bg.h"

namespace fl
{

scene_id scene_focus(context& ctx)
{
    bn::regular_bg_ptr backdrop = bg::create_soft();

    bn::vector<bn::sprite_ptr, 24> title_sprites;
    ctx.big_text->set_center_alignment();
    ctx.big_text->generate(0, -58, "HOW'S YOUR FOCUS?", title_sprites);

    bn::vector<bn::sprite_ptr, 24> hint_sprites;
    ctx.small_text->set_center_alignment();
    ctx.small_text->generate(0, 62, "A: PICK    B: SKIP", hint_sprites);

    bn::vector<bn::sprite_ptr, 5> icons;

    for(int i = 0; i < 5; ++i)
    {
        icons.push_back(bn::sprite_items::focus_icons.create_sprite((i - 2) * 40, 0, i));
    }

    bn::vector<bn::sprite_ptr, 12> label_sprites;
    int selected = 2;
    int last_selected = -1;
    int wobble = 0;

    while(true)
    {
        if(bn::keypad::left_pressed() && selected > 0)
        {
            --selected;
        }

        if(bn::keypad::right_pressed() && selected < 4)
        {
            ++selected;
        }

        if(selected != last_selected)
        {
            last_selected = selected;
            label_sprites.clear();
            ctx.small_text->generate(0, 26, focus_words[selected], label_sprites);
        }

        ++wobble;

        for(int i = 0; i < 5; ++i)
        {
            bool active = i == selected;
            icons[i].set_scale(active ? 2 : 1);
            icons[i].set_y(active ? ((wobble >> 4) & 1 ? -2 : 0) : 0);
        }

        if(bn::keypad::a_pressed())
        {
            ctx.pending.focus = focus_value(selected);
            ctx.pending.flags |= flag_focus_present;
            bn::sound_items::sfx_blip.play(bn::fixed(0.6));
            return scene_id::confirm;
        }

        if(bn::keypad::b_pressed())
        {
            ctx.pending.focus = focus_skipped;
            return scene_id::confirm;
        }

        bn::core::update();
    }
}

}
