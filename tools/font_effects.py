"""Flat antialiased ink and (+1,+1) shadow, inside fixed advances.

The Skies source masks remain untouched. Five private CLUT rows occupy the
font TIMs' existing zero-filled rows 10..14; native icons retain rows 0..9.
"""
import numpy as np

STYLE = 'flat-shadow-v2'
LEGACY_STYLE = 'getter-gradient-shadow-v1'
FIRST_ROW = 10
PALETTE_COUNT = 5
TOP, BOTTOM = 2, 12
BOTTOM_LIGHT = 0.72
SHADOW_RGB = (32, 32, 32)


def enabled(meta):
    return meta.get('font_effects') in (STYLE, LEGACY_STYLE)


def positioned(cell, width, scale):
    """Recover the source's left bearing as room for a one-pixel shadow.

    Keep every source ink sample and the original advance. Narrow punctuation
    and fallback marks may have less bearing; clip only their trailing shadow.
    """
    source = np.asarray(cell, dtype=np.uint8)[:, :width].copy()
    cols = np.flatnonzero(source.max(0))
    shift = min(scale, int(cols[0])) if len(cols) else 0
    if shift:
        source[:, :-shift] = source[:, shift:]
        source[:, -shift:] = 0
    return source


def native(cell, width, scale, gradient=False):
    source = positioned(cell, width, scale)
    ink = source > 0
    shade = np.zeros_like(ink)
    shade[scale:, scale:] = ink[:-scale, :-scale]
    fill=source
    if gradient:
        rows = np.arange(len(source))[:, None] / scale
        fill=np.where(source==1,1,np.where(rows < (TOP+BOTTOM)/2,3,2))
    result = np.where(ink,fill,np.where(shade,1,0)).astype(np.uint8)
    out = np.zeros_like(cell)
    out[:, :width] = result
    return out


def rgb15(rgb):
    values = [int(round(v * 31 / 255)) for v in rgb]
    return values[0] | values[1] << 5 | values[2] << 10


def private_palettes(clut):
    rows = []
    for role in range(PALETTE_COUNT):
        raw = clut[(role * 2 + 1) * 16 + 12] & 0x7fff
        foreground = tuple(((raw >> s) & 31) * 255 / 31 for s in (0, 5, 10))
        levels = [0, rgb15(SHADOW_RGB),
                  rgb15(tuple(c * BOTTOM_LIGHT for c in foreground)), raw]
        rows.append([levels[i // 4] for i in range(16)])
    return rows
