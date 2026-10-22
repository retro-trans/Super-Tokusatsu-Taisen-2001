"""Fit save/load slot captions using native VWF measurements.

Changes rendering only. The native save format, values, stage selection,
portraits, timestamps and load behavior are retained. Applied after runtime
Balance, inside its already reserved post-BSS executable region.
"""
import hashlib
import struct
import efont
import insert
import mips
from runtime_balance import asm, Payload, LIMIT

START = 0x800DD000
WIDTH = 244
POSITIONS = {
    0x80049558: (0xB0,184),  # four-digit current-turn value
    0x800495A8: (0x98,148),  # Turn
    0x800495CC: (0xDC,224),  # Total
    0x8004951C: (0x100,268), # four-digit total-turn value
}


class Area(Payload):
    def add(self,name,data):
        # Payload's base is the earlier Balance allocation; use its alignment
        # and assembler but reserve this module's separate zero-filled range.
        while len(self.data)%4:
            self.data.append(0)
        address=START+len(self.data)
        if isinstance(data,str):
            data=asm(data,address)
        self.labels[name]=address
        self.data.extend(data)
        assert START+len(self.data)<=LIMIT,'save-caption reservation exceeded'
        return address


def patch_exe(exe,report=False):
    out=bytearray(exe);original=mips.load();p=Area()
    assert len(out)==mips.off(LIMIT), 'apply after runtime_balance'
    assert not any(out[mips.off(START):mips.off(LIMIT)]),'save-caption region occupied'
    names={}
    for name,text in [('prefix','Stage '),('colon',': '),('full',' cleared'),
                      ('short',' Clr.'),('empty',''),('ellipsis','...'),
                      ('turn','Turn'),('total','Total')]:
        words=efont.encode_plain(text,insert.EF['encode'])+[0xfffe]
        names[name]=p.add(name,struct.pack('<%dH'%len(words),*words))

    # Measure exactly the native rendered glyphs, rather than the old 8/12px
    # estimator. The existing patched lookup returns the advance in v1.
    measure=p.add('measure','''addiu $sp,$sp,-64
    sw $ra,60($sp)
    sw $s0,56($sp)
    sw $s1,52($sp)
    move $s0,$a0
    move $s1,$zero
loop:
    lhu $a1,0($s0)
    addiu $s0,$s0,2
    ori $v0,$zero,0xfffd
    sltu $v0,$a1,$v0
    beqz $v0,done
    nop
    sltiu $v0,$a1,1454
    beqz $v0,loop
    nop
    jal 0x8004a7d8
    addiu $a0,$sp,16
    b loop
    addu $s1,$s1,$v1
done:
    move $v0,$s1
    lw $ra,60($sp)
    lw $s0,56($sp)
    lw $s1,52($sp)
    jr $ra
    addiu $sp,$sp,64
    ''')
    clip=p.add('clip','''addiu $sp,$sp,-80
    sw $ra,76($sp)
    sw $s0,72($sp)
    sw $s1,68($sp)
    sw $s2,64($sp)
    sw $s3,60($sp)
    move $s0,$a1
    move $s1,$a0
    move $s2,$a2
loop:
    lhu $s3,0($s0)
    nop
    sltiu $v0,$s3,1454
    beqz $v0,done
    move $a1,$s3
    jal 0x8004a7d8
    addiu $a0,$sp,16
    slt $v0,$s2,$v1
    bnez $v0,done
    nop
    sh $s3,0($s1)
    addiu $s0,$s0,2
    addiu $s1,$s1,2
    b loop
    subu $s2,$s2,$v1
done:
    ori $v0,$zero,0xfffe
    sh $v0,0($s1)
    lw $ra,76($sp)
    lw $s0,72($sp)
    lw $s1,68($sp)
    lw $s2,64($sp)
    lw $s3,60($sp)
    jr $ra
    addiu $sp,$sp,80
    ''')
    def addr(reg,address):
        return 'lui $%s,0x800d\nori $%s,$%s,%d\n'%(reg,reg,reg,address&0xffff)
    def append(pointer):
        return 'move $a0,$s3\n'+addr('a1',pointer)+'jal 0x8004d504\nnop\n'
    header=p.add('header','''addiu $sp,$sp,-0x110
    sw $ra,0x100($sp)
    sw $s0,0xe0($sp)
    sw $s1,0xe4($sp)
    sw $s2,0xe8($sp)
    sw $s3,0xec($sp)
    sw $s4,0xf0($sp)
    sw $s5,0xf4($sp)
    sw $s6,0xf8($sp)
    sw $s7,0xfc($sp)
    move $s0,$a0
    move $s1,$a1
    move $s2,$a2
    addiu $s3,$sp,0x20
    move $a0,$s3
    '''+addr('a1',names['prefix'])+'''jal 0x8004d4b8
    nop
    lhu $v0,4($s0)
    lhu $s6,16($s0)
    addiu $t1,$sp,0xc0
    addu $s6,$s6,$v0
    ori $v0,$zero,0xfffe
    sh $v0,0($t1)
    addiu $t0,$zero,10
digits:
    divu $zero,$s6,$t0
    mflo $s6
    mfhi $v0
    addiu $t1,$t1,-2
    addiu $v0,$v0,1
    sh $v0,0($t1)
    bnez $s6,digits
    nop
    move $a0,$s3
    jal 0x8004d504
    move $a1,$t1
    '''+append(names['colon'])+'''
    sll $s7,$v0,1
    addu $s7,$s7,$s3
    jal %d
    move $a0,$s3
    move $s4,$v0
    jal 0x8003c578
    addiu $a0,$s2,0xc94
    move $s2,$v0
    jal %d
    move $a0,$s2
    move $s6,$v0
    '''% (measure,measure)+addr('s5',names['empty'])+'''
    lhu $v0,16($s0)
    nop
    bnez $v0,budget
    nop
    '''+addr('s5',names['full'])+'''jal %d
    move $a0,$s5
    addu $v0,$v0,$s4
    addu $v0,$v0,$s6
    sltiu $v0,$v0,245
    bnez $v0,budget
    nop
    '''%measure+addr('s5',names['short'])+'''
budget:
    jal %d
    move $a0,$s5
    addiu $s4,$s4,-244
    addu $s4,$s4,$v0
    subu $s4,$zero,$s4
    slt $v0,$s4,$s6
    bnez $v0,truncate
    nop
    move $a0,$s3
    jal 0x8004d504
    move $a1,$s2
    b suffix
    nop
truncate:
    '''%measure+addr('a0',names['ellipsis'])+'''jal %d
    nop
    subu $a2,$s4,$v0
    move $a0,$s7
    jal %d
    move $a1,$s2
    '''%(measure,clip)+append(names['ellipsis'])+'''
suffix:
    move $a0,$s3
    jal 0x8004d504
    move $a1,$s5
    addiu $a0,$zero,30
    addiu $a1,$zero,64
    move $a2,$s1
    move $a3,$zero
    sw $s3,16($sp)
    addiu $v0,$zero,3
    jal 0x8004a954
    sw $v0,20($sp)
    lw $ra,0x100($sp)
    lw $s0,0xe0($sp)
    lw $s1,0xe4($sp)
    lw $s2,0xe8($sp)
    lw $s3,0xec($sp)
    lw $s4,0xf0($sp)
    lw $s5,0xf4($sp)
    lw $s6,0xf8($sp)
    lw $s7,0xfc($sp)
    jr $ra
    addiu $sp,$sp,0x110
    ''')
    for name,site in [('turn',0x8004959c),('total',0x800495c0)]:
        stub=p.add(name+'_pointer',addr('v0',names[name])+'jr $ra\nnop\n')
        pos=mips.off(site)
        assert out[pos:pos+8]==original[pos:pos+8]
        out[pos:pos+4]=asm('jal %d'%stub,site)
    # Suppress the old fixed Stage/digit/title/completion draws, replacing
    # their final block with one complete caption at the same row origin.
    pos=mips.off(0x800494ec)
    assert out[pos:pos+8]==original[pos:pos+8]
    out[pos:pos+8]=asm('j 0x80049518\nnop',0x800494ec)
    code=asm('''move $a0,$fp
    lh $a1,0x60($sp)
    lhu $a2,0x68($sp)
    jal %d
    nop
    j 0x8004984c
    nop
    '''%header,0x80049788)
    pos=mips.off(0x80049788)
    assert out[pos:pos+len(code)]==original[pos:pos+len(code)]
    out[pos:pos+len(code)]=code
    for address,(before,after) in POSITIONS.items():
        pos=mips.off(address)
        word=struct.unpack_from('<I',out,pos)[0]
        assert word&0xffff==before and word>>16==0x2405,hex(address)
        struct.pack_into('<I',out,pos,(word&0xffff0000)|after)
    out[mips.off(START):mips.off(START)+len(p.data)]=p.data
    info={'header_x':64,'header_width':WIDTH,'body_line_height':16,
          'current_turn':{'label':'Turn','label_x':148,'value_x':184,'digits':4},
          'total_turns':{'label':'Total','label_x':224,'value_x':268,'digits':4},
          'font_and_save_data_unchanged':True,'code_start':hex(START),
          'code_end':hex(START+len(p.data)),
          'labels':{k:hex(v) for k,v in p.labels.items()},
          'exe_sha256':hashlib.sha256(out).hexdigest()}
    return (bytes(out),info) if report else bytes(out)
