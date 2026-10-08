"""English episode title cards (EVENT #52-#141).
Each card: title area rows 20-80 redrawn; 第 (x 270-296) -> "EP", 話 (x 297-320) blanked.
work/translation/en/graphics.en.json maps EVENT index -> English title."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import gfx

WHITE, BLACK = (255, 255, 255), (0, 0, 0)


def fit(title, maxw=304):
    for size in (30, 28, 26, 24):
        if gfx.lettering(title, size, bold=1, shadow=True).shape[1] <= maxw:
            return [title], size
    words = title.split()
    best = None
    for k in range(1, len(words)):
        a, b = " ".join(words[:k]), " ".join(words[k:])
        for size in (24, 22, 20, 18):
            w = max(gfx.lettering(s, size, bold=1, shadow=True).shape[1] for s in (a, b))
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
        t.label((8, 22, 312, 80), lines[0], size, WHITE, bold=1, shadow=True)
    else:
        t.label((8, 20, 312, 50), lines[0], size, WHITE, bold=1, shadow=True)
        t.label((8, 52, 312, 82), lines[1], size, WHITE, bold=1, shadow=True)
    t.fill(270, 100, 320, 128, bg)
    t.label((272, 100, 296, 128), "EP", 18, WHITE, bold=1)
    return t.bytes()


if __name__ == "__main__":
    import tim2png
    data = open(os.path.join(ROOT, "work/source/unpacked/EVENT/0052.bin"), "rb").read()
    out = make_card(data, sys.argv[1] if len(sys.argv) > 1 else "The Man Who Fell to Earth")
    im = tim2png.parse(out)[0]
    im.convert("RGB").resize((640, 256)).save(sys.argv[2] if len(sys.argv) > 2 else "card_test.png")
