"""Execute the game's upgrade routines with controlled player-state fixtures.

Read-only by default. --verify runs native MIPS purchases and writes a report.
Synthetic units have zero base stats and 15-tier caps to exercise every table
entry; these fixture changes are never written to the disc or patch.
"""
import argparse
import json
import struct
from pathlib import Path

from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS32, UC_MODE_LITTLE_ENDIAN
from unicorn.mips_const import (UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2,
                               UC_MIPS_REG_A3, UC_MIPS_REG_V0, UC_MIPS_REG_SP,
                               UC_MIPS_REG_RA, UC_MIPS_REG_PC, UC_MIPS_REG_GP,
                               UC_MIPS_REG_S0, UC_MIPS_REG_S1, UC_MIPS_REG_S2,
                               UC_MIPS_REG_S7)
import balance
import mips

ROOT = Path(__file__).resolve().parents[1]
STATE = 0x100000
ACTOR = STATE+0x1568
ARGS = (UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2, UC_MIPS_REG_A3)
SOURCE = mips.load()


class Machine:
    def __init__(self, exe):
        cpu = self.cpu = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 | UC_MODE_LITTLE_ENDIAN)
        cpu.mem_map(0, 0x200000)
        cpu.mem_write(0x10000, exe[0x800:])
        cpu.mem_write(0xBD350, struct.pack('<I', 0x80100000))
        cpu.mem_write(0xBD118, struct.pack('<I', 0x801E8000))
        cpu.mem_write(0x1E8000, (ROOT/'work/source/unpacked/MAPMAIN/0001.bin').read_bytes())
        cpu.reg_write(UC_MIPS_REG_GP, 0x80190000)
        cpu.mem_write(0x1901B8, struct.pack('<I', 0x80180000))

    def run(self, start, *args, end=0x80008000):
        cpu = self.cpu
        for reg, value in zip(ARGS, args):
            cpu.reg_write(reg, value)
        cpu.reg_write(UC_MIPS_REG_SP, 0x801D0000)
        cpu.reg_write(UC_MIPS_REG_RA, end)
        cpu.emu_start(start, end, count=100000)
        # Unicorn reports the last instruction for a straight-line stop and
        # the destination for a function-return stop.
        expected = (end,) if end == 0x80008000 else (end, end-4)
        assert cpu.reg_read(UC_MIPS_REG_PC) in expected, hex(start)+' exceeded instruction limit'
        assert cpu.reg_read(UC_MIPS_REG_SP) == 0x801D0000, 'stack imbalance'
        return cpu.reg_read(UC_MIPS_REG_V0)

    def fixture(self, row, funds, materials, capped=False, saturated=False):
        cpu = self.cpu
        cpu.mem_write(STATE, bytes(0x5000))
        for actor in range(200):
            cpu.mem_write(ACTOR+50*actor, b'\xff')
        unit = 0 if row['size'] == 'small' else 0xA9
        cpu.mem_write(ACTOR, bytes([unit]))
        cpu.mem_write(0xAF330+unit, b'\x0f')  # fixture cap only
        tier = 15 if capped else row['tier']-1
        column = row['column']+(4 if row['size'] == 'large' else 0)
        table = balance.TABLES[row['table']]
        if row['table'] == 'unit_stats':
            current = sum(struct.unpack_from('<H', SOURCE, mips.off(table)+i*32+column*4+2)[0]
                          for i in range(tier))
            field, fmt = ((46, '<H'), (6, '<B'), (5, '<B'), (27, '<B'))[row['column']]
            if saturated:
                current = 65535 if row['column'] == 0 else 255
            cpu.mem_write(ACTOR+field, struct.pack(fmt, current))
        else:
            current = 0 if tier == 0 else struct.unpack_from('<H', SOURCE, mips.off(table)+(tier-1)*32+column*4+2)[0]
            cpu.mem_write(ACTOR+28, bytes([255 if saturated else current]))
            # Use weapon 1 with the requested native price type and max tier.
            cpu.mem_write(0x1E8000+14+13, bytes([(row['column'] << 4) | 15]))
        cpu.mem_write(STATE+0x22C, struct.pack('<I', funds))
        cpu.mem_write(STATE+0x234, struct.pack('<I', materials))

    def state(self):
        return bytes(self.cpu.mem_read(STATE, 0x5000))

    def quote(self, row):
        cpu = self.cpu
        if row['table'] == 'unit_stats':
            cpu.reg_write(UC_MIPS_REG_S1, row['column'])
            cpu.reg_write(UC_MIPS_REG_S7, int(row['size'] == 'large'))
            cpu.reg_write(UC_MIPS_REG_A1, row['tier']-1)
            # Include native table indexing, not just the final load.
            cpu.reg_write(UC_MIPS_REG_A0, 0x800B0000)
            self.run(0x800665F0, end=0x8006662C)
        else:
            cpu.reg_write(UC_MIPS_REG_S0, 1)
            cpu.reg_write(UC_MIPS_REG_S2, int(row['size'] == 'large'))
            cpu.reg_write(UC_MIPS_REG_S7, row['tier']-1)
            cpu.reg_write(UC_MIPS_REG_A0, 0x800B0000)
            self.run(0x80066B68, end=0x80066BBC)
        return struct.unpack('<II', cpu.mem_read(0x180078, 8))


def verify_native(original, patched):
    before, after = Machine(original), Machine(patched)
    totals = {'price_rows': 0, 'quote_checks': 0, 'successful_purchases': 0,
              'rejected_purchases': 0, 'cap_rejections': 0, 'saturation_rejections': 0}
    for row in balance.plan():
        stat = row['table'] == 'unit_stats'
        can, buy = (0x80069080, 0x80069900) if stat else (0x8006939C, 0x80069F08)
        args = (0, row['column']) if stat else (0, 0, 1)
        reference = None
        for machine, price in ((before, row['original_funds']), (after, row['funds'])):
            machine.fixture(row, price, price//2)
            assert machine.quote(row) == (price, price//2), ('quote', row)
            totals['quote_checks'] += 1
            assert machine.run(can, *args) == 1, ('affordable', row)
            assert machine.run(buy, *args) == 1, ('purchase', row)
            state = machine.state()
            assert struct.unpack_from('<I', state, 0x22C)[0] == 0, ('funds', row)
            assert struct.unpack_from('<I', state, 0x234)[0] == 0, ('materials', row)
            assert reference is None or state == reference, ('gains or other state changed', row)
            reference = state
            totals['successful_purchases'] += 1
            for funds, materials in ((price-1, price//2), (price, price//2-1), (0, 0)):
                machine.fixture(row, funds, materials)
                untouched = machine.state()
                assert machine.run(can, *args) == 0, ('insufficient resources accepted', row)
                assert machine.run(buy, *args) == 0, ('insufficient resources purchased', row)
                assert machine.state() == untouched, ('failed purchase changed state', row)
                totals['rejected_purchases'] += 1
            for mode in ('capped', 'saturated'):
                machine.fixture(row, 999999, 999999, **{mode: True})
                untouched = machine.state()
                assert machine.run(can, *args) == 0, (mode, row)
                assert machine.run(buy, *args) == 0, (mode+' bought', row)
                assert machine.state() == untouched, (mode+' changed state', row)
                totals['cap_rejections' if mode == 'capped' else 'saturation_rejections'] += 1
        totals['price_rows'] += 1
    return totals


def investigate_ammo(original):
    """Reproduce the original initializer's behavior, without applying a fix."""
    machine = Machine(original)
    weapons = (ROOT/'work/source/unpacked/MAPMAIN/0001.bin').read_bytes()
    first = None
    seventh_limited = []
    for unit in range(256):
        for slot in range(7):
            weapon = struct.unpack_from('<H', original, mips.off(0x800AB2F0)+unit*28+slot*2)[0]
            if weapon == 0 or weapon*14+10 >= len(weapons):
                continue
            maximum = weapons[weapon*14+10]
            if maximum and slot == 6:
                seventh_limited.append([unit, weapon])
            elif maximum and first is None:
                first = (unit, slot, weapon, maximum)
    assert first is not None
    unit, slot, weapon, maximum = first
    results = []
    for initial in (255, 0, max(0, maximum-1)):
        cpu = machine.cpu
        cpu.mem_write(STATE, bytes(0x5000))
        for actor in range(200):
            cpu.mem_write(ACTOR+50*actor, b'\xff')
        cpu.mem_write(ACTOR, bytes([unit]))
        cpu.mem_write(ACTOR+19, b'\xff'*7)
        cpu.mem_write(ACTOR+19+slot, bytes([initial]))
        cpu.mem_write(ACTOR+6, bytes([90, 3]))
        cpu.mem_write(ACTOR+46, struct.pack('<HH', 500, 20))
        machine.run(0x800180F8, end=0x80018174)
        result = cpu.mem_read(ACTOR+19+slot, 1)[0]
        assert result == (maximum if initial == 255 else initial)
        assert cpu.mem_read(ACTOR+7, 1)[0] == 90
        assert struct.unpack('<H', cpu.mem_read(ACTOR+48, 2))[0] == 500
        results.append({'ammo_before': initial, 'ammo_after': result,
                        'hp_after': 500, 'en_after': 90})
    assert not seventh_limited, 'seventh-slot assumption needs revisiting'
    return {'unit_id': unit, 'weapon_id': weapon, 'slot': slot, 'max_ammo': maximum,
            'original_map_setup_segment': '0x800180F8..0x80018174', 'cases': results,
            'ammo_limited_seventh_slots': seventh_limited,
            'conclusion': 'Map setup restores HP/EN but preserves already initialized ammo counts. Full between-stage/load behavior still needs gameplay tracing.',
            'fix_applied': False}


def verify_discs(version):
    import title_footer
    from check_graphics_build import directory, read_file, file_hash
    out = ROOT/'work/output'
    previous = out/'STT2001_EN_v0.3.21.bin'
    standard = out/('STT2001_EN_v%s.bin'%version)
    optional = out/('STT2001_EN_v%s_balance.bin'%version)
    pd, sd, bd = [directory(p) for p in (previous, standard, optional)]
    assert pd.keys() == sd.keys() == bd.keys()
    old_exe, exe, balanced_exe = [read_file(p, d['SLPS_028.63'])
                                 for p, d in ((previous, pd), (standard, sd), (optional, bd))]
    assert old_exe == exe, 'default build gameplay changed'
    balance.verify(exe, balanced_exe)
    before = {'MAPMAIN.DAT': read_file(previous, pd['MAPMAIN.DAT'])}
    title_footer.patch_files(before, version)
    assert read_file(standard, sd['MAPMAIN.DAT']) == before['MAPMAIN.DAT']
    title_footer.patch_files(before, version, balance=True)
    assert read_file(optional, bd['MAPMAIN.DAT']) == before['MAPMAIN.DAT']
    title_footer.verify_disc(standard, version)
    title_footer.verify_disc(optional, version, balance=True)
    untouched = []
    for name in sd.keys()-{'SLPS_028.63', 'MAPMAIN.DAT', 'DUMMY.DAT'}:
        expected = file_hash(previous, pd[name])
        assert file_hash(standard, sd[name]) == file_hash(optional, bd[name]) == expected, name+' changed'
        untouched.append(name)
    # Compare complete movie sectors, including XA/STR headers and parity.
    movie = pd['MOVIE.STR']
    assert movie == sd['MOVIE.STR'] == bd['MOVIE.STR']
    with previous.open('rb') as fp, standard.open('rb') as fs, optional.open('rb') as fb:
        for stream in (fp, fs, fb):
            stream.seek(movie['lba']*2352)
        remaining = ((movie['size']+2047)//2048)*2352
        while remaining:
            size = min(4*1024*1024, remaining)
            assert fp.read(size) == fs.read(size) == fb.read(size), 'raw movie sectors changed'
            remaining -= size
    for suffix in ('', '_balance'):
        report = json.loads((out/('STT2001_EN_v%s%s_report.json'%(version, suffix))).read_text(encoding='utf-8'))
        assert not report['problems'] and report['title_footer_verified']
        assert bool(report['balance']) == bool(suffix)
    return {'default_gameplay_identical_to': '0.3.21',
            'optional_exe_only_changes_240_price_halfwords': True,
            'title_versions_and_variant_verified_in_both_copies': True,
            'other_files_identical': sorted(untouched), 'raw_movie_sectors_identical': True,
            'build_problems': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--version', default='0.3.22')
    args = parser.parse_args()
    print('Plan: native quotes, purchases, funds/material boundaries, caps and identical gains for 240 price rows.')
    if not args.verify:
        print('Dry run: no files written.')
        return
    original = mips.load()
    patched = balance.patch_exe(original)
    disc = ROOT/('work/output/STT2001_EN_v%s_balance.bin'%args.version)
    built = disc.exists() and disc.with_name(disc.stem+'_report.json').exists()
    if built:
        from check_graphics_build import directory, read_file
        patched = read_file(disc, directory(disc)['SLPS_028.63'])
        # Native translated code outside the economy routines is permitted.
        for address in balance.TABLES.values():
            pos = mips.off(address)
            assert patched[pos:pos+480] == balance.patch_exe(original)[pos:pos+480]
    report = {'version': args.version, 'profile': balance.profile(),
              'disc_tested': built, 'native_mips': verify_native(original, patched),
              'original_ammo_investigation': investigate_ammo(original),
              'fixture': 'Zero-base synthetic S/L units; 15-tier caps. No graphics or system calls mocked.',
              'full_gameplay_verified': False}
    if built:
        report['disc_isolation'] = verify_discs(args.version)
    path = ROOT/('work/output/STT2001_EN_v%s_balance_verification.json'%args.version)
    path.write_text(json.dumps(report, indent=1)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
