"""Render encoded English strings as the game would (VWF + wrap), for QA.

python tools/preview_text.py STAGE0005 [n]  -> work/font/preview_STAGE0005.png
Decodes the rebuilt overlay from work/build/STAGE.DAT entries (via insert.build_all)
and draws the first n strings as dialogue pages.
"""
import json
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import efont  # noqa: E402
import vwf_font as V  # noqa: E402

EF = json.load(open(os.path.join(ROOT, "work", "font", "efont.json"), encoding="utf-8"))
Z = np.load(os.path.join(ROOT, "work", "font", "efont_cells.npz"))


def glyph(code):
    if efont.UNI_FIRST <= code < efont.UNI_FIRST + len(Z["uni"]):
        i = code - efont.UNI_FIRST
        return Z["uni"][i], EF["w_uni"][i]
    if efont.BI_FIRST <= code < efont.BI_FIRST + len(Z["bi"]):
        i = code - efont.BI_FIRST
        return Z["bi"][i], EF["w_bi"][i]
    return None, 8


def render_pages(words, width=264):
    """words: u16 list of one string. Returns list of page images."""
    pages, lines, cur = [], [], []
    for w in words + [0xFFFC]:
        if w == 0xFFFB:
            lines.append(cur)
            cur = []
        elif w == 0xFFFC:
            lines.append(cur)
            pages.append(lines)
            lines, cur = [], []
        else:
            cur.append(w)
    out = []
    for pg in pages:
        canvas = np.zeros((16 * max(len(pg), 1) + 8, width + 16), np.uint8)
        for li, ln in enumerate(pg):
            x = 8
            for w in ln:
                if w >= 0xFF00:
                    x += 0 if w not in (0xFF01, 0xFF02, 0xFF03, 0xFF04) else 40
                    continue
                cell, adv = glyph(w)
                if cell is not None:
                    reg = canvas[4 + li * 16:4 + li * 16 + 16, x:x + 12]
                    m = cell[:, :reg.shape[1]]
                    reg[m > 0] = m[m > 0]
                x += adv
        im = Image.new("RGB", canvas.shape[::-1])
        im.putdata([V.PAL[v] for v in canvas.flatten()])
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, width + 15, canvas.shape[0] - 1], outline=(255, 80, 80))
        out.append(im)
    return out


if __name__ == "__main__":
    import insert
    import repack
    import dump_script as D
    files, _ = insert.build_all()
    name = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    stage = repack.dat_entries(files["STAGE.DAT"])
    buf = stage[int(name[5:])]
    strs = D.overlay_strings(buf, 0)
    ims = []
    start = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    for off, ws, term in strs[start:start + n]:
        ws = list(ws)
        if ws and ws[0] == 0xFF33 and 0xFF30 in ws:
            k = ws.index(0xFF30)
            ws = ws[k + 1:]
            if ws and ws[0] == 0xFFFB:
                ws = ws[1:]
        ims += render_pages(ws)
    H = sum(i.size[1] + 6 for i in ims)
    sheet = Image.new("RGB", (ims[0].size[0], H), (40, 40, 40))
    y = 0
    for im in ims:
        sheet.paste(im, (0, y))
        y += im.size[1] + 6
    p = os.path.join(ROOT, "work", "font", "preview_%s.png" % name)
    sheet.resize((sheet.size[0] * 2, sheet.size[1] * 2), Image.NEAREST).save(p)
    print(p)
