# Feelo save data format (version 1)

Feelo stores all check-ins in the cartridge's 32 KB SRAM. The same bytes
appear verbatim in emulator save files (`feelo.sav` written by mGBA) and in
the `.sav` an EZ-Flash Omega DE keeps on its microSD card, so any tool that
reads this format can analyze the data off-device. `tools/parse_save.py` is
the reference reader.

All multi-byte values are **little-endian** (native GBA byte order).

## Layout

| Offset | Size | Contents |
|-------:|-----:|----------|
| 0      | 32   | Header copy A |
| 32     | 32   | Header copy B |
| 64     | 8 × 4088 | Check-in records (ring buffer) |

Capacity: `(32768 - 64) / 8 = 4088` records. At one check-in per day that is
more than 11 years; at three per day, ~3.7 years before the ring wraps and
the oldest records are overwritten.

## Header (32 bytes)

| Offset | Type | Field | Meaning |
|-------:|------|-------|---------|
| 0  | char[4] | `magic` | `"FEEL"` |
| 4  | u8  | `version` | format version, currently `1` |
| 5  | u8  | `rec_size` | record size in bytes, currently `8` |
| 6  | u16 | `count` | valid records in the ring (≤ 4088) |
| 8  | u16 | `next` | ring index of the next slot to write |
| 10 | u16 | — | reserved (0) |
| 12 | u32 | `write_seq` | bumped on every append; selects the newest copy |
| 16 | u32 | `total_written` | records ever written (does not wrap) |
| 20 | u32 | `last_datetime` | packed datetime of the newest dated record |
| 24 | u32 | — | reserved (0) |
| 28 | u32 | `crc` | CRC-32 (zlib polynomial) of bytes 0–27 |

### Double buffering

Every append writes the record first, then one header copy — alternating
A/B by `write_seq` parity. A power loss mid-write can therefore corrupt at
most one copy, and recovery falls back to the other copy, losing **at most
the newest record**. A reader must:

1. Validate both copies (magic, version, rec_size, `count`/`next` ranges, CRC).
2. Use the valid copy with the highest `write_seq`.
3. If neither is valid, treat the save as empty.

### Ring order

Records live at `64 + index * 8`. The newest record is at index
`(next - 1) mod 4088`; the oldest is `(next - count) mod 4088`. Iterating
`i = 0 .. count-1` over `(next - count + i) mod 4088` yields records
oldest → newest.

## Check-in record (8 bytes)

| Offset | Type | Field | Meaning |
|-------:|------|-------|---------|
| 0 | u32 | `datetime` | packed local time (below); `0` = RTC unavailable |
| 4 | i8  | `valence` | −100 (awful) … +100 (great) |
| 5 | i8  | `energy` | −100 (drained) … +100 (wired) |
| 6 | u8  | `focus` | 0 (lost) … 200 (locked in); `0xFF` = question skipped |
| 7 | u8  | `flags` | bit 0: focus present · bit 1: RTC was valid |

### Packed datetime (u32)

| Bits | Field | Range |
|------|-------|-------|
| 29–31 | — | reserved (0) |
| 26–28 | week day + 1 | 1 = Sunday … 7 = Saturday; 0 = unknown |
| 20–25 | year − 2000 | 0–63 (2000–2063) |
| 16–19 | month | 1–12 |
| 11–15 | day of month | 1–31 |
| 6–10  | hour | 0–23 |
| 0–5   | minute | 0–59 |

The week day is computed from the civil date (not read from the cartridge
RTC, whose week-day register is application-defined).

### Mood zones

The UI and the tools derive a 3×3 "mood zone" from valence/energy with
thresholds at ±33: zone = `row * 3 + col`, where `col` = 0/1/2 for
valence < −33 / −33…33 / > 33 and `row` = 0/1/2 for energy > 33 / −33…33 /
< −33. Zone names, row-major:

```
STRESSED  WIRED   PUMPED
DOWN      OKAY    HAPPY
DRAINED   SLEEPY  COZY
```

## Compatibility rules

- Readers must ignore records beyond `count` and tolerate arbitrary bytes in
  unused areas (a fresh cart reads `0xFF` everywhere).
- Any layout change bumps `version`; readers must refuse unknown versions.
- `rec_size` exists so future versions can grow the record without moving
  the log offset.
