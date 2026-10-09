"""Compact terrain glyphs in spare F1 cells, preserving the English font map.

Database labels point to one-cell aliases; full map terrain names are retained.
Run without flags for a dry run. --preview exports native/4x layout samples.
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import vwf_font as V

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT/'work/translation/en/ui_glyphs.en.json'
META = json.loads(MANIFEST.read_text(encoding='utf-8'))
FIRST = META['glyph_first']
# 3x5 capitals and narrower lowercase letters for the 24px heading.
FONT = {
 'A': ('010','101','111','101','101'), 'I': ('1','1','1','1','1'),
 'R': ('110','101','110','101','101'), 'L': ('100','100','100','100','111'),
 'N': ('101','111','111','111','101'), 'D': ('110','101','101','101','110'),
 'S': ('011','100','010','001','110'), 'E': ('111','100','110','100','111'),
 'P': ('110','101','110','100','100'), 'C': ('011','100','100','100','011'),
 'K': ('101','101','110','101','101'), 'G': ('011','100','101','101','011'),
 'F': ('111','100','110','100','100'), 'U': ('101','101','101','101','111'),
 'T': ('111','010','010','010','010'), 'e': ('000','010','101','110','011'),
 'r': ('00','11','10','10','10'), 'a': ('000','110','001','111','111'),
 'i': ('1','0','1','1','1'), 'n': ('000','110','101','101','101'),
}


def native_text(text, width):
    out = np.zeros((16, width), np.uint8)
    text_width = sum(len(FONT[c][0])+1 for c in text)-1
    assert text_width <= width, (text, text_width, width)
    x = (width-text_width)//2
    for c in text:
        rows = FONT[c]
        for y, row in enumerate(rows):
            for dx, bit in enumerate(row):
                if bit == '1':
                    out[y+6, x+dx] = 3
        x += len(rows[0])+1
    return out


def hi_text(text, width):
    path, index = V.FACES[V.DEFAULT_FACE]
    path = Path(V.FONT_DIR)/path
    for size in range(22, 13, -1):
        font = ImageFont.truetype(str(path), size, index=index)
        bounds = font.getbbox(text)
        if bounds[2]-bounds[0] <= width*4-4:
            break
    image = Image.new('L', (width*4, 64))
    x = (image.width-(bounds[2]-bounds[0]))//2-bounds[0]
    y = (image.height-(bounds[3]-bounds[1]))//2-bounds[1]
    ImageDraw.Draw(image).text((x,y), text, font=font, fill=255)
    # Match the game's four palette levels, with transparent background.
    return ((np.asarray(image).astype(np.uint16)*3+127)//255).astype(np.uint8)


def cells(hires=False):
    render = hi_text if hires else native_text
    out = {FIRST+i: render(row['short'], 12) for i,row in enumerate(META['terrain'])}
    heading = render(META['heading']['text'], 24)
    width = 48 if hires else 12
    for i in range(2):
        out[FIRST+7+i] = heading[:,i*width:(i+1)*width]
    return out


def apply_pixels(pixels, page_x):
    """Only alter F1; existing F0 word glyphs remain byte-for-byte intact."""
    for code, glyph in cells().items():
        r = code-FIRST
        x = page_x+(r%21)*12
        y = (r//21)*16
        target = pixels[y:y+16,x:x+12]
        assert target.shape == glyph.shape
        pixels[y:y+16,x:x+12] = (target & 3) | (glyph << 2)


def patch_database(data):
    out = bytearray(data)
    aliases = [(r['index'], [FIRST+i, 0xFFFE]) for i,r in enumerate(META['terrain'])]
    heading = [0xFF33, FIRST+7, FIRST+8, 0xFF30, 0xFFFE]
    heading_at = len(out)
    out += struct.pack('<5H', *heading)
    for index in META['heading']['indices']:
        struct.pack_into('<H', out, index*2, heading_at)
    for index, words in aliases:
        pointer = len(out)
        assert pointer < 0x10000
        struct.pack_into('<H', out, index*2, pointer)
        out += struct.pack('<2H', *words)
    return bytes(out)+bytes((-len(out))%4)


def preview():
    out = ROOT/'work/ui/unit_stats'
    out.mkdir(parents=True, exist_ok=True)
    for hires in (False, True):
        factor = 4 if hires else 1
        image = Image.new('RGB', (156*factor, 68*factor), (0,48,48))
        glyphs = cells(hires)
        palette = np.array([(0,48,48),(70,70,70),(160,160,160),(240,240,240)],np.uint8)
        def paste(code, x, y, gold=False):
            pal = palette.copy()
            if gold:
                pal[3] = (255,220,45)
            image.paste(Image.fromarray(pal[glyphs[code]]), (x*factor,y*factor))
        paste(FIRST+7, 4, 6, True)
        paste(FIRST+8, 16, 6, True)
        for i in range(7):
            x = 34+(i%4)*28
            y = 6+(i//4)*24
            paste(FIRST+i,x,y)
            # Native rating letters come from the game's normal English font.
            import insert
            import efont
            z = np.load(ROOT/'work/font/efont_cells.npz')
            grade = 'AABCEEE'[i]
            code = efont.encode_plain(grade,insert.EF['encode'])[0]
            cell = z['uni'][code-320]
            color = Image.fromarray(palette[cell])
            if hires:
                import texpack
                color = Image.fromarray(palette[texpack.shadow(texpack.HiFont().char(grade))])
            image.paste(color,((x+14)*factor,y*factor))
        display = image if hires else image.resize((624,272),Image.Resampling.NEAREST)
        display.save(out/('terrain_%s_preview.png' % ('4x' if hires else 'native')))
    print('Native and 4x terrain layout reconstructions exported; not emulator captures.')


if __name__ == '__main__':
    print('Dry run: codes %d-%d, nine 12x16 F1 cells; heading 24px.' % (FIRST,FIRST+8))
    print('Terrain labels:', ' / '.join(r['short'] for r in META['terrain']))
    print('Database indices:', ', '.join(hex(r['index']) for r in META['terrain']))
    cells(); cells(True)
    if '--preview' in sys.argv:
        preview()
