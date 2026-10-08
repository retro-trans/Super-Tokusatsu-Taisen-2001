"""Dump every translatable string of the game with the right font.

Output (local only, contains Japanese):
  work/script/ja/strings.json   all string occurrences
      {id, src, file, off, term, font, jp}   (jp = decoded with tags, see textcodec)
  work/script/ja/units.json     unique translation units in play order
      {uid, jp, speaker_jp, count, first, sources}

Sources:
  stage   STAGE.DAT script overlays (u32 pointer table @0x800E0000 + strings); font = per-stage variant
  bquote  BATTLE.DAT unit entries: overlay at +0x8434 (pointer table + strings); default font
  encyc   BATTLE.DAT #540 encyclopedia (u32 offset table + records); battle font (#538)
  db      MAPMAIN.DAT #2 database (u16 offset table); default font
  music   MAPMAIN.DAT #27 sound-test titles; default font
  exe     SLPS_028.63 menu strings; default font
Copies that are rebuilt from these at insertion time (not dumped): STAGE #630-719
(compressed stage scripts), MAPMAIN #24 (compressed DB), MAPMAIN #3 (DB, index-aligned).
"""
import glob
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fontsets as F  # noqa: E402
from kana_table import TABLE  # noqa: E402

UNP = os.path.join(ROOT, "work", "source", "unpacked")
OUT = os.path.join(ROOT, "work", "script", "ja")
VMAPS = json.load(open(os.path.join(ROOT, "work", "font", "variant_maps.json"), encoding="utf-8"))
FONTS = {str(v): VMAPS[str(v)] for v in range(11, 24)}
FONTS["battle"] = F.battle_map()
STAGE_VAR = json.load(open(os.path.join(ROOT, "work", "font", "stage_variant.json")))
PLACE = {0xFF01: "[HERO1]", 0xFF02: "[HERO2]", 0xFF03: "[HERO3]", 0xFF04: "[HERO4]",
         0xFF05: "[VAR5]", 0xFF06: "[VAR6]"}


ICONS = {277: "{direct}", 278: "{ranged}"}
ICONS11 = {1433: "{bullet}", 1434: "{elec}", 1435: "{beam}", 1436: "{water}", 1437: "{fire}", 1438: "{special}"}


def ch(code, font):
    if code in ICONS:
        return ICONS[code]
    if code < 320:
        return TABLE.get(code)
    if font == "11" and code in ICONS11:
        return ICONS11[code]
    return FONTS[font].get(str(code))


def decode(ws, font, dialogue=True):
    """-> (speaker or None, body) with tags."""
    ws = list(ws)
    speaker = None
    i = 0
    if dialogue and ws and ws[0] == 0xFF33 and 0xFF30 in ws:
        k = ws.index(0xFF30)
        speaker = decode(ws[1:k], font)[1]
        i = k + 1
        if i < len(ws) and ws[i] == 0xFFFB:
            i += 1
    out = []
    for w in ws[i:]:
        if w == 0xFFFB:
            out.append("\n")
        elif w == 0xFFFC:
            out.append("<p>")
        elif w == 0xFF30:
            out.append("</c>")
        elif w in (0xFF31, 0xFF32, 0xFF33):
            out.append("<c%d>" % (w - 0xFF30))
        elif w in PLACE:
            out.append(PLACE[w])
        elif w < 0xFF00 and ch(w, font):
            out.append(ch(w, font))
        else:
            out.append("{%04X}" % w)
    return speaker, "".join(out)


def words(buf, start=0, end=None):
    end = len(buf) if end is None else end
    return struct.unpack_from("<%dH" % ((end - start) // 2), buf, start)


def overlay_strings(buf, base):
    """Strings of an overlay section starting at byte `base` of buf:
    u32 pointers (0x800Exxxx) then strings ending in FFFE/FFFD."""
    ptrs = []
    p = base
    while p + 4 <= len(buf) and struct.unpack_from("<I", buf, p)[0] >> 16 == 0x800E:
        ptrs.append(struct.unpack_from("<I", buf, p)[0])
        p += 4
    if not ptrs:
        return []
    strings_start = p
    targets = sorted(set(x - 0x800E0000 + base for x in ptrs))
    out = []
    pos = strings_start
    last = max(targets)
    while pos <= last and pos + 2 <= len(buf):
        q = pos
        while q + 2 <= len(buf):
            w = struct.unpack_from("<H", buf, q)[0]
            if w in (0xFFFE, 0xFFFD):
                break
            q += 2
        out.append((pos, words(buf, pos, q), struct.unpack_from("<H", buf, q)[0]))
        pos = q + 2
    return out


def table16_strings(buf, first_off):
    """u16 offset table strings (DB / music): walk FFFE-terminated strings from first_off."""
    out = []
    pos = first_off
    while pos + 2 <= len(buf):
        q = pos
        while q + 2 <= len(buf) and struct.unpack_from("<H", buf, q)[0] not in (0xFFFE, 0xFFFD):
            q += 2
        if q + 2 > len(buf):
            break
        out.append((pos, words(buf, pos, q), struct.unpack_from("<H", buf, q)[0]))
        pos = q + 2
        if pos >= len(buf) or struct.unpack_from("<H", buf, pos)[0] == 0 and \
                all(b == 0 for b in buf[pos:pos + 32]):
            break
    return out


def is_text(ws):
    return all(w < 1454 or w >= 0xFF00 for w in ws)


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []

    def add(src, fname, off, ws, term, font):
        if not ws or not is_text(ws):
            return
        sp, body = decode(ws, font, dialogue=src in ("stage", "bquote"))
        rows.append({"id": "%s:%s:%05X" % (src, fname, off), "src": src, "file": fname, "off": off,
                     "term": "%04X" % term, "font": font, "speaker_jp": sp, "jp": body})

    # stage strings: scene font (per-stage variant) or map font (default) -- choose per string
    import math
    from collections import Counter
    stage_items = []
    for k in sorted(STAGE_VAR):
        buf = open(os.path.join(UNP, "STAGE", "%s.bin" % k), "rb").read()
        for off, ws, term in overlay_strings(buf, 0):
            stage_items.append((k, off, ws, term))
    big, uni = Counter(), Counter()

    def plain(ws, font):
        return "".join((ch(w, font) or "?") for w in ws if w < 0xFF00)
    for k, off, ws, term in stage_items:
        t = plain(ws, str(STAGE_VAR[k]))
        uni.update(t)
        big.update(t[i:i + 2] for i in range(len(t) - 1))
    V = len(uni) + 1

    def lp(t):
        return sum(math.log((big[t[i:i + 2]] + 0.1) / (uni[t[i]] + 0.1 * V)) for i in range(len(t) - 1))
    nmap = 0
    for k, off, ws, term in stage_items:
        font = str(STAGE_VAR[k])
        if any(F.is_variable(w) for w in ws if w < 0xFF00):
            if lp(plain(ws, "11")) > lp(plain(ws, font)) + 2.0:
                font = "11"
                nmap += 1
        add("stage", "STAGE%s" % k, off, ws, term, font)
    print("stage strings using the map font:", nmap)
    for f in sorted(glob.glob(os.path.join(UNP, "BATTLE", "*.bin"))):
        buf = open(f, "rb").read()
        if len(buf) > 0x8438 and buf[:4] == b"\x10\0\0\0" and struct.unpack_from("<I", buf, 0x8434)[0] >> 16 == 0x800E:
            name = "BATTLE" + os.path.basename(f)[:4]
            for off, ws, term in overlay_strings(buf, 0x8434):
                add("bquote", name, off, ws, term, "11")
    buf = open(os.path.join(UNP, "BATTLE", "0540.bin"), "rb").read()
    first = struct.unpack_from("<I", buf, 0)[0]
    pos = first
    while pos + 2 < len(buf):
        q = pos
        while q + 2 <= len(buf) and struct.unpack_from("<H", buf, q)[0] not in (0xFFFE, 0xFFFD):
            q += 2
        if q + 2 > len(buf):
            break
        add("encyc", "BATTLE0540", pos, words(buf, pos, q), struct.unpack_from("<H", buf, q)[0], "battle")
        pos = q + 2
    for idx, name in ((2, "db"), (27, "music")):
        buf = open(os.path.join(UNP, "MAPMAIN", "%04d.bin" % idx), "rb").read()
        first = struct.unpack_from("<H", buf, 0)[0]
        for off, ws, term in table16_strings(buf, first):
            add(name, "MAPMAIN%04d" % idx, off, ws, term, "11")
    exe = open(os.path.join(ROOT, "work", "source", "disc", "SLPS_028.63"), "rb").read()
    for off, ws, term in table16_strings(exe, 0x9A900):
        if off > 0x9AE00:
            break
        if any(16 <= w < 1454 for w in ws):
            add("exe", "SLPS", off, ws, term, "11")

    json.dump(rows, open(os.path.join(OUT, "strings.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    units, index = [], {}
    for r in rows:
        key = (r["speaker_jp"], r["jp"])
        if key not in index:
            index[key] = len(units)
            units.append({"uid": "U%05d" % len(units), "speaker_jp": r["speaker_jp"], "jp": r["jp"],
                          "count": 0, "first": r["id"], "sources": []})
        u = units[index[key]]
        u["count"] += 1
        if r["src"] not in u["sources"]:
            u["sources"].append(r["src"])
        r["uid"] = u["uid"]
    json.dump(rows, open(os.path.join(OUT, "strings.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    json.dump(units, open(os.path.join(OUT, "units.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    from collections import Counter
    c = Counter(r["src"] for r in rows)
    cu = Counter(u["sources"][0] for u in units)
    print("strings", len(rows), dict(c))
    print("unique units", len(units), dict(cu))
    print("unique JP chars", sum(len(u["jp"]) for u in units))


if __name__ == "__main__":
    main()
