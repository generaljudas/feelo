/*
 * Feelo — a Game Boy Advance wellness check-in tracker.
 * zlib License; built with the Butano engine (https://github.com/GValiente/butano).
 */

#include "bn_bg_palettes.h"
#include "bn_core.h"
#include "bn_log.h"
#include "bn_sprite_text_generator.h"

#include "common_variable_8x16_sprite_font.h"
#include "common_variable_8x8_sprite_font.h"

#include "fl_rtc.h"
#include "fl_scenes.h"
#include "fl_storage.h"

#ifdef FL_AUTOPILOT
    #include "fl_autopilot_commands.h"
#endif

int main()
{
#ifdef FL_AUTOPILOT
    // Smoke-test build: replays a scripted input session (see
    // tools/gen_autopilot.py) instead of reading the keypad.
    bn::core::init(fl::autopilot_commands);
#else
    bn::core::init();
#endif

    fl::storage::init();

    BN_LOG("feelo: boot ok, records=", fl::storage::count(),
           fl::storage::fresh_boot() ? " (fresh save)" : "",
           ", rtc=", fl::rtc::present() ? "present" : "absent");

    bn::sprite_text_generator big_text(common::variable_8x16_sprite_font);
    bn::sprite_text_generator small_text(common::variable_8x8_sprite_font);

    fl::context ctx;
    ctx.big_text = &big_text;
    ctx.small_text = &small_text;

    fl::scene_id scene = fl::scene_id::home;

    while(true)
    {
        bn::bg_palettes::set_fade_intensity(0);

        // Consume the key edge that triggered the previous scene change:
        // scenes read the keypad before their first update, so without this
        // a single A press would cascade through several scenes at once.
        bn::core::update();

        switch(scene)
        {

        case fl::scene_id::home:
            scene = fl::scene_home(ctx);
            break;

        case fl::scene_id::pad:
            scene = fl::scene_pad(ctx);
            break;

        case fl::scene_id::focus:
            scene = fl::scene_focus(ctx);
            break;

        case fl::scene_id::confirm:
            scene = fl::scene_confirm(ctx);
            break;

        case fl::scene_id::stats:
            scene = fl::scene_stats(ctx);
            break;
        }
    }
}
