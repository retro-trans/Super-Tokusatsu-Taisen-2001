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
    parser.add_argument('--previous-version', help='Previous public release; default: newest lower version in the catalog')
    parser.add_argument('--baseline',default='0.3.38')
    parser.add_argument('--catalog',type=Path,help='Reviewed catalog override; default: current public catalog')
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
    from retro_trans.core import sha256_file,Asset,parse_manifest,GitHubClient
    from retro_trans.catalog import Catalog, version_key
    from release_notes import render_release_notes
    assert sha256_file(target)==movie['bin_sha256']
    catalog=Catalog(json.loads(args.catalog.read_text(encoding='utf-8')) if args.catalog else
                    GitHubClient().json('https://raw.githubusercontent.com/retro-trans/retro-trans-tools/main/retro_trans/resources/catalog.json'))
    config={'game_id':'super-tokusatsu-taisen-2001','game_name':'Super Tokusatsu Taisen 2001',
            'platform':'PS1','version':version,'source_commit':commit,'patches':[]}
    published={r['manifest']['version'] for r in catalog.data['releases']
               if r['manifest']['game_id']==config['game_id']
               and version_key(r['manifest']['version']) < version_key(version)}
    previous=args.previous_version or max(published,key=version_key)
    assert previous in published, 'Upgrade source must be an earlier public release'
    sources=[('original',ROOT/'Super Tokusatsu Taisen 2001 (Japan).bin'),
             (previous,OUT/('STT2001_EN_v'+previous+'.bin'))]
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
    notes=render_release_notes(version,previous,movie['bin_sha256'],font['texture_images'])
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
