"""Contact sheets of TIM images (raw entries and CM-compressed blocks).
python tools/contact.py <DAT name> <first> <last> <out.png> [thumb]"""
import os, sys, struct
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import tim2png, cm
dat, a, b, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
T = int(sys.argv[5]) if len(sys.argv) > 5 else 160
ims = []
for i in range(a, b + 1):
    p = os.path.join(ROOT, "work", "source", "unpacked", dat, "%04d.bin" % i)
    if not os.path.exists(p): continue
    buf = open(p, "rb").read()
    srcs = [("", buf)]
    if buf[:2] == b"CM":
        try: srcs = [("c%d" % k, x) for k, x in enumerate(cm.blocks(buf))]
        except Exception: srcs = []
    for tag, x in srcs:
        try: r = tim2png.parse(x)
        except Exception: r = None
        if r and 0 not in r[0].size:
            im = r[0].convert("RGB"); im.thumbnail((T, T)); ims.append(("%d%s" % (i, tag), im))
cols = 8
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * (T + 4), rows * (T + 14)), (60, 0, 60))
d = ImageDraw.Draw(sheet)
for k, (name, im) in enumerate(ims):
    x, y = (k % cols) * (T + 4), (k // cols) * (T + 14)
    sheet.paste(im, (x, y + 12)); d.text((x + 2, y), name, fill=(255, 255, 0))
sheet.save(out); print(len(ims), "images ->", out)
