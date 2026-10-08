"""Split the unique translation units into batches for translator agents.

Input : work/script/ja/units.json, work/glossary/names.json
Output: work/translation/en/batches/B0001.json ...  (80 rows each, play order)
        work/translation/en/auto.json   units with no Japanese text (copied as-is)
        work/translation/en/plan.json   batch -> source/files/char count

Batch rows: {uid, kind, speaker_jp, speaker_en, jp, budget}
  kind   dialogue | narration | quote | encyclopedia | menu | music
  budget for one-line UI strings: the original width in pixels (8 px per
         kana/latin, 12 px per kanji); English VWF letters are ~5-7 px wide.
"""
import json
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(ROOT, "work", "script", "ja", "units.json")
GLOSS = os.path.join(ROOT, "work", "glossary", "names.json")
OUT = os.path.join(ROOT, "work", "translation", "en")
SIZE = 80
JP = re.compile(r"[぀-ヿ㐀-鿿々〆]")


def px(text):
    w = 0
    for ch in re.sub(r"<[^>]+>|\[[A-Z0-9]+\]|\{[a-zA-Z0-9]+\}", "", text):
        w += 12 if re.match(r"[㐀-鿿々]", ch) else 8
    return w


def to_ascii(s):
    s = s.replace("「", "").replace("」", "").replace("『", '"').replace("』", '"')
    s = s.replace("。", ".").replace("、", ", ").replace("□", " Kai ").replace(chr(10), " ")
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r" +", " ", s).strip()
    return re.sub(r"Kai (\d)", r"Kai-\g<1>", s)


def main():
    units = json.load(open(UNITS, encoding="utf-8"))
    gloss = json.load(open(GLOSS, encoding="utf-8"))
    os.makedirs(os.path.join(OUT, "batches"), exist_ok=True)
    auto, rows = {}, []
    for u in units:
        src = u["sources"][0]
        text = u["jp"]
        if not JP.search(text) and not (u["speaker_jp"] and JP.search(u["speaker_jp"])):
            auto[u["uid"]] = to_ascii(text)
            continue
        if src == "stage":
            kind = "dialogue" if u["speaker_jp"] else "narration"
        else:
            kind = {"bquote": "quote", "encyc": "encyclopedia", "db": "menu", "music": "music", "exe": "menu"}[src]
        sp = u["speaker_jp"]
        row = {"uid": u["uid"], "kind": kind, "src": src, "speaker_jp": sp,
               "speaker_en": (gloss.get(sp) or {}).get("en") if sp else None, "jp": text}
        if kind in ("menu", "music"):
            row["budget_px"] = px(text)
        rows.append(row)
    batches = [rows[i:i + SIZE] for i in range(0, len(rows), SIZE)]
    plan = []
    for k, b in enumerate(batches, 1):
        name = "B%04d" % k
        json.dump({"batch": name, "prev": "B%04d" % (k - 1) if k > 1 else None,
                   "next": "B%04d" % (k + 1) if k < len(batches) else None, "rows": b},
                  open(os.path.join(OUT, "batches", name + ".json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        plan.append({"batch": name, "src": sorted(set(r["src"] for r in b)),
                     "chars": sum(len(r["jp"]) for r in b), "rows": len(b)})
    json.dump(auto, open(os.path.join(OUT, "auto.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    json.dump(plan, open(os.path.join(OUT, "plan.json"), "w"), indent=0)
    print("rows", len(rows), "auto", len(auto), "batches", len(batches),
          "chars", sum(p["chars"] for p in plan))


if __name__ == "__main__":
    main()
