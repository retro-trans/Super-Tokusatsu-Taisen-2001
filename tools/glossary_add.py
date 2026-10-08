"""Add glossary entries. stdin lines: jp | en | kind | note  (kind/note optional)
Writes work/glossary/names.json {jp: {en, kind, note}}. Existing entries are
overwritten only with --force."""
import json, os, sys, io
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "work", "glossary", "names.json")
g = json.load(open(P, encoding="utf-8")) if os.path.exists(P) else {}
force = "--force" in sys.argv
n = 0
for line in io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8"):
    line = line.rstrip("\n")
    if not line.strip() or line.startswith("#"):
        continue
    parts = [p.strip() for p in line.split("|")]
    jp, en = parts[0], parts[1]
    kind = parts[2] if len(parts) > 2 else ""
    note = parts[3] if len(parts) > 3 else ""
    if jp in g and not force:
        continue
    g[jp] = {"en": en, "kind": kind, "note": note}
    n += 1
json.dump(g, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print("added", n, "total", len(g))
