"""Small helpers for disassembling SLPS_028.63 and stage overlays."""
import struct
import os
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE = os.path.join(ROOT, "work", "source", "disc", "SLPS_028.63")
BASE = 0x80010000
md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 + CS_MODE_LITTLE_ENDIAN)
md.skipdata = True


def load():
    return open(EXE, "rb").read()


def off(addr):
    return addr - BASE + 0x800


def dis(data, addr, n=40, stop_jr=False):
    o = off(addr)
    out = []
    for ins in md.disasm(data[o:o + n * 4], addr):
        out.append("%08x: %-7s %s" % (ins.address, ins.mnemonic, ins.op_str))
        if stop_jr and ins.mnemonic == "jr" and "ra" in ins.op_str:
            break
    return out


def callers(data, target):
    word = 0x0C000000 | ((target >> 2) & 0x3FFFFFF)
    res = []
    for i in range(0x800, len(data) - 4, 4):
        if struct.unpack_from("<I", data, i)[0] == word:
            res.append(i - 0x800 + BASE)
    return res


def func_start(data, addr):
    """Walk back to the previous 'addiu sp,sp,-N'."""
    a = addr
    while a > BASE:
        w = struct.unpack_from("<I", data, off(a))[0]
        if (w & 0xFFFF0000) == 0x27BD0000 and (w & 0x8000):
            return a
        a -= 4
    return None
