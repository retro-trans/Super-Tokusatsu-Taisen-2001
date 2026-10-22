"""Visible, save-backed difficulty menu on the actual Intermission root.

Applied after the historical runtime Balance and save-slot patches. State 22
is the root (type 6), not state 0, which is a unit context menu. Only UI hooks
change; all conditional gameplay rules and the saved flag remain identical.
"""
import hashlib
import json
import struct
import mips
import runtime_balance as rb
import efont

START, LIMIT = 0x800DD340, 0x800DE000
ROOT_STATE = 22


def patch_exe(exe, report=False, support_stronger=False, story_labels=False):
    assert not story_labels or support_stronger
    original = mips.load()
    out = bytearray(exe)
    data = bytearray()
    labels = {}

    def add(name, value):
        while len(data) % 4:
            data.append(0)
        addr = START + len(data)
        if isinstance(value, str):
            value = rb.asm(value, addr)
        labels[name] = addr
        data.extend(value)
        assert START + len(data) <= LIMIT
        return addr

    def put(addr, value):
        out[mips.off(addr):mips.off(addr)+len(value)] = value

    def jump(site, target, delay=0):
        put(site, struct.pack('<II', 0x08000000 | ((target >> 2) & 0x3ffffff), delay))

    modal = add('pending_choice', bytes(4))  # 0 closed; 1 Normal; 2 Gentle
    # Retain the original four panels, extend the left one by one row, and add
    # a fifth teal panel beneath the funds. No transient frame allocation.
    frames = bytearray(original[mips.off(0x800A8B60):mips.off(0x800A8BC0)])
    struct.pack_into('<H', frames, 24+10, 107)
    struct.pack_into('<H', frames, 36+10, 106)
    frames += struct.pack('<6H', 0xFC, 192, 108, 0x1A, 111, 83)
    frames += struct.pack('<6H', 0xFD, 193, 109, 0x0A, 110, 82)
    frames += struct.pack('<4H', 0xFF, 0, 0, 0)
    frame_addr = add('root_frames', bytes(frames))
    struct.pack_into('<I', out, mips.off(0x800A9A98+29*8+4), frame_addr)
    struct.pack_into('<H', out, mips.off(0x800B38CC+22*28+4), 6)

    # Remove the old state-0 Select input. Intercept only the root's sixth row
    # and the modal. All original five rows use the original input/action path.
    input_code = ('''lh $v1,0($a0)
    lui $t0,0x800d
    ori $t0,$t0,%d
    addiu $t1,$zero,22
    beq $v1,$t1,root
    nop
    sw $zero,0($t0)
    j 0x8005cc00
    nop
root:
    lw $t1,0($t0)
    nop
    bnez $t1,choice
    nop
    lh $t2,0x552($gp)
    addiu $t3,$zero,5
    bne $t2,$t3,native
    nop
    andi $t2,$s7,0x20
    beqz $t2,native
    nop
    andi $t2,$s1,0x20
    beqz $t2,consume
    nop
    lui $t2,0x800c
    lw $t2,-0x2cb0($t2)
    lui $t3,0x424d
    lw $t2,0x218($t2)
    ori $t3,$t3,1
    xor $t2,$t2,$t3
    sltiu $t2,$t2,1
    addiu $t2,$t2,1
    j store_choice
    nop
choice:
    andi $t2,$s1,0x40
    bnez $t2,close
    nop
    andi $t2,$s1,0xf000
    beqz $t2,confirm
    nop
    addiu $t2,$zero,3
    subu $t2,$t2,$t1
    j store_choice
    nop
confirm:
    andi $t2,$s1,0x20
    beqz $t2,consume
    nop
    lui $t2,0x800c
    lw $t2,-0x2cb0($t2)
    addiu $t3,$zero,2
    bne $t1,$t3,normal
    move $t4,$zero
    lui $t4,0x424d
    ori $t4,$t4,1
normal:
    sw $t4,0x218($t2)
close:
    sw $zero,0($t0)
    j redraw
    nop
store_choice:
    sw $t2,0($t0)
redraw:
    jal 0x8005fde0
    addiu $a0,$zero,22
consume:
    move $v0,$zero
    j 0x8005f12c
    sb $zero,0x20c($gp)
native:
    j 0x8005cc00
    nop
''') % (modal & 0xffff)
    if support_stronger:
        input_code = stronger_input(input_code)
    input_addr = add('input', input_code)
    jump(0x8005CBF8, input_addr, struct.unpack_from('<I', original, mips.off(0x8005CBFC))[0])

    ef = json.loads((rb.balance.ROOT/'work/font/efont.json').read_text(encoding='utf-8'))
    strings = {}
    menu_strings = [('row','Difficulty'),('heading','Difficulty'),
                       ('normal','Normal'),('gentle','Gentle'),
                       ('off','Normal'),('on','Gentle'),
                       ('help','O: OK  X: Back'),('open','Select mode'),
                       ('arrow','>')]
    if support_stronger:
        menu_strings.append(('stronger','Stronger'))
    if story_labels:
        menu_strings=[(key,{'Normal':'Default','Stronger':'Story'}.get(text,text))
                      for key,text in menu_strings]
    for name, text in menu_strings:
        words = efont.encode_plain(text, ef['encode'])+[0xFFFE]
        strings[name] = add(name, struct.pack('<%dH'%len(words),*words))
        assert efont.text_width(text,ef) <= (96 if name=='row' else 104)

    def draw(name, x, y, color=0):
        code = '''lui $v0,0x800d
        ori $v0,$v0,%d
        sw $v0,16($sp)
        addiu $v0,$zero,3
        sw $v0,20($sp)
        addiu $a0,$zero,%d
        addiu $a1,$zero,%d
        addiu $a2,$zero,%d
        jal 0x8004c90c
        addiu $a3,$zero,%d
        ''' % (strings[name]&0xffff,18 if support_stronger else 13,x,y,3 if support_stronger and color==1 else color)
        return code.replace('jal 0x8004c90c','jal 0x8004a954') if support_stronger else code

    draw_code = ('''addiu $sp,$sp,-40
    sw $ra,32($sp)
    addiu $v0,$zero,22
    bne $s6,$v0,done
    nop
    '''+draw('row',32,136)+draw('heading',200,112,1)+'''
    lui $v0,0x800d
    ori $v0,$v0,%d
    lw $v0,0($v0)
    nop
    beqz $v0,status
    nop
    sw $v0,28($sp)
    '''+draw('normal',208,132)+draw('gentle',208,148)+draw('help',200,172)+'''
    lw $v0,28($sp)
    nop
    addiu $v0,$v0,-1
    sll $v0,$v0,4
    addiu $a2,$v0,132
    lui $v0,0x800d
    ori $v0,$v0,%d
    sw $v0,16($sp)
    addiu $v0,$zero,3
    sw $v0,20($sp)
    addiu $a0,$zero,13
    addiu $a1,$zero,196
    jal 0x8004c90c
    addiu $a3,$zero,1
    j done
    nop
status:
    lui $v0,0x800d
    ori $v0,$v0,%d
    lui $t0,0x800c
    lw $t0,-0x2cb0($t0)
    lui $t1,0x424d
    lw $t0,0x218($t0)
    ori $t1,$t1,1
    bne $t0,$t1,label
    nop
    lui $v0,0x800d
    ori $v0,$v0,%d
label:
    sw $v0,16($sp)
    addiu $v0,$zero,3
    sw $v0,20($sp)
    addiu $a0,$zero,13
    addiu $a1,$zero,200
    addiu $a2,$zero,136
    jal 0x8004c90c
    addiu $a3,$zero,0
    '''+draw('open',200,160)+'''
done:
    lw $ra,32($sp)
    addiu $sp,$sp,40
    jr $ra
    nop
''') % (modal & 0xffff, strings['arrow']&0xffff,
        strings['off']&0xffff, strings['on']&0xffff)
    if support_stronger:
        # Five 16px rows fit the existing panel: title at 112, choices at
        # 128/144/160, help at 176. The closed status panel keeps its layout.
        old_choices=draw('normal',208,132)+draw('gentle',208,148)+draw('help',200,172)
        new_choices=draw('normal',208,128)+draw('gentle',208,144)+draw('stronger',208,160)+draw('help',200,176)
        assert old_choices in draw_code
        draw_code=draw_code.replace(old_choices,new_choices)
        draw_code=draw_code.replace('addiu $a2,$v0,132','addiu $a2,$v0,128')
        # Arrow/status calls were written inline in the historical routine.
        draw_code=draw_code.replace('addiu $a0,$zero,13','addiu $a0,$zero,18')
        draw_code=draw_code.replace('jal 0x8004c90c','jal 0x8004a954')
        draw_code=draw_code.replace('addiu $a3,$zero,1','addiu $a3,$zero,3')
        old_status="""bne $t0,$t1,label
    nop
    lui $v0,0x800d
    ori $v0,$v0,%d
label:
""" % (strings['on']&0xffff)
        new_status="""beq $t0,$t1,gentle_status
    nop
    addiu $t1,$t1,1
    bne $t0,$t1,label
    nop
    lui $v0,0x800d
    ori $v0,$v0,%d
    b label
    nop
gentle_status:
    lui $v0,0x800d
    ori $v0,$v0,%d
label:
""" % (strings['stronger']&0xffff,strings['on']&0xffff)
        assert old_status in draw_code
        draw_code=draw_code.replace(old_status,new_status)
        draw_code=draw_code.replace('bne $s6,$v0,done','bne $s6,$v0,return')
        draw_code=draw_code.replace('done:\n    lw $ra,32($sp)',
            'done:\n    jal 0x8004bf8c\n    addiu $a0,$zero,18\nreturn:\n    lw $ra,32($sp)')
    draw_addr = add('draw', draw_code)
    tail = add('draw_tail', '''jal %d
    nop
    lw $ra,0x45c($sp)
    lw $fp,0x458($sp)
    j 0x800627c4
    nop
''' % draw_addr)
    jump(0x800627BC, tail)
    put(START, data)
    info = {'menu':'Intermission > Difficulty > Normal / Gentle',
            'root_state':ROOT_STATE,'default':'Normal','select_shortcut_removed':True,
            'pending_choice':hex(modal),'code_start':hex(START),
            'code_end':hex(START+len(data)),
            'labels':{k:hex(v) for k,v in labels.items()},
            'exe_sha256':hashlib.sha256(out).hexdigest()}
    if support_stronger:
        info['menu']='Intermission > Difficulty > Normal / Gentle / Stronger'
        info['choice_names']=['Normal','Gentle','Stronger']
        info['choices_y']=[128,144,160]
        info['help_y']=176
        info['sprite_group']=18
    if story_labels:
        info['menu']='Intermission > Difficulty > Default / Gentle / Story'
        info['default']='Default'
        info['choice_names']=['Default','Gentle','Story']
    return (bytes(out),info) if report else bytes(out)


def stronger_input(code):
    old="""ori $t3,$t3,1
    xor $t2,$t2,$t3
    sltiu $t2,$t2,1
    addiu $t2,$t2,1
"""
    new="""nop
    subu $t2,$t2,$t3
    addiu $t4,$t2,-1
    sltiu $t4,$t4,2
    beqz $t4,open_normal
    nop
    addiu $t2,$t2,1
    b store_choice
    nop
open_normal:
    addiu $t2,$zero,1
"""
    assert old in code
    code=code.replace(old,new)
    old="""addiu $t2,$zero,3
    subu $t2,$t2,$t1
    j store_choice
    nop
"""
    new="""andi $t2,$s1,0x9000
    bnez $t2,previous
    nop
    addiu $t2,$t1,1
    sltiu $t3,$t2,4
    bnez $t3,store_choice
    nop
    b store_choice
    addiu $t2,$zero,1
previous:
    addiu $t2,$t1,-1
    bnez $t2,store_choice
    nop
    b store_choice
    addiu $t2,$zero,3
"""
    assert old in code
    code=code.replace(old,new)
    old="""addiu $t3,$zero,2
    bne $t1,$t3,normal
    move $t4,$zero
    lui $t4,0x424d
    ori $t4,$t4,1
"""
    new="""addiu $t3,$zero,1
    beq $t1,$t3,normal
    move $t4,$zero
    addiu $t3,$t1,-1
    lui $t4,0x424d
    or $t4,$t4,$t3
"""
    assert old in code
    return code.replace(old,new)
