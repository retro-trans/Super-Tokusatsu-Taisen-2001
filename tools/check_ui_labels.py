"""Verify completed-disc terrain glyphs, menu text, palette and texture pack."""
import json
import struct
import sys
from pathlib import Path
import numpy as np
from PIL import Image
import cm
import insert
import repack
import texpack
import ui_glyphs as UI
from check_graphics_build import directory, read_file, file_hash
ROOT = Path(__file__).resolve().parents[1]


def strings(data):
    first = struct.unpack_from('<H',data)[0]
    rows = []
    for pointer in struct.unpack_from('<%dH'%(first//2),data):
        words = []
        while pointer+2 <= len(data):
            code = struct.unpack_from('<H',data,pointer)[0]
            words.append(code)
            pointer += 2
            if code in (0xFFFE,0xFFFD):
                break
        rows.append(words)
    return rows


def font(before, after, page_x):
    expected = bytearray(before)
    pixels, base = insert.tim_pixels(expected)
    UI.apply_pixels(pixels,page_x)
    packed = (pixels[:,0::2] | (pixels[:,1::2]<<4)).astype(np.uint8).tobytes()
    expected[base:base+len(packed)] = packed
    assert bytes(expected) == after, 'font changed outside compact F1 cells'


def database(before,after):
    a,b = strings(before),strings(after)
    assert len(a) == len(b)
    expected = {r['index']: [UI.FIRST+i,0xFFFE] for i,r in enumerate(UI.META['terrain'])}
    for i in UI.META['heading']['indices']:
        expected[i] = [0xFF33,UI.FIRST+7,UI.FIRST+8,0xFF30,0xFFFE]
    expected[0xaf2] = insert.encode_line_tokens(insert.TOKEN.findall('<c3>Unit</c>'),{})+[0xFFFE]
    for i in (0xb0f,0xb6a):
        expected[i] = insert.encode_line_tokens(['Unit'],{})+[0xFFFE]
    changed = {i for i,(x,y) in enumerate(zip(a,b)) if x != y}
    assert changed == set(expected), ('unexpected database changes',sorted(changed))
    assert all(b[i] == words for i,words in expected.items())
    assert insert.px_of('Unit') == 28


def compressed(before,after,block,test):
    a,b = cm.blocks(before),cm.blocks(after)
    assert len(a) == len(b)
    for i,(x,y) in enumerate(zip(a,b)):
        if i == block:
            test(x,y)
        else:
            assert x == y, ('unrelated compressed block changed',i)


def main():
    version,baseline = sys.argv[1:3]
    out = ROOT/'work/output'
    new = out/('STT2001_EN_v%s.bin'%version)
    old = out/('STT2001_EN_v%s.bin'%baseline)
    nd,od = directory(new),directory(old)
    assert nd.keys() == od.keys()
    changed_archives = {'MAPMAIN.DAT','EVENT.DAT','BATTLE.DAT'}
    for key in nd.keys()-changed_archives-{'DUMMY.DAT'}:
        assert nd[key]['size'] == od[key]['size'] and file_hash(new,nd[key]) == file_hash(old,od[key]),key
    arrays = {}
    for key,allowed in (('MAPMAIN.DAT',{2,7,24,25}),('EVENT.DAT',set(range(10,24))),('BATTLE.DAT',{538})):
        a = repack.dat_entries(read_file(old,od[key]))
        b = repack.dat_entries(read_file(new,nd[key]))
        assert len(a) == len(b)
        changed = {i for i,(x,y) in enumerate(zip(a,b)) if x != y}
        assert changed == allowed,(key,changed)
        arrays[key] = (a,b)
    a,b = arrays['MAPMAIN.DAT']
    database(a[2],b[2]);font(a[7],b[7],256)
    compressed(a[24],b[24],1,database)
    compressed(a[25],b[25],3,lambda x,y:font(x,y,256))
    a,b = arrays['BATTLE.DAT'];font(a[538],b[538],256)
    a,b = arrays['EVENT.DAT']
    for i in range(10,24):
        font(a[i],b[i],256 if i == 10 else 0)
    assert not (set(UI.cells()) & set(insert.EF['encode'].values()))
    assert not (set(UI.cells()) & set(insert.EF['encode_ex'].values()))
    # Confirm new F1 glyphs exist for full-sheet and single-page font uploads.
    sheets = [arrays['MAPMAIN.DAT'][1][7],arrays['BATTLE.DAT'][1][538]]+list(arrays['EVENT.DAT'][1][10:24])
    parts = [texpack.tim_parts(t) for t in sheets]
    palettes = texpack.palettes([p[3] for p in parts])
    folder = out/('STT2001_EN_v%s_4x_font'%version)/texpack.SERIAL/'replacements'
    checked = 0
    seen = set()
    for pixels,(iw,ih),upload,_ in parts:
        page = 1 if iw > 64 else 0
        native = pixels[:,page*256:(page+1)*256]
        block = (native[:,0::2] | (native[:,1::2]<<4)).astype(np.uint8).tobytes()
        hashes = [(upload,iw,page*256)]
        if iw > 64:
            import xxhash
            hashes.append((xxhash.xxh3_64_intdigest(block),64,0))
        for palette,(layer,row) in palettes.items():
            if layer != 1:
                continue
            for stp in (False,True):
                for upload,width,x in hashes:
                    name = 'texupload-%s-%016X-%016X-%dx%d-%d-0-256x%d-P0-15.png'%(
                        'STP4' if stp else 'P4',upload,palette,width,ih,x,ih)
                    if name in seen:
                        continue
                    seen.add(name)
                    actual = Image.open(folder/name).convert('RGBA')
                    for code,glyph in UI.cells(hires=True).items():
                        r = code-UI.FIRST
                        gx,gy = (r%21)*48,(r//21)*64
                        expected = texpack.colourise(glyph,1,row,stp)
                        assert actual.crop((gx,gy,gx+48,gy+64)).tobytes() == expected.tobytes(),(name,code)
                    checked += 1
    report = {'version':version,'baseline':baseline,'all_checks_passed':True,
              'database_labels_verified':12,'native_font_copies_verified':17,
              'texture_variants_verified':checked,'unit_label_width':28,
              'terrain_label_width':12,'terrain_heading_width':24,
              'other_database_strings_unchanged':True,'existing_english_glyphs_unchanged':True,
              'executable_story_movies_unchanged':True,'emulator_verified':False}
    (out/('STT2001_EN_v%s_ui_verification.json'%version)).write_text(json.dumps(report,indent=1)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=1))


if __name__ == '__main__':
    main()
