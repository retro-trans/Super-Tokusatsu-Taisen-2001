"""Render the verified Stats draw list using font pixels from the built disc."""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import insert
import repack
import texpack
from check_graphics_build import directory, read_file

ROOT = Path(__file__).resolve().parents[1]


def width(code):
    for first,key,count in ((320,'uni',126),(446,'ex',336),(782,'bi',336)):
        if first <= code < first+count:
            return insert.EF['w_'+key][code-first]
    return 8 if code < 320 else 12


def main():
    version = sys.argv[1]
    folder = ROOT/'work/ui/unit_stats'
    draws = json.loads((folder/'stats_draws.en.json').read_text(encoding='utf-8'))
    disc = ROOT/('work/output/STT2001_EN_v%s.bin'%version)
    tim = repack.dat_entries(read_file(disc,directory(disc)['MAPMAIN.DAT']))[7]
    pix,_ = insert.tim_pixels(tim)
    hf = texpack.HiFont()
    for hires in (False,True):
        k = 4 if hires else 1
        if hires:
            pages = [texpack.hires_layers(pix,p,hf,'main' if p==0 else 'ex') for p in (0,1)]
        else:
            pages = [[pix[:,p*256:(p+1)*256]&3,pix[:,p*256:(p+1)*256]>>2] for p in (0,1)]
        image = Image.new('RGB',(320*k,116*k),(0,48,48))
        dest = np.array(image)

        def glyph(code,x,y,gold):
            w = width(code)
            if code < 320:
                page,layer,u,v = 0,0,(code%32)*8,(code//32)*16
            else:
                page,layer,u,v = texpack.cell_xy(code)
            cell = pages[page][layer][v*k:(v+16)*k,u*k:(u+w)*k]
            color = (255,220,40) if gold else (240,240,240)
            palette = np.array([(0,48,48),(65,65,65),(155,155,155),color],np.uint8)
            crop = dest[y*k:(y+16)*k,x*k:(x+w)*k]
            mask = cell>0
            crop[mask] = palette[cell[mask]]

        for d in draws:
            if d['y'] not in (117,141,175,196):
                continue
            x,y = d['x'],d['y']-109
            if d['kind']=='number':
                # The native numeric drawer right-aligns within its limit.
                value = str(d['value'])
                x += (d['limit']-len(value))*8
                for c in value:
                    glyph(int(c)+1,x,y,False)
                    x += 8
            else:
                gold = False
                for code in d['codes']:
                    if code==0xFF33:
                        gold = True
                    elif code==0xFF30:
                        gold = False
                    else:
                        glyph(code,x,y,gold)
                        x += width(code)
        image = Image.fromarray(dest)
        if not hires:
            image = image.resize((1280,464),Image.Resampling.NEAREST)
        filename = 'stats_%s_preview.png'%('4x' if hires else 'native')
        image.save(folder/filename)
        print(filename,'- built font / MIPS draw-list reconstruction, not an emulator capture')


if __name__=='__main__':
    main()
