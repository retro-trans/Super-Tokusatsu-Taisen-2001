"""Game font: glyph cutting and code -> character table support.

Font sheet: MAPMAIN.DAT entry 7 (TIM 512x256 4bpp). Each 4-bit pixel packs
four 1bpp layers; the game selects a layer with CLUT 0xF0 or 0xF1.
  bit1 = layer for CLUT F0, bit3 = layer for CLUT F1 (bits 0/2 = shadows).

Glyph lookup (SLPS_028.63 @ 0x8004A7D8):
  code < 320          : 8x16,  x=(code%32)*8, y=(code//32)*16, layer F0
  320 <= code < 782   : 12x16, a=code-110, page=a//336, r=a%336,
                        x=page*256+(r%21)*12, y=(r//21)*16, layer F0
  782 <= code < 1454  : same with page-=2, layer F1
Text is u16 LE; 0xFFxx are control codes, 0xFFFE ends a line/string.

Usage:
  python tools/font.py atlas    -> work/font/atlas_*.png (indexed sheets)
  python tools/font.py ocr      -> work/font/ocr_candidates.json
"""
import json
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHEET = os.path.join(ROOT, "work", "source", "unpacked", "MAPMAIN", "0007.bin")
OUT = os.path.join(ROOT, "work", "font")
NGLYPH = 1454


def load_layers():
    d = open(SHEET, "rb").read()
    pos = 8
    flags = struct.unpack_from("<I", d, 4)[0]
    if flags & 8:
        pos += struct.unpack_from("<I", d, pos)[0]
    blen, _, _, iw, ih = struct.unpack_from("<IHHHH", d, pos)
    raw = np.frombuffer(d[pos + 12:pos + 12 + iw * 2 * ih], dtype=np.uint8).reshape(ih, iw * 2)
    pix = np.empty((ih, iw * 4), dtype=np.uint8)
    pix[:, 0::2] = raw & 15
    pix[:, 1::2] = raw >> 4
    return {"F0": (pix >> 1) & 1, "F1": (pix >> 3) & 1}


def glyph_rect(code):
    if code < 320:
        return "F0", (code % 32) * 8, (code // 32) * 16, 8
    a = code - 110
    page, r = divmod(a, 336)
    layer = "F0"
    if code >= 782:
        page -= 2
        layer = "F1"
    return layer, page * 256 + (r % 21) * 12, (r // 21) * 16, 12


def glyphs():
    layers = load_layers()
    out = []
    for c in range(NGLYPH):
        layer, x, y, w = glyph_rect(c)
        g = np.zeros((16, 12), dtype=np.uint8)
        g[:, :w] = layers[layer][y:y + 16, x:x + w]
        out.append(g)
    return out


def atlas():
    os.makedirs(OUT, exist_ok=True)
    gs = glyphs()
    S, per_row, rows_per_sheet = 3, 16, 25
    per_sheet = per_row * rows_per_sheet
    for sheet in range((NGLYPH + per_sheet - 1) // per_sheet):
        im = Image.new("RGB", (per_row * (14 * S + 2) + 40, rows_per_sheet * 17 * S), (0, 0, 70))
        dr = ImageDraw.Draw(im)
        for k in range(per_sheet):
            c = sheet * per_sheet + k
            if c >= NGLYPH:
                break
            g = Image.fromarray(gs[c] * 255).resize((12 * S, 16 * S), Image.NEAREST).convert("RGB")
            x = 40 + (k % per_row) * (14 * S + 2)
            y = (k // per_row) * 17 * S
            im.paste(g, (x, y))
            if k % per_row == 0:
                dr.text((1, y + 18), "%d" % c, fill=(0, 255, 0))
        im.save(os.path.join(OUT, "atlas_%02d_%04d.png" % (sheet, sheet * per_sheet)))


def jis_chars():
    chars = []
    for lead in list(range(0x81, 0xA0)) + list(range(0xE0, 0xEB)):
        for tr in range(0x40, 0xFD):
            if tr == 0x7F:
                continue
            try:
                ch = bytes([lead, tr]).decode("cp932")
            except UnicodeDecodeError:
                continue
            chars.append(ch)
    return chars


def norm(g):
    """Crop to bounding box and pad into a fixed 14x14 frame (top-left)."""
    ys, xs = np.nonzero(g)
    out = np.zeros((14, 14), dtype=np.uint8)
    if len(ys) == 0:
        return out, (0, 0)
    c = g[ys.min():ys.max() + 1, xs.min():xs.max() + 1][:14, :14]
    out[:c.shape[0], :c.shape[1]] = c
    return out, c.shape


def ocr():
    os.makedirs(OUT, exist_ok=True)
    gs = glyphs()
    font = ImageFont.truetype("C:/Windows/Fonts/msgothic.ttc", 12)
    cands = jis_chars()
    refs, shapes = [], []
    for ch in cands:
        im = Image.new("L", (16, 16))
        ImageDraw.Draw(im).text((0, 0), ch, font=font, fill=255)
        n, sh = norm((np.asarray(im) > 127).astype(np.uint8))
        refs.append(n)
        shapes.append(sh)
    R = np.stack(refs).reshape(len(cands), -1).astype(np.int16)
    # shifted variants of the game glyph (dx,dy in -1..1) compared to refs
    res = {}
    for c, g in enumerate(gs):
        n, sh = norm(g)
        if sh == (0, 0):
            res[c] = [[" ", 0]]
            continue
        best = None
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                s = np.roll(np.roll(n, dy, 0), dx, 1).reshape(-1).astype(np.int16)
                dist = np.abs(R - s).sum(1)
                best = dist if best is None else np.minimum(best, dist)
        order = np.argsort(best)[:5]
        res[c] = [[cands[i], int(best[i])] for i in order]
    json.dump(res, open(os.path.join(OUT, "ocr_candidates.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print("wrote", len(res))


def blur(a):
    a = a.astype(np.float32)
    p = np.pad(a, 1)
    return (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:] + 4 * p[1:-1, 1:-1]) / 8


def bbox(a):
    ys, xs = np.nonzero(a)
    if len(ys) == 0:
        return None
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def ocr2():
    """Bounding-box-normalised, blurred comparison against several fonts."""
    gs = glyphs()
    cands = jis_chars()
    fonts = [("C:/Windows/Fonts/msgothic.ttc", 12, 0), ("C:/Windows/Fonts/msgothic.ttc", 16, 0),
             ("C:/Windows/Fonts/BIZ-UDGothicR.ttc", 14, 0), ("C:/Windows/Fonts/YuGothR.ttc", 14, 0)]
    crops = []  # per font: list of cropped binary arrays
    for path, size, idx in fonts:
        f = ImageFont.truetype(path, size, index=idx)
        lst = []
        for ch in cands:
            im = Image.new("L", (size * 2, size * 2))
            ImageDraw.Draw(im).text((2, 2), ch, font=f, fill=255)
            lst.append(bbox((np.asarray(im) > 110).astype(np.uint8)))
        crops.append(lst)
    shapes = {}
    for c, g in enumerate(gs):
        b = bbox(g)
        if b is not None:
            shapes.setdefault(b.shape, []).append((c, b))
    res = {str(c): [[" ", 0.0]] for c, g in enumerate(gs) if bbox(g) is None}
    for (h, w), items in shapes.items():
        best = np.full(len(cands), 1e9, dtype=np.float32)
        for lst in crops:
            M = np.zeros((len(cands), h, w), dtype=np.float32)
            for i, cr in enumerate(lst):
                if cr is None:
                    continue
                im = Image.fromarray(cr * 255).resize((w, h), Image.BILINEAR)
                M[i] = blur(np.asarray(im, dtype=np.float32) / 255)
            for c, b in items:
                gb = blur(b)
                d = ((M - gb) ** 2).reshape(len(cands), -1).sum(1) / (h * w)
                # penalise aspect mismatch
                key = c
                if key not in res:
                    res[key] = d
                else:
                    res[key] = np.minimum(res[key], d)
        for c, b in items:
            d = res[c]
            order = np.argsort(d)[:6]
            res[c] = [[cands[i], round(float(d[i]), 4)] for i in order]
    out = {str(k): v for k, v in sorted(res.items(), key=lambda kv: int(kv[0]))}
    json.dump(out, open(os.path.join(OUT, "ocr_candidates.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print("wrote", len(out))


if __name__ == "__main__":
    {"atlas": atlas, "ocr": ocr, "ocr2": ocr2}[sys.argv[1]]()
