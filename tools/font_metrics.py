"""Align Latin bodies to shared Skies-font guides without changing advances.

Coordinates are in the source's 4x raster. Ascenders and descenders keep
their distinct guides; accents retain their marks above the aligned body.
"""
import unicodedata
import numpy as np
from PIL import Image

STYLE = 'aligned-latin-v1'
CAP_TOP, X_TOP, BASELINE, DESCENDER = 8, 18, 45, 49
SHORT = 'acegmnopqrsuvwxyz'
DESCENDERS = 'gjpqyQ'


def bounds(cell):
    rows = np.flatnonzero((cell >= 2).any(axis=1))
    return (int(rows[0]), int(rows[-1])) if len(rows) else None


def band(out, source, first, last, top, bottom):
    if last < first or bottom < top:
        return
    part = Image.fromarray(source[first:last+1])
    out[top:bottom+1] = np.asarray(part.resize(
        (source.shape[1], bottom-top+1), Image.Resampling.NEAREST))


def align(ch, cell, reference=None):
    source = np.asarray(cell, dtype=np.uint8)
    out = source.copy()
    if ch in 'apq':
        out[:46] = 0
        band(out, source, 16, 45, X_TOP, BASELINE)
    elif ch == 'f':
        out[:] = 0
        band(out, source, 6, 45, CAP_TOP, BASELINE)
    elif ch == 'J':
        out[:] = 0
        band(out, source, 8, 47, CAP_TOP, BASELINE)
    elif ch.isascii() and ch.isdigit():
        # All ten solid digit contours already match the capital guides.
        # Remove only their varying antialias fringe outside those guides.
        out[:CAP_TOP] = 0
        out[BASELINE+1:] = 0
    elif reference is not None:
        base = unicodedata.normalize('NFD', ch)[0]
        first, last = bounds(reference)
        if base == 'i':
            # The accent replaces i's dot; align its lower stem separately.
            rows = np.flatnonzero((reference >= 2).any(axis=1))
            gaps = np.flatnonzero(np.diff(rows) > 1)
            if len(gaps):first = int(rows[gaps[-1]+1])
        top = CAP_TOP if base.isupper() else X_TOP
        out[:] = 0
        band(out, source, 0, first-1, 0, top-1)
        band(out, source, first, last, top, BASELINE)
        tail = np.flatnonzero(source[last+1:].any(axis=1))
        if len(tail):
            band(out, source, last+1, last+1+int(tail[-1]), BASELINE+1, DESCENDER)
    elif ch == '\u2026':
        # The GenEi fallback ellipsis otherwise floats above the Skies period.
        first, last = bounds(source)
        out[:] = 0
        band(out, source, first, last, 40, 47)

    if ch.isascii() and ch.isalpha():
        if ch.isupper() or ch in 'bdfhijkl':out[:CAP_TOP] = 0
        if ch in SHORT:out[:X_TOP] = 0
        if ch not in DESCENDERS:out[BASELINE+1:] = 0
    return out
