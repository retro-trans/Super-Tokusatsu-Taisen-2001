"""Fit Intermission menu captions and compose a complete stage-clear banner.

The native banner overwrote two fixed Japanese character slots with digits.
Append digits instead; retain the full title and abbreviate the completion
label for long captions. No font cells, gameplay values or menus are changed.
Run without flags for an in-memory dry run.
"""
import struct
from keystone import Ks,KS_ARCH_MIPS,KS_MODE_MIPS32,KS_MODE_LITTLE_ENDIAN
import insert

START,END=0x8006F8AC,0x8006F9CC
POSITIONS=[(0xA35D6,244,242),(0xA35F6,212,204),(0xA3606,280,270)]
CALLER=[(0x80070D1C,0x27BDFFA8,0x27BDFF58),
        (0x80070D20,0xAFBF0050,0xAFBF00A0),
        (0x80070D58,0x8FBF0050,0x8FBF00A0),
        (0x80070D64,0x27BD0058,0x27BD00A8)]
TEXT={'U21238':'<c3>Unit</c>','U21239':'<c3>Wpn</c>','U21193':' cleared'}


def patch_database(data):
    # These two entries are shared suffixes, without unique translation UIDs.
    # Give their table indices dedicated short labels without changing other text.
    out=bytearray(data)
    for index,label in ((0xD89,'Grow'),(0xD8A,'Upg.')):
        assert len(out)<0x10000
        struct.pack_into('<H',out,index*2,len(out))
        words=insert.encode_line_tokens(insert.TOKEN.findall(label),{})+[0xFFFE]
        out+=struct.pack('<%dH'%len(words),*words)
    return bytes(out)+bytes((-len(out))%4)


def off(address):
    return address-0x80010000+0x800


def compose_code():
    colon=insert.EF['encode'][':']
    space=insert.EF['encode'][' ']
    short=insert.encode_line_tokens(insert.TOKEN.findall(' Clr.'),{})
    assert len(short)==4
    code='''
    .set noreorder
    addiu $sp,$sp,-0x30
    sw $ra,0x2c($sp)
    sw $s0,0x28($sp)
    sw $s1,0x24($sp)
    sw $s2,0x20($sp)
    move $s1,$a0
    andi $s2,$a1,0xff
    andi $s0,$a2,0xff
    jal 0x8003c578
    addiu $a0,$zero,0xcef
    move $a0,$s1
    jal 0x8004d4b8
    move $a1,$v0
    beqz $s0,unknown
    addiu $t1,$sp,0x10
    addiu $t0,$zero,10
    div $zero,$s0,$t0
    mflo $t2
    mfhi $t3
    beqz $t2,ones
    addiu $t2,$t2,1
    sh $t2,0($t1)
    addiu $t1,$t1,2
ones:
    addiu $t3,$t3,1
    sh $t3,0($t1)
    ori $t0,$zero,0xfffe
    sh $t0,2($t1)
    b number
    addiu $a1,$sp,0x10
unknown:
    jal 0x8003c578
    addiu $a0,$zero,0xcf0
    move $a1,$v0
number:
    jal 0x8004d504
    move $a0,$s1
    lui $t0,%(delimiter_hi)d
    ori $t0,$t0,%(colon)d
    sw $t0,0x10($sp)
    ori $t0,$zero,0xfffe
    sh $t0,0x14($sp)
    move $a0,$s1
    jal 0x8004d504
    addiu $a1,$sp,0x10
    jal 0x8003c578
    addiu $a0,$s2,0xc94
    move $a0,$s1
    jal 0x8004d504
    move $a1,$v0
    sltiu $s0,$v0,28
    lui $t0,%(short_hi)d
    ori $t0,$t0,%(short_lo)d
    sw $t0,0x10($sp)
    lui $t0,%(tail_hi)d
    ori $t0,$t0,%(tail_lo)d
    sw $t0,0x14($sp)
    ori $t0,$zero,0xfffe
    sh $t0,0x18($sp)
    beqz $s0,suffix
    addiu $a1,$sp,0x10
    jal 0x8003c578
    addiu $a0,$zero,0xcf1
    move $a1,$v0
suffix:
    jal 0x8004d504
    move $a0,$s1
    lw $ra,0x2c($sp)
    lw $s0,0x28($sp)
    lw $s1,0x24($sp)
    lw $s2,0x20($sp)
    jr $ra
    addiu $sp,$sp,0x30
    '''%{'delimiter_hi':space,'colon':colon,'short_hi':short[1],'short_lo':short[0],
         'tail_hi':short[3],'tail_lo':short[2]}
    raw=bytes(Ks(KS_ARCH_MIPS,KS_MODE_MIPS32|KS_MODE_LITTLE_ENDIAN).asm(code,START)[0])
    assert len(raw)<=END-START,(len(raw),END-START)
    return raw+bytes(END-START-len(raw))


def patch_exe(exe):
    out=bytearray(exe)
    for offset,before,after in POSITIONS:
        assert struct.unpack_from('<H',out,offset)[0]==before
        struct.pack_into('<H',out,offset,after)
    for address,before,after in CALLER:
        assert struct.unpack_from('<I',out,off(address))[0]==before
        struct.pack_into('<I',out,off(address),after)
    out[off(START):off(END)]=compose_code()
    return bytes(out)


if __name__=='__main__':
    import mips
    patch_exe(mips.load())
    print('Dry run: append stage digits/colon/title/completion; 136-byte caller buffer; 28-code short-label threshold.')
    print('Hero list: Unit x=176, mode x=204; Wpn x=242, mode x=270; HP/EN unchanged.')
