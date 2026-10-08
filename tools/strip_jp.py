"""Write git-safe copies of the translation working files.

Japanese script text must never be committed (AGENTS.md). For every
work/translation/**/*.json that is not already *.en.json (and for
work/glossary/library.json) this writes a sibling
<name>.en.json where
  - fields that hold the Japanese source ("jp", "speaker_jp", "seen", "desc_jp") are dropped;
  - any other string (or dict key) with a run of JP_LIMIT or more Japanese
    characters is replaced by "[ja]". Short names and UI terms (allowed by the
    project rules) are kept.

python tools/strip_jp.py            write the .en.json copies
python tools/strip_jp.py --check    exit 1 if a tracked-to-be file still has long Japanese runs
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TR = os.path.join(ROOT, "work", "translation")
DROP = {"jp", "speaker_jp", "seen", "desc_jp"}
JP_LIMIT = 13
JP_RUN = re.compile("[　-ヿ㐀-鿿＀-￯‥…〜]{%d,}" % JP_LIMIT)


def clean(v):
    if isinstance(v, dict):
        out = {}
        for k, x in v.items():
            if k in DROP:
                continue
            k2 = "[ja]" if JP_RUN.search(k) else k
            if k2 == "[ja]":
                continue            # a dict keyed by Japanese script text: drop the entry
            out[k2] = clean(x)
        return out
    if isinstance(v, list):
        return [clean(x) for x in v]
    if isinstance(v, str) and JP_RUN.search(v):
        return JP_RUN.sub("[ja]", v)
    return v


EXTRA = [os.path.join(ROOT, "work", "glossary", "library.json")]   # has the Japanese descriptions


def sources():
    yield from (p for p in EXTRA if os.path.exists(p))
    for dp, _, fs in os.walk(TR):
        for f in fs:
            if f.endswith(".json") and not f.endswith(".en.json"):
                yield os.path.join(dp, f)


def main():
    n = 0
    for p in sources():
        d = json.load(open(p, encoding="utf-8"))
        q = p[:-5] + ".en.json"
        json.dump(clean(d), open(q, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        n += 1
    print("wrote %d .en.json files" % n)
    write_occurrences()


def write_occurrences():
    """work/script/occurrences.json: where every translated string sits on the disc
    (file, offset, terminator, font, uid) -- no text.  The inserter uses it in a
    public checkout and decodes the Japanese from the user's own disc."""
    ja = os.path.join(ROOT, "work", "script", "ja")
    rows = json.load(open(os.path.join(ja, "frozen_strings.json"), encoding="utf-8"))
    keep = ("src", "file", "off", "term", "font", "uid")
    out = [{k: r[k] for k in keep} for r in rows]
    extra = os.path.join(ja, "frozen_extra.json")
    if os.path.exists(extra):
        out += [dict({k: r[k] for k in keep}, extra=1) for r in json.load(open(extra, encoding="utf-8"))]
    json.dump(out, open(os.path.join(ROOT, "work", "script", "occurrences.json"), "w", encoding="utf-8"), indent=0)
    print("wrote work/script/occurrences.json (%d occurrences)" % len(out))


def check(paths):
    bad = []
    for p in paths:
        try:
            s = open(p, encoding="utf-8").read()
        except (UnicodeDecodeError, IsADirectoryError):
            continue
        m = JP_RUN.search(s)
        if m:
            bad.append((p, m.group(0)[:20]))
    return bad


if __name__ == "__main__":
    if "--check" in sys.argv:
        files = [l.strip() for l in sys.stdin if l.strip()]
        bad = check(files)
        for p, s in bad:
            print("JAPANESE RUN:", p, s)
        sys.exit(1 if bad else 0)
    main()
