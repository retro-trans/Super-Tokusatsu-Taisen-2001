"""Execute actual root-menu initialization, input driver and full renderer."""
import argparse
import json
import struct
from pathlib import Path
from unicorn.mips_const import *
import difficulty_menu as fix
import mips
import repack
from check_graphics_build import directory, read_file
from check_intermission_layout import Intermission, text
from check_dialogue_layout import width

ROOT = Path(__file__).resolve().parents[1]
MASK = 0x1fffffff
GP = 0x800BD0A8


class Menu(Intermission):
    def __init__(self, exe, db):
        self.pressed = self.held = 0
        self.path = []
        super().__init__(exe, db)
        self.cpu.reg_write(UC_MIPS_REG_GP, GP)
        self.put(GP+0x1B8,0x801A7000,'<I')
        self.put(0x800CC5F8,22)
        self.put(GP+0x5AC,255)
        self.put(GP+0x20C,1,'<B')
        self.put(0x801005A8,1,'<B')
        self.put(0x801005A9,1,'<B')
        self.put(0x8010022C,26755,'<I')
        self.put(0x80100234,16650,'<I')
        self.put(0x8010024A,3)
        # Empty rosters; the native eligibility scan still executes.
        for i in range(200):
            self.put(0x80101568+i*50,255,'<B')

    def put(self,a,v,fmt='<h'):
        self.cpu.mem_write(a&MASK,struct.pack(fmt,v))

    def get(self,a,fmt='<h'):
        return struct.unpack(fmt,self.cpu.mem_read(a&MASK,struct.calcsize(fmt)))[0]

    def call(self,address,args):
        from check_stats_layout import ARGS
        for reg,value in zip(ARGS,args):
            self.cpu.reg_write(reg,value)
        self.cpu.reg_write(UC_MIPS_REG_SP,0x801E0000)
        self.cpu.reg_write(UC_MIPS_REG_RA,0x80008000)
        self.cpu.mem_write(0x1E0010,bytes(16));self.draws=[]
        self.cpu.emu_start(address,0x80008000,count=500000)
        assert self.cpu.reg_read(UC_MIPS_REG_PC)==0x80008000,hex(self.cpu.reg_read(UC_MIPS_REG_PC))
        assert self.cpu.reg_read(UC_MIPS_REG_SP)==0x801E0000

    def hook(self,cpu,address,size,u):
        if address in (0x80094340,0x800942EC):
            cpu.reg_write(UC_MIPS_REG_V0,self.pressed if address==0x80094340 else self.held)
        elif address in (0x80016D6C,0x8001761C):
            cpu.reg_write(UC_MIPS_REG_V0,0x801A0000)
        elif address in (0x8001447C,0x80016E24,0x800422CC,0x80042288,0x80041F04):
            cpu.reg_write(UC_MIPS_REG_V0,0)
        else:
            if address in (0x8005CC00,0x8005D7A4,0x80061090,0x800627BC):
                self.path.append(hex(address))
            return super().hook(cpu,address,size,u)
        cpu.reg_write(UC_MIPS_REG_PC,cpu.reg_read(UC_MIPS_REG_RA))

    def key(self,pressed,held=None):
        self.pressed=pressed;self.held=pressed if held is None else held
        self.call(0x8005CAD4,())
        return self.cpu.reg_read(UC_MIPS_REG_V0)


def tests(exe, db):
    _,info=fix.patch_exe(exe,True)
    pending=int(info['pending_choice'],16)
    # Derive root state from the native type-6 entry, and identify its script
    # by the actual title/catalog IDs. This avoids the old state-0 assumption.
    state=exe[mips.off(0x800B1EEC+6*6)]
    assert state==22
    script_index=exe[mips.off(0x800B3890+state)]
    script=struct.unpack_from('<I',exe,mips.off(0x800B37D4+script_index*4))[0]
    assert script==0x800B2AD4
    assert struct.unpack_from('<H',exe,mips.off(script+8))[0]==0xB0A
    assert struct.unpack_from('<H',exe,mips.off(script+24))[0]==0xD98
    m=Menu(exe,db)
    m.call(0x8005C430,())  # actual config setup plus native root render
    labels=[text(d['codes']) for d in m.draws if d['kind']=='text']
    assert 'Intermission' in labels and 'M.Card' in labels,labels
    assert labels.count('Difficulty')==2 and 'Normal' in labels,labels
    assert '0x80061090' in m.path and '0x800627bc' in m.path
    examples=[{'mode':'Normal','pending':0,'draws':list(m.draws)}]
    assert m.get(0x800CC644)==6
    # Every original row still reaches the native dispatch. No Select toggles.
    for row in range(5):
        m.put(GP+0x552,row)
        m.key(0x100)
        assert not m.get(0x80100218,'<I') and not m.get(pending,'<I')
    m.put(GP+0x552,0)
    for expected in (1,2,3,4,5,0):
        m.key(0x4000)
        assert m.get(GP+0x552)==expected,(expected,m.get(GP+0x552))
    m.key(0x1000)
    assert m.get(GP+0x552)==5
    # Entering never changes the saved mode. Held confirm never repeats.
    assert m.key(0x20)==0
    assert m.get(pending,'<I')==1 and m.get(0x80100218,'<I')==0
    assert any(text(d.get('codes',[]))=='>' and d['y']==132 for d in m.draws)
    for _ in range(30):
        m.key(0,0x20)
        assert m.get(pending,'<I')==1 and m.get(0x80100218,'<I')==0
    m.key(0x4000)
    assert m.get(pending,'<I')==2
    examples.append({'mode':'Normal','pending':2,'draws':list(m.draws)})
    assert any(text(d.get('codes',[]))=='>' and d['y']==148 for d in m.draws)
    m.key(0x40)  # cancel discards pending choice
    assert m.get(pending,'<I')==0 and m.get(0x80100218,'<I')==0
    assert 'Normal' in [text(d.get('codes',[])) for d in m.draws]
    m.key(0x20);m.key(0x2000);m.key(0x20)
    assert m.get(pending,'<I')==0 and m.get(0x80100218,'<I')==fix.rb.MAGIC
    labels=[text(d.get('codes',[])) for d in m.draws]
    assert 'Gentle' in labels and 'Normal' not in labels,labels
    examples.append({'mode':'Gentle','pending':0,'draws':list(m.draws)})
    m.key(0,0x20)  # held confirm after applying must not reopen
    assert not m.get(pending,'<I')
    m.key(0x20)
    assert m.get(pending,'<I')==2
    m.key(0x1000);m.key(0x20)
    assert m.get(0x80100218,'<I')==0
    # Original confirm actions still return the same native result for the
    # non-disabled root rows; R&D native disabled behavior is retained.
    for row in (0,1,3,4):
        m.put(GP+0x552,row)
        assert m.key(0x20)==2,(row,m.cpu.reg_read(UC_MIPS_REG_V0))
        assert m.get(GP+0x552)==row and m.get(0x800CC5F8)==22
    for sample in examples:
        for d in sample['draws']:
            if d['kind']=='text' and d['x']>=192 and d['y']>=108:
                w=sum(width(c) for c in d['codes'])
                assert d['x']+w<=304 and d['y']+16<=192,d
    # The native frame descriptor is data, not a mock of the new geometry.
    frames=struct.unpack_from('<I',exe,mips.off(0x800A9A98+29*8+4))[0]
    assert struct.unpack_from('<6H',exe,mips.off(frames+24))==(0xFC,22,50,26,111,107)
    assert struct.unpack_from('<6H',exe,mips.off(frames+96))==(0xFC,192,108,26,111,83)
    return {'native_root_state_and_script_checked':True,
            'native_config_input_navigation_and_full_render_checked':True,
            'confirm_cancel_and_held_input_checked':True,
            'six_rows_wrap_and_original_confirm_actions_checked':True,
            'current_mode_and_pending_cursor_checked':True,
            'emulator_capture':False,'examples':examples,'patch':info}


def preview(tim, report, version):
    """Layout reconstruction using captured draws and completed native glyphs."""
    import numpy as np
    from PIL import Image,ImageDraw
    import gfx,texpack
    pixels=gfx.Tim(tim).idx
    image=Image.new('RGB',(640,256),(28,24,21));brush=ImageDraw.Draw(image)
    for col,sample in enumerate((report['examples'][2],report['examples'][1])):
        ox=col*320
        brush.text((ox+8,2),'Current mode' if col==0 else 'Choosing a mode',fill='white')
        for x,y,w,h in [(112,22,96,20),(22,50,112,108),(192,48,104,64),
                         (192,108,112,84),(16,196,288,24)]:
            brush.rectangle((ox+x,y+16,ox+x+w-1,y+16+h-1),fill=(0,48,48),outline=(10,12,12))
        brush.rectangle((ox+32,136+16,ox+127,151+16),fill=(0,145,0))
        for item in sample['draws']:
            if item['kind']!='text':continue
            x,y=ox+item['x'],item['y']+16
            gold=(item['y']==112 and item['x']==200) or text(item['codes'])=='>'
            for code in item['codes']:
                if code>=0xff00:continue
                if code<320:page,layer,u,v=0,0,code%32*8,code//32*16
                else:page,layer,u,v=texpack.cell_xy(code)
                advance=width(code)
                cell=(pixels[v:v+16,page*256+u:page*256+u+advance]>>(layer*2))&3
                pal=[(0,0,0),(35,35,35),(154,154,154),(255,220,40) if gold else (245,245,245)]
                for cy,cx in zip(*np.nonzero(cell)):
                    if 0<=x+int(cx)<640 and 0<=y+int(cy)<256:
                        image.putpixel((x+int(cx),y+int(cy)),pal[int(cell[cy,cx])])
                x+=advance
    ui=ROOT/'work/ui/difficulty';ui.mkdir(parents=True,exist_ok=True)
    image.resize((1280,512),Image.Resampling.NEAREST).save(ui/('layout_v%s.png'%version))
    (ui/'layout.en.json').write_text(json.dumps(report,indent=1)+'\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser();p.add_argument('--version',default='0.3.26')
    p.add_argument('--verify',action='store_true');args=p.parse_args()
    path=ROOT/('work/output/STT2001_EN_v%s.bin'%args.version)
    base=path if args.verify else ROOT/'work/output/STT2001_EN_v0.3.25.bin'
    d=directory(base);exe=read_file(base,d['SLPS_028.63'])
    if not args.verify:exe=fix.patch_exe(exe)
    mm=repack.dat_entries(read_file(base,d['MAPMAIN.DAT']))
    result=tests(exe,mm[2]);result['version']=args.version
    preview(mm[7],result,args.version)
    dest=path.with_name(path.stem+'_difficulty_verification.json')
    dest.write_text(json.dumps(result,indent=1)+'\n',encoding='utf-8')
    print('PASS: '+str(dest))


if __name__=='__main__':main()
