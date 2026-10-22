"""Batch Difficulty glyphs independently of the Intermission stage footer.

4C90C finalizes a whole reusable sprite group, not a single text line. Calling
it once per label replaces preceding labels. Use raw 4A954 and finalize once
in group 18, which the native root renderer clears before each redraw.
"""
import hashlib
import struct
import mips
import runtime_balance as rb
import difficulty_menu

START, LIMIT = 0x800DD720, 0x800DE000
GROUP = 18


def patch_exe(exe, report=False):
    _, previous = difficulty_menu.patch_exe(exe, True)
    labels = {k:int(v,16) for k,v in previous['labels'].items()}
    out = bytearray(exe)
    assert len(out)==mips.off(LIMIT)
    calls = groups = colors = 0
    for addr in range(labels['draw'],labels['draw_tail'],4):
        pos=mips.off(addr)
        word=struct.unpack_from('<I',out,pos)[0]
        if word==0x0C013243:  # jal 8004C90C
            struct.pack_into('<I',out,pos,0x0C012A55)  # jal 8004A954
            calls+=1
        elif word==0x2404000D:  # a0 = group 13
            struct.pack_into('<I',out,pos,0x24040000|GROUP)
            groups+=1
        elif word==0x24070001:  # color 1 is red; native yellow is 3
            struct.pack_into('<I',out,pos,0x24070003)
            colors+=1
    assert calls==groups==8 and colors==2,(calls,groups,colors)
    epilogue=labels['draw_tail']-16
    expected=rb.asm('lw $ra,32($sp)\naddiu $sp,$sp,40\njr $ra\nnop',epilogue)
    assert out[mips.off(epilogue):mips.off(epilogue)+16]==expected
    struct.pack_into('<II',out,mips.off(epilogue),
                     0x08000000|((START>>2)&0x3ffffff),0)
    code=rb.asm('''addiu $v0,$zero,22
    bne $s6,$v0,done
    nop
    jal 0x8004bf8c
    addiu $a0,$zero,18
done:
    lw $ra,32($sp)
    addiu $sp,$sp,40
    jr $ra
    nop
''',START)
    assert START+len(code)<=LIMIT
    out[mips.off(START):mips.off(START)+len(code)]=code
    info={'sprite_group':GROUP,'stage_footer_group':13,
          'raw_draw_sites':calls,'yellow_label_sites':colors,
          'finalize_once_per_root_draw':True,
          'code_start':hex(START),'code_end':hex(START+len(code)),
          'exe_sha256':hashlib.sha256(out).hexdigest()}
    return (bytes(out),info) if report else bytes(out)
