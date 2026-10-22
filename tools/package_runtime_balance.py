"""Verify/package a LOCAL runtime-Balance build. Does not publish or contact GitHub.

Default is dry-run. --write verifies the disc/compatible textures, generates
bare Japan/v0.3.18/v0.3.23 patches and decodes each with Retro Trans Tools.
"""
import argparse
import json
import shutil
import struct
import sys
import tempfile
import zipfile
from pathlib import Path
import gfx
import repack
import runtime_balance
import title_footer
from check_graphics_build import directory,read_file,file_hash

ROOT=Path(__file__).resolve().parents[1]


def verify_disc(version):
    out=ROOT/'work/output'
    old,new=[out/('STT2001_EN_v%s.bin'%v) for v in ('0.3.23',version)]
    od,nd=directory(old),directory(new)
    assert od.keys()==nd.keys()
    exe=read_file(new,nd['SLPS_028.63'])
    expected_exe=runtime_balance.patch_exe(read_file(old,od['SLPS_028.63']),support_stronger=tuple(map(int,version.split('.'))) >= (0,3,28))
    if tuple(map(int,version.split('.'))) >= (0,3,25):
        import save_slot_layout
        expected_exe=save_slot_layout.patch_exe(expected_exe)
    if tuple(map(int,version.split('.'))) >= (0,3,26):
        import difficulty_menu
        expected_exe=difficulty_menu.patch_exe(expected_exe,support_stronger=tuple(map(int,version.split('.'))) >= (0,3,28),story_labels=tuple(map(int,version.split('.'))) >= (0,3,29))
    if (0,3,27) <= tuple(map(int,version.split('.'))) < (0,3,28):
        import difficulty_render
        expected_exe=difficulty_render.patch_exe(expected_exe)
    assert exe==expected_exe
    assert len(exe)==struct.unpack_from('<I',exe,0x1c)[0]+0x800
    assert nd['SLPS_028.63']['size']==len(exe)
    assert nd['SLPS_028.63']['lba']==195412
    expected={'MAPMAIN.DAT':read_file(old,od['MAPMAIN.DAT'])}
    title_footer.patch_files(expected,version)
    assert read_file(new,nd['MAPMAIN.DAT'])==expected['MAPMAIN.DAT']
    assert title_footer.verify_disc(new,version)
    unchanged=[]
    for name in nd.keys()-{'SLPS_028.63','MAPMAIN.DAT','DUMMY.DAT'}:
        assert file_hash(old,od[name])==file_hash(new,nd[name]),name
        unchanged.append(name)
    for name in ('MOVIE.STR','VORTEX.XA'):
        assert nd[name]==od[name]
        size=((nd[name]['size']+2047)//2048)*2352
        with old.open('rb') as a,new.open('rb') as b:
            a.seek(nd[name]['lba']*2352);b.seek(nd[name]['lba']*2352)
            while size:
                n=min(size,4*1024*1024)
                assert a.read(n)==b.read(n),name+' raw sectors changed'
                size-=n
    # BIOS BOOT path is unchanged; directory sectors include the new EXE size
    # and location in both endian forms. The moved EXE cannot overlap a file.
    entries=sorted(nd.items(),key=lambda row:row[1]['lba'])
    assert all(a['lba']+(a['size']+2047)//2048<=b['lba'] for (_,a),(_,b) in zip(entries,entries[1:]))
    assert nd['DUMMY.DAT']['lba']+(nd['DUMMY.DAT']['size']+2047)//2048<=308233
    with new.open('rb') as f:
        f.seek(16*2352);pvd=f.read(2352)[24:2072]
        raw,recs=repack.read_dir(f,struct.unpack_from('<I',pvd,158)[0],struct.unpack_from('<I',pvd,166)[0])
    for pos,_,name in recs:
        if name in (b'\0',b'\1'):
            continue
        assert struct.unpack_from('<I',raw,pos+2)[0]==struct.unpack_from('>I',raw,pos+6)[0]
        assert struct.unpack_from('<I',raw,pos+10)[0]==struct.unpack_from('>I',raw,pos+14)[0]
    mm=repack.dat_entries(read_file(new,nd['MAPMAIN.DAT']))
    # Read the actual completed title image for human visual inspection.
    gfx.Tim(mm[19]).rgb().save(out/('STT2001_EN_v%s_title_preview.png'%version))
    build=json.loads(new.with_name(new.stem+'_report.json').read_text(encoding='utf-8'))
    assert not build['problems'] and build['title_footer_verified']
    public=json.loads(new.with_name(new.stem+'_public_source_verification.json').read_text(encoding='utf-8'))
    assert public['public_english_only_build_matches']
    import hashlib
    assert public['files']['SLPS_028.63']['sha256']==hashlib.sha256(exe).hexdigest()
    return {'version':version,'baseline':'0.3.23','completed_disc_verified':True,
            'only_runtime_exe_and_title_art_changed':True,'unchanged_files':sorted(unchanged),
            'raw_movie_and_audio_sectors_identical':True,'iso_directory_endian_pairs_match':True,
            'files_do_not_overlap':True,'exe_load_header_matches_file_size':True,
            'exe_relocated_to_lba':nd['SLPS_028.63']['lba'],
            'public_source_rebuild_matches':True,'full_emulator_campaign_verified':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version',nargs='?',default='0.3.24')
    parser.add_argument('--write',action='store_true')
    args=parser.parse_args()
    if not args.write:
        print('Dry run: completed-disc checks, matching texture ZIP, three bare patches and verified decode.')
        return
    version=args.version;out=ROOT/'work/output'
    report=verify_disc(version)
    native=json.loads((out/('STT2001_EN_v%s_runtime_balance_verification.json'%version)).read_text(encoding='utf-8'))
    assert native['native_save_pack_checksum_and_load_roundtrip'] and native['purchases']==960
    if tuple(map(int,version.split('.'))) >= (0,3,28):
        sprites=json.loads((out/('STT2001_EN_v%s_stronger_verification.json'%version)).read_text(encoding='utf-8'))
        assert sprites['native_retained_three_choice_sprites_checked']
        assert sprites['stronger_save_checksum_load_roundtrip']
        report['native_retained_sprites_verified']=True
        report['stronger_profile_verified']=True
    elif tuple(map(int,version.split('.'))) >= (0,3,27):
        sprites=json.loads((out/('STT2001_EN_v%s_difficulty_render_verification.json'%version)).read_text(encoding='utf-8'))
        assert sprites['old_arrow_only_and_erased_footer_reproduced']
        assert sprites['native_vwf_positions_allocator_and_finalizer_executed']
        assert sprites['difficulty_and_footer_groups_independent']
        report['native_retained_sprites_verified']=True
    font=out/'STT2001_EN_v0.3.23_4x_font/SLPS-02863'
    dest=out/('STT2001_EN_v%s_4x_font/SLPS-02863'%version)
    if not dest.exists():
        shutil.copytree(font,dest)
    a={p.relative_to(font):p for p in font.rglob('*') if p.is_file()}
    b={p.relative_to(dest):p for p in dest.rglob('*') if p.is_file()}
    assert a.keys()==b.keys() and len(a)==757
    assert all(a[k].read_bytes()==b[k].read_bytes() for k in a)
    report['texture_pack_files']=757
    readme='''Super Tokusatsu Taisen 2001 English v{v} — local Balance Mode test
No GitHub release has been created for this build.

Intermission main menu: press Select to change Balance: OFF/ON.
Default OFF. Your choice is stored in ordinary in-game saves.
ON = Gentle: 1.5x battle XP/funds/materials and chapter-clear rewards;
S upgrades 25% cheaper, L upgrades 50% cheaper; ally attack/armor +10%,
enemy attack/armor -10%; refill ammo at a fresh stage, not when resuming.
HP/EN, movement, accuracy/evasion, growth, upgrade gains/caps and scripted
level setters are unchanged. Turning OFF restores future original rules;
earned rewards, levels and upgrades remain. Integer amounts round down.

Apply exactly ONE bare .xdelta matching your source BIN using Retro Trans
Tools > Apply xdelta. Japan = clean SLPS-02863 Japanese BIN; v0.3.18 = public
English v0.3.18; v0.3.23 = local English v0.3.23. Output a NEW BIN named
STT2001_EN_v{v}.bin and place the matching CUE next to it. Boot the CUE.
For PSP, convert the patched BIN/CUE using your usual PS1 EBOOT workflow.
Source/output hashes and decode checks are in the patch verification JSON.
Start the new image afresh and load an in-game save. Emulator save states
can retain the previous executable, which does not contain this setting.

DuckStation optional 4x fonts: extract the matching font ZIP into its data
directory (Tools > Open Data Directory), merging textures/SLPS-02863/ and
including config.yaml. Enable Texture Cache and Texture Replacements, then
reload replacements or restart. This pack is byte-identical to v0.3.23;
matching v0.3.18+ packs remain compatible. The toggle also uses native fonts.

Native MIPS regressions, save serialization and disc integrity are checked.
Actual emulator/PSP rendering and a complete campaign still need testing.
'''.format(v=version)
    if tuple(map(int,version.split('.'))) >= (0,3,25):
        readme+='\nSave/load layout repair: Stage N: Title captions fit their slots, completion\nstatus stays visible, and Turn/Total have separate four-digit columns.\nA v0.3.24 upgrade patch is also included for the previous local build.\n'
    (out/('STT2001_EN_v%s_README.txt'%version)).write_text(readme,encoding='utf-8')
    if tuple(map(int,version.split('.'))) >= (0,3,26):
        readme=readme.replace('Intermission main menu: press Select to change Balance: OFF/ON.',
            'Intermission > Difficulty: choose Normal or Gentle, then Circle to apply.\nUp/Down changes the choice; Cross cancels. The side panel shows the saved mode.\nSelect no longer changes difficulty.')
        readme=readme.replace('Default OFF.', 'Default Normal (OFF).')
        readme=readme.replace('English v0.3.18; v0.3.23 = local English v0.3.23. Output a NEW BIN named',
            'English v0.3.18; v0.3.23/v0.3.24/v0.3.25 = the matching local English BIN.\nOutput a NEW BIN named')
        readme=readme.replace('A v0.3.24 upgrade patch is also included for the previous local build.',
            'Upgrade patches from local v0.3.24 and v0.3.25 are also included.')
        readme+='\nCold boot the new disc, then load an ordinary in-game save. Do not resume an\nold emulator save state: it retains the previous executable/menu in RAM.\n'
    if tuple(map(int,version.split('.'))) >= (0,3,27):
        readme+='\nFixed the v0.3.26 missing Difficulty labels and erased stage footer. All\nlabels now draw together in a separate group; the arrow/header use yellow.\nA v0.3.26-to-v'+version+' upgrade patch is included.\n'
    if tuple(map(int,version.split('.'))) >= (0,3,28):
        readme='''Super Tokusatsu Taisen 2001 English v{v} - local test build
No GitHub release has been created for this build.

Intermission > Difficulty: choose Normal, Gentle or Stronger.
Up/Down or Left/Right changes the choice; Circle applies; Cross cancels.
The side panel shows the saved mode. Normal is the default.
Normal: original gameplay rules.
Gentle: 1.5x XP, 1.5x battle/chapter funds and materials;
ally attack/armor +10%, enemy attack/armor -10%.
Stronger: 3x XP, 2x battle/chapter funds and materials;
ally attack/armor +25%, enemy attack/armor -25%.
Gentle and Stronger both give S upgrades 25% cheaper, L upgrades 50%
cheaper, and full ammo at a fresh stage, not when resuming mid-stage.
HP/EN, movement, accuracy/evasion, growth, upgrade gains/caps and scripted
level setters are unchanged. Switching back keeps earned progress.
Integer amounts round down. All three choices persist in in-game saves.

Apply exactly ONE bare .xdelta matching your source BIN using Retro Trans
Tools > Apply xdelta. Japan = clean Japanese SLPS-02863; v0.3.18 and v0.3.27
= their matching public English BINs. Output a NEW BIN named
STT2001_EN_v{v}.bin and place its CUE next to it. Boot the CUE.
For PSP, convert the patched BIN/CUE using your usual PS1 EBOOT workflow.
Source hashes and verified decode results are in the patch verification JSON.
Cold boot the new image, then load an ordinary in-game save. Old emulator
save states retain the previous executable/menu in RAM.

Optional DuckStation 4x font: extract the matching ZIP into its data directory
(Tools > Open Data Directory), merging textures/SLPS-02863/ with config.yaml.
Enable Texture Cache and Texture Replacements, then reload or restart.
All 757 texture/config files remain unchanged; v0.3.18+ packs are compatible.
The new menu also works with native fonts and needs no texture replacement.

Native MIPS gameplay, menu controls, retained glyphs, save serialization and
disc integrity are checked. Emulator/PSP playtesting remains pending.
'''.format(v=version)
    if tuple(map(int,version.split('.'))) >= (0,3,29):
        readme=readme.replace('Normal','Default').replace('Stronger','Story')
    (out/('STT2001_EN_v%s_README.txt'%version)).write_text(readme,encoding='utf-8')
    archive=out/('STT2001_EN_v%s_4x_font.zip'%version)
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        z.writestr('README.txt',readme)
        z.write(ROOT/'incoming/GenEiLatin/LICENSE.txt','LICENSE-font.txt')
        for relative,path in b.items():
            z.write(path,'textures/SLPS-02863/'+relative.as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert all(z.read('textures/SLPS-02863/'+k.as_posix())==p.read_bytes() for k,p in b.items())
    retro=ROOT.parent/'retro-trans-tools'
    sys.path.insert(0,str(retro))
    from retro_trans.core import ENGINE_SHA256,ENGINE_MEMBER,encode,decode,sha256_file
    engine_zip=retro/'retro_trans/resources/xdelta3-windows.zip'
    assert sha256_file(engine_zip)==ENGINE_SHA256
    target=out/('STT2001_EN_v%s.bin'%version);target_hash=sha256_file(target)
    records=[]
    with tempfile.TemporaryDirectory(prefix='runtime-package-',dir=str(out)) as td:
        temp=Path(td);engine=temp/'xdelta3.exe'
        with zipfile.ZipFile(engine_zip) as z:
            engine.write_bytes(z.read(ENGINE_MEMBER))
        input_versions=['0.3.18','0.3.23']
        if tuple(map(int,version.split('.'))) >= (0,3,25):
            input_versions.append('0.3.24')
        if tuple(map(int,version.split('.'))) >= (0,3,26):
            input_versions.append('0.3.25')
        if tuple(map(int,version.split('.'))) >= (0,3,27):
            input_versions.append('0.3.26')
        if tuple(map(int,version.split('.'))) >= (0,3,28):
            input_versions=['0.3.18','0.3.27']
        for label,source in [('Japan',ROOT/'Super Tokusatsu Taisen 2001 (Japan).bin')]+[
            ('v'+v,out/('STT2001_EN_v%s.bin'%v)) for v in input_versions]:
            name='STT2001-English-'+('v'+version if label=='Japan' else label+'-to-v'+version)+'.xdelta'
            patch=temp/name
            print('Creating/checking '+name,flush=True)
            encode(engine,source,target,patch)
            decoded=temp/'roundtrip.bin'
            decode(engine,source,patch,decoded,target.stat().st_size)
            assert sha256_file(decoded)==target_hash and decoded.stat().st_size==target.stat().st_size
            decoded.unlink()
            records.append({'patch':name,'source':source.name,'source_sha256':sha256_file(source),
                'patch_bytes':patch.stat().st_size,'target_sha256':target_hash,'roundtrip_verified':True})
            shutil.copy2(patch,out/name)
    report['patches']=records
    report['retro_trans_tools_manual_xdelta_verified']=True
    (out/('STT2001_EN_v%s_patch_verification.json'%version)).write_text(json.dumps(report,indent=1)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=1))


if __name__=='__main__':
    main()
