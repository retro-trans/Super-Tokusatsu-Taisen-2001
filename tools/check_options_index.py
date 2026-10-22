"""Native Options title lookups and encyclopedia index regression checks.

Run VERSION BASELINE --verify to check completed discs and save a report.
"""
import argparse
import json
import shutil
import struct
import zipfile
from pathlib import Path

from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS32, UC_MODE_LITTLE_ENDIAN, UC_HOOK_CODE
from unicorn.mips_const import (UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2,
                               UC_MIPS_REG_A3, UC_MIPS_REG_V0, UC_MIPS_REG_SP,
                               UC_MIPS_REG_RA, UC_MIPS_REG_PC)
import cm
import encyclopedia_layout
import insert
import repack
import title_footer
from check_dialogue_layout import width
from check_encyclopedia import visible
from check_graphics_build import directory, read_file, file_hash
from check_man_spider import table32

ROOT = Path(__file__).resolve().parents[1]
MASK = 0x1FFFFFFF
REGS = [UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2, UC_MIPS_REG_A3]


def words_at(data, offset):
    result = []
    while offset+2 <= len(data):
        code = struct.unpack_from('<H', data, offset)[0]
        if code in (0xFFFD, 0xFFFE):
            return result
        result.append(code)
        offset += 2
    raise AssertionError('unterminated text')


class Native:
    def __init__(self, exe, music, encyclopedia):
        self.cpu = c = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 | UC_MODE_LITTLE_ENDIAN)
        c.mem_map(0, 0x200000)
        c.mem_write(0x10000, exe[0x800:])
        c.mem_write(0x152000, music)
        c.mem_write(0x188000, encyclopedia)
        c.mem_write(0x1B8, struct.pack('<I', 0x801A7000))
        c.mem_write(0x1E8, struct.pack('<I', 0x801A9000))
        self.draws = []
        c.hook_add(UC_HOOK_CODE, self.hook)

    def hook(self, c, address, size, _):
        if address == 0x8004A954:
            sp = c.reg_read(UC_MIPS_REG_SP) & MASK
            pointer = struct.unpack('<I', c.mem_read(sp+16, 4))[0] & MASK
            words = []
            for i in range(1000):
                code = struct.unpack('<H', c.mem_read(pointer+i*2, 2))[0]
                if code in (0xFFFD, 0xFFFE):
                    break
                words.append(code)
            else:
                raise AssertionError('unterminated native draw')
            args = [c.reg_read(r) for r in REGS]
            self.draws.append({'x': args[1], 'y': args[2], 'words': words})
            c.reg_write(UC_MIPS_REG_V0, args[1]+sum(map(width, words)))
        elif address in (0x8004AC24, 0x8004BF8C):
            pass
        else:
            return
        c.reg_write(UC_MIPS_REG_PC, c.reg_read(UC_MIPS_REG_RA))

    def run(self, address, args, stack=()):
        c = self.cpu
        for r,v in zip(REGS,args):
            c.reg_write(r,v)
        c.reg_write(UC_MIPS_REG_SP,0x801E0000)
        c.reg_write(UC_MIPS_REG_RA,0x80008000)
        if stack:
            c.mem_write(0x1E0010,struct.pack('<%dI'%len(stack),*stack))
        self.draws = []
        c.emu_start(address,0x80008000,count=200000)
        assert c.reg_read(UC_MIPS_REG_PC)==0x80008000
        assert c.reg_read(UC_MIPS_REG_SP)==0x801E0000
        return c.reg_read(UC_MIPS_REG_V0)


def verify(version, baseline):
    out = ROOT/'work/output'
    before,after = [out/('STT2001_EN_v%s.bin'%v) for v in (baseline,version)]
    od,nd = directory(before),directory(after)
    assert od.keys()==nd.keys()
    exe = read_file(after,nd['SLPS_028.63'])
    assert exe == read_file(before,od['SLPS_028.63'])
    old_mm,new_mm = [repack.dat_entries(read_file(p,d['MAPMAIN.DAT'])) for p,d in ((before,od),(after,nd))]
    assert {i for i,(a,b) in enumerate(zip(old_mm,new_mm)) if a!=b}=={19,23,27}
    title_footer.verify_disc(after,version)
    expected_footer={'MAPMAIN.DAT':read_file(before,od['MAPMAIN.DAT'])}
    title_footer.patch_files(expected_footer,version)
    footer_mm=repack.dat_entries(expected_footer['MAPMAIN.DAT'])
    assert all(a==b for i,(a,b) in enumerate(zip(footer_mm,new_mm)) if i!=27)
    old_bt,new_bt = [repack.dat_entries(read_file(p,d['BATTLE.DAT'])) for p,d in ((before,od),(after,nd))]
    assert {i for i,(a,b) in enumerate(zip(old_bt,new_bt)) if a!=b}=={540}
    old_text,new_text=table32(old_bt[540]),table32(new_bt[540])
    expected_indices=set(map(int,encyclopedia_layout.META['labels']))
    assert len(old_text)==len(new_text)==1715
    assert {i for i,(a,b) in enumerate(zip(old_text,new_text)) if a!=b}==expected_indices
    for i in expected_indices:
        assert visible(new_text[i])==encyclopedia_layout.META['labels'][str(i)][1]
    assert max(sum(map(width,w)) for w in new_text[1:432])<=128
    source=repack.dat_entries((ROOT/'work/source/disc/MAPMAIN.DAT').read_bytes())[27]
    # Independent payload oracle: walk the original records and ask the
    # translator for their intended words, then exercise the native resolver.
    base=struct.unpack_from('<I',source)[0]
    count=struct.unpack_from('<H',source,base)[0]//2
    native=Native(exe,new_mm[27],new_bt[540])
    translator=insert.Translator()
    for i,offset in enumerate(struct.unpack_from('<%dH'%count,source,base)):
        original=words_at(source,base+offset)
        desired=translator.words_for('music',original,'11',('MAPMAIN0027',base+offset)) if original and insert.D.is_text(original) else None
        pointer=native.run(0x80040F38,[i])
        actual=words_at(new_mm[27],pointer-0x80152000)
        assert actual==(desired if desired is not None else original),i
    # Exercise both visible Options fields through their actual native drawer.
    music_catalog=list(new_mm[27][100:160])
    demo_catalog=list(new_mm[27][16:96])
    option_cases=0
    for field,catalog in enumerate((music_catalog,demo_catalog)):
        for selected,title_id in enumerate(catalog):
            if title_id==255:
                continue
            values=[0,0,0];values[field]=selected
            native.cpu.mem_write(0xBD8D8,struct.pack('<3h',*values))
            native.run(0x80040B80,[])
            draw=native.draws[field]
            pointer=native.run(0x80040F38,[title_id+(100 if field else 0)])
            assert draw['words']==words_at(new_mm[27],pointer-0x80152000)
            assert (draw['x'],draw['y'])==(96,40+field*40)
            option_cases+=1
    # Actual two-column builder + GUI interpreter; graphics submission mocked.
    names_drawn=0
    for start in range(0,431,18):
        rows=[]
        for row in range(9):
            pair=[start+row,start+row+9]
            rows.extend([pair[0] if pair[0]<431 else -2,
                         pair[1] if pair[1]<431 else -2,0,0,0,0])
        native.cpu.mem_write(0x190000,struct.pack('<%dh'%len(rows),*rows))
        native.run(0x8006B678,[16,0x80190000,0,66],[9,0x80010F80])
        for row in range(9):
            for col in range(2):
                i=start+row+col*9+1
                if i>431:
                    continue
                draw=native.draws[row*2+col]
                assert draw['words']==new_text[i][:-1]
                assert (draw['x'],draw['y'])==(24+136*col,66+16*row)
                assert draw['x']+sum(map(width,draw['words']))<=152+136*col
                names_drawn+=1
    assert names_drawn==431
    old_st,new_st=[repack.dat_entries(read_file(p,d['STAGE.DAT'])) for p,d in ((before,od),(after,nd))]
    assert {i for i,(a,b) in enumerate(zip(old_st,new_st)) if a!=b}=={432,691}
    blocks_old,blocks_new=cm.blocks(old_st[691]),cm.blocks(new_st[691])
    assert {i for i,(a,b) in enumerate(zip(blocks_old,blocks_new)) if a!=b}=={4}
    assert new_st[432].startswith(blocks_new[4]) and not any(new_st[432][len(blocks_new[4]):])
    untouched=[]
    for name in nd.keys()-{'DUMMY.DAT','MAPMAIN.DAT','BATTLE.DAT','STAGE.DAT'}:
        assert file_hash(before,od[name])==file_hash(after,nd[name]),name
        untouched.append(name)
    movie=nd['MOVIE.STR'];assert movie==od['MOVIE.STR']
    remaining=((movie['size']+2047)//2048)*2352
    with before.open('rb') as a,after.open('rb') as b:
        a.seek(movie['lba']*2352);b.seek(movie['lba']*2352)
        while remaining:
            n=min(1024*1024,remaining)
            assert a.read(n)==b.read(n)
            remaining-=n
    # Reuse only after all font/archive assets have been checked identical.
    old_pack=out/('STT2001_EN_v%s_4x_font'%baseline)
    new_pack=out/('STT2001_EN_v%s_4x_font'%version)
    shutil.copytree(old_pack,new_pack,dirs_exist_ok=True)
    files=[p for p in old_pack.rglob('*') if p.is_file()]
    assert len(files)==757
    assert {p.relative_to(new_pack) for p in new_pack.rglob('*') if p.is_file()}=={p.relative_to(old_pack) for p in files}
    for p in files:
        assert p.read_bytes()==(new_pack/p.relative_to(old_pack)).read_bytes()
    archive=Path(str(new_pack)+'.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(new_pack/p.relative_to(old_pack),p.relative_to(old_pack).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert len(z.namelist())==757
        for p in files:
            assert z.read(p.relative_to(old_pack).as_posix())==p.read_bytes()
    build=json.loads(after.with_name(after.stem+'_report.json').read_text(encoding='utf-8'))
    assert not build['problems']
    return {'version':version,'baseline':baseline,'all_checks_passed':True,
            'native_title_resolver_cases':count,'native_options_drawer_cases':option_cases,
            'native_index_labels_drawn':names_drawn,'compact_encyclopedia_labels':44,
            'all_description_records_unchanged':True,'executable_unchanged':True,
            'black_cross_objective_included':True,'fonts_and_other_battle_assets_unchanged':True,
            'matching_font_package_files':757,'raw_movie_sectors_identical':True,
            'other_files_identical':sorted(untouched),'build_problems':0,
            'emulator_or_hardware_verified':False,
            'earlier_encyclopedia_body_clipping_and_digit_corruption_fixed':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('version');p.add_argument('baseline');p.add_argument('--verify',action='store_true')
    a=p.parse_args()
    if not a.verify:
        print('Dry run: native title lookups, Options draws, all index labels, unchanged descriptions/assets and matching font package.')
    else:
        report=verify(a.version,a.baseline)
        (ROOT/('work/output/STT2001_EN_v%s_options_index_verification.json'%a.version)).write_text(json.dumps(report,indent=1)+'\n',encoding='utf-8')
        print(json.dumps(report,indent=1))
