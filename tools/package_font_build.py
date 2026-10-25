"""Package a checked local font build; never creates a GitHub release."""
import argparse,json,shutil,sys,tempfile,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('version');p.add_argument('--source',default='0.3.29');a=p.parse_args()
    out=ROOT/'work/output';version=a.version
    proof=json.loads((out/('STT2001_EN_v'+version+'_font_verification.json')).read_text())
    assert proof['dialogue_content_and_pointer_order_preserved'] and proof['texture_upload_ids_checked']
    public=json.loads((out/('STT2001_EN_v'+version+'_public_source_verification.json')).read_text())
    assert public['public_english_only_build_matches']
    native_2x=proof.get('native_2x',False)
    native_ui=tuple(map(int,version.split('.'))) >= (0,3,35)
    transition=tuple(map(int,version.split('.'))) >= (0,3,34)
    if transition:
        cleared=json.loads((out/('STT2001_EN_v'+version+'_font_transition_verification.json')).read_text())
        assert cleared['old_zero_height_flashing_reproduced']
        if native_ui:
            repaired=json.loads((out/('STT2001_EN_v'+version+'_native_ui_verification.json')).read_text())
            assert repaired['completed_disc_changes_limited_to_native_ui_fix_and_title']
        else:assert cleared['completed_disc_changes_limited_to_font_draw_and_title']
    stable=tuple(map(int,version.split('.'))) >= (0,3,32)
    if stable:
        saved=json.loads((out/('STT2001_EN_v'+version+'_saved_name_font_verification.json')).read_text())
        assert saved['public_glyph_codes_exact'] and saved['native_save_checksum_pack_load_cases']==4
    save_notes=('''This build restores the public English character-code assignments. Older
public saves, including campaigns continued through v0.3.30/v0.3.31, display
their saved hero names correctly without rewriting the save or resetting names.
New games first CREATED in the unpublished v0.3.30/v0.3.31 used interim name
codes; those names may need renaming. Future builds retain the public codes.

''' if stable else '')
    if native_2x:
        assert json.loads((out/('STT2001_EN_v'+version+'_native_2x_verification.json')).read_text())['full_pool_ordering_table_checked']
    font_notes=('''Dialogue, menus and fixed-width UI values use the original Skies of Arcadia
Latin bitmap from Rayblade. This build follows Riot Stars: a native 2x atlas
drawn at half size, with faint edges blended and solid strokes opaque. This
keeps the original glyph detail in the game without replacement textures.
Use 2x or 4x internal resolution in DuckStation to display that extra detail;
PS1/PSP output at original resolution still has the screen's pixel limit.
The optional matching 4x texture pack is also included separately.
''' if native_2x else '''Dialogue, menus and fixed-width UI values now use Rayblade's current Skies
of Arcadia Latin bitmap. The native PS1 version uses a uniform reduction
to the game's font cells. The optional 4x texture package keeps the original
Rayblade medium-bank ASCII masks and variable advances.
''')
    change_notes=('''Fixes flashing/overlapped old dialogue during page clearing. The native 2x
renderer now respects zero width/height, the scrolling vertical crop and
the shortened glyph height. The current font artwork, public saved-name
codes, original clear timing and opening-song subtitles are preserved.
The v0.3.32/v0.3.33 texture packages already match this build.

''' if transition else '')
    if native_ui:
        font_notes=font_notes.replace('with faint edges blended and solid strokes opaque.',
                                     'using the original shared palette shades and opaque ink.')
        change_notes='''Fixes corrupted HP/EN numbers when a native number drawer reuses an old
English text slot. Clears the stale font marker at allocation. Restores
the original shared palettes so weapon badges retain their gray backgrounds
and readable symbols. Font artwork, saved-name codes, dialogue-clear fix,
opening-song subtitles, gameplay and save format are preserved.
Use this matching texture package: the restored palettes change texture IDs.

'''
    readme='''Super Tokusatsu Taisen 2001 English v{v} - local font test
No GitHub release has been created for this build.

{change_notes}{save_notes}{font_notes}Accents and symbols absent from that source retain the previous GenEi font.
Translation wording,
difficulty choices and save format are preserved.

Apply STT2001-English-v{src}-to-v{v}.xdelta to your English v{src} BIN using
Retro Trans Tools > Apply xdelta, or another xdelta3 patcher. Write a NEW BIN
named STT2001_EN_v{v}.bin and place its matching CUE beside it. Boot the CUE.
Cold boot and load an ordinary in-game save; old emulator save states retain
the old font/executable in RAM. PSP users may convert the patched BIN/CUE
using their usual PS1 EBOOT workflow.

DuckStation: extract the matching v{v} font ZIP into its data directory
(Tools > Open Data Directory), merging textures/SLPS-02863/, including
config.yaml and the replacements/ subfolder. Enable Texture Cache and
Texture Replacements, then restart or reload replacements. The font
{texture_note}
Native text also works without replacement textures.

Font source: the original Skies USA Dreamcast Latin game artwork by
SEGA/Overworks, as integrated in Seireiki Rayblade English v0.7.0. No new
font-art license is granted; no standalone source font is included.
Fallback glyphs: GenEi Latin, SIL Open Font License 1.1 (included).

Native font/glyph, dialogue, menu, gameplay/save, completed-disc rebuild and
patch round-trip checks pass. Emulator/PSP playtesting remains pending.
'''.format(v=version,src=a.source,font_notes=font_notes,save_notes=save_notes,change_notes=change_notes,
           texture_note=('needs this matching v'+version+' pack because the shared palettes were restored.' if native_ui else
                         'uses the same texture IDs as v0.3.32/v0.3.33, so either pack still works.' if transition
                         else 'needs this new pack: earlier versions\' texture IDs alone cannot replace it.'))
    (out/('STT2001_EN_v'+version+'_README.txt')).write_bytes(readme.encode())
    font=out/('STT2001_EN_v'+version+'_4x_font/SLPS-02863')
    files=sorted(p for p in font.rglob('*') if p.is_file())
    assert len(files)==proof['texture_images']+1
    archive=out/('STT2001_EN_v'+version+'_4x_font.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        z.writestr('README.txt',readme)
        z.write(ROOT/'incoming/GenEiLatin/LICENSE.txt','LICENSE-font.txt')
        for path in files:z.write(path,'textures/SLPS-02863/'+path.relative_to(font).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert all(z.read('textures/SLPS-02863/'+path.relative_to(font).as_posix())==path.read_bytes() for path in files)
    sys.path.insert(0,str(ROOT.parent/'retro-trans-tools'))
    from retro_trans.core import ENGINE_SHA256,ENGINE_MEMBER,encode,decode,sha256_file
    engine_zip=ROOT.parent/'retro-trans-tools/retro_trans/resources/xdelta3-windows.zip'
    assert sha256_file(engine_zip)==ENGINE_SHA256
    source=out/('STT2001_EN_v'+a.source+'.bin');target=out/('STT2001_EN_v'+version+'.bin')
    patch=out/('STT2001-English-v'+a.source+'-to-v'+version+'.xdelta')
    with tempfile.TemporaryDirectory(prefix='font-patch-',dir=str(out)) as td:
        td=Path(td);engine=td/'xdelta3.exe'
        with zipfile.ZipFile(engine_zip) as z:engine.write_bytes(z.read(ENGINE_MEMBER))
        candidate=td/'update.xdelta';encode(engine,source,target,candidate)
        decoded=td/'roundtrip.bin';decode(engine,source,candidate,decoded,target.stat().st_size)
        assert decoded.stat().st_size==target.stat().st_size and sha256_file(decoded)==sha256_file(target)
        shutil.copyfile(candidate,patch)
    report={'version':version,'patch':patch.name,'source':source.name,'source_sha256':sha256_file(source),
        'target_sha256':sha256_file(target),'patch_sha256':sha256_file(patch),'patch_bytes':patch.stat().st_size,
        'texture_package':archive.name,'texture_images':proof['texture_images'],
        'roundtrip_verified':True,'retro_trans_tools_verified':True,'github_release_created':False}
    (out/('STT2001_EN_v'+version+'_patch_verification.json')).write_bytes((json.dumps(report,indent=1)+'\n').encode())
    print(json.dumps(report,indent=1))


if __name__=='__main__':main()
