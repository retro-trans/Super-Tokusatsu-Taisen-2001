"""English weapon markers in the original fixed-size font cells.

Codes and advances remain unchanged: D/I use eight pixels, attributes twelve.
Default is a dry run; --preview writes a native/4x reconstruction.
"""
import json
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
import ui_glyphs

ROOT = Path(__file__).resolve().parents[1]
META = json.loads((ROOT/'work/ui/weapons/markers.en.json').read_text(encoding='utf-8'))
PREFIX = {int(k): v for k,v in META['prefix'].items()}
ATTRIBUTES = {int(k): v for k,v in META['attributes'].items()}
FONT = dict(ui_glyphs.FONT)
FONT.update({'B':('110','101','110','101','110'),
             'M':('101','111','111','101','101'),
             'W':('101','101','111','111','101')})


def badges(hires=False):
    out = {}
    for code,row in ATTRIBUTES.items():
        if hires:
            ink = ui_glyphs.hi_text(row['short'],12)
            cell = np.zeros((64,48),np.uint8)
            cell[8:56,2:46] = 1
            # A crisp face atop the dark badge, preserving palette indices.
            cell = np.where(ink>=2,ink,cell).astype(np.uint8)
        else:
            cell = np.zeros((16,12),np.uint8)
            cell[2:14,1:11] = 1
            text = row['short']
            span = sum(len(FONT[c][0])+1 for c in text)-1
            assert span<=11
            x = (12-span)//2
            for char in text:
                for y,bits in enumerate(FONT[char]):
                    for dx,bit in enumerate(bits):
                        if bit=='1':
                            cell[y+5,x+dx] = 3
                x += len(FONT[char][0])+1
        out[code] = cell
    return out


def prefixes(hires=False,hf=None):
    # Native Latin capitals use the same shape/baseline as UI values.
    from PIL import Image as PILImage
    import efont
    import vwf_font as V
    if hires and hf is None:
        import texpack
        hf = texpack.HiFont()
    out = {}
    for code,row in PREFIX.items():
        glyph = V.render_char(efont.font(),row['short'])[0]
        columns = np.flatnonzero(glyph.max(0));left,right=int(columns[0]),int(columns[-1])+1
        span = min(right-left,7);factor=4 if hires else 1
        ink = hf.char(row['short'])[:,left*4:right*4] if hires else glyph[:,left:right]
        if ink.shape[1] != span*factor:
            ink = np.asarray(PILImage.fromarray(ink).resize((span*factor,16*factor),PILImage.Resampling.NEAREST))
        cell = np.zeros((16*factor,8*factor),np.uint8)
        x = (8-span)//2*factor
        cell[:,x:x+span*factor] = ink
        out[code] = cell
    return out


def apply_main(pixels):
    for code,glyph in prefixes().items():
        x,y=(code%32)*8,(code//32)*16
        pixels[y:y+16,x:x+8] = (pixels[y:y+16,x:x+8]&12)|glyph


def apply_ex(pixels,page_x):
    for code,glyph in badges().items():
        r=code-1118;x,y=page_x+(r%21)*12,(r//21)*16
        pixels[y:y+16,x:x+12] = (pixels[y:y+16,x:x+12]&3)|(glyph<<2)


@lru_cache(maxsize=1)
def original_prefixes():
    import fontsets
    return {code:fontsets.glyph_level(code)[:,:8] for code in PREFIX}


def upscale_main_base(pixels):
    out=pixels.copy()
    for code,glyph in original_prefixes().items():
        x,y=(code%32)*8,(code//32)*16
        out[y:y+16,x:x+8]=(out[y:y+16,x:x+8]&12)|glyph
    return out


def ex_key(pixels):
    layer=(pixels>>2).copy()
    for code in list(ATTRIBUTES)+list(ui_glyphs.cells()):
        r=code-1118;x,y=(r%21)*12,(r//21)*16
        layer[y:y+16,x:x+12]=0
    return layer.tobytes()


@lru_cache(maxsize=1)
def original_ex_pages():
    import fontsets
    pages = [fontsets.main_sheet()[:,256:512],fontsets.battle_sheet()[:,256:512]]
    pages += [fontsets.var_sheet(v) for v in fontsets.VARIANTS]
    out={}
    for page in pages:
        key=ex_key(page)
        if key in out:
            for code in ATTRIBUTES:
                r=code-1118;x,y=(r%21)*12,(r//21)*16
                assert np.array_equal(out[key][y:y+16,x:x+12]>>2,page[y:y+16,x:x+12]>>2)
        out[key]=page
    return out


def upscale_ex_base(pixels):
    """Restore original badge shapes for filtering, keeping neighboring cells stable."""
    original=original_ex_pages()[ex_key(pixels)]
    out=pixels.copy()
    for code in ATTRIBUTES:
        r=code-1118;x,y=(r%21)*12,(r//21)*16
        out[y:y+16,x:x+12]=(out[y:y+16,x:x+12]&3)|(original[y:y+16,x:x+12]&12)
    return out


def preview():
    image=Image.new('RGB',(720,220),(0,48,48));draw=ImageDraw.Draw(image)
    draw.text((12,6),'English weapon markers - reconstruction, not an emulator capture',fill='white')
    palette=np.array([(0,48,48),(65,65,65),(165,165,165),(240,240,240)],np.uint8)
    rows=list(PREFIX.items())+list(ATTRIBUTES.items())
    for i,(code,row) in enumerate(rows):
        x=16+(i%4)*176;y=32+(i//4)*86
        for hires in (False,True):
            cells=prefixes(hires) if code in PREFIX else badges(hires)
            glyph=Image.fromarray(palette[cells[code]])
            if not hires:
                glyph=glyph.resize((glyph.width*4,glyph.height*4),Image.Resampling.NEAREST)
            image.paste(glyph,(x+(64 if hires else 0),y))
        draw.text((x,y+65),row['meaning'],fill='white')
    image.save(ROOT/'work/ui/weapons/markers_preview.png')


if __name__=='__main__':
    print('Dry run:', {k:v['short'] for k,v in PREFIX.items()}, {k:v['short'] for k,v in ATTRIBUTES.items()})
    prefixes();prefixes(True);badges();badges(True);original_ex_pages()
    if '--preview' in sys.argv:
        preview()
