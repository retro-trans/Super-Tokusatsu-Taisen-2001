"""Verify actual inserted movie sectors, native video decode and disc identity."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import av
import numpy as np
import discimage
import movie_patch
import repack

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/output'

def directory(path):
    with path.open('rb') as f:
        f.seek(16*2352)
        pvd=f.read(2352)[24:2072]
        lba,size=struct.unpack_from('<I',pvd,158)[0],struct.unpack_from('<I',pvd,166)[0]
        data,recs=repack.read_dir(f,lba,size)
    return {name.decode().split(';')[0]:{'lba':struct.unpack_from('<I',data,off+2)[0],
            'size':struct.unpack_from('<I',data,off+10)[0]}
            for off,_,name in recs if name not in (b'\0',b'\1')}

def check_parity(raw):
    s=np.frombuffer(raw,dtype=np.uint8).reshape(-1,2352).copy()
    assert not np.any(s[:,18]&0x20),'Changed movie sector is not Form 1'
    lut=np.array(discimage.EDC_LUT,dtype=np.uint32)
    edc=np.zeros(len(s),dtype=np.uint32)
    for pos in range(16,2072):
        edc=(edc>>8)^lut[(edc^s[:,pos])&255]
    actual=s[:,2072:2076].copy().view('<u4').ravel()
    assert np.array_equal(edc,actual),'Movie sector EDC mismatch'
    s[:,12:16]=0
    ef=np.array(discimage.ECC_F,dtype=np.uint8)
    eb=np.array(discimage.ECC_B,dtype=np.uint8)
    for major,minor,mult,inc,offset in [(86,24,2,86,0x81c),(52,43,86,88,0x8c8)]:
        idx=(np.arange(major)//2)*mult+(np.arange(major)&1)
        a=np.zeros((len(s),major),dtype=np.uint8)
        b=a.copy()
        for _ in range(minor):
            t=s[:,12+idx]
            a=ef[a^t]
            b^=t
            idx=(idx+inc)%(major*minor)
        a=eb[ef[a]^b]
        assert np.array_equal(np.concatenate((a,a^b),axis=1),s[:,offset:offset+major*2]),'Movie ECC mismatch'

def same_range(a,b,start,end):
    a.seek(start)
    b.seek(start)
    while start<end:
        count=min(8*1024*1024,end-start)
        assert a.read(count)==b.read(count),('Unrelated disc data changed',start)
        start+=count

def main():
    p=argparse.ArgumentParser()
    p.add_argument('version')
    p.add_argument('baseline',nargs='?',default='0.3.4')
    args=p.parse_args()
    new=OUT/('STT2001_EN_v%s.bin'%args.version)
    old=OUT/('STT2001_EN_v%s.bin'%args.baseline)
    nd,od=directory(new),directory(old)
    assert nd==od,'Disc directory/LBA/size changed'
    assert new.stat().st_size==old.stat().st_size,'Disc size changed'
    filetable=json.loads(Path(str(new)+'.files.json').read_text())
    assert nd=={r['path']:{'lba':r['lba'],'size':r['size']} for r in filetable}
    inv=json.loads((movie_patch.SOURCE/'inventory.json').read_text())
    manifest=json.loads(movie_patch.MANIFEST.read_text(encoding='utf-8'))
    selected={c['id']:c for c in manifest['clips'] if c['subtitles'] or c.get('credits')}
    start=nd['MOVIE.STR']['lba']*2352
    end=start+inv[-1]['end_sector']*2352
    with new.open('rb') as a,old.open('rb') as b:
        same_range(a,b,0,start)
        same_range(a,b,end,new.stat().st_size)
        clips=[]
        parity=[]
        checked=0
        for row in inv:
            i=row['id']
            offset=start+row['start_sector']*2352
            size=(row['end_sector']-row['start_sector'])*2352
            a.seek(offset)
            inserted=a.read(size)
            if i not in selected:
                b.seek(offset)
                assert inserted==b.read(size),('Unedited movie changed',i)
                continue
            expected,report=movie_patch.validate(selected[i],row)
            assert inserted==expected,('Inserted stream differs',i)
            original=(movie_patch.SOURCE/('movie_%03d.str'%i)).read_bytes()
            for pos in range(0,size,2352):
                s=inserted[pos:pos+2352]
                if s!=original[pos:pos+2352]:
                    parity.append(s)
                if len(parity)==4096:
                    check_parity(b''.join(parity))
                    checked+=len(parity)
                    parity=[]
            verification=movie_patch.SOURCE/'verification'
            verification.mkdir(exist_ok=True)
            raw=verification/('movie_%03d_from_v%s.str'%(i,args.version))
            raw.write_bytes(inserted)
            with av.open(str(raw),format='psxstr') as container:
                count=0
                for frame in container.decode(video=0):
                    assert frame.width==row['width'] and frame.height==row['height']
                    frame.to_ndarray(format='rgb24')
                    count+=1
                assert count==row['frames'],(i,count,row['frames'])
            clips.append({'id':i,'frames':count,'edited_frames':len(report['edited_frames']),
                          'changed_sectors':report['changed_video_sectors'],
                          'xa_audio_unchanged':True,'native_decode_passed':True})
            print('Verified movie %03d: %d native frames, audio unchanged.'%(i,count),flush=True)
        if parity:
            check_parity(b''.join(parity))
            checked+=len(parity)
    with new.open('rb') as image:
        bin_hash=hashlib.file_digest(image,'sha256').hexdigest()
    result={'version':args.version,'baseline':args.baseline,'all_checks_passed':True,
            'disc_size':new.stat().st_size,'disc_directory_and_all_lbas_unchanged':True,
            'all_nonmovie_disc_bytes_identical':True,'unchanged_movie_count':len(inv)-len(selected),
            'movie_edc_ecc_sectors_verified':checked,'movies':clips,
            'bin_sha256':bin_hash,'emulator_verified':False}
    (OUT/('STT2001_EN_v%s_movie_verification.json'%args.version)).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('PASS: %d edited movies; %d sectors passed EDC/ECC.'%(len(clips),checked),flush=True)

if __name__=='__main__': main()
