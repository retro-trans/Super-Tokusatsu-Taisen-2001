"""Check Black Cross numbering/objective selection and prepare its English fix.

Default: dry run, native checks and overlay rebuilds in memory only.
--write: apply the single UID override, regenerate its stripped English copy,
and save an English-only investigation report. Does not create a game build.
"""
import argparse
import json
import struct
from pathlib import Path

from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS32, UC_MODE_LITTLE_ENDIAN
from unicorn.mips_const import UC_MIPS_REG_PC, UC_MIPS_REG_SP, UC_MIPS_REG_RA
import insert
import mips
import strip_jp

ROOT = Path(__file__).resolve().parents[1]
UID = 'U11024'
TEXT = 'Move Red, Blue and Green next to Navaron. Defeat all Zolders and Black Cross Ninjas!'
OCCURRENCE = ('STAGE0432', 0x4532)


def checks():
    exe = mips.load()
    program = (ROOT/'work/source/unpacked/STAGE/0433.bin').read_bytes()
    cpu = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 | UC_MODE_LITTLE_ENDIAN)
    cpu.mem_map(0, 0x200000)
    cpu.mem_write(0x10000, exe[0x800:])
    cpu.mem_write(0xBD350, struct.pack('<I', 0x80100000))
    cpu.mem_write(0x160000, program)

    def commands(start, end):
        pc = start
        while pc < end:
            opcode = struct.unpack_from('<H', program, pc)[0]
            handler = struct.unpack_from('<I', exe, mips.off(0x800B3F24)+opcode*4)[0]
            cpu.mem_write(0xCC670, struct.pack('<I', 0x80160000+pc))
            cpu.reg_write(UC_MIPS_REG_SP, 0x801D0000)
            cpu.reg_write(UC_MIPS_REG_RA, 0x80008000)
            cpu.emu_start(handler, 0x80008000, count=10000)
            assert cpu.reg_read(UC_MIPS_REG_PC) == 0x80008000
            assert cpu.reg_read(UC_MIPS_REG_SP) == 0x801D0000
            next_pc = struct.unpack('<I', cpu.mem_read(0xCC670, 4))[0]-0x80160000
            assert pc < next_pc <= end
            pc = next_pc

    counters = []
    for before in (37, 40):
        cpu.mem_write(0x1005A9, bytes([before]))
        commands(0x3894, 0x38A8)
        after = cpu.mem_read(0x1005A9, 1)[0]
        assert after == before+1
        counters.append({'before': before, 'display_counter': after})
    phases = []
    for start, expected in ((0x1EA4, 0), (0x2AC8, 1), (0x368C, 2)):
        commands(start, start+12)
        index = cpu.mem_read(0x10052F, 1)[0]
        assert index == expected
        phases.append({'script_offset': hex(start), 'objective_index': index})

    rows = insert.frozen_rows()
    assert [(r['file'], r['off']) for r in rows if r['uid'] == UID] == [OCCURRENCE]
    fonts = {(r['file'], r['off']): r['font'] for r in rows}
    source = (ROOT/'work/source/unpacked/STAGE/0432.bin').read_bytes()
    tr = insert.Translator()
    original_translation = json.loads((ROOT/'work/translation/en/out/B0138.en.json').read_text(encoding='utf-8'))
    tr.by_occ[OCCURRENCE] = next(r['en'] for r in original_translation['rows'] if r['uid'] == UID)
    font_at = lambda off, ws: fonts.get((OCCURRENCE[0], off), '11')
    old = insert.rebuild_overlay(source, 0, 'stage', font_at, tr, OCCURRENCE[0])
    tr.by_occ[OCCURRENCE] = TEXT
    tr.by_codes.clear()
    new = insert.rebuild_overlay(source, 0, 'stage', font_at, tr, OCCURRENCE[0])
    assert not insert.PROBLEMS

    def strings(blob):
        count = 0
        while struct.unpack_from('<I', blob, count*4)[0] >> 16 == 0x800E:
            count += 1
        values = []
        for i in range(count):
            off = struct.unpack_from('<I', blob, i*4)[0]-0x800E0000
            end = off
            while struct.unpack_from('<H', blob, end)[0] not in (0xFFFE, 0xFFFD):
                end += 2
            values.append(blob[off:end+2])
        return values

    a, b = strings(old), strings(new)
    assert len(a) == len(b)
    assert a[1] != b[1], 'clarification does not change the original English objective'
    assert all(x == y for i, (x, y) in enumerate(zip(a, b)) if i != 1)
    assert b[1] == insert.pack_words(insert.encode_text(TEXT, 'stage', [], '11', 3)+[0xFFFE])
    pages = insert.layout(TEXT, 220, 3)
    assert len(pages) == 1 and len(pages[0]) <= 3
    lines = [''.join(line) for line in pages[0]]
    return {'date': '2026-10-18', 'title': 'Black Cross', 'guide_label': '41B',
            'reported_in_game_number': 38, 'stage_record': 61,
            'strings_entry': 432, 'program_entry': 433, 'compressed_entry': 691,
            'native_chapter_counter': {'state_offset': '0x5A9', 'cases': counters,
                                       'fixed_scenario_number': False},
            'native_objective_selection': phases, 'changed_uid': UID,
            'clarified_objective': TEXT, 'lines': lines,
            'pointer_entries_checked': len(a), 'other_strings_unchanged': True,
            'event_conditions_changed': False, 'build_created': False,
            'limits': 'Native primitive handlers and overlay insertion checked. Adjacency event predicates, full map playthrough and UI screenshot are not yet verified.',
            'sources': ['https://gamefaqs.gamespot.com/ps/584485-super-tokusatsu-taisen-2001/faqs/82565/scenario-41b',
                        'https://www.akurasu.net/wiki/Super_Tokusatsu_Wars_2001/Complete_Chart']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    report = checks()
    print(json.dumps(report, indent=1))
    if not args.write:
        print('Dry run: no files written. --write prepares the next-build English override only.')
        return
    working = ROOT/'work/translation/en/overrides.json'
    public = working.with_name('overrides.en.json')
    data = json.loads(working.read_text(encoding='utf-8'))
    data[UID] = TEXT
    working.write_bytes((json.dumps(data, ensure_ascii=False, indent=1)+'\n').encode('utf-8'))
    public.write_bytes((json.dumps(strip_jp.clean(data), ensure_ascii=False, indent=1)+'\n').encode('utf-8'))
    assert not strip_jp.check([str(public)])
    destination = ROOT/'work/ui/objectives'
    destination.mkdir(exist_ok=True)
    (destination/'black_cross.en.json').write_text(json.dumps(report, indent=1)+'\n', encoding='utf-8')
    print('Prepared '+UID+' for the next build. Existing game images are unchanged.')


if __name__ == '__main__':
    main()
