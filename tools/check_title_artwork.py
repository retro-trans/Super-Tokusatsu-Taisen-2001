"""Check completed native artwork updates against an explicit baseline."""
import hashlib
import json
from pathlib import Path
import sys

import cm
import gfx
import gfx_translate
import repack
import title_footer
from check_graphics_build import directory, read_file

ROOT = Path(__file__).resolve().parents[1]


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else '0.9.5'
    baseline = sys.argv[2] if len(sys.argv) > 2 else '0.9.4'
    old = ROOT / ('work/output/STT2001_EN_v%s.bin' % baseline)
    new = ROOT / ('work/output/STT2001_EN_v%s.bin' % version)
    od, nd = directory(old), directory(new)
    assert od == nd, 'Disc allocation changed'
    targets = gfx_translate.load_manifest()['targets']
    kinds = {'copyright', 'artwork_logo', 'placeholder_title'}
    if any(t.get('lettering') == 'imagegen-sheet-v1' for t in targets):
        kinds.update(('episode','narration'))
    selected = [t for t in targets if t['kind'] in kinds]
    assert len(selected) == (144 if 'episode' in kinds else 53)
    assert sum(t['kind'] == 'episode' for t in targets) == 90
    expected = {n: read_file(old, od[n]) for n in ('MAPMAIN.DAT', 'EVENT.DAT')}
    report = []
    for archive in ('MAPMAIN', 'EVENT'):
        name = archive+'.DAT'
        entries = repack.dat_entries(expected[name])
        for target in [t for t in selected if t['archive'] == archive]:
            source = gfx_translate.source(target)
            edited, labels = gfx_translate.render(source, target)
            qa = gfx_translate.verify(source, edited, target)
            assert all(0 <= l['bounds'][0] < l['bounds'][2] <= qa['size'][0] and
                       0 <= l['bounds'][1] < l['bounds'][3] <= qa['size'][1] for l in labels)
            entries[target['entry']] = edited
            report.append(dict(asset=gfx_translate.name_of(target), **qa, lettering=labels))
        expected[name] = repack.dat_pack(entries)
    title_footer.patch_files(expected, version)
    for name, data in expected.items():
        assert data == read_file(new, nd[name]), ('Unexpected artwork archive content', name)
    for name in ('SLPS_028.63', 'BATTLE.DAT'):
        assert read_file(old, od[name]) == read_file(new, nd[name]), name
    # Compare complete raw disc bytes outside the two audited archives,
    # including every movie/audio sector and unused disc space.
    excluded = sorted((nd[name]['lba']*2352,
                       (nd[name]['lba']+(nd[name]['size']+2047)//2048)*2352)
                      for name in expected)
    with old.open('rb') as a, new.open('rb') as b:
        cursor=0
        for first,last in excluded+[(new.stat().st_size,new.stat().st_size)]:
            a.seek(cursor); b.seek(cursor)
            while cursor < first:
                size=min(8*1024*1024,first-cursor)
                assert a.read(size) == b.read(size), ('Unrelated disc bytes changed',cursor)
                cursor+=size
            cursor=last
    title_footer.verify_disc(new, version)
    entries = repack.dat_entries(read_file(new, nd['MAPMAIN.DAT']))
    gfx.Tim(entries[19]).rgb().save(ROOT/('work/output/STT2001_EN_v%s_title_preview.png'%version))
    result = dict(version=version, baseline=baseline, episode_cards_audited=90,
                  character_cards=2, copyright_screens=1, unused_placeholder_cards=50,
                  exact_expected_archives=True, executable_and_battle_font_unchanged=True,
                  title_copies_verified=True, all_other_raw_disc_bytes_identical=True,
                  movie_and_audio_payloads_unchanged=True, checks=report, emulator_verified=False)
    dest=ROOT/('work/output/STT2001_EN_v%s_artwork_verification.json'%version)
    dest.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('PASS: %d verified graphics, both exact archives, unchanged executable/battle font and both title versions.' % len(selected))


if __name__ == '__main__':
    main()
