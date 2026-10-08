"""Build the library glossary from the translated encyclopedia (BATTLE #540).

python tools/build_library.py
 -> work/glossary/library.json  (entries: jp, en, desc_jp, desc_en)
 -> work/glossary/names.json    (adds missing names as aliases, fills empty notes)
 -> docs/library_glossary.md    (readable table: Japanese name, English, summary)
"""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TR = os.path.join(ROOT, "work", "translation", "en")


def first_sentence(s):
    s = s.strip()
    m = re.match(r"(.+?[.!?])(\s|$)", s)
    return (m.group(1) if m else s)[:160]


def main():
    rows = sorted([r for r in json.load(open(os.path.join(ROOT, "work/script/ja/frozen_strings.json"), encoding="utf-8"))
                   if r["src"] == "encyc"], key=lambda r: r["off"])
    en = {}
    for f in os.listdir(os.path.join(TR, "out")):
        for r in json.load(open(os.path.join(TR, "out", f), encoding="utf-8"))["rows"]:
            en[r["uid"]] = r["en"]
    en.update(json.load(open(os.path.join(TR, "auto.json"), encoding="utf-8")))
    entries = []
    for r in rows:
        jp, e = r["jp"], en.get(r["uid"], "")
        is_desc = jp.startswith(" ") or (entries and ("。" in jp[-3:] or len(jp) > 30))
        if not is_desc or not entries:
            entries.append({"jp": jp.strip(), "en": e.strip(), "desc_jp": "", "desc_en": ""})
        else:
            entries[-1]["desc_jp"] += jp.replace("\n", "")
            entries[-1]["desc_en"] += (" " if entries[-1]["desc_en"] else "") + e
    json.dump(entries, open(os.path.join(ROOT, "work/glossary/library.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    p = os.path.join(ROOT, "work/glossary/names.json")
    g = json.load(open(p, encoding="utf-8"))
    for x in entries:
        k, e = x["jp"], x["en"]
        if not k or not e or k.startswith("－") or k in ("オリジナル", "現用兵器"):
            continue
        note = first_sentence(x["desc_en"]) if x["desc_en"] else ""
        if k not in g:
            g[k] = {"en": e, "kind": "library", "note": ("library: " + note) if note else "library entry"}
        elif note and not g[k].get("note"):
            g[k]["note"] = "library: " + note
    json.dump(g, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
    lines = ["# Library (Character Encyclopedia) glossary", "",
             "Built by tools/build_library.py from the translated in-game encyclopedia (BATTLE.DAT #540, title menu "
             "\"キャラクター辞典\"). A few Japanese names are battle-font misreads; the English is the checked spelling.", "",
             "| Japanese | English | Summary |", "|---|---|---|"]
    for x in entries:
        if x["en"] and not x["jp"].startswith("－"):
            lines.append("| %s | %s | %s |" % (x["jp"].replace("|", "/"), x["en"].replace("|", "/"),
                                              first_sentence(x["desc_en"]).replace("|", "/")))
    open(os.path.join(ROOT, "docs/library_glossary.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(len(entries), "entries")


if __name__ == "__main__":
    main()
