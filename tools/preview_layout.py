"""Reconstruct layout previews from native TIM/font pixels (not emulator captures)."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import efont
import gfx
import gfx_translate
import insert

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work/ui/dialogue"
OUT.mkdir(parents=True, exist_ok=True)
target = next(t for t in gfx_translate.load_manifest()["targets"] if t["archive"] == "EVENT" and t["entry"] == 52)
raw, _ = gfx_translate.render(gfx_translate.source(target), target)
atlas = gfx.Tim(raw).rgb()
for number in (1, 12):
    im = Image.new("RGB", (320, 240))
    im.paste(atlas.crop((0, 0, 320, 100)), (0, 72))
    x = 122 if number < 10 else 116
    im.paste(atlas.crop((256, 104, 308, 128)), (x, 68))
    x = 180 if number < 10 else 174
    for digit in str(number):
        u = int(digit)*24
        im.paste(atlas.crop((u+6, 104, u+18, 128)), (x, 68))
        x += 12
    im.paste(atlas.crop((240, 104, 241, 105)), (220, 69))
    im.resize((960, 720), Image.Resampling.NEAREST).save(OUT / ("stage_%d_layout.png" % number))

cells = np.load(ROOT / "work/font/efont_cells.npz")


def text(im, x, y, s, color):
    pix = im.load()
    for code in efont.encode_plain(s, insert.EF["encode"]):
        kind = "uni" if code < 446 else "bi"
        index = code - (320 if kind == "uni" else 782)
        cell = cells[kind][index]
        for cy, cx in zip(*np.nonzero(cell >= 2)):
            if 0 <= x+cx < im.width and 0 <= y+cy < im.height:
                pix[x+cx, y+cy] = color
        x += insert.EF["w_"+kind][index]


line = "Staff Officer Kitakura, this is your responsibility! I'll be considering what to do with you… understood?"
pages = insert.layout(line, 220, 3)
sheet = Image.new("RGB", (320, 112*len(pages)), (0, 0, 0))
for page, lines in enumerate(pages):
    im = Image.new("RGB", (320, 96))
    d = ImageDraw.Draw(im)
    d.rectangle((16, 8, 304, 88), fill=(50, 32, 22), outline=(170, 170, 180), width=2)
    d.rectangle((28, 34, 64, 76), fill=(16, 65, 100), outline=(0, 150, 210))
    text(im, 70, 15, "Director Sawa", (255, 220, 50))
    for n, tokens in enumerate(lines):
        text(im, 70, 31+n*16, "".join(tokens), (239, 239, 239))
    sheet.paste(im, (0, page*112+16))
    ImageDraw.Draw(sheet).text((16, page*112+2), "Layout reconstruction - page %d" % (page+1), fill=(160, 160, 170))
sheet.resize((960, sheet.height*3), Image.Resampling.NEAREST).save(OUT / "sawa_layout.png")
print("Stage 1/12 and Sawa layout reconstructions written; dialogue pages:")
print([["".join(row) for row in p] for p in pages])
