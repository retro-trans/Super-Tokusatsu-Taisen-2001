"""Riot Stars-style native 2x font atlas and half-size textured glyph quads.

The atlas reuses the English F1 left page. Compressed pairs/words expand at
draw time, keeping the native 255-object lifecycle and original VRAM extent.
Private code/data use the retired Select UI and the space after Difficulty.
"""
import json,struct
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image
import mips,runtime_balance as rb

ROOT=Path(__file__).resolve().parents[1]
A,LIMIT_A=0x800DCE38,0x800DD000
B,LIMIT_B=0x800DD7C0,0x800DE000
I=0x800DC9BC  # retired Select-input helper, 96 bytes
MAGIC=0x534B


def stable_lookup(labels):
    """Keep persisted glyph IDs independent of width; fit the native routine.

    The legacy UV calculation still serves icons and native fixed-width values.
    English widths come from token expansion plus the current atlas advances.
    """
    return rb.asm('''addiu $sp,$sp,-24
    sw $ra,20($sp)
    sw $a0,4($sp)
    andi $t0,$a1,0xffff
    sw $a1,8($sp)
    sltiu $v0,$t0,320
    beqz $v0,wide
    addiu $t1,$zero,0x1c
    andi $v0,$t0,31
    sll $v0,$v0,3
    sb $v0,0xe($a0)
    srl $v0,$t0,5
    sll $v0,$v0,4
    sb $v0,0xf($a0)
    addiu $v1,$zero,8
    b common
    addiu $t2,$zero,0xf0
wide:
    addiu $v0,$t0,-110
    addiu $v1,$zero,336
    divu $zero,$v0,$v1
    addiu $v1,$zero,21
    mflo $t3
    mfhi $t4
    addu $t1,$t1,$t3
    addiu $t2,$zero,0xf0
    divu $zero,$t4,$v1
    sltiu $v0,$t0,782
    bnez $v0,rowcol
    nop
    addiu $t1,$t1,-2
    sltiu $v0,$t0,0x5ae
    beqz $v0,rowcol
    nop
    addiu $t2,$zero,0xf1
rowcol:
    mflo $v0
    mfhi $v1
    sll $v0,$v0,4
    sb $v0,0xf($a0)
    sll $v0,$v1,1
    addu $v0,$v0,$v1
    sll $v0,$v0,2
    sb $v0,0xe($a0)
    sh $t1,0xc($a0)
    sh $t2,0x12($a0)
    addiu $t4,$zero,12
    sh $t4,8($a0)
    move $a0,$t0
    jal %d
    addiu $a1,$sp,16
    beqz $v1,fields
    move $t4,$zero
sum:
    lbu $t0,0($v0)
    lui $t1,0x800d
    ori $t1,$t1,%d
    sll $t0,$t0,1
    addu $t0,$t0,$t1
    lbu $t0,1($t0)
    addiu $v1,$v1,-1
    andi $t0,$t0,31
    addu $t4,$t4,$t0
    bnez $v1,sum
    addiu $v0,$v0,1
    lw $a0,4($sp)
    nop
    sh $t4,8($a0)
    b fields
    nop
common:
    sh $v1,8($a0)
    sh $t1,0xc($a0)
    sh $t2,0x12($a0)
fields:
    lw $a0,4($sp)
    lw $a1,8($sp)
    addiu $v0,$zero,0x30
    sh $v0,0x10($a0)
    addiu $v0,$zero,16
    sh $v0,0xa($a0)
    sw $zero,0($a0)
    lui $t0,0x800c
    ori $t0,$t0,0x6c10
    subu $t0,$a0,$t0
    sltiu $t0,$t0,0x23dc
    beqz $t0,done
    lw $t1,8($sp)
    addiu $t0,$zero,%d
    sh $t1,0x18($a0)
    sh $t0,0x1a($a0)
done:
    lw $ra,20($sp)
    addiu $sp,$sp,24
    jr $ra
    nop
'''%(labels['token'],labels['glyphs']&0xffff,MAGIC),0x8004a7d8)


@lru_cache(maxsize=1)
def assets():
    import rayblade_font as R
    meta=json.loads((ROOT/'work/font/efont.json').read_text(encoding='utf-8'))
    font=R.Font();atlas=np.zeros((256,256),np.uint8);desc=[];x=y=0
    for ch in meta['uni']:
        width=meta['widths'][ch]*2
        if x+width>254:x=0;y+=32
        assert y+32<=224,(ch,y)
        high=font.hires(ch)
        if ch in R.ASCII:cell=high[::2,::2]
        else:
            alpha=R.LEVELS[high]
            low=np.asarray(Image.fromarray(alpha).resize((24,32),Image.Resampling.BOX),dtype=np.int16)
            cell=np.argmin(abs(low[:,:,None]-R.LEVELS.astype(np.int16)),axis=2).astype(np.uint8)
        assert not cell[:,width:].any(),ch
        atlas[y:y+32,x:x+width]=cell[:,:width]
        desc.append(bytes([x,y|meta['widths'][ch]]));x+=width
    ids={ch:i for i,ch in enumerate(meta['uni'])}
    pairs=bytes(ids[c] for s in meta['bi'] for c in s)
    words=bytearray();lengths=[]
    for s in meta['ex']:
        lengths.append(len(s));words.extend(ids[c] for c in s)
    import ui_value_font
    native={**ui_value_font.CODES,277:'D',278:'I'}
    native=b''.join(struct.pack('<HB',code,ids[ch]) for code,ch in sorted(native.items()))+b'\xff\xff\0'
    return atlas,b''.join(desc),pairs,bytes(lengths)+words,native,len(lengths),y+32


def patch_tim(tim,main=True,native_ui=False):
    import insert
    out=bytearray(tim);pix,base=insert.tim_pixels(out)
    if main:
        pix[:,:256]=(pix[:,:256]&3)|(assets()[0]<<2)
        out[base:base+pix.size//2]=(pix[:,0::2]|(pix[:,1::2]<<4)).astype(np.uint8).tobytes()
    # F1 palettes: faint edge = half-blended foreground, both ink levels opaque.
    clen,cx,cy,cw,ch=struct.unpack_from('<IHHHH',out,8)
    for row in ([] if native_ui else range(1,cw*ch//16,2)):
        bright=struct.unpack_from('<H',out,20+row*32+24)[0]&0x7fff
        if not bright:continue
        colors=[0 if i<4 else bright|0x8000 if i<8 else bright for i in range(16)]
        struct.pack_into('<16H',out,20+row*32,*colors)
    return bytes(out)


def patch_files(files,native_ui=False):
    import repack,insert,cm
    for name,indices in [('MAPMAIN.DAT',[7]),('BATTLE.DAT',[537,538]),('EVENT.DAT',[10])]:
        entries=repack.dat_entries(files[name])
        for index in indices:entries[index]=patch_tim(entries[index],native_ui=native_ui)
        if name=='MAPMAIN.DAT':entries[25]=insert.rebuild_cm(entries[25],{3:patch_tim(cm.blocks(entries[25])[3],native_ui=native_ui)})
        if name=='EVENT.DAT':
            for index in range(11,24):entries[index]=patch_tim(entries[index],False,native_ui=native_ui)
        files[name]=repack.dat_pack(entries)


def patch_exe(exe,report=False,transition_clip=False,native_ui=False):
    out=bytearray(exe);_,desc,pairs,words,native,word_start,rows=assets()
    first=bytearray(b'F2X1');labels={}
    def data(name,raw):
        while len(first)%4:first.append(0)
        labels[name]=A+len(first);first.extend(raw)
    data('glyphs',desc);data('native',native);data('pairs0',pairs[:128])
    assert A+len(first)<=LIMIT_A,len(first)
    second=bytearray(words)
    while len(second)%4:second.append(0)
    labels['words']=B;labels['word_data']=B+word_start
    labels['pairs2']=B+len(second);second.extend(pairs[224:])
    def code(name,source):
        labels[name]=B+len(second);second.extend(rb.asm(source,labels[name]))
    code('token','''addiu $t0,$a0,-320
    sltiu $t1,$t0,126
    beqz $t1,pair
    nop
single:
    sb $t0,0($a1)
    move $v0,$a1
    jr $ra
    addiu $v1,$zero,1
pair:
    addiu $t0,$a0,-782
    sltiu $t1,$t0,336
    beqz $t1,word
    nop
    sltiu $t1,$t0,64
    bnez $t1,part0
    nop
    sltiu $t1,$t0,112
    bnez $t1,part1
    nop
    addiu $t0,$t0,-112
    lui $v0,0x800d
    ori $v0,$v0,%d
    b pair_done
    nop
part1:
    addiu $t0,$t0,-64
    lui $v0,0x800d
    ori $v0,$v0,%d
    b pair_done
    nop
part0:
    lui $v0,0x800d
    ori $v0,$v0,%d
pair_done:
    sll $t0,$t0,1
    addu $v0,$v0,$t0
    jr $ra
    addiu $v1,$zero,2
word:
    addiu $t0,$a0,-446
    sltiu $t1,$t0,336
    beqz $t1,native
    addiu $t1,$zero,21
    divu $zero,$t0,$t1
    mfhi $t1
    mflo $t0
    andi $t2,$t1,1
    bnez $t2,none
    sltiu $t2,$t1,20
    beqz $t2,none
    sll $t2,$t0,2
    addu $t0,$t0,$t2
    sll $t0,$t0,1
    srl $t1,$t1,1
    addu $t0,$t0,$t1
    sltiu $t1,$t0,160
    beqz $t1,none
    nop
    lui $t1,0x800d
    ori $t1,$t1,%d
    move $t2,$zero
prefix:
    beqz $t0,word_found
    nop
    lbu $t3,0($t1)
    addiu $t0,$t0,-1
    addu $t2,$t2,$t3
    b prefix
    addiu $t1,$t1,1
word_found:
    lbu $v1,0($t1)
    lui $v0,0x800d
    ori $v0,$v0,%d
    jr $ra
    addu $v0,$v0,$t2
native:
    lui $t1,0x800d
    ori $t1,$t1,%d
search:
    lbu $t0,0($t1)
    lbu $t3,1($t1)
    ori $t2,$zero,0xffff
    sll $t3,$t3,8
    or $t0,$t0,$t3
    beq $t0,$t2,none
    nop
    beq $t0,$a0,found
    nop
    b search
    addiu $t1,$t1,3
found:
    lbu $t0,2($t1)
    b single
    nop
none:
    jr $ra
    move $v1,$zero
'''%(labels['pairs2']&0xffff,I&0xffff,labels['pairs0']&0xffff,B&0xffff,labels['word_data']&0xffff,labels['native']&0xffff))
    legacy_lookup='''addiu $sp,$sp,-8
    sw $t8,0($sp)
    lui $t8,0x800c
    ori $t8,$t8,0x6c10
    subu $t8,$a0,$t8
    sltiu $t8,$t8,0x23dc
    beqz $t8,done
    nop
    addiu $t8,$zero,%d
    sh $a1,0x18($a0)
    sh $t8,0x1a($a0)
done:
    lw $t8,0($sp)
    addiu $sp,$sp,8
    move $t0,$a1
    j 0x8004a7e0
    sltiu $v0,$t0,320
'''%MAGIC
    if transition_clip:
        assert json.loads((ROOT/'work/font/efont.json').read_text(encoding='utf-8')).get('stable_encoding')
        # Stable builds replace the whole native lookup. Reclaim its unused
        # trampoline so clipping fits below the existing heap boundary.
        labels['lookup']=0x8004a7d8
    else:
        code('lookup',legacy_lookup)
    save='\n'.join('sw $s%d,%d($sp)'%(i,40+i*4) for i in range(8))
    restore='\n'.join('lw $s%d,%d($sp)'%(i,40+i*4) for i in range(8))
    draw_source='''addiu $sp,$sp,-80
    %s
    sw $ra,72($sp)
    mfhi $t0
    mflo $t1
    sw $t0,24($sp)
    sw $t1,28($sp)
    move $s0,$a0
    move $s1,$a1
    move $s2,$a2
    lui $t0,0x800c
    ori $t0,$t0,0x6c10
    subu $t0,$a0,$t0
    sltiu $t0,$t0,0x23dc
    beqz $t0,fallback
    nop
    lhu $t0,0x1a($a0)
    addiu $t1,$zero,%d
    bne $t0,$t1,fallback
    nop
    lw $t0,0($a0)
    lhu $a0,0x18($a0)
    bltz $t0,done
    addiu $a1,$sp,16
    sltiu $t0,$a0,320
    jal %d
    sw $t0,20($sp)
    beqz $v1,fallback
    move $s3,$v0
    move $s4,$v1
    lw $t0,4($s1)
    lw $t1,8($s1)
    andi $s2,$s2,0xffff
    sll $s2,$s2,2
    sll $t1,$t1,2
    addu $s1,$s2,$t0
    subu $s1,$s1,$t1
    lw $s2,0x14($s0)
    lui $t0,0xff
    ori $t0,$t0,0xffff
    and $s2,$s2,$t0
    lui $t0,0x2e00
    or $s2,$s2,$t0
    lh $s5,4($s0)
    lh $s6,6($s0)
    lui $t0,0x800d
    lh $t1,0x3d2c($t0)
    lh $t2,0x3d2e($t0)
    addu $s5,$s5,$t1
    addu $s6,$s6,$t2
    lhu $t0,0x10($s0)
    lhu $s7,0x12($s0)
    srl $t0,$t0,4
    andi $t0,$t0,0x3f
    ori $s7,$s7,1
    sll $s7,$s7,6
    or $s7,$s7,$t0
    sll $s7,$s7,16
loop:
    lbu $t0,0($s3)
    lui $t1,0x800d
    ori $t1,$t1,%d
    sll $t0,$t0,1
    addu $t0,$t0,$t1
    lbu $t1,0($t0)
    lbu $t2,1($t0)
    nop
    andi $t4,$t2,31
    andi $t2,$t2,0xe0
    sll $t3,$t4,1
    lui $t5,0x800d
    lw $t5,0x3df0($t5)
    lw $t6,0x33c($gp)
    addiu $t7,$t5,40
    sll $t6,$t6,2
    addiu $t8,$gp,0x38
    addu $t6,$t6,$t8
    lw $t6,0($t6)
    lui $t8,1
    ori $t8,$t8,0x8000
    addu $t6,$t6,$t8
    sltu $t6,$t6,$t7
    bnez $t6,done
    move $t6,$s5
    lw $t8,20($sp)
    nop
    beqz $t8,position
    nop
    lh $t8,8($s0)
    nop
    subu $t8,$t8,$t4
    sra $t8,$t8,1
    addu $t6,$t6,$t8
position:
    andi $t6,$t6,0xffff
    sll $t8,$s6,16
    or $t6,$t6,$t8
    sw $s2,4($t5)
    sw $t6,8($t5)
    addu $t6,$s5,$t4
    lw $t8,20($sp)
    nop
    beqz $t8,right
    nop
    lh $t8,8($s0)
    nop
    subu $t8,$t8,$t4
    sra $t8,$t8,1
    addu $t6,$t6,$t8
right:
    andi $t6,$t6,0xffff
    sll $t8,$s6,16
    or $t6,$t6,$t8
    sw $t6,16($t5)
    lw $t6,8($t5)
    lui $t8,0x10
    addu $t6,$t6,$t8
    sw $t6,24($t5)
    lw $t6,16($t5)
    nop
    addu $t6,$t6,$t8
    sw $t6,32($t5)
    sll $t6,$t2,8
    or $t6,$t6,$t1
    or $t8,$t6,$s7
    sw $t8,12($t5)
    addu $t8,$t6,$t3
    lui $t9,0x1c
    or $t8,$t8,$t9
    sw $t8,20($t5)
    addiu $t6,$t6,0x2000
    sw $t6,28($t5)
    addu $t6,$t6,$t3
    sw $t6,36($t5)
    lw $t6,0($s1)
    lui $t8,0xff
    ori $t8,$t8,0xffff
    and $t6,$t6,$t8
    lui $t9,0x900
    or $t6,$t6,$t9
    sw $t6,0($t5)
    and $t6,$t5,$t8
    sw $t6,0($s1)
    lui $t8,0x800d
    sw $t7,0x3df0($t8)
next:
    addu $s5,$s5,$t4
    addiu $s4,$s4,-1
    bnez $s4,loop
    addiu $s3,$s3,1
    b done
    nop
fallback:
    move $a0,$s0
    move $a1,$s1
    jal 0x80088bb8
    move $a2,$s2
done:
    lw $t0,24($sp)
    lw $t1,28($sp)
    mthi $t0
    mtlo $t1
    %s
    lw $ra,72($sp)
    addiu $sp,$sp,80
    jr $ra
    nop
'''%(save,MAGIC,labels['token'],labels['glyphs']&0xffff,restore)
    if transition_clip:
        draw_source=draw_source.replace('''    lw $t0,0($a0)
    lhu $a0,0x18($a0)
    bltz $t0,done
    addiu $a1,$sp,16''','''    lw $t0,0($a0)
    lhu $t1,8($a0)
    bltz $t0,done
    lhu $t2,0xa($a0)
    beqz $t1,done
    nop
    beqz $t2,done
    lhu $a0,0x18($s0)
    addiu $a1,$sp,16''')
        draw_source=draw_source.replace('''    sll $s7,$s7,16
loop:''','''    sll $s7,$s7,16
    lhu $a3,0xa($s0)
loop:''')
        # The native clear scrolls Y up, then clips rows by advancing the old
        # 16px cell V and reducing H. Apply that crop to the 32px atlas too.
        draw_source=draw_source.replace('''    andi $t2,$t2,0xe0''','''    andi $t2,$t2,0xe0
    lbu $t8,0xf($s0)
    nop
    andi $t8,$t8,15
    sll $t8,$t8,1
    addu $t2,$t2,$t8''')
        draw_source=draw_source.replace('''    lui $t8,0x10''','''    sll $t8,$a3,16''')
        draw_source=draw_source.replace('''    addiu $t6,$t6,0x2000''','''    sll $t8,$a3,9
    addu $t6,$t6,$t8''')
    if native_ui:
        assert transition_clip
        # Native F1 icons share these palettes. Keep their original shades;
        # font ink uses an opaque FT4 so the native STP flag cannot dim it.
        draw_source=draw_source.replace('lui $t0,0x2e00','lui $t0,0x2c00')
    code('draw',draw_source)
    assert B+len(second)<=LIMIT_B,('native font code exceeds private space',len(second))
    assert struct.unpack_from('<I',out,mips.off(0x800155f0))[0]==0x0c0222ee
    out[mips.off(A):mips.off(A)+len(first)]=first
    out[mips.off(I):mips.off(I)+96]=pairs[128:224]
    out[mips.off(B):mips.off(B)+len(second)]=second
    struct.pack_into('<II',out,mips.off(0x8004a7d8),0x08000000|((labels['lookup']>>2)&0x3ffffff),0)
    stable=json.loads((ROOT/'work/font/efont.json').read_text(encoding='utf-8')).get('stable_encoding')
    if stable:
        code=stable_lookup(labels)
        room=0x8004a954-0x8004a7d8
        assert len(code)<=room,('stable lookup too large',len(code),room)
        out[mips.off(0x8004a7d8):mips.off(0x8004a954)]=code+bytes(room-len(code))
    if native_ui:
        # Numeric and icon drawers can reuse a text object without calling
        # glyph lookup. Its previous font token marker must not survive.
        labels['allocate']=0x8004a7d8+len(code)
        cleanup=rb.asm('''sh $zero,0x1a($s2)
        move $v0,$s2
        j 0x8004c28c
        lw $ra,0x20($sp)''',labels['allocate'])
        assert labels['allocate']+len(cleanup)<=0x8004a954
        assert out[mips.off(0x8004c284):mips.off(0x8004c28c)]==struct.pack('<II',0x02401021,0x8fbf0020)
        out[mips.off(labels['allocate']):mips.off(labels['allocate'])+len(cleanup)]=cleanup
        struct.pack_into('<II',out,mips.off(0x8004c284),0x08000000|((labels['allocate']>>2)&0x3ffffff),0)
    struct.pack_into('<I',out,mips.off(0x800155f0),0x0c000000|((labels['draw']>>2)&0x3ffffff))
    info={'labels':{k:hex(v) for k,v in labels.items()},'data_a':[hex(A),hex(A+len(first))],
        'data_i':[hex(I),hex(I+96)],'data_b':[hex(B),hex(labels['token'])],'code_end':hex(B+len(second)),
        'atlas_rows':rows,'original_vram_allocation_retained':True,'packet_buffer_bytes':0x1c000,
        'font_packet_limit':0x18000,'primitive':'POLY_FT4 semi-transparent, blend mode 0',
        'coverage':'Faint edge half-blended; solid ink opaque','emulator_replacements_required':False,
        'native_transition_clipping':transition_clip,'native_ui_compatibility':native_ui}
    if native_ui:
        info['primitive']='POLY_FT4 opaque, native shared palettes'
        info['coverage']='Original F1 palette shades, opaque ink; native badges retain their shades'
    if stable:info['stable_encoding']=stable;info['stable_lookup_bytes']=len(code)
    return (bytes(out),info) if report else bytes(out)
