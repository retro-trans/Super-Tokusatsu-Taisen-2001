"""Audit actual built dialogue, sprite scripts, graphics and retained movies.

python tools/check_dialogue_layout.py 0.3.7 0.3.6
Checks both dialogue overlays and their compressed stage copies, using the
executable's VWF thresholds and maximum saved-name lengths. Compares English
content with the baseline independently of wrapping and glyph tokenization.
"""
import hashlib
import json
import re
import struct
import sys
from collections import Counter
from pathlib import Path

import cm
import dump_script as D
import gfx
import gfx_translate
import insert
import repack
import stage_cards
from check_graphics_build import directory, read_file, file_hash

ROOT = Path(__file__).resolve().parents[1]
EDITS = json.loads((ROOT / "work/translation/en/dialogue_layout.en.json").read_text(encoding="utf-8"))
REVERSE = {v: k for k, v in insert.EF["encode"].items()}
REVERSE.update({v: k for k, v in insert.EF.get("encode_ex", {}).items()})
PH = {insert.CTRL[k]: v for k, v in insert.PH_W.items()}


def width(code):
    if code in PH:
        return PH[code]
    if code >= 0xFF00:
        return 0
    if 320 <= code < 446:
        table = insert.EF["t_uni"]
    elif 782 <= code < 1118:
        table = insert.EF["t_bi"]
    elif 446 <= code < 782:
        table = insert.EF["t_ex"]
    else:
        return 8 if code < 320 else 12
    return sum(t <= code for t in table)


def content(words):
    # Whitespace and page/color controls may move; visible content may not.
    text = re.sub(r"\s+", "", "".join(REVERSE.get(c, "{%04X}" % c) for c in words
                  if c not in (0, 0xFFFB, 0xFFFC, 0xFF30, 0xFF31, 0xFF32, 0xFF33)))
    for before, after in EDITS["choice_rewordings"]:
        text = text.replace(re.sub(r"\s+", "", before), re.sub(r"\s+", "", after))
    for before, after in EDITS.get("speaker_display", {}).items():
        text = text.replace(re.sub(r"\s+", "", before), re.sub(r"\s+", "", after))
    return text


def check_words(words, kind, stats):
    words = list(words)
    if words and words[0] == 0xFF33 and 0xFF30 in words:
        end = words.index(0xFF30)
        speaker = sum(width(c) for c in words[1:end])
        stats["maximum_speaker_width"] = max(stats["maximum_speaker_width"], speaker)
        assert speaker <= 220, ("speaker overflow", speaker, "".join(REVERSE.get(c, "{%04X}" % c) for c in words[1:end]))
        words = words[end+1:]
        if words and words[0] == 0xFFFB:
            words = words[1:]
    plain = "".join(REVERSE.get(c, "\n" if c == 0xFFFB else "") for c in words)
    rows = plain.splitlines()
    choice = len(rows) >= 2 and all(r.startswith('"') and r.endswith('"') for r in rows)
    if choice:
        assert 0xFFFC not in words, "choice menu paginated"
        stats["choice_menus"] += 1
        stats["maximum_choice_options"] = max(stats["maximum_choice_options"], len(rows))
    lines, advance, pages = 1, 0, 1
    for code in words + [0xFFFC]:
        if code in (0xFFFB, 0xFFFC):
            stats["maximum_line_width"] = max(stats["maximum_line_width"], advance)
            assert advance <= 220, ("line overflow", advance)
            advance = 0
            if code == 0xFFFB:
                lines += 1
            else:
                if not choice:
                    stats["maximum_"+kind+"_page_lines"] = max(stats["maximum_"+kind+"_page_lines"], lines)
                    assert lines <= (3 if kind == "stage" else 2), ("too many lines", lines)
                lines = 1
                pages += 1
        else:
            advance += width(code)
    stats[kind+"_strings"] += 1
    stats[kind+"_pages"] += pages-1


def overlay(before, after, base, kind, stats):
    old = D.overlay_strings(before, base)
    new = D.overlay_strings(after, base)
    assert len(old) == len(new), "dialogue count changed"
    n = 0
    while struct.unpack_from("<I", before, base+n*4)[0] >> 16 == 0x800E:
        n += 1
    op = struct.unpack_from("<%dI" % n, before, base)
    np = struct.unpack_from("<%dI" % n, after, base)
    oi = {off: i for i, (off, _, _) in enumerate(old)}
    ni = {off: i for i, (off, _, _) in enumerate(new)}
    assert [oi[p-0x800E0000+base] for p in op] == [ni[p-0x800E0000+base] for p in np], "pointer order changed"
    for (_, ow, ot), (_, nw, nt) in zip(old, new):
        assert ot == nt, "dialogue terminator changed"
        assert content(ow) == content(nw), "visible English content changed"
        check_words(nw, kind, stats)


def main():
    version, baseline = sys.argv[1:3]
    new = ROOT / ("work/output/STT2001_EN_v%s.bin" % version)
    old = ROOT / ("work/output/STT2001_EN_v%s.bin" % baseline)
    nd, od = directory(new), directory(old)
    table = json.loads(Path(str(new)+".files.json").read_text())
    assert nd == {r["path"]: {"lba": r["lba"], "size": r["size"]} for r in table}
    stats = Counter()
    ns, os_ = [repack.dat_entries(read_file(p, directory(p)["STAGE.DAT"])) for p in (new, old)]
    for i, key in enumerate(sorted(D.STAGE_VAR)):
        idx = int(key)
        overlay(os_[idx], ns[idx], 0, "stage", stats)
        assert cm.blocks(ns[630+i])[4] == ns[idx][:len(cm.blocks(ns[630+i])[4])], "stage compressed copy mismatch"
        original = (ROOT / "work/source/unpacked/STAGE" / ("%04d.bin" % (idx+1))).read_bytes()
        expected, routines = stage_cards.patch_script(original)
        # Scene commands are separate from the dialogue overlay. Compare the
        # entire script, including its unchanged relative branches and padding.
        prefix = original.find(stage_cards.PREFIX)
        if routines:
            assert prefix >= 0
            assert ns[idx+1] == expected, "card script differs"
            block = cm.blocks(ns[630+i])[5]
            assert block == expected[:len(block)], "compressed card script differs"
        stats["stage_card_routines"] += routines
    nb, ob = [repack.dat_entries(read_file(p, directory(p)["BATTLE.DAT"])) for p in (new, old)]
    for a, b in zip(ob, nb):
        if len(a) > 0x8438 and a[:4] == b"\x10\0\0\0" and struct.unpack_from("<I", a, 0x8434)[0] >> 16 == 0x800E:
            overlay(a, b, 0x8434, "bquote", stats)
    targets = gfx_translate.load_manifest()["targets"]
    archives = {name: repack.dat_entries(read_file(new, nd[name+".DAT"]))
                for name in {t["archive"] for t in targets}}
    for target in targets:
        entries = archives[target["archive"]]
        actual = entries[target["entry"]]
        if "block" in target:
            actual = cm.blocks(actual)[target["block"]]
        source = gfx_translate.source(target)
        expected, _ = gfx_translate.render(source, target)
        gfx_translate.verify(source, actual, target)
        assert actual == expected, "built graphic differs from exported source"
        stats["verified_graphics"] += 1
    # The movie region, including XA audio and parity, must match the approved
    # baseline byte for byte even if later archives move during repacking.
    movie = nd["MOVIE.STR"]
    assert movie == od["MOVIE.STR"]
    count = (movie["size"]+2047)//2048*2352
    offset = movie["lba"]*2352
    digest = hashlib.sha256()
    with new.open("rb") as a, old.open("rb") as b:
        a.seek(offset); b.seek(offset)
        while count:
            size = min(count, 4*1024*1024)
            chunk = a.read(size)
            assert chunk == b.read(size), "approved movies changed"
            digest.update(chunk)
            count -= size
    unchanged = []
    for name in nd:
        if name in ("STAGE.DAT", "BATTLE.DAT", "EVENT.DAT", "DUMMY.DAT"):
            continue
        assert nd[name]["size"] == od[name]["size"]
        assert file_hash(new, nd[name]) == file_hash(old, od[name]), ("unrelated file changed", name)
        unchanged.append(name)
    result = {"version": version, "baseline": baseline, "all_checks_passed": True,
              "stats": dict(stats), "english_content_and_pointer_order_preserved": True,
              "disc_directory_verified": True, "movies_raw_sha256": digest.hexdigest(),
              "movie_region_byte_identical": True, "unchanged_files": unchanged,
              "emulator_verified": False}
    path = ROOT / ("work/output/STT2001_EN_v%s_layout_verification.json" % version)
    path.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
