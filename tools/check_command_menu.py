"""Execute native command-menu placement/drawing; dry run unless --verify.

The completed-disc audit allows only the command frame/highlight patch and
the automatically updated title version. All names and other files must match.
"""
import argparse
import itertools
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS32, UC_MODE_LITTLE_ENDIAN, UC_HOOK_CODE
from unicorn.mips_const import UC_MIPS_REG_SP, UC_MIPS_REG_RA, UC_MIPS_REG_PC, UC_MIPS_REG_V0

import command_menu as FIX
import mips
import repack
import title_footer
import gfx
import texpack
from check_graphics_build import directory, read_file, file_hash
from check_stats_layout import ARGS, MASK
from check_ui_labels import strings
from check_intermission_layout import text
from check_dialogue_layout import width

ROOT = Path(__file__).resolve().parents[1]


class MenuCPU:
    def __init__(self, exe, db):
        self.cpu = cpu = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 | UC_MODE_LITTLE_ENDIAN)
        cpu.mem_map(0, 0x200000)
        cpu.mem_write(0x10000, exe[0x800:])
        cpu.mem_write(0xF3000, db)
        self.transform_table = exe[mips.off(0x800AE478):mips.off(0x800AE478)+512]
        self.frames, self.draws, self.highlights = [], [], []
        cpu.hook_add(UC_HOOK_CODE, self.hook)

    def word(self, address):
        return struct.unpack('<I', self.cpu.mem_read(address & MASK, 4))[0]

    def hook(self, cpu, address, size, unused):
        a = [cpu.reg_read(r) for r in ARGS]
        sp = cpu.reg_read(UC_MIPS_REG_SP)
        if address == 0x80041F04:
            self.frames.append({'width': a[1], 'height': a[2], 'x': a[3], 'y': self.word(sp+16)})
        elif address == 0x8004A954:
            pointer = self.word(sp+16) & MASK
            codes = []
            for i in range(200):
                code = struct.unpack('<H', cpu.mem_read(pointer+i*2, 2))[0]
                if code in (0xFFFE, 0xFFFD):
                    break
                codes.append(code)
            else:
                raise AssertionError('unterminated menu label')
            self.draws.append({'x': a[1], 'y': a[2], 'codes': codes})
        elif address == 0x800423C0:
            self.highlights.append(a[1])
        elif address not in (0x800428A0, 0x8004CAD8, 0x8004A1C4):
            return
        cpu.reg_write(UC_MIPS_REG_V0, 0)
        cpu.reg_write(UC_MIPS_REG_PC, cpu.reg_read(UC_MIPS_REG_RA))

    def call(self, address, args, stop=0x80008000):
        cpu = self.cpu
        self.frames, self.draws, self.highlights = [], [], []
        for reg, value in zip(ARGS, args):
            cpu.reg_write(reg, value & 0xFFFFFFFF)
        cpu.reg_write(UC_MIPS_REG_SP, 0x801E0000)
        cpu.reg_write(UC_MIPS_REG_RA, 0x80008000)
        cpu.emu_start(address, stop, count=40000)
        assert cpu.reg_read(UC_MIPS_REG_PC) == stop
        if stop == 0x80008000:
            assert cpu.reg_read(UC_MIPS_REG_SP) == 0x801E0000

    def frame(self, menu, x, y, count, extra, capacity):
        self.cpu.mem_write((menu+4) & MASK, struct.pack('<h', count))
        self.cpu.mem_write((menu+10) & MASK, struct.pack('<hhh', x, 100, capacity))
        self.call(FIX.START, (menu, y, extra))
        assert len(self.frames) == 1
        stored = struct.unpack('<hh', self.cpu.mem_read((menu+10) & MASK, 4))
        return self.frames[0], stored

    def labels(self, mask, actor=0, flag=0, form=None):
        cpu = self.cpu
        cpu.mem_write(0xBD460, struct.pack('<I', 0))
        cpu.mem_write(0xBD358, struct.pack('<I', 0x80110000))
        cpu.mem_write(0xBD350, struct.pack('<I', 0x80100000))
        cpu.mem_write(0x110000, bytes([0, 0, 0, 0]))
        cpu.mem_write(0x101568, bytes([actor]))
        cpu.mem_write(0x1004AC, bytes([flag])*256)
        cpu.mem_write(0xAE478, self.transform_table)
        if form is not None:
            cpu.mem_write(0xAE478+actor*2, bytes([form]))
        self.call(0x800397C8, (mask, 24, 40))
        return list(self.draws)


def tests(before, after, db):
    # PS1 has a load delay which Unicorn does not model. In this helper all
    # loads must have an independent following instruction and must never
    # occur in a branch delay slot (whose successor can be the branch target).
    instructions = list(mips.md.disasm(after[mips.off(FIX.START):mips.off(FIX.END)], FIX.START))
    loads = 0
    for i, ins in enumerate(instructions):
        if ins.mnemonic in ('lh', 'lhu', 'lw', 'lb', 'lbu'):
            register = ins.op_str.split(',')[0].strip()
            assert register not in instructions[i+1].op_str, 'PS1 load-use delay hazard'
            assert instructions[i-1].mnemonic not in ('beq', 'bne', 'beqz', 'bnez', 'j', 'jal', 'jr')
            loads += 1
    assert loads == 3
    old, new = MenuCPU(before, db), MenuCPU(after, db)
    frame_cases = 0
    for menu, x, y, count, extra in itertools.product(
            (FIX.MENU, FIX.MENU+28, FIX.MENU+56),
            (-32, 0, 8, 24, 100, 168, 200, 296, 320),
            (0, 8, 24, 100, 200, 240), (1, 2, 4, 6, 8, 10, 12), (0, 16, 32)):
        a, sa = old.frame(menu, x, y, count, extra, 64)
        b, sb = new.frame(menu, x, y, count, extra, 128 if menu == FIX.MENU else 64)
        if menu == FIX.MENU:
            assert b['width'] == a['width']+FIX.DELTA
            assert b['height'] == a['height'] and b['y'] == a['y'] and sb[1] == sa[1], (x, y, count, extra, a, sa, b, sb)
            assert 8 <= b['x'] and b['x']+b['width'] <= 312
            assert sb[0] == b['x']+16
        else:
            assert (a, sa) == (b, sb), 'unrelated submenu changed'
        frame_cases += 1
    # Execute the actual cursor initializer through its first width submission.
    new.cpu.mem_write((FIX.MENU+14) & MASK, struct.pack('<H', FIX.TEXT_WIDTH))
    new.call(0x80041960, (FIX.MENU, 19), stop=0x80041A08)
    assert new.highlights == [128], new.highlights
    # All static command bits plus every vehicle/form state and flag polarity.
    table = before[mips.off(0x800B01B4):mips.off(0x800B0204)]
    actors = sorted({table[i] for i in range(0, len(table), 4)})
    scenarios = [(1 << bit, 0, 0, None) for bit in range(32)]
    scenarios += [(1 << 15, actor, flag, None) for actor in actors for flag in (0, 255)]
    transforms = before[mips.off(0x800A7618):mips.off(0x800A7618)+40]
    scenarios += [(1 << 4, actor, 0, form) for actor, form in zip(transforms[::2], transforms[1::2])]
    found, widest = set(), 0
    for scenario in scenarios:
        a, b = old.labels(*scenario), new.labels(*scenario)
        assert a == b, 'command content/order/positions changed'
        for row in b:
            w = sum(width(c) for c in row['codes'])
            assert w <= FIX.TEXT_WIDTH, (text(row['codes']), w)
            widest = max(widest, w)
            found.add(text(row['codes']))
    reported = ('Double Machine', 'Grand Birth', 'Moto-Sharian', 'Battle Hopper', 'Riderman Machine')
    assert all(name in found for name in reported), found
    return {'native_frame_cases': frame_cases, 'native_command_draw_cases': len(scenarios),
            'ps1_load_delays_checked': loads,
            'command_labels_checked': len(found), 'maximum_command_width': widest,
            'text_and_highlight_width': 128, 'base_frame_width': 160,
            'reported_names_preserved': list(reported), 'all_command_names_and_order_unchanged': True,
            'unrelated_submenu_frames_unchanged': True, 'native_highlight_width_verified': True,
            'horizontal_frame_bounds': [8, 312], 'vertical_placement_unchanged': True}


def previews(entries, version):
    """Draw measured frames and completed native glyphs, not emulator captures."""
    rows = strings(entries[2])
    pixels = gfx.Tim(entries[7]).idx
    image = Image.new('RGB', (640, 480), (20, 27, 34))
    draw = ImageDraw.Draw(image)
    records = []
    cases = [('Double Machine', 0x4E, True), ('Grand Birth / Moto-Sharian', 0x3E, False),
             ('Battle Hopper', 0x7D, True)]
    def lettering(codes, x, y):
        for code in codes:
            if code >= 0xFF00:
                continue
            advance = width(code)
            if code < 320:
                page, layer, u, v = 0, 0, code % 32 * 8, code // 32 * 16
            else:
                page, layer, u, v = texpack.cell_xy(code)
            cell = (pixels[v:v+16, page*256+u:page*256+u+advance] >> (layer*2)) & 3
            for cy, cx in zip(*np.nonzero(cell)):
                image.putpixel((x+int(cx), y+int(cy)), [(0, 0, 0), (25, 25, 25), (154, 154, 154), (245, 245, 245)][int(cell[cy, cx])])
            x += advance
    for row, (name, vehicle, henshin) in enumerate(cases):
        indices = [0xB4C, 0xB4D, 0xB50, vehicle, 0xB5C, 0xB5E] if henshin else [0xB4C, 0x966, vehicle, 0xB5C, 0xB5E]
        for column, capacity in enumerate((64, 128)):
            x, y = 84+column*320, 30+row*160
            draw.text((8+column*320, 6+row*160), '%s: %s' % ('Before' if not column else 'v'+version, name), fill=(235, 235, 235))
            draw.rectangle((x, y, x+capacity+31, y+len(indices)*16+23), fill=(57, 38, 29), outline=(182, 183, 196), width=2)
            draw.rectangle((x+16, y+12, x+16+capacity-1, y+27), fill=(0, 154, 8))
            for n, index in enumerate(indices):
                lettering(rows[index], x+16, y+12+n*16)
                if column:
                    records.append({'sample': name, 'database_index': index, 'text': text(rows[index]),
                                    'width': sum(width(c) for c in rows[index]), 'available_width': capacity})
    dest = ROOT/'work/ui/command_menu'
    dest.mkdir(parents=True, exist_ok=True)
    image.resize((1280, 960), Image.Resampling.NEAREST).save(dest/('comparison_v%s.png' % version))
    (dest/'layout.en.json').write_text(json.dumps({'version': version, 'preview_is_reconstruction_not_emulator_capture': True,
             'native_text_width_before': 64, 'native_text_width_after': 128,
             'native_frame_width_before': 96, 'native_frame_width_after': 160,
             'native_frame_x_bounds': [8, 312], 'screenshots': ['reported_double_machine.png', 'reported_sharivan.png', 'reported_battle_hopper.png'],
             'labels': records}, indent=1)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', nargs='?', default='0.3.21')
    parser.add_argument('baseline', nargs='?', default='0.3.20')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    out = ROOT/'work/output'
    old = out/('STT2001_EN_v%s.bin' % args.baseline)
    od = directory(old)
    before = read_file(old, od['SLPS_028.63'])
    mm = read_file(old, od['MAPMAIN.DAT'])
    db = repack.dat_entries(mm)[2]
    proposed = FIX.patch_exe(before)
    report = tests(before, proposed, db)
    print(json.dumps(report, indent=1), flush=True)
    if not args.verify:
        print('Dry run: actual MIPS routines tested in memory; no files written.')
        return
    new = out/('STT2001_EN_v%s.bin' % args.version)
    nd = directory(new)
    assert od.keys() == nd.keys()
    assert read_file(new, nd['SLPS_028.63']) == proposed, 'unexpected executable changes'
    expected = {'MAPMAIN.DAT': mm}
    title_footer.patch_files(expected, args.version)
    assert read_file(new, nd['MAPMAIN.DAT']) == expected['MAPMAIN.DAT'], 'unexpected title/database changes'
    title_footer.verify_disc(new, args.version)
    unchanged = []
    for name in nd:
        if name in ('SLPS_028.63', 'MAPMAIN.DAT', 'DUMMY.DAT'):
            continue
        assert od[name]['size'] == nd[name]['size'] and file_hash(old, od[name]) == file_hash(new, nd[name]), name
        unchanged.append(name)
    movie = nd['MOVIE.STR']
    assert movie == od['MOVIE.STR']
    remaining = ((movie['size']+2047)//2048)*2352
    with old.open('rb') as a, new.open('rb') as b:
        a.seek(movie['lba']*2352); b.seek(movie['lba']*2352)
        while remaining:
            size = min(1024*1024, remaining)
            assert a.read(size) == b.read(size), 'movie sectors changed'
            remaining -= size
    packs = [out/('STT2001_EN_v%s_4x_font' % v)/'SLPS-02863' for v in (args.baseline, args.version)]
    files = [{p.relative_to(folder).as_posix(): p for p in folder.rglob('*') if p.is_file()} for folder in packs]
    assert files[0].keys() == files[1].keys() and len(files[1]) == 757
    assert all(files[0][name].read_bytes() == files[1][name].read_bytes() for name in files[0])
    build = json.loads((out/('STT2001_EN_v%s_report.json' % args.version)).read_text(encoding='utf-8'))
    assert build['version'] == args.version and not build['problems'] and build['title_footer_verified']
    report.update({'version': args.version, 'baseline': args.baseline, 'all_checks_passed': True,
                   'unchanged_files': unchanged, 'database_and_names_identical': True,
                   'raw_movie_sectors_identical': True, 'matching_font_pack_files': 757,
                   'font_pack_identical_to_previous_build': True, 'build_problems': 0,
                   'emulator_or_hardware_verified': False})
    previews(repack.dat_entries(read_file(new, nd['MAPMAIN.DAT'])), args.version)
    (out/('STT2001_EN_v%s_command_menu_verification.json' % args.version)).write_text(json.dumps(report, indent=1)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
