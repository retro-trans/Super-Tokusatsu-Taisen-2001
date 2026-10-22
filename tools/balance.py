"""Opt-in economy prototype. Default CLI is read-only; --write exports an EXE.

The two native tables contain interleaved u16 price/value pairs. Change ONLY
prices, so level-up growth and scenario-supplied upgrades retain their values.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

import mips

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT/'work/translation/en/balance.en.json'
TABLES = {'unit_stats': 0x800AEF70, 'weapons': 0x800AF150}
TABLE_SHA256 = {
    'unit_stats': '4ff2b029c91c156674ccbc71e6e5e939d7a1961ed04448e6bd0095a2530ea5d8',
    'weapons': '442b3784de58df73029a3c6a676a3ccbedfc9749bf02549962ecb8f060405ebb',
}
TIERS = 15


def profile():
    data = json.loads(PROFILE.read_text(encoding='utf-8'))
    assert data['id'] == 'economy-v1'
    for size in ('small', 'large'):
        assert type(data[size+'_unit_price_percent']) is int
        assert 1 <= data[size+'_unit_price_percent'] <= 100
    return data


def plan():
    source = mips.load()
    settings = profile()
    changes = []
    for table, address in TABLES.items():
        original = source[mips.off(address):mips.off(address)+480]
        assert hashlib.sha256(original).hexdigest() == TABLE_SHA256[table], 'unexpected original '+table+' table'
        for tier in range(TIERS):
            for column in range(8):
                pos = mips.off(address) + tier*32 + column*4
                old, gain = struct.unpack_from('<HH', source, pos)
                size = 'small' if column < 4 else 'large'
                new = old * settings[size+'_unit_price_percent'] // 100
                assert 0 < new <= old <= 65535
                changes.append({'table': table, 'tier': tier+1, 'size': size,
                                'column': column % 4, 'offset': pos,
                                'original_funds': old, 'funds': new,
                                'materials': new//2, 'unchanged_value': gain})
    return changes


def patch_exe(exe):
    result = bytearray(exe)
    for row in plan():
        pos = row['offset']
        assert struct.unpack_from('<HH', result, pos) == (row['original_funds'], row['unchanged_value']), \
            'unexpected/already balanced upgrade table at '+hex(pos)
        struct.pack_into('<H', result, pos, row['funds'])
    return bytes(result)


def verify(original, patched):
    assert patched == patch_exe(original), 'balance patch differs from profile'
    allowed = {r['offset']+i for r in plan() for i in range(2)}
    assert len(original) == len(patched)
    assert all(a == b or i in allowed for i, (a, b) in enumerate(zip(original, patched)))
    return {'profile': profile(), 'price_halfwords': len(plan()),
            'only_price_halfwords_changed': True,
            'exe_sha256': hashlib.sha256(patched).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', type=Path, metavar='EXE')
    args = parser.parse_args()
    before = mips.load()
    after = patch_exe(before)
    report = verify(before, after)
    report['sample_first_tier'] = [r for r in plan() if r['tier'] == 1]
    print(json.dumps(report, indent=1))
    if args.write:
        args.write.write_bytes(after)
    else:
        print('Dry run: no files written. Build with tools/build.py VERSION --balance.')


if __name__ == '__main__':
    main()
