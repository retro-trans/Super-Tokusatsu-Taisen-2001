"""Count the translatable text in the game (glyph-coded strings).

Sources (see docs/text_format.md):
  STAGE.DAT  script overlays (entries starting with 0x800Exxxx pointers)
  BATTLE.DAT entry 540  battle quotes
  MAPMAIN.DAT entry 2   master database (names, units, weapons, items, help, system)
  MAPMAIN.DAT entry 27  sound-test titles
  SLPS_028.63           menu/system strings (glyph-coded, 0x9A900 area)

A "string" is a run of u16 codes ending in 0xFFFE. Characters counted =
glyph codes (< 1454) excluding the space glyph 0; control codes (0xFFxx) are
not counted. Dialogue speaker blocks (FF33 name FF30) are counted separately.

Usage: python tools/text_census.py  -> prints a table, writes work/text_census.json
"""
import glob
import json
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNP = os.path.join(ROOT, "work", "source", "unpacked")
NGLYPH = 1454


def words(path):
    d = open(path, "rb").read()
    return struct.unpack_from("<%dH" % (len(d) // 2), d)


def valid(w):
    return w < NGLYPH or w >= 0xFF00


def strings_in_span(ws):
    """Strings between the start of the first string and the last 0xFFFE."""
    fe = [i for i, w in enumerate(ws) if w == 0xFFFE]
    if not fe:
        return []
    start = fe[0]
    while start > 0 and valid(ws[start - 1]) and ws[start - 1] != 0xFFFF:
        start -= 1
    out, cur = [], []
    for w in ws[start:fe[-1] + 1]:
        if w == 0xFFFE:
            out.append(tuple(cur))
            cur = []
        else:
            cur.append(w)
    return out


def split_speaker(s):
    if s and s[0] == 0xFF33 and 0xFF30 in s:
        k = s.index(0xFF30)
        return s[1:k], s[k + 1:]
    return (), s


def nchars(s):
    return sum(1 for w in s if 0 < w < NGLYPH)


def census(name, strs):
    strs = [s for s in strs if all(valid(w) for w in s) and any(16 <= w < NGLYPH for w in s)]
    speakers, body, lines = [], [], 0
    for s in strs:
        sp, b = split_speaker(s)
        if sp:
            speakers.append(sp)
            lines += 1
        body.append(b)
    uniq = set(strs)
    return {
        "source": name,
        "strings": len(strs),
        "unique_strings": len(uniq),
        "dialogue_lines": lines,
        "chars": sum(nchars(b) for b in body),
        "speaker_chars": sum(nchars(sp) for sp in speakers),
        "unique_chars": sum(nchars(split_speaker(s)[1]) for s in uniq),
        "page_breaks": sum(s.count(0xFFFC) for s in strs),
    }


def main():
    rows = []
    stage = []
    for f in sorted(glob.glob(os.path.join(UNP, "STAGE", "*.bin"))):
        d = open(f, "rb").read(4)
        if d[2:4] == b"\x0e\x80":
            stage += strings_in_span(words(f))
    rows.append(census("Stage scripts (STAGE.DAT x90)", stage))
    bq = [s for s in strings_in_span(words(os.path.join(UNP, "BATTLE", "0540.bin")))]
    rows.append(census("Battle quotes (BATTLE.DAT #540)", bq))
    rows.append(census("Database: names/units/weapons/help (MAPMAIN #2)", strings_in_span(words(os.path.join(UNP, "MAPMAIN", "0002.bin")))))
    rows.append(census("Sound-test titles (MAPMAIN #27)", strings_in_span(words(os.path.join(UNP, "MAPMAIN", "0027.bin")))))
    exe = words(os.path.join(ROOT, "work", "source", "disc", "SLPS_028.63"))
    exe_strs, cur = [], []
    for w in exe:
        if w == 0xFFFE:
            if cur and len(cur) < 200:
                exe_strs.append(tuple(cur))
            cur = []
        elif valid(w):
            cur.append(w)
        else:
            cur = []
    rows.append(census("Executable menus (SLPS_028.63)", exe_strs))
    tot = {k: sum(r[k] for r in rows) for k in rows[0] if k != "source"}
    tot["source"] = "TOTAL"
    rows.append(tot)
    print("%-50s %8s %8s %8s %9s %9s %9s" % ("source", "strings", "unique", "dlg", "chars", "uniq_ch", "spk_ch"))
    for r in rows:
        print("%-50s %8d %8d %8d %9d %9d %9d" % (r["source"], r["strings"], r["unique_strings"], r["dialogue_lines"], r["chars"], r["unique_chars"], r["speaker_chars"]))
    json.dump(rows, open(os.path.join(ROOT, "work", "text_census.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
