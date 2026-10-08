"""Extract every file from the PS1 MODE2/2352 disc image.

Usage: python tools/extract_iso.py [bin] [outdir]

Form 1 sectors contribute their 2048-byte user data. Files containing
Form 2 sectors (XA audio / STR video) are written as raw 2352-byte
sectors with a .raw2352 suffix so nothing is lost.
Also writes work/source/disc_files.json (LBA, size, form2 flag).
"""
import json
import os
import struct
import sys

SECTOR = 2352
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_BIN = os.path.join(ROOT, "Super Tokusatsu Taisen 2001 (Japan).bin")
DEFAULT_OUT = os.path.join(ROOT, "work", "source", "disc")


class Disc:
    def __init__(self, path):
        self.f = open(path, "rb")

    def raw(self, lba):
        self.f.seek(lba * SECTOR)
        return self.f.read(SECTOR)

    def user(self, lba):
        return self.raw(lba)[24:24 + 2048]

    def is_form2(self, lba):
        return bool(self.raw(lba)[18] & 0x20)


def parse_dir(disc, lba, size, path, out):
    data = b"".join(disc.user(lba + i) for i in range((size + 2047) // 2048))
    pos = 0
    while pos < len(data):
        ln = data[pos]
        if ln == 0:
            pos = (pos // 2048 + 1) * 2048
            continue
        rec = data[pos:pos + ln]
        ext = struct.unpack_from("<I", rec, 2)[0]
        dsize = struct.unpack_from("<I", rec, 10)[0]
        flags = rec[25]
        nlen = rec[32]
        name = rec[33:33 + nlen]
        pos += ln
        if name in (b"\x00", b"\x01"):
            continue
        name = name.decode("ascii", "replace").split(";")[0]
        full = path + "/" + name if path else name
        if flags & 2:
            parse_dir(disc, ext, dsize, full, out)
        else:
            out.append({"path": full, "lba": ext, "size": dsize})


def main():
    bin_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BIN
    out_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT
    disc = Disc(bin_path)
    pvd = disc.user(16)
    assert pvd[1:6] == b"CD001", "no ISO9660 PVD"
    root = pvd[156:156 + 34]
    files = []
    parse_dir(disc, struct.unpack_from("<I", root, 2)[0],
              struct.unpack_from("<I", root, 10)[0], "", files)
    for fe in files:
        nsec = (fe["size"] + 2047) // 2048
        form2 = any(disc.is_form2(fe["lba"] + i) for i in range(min(nsec, 16)))
        fe["form2"] = form2
        dst = os.path.join(out_dir, fe["path"].replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst + (".raw2352" if form2 else ""), "wb") as o:
            if form2:
                # ISO size for XA files is often n*2048 of n raw sectors
                for i in range(nsec):
                    o.write(disc.raw(fe["lba"] + i))
            else:
                left = fe["size"]
                for i in range(nsec):
                    chunk = disc.user(fe["lba"] + i)[:min(2048, left)]
                    o.write(chunk)
                    left -= len(chunk)
        print("%-40s lba=%7d size=%10d%s" % (fe["path"], fe["lba"], fe["size"],
                                              " [XA/form2]" if form2 else ""))
    with open(os.path.join(os.path.dirname(out_dir), "disc_files.json"), "w") as o:
        json.dump(files, o, indent=1)


if __name__ == "__main__":
    main()
