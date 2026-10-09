"""Check completed-disc UI value cells and matching 4x upload replacements.

Checks the exact allowed changes against the previous build, including native
codes, F1 data, CLUTs, English glyphs and every other game file. Defaults to a
dry run; --verify performs the read-only audit and writes its report.
"""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image
import xxhash
import cm
import insert
import repack
import texpack
import ui_value_font as UI
from kana_table import TABLE
from check_graphics_build import directory, read_file, file_hash

ROOT = Path(__file__).resolve().parents[1]


def font(before,after):
    expected = bytearray(before)
    pixels,base = insert.tim_pixels(expected)
    UI.apply_pixels(pixels)
    raw = (pixels[:,0::2]|(pixels[:,1::2]<<4)).astype(np.uint8).tobytes()
    expected[base:base+len(raw)] = raw
    assert after == bytes(expected), 'Font changed outside the 21 F0 value cells'
    for code,glyph in UI.cells().items():
        assert TABLE[code] == {'?':'？','%':'％'}.get(UI.CODES[code],UI.CODES[code])
        assert glyph.shape == (16,8)
        rows,cols = np.nonzero(glyph)
        assert cols.max()<8 and rows.max()<12 and rows.min()>=1


def verify(version,baseline):
    out = ROOT/'work/output'
    old,new = [out/('STT2001_EN_v%s.bin'%v) for v in (baseline,version)]
    od,nd = directory(old),directory(new)
    arrays = {}
    allowed = {'MAPMAIN.DAT':{7,25},'BATTLE.DAT':{538},'EVENT.DAT':{10}}
    for key,entry in nd.items():
        if key not in allowed and key != 'DUMMY.DAT':
            assert file_hash(old,od[key]) == file_hash(new,entry),key
    for key,indices in allowed.items():
        a,b = [repack.dat_entries(read_file(path,entries[key])) for path,entries in ((old,od),(new,nd))]
        assert len(a)==len(b)
        changed = {i for i,(x,y) in enumerate(zip(a,b)) if x!=y}
        assert changed==indices,(key,changed)
        arrays[key]=(a,b)
    a,b=arrays['MAPMAIN.DAT']
    font(a[7],b[7])
    ca,cb=cm.blocks(a[25]),cm.blocks(b[25])
    assert len(ca)==len(cb)
    for i,(x,y) in enumerate(zip(ca,cb)):
        if i==3:
            font(x,y)
        else:
            assert x==y,('MAPMAIN25 block',i)
    font(arrays['BATTLE.DAT'][0][538],arrays['BATTLE.DAT'][1][538])
    font(arrays['EVENT.DAT'][0][10],arrays['EVENT.DAT'][1][10])
    parts = [(texpack.tim_parts(a[i]),texpack.tim_parts(b[i]))
             for key,i in (('MAPMAIN.DAT',7),('BATTLE.DAT',538)) for a,b in (arrays[key],)]
    palettes=texpack.palettes([p[3] for p in (texpack.tim_parts(arrays['BATTLE.DAT'][1][537]),)]+[b[3] for a,b in parts]+[
        texpack.tim_parts(t)[3] for t in arrays['EVENT.DAT'][1][11:24]])
    folders=[out/('STT2001_EN_v%s_4x_font'%v)/texpack.SERIAL for v in (baseline,version)]
    assert (folders[0]/'config.yaml').read_bytes()==(folders[1]/'config.yaml').read_bytes()
    checked=set()
    cells=UI.cells(True)
    for oldpart,newpart in parts:
        # Full-sheet upload and standalone left-page upload, all palette modes.
        keys=[]
        for pixels,(iw,ih),upload,_ in (oldpart,newpart):
            sub=pixels[:,:256]
            raw=(sub[:,0::2]|(sub[:,1::2]<<4)).astype(np.uint8).tobytes()
            keys.append([(upload,iw),(xxhash.xxh3_64_intdigest(raw),64)])
        mask=np.zeros((1024,1024),bool)
        for code in cells:
            x,y=(code%32)*32,(code//32)*64
            mask[y:y+64,x:x+32]=True
        for palette,(layer,row) in palettes.items():
            for stp in (False,True):
                for (oh,ow),(nh,nw) in zip(*keys):
                    names=['texupload-%s-%016X-%016X-%dx256-0-0-256x256-P0-15.png'%(
                        'STP4' if stp else 'P4',h,palette,w) for h,w in ((oh,ow),(nh,nw))]
                    if names[1] in checked:
                        continue
                    before=np.asarray(Image.open(folders[0]/'replacements'/names[0]).convert('RGBA'))
                    after=np.asarray(Image.open(folders[1]/'replacements'/names[1]).convert('RGBA'))
                    if layer==0:
                        assert np.array_equal(before[~mask],after[~mask]),names[1]
                        for code,glyph in cells.items():
                            x,y=(code%32)*32,(code//32)*64
                            expected=np.asarray(texpack.colourise(texpack.shadow(glyph),0,row,stp))
                            assert np.array_equal(after[y:y+64,x:x+32],expected),(names[1],code)
                    else:
                        assert np.array_equal(before,after),('F1 pack changed',names[1])
                    checked.add(names[1])
    # All replacement files retaining an old hash must be byte-identical.
    oldfiles={p.name:p for p in (folders[0]/'replacements').glob('*.png')}
    newfiles={p.name:p for p in (folders[1]/'replacements').glob('*.png')}
    assert len(newfiles)==len(oldfiles)==756
    shared=set(oldfiles)&set(newfiles)
    assert all(oldfiles[n].read_bytes()==newfiles[n].read_bytes() for n in shared)
    # A changed full-sheet hash also renames its unchanged right-page PNGs.
    aliases={'%016X'%b[2]:'%016X'%a[2] for a,b in parts}
    renamed=set(newfiles)-shared-checked
    for name in renamed:
        oldname=name
        for newhash,oldhash in aliases.items():
            oldname=oldname.replace('-'+newhash+'-','-'+oldhash+'-',1)
        assert oldname in oldfiles,('unaccounted replacement',name)
        assert oldfiles[oldname].read_bytes()==newfiles[name].read_bytes(),('right-page pixels changed',name)
    assert shared|checked|renamed==set(newfiles)
    build=json.loads((out/('STT2001_EN_v%s_report.json'%version)).read_text(encoding='utf-8'))
    assert not build['problems']
    report={'version':version,'baseline':baseline,'all_checks_passed':True,
            'value_glyphs':len(cells),'native_font_copies':4,'fixed_advance':8,
            'texture_variants_verified':len(checked),'replacement_files':len(newfiles),
            'replacement_names_changed':len(set(newfiles)-set(oldfiles)),
            'unchanged_replacements_verified':len(shared),
            'unchanged_right_page_replacements_with_new_names':len(renamed),
            'all_replacement_files_verified':True,
            'native_codes_and_palette_preserved':True,'f1_and_english_font_preserved':True,
            'executable_dialogue_graphics_movies_unchanged':True,'emulator_verified':False}
    (out/('STT2001_EN_v%s_value_font_verification.json'%version)).write_text(json.dumps(report,indent=1)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=1))


if __name__=='__main__':
    version=sys.argv[1] if len(sys.argv)>1 else '0.3.15'
    baseline=sys.argv[2] if len(sys.argv)>2 else '0.3.14'
    print('Audit %s against %s: four font copies / 21 F0 cells; unchanged executable, text, icons, palettes and movies.'%(version,baseline))
    if '--verify' in sys.argv:
        verify(version,baseline)
    else:
        print('Dry run. Add --verify to inspect the completed disc and save the verification report.')
