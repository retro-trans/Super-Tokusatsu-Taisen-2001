"""Reproduce v26 text loss and inspect live native glyph/sprite ownership.

Execute raw text, VWF glyph lookup, positions, reusable allocator, clear and
finalizer. Only hardware/controller and generic engine object registration
are modeled. Checks inspect retained sprites, not just text draw requests.
"""
import argparse
import json
import struct
from pathlib import Path
from unicorn.mips_const import *
import difficulty_render as fix
import repack
import mips
from check_difficulty_menu import Menu, GP, MASK
from check_intermission_layout import text
from check_graphics_build import directory, read_file

ROOT=Path(__file__).resolve().parents[1]


class Sprites(Menu):
    def __init__(self,exe,db):
        self.submits=[]
        self.requests=[]
        super().__init__(exe,db)
        self.cpu.mem_write(0xC6588,bytes(256))
        self.cpu.mem_write(0xC6688,bytes(1024))
        self.cpu.mem_write(0xC6A88,bytes([255])*256)
        self.cpu.mem_write(0xC6C10,bytes(255*36))
        self.put(GP+0x4D8,0)

    def hook(self,cpu,address,size,u):
        if address in (0x8004C90C,0x8004BF8C,0x8004A954):
            if address==0x8004BF8C:
                self.submits.append(cpu.reg_read(UC_MIPS_REG_A0))
            if address==0x8004A954:
                sp=cpu.reg_read(UC_MIPS_REG_SP)
                pointer=self.word(sp+16)&MASK
                self.requests.append({'group':cpu.reg_read(UC_MIPS_REG_A0),
                    'x':cpu.reg_read(UC_MIPS_REG_A1),'y':cpu.reg_read(UC_MIPS_REG_A2),
                    'color':cpu.reg_read(UC_MIPS_REG_A3),
                    'codes':self.read_words(pointer)})
            return  # Execute every text/glyph/sprite routine, including submit.
        if address in (0x80016D3C,0x80016FCC):
            cpu.reg_write(UC_MIPS_REG_V0,128 if address==0x80016FCC else 0)
            cpu.reg_write(UC_MIPS_REG_PC,cpu.reg_read(UC_MIPS_REG_RA))
            return
        return super().hook(cpu,address,size,u)

    def live(self,group):
        result=[]
        for slot in range(255):
            if self.get(0x800C6A88+slot,'<B')!=group:continue
            addr=0x800C6C10+slot*36
            attr=self.get(addr,'<I')
            assert not attr&0x80000000,('retired sprite still owned',slot)
            result.append({'slot':slot,'x':self.get(addr+4),'y':self.get(addr+6),
                           'width':self.get(addr+8), 'height':self.get(addr+10),
                           'tpage':self.get(addr+12,'<H'),
                           'u':self.get(addr+14,'<B'),'v':self.get(addr+15,'<B'),
                           'clut':self.get(addr+18,'<H')})
        return sorted(result,key=lambda s:(s['y'],s['x']))


def tests(old, new, db):
    # The actual old allocator/finalizer reproduces the user's arrow-only
    # screenshot and erased stage caption, despite all draw requests existing.
    bad=Sprites(old,db)
    bad.call(0x8005C430,())
    bad.put(GP+0x552,5);bad.key(0x20)
    previous=bad.live(13)
    assert len(previous)==1 and previous[0]['x']==196 and previous[0]['y']==132,previous
    assert previous[0]['clut']==0xF2  # native color 1: red
    assert len(bad.requests)>10
    assert not any(s['y']==200 for s in previous)

    game=Sprites(new,db)
    game.call(0x8005C430,())
    snapshots=[]
    def check(name, cursor=None, mode='Normal'):
        live=game.live(18)
        footer=game.live(13)
        requests=[r for r in game.requests if r['group']==18]
        # Latest transaction: read backward to its first row label.
        first=max(i for i,r in enumerate(requests) if r['x']==32 and r['y']==136)
        requested=requests[first:]
        assert [text(r['codes']) for r in requested][:2]==['Difficulty','Difficulty']
        assert len(live)==sum(len([c for c in r['codes'] if c<0xff00]) for r in requested)
        for r in requested:
            line=sorted([s for s in live if s['y']==r['y'] and
                         (s['x']<160)==(r['x']<160)],key=lambda s:s['x'])
            if r['y'] in (132,148) and cursor==r['y']:
                line=[s for s in line if s['x']>=208] if r['x']==208 else [s for s in line if s['x']==196]
            assert line and line[0]['x']==r['x'],(name,r,line)
            assert all(s['height']==16 and s['width']>0 for s in line)
        assert footer and all(s['y']==200 for s in footer),(name,footer)
        assert game.submits[-1]==18 and game.submits[-2]==10,game.submits[-8:]
        assert len([s for s in live if s['x']==200 and s['y']==112 and s['clut']==0xF6])==1
        if cursor is not None:
            arrow=[s for s in live if s['x']==196]
            assert len(arrow)==1 and arrow[0]['y']==cursor and arrow[0]['clut']==0xF6
        else:
            assert mode in [text(r['codes']) for r in requested]
            assert not any(s['x']==196 for s in live)
        snapshots.append({'state':name,'difficulty_sprites':live,'footer_sprites':footer,
                          'draw_requests':requested})

    check('initial Normal')
    game.put(GP+0x552,5);game.key(0x20);check('open',132)
    game.key(0x4000);check('choose Gentle',148)
    game.key(0x40);check('cancel keeps Normal')
    game.key(0x20);game.key(0x4000);game.key(0x20);check('applied Gentle',mode='Gentle')
    for _ in range(2):
        game.key(0x20);game.key(0x1000);game.key(0x20)
    check('repeated redraws',mode='Gentle')
    assert len(game.live(18))+len(game.live(13))<150
    return {'old_arrow_only_and_erased_footer_reproduced':True,
            'native_vwf_positions_allocator_and_finalizer_executed':True,
            'difficulty_and_footer_groups_independent':True,
            'normal_gentle_cancel_and_repeated_redraws_checked':True,
            'yellow_clut_verified':True,'sprite_pool_limit':255,
            'emulator_capture':False,'old_retained_sprites':previous,
            'snapshots':snapshots}


def preview(tim, report, version, samples=None):
    """Reconstruct retained glyphs, using actual UV/CLUT/position/size values."""
    import gfx
    import numpy as np
    from PIL import Image,ImageDraw
    pixels=gfx.Tim(tim).idx
    image=Image.new('RGB',(960,256),(28,24,21));brush=ImageDraw.Draw(image)
    if samples is None:samples=[('v0.3.26 - retained text',report['old_retained_sprites']),
        ('v'+version+' - Normal',report['snapshots'][0]['difficulty_sprites']+report['snapshots'][0]['footer_sprites']),
        ('v'+version+' - choosing Gentle',report['snapshots'][2]['difficulty_sprites']+report['snapshots'][2]['footer_sprites'])]
    for col,(title,sprites) in enumerate(samples):
        ox=col*320
        brush.text((ox+8,2),title,fill='white')
        for x,y,w,h in [(22,50,112,108),(192,108,112,84),(16,196,288,24)]:
            brush.rectangle((ox+x,y+16,ox+x+w-1,y+h+15),fill=(0,48,48),outline=(10,12,12))
        brush.rectangle((ox+32,152,ox+127,167),fill=(0,145,0))
        for s in sprites:
            page=s['tpage']-0x1c;layer=s['clut']&1
            u,v,w,h=s['u'],s['v'],s['width'],s['height']
            cell=(pixels[v:v+h,page*256+u:page*256+u+w]>>(layer*2))&3
            color={1:(240,90,100),3:(255,220,40)}.get((s['clut']-0xf0)//2,(245,245,245))
            palette=[(0,0,0),(35,35,35),(154,154,154),color]
            for cy,cx in zip(*np.nonzero(cell)):
                x,y=ox+s['x']+int(cx),s['y']+int(cy)+16
                if 0<=x<960 and 0<=y<256:image.putpixel((x,y),palette[int(cell[cy,cx])])
    ui=ROOT/'work/ui/difficulty';ui.mkdir(parents=True,exist_ok=True)
    image.resize((1920,512),Image.Resampling.NEAREST).save(ui/('retained_sprites_v%s.png'%version))
    if 'stronger_save_checksum_load_roundtrip' not in report:
        (ui/'sprite_layout.en.json').write_text(json.dumps(report,indent=1)+'\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser();p.add_argument('--version',default='0.3.27')
    p.add_argument('--verify',action='store_true');a=p.parse_args()
    old=ROOT/'work/output/STT2001_EN_v0.3.26.bin';d=directory(old)
    before=read_file(old,d['SLPS_028.63'])
    path=ROOT/('work/output/STT2001_EN_v%s.bin'%a.version)
    after=read_file(path,directory(path)['SLPS_028.63']) if a.verify else fix.patch_exe(before)
    assert after==fix.patch_exe(before)
    mm=repack.dat_entries(read_file(old,d['MAPMAIN.DAT']));db=mm[2]
    r=tests(before,after,db);r['version']=a.version
    preview(mm[7],r,a.version)
    dest=path.with_name(path.stem+'_difficulty_render_verification.json')
    dest.write_text(json.dumps(r,indent=1)+'\n',encoding='utf-8')
    print('PASS: '+str(dest))


if __name__=='__main__':main()
