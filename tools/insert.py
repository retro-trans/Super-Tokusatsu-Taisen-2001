"""Insert the English translation into the game files.

Every container is parsed, each string is decoded with its font, the
translation is looked up by its Japanese text (speaker + body), and the
English is wrapped, encoded (single/double glyphs, tools/efont.py) and written
back; pointer/offset tables are remapped. Strings with no translation keep
their original bytes, so partial builds work.

python tools/insert.py            -> work/build/files/*  (patched entries) + report
Used by tools/build.py.
"""
import json
import os
import re
import struct
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import cm  # noqa: E402
import dump_script as D  # noqa: E402
import efont  # noqa: E402
import fontsets as F  # noqa: E402

UNP = os.path.join(ROOT, "work", "source", "unpacked")
TR = os.path.join(ROOT, "work", "translation", "en")
EF = json.load(open(os.path.join(ROOT, "work", "font", "efont.json"), encoding="utf-8"))
GLOSS = json.load(open(os.path.join(ROOT, "work", "glossary", "names.json"), encoding="utf-8"))
DISPLAY = json.load(open(os.path.join(TR, "dialogue_layout.en.json"), encoding="utf-8")).get("speaker_display", {})

# Portrait dialogue starts at x=70; leave room before the frame at x=304.
# This also leaves space for the optional 4x font's small shadow.
WRAP = {"stage": 220, "bquote": 220, "encyc": 264}
CTRL = {"<c1>": 0xFF31, "<c2>": 0xFF32, "<c3>": 0xFF33, "</c>": 0xFF30,
        "[HERO1]": 0xFF01, "[HERO2]": 0xFF02, "[HERO3]": 0xFF03, "[HERO4]": 0xFF04,
        "[VAR5]": 0xFF05, "[VAR6]": 0xFF06}
# Save names have eight surname and five given-name codes. Reserve the
# original 12px glyph width so renamed heroes and existing Japanese saves fit.
PH_W = {"[HERO1]": 96, "[HERO2]": 60, "[HERO3]": 96, "[HERO4]": 60, "[VAR5]": 0, "[VAR6]": 75}   # VAR6 = "Inazuman F" (75 px)
TOKEN = re.compile(r"(<c[123]>|</c>|<p>|\[(?:HERO[1-4]|VAR[56])\]|\{[A-Za-z0-9]+\}|\s+|[^\s<\[{]+|[<\[{])")
STATS = Counter()
CHOICE = re.compile("^「[^」\n]*」(\n「[^」\n]*」)+$")
PROBLEMS = []
GRAPHICS_REPORT = []


# ---------------------------------------------------------------- translations
FROZEN = os.path.join(ROOT, "work", "script", "ja")
OCCURRENCES = os.path.join(ROOT, "work", "script", "occurrences.json")
# A public checkout has no Japanese: only the stripped *.en.json copies and the
# offsets-only occurrence map.  STT_PUBLIC=1 forces that mode in a full checkout.
PUBLIC = os.environ.get("STT_PUBLIC") == "1" or not os.path.exists(os.path.join(FROZEN, "frozen_strings.json"))


def tr_path(name):
    """work/translation/en/<name>: the working file, or its stripped .en.json copy."""
    p = os.path.join(TR, name)
    if PUBLIC or not os.path.exists(p):
        q = p[:-5] + ".en.json"
        if os.path.exists(q):
            return q
    return p


def read_ws(fname, off, term):
    """Words of the string at (file, offset) in the user's own unpacked disc."""
    if fname == "SLPS":
        path = os.path.join(ROOT, "work", "source", "disc", "SLPS_028.63")
    else:
        m = re.match(r"([A-Z]+)(\d{4})$", fname)
        path = os.path.join(UNP, m.group(1), m.group(2) + ".bin")
    buf = _BUFS.get(path)
    if buf is None:
        buf = _BUFS[path] = open(path, "rb").read()
    ws = []
    while True:
        w = struct.unpack_from("<H", buf, off + 2 * len(ws))[0]
        if w == term:
            return ws
        ws.append(w)


_BUFS = {}


def frozen_rows():
    """Occurrences of the frozen dump (+ strings found later): file, off, uid, src, font."""
    if not PUBLIC:
        rows = json.load(open(os.path.join(FROZEN, "frozen_strings.json"), encoding="utf-8"))
        extra = os.path.join(FROZEN, "frozen_extra.json")
        if os.path.exists(extra):   # strings found after the dump was frozen (e.g. encyclopedia, page-2 glyphs)
            rows += json.load(open(extra, encoding="utf-8"))
        return rows
    return json.load(open(OCCURRENCES, encoding="utf-8"))


def frozen_units(rows):
    """uid -> (speaker, Japanese text).  Public mode decodes them from the user's disc."""
    if not PUBLIC:
        return [(u["uid"], u["speaker_jp"], u["jp"])
                for u in json.load(open(os.path.join(FROZEN, "frozen_units.json"), encoding="utf-8"))]
    seen, out = set(), []
    for r in rows:
        if r["uid"] in seen or r.get("extra"):
            continue
        seen.add(r["uid"])
        ws = read_ws(r["file"], r["off"], int(r["term"], 16))
        sp, body = D.decode(ws, r["font"], dialogue=r["src"] in ("stage", "bquote"))
        out.append((r["uid"], sp, body))
    return out


def load_translations():
    """Translations are keyed by the frozen dump the batches were made from:
    occurrence (file, offset) -> uid -> English. Text keys (current decode of
    the frozen occurrences) are added for containers that are not in the dump
    (e.g. MAPMAIN #24, a copy of the database)."""
    rows = frozen_rows()
    units = frozen_units(rows)
    en = {}
    out = os.path.join(TR, "out")
    names = sorted(f for f in os.listdir(out) if f.endswith(".json") and not f.endswith(".en.json"))
    if PUBLIC or not names:
        names = sorted(f for f in os.listdir(out) if f.endswith(".en.json"))
    for f in names:
        for r in json.load(open(os.path.join(out, f), encoding="utf-8")).get("rows", []):
            en[r["uid"]] = r["en"]
    en.update(json.load(open(tr_path("auto.json"), encoding="utf-8")))
    op = tr_path("overrides.json")
    if os.path.exists(op):
        en.update({k: v for k, v in json.load(open(op, encoding="utf-8")).items() if not k.startswith("_")})
    rp = tr_path("replacements.json")
    if os.path.exists(rp):
        pairs = json.load(open(rp, encoding="utf-8"))["pairs"]
        for k, v in en.items():
            for a, b in pairs:
                v = re.sub(a[3:], b, v) if a.startswith("re:") else v.replace(a, b)
            en[k] = v
    man = tr_path("manual.json")
    manual = json.load(open(man, encoding="utf-8")) if os.path.exists(man) else {}
    by_text = {}
    for uid, sp, jp in units:
        if uid in en:
            by_text[(sp, jp)] = en[uid]
    by_occ = {}
    for r in rows:
        if r["uid"] in en:
            by_occ[(r["file"], r["off"])] = en[r["uid"]]
    # per-occurrence overrides ("@FILE:offset" in overrides.json), e.g. a unit
    # name shortened for the map windows but kept in full in the encyclopedia
    if os.path.exists(op):
        occ = {"%s:%s" % (r["file"], r["off"]): (r["file"], r["off"]) for r in rows if not r.get("extra")}
        for k, v in json.load(open(op, encoding="utf-8")).items():
            if k.startswith("@"):
                if k[1:] not in occ:
                    raise KeyError("override %s: no such occurrence" % k)
                by_occ[occ[k[1:]]] = v
    return by_text, manual, by_occ


# ---------------------------------------------------------------- encoding
def px_of(tok):
    if tok in PH_W:
        return PH_W[tok]
    if tok.startswith("{"):
        return 8 if tok in ("{direct}", "{ranged}") else 12
    if tok in CTRL or tok == "<p>":
        return 0
    return efont.text_width(tok, EF)


def icon_queue(orig_words, font):
    q = defaultdict(list)
    for w in orig_words:
        if w < 0xFF00:
            c = D.ch(w, font)
            if c and c.startswith("{") and len(c) > 1:
                q[c].append(w)
    return q


ENC_MAIN = EF["encode"]
ENC_ENCYC = dict(EF["encode"])
ENC_ENCYC.update(EF.get("encode_ex", {}))
# DB string with the default hero/heroine names (FF05 pieces); see encode_text
DEFAULT_NAMES = "Sakomizu[VAR5]"
NAME_LIMITS = (8, 5)        # codes per surname / given-name save buffer (+0x24e.. in the save struct)


def encode_line_tokens(tokens, icons, enc=None):
    enc = enc or ENC_MAIN
    out, buf = [], ""
    for t in tokens:
        if t in CTRL or t.startswith("{") and t.endswith("}") and len(t) > 2:
            if buf:
                out += efont.encode_plain(buf, enc)
                buf = ""
            if t in CTRL:
                out.append(CTRL[t])
            else:
                m = re.match(r"\{([0-9A-F]{4})\}$", t)
                if m:
                    out.append(int(m.group(1), 16))
                elif icons.get(t):
                    out.append(icons[t].pop(0))
                else:
                    raise ValueError("icon %s has no source code" % t)
        else:
            buf += t
    if buf:
        out += efont.encode_plain(buf, enc)
    return out


def layout(en, width, max_lines):
    """Wrap English into pages/lines (breaks only at spaces).
    Returns a list of pages, each a list of lines, each a token list."""
    pages = []
    for ptext in en.split("<p>"):
        words = []          # each word = list of tokens with no space inside
        cur = []
        for t in TOKEN.findall(ptext.strip()):
            if t.isspace():
                if cur:
                    words.append(cur)
                cur = []
            else:
                cur.append(t)
        if cur:
            words.append(cur)
        # An unusually long unbroken word must not bypass the wrap limit.
        bounded = []
        for word in words:
            if width and sum(px_of(t) for t in word) > width:
                part, used = [], 0
                for token in word:
                    pieces = [token] if token in CTRL or token.startswith("{") else list(token)
                    for piece in pieces:
                        pw = px_of(piece)
                        if pw > width:
                            raise ValueError("token exceeds dialogue width: %s" % piece)
                        if part and used + pw > width:
                            bounded.append(part)
                            part, used = [], 0
                        part.append(piece)
                        used += pw
                if part:
                    bounded.append(part)
            else:
                bounded.append(word)
        words = bounded
        lines, line, lw = [], [], 0
        space_w = px_of(" ")
        for w in words:
            ww = sum(px_of(t) for t in w)
            if line and width and lw + space_w + ww > width:
                lines.append(line)
                line, lw = list(w), ww
            else:
                if line:
                    line.append(" ")
                    lw += space_w
                line += w
                lw += ww
        if line or not lines:
            lines.append(line)
        while lines:
            # Prefer a sentence boundary over leaving a few words alone in
            # the following box. Rewrap the remainder without changing text.
            if max_lines == 3 and len(lines) > max_lines:
                boundary = None
                for li, row in enumerate(lines[:max_lines]):
                    for ti, token in enumerate(row):
                        if li > 0 and re.search(r"[.!?\u2026][\"')]*$", token) and token not in (
                                "Dr.", "Mr.", "Mrs.", "Ms.", "Prof.", "St.", "No."):
                            boundary = li, ti
                if boundary:
                    li, ti = boundary
                    pages.append(lines[:li] + [lines[li][:ti+1]])
                    rest = [lines[li][ti+1:]] + lines[li+1:]
                    remaining = " ".join("".join(row).strip() for row in rest).strip()
                    pages.extend(layout(remaining, width, max_lines))
                    lines = []
                    continue
            pages.append(lines[:max_lines])
            lines = lines[max_lines:]
    return pages


def encode_text(en, kind, orig_words, font, max_lines=4):
    icons = icon_queue(orig_words, font)
    width = WRAP.get(kind)
    enc = ENC_ENCYC if kind == "encyc" else ENC_MAIN
    if width is None:   # one-line UI text: no wrapping, keep explicit structure
        if en.startswith(DEFAULT_NAMES):
            enc = ENC_ENCYC
        return encode_line_tokens(TOKEN.findall(en.replace("<p>", "")), icons, enc)
    pages = layout(en, width, max_lines)
    out = []
    for pi, page in enumerate(pages):
        if pi:
            out.append(0xFFFC)
        for li, line in enumerate(page):
            if li:
                out.append(0xFFFB)
            out += encode_line_tokens(line, icons, enc)
    return out


def encode_name(name_en):
    return efont.encode_plain(name_en, EF["encode"])


def page_lines(jp_body):
    return max(p.count("\n") + 1 for p in jp_body.split("<p>"))


# ---------------------------------------------------------------- string translation
GRID = re.compile(r"^[ぁ-ヿA-Za-z0-9ー ]{5}( [ぁ-ヿA-Za-z0-9ー ]{1,5}){2,}")


def grid_words(en, n):
    """Name-entry grid row: fixed-width 8 px glyphs (original font), exactly n cells."""
    out = []
    for ch in en[:n]:
        if "A" <= ch <= "Z":
            out.append(177 + ord(ch) - 65)
        elif "a" <= ch <= "z":
            out.append(203 + ord(ch) - 97)
        elif "0" <= ch <= "9":
            out.append(1 + ord(ch) - 48)
        elif ch == "-":
            out.append(232)
        elif ch == ".":
            out.append(236)
        else:
            out.append(0)
    return out + [0] * (n - len(out))


class Translator:
    def __init__(self):
        self.by_text, self.manual, self.by_occ = load_translations()
        self.by_codes = {}

    def words_for(self, src, ws, font, occ=None):
        """Original words (no terminator) -> new words, or None to keep original.
        occ = (file, offset) of the string in the frozen dump, when known."""
        dialogue = src in ("stage", "bquote")
        sp, body = D.decode(ws, font, dialogue=dialogue)
        key = (sp, body)
        en = self.by_occ.get(occ) if occ else None
        if en is not None:
            self.by_codes[(src, tuple(ws))] = en
        if en is None:
            en = self.by_codes.get((src, tuple(ws)))
        if en is None:
            en = self.by_text.get(key)
        if en is None:
            en = self.manual.get(body) if not sp else None
        if en is None:
            if any(16 <= w < 1454 for w in ws):
                STATS["untranslated_" + src] += 1
            return None
        try:
            lines = 3 if src == "stage" else (2 if src == "bquote" else 99)
            new = []
            if sp is not None:
                g = GLOSS.get(sp)
                name = g["en"] if g else None
                if name is None and sp.startswith("["):
                    new_sp = [CTRL[t] for t in re.findall(r"\[(?:HERO[1-4]|VAR[56])\]", sp)]
                    for i in range(len(new_sp) - 1, 0, -1):
                        new_sp.insert(i, 0)
                elif name is None:
                    k = ws.index(0xFF30)
                    new_sp = list(ws[1:k])
                    PROBLEMS.append("speaker not in glossary: %s" % sp)
                else:
                    new_sp = encode_name(DISPLAY.get(name, name))
                new = [0xFF33] + new_sp + [0xFF30, 0xFFFB]
            if src == "db" and GRID.match(body) and len(ws) >= 20:
                new = grid_words(en, len(ws))
                STATS["translated_db"] += 1
                return new
            if CHOICE.match(body.strip()):
                opts = re.findall(r'"([^"]*)"', en)
                n_opt = body.strip().count(chr(10)) + 1
                if len(opts) != n_opt:
                    raise ValueError("choice row needs %d quoted options" % n_opt)
                icons = icon_queue(ws, font)
                for k, o in enumerate(opts):
                    if k:
                        new.append(0xFFFB)
                    line = '"%s"' % o.strip()
                    if efont.text_width(line, EF) > WRAP.get(src, 236):
                        PROBLEMS.append("choice option too wide: %s" % line)
                    new += encode_line_tokens(TOKEN.findall(line), icons)
            else:
                new += encode_text(en, src if src in WRAP else "ui", ws, font, lines)
            if sp is None and dialogue and new and new[0] == 0xFF33:
                new = [0xFF30] + new    # a leading FF33 would be read as a speaker tag
            STATS["translated_" + src] += 1
            return new
        except ValueError as e:
            PROBLEMS.append("%s: %s | %s" % (src, e, en[:60]))
            STATS["encode_error"] += 1
            return None


# ---------------------------------------------------------------- containers
def pack_words(ws):
    return struct.pack("<%dH" % len(ws), *ws)


def rebuild_overlay(buf, base, src, font_of, tr, fname=None):
    """Overlay = u32 pointers (0x800Exxxx) + strings. font_of(old_off, ws) -> font."""
    nptr = 0
    while struct.unpack_from("<I", buf, base + nptr * 4)[0] >> 16 == 0x800E:
        nptr += 1
    ptrs = struct.unpack_from("<%dI" % nptr, buf, base)
    strings = D.overlay_strings(buf, base)
    body = bytearray()
    remap = {}
    first = base + nptr * 4
    for off, ws, term in strings:
        new = tr.words_for(src, list(ws), font_of(off, ws), (fname, off) if fname else None)
        if new is None:
            new = list(ws)
        remap[off] = first + len(body) - base
        body += pack_words(new + [term])
    # pointers into terminators / unknown targets
    out_ptr = []
    for p in ptrs:
        o = p - 0x800E0000 + base
        if o not in remap:
            raise ValueError("pointer to 0x%X is not a string start" % o)
        out_ptr.append(0x800E0000 + remap[o])
    data = bytes(buf[:base]) + struct.pack("<%dI" % nptr, *out_ptr) + bytes(body)
    return data + bytes((-len(data)) % 4)


def rebuild_table16(buf, src, tr, font="11", suffix_tr=None, fname=None):
    """u16 offset table + FFFE strings (database)."""
    first = struct.unpack_from("<H", buf, 0)[0]
    table = list(struct.unpack_from("<%dH" % (first // 2), buf, 0))
    spans = []
    pos = first
    while pos + 2 <= len(buf):
        q = pos
        while q + 2 <= len(buf) and struct.unpack_from("<H", buf, q)[0] not in (0xFFFE, 0xFFFD):
            q += 2
        if q + 2 > len(buf):
            break
        spans.append((pos, q))
        pos = q + 2
        if all(b == 0 for b in buf[pos:pos + 16]):
            break
    end_orig = pos
    body = bytearray()
    start_map, term_map, piece_map = {}, {}, {}
    new_words = {}
    for a, b in spans:
        ws = list(struct.unpack_from("<%dH" % ((b - a) // 2), buf, a))
        new = tr.words_for(src, ws, font, (fname, a) if fname else None)
        if new is None:
            new = ws
        new_words[a] = (ws, new)
        start_map[a] = first + len(body)
        # positions after each FF05 separator (default name list)
        k = 0
        for i, w in enumerate(new):
            if w == 0xFF05:
                piece_map[(a, k)] = first + len(body) + 2 * (i + 1)
                k += 1
        body += pack_words(new)
        term_map[b] = first + len(body)
        body += pack_words([struct.unpack_from("<H", buf, b)[0]])
    extra = bytearray()
    new_table = []
    for t in table:
        if t in start_map:
            new_table.append(start_map[t])
            continue
        if t in term_map:
            new_table.append(term_map[t])
            continue
        a = max(x for x, _ in spans if x < t)
        ws, new = new_words[a]
        idx = (t - a) // 2
        seps = [i for i, w in enumerate(ws) if w == 0xFF05]
        if idx - 1 in seps:
            new_table.append(piece_map.get((a, seps.index(idx - 1)), start_map[a]))
            continue
        # shared suffix: write a separate string for it
        suf = ws[idx:]
        sp, body_jp = D.decode(suf, font, dialogue=False)
        en = (suffix_tr or {}).get(body_jp) or tr.by_text.get((None, body_jp)) or tr.manual.get(body_jp)
        if en is None:
            PROBLEMS.append("db suffix without translation: %s" % body_jp)
            sw = suf
        else:
            sw = encode_line_tokens(TOKEN.findall(en), icon_queue(suf, font))
        new_table.append(first + len(body) + len(extra))
        extra += pack_words(sw + [0xFFFE])
    data = struct.pack("<%dH" % len(new_table), *new_table) + bytes(body) + bytes(extra)
    if max(new_table) > 0xFFFF:
        raise ValueError("database larger than 64 KB")
    data += bytes(buf[end_orig:end_orig]) if False else b""
    return data + bytes((-len(data)) % 4)


def rebuild_sequential(buf, first, src, tr, font="11", fname=None):
    """Header kept as-is, then FFFE strings in order (music titles)."""
    out = bytearray(buf[:first])
    pos = first
    while pos + 2 <= len(buf):
        q = pos
        while q + 2 <= len(buf) and struct.unpack_from("<H", buf, q)[0] not in (0xFFFE, 0xFFFD):
            q += 2
        if q + 2 > len(buf):
            break
        ws = list(struct.unpack_from("<%dH" % ((q - pos) // 2), buf, pos))
        head = []
        if ws and not D.is_text(ws):    # header data, then the first title, in one run
            k = max(i for i, w in enumerate(ws) if not D.is_text([w]))
            head, ws = ws[:k + 1], ws[k + 1:]
        at = pos + 2 * len(head)
        new = tr.words_for(src, ws, font, (fname, at) if fname else None) if ws and D.is_text(ws) else None
        out += pack_words(head + (new if new is not None else ws) + [struct.unpack_from("<H", buf, q)[0]])
        pos = q + 2
        if all(b == 0 for b in buf[pos:pos + 16]):
            break
    return bytes(out) + bytes((-len(out)) % 4)


def is_text_battle(ws):
    """Battle font has three pages: codes up to 1789 (page 2, F0) are glyphs."""
    return all(w < 1790 or w >= 0xFF00 for w in ws)


def rebuild_encyc(buf, tr):
    """Encyclopedia (BATTLE #540): u32 pointer table + strings (FFFE ends an entry,
    FFFD ends a piece that runs on into the next one).  Self-contained strings
    (reached only through the table, ending in FFFE) are shared when identical
    or when one is the tail of another: the English must fit below 0x801A7000."""
    n = struct.unpack_from("<I", buf, 0)[0] // 4
    table = struct.unpack_from("<%dI" % n, buf, 0)
    tset = set(table)
    pieces = []                 # (pos, term_pos, words incl. terminator, run_in)
    pos = table[0]
    prev_term = 0xFFFE
    while pos + 2 < len(buf):
        q = pos
        while q + 2 <= len(buf) and struct.unpack_from("<H", buf, q)[0] not in (0xFFFE, 0xFFFD):
            q += 2
        if q + 2 > len(buf):
            break
        ws = list(struct.unpack_from("<%dH" % ((q - pos) // 2), buf, pos))
        new = tr.words_for("encyc", ws, "battle", ("BATTLE0540", pos)) if ws and is_text_battle(ws) else None
        term = struct.unpack_from("<H", buf, q)[0]
        pieces.append((pos, q, (new if new is not None else ws) + [term], prev_term == 0xFFFD))
        prev_term = term
        pos = q + 2
    # chains: pieces joined by FFFD stay together and in order
    chains, cur = [], []
    for pc in pieces:
        if cur and not pc[3]:
            chains.append(cur)
            cur = []
        cur.append(pc)
    if cur:
        chains.append(cur)
    # (the first entry must stay right after the table: its offset gives the entry count)
    alone = [c[0] for c in chains if len(c) == 1 and c[0][2][-1] == 0xFFFE and c[0][0] != table[0]]
    alone_ids = {pc[0] for pc in alone}
    body = []                   # words
    smap, tmap = {}, {}
    for c in chains:            # chains and FFFD pieces first, in their original order
        if len(c) == 1 and c[0][0] in alone_ids:
            continue
        for pos, q, words, _ in c:
            smap[pos] = len(body)
            body += words
            tmap[q] = len(body) - 1
    # self-contained strings, longest first: reuse an identical string or a tail
    placed = []                 # (start index in body, words)
    for pos, q, words, _ in sorted(alone, key=lambda pc: -len(pc[2])):
        at = None
        for st, w in placed:
            if len(w) >= len(words) and w[len(w) - len(words):] == words:
                at = st + len(w) - len(words)
                break
        if at is None:
            at = len(body)
            body += words
            placed.append((at, words))
        else:
            STATS["encyc_shared"] += 1
        smap[pos] = at
        tmap[q] = at + len(words) - 1
    out_t = []
    for t in table:
        if t in smap:
            out_t.append(n * 4 + 2 * smap[t])
        elif t in tmap:
            out_t.append(n * 4 + 2 * tmap[t])
        else:
            raise ValueError("encyclopedia offset 0x%X not at a string" % t)
    data = struct.pack("<%dI" % n, *out_t) + pack_words(body)
    return data + bytes((-len(data)) % 4)


def cm_blocks_raw(buf):
    pos, out = 0, []
    while pos + 10 <= len(buf) and buf[pos:pos + 2] == b"CM":
        data, nxt = cm.decompress(buf, pos)
        out.append((data, buf[pos:nxt]))
        pos = nxt
    return out


def rebuild_cm(buf, replace):
    """replace: {block_index: new_data}. Unchanged blocks keep their bytes."""
    out = bytearray()
    for i, (data, raw) in enumerate(cm_blocks_raw(buf)):
        out += cm.compress(replace[i]) if i in replace else raw
    return bytes(out)


# ---------------------------------------------------------------- font sheets
def tim_pixels(tim):
    import numpy as np
    blen = struct.unpack_from("<I", tim, 8)[0]
    pos = 8 + blen
    _, _, _, iw, ih = struct.unpack_from("<IHHHH", tim, pos)
    raw = np.frombuffer(tim[pos + 12:pos + 12 + iw * 2 * ih], dtype=np.uint8).reshape(ih, iw * 2)
    pix = np.empty((ih, iw * 4), dtype=np.uint8)
    pix[:, 0::2] = raw & 15
    pix[:, 1::2] = raw >> 4
    return pix, pos + 12


def write_font(tim, extra=False, main=True, ex_x=256, native_values=True):
    """English glyphs into a font sheet.  main: single + two-letter glyphs (page 0);
    extra: the 24 px word glyphs (F0 layer of the right page, ex_x = where that
    page starts in this TIM: 256 for full sheets, 0 for the per-scene right pages)."""
    import numpy as np
    z = np.load(os.path.join(ROOT, "work", "font", "efont_cells.npz"))
    tim = bytearray(tim)
    pix, base = tim_pixels(tim)
    if main and native_values:
        import ui_value_font
        ui_value_font.apply_pixels(pix)
        import weapon_markers
        weapon_markers.apply_main(pix)
    for i in range(efont.UNI_COUNT if main else 0):
        a = efont.UNI_FIRST + i - 110
        x, y = (a % 21) * 12, (a // 21) * 16
        cell = z["uni"][i] if i < len(z["uni"]) else np.zeros((16, 12), np.uint8)
        pix[y:y + 16, x:x + 12] = (pix[y:y + 16, x:x + 12] & 0xC) | cell
    for i in range(efont.BI_COUNT if main else 0):
        r = i
        x, y = (r % 21) * 12, (r // 21) * 16
        cell = z["bi"][i] if i < len(z["bi"]) else np.zeros((16, 12), np.uint8)
        pix[y:y + 16, x:x + 12] = (pix[y:y + 16, x:x + 12] & 0x3) | (cell << 2)
    if extra:   # word glyphs: right page, F0 layer, 24 px wide (two cells)
        for i, code in enumerate(efont.EX_SLOTS):
            r = code - 110 - 336
            x, y = ex_x + (r % 21) * 12, (r // 21) * 16
            cell = z["ex"][i] if i < len(z["ex"]) else np.zeros((16, efont.EX_W), np.uint8)
            pix[y:y + 16, x:x + efont.EX_W] = (pix[y:y + 16, x:x + efont.EX_W] & 0xC) | cell
        import ui_glyphs
        ui_glyphs.apply_pixels(pix, ex_x)
        import weapon_markers
        weapon_markers.apply_ex(pix, ex_x)
    packed = (pix[:, 0::2] | (pix[:, 1::2] << 4)).astype(np.uint8).tobytes()
    tim[base:base + len(packed)] = packed
    return bytes(tim)


# ---------------------------------------------------------------- main
def build_all():
    tr = Translator()
    files = {}
    import repack
    # ---- STAGE.DAT
    stage = repack.dat_entries(open(os.path.join(ROOT, "work", "source", "disc", "STAGE.DAT"), "rb").read())
    rows = frozen_rows()
    font_at = {(r["file"], r["off"]): r["font"] for r in rows}
    keys = sorted(D.STAGE_VAR)
    for i, k in enumerate(keys):
        idx = int(k)
        name = "STAGE%s" % k
        import stage_cards
        stage[idx+1], count = stage_cards.patch_script(stage[idx+1])
        STATS["stage_card_routines"] += count
        new = rebuild_overlay(stage[idx], 0, "stage", lambda off, ws, n=name: font_at.get((n, off), "11"), tr, name)
        STATS["max_overlay"] = max(STATS["max_overlay"], len(new))
        if len(new) > 0x12C00:
            PROBLEMS.append("%s overlay is %d bytes (limit 0x12C00)" % (name, len(new)))
        stage[idx] = new
        stage[630 + i] = rebuild_cm(stage[630 + i], {4: new, 5: stage[idx+1][:len(cm.blocks(stage[630+i])[5])]})
    files["STAGE.DAT"] = repack.dat_pack(stage)
    # ---- BATTLE.DAT
    battle = repack.dat_entries(open(os.path.join(ROOT, "work", "source", "disc", "BATTLE.DAT"), "rb").read())
    for i, e in enumerate(battle):
        if len(e) > 0x8438 and e[:4] == b"\x10\0\0\0" and struct.unpack_from("<I", e, 0x8434)[0] >> 16 == 0x800E:
            battle[i] = rebuild_overlay(e, 0x8434, "bquote", lambda off, ws: "11", tr, "BATTLE%04d" % i)
    battle[540] = rebuild_encyc(battle[540], tr)
    STATS["encyc_bytes"] = len(battle[540])
    if len(battle[540]) > 0x1F000:
        PROBLEMS.append("encyclopedia is %d bytes (limit 0x1F000)" % len(battle[540]))
    # This encyclopedia sheet has 16px tab cells instead of native UI digits.
    battle[537] = write_font(battle[537], native_values=False)
    battle[538] = write_font(battle[538], extra=True)
    files["BATTLE.DAT"] = repack.dat_pack(battle)
    # ---- MAPMAIN.DAT
    mm = repack.dat_entries(open(os.path.join(ROOT, "work", "source", "disc", "MAPMAIN.DAT"), "rb").read())
    import ui_glyphs
    import intermission_layout
    db2 = intermission_layout.patch_database(ui_glyphs.patch_database(rebuild_table16(mm[2], "db", tr, fname="MAPMAIN0002")))
    mm[2] = db2
    blocks24 = cm_blocks_raw(mm[24])
    db24 = intermission_layout.patch_database(ui_glyphs.patch_database(rebuild_table16(blocks24[1][0], "db", tr)))
    if len(db24) > 0xD000:
        PROBLEMS.append("database is %d bytes (limit 0xD000 at 0x800F3000)" % len(db24))
    STATS["db_bytes"] = len(db24)
    mm[24] = rebuild_cm(mm[24], {1: db24})
    mm[27] = rebuild_sequential(mm[27], struct.unpack_from("<I", mm[27], 0)[0], "music", tr, fname="MAPMAIN0027")
    mm[7] = write_font(mm[7], extra=True)
    b25 = cm_blocks_raw(mm[25])
    mm[25] = rebuild_cm(mm[25], {3: write_font(b25[3][0], extra=True)})
    files["MAPMAIN.DAT"] = repack.dat_pack(mm)
    # ---- EVENT.DAT
    ev = repack.dat_entries(open(os.path.join(ROOT, "work", "source", "disc", "EVENT.DAT"), "rb").read())
    ev[10] = write_font(ev[10], extra=True)
    for i in range(11, 24):     # per-scene right pages (kanji no longer used by the English text)
        ev[i] = write_font(ev[i], extra=True, main=False, ex_x=0)
    files["EVENT.DAT"] = repack.dat_pack(ev)
    import gfx_translate
    GRAPHICS_REPORT[:] = gfx_translate.patch_files(files)
    STATS["translated_graphics"] = len(GRAPHICS_REPORT)
    return files, tr


def patch_exe_strings(exe, tr):
    """Exe menu strings are rewritten in place (they cannot move or grow).
    work/translation/en/exe_strings.json gives the English per offset."""
    exe = bytearray(exe)
    ov = json.load(open(tr_path("exe_strings.json"), encoding="utf-8"))
    for off, ws, term in D.table16_strings(bytes(exe), 0x9A900):
        if off > 0x9AF70:
            break
        if not ws or not D.is_text(ws) or not any(16 <= w < 1454 for w in ws):
            continue
        key = "%05X" % off
        if key in ov:
            v = ov[key]
            if v is None:
                continue
            keep, text = (v[0], v[1]) if isinstance(v, list) else (0, v)
            new = list(ws[:keep]) + encode_line_tokens(TOKEN.findall(text), {})
        else:
            new = tr.words_for("exe", list(ws), "11", ("SLPS", off))
            if new is None:
                continue
        if len(new) > len(ws):
            PROBLEMS.append("exe string at 0x%X too long (%d > %d codes)" % (off, len(new), len(ws)))
            continue
        STATS["exe_written"] += 1
        new = new + [0xFF30] * (len(ws) - len(new))
        struct.pack_into("<%dH" % len(new), exe, off, *new)
    return bytes(exe)


SAVE_HDR = 0x9A650          # memory-card header template ("SC", icon flag, blocks, title)


def patch_save_title(exe):
    """Memory-card save title (Shift-JIS, shown by the BIOS card manager).
    0x80042e14 writes the slot digit at title+0x1D and the episode number at
    +0x22..+0x25.  New layout "ＳＴＴ２００１　Ｆｉｌｅ　1　ＥＰ01": the slot digit
    moves to +0x1B (sb offset 0x21 -> 0x1F) and episodes 1-9 get a leading
    '０' instead of a space."""
    exe = bytearray(exe)
    title = "ＳＴＴ２００１　Ｆｉｌｅ　１　ＥＰ０１".encode("cp932")
    assert len(title) == 38
    exe[SAVE_HDR + 4:SAVE_HDR + 4 + 64] = title + bytes(64 - len(title))
    assert exe[0x3362C:0x33630] == bytes.fromhex("2100c4a0")     # sb $a0, 0x21($a2)
    exe[0x3362C] = 0x1F
    assert exe[0x33630:0x33634] == bytes.fromhex("81400224")     # addiu $v0, $zero, 0x4081 ('　')
    exe[0x33630:0x33632] = (0x4F82).to_bytes(2, "little")       # '０'
    return bytes(exe)


HERO_SELECT_X = [(0xA3C36, 0x40, 0x38), (0xA3C46, 0xA8, 0xB8),     # Lucifard route: hero, heroine
                 (0xA3C66, 0x40, 0x38), (0xA3C76, 0xA8, 0xB8)]     # EATER route
SEP_CODE = 0x8005F50C - 0x80010000 + 0x800


def patch_hero_select(exe):
    """Hero-select screen (layout table at 0x800B3434: type, x, y, ?, pointer).
    The composed names "surname + code 0 + given name" are wider in English:
    the hero column moves left 8 px, the heroine column right 16 px, and the
    separator becomes the 4 px English space (code 320) instead of the 8 px
    code 0.  0x8005F50C: ori v0,zero,0xffff / sh zero,0x10(sp) / .. / sh v0,0x12(sp)
    -> lui v0,0xffff / ori v0,v0,320 / .. / sw v0,0x10(sp)."""
    exe = bytearray(exe)
    for off, old, new in HERO_SELECT_X:
        assert struct.unpack_from("<H", exe, off)[0] == old, hex(off)
        struct.pack_into("<H", exe, off, new)
    o = SEP_CODE
    assert struct.unpack_from("<4I", exe, o) == (0x3402FFFF, 0xA7A00010, struct.unpack_from("<I", exe, o + 8)[0], 0xA7A20012)
    struct.pack_into("<I", exe, o, 0x3C02FFFF)
    struct.pack_into("<I", exe, o + 4, 0x34420000 | efont_space())
    struct.pack_into("<I", exe, o + 12, 0xAFA20010)
    return bytes(exe)


def efont_space():
    return EF["encode"][" "]


def check_default_names(files):
    """Each default name (DB #2 strings 0xB36-0xB3D) is copied into a fixed save
    buffer: surnames 8 codes, given names 5 (NAME_LIMITS); a longer name runs
    into the next buffer.  Reads the built database."""
    import repack
    db = repack.dat_entries(files["MAPMAIN.DAT"])[2]
    table = struct.unpack_from("<3503H", db, 0)
    for k, idx in enumerate(range(0xB36, 0xB3E)):
        o, n = table[idx], 0
        while struct.unpack_from("<H", db, o + 2 * n)[0] < 0x5AE:
            n += 1
        lim = NAME_LIMITS[k % 2]
        if n > lim:
            PROBLEMS.append("default name #%X is %d codes (save buffer holds %d)" % (idx, n, lim))
        STATS["name_codes_max"] = max(STATS["name_codes_max"], n)


VAR6_SLOTS = [   # FF06 in dialogue: the text drawers (0x8004AB08, 0x8004BBB0) pick one by a story flag
    (0x800AA108, 6, "Inazuman"),      # original イナズマン + FF05
    (0x800AA114, 7, "Inazuman F"),    # original イナズマンF + FF05
]


def patch_var6(exe):
    """The FF06 variable is drawn from two fixed exe strings (terminated by FF05).
    They hold 5 and 6 codes; the English names fit with the "Ina"/"ma" word glyphs,
    which every font sheet carries since 0.3.3."""
    exe = bytearray(exe)
    for addr, slot, name in VAR6_SLOTS:
        off = addr - 0x80010000 + 0x800
        old = struct.unpack_from("<%dH" % slot, exe, off)
        assert old[-1] == 0xFF05 and all(w < 0xFF00 for w in old[:-1]), (hex(addr), old)
        codes = efont.encode_plain(name, ENC_ENCYC)
        if len(codes) > slot - 1:
            PROBLEMS.append("VAR6 name %r is %d codes (slot holds %d)" % (name, len(codes), slot - 1))
            continue
        new = codes + [0xFF05] + [0xFF05] * (slot - 1 - len(codes))
        struct.pack_into("<%dH" % slot, exe, off, *new)
        STATS["var6_written"] += 1
    return bytes(exe)


if __name__ == "__main__":
    files, tr = build_all()
    print(dict(STATS))
    for p in PROBLEMS[:40]:
        print("PROBLEM", p)
    print("problems:", len(PROBLEMS))
    for k, v in files.items():
        print(k, len(v))
