// Host-test shim replacing Butano's bn_sram.h: SRAM is a 32KB RAM buffer
// that tests can inspect, corrupt and dump to a .sav file.
#ifndef BN_SRAM_H
#define BN_SRAM_H

#include <cstdint>
#include <cstring>

namespace bn::sram
{

inline uint8_t buffer[32768];

[[nodiscard]] constexpr int size()
{
    return 32768;
}

template<typename Type>
void read_offset(Type& destination, int offset)
{
    std::memcpy(&destination, buffer + offset, sizeof(Type));
}

template<typename Type>
void write_offset(const Type& source, int offset)
{
    std::memcpy(buffer + offset, &source, sizeof(Type));
}

template<typename Type>
void read(Type& destination)
{
    read_offset(destination, 0);
}

template<typename Type>
void write(const Type& source)
{
    write_offset(source, 0);
}

}

#endif
