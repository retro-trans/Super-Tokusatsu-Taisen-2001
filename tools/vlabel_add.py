"""Record verified labels for unknown variant glyph shapes.
python tools/vlabel_add.py <first_shape_index> "<tokens>"
tokens: one per shape; '1'-'5' = that OCR candidate, '?' after = uncertain,
any other char = the correct character. Spaces are ignored.
Writes work/font/vlabels.json {shape_index: char}."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BATTLE = "--battle" in sys.argv
if BATTLE: sys.argv.remove("--battle")
P = os.path.join(ROOT, "work", "font", "blabels.json" if BATTLE else "vlabels.json")
ocr = json.load(open(os.path.join(ROOT, "work", "font", "battle_ocr.json" if BATTLE else "variant_ocr.json"), encoding="utf-8"))
lab = json.load(open(P, encoding="utf-8")) if os.path.exists(P) else {"labels": {}, "uncertain": []}
i = int(sys.argv[1])
groups = sys.argv[2].split()
bad = [g for g in groups[:-1] if len(g.replace("?", "")) != 10]
if bad: sys.exit("group(s) without 10 tokens: %s" % bad)
s = "".join(groups)
k = 0
while k < len(s):
    t = s[k]; unsure = k + 1 < len(s) and s[k + 1] == "?"
    ch = ocr["cands"][i][int(t) - 1][0] if t in "12345" else t
    lab["labels"][str(i)] = ch
    if unsure and i not in lab["uncertain"]: lab["uncertain"].append(i)
    i += 1; k += 2 if unsure else 1
json.dump(lab, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("labels %d, uncertain %d, next %d" % (len(lab["labels"]), len(lab["uncertain"]), i))
