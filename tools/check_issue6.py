"""Reproduce Father objective clipping and audit the complete local repair."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import struct

import check_dialogue_layout as L
from check_difficulty_render import Sprites
from check_graphics_build import directory,read_file
import dump_script as D
import insert
import repack
import title_footer
from runtime_balance import asm

ROOT=Path(__file__).resolve().parents[1]
UID,ENTRY,OFFSET='U02575',117,25754
OLD='Defeat all of Makuu and the Shocker army! However, if an Executive Monster reaches the Makuu base before Gavan does, Machiko Shirakawa will die!'
NEW='Defeat all Makuu and Shocker forces! Machiko Shirakawa dies if an Executive Monster beats Gavan to the Makuu base.'


def text(words):return ''.join(L.REVERSE.get(c,'') for c in words)
def canonical(value):return re.sub(r'\s+','',value)


class ObjectiveSprites(Sprites):
    def read_words(self,pointer):
        # Objectives are longer than the menu captions in the base fixture.
        words=[]
        for i in range(1024):
            value=self.get((pointer&0x1fffffff)+2*i,'<H')
            if value in (0xfffe,0xfffd):return words
            words.append(value)
        raise AssertionError('Unterminated objective')


def native_draw(exe,db,words):
    game=ObjectiveSprites(exe,db)
    words=list(words)+[0xfffe]
    game.cpu.mem_write(0x144000,struct.pack('<%dH'%len(words),*words))
    game.cpu.mem_write(0x142000,asm('''addiu $sp,$sp,-32
    sw $ra,28($sp)
    lui $t0,0x8014
    ori $t0,$t0,0x4000
    sw $t0,16($sp)
    sw $zero,20($sp)
    move $a0,$zero
    addiu $a1,$zero,18
    addiu $a2,$zero,30
    jal 0x8004a954
    move $a3,$zero
    jal 0x8004bf8c
    move $a0,$zero
    lw $ra,28($sp)
    addiu $sp,$sp,32
    jr $ra
    nop''',0x80142000))
    game.call(0x80142000,())
    lines={}
    for item in game.live(0):
        code=game.get(0x800c6c10+36*item['slot']+0x18,'<H')
        row=lines.setdefault(item['y'],dict(y=item['y'],text='',right=18))
        row['text']+=L.REVERSE.get(code,'{unsupported-control}')
        row['right']=max(row['right'],item['x']+item['width'])
    return game,list(lines.values())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--version',default='0.9.9');a=p.parse_args()
    out=ROOT/'work/output'
    before,after=[out/('STT2001_EN_v%s.bin'%v) for v in ('0.9.8',a.version)]
    od,nd=directory(before),directory(after)
    assert od==nd and before.stat().st_size==after.stat().st_size
    old,new=[repack.dat_entries(read_file(p,d['STAGE.DAT'])) for p,d in ((before,od),(after,nd))]
    source=(ROOT/'work/source/unpacked/STAGE/0117.bin').read_bytes()
    originals=D.overlay_strings(source,0)
    index=next(i for i,r in enumerate(originals) if r[0]==OFFSET)
    occurrences=[r for r in insert.frozen_rows() if r['uid']==UID]
    assert len(occurrences)==1 and (occurrences[0]['file'],occurrences[0]['off'])==('STAGE0117',OFFSET)
    old_rows,new_rows=[D.overlay_strings(data,0) for data in (old[ENTRY],new[ENTRY])]
    assert len(old_rows)==len(new_rows)
    old_words,new_words=old_rows[index][1],new_rows[index][1]
    assert canonical(text(old_words))==canonical(OLD)
    assert canonical(text(new_words))==canonical(NEW)
    assert old_words.count(0xfffc)==1 and 0xfffc not in new_words
    assert new_words.count(0xfffb)==2
    expected=insert.layout(NEW,220,3)
    assert len(expected)==1 and len(expected[0])==3
    stats=Counter()
    for i,((_,ow,ot),(_,nw,nt)) in enumerate(zip(old_rows,new_rows)):
        assert ot==nt
        if i!=index:assert ow==nw,('Unrelated text changed',i)
        L.check_words(nw,'stage',stats)
    count=0
    while struct.unpack_from('<I',old[ENTRY],count*4)[0]>>16==0x800e:count+=1
    orders=[]
    for data,rows in ((old[ENTRY],old_rows),(new[ENTRY],new_rows)):
        lookup={off:i for i,(off,_,_) in enumerate(rows)}
        orders.append([lookup[v-0x800e0000] for v in struct.unpack_from('<%dI'%count,data)])
    assert orders[0]==orders[1]
    packed=630+next(i for i,k in enumerate(sorted(D.STAGE_VAR)) if int(k)==ENTRY)
    original_blocks,new_blocks=[insert.cm_blocks_raw(parts[packed]) for parts in (old,new)]
    assert len(original_blocks)==len(new_blocks)
    assert new_blocks[4][0]==new[ENTRY][:len(new_blocks[4][0])]
    assert all(x[1]==y[1] for i,(x,y) in enumerate(zip(original_blocks,new_blocks)) if i!=4)
    changed=[i for i,(x,y) in enumerate(zip(old,new)) if x!=y]
    assert changed==sorted([ENTRY,packed]),changed
    old[ENTRY]=new[ENTRY];old[packed]=new[packed]
    assert repack.dat_pack(old)==read_file(after,nd['STAGE.DAT'])
    expected_map={'MAPMAIN.DAT':read_file(before,od['MAPMAIN.DAT'])}
    title_footer.patch_files(expected_map,a.version)
    assert expected_map['MAPMAIN.DAT']==read_file(after,nd['MAPMAIN.DAT'])
    title_footer.verify_disc(after,a.version)
    exe=read_file(after,nd['SLPS_028.63'])
    mm=repack.dat_entries(read_file(after,nd['MAPMAIN.DAT']))
    _,native_old=native_draw(exe,mm[2],old_words)
    _,native_new=native_draw(exe,mm[2],new_words)
    assert max(r['right'] for r in native_old)>304,'Old clipping not reproduced'
    assert len(native_new)==3 and all(r['right']<=238 for r in native_new)
    assert [r['text'] for r in native_new]==[''.join(line) for line in expected[0]]
    assert 'Machiko Shirakawa dies' in ' '.join(r['text'] for r in native_new)
    excluded=sorted((nd[n]['lba']*2352,(nd[n]['lba']+(nd[n]['size']+2047)//2048)*2352)
                    for n in ('STAGE.DAT','MAPMAIN.DAT'))
    with before.open('rb') as x,after.open('rb') as y:
        cursor=0
        for first,last in excluded+[(after.stat().st_size,after.stat().st_size)]:
            x.seek(cursor);y.seek(cursor)
            while cursor<first:
                n=min(8*1024*1024,first-cursor)
                assert x.read(n)==y.read(n),('Unrelated disc bytes changed',cursor)
                cursor+=n
            cursor=last
    result=dict(version=a.version,baseline='0.9.8',issue=6,all_checks_passed=True,
                changed_uid=UID,original_occurrence=['STAGE0117',OFFSET],english=NEW,
                changed_stage_entries=changed,changed_dialogue_rows=1,
                original_pagination_and_native_overflow_reproduced=True,
                native_before=native_old,native_after=native_new,native_text_drawer_executed=True,
                objective_is_one_page=True,maximum_objective_body_lines=3,
                dialogue_layout=dict(stats),all_other_strings_and_scene_commands_unchanged=True,
                issue5_fix_preserved=True,compressed_copy_verified=True,
                pointer_order_and_terminators_preserved=True,title_copies_verified=True,
                all_other_raw_disc_bytes_identical=True,movies_audio_font_and_executable_unchanged=True,
                emulator_verified=False)
    (out/('STT2001_EN_v%s_issue6_verification.json'%a.version)).write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print('PASS: old native overflow reproduced; full warning fits three lines; unrelated game bytes preserved.')


if __name__=='__main__':main()
