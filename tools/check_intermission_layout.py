"""Execute the actual Intermission caption composer and list/menu interpreters.

Default: dry run on v0.3.16 with the proposed changes in memory. --verify checks
the completed disc, copies the compatible font pack and saves a report/preview.
"""
import json
import shutil
import struct
import sys
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from unicorn.mips_const import UC_MIPS_REG_SP,UC_MIPS_REG_RA,UC_MIPS_REG_PC,UC_MIPS_REG_V0
import cm
import insert
import intermission_layout as FIX
import repack
import texpack
from check_stats_layout import Screen,ARGS,MASK
from check_ui_labels import strings
from check_dialogue_layout import REVERSE,width
from check_graphics_build import directory,read_file,file_hash

ROOT=Path(__file__).resolve().parents[1]
LABELS={0xD87:'<c3>Unit</c>',0xD88:'<c3>Wpn</c>',0xD89:'Grow',0xD8A:'Upg.',0xD9F:'Mecha',0xCF1:' cleared'}


def text(words):
    return ''.join(REVERSE.get(c,str(c-1) if 1<=c<=10 else '{%X}'%c) for c in words if c<0xFF00)


def patch_db(data):
    out=bytearray(data)
    for index,label in LABELS.items():
        struct.pack_into('<H',out,index*2,len(out))
        codes=insert.encode_line_tokens(insert.TOKEN.findall(label),{})+[0xFFFE]
        out+=struct.pack('<%dH'%len(codes),*codes)
    return bytes(out)+bytes((-len(out))%4)


class Intermission(Screen):
    def hook(self,cpu,address,size,unused):
        if address in (0x8004C90C,0x8004BF8C):
            if address==0x8004C90C:
                sp=cpu.reg_read(UC_MIPS_REG_SP)
                pointer=self.word(sp+16)&MASK
                codes=self.read_words(pointer)
                self.draws.append({'kind':'text','x':cpu.reg_read(ARGS[1]),'y':cpu.reg_read(ARGS[2]),'codes':codes})
            cpu.reg_write(UC_MIPS_REG_V0,0)
            cpu.reg_write(UC_MIPS_REG_PC,cpu.reg_read(UC_MIPS_REG_RA))
        else:
            super().hook(cpu,address,size,unused)

    def read_words(self,pointer):
        words=[]
        for i in range(100):
            value=struct.unpack('<H',self.cpu.mem_read((pointer+i*2)&MASK,2))[0]
            if value==0xFFFE:
                return words
            words.append(value)
        raise AssertionError('unterminated caption')

    def call(self,address,args):
        cpu=self.cpu;stack,stop=0x801E0000,0x80008000
        for reg,value in zip(ARGS,args):
            cpu.reg_write(reg,value)
        cpu.reg_write(UC_MIPS_REG_SP,stack);cpu.reg_write(UC_MIPS_REG_RA,stop)
        cpu.mem_write((stack+16)&MASK,bytes(16));self.draws=[]
        cpu.emu_start(address,stop,count=30000)
        assert cpu.reg_read(UC_MIPS_REG_PC)==stop
        assert cpu.reg_read(UC_MIPS_REG_SP)==stack


def tests(exe,db):
    s=Intermission(exe,db);cpu=s.cpu;rows=strings(db)
    stats=Counter();sample=None
    for title in range(91):
        for number in (0,1,9,10,90):
            cpu.mem_write(0x1005A8,bytes([title,number]))
            # Run the actual caller too: a returned RA checks the enlarged buffer.
            s.call(0x80070D14,(0,0,0,0))
            assert len(s.draws)==1
            d=s.draws[0];caption=text(d['codes'])
            prefix='Stage '+(str(number) if number else '--')+': '+text(rows[0xC94+title])
            assert caption in (prefix+' cleared',prefix+' Clr.'),(title,number,caption,prefix)
            assert d['x']==20 and d['y']==200
            span=sum(width(c) for c in d['codes'])
            assert span<=284,(title,number,span,caption)
            assert len(d['codes'])*2+2<=136
            stats['caption_cases']+=1
            stats['maximum_caption_width']=max(stats['maximum_caption_width'],span)
            stats['maximum_caption_bytes']=max(stats['maximum_caption_bytes'],len(d['codes'])*2+2)
            if title==1 and number==1:
                sample=d
    choices={'Grow':0xD89,'Upg.':0xD8A}
    assert all(text(rows[index])==name for name,index in choices.items())
    modes=[]
    for first in ('Grow','Upg.'):
        for second in ('Grow','Upg.'):
            cpu.mem_write(0x1A707C,struct.pack('<4I',choices[first],choices[second],0xFFFFFFFF,0xFFFFFFFF))
            s.call(0x8004AEBC,(20,0x800B2DB4,0,0))
            draws=[d for d in s.draws if d['kind']=='text' and d['y']==144]
            assert [(d['x'],text(d['codes'])) for d in draws]==[(176,'Unit'),(242,'Wpn'),(204,first),(270,second)]
            ordered=sorted(draws,key=lambda d:d['x'])
            ends=[d['x']+sum(width(c) for c in d['codes']) for d in ordered]
            assert all(ends[i]<=ordered[i+1]['x'] for i in range(3)),(ordered,ends)
            assert ends[-1]<=308
            modes.append(draws);stats['mode_cases']+=1
    for script in (0x800B2BE4,0x800B2CE4):
        s.call(0x8004AEBC,(20,script,0,0))
        mecha=[d for d in s.draws if text(d.get('codes',[]))=='Mecha']
        assert len(mecha)==1 and sum(width(c) for c in mecha[0]['codes'])==43
        stats['menu_header_cases']+=1
    return dict(stats),sample,modes


def preview(tim,sample,modes):
    pixels,_=insert.tim_pixels(tim);hf=texpack.HiFont()
    pages=[texpack.hires_layers(pixels,i,hf,'main' if i==0 else 'ex') for i in (0,1)]
    image=Image.new('RGB',(1152,500),(0,48,48));draw=ImageDraw.Draw(image)
    draw.text((16,8),'Intermission fixes - 4x reconstruction, not an emulator capture',fill='white')
    def render(codes,x,y):
        gold=False
        for code in codes:
            if code in (0xFF33,0xFF30):
                gold=code==0xFF33;continue
            if code>=0xFF00:
                continue
            if code<320:
                page,layer,u,v=0,0,(code%32)*8,(code//32)*16
            else:
                page,layer,u,v=texpack.cell_xy(code)
            advance=width(code)
            cell=pages[page][layer][v*4:(v+16)*4,u*4:(u+advance)*4]
            palette=np.array([(0,48,48),(55,55,55),(150,150,150),(255,220,40) if gold else (240,240,240)],np.uint8)
            image.paste(Image.fromarray(palette[cell]),(x*4,y*4));x+=advance
    render(insert.encode_line_tokens(insert.TOKEN.findall('Mecha'),{}),6,10)
    for i,row in enumerate(modes):
        for d in row:
            render(d['codes'],6+d['x']-176,30+i*18)
    render(sample['codes'],6,106)
    image.save(ROOT/'work/ui/intermission/fixed_4x_preview.png')


def main():
    version='0.3.17';baseline='0.3.16';out=ROOT/'work/output'
    old=out/('STT2001_EN_v%s.bin'%baseline);od=directory(old)
    mm=repack.dat_entries(read_file(old,od['MAPMAIN.DAT']))
    oldexe=read_file(old,od['SLPS_028.63'])
    if '--verify' not in sys.argv:
        stats,sample,modes=tests(FIX.patch_exe(oldexe),patch_db(mm[2]))
        print('Dry run passed:',stats,text(sample['codes']))
        return
    new=out/('STT2001_EN_v%s.bin'%version);nd=directory(new)
    exe=read_file(new,nd['SLPS_028.63']);assert exe==FIX.patch_exe(oldexe)
    for key in nd:
        if key not in ('SLPS_028.63','MAPMAIN.DAT','DUMMY.DAT'):
            assert file_hash(new,nd[key])==file_hash(old,od[key]),key
    updated=repack.dat_entries(read_file(new,nd['MAPMAIN.DAT']))
    assert len(mm)==len(updated)
    assert {i for i,(x,y) in enumerate(zip(mm,updated)) if x!=y}=={2,24}
    for before,after in ((mm[2],updated[2]),(cm.blocks(mm[24])[1],cm.blocks(updated[24])[1])):
        a,b=strings(before),strings(after)
        assert len(a)==len(b)
        assert {i for i,(x,y) in enumerate(zip(a,b)) if x!=y}==set(LABELS)
        for index,label in LABELS.items():
            assert b[index]==insert.encode_line_tokens(insert.TOKEN.findall(label),{})+[0xFFFE]
    a,b=cm.blocks(mm[24]),cm.blocks(updated[24])
    assert len(a)==len(b) and all(x==y for i,(x,y) in enumerate(zip(a,b)) if i!=1)
    stats,sample,modes=tests(exe,updated[2]);preview(updated[7],sample,modes)
    src,dst=[out/('STT2001_EN_v%s_4x_font'%v) for v in (baseline,version)]
    shutil.copytree(src,dst,dirs_exist_ok=True)
    names={p.relative_to(src) for p in src.rglob('*') if p.is_file()}
    assert names=={p.relative_to(dst) for p in dst.rglob('*') if p.is_file()}
    assert all((src/n).read_bytes()==(dst/n).read_bytes() for n in names)
    assert not json.loads((out/('STT2001_EN_v%s_report.json'%version)).read_text(encoding='utf-8'))['problems']
    report={'version':version,'baseline':baseline,'all_checks_passed':True,'actual_mips_checks':stats,
            'stage_1_caption':text(sample['codes']),'database_labels':len(LABELS),'same_texture_pack_files':len(names),
            'gameplay_fonts_dialogues_movies_and_other_graphics_unchanged':True,'emulator_verified':False}
    (out/('STT2001_EN_v%s_intermission_verification.json'%version)).write_text(json.dumps(report,indent=1)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=1))


if __name__=='__main__':
    main()
