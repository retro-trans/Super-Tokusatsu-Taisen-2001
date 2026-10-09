"""Verify the Critical sprites on a completed disc against its previous build."""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import cm
import gfx
import gfx_translate as G
import repack
from check_graphics_build import directory, read_file, file_hash

ROOT = Path(__file__).resolve().parents[1]


def main():
    version, baseline = sys.argv[1:3]
    output = ROOT / 'work/output'
    old, new = [output / ('STT2001_EN_v%s.bin' % v) for v in (baseline, version)]
    od, nd = directory(old), directory(new)
    assert od.keys() == nd.keys()
    unchanged = []
    for key in nd.keys() - {'MAPMAIN.DAT', 'DUMMY.DAT'}:
        assert nd[key]['size'] == od[key]['size'], key
        assert file_hash(new, nd[key]) == file_hash(old, od[key]), key
        unchanged.append(key)
    a, b = [repack.dat_entries(read_file(p, d['MAPMAIN.DAT']))
            for p, d in ((old, od), (new, nd))]
    assert len(a) == len(b)
    assert {i for i, (x, y) in enumerate(zip(a, b)) if x != y} == {17, 25}
    ca, cb = cm.blocks(a[25]), cm.blocks(b[25])
    assert len(ca) == len(cb)
    assert all(x == y for i, (x, y) in enumerate(zip(ca, cb)) if i != 5)
    targets = [t for t in G.load_manifest()['targets'] if t['kind'] == 'battle_callout']
    checks, pixels = [], []
    for t in targets:
        before = ca[5] if 'block' in t else a[t['entry']]
        after = cb[5] if 'block' in t else b[t['entry']]
        expected, labels = G.render(before, t)
        assert after == expected
        checks.append({'asset': G.name_of(t), **G.verify(before, after, t), 'labels': labels})
        pixels.append(gfx.Tim(after).idx[:8, 136:160])
    assert np.array_equal(*pixels)
    # The existing replacement pack still matches every font texture.
    src, dst = [output / ('STT2001_EN_v%s_4x_font' % v) for v in (baseline, version)]
    shutil.copytree(src, dst, dirs_exist_ok=True)
    names = {p.relative_to(src) for p in src.rglob('*') if p.is_file()}
    assert names == {p.relative_to(dst) for p in dst.rglob('*') if p.is_file()}
    assert all((src / n).read_bytes() == (dst / n).read_bytes() for n in names)
    # Native sprite reconstruction; the actual runtime selects this yellow CLUT.
    preview = Image.new('RGB', (384, 192), (24, 32, 24))
    d = ImageDraw.Draw(preview)
    palette = np.zeros((16, 3), np.uint8)
    palette[1], palette[4] = (255, 255, 0), (8, 0, 0)
    sample = Image.fromarray(palette[pixels[0]])
    for y, factor, caption in ((28, 4, 'Native sprite (4x enlargement)'),
                               (106, 8, 'Same sprite (8x enlargement)')):
        d.text((16, y-16), caption, fill='white')
        preview.paste(sample.resize((24*factor, 8*factor), Image.Resampling.NEAREST), (16, y))
    d.text((16, 176), 'Asset reconstruction; not an emulator capture.', fill='white')
    preview.save(G.PREVIEWS / 'critical_translation_preview.png')
    report = {'version': version, 'baseline': baseline, 'all_checks_passed': True,
              'sprites': checks, 'only_mapmain_entries_changed': [17, 25],
              'compressed_copy_only_block_changed': 5,
              'unchanged_game_files': sorted(unchanged),
              'texture_pack_identical_files': len(names), 'emulator_verified': False}
    (output / ('STT2001_EN_v%s_critical_verification.json' % version)).write_text(
        json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
