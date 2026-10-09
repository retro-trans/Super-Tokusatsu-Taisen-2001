"""Stage title cards with consistent regular lettering and matching numerals.
The stage-script sprite rectangles are updated by stage_cards.patch_script.
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import gfx

WHITE, BLACK = (255, 255, 255), (0, 0, 0)


def fit(title, maxw=304):
    for size in (24, 22):
        if gfx.lettering(title, size).shape[1] <= maxw:
            return [title], size
    words = title.split()
    best = None
    for k in range(1, len(words)):
        a, b = " ".join(words[:k]), " ".join(words[k:])
        for size in (24, 22, 20, 18):
            w = max(gfx.lettering(s, size).shape[1] for s in (a, b))
            if w <= maxw:
                cand = (size, -abs(len(a) - len(b)), [a, b])
                if best is None or cand > best:
                    best = cand
                break
    if best:
        return best[2], best[0]
    raise ValueError("episode title cannot fit: %r" % title)


def make_card(data, title):
    t = gfx.Tim(data)
    bg = t.idx[5, 5]
    t.fill(0, 18, 320, 84, bg)
    lines, size = fit(title)
    if len(lines) == 1:
        t.label((8, 22, 312, 80), lines[0], size, WHITE)
    else:
        t.label((8, 20, 312, 50), lines[0], size, WHITE)
        t.label((8, 52, 312, 82), lines[1], size, WHITE)
    t.fill(0, 100, 320, 128, bg)
    for digit in range(10):
        t.label((digit * 24, 104, (digit + 1) * 24, 128), str(digit), 18, WHITE)
    t.label((256, 104, 308, 128), "Stage", 18, WHITE)
    return t.bytes()


if __name__ == "__main__":
    import tim2png
    data = open(os.path.join(ROOT, "work/source/unpacked/EVENT/0052.bin"), "rb").read()
    out = make_card(data, sys.argv[1] if len(sys.argv) > 1 else "The Man Who Fell to Earth")
    im = tim2png.parse(out)[0]
    im.convert("RGB").resize((640, 256)).save(sys.argv[2] if len(sys.argv) > 2 else "card_test.png")
