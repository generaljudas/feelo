#include "fl_storage.h"

#include "bn_sram.h"

namespace fl::storage
{

namespace
{
    constexpr char magic_0 = 'F', magic_1 = 'E', magic_2 = 'E', magic_3 = 'L';
    constexpr uint8_t format_version = 1;

    struct alignas(4) header
    {
        char magic[4];
        uint8_t version;
        uint8_t rec_size;
        uint16_t count;          // valid records in the ring
        uint16_t next;           // next slot to write [0, capacity)
        uint16_t reserved0;
        uint32_t write_seq;      // bumped on every append; picks the newest header copy
        uint32_t total_written;
        uint32_t last_datetime;
        uint32_t reserved1;
        uint32_t crc;            // crc32 of the previous 28 bytes
    };

    static_assert(sizeof(header) == header_bytes);

    header current;
    bool formatted = false;

    [[nodiscard]] uint32_t crc32(const uint8_t* data, int size)
    {
        uint32_t crc = 0xFFFFFFFF;

        for(int i = 0; i < size; ++i)
        {
            crc ^= data[i];

            for(int bit = 0; bit < 8; ++bit)
            {
                crc = (crc >> 1) ^ (0xEDB88320 & (0 - (crc & 1)));
            }
        }

        return crc ^ 0xFFFFFFFF;
    }

    [[nodiscard]] uint32_t header_crc(const header& h)
    {
        return crc32(reinterpret_cast<const uint8_t*>(&h), header_bytes - 4);
    }

    [[nodiscard]] bool header_valid(const header& h)
    {
        return h.magic[0] == magic_0 && h.magic[1] == magic_1 && h.magic[2] == magic_2 &&
                h.magic[3] == magic_3 && h.version == format_version &&
                h.rec_size == uint8_t(sizeof(check_in)) && h.count <= capacity &&
                h.next < capacity && h.crc == header_crc(h);
    }

    void store_header()
    {
        current.crc = header_crc(current);

        // Alternate the destination copy so a power loss mid-write leaves
        // the other copy intact.
        int offset = (current.write_seq & 1) ? header_bytes : 0;
        bn::sram::write_offset(current, offset);
    }
}

void init()
{
    formatted = false;

    header a;
    header b;
    bn::sram::read_offset(a, 0);
    bn::sram::read_offset(b, header_bytes);

    bool a_valid = header_valid(a);
    bool b_valid = header_valid(b);

    if(a_valid && b_valid)
    {
        current = a.write_seq >= b.write_seq ? a : b;
    }
    else if(a_valid)
    {
        current = a;
    }
    else if(b_valid)
    {
        current = b;
    }
    else
    {
        current = header{};
        current.magic[0] = magic_0;
        current.magic[1] = magic_1;
        current.magic[2] = magic_2;
        current.magic[3] = magic_3;
        current.version = format_version;
        current.rec_size = uint8_t(sizeof(check_in));
        formatted = true;

        // Write both copies so the next boot finds a valid header either way.
        current.write_seq = 0;
        store_header();
        current.write_seq = 1;
        store_header();
    }
}

bool fresh_boot()
{
    return formatted;
}

int count()
{
    return current.count;
}

uint32_t total_written()
{
    return current.total_written;
}

bool wrapped()
{
    return current.total_written > uint32_t(capacity);
}

check_in get(int age)
{
    int index = int(current.next) - 1 - age;

    while(index < 0)
    {
        index += capacity;
    }

    check_in result;
    bn::sram::read_offset(result, log_offset + index * int(sizeof(check_in)));
    return result;
}

void append(const check_in& record)
{
    bn::sram::write_offset(record, log_offset + int(current.next) * int(sizeof(check_in)));

    current.next = uint16_t((current.next + 1) % capacity);

    if(current.count < capacity)
    {
        ++current.count;
    }

    ++current.write_seq;
    ++current.total_written;

    if(record.datetime)
    {
        current.last_datetime = record.datetime;
    }

    store_header();
}

}
