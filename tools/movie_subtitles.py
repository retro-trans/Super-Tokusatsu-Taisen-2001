"""Render review MP4s from the English-only movie manifest; no game insertion."""
import argparse
import json
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'work/output/movies_v0.3.4_preview'
MANIFEST = ROOT / 'work/translation/en/movies.en.json'
FFMPEG = 'C:/Program Files/ShareX/ffmpeg.exe'
SUBTITLE_HOLD = 0.5

def display_subtitles(clip):
    """Hold captions after speech, without overlapping the next caption."""
    rows=clip['subtitles']
    result=[]
    for i,row in enumerate(rows):
        voice_end=row.get('voice_end',row['end'])
        next_start=rows[i+1]['start'] if i+1<len(rows) else clip['duration']
        end=min(max(row['end'],voice_end+SUBTITLE_HOLD),next_start,clip['duration'])
        assert row['start']<end,(clip['id'],row)
        result.append(dict(row,end=round(end,6)))
    return result

def timestamp(seconds, ass=False):
    units = round(seconds*(100 if ass else 1000))
    scale = 100 if ass else 1000
    h, units = divmod(units,3600*scale)
    m, units = divmod(units,60*scale)
    s, fraction = divmod(units,scale)
    return ('%d:%02d:%02d.%02d' if ass else '%02d:%02d:%02d,%03d') % (h,m,s,fraction)

def write_subtitles(clip, credits):
    name='movie_%03d' % clip['id']
    folder=ROOT/'work/translation/en/movies'
    folder.mkdir(parents=True,exist_ok=True)
    rows=display_subtitles(clip)
    (folder/(name+'.srt')).write_text('\n\n'.join('%d\n%s --> %s\n%s' %
        (n,timestamp(r['start']),timestamp(r['end']),r['en']) for n,r in enumerate(rows,1))+'\n',encoding='utf-8')
    lines=['[Script Info]','ScriptType: v4.00+','PlayResX: 960','PlayResY: 720','WrapStyle: 2',
        '[V4+ Styles]', 'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
        'Style: Default,GenEi LateGo P v2,36,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,36,36,32,1',
        'Style: Credit,GenEi LateGo P v2,30,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1',
        'Style: Note,GenEi LateGo P v2,22,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,1,0,8,20,20,20,1',
        '[Events]','Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
    def event(start,end,text,style='Default'):
        assert 0 <= start < end <= clip['duration']+0.15,(clip['id'],start,end)
        lines.append('Dialogue: 0,%s,%s,%s,,0,0,0,,%s' % (timestamp(start,True),timestamp(end,True),style,text.replace('\n',r'\N')))
    for r in rows:
        event(r['start'],r['end'],r['en'])
    if clip.get('lyric_draft'):
        event(14,113,'Draft lyric translation','Note')
    if clip.get('credits'):
        for i,page in enumerate(credits):
            start=5+4*i
            event(start,start+4,r'{\pos(96,106)\fad(250,250)}'+page['heading'],'Credit')
            y=139 if i==0 else (151 if page.get('layout')!='left' else 158)
            size=26 if i==0 else (30 if page.get('layout')!='left' else 28)
            event(start,start+4,r'{\pos(126,%d)\fs%d\fad(250,250)}' % (y,size)+page['body'],'Credit')
    (folder/(name+'.ass')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return name

def render(clip,credits):
    name=write_subtitles(clip,credits)
    dest=BASE/'english'/(name+'_en.mp4')
    dest.parent.mkdir(parents=True,exist_ok=True)
    filters=['scale=960:720:force_original_aspect_ratio=decrease:flags=lanczos:in_range=pc:out_range=tv',
             'pad=960:720:(ow-iw)/2:(oh-ih)/2','setsar=1']
    if clip.get('credits'):
        filters += ['drawbox=x=0:y=72:w=960:h=210:color=black:t=fill:enable=between(t\\,5\\,93)',
                    'drawbox=x=0:y=282:w=396:h=336:color=black:t=fill:enable=between(t\\,5\\,93)']
    fonts=ROOT/'work/source/movies/fonts'
    fonts.mkdir(exist_ok=True)
    font=fonts/'GenEiLateGo_v2.ttc'
    if not font.exists():
        import shutil
        shutil.copyfile(ROOT/'incoming/GenEiLatin/GenEiLateGo_v2.ttc',font)
    filters += ['subtitles=work/translation/en/movies/'+name+'.ass:fontsdir=work/source/movies/fonts']
    cmd=[FFMPEG,'-hide_banner','-loglevel','warning','-y','-i',str(BASE/'original'/(name+'.mp4')),
         '-vf',','.join(filters),'-c:v','libx264','-preset','fast','-crf','18',
         '-pix_fmt','yuv420p','-color_range','tv','-r','12','-c:a','aac','-b:a','128k','-ar','48000','-ac','2',
         '-movflags','+faststart','-metadata','title='+clip['title'],'-metadata','comment=English review preview; original Japanese audio',str(dest)]
    log=ROOT/'work/source/movies'/(name+'_subtitle_render.log')
    with log.open('w',encoding='utf-8') as out:
        subprocess.run(cmd,cwd=ROOT,stdout=out,stderr=out,check=True)
    print(str(dest.relative_to(ROOT)),flush=True)

def reel(clips,name):
    # Re-encode a joined timeline rather than concatenating differing AAC tails.
    folder=BASE/'english'
    listing=BASE/(name+'.concat.txt')
    listing.write_text(''.join("file 'english/movie_%03d_en.mp4'\nduration %.9f\n" % (c['id'],c['duration']) for c in clips),encoding='utf-8')
    chapters=BASE/(name+'.ffmetadata')
    meta=[';FFMETADATA1','title=Super Tokusatsu Taisen 2001 - English movie review']
    t=0
    for c in clips:
        end=t+c['duration']
        meta += ['[CHAPTER]','TIMEBASE=1/1000','START='+str(round(t*1000)),
                 'END='+str(round(end*1000)),'title=%03d - %s' % (c['id'],c['title'])]
        t=end
    chapters.write_text('\n'.join(meta)+'\n',encoding='utf-8')
    cmd=[FFMPEG,'-hide_banner','-loglevel','warning','-y','-f','concat','-safe','0','-i',str(listing),
         '-i',str(chapters),'-map_metadata','1','-map_chapters','1','-c:v','libx264','-preset','fast','-crf','18',
         '-r','12','-af','aresample=async=1000:first_pts=0','-c:a','aac','-b:a','128k','-ar','48000','-ac','2','-movflags','+faststart',str(BASE/(name+'.mp4'))]
    with (ROOT/'work/source/movies'/(name+'_render.log')).open('w',encoding='utf-8') as out:
        subprocess.run(cmd,cwd=ROOT,stdout=out,stderr=out,check=True)
    print(name+'.mp4',flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--ids')
    p.add_argument('--reels',action='store_true')
    args=p.parse_args()
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    clips=manifest['clips']
    if args.reels:
        reel([c for c in clips if c['id']>=65],'main_movies_en')
        reel([c for c in clips if c['id']<=64],'battle_movies_en')
    else:
        ids=[int(x) for x in args.ids.split(',')] if args.ids else list(range(65,75))+list(range(1,65))
        for clip_id in ids:
            render(next(c for c in clips if c['id']==clip_id),manifest['credit_pages'])

if __name__=='__main__':
    main()
