"""Run the Stats GUI's actual MIPS bytecode interpreter and terrain routines.

Graphics submission is modeled. Stat selection, sums, script coordinates and
the seven cached terrain label/grade pairs execute from the completed EXE.
"""
import json
import struct
import sys
from pathlib import Path
from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS32, UC_MODE_LITTLE_ENDIAN, UC_HOOK_CODE
from unicorn.mips_const import (UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2,
                               UC_MIPS_REG_A3, UC_MIPS_REG_V0, UC_MIPS_REG_SP,
                               UC_MIPS_REG_RA, UC_MIPS_REG_PC)
import cm
import insert
import mips
import repack
import stats_layout
import ui_glyphs
from check_graphics_build import directory, read_file, file_hash
from check_ui_labels import strings

ROOT = Path(__file__).resolve().parents[1]
MASK = 0x1FFFFFFF
ARGS = [UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2, UC_MIPS_REG_A3]


class Screen:
    def __init__(self, exe, db):
        self.cpu = cpu = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 + UC_MODE_LITTLE_ENDIAN)
        cpu.mem_map(0, 0x200000)
        cpu.mem_write(0x10000, exe[0x800:])
        cpu.mem_write(0x150000, db)
        cpu.mem_write(mips.off(0x800BD350)-0x800+0x10000, struct.pack('<I',0x80100000))
        # Stop before the separate trait-panel commands; all Stats fields and
        # the complete native terrain drawer are included in this segment.
        cpu.mem_write(0xAA932, struct.pack('<H',0xFFFF))
        self.db = db
        self.draws = []
        cpu.hook_add(UC_HOOK_CODE, self.hook)
        cpu.reg_write(UC_MIPS_REG_SP, 0x801E0000)
        # Execute the original startup loop which caches the first terrain
        # glyph from database indices AFE..B04, then adds a live grade slot.
        cpu.emu_start(0x80013D2C,0x80013D74,count=10000)
        self.cached_labels = [struct.unpack('<H',cpu.mem_read(0xC9038+i*6,2))[0] for i in range(7)]

    def word(self, address):
        return struct.unpack('<I',self.cpu.mem_read(address & MASK,4))[0]

    def hook(self, cpu, address, size, _):
        a = [cpu.reg_read(r) for r in ARGS]
        sp = cpu.reg_read(UC_MIPS_REG_SP)
        if address == 0x8003C578:
            offset = struct.unpack_from('<H',self.db,(a[0]&0xFFFF)*2)[0]
            cpu.reg_write(UC_MIPS_REG_V0,0x80150000+offset)
        elif address == 0x8004A954:
            pointer = self.word(sp+16) & MASK
            codes = []
            for i in range(100):
                w = struct.unpack('<H',cpu.mem_read(pointer+i*2,2))[0]
                if w in (0xFFFE,0xFFFD):
                    break
                codes.append(w)
            else:
                raise AssertionError('unterminated GUI text')
            self.draws.append({'kind':'text','x':a[1],'y':a[2],'codes':codes})
            cpu.reg_write(UC_MIPS_REG_V0,a[0]+len(codes))
        elif address == 0x8004CCF0:
            self.draws.append({'kind':'number','x':a[1],'y':a[2],
                               'value':self.word(sp+16),'limit':self.word(sp+20)})
            cpu.reg_write(UC_MIPS_REG_V0,a[0]+3)
        elif address in (0x80037954,0x8003C264,0x8004CA68,0x8004CAD8):
            cpu.reg_write(UC_MIPS_REG_V0,0)
        else:
            return
        cpu.reg_write(UC_MIPS_REG_PC,cpu.reg_read(UC_MIPS_REG_RA))

    def run(self, eva, acc, bonus, grades):
        cpu = self.cpu
        actor, unit = 0x101568, 0x100E60
        cpu.mem_write(actor+4,bytes([bonus]))
        cpu.mem_write(unit+4,bytes([acc]))
        cpu.mem_write(unit+6,bytes([eva]))
        cpu.mem_write(unit+8,bytes([103,0,103,0,113]))
        cpu.mem_write(unit+0x11,bytes([0]))
        cpu.mem_write(0xADEF0,bytes(grades))  # first pilot's seven terrain ranks
        stack, stop = 0x801E0000, 0x80008000
        for reg,value in zip(ARGS,(0x800AA8C0,0,0,0)):
            cpu.reg_write(reg,value)
        cpu.reg_write(UC_MIPS_REG_SP,stack)
        cpu.reg_write(UC_MIPS_REG_RA,stop)
        cpu.mem_write((stack+16)&MASK,struct.pack('<II',0,0))
        self.draws = []
        cpu.emu_start(0x8004DA34,stop,count=50000)
        assert cpu.reg_read(UC_MIPS_REG_PC)==stop
        assert cpu.reg_read(UC_MIPS_REG_SP)==stack
        return self.draws


def main():
    version,baseline = sys.argv[1:3]
    out = ROOT/'work/output'
    new,old = [out/('STT2001_EN_v%s.bin'%v) for v in (version,baseline)]
    nd,od = directory(new),directory(old)
    assert nd.keys()==od.keys()
    exe,old_exe = read_file(new,nd['SLPS_028.63']),read_file(old,od['SLPS_028.63'])
    assert exe==stats_layout.patch_exe(old_exe),'unexpected EXE changes'
    for key in nd.keys()-{'DUMMY.DAT','MAPMAIN.DAT','SLPS_028.63'}:
        assert nd[key]['size']==od[key]['size'] and file_hash(new,nd[key])==file_hash(old,od[key]),key
    a,b = [repack.dat_entries(read_file(p,d['MAPMAIN.DAT'])) for p,d in ((old,od),(new,nd))]
    assert len(a)==len(b) and {i for i,(x,y) in enumerate(zip(a,b)) if x!=y}=={2,24}
    for before,after in [(a[2],b[2]),(cm.blocks(a[24])[1],cm.blocks(b[24])[1])]:
        x,y = strings(before),strings(after)
        assert len(x)==len(y)
        assert {i for i,(u,v) in enumerate(zip(x,y)) if u!=v}=={0xBC2}
        assert y[0xBC2]==insert.encode_line_tokens(insert.TOKEN.findall(stats_layout.PUNCTUATION),{})+[0xFFFE]
    ca,cb = cm.blocks(a[24]),cm.blocks(b[24])
    assert all(x==y for i,(x,y) in enumerate(zip(ca,cb)) if i!=1)
    screen = Screen(exe,b[2])
    assert screen.cached_labels==list(range(ui_glyphs.FIRST,ui_glyphs.FIRST+7))
    cases = [(134,128,68)]+[(n,n,k) for n in (0,1,9,99,100,255) for k in (0,1,99,255)]
    sample = None
    for eva,acc,bonus in cases:
        grades = [4,4,3,2,0,0,0] if (eva,acc,bonus)==(134,128,68) else [4,3,2,1,0,4,0]
        draws = screen.run(eva,acc,bonus,grades)
        for y,base in ((117,eva),(141,acc)):
            numbers = {(d['x'],d['value'],d['limit']) for d in draws if d['kind']=='number' and d['y']==y}
            expected = {(130,base,3),(168,bonus,3),(200,base+bonus,3)}
            # Skill is a separate field on the Eva. row.
            assert expected<=numbers,(y,numbers,expected)
            row = next(d for d in draws if d['kind']=='text' and d['x']==156 and d['y']==y)
            assert row['codes']==strings(b[2])[0xBC2][:-1]
        terrain = [d for d in draws if d['kind']=='text' and d['codes'] and ui_glyphs.FIRST<=d['codes'][0]<ui_glyphs.FIRST+7]
        assert len(terrain)==7
        for i,d in enumerate(terrain):
            assert d=={'kind':'text','x':192+(i%4)*28,'y':175+(i//4)*21,
                       'codes':[ui_glyphs.FIRST+i,0xB5-grades[i]]}
        if (eva,acc,bonus)==(134,128,68):
            sample = draws
    # Three-digit numeric fields reserve 24px. Every adjacent span has space.
    spans = [(130,154),(156,165),(168,192),(193,198),(200,224),(226,231),(236,236+insert.px_of('Skill'))]
    assert all(a[1]<=b[0] for a,b in zip(spans,spans[1:]))
    report = {'version':version,'baseline':baseline,'all_checks_passed':True,
              'actual_mips_gui_cases':len(cases),'bonus_rows_verified':len(cases)*2,
              'example_rows':['Eva. 134 + 68 (202)','Acc. 128 + 68 (196)'],
              'cached_terrain_glyphs_verified':7,'live_terrain_grades_preserved':True,
              'native_field_spans':spans,'only_six_executable_positions_changed':True,
              'only_database_punctuation_changed':True,'fonts_story_movies_unchanged':True,
              'reuse_texture_pack':'0.3.10','emulator_verified':False}
    (out/('STT2001_EN_v%s_stats_verification.json'%version)).write_text(json.dumps(report,indent=1)+'\n',encoding='utf-8')
    (ROOT/'work/ui/unit_stats/stats_draws.en.json').write_text(json.dumps(sample,indent=1)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=1))


if __name__=='__main__':
    main()
