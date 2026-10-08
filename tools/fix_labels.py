"""Correct glyph labels from known words.

python tools/fix_labels.py "博土=博士" "太岩太太=大岩大太" ...

For each pair, finds dumped strings whose decoded text contains the wrong
word, reads the raw codes, and for every differing character records an
override for that glyph *shape* (so the fix reaches every font sheet that
contains the same glyph). Overrides go to work/font/shape_overrides.json and
are applied by fontsets.build_maps / battle_map. Re-run tools/dump_script.py
afterwards.
"""
import hashlib
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fontsets as F  # noqa: E402

P = os.path.join(ROOT, "work", "font", "shape_overrides.json")


def shape_key(code, font):
    g = F.battle_glyph_level(code) if font == "battle" else F.glyph_level(code, int(font))
    return hashlib.md5(g.tobytes()).hexdigest()


def raw_words(row):
    f = row["file"]
    if f == "SLPS":
        buf = open(os.path.join(ROOT, "work", "source", "disc", "SLPS_028.63"), "rb").read()
    else:
        buf = open(os.path.join(ROOT, "work", "source", "unpacked", f[:-4], f[-4:] + ".bin"), "rb").read()
    q = row["off"]
    out = []
    while True:
        w = struct.unpack_from("<H", buf, q)[0]
        if w in (0xFFFE, 0xFFFD):
            return out
        out.append(w)
        q += 2


def main():
    import dump_script as D
    rows = json.load(open(os.path.join(ROOT, "work", "script", "ja", "strings.json"), encoding="utf-8"))
    ov = json.load(open(P, encoding="utf-8")) if os.path.exists(P) else {}
    for pair in sys.argv[1:]:
        wrong, right = pair.split("=")
        assert len(wrong) == len(right), pair
        hits = 0
        for r in rows:
            if wrong not in (r["jp"] + (r["speaker_jp"] or "")):
                continue
            ws = [w for w in raw_words(r) if w < 0xFF00]
            chars = [(lambda c: c if c and len(c) == 1 else "")(D.ch(w, r["font"])) for w in ws]
            text = "".join(chars)
            i = text.find(wrong)
            if i < 0:
                continue
            for k in range(len(wrong)):
                if wrong[k] != right[k]:
                    code = ws[i + k]
                    if code < 320:
                        continue
                    ov[shape_key(code, r["font"])] = right[k]
            hits += 1
        print("%s: %d strings" % (pair, hits))
    json.dump(ov, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print("overrides:", len(ov))


if __name__ == "__main__":
    main()
