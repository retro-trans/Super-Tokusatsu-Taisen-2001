"""Full turn label and compact number field in the native turn announcement.

The numeric drawer's limit gets a private high-bit flag at this one caller.
Normal fields keep their original right alignment. The flagged field removes
unused leading digit slots, retaining the original four-digit capacity.
Run without arguments for an in-memory dry run; builds call patch_exe().
"""
import struct

from keystone import Ks, KS_ARCH_MIPS, KS_MODE_MIPS32, KS_MODE_LITTLE_ENDIAN

BASE = 0x80010000
DRAW = 0x8004CCF0
DRAW_END = 0x8004CE30
LABEL_X = 0x80019EBC
NUMBER_X = 0x80019ED8
NUMBER_LIMIT = 0x80019EF0


def offset(address):
    return address - BASE + 0x800


def number_drawer():
    ks = Ks(KS_ARCH_MIPS, KS_MODE_MIPS32 + KS_MODE_LITTLE_ENDIAN)
    code = """
    .set noreorder
    addiu $sp, $sp, -0x40
    sw $s0, 0x18($sp)
    sw $s1, 0x1c($sp)
    sw $s2, 0x20($sp)
    sw $s3, 0x24($sp)
    sw $s4, 0x28($sp)
    sw $s5, 0x2c($sp)
    sw $s6, 0x30($sp)
    sw $s7, 0x34($sp)
    sw $ra, 0x38($sp)
    lw $s2, 0x50($sp)
    lw $s4, 0x54($sp)
    lw $s6, 0x58($sp)
    move $s7, $a0
    andi $s5, $a3, 0xff
    sll $s5, $s5, 1
    move $s3, $zero
    andi $t0, $s4, 0xff
    xori $t0, $t0, 0x84
    bnez $t0, aligned
    andi $s4, $s4, 0xff
    addiu $s4, $zero, 4
    sltiu $t0, $s2, 10
    sltiu $t1, $s2, 100
    sltiu $t2, $s2, 1000
    addu $t0, $t0, $t1
    addu $t0, $t0, $t2
    sll $t0, $t0, 3
    subu $a1, $a1, $t0
aligned:
    addiu $t0, $s4, -1
    sll $t0, $t0, 3
    addu $a1, $a1, $t0
    sh $a1, 0x10($sp)
    beqz $s4, done
    sh $a2, 0x12($sp)
loop:
    addiu $t0, $zero, 10
    div $zero, $s2, $t0
    andi $a0, $s7, 0xff
    sll $a1, $s6, 16
    mfhi $s0
    mflo $s2
    jal 0x8004c0ec
    sra $a1, $a1, 16
    move $s1, $v0
    move $a0, $s1
    addiu $s0, $s0, 1
    jal 0x8004a7d8
    andi $a1, $s0, 0xffff
    move $a0, $s1
    addiu $a1, $sp, 0x10
    addiu $a2, $sp, 0x12
    addiu $a3, $zero, -8
    lui $v0, 0x1000
    jal 0x8004d834
    sw $v0, 0($s1)
    lhu $v0, 0x12($s1)
    addiu $s3, $s3, 1
    addu $v0, $v0, $s5
    blez $s2, done
    sh $v0, 0x12($s1)
    slt $v0, $s3, $s4
    bnez $v0, loop
    nop
done:
    lh $v0, 0x10($sp)
    lw $ra, 0x38($sp)
    lw $s0, 0x18($sp)
    lw $s1, 0x1c($sp)
    lw $s2, 0x20($sp)
    lw $s3, 0x24($sp)
    lw $s4, 0x28($sp)
    lw $s5, 0x2c($sp)
    lw $s6, 0x30($sp)
    lw $s7, 0x34($sp)
    jr $ra
    addiu $sp, $sp, 0x40
    """
    data = bytes(ks.asm(code, DRAW)[0])
    assert len(data) <= DRAW_END - DRAW, len(data)
    return data + bytes(DRAW_END - DRAW - len(data))


def patch_exe(exe):
    exe = bytearray(exe)
    expected = {LABEL_X: 0x24050080, NUMBER_X: 0x240500A0,
                NUMBER_LIMIT: 0x24020004, DRAW: 0x27BDFFC0}
    for address, word in expected.items():
        assert struct.unpack_from('<I', exe, offset(address))[0] == word, hex(address)
    # 30px label + 6px space + up to four 8px digits fits the 96px popup.
    struct.pack_into('<I', exe, offset(LABEL_X), 0x2405007C)  # x=124
    struct.pack_into('<I', exe, offset(NUMBER_X), 0x24450006)  # x=label end+6
    struct.pack_into('<I', exe, offset(NUMBER_LIMIT), 0x24020084)
    exe[offset(DRAW):offset(DRAW_END)] = number_drawer()
    return bytes(exe)


if __name__ == '__main__':
    import mips
    patched = patch_exe(mips.load())
    print('Dry run: label at x=124, number at label end+6; max 4 digits.')
    print('Numeric drawer: %d bytes, original allocation %d bytes.' %
          (len(number_drawer()), DRAW_END-DRAW))
    for n in (1, 9, 10, 99, 100, 999, 1000, 9999):
        digits = len(str(n))
        print('Turn %d: label [124,154), number [160,%d)' % (n, 160+digits*8))
