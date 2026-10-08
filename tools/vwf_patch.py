"""VWF patch: rewrite the glyph-lookup routine (SLPS_028.63 @ 0x8004A7D8).

The original routine fills a GsSPRITE-like struct for one glyph:
  +0 attr=0, +8 w, +A h=16, +C tpage, +E u, +F v, +10 cx=0x30, +12 cy (CLUT row)
Every text drawer advances x by +8 (w), so per-glyph widths give a VWF
everywhere. The rewrite is shorter than the original (it uses divu instead of
magic multiplies), and the freed space holds the width table for the English
glyphs (codes VWF_FIRST .. VWF_FIRST+VWF_COUNT-1). Other codes keep 8/12.

Also writes the English glyphs into the font sheet (F0 layer, bits 0-1).
"""
import json
import os
import struct
import sys

import numpy as np
from keystone import Ks, KS_ARCH_MIPS, KS_MODE_MIPS32, KS_MODE_LITTLE_ENDIAN

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import vwf_font  # noqa: E402

FUNC = 0x8004A7D8
FUNC_END = 0x8004A954          # next function starts here
EXE_BASE = 0x80010000


def asm_routine(t_uni, t_bi, t_ex):
    """t_uni / t_bi: 12 thresholds each; width(code) = #thresholds <= code,
    for codes 320-445 and 782-1117. Other codes keep 8/12."""
    ks = Ks(KS_ARCH_MIPS, KS_MODE_MIPS32 + KS_MODE_LITTLE_ENDIAN)
    code_tmpl = """
    .set noreorder
    andi  $t0, $a1, 0xffff
    sltiu $v0, $t0, 320
    beqz  $v0, wide
    addiu $t1, $zero, 0x1c
    andi  $v0, $t0, 31
    sll   $v0, $v0, 3
    sb    $v0, 0xe($a0)
    srl   $v0, $t0, 5
    sll   $v0, $v0, 4
    sb    $v0, 0xf($a0)
    addiu $v1, $zero, 8
    b     common
    addiu $t2, $zero, 0xf0
wide:
    addiu $v0, $t0, -110
    addiu $v1, $zero, 336
    divu  $zero, $v0, $v1
    addiu $v1, $zero, 21
    mflo  $t3
    mfhi  $t4
    addu  $t1, $t1, $t3
    addiu $t2, $zero, 0xf0
    divu  $zero, $t4, $v1
    sltiu $v0, $t0, 782
    bnez  $v0, rowcol
    nop
    addiu $t1, $t1, -2
    sltiu $v0, $t0, 0x5ae
    beqz  $v0, rowcol
    nop
    addiu $t2, $zero, 0xf1
rowcol:
    mflo  $v0
    mfhi  $v1
    sll   $v0, $v0, 4
    sb    $v0, 0xf($a0)
    sll   $a2, $v1, 1
    addu  $a2, $a2, $v1
    sll   $a2, $a2, 2
    sb    $a2, 0xe($a0)
    addiu $v1, $zero, 12
    lui   $a2, TABHI
    addiu $a2, $a2, TABLO
    addiu $t3, $zero, 12
    addiu $v0, $t0, -320
    sltiu $v0, $v0, 126
    bnez  $v0, vwf
    addiu $v0, $t0, -782
    sltiu $v0, $v0, 336
    bnez  $v0, vwf
    addiu $a2, $a2, 24
    addiu $v0, $t0, -446
    sltiu $v0, $v0, 336
    beqz  $v0, common
    addiu $a2, $a2, 24
    addiu $t3, $zero, 24
vwf:
    move  $v1, $zero
vloop:
    lhu   $t4, 0($a2)
    addiu $a2, $a2, 2
    sltu  $t4, $t0, $t4
    xori  $t4, $t4, 1
    addiu $t3, $t3, -1
    bnez  $t3, vloop
    addu  $v1, $v1, $t4
common:
    sh    $v1, 8($a0)
    sh    $t1, 0xc($a0)
    sh    $t2, 0x12($a0)
    addiu $v0, $zero, 0x30
    sh    $v0, 0x10($a0)
    addiu $v0, $zero, 0x10
    sh    $v0, 0xa($a0)
    jr    $ra
    sw    $zero, 0($a0)
"""

    def build(table_addr):
        hi = ((table_addr + 0x8000) >> 16) & 0xFFFF
        lo = table_addr & 0xFFFF
        lo_s = lo - 0x10000 if lo >= 0x8000 else lo
        src = code_tmpl.replace("TABHI", "0x%x" % hi).replace("TABLO", str(lo_s))
        enc, _ = ks.asm(src, FUNC)
        return bytes(enc)

    code = build(FUNC + 0x400)
    table_addr = FUNC + ((len(code) + 3) & ~3)
    code = build(table_addr)
    assert len(t_uni) == 12 and len(t_bi) == 12 and len(t_ex) == 24
    tab = struct.pack("<48H", *(list(t_uni) + list(t_bi) + list(t_ex)))
    blob = code + bytes((table_addr - FUNC) - len(code)) + tab
    room = FUNC_END - FUNC
    if len(blob) > room:
        raise SystemExit("routine too big: %d > %d" % (len(blob), room))
    blob += bytes(room - len(blob))
    return blob, table_addr


def patch_exe(exe, t_uni, t_bi, t_ex):
    exe = bytearray(exe)
    blob, tab = asm_routine(t_uni, t_bi, t_ex)
    o = FUNC - EXE_BASE + 0x800
    exe[o:o + len(blob)] = blob
    return bytes(exe), tab


def patch_font_tim(tim, cells):
    """Write VWF cells into the low 2 bits (F0 layer) of the font TIM."""
    tim = bytearray(tim)
    blen = struct.unpack_from("<I", tim, 8)[0]
    pos = 8 + blen
    _, _, _, iw, ih = struct.unpack_from("<IHHHH", tim, pos)
    base = pos + 12
    row_bytes = iw * 2
    for i, cell in enumerate(cells):
        code = vwf_font.VWF_FIRST + i
        a = code - 110
        page, r = divmod(a, 336)
        assert page == 0 and code < 782
        x0, y0 = page * 256 + (r % 21) * 12, (r // 21) * 16
        for y in range(16):
            for x in range(12):
                px = x0 + x
                off = base + (y0 + y) * row_bytes + px // 2
                b = tim[off]
                sh = 0 if px % 2 == 0 else 4
                nib = (b >> sh) & 15
                nib = (nib & 0xC) | int(cell[y, x])
                tim[off] = (b & ~(15 << sh) & 0xFF) | (nib << sh)
    return bytes(tim)


if __name__ == "__main__":
    m = json.load(open(os.path.join(ROOT, "work", "font", "efont.json"), encoding="utf-8"))
    blob, tab = asm_routine(m["t_uni"], m["t_bi"], m["t_ex"])
    from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN
    md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 + CS_MODE_LITTLE_ENDIAN)
    for ins in md.disasm(blob[:tab - FUNC], FUNC):
        print("%08x: %-7s %s" % (ins.address, ins.mnemonic, ins.op_str))
    print("tables at %08x, %d of %d bytes" % (tab, tab - FUNC + 96, FUNC_END - FUNC))
