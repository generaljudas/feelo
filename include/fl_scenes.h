#ifndef FL_SCENES_H
#define FL_SCENES_H

#include "bn_sprite_text_generator.h"

#include "fl_checkin.h"

namespace fl
{

enum class scene_id
{
    home,
    pad,
    focus,
    confirm,
    stats,
};

// Shared per-check-in state carried between scenes.
struct context
{
    check_in pending{};
    bn::sprite_text_generator* big_text;    // 8x16 variable font
    bn::sprite_text_generator* small_text;  // 8x8 variable font
};

[[nodiscard]] scene_id scene_home(context& ctx);
[[nodiscard]] scene_id scene_pad(context& ctx);
[[nodiscard]] scene_id scene_focus(context& ctx);
[[nodiscard]] scene_id scene_confirm(context& ctx);
[[nodiscard]] scene_id scene_stats(context& ctx);

}

#endif
