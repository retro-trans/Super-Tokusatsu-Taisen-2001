"""Execute native dialogue clear/crop frames and inspect actual font packets."""
import argparse,json,struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from unicorn.mips_const import UC_MIPS_REG_V1
import efont,mips,native_font2x as N,repack,texpack
from runtime_balance import asm
from check_difficulty_render import Sprites
from check_graphics_build import directory,read_file
from check_native_font2x import init,GPU,OT,SPRITE

ROOT=Path(__file__).resolve().parents[1]


def draw_text(game,meta,lines):
    # Distinct stubs also avoid Unicorn's cached translated instructions when
    # the next page has fewer draw calls than the preceding page.
    source=[];stub=0x80142000+len(lines)*0x200
    for i,(label,y,color) in enumerate(lines):
        codes=efont.encode_plain(label,{**meta['encode'],**meta['encode_ex']})+[0xfffe]
        address=0x80144000+i*0x200
        game.cpu.mem_write(address&0x1fffffff,struct.pack('<%dH'%len(codes),*codes))
        source.append('''lui $t0,0x8014
        ori $t0,$t0,%d
        sw $t0,16($sp)
        sw $zero,20($sp)
        move $a0,$zero
        addiu $a1,$zero,70
        addiu $a2,$zero,%d
        jal 0x8004a954
        addiu $a3,$zero,%d'''%(address&0xffff,y,color))
    source='''addiu $sp,$sp,-32
    sw $ra,28($sp)
    '''+'\n'.join(source)+'''
    jal 0x8004bf8c
    move $a0,$zero
    lw $ra,28($sp)
    addiu $sp,$sp,32
    jr $ra
    nop'''
    game.cpu.mem_write(stub&0x1fffffff,asm(source,stub));game.call(stub,())


def packets(game,sorter):
    init(game.cpu)
    before=bytes(game.cpu.mem_read(0xc6588,0x2b00))
    for item in game.live(0):game.call(sorter,(SPRITE+36*item['slot'],OT,3))
    assert bytes(game.cpu.mem_read(0xc6588,0x2b00))==before,'Drawing mutated retained text'
    size=game.get(0x800d3df0,'<I')-GPU
    assert size%40==0
    return bytes(game.cpu.mem_read(GPU&0x1fffffff,size))


def check_packets(game,data,meta,atlas):
    expected=[];reverse={v:k for k,v in {**meta['encode'],**meta['encode_ex']}.items()}
    for item in game.live(0):
        address=SPRITE+36*item['slot']
        if not item['width'] or not item['height']:continue
        token=reverse[game.get(address+0x18,'<H')];x=item['x']
        crop=item['v']&15;h=item['height']
        assert crop+h<=16
        for ch in token:
            index=meta['uni'].index(ch);u,v=atlas[1][index*2:index*2+2]
            expected.append((x,item['y'],meta['widths'][ch],h,u,(v&0xe0)+crop*2))
            x+=meta['widths'][ch]
    assert len(data)==len(expected)*40,(len(data),len(expected))
    for i,(x,y,w,h,u,v) in enumerate(expected):
        packet=data[i*40:i*40+40]
        assert struct.unpack_from('<hh',packet,8)==(x,y)
        assert struct.unpack_from('<hh',packet,16)==(x+w,y)
        assert struct.unpack_from('<hh',packet,24)==(x,y+h)
        assert struct.unpack_from('<hh',packet,32)==(x+w,y+h)
        assert packet[12:14]==bytes([u,v]) and packet[20:22]==bytes([u+2*w,v])
        assert packet[28:30]==bytes([u,v+2*h]) and packet[36:38]==bytes([u+2*w,v+2*h])
    return len(expected)


def render(data,atlas,pal):
    image=Image.new('RGB',(320,240),(18,30,30));draw=ImageDraw.Draw(image)
    draw.rectangle((16,124,304,216),fill=(48,32,24),outline=(150,150,160),width=2)
    for i in range(0,len(data),40):
        p=data[i:i+40];x,y=struct.unpack_from('<hh',p,8);right=struct.unpack_from('<h',p,16)[0]
        bottom=struct.unpack_from('<h',p,26)[0];u,v,clut=struct.unpack_from('<BBH',p,12)
        row=(clut>>6)-0xf0
        for yy in range(max(0,bottom-y)*2):
            for xx in range(max(0,right-x)*2):
                level=int(atlas[v+yy,u+xx])
                if not level:continue
                color=int(pal[row*16+level*4]);rgb=texpack.c15(color)
                rgb=tuple(min(255,c*m//128) for c,m in zip(rgb,p[4:7]))
                px,py=x+xx//2,y+yy//2
                if not (0<=px<320 and 0<=py<240):continue
                old=image.getpixel((px,py))
                image.putpixel((px,py),tuple((a+b)//2 for a,b in zip(old,rgb)) if color&0x8000 and p[7]&2 else rgb)
    return image


def main():
    p=argparse.ArgumentParser();p.add_argument('--version',default='0.3.34');p.add_argument('--verify',action='store_true');a=p.parse_args()
    out=ROOT/'work/output';base=out/'STT2001_EN_v0.3.33.bin';d=directory(base)
    old=read_file(base,d['SLPS_028.63']);mm=repack.dat_entries(read_file(base,d['MAPMAIN.DAT']))
    raw=out/'STT2001_EN_v0.3.30.bin';unpatched=read_file(raw,directory(raw)['SLPS_028.63'])
    native_ui=tuple(map(int,a.version.split('.'))) >= (0,3,35)
    candidate,info=N.patch_exe(unpatched,True,transition_clip=True,native_ui=native_ui)
    target=out/('STT2001_EN_v'+a.version+'.bin')
    new=read_file(target,directory(target)['SLPS_028.63']) if a.verify else candidate
    assert new[mips.off(N.B):mips.off(N.LIMIT_B)]==candidate[mips.off(N.B):mips.off(N.LIMIT_B)]
    old_sorter=0x80000000|((struct.unpack_from('<I',old,mips.off(0x800155f0))[0]&0x3ffffff)<<2)
    sorter=int(info['labels']['draw'],16)
    games=[Sprites(exe,mm[2]) for exe in (old,new)]
    meta=json.loads((ROOT/'work/font/efont.json').read_text(encoding='utf-8'));atlas=N.assets()
    pal=texpack.tim_parts(mm[7])[3];frames=[];checked=0;hidden=0;ghost=0
    new_mm=repack.dat_entries(read_file(target,directory(target)['MAPMAIN.DAT'])) if a.verify else mm
    new_pal=texpack.tim_parts(new_mm[7])[3]
    lines=[('Takeshi Hongo',136,3),('Shocker has agents all over the world.',152,0),
           ('This looks like a good place to hide.',168,0),('We should keep moving.',184,0)]
    for game in games:
        draw_text(game,meta,lines)
        game.put(0x800c6b90,136);game.put(0x800c6bb0,60)
    for frame in range(35):
        raw_packets=[packets(g,s) for g,s in zip(games,(old_sorter,sorter))]
        checked+=check_packets(games[1],raw_packets[1],meta,atlas)
        live=games[1].live(0)
        assert games[0].live(0)==live,'Native clear state differs'
        cropped=sum(0<h['height']<16 for h in live)
        hidden+=sum(h['height']==0 for h in live)
        ghost+=sum(games[0].get(SPRITE+slot['slot']*36+0xa,'<H')==0 for slot in live) if raw_packets[0] else 0
        if frame in (0,12,28,34):
            frames.append((frame,raw_packets,cropped))
        if frame<34:
            for game in games:
                # Native clear expects the calling driver's dialogue-state base
                # in V1; execute its real Y/V/H/color updates and group scan.
                game.cpu.reg_write(UC_MIPS_REG_V1,0x800c6b88)
                game.call(0x8004c2a4,(0,1,0))
    assert not raw_packets[1] and raw_packets[0], 'Old zero-height flashing not reproduced'
    assert ghost>0 and hidden>0 and any(c for _,_,c in frames)
    # Immediate/skip clear retires objects, then the same speaker gets new text.
    for game in games:
        game.call(0x8004c2a4,(0,1,1))
        assert not game.live(0)
        draw_text(game,meta,[('Takeshi Hongo',136,3),('We can rest here for a while.',152,0)])
    final=[packets(g,s) for g,s in zip(games,(old_sorter,sorter))]
    checked+=check_packets(games[1],final[1],meta,atlas)
    if native_ui:
        expected=bytearray(final[0])
        for i in range(7,len(expected),40):expected[i]=0x2c
        assert bytes(expected)==final[1], 'Normal new-page geometry changed'
    else:assert final[0]==final[1], 'Normal new-page output changed'
    assert {s['y'] for s in games[1].live(0)}=={136,152},'Old body rows survived page replacement'
    frames.append(('next page',final,0))
    canvas=Image.new('RGB',(1280,256*len(frames)*2),(10,14,18));brush=ImageDraw.Draw(canvas)
    for row,(frame,items,_) in enumerate(frames):
        for col,data in enumerate(items):
            x,y=col*640,row*512
            brush.text((x+12,y+6),('v0.3.33' if col==0 else 'v'+a.version)+' / native clear frame '+str(frame),fill='white')
            canvas.paste(render(data,atlas[0],new_pal if col else pal).resize((640,480),Image.Resampling.NEAREST),(x,y+26))
    ui=ROOT/'work/ui/font';ui.mkdir(exist_ok=True,parents=True)
    image=ui/('clear-transition-v'+a.version+'.png');canvas.save(image)
    result={'version':a.version,'old_zero_height_flashing_reproduced':True,'native_clear_animation_frames':35,
            'native_clear_y_v_height_color_updates_executed':True,'clipped_ft4_packets_checked':checked,
            'zero_height_glyph_observations':hidden,'old_ghost_observations':ghost,
            'crop_and_geometry_match_native_height':True,'draw_does_not_mutate_text_state':True,
            'same_speaker_next_page_packets_unchanged':not native_ui,'same_speaker_next_page_geometry_unchanged':True,
            'immediate_clear_and_slot_reuse_checked':True,
            'preview':str(image.relative_to(ROOT)),'emulator_capture':False}
    if a.verify and not native_ui:
        import title_footer
        nd=directory(target)
        assert nd==d and target.stat().st_size==base.stat().st_size
        expected=bytearray(old)
        expected[mips.off(N.B):mips.off(N.LIMIT_B)]=candidate[mips.off(N.B):mips.off(N.LIMIT_B)]
        expected[mips.off(0x800155f0):mips.off(0x800155f0)+4]=candidate[mips.off(0x800155f0):mips.off(0x800155f0)+4]
        assert new==bytes(expected),'Unrelated executable bytes changed'
        title={'MAPMAIN.DAT':read_file(base,d['MAPMAIN.DAT'])}
        title_footer.patch_files(title,a.version)
        assert read_file(target,nd['MAPMAIN.DAT'])==title['MAPMAIN.DAT']
        title_footer.verify_disc(target,a.version)
        excludes=sorted((nd[n]['lba']*2352,(nd[n]['lba']+(nd[n]['size']+2047)//2048)*2352)
                        for n in ('SLPS_028.63','MAPMAIN.DAT'))
        with target.open('rb') as x,base.open('rb') as y:
            start=0
            for end,next_start in excludes+[(target.stat().st_size,target.stat().st_size)]:
                x.seek(start);y.seek(start)
                while start<end:
                    size=min(4*1024*1024,end-start)
                    assert x.read(size)==y.read(size),('Unrelated raw disc bytes changed',start)
                    start+=size
                start=next_start
        result['completed_disc_changes_limited_to_font_draw_and_title']=True
        result['raw_movies_audio_font_assets_and_gameplay_preserved']=True
        result['completed_title_version_and_credit_checked']=True
    (out/('STT2001_EN_v'+a.version+'_font_transition_verification.json')).write_bytes((json.dumps(result,indent=1)+'\n').encode())
    print(json.dumps(result,indent=1))


if __name__=='__main__':main()
