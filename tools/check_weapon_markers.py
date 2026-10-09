"""Dry-run marker/menu checks; --verify audits v0.3.18 and its font pack."""
import itertools
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from unicorn.mips_const import UC_MIPS_REG_S0,UC_MIPS_REG_S1,UC_MIPS_REG_S2,UC_MIPS_REG_S6,UC_MIPS_REG_PC
import cm
import insert
import repack
import texpack
import weapon_markers as FIX
from check_graphics_build import directory,read_file,file_hash
from check_ui_labels import strings
from check_intermission_layout import Intermission,text
from check_dialogue_layout import width

ROOT=Path(__file__).resolve().parents[1]
PARTS={0xA74,0xB12,0xB1E,0xD8F}


def changed_font(before,after,main,page_x):
    expected=bytearray(before);pixels,base=insert.tim_pixels(expected)
    if main:
        FIX.apply_main(pixels)
    FIX.apply_ex(pixels,page_x)
    raw=(pixels[:,0::2]|(pixels[:,1::2]<<4)).astype(np.uint8).tobytes()
    expected[base:base+len(raw)]=raw
    assert after==bytes(expected),'Font changed outside weapon markers'


def popup(exe,db):
    screen=Intermission(exe,db);cpu=screen.cpu;cases=labels=0
    # Execute the native dynamic-menu draw loop for every nonempty subset of
    # its five options. Selection conditions and frame code are unchanged.
    for count in range(1,6):
        for options in itertools.combinations(range(5),count):
            cpu.mem_write(0x101A00,bytes(options))
            cpu.reg_write(UC_MIPS_REG_S0,0)
            cpu.reg_write(UC_MIPS_REG_S1,count)
            cpu.reg_write(UC_MIPS_REG_S2,0x80101A00)
            cpu.reg_write(UC_MIPS_REG_S6,0)
            screen.draws=[]
            cpu.emu_start(0x8005FA2C,0x8005FA80,count=10000)
            assert cpu.reg_read(UC_MIPS_REG_PC)==0x8005FA80
            assert len(screen.draws)==count
            for row,(option,draw) in enumerate(zip(options,screen.draws)):
                assert draw['x']==124 and draw['y']==60+row*16
                assert text(draw['codes'])==text(strings(db)[0xD8D+option])
                assert sum(width(c) for c in draw['codes'])<=64
                labels+=1
            cases+=1
    return cases,labels


def keys(part,page):
    pixels,(iw,ih),upload,_=part
    out=[(upload,iw,page*256)]
    if iw>64:
        import xxhash
        sub=pixels[:,page*256:(page+1)*256]
        raw=(sub[:,0::2]|(sub[:,1::2]<<4)).astype(np.uint8).tobytes()
        out.append((xxhash.xxh3_64_intdigest(raw),64,0))
    return out


def pack(before,after,folder_old,folder_new):
    sheets=[('MAPMAIN.DAT',7,[(0,'main'),(1,'ex')]),
            ('BATTLE.DAT',538,[(0,'main'),(1,'ex')]),
            ('BATTLE.DAT',537,[(0,'encyc')])]
    sheets += [('EVENT.DAT',i,[(0,'ex')]) for i in range(11,24)]
    parts=[texpack.tim_parts(after[a][i]) for a,i,pages in sheets]
    palettes=texpack.palettes([part[3] for part in parts]);seen=set();hf=texpack.HiFont()
    changed=0
    for archive,index,pages in sheets:
        oldpart=texpack.tim_parts(before[archive][index]);newpart=texpack.tim_parts(after[archive][index])
        for page,role in pages:
            layers=texpack.hires_layers(newpart[0],page,hf,role)
            for ph,(layer,row) in palettes.items():
                mask=np.zeros((1024,1024),bool)
                if role=='main' and layer==0:
                    for code in FIX.PREFIX:
                        x,y=(code%32)*32,(code//32)*64;mask[y:y+64,x:x+32]=True
                if role=='ex' and layer==1:
                    for code in FIX.ATTRIBUTES:
                        r=code-1118;x,y=(r%21)*48,(r//21)*64;mask[y:y+64,x:x+48]=True
                for stp in (False,True):
                    for oldkey,newkey in zip(keys(oldpart,page),keys(newpart,page)):
                        def name(key):
                            h,w,x=key
                            return 'texupload-%s-%016X-%016X-%dx256-%d-0-256x256-P0-15.png'%('STP4' if stp else 'P4',h,ph,w,x)
                        oldname,newname=name(oldkey),name(newkey)
                        if newname in seen:
                            continue
                        previous=np.asarray(Image.open(folder_old/oldname).convert('RGBA'))
                        actual=np.asarray(Image.open(folder_new/newname).convert('RGBA'))
                        expected=np.asarray(texpack.colourise(layers[layer],layer,row,stp))
                        assert np.array_equal(actual,expected),newname
                        assert np.array_equal(previous[~mask],actual[~mask]),('Neighboring texture changed',newname)
                        changed+=int(not np.array_equal(previous,actual));seen.add(newname)
    names={p.name for p in folder_new.glob('*.png')}
    assert seen==names,('Unchecked textures',names-seen)
    return len(seen),changed


def main():
    version,baseline='0.3.18','0.3.17';out=ROOT/'work/output'
    old=out/('STT2001_EN_v%s.bin'%baseline);od=directory(old)
    exe=read_file(old,od['SLPS_028.63']);db=repack.dat_entries(read_file(old,od['MAPMAIN.DAT']))[2]
    oldrows=strings(db)
    assert {i for i,row in enumerate(oldrows) if text(row)=='Upgrade Parts'}==PARTS
    assert not set(FIX.ATTRIBUTES)&set(insert.EF['encode_ex'].values())
    assert not set(FIX.ATTRIBUTES)&set(insert.EF['encode'].values())
    words=insert.encode_line_tokens(['Parts'],{})+[0xFFFE]
    assert sum(width(c) for c in words)==34
    proposed=bytearray(db)
    for index in PARTS:
        struct.pack_into('<H',proposed,index*2,len(proposed))
        proposed+=struct.pack('<%dH'%len(words),*words)
    cases,labels=popup(exe,bytes(proposed))
    print('Dry run passed: 8 glyph cells; Parts 34/64px; %d native menu draw cases / %d labels'%(cases,labels))
    if '--verify' not in sys.argv:
        return
    new=out/('STT2001_EN_v%s.bin'%version);nd=directory(new)
    assert read_file(new,nd['SLPS_028.63'])==exe
    allowed={'MAPMAIN.DAT':{2,7,24,25},'BATTLE.DAT':{538},'EVENT.DAT':set(range(10,24))}
    before,after={},{}
    for key in nd:
        if key not in allowed and key!='DUMMY.DAT':
            assert file_hash(new,nd[key])==file_hash(old,od[key]),key
    for archive,indices in allowed.items():
        a,b=[repack.dat_entries(read_file(p,d[archive])) for p,d in ((old,od),(new,nd))]
        assert len(a)==len(b)
        assert {i for i,(x,y) in enumerate(zip(a,b)) if x!=y}==indices,archive
        before[archive],after[archive]=a,b
    def database(a,b):
        first,last=strings(a),strings(b)
        assert len(first)==len(last)
        assert {i for i,(x,y) in enumerate(zip(first,last)) if x!=y}==PARTS
        assert all(last[i]==words for i in PARTS)
    def compressed(a,b,index,check):
        first,last=cm.blocks(a),cm.blocks(b)
        assert len(first)==len(last)
        assert {i for i,(x,y) in enumerate(zip(first,last)) if x!=y}=={index}
        check(first[index],last[index])
    a,b=before['MAPMAIN.DAT'],after['MAPMAIN.DAT']
    database(a[2],b[2]);changed_font(a[7],b[7],True,256)
    compressed(a[24],b[24],1,database)
    compressed(a[25],b[25],3,lambda x,y:changed_font(x,y,True,256))
    changed_font(before['BATTLE.DAT'][538],after['BATTLE.DAT'][538],True,256)
    for i in range(10,24):
        changed_font(before['EVENT.DAT'][i],after['EVENT.DAT'][i],i==10,256 if i==10 else 0)
    cases,labels=popup(exe,b[2])
    oldfolder=out/('STT2001_EN_v%s_4x_font'%baseline)/texpack.SERIAL
    newfolder=out/('STT2001_EN_v%s_4x_font'%version)/texpack.SERIAL
    count,changed=pack(before,after,oldfolder/'replacements',newfolder/'replacements')
    assert (oldfolder/'config.yaml').read_bytes()==(newfolder/'config.yaml').read_bytes()
    assert not json.loads((out/('STT2001_EN_v%s_report.json'%version)).read_text(encoding='utf-8'))['problems']
    report={'version':version,'baseline':baseline,'all_checks_passed':True,
            'marker_codes':8,'native_font_copies':17,'parts_labels_per_database':len(PARTS),
            'actual_mips_menu_draw_cases':cases,'actual_mips_menu_labels':labels,'parts_width':34,'menu_text_width':64,
            'replacement_images_verified':count,'replacement_images_with_changed_pixels':changed,
            'neighboring_texture_pixels_unchanged':True,
            'executable_dialogue_weapon_data_graphics_movies_unchanged':True,'emulator_verified':False}
    (out/('STT2001_EN_v%s_weapon_ui_verification.json'%version)).write_text(json.dumps(report,indent=1)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=1))


if __name__=='__main__':
    main()
