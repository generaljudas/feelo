#!/usr/bin/env python3
"""Generate all Feelo pixel-art assets (BMP + JSON) and SFX (WAV).

Butano's importer requires: uncompressed BMP, 40-byte BITMAPINFOHEADER,
8bpp indexed, first palette color = transparent, all pixel indices <= 15
(so the image is treated as a 16-color / 4bpp asset).
Pillow's P-mode BMP writer satisfies this; we assert it after writing.

Run from the repo root:  .venv/bin/python tools/gen_assets.py
Also writes an upscaled preview sheet to build/asset_preview.png.
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
# Palette (16 unique RGB entries; index 0 is the transparent color)
# ----------------------------------------------------------------------------
T = 0            # transparent (magenta, never drawn)
OUT = 1          # outline: deep plum
BODY = 2         # mascot body: mint
SHADE = 3        # body shade
LIGHT = 4        # body highlight
WHITE = 5        # eye whites / shine
PUPIL = 6        # pupils / dark face lines
MOUTH = 7        # mouth interior
BLUSH = 8        # blush pink
TEAR = 9         # tear / sweat blue
SPARK = 10       # sparkle yellow
LAV = 11         # lavender (zzz, pad frame)
BASE = 12        # background base plum
DOT = 13         # background dim dots
STAR = 14        # background stars
ACCENT = 15      # background bright accents

PALETTE = [
    (255, 0, 255),    # 0 transparent
    (43, 32, 54),     # 1 outline
    (124, 224, 195),  # 2 body mint
    (79, 179, 154),   # 3 shade
    (178, 242, 222),  # 4 highlight
    (255, 255, 255),  # 5 white
    (32, 24, 48),     # 6 pupil
    (180, 80, 106),   # 7 mouth
    (247, 154, 192),  # 8 blush
    (124, 196, 247),  # 9 tear/sweat
    (255, 217, 138),  # 10 sparkle
    (201, 184, 232),  # 11 lavender
    (36, 27, 51),     # 12 bg base
    (58, 45, 82),     # 13 bg dots
    (85, 68, 122),    # 14 bg stars
    (143, 127, 192),  # 15 bg accent
]


def new_canvas(w, h, fill=T):
    img = Image.new('P', (w, h), fill)
    flat = []
    for rgb in PALETTE:
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
# Mascot: 32x32, 11 frames (9 mood-zone expressions + 2 celebrate frames).
# Frame index = row*3 + col; row 0 = high energy, col 0 = negative valence.
# ----------------------------------------------------------------------------
POSE_PERK, POSE_NORMAL, POSE_SQUASH = 1, 0, -1


def draw_body(d, pose):
    """Round mint blob with ear nubs; posture varies with energy."""
    if pose == POSE_PERK:
        box, ear_y = (4, 6, 27, 29), 3
    elif pose == POSE_SQUASH:
        box, ear_y = (2, 11, 29, 29), 8
    else:
        box, ear_y = (3, 8, 28, 29), 5
    x0, y0, x1, y1 = box
    # ear nubs peeking from behind the body
    for ex in (x0 + 4, x1 - 8):
        d.ellipse((ex, ear_y, ex + 4, ear_y + 5), fill=BODY, outline=OUT)
    # body: shade crescent under a mint core, single dark outline
    d.ellipse(box, fill=SHADE, outline=OUT)
    d.ellipse((x0 + 1, y0 + 1, x1 - 1, y1 - 3), fill=BODY)
    # top-left highlight
    d.ellipse((x0 + 4, y0 + 3, x0 + 8, y0 + 6), fill=LIGHT)


def face_y(pose):
    return {POSE_PERK: 16, POSE_NORMAL: 17, POSE_SQUASH: 19}[pose]


def draw_eye(d, cx, ey, style):
    if style == 'dot':
        d.rectangle((cx - 1, ey - 1, cx, ey + 1), fill=PUPIL)
    elif style == 'wide':
        d.ellipse((cx - 2, ey - 2, cx + 1, ey + 2), fill=WHITE)
        d.rectangle((cx - 1, ey, cx, ey + 1), fill=PUPIL)
    elif style == 'happy':   # ^ shaped
        d.line((cx - 2, ey + 1, cx, ey - 1), fill=PUPIL)
        d.line((cx, ey - 1, cx + 2, ey + 1), fill=PUPIL)
    elif style == 'sadclosed':   # v shaped (downcast closed lid)
        d.line((cx - 2, ey - 1, cx, ey + 1), fill=PUPIL)
        d.line((cx, ey + 1, cx + 2, ey - 1), fill=PUPIL)
    elif style == 'flat':    # sleepy = =
        d.line((cx - 2, ey, cx + 2, ey), fill=PUPIL)
        d.line((cx - 2, ey + 2, cx + 2, ey + 2), fill=PUPIL)
    elif style == 'sparkle':
        d.line((cx - 2, ey, cx + 2, ey), fill=SPARK)
        d.line((cx, ey - 2, cx, ey + 2), fill=SPARK)
        d.point((cx, ey), fill=WHITE)
    elif style == 'droop':
        d.rectangle((cx - 1, ey, cx, ey + 1), fill=PUPIL)
        d.line((cx - 2, ey - 2, cx + 2, ey - 2), fill=PUPIL)
    elif style == 'uu':      # relaxed closed u u
        d.line((cx - 2, ey - 1, cx - 2, ey), fill=PUPIL)
        d.line((cx + 2, ey - 1, cx + 2, ey), fill=PUPIL)
        d.line((cx - 1, ey + 1, cx + 1, ey + 1), fill=PUPIL)


def draw_brows(d, fy, style):
    ley, rey = fy - 5, fy - 5
    if style == 'angry':     # inner tips down
        d.line((9, ley, 13, ley + 2), fill=PUPIL)
        d.line((19, rey + 2, 23, rey), fill=PUPIL)
    elif style == 'worry':   # inner tips up
        d.line((9, ley + 2, 13, ley), fill=PUPIL)
        d.line((19, rey, 23, rey + 2), fill=PUPIL)


def draw_mouth(d, fy, style):
    mx, my = 16, fy + 5
    if style == 'smile':
        d.arc((mx - 3, my - 3, mx + 3, my + 1), 20, 160, fill=PUPIL)
    elif style == 'open':
        d.pieslice((mx - 3, my - 3, mx + 3, my + 2), 0, 180, fill=MOUTH)
        d.arc((mx - 3, my - 3, mx + 3, my + 2), 0, 180, fill=PUPIL)
    elif style == 'grin':
        d.pieslice((mx - 4, my - 4, mx + 4, my + 2), 0, 180, fill=MOUTH)
        d.arc((mx - 4, my - 4, mx + 4, my + 2), 0, 180, fill=PUPIL)
        d.line((mx - 2, my - 1, mx + 2, my - 1), fill=WHITE)
    elif style == 'flat':
        d.line((mx - 2, my, mx + 2, my), fill=PUPIL)
    elif style == 'frown':
        d.arc((mx - 3, my, mx + 3, my + 4), 200, 340, fill=PUPIL)
    elif style == 'wobble':
        for i, dy in enumerate((0, 1, 0, 1, 0, 1)):
            d.point((mx - 3 + i, my + dy), fill=PUPIL)
    elif style == 'o':
        d.ellipse((mx - 1, my - 1, mx + 1, my + 1), outline=PUPIL)


def draw_extra(d, fy, extra):
    if extra == 'blush':
        d.rectangle((7, fy + 2, 8, fy + 2), fill=BLUSH)
        d.rectangle((23, fy + 2, 24, fy + 2), fill=BLUSH)
    elif extra == 'sweat':
        d.point((26, fy - 7), fill=TEAR)
        d.rectangle((25, fy - 6, 26, fy - 5), fill=TEAR)
    elif extra == 'tear':
        d.point((10, fy + 2), fill=TEAR)
        d.rectangle((10, fy + 3, 11, fy + 4), fill=TEAR)
    elif extra == 'zzz':
        # big Z
        d.line((23, 2, 26, 2), fill=LAV)
        d.line((26, 2, 23, 5), fill=LAV)
        d.line((23, 5, 26, 5), fill=LAV)
        # small z
        d.line((28, 6, 30, 6), fill=LAV)
        d.point((29, 7), fill=LAV)
        d.line((28, 8, 30, 8), fill=LAV)
    elif extra == 'spark':
        for sx, sy in ((5, 5), (27, 3)):
            d.line((sx - 1, sy, sx + 1, sy), fill=SPARK)
            d.line((sx, sy - 1, sx, sy + 1), fill=SPARK)


# (pose, eyes, brows, mouth, extras) — index = row*3+col
EXPRESSIONS = [
    (POSE_PERK,   'wide',      'angry', 'wobble', ('sweat',)),          # 0 STRESSED
    (POSE_PERK,   'wide',      None,    'o',      ('spark',)),          # 1 WIRED
    (POSE_PERK,   'sparkle',   None,    'grin',   ('blush', 'spark')),  # 2 PUMPED
    (POSE_NORMAL, 'droop',     'worry', 'frown',  ()),                  # 3 DOWN
    (POSE_NORMAL, 'dot',       None,    'flat',   ()),                  # 4 OKAY
    (POSE_NORMAL, 'happy',     None,    'smile',  ('blush',)),          # 5 HAPPY
    (POSE_SQUASH, 'sadclosed', 'worry', 'wobble', ('tear',)),           # 6 DRAINED
    (POSE_SQUASH, 'flat',      None,    'o',      ('zzz',)),            # 7 SLEEPY
    (POSE_SQUASH, 'uu',        None,    'smile',  ('blush',)),          # 8 COZY
    (POSE_PERK,   'happy',     None,    'grin',   ('blush', 'spark')),  # 9 YAY (up)
    (POSE_SQUASH, 'sparkle',   None,    'grin',   ('blush',)),          # 10 YAY (down)
]


def gen_mascot():
    frames = len(EXPRESSIONS)
    sheet = new_canvas(32, 32 * frames)
    for i, (pose, eyes, brows, mouth, extras) in enumerate(EXPRESSIONS):
        frame = new_canvas(32, 32)
        d = ImageDraw.Draw(frame)
        draw_body(d, pose)
        fy = face_y(pose)
        draw_eye(d, 11, fy - 1, eyes)
        draw_eye(d, 21, fy - 1, eyes)
        if brows:
            draw_brows(d, fy, brows)
        draw_mouth(d, fy, mouth)
        for extra in extras:
            draw_extra(d, fy, extra)
        sheet.paste(frame, (0, i * 32))
    save_bmp(sheet, 'mascot')
    write_json('mascot', '{\n    "type": "sprite",\n    "height": 32\n}')
    return sheet


# ----------------------------------------------------------------------------
# Cursor ring: 16x16, 2 frames (pulse)
# ----------------------------------------------------------------------------
def gen_cursor():
    sheet = new_canvas(16, 32)
    for i, r in enumerate((5, 6)):
        frame = new_canvas(16, 16)
        d = ImageDraw.Draw(frame)
        d.ellipse((8 - r, 8 - r, 7 + r, 7 + r), outline=WHITE)
        t = r + 2
        for dx, dy in ((t, 0), (-t, 0), (0, t), (0, -t)):
            d.point((8 + dx - (1 if dx > 0 else 0), 8 + dy - (1 if dy > 0 else 0)),
                    fill=SPARK)
        sheet.paste(frame, (0, i * 16))
    save_bmp(sheet, 'cursor')
    write_json('cursor', '{\n    "type": "sprite",\n    "height": 16\n}')
    return sheet


# ----------------------------------------------------------------------------
# Focus icons: 16x16, 5 frames (locked-in ... lost)
# ----------------------------------------------------------------------------
def gen_focus_icons():
    sheet = new_canvas(16, 80)
    for i in range(5):
        frame = new_canvas(16, 16)
        d = ImageDraw.Draw(frame)
        if i == 0:    # LOCKED IN: bullseye
            d.ellipse((2, 2, 13, 13), outline=SPARK)
            d.ellipse((5, 5, 10, 10), outline=WHITE)
            d.rectangle((7, 7, 8, 8), fill=SPARK)
        elif i == 1:  # STEADY: ring + dot
            d.ellipse((3, 3, 12, 12), outline=WHITE)
            d.rectangle((7, 7, 8, 8), fill=WHITE)
        elif i == 2:  # SO-SO: wavy line
            for x in range(3, 13):
                y = 8 + (1 if (x // 2) % 2 else -1)
                d.point((x, y), fill=WHITE)
        elif i == 3:  # SCATTERED: stray dots
            for x, y in ((4, 4), (11, 3), (13, 9), (6, 11), (9, 7), (3, 8)):
                d.rectangle((x, y, x + 1, y + 1), fill=WHITE)
        else:         # LOST: spiral
            cx, cy = 8, 8
            for t in range(40):
                ang = t * 0.45
                r = 1.0 + t * 0.14
                x = int(round(cx + r * math.cos(ang)))
                y = int(round(cy + r * math.sin(ang)))
                if 0 <= x < 16 and 0 <= y < 16:
                    d.point((x, y), fill=LAV)
        sheet.paste(frame, (0, i * 16))
    save_bmp(sheet, 'focus_icons')
    write_json('focus_icons', '{\n    "type": "sprite",\n    "height": 16\n}')
    return sheet


# ----------------------------------------------------------------------------
# Dot sprite for the stats sparkline: 8x8, 2 frames (bright point, dim tick)
# ----------------------------------------------------------------------------
def gen_dot():
    sheet = new_canvas(8, 16)
    d = ImageDraw.Draw(sheet)
    d.rectangle((3, 3, 4, 4), fill=SPARK)      # frame 0: data point
    d.point((3, 8 + 3), fill=STAR)             # frame 1: baseline tick
    d.point((4, 8 + 3), fill=STAR)
    save_bmp(sheet, 'dot')
    write_json('dot', '{\n    "type": "sprite",\n    "height": 8\n}')
    return sheet


# ----------------------------------------------------------------------------
# Backgrounds: 256x256 starfield, and a variant with the mood-pad frame
# ----------------------------------------------------------------------------
def starfield(d):
    d.rectangle((0, 0, 255, 255), fill=BASE)
    seed = 0x1234ABCD
    for _ in range(260):
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        x = seed % 256
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        y = seed % 256
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        kind = seed % 10
        if kind < 6:
            d.point((x, y), fill=DOT)
        elif kind < 9:
            d.point((x, y), fill=STAR)
        else:  # tiny plus star
            d.point((x, y), fill=ACCENT)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                d.point(((x + dx) % 256, (y + dy) % 256), fill=STAR)


def gen_bg_soft():
    img = new_canvas(256, 256, BASE)
    starfield(ImageDraw.Draw(img))
    save_bmp(img, 'bg_soft')
    write_json('bg_soft', '{\n    "type": "regular_bg"\n}')
    return img


def gen_bg_pad():
    img = new_canvas(256, 256, BASE)
    d = ImageDraw.Draw(img)
    starfield(d)
    # The GBA screen shows the center 240x160 of this 256x256 map.
    # Pad play-area: 136x136 rounded frame centered at (128,128).
    x0, y0, x1, y1 = 128 - 68, 128 - 68, 128 + 68, 128 + 68
    d.rounded_rectangle((x0, y0, x1, y1), radius=8, outline=ACCENT)
    d.rounded_rectangle((x0 - 1, y0 - 1, x1 + 1, y1 + 1), radius=9, outline=STAR)
    # dotted center axes
    for t in range(x0 + 4, x1 - 3, 4):
        d.point((t, 128), fill=STAR)
        d.point((128, t), fill=STAR)
    # center marker
    d.rectangle((127, 127, 128, 128), fill=LAV)
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
        env = 1.0 - i / n            # linear decay
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
def preview(sheets):
    scale = 5
    cols = sum(s.width for s in sheets) + 8 * (len(sheets) + 1)
    rows = max(s.height for s in sheets) + 16
    canvas = Image.new('RGB', (cols, rows), (24, 18, 34))
    x = 8
    for s in sheets:
        canvas.paste(s.convert('RGB'), (x, 8))
        x += s.width + 8
    canvas = canvas.resize((canvas.width * scale, canvas.height * scale),
                           Image.NEAREST)
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    path = os.path.join(PREVIEW_DIR, 'asset_preview.png')
    canvas.save(path)
    print('preview:', path)


def main():
    os.makedirs(GFX, exist_ok=True)
    os.makedirs(AUDIO, exist_ok=True)
    sheets = [gen_mascot(), gen_cursor(), gen_focus_icons(), gen_dot()]
    bgs = [gen_bg_soft(), gen_bg_pad()]
    gen_audio()
    preview(sheets)
    # separate preview of bg centers (visible 240x160 screen area)
    scale = 2
    canvas = Image.new('RGB', ((240 + 8) * 2 + 8, 160 + 16), (0, 0, 0))
    for i, bg in enumerate(bgs):
        crop = bg.convert('RGB').crop((8, 48, 248, 208))
        canvas.paste(crop, (8 + i * 248, 8))
    canvas = canvas.resize((canvas.width * scale, canvas.height * scale),
                           Image.NEAREST)
    canvas.save(os.path.join(PREVIEW_DIR, 'bg_preview.png'))
    print('done')


if __name__ == '__main__':
    main()
