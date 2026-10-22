"""Execute native MIPS paths for both states of the Gentle Balance setting."""
import argparse
import json
import struct
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.mips_const import *
import balance
import mips
import runtime_balance as rb
from check_balance import Machine, STATE, ACTOR

ROOT = Path(__file__).resolve().parents[1]
MASK = 0x1fffffff


def put(c, address, value, fmt='<I'):
    c.mem_write(address & MASK,struct.pack(fmt,value))


def get(c, address, fmt='<I'):
    return struct.unpack(fmt,c.mem_read(address & MASK,struct.calcsize(fmt)))[0]


def mode(m, value):
    put(m.cpu,STATE+rb.FLAG,rb.MAGIC if value else 0)


def verify(exe, db=None):
    _,info = rb.patch_exe(mips.load(),True)
    labels = {k:int(v,16) for k,v in info['labels'].items()}
    original = mips.load()
    visible_menu = exe[mips.off(0x8005CBF8):mips.off(0x8005CBFC)] != rb.patch_exe(original)[mips.off(0x8005CBF8):mips.off(0x8005CBFC)]
    result = {'price_rows':0,'purchases':0,'rejected_purchases':0}
    ref,game = Machine(original),Machine(exe)
    for row in balance.plan():
        stat = row['table']=='unit_stats'
        can,buy=(0x80069080,0x80069900) if stat else (0x8006939c,0x80069f08)
        args=(0,row['column']) if stat else (0,0,1)
        expected = None
        # OFF after ON checks restore original prices, with no compounded cuts.
        for on in (False,True,True,False):
            price = row['funds'] if on else row['original_funds']
            for m,p in ((ref,row['original_funds']),(game,price)):
                m.fixture(row,p,p//2)
                if m is game:
                    mode(m,on)
                assert m.quote(row)==(p,p//2),('quote',on,row)
                assert m.run(can,*args)==1
                assert m.run(buy,*args)==1
                state = bytearray(m.state())
                state[rb.FLAG:rb.FLAG+4]=bytes(4)
                if m is ref:
                    expected=state
                else:
                    assert state==expected,('purchase changed gains/state',on,row)
                    result['purchases']+=1
            for funds,mat in ((price-1,price//2),(price,price//2-1)):
                game.fixture(row,funds,mat)
                mode(game,on)
                before=game.state()
                assert game.run(can,*args)==0
                assert game.run(buy,*args)==0
                assert game.state()==before
                result['rejected_purchases']+=1
        result['price_rows']+=1

    if not visible_menu:
        # Main intermission Select only. Other inputs and submenus cannot toggle.
        m=Machine(exe);c=m.cpu
        put(c,0x180000,0,'<h')
        for state,buttons,expected in ((0,0,0),(1,0x100,0),(0,0x100,rb.MAGIC),
                                       (2,0x100,rb.MAGIC),(0,0x100,0),(0,0x20,0)):
            put(c,0x180000,state,'<h')
            c.reg_write(UC_MIPS_REG_S1,buttons)
            m.run(labels['input'],0x80180000)
            assert get(c,STATE+rb.FLAG)==expected
            assert c.reg_read(UC_MIPS_REG_V1)==state
        result['toggle_checks']=6
    else:
        from check_difficulty_menu import tests
        assert db is not None
        result['difficulty_menu']=tests(exe,db)
        result['toggle_checks']='native root menu confirm/cancel/held input'
    m=Machine(exe);c=m.cpu
    # Exact marker needed: unrelated bytes in an older save cannot enable mode.
    for bad in (0,1,0xffffffff,0x424d0000,0x424d0002):
        put(c,STATE+rb.FLAG,bad)
        m.run(labels['prices_sync'])
        for address in balance.TABLES.values():
            assert bytes(c.mem_read(address&MASK,480))==original[mips.off(address):mips.off(address)+480]
    result['old_state_defaults_off']=True

    # Original save packer copies +0..3C77 verbatim and includes it in the
    # native 16 KiB checksum. Execute packing/loading rather than copying a
    # synthetic flag ourselves. Empty enemy roster avoids unrelated growth.
    for on in (False,True):
        m=Machine(exe);c=m.cpu;mode(m,on)
        for enemy in range(50):
            c.mem_write(STATE+0x3e6c+enemy*34,b'\xff')
        for address in (0x800428d4,0x80042be4):
            if address==0x80042be4:
                assert get(c,0x170000+rb.FLAG)==(rb.MAGIC if on else 0)
                c.mem_write(STATE,bytes(0x45a0))
            c.reg_write(UC_MIPS_REG_A0,0x80170000)
            c.reg_write(UC_MIPS_REG_SP,0x801d0000)
            c.reg_write(UC_MIPS_REG_RA,0x80008000)
            c.emu_start(address,0x80008000,count=400000)
            assert c.reg_read(UC_MIPS_REG_PC)==0x80008000,hex(c.reg_read(UC_MIPS_REG_PC))
            assert c.reg_read(UC_MIPS_REG_SP)==0x801d0000
        assert get(c,STATE+rb.FLAG)==(rb.MAGIC if on else 0)
    result['native_save_pack_checksum_and_load_roundtrip']=True

    # Execute startup BSS clear and stop at BIOS InitHeap. Injected code must
    # survive the clear, and heap must begin beyond the reserved code area.
    m=Machine(exe);c=m.cpu
    code=bytes(c.mem_read(rb.START&MASK,rb.LIMIT-rb.START))
    c.reg_write(UC_MIPS_REG_RA,0x80008000)
    c.emu_start(0x8005b8ac,0x8005b8d0,count=400000)
    assert bytes(c.mem_read(0xbd350,0xdc368-0xbd350))==bytes(0xdc368-0xbd350)
    c.emu_start(0x8005b8d0,0x80081788,count=400000)
    assert c.reg_read(UC_MIPS_REG_PC)==0x80081788
    assert c.reg_read(UC_MIPS_REG_A0)==rb.LIMIT+4
    assert bytes(c.mem_read(rb.START&MASK,len(code)))==code
    result['native_boot_bss_clear_and_heap_reservation_checked']=True

    if not visible_menu:
        # Execute the native drawing wrapper; intercept only sprite submission.
        # Capture actual encoded words/coordinates for the layout artifact.
        from check_dialogue_layout import width
        from check_intermission_layout import text
        draws=[]
        m=Machine(exe);c=m.cpu
        def capture(cpu,address,size,_):
            if address==0x8004a954:
                sp=cpu.reg_read(UC_MIPS_REG_SP)&MASK
                pointer=get(cpu,sp+16)&MASK
                codes=[]
                for i in range(100):
                    word=get(cpu,pointer+i*2,'<H')
                    if word in (0xfffd,0xfffe):
                        break
                    codes.append(word)
                else:
                    raise AssertionError('unterminated Balance label')
                x=cpu.reg_read(UC_MIPS_REG_A1);y=cpu.reg_read(UC_MIPS_REG_A2)
                assert cpu.reg_read(UC_MIPS_REG_A0)==13
                assert get(cpu,sp+20)==3
                w=sum(width(code) for code in codes)
                assert 8<=x and x+w<=312 and 152<=y and y+16<=196
                draws.append({'x':x,'y':y,'width':w,'text':text(codes),'codes':codes})
                cpu.reg_write(UC_MIPS_REG_V0,x+w)
            elif address!=0x8004bf8c:
                return
            cpu.reg_write(UC_MIPS_REG_PC,cpu.reg_read(UC_MIPS_REG_RA))
        c.hook_add(UC_HOOK_CODE,capture)
        examples=[]
        for on in (False,True):
            mode(m,on)
            for menu in range(57):
                c.reg_write(UC_MIPS_REG_S6,menu)
                draws.clear()
                m.run(labels['draw'])
                if menu==0:
                    assert [d['text'] for d in draws]==['Balance: '+('ON' if on else 'OFF'),'Select: Change']
                    examples.append({'on':on,'draws':list(draws)})
                else:
                    assert not draws
        result['native_setting_draw_checks']=114
        result['setting_layout']=examples

    else:
        result['setting_layout']=result['difficulty_menu']['examples']
        result['native_setting_draw_checks']='full root renderer, Normal / Gentle / pending choice'
    # Native reward commit, including pending displayed values. No GUI mocks.
    reward_cases=[]
    for on in (False,True):
        for funds,mat,xp in ((0,0,0),(101,57,301),(200000,123456,30000)):
            m=Machine(exe);c=m.cpu;mode(m,on)
            put(c,STATE+0x22c,1000);put(c,STATE+0x234,2000)
            c.mem_write(0xbd8d8,struct.pack('<IIh',funds,mat,xp))
            m.run(0x80047a18,end=0x80047a64)
            f=funds*3//2 if on else funds
            t=mat*3//2 if on else mat
            x=min(32767,xp*3//2) if on else xp
            assert get(c,STATE+0x22c)==1000+f
            assert get(c,STATE+0x234)==2000+t
            assert get(c,0xbd8d8)==f and get(c,0xbd8dc)==t
            assert get(c,0xbd8e0,'<h')==max(1,x),(on,xp,get(c,0xbd8e0,'<h'),x)
            reward_cases.append({'on':on,'input':[funds,mat,xp],'pending':[f,t,max(1,x)]})
        # Non-kill XP-only branch must receive the same boost, once.
        m=Machine(exe);c=m.cpu;mode(m,on)
        put(c,0xbd8e0,301,'<h')
        m.run(0x80047ab4,end=0x80047ad4)
        assert get(c,0xbd8e0,'<h')==(451 if on else 301)
        # Chapter reward uses the same pending/display buffer as actual payout.
        for kills in (0,1,255):
            m=Machine(exe);c=m.cpu;mode(m,on)
            c.reg_write(UC_MIPS_REG_T0,0x80100000)
            c.reg_write(UC_MIPS_REG_T7,0x800bd8d8)
            c.reg_write(UC_MIPS_REG_T4,0x800c0000)
            amount=kills*200
            c.reg_write(UC_MIPS_REG_V0,amount)
            m.run(0x80026d64,end=0x80026d94)
            amount=amount*3//2 if on else amount
            assert get(c,STATE+0x22c)==get(c,STATE+0x234)==amount
            assert get(c,0xbd8d8)==get(c,0xbd8dc)==amount
    result['rewards']=reward_cases
    result['xp_only_and_stage_rewards_checked']=True
    # Execute the unchanged native cap before its level-growth/skill loop.
    for initial,award in ((0,1),(48990,30),(49000,32767)):
        ref,game=Machine(original),Machine(exe)
        for m in (ref,game):
            for actor in range(200):
                m.cpu.mem_write(ACTOR+actor*50,b'\xff')
            m.cpu.mem_write(STATE+0xe60,struct.pack('<H',initial))
            m.cpu.reg_write(UC_MIPS_REG_A0,0)
            m.cpu.reg_write(UC_MIPS_REG_A1,award)
            m.cpu.reg_write(UC_MIPS_REG_SP,0x801d0000)
            m.cpu.emu_start(0x800343dc,0x80034478,count=200)
            assert m.cpu.reg_read(UC_MIPS_REG_PC) in (0x80034478,0x80034474),hex(m.cpu.reg_read(UC_MIPS_REG_PC))
            assert m.cpu.reg_read(UC_MIPS_REG_S1)==min(max(1,award),49000-initial)
        assert game.state()==ref.state()
        assert get(game.cpu,STATE+0xe60,'<H')<=49000
    assert exe[mips.off(0x800343dc):mips.off(0x800348c0)]==original[mips.off(0x800343dc):mips.off(0x800348c0)]
    assert exe[mips.off(0x800790b8):mips.off(0x800790bc)]==original[mips.off(0x800790b8):mips.off(0x800790bc)]
    result['native_xp_cap_and_scripted_level_setter_unchanged']=True

    # Fresh-stage setup versus the untouched general initializer (transform,
    # upgrade, resume). Last actor catches address-stride errors.
    ammo_cases=0
    for on in (False,True):
        for actor in (0,1,199):
            for initial in (0,7,255):
                for fresh in (False,True):
                    m=Machine(exe);c=m.cpu;mode(m,on)
                    c.mem_write(ACTOR+50*actor,bytes([2]))
                    c.mem_write(ACTOR+50*actor+19,bytes([initial])*6)
                    before=bytes(c.mem_read(ACTOR+50*actor,50))
                    address=labels['stage_ammo'] if fresh else 0x8003d274
                    m.run(address,actor)
                    # slot 1 is the known 8-round weapon; native source data.
                    assert get(c,ACTOR+50*actor+20,'<B')==(8 if initial==255 or on and fresh else initial)
                    after=bytes(c.mem_read(ACTOR+50*actor,50))
                    assert before[:19]==after[:19] and before[25:]==after[25:]
                    ammo_cases+=1
    assert exe[mips.off(0x8001809c):mips.off(0x800180fc)]==original[mips.off(0x8001809c):mips.off(0x800180fc)]
    result['ammo_cases']=ammo_cases
    result['native_resume_branch_unchanged']=True

    # Complete native attack-minus-defense formula, for both sides including
    # allied targets/friendly fire. No stat writes or fake terrain functions.
    combat=[]
    for attacker,defender in ((1,0),(0,1),(1,1),(0,0)):
        for attack,armor in ((100,20),(51,13),(255,255)):
            amounts=[]
            for image,on in ((original,False),(exe,False),(exe,True)):
                m=Machine(image);c=m.cpu;mode(m,on)
                c.mem_write(ACTOR,bytes([0])*50)
                put(c,ACTOR+26,armor,'<B')
                put(c,STATE+0xe68,attack,'<B')
                put(c,STATE+0xe6a,attack,'<B')
                put(c,STATE+0xe70,100,'<B')
                put(c,STATE+0x3e6c,0,'<B');put(c,STATE+0x3e7c,armor,'<B')
                put(c,STATE+0x3c7d,attack,'<B');put(c,STATE+0x3c7e,attack,'<B')
                put(c,STATE+0x3c80,100,'<B')
                # Neutral A terrain on native maps (terrain/rank lookups intact).
                c.mem_write(0x1ec000,b'\0'*0x2000)
                c.mem_write(0x1d0010,struct.pack('<6I',defender,0,0,0,1,80))
                before=m.state()
                damage=m.run(0x800546b8,attacker,0,0,0)
                assert m.state()==before, 'damage calculation mutated saved stats'
                amounts.append(damage)
            assert amounts[0]==amounts[1], ('OFF damage differs',combat)
            if attacker==1 and defender==0:
                assert amounts[2]>=amounts[1]
            if attacker==0 and defender==1:
                assert amounts[2]<=amounts[1]
            combat.append({'attacker':attacker,'defender':defender,'attack':attack,'armor':armor,'damage':amounts})
    assert any(r['damage'][2]!=r['damage'][1] for r in combat)
    result['combat']=combat

    # Audit every injected instruction for PS1 load delay hazards. Unicorn
    # does not emulate these delays. Explicit nops also protect return loads.
    hazards=[]
    code_data=exe[mips.off(rb.START):mips.off(rb.LIMIT)]
    instructions=list(mips.md.disasm(code_data,rb.START))
    data_ranges=[(labels['prices'],labels['prices_sync']),
                 (labels['off'],labels['draw'])]
    if any(exe[mips.off(0x800dd000):mips.off(0x800dd050)]):
        import save_slot_layout
        _,save_info=save_slot_layout.patch_exe(rb.patch_exe(mips.load()),True)
        # Save-caption private data precedes its first measured-width helper.
        data_ranges.append((save_slot_layout.START,int(save_info['labels']['measure'],16)))
    if visible_menu:
        import difficulty_menu
        _,menu_info=difficulty_menu.patch_exe(exe,True)
        ml={k:int(v,16) for k,v in menu_info['labels'].items()}
        data_ranges.extend([(ml['pending_choice'],ml['input']),(ml['row'],ml['draw'])])
    for i,j in zip(instructions,instructions[1:]):
        if any(a<=i.address<b for a,b in data_ranges):
            continue
        if i.mnemonic in ('lw','lh','lhu','lb','lbu'):
            reg=i.op_str.split(',')[0]
            # Overwriting a load result is also hazardous; exempt zero only.
            if reg in j.op_str.split(', ') or ('('+reg+')') in j.op_str:
                hazards.append([hex(i.address),i.mnemonic+' '+i.op_str,j.mnemonic+' '+j.op_str])
    assert not hazards,hazards
    result['ps1_load_delay_hazards']=hazards
    hilo=[]
    for index,i in enumerate(instructions):
        if any(a<=i.address<b for a,b in data_ranges):
            continue
        if i.mnemonic in ('mfhi','mflo'):
            for j in instructions[index+1:index+3]:
                if j.mnemonic in ('mult','multu','div','divu'):
                    hilo.append([hex(i.address),hex(j.address)])
    assert not hilo,hilo
    result['ps1_hi_lo_hazards']=hilo
    result['runtime_info']=info
    result['full_emulator_campaign_verified']=False
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true')
    parser.add_argument('--version',default='0.3.24')
    args=parser.parse_args()
    if not args.verify:
        print('Dry run. Use --verify to execute native MIPS regression tests.')
        return
    path=ROOT/('work/output/STT2001_EN_v%s.bin'%args.version)
    if path.exists() and path.with_name(path.stem+'_report.json').exists():
        from check_graphics_build import directory,read_file
        exe=read_file(path,directory(path)['SLPS_028.63'])
    else:
        exe=rb.patch_exe(mips.load())
    db=None
    if path.exists():
        import repack
        db=repack.dat_entries(read_file(path,directory(path)['MAPMAIN.DAT']))[2]
    report=verify(exe,db)
    dest=path.with_name(path.stem+'_runtime_balance_verification.json')
    dest.write_text(json.dumps(report,indent=1)+'\n',encoding='utf-8')
    ui=ROOT/'work/ui/balance'
    ui.mkdir(parents=True,exist_ok=True)
    (ui/'layout.en.json').write_text(json.dumps({'version':args.version,
        'screen':'Intermission main menu','button':('Difficulty menu' if tuple(map(int,args.version.split('.'))) >= (0,3,26) else 'Select'),'default':'Normal',
        'footer_y':200,'native_font_height':16,'examples':report['setting_layout'],
        'sprite_submission_modeled':True,'emulator_capture':False},indent=1)+'\n',encoding='utf-8')
    print('PASS: '+str(dest))


if __name__=='__main__':
    main()
