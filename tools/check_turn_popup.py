"""Execute original/patched MIPS number drawers and compare produced sprites.

Graphics allocation/placement calls are modeled; the actual MIPS arithmetic,
loops, stack, branches and register restoration execute in Unicorn.
python tools/check_turn_popup.py [build-version baseline-version]
"""
import json
import struct
import sys
from pathlib import Path

from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS32, UC_MODE_LITTLE_ENDIAN, UC_HOOK_CODE
from unicorn.mips_const import (UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2,
                               UC_MIPS_REG_A3, UC_MIPS_REG_V0, UC_MIPS_REG_SP,
                               UC_MIPS_REG_RA, UC_MIPS_REG_PC, UC_MIPS_REG_S0)
import mips
import turn_popup

ROOT = Path(__file__).resolve().parents[1]
CPUS = {}


def run(exe, number, limit, x=160, color=0, layer=0, sprite_id=11):
    new_cpu = exe not in CPUS
    if new_cpu:
        cpu = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 + UC_MODE_LITTLE_ENDIAN)
        cpu.mem_map(0, 0x200000)
        cpu.mem_write(0x10000, exe[0x800:])
        CPUS[exe] = cpu
    cpu = CPUS[exe]
    stack = 0x801E0000
    stop = 0x80008000
    regs = [UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2, UC_MIPS_REG_A3]
    for reg, value in zip(regs, (sprite_id, x, 112, color)):
        cpu.reg_write(reg, value)
    cpu.reg_write(UC_MIPS_REG_SP, stack)
    cpu.reg_write(UC_MIPS_REG_RA, stop)
    saved = [0x12340000+i for i in range(8)]
    for i, value in enumerate(saved):
        cpu.reg_write(UC_MIPS_REG_S0+i, value)
    cpu.mem_write((stack+16)&0x1fffffff, struct.pack('<III', number & 0xffffffff, limit, layer))
    sprites, codes = [], []
    cpu.test_state = (sprites, codes, sprite_id, layer, color)

    def hook(uc, address, size, data):
        sprites, codes, sprite_id, layer, color = uc.test_state
        args = [uc.reg_read(r) for r in regs]
        if address == 0x8004C0EC:
            pointer = 0x80190000 + len(sprites)*64
            uc.mem_write(pointer&0x1fffffff, bytes(64))
            uc.reg_write(UC_MIPS_REG_V0, pointer)
        elif address == 0x8004A7D8:
            codes.append(args[1])
            uc.mem_write((args[0]+8)&0x1fffffff, struct.pack('<HH', 8, 16))
            uc.mem_write((args[0]+18)&0x1fffffff, struct.pack('<H', 240))
        elif address == 0x8004D834:
            sx = struct.unpack('<h', uc.mem_read(args[1]&0x1fffffff, 2))[0]
            sy = struct.unpack('<h', uc.mem_read(args[2]&0x1fffffff, 2))[0]
            sprites.append({'code': codes[-1], 'x': sx, 'y': sy,
                            'id': sprite_id, 'layer': layer, 'color': color})
            advance = args[3] if args[3] < 0x80000000 else args[3]-0x100000000
            uc.mem_write(args[1]&0x1fffffff, struct.pack('<h', sx+advance))
        else:
            return
        uc.reg_write(UC_MIPS_REG_PC, uc.reg_read(UC_MIPS_REG_RA))

    if new_cpu:
        cpu.hook_add(UC_HOOK_CODE, hook)
    cpu.emu_start(turn_popup.DRAW, stop, count=10000)
    assert cpu.reg_read(UC_MIPS_REG_PC) == stop, 'drawer did not return'
    assert cpu.reg_read(UC_MIPS_REG_SP) == stack, 'stack not restored'
    assert [cpu.reg_read(UC_MIPS_REG_S0+i) for i in range(8)] == saved
    return sprites, cpu.reg_read(UC_MIPS_REG_V0)


def main():
    original = mips.load()
    patched = turn_popup.patch_exe(original)
    count = 0
    for n in (-2147483648, -101, -1, 0, 1, 9, 10, 99, 100, 999, 1000,
              9999, 10000, 65535, 2147483647):
        for limit in (0, 1, 2, 3, 4, 5, 8, 127, 128, 255):
            for color, layer in ((0, 0), (3, 1), (7, 2)):
                assert run(original, n, limit, color=color, layer=layer) == run(
                    patched, n, limit, color=color, layer=layer), (n, limit, color, layer)
                count += 1
    # Check every turn representable by the original four-digit field.
    for n in range(10000):
        sprites, _ = run(patched, n, 0x84)
        ordered = sorted(sprites, key=lambda s: s['x'])
        assert ''.join(str(s['code']-1) for s in ordered) == str(n), n
        assert [s['x'] for s in ordered] == list(range(160, 160+8*len(str(n)), 8)), n
    report = {'ordinary_numeric_cases_equal': count, 'turn_values_verified': 10000,
              'label': 'Turn', 'label_x': 124, 'label_width': 30,
              'number_x': 160, 'gap_pixels': 6, 'maximum_number_right': 192,
              'emulator_verified': False}
    if len(sys.argv) > 1:
        from check_graphics_build import directory, read_file, file_hash
        import insert
        import repack
        import cm
        version, baseline = sys.argv[1:3]
        out = ROOT/'work/output'
        new = out/('STT2001_EN_v%s.bin' % version)
        old = out/('STT2001_EN_v%s.bin' % baseline)
        nd, od = directory(new), directory(old)
        exe = read_file(new, nd['SLPS_028.63'])
        old_exe = read_file(old, od['SLPS_028.63'])
        assert exe == turn_popup.patch_exe(old_exe), 'unexpected executable changes'
        for key in nd.keys()-{'DUMMY.DAT', 'MAPMAIN.DAT', 'SLPS_028.63'}:
            assert nd[key]['size'] == od[key]['size'] and file_hash(new, nd[key]) == file_hash(old, od[key]), key
        nm = repack.dat_entries(read_file(new, nd['MAPMAIN.DAT']))
        om = repack.dat_entries(read_file(old, od['MAPMAIN.DAT']))
        assert len(nm) == len(om)
        assert [i for i, (a, b) in enumerate(zip(nm, om)) if a != b] == [2, 24]
        db = nm[2]
        p = struct.unpack_from('<H', db, 0xcf4*2)[0]
        expected = insert.encode_line_tokens(insert.TOKEN.findall('<c3>Turn</c>'), {}) + [0xFFFE]
        assert struct.unpack_from('<%dH' % len(expected), db, p) == tuple(expected)
        def db_rows(data):
            count = struct.unpack_from('<H', data)[0]//2
            result = []
            for pointer in struct.unpack_from('<%dH' % count, data):
                words = []
                while pointer+2 <= len(data):
                    code = struct.unpack_from('<H', data, pointer)[0]
                    words.append(code)
                    pointer += 2
                    if code in (0xFFFE, 0xFFFD):
                        break
                result.append(words)
            return result
        for before, after in ((om[2], nm[2]), (cm.blocks(om[24])[1], cm.blocks(nm[24])[1])):
            a, b = db_rows(before), db_rows(after)
            assert len(a) == len(b)
            assert [i for i, (x, y) in enumerate(zip(a, b)) if x != y] == [0xcf4]
            assert b[0xcf4] == expected
        a, b = cm.blocks(om[24]), cm.blocks(nm[24])
        assert len(a) == len(b) and all(x == y for i, (x, y) in enumerate(zip(a, b)) if i != 1)
        def pack_files(ver):
            folder = out/('STT2001_EN_v%s_4x_font' % ver)/'SLPS-02863'
            return {str(p.relative_to(folder)): p.read_bytes() for p in folder.rglob('*') if p.is_file()}
        assert pack_files(version) == pack_files(baseline), 'font texture pack changed'
        report.update(version=version, baseline=baseline, disc_verified=True)
        (out/('STT2001_EN_v%s_turn_verification.json' % version)).write_text(
            json.dumps(report, indent=1)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
