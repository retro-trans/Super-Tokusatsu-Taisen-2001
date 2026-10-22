"""Verify the completed title-footer build against its previous image.

Default is a dry run of the check plan; --verify audits the actual disc,
unchanged files/movie sectors/font package, then writes an English report.
"""
import argparse
import json
from pathlib import Path

import cm
import repack
import title_footer
from check_graphics_build import directory, read_file, file_hash

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', nargs='?', default='0.3.19')
    parser.add_argument('baseline', nargs='?', default='0.3.18')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    title_footer.validate_version(args.version)
    if not args.verify:
        print('Dry run: check both title-art copies for v%s / %s; only MAPMAIN entries 19 and 23 block 0 may change. Compare all other game files, raw movie sectors and 756 font replacements against v%s.' % (args.version, title_footer.URL, args.baseline))
        return
    out = ROOT/'work/output'
    old, new = [out/('STT2001_EN_v%s.bin' % v) for v in (args.baseline, args.version)]
    print('Checking completed title artwork and archive contents...', flush=True)
    od, nd = directory(old), directory(new)
    title_footer.verify_disc(new, args.version)
    assert od.keys() == nd.keys()
    inventory = json.loads(Path(str(new)+'.files.json').read_text(encoding='utf-8'))
    assert nd == {r['path']: {'lba': r['lba'], 'size': r['size']} for r in inventory}
    original_mm = read_file(old, od['MAPMAIN.DAT'])
    expected = {'MAPMAIN.DAT': original_mm}
    footer_report = title_footer.patch_files(expected, args.version)
    actual_mm = read_file(new, nd['MAPMAIN.DAT'])
    assert actual_mm == expected['MAPMAIN.DAT'], 'unexpected MAPMAIN change'
    a, b = repack.dat_entries(original_mm), repack.dat_entries(actual_mm)
    assert len(a) == len(b)
    assert all(x == y for i, (x, y) in enumerate(zip(a, b)) if i not in (19, 23))
    title_footer.verify(a[19], b[19], args.version)
    ca, cb = cm.blocks(a[23]), cm.blocks(b[23])
    title_footer.verify(ca[0], cb[0], args.version)
    assert ca[1:] == cb[1:]
    # A different version must produce different pixels from the same source.
    alternate = args.version.rsplit('.', 1)[0]+'.'+str(int(args.version.rsplit('.', 1)[1])+1)
    assert title_footer.apply(a[19], alternate)[0] != b[19]
    assert title_footer.apply(b[19], args.version)[0] == b[19], 'repeat stamping changes pixels'
    assert title_footer.apply(b[19], alternate)[0] == title_footer.apply(a[19], alternate)[0], 'previous version leaves ghost pixels'
    unchanged = []
    print('Comparing unrelated game files...', flush=True)
    for name in nd:
        if name in ('MAPMAIN.DAT', 'DUMMY.DAT'):
            continue
        assert od[name]['size'] == nd[name]['size'] and file_hash(old, od[name]) == file_hash(new, nd[name]), name+' changed'
        unchanged.append(name)
    # Approved movie insertion modifies entire raw sectors, not just file payload.
    assert od['MOVIE.STR'] == nd['MOVIE.STR']
    print('Comparing raw movie sectors...', flush=True)
    movie = nd['MOVIE.STR']
    remaining = ((movie['size']+2047)//2048)*2352
    with old.open('rb') as fa, new.open('rb') as fb:
        fa.seek(movie['lba']*2352); fb.seek(movie['lba']*2352)
        while remaining:
            size = min(1024*1024, remaining)
            assert fa.read(size) == fb.read(size), 'movie raw sectors changed'
            remaining -= size
    packs = [out/('STT2001_EN_v%s_4x_font' % v)/'SLPS-02863' for v in (args.baseline, args.version)]
    print('Comparing matching font-package files...', flush=True)
    inventories = [{p.relative_to(folder).as_posix(): p for p in folder.rglob('*') if p.is_file()} for folder in packs]
    assert inventories[0].keys() == inventories[1].keys()
    assert all(inventories[0][name].read_bytes() == inventories[1][name].read_bytes() for name in inventories[0])
    pngs = sum(name.endswith('.png') for name in inventories[1])
    assert pngs == 756
    build = json.loads((out/('STT2001_EN_v%s_report.json' % args.version)).read_text(encoding='utf-8'))
    assert not build['problems'] and build['version'] == args.version and build['title_footer'] == footer_report
    report = {'version': args.version, 'baseline': args.baseline, 'all_checks_passed': True,
              'title_footer': footer_report, 'different_versions_change_pixels': True,
              'repeat_and_upgrade_stamping_preserve_exact_pixels': True,
              'unrelated_mapmain_entries_and_menu_preserved': True,
              'unchanged_files': unchanged, 'raw_movie_sectors_identical': True,
              'matching_font_pack_files': len(inventories[1]), 'matching_font_pack_pngs': pngs,
              'font_pack_identical_to_previous_build': True, 'build_problems': 0,
              'emulator_appearance': 'See docs/title_footer.md for separately recorded visual checks.'}
    (out/('STT2001_EN_v%s_title_footer_verification.json' % args.version)).write_text(json.dumps(report, indent=1)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
