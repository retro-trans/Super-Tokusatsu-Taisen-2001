"""Widen the map command menu and keep its frame inside the native screen.

Run without flags for a dry run. The normal builder calls patch_exe().
Names, command flags, option order, selection logic and submenu sizes remain
unchanged. Only the primary menu's frame and highlight become wider.
"""
import hashlib
import struct

from keystone import Ks, KS_ARCH_MIPS, KS_MODE_MIPS32, KS_MODE_LITTLE_ENDIAN

import mips

MENU = 0x800A7204
START, END = 0x8003D988, 0x8003DA4C
TEXT_WIDTH = 128
DELTA = TEXT_WIDTH - 64


def frame_code():
    # Same native vertical placement, frame height, depth and renderer call.
    # The caller already adjusts the highlight width for its special +16 case;
    # retain its a2 frame adjustment without counting that width twice.
    code = '''
    .set noreorder
    addiu $sp,$sp,-0x20
    sw $ra,0x18($sp)
    addiu $a1,$a1,-16
    sll $a1,$a1,16
    sra $a1,$a1,16
    lh $t1,4($a0)
    slti $v0,$a1,8
    beqz $v0,min_y
    nop
    addiu $a1,$zero,8
min_y:
    addiu $t1,$t1,2
    sll $t1,$t1,4
    addu $v0,$t1,$a1
    addiu $v0,$v0,8
    slti $v0,$v0,241
    bnez $v0,max_y
    addiu $v0,$zero,232
    subu $a1,$v0,$t1
max_y:
    addiu $a1,$a1,16
    sh $a1,0xc($a0)
    addiu $a1,$a1,-12
    sw $a1,0x10($sp)
    addiu $a1,$a2,96
    addiu $a2,$t1,-8
    lh $a3,0xa($a0)
    lui $t0,0x800a
    ori $t0,$t0,0x7204
    bne $a0,$t0,draw
    nop
    addiu $a1,$a1,%(delta)d
    addiu $v0,$zero,328
    subu $v0,$v0,$a1
    slt $t1,$v0,$a3
    beqz $t1,left
    nop
    move $a3,$v0
left:
    slti $t1,$a3,24
    beqz $t1,x_ready
    nop
    addiu $a3,$zero,24
x_ready:
    sh $a3,0xa($a0)
draw:
    addiu $a3,$a3,-16
    jal 0x80041f04
    addiu $a0,$zero,10
    lw $ra,0x18($sp)
    nop
    jr $ra
    addiu $sp,$sp,0x20
    ''' % {'delta': DELTA}
    raw = bytes(Ks(KS_ARCH_MIPS, KS_MODE_MIPS32 | KS_MODE_LITTLE_ENDIAN).asm(code, START)[0])
    assert len(raw) <= END-START, (len(raw), END-START)
    return raw + bytes(END-START-len(raw))


def patch_exe(exe):
    original = mips.load()
    a, b = mips.off(START), mips.off(END)
    assert hashlib.sha256(original[a:b]).hexdigest() == '7b6a4510f878affd0788b409544a953502738a7cbbb8c532d09b1a19570a92a2'
    assert exe[a:b] == original[a:b], 'unexpected map-menu frame code'
    offset = mips.off(MENU)+14
    assert struct.unpack_from('<H', exe, offset)[0] == 64, 'unexpected map-menu highlight width'
    out = bytearray(exe)
    struct.pack_into('<H', out, offset, TEXT_WIDTH)
    out[a:b] = frame_code()
    return bytes(out)


if __name__ == '__main__':
    patch_exe(mips.load())
    print('Dry run: primary command menu text/highlight width 64 -> 128 pixels; frame 96 -> 160 pixels.')
    print('Keep full command names; clamp this frame to x=8..312. Other menu frames retain their dimensions.')
    print('Frame routine uses its existing %d-byte allocation; no files written.' % (END-START))
