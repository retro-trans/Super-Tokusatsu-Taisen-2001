"""Render public-save name variables through the real allocator and FT4 writer."""
import argparse,json,struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import efont,mips,repack,texpack
from check_graphics_build import directory,read_file
from check_difficulty_render import Sprites
from check_native_font2x import init,GPU,OT
from runtime_balance import asm
from check_balance import Machine
from unicorn.mips_const import UC_MIPS_REG_A0,UC_MIPS_REG_SP,UC_MIPS_REG_RA,UC_MIPS_REG_PC

ROOT=Path(__file__).resolve().parents[1]
FIELDS=[(0x24e,8),(0x272,5),(0x260,8),(0x27e,5)]


class Names(Sprites):
    def read_words(self,pointer):
        words=[]
        for i in range(200):
            w=self.get(pointer+i*2,'<H')
            if w in (0xff05,0xfffd,0xfffe):return words
            words.append(w)
        raise AssertionError('unterminated name')


def setup(exe,db,names,legacy):
    s=Names(exe,db)
    for (offset,limit),name in zip(FIELDS,names):
        codes=efont.encode_plain(name,{**legacy['encode'],**legacy['encode_ex']})
        assert len(codes)<=limit
        s.cpu.mem_write(0x100000+offset,struct.pack('<%dH'%(limit+1),*(codes+[0xff05]*(limit+1-len(codes)))))
    return s


def draw(s,script,y=74):
    script=script+[0xfffe]
    s.cpu.mem_write(0x143000,struct.pack('<%dH'%len(script),*script))
    # Distinct code addresses avoid Unicorn reusing an earlier immediate Y.
    stub=0x80142000+y*0x100
    code=asm('''addiu $sp,$sp,-32
    sw $ra,28($sp)
    lui $t0,0x8014
    ori $t0,$t0,0x3000
    sw $t0,16($sp)
    sw $zero,20($sp)
    addiu $a0,$zero,18
    addiu $a1,$zero,184
    addiu $a2,$zero,%d
    jal 0x8004a954
    move $a3,$zero
    jal 0x8004bf8c
    addiu $a0,$zero,18
    lw $ra,28($sp)
    addiu $sp,$sp,32
    jr $ra
    nop'''%y,stub)
    s.cpu.mem_write(stub&0x1fffffff,code);s.call(stub,())
    return s.live(18)


def text(s,live,meta):
    reverse={v:k for k,v in {**meta['encode'],**meta['encode_ex']}.items()}
    return ''.join(reverse[s.get(0x800c6c10+r['slot']*36+0x18,'<H')] for r in live)


def preview(old,new,oldmm,mm,legacy,oldmeta,version):
    canvas=Image.new('RGB',(1280,360),(0,48,48));d=ImageDraw.Draw(canvas)
    labels=['v0.3.31 - public save names','v'+version+' - same saved bytes']
    for col,(exe,data,meta) in enumerate([(old,oldmm,oldmeta),(new,mm,legacy)]):
        s=setup(exe,data[2],('Sakomizu','Takuma','','Saki'),legacy)
        d.text((col*640+16,12),labels[col],fill='white')
        # Original raw drawer recursively reads FF01..FF04 saved-name fields.
        init(s.cpu)
        target=struct.unpack_from('<I',exe,mips.off(0x800155f0))[0]&0x3ffffff
        sorter=0x80000000|(target<<2)
        for script,y in [([0xff01,legacy['encode'][' '],0xff02],74),([0xff04],90)]:
            for r in draw(s,script,y):s.call(sorter,(0x800c6c10+r['slot']*36,OT,3))
        end=s.get(0x800d3df0,'<I');raw=bytes(s.cpu.mem_read(GPU&0x1fffffff,end-GPU))
        pixels,_,_,pal=texpack.tim_parts(data[7])
        atlas=(pixels[:,:256]>>2)&3
        for start in range(0,len(raw),40):
            packet=raw[start:start+40];x,y=struct.unpack_from('<hh',packet,8)
            xr=struct.unpack_from('<h',packet,16)[0];u,v,clut=struct.unpack_from('<BBH',packet,12)
            row=(clut>>6)-0xf0
            for yy,xx in zip(*np.nonzero(atlas[v:v+32,u:u+(xr-x)*2])):
                level=int(atlas[v+yy,u+xx]);color=pal[row*16+level*4];rgb=texpack.c15(color)
                left,top=col*640+(x-176)*4+int(xx)*2,(y-64)*4+int(yy)*2+16
                for py in range(top,top+2):
                    for px in range(left,left+2):
                        if 0<=px<1280 and 0<=py<360:
                            bg=canvas.getpixel((px,py));canvas.putpixel((px,py),tuple((a+b)//2 for a,b in zip(bg,rgb)) if color&0x8000 and packet[7]&2 else rgb)
    path=ROOT/'work/ui/font'/('saved-names-v'+version+'.png');canvas.save(path)
    return str(path)


def main():
    p=argparse.ArgumentParser();p.add_argument('--version',default='0.3.32');a=p.parse_args()
    out=ROOT/'work/output';target=out/('STT2001_EN_v'+a.version+'.bin');base=out/'STT2001_EN_v0.3.31.bin'
    exe=read_file(target,directory(target)['SLPS_028.63']);old=read_file(base,directory(base)['SLPS_028.63'])
    mm=repack.dat_entries(read_file(target,directory(target)['MAPMAIN.DAT']))
    oldmm=repack.dat_entries(read_file(base,directory(base)['MAPMAIN.DAT']))
    legacy=json.loads((ROOT/'work/font/encoding.en.json').read_text(encoding='utf-8'))
    meta=json.loads((ROOT/'work/font/efont.json').read_text(encoding='utf-8'))
    oldmeta=json.loads((out/'font-baseline-v0.3.31/efont.json').read_text(encoding='utf-8'))
    assert all(meta[k]==legacy[k] for k in ('uni','bi','ex','encode','encode_ex'))
    examples=[]
    fixtures=[('Sakomizu','Takuma','','Saki'),('Kanou','Eiji','Hinata','Ran'),
              ('Lovelace','Ada','Nova','Kai'),('A-B','Zed','Luna','Faye')]
    for names in fixtures:
        s=setup(exe,mm[2],names,legacy);before=bytes(s.cpu.mem_read(0x100000,0x45a0))
        scripts=[[0xff01],[0xff02],[0xff03],[0xff04],[0xff01,legacy['encode'][' '],0xff02],
                 [0xff03,legacy['encode'][' '],0xff04]]
        expected=list(names)+[names[0]+' '+names[1],names[2]+' '+names[3]]
        for script,want in zip(scripts,expected):
            live=draw(s,script);got=text(s,live,meta);assert got==want,(names,script,got,want)
            assert bytes(s.cpu.mem_read(0x100000,0x45a0))==before
            assert sum(r['width'] for r in live)==sum(meta['widths'][ch] for ch in want)
        # Exercise the real checksum, packer and loader with those old codes.
        m=Machine(exe);c=m.cpu
        for offset,limit in FIELDS:
            c.mem_write(0x100000+offset,before[offset:offset+(limit+1)*2])
        c.mem_write(0x100218,struct.pack('<I',0x424d0002))
        for enemy in range(50):c.mem_write(0x103e6c+enemy*34,b'\xff')
        for address in (0x800428d4,0x80042be4):
            if address==0x80042be4:c.mem_write(0x100000,bytes(0x45a0))
            c.reg_write(UC_MIPS_REG_A0,0x80170000);c.reg_write(UC_MIPS_REG_SP,0x801d0000)
            c.reg_write(UC_MIPS_REG_RA,0x80008000);c.emu_start(address,0x80008000,count=400000)
            assert c.reg_read(UC_MIPS_REG_PC)==0x80008000
        for offset,limit in FIELDS:
            assert bytes(c.mem_read(0x100000+offset,(limit+1)*2))==before[offset:offset+(limit+1)*2]
        assert bytes(c.mem_read(0x100218,4))==struct.pack('<I',0x424d0002)
        examples.append(names)
    bad=setup(old,oldmm[2],fixtures[0],legacy)
    corrupted=text(bad,draw(bad,[0xff01,legacy['encode'][' '],0xff02]),oldmeta)
    assert corrupted!='Sakomizu Takuma' and corrupted.startswith('?AF'),corrupted
    # The original name-entry keyboard stores native 8px letter/digit codes.
    # They must remain native codes rather than being decoded as English tokens.
    keyboard=[177+ord(ch)-65 for ch in 'JUNO']
    keyboard_digits=[1,8]  # 07
    native=setup(exe,mm[2],('','','',''),legacy)
    for offset,limit,codes in [(0x24e,8,keyboard),(0x272,5,keyboard_digits)]:
        native.cpu.mem_write(0x100000+offset,struct.pack('<%dH'%(limit+1),*(codes+[0xff05]*(limit+1-len(codes)))))
    before=bytes(native.cpu.mem_read(0x100000,0x45a0))
    live=draw(native,[0xff01,0xff02])
    assert [native.get(0x800c6c10+r['slot']*36+0x18,'<H') for r in live]==keyboard+keyboard_digits
    assert all(r['width']==8 for r in live)
    assert bytes(native.cpu.mem_read(0x100000,0x45a0))==before
    # Unicorn does not model R3000 load delays; audit the new width routine.
    ins=list(mips.md.disasm(exe[mips.off(0x8004a7d8):mips.off(0x8004a954)],0x8004a7d8))
    for i,j in zip(ins,ins[1:]):
        if i.mnemonic in ('lw','lbu','lhu','lh','lb'):
            reg=i.op_str.split(',')[0]
            assert reg not in j.op_str.split(', ') and '('+reg+')' not in j.op_str,(hex(i.address),i.op_str,j.op_str)
    for index,i in enumerate(ins):
        if i.mnemonic in ('mfhi','mflo'):
            assert not any(j.mnemonic in ('mult','multu','div','divu') for j in ins[index+1:index+3])
    image=preview(old,exe,oldmm,mm,legacy,oldmeta,a.version)
    report={'version':a.version,'public_glyph_codes_exact':True,'name_variable_cases':24,
            'default_and_custom_name_examples':examples,'reported_corruption_reproduced':corrupted,
            'native_recursive_saved_name_draw_executed':True,'player_save_bytes_unchanged':True,
            'native_save_checksum_pack_load_cases':len(fixtures),'difficulty_flag_preserved':True,
            'native_keyboard_name_codes_and_advances_preserved':True,
            'native_widths_and_ps1_delays_checked':True,'preview':image,'emulator_capture':False}
    (out/('STT2001_EN_v'+a.version+'_saved_name_font_verification.json')).write_bytes((json.dumps(report,indent=1)+'\n').encode())
    print(json.dumps(report,indent=1))


if __name__=='__main__':main()
