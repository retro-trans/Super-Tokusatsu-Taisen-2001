"""Append transcribed kanji to work/font/charmap.json.
Usage: python tools/charmap_add.py <first_code> "<chars>"
A '?' right after a char marks it uncertain (stored in charmap_uncertain)."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "work", "font", "charmap.json")
m = json.load(open(P, encoding="utf-8")) if os.path.exists(P) else {"map": {}, "uncertain": []}
code = int(sys.argv[1]); s = sys.argv[2].replace(" ", "")
i = 0
while i < len(s):
    ch = s[i]; unsure = i + 1 < len(s) and s[i + 1] == "?"
    m["map"][str(code)] = ch
    if unsure and code not in m["uncertain"]:
        m["uncertain"].append(code)
    elif not unsure and code in m["uncertain"]:
        m["uncertain"].remove(code)
    code += 1; i += 2 if unsure else 1
json.dump(m, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("now %d codes, %d uncertain, last=%d" % (len(m["map"]), len(m["uncertain"]), code - 1))
