"""Unpack the *.DAT sector archives.

Format (little endian):
  u16 count, then count+1 u16 sector offsets (2048-byte sectors).
  Entry i spans sectors [off[i], off[i+1]).  The header sits in sector 0
  (may span more sectors when the table is large).

Usage: python tools/dat_archive.py <file.DAT> [outdir]
Writes <outdir>/<NAME>/NNNN.bin and an index.json.
"""
import json
import os
import struct
import sys

SEC = 2048


def read_index(data):
    count = struct.unpack_from("<H", data, 0)[0]
    offs = struct.unpack_from("<%dH" % (count + 1), data, 2)
    ents = []
    for i in range(count):
        a, b = offs[i], offs[i + 1]
        ents.append((i, a * SEC, (b - a) * SEC))
    return ents


def main():
    src = sys.argv[1]
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    outroot = sys.argv[2] if len(sys.argv) > 2 else os.path.join(root, "work", "source", "unpacked")
    data = open(src, "rb").read()
    name = os.path.splitext(os.path.basename(src))[0]
    out = os.path.join(outroot, name)
    os.makedirs(out, exist_ok=True)
    idx = []
    for i, off, size in read_index(data):
        with open(os.path.join(out, "%04d.bin" % i), "wb") as o:
            o.write(data[off:off + size])
        idx.append({"id": i, "offset": off, "size": size})
    json.dump(idx, open(os.path.join(out, "index.json"), "w"), indent=0)
    print("%s: %d entries, last ends at 0x%X of 0x%X" % (name, len(idx), idx[-1]["offset"] + idx[-1]["size"], len(data)))


if __name__ == "__main__":
    main()
