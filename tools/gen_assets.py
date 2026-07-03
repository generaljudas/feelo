#!/usr/bin/env python3
"""Generate all Feelo pixel-art assets (BMP + JSON) and SFX (WAV).

Butano's importer requires: uncompressed BMP, 40-byte BITMAPINFOHEADER,
8bpp indexed, first palette color = transparent, all pixel indices <= 15
(so the image is treated as a 16-color / 4bpp asset).
Pillow's P-mode BMP writer satisfies this; we assert it after writing.

The mascot is drawn scale-parametrically: the same code renders the 32x32
sheet (mood pad) and the 64x64 sheet (home / celebrate screens), with extra
detail — eye shine, ear interiors, deeper shading — at the high resolution.

Run from the repo root:  .venv/bin/python tools/gen_assets.py
Preview sheets land in build/asset_preview.png and build/bg_preview.png.
"""

import math
import os
import struct
import wave

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GFX = os.path.join(ROOT, 'graphics')
AUDIO = os.path.join(ROOT, 'audio')
PREVIEW_DIR = os.path.join(ROOT, 'build')

# ----------------------------------------------------------------------------
# Palettes (16 unique RGB entries each; index 0 is the transparent color).
# Sprites and backgrounds are separate BMPs, so they get separate palettes.
# ----------------------------------------------------------------------------
T = 0             # transparent (magenta, never drawn)

# --- sprite palette ---
OUT = 1           # outline: deep plum
BODY = 2          # mascot body: mint
SHADE = 3         # body shade
DEEP = 4          # body deep shade (bottom rim)
LIGHT = 5         # body highlight
WHITE = 6         # eye whites / shine / teeth
PUPIL = 7         # pupils / dark face lines
MOUTH = 8         # mouth interior
TONGUE = 9        # tongue / mouth accent
BLUSH = 10        # blush pink
TEAR = 11         # tear / sweat blue
SPARK = 12        # sparkle yellow
LAV = 13          # lavender (zzz, lost spiral)
EARIN = 14        # ear interior
AMBER = 15        # warm accent (focus icons)

SPRITE_PALETTE = [
    (255, 0, 255),    # 0 transparent
    (38, 30, 56),     # 1 outline
    (124, 224, 195),  # 2 body mint
    (86, 186, 158),   # 3 shade
    (58, 143, 124),   # 4 deep shade
    (182, 244, 222),  # 5 highlight
    (255, 255, 255),  # 6 white
    (32, 24, 48),     # 7 pupil
    (146, 62, 92),    # 8 mouth
    (231, 123, 157),  # 9 tongue
    (247, 154, 192),  # 10 blush
    (124, 196, 247),  # 11 tear/sweat
    (255, 217, 138),  # 12 sparkle
    (201, 184, 232),  # 13 lavender
    (100, 205, 172),  # 14 ear interior
    (247, 178, 106),  # 15 amber
]

# --- background palette ---
B_TOP = 1         # sky top (darkest)
B_MID = 2         # sky middle
B_LOW = 3         # sky near horizon (lightest)
B_DOT = 4         # dim star speck
B_STAR = 5        # star
B_BRIGHT = 6      # bright star / frame highlight
B_WARM = 7        # rare warm twinkle
B_HILL = 8        # hill silhouette
B_HILLRIM = 9     # hill rim light
B_FRAME = 10      # pad frame main
B_FRAMEGLOW = 11  # pad frame outer glow
B_AXIS = 12       # pad axis dots
B_MARK = 13       # pad center marker / corner accents
B_MOON = 14       # moon
B_MOONSH = 15     # moon shade

BG_PALETTE = [
    (255, 0, 255),    # 0 transparent
    (26, 20, 42),     # 1 sky top
    (36, 27, 51),     # 2 sky mid
    (46, 36, 66),     # 3 sky low
    (58, 45, 82),     # 4 dot
    (85, 68, 122),    # 5 star
    (143, 127, 192),  # 6 bright
    (255, 217, 138),  # 7 warm twinkle
    (20, 15, 33),     # 8 hill
    (66, 52, 96),     # 9 hill rim
    (150, 134, 199),  # 10 frame
    (79, 63, 118),    # 11 frame glow
    (94, 75, 143),    # 12 axis dots
    (201, 184, 232),  # 13 marker
    (242, 230, 201),  # 14 moon
    (217, 201, 168),  # 15 moon shade
]


def new_canvas(w, h, palette, fill=T):
    img = Image.new('P', (w, h), fill)
    flat = []
    for rgb in palette:
        flat.extend(rgb)
    flat.extend([0] * (768 - len(flat)))
    img.putpalette(flat)
    return img


def save_bmp(img, name):
    path = os.path.join(GFX, name + '.bmp')
    img.save(path, 'BMP')
    verify_bmp(path)
    return path


def verify_bmp(path):
    """Assert the invariants Butano's tools/bmp.py checks."""
    with open(path, 'rb') as f:
        data = f.read()
    pixels_offset = struct.unpack_from('I', data, 10)[0]
    header_size = struct.unpack_from('I', data, 14)[0]
    bpp = struct.unpack_from('H', data, 28)[0]
    compression = struct.unpack_from('I', data, 30)[0]
    assert header_size == 40, f'{path}: header {header_size} != 40'
    assert bpp == 8, f'{path}: bpp {bpp} != 8'
    assert compression == 0, f'{path}: compressed'
    max_index = max(data[pixels_offset:])
    assert max_index <= 15, f'{path}: pixel index {max_index} > 15'


def write_json(name, content):
    with open(os.path.join(GFX, name + '.json'), 'w') as f:
        f.write(content + '\n')


# ----------------------------------------------------------------------------
# Mascot: 11 frames (9 mood-zone expressions + 2 celebrate frames), drawn at
# scale s (1 -> 32x32, 2 -> 64x64). Frame index = row*3 + col; row 0 = high
# energy, col 0 = negative valence.
# ----------------------------------------------------------------------------
POSE_PERK, POSE_NORMAL, POSE_SQUASH = 1, 0, -1


def draw_body(d, s, pose, arms=None):
    """Round mint blob: feet, ears (and arms) peek from behind the body."""
    if pose == POSE_PERK:
        box, ear_y = (4, 6, 27, 28), 3
    elif pose == POSE_SQUASH:
        box, ear_y = (2, 11, 29, 28), 8
    else:
        box, ear_y = (3, 8, 28, 28), 5
    x0, y0, x1, y1 = [v * s for v in box]

    # feet nubs
    for fx in (9, 18):
        d.ellipse((fx * s, 26 * s, (fx + 5) * s, 30 * s - 1), fill=SHADE, outline=OUT)

    # ears
    for i, ex in enumerate((x0 + 4 * s, x1 - 8 * s)):
        d.ellipse((ex, ear_y * s, ex + 4 * s, (ear_y + 5) * s), fill=BODY, outline=OUT)
        if s > 1:
            d.ellipse((ex + s + 1, (ear_y + 1) * s + 1, ex + 3 * s - 1, (ear_y + 3) * s),
                      fill=EARIN)

    # celebrate arms, raised
    if arms == 'up':
        d.ellipse((0, (y0 // s + 4) * s, 4 * s, (y0 // s + 11) * s), fill=BODY, outline=OUT)
        d.ellipse((32 * s - 4 * s - 1, (y0 // s + 4) * s, 32 * s - 1, (y0 // s + 11) * s),
                  fill=BODY, outline=OUT)

    # body: deep rim -> shade -> core, one dark outline
    d.ellipse((x0, y0, x1, y1), fill=DEEP, outline=OUT)
    d.ellipse((x0 + s, y0 + s, x1 - s, y1 - 2 * s), fill=SHADE)
    d.ellipse((x0 + s, y0 + s, x1 - s, y1 - 4 * s), fill=BODY)

    # top-left highlight
    d.ellipse((x0 + 4 * s, y0 + 3 * s, x0 + 9 * s, y0 + 6 * s), fill=LIGHT)
    if s > 1:
        d.ellipse((x0 + 11 * s, y0 + 2 * s, x0 + 14 * s, y0 + 3 * s + 1), fill=LIGHT)


def face_y(pose):
    return {POSE_PERK: 16, POSE_NORMAL: 17, POSE_SQUASH: 19}[pose]


def draw_eye(d, s, cx, ey, style):
    cx *= s
    ey *= s
    if style == 'dot':
        d.ellipse((cx - s, ey - s, cx + s, ey + 2 * s - 1), fill=PUPIL)
        if s > 1:
            d.point((cx - 1, ey - 1), fill=WHITE)
    elif style == 'wide':
        d.ellipse((cx - 2 * s, ey - 2 * s, cx + 2 * s - 1, ey + 3 * s - 1), fill=WHITE)
        d.ellipse((cx - s, ey, cx + s - 1, ey + 2 * s - 1), fill=PUPIL)
        if s > 1:
            d.point((cx - s, ey + 1), fill=WHITE)
    elif style == 'happy':       # ^
        d.line((cx - 2 * s, ey + s, cx, ey - s), fill=PUPIL, width=s)
        d.line((cx, ey - s, cx + 2 * s, ey + s), fill=PUPIL, width=s)
    elif style == 'sadclosed':   # downcast closed lid (∩ curve)
        d.arc((cx - 2 * s, ey - s, cx + 2 * s, ey + 2 * s), 180, 360, fill=PUPIL, width=s)
    elif style == 'flat':        # sleepy = =
        d.line((cx - 2 * s, ey, cx + 2 * s, ey), fill=PUPIL, width=s)
        d.line((cx - 2 * s, ey + 2 * s, cx + 2 * s, ey + 2 * s), fill=PUPIL, width=s)
    elif style == 'sparkle':
        d.line((cx - 2 * s, ey, cx + 2 * s, ey), fill=SPARK, width=s)
        d.line((cx, ey - 2 * s, cx, ey + 2 * s), fill=SPARK, width=s)
        if s > 1:
            d.point((cx - s - 1, ey - s - 1), fill=SPARK)
            d.point((cx + s, ey - s - 1), fill=SPARK)
            d.point((cx - s - 1, ey + s), fill=SPARK)
            d.point((cx + s, ey + s), fill=SPARK)
        d.rectangle((cx - 1, ey - 1, cx, ey), fill=WHITE)
    elif style == 'droop':
        d.ellipse((cx - s, ey, cx + s - 1, ey + 2 * s - 1), fill=PUPIL)
        d.line((cx - 2 * s, ey - 2 * s, cx + 2 * s, ey - 2 * s), fill=PUPIL, width=s)
    elif style == 'uu':          # relaxed closed u u
        d.arc((cx - 2 * s, ey - 2 * s, cx + 2 * s, ey + s), 0, 180, fill=PUPIL, width=s)


def draw_brows(d, s, fy, style):
    # Sit well above the eyes (which span up to ey-2 = fy-3) so they never
    # merge into them and read as a second pair of eyes.
    y = (fy - 7) * s
    if style == 'angry':     # inner tips down
        d.line((10 * s, y, 13 * s, y + s), fill=PUPIL, width=s)
        d.line((19 * s, y + s, 22 * s, y), fill=PUPIL, width=s)
    elif style == 'worry':   # inner tips up
        d.line((10 * s, y + s, 13 * s, y), fill=PUPIL, width=s)
        d.line((19 * s, y, 22 * s, y + s), fill=PUPIL, width=s)


def draw_mouth(d, s, fy, style):
    mx, my = 16 * s, (fy + 5) * s
    if style == 'smile':
        d.arc((mx - 3 * s, my - 3 * s, mx + 3 * s, my + s), 20, 160, fill=PUPIL, width=s)
    elif style == 'open':
        d.pieslice((mx - 3 * s, my - 3 * s, mx + 3 * s, my + 2 * s), 0, 180, fill=MOUTH)
        d.arc((mx - 3 * s, my - 3 * s, mx + 3 * s, my + 2 * s), 0, 180, fill=PUPIL, width=s)
        if s > 1:
            d.pieslice((mx - s - 1, my, mx + s + 1, my + 2 * s + 1), 180, 360, fill=TONGUE)
    elif style == 'grin':
        d.pieslice((mx - 4 * s, my - 4 * s, mx + 4 * s, my + 2 * s), 0, 180, fill=MOUTH)
        d.arc((mx - 4 * s, my - 4 * s, mx + 4 * s, my + 2 * s), 0, 180, fill=PUPIL, width=s)
        d.line((mx - 2 * s, my - s, mx + 2 * s, my - s), fill=WHITE, width=s)
        if s > 1:
            d.pieslice((mx - 2 * s, my, mx + 2 * s, my + 2 * s + 2), 180, 360, fill=TONGUE)
    elif style == 'flat':
        d.line((mx - 2 * s, my, mx + 2 * s, my), fill=PUPIL, width=s)
    elif style == 'frown':
        d.arc((mx - 3 * s, my, mx + 3 * s, my + 4 * s), 200, 340, fill=PUPIL, width=s)
    elif style == 'wobble':
        for i, dy in enumerate((0, 1, 0, 1, 0, 1)):
            d.rectangle(((mx - 3 * s) + i * s, my + dy * s,
                         (mx - 3 * s) + (i + 1) * s - 1, my + (dy + 1) * s - 1), fill=PUPIL)
    elif style == 'o':
        d.ellipse((mx - s, my - s, mx + s, my + s), outline=PUPIL, width=s)


def draw_extra(d, s, fy, extra):
    if extra == 'blush':
        d.ellipse((6 * s, (fy + 2) * s, 9 * s, (fy + 3) * s), fill=BLUSH)
        d.ellipse((23 * s, (fy + 2) * s, 26 * s, (fy + 3) * s), fill=BLUSH)
    elif extra == 'sweat':
        d.point((26 * s, (fy - 7) * s), fill=TEAR)
        d.ellipse((25 * s, (fy - 6) * s, 26 * s + s - 1, (fy - 5) * s + s - 1), fill=TEAR)
    elif extra == 'tear':
        d.point((10 * s, (fy + 2) * s), fill=TEAR)
        d.ellipse((10 * s, (fy + 3) * s, 11 * s + s - 1, (fy + 4) * s + s - 1), fill=TEAR)
    elif extra == 'zzz':
        d.line((23 * s, 2 * s, 26 * s, 2 * s), fill=LAV, width=s)
        d.line((26 * s, 2 * s, 23 * s, 5 * s), fill=LAV, width=s)
        d.line((23 * s, 5 * s, 26 * s, 5 * s), fill=LAV, width=s)
        d.line((28 * s, 6 * s, 30 * s, 6 * s), fill=LAV)
        d.point((29 * s, 7 * s), fill=LAV)
        d.line((28 * s, 8 * s, 30 * s, 8 * s), fill=LAV)
    elif extra == 'spark':
        for sx, sy in ((5, 5), (27, 3)):
            d.line(((sx - 1) * s, sy * s, (sx + 1) * s, sy * s), fill=SPARK, width=s)
            d.line((sx * s, (sy - 1) * s, sx * s, (sy + 1) * s), fill=SPARK, width=s)


# (pose, eyes, brows, mouth, extras, arms) — index = row*3+col
EXPRESSIONS = [
    (POSE_PERK,   'wide',      'angry', 'wobble', ('sweat',), None),           # 0 STRESSED
    (POSE_PERK,   'wide',      None,    'o',      ('spark',), None),           # 1 WIRED
    (POSE_PERK,   'sparkle',   None,    'grin',   ('blush', 'spark'), None),   # 2 PUMPED
    (POSE_NORMAL, 'droop',     'worry', 'frown',  (), None),                   # 3 DOWN
    (POSE_NORMAL, 'dot',       None,    'flat',   (), None),                   # 4 OKAY
    (POSE_NORMAL, 'happy',     None,    'smile',  ('blush',), None),           # 5 HAPPY
    (POSE_SQUASH, 'sadclosed', 'worry', 'wobble', ('tear',), None),            # 6 DRAINED
    (POSE_SQUASH, 'flat',      None,    'o',      ('zzz',), None),             # 7 SLEEPY
    (POSE_SQUASH, 'uu',        None,    'smile',  ('blush',), None),           # 8 COZY
    (POSE_PERK,   'happy',     None,    'grin',   ('blush', 'spark'), 'up'),   # 9 YAY (up)
    (POSE_SQUASH, 'sparkle',   None,    'grin',   ('blush',), 'up'),           # 10 YAY (down)
]


def gen_mascot(s, name):
    size = 32 * s
    sheet = new_canvas(size, size * len(EXPRESSIONS), SPRITE_PALETTE)
    for i, (pose, eyes, brows, mouth, extras, arms) in enumerate(EXPRESSIONS):
        frame = new_canvas(size, size, SPRITE_PALETTE)
        d = ImageDraw.Draw(frame)
        draw_body(d, s, pose, arms)
        fy = face_y(pose)
        draw_eye(d, s, 11, fy - 1, eyes)
        draw_eye(d, s, 21, fy - 1, eyes)
        if brows:
            draw_brows(d, s, fy, brows)
        draw_mouth(d, s, fy, mouth)
        for extra in extras:
            draw_extra(d, s, fy, extra)
        sheet.paste(frame, (0, i * size))
    save_bmp(sheet, name)
    write_json(name, '{\n    "type": "sprite",\n    "height": %d\n}' % size)
    return sheet


# ----------------------------------------------------------------------------
# Cursor: 16x16, 2 frames — corner brackets + center dot, pulsing
# ----------------------------------------------------------------------------
def gen_cursor():
    sheet = new_canvas(16, 32, SPRITE_PALETTE)
    for i, r in enumerate((5, 7)):
        frame = new_canvas(16, 16, SPRITE_PALETTE)
        d = ImageDraw.Draw(frame)
        for sx in (-1, 1):
            for sy in (-1, 1):
                cx, cy = 8 + sx * r - (1 if sx > 0 else 0), 8 + sy * r - (1 if sy > 0 else 0)
                d.line((cx, cy, cx - sx * 2, cy), fill=WHITE)
                d.line((cx, cy, cx, cy - sy * 2), fill=WHITE)
        d.rectangle((7, 7, 8, 8), fill=SPARK)
        sheet.paste(frame, (0, i * 16))
    save_bmp(sheet, 'cursor')
    write_json('cursor', '{\n    "type": "sprite",\n    "height": 16\n}')
    return sheet


# ----------------------------------------------------------------------------
# Focus icons: 16x16, 5 frames (locked-in ... lost)
# ----------------------------------------------------------------------------
def gen_focus_icons():
    sheet = new_canvas(16, 80, SPRITE_PALETTE)
    for i in range(5):
        frame = new_canvas(16, 16, SPRITE_PALETTE)
        d = ImageDraw.Draw(frame)
        if i == 0:    # LOCKED IN: amber bullseye
            d.ellipse((1, 1, 14, 14), outline=AMBER)
            d.ellipse((4, 4, 11, 11), outline=WHITE)
            d.ellipse((6, 6, 9, 9), fill=AMBER, outline=SPARK)
        elif i == 1:  # STEADY: ring + dot
            d.ellipse((2, 2, 13, 13), outline=WHITE)
            d.ellipse((6, 6, 9, 9), fill=WHITE)
        elif i == 2:  # SO-SO: gentle wave
            for x in range(2, 14):
                y = 8 + round(1.5 * math.sin((x - 2) * math.pi / 5))
                d.point((x, y), fill=WHITE)
                d.point((x, y + 1), fill=LAV)
        elif i == 3:  # SCATTERED: dots drifting apart
            for x, y, c in ((4, 4, WHITE), (11, 3, LAV), (13, 9, WHITE),
                            (5, 11, LAV), (9, 7, WHITE), (2, 8, LAV)):
                d.rectangle((x, y, x + 1, y + 1), fill=c)
        else:         # LOST: spiral fading out
            cx, cy = 8, 8
            for t in range(34):
                ang = t * 0.42
                r = 1.2 + t * 0.16
                x = int(round(cx + r * math.cos(ang)))
                y = int(round(cy + r * math.sin(ang)))
                if 0 <= x < 16 and 0 <= y < 16:
                    d.point((x, y), fill=LAV if t < 22 else B_DOT and LAV)
            d.point((8, 8), fill=WHITE)
        sheet.paste(frame, (0, i * 16))
    save_bmp(sheet, 'focus_icons')
    write_json('focus_icons', '{\n    "type": "sprite",\n    "height": 16\n}')
    return sheet


# ----------------------------------------------------------------------------
# Sparkline dots: 8x8, 3 frames (positive point, baseline tick, negative point)
# ----------------------------------------------------------------------------
def gen_dot():
    sheet = new_canvas(8, 24, SPRITE_PALETTE)
    d = ImageDraw.Draw(sheet)
    d.rectangle((3, 3, 4, 4), fill=SPARK)        # frame 0: positive
    d.point((3, 8 + 3), fill=LAV)                # frame 1: baseline tick
    d.point((4, 8 + 3), fill=LAV)
    d.rectangle((3, 16 + 3, 4, 16 + 4), fill=TEAR)   # frame 2: negative
    save_bmp(sheet, 'dot')
    write_json('dot', '{\n    "type": "sprite",\n    "height": 8\n}')
    return sheet


# ----------------------------------------------------------------------------
# Backgrounds: 256x256. Dithered night-sky gradient; home gets a moon and
# rolling hills, the pad gets a polished frame. Visible area = rows 48..208.
# ----------------------------------------------------------------------------
def lcg_stream(seed):
    while True:
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        yield seed


def sky(d, rng):
    # three bands, checker-dithered over 10-row transitions
    band_mid_start, band_low_start = 110, 170

    def band_color(y, x):
        for start, a, b in ((band_low_start, B_MID, B_LOW), (band_mid_start, B_TOP, B_MID)):
            if y >= start + 10:
                continue
            if y >= start:
                return b if (x + y) % 2 == 0 and (y - start) > 5 - next(rng) % 3 else \
                    (a if (x + y) % 2 else (b if (y - start) > 4 else a))
        if y >= band_low_start:
            return B_LOW
        if y >= band_mid_start:
            return B_MID
        return B_TOP

    for y in range(256):
        if y < band_mid_start:
            d.line((0, y, 255, y), fill=B_TOP)
        elif y < band_mid_start + 10:
            for x in range(256):
                t = (y - band_mid_start) / 10
                d.point((x, y), fill=B_MID if ((x + y) % 2 == 0) == (t > 0.5) or t > 0.75
                        else B_TOP)
        elif y < band_low_start:
            d.line((0, y, 255, y), fill=B_MID)
        elif y < band_low_start + 10:
            for x in range(256):
                t = (y - band_low_start) / 10
                d.point((x, y), fill=B_LOW if ((x + y) % 2 == 0) == (t > 0.5) or t > 0.75
                        else B_MID)
        else:
            d.line((0, y, 255, y), fill=B_LOW)


def stars(d, rng, count=240, y_max=250):
    for _ in range(count):
        x = next(rng) % 256
        y = next(rng) % y_max
        kind = next(rng) % 12
        if kind < 7:
            d.point((x, y), fill=B_DOT)
        elif kind < 10:
            d.point((x, y), fill=B_STAR)
        elif kind < 11:
            d.point((x, y), fill=B_BRIGHT)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                d.point(((x + dx) % 256, (y + dy) % 256), fill=B_STAR)
        else:
            d.point((x, y), fill=B_WARM)


def moon(d, cx=196, cy=78, r=11):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=B_MOON)
    # crescent: bite out with sky color; rim shade along the inner curve
    d.ellipse((cx - r + 7, cy - r - 3, cx + r + 7, cy + r - 3), fill=B_TOP)
    d.arc((cx - r, cy - r, cx + r, cy + r), 60, 250, fill=B_MOONSH)


def hills(d, rng):
    for x in range(256):
        y1 = 206 - round(7 * math.sin((x + 30) * math.pi / 128))
        y2 = 214 - round(9 * math.sin((x + 150) * math.pi / 96))
        top = min(y1, y2)
        d.line((x, top, x, 255), fill=B_HILL)
        d.point((x, top), fill=B_HILLRIM)
        if next(rng) % 37 == 0 and top < 253:
            d.point((x, top + 2 + next(rng) % 3), fill=B_HILLRIM)


def gen_bg_soft():
    img = new_canvas(256, 256, BG_PALETTE, B_TOP)
    d = ImageDraw.Draw(img)
    rng = lcg_stream(0x1234ABCD)
    sky(d, rng)
    stars(d, rng, count=250, y_max=200)
    moon(d)
    hills(d, rng)
    save_bmp(img, 'bg_soft')
    write_json('bg_soft', '{\n    "type": "regular_bg"\n}')
    return img


def gen_bg_pad():
    img = new_canvas(256, 256, BG_PALETTE, B_TOP)
    d = ImageDraw.Draw(img)
    rng = lcg_stream(0xBADC0FFE)
    sky(d, rng)
    stars(d, rng, count=230, y_max=250)

    # pad frame: 136 half-width play area centered at (128,128)
    x0, y0, x1, y1 = 128 - 68, 128 - 68, 128 + 68, 128 + 68
    d.rounded_rectangle((x0 - 2, y0 - 2, x1 + 2, y1 + 2), radius=10, outline=B_FRAMEGLOW)
    d.rounded_rectangle((x0, y0, x1, y1), radius=8, outline=B_FRAME)

    # corner accents
    for sx in (0, 1):
        for sy in (0, 1):
            cx = (x0 + 4) if sx == 0 else (x1 - 4)
            cy = (y0 + 4) if sy == 0 else (y1 - 4)
            dx = 1 if sx == 0 else -1
            dy = 1 if sy == 0 else -1
            d.line((cx, cy, cx + 3 * dx, cy), fill=B_MARK)
            d.line((cx, cy, cx, cy + 3 * dy), fill=B_MARK)

    # dotted axes + center marker
    for t in range(x0 + 6, x1 - 5, 4):
        d.point((t, 128), fill=B_AXIS)
        d.point((128, t), fill=B_AXIS)
    d.rectangle((126, 126, 129, 129), outline=B_MARK)

    # axis end chevrons (up/down/left/right hints)
    for ex, ey, dx, dy in ((128, y0 - 6, 0, -1), (128, y1 + 6, 0, 1),
                           (x0 - 6, 128, -1, 0), (x1 + 6, 128, 1, 0)):
        d.line((ex - 2 * abs(dy), ey - 2 * abs(dx), ex + dx * 2, ey + dy * 2), fill=B_BRIGHT)
        d.line((ex + 2 * abs(dy), ey + 2 * abs(dx), ex + dx * 2, ey + dy * 2), fill=B_BRIGHT)
    save_bmp(img, 'bg_pad')
    write_json('bg_pad', '{\n    "type": "regular_bg"\n}')
    return img


# ----------------------------------------------------------------------------
# SFX: tiny 8-bit 22050 Hz mono square-wave chirps
# ----------------------------------------------------------------------------
def write_wav(name, samples):
    path = os.path.join(AUDIO, name + '.wav')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(22050)
        w.writeframes(bytes(samples))


def square_note(freq, ms, volume=52):
    n = int(22050 * ms / 1000)
    period = 22050 / freq
    out = []
    for i in range(n):
        env = 1.0 - i / n
        v = int(volume * env)
        phase = (i % period) / period
        out.append(128 + v if phase < 0.5 else 128 - v)
    return out


def gen_audio():
    write_wav('sfx_blip', square_note(1046, 70))
    tada = []
    for f in (523, 659, 784):
        tada += square_note(f, 95)
    tada += square_note(1046, 220, volume=58)
    write_wav('sfx_tada', tada)


# ----------------------------------------------------------------------------
# Preview sheets (PNG, upscaled) for human inspection
# ----------------------------------------------------------------------------
def preview(sheets, path, scale=4):
    cols = sum(s.width for s in sheets) + 8 * (len(sheets) + 1)
    rows = max(s.height for s in sheets) + 16
    canvas = Image.new('RGB', (cols, rows), (24, 18, 34))
    x = 8
    for s in sheets:
        canvas.paste(s.convert('RGB'), (x, 8))
        x += s.width + 8
    canvas = canvas.resize((canvas.width * scale, canvas.height * scale), Image.NEAREST)
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    canvas.save(path)
    print('preview:', path)


def main():
    os.makedirs(GFX, exist_ok=True)
    os.makedirs(AUDIO, exist_ok=True)
    small = gen_mascot(1, 'mascot')
    big = gen_mascot(2, 'mascot_big')
    sheets = [big, small, gen_cursor(), gen_focus_icons(), gen_dot()]
    bgs = [gen_bg_soft(), gen_bg_pad()]
    gen_audio()
    preview(sheets, os.path.join(PREVIEW_DIR, 'asset_preview.png'), scale=4)

    # bg preview: the visible 240x160 screen area of each bg
    scale = 2
    canvas = Image.new('RGB', ((240 + 8) * 2 + 8, 160 + 16), (0, 0, 0))
    for i, bg in enumerate(bgs):
        crop = bg.convert('RGB').crop((8, 48, 248, 208))
        canvas.paste(crop, (8 + i * 248, 8))
    canvas = canvas.resize((canvas.width * scale, canvas.height * scale), Image.NEAREST)
    canvas.save(os.path.join(PREVIEW_DIR, 'bg_preview.png'))
    print('done')


if __name__ == '__main__':
    main()
