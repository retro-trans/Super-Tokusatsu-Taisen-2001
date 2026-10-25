"""Completed-disc font, source-mask, dialogue and replacement-ID checks."""
import argparse,hashlib,json,struct
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
import cm,efont,gfx,mips,repack,texpack,rayblade_font as R
import check_dialogue_layout as dialogue
from check_graphics_build import directory,read_file,file_hash
from check_balance import Machine

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--version',default='0.3.30')
    p.add_argument('--movie-baseline',help='Approved movie revision to retain, independently of the font baseline')
    a=p.parse_args()
    out=ROOT/'work/output';disc=out/('STT2001_EN_v'+a.version+'.bin');old=out/'STT2001_EN_v0.3.29.bin'
    nd,od=directory(disc),directory(old)
    movie_old=out/('STT2001_EN_v'+a.movie_baseline+'.bin') if a.movie_baseline else old
    movie_od=directory(movie_old)
    archives={n:repack.dat_entries(read_file(disc,nd[n+'.DAT'])) for n in ('MAPMAIN','BATTLE','EVENT','STAGE')}
    mm,bt,ev=archives['MAPMAIN'],archives['BATTLE'],archives['EVENT']
    meta=json.loads((ROOT/'work/font/efont.json').read_text(encoding='utf-8'))
    prior=json.loads((out/'font-baseline-v0.3.29/efont.json').read_text(encoding='utf-8'))
    old_reverse={v:k for k,v in {**prior['encode'],**prior['encode_ex']}.items()}
    assert set(meta['uni'])==set(prior['uni']) and set(meta['bi'])==set(prior['bi']) and set(meta['ex'])==set(prior['ex'])
    font=R.Font();blob=font.blob;source={}
    for ch in R.ASCII:
        i=R.MEDIUM.index(ch);glyph=np.zeros((64,48),np.uint8)
        for y in range(64):
            left,right=struct.unpack_from('<II',blob,0x8200+i*512+y*8)
            for x in range(32):glyph[y,x]=((left if x<16 else right)>>(30-2*(x%16)))&3
        assert np.array_equal(texpack.HiFont().char(ch),glyph)
        assert meta['widths'][ch]==blob[0xa0+i]
        assert not glyph[:,meta['widths'][ch]*4:].any(),ch
        source[ch]=glyph
    cells=np.load(ROOT/'work/font/efont_cells.npz')
    sheets=[('MAPMAIN7',mm[7],True,True,256),('MAPMAIN25',cm.blocks(mm[25])[3],True,True,256),
        ('BATTLE537',bt[537],True,False,256),('BATTLE538',bt[538],True,True,256),('EVENT10',ev[10],True,True,256)]+[
        ('EVENT'+str(i),ev[i],False,True,0) for i in range(11,24)]
    checked=0
    for name,tim,main,extra,offset in sheets:
        pixels=gfx.Tim(tim).idx
        if main:
            for i in range(len(meta['uni'])):
                _,_,x,y=texpack.cell_xy(efont.UNI_FIRST+i)
                assert np.array_equal(pixels[y:y+16,x:x+12]&3,cells['uni'][i]),(name,'uni',i)
                checked+=1
            if meta.get('native_2x'):
                import native_font2x
                assert np.array_equal((pixels[:,:256]>>2)&3,native_font2x.assets()[0]),name
            for i in range(0 if meta.get('native_2x') else len(meta['bi'])):
                _,_,x,y=texpack.cell_xy(efont.BI_FIRST+i)
                assert np.array_equal((pixels[y:y+16,x:x+12]>>2)&3,cells['bi'][i]),(name,'bi',i)
                checked+=1
        if extra:
            for i,code in enumerate(efont.EX_SLOTS[:len(meta['ex'])]):
                _,_,x,y=texpack.cell_xy(code);x+=offset
                assert np.array_equal(pixels[y:y+16,x:x+24]&3,cells['ex'][i]),(name,'ex',i)
                checked+=1
    exe=read_file(disc,nd['SLPS_028.63']);cpu=Machine(exe)
    glyphs={**meta['encode'],**meta['encode_ex']}
    for token,code in glyphs.items():
        cpu.run(0x8004a7d8,0x80150000,code)
        width=struct.unpack('<H',cpu.cpu.mem_read(0x150008,2))[0]
        assert width==sum(meta['widths'][c] for c in token),(token,width)
    stats=Counter()
    os=repack.dat_entries(read_file(old,od['STAGE.DAT']))
    for i,key in enumerate(sorted(dialogue.D.STAGE_VAR)):
        index=int(key);new=archives['STAGE'][index]
        dialogue.overlay(os[index],new,0,'stage',stats,old_reverse=old_reverse)
        assert cm.blocks(archives['STAGE'][630+i])[4]==new[:len(cm.blocks(archives['STAGE'][630+i])[4])]
    ob=repack.dat_entries(read_file(old,od['BATTLE.DAT']))
    for before,after in zip(ob,bt):
        if len(before)>0x8438 and before[:4]==b'\x10\0\0\0' and struct.unpack_from('<I',before,0x8434)[0]>>16==0x800e:
            dialogue.overlay(before,after,0x8434,'bquote',stats,old_reverse=old_reverse)
    unchanged=[]
    for name in ('SOUND.DAT','MOVIE.STR','VORTEX.XA','WAZA1.DAT','WAZA2.DAT','WAZA3.DAT','SYSTEM.CNF'):
        reference,table=(movie_old,movie_od) if name=='MOVIE.STR' else (old,od)
        assert file_hash(reference,table[name])==file_hash(disc,nd[name]),name
        unchanged.append(name)
    for name in ('MOVIE.STR','VORTEX.XA'):
        reference,table=(movie_old,movie_od) if name=='MOVIE.STR' else (old,od)
        assert table[name]==nd[name]
        remain=((nd[name]['size']+2047)//2048)*2352
        with reference.open('rb') as x,disc.open('rb') as y:
            x.seek(nd[name]['lba']*2352);y.seek(nd[name]['lba']*2352)
            while remain:
                n=min(remain,4*1024*1024);assert x.read(n)==y.read(n);remain-=n
    # Every texture filename must match a completed native upload and palette.
    import xxhash
    part_sheets=[mm[7],bt[538],bt[537]]+ev[11:24]
    parts=[texpack.tim_parts(t) for t in part_sheets];pals=texpack.palettes([p[3] for p in parts])
    valid=set()
    for pixels,(iw,ih),upload,clut in parts:
        for page in range(pixels.shape[1]//256):
            valid.add((upload,iw,page*256))
            block=pixels[:,page*256:(page+1)*256]
            raw=(block[:,0::2]|(block[:,1::2]<<4)).astype(np.uint8).tobytes()
            valid.add((xxhash.xxh3_64_intdigest(raw),64,0))
    folder=out/('STT2001_EN_v'+a.version+'_4x_font/SLPS-02863')
    pngs=list((folder/'replacements').glob('*.png'));assert pngs
    core_checks=0;mainhash=texpack.tim_parts(mm[7])[2]
    for path in pngs:
        bits=path.name.split('-');h=int(bits[2],16);ph=int(bits[3],16)
        iw=int(bits[4].split('x')[0]);x=int(bits[5]);assert (h,iw,x) in valid and ph in pals,path.name
        im=Image.open(path);assert im.size==(1024,1024);im.verify()
        if h==mainhash and x==0:
            layer,row=pals[ph]
            if layer:continue
            rgba=np.asarray(Image.open(path).convert('RGBA'))
            for ch,glyph in source.items():
                code=meta['encode'][ch];_,_,cx,cy=texpack.cell_xy(code)
                pixels=rgba[cy*4:(cy+16)*4,cx*4:(cx+12)*4]
                for level in (1,2,3):
                    mask=glyph==level
                    if not mask.any():continue
                    color=row[level];expected=texpack.c15(color)+(texpack.STP_ALPHA if bits[1]=='STP4' and color&0x8000 else 255,)
                    assert (pixels[mask]==expected).all(),(path.name,ch,level)
                core_checks+=1
    assert core_checks>=95
    assert 'MaxVRAMWriteSplits: true' in (folder/'config.yaml').read_text()
    gfx.Tim(mm[19]).rgb().save(out/('STT2001_EN_v'+a.version+'_title_preview.png'))
    report={'version':a.version,'font_source':R.provenance(native_2x=meta.get('native_2x',False)),'native_2x':meta.get('native_2x',False),'exact_source_ascii_masks':95,
        'all_prior_glyph_tokens_preserved':True,'completed_sheet_glyph_checks':checked,'font_copies':len(sheets),
        'native_vwf_glyph_cases':len(glyphs),'dialogue':dict(stats),
        'dialogue_content_and_pointer_order_preserved':True,'unchanged_files':unchanged,
        'raw_movie_and_audio_sectors_unchanged':True,'movie_baseline':a.movie_baseline or '0.3.29',
        'texture_images':len(pngs),'texture_upload_ids_checked':True,
        'exact_source_texture_core_checks':core_checks,'emulator_playtest':False}
    dest=out/('STT2001_EN_v'+a.version+'_font_verification.json');dest.write_bytes((json.dumps(report,indent=1)+'\n').encode())
    print(json.dumps({k:v for k,v in report.items() if k!='font_source'},indent=1))


if __name__=='__main__':main()
