"""Match fixed-width UI values to the English label font.

The runtime still uses the original codes and eight-pixel advance. Only F0
pixels change. Encyclopedia tab sheets have a separate layout and are excluded.
Run without arguments for a dry run; --preview exports a reconstruction.
"""
import json
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
import efont
import vwf_font as V

ROOT = Path(__file__).resolve().parents[1]
META = json.loads((ROOT/'work/ui/unit_stats/value_font.en.json').read_text(encoding='utf-8'))
CODES = {int(k): v for k, v in META['codes'].items()}


def cells(hires=False, hf=None):
    font = efont.font()
    if hires and hf is None:
        import texpack
        hf = texpack.HiFont()
    result = {}
    for code, char in CODES.items():
        native = V.render_char(font, char)[0]
        cols = np.flatnonzero(native.max(0))
        left, right = int(cols[0]), int(cols[-1])+1
        width = min(right-left, 7)
        x = (8-width)//2
        if hires:
            # Use the same native placement and baseline as the English labels.
            glyph = hf.char(char)[:,left*4:right*4]
            if glyph.shape[1] != width*4:
                glyph = np.asarray(Image.fromarray(glyph).resize((width*4,64),Image.Resampling.NEAREST))
            cell = np.zeros((64,32),np.uint8)
            cell[:,x*4:(x+width)*4] = glyph
        else:
            glyph = native[:,left:right]
            if glyph.shape[1] != width:
                # Compress only horizontally: preserve the shared font height.
                tone = Image.fromarray((glyph.astype(np.uint16)*85).astype(np.uint8))
                tone = np.asarray(tone.resize((width,16),Image.Resampling.LANCZOS))
                glyph = np.where(tone>=150,3,np.where(tone>=70,2,0)).astype(np.uint8)
            cell = np.zeros((16,8),np.uint8)
            cell[:,x:x+width] = glyph
        result[code] = cell
    return result


def apply_pixels(pixels):
    for code, glyph in cells().items():
        x, y = (code%32)*8, (code//32)*16
        pixels[y:y+16,x:x+8] = (pixels[y:y+16,x:x+8]&12)|glyph


@lru_cache(maxsize=1)
def original_cells():
    import insert
    import repack
    source = repack.dat_entries((ROOT/'work/source/disc/MAPMAIN.DAT').read_bytes())[7]
    pixels,_ = insert.tim_pixels(source)
    return {code:(pixels[(code//32)*16:(code//32+1)*16,(code%32)*8:(code%32+1)*8]&3).copy()
            for code in CODES}


def upscale_base(pixels):
    """Keep Scale4x's neighboring glyph pixels identical to the previous pack.

    Native values are overwritten by independent high-resolution cells later.
    Restoring their original shapes before filtering prevents the filter from
    changing adjacent icon/kana edges outside those cells.
    """
    out = pixels.copy()
    for code,glyph in original_cells().items():
        x,y = (code%32)*8,(code//32)*16
        out[y:y+16,x:x+8] = (out[y:y+16,x:x+8]&12)|glyph
    return out


def preview():
    import fontsets
    import texpack
    image = Image.new('RGB',(960,432),(38,29,23))
    draw = ImageDraw.Draw(image)
    draw.text((16,8),'Before (top) / matched values (bottom) - reconstructed native pixels',fill='white')
    pairs = [('Lv.', '4'),('Sz.', 'S'),('Will', '121'),('Acc.', '100%'),('Will', '???')]
    native = cells()
    palette = np.array([(38,29,23),(70,60,50),(170,160,150),(240,235,225)],np.uint8)
    for row in range(2):
        for i,(label,value) in enumerate(pairs):
            x, y = 12+(i%3)*80, 12+row*48+(i//3)*20
            for char in label:
                cell,advance = V.render_char(efont.font(),char)
                pal = palette.copy(); pal[2]=(190,165,45); pal[3]=(255,220,45)
                glyph = Image.fromarray(pal[cell]).resize((48,64),Image.Resampling.NEAREST)
                image.paste(glyph,(x*4,y*4)); x += advance
            x += 6
            for char in value:
                code = next(k for k,v in CODES.items() if v==char)
                glyph = native[code] if row else fontsets.glyph_level(code)[:,:8]
                image.paste(Image.fromarray(palette[glyph]).resize((32,64),Image.Resampling.NEAREST),(x*4,y*4))
                x += 8
    path = ROOT/'work/ui/unit_stats/value_font_preview.png'
    image.save(path)
    print(path)
    hf = texpack.HiFont()
    native = cells(True, hf)
    image = Image.new('RGB',(960,192),(38,29,23))
    ImageDraw.Draw(image).text((16,8),'Matched values with the 4x pack - reconstruction',fill='white')
    for i,(label,value) in enumerate(pairs):
        x, y = 12+(i%3)*80, 12+(i//3)*20
        for char in label:
            pal = palette.copy(); pal[2]=(190,165,45); pal[3]=(255,220,45)
            image.paste(Image.fromarray(pal[texpack.shadow(hf.char(char))]),(x*4,y*4))
            x += V.render_char(efont.font(),char)[1]
        x += 6
        for char in value:
            code = next(k for k,v in CODES.items() if v==char)
            image.paste(Image.fromarray(palette[texpack.shadow(native[code])]),(x*4,y*4))
            x += 8
    path = ROOT/'work/ui/unit_stats/value_font_4x_preview.png'
    image.save(path)
    print(path)


if __name__ == '__main__':
    print('Dry run: %d F0 value glyphs; fixed 8x16 cells and 8px runtime advance.'%len(CODES))
    print('Samples: Lv. 4 / Sz. S / Will 121 / Acc. 100% / Will ???')
    for code, cell in cells().items():
        lit = np.argwhere(cell>0)
        print('%d %s: ink %dx%d, rows %d..%d'%(code,CODES[code],int(lit[:,1].ptp()+1),int(lit[:,0].ptp()+1),int(lit[:,0].min()),int(lit[:,0].max())))
    cells(True)
    if '--preview' in sys.argv:
        preview()
