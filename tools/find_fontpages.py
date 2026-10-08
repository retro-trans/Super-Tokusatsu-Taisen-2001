"""Find every 4bpp image (raw TIM or inside CM blocks) that holds font glyphs:
count 12x16 cells (21x16 grid, both 2bpp layers) that exactly match a glyph
from the default font. Output: work/font/fontpages.json"""
import glob, json, os, struct, sys
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fontsets as F, cm

known = set()
for code in range(320, 1454):
    g = F.glyph_level(code, 11)
    if g.any(): known.add(g.tobytes())

def tims(buf):
    """yield (offset, w_px, h, pixels) for 4bpp TIMs starting at offset 0 of buf"""
    if buf[:4] != b"\x10\0\0\0": return
    fl = struct.unpack_from("<I", buf, 4)[0]
    if fl & 7 != 0: return
    p = 8
    if fl & 8: p += struct.unpack_from("<I", buf, p)[0]
    if p + 12 > len(buf): return
    blen, x, y, w, h = struct.unpack_from("<IHHHH", buf, p)
    if w * 2 * h > len(buf) - p - 12 or w == 0: return
    raw = np.frombuffer(buf[p + 12:p + 12 + w * 2 * h], np.uint8).reshape(h, w * 2)
    pix = np.empty((h, w * 4), np.uint8); pix[:, 0::2] = raw & 15; pix[:, 1::2] = raw >> 4
    yield (x, y), pix

def score(pix):
    h, w = pix.shape
    hit = 0
    for half in range(0, w - 251, 256):
        for sh in (0, 2):
            for r in range(h // 16):
                for c in range(21):
                    g = (pix[r*16:r*16+16, half + c*12:half + c*12 + 12] >> sh) & 3
                    if g.shape == (16, 12) and g.tobytes() in known: hit += 1
    return hit

res = []
for f in sorted(glob.glob(os.path.join(ROOT, "work/source/unpacked/*/*.bin"))):
    buf = open(f, "rb").read()
    srcs = [("raw", buf)]
    if buf[:2] == b"CM":
        try: srcs = [("cm%d" % i, b) for i, b in enumerate(cm.blocks(buf))]
        except Exception: srcs = []
    for tag, b in srcs:
        for vram, pix in tims(b):
            s = score(pix)
            if s >= 40:
                res.append([os.path.relpath(f, ROOT), tag, vram, list(pix.shape), s])
                print(res[-1], flush=True)
json.dump(res, open(os.path.join(ROOT, "work/font/fontpages.json"), "w"), indent=0)
