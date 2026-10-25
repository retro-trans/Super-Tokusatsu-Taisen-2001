"""Check the complete opening review, bilingual timing, layout and source audio audit."""
import argparse,hashlib,json,subprocess
from pathlib import Path
import av,numpy as np,soundfile as sf
from PIL import Image,ImageFont
from movie_subtitles import display_subtitles,srt_text,timestamp
from movie_verify import inspect
from movie_insert import caption

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',default='0.3.38')
    args=parser.parse_args()
    manifest=ROOT/'work/translation/en/opening_song.en.json'
    review=json.loads(manifest.read_text(encoding='utf-8'));clip=review['clips'][0]
    assert review['version']==args.version
    folder=ROOT/('work/output/opening_song_review_v'+args.version)
    info=inspect(folder/'movie_074_en.mp4');assert info['video_frames']==1485
    rows=display_subtitles(clip);sub=folder/'subtitles'
    srt=(sub/'movie_074.srt').read_text(encoding='utf-8');ass=(sub/'movie_074.ass').read_text(encoding='utf-8')
    expected='\n\n'.join('%d\n%s --> %s\n%s'%(i,timestamp(r['start']),timestamp(r['end']),srt_text(r)) for i,r in enumerate(rows,1))+'\n'
    assert srt==expected
    font=ROOT/'incoming/GenEiLatin/GenEiLateGo_v2.ttc'
    english=ImageFont.truetype(str(font),36,index=1);roman=ImageFont.truetype(str(font),32,index=1)
    widths={'english':0,'romaji':0};unresolved=[]
    for i,r in enumerate(rows):
        next_start=rows[i+1]['start'] if i+1<len(rows) else clip['duration']
        assert r['end']>=min(r['voice_end']+.5,next_start,clip['duration'])-1e-6
        assert r['start']<r['end']<=next_start+1e-6
        for key,f in [('en',english),('romaji',roman)]:
            for line in r.get(key,'').splitlines():
                assert f.getlength(line)<=888,(key,line)
                label='english' if key=='en' else 'romaji';widths[label]=max(widths[label],round(f.getlength(line),2))
        event='Dialogue: 0,%s,%s,Default,,0,0,0,,%s'%(timestamp(r['start'],True),timestamp(r['end'],True),r['en'].replace('\n',r'\N'))
        assert event in ass
        if r.get('romaji') and r['romaji']!=r['en']:
            assert 'Dialogue: 0,%s,%s,Romaji,,0,0,0,,%s'%(timestamp(r['start'],True),timestamp(r['end'],True),r['romaji'].replace('\n',r'\N')) in ass
        if r.get('review_required'):unresolved.append([r['start'],r['voice_end']])
        else:assert r.get('romaji'),r
        caption(Image.new('RGB',(320,240)),r['en'],r.get('romaji'),clip.get('romaji_top',5),clip.get('english_bottom',5))
    assert unresolved==[]
    omitted=review['review'].get('intentionally_omitted_seconds',[])
    if tuple(map(int,args.version.split('.')))>=(0,3,36):
        assert omitted==[]
        refrain=next(r for r in rows if r['en']=='We get rainbow!')
        assert (refrain['start'],refrain['voice_end'],refrain['end'])==(95.4,97.68,98.18)
        assert refrain['romaji']==refrain['en']
        assert ass.count(',,We get rainbow!')==1
        assert review['review']['lyric_reference']['source']=='User-provided Spotify lyric screenshot'
    else:
        assert omitted==[95.4,97.68]
    romaji_bounds=[]
    if tuple(map(int,args.version.split('.')))>=(0,3,37):
        assert clip['romaji_top']==16
        style=next(line for line in ass.splitlines() if line.startswith('Style: Romaji,'))
        assert style.split(',')[-2]=='48'
        for r in rows:
            if r['romaji']==r['en']:continue
            english_only=Image.new('RGB',(320,240))
            caption(english_only,r['en'],english_bottom=clip.get('english_bottom',5))
            bilingual=Image.new('RGB',(320,240))
            caption(bilingual,r['en'],r['romaji'],clip['romaji_top'],clip.get('english_bottom',5))
            diff=np.any(np.asarray(bilingual)!=np.asarray(english_only),axis=2)
            y,x=np.where(diff)
            assert len(y) and y.min()>=15 and y.max()<48,(r,diff)
            # Cropping twelve lines off the top must not remove any romaji ink.
            assert not diff[:12].any()
            assert np.array_equal(np.asarray(bilingual)[120:],np.asarray(english_only)[120:])
            romaji_bounds.append([int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)])
    english_bounds=[];old_bottom_clipped=0
    if tuple(map(int,args.version.split('.')))>=(0,3,38):
        assert clip['english_bottom']==16
        style=next(line for line in ass.splitlines() if line.startswith('Style: Default,'))
        assert style.split(',')[-2]=='48'
        for r in rows:
            before=Image.new('RGB',(320,240));after=before.copy()
            caption(before,r['en'])
            caption(after,r['en'],english_bottom=clip['english_bottom'])
            old=np.asarray(before);new=np.asarray(after)
            assert np.array_equal(new[:-11],old[11:])
            assert not new[-12:].any()
            old_bottom_clipped+=int(old[-12:].any())
            y,x=np.where(np.any(new,axis=2))
            assert len(y) and y.max()<228
            english_bounds.append([int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)])
    # Inspect native-size layouts at both recovered lyric lines and the refrain.
    ui=ROOT/'work/ui/movies/song_review';ui.mkdir(parents=True,exist_ok=True)
    wanted={round(t*12) for t in (27.5,35,43,50,95,96,97.92,98.25)}
    with av.open(str(ROOT/'work/source/movies/movie_074.str'),format='psxstr') as video:
        for n,frame in enumerate(video.decode(video=0)):
            if n not in wanted:continue
            r=next(s for s in rows if s['start']<=n/12<s['end'])
            image=frame.to_image();caption(image,r['en'],r.get('romaji'),clip.get('romaji_top',5),clip.get('english_bottom',5))
            image.resize((960,720),Image.Resampling.NEAREST).save(ui/('native_%05d.png'%n))
    main=json.loads((ROOT/'work/translation/en/movies.en.json').read_text(encoding='utf-8'))
    baseline=args.version
    before=json.loads((ROOT/('work/source/movies/song_audit/movies_before_v'+baseline+'.en.json')).read_text(encoding='utf-8'))
    assert next(c for c in main['clips'] if c['id']==74)==clip
    assert main['credit_pages']==before['credit_pages']
    assert [c for c in main['clips'] if c['id']!=74]==[c for c in before['clips'] if c['id']!=74]
    prepared=list((ROOT/'work/source/movies/encoded').glob('movie_*/report.json'))
    assert len(prepared)==28
    import movie_patch
    for p in prepared:
        report=json.loads(p.read_text())
        c=next(c for c in main['clips'] if c['id']==report['id'])
        assert report['native_fingerprint']==movie_patch.native_fingerprint(c,main)
    audit=ROOT/'work/source/movies/song_audit';audio=[]
    for i in (71,72,73,74):
        source=(ROOT/'work/source/movies'/('movie_%03d.wav'%i)).read_bytes()
        source_id=71 if i==72 else i
        mix,_=sf.read(audit/('movie_%03d_stereo.wav'%source_id),dtype='float32')
        vocals,_=sf.read(audit/('movie_%03d_vocals.wav'%source_id),dtype='float32')
        ratio=float(np.sqrt(np.mean(vocals* vocals))/np.sqrt(np.mean(mix*mix)))
        audio.append({'id':i,'source_audio_sha256':hashlib.sha256(source).hexdigest(),'vocal_to_mix_rms':round(ratio,5)})
    assert audio[0]['source_audio_sha256']==audio[1]['source_audio_sha256']
    assert all(r['vocal_to_mix_rms']<.01 for r in audio[:3]) and audio[-1]['vocal_to_mix_rms']>.4
    report={'all_checks_passed':True,'review_version':review['version'],'video':info,'subtitle_cues':len(rows),
            'romaji_cues':sum(bool(r.get('romaji')) for r in rows),'unresolved_refrain_seconds':unresolved,
            'intentionally_omitted_refrain_seconds':omitted,
            'lyric_reference':review['review'].get('lyric_reference'),
            'maximum_preview_line_widths':widths,'post_voice_hold':.5,'native_caption_layouts_checked':len(rows),
            'romaji_top_native_pixels':clip.get('romaji_top',5),'romaji_ink_bounds':romaji_bounds,
            'top_12_pixel_crop_checked':bool(romaji_bounds),
            'english_bottom_native_pixels':clip.get('english_bottom',5),'english_ink_bounds':english_bounds,
            'bottom_12_pixel_crop_checked':bool(english_bounds),'old_bottom_clipped_cues':old_bottom_clipped,
            'native_layout_is_emulator_capture':False,'ending_audio_audit':audio,
            'other_73_clips_and_credit_pages_unchanged':True,
            'game_manifest_opening_matches_review':True,'human_listening_confirmation':False}
    (folder/'verification.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps(report,indent=1))


if __name__=='__main__':main()
