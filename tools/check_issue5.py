"""Verify branch-specific Atefarina pronouns on a completed native build."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import struct

import cm
import dump_script as D
import insert
import repack
import title_footer
import check_dialogue_layout as L
from check_graphics_build import directory,read_file

ROOT=Path(__file__).resolve().parents[1]
BEFORE='Damn… He got away!?<p>No… I should say he was kind enough to leave…'
AFTER='Damn… She got away!?<p>No… I should say she was kind enough to leave…'
CASES=[('STAGE0061',14352,'U01396',BEFORE),('STAGE0061',14420,'U01397',BEFORE),
       ('STAGE0068',13758,'U01396',AFTER),('STAGE0068',13826,'U01397',AFTER)]


def body(words):
    words=list(words)
    if words[0]==0xff33:
        words=words[words.index(0xff30)+1:]
    if words and words[0]==0xfffb:words=words[1:]
    return words


def visible(words):
    return re.sub(r'\s+','',''.join(L.REVERSE.get(c,'') for c in body(words)))


def expected(text):
    return re.sub(r'\s+','',text.replace('<p>',''))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version',default='0.9.8')
    args=p.parse_args()
    out=ROOT/'work/output'
    old,new=[out/('STT2001_EN_v%s.bin'%v) for v in ('0.9.7',args.version)]
    od,nd=directory(old),directory(new)
    assert od==nd and old.stat().st_size==new.stat().st_size
    before=repack.dat_entries(read_file(old,od['STAGE.DAT']))
    after=repack.dat_entries(read_file(new,nd['STAGE.DAT']))
    source=json.loads((ROOT/'work/script/occurrences.json').read_text(encoding='utf-8'))
    assert len([r for r in source if r['uid'] in ('U01396','U01397')])==4
    checks=[];targets=set();compiled={}
    translator=insert.Translator()
    for file,off,uid,text in CASES:
        occurrence=next(r for r in source if r['file']==file and r['off']==off)
        assert occurrence['uid']==uid
        entry=int(file[5:])
        raw=(ROOT/('work/source/unpacked/STAGE/%04d.bin'%entry)).read_bytes()
        originals=D.overlay_strings(raw,0)
        index=next(i for i,(position,_,_) in enumerate(originals) if position==off)
        old_words=D.overlay_strings(before[entry],0)[index][1]
        new_words=D.overlay_strings(after[entry],0)[index][1]
        assert visible(old_words)==expected(BEFORE),(file,off,'baseline')
        assert visible(new_words)==expected(text),(file,off,'gender')
        if entry==61:
            assert old_words==new_words, 'Male branch changed'
        else:
            targets.add(index)
        # Execute the existing occurrence resolver in both orders to catch
        # any leak through its shared-source-string cache.
        compiled[(file,off)]=new_words
        for _ in range(2):
            words=translator.words_for('stage',originals[index][1],str(occurrence['font']),(file,off))
            assert words==list(new_words)
        checks.append(dict(file=file,offset=off,uid=uid,english=text,unchanged=entry==61))
    for file,off,uid,text in reversed(CASES):
        occurrence=next(r for r in source if r['file']==file and r['off']==off)
        ws=insert.read_ws(file,off,int(occurrence['term'],16))
        assert translator.words_for('stage',ws,str(occurrence['font']),(file,off))==list(compiled[(file,off)])
    old_rows,new_rows=[D.overlay_strings(data,0) for data in (before[68],after[68])]
    assert len(old_rows)==len(new_rows)
    count=0
    while struct.unpack_from('<I',before[68],count*4)[0]>>16==0x800e:count+=1
    order=[]
    for data,rows in ((before[68],old_rows),(after[68],new_rows)):
        indices={off:i for i,(off,_,_) in enumerate(rows)}
        order.append([indices[v-0x800e0000] for v in struct.unpack_from('<%dI'%count,data)])
    assert order[0]==order[1]
    stats=Counter()
    changed=[]
    for i,((_,ow,ot),(_,nw,nt)) in enumerate(zip(old_rows,new_rows)):
        assert ot==nt
        if i not in targets:assert ow==nw,('Unrelated dialogue changed',i)
        else:
            assert ow!=nw
            changed.append(i)
        L.check_words(nw,'stage',stats)
    assert set(changed)==targets and len(changed)==2
    packed=630+next(i for i,k in enumerate(sorted(D.STAGE_VAR)) if int(k)==68)
    ob,nb=[insert.cm_blocks_raw(parts[packed]) for parts in (before,after)]
    assert len(ob)==len(nb)
    assert nb[4][0]==after[68][:len(nb[4][0])]
    assert all(a[1]==b[1] for i,(a,b) in enumerate(zip(ob,nb)) if i!=4)
    changed_entries=[i for i,(a,b) in enumerate(zip(before,after)) if a!=b]
    assert changed_entries==sorted([68,packed]),changed_entries
    before[68]=after[68];before[packed]=after[packed]
    assert repack.dat_pack(before)==read_file(new,nd['STAGE.DAT'])
    mapmain={'MAPMAIN.DAT':read_file(old,od['MAPMAIN.DAT'])}
    title_footer.patch_files(mapmain,args.version)
    assert mapmain['MAPMAIN.DAT']==read_file(new,nd['MAPMAIN.DAT'])
    title_footer.verify_disc(new,args.version)
    excluded=sorted((nd[n]['lba']*2352,(nd[n]['lba']+(nd[n]['size']+2047)//2048)*2352)
                    for n in ('STAGE.DAT','MAPMAIN.DAT'))
    with old.open('rb') as a,new.open('rb') as b:
        cursor=0
        for first,last in excluded+[(new.stat().st_size,new.stat().st_size)]:
            a.seek(cursor);b.seek(cursor)
            while cursor<first:
                n=min(8*1024*1024,first-cursor)
                assert a.read(n)==b.read(n),('Unrelated raw bytes changed',cursor)
                cursor+=n
            cursor=last
    result=dict(version=args.version,baseline='0.9.7',issue=5,all_checks_passed=True,
                branch_cases=checks,changed_stage_entries=changed_entries,changed_dialogue_rows=2,
                shared_translation_unchanged=True,male_branch_byte_identical=True,
                all_other_dialogue_unchanged=True,pointer_order_and_terminators_preserved=True,
                compressed_copy_verified=True,occurrence_cache_orders_checked=True,
                dialogue_layout=dict(stats),title_copies_verified=True,
                all_other_raw_disc_bytes_identical=True,movies_audio_font_and_executable_unchanged=True,
                emulator_verified=False)
    (out/('STT2001_EN_v%s_issue5_verification.json'%args.version)).write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print('PASS: both female variants corrected, both male variants unchanged; all unrelated game bytes preserved.')


if __name__=='__main__':main()
