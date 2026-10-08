"""Write data back into the MODE2/2352 disc image (Form 1 sectors) with
correct EDC/ECC. Files keep their size and LBA (in-place patching).

    from discimage import Image
    img = Image(path)              # opened read/write
    img.write_file("SLPS_028.63", data)
    img.write_dat_entry("STAGE.DAT", 5, data)

python tools/discimage.py selftest   -> recomputes EDC/ECC of original sectors
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECTOR = 2352
FILES_JSON = os.path.join(ROOT, "work", "source", "disc_files.json")

EDC_LUT = []
for i in range(256):
    e = i
    for _ in range(8):
        e = (e >> 1) ^ (0xD8018001 if e & 1 else 0)
    EDC_LUT.append(e)
ECC_F = [0] * 256
ECC_B = [0] * 256
for i in range(256):
    j = ((i << 1) ^ (0x11D if i & 0x80 else 0)) & 0xFF
    ECC_F[i] = j
    ECC_B[i ^ j] = i


def edc(buf):
    e = 0
    for b in buf:
        e = (e >> 8) ^ EDC_LUT[(e ^ b) & 0xFF]
    return e


def _ecc_block(s, major_count, minor_count, major_mult, minor_inc, dest_off):
    size = major_count * minor_count
    out = bytearray(major_count * 2)
    for major in range(major_count):
        index = (major >> 1) * major_mult + (major & 1)
        a = b = 0
        for _ in range(minor_count):
            t = s[0xC + index]
            index += minor_inc
            if index >= size:
                index -= size
            a ^= t
            b ^= t
            a = ECC_F[a]
        a = ECC_B[ECC_F[a] ^ b]
        out[major] = a
        out[major + major_count] = a ^ b
    s[dest_off:dest_off + len(out)] = out


def fix_form1(sec):
    """sec: bytearray(2352) with header/subheader/data set. Fills EDC + ECC."""
    sec[2072:2076] = struct.pack("<I", edc(sec[16:2072]))
    hdr = bytes(sec[12:16])
    sec[12:16] = b"\0\0\0\0"
    _ecc_block(sec, 86, 24, 2, 86, 0x81C)
    _ecc_block(sec, 52, 43, 86, 88, 0x8C8)
    sec[12:16] = hdr
    return sec


class Image:
    def __init__(self, path):
        self.f = open(path, "r+b")
        self.files = {e["path"]: e for e in json.load(open(FILES_JSON))}

    def read_sector(self, lba):
        self.f.seek(lba * SECTOR)
        return bytearray(self.f.read(SECTOR))

    def write_user(self, lba, data):
        """Write 2048-byte chunks starting at lba (Form 1)."""
        for i in range(0, len(data), 2048):
            sec = self.read_sector(lba + i // 2048)
            if sec[18] & 0x20:
                raise ValueError("sector %d is Form 2" % (lba + i // 2048))
            chunk = data[i:i + 2048]
            sec[24:24 + len(chunk)] = chunk
            fix_form1(sec)
            self.f.seek((lba + i // 2048) * SECTOR)
            self.f.write(sec)

    def write_file(self, name, data):
        e = self.files[name]
        if len(data) > e["size"]:
            raise ValueError("%s grew: %d > %d" % (name, len(data), e["size"]))
        self.write_user(e["lba"], data)

    def write_dat_entry(self, dat, idx, data):
        e = self.files[dat]
        self.f.seek(e["lba"] * SECTOR + 24)
        head = self.f.read(2048)
        count = struct.unpack_from("<H", head, 0)[0]
        offs = struct.unpack_from("<%dH" % (count + 1), head, 2)
        cap = (offs[idx + 1] - offs[idx]) * 2048
        if len(data) > cap:
            raise ValueError("%s #%d grew: %d > %d" % (dat, idx, len(data), cap))
        self.write_user(e["lba"] + offs[idx], data)

    def close(self):
        self.f.close()


def selftest():
    src = os.path.join(ROOT, "Super Tokusatsu Taisen 2001 (Japan).bin")
    f = open(src, "rb")
    bad = 0
    for lba in (16, 24, 25, 1000, 214574, 245714):
        f.seek(lba * SECTOR)
        sec = bytearray(f.read(SECTOR))
        if sec[18] & 0x20:
            continue
        ref = bytes(sec)
        fix_form1(sec)
        ok = bytes(sec) == ref
        bad += not ok
        print("lba %d: %s" % (lba, "OK" if ok else "MISMATCH"))
    print("selftest", "passed" if not bad else "FAILED")


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
