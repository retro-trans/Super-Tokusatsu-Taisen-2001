"""Measure the completed native atlas against Latin baseline/x-height guides."""
import argparse
import json
from pathlib import Path
import string
import unicodedata

import numpy as np
from PIL import Image, ImageDraw

import font_effects as FX
import font_metrics as M
import gfx
import native_font2x as N
import rayblade_font as R
import repack
import texpack
from check_graphics_build import directory, read_file

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--version',default='0.9.4')
    args=parser.parse_args()
    out=ROOT/'work/output'
    target=out/('STT2001_EN_v'+args.version+'.bin')
    old=out/'STT2001_EN_v0.9.3.bin'
    meta=json.loads((ROOT/'work/font/efont.json').read_text(encoding='utf-8'))
    assert meta['font_effects']==FX.STYLE and meta['font_metrics']==M.STYLE
    mm=repack.dat_entries(read_file(target,directory(target)['MAPMAIN.DAT']))
    oldmm=repack.dat_entries(read_file(old,directory(old)['MAPMAIN.DAT']))
    exe=read_file(target,directory(target)['SLPS_028.63'])
    assert exe==read_file(old,directory(old)['SLPS_028.63']), 'Renderer/gameplay changed'
    atlas=gfx.Tim(mm[7]).idx[:,:256]>>2
    oldatlas=gfx.Tim(oldmm[7]).idx[:,:256]>>2
    import ui_value_font
    pixels,oldpixels=[gfx.Tim(tim).idx&3 for tim in (mm[7],oldmm[7])]
    for code in ui_value_font.CODES:
        x,y=(code%32)*8,(code//32)*16
        assert np.array_equal(pixels[y:y+16,x:x+8],oldpixels[y:y+16,x:x+8]),'Small native HUD glyph changed'
    desc=N.assets()[1]
    records={}
    for i,ch in enumerate(meta['uni']):
        x,packed=desc[i*2:i*2+2]
        y=packed&0xe0
        cell=atlas[y:y+32,x:x+meta['widths'][ch]*2]
        oldcell=oldatlas[y:y+32,x:x+meta['widths'][ch]*2]
        readings=[]
        for sample in (cell,cell[::2,::2],cell[1::2,1::2]):
            rows=np.flatnonzero((sample>=2).any(axis=1))
            readings.append([int(rows[0]),int(rows[-1])] if len(rows) else None)
        records[ch]={'code':meta['encode'][ch],'atlas_rect':[x,y,cell.shape[1],32],
                     'advance':meta['widths'][ch],'ink_y':readings,
                     'prior_ink_y':M.bounds(oldcell)}
    short='acemnorsuvwxz'
    for ch in short:
        assert records[ch]['ink_y']==[[9,22],[5,11],[4,10]],(ch,records[ch])
    for ch in string.ascii_uppercase.replace('Q','')+string.digits+'bdfhikl':
        assert records[ch]['ink_y']==[[4,22],[2,11],[2,10]],(ch,records[ch])
    for ch in 'gpqy':
        assert records[ch]['ink_y']==[[9,24],[5,12],[4,11]],(ch,records[ch])
    assert records['j']['ink_y'][0]==[4,24]
    assert records['Q']['ink_y'][0]==[4,24]
    accents=[]
    for ch in meta['uni']:
        decomposed=unicodedata.normalize('NFD',ch)
        if len(decomposed)>1 and decomposed[0] in string.ascii_letters:
            expected=24 if '\u0327' in decomposed else 22
            assert records[ch]['ink_y'][0][1]==expected,(ch,records[ch])
            if '\u0327' not in decomposed:
                assert records[ch]['ink_y'][0][0] < (4 if decomposed[0].isupper() else 9)
            accents.append(ch)
    assert records['a']['prior_ink_y'][0] < records['e']['prior_ink_y'][0]
    assert records['a']['ink_y']==records['e']['ink_y']

    # All solid source samples keep one constant colour, irrespective of row.
    raw=R.Font(normalize=True)
    checks=0
    for i,ch in enumerate(R.ASCII):
        high=raw.hires(ch)[::2,::2]
        width=meta['widths'][ch]*2
        cols=np.flatnonzero(high[:,:width].max(0))
        shift=min(2,int(cols[0])) if len(cols) else 0
        yy,xx=np.nonzero(high[:,:width]==3)
        index=meta['uni'].index(ch)
        x,packed=desc[index*2:index*2+2]
        assert np.all(atlas[(packed&0xe0)+yy,x+xx-shift]==3),('Row shading survived',ch)
        checks+=len(yy)

    image=Image.new('RGB',(1180,540),(18,30,30))
    draw=ImageDraw.Draw(image)
    cases=[('v0.9.3: lowercase',oldatlas,'abcdefghijklmnopqrstuvwxyz'),
           ('v'+args.version+': aligned lowercase, flat ink and shadow',atlas,'abcdefghijklmnopqrstuvwxyz'),
           ('Capitals and ascenders',atlas,'ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
           ('Aligned digits',atlas,'0123456789')]
    palette=texpack.tim_parts(mm[7])[3]
    lut=np.array([(18,30,30)]+[texpack.c15(palette[10*16+v*4]) for v in (1,2,3)],np.uint8)
    for row,(label,sheet,chars) in enumerate(cases):
        oy=22+row*130
        draw.text((12,oy-16),label+' (native font preview)',fill='white')
        draw.line((12,oy+44,1160,oy+44),fill=(62,92,110))
        draw.line((12,oy+18,1160,oy+18),fill=(38,68,58))
        for col,ch in enumerate(chars):
            i=meta['uni'].index(ch);x,packed=desc[i*2:i*2+2]
            cell=sheet[packed&0xe0:(packed&0xe0)+32,x:x+meta['widths'][ch]*2]
            glyph=Image.fromarray(lut[cell]).resize((cell.shape[1]*2,64),Image.Resampling.NEAREST)
            image.paste(glyph,(18+col*44,oy))
            draw.text((24+col*44,oy+72),ch,fill=(190,190,190))
    folder=ROOT/'work/ui/font'
    preview=folder/('alignment-v'+args.version+'.png')
    image.save(preview)
    detail={'version':args.version,'baseline_native':M.BASELINE/4,'capital_top_native':M.CAP_TOP/4,
            'xheight_top_native':M.X_TOP/4,'descender_bottom_native':M.DESCENDER/4,
            'glyphs':records,'preview_is_emulator_capture':False}
    (folder/('metrics-v'+args.version+'.en.json')).write_bytes((json.dumps(detail,ensure_ascii=False,indent=1)+'\n').encode())
    result={'version':args.version,'all_checks_passed':True,'glyphs_measured':len(records),
            'short_lowercase_letters_aligned':short,'capital_digit_ascender_letters_aligned':True,
            'a_and_e_match_both_native_sampling_phases':True,'accents_preserved':accents,
            'descenders_preserved':True,'flat_ink_samples_checked':checks,'renderer_byte_identical_to':'0.9.3',
            'small_native_hud_cells_preserved':len(ui_value_font.CODES),
            'native_only':True,'preview':str(preview.relative_to(ROOT)),'emulator_verified':False}
    (out/('STT2001_EN_v'+args.version+'_font_metrics_verification.json')).write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
