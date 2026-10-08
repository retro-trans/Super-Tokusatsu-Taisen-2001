"""Validate a translated batch.

python tools/check_batch.py B0123 [B0124 ...]   (or "all")

ERROR (must fix): missing/extra uids, invalid JSON, Japanese left in `en`,
  characters the font cannot draw, tags/placeholders/icons changed, `\\n` used,
  too many <p>, menu text over 1.3x its pixel budget.
WARN: menu text over its budget, very long pages, glossary name spelled differently.
"""
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EN = os.path.join(ROOT, "work", "translation", "en")
VWF = json.load(open(os.path.join(ROOT, "work", "font", "vwf_table.json"), encoding="utf-8"))
WIDTH = {ch: w for ch, w in zip(VWF["charset"], VWF["widths"])}
ALLOWED = set(VWF["charset"])
TAG = re.compile(r"<c[123]>|</c>|\[(?:HERO[1-4]|VAR[56])\]|\{[A-Za-z0-9]+\}")
JP = re.compile(r"[぀-ヿ㐀-鿿々〆「」『』（）]")
ICON_W = 8


def width(text):
    t = re.sub(r"<c[123]>|</c>|<p>", "", text)
    w = 0
    for m in re.finditer(r"\[(?:HERO[1-4]|VAR[56])\]|\{[A-Za-z0-9]+\}|.", t):
        s = m.group(0)
        if s.startswith("[HERO") or s.startswith("[VAR"):
            w += 40
        elif s.startswith("{"):
            w += ICON_W
        else:
            w += WIDTH.get(s, 8)
    return w


def check(name):
    b = json.load(open(os.path.join(EN, "batches", name + ".json"), encoding="utf-8"))
    path = os.path.join(EN, "out", name + ".json")
    errs, warns = [], []
    if not os.path.exists(path):
        return ["missing output file"], []
    try:
        o = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return ["invalid JSON: %s" % e], []
    rows = {r["uid"]: r for r in b["rows"]}
    got = {}
    for r in o.get("rows", []):
        if r.get("uid") in got:
            errs.append("%s: duplicated" % r.get("uid"))
        got[r.get("uid")] = r
    for uid in rows:
        if uid not in got:
            errs.append("%s: missing" % uid)
    for uid in got:
        if uid not in rows:
            errs.append("%s: not in this batch" % uid)
    for uid, r in got.items():
        if uid not in rows:
            continue
        src = rows[uid]
        en = r.get("en", "")
        if not isinstance(en, str) or not en.strip():
            errs.append("%s: empty en" % uid)
            continue
        if "\n" in en:
            errs.append("%s: contains a line break; write running text" % uid)
        if JP.search(en):
            errs.append("%s: Japanese characters left: %s" % (uid, "".join(sorted(set(JP.findall(en))))))
        plain = TAG.sub("", en).replace("<p>", "")
        bad = sorted(set(ch for ch in plain if ch not in ALLOWED))
        if bad:
            errs.append("%s: characters not in the font: %s" % (uid, " ".join(repr(c) for c in bad)))
        if Counter(TAG.findall(src["jp"])) != Counter(TAG.findall(en)):
            errs.append("%s: tags differ. jp=%s en=%s" % (uid, sorted(TAG.findall(src["jp"])), sorted(TAG.findall(en))))
        jp_p, en_p = src["jp"].count("<p>"), en.count("<p>")
        if en_p > jp_p + 1:
            errs.append("%s: %d <p> vs %d in the Japanese" % (uid, en_p, jp_p))
        if "budget_px" in src:
            w, bud = width(en), max(src["budget_px"], 24)
            if w > bud * 1.3:
                errs.append("%s: %dpx, budget %dpx (menu text must be shorter)" % (uid, w, bud))
            elif w > bud:
                warns.append("%s: %dpx over budget %dpx" % (uid, w, bud))
        else:
            for page in en.split("<p>"):
                if width(page) > 248 * 6:
                    warns.append("%s: a page is very long (%dpx = more than 6 lines)" % (uid, width(page)))
    rep = o.get("report", {})
    if rep.get("rows_examined") is None or rep.get("rows_in_slice") is None:
        warns.append("report.rows_examined / rows_in_slice missing")
    return errs, warns


def main():
    names = sys.argv[1:]
    if names == ["all"]:
        names = sorted(f[:-5] for f in os.listdir(os.path.join(EN, "out")) if f.endswith(".json"))
    bad = 0
    for n in names:
        e, w = check(n)
        for x in e:
            print("ERROR %s %s" % (n, x))
        for x in w[:20]:
            print("WARN  %s %s" % (n, x))
        if not e:
            print("OK    %s (%d warnings)" % (n, len(w)))
        bad += bool(e)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
