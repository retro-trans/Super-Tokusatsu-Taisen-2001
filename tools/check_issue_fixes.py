"""Exercise issue #2/#3 native response, upgrade and Stats text on built discs."""
import argparse
import json
import struct
from pathlib import Path
from collections import Counter
from PIL import Image
import insert, issue_ui, mips, native_font2x as N, repack, texpack, dump_script as D
from check_graphics_build import directory, read_file, file_hash
from check_native_ui_font import NativeUI, number, packets
from check_stats_layout import Screen
from check_intermission_layout import text
from check_native_font2x import init, GPU, OT, SPRITE
from check_font_transition import render
from check_dialogue_layout import REVERSE, width
from check_ui_labels import strings
from check_man_spider import table32

ROOT = Path(__file__).resolve().parents[1]


def read_words(exe, address):
    words = []
    while True:
        code = struct.unpack_from('<H', exe, mips.off(address)+len(words)*2)[0]
        if code == 0xFFFE:
            return words
        words.append(code)


def upgrade(exe, db, maximum):
    # Keep the real first three descriptors (prompt, caption, live value).
    # Stop before unrelated money/part rows, which require other game state.
    fixture = bytearray(exe)
    offset = mips.off(0x800B2E94)
    fixture[offset:offset+16] = b'\xff'+bytes(15)
    game = NativeUI(bytes(fixture), db)
    game.put(0x801A7050, maximum, '<I')
    game.call(0x8004AEBC, (0, 0x800B2E64, 0))
    caption = next(r for r in game.requests if r['y'] == 62)
    right = caption['x']+sum(width(c) for c in caption['codes'])
    digits = [s for s in game.live(0) if s['y'] == 62 and
              1 <= game.get(SPRITE+s['slot']*36+0x18, '<H') <= 10]
    assert digits and len(digits) == len(str(maximum)), digits
    left = min(s['x'] for s in digits)
    return game, text(caption['codes']), right, left


def brackets(draws, y):
    row = next(d for d in draws if d['kind'] == 'text' and d['x'] == 156 and d['y'] == y)
    x = row['x']; positions = {}
    for code in row['codes']:
        for char in REVERSE.get(code, ''):
            if char in '+()':
                positions[char] = (x, x+insert.EF['widths'][char])
            x += insert.EF['widths'][char]
    return positions


def terminology(disc, entries, mm, version='0.9.1'):
    counts=Counter();checked=Counter()
    restored_henshin = tuple(map(int, version.split('.'))) >= (0, 9, 2)
    def scan(words,kind):
        visible=''.join(REVERSE.get(c,'') for c in words)
        forbidden = ('Lucifard','Oyassan') + (() if restored_henshin else ('Henshin',))
        assert not any(t in visible for t in forbidden),(kind,visible)
        for term in ('Luciferd','Henshin','Transform','Pops','Mr. Tachibana'):
            counts[term]+=visible.count(term)
        checked[kind]+=1
    stages=repack.dat_entries(read_file(disc,entries['STAGE.DAT']))
    for key in sorted(D.STAGE_VAR):
        for _,words,_ in D.overlay_strings(stages[int(key)],0):scan(words,'story')
    battle=repack.dat_entries(read_file(disc,entries['BATTLE.DAT']))
    for part in battle:
        if len(part)>0x8438 and part[:4]==b'\x10\0\0\0' and struct.unpack_from('<I',part,0x8434)[0]>>16==0x800e:
            for _,words,_ in D.overlay_strings(part,0x8434):scan(words,'battle')
    for words in table32(battle[540]):scan(words,'encyclopedia')
    rows=strings(mm[2])
    for words in rows:scan(words,'database')
    if restored_henshin:
        assert counts['Henshin'] > 0, 'Restored Henshin is missing'
    assert text(rows[0xB13])=='Continue' and text(rows[0xB27])=='Max Lv.'
    import gfx_translate
    logo=next(t for t in gfx_translate.load_manifest()['targets'] if t.get('kind')=='artwork_logo')
    if logo.get('wordmark'):
        assert logo['en']=='Fusion Steel Luciferd' and (ROOT/logo['wordmark']).is_file()
    else:
        assert logo['labels'][0]['en']=='Luciferd'
    expected,_=gfx_translate.render(gfx_translate.source(logo),logo)
    event=repack.dat_entries(read_file(disc,entries['EVENT.DAT']))
    assert event[logo['entry']]==expected,'Completed artwork mismatch'
    return {'no_old_terms_in_compiled_text':True,'checked':dict(checked),
            'replacement_occurrences':dict(counts),'continue_and_max_labels_verified':True,
            'completed_luciferd_artwork_matches':True}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--version', default='0.9.1')
    a = p.parse_args(); out = ROOT/'work/output'
    before = out/'STT2001_EN_v0.9.0.bin'; after = out/('STT2001_EN_v'+a.version+'.bin')
    old_dir, new_dir = directory(before), directory(after)
    old_exe, exe = read_file(before, old_dir['SLPS_028.63']), read_file(after, new_dir['SLPS_028.63'])
    expected_exe = old_exe
    if tuple(map(int,a.version.split('.'))) >= (0,9,3):
        # The font effect changes only its existing private renderer region.
        base=out/'STT2001_EN_v0.3.30.bin'
        native=N.patch_exe(read_file(base,directory(base)['SLPS_028.63']),
                           transition_clip=True,native_ui=True)
        expected_exe=bytearray(old_exe)
        expected_exe[mips.off(N.B):mips.off(N.LIMIT_B)]=native[mips.off(N.B):mips.off(N.LIMIT_B)]
        expected_exe=bytes(expected_exe)
    assert exe == issue_ui.patch_exe(expected_exe), 'Unrelated executable/gameplay changes'
    old_mm, mm = [repack.dat_entries(read_file(path, d['MAPMAIN.DAT']))
                  for path, d in ((before, old_dir), (after, new_dir))]
    terms=terminology(after,new_dir,mm,a.version)
    response = []
    for pointer, original, address, want in issue_ui.RESPONSES:
        assert struct.unpack_from('<I', old_exe, pointer)[0] == original
        old = text(read_words(old_exe, original))
        assert old in ('vd', 'rd'), old
        assert struct.unpack_from('<I', exe, pointer)[0] == address
        got = text(read_words(exe, address)); assert got == want, got
        # Execute the actual text allocator/lookup/finalizer from its table pointer.
        game = NativeUI(exe, mm[2]); game.put(0x80144000, 0, '<I')
        from runtime_balance import asm
        stub = asm('''addiu $sp,$sp,-32
        sw $ra,28($sp)
        lui $t0,0x800b
        lw $t0,%d($t0)
        nop
        sw $t0,16($sp)
        sw $zero,20($sp)
        move $a0,$zero
        addiu $a1,$zero,32
        addiu $a2,$zero,150
        jal 0x8004a954
        move $a3,$zero
        jal 0x8004bf8c
        move $a0,$zero
        lw $ra,28($sp)
        addiu $sp,$sp,32
        jr $ra
        nop''' % (pointer-0x800+0x80010000-0x800B0000), 0x80142000)
        game.cpu.mem_write(0x142000, stub); game.call(0x80142000, ())
        tokens = [REVERSE[game.get(SPRITE+s['slot']*36+0x18, '<H')] for s in game.live(0)]
        assert ''.join(tokens) == want
        response.append({'before': old, 'after': got, 'native_retained_text': ''.join(tokens)})
    _, _, old_right, old_left = upgrade(old_exe, old_mm[2], 15)
    assert old_right > old_left, 'Old max-level overlap did not reproduce'
    for maximum in (0, 1, 9, 10, 15, 99):
        _, caption, right, left = upgrade(exe, mm[2], maximum)
        assert caption == 'Max Lv.' and right <= left, (caption, right, left)
    s = Screen(exe, mm[2]); old_screen = Screen(old_exe, old_mm[2])
    cases = [(134,131,68)] + [(n,n,k) for n in (0,1,9,99,100,255) for k in (0,1,99,255)]
    for eva, acc, bonus in cases:
        draws = s.run(eva, acc, bonus, [0]*7)
        for y, base in ((117,eva),(141,acc)):
            values = {(d['x'], d['value'], d['limit']) for d in draws if d['kind']=='number' and d['y']==y}
            assert {(130,base,3),(168,bonus,3),(200,base+bonus,3)} <= values
            marks = brackets(draws, y)
            assert marks['+'][1] <= 168 and 192 <= marks['('][0]
            assert marks['('][1] <= 200 and 224 <= marks[')'][0] and marks[')'][1] <= 236
    old_marks = brackets(old_screen.run(134,131,68,[0]*7),117)
    assert old_marks['('][0] < 192 and old_marks[')'][0] < 224
    # Check native number-slot reuse in the actual new executable too.
    sorter = 0x80000000 | ((struct.unpack_from('<I', exe, mips.off(0x800155F0))[0]&0x3FFFFFF)<<2)
    numeric_cases = 0
    from check_font_transition import draw_text
    for large in (False,True):
        for value in (0,9,59,190,9999):
            game = NativeUI(exe, mm[2]); draw_text(game, insert.EF, [('Luciferd',136,3)])
            number(game,value,large)
            assert len(game.live(0)) == len(str(value))
            if not large:
                assert packets(game,sorter) == packets(game,0x80088BB8)
            numeric_cases += 1
    # Reconstruct the actual Stats row objects/FT4 packets at native resolution.
    frames=[]
    for data,db in ((old_exe,old_mm[2]),(exe,mm[2])):
        game=NativeUI(data,db);game.run(134,131,68,[0]*7);init(game.cpu)
        for item in game.live(0):
            if item['y'] in (117,141):
                game.call(sorter,(SPRITE+36*item['slot'],OT,3))
        raw=bytes(game.cpu.mem_read(GPU&0x1FFFFFFF,game.get(0x800D3DF0,'<I')-GPU))
        assert len(raw)%40==0
        image=render(raw,N.assets()[0],texpack.tim_parts(mm[7])[3]).crop((20,110,304,158))
        frames.append(image)
    preview=Image.new('RGB',(284,96));preview.paste(frames[0],(0,0));preview.paste(frames[1],(0,48))
    folder=ROOT/'work/ui/issues';folder.mkdir(parents=True,exist_ok=True)
    preview.resize((1136,384),Image.Resampling.NEAREST).save(folder/('stats-v'+a.version+'.png'))
    unchanged=[]
    for name in ('SOUND.DAT','VORTEX.XA','WAZA1.DAT','WAZA2.DAT','WAZA3.DAT','SYSTEM.CNF'):
        assert file_hash(before,old_dir[name])==file_hash(after,new_dir[name]),name
        unchanged.append(name)
    report={'version':a.version,'issues':[2,3,4],'responses':response,'max_level_cases':6,
            'old_max_overlap_reproduced':True,'stats_cases':len(cases),'old_bracket_overlap_reproduced':True,
            'brackets':brackets(draws,117),'native_numeric_reuse_cases':numeric_cases,
            'unchanged_gameplay_audio_files':unchanged,'terminology':terms,
            'executable_changes_only_two_pointers_and_reserved_labels':True,'emulator_playtest':False}
    target=out/('STT2001_EN_v'+a.version+'_issue_verification.json')
    target.write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps(report,indent=2))


if __name__ == '__main__':main()
