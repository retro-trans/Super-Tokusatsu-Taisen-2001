"""Execute the native glyph marker, token expansion and actual FT4 writer."""
import argparse,json,struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from unicorn.mips_const import *
import native_font2x as N,efont,repack,gfx,texpack,mips
from check_balance import Machine
from check_graphics_build import directory,read_file
from check_difficulty_render import Sprites

ROOT=Path(__file__).resolve().parents[1]
GPU,OT,HEAD,SPRITE=0x801b0000,0x80160000,0x8016100c,0x800c6c10


def init(cpu):
    cpu.reg_write(UC_MIPS_REG_GP,0x800bd0a8)
    for addr,data in [(0xd3df0,struct.pack('<I',GPU)),(0xd3d2c,bytes(4)),(0xbd3e4,bytes(4)),
        (0x160000,struct.pack('<III',0,0x80161000,0)),(0x16100c,struct.pack('<I',0xffffff))]:cpu.mem_write(addr,data)


def palette(tim):return texpack.tim_parts(tim)[3]


def preview(old_exe,new_exe,old_mm,mm,labels,version):
    # Execute the real root renderer and allocator, then draw its retained objects.
    samples=[];meta=json.loads((ROOT/'work/font/efont.json').read_text(encoding='utf-8'))
    for exe,db in ((old_exe,old_mm[2]),(new_exe,mm[2])):
        s=Sprites(exe,db);s.call(0x8005c430,());s.put(0x800bd0a8+0x552,5)
        # Redraw the selected Difficulty row, leaving its saved status visible.
        s.call(0x8005fde0,(22,));samples.append(s)
    canvas=Image.new('RGB',(2560,1024),(25,22,20));d=ImageDraw.Draw(canvas)
    for col,s in enumerate(samples):
        ox=1280*col
        d.text((ox+12,8),'v0.3.30 - reduced bitmap' if col==0 else 'v'+version+' - native 2x atlas / FT4 (no replacement)',fill='white')
        for x,y,w,h in [(112,14,96,20),(22,50,112,112),(192,50,104,66),(192,108,112,84),(16,196,288,24)]:
            d.rectangle((ox+x*4,y*4+32,ox+(x+w)*4-1,(y+h)*4+31),fill=(0,48,48),outline=(120,120,128),width=3)
        d.rectangle((ox+32*4,136*4+32,ox+128*4-1,152*4+31),fill=(0,145,0))
        if col==0:
            pix=gfx.Tim(old_mm[7]).idx;pal=palette(old_mm[7])
            for slot in range(255):
                addr=SPRITE+slot*36
                if s.get(0x800c6a88+slot,'<B')==255 or s.get(addr,'<I')&0x80000000:continue
                x,y,w,h=[s.get(addr+i) for i in (4,6,8,10)]
                page=s.get(addr+12,'<H')-0x1c;u=s.get(addr+14,'<B');v=s.get(addr+15,'<B');cy=s.get(addr+18,'<H')
                if page not in (0,1):continue
                levels=(pix[v:v+h,page*256+u:page*256+u+w]>>(2*(cy&1)))&3
                for yy,xx in zip(*np.nonzero(levels)):
                    color=texpack.c15(pal[(cy-0xf0)*16+int(levels[yy,xx])*(4 if cy&1 else 1)])
                    d.rectangle((ox+(x+int(xx))*4,(y+int(yy))*4+32,ox+(x+int(xx)+1)*4-1,(y+int(yy)+1)*4+31),fill=color)
        else:
            init(s.cpu)
            for slot in range(255):
                addr=SPRITE+slot*36
                if s.get(0x800c6a88+slot,'<B')==255 or s.get(addr,'<I')&0x80000000:continue
                s.call(labels['draw'],(addr,OT,3))
            end=s.get(0x800d3df0,'<I');raw=bytes(s.cpu.mem_read(GPU&0x1fffffff,end-GPU))
            assert len(raw)%40==0
            pal=palette(mm[7]);atlas=N.assets()[0]
            for start in range(0,len(raw),40):
                packet=raw[start:start+40];x,y=struct.unpack_from('<hh',packet,8);xr=struct.unpack_from('<h',packet,16)[0]
                u,v,clut=struct.unpack_from('<BBH',packet,12);width=(xr-x)*2;row=(clut>>6)-0xf0
                for yy,xx in zip(*np.nonzero(atlas[v:v+32,u:u+width])):
                    level=int(atlas[v+yy,u+xx]);color=pal[row*16+level*4];rgb=texpack.c15(color)
                    left,top=ox+x*4+int(xx)*2,y*4+int(yy)*2+32
                    for py in range(top,top+2):
                        for px in range(left,left+2):
                            if not (0<=px<2560 and 0<=py<1024):continue
                            bg=canvas.getpixel((px,py));canvas.putpixel((px,py),tuple((a+b)//2 for a,b in zip(bg,rgb)) if color&0x8000 and packet[7]&2 else rgb)
    ui=ROOT/'work/ui/font';ui.mkdir(exist_ok=True,parents=True)
    target=ui/('native-2x-menu-v'+version+'.png');canvas.save(target)
    return str(target)


def main():
    p=argparse.ArgumentParser();p.add_argument('--version',default='0.3.31');p.add_argument('--verify',action='store_true');a=p.parse_args()
    out=ROOT/'work/output';base=out/'STT2001_EN_v0.3.30.bin';old=read_file(base,directory(base)['SLPS_028.63'])
    candidate,info=N.patch_exe(old,True,transition_clip=tuple(map(int,a.version.split('.'))) >= (0,3,34),native_ui=tuple(map(int,a.version.split('.'))) >= (0,3,35));labels={k:int(v,16) for k,v in info['labels'].items()}
    target=out/('STT2001_EN_v'+a.version+'.bin')
    exe=read_file(target,directory(target)['SLPS_028.63']) if a.verify else candidate
    for start,end in [(N.A,N.LIMIT_A),(N.I,N.I+96),(N.B,N.LIMIT_B)]:
        assert exe[mips.off(start):mips.off(end)]==candidate[mips.off(start):mips.off(end)]
    for start,size in [(0x8004a7d8,8),(0x800155f0,4)]:
        assert exe[mips.off(start):mips.off(start)+size]==candidate[mips.off(start):mips.off(start)+size]
    m=Machine(exe);c=m.cpu;meta=json.loads((ROOT/'work/font/efont.json').read_text(encoding='utf-8'))
    glyphs={**meta['encode'],**meta['encode_ex']};packets=0
    regs=[UC_MIPS_REG_S0+i for i in range(8)]
    for token,code in glyphs.items():
        m.run(labels['token'],code,0x80150000)
        ptr=c.reg_read(UC_MIPS_REG_V0)&0x1fffffff;count=c.reg_read(UC_MIPS_REG_V1)
        assert ''.join(meta['uni'][i] for i in c.mem_read(ptr,count))==token
        m.run(0x8004a7d8,SPRITE,code)
        assert c.reg_read(UC_MIPS_REG_A1)==code
        assert struct.unpack('<H',c.mem_read(0xc6c2a,2))[0]==N.MAGIC
        init(c);c.mem_write(0xc6c14,struct.pack('<hh',10,20));c.mem_write(0xc6c24,b'\x80'*3)
        values=[0x12340000+i for i in range(8)]
        for reg,value in zip(regs,values):c.reg_write(reg,value)
        c.reg_write(UC_MIPS_REG_HI,0x12345678);c.reg_write(UC_MIPS_REG_LO,0x87654321)
        m.run(labels['draw'],SPRITE,OT,3)
        assert [c.reg_read(r) for r in regs]==values
        assert c.reg_read(UC_MIPS_REG_HI)==0x12345678 and c.reg_read(UC_MIPS_REG_LO)==0x87654321
        end=struct.unpack('<I',c.mem_read(0xd3df0,4))[0];assert end-GPU==len(token)*40
        x=10
        for i,ch in enumerate(token):
            packet=bytes(c.mem_read((GPU&0x1fffffff)+i*40,40));assert packet[7]==(0x2c if info['native_ui_compatibility'] else 0x2e) and packet[3]==9
            assert struct.unpack_from('<hh',packet,8)==(x,20)
            assert struct.unpack_from('<hh',packet,16)==(x+meta['widths'][ch],20)
            assert struct.unpack_from('<hh',packet,24)==(x,36)
            index=meta['uni'].index(ch);u,v=N.assets()[1][index*2:index*2+2];v&=0xe0
            assert packet[12:14]==bytes([u,v]) and packet[20:22]==bytes([u+2*meta['widths'][ch],v])
            x+=meta['widths'][ch];packets+=1
    # Native fixed-width values and D/I keep their original slot advances.
    import ui_value_font
    native={**ui_value_font.CODES,277:'D',278:'I'}
    for code,ch in native.items():
        m.run(labels['token'],code,0x80150000)
        ptr=c.reg_read(UC_MIPS_REG_V0)&0x1fffffff
        assert c.reg_read(UC_MIPS_REG_V1)==1 and meta['uni'][c.mem_read(ptr,1)[0]]==ch
        m.run(0x8004a7d8,SPRITE,code);init(c)
        c.mem_write(0xc6c14,struct.pack('<hh',10,20))
        m.run(labels['draw'],SPRITE,OT,3)
        packet=bytes(c.mem_read(GPU&0x1fffffff,40))
        w=meta['widths'][ch];slot=struct.unpack('<h',c.mem_read(0xc6c18,2))[0]
        left=10+(slot-w)//2
        assert struct.unpack_from('<hh',packet,8)==(left,20)
        assert struct.unpack_from('<hh',packet,16)==(left+w,20)
    # Fill every retained slot with the longest token, checking the shared OT.
    longest=max(glyphs,key=len);init(c)
    for slot in range(255):
        addr=SPRITE+slot*36;m.run(0x8004a7d8,addr,glyphs[longest])
        c.mem_write((addr&0x1fffffff)+4,struct.pack('<hh',10,20))
        m.run(labels['draw'],addr,OT,3)
    stress_packets=255*len(longest)
    end=struct.unpack('<I',c.mem_read(0xd3df0,4))[0]
    assert end-GPU==stress_packets*40 and end<GPU+0x18000
    link=struct.unpack('<I',c.mem_read(HEAD&0x1fffffff,4))[0];seen=set()
    while link!=0xffffff:
        assert GPU&0xffffff<=link<(end&0xffffff) and link not in seen
        seen.add(link);tag=struct.unpack('<I',c.mem_read(link,4))[0]
        assert tag>>24==9;link=tag&0xffffff
    assert len(seen)==stress_packets
    # Fallback, retired-object handling and the bounded shared packet buffer.
    init(c);m.run(0x8004a7d8,SPRITE,0);m.run(labels['draw'],SPRITE,OT,3)
    assert struct.unpack('<I',c.mem_read(0xd3df0,4))[0]-GPU==24
    init(c);m.run(0x8004a7d8,SPRITE,meta['encode']['A']);c.mem_write(0xc6c10,struct.pack('<I',0x80000000))
    m.run(labels['draw'],SPRITE,OT,3);assert struct.unpack('<I',c.mem_read(0xd3df0,4))[0]==GPU
    hidden_cases=0
    if info['native_transition_clipping']:
        for code in (meta['encode']['A'],glyphs[longest],277):
            for offset in (8,10):
                init(c);m.run(0x8004a7d8,SPRITE,code)
                c.mem_write((SPRITE&0x1fffffff)+offset,bytes(2))
                m.run(labels['draw'],SPRITE,OT,3)
                assert struct.unpack('<I',c.mem_read(0xd3df0,4))[0]==GPU
                hidden_cases+=1
    init(c);m.run(0x8004a7d8,SPRITE,meta['encode']['A']);c.mem_write(0xd3df0,struct.pack('<I',GPU+0x18000))
    before=bytes(c.mem_read((GPU&0x1fffffff)+0x18000,64));m.run(labels['draw'],SPRITE,OT,3)
    assert bytes(c.mem_read((GPU&0x1fffffff)+0x18000,64))==before
    oldmm=repack.dat_entries(read_file(base,directory(base)['MAPMAIN.DAT']))
    if a.verify:mm=repack.dat_entries(read_file(target,directory(target)['MAPMAIN.DAT']))
    else:mm=list(oldmm);mm[7]=N.patch_tim(mm[7],native_ui=info['native_ui_compatibility'])
    assert np.array_equal((gfx.Tim(mm[7]).idx[:,:256]>>2)&3,N.assets()[0])
    oldpix=gfx.Tim(oldmm[7]).idx;newpix=gfx.Tim(mm[7]).idx
    keep=np.ones(oldpix.shape,dtype=bool)
    if meta.get('stable_encoding'):
        # Restoring public code order deliberately moves the English F0 cells.
        # check_rayblade_font independently checks every moved cell's source.
        for code in list(range(320,446))+efont.EX_SLOTS:
            page,_,x,y=texpack.cell_xy(code);x+=page*256
            keep[y:y+16,x:x+(24 if code in efont.EX_SLOTS else 12)]=False
    assert np.array_equal((oldpix&3)[keep],(newpix&3)[keep])
    oldpal=palette(oldmm[7]);newpal=palette(mm[7])
    for row in range(len(newpal)//16):
        colors=newpal[row*16:row*16+16]
        if row%2==0:assert np.array_equal(colors,oldpal[row*16:row*16+16])
        elif info['native_ui_compatibility']:
            assert np.array_equal(colors,oldpal[row*16:row*16+16])
        elif colors[12]:
            assert colors[4]&0x8000 and not colors[8]&0x8000 and colors[8]==colors[12]
    image=preview(old,exe,oldmm,mm,labels,a.version)
    report={'version':a.version,'token_cases':len(glyphs),'native_ft4_packets_checked':packets,
        'callee_saved_registers_and_hi_lo_preserved':True,'nonfont_sprite_fallback_checked':True,
        'native_fixed_width_cases':len(native),'full_pool_stress_packets':stress_packets,
        'full_pool_ordering_table_checked':True,'native_shared_palettes_checked':info['native_ui_compatibility'],
        'faint_edge_and_opaque_ink_palettes_checked':not info['native_ui_compatibility'],
        'retired_and_packet_limit_checked':True,'original_vram_extent_preserved':True,
        'zero_width_and_height_cases':hidden_cases,
        'preview':image,'emulator_capture':False,'implementation':info}
    (out/('STT2001_EN_v'+a.version+'_native_2x_verification.json')).write_bytes((json.dumps(report,indent=1)+'\n').encode())
    print(json.dumps(report,indent=1))


if __name__=='__main__':main()
