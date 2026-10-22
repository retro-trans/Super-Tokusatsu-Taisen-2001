"""Read-only encyclopedia report triage; --write saves English audit metadata.

This detects existing layout defects, so defects are findings rather than a
successful regression check. It does not change translations or build assets.
"""
import json
import struct
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS32, UC_MODE_LITTLE_ENDIAN
from unicorn.mips_const import (UC_MIPS_REG_A0, UC_MIPS_REG_A1,
                               UC_MIPS_REG_RA, UC_MIPS_REG_PC)
import gfx
import insert
import mips
import repack
from check_graphics_build import directory, read_file
from check_man_spider import table32
from check_dialogue_layout import REVERSE, width

ROOT = Path(__file__).resolve().parents[1]


def visible(words):
    return ''.join('\n' if c == 0xFFFB else REVERSE.get(c, '') for c in words)


def audit(version):
    image = ROOT / ('work/output/STT2001_EN_v%s.bin' % version)
    entries = directory(image)
    exe = read_file(image, entries['SLPS_028.63'])
    battle = repack.dat_entries(read_file(image, entries['BATTLE.DAT']))
    texts = table32(battle[540])
    # Actual detail-page command list: description and series drawers.
    for address, expected in [(0x800B3714, (12, 0, 24, 122, 0)),
                              (0x800B3724, (12, 0, 24, 61, 0))]:
        assert struct.unpack_from('<BBhhh', exe, mips.off(address)) == expected
    cpu = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 | UC_MODE_LITTLE_ENDIAN)
    cpu.mem_map(0, 0x200000)
    cpu.mem_write(0x10000, exe[0x800:])
    lookup_codes = sorted(set(c for words in texts for c in words if c in REVERSE))
    for code in lookup_codes:
        cpu.reg_write(UC_MIPS_REG_A0, 0x80100000)
        cpu.reg_write(UC_MIPS_REG_A1, code)
        cpu.reg_write(UC_MIPS_REG_RA, 0x80008000)
        cpu.emu_start(0x8004A7D8, 0x80008000, count=1000)
        assert cpu.reg_read(UC_MIPS_REG_PC) == 0x80008000
        sprite = cpu.mem_read(0x100000, 0x14)
        assert struct.unpack_from('<H', sprite, 8)[0] == width(code), code
        page, cell = divmod(code - 110, 336)
        if code >= 782:
            page -= 2
        assert struct.unpack_from('<H', sprite, 12)[0] == 0x1C + page, code
        assert sprite[14:16] == bytes([(cell % 21)*12, (cell // 21)*16]), code
    # Verify the complete extra-word layer in the built atlas, independently
    # of decoding the English source strings.
    pixels = gfx.Tim(battle[538]).idx
    cells = np.load(ROOT / 'work/font/efont_cells.npz')['ex']
    for i, code in enumerate(insert.efont.EX_SLOTS):
        r = code - 446
        x, y = 256 + (r % 21)*12, (r // 21)*16
        expected = cells[i] if i < len(cells) else np.zeros((16, 24), np.uint8)
        assert np.array_equal(pixels[y:y+16, x:x+24] & 3, expected), code
    bodies = texts[501:1001]
    histogram = Counter(w.count(0xFFFB)+1 for w in bodies)
    overflows = [501+i for i,w in enumerate(bodies) if w.count(0xFFFB)+1 > 6]
    examples = []
    for index, uid in [(538, 'U19351'), (583, 'U19442')]:
        words = texts[index]
        lines = visible(words).split('\n')
        examples.append({'description_index': index, 'translation_id': uid,
                         'name': visible(texts[index-500]), 'lines': len(lines),
                         'last_line_bottom': 122+len(lines)*16,
                         'text': '\n'.join(lines)})
    return {'version_inspected': version, 'status': 'defects_confirmed_not_fixed',
            'hardware_reproduction': False, 'reporter_expected_version': '0.3.18',
            'reporter_actual_image_version_verified': False,
            'description_y': 122, 'line_height': 16, 'safe_body_lines': 6,
            'description_slot_line_counts': dict(sorted(histogram.items())),
            'description_slots_exceeding_six_lines': overflows,
            'native_glyph_lookup_codes_verified': len(lookup_codes),
            'built_extra_word_cells_verified': len(insert.efont.EX_SLOTS),
            'digit_corruption_reproduced': False, 'examples': examples}


if __name__ == '__main__':
    version = next((s for s in sys.argv[1:] if not s.startswith('--')), '0.3.22')
    report = audit(version)
    if '--write' in sys.argv:
        target = ROOT / 'work/ui/encyclopedia'
        target.mkdir(parents=True, exist_ok=True)
        (target/'report.en.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
