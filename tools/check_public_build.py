"""Rebuild with stripped English files and compare against a completed disc.

Dry run by default. --verify rebuilds archives and executable in memory, then
writes an English-only verification report. Movie sectors are checked elsewhere.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version')
    parser.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    print('Public-source rebuild: stripped English translations and offsets-only occurrence map.')
    if not args.verify:
        print('Dry run; --verify compares rebuilt files with v'+args.version)
        return
    os.environ['STT_PUBLIC']='1'
    import insert
    import vwf_patch
    from check_graphics_build import directory,read_file
    files,tr=insert.build_all()
    ef=insert.EF
    exe,_=vwf_patch.patch_exe((ROOT/'work/source/disc/SLPS_028.63').read_bytes(),ef['t_uni'],ef['t_bi'],ef['t_ex'])
    exe=insert.patch_exe_strings(exe,tr)
    exe=insert.patch_save_title(exe)
    exe=insert.patch_hero_select(exe)
    exe=insert.patch_var6(exe)
    import turn_popup,stats_layout,growth_layout,battle_voice_layout,intermission_layout
    for module in (turn_popup,stats_layout,growth_layout,battle_voice_layout,intermission_layout):
        exe=module.patch_exe(exe)
    insert.check_default_names(files)
    files['SLPS_028.63']=exe
    assert not insert.PROBLEMS,insert.PROBLEMS
    disc=ROOT/('work/output/STT2001_EN_v%s.bin'%args.version)
    entries=directory(disc);verified={}
    for name,data in files.items():
        assert data==read_file(disc,entries[name]),name+' differs in public mode'
        verified[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    report={'version':args.version,'public_english_only_build_matches':True,
            'files':verified,'build_problems':len(insert.PROBLEMS),
            'movies_checked_by_release_roundtrip':True}
    (ROOT/('work/output/STT2001_EN_v%s_public_source_verification.json'%args.version)).write_text(json.dumps(report,indent=1)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=1))


if __name__=='__main__':
    main()
