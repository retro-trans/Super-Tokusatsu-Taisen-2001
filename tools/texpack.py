"""4x font texture pack for DuckStation (texture cache / VRAM-write replacements).

DuckStation names a replacement after the VRAM write it replaces:
  texupload-<P4|STP4>-<write hash>-<palette hash>-<w>x<h>-<x>-<y>-<aw>x<ah>-P0-15.png
  write hash   = XXH3-64 of the uploaded pixel block (the TIM image data)
  palette hash = XXH3-64 of the 16 CLUT entries
  w x h        = write size in VRAM halfwords; x, y, aw x ah = covered texels
(verified against dumps from v0.3.2: font sheet 647797B20330DB37, CLUT rows).

Each 4bpp font pixel holds two 2-bit layers (F0 bits 0-1, F1 bits 2-3) and the
CLUT row picks the layer and the colour, so every (sheet page, CLUT row, blend
mode) gets its own image.  English glyph cells are re-rendered from Gen'ei
LateGo at 4x with the same metrics as the 1x font (so the VWF widths still
line up); all other cells (kana, icons, kanji) are upscaled with Scale4x.

Pages written: MAPMAIN #7 pages 0-1 (EVENT #10 / MAPMAIN #25 hold the same
data), BATTLE #538 pages 0-1, BATTLE #537, and the per-scene right pages
EVENT #11-#23 (F0 palettes only: they carry the 24 px word glyphs).

python tools/texpack.py <version>   (also called by tools/build.py)
Output: work/output/STT2001_EN_v<ver>_4x_font/SLPS-02863/replacements/
"""
import json
import shutil
import os
import struct
import sys

import numpy as np
import xxhash
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import efont  # noqa: E402
import vwf_font as V  # noqa: E402

K = 4                       # scale
SERIAL = "SLPS-02863"
STP_ALPHA = 143             # what DuckStation dumps use for semi-transparent texels
SHADOW = (2, 2)             # drop shadow of the 4x English glyphs (dx, dy in 4x pixels); None = off


# ---------------------------------------------------------------- TIM helpers
def tim_parts(t):
    flags = struct.unpack_from("<I", t, 4)[0]
    clut, p = None, 8
    if flags & 8:
        clen, cx, cy, cw, ch = struct.unpack_from("<IHHHH", t, 8)
        clut = list(struct.unpack_from("<%dH" % (cw * ch), t, 20))
        p = 8 + clen
    _, ix, iy, iw, ih = struct.unpack_from("<IHHHH", t, p)
    block = bytes(t[p + 12:p + 12 + iw * ih * 2])
    raw = np.frombuffer(block, np.uint8).reshape(ih, iw * 2)
    pix = np.empty((ih, iw * 4), np.uint8)
    pix[:, 0::2] = raw & 15
    pix[:, 1::2] = raw >> 4
    return pix, (iw, ih), xxhash.xxh3_64_intdigest(block), clut


def palettes(cluts):
    """Distinct 16-colour rows that are font palettes: (hash, layer, colours[16])."""
    out = {}
    for clut in cluts:
        if not clut:
            continue
        for r in range(len(clut) // 16):
            row = clut[r * 16:r * 16 + 16]
            if not any(row):
                continue
            if all(row[i] == row[i % 4] for i in range(16)):
                layer = 0
            elif all(row[i] == row[(i // 4) * 4] for i in range(16)):
                layer = 1
            else:
                continue
            h = xxhash.xxh3_64_intdigest(struct.pack("<16H", *row))
            out[h] = (layer, row)
    return out


# ---------------------------------------------------------------- scaling
def scale2x(a):
    p = np.pad(a, 1, mode="edge")
    B, D, E, F, H = p[:-2, 1:-1], p[1:-1, :-2], p[1:-1, 1:-1], p[1:-1, 2:], p[2:, 1:-1]
    o = np.empty((a.shape[0] * 2, a.shape[1] * 2), a.dtype)
    o[0::2, 0::2] = np.where((B == D) & (B != F) & (D != H), D, E)
    o[0::2, 1::2] = np.where((B == F) & (B != D) & (F != H), F, E)
    o[1::2, 0::2] = np.where((D == H) & (D != B) & (H != F), D, E)
    o[1::2, 1::2] = np.where((H == F) & (D != H) & (B != F), F, E)
    return o


def scale4x(a):
    return scale2x(scale2x(a))


# ---------------------------------------------------------------- hi-res glyphs
class HiFont:
    def __init__(self):
        fname, idx = V.FACES[V.DEFAULT_FACE]
        path = os.path.join(V.FONT_DIR, fname)
        self.lo = ImageFont.truetype(path, V.DEFAULT_SIZE, index=idx)
        self.hi = ImageFont.truetype(path, V.DEFAULT_SIZE * K, index=idx)
        self.cache = {}
        meta = json.load(open(os.path.join(ROOT, "work", "font", "efont.json"), encoding="utf-8"))
        self.meta = meta
        self.adv = meta["widths"]

    def char(self, ch):
        """(K*16 x K*12 level array) aligned like vwf_font.render_char's 1x cell."""
        if ch in self.cache:
            return self.cache[ch]
        cell = np.zeros((16 * K, 12 * K), np.uint8)
        if ch != " ":
            big = Image.new("L", (40, 40))
            ImageDraw.Draw(big).text((8, 8 + V.BASELINE - self.lo.getmetrics()[0]), ch, font=self.lo, fill=255)
            a = np.asarray(big, np.int32)
            cols = np.nonzero(a.max(0) > 40)[0]
            if len(cols):
                x0 = int(cols[0])
                w = min(int(cols[-1]) - x0 + 1, 11)
                bh = Image.new("L", (40 * K, 40 * K))
                ImageDraw.Draw(bh).text((8 * K, (8 + V.BASELINE) * K - self.hi.getmetrics()[0]), ch,
                                        font=self.hi, fill=255)
                b = np.asarray(bh, np.int32)[8 * K:(8 + 16) * K, x0 * K:x0 * K + w * K]
                cell[:b.shape[0], :b.shape[1]] = np.where(b >= 150, 3, np.where(b >= 70, 2, 0))
        self.cache[ch] = cell
        return cell

    def string(self, s, width):
        out = np.zeros((16 * K, (width + 12) * K), np.uint8)
        x = 0
        for ch in s:
            c = self.char(ch)
            reg = out[:, x * K:x * K + c.shape[1]]
            np.maximum(reg, c[:, :reg.shape[1]], out=reg)
            x += self.adv.get(ch, 8)
        return out[:, :width * K]


def cell_xy(code):
    """(page, layer, x, y) of a 12 px code, as in the font lookup routine."""
    a = code - 110
    page, r = a // 336, a % 336
    layer = 0
    if code >= 782:
        page -= 2
        layer = 1
    return page, layer, (r % 21) * 12, (r // 21) * 16


# ---------------------------------------------------------------- pages
def shadow(cell):
    """Palette level 1 (each colour's shadow shade) right of / below the ink."""
    if not SHADOW:
        return cell
    dx, dy = SHADOW
    lit = cell > 0
    sh = np.zeros_like(lit)
    sh[dy:, dx:] = lit[:-dy or None, :-dx or None]
    return np.where(lit, cell, np.where(sh, 1, 0)).astype(np.uint8)


def hires_layers(pix, page, hf, role):
    """Two K-scaled level maps (F0, F1) for one 256x256 page of a font sheet.
    role "main": English and native values; "encyc": English only (tab sheet);
    "ex": word glyphs and compact terrain labels."""
    sub = pix[:, page * 256:(page + 1) * 256]
    if role == "main":
        import ui_value_font
        sub = ui_value_font.upscale_base(sub)
        import weapon_markers
        sub = weapon_markers.upscale_main_base(sub)
    if role == "ex":
        import weapon_markers
        sub = weapon_markers.upscale_ex_base(sub)
    layers = [scale4x(sub & 3), scale4x(sub >> 2)]
    if role in ("main", "encyc"):
        m = hf.meta
        for i, ch in enumerate(m["uni"]):
            _, ly, x, y = cell_xy(efont.UNI_FIRST + i)
            layers[ly][y * K:(y + 16) * K, x * K:(x + 12) * K] = shadow(hf.char(ch))
        for i, s in enumerate(m["bi"]):
            _, ly, x, y = cell_xy(efont.BI_FIRST + i)
            layers[ly][y * K:(y + 16) * K, x * K:(x + 12) * K] = shadow(hf.string(s, 12))
        if role == "main":
            import ui_value_font
            for code, glyph in ui_value_font.cells(hires=True, hf=hf).items():
                x, y = (code%32)*8, (code//32)*16
                layers[0][y*K:(y+16)*K,x*K:(x+8)*K] = shadow(glyph)
            import weapon_markers
            for code,glyph in weapon_markers.prefixes(hires=True,hf=hf).items():
                x,y=(code%32)*8,(code//32)*16
                layers[0][y*K:(y+16)*K,x*K:(x+8)*K] = shadow(glyph)
    if role == "ex":
        for i, g in enumerate(hf.meta["ex"]):
            _, ly, x, y = cell_xy(efont.EX_SLOTS[i])
            layers[ly][y * K:(y + 16) * K, x * K:(x + efont.EX_W) * K] = shadow(hf.string(g, efont.EX_W))
        import ui_glyphs
        for code, glyph in ui_glyphs.cells(hires=True).items():
            _, ly, x, y = cell_xy(code)
            layers[ly][y*K:(y+16)*K,x*K:(x+12)*K] = glyph
        import weapon_markers
        for code,glyph in weapon_markers.badges(hires=True).items():
            _,ly,x,y=cell_xy(code)
            layers[ly][y*K:(y+16)*K,x*K:(x+12)*K] = glyph
    return layers


def c15(v):
    return tuple(int(round(((v >> s) & 31) * 255 / 31)) for s in (0, 5, 10))


def colourise(levels, layer, row, stp):
    lut = np.zeros((4, 4), np.uint8)
    for lv in range(1, 4):
        v = row[lv if layer == 0 else lv * 4]
        if v == 0:
            continue
        lut[lv, :3] = c15(v)
        lut[lv, 3] = STP_ALPHA if stp and v & 0x8000 else 255
    return Image.fromarray(lut[levels], "RGBA")


def build(files, version, log=print):
    import repack
    import cm
    mm = repack.dat_entries(files["MAPMAIN.DAT"])
    bt = repack.dat_entries(files["BATTLE.DAT"])
    ev = repack.dat_entries(files["EVENT.DAT"])
    sheets = [  # (name, tim, [(page in this TIM, role)]); "ex" pages only need the F0 palettes
        ("MAPMAIN7", mm[7], [(0, "main"), (1, "ex")]),
        ("BATTLE538", bt[538], [(0, "main"), (1, "ex")]),
        ("BATTLE537", bt[537], [(0, "encyc")]),
    ] + [("EVENT%d" % i, ev[i], [(0, "ex")]) for i in range(11, 24)]
    parts = {n: tim_parts(t) for n, t, _ in sheets}
    pals = palettes([parts[n][3] for n in parts])
    out = os.path.join(ROOT, "work", "output", "STT2001_EN_v%s_4x_font" % version, SERIAL, "replacements")
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.startswith("texupload-"):
            os.remove(os.path.join(out, f))
    hf = HiFont()
    n = 0
    seen = set()
    for name, _, pages in sheets:
        pix, (iw, ih), h, _ = parts[name]
        for page, role in pages:
            if (h, page) in seen:       # identical sheets (EVENT #11 = default page, ...)
                continue
            seen.add((h, page))
            layers = hires_layers(pix, page, hf, role)
            # the sheet as one upload, and (for multi-page sheets) this page uploaded on its own
            keys = [(h, iw, page * 256)]
            if iw > 64:
                blk = pix[:, page * 256:(page + 1) * 256]
                raw = (blk[:, 0::2] | (blk[:, 1::2] << 4)).astype(np.uint8).tobytes()
                keys.append((xxhash.xxh3_64_intdigest(raw), 64, 0))
            for ph, (layer, row) in pals.items():
                # The right page also carries the compact F1 terrain labels.
                for stp in (False, True):
                    img = colourise(layers[layer], layer, row, stp)
                    first = None
                    for kh, kw, kx in keys:
                        fn = "texupload-%s-%016X-%016X-%dx%d-%d-0-256x%d-P0-15.png" % (
                            "STP4" if stp else "P4", kh, ph, kw, ih, kx, ih)
                        if first is None:
                            img.save(os.path.join(out, fn), optimize=True)
                            first = fn
                        else:
                            shutil.copyfile(os.path.join(out, first), os.path.join(out, fn))
                        n += 1
    # Story scenes upload their right font page over half of the main font sheet;
    # with DuckStation's default (0 splits) the whole sheet stops being tracked.
    with open(os.path.join(os.path.dirname(out), "config.yaml"), "w", encoding="utf-8") as c:
        c.write("# Super Tokusatsu Taisen 2001 English: 4x font pack settings\n"
                "# The game overwrites half of its font sheet with a per-scene page;\n"
                "# allow the original upload to be split so it stays tracked.\n"
                "# DuckStation reads this option as a bool (true = 1 split), not a number.\n"
                "MaxVRAMWriteSplits: true\n")
    log("texture pack: %d files (%d palettes) -> %s" % (n, len(pals), out))
    return out


def preview(text, out_png):
    """Side by side: 1x font upscaled (nearest) vs the 4x replacement glyphs."""
    hf = HiFont()
    m = hf.meta
    codes = efont.encode_plain(text, m["encode"])
    z = np.load(os.path.join(ROOT, "work", "font", "efont_cells.npz"))
    W = sum(m["w_uni"][c - 320] if c < 782 else m["w_bi"][c - 782] for c in codes) + 8
    lo = np.zeros((16, W + 12), np.uint8)
    hi = np.zeros((16 * K, (W + 12) * K), np.uint8)
    x = 4
    for c in codes:
        if c < 782:
            i, w = c - 320, m["w_uni"][c - 320]
            cl, ch = z["uni"][i], hf.char(m["uni"][i])
        else:
            i, w = c - 782, m["w_bi"][c - 782]
            cl, ch = z["bi"][i], hf.string(m["bi"][i], 12)
        ch = shadow(ch)
        lo[:, x:x + w] = np.maximum(lo[:, x:x + w], cl[:, :w])
        reg = hi[:, x * K:(x + w) * K]
        hi[:, x * K:(x + w) * K] = np.where(ch[:, :w * K] >= 2, ch[:, :w * K], np.maximum(reg, ch[:, :w * K]))
        x += w
    pal = np.array([(24, 40, 48), (99, 99, 99), (165, 165, 165), (230, 230, 230)], np.uint8)
    a = Image.fromarray(pal[lo]).resize(((W + 12) * K, 16 * K), Image.NEAREST)
    b = Image.fromarray(pal[hi])
    im = Image.new("RGB", (a.width, a.height * 2 + 8), (0, 0, 0))
    im.paste(a, (0, 0))
    im.paste(b, (0, a.height + 8))
    im.save(out_png)


if __name__ == "__main__":
    if sys.argv[1] == "preview":
        preview(sys.argv[2], sys.argv[3])
    else:
        ver = sys.argv[1]
        fl = {x["path"]: x for x in json.load(open(os.path.join(
            ROOT, "work", "output", "STT2001_EN_v%s.bin.files.json" % ver)))}
        f = open(os.path.join(ROOT, "work", "output", "STT2001_EN_v%s.bin" % ver), "rb")

        def rd(name):
            x = fl[name]
            f.seek(x["lba"] * 2352)
            n = (x["size"] + 2047) // 2048
            return b"".join(f.read(2352)[24:2072] for _ in range(n))[:x["size"]]
        build({n: rd(n) for n in ("MAPMAIN.DAT", "BATTLE.DAT", "EVENT.DAT")}, ver)
