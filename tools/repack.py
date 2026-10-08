"""Rebuild DAT archives and re-lay out the disc so files may grow.

dat_pack(entries)            -> bytes of a DAT archive (u16 count + u16 sector offsets)
dat_entries(path)            -> list of entry bytes (trailing sector padding kept)
rebuild(src_bin, out_bin, new_files)
    new_files: {"STAGE.DAT": bytes, ...}. Files keep their order on disc.
    Files before STAGE.DAT keep their LBA (MOVIE.STR / VORTEX.XA are never moved).
    From STAGE.DAT on, files are packed back to back; DUMMY.DAT (padding at the
    end of the disc) shrinks to absorb any growth. Root directory records are
    updated. Every written sector gets a fresh header, EDC and ECC.
"""
import json
import os
import struct
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import discimage  # noqa: E402

SECTOR = 2352
FIXED = ("SYSTEM.CNF", "SLPS_028.63", "MOVIE.STR", "VORTEX.XA")


def dat_entries(buf):
    count = struct.unpack_from("<H", buf, 0)[0]
    offs = struct.unpack_from("<%dH" % (count + 1), buf, 2)
    return [buf[offs[i] * 2048:offs[i + 1] * 2048] for i in range(count)]


def dat_pack(entries):
    count = len(entries)
    head_len = 2 + 2 * (count + 1)
    head_secs = (head_len + 2047) // 2048
    offs, pos = [], head_secs
    body = bytearray()
    for e in entries:
        offs.append(pos)
        pad = (-len(e)) % 2048
        body += e + bytes(pad)
        pos += (len(e) + pad) // 2048
    offs.append(pos)
    if pos > 0xFFFF:
        raise ValueError("archive too big")
    head = struct.pack("<H", count) + struct.pack("<%dH" % (count + 1), *offs)
    head += bytes(head_secs * 2048 - len(head))
    return bytes(head) + bytes(body)


def bcd(n):
    return ((n // 10) << 4) | (n % 10)


def header(lba):
    a = lba + 150
    m, s, f = a // 4500, (a // 75) % 60, a % 75
    return bytes([0, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 0, bcd(m), bcd(s), bcd(f), 2])


def make_sector(lba, data, last):
    sec = bytearray(SECTOR)
    sec[0:16] = header(lba)
    sub = bytes([0, 0, 0x89 if last else 0x08, 0])
    sec[16:20] = sub
    sec[20:24] = sub
    sec[24:24 + len(data)] = data
    discimage.fix_form1(sec)
    return bytes(sec)


def read_dir(f, lba, size):
    f.seek(lba * SECTOR)
    data = b"".join(f.read(SECTOR)[24:24 + 2048] for _ in range((size + 2047) // 2048))
    recs, pos = [], 0
    while pos < len(data):
        ln = data[pos]
        if ln == 0:
            pos = (pos // 2048 + 1) * 2048
            continue
        name = data[pos + 33:pos + 33 + data[pos + 32]]
        recs.append((pos, ln, name))
        pos += ln
    return bytearray(data), recs


def rebuild(src_bin, out_bin, new_files, log=print):
    import shutil
    if src_bin != out_bin:
        shutil.copyfile(src_bin, out_bin)
    f = open(out_bin, "r+b")
    f.seek(16 * SECTOR)
    pvd = f.read(SECTOR)[24:24 + 2048]
    vol = struct.unpack_from("<I", pvd, 80)[0]
    rlba = struct.unpack_from("<I", pvd, 156 + 2)[0]
    rsize = struct.unpack_from("<I", pvd, 156 + 10)[0]
    dirdata, recs = read_dir(f, rlba, rsize)
    files = []
    for pos, ln, name in recs:
        if name in (b"\0", b"\1"):
            continue
        n = name.decode().split(";")[0]
        files.append({"name": n, "pos": pos, "lba": struct.unpack_from("<I", dirdata, pos + 2)[0],
                      "size": struct.unpack_from("<I", dirdata, pos + 10)[0]})
    files.sort(key=lambda e: e["lba"])
    src = open(src_bin, "rb")
    cursor = None
    plan = []
    for e in files:
        if e["name"] in FIXED:
            if e["name"] in new_files and len(new_files[e["name"]]) > e["size"]:
                raise ValueError("%s cannot grow" % e["name"])
            plan.append((e, e["lba"], len(new_files.get(e["name"], b"")) or e["size"]))
            continue
        if cursor is None:
            cursor = e["lba"]
        size = len(new_files[e["name"]]) if e["name"] in new_files else e["size"]
        if e["name"] == "DUMMY.DAT":
            end = e["lba"] + (e["size"] + 2047) // 2048   # keep the post-gap after DUMMY.DAT
            size = max(0, (end - cursor)) * 2048
        plan.append((e, cursor, size))
        cursor += (size + 2047) // 2048
    dummy = [e for e in files if e["name"] == "DUMMY.DAT"][0]
    if cursor > dummy["lba"] + (dummy["size"] + 2047) // 2048:
        raise ValueError("disc full: files run past the end of DUMMY.DAT")
    for e, lba, size in plan:
        changed = e["name"] in new_files
        moved = lba != e["lba"]
        if e["name"] in FIXED and not changed:
            continue
        nsec = (size + 2047) // 2048
        log("write %-12s lba %6d -> %6d  %9d bytes%s" % (e["name"], e["lba"], lba, size, " (new)" if changed else ""))
        f.seek(lba * SECTOR)
        out = bytearray()
        # EDC/ECC of mode 2 form 1 sectors do not cover the address, so moved
        # sectors only need a new header, and zero sectors can be reused.
        zero_mid = make_sector(0, bytes(2048), False)
        zero_last = make_sector(0, bytes(2048), True)
        for i in range(nsec):
            if e["name"] == "DUMMY.DAT":
                sec = zero_last if i == nsec - 1 else zero_mid
            elif changed:
                sec = make_sector(lba + i, new_files[e["name"]][i * 2048:(i + 1) * 2048], i == nsec - 1)
            else:
                src.seek((e["lba"] + i) * SECTOR)
                sec = src.read(SECTOR)
            out += header(lba + i) + sec[16:]
            if len(out) >= 4 * 1024 * 1024:
                f.write(out)
                out = bytearray()
        f.write(out)
        struct.pack_into("<I", dirdata, e["pos"] + 2, lba)
        struct.pack_into(">I", dirdata, e["pos"] + 6, lba)
        struct.pack_into("<I", dirdata, e["pos"] + 10, size)
        struct.pack_into(">I", dirdata, e["pos"] + 14, size)
    for i in range((rsize + 2047) // 2048):
        f.seek((rlba + i) * SECTOR)
        sec = bytearray(f.read(SECTOR))
        sec[24:24 + 2048] = dirdata[i * 2048:(i + 1) * 2048]
        discimage.fix_form1(sec)
        f.seek((rlba + i) * SECTOR)
        f.write(sec)
    f.close()
    # refresh the file table used by discimage
    json.dump([{"path": e["name"], "lba": lba, "size": size} for e, lba, size in plan],
              open(out_bin + ".files.json", "w"), indent=0)
    return plan


if __name__ == "__main__":
    # self test: repack STAGE.DAT from its own entries and rebuild
    src = os.path.join(ROOT, "Super Tokusatsu Taisen 2001 (Japan).bin")
    d = open(os.path.join(ROOT, "work", "source", "disc", "STAGE.DAT"), "rb").read()
    print("repack identical:", dat_pack(dat_entries(d)) == d)
