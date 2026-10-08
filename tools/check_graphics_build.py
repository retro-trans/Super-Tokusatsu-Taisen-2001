"""Compare a completed graphics build with its pre-graphics English baseline.

python tools/check_graphics_build.py 0.3.4 0.3.3
Reads real ISO directory records and verifies complete patched archives,
unchanged game files, CM blocks and pre-existing English font layers.
"""
import json
import hashlib
import struct
import sys
from pathlib import Path

import gfx_translate
import repack

ROOT = Path(__file__).resolve().parents[1]


def directory(path):
    with path.open("rb") as f:
        f.seek(16*2352)
        pvd = f.read(2352)[24:2072]
        lba = struct.unpack_from("<I", pvd, 158)[0]
        size = struct.unpack_from("<I", pvd, 166)[0]
        raw, records = repack.read_dir(f, lba, size)
    return {name.decode().split(";")[0]:
            {"lba": struct.unpack_from("<I", raw, off+2)[0],
             "size": struct.unpack_from("<I", raw, off+10)[0]}
            for off, _, name in records if name not in (b"\0", b"\1")}


def read_file(path, info):
    with path.open("rb") as f:
        f.seek(info["lba"]*2352)
        count = (info["size"]+2047)//2048
        raw = f.read(count*2352)
    return b"".join(raw[i*2352+24:i*2352+2072] for i in range(count))[:info["size"]]


def file_hash(path, info):
    """Stream large movie/audio files without keeping them in memory."""
    digest = hashlib.sha256()
    remaining = info["size"]
    with path.open("rb") as f:
        f.seek(info["lba"]*2352)
        while remaining:
            count = min(128, (remaining+2047)//2048)
            raw = f.read(count*2352)
            if len(raw) != count*2352:
                raise AssertionError("truncated disc file")
            for i in range(count):
                used = min(2048, remaining)
                digest.update(raw[i*2352+24:i*2352+24+used])
                remaining -= used
    return digest.digest()


def main():
    version, baseline = sys.argv[1:3]
    output = ROOT / "work/output"
    new = output / ("STT2001_EN_v%s.bin" % version)
    old = output / ("STT2001_EN_v%s.bin" % baseline)
    nd, od = directory(new), directory(old)
    if nd.keys() != od.keys():
        raise AssertionError("disc file inventory changed")
    exported = json.loads(Path(str(new)+".files.json").read_text())
    if nd != {r["path"]: {"lba": r["lba"], "size": r["size"]} for r in exported}:
        raise AssertionError("disc directory differs from build file table")
    changed = {t["archive"]+".DAT" for t in gfx_translate.load_manifest()["targets"]}
    original = {key: read_file(old, od[key]) for key in changed}
    expected = dict(original)
    report = gfx_translate.patch_files(expected)
    for key in changed:
        if read_file(new, nd[key]) != expected[key]:
            raise AssertionError("built archive differs from expected graphics: %s" % key)
    unchanged = []
    for key in nd:
        if key in changed or key == "DUMMY.DAT":
            continue
        if nd[key]["size"] != od[key]["size"] or file_hash(new, nd[key]) != file_hash(old, od[key]):
            raise AssertionError("unrelated game file changed: %s" % key)
        unchanged.append(key)
    result = {"version": version, "baseline": baseline, "verified_graphics": len(report),
              "archives_match_expected": sorted(changed),
              "unchanged_game_files": sorted(unchanged),
              "disc_directory_verified": True, "emulator_verified": False}
    (output / ("STT2001_EN_v%s_graphics_verification.json" % version)).write_text(
        json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
