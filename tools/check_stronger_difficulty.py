"""Native controls, retained glyphs, save/load and three-profile gameplay checks."""
import argparse
import json
import struct
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.mips_const import *
import balance
import mips
import runtime_balance as rb
import difficulty_menu as menu
import repack
from check_balance import Machine,STATE,ACTOR
from check_runtime_balance import put,get
from check_difficulty_menu import Menu,GP
from check_difficulty_render import Sprites
from check_intermission_layout import text
from check_graphics_build import directory,read_file

ROOT=Path(__file__).resolve().parents[1]


def menu_checks(m,info):
    normal,gentle,strong=info['choice_names']
    pending=int(info['pending_choice'],16)
    samples=[]
    def capture(name):
        samples.append({'mode':name,'pending':m.get(pending,'<I'),'draws':list(m.draws)})
    def label(name):
        assert name in [text(d.get('codes',[])) for d in m.draws]
    assert m.get(0x800CC644)==6
    capture(normal)
    for row in range(5):
        m.put(GP+0x552,row);m.key(0x100)
        assert m.get(0x80100218,'<I')==0
    for row in (0,1,3,4):
        m.put(GP+0x552,row);assert m.key(0x20)==2
    m.put(GP+0x552,0)
    for expected in (1,2,3,4,5,0):
        m.key(0x4000);assert m.get(GP+0x552)==expected
    m.key(0x1000);assert m.get(GP+0x552)==5
    assert m.key(0x20)==0 and m.get(pending,'<I')==1
    for _ in range(30):
        m.key(0,0x20);assert m.get(pending,'<I')==1
    # Three-way wrap in both directions, including left/right alternatives.
    for key,choice in ((0x1000,3),(0x8000,2),(0x2000,3),(0x4000,1),
                       (0x4000,2),(0x4000,3)):
        m.key(key);assert m.get(pending,'<I')==choice
        assert m.get(0x80100218,'<I')==0
    capture('choosing '+strong)
    m.key(0x40);assert not m.get(pending,'<I') and not m.get(0x80100218,'<I')
    label(normal)
    m.key(0x20);m.key(0x4000);m.key(0x20)
    assert m.get(0x80100218,'<I')==rb.MAGIC;label('Gentle')
    m.key(0,0x20);assert not m.get(pending,'<I')
    m.key(0x20);assert m.get(pending,'<I')==2
    m.key(0x4000);m.key(0x20)
    assert m.get(0x80100218,'<I')==rb.STRONG_MAGIC;label(strong);capture(strong)
    m.key(0x20);assert m.get(pending,'<I')==3
    m.key(0x40);assert m.get(0x80100218,'<I')==rb.STRONG_MAGIC
    m.key(0x20);m.key(0x4000);m.key(0x20)
    assert m.get(0x80100218,'<I')==0;label(normal)
    for marker in (1,0xffffffff,0x424d0000,0x424d0003):
        m.put(0x80100218,marker,'<I');m.call(0x8005FDE0,(22,));label(normal)
        m.key(0x20);assert m.get(pending,'<I')==1
        m.key(0x40);assert m.get(0x80100218,'<I')==marker
    m.put(0x80100218,0,'<I')
    return {'three_choices_and_wrap_checked':True,'old_save_markers_preserved':True,
            'confirm_cancel_and_held_input_checked':True,
            'six_rows_and_original_actions_checked':True,'emulator_capture':False,
            'examples':samples,'patch':info}


def tests(exe,db,story_labels=False):
    names=['Default','Gentle','Story'] if story_labels else ['Normal','Gentle','Stronger']
    _,info=rb.patch_exe(mips.load(),True,support_stronger=True)
    labels={k:int(v,16) for k,v in info['labels'].items()}
    result={'stronger_prices':0,'stronger_purchases':0}
    a,b=Machine(exe),Machine(exe)
    for row in balance.plan():
        can,buy=(0x80069080,0x80069900) if row['table']=='unit_stats' else (0x8006939c,0x80069f08)
        args=(0,row['column']) if row['table']=='unit_stats' else (0,0,1)
        states=[]
        for m,flag in ((a,rb.MAGIC),(b,rb.STRONG_MAGIC)):
            m.fixture(row,row['funds'],row['funds']//2)
            put(m.cpu,STATE+rb.FLAG,flag)
            assert m.quote(row)==(row['funds'],row['funds']//2)
            assert m.run(can,*args)==1 and m.run(buy,*args)==1
            state=bytearray(m.state());state[rb.FLAG:rb.FLAG+4]=bytes(4);states.append(state)
        assert states[0]==states[1]
        # Switching from Stronger to Normal restores exact original prices.
        put(b.cpu,STATE+rb.FLAG,0)
        b.run(labels['prices_sync'])
        for address in balance.TABLES.values():
            assert bytes(b.cpu.mem_read(address&0x1fffffff,480))==mips.load()[mips.off(address):mips.off(address)+480]
        result['stronger_prices']+=1;result['stronger_purchases']+=1
    rewards=[]
    for funds,mat,xp in ((0,0,0),(101,57,301),(200000,123456,30000)):
        m=Machine(exe);c=m.cpu;put(c,STATE+rb.FLAG,rb.STRONG_MAGIC)
        c.mem_write(0xbd8d8,struct.pack('<IIh',funds,mat,xp))
        m.run(0x80047a18,end=0x80047a64)
        assert get(c,STATE+0x22c)==get(c,0xbd8d8)==funds*2
        assert get(c,STATE+0x234)==get(c,0xbd8dc)==mat*2
        assert get(c,0xbd8e0,'<h')==max(1,min(32767,xp*3))
        rewards.append({'input':[funds,mat,xp],'pending':[funds*2,mat*2,max(1,min(32767,xp*3))]})
    for xp in (1,301,10923,30000):
        m=Machine(exe);put(m.cpu,STATE+rb.FLAG,rb.STRONG_MAGIC)
        put(m.cpu,0xbd8e0,xp,'<h');m.run(0x80047ab4,end=0x80047ad4)
        assert get(m.cpu,0xbd8e0,'<h')==min(32767,xp*3)
    for kills in (0,1,255):
        m=Machine(exe);c=m.cpu;put(c,STATE+rb.FLAG,rb.STRONG_MAGIC)
        for reg,value in [(UC_MIPS_REG_T0,0x80100000),(UC_MIPS_REG_T7,0x800bd8d8),
                          (UC_MIPS_REG_T4,0x800c0000),(UC_MIPS_REG_V0,kills*200)]:c.reg_write(reg,value)
        m.run(0x80026d64,end=0x80026d94)
        assert get(c,STATE+0x22c)==get(c,STATE+0x234)==get(c,0xbd8d8)==get(c,0xbd8dc)==kills*400
    result['rewards']=rewards;result['xp_only_and_chapter_rewards_checked']=True
    # Check native working attack/armor and the complete damage function.
    combat=[]
    for attacker,defender in ((1,0),(0,1),(1,1),(0,0)):
        for attack,armor in ((100,20),(51,13),(255,255),(1,1)):
            m=Machine(exe);c=m.cpu;put(c,STATE+rb.FLAG,rb.STRONG_MAGIC)
            c.mem_write(ACTOR,bytes(50));put(c,ACTOR+26,armor,'<B')
            for address,value in [(STATE+0xe68,attack),(STATE+0xe6a,attack),(STATE+0xe70,100),
                (STATE+0x3e6c,0),(STATE+0x3e7c,armor),(STATE+0x3c7d,attack),
                (STATE+0x3c7e,attack),(STATE+0x3c80,100)]:put(c,address,value,'<B')
            c.mem_write(0x1ec000,bytes(0x2000));c.mem_write(0x1d0010,struct.pack('<6I',defender,0,0,0,1,80))
            working={}
            def capture(cpu,address,size,_):
                if address in (labels['combat_stats'],0x80054ae4):
                    working['before' if address==labels['combat_stats'] else 'after']=[cpu.reg_read(UC_MIPS_REG_S4),cpu.reg_read(UC_MIPS_REG_S1)]
            c.hook_add(UC_HOOK_CODE,capture)
            before=m.state();damage=m.run(0x800546b8,attacker,0,0,0)
            assert m.state()==before
            expected=[max(1,x*p//100) if x else 0 for x,p in zip(working['before'],(125 if attacker==1 else 75,125 if defender==1 else 75))]
            assert working['after']==expected,(attacker,defender,working,expected)
            combat.append({'attacker':attacker,'defender':defender,'working':working,'damage':damage})
    result['combat']=combat
    for actor in (0,1,199):
        for initial in (0,7,255):
            for fresh in (False,True):
                m=Machine(exe);c=m.cpu;put(c,STATE+rb.FLAG,rb.STRONG_MAGIC)
                c.mem_write(ACTOR+50*actor,bytes([2]));c.mem_write(ACTOR+50*actor+19,bytes([initial])*6)
                before=bytes(c.mem_read(ACTOR+50*actor,50))
                m.run(labels['stage_ammo'] if fresh else 0x8003d274,actor)
                assert get(c,ACTOR+50*actor+20,'<B')==(8 if initial==255 or fresh else initial)
                after=bytes(c.mem_read(ACTOR+50*actor,50));assert before[:19]==after[:19] and before[25:]==after[25:]
    result['ammo_cases']=18
    m=Machine(exe);c=m.cpu;put(c,STATE+rb.FLAG,rb.STRONG_MAGIC)
    for enemy in range(50):c.mem_write(STATE+0x3e6c+enemy*34,b'\xff')
    for address in (0x800428d4,0x80042be4):
        if address==0x80042be4:c.mem_write(STATE,bytes(0x45a0))
        c.reg_write(UC_MIPS_REG_A0,0x80170000);c.reg_write(UC_MIPS_REG_SP,0x801d0000);c.reg_write(UC_MIPS_REG_RA,0x80008000)
        c.emu_start(address,0x80008000,count=400000);assert c.reg_read(UC_MIPS_REG_PC)==0x80008000
    assert get(c,STATE+rb.FLAG)==rb.STRONG_MAGIC
    result['stronger_save_checksum_load_roundtrip']=True
    # Real retained sprites, including the tighter three-choice panel.
    s=Sprites(exe,db);s.call(0x8005c430,());s.put(GP+0x552,5);snapshots=[]
    for selected in range(1,4):
        s.key(0x20)
        # Each preceding selection was applied, so its row is initially active.
        if selected>1:s.key(0x4000)
        live=s.live(18);requests=[r for r in s.requests if r['group']==18]
        start=max(i for i,r in enumerate(requests) if r['x']==32 and r['y']==136);requests=requests[start:]
        assert [text(r['codes']) for r in requests][2:5]==names
        assert len(live)==sum(len([c for c in r['codes'] if c<0xff00]) for r in requests)
        assert any(g['x']==196 and g['y']==128+(selected-1)*16 and g['clut']==0xf6 for g in live)
        assert all(g['x']+g['width']<=304 and g['y']+g['height']<=192 for g in live if g['x']>=192)
        footer=s.live(13);assert footer and all(g['y']==200 for g in footer)
        snapshots.append({'state':names[selected-1],'difficulty_sprites':live,'footer_sprites':footer,'draw_requests':requests})
        s.key(0x20)
        assert s.get(0x80100218,'<I')==(0 if selected==1 else rb.MAGIC if selected==2 else rb.STRONG_MAGIC)
        assert text([r for r in s.requests if r['group']==18 and r['y']==136 and r['x']==200][-1]['codes'])==names[selected-1]
    result['native_retained_three_choice_sprites_checked']=True
    result['snapshots']=snapshots;result['emulator_capture']=False
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--version',default='0.3.29');p.add_argument('--verify',action='store_true');a=p.parse_args()
    story_labels=tuple(map(int,a.version.split('.'))) >= (0,3,29)
    out=ROOT/'work/output';base=out/'STT2001_EN_v0.3.23.bin';d=directory(base)
    path=out/('STT2001_EN_v%s.bin'%a.version)
    if a.verify:exe=read_file(path,directory(path)['SLPS_028.63'])
    else:
        import save_slot_layout
        exe=menu.patch_exe(save_slot_layout.patch_exe(rb.patch_exe(read_file(base,d['SLPS_028.63']),support_stronger=True)),support_stronger=True,story_labels=story_labels)
    font_disc=path if a.verify else base
    mm=repack.dat_entries(read_file(font_disc,directory(font_disc)['MAPMAIN.DAT']));r=tests(exe,mm[2],story_labels=story_labels);r['version']=a.version
    # The 2x renderer expands tokens into FT4 packets after object retention;
    # check_native_font2x reconstructs that actual drawing path instead.
    if not json.loads((ROOT/'work/font/efont.json').read_text(encoding='utf-8')).get('native_2x'):
        from check_difficulty_render import preview
        preview(mm[7],r,a.version,samples=[('v'+a.version+' - '+s['state'],
            s['difficulty_sprites']+s['footer_sprites']) for s in r['snapshots']])
    dest=path.with_name(path.stem+'_stronger_verification.json');dest.write_bytes((json.dumps(r,indent=1)+'\n').encode())
    print('PASS: '+str(dest))


if __name__=='__main__':main()
