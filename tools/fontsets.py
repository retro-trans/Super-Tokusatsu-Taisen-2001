"""Font variants.

The font in VRAM = MAPMAIN #7 left half (fixed) + a 256x256 sheet for the
right half that changes per scene: EVENT #11 (default, same as MAPMAIN #7's
right half) or one of EVENT #12-#23. Codes on the right half:
    446-781  (layer F0, rows of 21)    1118-1453 (layer F1)
Fixed codes: 0-445 and 782-1117.

    glyph_level(code, variant)  -> 12x16 array of 2bpp levels
    variant 11..23

python tools/fontsets.py label  -> work/font/variants.json
    auto-labels every variant glyph by exact pixel match with a glyph already
    named in charmap.json (default set); the rest are listed for manual reading.
"""
import json
import os
import struct
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNP = os.path.join(ROOT, "work", "source", "unpacked")
VARIANTS = list(range(11, 24))


def _sheet(path):
    d = open(path, "rb").read()
    p = 8 + struct.unpack_from("<I", d, 8)[0]
    _, x, y, w, h = struct.unpack_from("<IHHHH", d, p)
    raw = np.frombuffer(d[p + 12:p + 12 + w * 2 * h], dtype=np.uint8).reshape(h, w * 2)
    pix = np.empty((h, w * 4), dtype=np.uint8)
    pix[:, 0::2] = raw & 15
    pix[:, 1::2] = raw >> 4
    return pix


_MAIN = None
_VAR = {}


def main_sheet():
    global _MAIN
    if _MAIN is None:
        _MAIN = _sheet(os.path.join(UNP, "MAPMAIN", "0007.bin"))
    return _MAIN


def var_sheet(v):
    if v not in _VAR:
        _VAR[v] = _sheet(os.path.join(UNP, "EVENT", "%04d.bin" % v))
    return _VAR[v]


def is_variable(code):
    return 446 <= code < 782 or 1118 <= code < 1454


def glyph_level(code, variant=11):
    """2bpp levels (0..3) of a glyph, 16 rows x 12 cols (8 cols used for code<320)."""
    g = np.zeros((16, 12), np.uint8)
    if code < 320:
        x, y = (code % 32) * 8, (code // 32) * 16
        g[:, :8] = main_sheet()[y:y + 16, x:x + 8] & 3
        return g
    a = code - 110
    page, r = divmod(a, 336)
    shift = 0
    if code >= 782:
        page -= 2
        shift = 2
    x, y = (r % 21) * 12, (r // 21) * 16
    if page == 0:
        src = main_sheet()[y:y + 16, x:x + 12]
    else:
        src = var_sheet(variant)[y:y + 16, x:x + 12]
    return (src >> shift) & 3


def key(g):
    return g.tobytes()


def label():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from kana_table import TABLE
    cm = json.load(open(os.path.join(ROOT, "work", "font", "charmap.json"), encoding="utf-8"))
    known = {}
    for code in range(0, 1454):
        ch = TABLE.get(code) if code < 320 else cm["map"].get(str(code))
        if ch:
            known.setdefault(key(glyph_level(code, 11)), ch)
    out = {"variants": {}, "unknown": {}}
    for v in VARIANTS:
        lab, unk = {}, []
        for code in list(range(446, 782)) + list(range(1118, 1454)):
            g = glyph_level(code, v)
            if not g.any():
                continue
            ch = known.get(key(g))
            if ch:
                lab[str(code)] = ch
            else:
                unk.append(code)
        out["variants"][str(v)] = lab
        out["unknown"][str(v)] = unk
        print("variant %d: %d labelled, %d unknown" % (v, len(lab), len(unk)))
    # unknown glyph shapes shared across variants -> read once
    shapes = {}
    for v in VARIANTS:
        for code in out["unknown"][str(v)]:
            shapes.setdefault(key(glyph_level(code, v)), []).append([v, code])
    out["unknown_shapes"] = list(shapes.values())
    print("distinct unknown shapes:", len(shapes))
    json.dump(out, open(os.path.join(ROOT, "work", "font", "variants.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)




def build_maps():
    """Combine charmap.json (default/fixed), auto labels and vlabels.json into
    work/font/variant_maps.json: {variant: {code: char}} for codes 320-1453."""
    cm = json.load(open(os.path.join(ROOT, "work", "font", "charmap.json"), encoding="utf-8"))["map"]
    v = json.load(open(os.path.join(ROOT, "work", "font", "variants.json"), encoding="utf-8"))
    vl = json.load(open(os.path.join(ROOT, "work", "font", "vlabels.json"), encoding="utf-8"))["labels"]
    shape_label = {}
    for i, members in enumerate(v["unknown_shapes"]):
        if str(i) in vl:
            var, code = members[0]
            shape_label[glyph_level(code, var).tobytes()] = vl[str(i)]
    known = {}
    for code in range(320, 1454):
        if str(code) in cm:
            known.setdefault(glyph_level(code, 11).tobytes(), cm[str(code)])
    import hashlib
    op = os.path.join(ROOT, "work", "font", "shape_overrides.json")
    ov = json.load(open(op, encoding="utf-8")) if os.path.exists(op) else {}
    maps = {}
    for var in VARIANTS:
        m = {}
        for code in range(320, 1454):
            if not is_variable(code) or var == 11:
                if str(code) in cm:
                    m[str(code)] = cm[str(code)]
                continue
            k = glyph_level(code, var).tobytes()
            ch = known.get(k) or shape_label.get(k)
            if ch:
                m[str(code)] = ch
        for code in range(320, 1454):
            h = hashlib.md5(glyph_level(code, var).tobytes()).hexdigest()
            if h in ov:
                m[str(code)] = ov[h]
        maps[str(var)] = m
    json.dump(maps, open(os.path.join(ROOT, "work", "font", "variant_maps.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    return maps



# ---- battle font: BATTLE #538 (768x256, three texture pages) ----
_BAT = None


def battle_sheet():
    global _BAT
    if _BAT is None:
        _BAT = _sheet(os.path.join(UNP, "BATTLE", "0538.bin"))
    return _BAT


def battle_glyph_level(code):
    g = np.zeros((16, 12), np.uint8)
    S = battle_sheet()
    if code < 320:
        x, y = (code % 32) * 8, (code // 32) * 16
        g[:, :8] = S[y:y + 16, x:x + 8] & 3
        return g
    a = code - 110
    page, r = divmod(a, 336)
    shift = 0
    if code >= 782:
        page -= 2
        if code < 1454:
            shift = 2
    x, y = page * 256 + (r % 21) * 12, (r // 21) * 16
    if x + 12 > S.shape[1]:
        return g
    return (S[y:y + 16, x:x + 12] >> shift) & 3


def battle_label():
    """Auto-label battle font cells using every glyph labelled so far."""
    maps = json.load(open(os.path.join(ROOT, "work", "font", "variant_maps.json"), encoding="utf-8"))
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from kana_table import TABLE
    known = {}
    for var in VARIANTS:
        for code, ch in maps[str(var)].items():
            known.setdefault(glyph_level(int(code), var).tobytes(), ch)
    lab, unknown = {}, {}
    for code in range(0, 1790):
        g = battle_glyph_level(code)
        if not g.any():
            continue
        if code < 320:
            if code in TABLE:
                lab[str(code)] = TABLE[code]
            continue
        ch = known.get(g.tobytes())
        if ch:
            lab[str(code)] = ch
        else:
            unknown.setdefault(g.tobytes(), []).append(code)
    json.dump({"labels": lab, "unknown_shapes": list(unknown.values())},
              open(os.path.join(ROOT, "work", "font", "battle_font.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)
    print("battle font: %d labelled, %d unknown shapes" % (len(lab), len(unknown)))


if __name__ == "__main__":
    {"label": label, "maps": build_maps, "battle": battle_label}[sys.argv[1]]()


def battle_map():
    """Final battle font map {code: char} (auto labels + blabels.json)."""
    bf = json.load(open(os.path.join(ROOT, "work", "font", "battle_font.json"), encoding="utf-8"))
    bl = json.load(open(os.path.join(ROOT, "work", "font", "blabels.json"), encoding="utf-8"))["labels"]
    m = dict(bf["labels"])
    for i, codes in enumerate(bf["unknown_shapes"]):
        if str(i) in bl:
            for c in codes:
                m[str(c)] = bl[str(i)]
    import hashlib
    op = os.path.join(ROOT, "work", "font", "shape_overrides.json")
    ov = json.load(open(op, encoding="utf-8")) if os.path.exists(op) else {}
    for code in range(320, 1790):
        h = hashlib.md5(battle_glyph_level(code).tobytes()).hexdigest()
        if h in ov:
            m[str(code)] = ov[h]
    return m
