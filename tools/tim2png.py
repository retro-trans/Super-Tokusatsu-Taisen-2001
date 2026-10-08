"""Convert PS1 TIM images to PNG.

Usage: python tools/tim2png.py <in.bin|dir> [outdir] [--gray]
  --gray  ignore the CLUT and render 4/8bpp indices as grayscale
          (handy for fonts whose CLUT is supplied at runtime).
"""
import os
import struct
import sys

from PIL import Image


def c15(v):
    r, g, b = v & 31, (v >> 5) & 31, (v >> 10) & 31
    a = 0 if v == 0 else 255
    return (r * 255 // 31, g * 255 // 31, b * 255 // 31, a)


def parse(data, gray=False):
    if data[:4] != b"\x10\0\0\0":
        return None
    flags = struct.unpack_from("<I", data, 4)[0]
    bpp = flags & 3
    pos = 8
    clut = None
    if flags & 8:
        blen, cx, cy, cw, ch = struct.unpack_from("<IHHHH", data, pos)
        vals = struct.unpack_from("<%dH" % (cw * ch), data, pos + 12)
        clut = [c15(v) for v in vals]
        pos += blen
    blen, ix, iy, iw, ih = struct.unpack_from("<IHHHH", data, pos)
    pix = data[pos + 12:pos + blen]
    if bpp == 0:
        w = iw * 4
        idx = []
        for b in pix[:iw * 2 * ih]:
            idx += [b & 15, b >> 4]
        pal = clut if clut and not gray else [(i * 17, i * 17, i * 17, 255) for i in range(16)]
    elif bpp == 1:
        w = iw * 2
        idx = list(pix[:iw * 2 * ih])
        pal = clut if clut and not gray else [(i, i, i, 255) for i in range(256)]
    elif bpp == 2:
        w = iw
        vals = struct.unpack_from("<%dH" % (iw * ih), pix)
        im = Image.new("RGBA", (w, ih))
        im.putdata([c15(v) for v in vals])
        return im, (ix, iy), bpp
    else:
        return None
    im = Image.new("RGBA", (w, ih))
    im.putdata([pal[i % len(pal)] for i in idx])
    return im, (ix, iy), bpp


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    gray = "--gray" in sys.argv
    src = args[0]
    out = args[1] if len(args) > 1 else os.path.join(os.path.dirname(src) if os.path.isfile(src) else src, "png")
    os.makedirs(out, exist_ok=True)
    files = [src] if os.path.isfile(src) else [os.path.join(src, f) for f in sorted(os.listdir(src)) if f.endswith(".bin")]
    for f in files:
        try:
            r = parse(open(f, "rb").read(), gray)
        except struct.error:
            r = None
        if not r or 0 in r[0].size:
            continue
        im, vram, bpp = r
        name = os.path.splitext(os.path.basename(f))[0]
        im.save(os.path.join(out, "%s.png" % name))
        print("%s %dx%d %dbpp vram=%s" % (name, im.size[0], im.size[1], (4, 8, 16)[bpp], vram))


if __name__ == "__main__":
    main()
