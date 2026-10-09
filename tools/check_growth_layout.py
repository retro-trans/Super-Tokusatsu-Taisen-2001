"""Verify the completed build's Unit growth row and all four runtime variants."""
import json
import struct
import sys
from pathlib import Path
from unicorn.mips_const import UC_MIPS_REG_SP, UC_MIPS_REG_RA, UC_MIPS_REG_PC
import cm
import growth_layout
import insert
import repack
import texpack
from check_graphics_build import directory, read_file, file_hash
from check_ui_labels import strings
from check_stats_layout import Screen, ARGS, MASK
from preview_stats_layout import width

ROOT = Path(__file__).resolve().parents[1]


def run(screen,unit_id,variant):
    cpu = screen.cpu
    cpu.mem_write(0x101568,bytes([unit_id]))
    # The original table packs even-unit modes in the high nibble, odd in low.
    packed = variant << 4 if unit_id==0 else variant
    cpu.mem_write(0xAECE8,bytes([packed]))
    cpu.mem_write(0xAA862,struct.pack('<H',0xFFFF))
    stack,stop = 0x801E0000,0x80008000
    for reg,value in zip(ARGS,(0x800AA84C,0,0,0)):
        cpu.reg_write(reg,value)
    cpu.reg_write(UC_MIPS_REG_SP,stack)
    cpu.reg_write(UC_MIPS_REG_RA,stop)
    cpu.mem_write((stack+16)&MASK,struct.pack('<II',0,0))
    screen.draws = []
    cpu.emu_start(0x8004DA34,stop,count=50000)
    assert cpu.reg_read(UC_MIPS_REG_PC)==stop
    assert cpu.reg_read(UC_MIPS_REG_SP)==stack
    return [d for d in screen.draws if d['kind']=='text' and d['y']==123]


def preview(tim,rows):
    import numpy as np
    from PIL import Image
    pix,_ = insert.tim_pixels(tim)
    hf = texpack.HiFont()
    folder = ROOT/'work/ui/unit_stats'
    for hires in (False,True):
        k = 4 if hires else 1
        pages = ([texpack.hires_layers(pix,p,hf,'main' if p==0 else 'ex') for p in (0,1)] if hires else
                 [[pix[:,p*256:(p+1)*256]&3,pix[:,p*256:(p+1)*256]>>2] for p in (0,1)])
        # Original content width x=16..148; each reconstructed row uses 28px.
        dest = np.zeros((112*k,132*k,3),np.uint8)
        dest[:] = (0,48,48)
        for n,row in enumerate(rows):
            for d in row:
                x,y,gold = d['x']-16,6+n*28,False
                for code in d['codes']:
                    if code==0xFF33:
                        gold = True
                        continue
                    if code==0xFF30:
                        gold = False
                        continue
                    w = width(code)
                    if code<320:
                        page,layer,u,v = 0,0,(code%32)*8,(code//32)*16
                    else:
                        page,layer,u,v = texpack.cell_xy(code)
                    cell = pages[page][layer][v*k:(v+16)*k,u*k:(u+w)*k]
                    color = (255,220,40) if gold else (240,240,240)
                    palette = np.array([(0,48,48),(65,65,65),(155,155,155),color],np.uint8)
                    target = dest[y*k:(y+16)*k,x*k:(x+w)*k]
                    assert target.shape[:2]==cell.shape
                    mask = cell>0
                    target[mask] = palette[cell[mask]]
                    x += w
        image = Image.fromarray(dest)
        if not hires:
            image = image.resize((528,448),Image.Resampling.NEAREST)
        image.save(folder/('growth_%s_preview.png'%('4x' if hires else 'native')))


def main():
    version,baseline = sys.argv[1:3]
    out = ROOT/'work/output'
    new,old = [out/('STT2001_EN_v%s.bin'%v) for v in (version,baseline)]
    nd,od = directory(new),directory(old)
    assert nd.keys()==od.keys()
    exe,old_exe = read_file(new,nd['SLPS_028.63']),read_file(old,od['SLPS_028.63'])
    assert exe==growth_layout.patch_exe(old_exe)
    for key in nd.keys()-{'DUMMY.DAT','MAPMAIN.DAT','SLPS_028.63'}:
        assert nd[key]['size']==od[key]['size'] and file_hash(new,nd[key])==file_hash(old,od[key]),key
    a,b = [repack.dat_entries(read_file(p,d['MAPMAIN.DAT'])) for p,d in ((old,od),(new,nd))]
    assert len(a)==len(b) and {i for i,(x,y) in enumerate(zip(a,b)) if x!=y}=={2,24}
    for before,after in ((a[2],b[2]),(cm.blocks(a[24])[1],cm.blocks(b[24])[1])):
        x,y = strings(before),strings(after)
        assert len(x)==len(y)
        assert {i for i,(u,v) in enumerate(zip(x,y)) if u!=v}==set(range(0xB79,0xB7D))
        for i in range(0xB79,0xB7D):
            # Only the space between the two icon/label groups was removed.
            # Greedy bigrams can encode the old trailing space with a letter.
            text = growth_layout.TEXT['U%d'%(20942+i-0xB79)]
            def encoded(s):
                return insert.encode_line_tokens(insert.TOKEN.findall(s),{'{man}':[284],'{sword}':[285]})+[0xFFFE]
            assert x[i]==encoded(text.replace('{sword}',' {sword}'))
            assert y[i]==encoded(text)
    ca,cb = cm.blocks(a[24]),cm.blocks(b[24])
    assert len(ca)==len(cb) and all(x==y for i,(x,y) in enumerate(zip(ca,cb)) if i!=1)
    screen = Screen(exe,b[2])
    db = strings(b[2])
    rows,widths = [],[]
    for unit_id in (0,1):
        for variant in range(4):
            row = run(screen,unit_id,variant)
            assert len(row)==2
            assert row[0]=={'kind':'text','x':18,'y':123,'codes':db[0xB78][:-1]}
            assert row[1]=={'kind':'text','x':56,'y':123,'codes':db[0xB79+variant][:-1]}
            span = sum(width(c) for c in row[1]['codes'])
            assert span in (90,83,83,76) and 56+span<=146
            assert 18+insert.px_of('Grow')==55<56
            if unit_id==0:
                rows.append(row)
                widths.append(span)
    preview(b[7],rows)
    report = {'version':version,'baseline':baseline,'all_checks_passed':True,
              'actual_mips_growth_cases':8,'growth_combinations_verified':4,
              'heading_x':18,'badges_x':56,'badge_widths':widths,'maximum_right':146,
              'content_right_boundary':148,'heading_to_badges_gap':1,
              'labels_icons_and_growth_selection_preserved':True,
              'only_two_executable_positions_changed':True,
              'other_text_fonts_story_movies_unchanged':True,'emulator_verified':False}
    (out/('STT2001_EN_v%s_growth_verification.json'%version)).write_text(json.dumps(report,indent=1)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=1))


if __name__=='__main__':
    main()
