"""Audit battle caption origins, actual MIPS text placement and completed disc."""
import json
import shutil
import struct
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS32, UC_MODE_LITTLE_ENDIAN, UC_HOOK_CODE
from unicorn.mips_const import *

import battle_voice_layout as B
import dump_script as D
import efont
import insert
import mips
import repack
from check_dialogue_layout import check_words, content
from check_graphics_build import directory, read_file, file_hash

ROOT = Path(__file__).resolve().parents[1]
MASK = 0x1FFFFFFF
ARGS = (UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2, UC_MIPS_REG_A3)


class Cpu:
    def __init__(self, exe):
        self.cpu = c = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 + UC_MODE_LITTLE_ENDIAN)
        c.mem_map(0, 0x200000)
        c.mem_write(0x10000, exe[0x800:])
        c.reg_write(UC_MIPS_REG_GP, 0x80170000)
        self.init = []
        self.draws = []
        c.hook_add(UC_HOOK_CODE, self.hook)

    def hook(self, c, address, size, _):
        a = [c.reg_read(r) for r in ARGS]
        if address in (0x80058DE8, 0x8004C730):
            self.init.append(a)
        elif address == 0x8004C840:
            c.reg_write(UC_MIPS_REG_V0, 0)
        elif address == 0x8004BE94:
            c.reg_write(UC_MIPS_REG_V0, 0x80150000+len(self.draws)*36)
        elif address == 0x8004A7D8:
            x, y = struct.unpack('<HH', c.mem_read(0xC6B9A, 4))
            self.draws.append((a[1], x, y))
            return  # Execute the real glyph lookup and width table.
        else:
            return
        c.reg_write(UC_MIPS_REG_PC, c.reg_read(UC_MIPS_REG_RA))

    def run(self, address, args=(0, 0, 0, 0), extra=(0, 0)):
        c = self.cpu
        for r, v in zip(ARGS, args):
            c.reg_write(r, v)
        c.reg_write(UC_MIPS_REG_SP, 0x801E0000)
        c.reg_write(UC_MIPS_REG_RA, 0x80008000)
        c.mem_write(0x1E0010, struct.pack('<II', *extra))
        c.emu_start(address, 0x80008000, count=500000)
        assert c.reg_read(UC_MIPS_REG_PC) == 0x80008000

    def origins(self, command, mode, side):
        c = self.cpu
        c.mem_write(0xCC670, struct.pack('<I', 0x801F0000))
        c.mem_write(0xCC6B2, bytes(2))
        c.mem_write(0xCDEA4, bytes([mode]))
        c.mem_write(0x1F0000, bytes([0, 0, 0, side, 0, 0, 0, 0]))
        self.init = []
        self.run(command)
        assert len(self.init) == 1
        return self.init[0]

    def text(self, words, y):
        words = list(words)
        c = self.cpu
        c.mem_write(0xC6B88, bytes(44))
        c.mem_write(0x170120, struct.pack('<I', 0x80120000))
        c.mem_write(0x120000, struct.pack('<II', 0x800E0100, 0x800E0200))
        c.mem_write(0x120100, struct.pack('<%dH' % (len(words)+1), *(words+[0xFFFD])))
        self.run(0x8004A0D8, (0, 72, y, 272), (240, 0))
        c.mem_write(0xC6BA4, bytes([0]))  # Instant text; only suppress the delay.
        self.draws = []
        self.run(0x8004B92C)
        return self.draws


def main():
    version, baseline = sys.argv[1:3]
    out = ROOT/'work/output'
    old, new = [out/('STT2001_EN_v%s.bin' % v) for v in (baseline, version)]
    od, nd = directory(old), directory(new)
    a, b = [read_file(p, d['SLPS_028.63']) for p, d in ((old, od), (new, nd))]
    assert b == B.patch_exe(a)
    assert od.keys() == nd.keys()
    unchanged = []
    for key in nd.keys()-{'SLPS_028.63', 'DUMMY.DAT'}:
        assert od[key]['size'] == nd[key]['size'] and file_hash(old, od[key]) == file_hash(new, nd[key]), key
        unchanged.append(key)
    c = Cpu(b)
    cases = []
    for command in (0x8007348C, 0x80079EE4):
        for mode in (0, 1):
            for side in (0, 1):
                args = c.origins(command, mode, side)
                expected = (22, 154) if mode == 0 else (44, 176)
                assert args[1] == 72 and args[2] == expected[side], args
                cases.append({'command': hex(command), 'mode': mode, 'side': side, 'y': args[2]})
    battle = repack.dat_entries(read_file(new, nd['BATTLE.DAT']))
    words = next(ws for _, ws, _ in D.overlay_strings(battle[61], 0x8434)
                 if content(ws) == 'LucifardComeforth,steelblade!UltrasonicBlade!!')
    bottom = c.text(words, 176)
    assert sorted({y for _, _, y in bottom}) == [176, 192, 208]
    top = c.text(words, 44)
    assert sorted({y for _, _, y in top}) == [44, 60, 76]
    # Entire native glyph rectangles, including 4x replacements, clear the frame.
    assert max(y+16 for _, _, y in bottom) == 224
    assert max(y+16 for _, _, y in top) == 92
    stats = Counter()
    for data in battle:
        if len(data)>0x8438 and data[:4]==b'\x10\0\0\0' and struct.unpack_from('<I',data,0x8434)[0]>>16==0x800E:
            for _, ws, _ in D.overlay_strings(data, 0x8434):
                check_words(ws, 'bquote', stats)
    assert stats['bquote_strings'] == 12617
    src, dst = [out/('STT2001_EN_v%s_4x_font' % v) for v in (baseline, version)]
    shutil.copytree(src, dst, dirs_exist_ok=True)
    names = {p.relative_to(src) for p in src.rglob('*') if p.is_file()}
    assert names == {p.relative_to(dst) for p in dst.rglob('*') if p.is_file()}
    assert all((src/n).read_bytes() == (dst/n).read_bytes() for n in names)
    preview(bottom)
    report = {'version': version, 'baseline': baseline, 'all_checks_passed': True,
              'actual_mips_origin_cases': cases, 'actual_typewriter_lower_rows': [176,192,208],
              'actual_typewriter_upper_rows': [44,60,76], 'glyph_height':16,
              'other_text_fonts_graphics_movies_unchanged': True,
              'battle_quote_checks': dict(stats), 'unchanged_files': sorted(unchanged),
              'texture_pack_identical_files':len(names), 'emulator_verified':False}
    (out/('STT2001_EN_v%s_battle_voice_verification.json' % version)).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


def preview(draws):
    # Actual MIPS positions on a schematic frame, using the existing English cells.
    z = np.load(ROOT/'work/font/efont_cells.npz')
    im = Image.new('RGB', (320, 72), (0,0,0))
    d = ImageDraw.Draw(im)
    d.rectangle((0,8,319,63),fill=(45,31,23),outline=(175,175,190),width=2)
    for code,x,y in draws:
        if 320<=code<446: cell=z['uni'][code-320]
        elif 446<=code<782: cell=z['ex'][code-446]
        else: cell=z['bi'][code-782]
        yy=y-164
        pal=np.array([(45,31,23),(65,65,65),(165,165,165),(240,240,240)],np.uint8)
        if y==176: pal[3]=(255,220,40)
        patch=Image.fromarray(pal[cell]); im.paste(patch,(x,yy))
    im.resize((960,216),Image.Resampling.NEAREST).save(ROOT/'work/ui/dialogue/battle_voice_layout.png')


if __name__=='__main__':
    main()
