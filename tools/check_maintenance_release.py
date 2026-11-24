"""Bind retained v0.9.7 native-art/font audits to the exact v0.9.9 text fixes.

This deliberately supports one reviewed delta. A future maintenance release
must describe and check its own changes before reusing any historical audit.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from check_graphics_build import directory, read_file, file_hash
import repack
import title_footer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'work/output'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    # These execute complete raw-disc delta checks, not merely string searches.
    for tool, version in [('check_issue5.py', '0.9.8'), ('check_issue6.py', '0.9.9')]:
        subprocess.run([sys.executable, str(ROOT / 'tools' / tool), '--version', version],
                       cwd=ROOT, check=True)
    baseline = OUT / 'STT2001_EN_v0.9.7.bin'
    target = OUT / 'STT2001_EN_v0.9.9.bin'
    assert digest(baseline) == '110ab27fcbb9de6b5dc991e7f6ad2dd25291733f516814ef044951bcdacf92ae'
    target_hash = digest(target)
    assert target_hash == '894c64cc62527e7c8362cd1db276e3521c21d235046257deb4fc7b548b7881aa'
    bd, td = directory(baseline), directory(target)
    assert bd == td
    unchanged = {}
    for name in bd:
        if name not in ('MAPMAIN.DAT', 'STAGE.DAT'):
            old_hash, new_hash = file_hash(baseline, bd[name]), file_hash(target, td[name])
            assert old_hash == new_hash, name
            unchanged[name] = new_hash.hex()
            continue
        old, new = read_file(baseline, bd[name]), read_file(target, td[name])
        if name == 'MAPMAIN.DAT':
            files = {name: old}
            title_footer.patch_files(files, '0.9.9')
            assert files[name] == new
        elif name == 'STAGE.DAT':
            a, b = repack.dat_entries(old), repack.dat_entries(new)
            assert len(a) == len(b)
            assert [i for i, (x, y) in enumerate(zip(a, b)) if x != y] == [68, 117, 639, 646]
    assert title_footer.verify_disc(target, '0.9.9')
    reports = {}
    for suffix in ('font_verification', 'font_effects_verification', 'artwork_verification'):
        path = OUT / ('STT2001_EN_v0.9.7_' + suffix + '.json')
        data = json.loads(path.read_text(encoding='utf-8'))
        assert data['version'] == '0.9.7'
        if suffix == 'artwork_verification':
            assert data['exact_expected_archives'] and data['title_copies_verified']
        else:
            assert data.get('all_checks_passed', data.get('dialogue_content_and_pointer_order_preserved'))
        reports[suffix] = digest(path)
    checks = json.loads((OUT / 'release-checks-v0.9.7.json').read_text(encoding='utf-8'))
    assert len(checks) == 9 and all(r['returncode'] == 0 for r in checks)
    result = dict(version='0.9.9', baseline='0.9.7', all_checks_passed=True,
                  baseline_sha256=digest(baseline), target_sha256=target_hash,
                  changed_stage_entries=[68, 117, 639, 646],
                  changed_text_rows=3, scene_commands_and_pointer_order_preserved=True,
                  mapmain_only_exact_automatic_title_stamp=True,
                  all_other_raw_disc_bytes_identical=True,
                  unchanged_file_sha256=unchanged, retained_reports=reports,
                  retained_report_execution_version='0.9.7',
                  current_delta_checks=['v0.9.7 -> v0.9.8: issue #5 complete delta',
                                        'v0.9.8 -> v0.9.9: issue #6 complete delta and native objective draw'],
                  font_style_and_artwork_byte_identity_verified=True,
                  dialogue_preservation_exceptions='Only the two Atefarina rows and Father objective; separately verified with their original occurrence IDs.',
                  emulator_verified=False)
    (OUT / 'STT2001_EN_v0.9.9_maintenance_verification.json').write_text(
        json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('PASS: exact public baseline, three approved text changes, native assets and retained audit hashes.')


if __name__ == '__main__':
    main()
