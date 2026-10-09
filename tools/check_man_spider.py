"""Audit the Man Spider rename on a completed disc against the previous build.

Dry run by default; --verify checks text, layout, containers and retained assets,
then copies the already compatible texture pack and writes the audit report.
"""
import json
import shutil
import struct
import sys
from collections import Counter
from pathlib import Path

import cm
import dump_script as D
import repack
import check_dialogue_layout as L
from check_graphics_build import directory,read_file,file_hash
from check_ui_labels import strings

ROOT=Path(__file__).resolve().parents[1]
OLD,NEW='SpiderMan','ManSpider'
VISIBLE=L.content


def canon(words):
    return VISIBLE(words).replace(OLD,NEW)


def texts(a,b,stats,kind):
    assert len(a)==len(b)
    for old,new in zip(a,b):
        before,after=VISIBLE(old),VISIBLE(new)
        assert canon(old)==after,('unrelated text changed',kind,before,after)
        assert OLD not in after,('old name remains',kind)
        stats[kind+'_name_occurrences']+=before.count(OLD)
        if OLD not in before:
            assert old==new,('unrelated glyphs or controls changed',kind)


def overlay(a,b,base,kind,stats):
    old,new=D.overlay_strings(a,base),D.overlay_strings(b,base)
    texts([w for _,w,_ in old],[w for _,w,_ in new],stats,kind)
    # Existing audit also checks pointer order, terminators and page limits.
    L.content=canon
    try:
        L.overlay(a,b,base,kind,stats)
    finally:
        L.content=VISIBLE


def table32(data):
    n=struct.unpack_from('<I',data)[0]//4
    result=[]
    for pos in struct.unpack_from('<%dI'%n,data):
        words=[]
        while pos+2<=len(data):
            word=struct.unpack_from('<H',data,pos)[0]
            words.append(word);pos+=2
            if word==0xFFFE:
                break
        else:
            raise AssertionError('unterminated encyclopedia record')
        result.append(words)
    return result


def verify(version,baseline):
    out=ROOT/'work/output'
    old,new=[out/('STT2001_EN_v%s.bin'%v) for v in (baseline,version)]
    od,nd=directory(old),directory(new)
    for key in nd:
        if key not in ('STAGE.DAT','MAPMAIN.DAT','BATTLE.DAT','DUMMY.DAT'):
            assert file_hash(old,od[key])==file_hash(new,nd[key]),key
    stats=Counter()
    arrays={key:tuple(repack.dat_entries(read_file(p,d[key])) for p,d in ((old,od),(new,nd)))
            for key in ('STAGE.DAT','MAPMAIN.DAT','BATTLE.DAT')}
    a,b=arrays['STAGE.DAT'];assert len(a)==len(b)
    allowed=set()
    for i,key in enumerate(sorted(D.STAGE_VAR)):
        idx=int(key);allowed|={idx,630+i}
        overlay(a[idx],b[idx],0,'stage',stats)
        ca,cb=cm.blocks(a[630+i]),cm.blocks(b[630+i])
        assert len(ca)==len(cb)
        for j,(x,y) in enumerate(zip(ca,cb)):
            if j==4:
                assert y==b[idx][:len(y)]
            else:
                assert x==y,('stage CM block changed',idx,j)
    assert all(x==y for i,(x,y) in enumerate(zip(a,b)) if i not in allowed)
    a,b=arrays['BATTLE.DAT'];assert len(a)==len(b)
    allowed={540}
    for i,(x,y) in enumerate(zip(a,b)):
        if len(x)>0x8438 and x[:4]==b'\x10\0\0\0' and struct.unpack_from('<I',x,0x8434)[0]>>16==0x800E:
            allowed.add(i)
            assert x[:0x8434]==y[:0x8434],('battle prefix changed',i)
            overlay(x,y,0x8434,'bquote',stats)
    assert all(x==y for i,(x,y) in enumerate(zip(a,b)) if i not in allowed)
    texts(table32(a[540]),table32(b[540]),stats,'encyclopedia')
    a,b=arrays['MAPMAIN.DAT'];assert len(a)==len(b)
    assert all(x==y for i,(x,y) in enumerate(zip(a,b)) if i not in (2,24))
    texts(strings(a[2]),strings(b[2]),stats,'database')
    ca,cb=cm.blocks(a[24]),cm.blocks(b[24]);assert len(ca)==len(cb)
    for i,(x,y) in enumerate(zip(ca,cb)):
        if i==1:
            texts(strings(x),strings(y),stats,'compressed_database')
        else:
            assert x==y,('database CM block changed',i)
    assert stats['stage_strings']==26261 and stats['bquote_strings']==12617
    assert all(stats[k+'_name_occurrences']>0 for k in ('stage','bquote','encyclopedia','database','compressed_database'))
    # Retain every movie sector, including XA audio and parity.
    assert od['MOVIE.STR']==nd['MOVIE.STR']
    offset=nd['MOVIE.STR']['lba']*2352
    remaining=(nd['MOVIE.STR']['size']+2047)//2048*2352
    with old.open('rb') as x,new.open('rb') as y:
        x.seek(offset);y.seek(offset)
        while remaining:
            size=min(remaining,4*1024*1024)
            assert x.read(size)==y.read(size)
            remaining-=size
    src,dst=[out/('STT2001_EN_v%s_4x_font'%v) for v in (baseline,version)]
    shutil.copytree(src,dst,dirs_exist_ok=True)
    names={p.relative_to(src) for p in src.rglob('*') if p.is_file()}
    assert names=={p.relative_to(dst) for p in dst.rglob('*') if p.is_file()}
    assert all((src/n).read_bytes()==(dst/n).read_bytes() for n in names)
    report={'version':version,'baseline':baseline,'all_checks_passed':True,
            'name':'Man Spider','checks':dict(stats),'all_other_english_and_pointer_order_preserved':True,
            'fonts_graphics_executable_and_movies_unchanged':True,'identical_texture_pack_files':len(names),
            'emulator_verified':False}
    build=json.loads((out/('STT2001_EN_v%s_report.json'%version)).read_text(encoding='utf-8'))
    assert not build['problems']
    (out/('STT2001_EN_v%s_name_verification.json'%version)).write_text(json.dumps(report,indent=1)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=1))


if __name__=='__main__':
    version=sys.argv[1] if len(sys.argv)>1 else '0.3.16'
    baseline=sys.argv[2] if len(sys.argv)>2 else '0.3.15'
    print('Audit: only Spider Man -> Man Spider; all dialogue layouts and shared assets retained.')
    if '--verify' in sys.argv:
        verify(version,baseline)
    else:
        print('Dry run. --verify audits the disc, copies the compatible font pack and saves its report.')
