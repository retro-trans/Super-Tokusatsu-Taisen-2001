"""Native, reversible intermission difficulty (Gentle / optional Stronger).

Original prices remain in the file. Conditional hooks refresh their RAM copy
before every quote, affordability check and purchase. Combat modifies working
registers only. Never scale stored unit/pilot stats or scripted XP setters.
"""
import hashlib
import json
import struct
from keystone import Ks, KS_ARCH_MIPS, KS_MODE_MIPS32, KS_MODE_LITTLE_ENDIAN
import balance
import mips

START, LIMIT = 0x800DC400, 0x800DE000
FLAG, MAGIC = 0x218, 0x424D0001
STRONG_MAGIC = 0x424D0002
PRICE_SITES = (0x800665F0, 0x80066B68, 0x80069080, 0x80069900,
               0x8006939C, 0x80069F08)


def flag_test(no, support_stronger=False):
    if support_stronger:
        # Preserve exact mode 1/2 in the reserved scratch slot, accepting no
        # other old-save values. All callers already own at least 16 bytes.
        return """lui $k0,0x800c
        lw $k0,-0x2cb0($k0)
        lui $k1,0x424d
        lw $k0,0x218($k0)
        nop
        subu $k0,$k0,$k1
        addiu $k1,$k0,-1
        sltiu $k1,$k1,2
        beqz $k1,%s
        nop
        sw $k0,8($sp)
        """ % no
    return '''lui $k0,0x800c
    lw $k0,-0x2cb0($k0)
    lui $k1,0x424d
    lw $k0,0x218($k0)
    ori $k1,$k1,1
    bne $k0,$k1,%s
    nop
    ''' % no


def asm(code, address):
    # k0/k1 are kernel interrupt scratch and must never be used by game code.
    code = code.replace('$k0','$t8').replace('$k1','$t9')
    return bytes(Ks(KS_ARCH_MIPS, KS_MODE_MIPS32 | KS_MODE_LITTLE_ENDIAN).asm(
        '.set noreorder\n'+code, address)[0])


class Payload:
    def __init__(self):
        self.data = bytearray()
        self.labels = {}

    def add(self, name, data):
        while len(self.data) % 4:
            self.data.append(0)
        address = START+len(self.data)
        if isinstance(data, str):
            data = asm(data, address)
        self.labels[name] = address
        self.data.extend(data)
        assert START+len(self.data) <= LIMIT, 'runtime reservation exceeded'
        return address


def patch_exe(exe, report=False, support_stronger=False):
    original = mips.load()
    result = bytearray(exe)
    assert len(result) == len(original) == 0xAE000
    p = Payload()
    sites = {}

    def patch(address, target, link=False, delay=None):
        pos = mips.off(address)
        assert result[pos:pos+8] == original[pos:pos+8], hex(address)+' hook already changed'
        sites[hex(address)] = result[pos:pos+8].hex()
        word = (0x0C000000 if link else 0x08000000) | ((target >> 2) & 0x3ffffff)
        struct.pack_into('<II', result, pos, word,
                         0 if delay is None else struct.unpack('<I', delay)[0])

    # Independent original/discounted price pairs, excluding gains/caps.
    pairs = b''.join(struct.pack('<HH', r['original_funds'], r['funds']) for r in balance.plan())
    table = p.add('prices', pairs)
    # Preserve all caller-saved registers and HI/LO: used from inside UI code.
    regs = ['v0','v1','a0','a1','a2','a3']+['t%d'%i for i in range(10)]+['ra']
    save = '\n'.join('sw $%s,%d($sp)'%(r,16+4*i) for i,r in enumerate(regs))
    restore = '\n'.join('lw $%s,%d($sp)'%(r,16+4*i) for i,r in enumerate(regs))
    def scale(reg, temp, kind, label):
        gentle = 'srl $%s,$%s,1\naddu $%s,$%s,$%s\n' % (temp,reg,reg,reg,temp)
        if not support_stronger:
            return gentle
        extra = ('sll $%s,$%s,1' if kind=='xp' else 'move $%s,$%s') % (temp,reg)
        return """lw $%s,8($sp)
        nop
        addiu $%s,$%s,-2
        bnez $%s,%s_gentle
        nop
        %s
        b %s_add
        nop
%s_gentle:
        srl $%s,$%s,1
%s_add:
        addu $%s,$%s,$%s
        """ % (temp,temp,temp,temp,label,extra,label,label,temp,reg,label,reg,reg,temp)

    selector = """ori $t2,$t2,1
    xor $t1,$t1,$t2
    sltiu $t1,$t1,1
    """
    if support_stronger:
        selector = """nop
        subu $t1,$t1,$t2
        addiu $t1,$t1,-1
        sltiu $t1,$t1,2
        """
    sync = p.add('prices_sync', '''addiu $sp,$sp,-112
    %s
    mfhi $t0
    mflo $t1
    sw $t0,88($sp)
    sw $t1,92($sp)
    lui $t0,0x800c
    lw $t0,-0x2cb0($t0)
    lui $t2,0x424d
    lw $t1,0x218($t0)
    %s
    sll $t1,$t1,1
    lui $t0,0x800d
    ori $t0,$t0,%d
    addu $t0,$t0,$t1
    lui $t2,0x800a
    ori $t2,$t2,0xef70
    addiu $t3,$zero,240
loop:
    lhu $t4,0($t0)
    addiu $t0,$t0,4
    sh $t4,0($t2)
    addiu $t3,$t3,-1
    bnez $t3,loop
    addiu $t2,$t2,4
    lw $t0,88($sp)
    lw $t1,92($sp)
    mthi $t0
    mtlo $t1
    %s
    nop
    jr $ra
    addiu $sp,$sp,112
    ''' % (save, selector, table & 0xffff, restore))
    # Two adjacent 480-byte native tables, with interleaved price/gain pairs.
    assert balance.TABLES['weapons'] == balance.TABLES['unit_stats']+480
    for address in PRICE_SITES:
        ins = list(mips.md.disasm(original[mips.off(address):mips.off(address)+8], address))
        displaced = '\n'.join(i.mnemonic+' '+i.op_str for i in ins)
        stub = p.add('price_'+hex(address), '''addiu $sp,$sp,-24
        sw $ra,16($sp)
        jal %d
        nop
        lw $ra,16($sp)
        addiu $sp,$sp,24
        %s
        j %d
        nop
        ''' % (sync, displaced, address+8))
        patch(address, stub)

    # Save-backed setting, in an unused four-byte player-state gap.
    # Exact magic makes old saves/default zero unambiguously OFF.
    enter = 'addiu $sp,$sp,-16\nsw $t8,0($sp)\nsw $t9,4($sp)\n'
    leave = 'lw $t8,0($sp)\nlw $t9,4($sp)\naddiu $sp,$sp,16\n'
    toggle = p.add('input', enter+'''lh $v1,0($a0)
    nop
    bnez $v1,done
    nop
    andi $k0,$s1,0x100
    beqz $k0,done
    nop
    lui $k0,0x800c
    lw $k0,-0x2cb0($k0)
    lui $k1,0x424d
    lw $v0,0x218($k0)
    ori $k1,$k1,1
    bne $v0,$k1,enable
    nop
    move $k1,$zero
enable:
    sw $k1,0x218($k0)
done:
    '''+leave+'''
    jr $ra
    nop
    ''')
    patch(0x8005CBF8, toggle, True, original[mips.off(0x8005CBFC):mips.off(0x8005CC00)])

    # Award commitment executes once before the native reward display/XP flow.
    # Clamp signed-short XP pending buffer to avoid turning large gains negative.
    reward = p.add('battle_rewards', enter+flag_test('done', support_stronger)+'''
    lui $k0,0x800c
    lw $k1,-0x2728($k0)
    nop
    '''+scale('k1','v0','reward','funds')+'''
    sw $k1,-0x2728($k0)
    lw $k1,-0x2724($k0)
    nop
    '''+scale('k1','v0','reward','materials')+'''
    sw $k1,-0x2724($k0)
    lh $k1,-0x2720($k0)
    nop
    blez $k1,done
    nop
    '''+scale('k1','v0','xp','battle_xp')+'''
    srl $v0,$k1,15
    beqz $v0,xp
    nop
    addiu $k1,$zero,32767
xp:
    sh $k1,-0x2720($k0)
done:
    '''+leave+'''
    lui $a1,0x800c
    lui $a0,0x800c
    j 0x80047a20
    nop
    ''')
    patch(0x80047A18, reward)
    xp_only = p.add('xp_only', enter+flag_test('done', support_stronger)+'''
    lui $k0,0x800c
    lh $k1,-0x2720($k0)
    nop
    blez $k1,done
    nop
    '''+scale('k1','v0','xp','nonkill_xp')+'''
    srl $v0,$k1,15
    beqz $v0,xp
    nop
    addiu $k1,$zero,32767
xp:
    sh $k1,-0x2720($k0)
done:
    '''+leave+'''
    lui $v0,0x800c
    addiu $v1,$v0,-0x2728
    j 0x80047abc
    nop
    ''')
    patch(0x80047AB4, xp_only)
    stage = p.add('stage_rewards', enter+flag_test('done', support_stronger)+'''
    '''+scale('v0','k0','reward','chapter')+'''
    sw $v0,4($t7)
    sw $v0,-0x2728($t4)
done:
    '''+leave+'''
    lw $v1,0x22c($t0)
    move $a1,$zero
    j 0x80026d74
    nop
    ''')
    patch(0x80026D6C, stage)

    # Only the fresh-map call, after the game's resume-path branch.
    ammo = p.add('stage_ammo', enter+flag_test('done', support_stronger)+'''
    sll $k0,$a0,1
    addu $k0,$k0,$a0
    sll $k0,$k0,3
    addu $k0,$k0,$a0
    sll $k0,$k0,1
    lui $k1,0x800c
    lw $k1,-0x2cb0($k1)
    nop
    addu $k0,$k0,$k1
    addiu $k1,$zero,255
    sb $k1,0x157b($k0)
    sb $k1,0x157c($k0)
    sb $k1,0x157d($k0)
    sb $k1,0x157e($k0)
    sb $k1,0x157f($k0)
    sb $k1,0x1580($k0)
done:
    '''+leave+'''
    j 0x8003d274
    nop
    ''')
    patch(0x8001815C, ammo, True, original[mips.off(0x80018160):mips.off(0x80018164)])

    # Save the attacker-side selector in unused local stack storage. Defender
    # side remains at original stack argument +16 (new sp +0x60).
    entry = p.add('damage_entry', '''addiu $sp,$sp,-0x50
    sw $a0,0x1c($sp)
    move $t1,$a1
    j 0x800546c0
    nop
    ''')
    patch(0x800546B8, entry)
    stats_code = enter+flag_test('done', support_stronger)
    for reg, field, name in (('s4',0x2c,'attack'), ('s1',0x70,'armor')):
        stats_code += '''lw $k0,%d($sp)
        addiu $k1,$zero,1
        bne $k0,$k1,%s_enemy
        nop
        addiu $k1,$zero,110
        b %s_scale
        nop
%s_enemy:
        addiu $k1,$zero,90
%s_scale:
        multu $%s,$k1
        mflo $k0
        addiu $k1,$zero,100
        nop
        divu $zero,$k0,$k1
        mflo $k0
        beqz $%s,%s_zero
        nop
        bnez $k0,%s_zero
        nop
        addiu $k0,$zero,1
%s_zero:
        move $%s,$k0
        ''' % (field,name,name,name,name,reg,reg,name,name,name,reg)
    if support_stronger:
        for name in ('attack','armor'):
            chosen = """lw $k0,8($sp)
            nop
            addiu $k0,$k0,-2
            bnez $k0,%s_base
            nop
            addiu $k0,$k1,-90
            beqz $k0,%s_strong_enemy
            addiu $k1,$zero,125
            b %s_base
            nop
%s_strong_enemy:
            addiu $k1,$zero,75
%s_base:
            """ % (name,name,name,name,name)
            stats_code=stats_code.replace(name+'_scale:\n',name+'_scale:\n'+chosen)
    stats_code += '''done:
    '''+leave+'''
    lhu $t3,0x18($sp)
    j 0x80054ae4
    nop
    '''
    stat_hook = p.add('combat_stats', stats_code)
    patch(0x80054ADC, stat_hook)

    # Compact native-font setting in the free intermission area above footer.
    import efont
    ef = json.loads((balance.ROOT/'work/font/efont.json').read_text(encoding='utf-8'))
    strings = {}
    for name,text in [('off','Balance: OFF'),('on','Balance: ON'),('hint','Select: Change')]:
        words = efont.encode_plain(text, ef['encode'])+[0xfffe]
        strings[name] = p.add(name, struct.pack('<%dH'%len(words),*words))
        assert efont.text_width(text,ef) <= 180
    draw = p.add('draw', '''addiu $sp,$sp,-32
    sw $ra,24($sp)
    bnez $s6,done
    nop
    lui $a0,0x800d
    ori $a0,$a0,%d
    '''%(strings['off']&0xffff)+flag_test('label', support_stronger)+'''
    lui $a0,0x800d
    ori $a0,$a0,%d
label:
    sw $a0,16($sp)
    addiu $a0,$zero,3
    sw $a0,20($sp)
    addiu $a0,$zero,13
    addiu $a1,$zero,24
    addiu $a2,$zero,160
    jal 0x8004c90c
    addiu $a3,$zero,1
    lui $a0,0x800d
    ori $a0,$a0,%d
    sw $a0,16($sp)
    addiu $a0,$zero,3
    sw $a0,20($sp)
    addiu $a0,$zero,13
    addiu $a1,$zero,24
    addiu $a2,$zero,178
    jal 0x8004c90c
    addiu $a3,$zero,0
done:
    lw $ra,24($sp)
    addiu $sp,$sp,32
    jr $ra
    nop
    '''%(strings['on']&0xffff,strings['hint']&0xffff))
    tail = p.add('draw_tail', '''jal %d
    nop
    lw $ra,0x45c($sp)
    lw $fp,0x458($sp)
    j 0x800627c4
    nop
    '''%draw)
    patch(0x800627BC, tail)

    # Reserve code after BSS, below stage overlays, by moving BIOS heap start.
    # The startup clear still ends at DC368, so it cannot erase the new code.
    assert struct.unpack_from('<I', result, mips.off(0x8005B900))[0] == 0x2484C368
    struct.pack_into('<I', result, mips.off(0x8005B900),0x2484E000)
    result.extend(bytes(mips.off(LIMIT)-len(result)))
    result[mips.off(START):mips.off(START)+len(p.data)] = p.data
    struct.pack_into('<I',result,0x1c,LIMIT-0x80010000)
    assert not support_stronger or START+len(p.data) <= 0x800DD000, 'runtime code overlaps save-slot payload'
    info = {'profile':'Gentle','default':'OFF','input':'Select at intermission main menu',
            'xp_and_rewards':'150%, floor, XP pending capped at 32767; native level cap unchanged',
            'ally_attack_armor_percent':110,'enemy_attack_armor_percent':90,
            'prices':balance.profile(),'ammo':'six native ammo slots, fresh-stage setup only',
            'flag_offset':hex(FLAG),'flag_magic':hex(MAGIC),
            'code_start':hex(START),'code_end':hex(START+len(p.data)),
            'heap_start':hex(LIMIT),'labels':{k:hex(v) for k,v in p.labels.items()},
            'hooks':sites,'exe_sha256':hashlib.sha256(result).hexdigest()}
    if support_stronger:
        info['profiles']={'Gentle':{'xp_percent':150,'reward_percent':150,'ally_percent':110,'enemy_percent':90},
                          'Stronger':{'xp_percent':300,'reward_percent':200,'ally_percent':125,'enemy_percent':75}}
        info['strong_flag_magic']=hex(STRONG_MAGIC)
    return (bytes(result),info) if report else bytes(result)
