"""Insert pre-encoded STR clips in place. Pure Python; safe for build.py."""
import hashlib
import json
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'work/source/movies'
MANIFEST=ROOT/'work/translation/en/movies.en.json'

def expected_frames(clip):
    rows=clip['subtitles']
    return [n for n in range(round(clip['duration']*12))
            if any(s['start']<=n/12<s['end'] for s in rows)
            or (clip.get('credits') and 5<=n/12<=93)]

def validate(clip,inventory):
    i=clip['id']
    name='movie_%03d'%i
    folder=SOURCE/'encoded'/name
    report=json.loads((folder/'report.json').read_text(encoding='utf-8'))
    original=(SOURCE/(name+'.str')).read_bytes()
    encoded=(folder/(name+'.str')).read_bytes()
    assert report['source_sha256']==hashlib.sha256(original).hexdigest(),i
    assert report['encoded_sha256']==hashlib.sha256(encoded).hexdigest(),i
    assert report['manifest_sha256']==hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),i
    assert report['edited_frames']==expected_frames(clip),i
    assert len(encoded)==len(original)==(inventory['end_sector']-inventory['start_sector'])*2352,i
    edited=set(report['edited_frames'])
    changed=0
    seen=set()
    audio_sectors=0
    for offset in range(0,len(original),2352):
        a=original[offset:offset+2352]
        b=encoded[offset:offset+2352]
        if a[24:28]==bytes.fromhex('60010180'):
            chunk,chunks,frame,size,w,h=struct.unpack_from('<HHIIHH',b,28)
            if chunk==0:
                seen.add(frame-1)
            assert a[:36]==b[:36] and a[40:44]==b[40:44],(i,frame,chunk)
            assert size<=chunks*2016,(i,frame,size,chunks)
            if frame-1 not in edited:
                assert a==b,(i,'untargeted frame changed',frame)
            elif a!=b:
                changed+=1
        else:
            assert a==b,(i,'audio/nonvideo sector changed',offset//2352)
            audio_sectors+=(a[18]&14)==4
    assert len(seen)==inventory['frames'] and audio_sectors==inventory['audio_sectors'],i
    assert changed>0,i
    return encoded,dict(report,changed_video_sectors=changed,audio_sectors_unchanged=audio_sectors)

def patch(path):
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    inventory=json.loads((SOURCE/'inventory.json').read_text())
    files=json.loads((ROOT/'work/source/disc_files.json').read_text())
    movie=next(e for e in files if e['path']=='MOVIE.STR')
    selected=[c for c in manifest['clips'] if c['subtitles'] or c.get('credits')]
    report=[]
    # Validate every prepared replacement before opening the new image for writes.
    for clip in selected:
        _,item=validate(clip,inventory[clip['id']-1])
        report.append(item)
    with Path(path).open('r+b') as image:
        for clip in selected:
            row=inventory[clip['id']-1]
            name='movie_%03d'%clip['id']
            offset=(movie['lba']+row['start_sector'])*2352
            original=(SOURCE/(name+'.str')).read_bytes()
            image.seek(offset)
            assert image.read(len(original))==original,('movie baseline differs',clip['id'])
            encoded=(SOURCE/'encoded'/name/(name+'.str')).read_bytes()
            image.seek(offset)
            image.write(encoded)
    result={'manifest_preview_revision':manifest['preview_revision'],'movies_replaced':len(report),
            'edited_frames':sum(len(r['edited_frames']) for r in report),
            'changed_video_sectors':sum(r['changed_video_sectors'] for r in report),
            'audio_unchanged':True,'frame_counts_and_sector_allocations_unchanged':True,
            'clips':report,'emulator_verified':False}
    print('Inserted %d movies, %d caption/credit frames.'%(len(report),result['edited_frames']))
    return result
