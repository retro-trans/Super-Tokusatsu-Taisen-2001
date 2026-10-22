"""Run the actual save/load renderer, numeric drawer and measured captions."""
import argparse
import json
import shutil
import struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from unicorn.mips_const import *
import gfx
import mips
import repack
import save_slot_layout as FIX
import texpack
from check_stats_layout import Screen,ARGS,MASK
from check_intermission_layout import text
from check_dialogue_layout import width
from check_ui_labels import strings
from check_graphics_build import directory,read_file,file_hash

ROOT=Path(__file__).resolve().parents[1]


class Slots(Screen):
    def hook(self,c,address,size,unused):
        if address==0x8004ccf0:
            return # Execute the native numeric formatter, not a string model.
        if address==0x8004c0ec:
            c.reg_write(UC_MIPS_REG_V0,0x801a0000)
        elif address==0x8004a7d8:
            if c.reg_read(UC_MIPS_REG_A0)==0x801a0000:
                self.digit=c.reg_read(UC_MIPS_REG_A1)
            return # Native glyph lookup and VWF advance execute unchanged.
        elif address==0x8004d834:
            if c.reg_read(UC_MIPS_REG_A0)==0x801a0000:
                x,y=[struct.unpack('<h',c.mem_read(c.reg_read(r)&MASK,2))[0] for r in (UC_MIPS_REG_A1,UC_MIPS_REG_A2)]
                self.draws.append({'kind':'digit','x':x,'y':y,'codes':[self.digit]})
            return
        elif address in (0x8004ac24,0x8004bf8c,0x8004cad8):
            c.reg_write(UC_MIPS_REG_V0,0)
        else:
            super().hook(c,address,size,unused)
            return
        c.reg_write(UC_MIPS_REG_PC,c.reg_read(UC_MIPS_REG_RA))

    def call(self,address,args):
        c=self.cpu
        for r,v in zip(ARGS,args):
            c.reg_write(r,v&0xffffffff)
        c.reg_write(UC_MIPS_REG_SP,0x801e0000)
        c.reg_write(UC_MIPS_REG_RA,0x80008000)
        self.draws=[]
        c.emu_start(address,0x80008000,count=400000)
        assert c.reg_read(UC_MIPS_REG_PC)==0x80008000,hex(c.reg_read(UC_MIPS_REG_PC))
        assert c.reg_read(UC_MIPS_REG_SP)==0x801e0000
        return list(self.draws)


def record(portrait,title,number,turns,total,active=0):
    data=bytearray(24)
    struct.pack_into('<6h',data,0,portrait,title-1,number,total,turns,0)
    struct.pack_into('<hhI',data,16,active,title-1,3105*60)
    return bytes(data)


def tests(original,exe,db):
    old,new=Slots(original,db),Slots(exe,db)
    # Reproduce the user's two reported captions and empty third slot.
    reports=[]
    fixture=record(0,1,1,4,3)+record(0,3,1,1,3,1)+struct.pack('<h',-1)+bytes(22)
    for screen in (old,new):
        screen.cpu.mem_write(0x120000,fixture)
        reports.append(screen.call(0x800493b8,(0,)))
    captions=[d for d in reports[1] if d['kind']=='text' and d['y'] in (96,136)]
    assert [text(d['codes']) for d in captions]==['Stage 1: Fell to Earth cleared',"Stage 2: Shocker's Plot"],[text(d['codes']) for d in captions]
    # Footers include distinct labels, with numeric glyphs outside each span.
    for y in (112,152):
        row=[d for d in reports[1] if d['y']==y]
        assert any(d['x']==148 and text(d['codes'])=='Turn' for d in row)
        assert any(d['x']==224 and text(d['codes'])=='Total' for d in row)
        for d in row:
            end=d['x']+sum(map(width,d['codes']))
            if d['kind']=='digit' and d['x']>=144:
                assert 184<=d['x']<216 or 268<=d['x']<300,(d,end)
    assert new.cpu.mem_read(0x120000,len(fixture))==fixture
    rows=strings(db);checked=0;truncated=0;max_width=0
    # Every chapter title, both progress states, multiple stage-number widths
    # and save-page row origins. Use the real shared renderer for every case.
    for title in range(91):
        for active in (0,1):
            for number in (0,1,9,10,99,255):
                data=b''.join(record(0,title,number,9999,9999,active) for _ in range(3))
                new.cpu.mem_write(0x120000,data)
                drawn=new.call(0x800493b8,(0,))
                headers=[d for d in drawn if d['kind']=='text' and d['y'] in (96,136,176)]
                assert len(headers)==3
                for d in headers:
                    value=text(d['codes'])
                    assert value.startswith('Stage %d: '%(number+active)),(title,value)
                    assert len(d['codes'])<64
                    w=sum(map(width,d['codes']));max_width=max(w,max_width)
                    assert d['x']==64 and w<=244,(title,value,w)
                    if active==0:
                        assert value.endswith((' cleared',' Clr.')),(title,value)
                    if '...' in value:
                        truncated+=1
                for d in drawn:
                    if d['y'] in (112,152,192) and d['kind']=='digit' and d['x']>=144:
                        assert 184<=d['x']<216 or 268<=d['x']<300,d
                assert new.cpu.mem_read(0x120000,len(data))==data
                checked+=1
    # A page starting later in the slot list and the one-slot quick-load view.
    new.cpu.mem_write(0x120000,fixture*5)
    for start,expected in ((-1,1),(0,2),(3,2),(6,2),(9,2),(12,2)):
        drawn=new.call(0x800493b8,(start,))
        headers=[d for d in drawn if d['kind']=='text' and text(d['codes']).startswith('Stage ')]
        assert len(headers)==expected,(start,headers)
    # All injected code must observe PS1 load and HI/LO result delays.
    _,info=FIX.patch_exe(original,True)
    start=int(info['labels']['measure'],16);end=int(info['code_end'],16)
    ins=list(mips.md.disasm(exe[mips.off(start):mips.off(end)],start))
    for index,i in enumerate(ins[:-1]):
        j=ins[index+1]
        if i.mnemonic in ('lw','lhu','lh','lb','lbu'):
            reg=i.op_str.split(',')[0]
            assert reg not in j.op_str.split(', ') and '('+reg+')' not in j.op_str,(hex(i.address),i.op_str,j.op_str)
        if i.mnemonic in ('mflo','mfhi'):
            assert not any(j.mnemonic in ('mult','multu','div','divu') for j in ins[index+1:index+3]),hex(i.address)
    return {'all_chapter_titles':91,'native_three_slot_cases':checked,
            'native_header_draws':checked*3,'additional_page_cases':6,
            'maximum_header_width':max_width,'ellipsis_cases':truncated,
            'native_numeric_drawer_executed':True,'save_metadata_unchanged':True,
            'original_report_captions':[text(d['codes']) for d in captions],
            'ps1_load_and_hi_lo_delays_checked':True,
            'emulator_capture':False},reports


def preview(tim,reports,version):
    pixels=gfx.Tim(tim).idx
    image=Image.new('RGB',(640,240),(20,25,29));draw=ImageDraw.Draw(image)
    for col,report in enumerate(reports):
        origin=col*320
        draw.text((origin+16,12),'Before' if col==0 else 'v'+version+' - native font reconstruction',fill='white')
        for row in range(3):
            y=92+row*40
            draw.rectangle((origin+20,y,origin+308,y+39),fill=(53,43,34),outline=(135,135,148))
        for item in report:
            x,y=origin+item['x'],item['y']
            for code in item['codes']:
                if code>=0xff00:
                    continue
                if code<320:
                    page,layer,u,v=0,0,code%32*8,code//32*16
                else:
                    page,layer,u,v=texpack.cell_xy(code)
                advance=width(code)
                cell=(pixels[v:v+16,page*256+u:page*256+u+advance]>>(layer*2))&3
                pal=[(0,0,0),(35,35,35),(154,154,154),(245,245,245)]
                for cy,cx in zip(*np.nonzero(cell)):
                    if 0<=x+int(cx)<640 and 0<=y+int(cy)<240:
                        image.putpixel((x+int(cx),y+int(cy)),pal[int(cell[cy,cx])])
                x+=advance
    ui=ROOT/'work/ui/save_slots';ui.mkdir(parents=True,exist_ok=True)
    image.resize((1280,480),Image.Resampling.NEAREST).save(ui/('comparison_v%s.png'%version))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',default='0.3.25')
    parser.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    out=ROOT/'work/output';old=out/'STT2001_EN_v0.3.24.bin';od=directory(old)
    original=read_file(old,od['SLPS_028.63'])
    mm=repack.dat_entries(read_file(old,od['MAPMAIN.DAT']))
    proposed=FIX.patch_exe(original)
    if tuple(map(int,args.version.split('.'))) >= (0,3,26):
        import difficulty_menu
        proposed=difficulty_menu.patch_exe(proposed)
    if tuple(map(int,args.version.split('.'))) >= (0,3,27):
        import difficulty_render
        proposed=difficulty_render.patch_exe(proposed)
    target=out/('STT2001_EN_v%s.bin'%args.version)
    exe=read_file(target,directory(target)['SLPS_028.63']) if args.verify else proposed
    assert exe==proposed
    report,reports=tests(original,exe,mm[2])
    print(json.dumps(report,indent=1),flush=True)
    if not args.verify:
        print('In-memory checks only; completed-disc validation uses --verify.')
        return
    nd=directory(target)
    for name in nd.keys()-{'SLPS_028.63','MAPMAIN.DAT','DUMMY.DAT'}:
        assert file_hash(old,od[name])==file_hash(target,nd[name]),name
    preview(mm[7],reports,args.version)
    report['version']=args.version
    report['baseline']='0.3.24'
    (out/('STT2001_EN_v%s_save_slot_verification.json'%args.version)).write_text(json.dumps(report,indent=1)+'\n',encoding='utf-8')
    ui=ROOT/'work/ui/save_slots'
    (ui/'layout.en.json').write_text(json.dumps({'version':args.version,'rows_y':[96,136,176],
        'header_x':64,'header_width':244,'turn_label_x':148,'turn_value_x':184,
        'total_label_x':224,'total_value_x':268,'numeric_digits':4,'source_report':'reported.png',
        'preview_is_reconstruction':True,'report_example':reports[1]},indent=1)+'\n',encoding='utf-8')
    source=Path('C:/Users/Binh/AppData/Local/Temp/codex-clipboard-1f4a907f-a43c-4185-99ee-32d0546efd7e.png')
    if source.exists() and not (ui/'reported.png').exists():
        shutil.copy2(source,ui/'reported.png')


if __name__=='__main__':
    main()
