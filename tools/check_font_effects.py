"""Audit the styled native font on the completed disc; no replacements needed."""
import argparse
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import cm
import font_effects as FX
import gfx
import mips
import native_font2x as N
import rayblade_font as R
import repack
import texpack
from check_balance import Machine
from check_font_transition import draw_text, packets, render
from check_difficulty_render import Sprites
from check_graphics_build import directory, read_file, file_hash
from check_native_font2x import GPU, OT, SPRITE, init

ROOT = Path(__file__).resolve().parents[1]


def font_copies(mm, battle, event):
    return ([('MAPMAIN7', mm[7], True),
             ('MAPMAIN25', cm.blocks(mm[25])[3], True),
             ('BATTLE537', battle[537], True), ('BATTLE538', battle[538], True),
             ('EVENT10', event[10], True)] +
            [('EVENT%d' % i, event[i], False) for i in range(11, 24)])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', default='0.9.3')
    parser.add_argument('--movie-baseline', help='Separately verified movie revision to retain')
    args = parser.parse_args()
    out = ROOT / 'work/output'
    baseline_version='0.9.3' if tuple(map(int,args.version.split('.'))) >= (0,9,4) else '0.9.2'
    baseline, target = [out / ('STT2001_EN_v%s.bin' % v)
                        for v in (baseline_version, args.version)]
    bd, td = directory(baseline), directory(target)
    assert bd.keys() == td.keys() and baseline.stat().st_size == target.stat().st_size
    for name in repack.FIXED:
        assert bd[name] == td[name], ('Fixed movie/audio/boot allocation moved', name)
    table=json.loads(Path(str(target)+'.files.json').read_text())
    assert td=={r['path']:{'lba':r['lba'],'size':r['size']} for r in table}
    movable=sorted((v['lba'],v['size'],k) for k,v in td.items() if k not in repack.FIXED)
    for (lba,size,_),(following,_,_) in zip(movable,movable[1:]):
        assert lba+(size+2047)//2048 == following, 'Relocated archives overlap or leave a gap'
    growth=td['MAPMAIN.DAT']['size']-bd['MAPMAIN.DAT']['size']
    assert growth == bd['DUMMY.DAT']['size']-td['DUMMY.DAT']['size']
    meta = json.loads((ROOT/'work/font/efont.json').read_text(encoding='utf-8'))
    oldmeta = json.loads((out/('font-baseline-v'+baseline_version)/'efont.json').read_text(encoding='utf-8'))
    assert FX.enabled(meta)
    for key in ('encode', 'encode_ex', 'uni', 'bi', 'ex', 'widths', 'w_uni', 'w_bi', 'w_ex'):
        assert meta[key] == oldmeta[key], ('Encoding or advance changed', key)
    oldexe, exe = [read_file(p, d['SLPS_028.63']) for p, d in ((baseline, bd), (target, td))]
    report = json.loads((out/('STT2001_EN_v%s_report.json' % args.version)).read_text(encoding='utf-8'))
    start = int(report['native_font_2x']['labels']['draw'], 16)
    end = int(report['native_font_2x']['code_end'], 16)
    assert end == 0x800ddff0
    expected = bytearray(oldexe)
    expected[mips.off(start):mips.off(end)] = exe[mips.off(start):mips.off(end)]
    assert exe == bytes(expected), 'Unrelated executable change'
    instructions = list(mips.md.disasm(exe[mips.off(start):mips.off(end)], start))
    load_checks = 0
    for i, ins in enumerate(instructions[:-1]):
        if ins.mnemonic in ('lb', 'lbu', 'lh', 'lhu', 'lw'):
            reg = ins.op_str.split(',')[0]
            following = instructions[i+1]
            assert reg not in following.op_str.split(', ') and '('+reg+')' not in following.op_str, (
                hex(ins.address), ins.op_str, following.op_str)
            load_checks += 1

    archives = []
    for disc, entries in ((baseline, bd), (target, td)):
        archives.append([repack.dat_entries(read_file(disc, entries[n+'.DAT']))
                         for n in ('MAPMAIN', 'BATTLE', 'EVENT')])
    oldcopies, copies = [font_copies(*a) for a in archives]
    icon_pages = 0
    for (name, old, main), (newname, new, _) in zip(oldcopies, copies):
        assert name == newname and len(old) == len(new)
        assert old[:20] == new[:20], ('Font VRAM allocation changed', name)
        oldpix, _, _, oldpal = texpack.tim_parts(old)
        pix, _, _, pal = texpack.tim_parts(new)
        assert pal[:160] == oldpal[:160] and pal[240:] == oldpal[240:]
        if name == 'BATTLE537':
            assert pal == oldpal, 'Encyclopedia tab artwork palette changed'
        else:
            if baseline_version=='0.9.2':
                assert not any(oldpal[160:240])
            else:
                assert pal==oldpal, 'Shadow palette changed'
            for i, row in enumerate(FX.private_palettes(oldpal)):
                assert pal[(10+i)*16:(11+i)*16] == row
        if main:
            assert np.array_equal(pix[:, :256] >> 2, N.assets()[0])
        if not main or pix.shape[1] > 256:
            x = 256 if main else 0
            assert np.array_equal(pix[:, x:] >> 2, oldpix[:, x:] >> 2), ('Native icon changed', name)
            icon_pages += 1

    machine = Machine(exe)
    cpu = machine.cpu
    cases = 0
    for ch in meta['uni']:
        for role in range(8):
            for layer in range(2):
                init(cpu)
                machine.run(0x8004a7d8, SPRITE, meta['encode'][ch])
                cpu.mem_write((SPRITE & 0x1fffffff)+4, struct.pack('<hh', 10, 20))
                cpu.mem_write((SPRITE & 0x1fffffff)+18, struct.pack('<H', 0xf0+role*2+layer))
                machine.run(start, SPRITE, OT, 3)
                size = struct.unpack('<I', cpu.mem_read(0xd3df0, 4))[0]-GPU
                if role >= 5:
                    assert size == 0, 'Unused text colour sampled outside the font CLUT'
                else:
                    assert size == 40
                    packet = bytes(cpu.mem_read(GPU & 0x1fffffff, 40))
                    clut = struct.unpack_from('<H', packet, 14)[0]
                    assert clut >> 6 == 0xfa+role
                    assert struct.unpack_from('<hh', packet, 8) == (10, 20)
                    assert struct.unpack_from('<hh', packet, 16) == (10+meta['widths'][ch], 20)
                cases += 1

    # Check the source ink and row shading in the actual native atlas.
    mm = archives[1][0]
    oldmm = archives[0][0]
    pixel, (iw, ih), upload, pal = texpack.tim_parts(mm[7])
    font = R.Font(normalize=bool(meta.get('font_metrics')))
    contour_checks = 0
    shadow_pixels = 0
    for i, ch in enumerate(meta['uni']):
        high=font.hires(ch)
        if ch in R.ASCII:
            raw=high[::2,::2]
        else:
            alpha=R.LEVELS[high]
            low=np.asarray(Image.fromarray(alpha).resize((24,32),Image.Resampling.BOX),dtype=np.int16)
            raw=np.argmin(abs(low[:,:,None]-R.LEVELS.astype(np.int16)),axis=2).astype(np.uint8)
        width=meta['widths'][ch]*2
        raw=raw[:,:width]
        cols=np.flatnonzero(raw.max(0))
        shift=min(2,int(cols[0])) if len(cols) else 0
        yy,xx=np.nonzero(raw>=2)
        x,packed=N.assets()[1][i*2:i*2+2]
        actual=pixel[(packed&0xe0)+yy,x+xx-shift]>>2
        expected=np.where(yy<14,3,2) if meta['font_effects']==FX.LEGACY_STYLE else raw[yy,xx]
        assert np.array_equal(actual,expected), ('Native contour/fill',ch)
        ink=np.zeros_like(raw,dtype=bool)
        source_y,source_x=np.nonzero(raw)
        ink[source_y,source_x-shift]=True
        shadow=np.zeros_like(ink)
        shadow[2:,2:]=ink[:-2,:-2]
        shadow &= ~ink
        cell=pixel[(packed&0xe0):(packed&0xe0)+32,x:x+width]>>2
        assert np.all(cell[shadow]==1), ('Missing down-right native shadow',ch)
        shadow_pixels+=int(shadow.sum())
        contour_checks+=1
    assert shadow_pixels>0

    unchanged = []
    for name in td:
        if name not in ('SLPS_028.63', 'MAPMAIN.DAT', 'BATTLE.DAT', 'EVENT.DAT', 'DUMMY.DAT'):
            reference = (out/('STT2001_EN_v%s.bin' % args.movie_baseline)
                         if name == 'MOVIE.STR' and args.movie_baseline else baseline)
            reference_dir = directory(reference) if reference != baseline else bd
            assert file_hash(reference, reference_dir[name]) == file_hash(target, td[name]), name
            unchanged.append(name)
    # Reconstruct the actual native draw packets, keeping the before/after
    # palette and atlas from their respective completed game images.
    frames = []
    lines = [('Takeshi Hongo', 136, 3), ('Rider Henshin!', 152, 0),
             ('We should keep moving.', 168, 0)]
    for binary, db, tim in ((oldexe, oldmm[2], oldmm[7]), (exe, mm[2], mm[7])):
        game = Sprites(binary, db)
        draw_text(game, meta, lines)
        atlas = gfx.Tim(tim).idx[:, :256] >> 2
        frame = render(packets(game, start), atlas, texpack.tim_parts(tim)[3])
        frames.append(frame.crop((16, 124, 305, 217)).resize((1156, 372), Image.Resampling.NEAREST))
    preview = Image.new('RGB', (1156, 790), (18, 26, 28))
    draw = ImageDraw.Draw(preview)
    effect_label='flat ink and shadow' if meta['font_effects']==FX.STYLE else 'gradient and shadow'
    for i, (label, frame) in enumerate(zip(('v'+baseline_version, 'v'+args.version+' - '+effect_label), frames)):
        draw.text((8, i*395+6), label+' (native font preview)', fill='white')
        preview.paste(frame, (0, i*395+22))
    dest = ROOT/'work/ui/font'/('getter-style-v%s.png' % args.version)
    preview.save(dest)
    result = {'version': args.version, 'baseline': baseline_version, 'all_checks_passed': True,
              'movie_baseline': args.movie_baseline or baseline_version,
              'font_copies': len(copies), 'native_icon_pages_unchanged': icon_pages,
              'native_colour_and_glyph_cases': cases, 'native_contour_and_fill_checks': contour_checks,
              'down_right_shadow_pixels_checked':shadow_pixels,
              'native_only':True,'emulator_replacements_required':False,
              'ps1_independent_load_delays_checked': load_checks,
              'encoding_and_advances_unchanged': True, 'original_icon_palettes_preserved': True,
              'unused_font_colours_hidden': True, 'renderer_code_end': hex(end),
              'fixed_movie_audio_lbas_preserved':True, 'archive_compression_growth_bytes':growth,
              'disc_directory_and_nonoverlap_verified':True,
              'unchanged_files': unchanged, 'preview': str(dest.relative_to(ROOT)),
              'emulator_verified': False}
    (out/('STT2001_EN_v%s_font_effects_verification.json' % args.version)).write_bytes(
        (json.dumps(result, indent=2)+'\n').encode())
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
