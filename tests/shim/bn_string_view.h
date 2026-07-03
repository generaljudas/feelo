// Host-test shim replacing Butano's bn_string_view.h.
#ifndef BN_STRING_VIEW_H
#define BN_STRING_VIEW_H

#include <string_view>

namespace bn
{
using string_view = std::string_view;
}

#endif
