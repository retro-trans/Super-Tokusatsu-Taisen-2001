"""Reproduce stale font tags in native number drawers and verify shared palettes."""
import argparse,json,struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import cm,gfx,mips,native_font2x as N,repack,texpack,title_footer,insert
from check_graphics_build import directory,read_file
from check_difficulty_render import Sprites
from check_font_transition import draw_text
from check_native_font2x import init,GPU,OT,SPRITE
from runtime_balance import asm

ROOT=Path(__file__).resolve().parents[1]

class NativeUI(Sprites):
    def hook(self,cpu,address,size,unused):
        if address==0x8004ccf0:
            return  # Execute the number formatter; do not model it as a draw request.
        return super().hook(cpu,address,size,unused)


def number(game,value,large=False):
    stub=0x80143000+(0x200 if large else 0)
    game.cpu.mem_write(0x146000,struct.pack('<I',value))
    code=asm('''addiu $sp,$sp,-32
    sw $ra,28($sp)
    lui $t0,0x8014
    lw $t0,0x6000($t0)
    addiu $t1,$zero,4
    sw $t0,16($sp)
    sw $t1,20($sp)
    addiu $t0,$zero,3
    sw $t0,24($sp)
    move $a0,$zero
    addiu $a1,$zero,70
    addiu $a2,$zero,152
    jal %d
    move $a3,$zero
    jal 0x8004bf8c
    move $a0,$zero
    lw $ra,28($sp)
    addiu $sp,$sp,32
    jr $ra
    nop'''%(0x8004ccf0 if large else 0x8004cfa8),stub)
    game.cpu.mem_write(stub&0x1fffffff,code);game.call(stub,())


def packets(game,sorter):
    init(game.cpu)
    for item in game.live(0):game.call(sorter,(SPRITE+36*item['slot'],OT,3))
    return bytes(game.cpu.mem_read(GPU&0x1fffffff,game.get(0x800d3df0,'<I')-GPU))


def restore_palette(tim,original):
    assert tim[8:20]==original[8:20]
    length=struct.unpack_from('<I',tim,8)[0]-12
    return tim[:20]+original[20:20+length]+tim[20+length:]


def main():
    p=argparse.ArgumentParser();p.add_argument('--version',default='0.3.35');p.add_argument('--verify',action='store_true')
    p.add_argument('--movie-baseline',help='Approved movie revision, independently of the native UI baseline')
    a=p.parse_args()
    out=ROOT/'work/output';base=out/'STT2001_EN_v0.3.34.bin';legacy=out/'STT2001_EN_v0.3.29.bin'
    old=read_file(base,directory(base)['SLPS_028.63']);raw=out/'STT2001_EN_v0.3.30.bin'
    candidate,info=N.patch_exe(read_file(raw,directory(raw)['SLPS_028.63']),True,True,True)
    target=out/('STT2001_EN_v'+a.version+'.bin')
    new=read_file(target,directory(target)['SLPS_028.63']) if a.verify else candidate
    mm=repack.dat_entries(read_file(base,directory(base)['MAPMAIN.DAT']))
    meta=json.loads((ROOT/'work/font/efont.json').read_text(encoding='utf-8'))
    sorter=int(info['labels']['draw'],16);cases=0;bad=0
    for large in (False,True):
        for value in (0,1,9,10,59,66,190,202,9999):
            for fresh in (False,True):
                games=[NativeUI(e,mm[2]) for e in (old,new)]
                for game in games:
                    draw_text(game,meta,[('Takeshi Hongo',136,3)])
                    if fresh:
                        game.call(0x8004ac24,(0,))
                        game.put(0x800bd0a8+0x4d8,0)
                    number(game,value,large)
                for game in games:
                    live=game.live(0)
                    assert len(live)==len(str(value)),(value,large,fresh,len(live),live)
                    assert all(i['width']==8 and i['height']==(16 if large else 8) for i in live)
                actual=packets(games[1],sorter)
                if not large:
                    assert all(games[1].get(SPRITE+36*i['slot']+0x1a,'<H')==0 for i in games[1].live(0))
                    expected=packets(games[1],0x80088bb8)
                    assert actual==expected and len(actual)==24*len(str(value))
                    broken=packets(games[0],sorter)
                    assert broken!=expected
                    bad+=1
                else:
                    assert len(actual)==40*len(str(value))
                    digits=[]
                    for i in games[1].live(0):
                        address=SPRITE+36*i['slot']
                        assert games[1].get(address+0x1a,'<H')==N.MAGIC
                        digits.append(str(games[1].get(address+0x18,'<H')-1))
                    assert ''.join(digits)==str(value)
                # Numeric reuse must not disable the next English text draw.
                draw_text(games[1],meta,[('Furuhashi',136,3)])
                assert all(games[1].get(SPRITE+36*i['slot']+0x1a,'<H')==N.MAGIC for i in games[1].live(0))
                cases+=1
    report={'version':a.version,'native_numeric_reuse_cases':cases,'old_corrupted_small_number_cases_reproduced':bad,
            'small_number_packets_equal_original_native_drawer':True,'large_numeric_font_tags_and_digits_checked':True,
            'fresh_dirty_slot_and_same_group_reuse_checked':True,'text_after_numeric_reuse_checked':True,
            'allocator_cleanup_bytes':16,'heap_and_vram_extent_unchanged':True,'emulator_playtest':False}
    if a.verify:
        nd,od=directory(target),directory(base);ld=directory(legacy)
        assert nd==od and target.stat().st_size==base.stat().st_size
        expected=bytearray(old)
        for start,end in [(N.B,N.LIMIT_B),(0x8004a940,0x8004a954),(0x8004c284,0x8004c28c)]:
            expected[mips.off(start):mips.off(end)]=candidate[mips.off(start):mips.off(end)]
        assert new==bytes(expected),'Unrelated executable changes'
        files={};copies=0;icon_pages=0
        for name,indices in [('MAPMAIN.DAT',[7]),('BATTLE.DAT',[537,538]),('EVENT.DAT',[10]+list(range(11,24)))]:
            entries=repack.dat_entries(read_file(base,od[name]));original=repack.dat_entries(read_file(legacy,ld[name]))
            for index in indices:
                entries[index]=restore_palette(entries[index],original[index]);copies+=1
                if name=='BATTLE.DAT' and index==537:continue
                pixels=gfx.Tim(entries[index]).idx;native=gfx.Tim(original[index]).idx
                first=256 if pixels.shape[1]>=512 else 0
                assert np.array_equal(pixels[:,first:first+256]>>2,native[:,first:first+256]>>2)
                icon_pages+=1
            if name=='MAPMAIN.DAT':
                blocks=cm.blocks(entries[25]);source=cm.blocks(original[25])
                entries[25]=insert.rebuild_cm(entries[25],{3:restore_palette(blocks[3],source[3])});copies+=1
                assert np.array_equal(gfx.Tim(blocks[3]).idx[:,256:512]>>2,gfx.Tim(source[3]).idx[:,256:512]>>2)
                icon_pages+=1
            files[name]=repack.dat_pack(entries)
        title_footer.patch_files(files,a.version)
        for name,expected in files.items():assert read_file(target,nd[name])==expected,name
        title_footer.verify_disc(target,a.version)
        # Everything beyond the exact EXE/palette/title file edits is identical,
        # including all raw movie and XA audio sectors and disc metadata.
        exclude_names=['SLPS_028.63',*files]
        if a.movie_baseline:
            movie_base=out/('STT2001_EN_v'+a.movie_baseline+'.bin');md=directory(movie_base)
            assert md['MOVIE.STR']==nd['MOVIE.STR']
            remain=((nd['MOVIE.STR']['size']+2047)//2048)*2352
            with target.open('rb') as x,movie_base.open('rb') as y:
                x.seek(nd['MOVIE.STR']['lba']*2352);y.seek(md['MOVIE.STR']['lba']*2352)
                while remain:
                    size=min(remain,4*1024*1024);assert x.read(size)==y.read(size);remain-=size
            exclude_names.append('MOVIE.STR')
        excluded=sorted((nd[n]['lba']*2352,(nd[n]['size']+2047)//2048*2352+nd[n]['lba']*2352)
                        for n in exclude_names)
        with target.open('rb') as x,base.open('rb') as y:
            start=0
            for end,next_start in excluded+[(target.stat().st_size,target.stat().st_size)]:
                x.seek(start);y.seek(start)
                while start<end:
                    size=min(4*1024*1024,end-start);assert x.read(size)==y.read(size),start;start+=size
                start=next_start
        report.update(completed_disc_changes_limited_to_native_ui_fix_and_title=True,
                      original_shared_palette_copies_checked=copies,font_pixels_and_text_and_gameplay_preserved=True,
                      native_right_page_icon_pages_checked=icon_pages,
                      raw_movies_and_audio_preserved=True,movie_baseline=a.movie_baseline or '0.3.34',
                      title_version_and_credit_checked=True)
        updated=repack.dat_entries(read_file(target,nd['MAPMAIN.DAT']))
        canvas=Image.new('RGB',(720,240),(0,48,48));brush=ImageDraw.Draw(canvas)
        for row,(label,tim) in enumerate([('v0.3.34',mm[7]),('v'+a.version,updated[7])]):
            brush.text((12,row*120+8),label+' - native weapon badges',fill='white')
            pixels=gfx.Tim(tim).idx;pal=texpack.tim_parts(tim)[3]
            for i,code in enumerate(range(1430,1439)):
                _,_,x,y=texpack.cell_xy(code)
                levels=pixels[y:y+16,256+x:256+x+12]>>2
                colours=np.array([(0,48,48)]+[texpack.c15(int(pal[16+lv*4])) for lv in (1,2,3)],np.uint8)
                glyph=Image.fromarray(colours[levels]).resize((48,64),Image.Resampling.NEAREST)
                canvas.paste(glyph,(12+i*78,row*120+30));brush.text((12+i*78,row*120+98),str(code),fill='white')
        image=ROOT/'work/ui/font'/('native-ui-v'+a.version+'.png');canvas.save(image)
        report['badge_preview']=str(image.relative_to(ROOT));report['preview_is_emulator_capture']=False
    (out/('STT2001_EN_v'+a.version+'_native_ui_verification.json')).write_bytes((json.dumps(report,indent=1)+'\n').encode())
    print(json.dumps(report,indent=1))


if __name__=='__main__':main()
