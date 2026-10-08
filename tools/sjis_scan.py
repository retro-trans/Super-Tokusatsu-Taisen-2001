"""Scan binary files for runs of Shift-JIS text.

Usage: python tools/sjis_scan.py <file> [--min N] [--out tsv]

A run is a sequence of valid double-byte SJIS characters (optionally mixed
with printable ASCII / half-width kana) containing at least N full-width
characters. Prints offset, length and decoded text. Use for discovery only;
real extraction goes through format-specific tools.
"""
import argparse
import sys


def is_lead(b):
    return 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF


def is_trail(b):
    return 0x40 <= b <= 0xFC and b != 0x7F


def scan(data, min_wide=3, allow_ascii=True):
    i, n = 0, len(data)
    while i < n:
        start, wide, j = i, 0, i
        while j < n:
            b = data[j]
            if is_lead(b) and j + 1 < n and is_trail(data[j + 1]):
                try:
                    data[j:j + 2].decode("cp932")
                except UnicodeDecodeError:
                    break
                wide += 1
                j += 2
            elif allow_ascii and (0x20 <= b < 0x7F or 0xA1 <= b <= 0xDF):
                j += 1
            else:
                break
        if wide >= min_wide:
            yield start, data[start:j]
            i = j
        else:
            i = start + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--min", type=int, default=3)
    ap.add_argument("--out")
    ap.add_argument("--start", type=lambda s: int(s, 0), default=0)
    ap.add_argument("--end", type=lambda s: int(s, 0), default=None)
    a = ap.parse_args()
    data = open(a.file, "rb").read()[a.start:a.end]
    out = open(a.out, "w", encoding="utf-8") if a.out else sys.stdout
    count = 0
    for off, raw in scan(data, a.min):
        out.write("%08X\t%d\t%s\n" % (off + a.start, len(raw), raw.decode("cp932", "replace")))
        count += 1
    sys.stderr.write("%d runs\n" % count)


if __name__ == "__main__":
    main()
