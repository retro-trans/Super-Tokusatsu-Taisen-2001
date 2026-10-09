"""Install matching font textures without deleting older texture IDs.

Dry run by default; --write backs up overwritten files and saves a report.
Pass DuckStation's active data folder as --data-dir.
"""
import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERIAL = 'SLPS-02863'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version')
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    source = ROOT / ('work/output/STT2001_EN_v%s_4x_font' % args.version) / SERIAL
    target = args.data_dir.resolve() / 'textures' / SERIAL
    assert (args.data_dir / 'settings.ini').is_file(), 'Not a DuckStation data folder'
    files = sorted((source / 'replacements').glob('texupload-*.png'))
    assert files, 'Pack contains no textures'
    additions, changes = [], []
    for path in files:
        destination = target / 'replacements' / path.name
        if not destination.exists():
            additions.append(path)
        elif digest(path) != digest(destination):
            changes.append(path)
    config = target / 'config.yaml'
    previous = config.read_bytes() if config.exists() else b''
    body = previous.decode('utf-8-sig')
    option = re.compile(r'^MaxVRAMWriteSplits:[^\r\n]*', re.MULTILINE)
    if not re.search(r'^MaxVRAMWriteSplits:\s*true\s*(?:#.*)?$', body, re.MULTILINE):
        body = option.sub('MaxVRAMWriteSplits: true', body) if option.search(body) else body.rstrip() + '\nMaxVRAMWriteSplits: true\n'
        updated_config = body.encode('utf-8')
    else:
        updated_config = previous
    report = {'version': args.version, 'target': str(target), 'pack_textures': len(files),
              'new_texture_ids': len(additions), 'updated_images': len(changes),
              'config_changed': updated_config != previous,
              'older_texture_ids_preserved': True, 'written': args.write,
              'sample_new_ids': [p.name for p in additions[:3]]}
    if args.write:
        backup = ROOT / 'work/output/font_install_backups' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        for path in changes:
            saved = backup / 'replacements' / path.name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target / 'replacements' / path.name, saved)
        if updated_config != previous and config.exists():
            backup.mkdir(parents=True, exist_ok=True)
            shutil.copy2(config, backup / 'config.yaml')
        (target / 'replacements').mkdir(parents=True, exist_ok=True)
        for path in additions + changes:
            shutil.copy2(path, target / 'replacements' / path.name)
        if updated_config != previous:
            config.write_bytes(updated_config)
        assert all(digest(p) == digest(target / 'replacements' / p.name) for p in files)
        assert config.read_bytes() == updated_config
        report['all_pack_files_verified'] = True
        report['backup'] = str(backup) if backup.exists() else None
        report['installed_texture_files'] = len(list((target / 'replacements').glob('*.png')))
        output = ROOT / ('work/output/STT2001_EN_v%s_font_install.json' % args.version)
        output.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
