"""Package a verified local movie-only update and its unchanged matching font pack."""
import argparse,json,shutil,sys,tempfile,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('version');p.add_argument('--source',default='0.3.32');a=p.parse_args()
    out=ROOT/'work/output';stem='STT2001_EN_v'+a.version;base='STT2001_EN_v'+a.source
    movie=json.loads((out/(stem+'_movie_verification.json')).read_text())
    assert movie['all_checks_passed'] and movie['all_other_disc_bytes_identical']
    assert movie['baseline']==a.source and movie['changed_movie_ids_from_baseline']==[74]
    assert movie['nonmovie_exception']=='Exact automatic MAPMAIN title stamp only'
    public=json.loads((out/(stem+'_public_source_verification.json')).read_text())
    assert public['public_english_only_build_matches'] and public['build_problems']==0
    font_source=a.source
    while not (out/('STT2001_EN_v'+font_source+'_font_verification.json')).exists():
        inherited=json.loads((out/('STT2001_EN_v'+font_source+'_patch_verification.json')).read_text())
        assert inherited['roundtrip_verified']
        previous=inherited['texture_files_identical_to']
        assert tuple(map(int,previous.split('.')))<tuple(map(int,font_source.split('.')))
        font_source=previous
    font=json.loads((out/('STT2001_EN_v'+font_source+'_font_verification.json')).read_text())
    assert font['texture_upload_ids_checked'] and font['dialogue_content_and_pointer_order_preserved']
    prior=json.loads((out/(base+'_patch_verification.json')).read_text())
    review=json.loads((out/('opening_song_review_v'+a.version)/'verification.json').read_text())
    assert review['all_checks_passed'] and review['game_manifest_opening_matches_review']
    current=json.loads((ROOT/'work/translation/en/opening_song.en.json').read_text(encoding='utf-8'))
    assert current['version']==a.version
    has_refrain=any(r['en']=='We get rainbow!' for r in current['clips'][0]['subtitles'])
    lyric_notes=('Adds "We get rainbow!" around 1:35-1:38, using the Spotify lyric\n'
                 'screenshot supplied and approved by the user. Retains the restored opening\n'
                 'verse and romaji. The full song\'s extra verse is absent from the game cut.\n'
                 if has_refrain else
                 'Restores two opening lyric lines around 0:26-0:39 and adds romaji above the\n'
                 'English translation. The unclear English refrain around 1:35-1:38 is omitted\n'
                 'at the user\'s request.\n')
    if tuple(map(int,a.version.split('.')))>=(0,3,37):
        assert current['clips'][0]['romaji_top']==16
        lyric_notes=('Moves the opening romaji down from y=5 to y=16 in the native movie,\n'
                     'giving it more room below the top edge during gameplay. The matching\n'
                     'MP4 uses a 48-pixel top margin. Lyrics, timing, English captions and\n'
                     'the original opening audio are retained, including "We get rainbow!".\n')
    if tuple(map(int,a.version.split('.')))>=(0,3,38):
        assert current['clips'][0]['english_bottom']==16
        lyric_notes=('Raises the opening English subtitles by 11 native pixels, using a\n'
                     '16-pixel bottom inset. Romaji stays at y=16. The matching MP4 uses\n'
                     '48-pixel top/bottom margins. Lyrics, timing, font sizes and original\n'
                     'opening audio are retained, including "We get rainbow!".\n')
    readme='''Super Tokusatsu Taisen 2001 English v{v} - local opening-song update
No GitHub release has been created for this build.

{lyric_notes}Captions stay for 0.5 seconds after the line ends,
unless the next caption starts sooner. Original XA audio is unchanged.
Only the opening movie and automatic title version differ from v{src}.
The other 73 movies, font, saved-name fix, difficulty and save format remain
unchanged. Staff rolls share instrumental audio; the short ending also
appears instrumental. Human listening and emulator/PSP confirmation remain
pending; native decoding, disc, subtitle and patch round-trip checks pass.

Apply STT2001-English-v{src}-to-v{v}.xdelta to your v{src} English BIN using
Retro Trans Tools > Apply xdelta. Save as STT2001_EN_v{v}.bin and place the
matching CUE beside it. Cold boot the CUE, then load an ordinary game save.
Old emulator save states can retain old code in RAM. PSP users can convert
the patched BIN/CUE with their usual PS1 EBOOT workflow.

The optional v{v} texture ZIP contains exactly the same {count} images and
configuration as v{src}; an installed v{src} pack already matches this build.
For a fresh installation, extract into DuckStation's data directory
(Tools > Open Data Directory), merging textures/SLPS-02863/, including
config.yaml and replacements/. Enable Texture Cache and Texture
Replacements, then restart or reload replacements. Native text works
without the pack; 2x/4x internal resolution shows the native 2x font detail.

Font artwork: Skies of Arcadia by SEGA/Overworks, as integrated in Seireiki
Rayblade. No new font-art license is granted. GenEi Latin fallback uses the
included SIL Open Font License 1.1.
'''.format(v=a.version,src=a.source,lyric_notes=lyric_notes,count=font['texture_images'])
    (out/(stem+'_README.txt')).write_bytes(readme.encode())
    archive=out/(stem+'_4x_font.zip')
    with zipfile.ZipFile(out/(base+'_4x_font.zip')) as old,zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as new:
        textures=[n for n in old.namelist() if n.startswith('textures/')]
        assert len(textures)==font['texture_images']+1
        new.writestr('README.txt',readme)
        new.writestr('LICENSE-font.txt',old.read('LICENSE-font.txt'))
        for name in textures:new.writestr(name,old.read(name))
    with zipfile.ZipFile(out/(base+'_4x_font.zip')) as old,zipfile.ZipFile(archive) as new:
        assert new.testzip() is None
        assert all(old.read(n)==new.read(n) for n in textures)
    sys.path.insert(0,str(ROOT.parent/'retro-trans-tools'))
    from retro_trans.core import ENGINE_SHA256,ENGINE_MEMBER,encode,decode,sha256_file
    source=out/(base+'.bin');target=out/(stem+'.bin')
    assert sha256_file(source)==prior['target_sha256']
    assert sha256_file(target)==movie['bin_sha256']
    engine_zip=ROOT.parent/'retro-trans-tools/retro_trans/resources/xdelta3-windows.zip'
    assert sha256_file(engine_zip)==ENGINE_SHA256
    patch=out/('STT2001-English-v'+a.source+'-to-v'+a.version+'.xdelta')
    with tempfile.TemporaryDirectory(prefix='movie-patch-',dir=str(out)) as td:
        td=Path(td);engine=td/'xdelta3.exe'
        with zipfile.ZipFile(engine_zip) as z:engine.write_bytes(z.read(ENGINE_MEMBER))
        candidate=td/'update.xdelta';encode(engine,source,target,candidate)
        decoded=td/'roundtrip.bin';decode(engine,source,candidate,decoded,target.stat().st_size)
        assert decoded.stat().st_size==target.stat().st_size and sha256_file(decoded)==movie['bin_sha256']
        shutil.copyfile(candidate,patch)
    report={'version':a.version,'patch':patch.name,'source':source.name,'source_sha256':prior['target_sha256'],
            'target_sha256':movie['bin_sha256'],'patch_sha256':sha256_file(patch),'patch_bytes':patch.stat().st_size,
            'texture_package':archive.name,'texture_images':font['texture_images'],'texture_files_identical_to':a.source,
            'font_verification_source':font_source,
            'roundtrip_verified':True,'retro_trans_tools_verified':True,'github_release_created':False}
    (out/(stem+'_patch_verification.json')).write_bytes((json.dumps(report,indent=1)+'\n').encode())
    print(json.dumps(report,indent=1))


if __name__=='__main__':main()
