// Host-side test of the Feelo storage engine and record format.
//
// Compiles the real fl_storage.cpp against a RAM-backed bn_sram.h shim,
// exercises fresh boot / append / reload / corruption recovery / ring wrap,
// then dumps SRAM to a .sav for tools/parse_save.py to cross-check.
//
// Build & run (from repo root):
//   c++ -std=c++20 -Itests/shim -Iinclude tests/host_test.cpp src/fl_storage.cpp -o build/host_test
//   ./build/host_test build/test.sav

#include <cassert>
#include <cstdio>
#include <cstring>

#include "bn_sram.h"
#include "fl_checkin.h"
#include "fl_storage.h"

using namespace fl;

namespace
{
    check_in make_record(int i)
    {
        check_in record{};
        record.datetime = pack_datetime(2026, 7, 1 + (i % 28), (i * 3) % 24, i % 60, i % 7);
        record.valence = int8_t((i * 17) % 201 - 100);
        record.energy = int8_t((i * 31) % 201 - 100);
        record.focus = (i % 4 == 3) ? focus_skipped : uint8_t((i % 5) * 50);
        record.flags = flag_rtc_valid | ((i % 4 == 3) ? 0 : flag_focus_present);
        return record;
    }

    bool records_equal(const check_in& a, const check_in& b)
    {
        return std::memcmp(&a, &b, sizeof(check_in)) == 0;
    }
}

int main(int argc, char** argv)
{
    // 1. Fresh boot: uninitialized SRAM reads as 0xFF on real hardware.
    std::memset(bn::sram::buffer, 0xFF, sizeof(bn::sram::buffer));
    storage::init();
    assert(storage::fresh_boot());
    assert(storage::count() == 0);
    assert(storage::total_written() == 0);

    // 2. Append and read back.
    for(int i = 0; i < 5; ++i)
    {
        storage::append(make_record(i));
    }

    assert(storage::count() == 5);
    assert(storage::total_written() == 5);
    assert(records_equal(storage::get(0), make_record(4)));   // newest
    assert(records_equal(storage::get(4), make_record(0)));   // oldest

    // 3. Reload from SRAM (simulated power cycle).
    storage::init();
    assert(! storage::fresh_boot());
    assert(storage::count() == 5);
    assert(records_equal(storage::get(2), make_record(2)));

    // 4. Corrupt the NEWEST header copy; recovery falls back to the stale
    // copy, losing at most the latest append (designed crash-safety bound).
    // After 5 appends write_seq is 6, so copy A (even seq) is the newest.
    bn::sram::buffer[4] ^= 0xA5;
    storage::init();
    assert(! storage::fresh_boot());
    assert(storage::count() == 4);
    assert(records_equal(storage::get(0), make_record(3)));

    // Re-append the lost record; the rewritten header heals copy A.
    storage::append(make_record(4));
    storage::init();
    assert(storage::count() == 5);
    assert(records_equal(storage::get(0), make_record(4)));

    // 5. Corrupt BOTH copies: must reformat cleanly, not crash.
    std::memset(bn::sram::buffer, 0x00, storage::log_offset);
    storage::init();
    assert(storage::fresh_boot());
    assert(storage::count() == 0);

    for(int i = 0; i < 5; ++i)
    {
        storage::append(make_record(i));
    }

    assert(storage::count() == 5);

    // 6. Ring wrap: fill past capacity; the oldest records fall off.
    int extra = storage::capacity + 20 - 5;

    for(int i = 5; i < 5 + extra; ++i)
    {
        storage::append(make_record(i));
    }

    assert(storage::count() == storage::capacity);
    assert(storage::total_written() == uint32_t(storage::capacity) + 20);
    assert(storage::wrapped());
    assert(records_equal(storage::get(0), make_record(storage::capacity + 20 - 1)));
    assert(records_equal(storage::get(storage::capacity - 1), make_record(20)));

    storage::init();
    assert(storage::count() == storage::capacity);
    assert(records_equal(storage::get(0), make_record(storage::capacity + 20 - 1)));

    // 7. Reset and write a small, human-checkable log, then dump to .sav.
    std::memset(bn::sram::buffer, 0xFF, sizeof(bn::sram::buffer));
    storage::init();

    for(int i = 0; i < 12; ++i)
    {
        storage::append(make_record(i));
    }

    if(argc > 1)
    {
        std::FILE* file = std::fopen(argv[1], "wb");

        if(! file)
        {
            std::perror("fopen");
            return 1;
        }

        std::fwrite(bn::sram::buffer, 1, sizeof(bn::sram::buffer), file);
        std::fclose(file);
        std::printf("wrote %s (12 records)\n", argv[1]);
    }

    // 8. Sanity-check the shared helpers.
    static_assert(mood_zone(100, 100) == 2);
    static_assert(mood_zone(-100, 100) == 0);
    static_assert(mood_zone(0, 0) == 4);
    static_assert(mood_zone(100, -100) == 8);
    static_assert(focus_value(0) == 200);
    static_assert(focus_value(4) == 0);
    static_assert(focus_option(200) == 0);
    static_assert(focus_option(0) == 4);
    static_assert(dt_year(pack_datetime(2026, 7, 2, 21, 30, 4)) == 2026);
    static_assert(dt_month(pack_datetime(2026, 7, 2, 21, 30, 4)) == 7);
    static_assert(dt_day(pack_datetime(2026, 7, 2, 21, 30, 4)) == 2);
    static_assert(dt_hour(pack_datetime(2026, 7, 2, 21, 30, 4)) == 21);
    static_assert(dt_minute(pack_datetime(2026, 7, 2, 21, 30, 4)) == 30);
    static_assert(dt_week_day(pack_datetime(2026, 7, 2, 21, 30, 4)) == 4);
    static_assert(day_number(2026, 7, 2) - day_number(2026, 6, 30) == 2);
    static_assert(day_number(2024, 3, 1) - day_number(2024, 2, 28) == 2);   // leap year

    std::puts("host_test: ALL OK");
    return 0;
}
