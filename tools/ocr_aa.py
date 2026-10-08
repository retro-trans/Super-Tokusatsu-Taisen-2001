"""Recognise game kanji by comparing with anti-aliased renders of system fonts.

python tools/ocr_aa.py calibrate        -> accuracy of each font/size on labelled glyphs
python tools/ocr_aa.py run <font> <size> -> work/font/variant_ocr.json (top-5 per unknown shape)
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fontsets as F  # noqa: E402

FONTS = {
    "msgothic": "C:/Windows/Fonts/msgothic.ttc",
    "yugoth": "C:/Windows/Fonts/YuGothR.ttc",
    "yugothm": "C:/Windows/Fonts/YuGothM.ttc",
    "bizud": "C:/Windows/Fonts/BIZ-UDGothicR.ttc",
    "bizudb": "C:/Windows/Fonts/BIZ-UDGothicB.ttc",
    "meiryo": "C:/Windows/Fonts/meiryo.ttc",
}
LV = np.array([0.0, 0.3, 0.65, 1.0], np.float32)


def kanji_candidates():
    out = []
    for lead in list(range(0x88, 0xA0)) + list(range(0xE0, 0xEB)):
        for tr in range(0x40, 0xFD):
            if tr == 0x7F:
                continue
            try:
                ch = bytes([lead, tr]).decode("cp932")
            except UnicodeDecodeError:
                continue
            out.append(ch)
    # kana / symbols that can appear in the 12px area too
    out += [chr(c) for c in range(0x3041, 0x3097)] + [chr(c) for c in range(0x30A1, 0x30F7)]
    out += list("々〆ヵヶ○△□◎●▲■◆★☆♪※→←↑↓＋－×÷＝％＆＠！？・…ー々")
    return out


def norm(a):
    a = a - a.mean()
    n = np.sqrt((a * a).sum())
    return a / n if n > 0 else a


def render_set(chars, path, size):
    f = ImageFont.truetype(path, size)
    arr = np.zeros((len(chars), 16, 12), np.float32)
    for i, ch in enumerate(chars):
        im = Image.new("L", (24, 24))
        ImageDraw.Draw(im).text((0, 0), ch, font=f, fill=255)
        a = np.asarray(im, np.float32) / 255
        ys, xs = np.nonzero(a > 0.15)
        if len(ys) == 0:
            continue
        c = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1][:16, :12]
        arr[i, :c.shape[0], :c.shape[1]] = c
    return arr


def align(g):
    """Crop a game glyph (float) to its bounding box, top-left aligned."""
    ys, xs = np.nonzero(g > 0)
    out = np.zeros((16, 12), np.float32)
    if len(ys) == 0:
        return out
    c = g[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    out[:c.shape[0], :c.shape[1]] = c
    return out


def score(glyphs, refs):
    """glyphs: (n,16,12) aligned; refs: (m,16,12). Returns (n,m) correlation, best over small shifts."""
    R = np.stack([norm(r) for r in refs]).reshape(len(refs), -1)
    best = None
    for dy in (0, 1):
        for dx in (0, 1):
            G = np.stack([norm(np.roll(np.roll(g, dy, 0), dx, 1)) for g in glyphs]).reshape(len(glyphs), -1)
            s = G @ R.T
            best = s if best is None else np.maximum(best, s)
    return best


def labelled():
    from kana_table import TABLE  # noqa
    cm = json.load(open(os.path.join(ROOT, "work", "font", "charmap.json"), encoding="utf-8"))
    items = []
    for k, ch in cm["map"].items():
        k = int(k)
        if k in cm["uncertain"] or len(ch) != 1 or ch in "√〓":
            continue
        items.append((LV[F.glyph_level(k, 11)], ch))
    return items


def big_crops(chars, path, size=48):
    f = ImageFont.truetype(path, size)
    out = []
    for ch in chars:
        im = Image.new("L", (size * 2, size * 2))
        ImageDraw.Draw(im).text((4, 4), ch, font=f, fill=255)
        bb = im.getbbox()
        out.append(im.crop(bb) if bb else None)
    return out


def bbox_of(g):
    ys, xs = np.nonzero(g > 0)
    return (ys.min(), ys.max() + 1, xs.min(), xs.max() + 1) if len(ys) else None


def score_bbox(glyph_list, crops):
    """Each glyph vs every candidate resized to the glyph's bbox. Returns (n,m)."""
    res = np.zeros((len(glyph_list), len(crops)), np.float32)
    groups = {}
    for i, g in enumerate(glyph_list):
        b = bbox_of(g)
        if b is None:
            continue
        groups.setdefault((b[1] - b[0], b[3] - b[2]), []).append((i, g[b[0]:b[1], b[2]:b[3]]))
    for (h, w), items in groups.items():
        R = np.zeros((len(crops), h * w), np.float32)
        for j, c in enumerate(crops):
            if c is None:
                continue
            a = np.asarray(c.resize((w, h), Image.BOX), np.float32).reshape(-1) / 255
            R[j] = norm(a)
        G = np.stack([norm(g.reshape(-1)) for _, g in items])
        S = G @ R.T
        for k, (i, _) in enumerate(items):
            res[i] = S[k]
    return res


def calibrate():
    items = labelled()
    chars = kanji_candidates()
    idx = {c: i for i, c in enumerate(chars)}
    items = [(g, ch) for g, ch in items if ch in idx]
    truth = np.array([idx[ch] for _, ch in items])
    for name in ("msgothic", "yugothm", "bizud", "bizudb", "meiryo"):
        crops = big_crops(chars, FONTS[name])
        s = score_bbox([g for g, _ in items], crops)
        top = np.argsort(-s, 1)[:, :5]
        print("%-9s bbox top1 %.3f  top5 %.3f" % (name, (top[:, 0] == truth).mean(), (top == truth[:, None]).any(1).mean()), flush=True)


def calibrate_old():
    items = labelled()
    chars = kanji_candidates()
    idx = {c: i for i, c in enumerate(chars)}
    items = [(g, ch) for g, ch in items if ch in idx]
    G = np.stack([align(g) for g, _ in items])
    truth = np.array([idx[ch] for _, ch in items])
    for name in ("msgothic", "yugoth", "yugothm", "bizud", "bizudb", "meiryo"):
        for size in (12, 13, 14):
            refs = render_set(chars, FONTS[name], size)
            s = score(G, refs)
            top = np.argsort(-s, 1)[:, :5]
            a1 = (top[:, 0] == truth).mean()
            a5 = (top == truth[:, None]).any(1).mean()
            print("%-9s %2d  top1 %.3f  top5 %.3f" % (name, size, a1, a5), flush=True)


def run(name, size):
    v = json.load(open(os.path.join(ROOT, "work", "font", "variants.json"), encoding="utf-8"))
    chars = kanji_candidates()
    crops = big_crops(chars, FONTS[name])
    shapes = v["unknown_shapes"]
    G = [LV[F.glyph_level(code, var)] for var, code in (s[0] for s in shapes)]
    out = []
    s = score_bbox(G, crops)
    top = np.argsort(-s, 1)[:, :5]
    for j in range(len(top)):
        out.append([[chars[t], round(float(s[j, t]), 3)] for t in top[j]])
    json.dump({"shapes": shapes, "cands": out}, open(os.path.join(ROOT, "work", "font", "variant_ocr.json"), "w",
                                                      encoding="utf-8"), ensure_ascii=False)
    print("done", len(out))


if __name__ == "__main__" and sys.argv[1] in ("calibrate", "run"):
    if sys.argv[1] == "calibrate":
        calibrate()
    else:
        run(sys.argv[2], sys.argv[3])


def run_ensemble():
    v = json.load(open(os.path.join(ROOT, "work", "font", "variants.json"), encoding="utf-8"))
    chars = kanji_candidates()
    shapes = v["unknown_shapes"]
    G = [LV[F.glyph_level(code, var)] for var, code in (s[0] for s in shapes)]
    S = 0
    for name, wt in (("bizudb", 1.0), ("bizud", 0.7), ("msgothic", 0.4), ("meiryo", 0.4)):
        S = S + wt * score_bbox(G, big_crops(chars, FONTS[name]))
    top = np.argsort(-S, 1)[:, :5]
    out = [[[chars[t], round(float(S[j, t]), 3)] for t in top[j]] for j in range(len(top))]
    json.dump({"shapes": shapes, "cands": out}, open(os.path.join(ROOT, "work", "font", "variant_ocr.json"), "w",
                                                      encoding="utf-8"), ensure_ascii=False)
    print("done", len(out))


def sheets():
    from PIL import ImageFont as IF
    d = json.load(open(os.path.join(ROOT, "work", "font", "variant_ocr.json"), encoding="utf-8"))
    lf = IF.truetype("C:/Windows/Fonts/msgothic.ttc", 12)
    cf = IF.truetype("C:/Windows/Fonts/BIZ-UDGothicR.ttc", 15)
    col = {0: 255, 1: 200, 2: 120, 3: 0}
    COLS, ROWS, CW, CH, S = 10, 10, 84, 74, 4
    per = COLS * ROWS
    n = len(d["shapes"])
    for sh in range((n + per - 1) // per):
        im = Image.new("L", (COLS * CW, ROWS * CH), 255)
        dr = ImageDraw.Draw(im)
        for k in range(per):
            i = sh * per + k
            if i >= n:
                break
            var, code = d["shapes"][i][0]
            g = F.glyph_level(code, var)
            gi = Image.new("L", (12, 16))
            gi.putdata([col[int(v)] for v in g.flatten()])
            x, y = (k % COLS) * CW, (k // COLS) * CH
            im.paste(gi.resize((48, 64), Image.NEAREST), (x + 2, y + 8))
            dr.text((x + 2, y), str(i), font=lf, fill=0)
            for j, (c, _) in enumerate(d["cands"][i][:5]):
                dr.text((x + 52, y + 2 + j * 14), "%d%s" % (j + 1, c), font=cf, fill=0)
            dr.rectangle([x, y, x + CW - 1, y + CH - 1], outline=170)
        im.save(os.path.join(ROOT, "work", "font", "vreview_%02d.png" % sh))
    print("sheets", (n + per - 1) // per)


if __name__ == "__main__" and sys.argv[1] in ("ensemble", "sheets"):
    {"ensemble": run_ensemble, "sheets": sheets}[sys.argv[1]]()


def battle_ocr():
    from PIL import ImageFont as IF
    bf = json.load(open(os.path.join(ROOT, "work", "font", "battle_font.json"), encoding="utf-8"))
    chars = kanji_candidates()
    shapes = bf["unknown_shapes"]
    G = [LV[F.battle_glyph_level(c[0])] for c in shapes]
    S = 0
    for name, wt in (("bizudb", 1.0), ("bizud", 0.7), ("msgothic", 0.4), ("meiryo", 0.4)):
        S = S + wt * score_bbox(G, big_crops(chars, FONTS[name]))
    top = np.argsort(-S, 1)[:, :5]
    cands = [[[chars[t], round(float(S[j, t]), 3)] for t in top[j]] for j in range(len(top))]
    json.dump({"shapes": shapes, "cands": cands},
              open(os.path.join(ROOT, "work", "font", "battle_ocr.json"), "w", encoding="utf-8"), ensure_ascii=False)
    lf = IF.truetype("C:/Windows/Fonts/msgothic.ttc", 12)
    cf = IF.truetype("C:/Windows/Fonts/BIZ-UDGothicR.ttc", 15)
    col = {0: 255, 1: 200, 2: 120, 3: 0}
    COLS, ROWS, CW, CH = 10, 10, 84, 74
    per = COLS * ROWS
    n = len(shapes)
    for sh in range((n + per - 1) // per):
        im = Image.new("L", (COLS * CW, ROWS * CH), 255)
        dr = ImageDraw.Draw(im)
        for k in range(per):
            i = sh * per + k
            if i >= n:
                break
            g = F.battle_glyph_level(shapes[i][0])
            gi = Image.new("L", (12, 16))
            gi.putdata([col[int(v)] for v in g.flatten()])
            x, y = (k % COLS) * CW, (k // COLS) * CH
            im.paste(gi.resize((48, 64), Image.NEAREST), (x + 2, y + 8))
            dr.text((x + 2, y), str(i), font=lf, fill=0)
            for j, (c, _) in enumerate(cands[i][:5]):
                dr.text((x + 52, y + 2 + j * 14), "%d%s" % (j + 1, c), font=cf, fill=0)
            dr.rectangle([x, y, x + CW - 1, y + CH - 1], outline=170)
        im.save(os.path.join(ROOT, "work", "font", "breview_%02d.png" % sh))
    print("battle shapes", n, "sheets", (n + per - 1) // per)


if __name__ == "__main__" and sys.argv[1] == "battle":
    battle_ocr()
