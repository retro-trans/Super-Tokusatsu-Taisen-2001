"""English font v2: single glyphs + two-letter glyphs, widths by code order.

Layout (shared by every font sheet's texture page 0):
  codes 320-445  (F0 layer, rows 10-15)  single characters, sorted by width
  codes 782-1117 (F1 layer, all rows)    two-character glyphs ("e ", "th", ...),
                                          sorted by width
Because each range is sorted by width, the VWF routine finds a glyph's width
from 12 thresholds per range (tools/vwf_patch.py) instead of a table.

python tools/efont.py build [corpus.txt]  -> work/font/efont.json + efont_cells.npz
python tools/efont.py preview "text"      -> work/font/efont_preview.png
"""
import json
import os
import re
import sys
from collections import Counter

import numpy as np
from PIL import Image, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import vwf_font as V  # noqa: E402

OUT = os.path.join(ROOT, "work", "font")
UNI_FIRST, UNI_COUNT = 320, 126
BI_FIRST, BI_COUNT = 782, 336
EX_FIRST, EX_COUNT = 446, 336    # extra glyphs, battle font (BATTLE #538) only: encyclopedia
# extra glyphs are up to 24 px wide: each uses two neighbouring cells (even column + next)
EX_SLOTS = [EX_FIRST + row * 21 + col for row in range(16) for col in range(0, 20, 2)]
EX_W = 24
CELL_W = 12


def font():
    fname, idx = V.FACES[V.DEFAULT_FACE]
    return ImageFont.truetype(os.path.join(V.FONT_DIR, fname), V.DEFAULT_SIZE, index=idx)


def unigrams(f):
    out = {}
    for ch in V.CHARSET:
        c, w = V.render_char(f, ch)
        out[ch] = (c, int(w))
    return out


def ink_right(cell):
    cols = np.nonzero(cell.max(0))[0]
    return int(cols[-1]) + 1 if len(cols) else 0


def compose(u, a, b):
    ca, wa = u[a]
    cb, wb = u[b]
    if wa + ink_right(cb) > CELL_W or wa + wb > CELL_W:
        return None
    cell = ca.copy()
    part = np.zeros_like(cell)
    part[:, wa:] = cb[:, :CELL_W - wa]
    lit_b = part >= 2
    cell = np.where(lit_b, part, np.where(cell >= 2, cell, np.maximum(cell, part)))
    return cell.astype(np.uint8), int(wa + wb)


def compose_n(u, s):
    """Compose 2 or 3 characters into one cell (None if wider than a cell)."""
    if len(s) == 2:
        return compose(u, s[0], s[1])
    first = compose(u, s[0], s[1])
    if first is None:
        return None
    cell, w = first
    cc, wc = u[s[2]]
    if w + ink_right(cc) > CELL_W or w + wc > CELL_W:
        return None
    part = np.zeros_like(cell)
    part[:, w:] = cc[:, :CELL_W - w]
    lit = part >= 2
    cell = np.where(lit, part, np.where(cell >= 2, cell, np.maximum(cell, part)))
    return cell.astype(np.uint8), int(w + wc)


def compose_wide(u, s, limit=EX_W):
    """Compose a string into a 16 x limit canvas; None if too wide."""
    x = 0
    canvas = np.zeros((16, limit + 12), np.uint8)
    for i, ch in enumerate(s):
        cc, wc = u[ch]
        if i == len(s) - 1 and x + ink_right(cc) > limit:
            return None
        part = np.zeros_like(canvas)
        part[:, x:x + 12] = cc
        lit = part >= 2
        canvas = np.where(lit, part, np.where(canvas >= 2, canvas, np.maximum(canvas, part)))
        x += wc
        if x > limit:
            return None
    return canvas[:, :limit].astype(np.uint8), int(x)


def corpus_text(paths, only_kind=None):
    tag = re.compile(r"<c[123]>|</c>|<p>|\[(?:HERO[1-4]|VAR[56])\]|\{[A-Za-z0-9]+\}")
    kinds = None
    if only_kind:
        kinds = {}
        bdir = os.path.join(ROOT, "work", "translation", "en", "batches")
        for p in paths:
            b = os.path.join(bdir, os.path.basename(p))
            if os.path.exists(b):
                for r in json.load(open(b, encoding="utf-8"))["rows"]:
                    kinds[r["uid"]] = r["kind"]
    out = []
    for p in paths:
        d = json.load(open(p, encoding="utf-8"))
        for r in d.get("rows", []):
            if kinds is not None and kinds.get(r.get("uid")) != only_kind:
                continue
            out.extend(tag.split(r.get("en", "")))
    return out


def build(corpus_paths=None):
    f = font()
    u = unigrams(f)
    if corpus_paths is None:
        d = os.path.join(ROOT, "work", "translation", "en", "out")
        corpus_paths = [os.path.join(d, x) for x in sorted(os.listdir(d)) if x.endswith(".json")]
    segs = corpus_text(corpus_paths)
    cnt = Counter()
    for s in segs:
        for i in range(len(s) - 1):
            cnt[s[i:i + 2]] += 1
    bigrams = []
    for bg, n in cnt.most_common():
        if len(bigrams) >= BI_COUNT:
            break
        if bg[0] in u and bg[1] in u and compose(u, bg[0], bg[1]):
            bigrams.append(bg)
    # extra glyphs for the encyclopedia (battle font): word pieces up to 24 px
    enc_segs = corpus_text(corpus_paths, only_kind="encyclopedia")
    base_enc = {}
    for i, ch in enumerate(V.CHARSET):
        base_enc[ch] = 1
    for b in bigrams:
        base_enc[b] = 1
    cand = Counter()
    for s_ in enc_segs:
        for n_ in range(2, 10):
            for i in range(len(s_) - n_ + 1):
                cand[s_[i:i + n_]] += 1
    cands = []
    for g, n in cand.items():
        if n < 5 or not all(c in u for c in g) or compose_wide(u, g) is None:
            continue
        if len(encode_plain(g, base_enc)) <= 1:
            continue
        cands.append((g, n))
    # greedy: each pick maximises occurrences x codes saved under the current set
    extra, enc_now = [], dict(base_enc)
    for _ in range(len(EX_SLOTS)):
        best = None
        for g, n in cands:
            if g in enc_now:
                continue
            sc = n * (len(encode_plain(g, enc_now)) - 1)
            if best is None or sc > best[0]:
                best = (sc, g)
        if best is None or best[0] <= 0:
            break
        enc_now[best[1]] = 1
        extra.append(best[1])
    uni = sorted(V.CHARSET, key=lambda c: (u[c][1], V.CHARSET.index(c)))
    bi = sorted(bigrams, key=lambda s: (compose(u, s[0], s[1])[1], s))
    encode, cells_u, cells_b, w_u, w_b = {}, [], [], [], []
    for i, ch in enumerate(uni):
        encode[ch] = UNI_FIRST + i
        cells_u.append(u[ch][0])
        w_u.append(u[ch][1])
    for i, s in enumerate(bi):
        c, w = compose(u, s[0], s[1])
        encode[s] = BI_FIRST + i
        cells_b.append(c)
        w_b.append(w)

    ex = sorted(extra, key=lambda g: (compose_wide(u, g)[1], g))
    encode_ex, cells_x, w_x = {}, [], []
    for i, g in enumerate(ex):
        c, w = compose_wide(u, g)
        encode_ex[g] = EX_SLOTS[i]
        cells_x.append(c)
        w_x.append(w)

    def ex_thresholds(widths):
        t = []
        for k in range(1, EX_W + 1):
            pos = next((i for i, w in enumerate(widths) if w >= k), len(widths))
            t.append(EX_SLOTS[pos] if pos < len(widths) else 0xFFFF)
        return t

    def thresholds(first, widths, count):
        # width(code) = number of thresholds <= code  (12 thresholds, widths 1..12)
        t = []
        for k in range(1, 13):
            pos = next((i for i, w in enumerate(widths) if w >= k), len(widths))
            t.append(first + pos if pos < len(widths) else first + count + 1000)
        return t
    meta = {"encode": encode, "encode_ex": encode_ex, "uni_first": UNI_FIRST, "bi_first": BI_FIRST,
            "ex_first": EX_FIRST, "uni": uni, "bi": bi, "ex": ex, "w_uni": w_u, "w_bi": w_b, "w_ex": w_x,
            "t_uni": thresholds(UNI_FIRST, w_u, UNI_COUNT), "t_bi": thresholds(BI_FIRST, w_b, BI_COUNT),
            "t_ex": ex_thresholds(w_x),
            "widths": {ch: u[ch][1] for ch in V.CHARSET}}
    json.dump(meta, open(os.path.join(OUT, "efont.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    np.savez(os.path.join(OUT, "efont_cells.npz"), uni=np.stack(cells_u),
             bi=np.stack(cells_b) if cells_b else np.zeros((0, 16, 12), np.uint8),
             ex=np.stack(cells_x) if cells_x else np.zeros((0, 16, EX_W), np.uint8))
    tot = sum(len(s) for s in segs)
    codes = sum(len(encode_plain(s, encode)) for s in segs)
    print("glyphs: %d single, %d double; corpus %d chars -> %d codes (%.1f%%)" %
          (len(uni), len(bi), tot, codes, 100.0 * codes / max(tot, 1)))
    both = dict(encode)
    both.update(encode_ex)
    et = sum(len(s_) for s_ in enc_segs)
    ec = sum(len(encode_plain(s_, both)) for s_ in enc_segs)
    print("encyclopedia: %d extra glyphs; %d chars -> %d codes (%.1f%%)" % (len(ex), et, ec, 100.0 * ec / max(et, 1)))
    return meta


def encode_plain(s, encode, maxlen=8):
    """Fewest codes for plain text (DP over glyphs of 1..maxlen characters)."""
    n = len(s)
    best = [0] + [10 ** 9] * n
    back = [None] * (n + 1)
    for i in range(1, n + 1):
        for k in range(1, min(maxlen, i) + 1):
            tok = s[i - k:i]
            if tok in encode and best[i - k] + 1 < best[i]:
                best[i], back[i] = best[i - k] + 1, tok
        if best[i] >= 10 ** 9:
            raise ValueError("cannot encode %r in %r" % (s[i - 1], s))
    out, i = [], n
    while i > 0:
        tok = back[i]
        out.append(encode[tok])
        i -= len(tok)
    return out[::-1]


def text_width(s, meta):
    return sum(meta["widths"].get(c, 8) for c in s)


def preview(text):
    meta = json.load(open(os.path.join(OUT, "efont.json"), encoding="utf-8"))
    z = np.load(os.path.join(OUT, "efont_cells.npz"))
    codes = encode_plain(text, meta["encode"])
    W = 8 + sum((meta["w_uni"][c - UNI_FIRST] if c < BI_FIRST else meta["w_bi"][c - BI_FIRST]) for c in codes) + 12
    canvas = np.zeros((32, W), np.uint8)
    x = 8
    for c in codes:
        cell = z["uni"][c - UNI_FIRST] if c < BI_FIRST else z["bi"][c - BI_FIRST]
        w = meta["w_uni"][c - UNI_FIRST] if c < BI_FIRST else meta["w_bi"][c - BI_FIRST]
        reg = canvas[8:24, x:x + 12]
        m = cell[:, :reg.shape[1]]
        reg[m > 0] = m[m > 0]
        x += w
    im = Image.new("RGB", (W, 32))
    im.putdata([V.PAL[v] for v in canvas.flatten()])
    im.resize((W * 3, 96), Image.NEAREST).save(os.path.join(OUT, "efont_preview.png"))
    print(len(text), "chars ->", len(codes), "codes")


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build(sys.argv[2:] or None)
    else:
        preview(sys.argv[2])
