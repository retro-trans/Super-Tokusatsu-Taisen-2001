"""Package LOCAL balance-test patches; never contacts GitHub or publishes.

Dry-run by default. --write creates bare xdelta patches using the verified
local engine bundled with ../retro-trans-tools, then decodes and hashes each.
"""
import argparse
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version')
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--retro-tools', type=Path, default=ROOT.parent/'retro-trans-tools')
    args = parser.parse_args()
    import title_footer
    title_footer.validate_version(args.version)
    sys.path.insert(0, str(args.retro_tools.resolve()))
    from retro_trans.core import ENGINE_SHA256, ENGINE_MEMBER, encode, decode, sha256_file
    out = ROOT/'work/output'
    dest = out/('balance-test-v'+args.version)
    target = out/('STT2001_EN_v%s_balance.bin'%args.version)
    sources = [('Japan', ROOT/'Super Tokusatsu Taisen 2001 (Japan).bin'),
               ('v0.3.18', out/'STT2001_EN_v0.3.18.bin'),
               ('v'+args.version, out/('STT2001_EN_v%s.bin'%args.version))]
    engine_zip = args.retro_tools/'retro_trans/resources/xdelta3-windows.zip'
    assert sha256_file(engine_zip) == ENGINE_SHA256, 'unverified local patch engine'
    font = out/'STT2001_EN_v0.3.21_4x_font/SLPS-02863'
    font_files = sorted(p for p in font.rglob('*') if p.is_file())
    assert len(font_files) == 757 and sum(p.suffix == '.png' for p in font_files) == 756
    print('LOCAL package: 3 bare patches (Japan, v0.3.18, standard v%s -> balance), matching 757-file texture pack, instructions and hashes.'%args.version, flush=True)
    print('First-tier example: S HP 2000 -> 1500 funds; L HP 2000 -> 1000 funds.', flush=True)
    if not args.write:
        print('Dry run: no files written.')
        return
    assert not dest.exists(), 'local package already exists; do not silently overwrite'
    verification = json.loads((out/('STT2001_EN_v%s_balance_verification.json'%args.version)).read_text(encoding='utf-8'))
    assert verification['disc_tested'] and verification['disc_isolation']['optional_exe_only_changes_240_price_halfwords']
    public = json.loads((out/('STT2001_EN_v%s_balance_public_source_verification.json'%args.version)).read_text(encoding='utf-8'))
    assert public['public_english_only_build_matches']
    target_hash = sha256_file(target)
    entries = []
    with tempfile.TemporaryDirectory(prefix='balance-package-', dir=str(out)) as temporary:
        stage = Path(temporary)
        engine = stage/'xdelta3.exe'
        with zipfile.ZipFile(engine_zip) as bundle:
            engine.write_bytes(bundle.read(ENGINE_MEMBER))
        for label, source in sources:
            patch_name = 'STT2001-English-%s-to-v%s-balance.xdelta'%(label, args.version)
            patch = stage/patch_name
            print('Creating and checking '+patch_name, flush=True)
            source_hash = sha256_file(source)
            encode(engine, source, target, patch)
            decoded = stage/'roundtrip.bin'
            decode(engine, source, patch, decoded, target.stat().st_size)
            assert decoded.stat().st_size == target.stat().st_size and sha256_file(decoded) == target_hash
            decoded.unlink()
            assert sha256_file(source) == source_hash
            entries.append({'patch': patch_name, 'source': source.name, 'source_sha256': source_hash,
                            'source_bytes': source.stat().st_size, 'target_sha256': target_hash,
                            'target_bytes': target.stat().st_size, 'patch_bytes': patch.stat().st_size,
                            'patch_sha256': sha256_file(patch), 'roundtrip_verified': True})
        engine.unlink()
        readme = '''Super Tokusatsu Taisen 2001 v{v} - OPTIONAL BALANCE PROTOTYPE
Local testing only; not a GitHub release. Title: v{v}/balance.

Purchased unit-stat and weapon upgrades cost 25% less for S units and 50%
less for L units. Materials follow the same reduction. Large giants and
robots share the L prices. Upgrade gains/caps, XP, combat stats, enemies,
rewards, ammo and scenario rules retain their original behavior.
These percentages are initial tuning choices, not playthrough-tested balance.

Choose ONE patch that matches your source .bin:
- Japan: clean Japanese SLPS-02863 MODE2/2352 .bin; includes the translation.
- v0.3.18: published English v0.3.18 .bin; upgrades directly to this prototype.
- v{v}: standard English v{v} .bin; adds only the balance option/title label.
Other translated versions and CHD/EBOOT files are not direct patch inputs.
Source/output SHA-256 values are in PATCH-VERIFICATION.json.

Retro Trans Tools: open Apply xdelta, select the source .bin and matching
.xdelta, then choose a NEW output .bin. Manual Apply xdelta works offline;
this unpublished prototype is not offered in the automatic release catalog.
Use the supplied .cue beside the resulting {target}, with that exact filename.
For PSP, convert the patched BIN/CUE using your usual PS1 EBOOT workflow.
Keep your original image and an in-game save backup. Existing purchases are
not refunded; existing upgrades/levels are preserved. Prefer in-game saves
over emulator save states when switching builds. To return to normal prices,
switch back to the standard image; do not reapply patches to the balance image.

Matching DuckStation 4x texture pack:
Extract STT2001-4x-font-pack-v{v}.zip into DuckStation's data directory
(Tools > Open Data Directory), merging textures/SLPS-02863/. Include config.yaml.
Enable Texture Cache and Texture Replacements and restart/reload replacements.
The 757 files are byte-identical to v0.3.21; v0.3.18+ fonts also remain compatible.
The title version and balance marker are native artwork and need no texture pack.

Known limits: ammo persistence and forced-loss/last-enemy story events have
not been patched. No complete emulator, PSP or physical-console playthrough
has validated this prototype. See the included investigation and verification.
'''.format(v=args.version, target=target.name)
        (stage/'README.txt').write_text(readme, encoding='utf-8')
        cue = out/('STT2001_EN_v%s_balance.cue'%args.version)
        shutil.copy2(cue, stage/cue.name)
        shutil.copy2(ROOT/'docs/balance_patch.md', stage/'INVESTIGATION.md')
        shutil.copy2(out/('STT2001_EN_v%s_balance_verification.json'%args.version), stage/'NATIVE-VERIFICATION.json')
        report = {'version': args.version, 'variant': 'economy-v1', 'local_test_only': True,
                  'retro_trans_tools_manual_xdelta': True, 'patches': entries,
                  'texture_pack_files': 757, 'texture_pack_matches': '0.3.21'}
        (stage/'PATCH-VERIFICATION.json').write_text(json.dumps(report, indent=1)+'\n', encoding='utf-8')
        archive = stage/('STT2001-4x-font-pack-v%s.zip'%args.version)
        with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
            bundle.writestr('README.txt', readme)
            bundle.write(ROOT/'incoming/GenEiLatin/LICENSE.txt', 'LICENSE-font.txt')
            for path in font_files:
                bundle.write(path, 'textures/SLPS-02863/'+path.relative_to(font).as_posix())
        with zipfile.ZipFile(archive) as bundle:
            assert bundle.testzip() is None and len(bundle.namelist()) == 759
            for path in font_files:
                assert bundle.read('textures/SLPS-02863/'+path.relative_to(font).as_posix()) == path.read_bytes()
        # Retain the conventional unpacked package for later local build checks.
        conventional = out/('STT2001_EN_v%s_4x_font/SLPS-02863'%args.version)
        if not conventional.exists():
            shutil.copytree(font, conventional)
        else:
            assert {p.relative_to(conventional) for p in conventional.rglob('*') if p.is_file()} == {p.relative_to(font) for p in font_files}
        assert all((conventional/p.relative_to(font)).read_bytes() == p.read_bytes() for p in font_files)
        (stage/'SHA256SUMS.txt').write_text(''.join(sha256_file(p)+'  '+p.name+'\n' for p in sorted(stage.iterdir())), encoding='utf-8')
        dest.mkdir()
        for path in stage.iterdir():
            shutil.move(str(path), str(dest/path.name))
    print(json.dumps(report, indent=1), flush=True)
    print('Local test package: '+str(dest))


if __name__ == '__main__':
    main()
