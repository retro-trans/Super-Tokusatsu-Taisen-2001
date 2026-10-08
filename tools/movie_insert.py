"""Encode approved captions into original PSX STR frame slots using jPSXdec.

Run with tools/movie_env/Scripts/python.exe. Only caption/credit frames are
re-encoded; original frame/sector allocation and XA audio remain unchanged.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET
import av
from PIL import Image, ImageDraw, ImageFont
from movie_subtitles import display_subtitles

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'work/source/movies'
ENCODED=SOURCE/'encoded'
JAR=ROOT/'tools/jpsxdec/jpsxdec_v2.1-beta/jpsxdec.jar'
FONT=ROOT/'incoming/GenEiLatin/GenEiLateGo_v2.ttc'
MANIFEST=ROOT/'work/translation/en/movies.en.json'

def wrap(text,font,width):
    lines=[]
    for paragraph in text.splitlines():
        line=''
        for word in paragraph.split():
            candidate=(line+' '+word).strip()
            if font.getlength(candidate)>width and line:
                lines.append(line)
                line=word
            else:
                line=candidate
        if line:
            lines.append(line)
    assert all(font.getlength(line)<=width for line in lines),(text,width)
    return lines

def caption(image,text):
    w,h=image.size
    size=9 if w==160 else 12
    font=ImageFont.truetype(str(FONT),size,index=1)
    lines=wrap(text,font,w-8)
    spacing=size+2
    assert len(lines)<=4 if w==160 else len(lines)<=3,(text,lines)
    top=h-5-spacing*len(lines)
    draw=ImageDraw.Draw(image)
    for i,line in enumerate(lines):
        x=(w-font.getlength(line))/2
        draw.text((x,top+i*spacing),line,font=font,fill='white',stroke_width=1,
                  stroke_fill='black',anchor='lt')
    return (0,max(0,(top//16)*16),w,h-max(0,(top//16)*16))

def run_java(args,log):
    with log.open('w',encoding='utf-8') as out:
        subprocess.run(['java','-Xmx2g','-jar',str(JAR)]+args,cwd=log.parent,
                       stdout=out,stderr=out,check=True)
    text=log.read_text(encoding='utf-8',errors='replace')
    assert 'Unable to compress' not in text and 'Error:' not in text,text[-2000:]

def prepare(clip,inventory,test_frame=None):
    i=clip['id']
    name='movie_%03d'%i
    folder=ENCODED/name
    folder.mkdir(parents=True,exist_ok=True)
    raw=folder/(name+'.str')
    shutil.copyfile(SOURCE/(name+'.str'),raw)
    frames=folder/'frames'
    frames.mkdir(exist_ok=True)
    subtitles=display_subtitles(clip)
    root=ET.Element('str-replace',version='0.3')
    credit_container=None
    if clip.get('credits'):
        # Credits already approved in the MP4; reduce to original native size.
        credit_container=av.open(str(ROOT/'work/output/movies_v0.3.4_preview/english'/(name+'_en.mp4')))
        credit_iterator=iter(credit_container.decode(video=0))
        mask=Image.new('RGB',(inventory['width'],inventory['height']),'black')
        md=ImageDraw.Draw(mask)
        md.rectangle((0,24,319,93),fill='white')
        md.rectangle((0,94,131,205),fill='white')
        mask.save(folder/'credit_mask.png')
    changed=[]
    with av.open(str(SOURCE/(name+'.str')),format='psxstr') as source:
        for n,frame in enumerate(source.decode(video=0)):
            t=n/12
            credit_frame=next(credit_iterator) if credit_container else None
            active=next((s for s in subtitles if s['start']<=t<s['end']),None)
            credit=clip.get('credits') and 5<=t<=93
            if not active and not credit:
                continue
            if test_frame is not None and n!=test_frame:
                continue
            image=frame.to_image()
            if credit:
                image=credit_frame.to_image().resize(image.size,Image.Resampling.LANCZOS)
            rect=caption(image,active['en']) if active else None
            dest=frames/('%05d.png'%n)
            image.save(dest)
            # Full-frame quantization preserves bright lettering. Partial
            # STR-v3 encoding dims AC detail when preserving the old qscale.
            ET.SubElement(root,'replace',{'frame':str(n)}).text=str(dest)
            changed.append(n)
    if credit_container:
        credit_container.close()
    assert n+1==inventory['frames'],(i,n+1,inventory['frames'])
    xml=folder/'replace.xml'
    ET.ElementTree(root).write(xml,encoding='utf-8',xml_declaration=True)
    index=folder/(name+'.idx')
    run_java(['-f',str(raw),'-x',str(index)],folder/'index.log')
    run_java(['-x',str(index),'-i','0','-replaceframes',str(xml)],folder/'encode.log')
    report={'id':i,'frames':n+1,'edited_frames':changed,'subtitle_count':len(subtitles),
            'source_sha256':hashlib.sha256((SOURCE/(name+'.str')).read_bytes()).hexdigest(),
            'encoded_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),
            'manifest_sha256':hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
            'encoder':'jPSXdec v2.1 beta, full changed frames, original slot capacities'}
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('%s: %d frames edited'%(name,len(changed)),flush=True)
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--ids')
    p.add_argument('--test-frame',type=int)
    args=p.parse_args()
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    inventory=json.loads((SOURCE/'inventory.json').read_text())
    selected=[c for c in manifest['clips'] if c['subtitles'] or c.get('credits')]
    if args.ids:
        ids=[int(x) for x in args.ids.split(',')]
        selected=[c for c in selected if c['id'] in ids]
    for clip in selected:
        prepare(clip,inventory[clip['id']-1],args.test_frame)

if __name__=='__main__': main()
