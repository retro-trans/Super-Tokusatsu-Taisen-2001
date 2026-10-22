"""Native title-art footer: build version and the Retro Trans address.

python tools/title_footer.py 0.3.20         dry run, no files written
python tools/title_footer.py 0.3.20 --write export asset previews/metadata
The normal builder stamps both title-art copies with its version argument.
"""
import argparse
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

import cm
import gfx
import repack

ROOT = Path(__file__).resolve().parents[1]
URL = 'github.com/retro-trans'
BOX = (188, 208, 312, 234)
FONT_SIZE = 9
BITMAP_FROM = (0, 3, 20)
SOURCE_SHA256 = 'c8711b3bf81f830fed1a83713b7c1ea61bd6764c9f4dd4bbc77e675f7cd2abbd'


@lru_cache(maxsize=1)
def pristine():
    data = (ROOT/'work/source/unpacked/MAPMAIN/0019.bin').read_bytes()
    assert hashlib.sha256(data).hexdigest() == SOURCE_SHA256, 'unexpected original title artwork'
    return gfx.Tim(data)


def validate_version(version):
    if not re.fullmatch(r'0\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version):
        raise ValueError('build version must be 0.x.y')
    return version


@lru_cache(maxsize=1)
def bitmap_font():
    font = json.loads((ROOT/'work/ui/title/footer_font.en.json').read_text(encoding='utf-8'))
    for rows in font['glyphs'].values():
        assert len(rows) == font['height']
        assert len({len(row) for row in rows}) == 1
        assert all(set(row) <= {'0', '1'} for row in rows)
    return font


def bitmap_lettering(label):
    font = bitmap_font()
    glyphs = [np.array([[int(pixel) for pixel in row] for row in font['glyphs'][ch]],
                       dtype=np.uint8) for ch in label]
    gap = np.zeros((font['height'], font['spacing']), np.uint8)
    mask = np.concatenate([part for i, glyph in enumerate(glyphs)
                           for part in ([gap, glyph] if i else [glyph])], axis=1)
    ys, xs = np.nonzero(mask)
    return mask[ys.min():ys.max()+1, xs.min():xs.max()+1]


def apply(data, version, balance=False):
    validate_version(version)
    tim = gfx.Tim(data)
    assert (tim.w, tim.h, tim.bpp) == (320, 240, 1), 'unexpected title artwork'
    clean = pristine()
    assert tim.clut == clean.clut, 'title palette differs from original'
    # Remove any previous version before drawing; repeat/upgrade stamping must
    # never leave the narrower old digit's edge underneath a new version.
    x0, y0, x1, y1 = BOX
    tim.idx[y0:y1, x0:x1] = clean.idx[y0:y1, x0:x1]
    labels = []
    if tuple(map(int, version.split('.'))) >= BITMAP_FROM:
        # Pixel artwork avoids font rasterisation, outline collisions and
        # dependence on installed fonts or emulator replacement texture IDs.
        for label, bottom in (('v'+version+('/balance' if balance else ''), 219), (URL, 232)):
            mask = bitmap_lettering(label)
            h, w = mask.shape
            x, y = BOX[2]-2-w, bottom-h
            panel = (x-2, y-2, BOX[2], bottom+2)
            assert x >= 202 and panel[1] >= BOX[1], 'title footer overflow: '+label
            assert panel[0] >= BOX[0] and panel[3] <= BOX[3]
            tim.fill(*panel, tim.nearest((0, 0, 0)))
            tim.idx[y:bottom, x:x+w][mask != 0] = tim.nearest((255, 255, 255))
            labels.append({'text': label, 'bounds': [x, y, x+w, bottom],
                           'font': bitmap_font()['name'], 'pixel_height': h,
                           'backing_bounds': list(panel)})
        return tim.bytes(), labels
    # Preserve the original v0.3.19 rendering for historical rebuilds.
    for label, bottom in (('v'+version, 221), (URL, 234)):
        mask = gfx.lettering(label, FONT_SIZE, outline=1)
        h, w = mask.shape
        assert w <= BOX[2]-BOX[0] and h <= 12, 'title footer overflow: '+label
        x, y = BOX[2]-w, bottom-h
        assert y >= BOX[1]
        dest = tim.idx[y:bottom, x:BOX[2]]
        dest[mask == 1] = tim.nearest((0, 0, 0))
        dest[mask == 2] = tim.nearest((246, 246, 255))
        labels.append({'text': label, 'bounds': [x, y, BOX[2], bottom],
                       'font_size': FONT_SIZE})
    return tim.bytes(), labels


def verify(original, built, version, balance=False):
    expected, labels = apply(original, version, balance)
    assert built == expected, 'missing or wrong-version title footer'
    a, b = gfx.Tim(original), gfx.Tim(built)
    allowed = np.zeros(a.idx.shape, bool)
    x0, y0, x1, y1 = BOX
    allowed[y0:y1, x0:x1] = True
    assert not np.any((a.idx != b.idx) & ~allowed), 'pixels outside footer changed'
    assert len(original) == len(built)
    end = a.pix_off + a.idx.size
    assert original[:a.pix_off] == built[:b.pix_off] and original[end:] == built[end:], 'TIM metadata/CLUT/padding changed'
    assert np.any(a.idx != b.idx), 'footer is blank'
    return labels


def patch_files(files, version, balance=False):
    validate_version(version)
    entries = repack.dat_entries(files['MAPMAIN.DAT'])
    blocks = cm.blocks(entries[23])
    assert np.array_equal(gfx.Tim(entries[19]).idx, gfx.Tim(blocks[0]).idx), 'title artwork copies differ'
    report = []
    for entry, block, source in ((19, None, entries[19]), (23, 0, blocks[0])):
        edited, _ = apply(source, version, balance)
        labels = verify(source, edited, version, balance)
        if block is None:
            entries[entry] = edited
        else:
            import insert
            entries[entry] = insert.rebuild_cm(entries[entry], {block: edited})
            assert cm.blocks(entries[entry])[1:] == blocks[1:], 'title menu block changed'
        report.append({'entry': entry, 'block': block, 'version': version,
                       'labels': labels, 'allowed_rect': list(BOX),
                       'palette_and_metadata_preserved': True})
    files['MAPMAIN.DAT'] = repack.dat_pack(entries)
    return report


def verify_disc(path, version, balance=False):
    """Read back the written disc, so a successful build cannot carry a stale number."""
    from check_graphics_build import directory, read_file
    entries = repack.dat_entries(read_file(Path(path), directory(Path(path))['MAPMAIN.DAT']))
    source_dir = ROOT/'work/source/unpacked/MAPMAIN'
    raw = (source_dir/'0019.bin').read_bytes()
    packed = cm.blocks((source_dir/'0023.bin').read_bytes())[0]
    verify(raw, entries[19], version, balance)
    verify(packed, cm.blocks(entries[23])[0], version, balance)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version')
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--balance', action='store_true')
    args = parser.parse_args()
    validate_version(args.version)
    source = ROOT/'work/source/unpacked/MAPMAIN/0019.bin'
    original = source.read_bytes()
    edited, _ = apply(original, args.version, args.balance)
    labels = verify(original, edited, args.version, args.balance)
    report = {'version': args.version, 'labels': labels,
              'allowed_rect': list(BOX), 'preview_is_asset_not_emulator_capture': True}
    print(json.dumps(report, indent=1))
    if args.write:
        dest = ROOT/'work/ui/title'
        dest.mkdir(parents=True, exist_ok=True)
        suffix = '_balance' if args.balance else ''
        gfx.Tim(edited).rgb().resize((960, 720), Image.Resampling.NEAREST).save(dest/('footer_v%s%s.png' % (args.version, suffix)))
        gfx.Tim(edited).rgb().save(dest/('footer_v%s%s_native.png' % (args.version, suffix)))
        (dest/('footer%s.en.json'%suffix)).write_text(json.dumps(report, indent=1)+'\n', encoding='utf-8')
    else:
        print('Dry run: no files written.')


if __name__ == '__main__':
    main()
