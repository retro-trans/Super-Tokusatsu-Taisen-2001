"""Reproduce the old Episode 6 stack overflow and check every clear caption.

Run with local completed discs: python tools/check_stage_clear_crash.py
Defaults to v0.3.18 against v0.3.6. --verify writes a diagnostic report;
otherwise all checks run in memory. Graphics submission is modeled, while
the actual caller, caption composer and string-copy instructions execute.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from unicorn import UcError
from unicorn.mips_const import UC_MIPS_REG_PC, UC_MIPS_REG_RA, UC_MIPS_REG_S0
import cm
import repack
from check_graphics_build import directory, read_file
from check_intermission_layout import Intermission, text
from check_ui_labels import strings
from check_dialogue_layout import width

ROOT = Path(__file__).resolve().parents[1]
CALLER = 0x80070D14
STOP = 0x80008000
SAVED = [0x12340000+i for i in range(8)]
GUARD = bytes([0xA5])*32


def disc(version):
    path = ROOT/('work/output/STT2001_EN_v%s.bin' % version)
    entries = directory(path)
    exe = read_file(path, entries['SLPS_028.63'])
    mm = repack.dat_entries(read_file(path, entries['MAPMAIN.DAT']))
    return path, exe, mm[2], cm.blocks(mm[24])[1]


def caption(screen, title, number):
    cpu = screen.cpu
    cpu.mem_write(0x1005A8, bytes([title, number]))
    cpu.mem_write(0x1E0020, GUARD)
    for i, value in enumerate(SAVED):
        cpu.reg_write(UC_MIPS_REG_S0+i, value)
    failure = None
    try:
        screen.call(CALLER, (0, 0, 0, 0))
    except UcError as exc:
        failure = str(exc)
    assert len(screen.draws) == 1, 'clear caption was not submitted'
    words = screen.draws[0]['codes']
    preserved = [cpu.reg_read(UC_MIPS_REG_S0+i) for i in range(8)] == SAVED
    guard = bytes(cpu.mem_read(0x1E0020, len(GUARD))) == GUARD
    return {'title_id': title, 'episode': number, 'text': text(words),
            'bytes_with_terminator': len(words)*2+2,
            'width': sum(width(c) for c in words),
            'returns': cpu.reg_read(UC_MIPS_REG_PC) == STOP,
            'return_address': '0x%08X' % cpu.reg_read(UC_MIPS_REG_RA),
            'saved_registers_preserved': preserved,
            'parent_stack_guard_preserved': guard, 'failure': failure}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', nargs='?', default='0.3.18')
    parser.add_argument('baseline', nargs='?', default='0.3.6')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    _, oldexe, olddb, _ = disc(args.baseline)
    path, exe, db, compressed_db = disc(args.version)
    earlier = []
    for title in range(1, 6):
        row = caption(Intermission(oldexe, olddb), title, title)
        assert row['returns'] and row['bytes_with_terminator'] <= 56
        earlier.append(row)
    # Title 7 follows the optional Boy & Robo chapter: on the reported route
    # it is displayed as Episode 6 and features Colonel Zol's death.
    broken = caption(Intermission(oldexe, olddb), 7, 6)
    assert broken['bytes_with_terminator'] == 68
    assert not broken['returns'] and broken['failure']
    assert broken['return_address'] == '0x01770179'
    old_frame = struct.unpack_from('<I', oldexe, 0x80070D1C-0x80010000+0x800)[0]
    assert old_frame == 0x27BDFFA8  # 0x58 frame, text at +0x18, RA at +0x50
    rows, alternate = strings(db), strings(compressed_db)
    assert rows[0xC94:0xCF2] == alternate[0xC94:0xCF2]
    screen = Intermission(exe, db)
    total = maximum_bytes = maximum_width = 0
    for title in range(91):
        for number in range(91):
            row = caption(screen, title, number)
            prefix = 'Stage %s: %s' % (number if number else '--', text(rows[0xC94+title]))
            assert row['text'] in (prefix+' cleared', prefix+' Clr.'), row
            assert row['returns'] and row['failure'] is None, row
            assert row['saved_registers_preserved'] and row['parent_stack_guard_preserved'], row
            assert row['bytes_with_terminator'] <= 136 and row['width'] <= 284, row
            total += 1
            maximum_bytes = max(maximum_bytes, row['bytes_with_terminator'])
            maximum_width = max(maximum_width, row['width'])
    fixed = caption(screen, 7, 6)
    report = {'version': args.version, 'baseline': args.baseline,
              'all_checks_passed': True, 'old_caption_buffer_bytes': 56,
              'old_saved_return_address_overwritten': True,
              'earlier_chapters_return': earlier, 'old_episode_6': broken,
              'fixed_episode_6': fixed, 'current_caption_buffer_bytes': 136,
              'current_caption_cases': total, 'maximum_caption_bytes': maximum_bytes,
              'maximum_caption_width': maximum_width, 'both_database_copies_match': True,
              'disc_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'graphics_submission_modeled': True, 'full_chapter_playthrough_verified': False,
              'reporter_build_unknown': True, 'game_files_modified': False}
    if args.verify:
        dest = ROOT/('work/output/STT2001_EN_v%s_stage_clear_crash_verification.json' % args.version)
        dest.write_text(json.dumps(report, indent=1)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=1))
    if not args.verify:
        print('Dry run: no files written.')


if __name__ == '__main__':
    main()
