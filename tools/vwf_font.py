"""Build the English variable-width font from Gen'ei Latin (SIL OFL 1.1).

Glyphs go into the 12x16 cells of codes VWF_FIRST.. (F0 layer, texture
page 0, rows 10-15 of MAPMAIN #7), drawn in the game's 2bpp style:
  0 transparent, 1 dark shadow (unused unless SHADOW), 2 mid (anti-alias), 3 bright core.
The width table drives the VWF patch (tools/vwf_patch.py).

Usage:
  python tools/vwf_font.py preview [size] [face]   -> work/font/vwf_preview.png
  python tools/vwf_font.py build                    -> work/font/vwf_table.json + vwf_cells.npy
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "work", "font")
FONT_DIR = os.path.join(ROOT, "incoming", "GenEiLatin")
FACES = {"go": ("GenEiLateGo_v2.ttc", 1), "min": ("GenEiLateMin_v2.ttc", 0)}

VWF_FIRST = 320          # first code used by the English font
VWF_COUNT = 126          # cells available in page 0 rows 10-15
CELL_W, CELL_H = 12, 16
SPACE_W = 4
EXTRAS = "’‘“”…—–éèêëàâçôöüïÉ♪♥★☆×°«»・±→←"
CHARSET = "".join(chr(c) for c in range(0x20, 0x7F)) + EXTRAS
assert len(CHARSET) <= VWF_COUNT

DEFAULT_SIZE = 13
DEFAULT_FACE = "go"
BASELINE = 12            # pixel row of the baseline inside the 16px cell


SPACING = "font"        # "tight": ink+1, "font": font advance
SHADOW = False          # drop shadow (level 1) right/below the ink; off since 0.3.2


def render_char(font, ch):
    """Return (2bpp cell array, advance width)."""
    if ch == " ":
        return np.zeros((CELL_H, CELL_W), np.uint8), SPACE_W
    big = Image.new("L", (40, 40))
    ascent = font.getmetrics()[0]
    ImageDraw.Draw(big).text((8, 8 + BASELINE - ascent), ch, font=font, fill=255)
    a = np.asarray(big, dtype=np.int32)
    cols = np.nonzero(a.max(0) > 40)[0]
    if len(cols) == 0:
        return np.zeros((CELL_H, CELL_W), np.uint8), SPACE_W
    x0, x1 = cols[0], cols[-1]
    ink = a[8:8 + CELL_H, x0:x1 + 1]
    w = min(ink.shape[1], CELL_W - 1)
    ink = ink[:, :w]
    core = np.zeros((CELL_H, CELL_W), np.uint8)
    core[:ink.shape[0], :w] = np.where(ink >= 150, 3, np.where(ink >= 70, 2, 0))
    lit = core > 0
    shadow = np.zeros_like(lit)
    shadow[1:, 1:] = lit[:-1, :-1]
    shadow[:, 1:] |= lit[:, :-1]
    cell = np.where(lit, core, np.where(shadow & SHADOW, 1, 0)).astype(np.uint8)
    if SPACING == "font":
        lsb = x0 - 8
        adv = int(round(font.getlength(ch))) - max(lsb, 0) + 1
        adv = max(min(adv, CELL_W), w + 1)
    else:
        adv = min(w + 1, CELL_W)   # ink + shadow column
    if ch in "ijl!.,:;'|" and SPACING == "tight":
        adv = min(adv + 1, CELL_W)
    return cell, adv


def build_cells(size=DEFAULT_SIZE, face=DEFAULT_FACE):
    fname, idx = FACES[face]
    font = ImageFont.truetype(os.path.join(FONT_DIR, fname), size, index=idx)
    cells, widths = [], []
    for ch in CHARSET:
        c, w = render_char(font, ch)
        cells.append(c)
        widths.append(int(w))
    return cells, widths


def encode_table():
    return {ch: VWF_FIRST + i for i, ch in enumerate(CHARSET)}


PAL = {0: (24, 32, 96), 1: (40, 40, 40), 2: (165, 165, 165), 3: (230, 230, 230)}


def preview(size=DEFAULT_SIZE, face=DEFAULT_FACE):
    cells, widths = build_cells(size, face)
    table = encode_table()
    lines = [
        "Gavan: \"I won't let you get away,",
        "Lucifard! The Space Sheriff never",
        "gives up!\" Quick brown fox, jumping…",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789",
        "abcdefghijklmnopqrstuvwxyz !?.,'-()",
    ]
    W = 320
    canvas = np.zeros((16 * len(lines) + 16, W), np.uint8)
    for li, line in enumerate(lines):
        x = 8
        for ch in line:
            i = table[ch] - VWF_FIRST
            c, w = cells[i], widths[i]
            if x + w > W:
                break
            region = canvas[8 + li * 16:8 + li * 16 + 16, x:x + CELL_W]
            m = c[:, :region.shape[1]]
            region[m > 0] = m[m > 0]
            x += w
    im = Image.new("RGB", (W, canvas.shape[0]))
    im.putdata([PAL[v] for v in canvas.flatten()])
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, "vwf_preview_%s_%d.png" % (face, size))
    im.resize((W * 3, canvas.shape[0] * 3), Image.NEAREST).save(p)
    print(p)


def build(size=DEFAULT_SIZE, face=DEFAULT_FACE):
    cells, widths = build_cells(size, face)
    os.makedirs(OUT, exist_ok=True)
    np.save(os.path.join(OUT, "vwf_cells.npy"), np.stack(cells))
    json.dump({"first_code": VWF_FIRST, "font": FACES[face][0], "size": size,
               "charset": CHARSET, "widths": widths, "encode": encode_table()},
              open(os.path.join(OUT, "vwf_table.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("built %d glyphs, widths %d..%d" % (len(cells), min(widths), max(widths)))


if __name__ == "__main__":
    cmd = sys.argv[1]
    size = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_SIZE
    face = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_FACE
    {"preview": preview, "build": build}[cmd](size, face)
