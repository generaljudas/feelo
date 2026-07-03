#!/usr/bin/env python3
"""Parse a Feelo SRAM save (.sav) into CSV and a summary report.

Works on raw 32KB SRAM dumps: the .sav mGBA writes next to the ROM, or the
.sav an EZ-Flash Omega DE stores on its microSD card.

Usage:
    python3 tools/parse_save.py feelo.sav              # summary
    python3 tools/parse_save.py feelo.sav --csv out.csv

Binary format spec: docs/DATA_FORMAT.md (stdlib only, no dependencies).
"""

import argparse
import csv
import struct
import sys
import zlib

HEADER_BYTES = 32
LOG_OFFSET = HEADER_BYTES * 2
RECORD_SIZE = 8
CAPACITY = (32768 - LOG_OFFSET) // RECORD_SIZE

FOCUS_SKIPPED = 0xFF
FLAG_FOCUS = 0x01
FLAG_RTC = 0x02

WEEK_DAYS = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
MOOD_WORDS = ['STRESSED', 'WIRED', 'PUMPED',
              'DOWN', 'OKAY', 'HAPPY',
              'DRAINED', 'SLEEPY', 'COZY']
FOCUS_WORDS = ['LOST', 'SCATTERED', 'SO-SO', 'STEADY', 'LOCKED IN']  # by value/50
BUCKETS = ['00-04h', '04-08h', '08-12h', '12-16h', '16-20h', '20-24h']


def parse_header(data, offset):
    (magic, version, rec_size, count, nxt, _res0, write_seq, total_written,
     last_dt, _res1, crc) = struct.unpack_from('<4sBBHHHIIIII', data, offset)
    if magic != b'FEEL' or version != 1 or rec_size != RECORD_SIZE:
        return None
    if count > CAPACITY or nxt >= CAPACITY:
        return None
    if crc != zlib.crc32(data[offset:offset + HEADER_BYTES - 4]):
        return None
    return {'count': count, 'next': nxt, 'write_seq': write_seq,
            'total_written': total_written, 'last_datetime': last_dt}


def unpack_datetime(dt):
    if not dt:
        return None
    return {
        'week_day': ((dt >> 26) & 0x7) - 1,
        'year': ((dt >> 20) & 0x3F) + 2000,
        'month': (dt >> 16) & 0xF,
        'day': (dt >> 11) & 0x1F,
        'hour': (dt >> 6) & 0x1F,
        'minute': dt & 0x3F,
    }


def iso(ts):
    if not ts:
        return ''
    return (f"{ts['year']:04d}-{ts['month']:02d}-{ts['day']:02d} "
            f"{ts['hour']:02d}:{ts['minute']:02d}")


def mood_zone(valence, energy):
    col = 0 if valence < -33 else (2 if valence > 33 else 1)
    row = 0 if energy > 33 else (2 if energy < -33 else 1)
    return row * 3 + col


def load(path):
    with open(path, 'rb') as f:
        data = f.read()
    if len(data) < 32768:
        sys.exit(f'error: {path} is {len(data)} bytes; expected a >=32KB SRAM dump')
    data = data[:32768]

    header_a = parse_header(data, 0)
    header_b = parse_header(data, HEADER_BYTES)
    headers = [h for h in (header_a, header_b) if h]
    if not headers:
        sys.exit('error: no valid Feelo header found (is this a Feelo .sav?)')
    header = max(headers, key=lambda h: h['write_seq'])

    records = []
    count, nxt = header['count'], header['next']
    for i in range(count):
        index = (nxt - count + i) % CAPACITY          # oldest -> newest
        offset = LOG_OFFSET + index * RECORD_SIZE
        dt, valence, energy, focus, flags = struct.unpack_from('<IbbBB', data, offset)
        records.append({
            'datetime': iso(unpack_datetime(dt)),
            'week_day': WEEK_DAYS[((dt >> 26) & 0x7) - 1] if dt and (dt >> 26) & 0x7 else '',
            'valence': valence,
            'energy': energy,
            'focus': '' if focus == FOCUS_SKIPPED else focus,
            'mood': MOOD_WORDS[mood_zone(valence, energy)],
            'rtc_valid': bool(flags & FLAG_RTC),
            'raw_datetime': dt,
            'flags': flags,
        })
    return header, records


def summarize(header, records):
    print(f"records in log:   {header['count']}")
    print(f"total ever:       {header['total_written']}"
          + ('  (ring wrapped, oldest lost)' if header['total_written'] > CAPACITY else ''))
    if not records:
        return

    dated = [r for r in records if r['datetime']]
    if dated:
        print(f"first check-in:   {dated[0]['datetime']}")
        print(f"last check-in:    {dated[-1]['datetime']}")

    n = len(records)
    avg_v = sum(r['valence'] for r in records) / n
    avg_e = sum(r['energy'] for r in records) / n
    print(f"avg valence:      {avg_v:+.1f}")
    print(f"avg energy:       {avg_e:+.1f}")
    focused = [r['focus'] for r in records if r['focus'] != '']
    if focused:
        avg_f = sum(focused) / len(focused)
        print(f"avg focus:        {avg_f:.0f}/200 ({FOCUS_WORDS[min(4, int(avg_f + 25) // 50)]},"
              f" n={len(focused)})")

    zones = {}
    for r in records:
        zones[r['mood']] = zones.get(r['mood'], 0) + 1
    top = sorted(zones.items(), key=lambda kv: -kv[1])
    print('moods:            ' + ', '.join(f'{m} x{c}' for m, c in top))

    by_bucket = {}
    for r in dated:
        hour = int(r['datetime'][11:13])
        by_bucket.setdefault(hour // 4, []).append(r['valence'])
    if by_bucket:
        print('valence by time of day:')
        for bucket in sorted(by_bucket):
            vals = by_bucket[bucket]
            print(f'  {BUCKETS[bucket]}  {sum(vals) / len(vals):+6.1f}  (n={len(vals)})')

    by_dow = {}
    for r in dated:
        if r['week_day']:
            by_dow.setdefault(r['week_day'], []).append(r['valence'])
    if by_dow:
        print('valence by weekday:')
        for day in WEEK_DAYS:
            if day in by_dow:
                vals = by_dow[day]
                print(f'  {day}  {sum(vals) / len(vals):+6.1f}  (n={len(vals)})')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('sav', help='path to the .sav file (raw SRAM dump)')
    parser.add_argument('--csv', metavar='PATH', help='also export records as CSV')
    args = parser.parse_args()

    header, records = load(args.sav)
    summarize(header, records)

    if args.csv:
        fields = ['datetime', 'week_day', 'valence', 'energy', 'focus', 'mood',
                  'rtc_valid', 'raw_datetime', 'flags']
        with open(args.csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(records)
        print(f'\nwrote {len(records)} records to {args.csv}')


if __name__ == '__main__':
    main()
