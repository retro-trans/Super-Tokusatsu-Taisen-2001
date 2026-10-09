"""Adjust the shared title-card sprite commands, without changing script size.

Opcode 57 makes a texture sprite; opcode 59 positions it. Original cards
use sprite 28 for the prefix, 26/27 for digits and 29 for the suffix.
The exact texture-page/CLUT/UV signature identifies the shared card routine.
This runs before dialogue insertion, so both raw and compressed script copies
receive the same fixed-size changes and existing relative branches stay valid.
"""
import struct

PREFIX = struct.pack("<10H", 57, 28, 704, 256, 0, 500, 16, 104, 40, 128)
SUFFIX = struct.pack("<10H", 57, 29, 704, 256, 0, 500, 40, 104, 64, 128)


def patch_script(data):
    if PREFIX not in data:
        return data, 0
    out = bytearray(data)
    starts = [i for i in range(0, len(data) - 19, 2) if data[i:i+20] == PREFIX]
    for start in starts:
        # All shared routines end within 2 KiB. Stop after their sprite-30
        # positioning command (the title); do not inspect dialogue payloads.
        end = min(start + 2048, len(data) - 20)
        for off in range(start, end, 2):
            rec = struct.unpack_from("<10H", data, off)
            if data[off:off+20] == PREFIX:
                struct.pack_into("<2H", out, off+12, 0, 104)
                struct.pack_into("<H", out, off+16, 52)
            elif data[off:off+20] == SUFFIX:
                # A 1px blank sample parked clear of the header. The original
                # black texels are opaque, so a wide suffix would erase digits.
                struct.pack_into("<H", out, off+4, 576)
                struct.pack_into("<4H", out, off+12, 240, 104, 240, 104)
            elif rec[:6] in ((57, 26, 576, 256, 0, 500), (57, 27, 576, 256, 0, 500)) and rec[7] == 104 and rec[9] == 128 and rec[8]-rec[6] == 24:
                # Tight 12px numeral cells; quads never overlap or cover the
                # preceding digit with their opaque black background.
                struct.pack_into("<H", out, off+12, rec[6]+6)
                struct.pack_into("<H", out, off+16, rec[8]-6)
            elif rec[0] == 59 and rec[1] in (26, 27, 28, 29) and rec[3] in (68, 69):
                x = rec[2]
                if rec[1] == 28 and x in (112, 124):
                    struct.pack_into("<2H", out, off+4, 116 if x == 112 else 122, 68)
                elif rec[1] in (26, 27) and x in (136, 148, 160):
                    struct.pack_into("<H", out, off+4, {136: 174, 148: 180, 160: 186}[x])
                elif rec[1] == 29:
                    struct.pack_into("<H", out, off+4, 220)
            elif rec[0] == 59 and rec[1] == 30:
                break
    return bytes(out), len(starts)


if __name__ == "__main__":
    from pathlib import Path
    total = 0
    for p in sorted((Path(__file__).resolve().parents[1] / "work/source/unpacked/STAGE").glob("*.bin")):
        before = p.read_bytes()
        after, n = patch_script(before)
        if n:
            print(p.name, n, "routines,", sum(a != b for a, b in zip(before, after)), "changed bytes")
            total += n
    print(total, "card routines checked; no files written")
