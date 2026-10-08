"""Decode every preview frame and audio packet; record review evidence."""
import json
from pathlib import Path
import av
from movie_subtitles import display_subtitles, timestamp, SUBTITLE_HOLD
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'work/output/movies_v0.3.4_preview'
def inspect(path):
    with av.open(str(path)) as c:
        v=c.streams.video[0]
        a=c.streams.audio[0]
        info={'file':str(path.relative_to(ROOT)),'width':v.width,'height':v.height,
              'fps':str(v.average_rate),'audio_rate':a.rate,'audio_channels':a.channels,
              'video_frames':0,'audio_samples':0,'chapters':len(c.chapters())}
        previous={}
        for packet in c.demux(v,a):
            for frame in packet.decode():
                if frame.pts is not None:
                    kind=packet.stream.type
                    assert frame.pts>previous.get(kind,-100000), (path,kind,frame.pts)
                    previous[kind]=frame.pts
                if packet.stream.type=='video':
                    info['video_frames']+=1
                else:
                    info['audio_samples']+=frame.samples
        info['video_seconds']=round(info['video_frames']/12,6)
        info['audio_seconds']=round(info['audio_samples']/info['audio_rate'],6)
        assert info['width']==960 and info['height']==720 and info['fps']=='12'
        assert info['audio_rate']==48000 and info['audio_channels']==2
        assert abs(info['audio_seconds']-info['video_seconds'])<.25,info
        return info
def main():
    manifest=json.loads((ROOT/'work/translation/en/movies.en.json').read_text(encoding='utf-8'))
    inv=json.loads((ROOT/'work/source/movies/inventory.json').read_text())
    rows=[]
    for clip in manifest['clips']:
        row=inspect(BASE/'english'/('movie_%03d_en.mp4'%clip['id']))
        assert row['video_frames']==inv[clip['id']-1]['frames'],row
        subtitles=display_subtitles(clip)
        stem='movie_%03d'%clip['id']
        subfolder=ROOT/'work/translation/en/movies'
        srt=(subfolder/(stem+'.srt')).read_text(encoding='utf-8')
        ass=(subfolder/(stem+'.ass')).read_text(encoding='utf-8')
        expected_srt='\n\n'.join('%d\n%s --> %s\n%s' %
            (i,timestamp(s['start']),timestamp(s['end']),s['en'])
            for i,s in enumerate(subtitles,1))+'\n'
        assert srt==expected_srt,stem
        for i,s in enumerate(subtitles):
            assert 0<=s['start']<s['end']<=row['video_seconds']+.000001
            next_start=subtitles[i+1]['start'] if i+1<len(subtitles) else clip['duration']
            expected=min(s['voice_end']+SUBTITLE_HOLD,next_start,clip['duration'])
            assert s['end']+.000001>=expected,(clip['id'],s)
            assert s['end']<=next_start+.000001,(clip['id'],s)
            event='Dialogue: 0,%s,%s,Default,,0,0,0,,%s' % (
                timestamp(s['start'],True),timestamp(s['end'],True),s['en'].replace('\n',r'\N'))
            assert event in ass,(stem,event)
        row['id']=clip['id']
        rows.append(row)
    for name,selection in [('main_movies_en',inv[64:]),('battle_movies_en',inv[:64])]:
        path=BASE/(name+'.mp4')
        if path.exists():
            row=inspect(path)
            assert row['video_frames']==sum(i['frames'] for i in selection),row
            assert row['chapters']==len(selection),row
            rows.append(row)
    result={'all_checks_passed':True,'preview_revision':manifest['preview_revision'],
            'subtitle_hold_seconds':SUBTITLE_HOLD,
            'checks':'Full video/audio decode, monotonic timestamps, frame counts, subtitle bounds and post-voice hold, chapter counts, image/audio formats',
            'clips':rows}
    (BASE/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Verified %d files, %d video frames.'%(len(rows),sum(r['video_frames'] for r in rows)),flush=True)
if __name__=='__main__': main()
