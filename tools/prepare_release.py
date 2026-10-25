"""Prepare verified public patches and matching textures; never publish to GitHub."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/output'


def write(path,value):
    path.write_bytes((json.dumps(value,indent=2)+'\n').encode('utf-8'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version')
    parser.add_argument('--sources',default='0.3.6,0.3.18,0.3.27,0.3.29')
    parser.add_argument('--baseline',default='0.3.38')
    parser.add_argument('--catalog',type=Path,default=ROOT.parent/'retro-trans-tools/retro_trans/resources/catalog.json')
    args=parser.parse_args();version=args.version
    import title_footer
    title_footer.validate_version(version)
    target=OUT/('STT2001_EN_v'+version+'.bin')
    assert title_footer.verify_disc(target,version)
    def proof(suffix):
        return json.loads((OUT/('STT2001_EN_v'+version+'_'+suffix+'.json')).read_text(encoding='utf-8'))
    movie=proof('movie_verification');public=proof('public_source_verification')
    font=proof('font_verification');runtime=proof('runtime_balance_verification');story=proof('stronger_verification')
    native=proof('native_2x_verification');numbers=proof('native_ui_verification')
    clear=proof('font_transition_verification');saved=proof('saved_name_font_verification')
    opening=json.loads((OUT/('opening_song_review_v'+version)/'verification.json').read_text())
    assert movie['all_checks_passed'] and movie['all_other_disc_bytes_identical']
    assert movie['baseline']==args.baseline and movie['changed_movie_ids_from_baseline']==[]
    assert public['public_english_only_build_matches'] and public['build_problems']==0
    assert font['texture_upload_ids_checked'] and font['dialogue_content_and_pointer_order_preserved']
    assert native['full_pool_ordering_table_checked'] and numbers['small_number_packets_equal_original_native_drawer']
    assert clear['crop_and_geometry_match_native_height']
    assert runtime['native_save_pack_checksum_and_load_roundtrip'] and story['stronger_save_checksum_load_roundtrip']
    assert story['native_retained_three_choice_sprites_checked']
    assert opening['all_checks_passed'] and opening['top_12_pixel_crop_checked'] and opening['bottom_12_pixel_crop_checked']
    assert saved['version']==version
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    sys.path.insert(0,str(ROOT.parent/'retro-trans-tools'))
    from retro_trans.release import build_release,validate_directory
    from retro_trans.core import sha256_file,Asset,parse_manifest
    from retro_trans.catalog import Catalog
    assert sha256_file(target)==movie['bin_sha256']
    catalog=Catalog(json.loads(args.catalog.read_text(encoding='utf-8')))
    config={'game_id':'super-tokusatsu-taisen-2001','game_name':'Super Tokusatsu Taisen 2001',
            'platform':'PS1','version':version,'source_commit':commit,'patches':[]}
    sources=[('original',ROOT/'Super Tokusatsu Taisen 2001 (Japan).bin')]+[
        (v,OUT/('STT2001_EN_v'+v+'.bin')) for v in args.sources.split(',')]
    for source_version,path in sources:
        assert source_version not in ('0.3.23','0.3.24')
        node=catalog.nodes[(config['game_id'],'original','en',source_version)]
        assert sha256_file(path)==node.hashes['sha256'],('Not the published source binary',source_version)
        name='STT2001-English-'+('v'+version if source_version=='original' else 'v'+source_version+'-to-v'+version)+'.xdelta'
        config['patches'].append({'patch':name,'edition':'original','language':'en','source_version':source_version,
            'source_format':'bin','target_format':'bin','source':str(path),'target':str(target)})
    config_path=OUT/('release-config-v'+version+'.json');write(config_path,config)
    dest=OUT/('release-v'+version)
    print('Creating and round-trip checking %d public patches.'%len(sources),flush=True)
    manifest=build_release(config_path,dest)
    assert all(p['target_sha256']==movie['bin_sha256'] for p in manifest['patches'])
    notes='''English translation for **Super Tokusatsu Taisen 2001**, PlayStation **SLPS-02863**.

### New in v{v}

- New native Skies of Arcadia font, following the Rayblade/Riot Stars rendering approach, with a matching optional texture package.
- Existing public saves retain their character names after the font change.
- Fixed flashing text when dialogue clears, corrupted HP/EN numbers from reused text slots, and weapon badges appearing as white blocks.
- Restored missing opening lyrics, added romaji, and included the user-approved "We get rainbow!" refrain. Romaji and English sit farther inside the picture to avoid edge clipping. Original audio is unchanged.
- Includes all previous translation/UI fixes and **Intermission > Difficulty: Default / Gentle / Story**. The title screen shows **v{v}** and **github.com/retro-trans**.

This publishes the completed local v0.3.38 revision under the requested v{v} number. Only the title version changes from that local build.

### Install

Use [Retro Trans Tools](https://github.com/retro-trans/retro-trans-tools/releases/latest), refresh its catalog or open this release URL, and select your source BIN/CUE. Its standard manifest, checksums and complete-disc round-trip validation are included.

Apply exactly one bare patch matching your source:

| Your source BIN | Patch |
|---|---|
| Original Japanese SLPS-02863, MODE2/2352 | `STT2001-English-v{v}.xdelta` |
{routes}

DeltaPatcher and xdelta3 can also apply these patches. You need your own game image; no game image is distributed. Unpublished v0.3.23/v0.3.24 upgrades remain withdrawn.

All source/output images are 725,316,816 bytes. Source hashes are in `BUILD-MANIFEST.json`.
Output SHA-256: `{sha}`.

Name the patched image `STT2001_EN_v{v}.bin`. Download `STT2001_EN_v{v}.cue.txt`, remove the final `.txt` from its filename, and place the resulting `STT2001_EN_v{v}.cue` beside the BIN. **Cold boot the CUE, then load an ordinary in-game save.** Old emulator save states retain old code and text in RAM. PSP users can convert the patched BIN/CUE using their usual PS1 EBOOT workflow.

### Matching optional texture package

Download **STT2001-4x-font-pack-v{v}.zip**. Public v0.3.29 and older packs alone do not match the new font.

1. In DuckStation, open **Tools > Open Data Directory**.
2. Extract the ZIP there, merging `textures/SLPS-02863/`. Keep `config.yaml` and the `replacements/` directory containing all {count} PNGs.
3. Enable **Texture Cache** and **Texture Replacements**; use 2x/4x internal resolution for sharper text.
4. Reload replacements or restart DuckStation.

Local v0.3.35-v0.3.38 packs already contain the same texture payload. Native text also works without replacements. Fonts use the Skies of Arcadia bitmap by SEGA/Overworks as integrated in Seireiki Rayblade, with GenEi Latin fallback by okoneya (included SIL OFL 1.1). No new license for the Skies artwork is granted.

### Difficulty

Default retains original gameplay. Gentle gives 1.5x XP/rewards, +10% ally / -10% enemy attack and armor. Story gives 3x XP, 2x rewards, +25% ally / -25% enemy attack and armor. Both assistance modes give 25% cheaper S-unit / 50% cheaper L-unit upgrades and refill ammo at a fresh stage, not when resuming mid-stage. HP/EN, movement, hit rates and saved base stats remain unchanged. Circle applies, Cross cancels; the selected mode is saved. Switching back retains earned progress.

### Verification and remaining playtesting

Checks cover all 18 font copies, texture IDs, stable saved names, native numeric drawers, dialogue clearing, three difficulty modes, purchases/rewards, save checksums/load, instruction delays and the English-only source rebuild. All native movie streams decode; original audio and movie allocations are preserved. Opening captions survive simulated top/bottom cropping. Every published patch round-trips to the exact target through Retro Trans Tools.

Emulator/PSP playback and a full campaign remain unverified. Some encyclopedia descriptions still clip; the earlier Kaimen Green corruption report remains unreproduced. Some battle callouts/logos remain Japanese. Machine-assisted translation still needs full fluent review; song transcriptions have not received an independent human listening approval. Please include the title-screen version and a screenshot with reports.
'''.format(v=version,routes='\n'.join('| Public English v{src} | `STT2001-English-v{src}-to-v{v}.xdelta` |'.format(src=v,v=version) for v in args.sources.split(',')),sha=movie['bin_sha256'],count=font['texture_images'])
    (dest/('README-v'+version+'.txt')).write_bytes(notes.encode('utf-8'))
    (OUT/('release-notes-v'+version+'.md')).write_bytes(notes.encode('utf-8'))
    shutil.copyfile(ROOT/'CHANGELOG.md',dest/('CHANGELOG-v'+version+'.txt'))
    # Catalog extras accept text templates; users remove the final .txt.
    shutil.copyfile(target.with_suffix('.cue'),dest/(target.with_suffix('.cue').name+'.txt'))
    write(dest/'PUBLIC-SOURCE-VERIFICATION.json',public)
    write(dest/'FONT-VERIFICATION.json',font)
    write(dest/'UI-VERIFICATION.json',{'native_2x':native,'numeric_and_badges':numbers,'dialogue_clear':clear,'saved_names':saved})
    write(dest/'RUNTIME-VERIFICATION.json',{'gameplay_and_saves':runtime,'story_and_menu':story})
    write(dest/'MOVIE-VERIFICATION.json',{'completed_disc':movie,'opening_review':opening})
    folder=OUT/('STT2001_EN_v'+version+'_4x_font/SLPS-02863')
    paths={p.relative_to(folder).as_posix():p for p in folder.rglob('*') if p.is_file()}
    assert len(paths)==font['texture_images']+1
    archive=dest/('STT2001-4x-font-pack-v'+version+'.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        z.writestr('README.txt',notes)
        z.write(ROOT/'incoming/GenEiLatin/LICENSE.txt','LICENSE-font.txt')
        for name,path in paths.items():z.write(path,'textures/SLPS-02863/'+name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert all(z.read('textures/SLPS-02863/'+n)==p.read_bytes() for n,p in paths.items())
    sums=['{}  {}'.format(sha256_file(p),p.name) for p in sorted(dest.iterdir()) if p.name!='SHA256SUMS.txt']
    (dest/'SHA256SUMS.txt').write_bytes(('\n'.join(sums)+'\n').encode())
    validate_directory(dest)
    # Match the catalog validator's supported supplemental-asset policy.
    for path in dest.iterdir():
        if path.suffix.lower()!='.xdelta':
            assert path.suffix.lower() in ('.json','.txt','.md','.png','.zip')
            assert 0<path.stat().st_size<=64*1024**2
    assets={p.name:Asset(p.name,'https://github.com/retro-trans/Super-Tokusatsu-Taisen-2001/releases/download/v'+version+'/'+p.name,p.stat().st_size,sha256_file(p)) for p in dest.iterdir()}
    assert len(parse_manifest(manifest,assets))==len(sources)
    print('PUBLIC RELEASE READY: '+str(dest),flush=True)
    print('Assets: %d; source commit %s'%(len(assets),commit),flush=True)


if __name__=='__main__':main()
