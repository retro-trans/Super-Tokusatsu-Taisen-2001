"""Edit TIM graphics: erase Japanese text and draw English in the image's own palette.

Text is rendered with Gen'ei LateGo (SIL OFL 1.1, Latin from Linux Biolinum),
optionally bold/outlined, then quantised to the nearest CLUT colour.

    t = Tim(bytes)                     # 4bpp or 8bpp with CLUT
    t.fill(x0, y0, x1, y1, index)      # erase a box with one palette index
    t.text(x, y, "Text", size, color_rgb, outline_rgb=None, shadow_rgb=None,
           align="left", width=None, bold=1)
    data = t.bytes()
"""
import os
import struct

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, "incoming", "GenEiLatin", "GenEiLateGo_v2.ttc")


def lettering(text, size, bold=0, outline=0, shadow=False):
    """Tightly cropped OFL lettering: 0 background, 1 edge/shadow, 2 face."""
    f = ImageFont.truetype(FONT, size, index=1)
    box = f.getbbox(text, stroke_width=bold)
    im = Image.new("L", (box[2] - box[0] + 8, box[3] - box[1] + 8))
    ImageDraw.Draw(im).text((4 - box[0], 4 - box[1]), text, font=f,
                           fill=255, stroke_width=bold)
    core = np.asarray(im) > 110
    edge = np.zeros_like(core)
    for dy in range(-outline, outline + 1):
        for dx in range(-outline, outline + 1):
            edge |= np.roll(np.roll(core, dy, 0), dx, 1)
    if shadow:
        edge |= np.roll(np.roll(core, 1, 0), 1, 1)
    pixels = np.where(core, 2, np.where(edge, 1, 0)).astype(np.uint8)
    ys, xs = np.nonzero(pixels)
    if not len(xs):
        raise ValueError("empty lettering")
    return pixels[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def c15(v):
    return ((v & 31) * 255 // 31, ((v >> 5) & 31) * 255 // 31, ((v >> 10) & 31) * 255 // 31)


class Tim:
    def __init__(self, data):
        self.raw = bytearray(data)
        flags = struct.unpack_from("<I", data, 4)[0]
        self.bpp = flags & 3
        assert flags & 8 and self.bpp in (0, 1), "need 4/8bpp TIM with CLUT"
        clen, cx, cy, cw, ch = struct.unpack_from("<IHHHH", data, 8)
        self.clut_off = 20
        self.clut = list(struct.unpack_from("<%dH" % (cw * ch), data, 20))
        self.ncol = 16 if self.bpp == 0 else 256
        p = 8 + clen
        blen, ix, iy, iw, ih = struct.unpack_from("<IHHHH", data, p)
        self.pix_off = p + 12
        self.h = ih
        if self.bpp == 0:
            self.w = iw * 4
            raw = np.frombuffer(bytes(data[self.pix_off:self.pix_off + iw * 2 * ih]), np.uint8).reshape(ih, iw * 2)
            self.idx = np.empty((ih, self.w), np.uint8)
            self.idx[:, 0::2] = raw & 15
            self.idx[:, 1::2] = raw >> 4
        else:
            self.w = iw * 2
            self.idx = np.frombuffer(bytes(data[self.pix_off:self.pix_off + iw * 2 * ih]), np.uint8).reshape(ih, self.w).copy()
        self.palette = [c15(v) for v in self.clut[:self.ncol]]

    def rgb(self):
        pal = np.array(self.palette, np.uint8)
        return Image.fromarray(pal[self.idx % len(pal)])

    def nearest(self, rgb, avoid0=True):
        best, bd = 0, 1e9
        for i, (c, v) in enumerate(zip(self.palette, self.clut)):
            if avoid0 and v == 0:
                continue
            d = sum((a - b) ** 2 for a, b in zip(c, rgb))
            if d < bd:
                best, bd = i, d
        return best

    def fill(self, x0, y0, x1, y1, index):
        self.idx[y0:y1, x0:x1] = index

    def label(self, rect, text, size, color=(255, 255, 255), edge=(80, 80, 80),
              bold=0, outline=0, shadow=False, min_size=7, gradient=None):
        """Fit and centre lettering inside a measured sprite; fail on overflow."""
        x0, y0, x1, y1 = rect
        if not (0 <= x0 < x1 <= self.w and 0 <= y0 < y1 <= self.h):
            raise ValueError("invalid sprite rectangle: %r" % (rect,))
        for chosen in range(size, min_size - 1, -1):
            mask = lettering(text, chosen, bold, outline, shadow)
            h, w = mask.shape
            if w <= x1 - x0 and h <= y1 - y0:
                break
        else:
            raise ValueError("%r does not fit %r" % (text, rect))
        x, y = x0 + (x1 - x0 - w) // 2, y0 + (y1 - y0 - h) // 2
        dest = self.idx[y:y + h, x:x + w]
        dest[mask == 1] = self.nearest(edge)
        if gradient:
            for row in range(h):
                rgb = tuple(round(a + (b - a) * row / max(h - 1, 1))
                            for a, b in zip(*gradient))
                dest[row, mask[row] == 2] = self.nearest(rgb)
        else:
            dest[mask == 2] = self.nearest(color)
        return {"text": text, "font_size": chosen, "bounds": [x, y, x + w, y + h]}

    def text(self, x, y, s, size, color, outline=None, shadow=None, align="left", width=None, bold=1,
             spacing=0, region=None):
        """Draw text; (x, y) = top-left of the text box. Returns the pixel width used."""
        f = ImageFont.truetype(FONT, size, index=1)
        tw = int(f.getlength(s)) + spacing * max(len(s) - 1, 0) + 2 * bold + 4
        th = size + 8
        layer = Image.new("L", (tw + 8, th + 8))
        d = ImageDraw.Draw(layer)
        cx = 4
        for ch in s:
            d.text((cx, 2), ch, font=f, fill=255, stroke_width=0)
            if bold:
                for b in range(1, bold + 1):
                    d.text((cx + b, 2), ch, font=f, fill=255)
            cx += f.getlength(ch) + spacing
        a = np.asarray(layer, np.int32)
        if width is not None and align != "left":
            used = int(cx - 4 + bold)
            off = (width - used) // 2 if align == "center" else width - used
            x = x + off - 4
        else:
            x = x - 4
        ci = self.nearest(color)
        mask = a > 110
        if outline is not None:
            oi = self.nearest(outline)
            m2 = np.zeros_like(mask)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    m2 |= np.roll(np.roll(mask, dy, 0), dx, 1)
            self._paint(x, y, m2 & ~mask, oi, region)
        if shadow is not None:
            si = self.nearest(shadow)
            sm = np.roll(np.roll(mask, 1, 0), 1, 1) & ~mask
            self._paint(x, y, sm, si, region)
        self._paint(x, y, mask, ci, region)
        return int(cx - 4)

    def _paint(self, x, y, mask, index, region=None):
        ys, xs = np.nonzero(mask)
        for py, px in zip(ys + y - 2, xs + x):
            if 0 <= py < self.h and 0 <= px < self.w:
                if region and not (region[0] <= px < region[2] and region[1] <= py < region[3]):
                    continue
                self.idx[py, px] = index

    def bytes(self):
        if self.bpp == 0:
            packed = (self.idx[:, 0::2] | (self.idx[:, 1::2] << 4)).astype(np.uint8).tobytes()
        else:
            packed = self.idx.astype(np.uint8).tobytes()
        out = bytearray(self.raw)
        out[self.pix_off:self.pix_off + len(packed)] = packed
        return bytes(out)
