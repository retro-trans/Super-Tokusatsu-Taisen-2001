"""Native intertitles assembled from image-generated lettering assets.

Only artwork is replaced: stage numbering, sprite rectangles and scripts stay
unchanged. The generated source sheet is retained alongside its prompts.
"""
from functools import lru_cache
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'work/ui/intertitles/lettering-source-v0.9.7.png'
ROWS = ['ABCDEF', 'GHIJKL', 'MNOPQR', 'STUVWX', 'YZ0123', '456789', "!?',.-", ':()']


@lru_cache(maxsize=1)
def glyphs():
    image=np.asarray(Image.open(SOURCE).convert('L'))
    ys=np.where((image>128).sum(axis=1)>8)[0]
    groups=[]
    for y in ys:
        if not groups or y-groups[-1][-1]>28:
            groups.append([])
        groups[-1].append(y)
    assert len(groups)==8, 'Generated sheet must contain eight distinct rows'
    result={}
    for row,chars in enumerate(ROWS):
        y0,y1=min(groups[row]),max(groups[row])+1
        for col,ch in enumerate(chars):
            x0,x1=round(col*image.shape[1]/6),round((col+1)*image.shape[1]/6)
            cell=image[y0:y1,x0:x1]
            gy,gx=np.nonzero(cell>128)
            assert len(gx)>0, ('Missing generated glyph',ch)
            bx0,bx1=max(0,gx.min()-1),min(cell.shape[1],gx.max()+2)
            by0,by1=max(0,gy.min()-1),min(cell.shape[0],gy.max()+2)
            mask=cell[by0:by1,bx0:bx1].copy()
            # Remove the source's very slight white-face texture and black
            # compression noise, retaining antialiased contour coverage.
            mask[mask>=220]=255
            mask[mask<=8]=0
            result[ch]=mask
    assert len(result)==45
    return result


@lru_cache(maxsize=512)
def letter(ch,size):
    src=glyphs()[ch]
    reference=float(np.median([glyphs()[c].shape[0] for c in 'ABCEFHIKLMNPRSTUVWXYZ0123456789']))
    if ch.isalnum() or ch in '!?()':
        height=size+(round(size*0.08) if ch=='Q' else 0)
        width=max(1,round(src.shape[1]*size/reference))
        top=0
    else:
        height=max(1,round(src.shape[0]*size/reference))
        width=max(1,round(src.shape[1]*size/reference))
        top={"'":0, ',':size-height+round(size*0.12), '.':size-height,
             '-':round(size*0.48), ':':size-height}[ch]
    mask=np.asarray(Image.fromarray(src).resize((width,height),Image.Resampling.LANCZOS))
    return mask,top


@lru_cache(maxsize=512)
def lettering(text,size):
    text=text.upper()
    assert all(c==' ' or c in glyphs() for c in text), text
    gap=max(1,round(size*0.08))
    pieces=[]
    for ch in text:
        if ch==' ':
            pieces.append((None,0,max(2,round(size*0.32))))
        else:
            mask,top=letter(ch,size)
            pieces.append((mask,top,mask.shape[1]+gap))
    width=sum(w for _,_,w in pieces)-gap
    height=max(top+mask.shape[0] for mask,top,_ in pieces if mask is not None)
    output=np.zeros((height,width),np.uint8)
    x=0
    for mask,top,advance in pieces:
        if mask is not None:
            output[top:top+mask.shape[0],x:x+mask.shape[1]]=mask
        x+=advance
    return output


def put(tim,rect,mask,text):
    x0,y0,x1,y1=rect
    h,w=mask.shape
    assert w<=x1-x0 and h<=y1-y0, (text,mask.shape,rect)
    x,y=x0+(x1-x0-w)//2,y0+(y1-y0-h)//2
    bg=np.array(tim.palette[int(tim.idx[5,5])],dtype=np.int32)
    shades=bg[None,:]+np.arange(256,dtype=np.int32)[:,None]*(255-bg[None,:])//255
    pal=np.array(tim.palette,dtype=np.int32)
    lut=((shades[:,None,:]-pal[None,:,:])**2).sum(axis=2).argmin(axis=1).astype(np.uint8)
    tim.idx[y:y+h,x:x+w]=lut[mask]
    return dict(text=text,bounds=[x,y,x+w,y+h],image_generated=True)


def fit(title):
    for size in (24,22):
        if lettering(title,size).shape[1]<=304:
            return [title],size
    words=title.split()
    choices=[]
    for cut in range(1,len(words)):
        lines=[' '.join(words[:cut]),' '.join(words[cut:])]
        for size in (24,22,20,18,16):
            widths=[lettering(line,size).shape[1] for line in lines]
            if max(widths)<=304:
                choices.append((size,-abs(widths[0]-widths[1]),lines))
                break
    assert choices, ('Title cannot fit',title)
    size,_,lines=max(choices)
    return lines,size


def make_episode(tim,title):
    bg=int(tim.idx[5,5])
    tim.fill(0,18,320,84,bg)
    lines,size=fit(title)
    assert ' '.join(lines) == title, 'Stage title wording changed'
    boxes=[(8,22,312,80)] if len(lines)==1 else [(8,20,312,50),(8,52,312,82)]
    labels=[put(tim,box,lettering(line,size),line.upper()) for box,line in zip(boxes,lines)]
    tim.fill(0,100,320,128,bg)
    for digit in range(10):
        # The running game samples only the middle 12 pixels of each cell.
        mask=lettering(str(digit),18)
        if mask.shape[1]>12:
            mask=np.asarray(Image.fromarray(mask).resize((12,mask.shape[0]),Image.Resampling.LANCZOS))
        labels.append(put(tim,(digit*24+6,104,digit*24+18,128),mask,str(digit)))
    size=18
    while lettering('STAGE',size).shape[1]>52:
        size-=1
    labels.append(put(tim,(256,104,308,128),lettering('STAGE',size),'STAGE'))
    return labels


def make_narration(tim,target):
    rect=target['regions'][0]
    tim.fill(*rect,int(tim.idx[5,5]))
    image=Image.open(ROOT/target['lettering_asset']).convert('L')
    a=np.asarray(image)
    y,x=np.nonzero(a>64)
    image=image.crop((max(0,x.min()-2),max(0,y.min()-2),min(image.width,x.max()+3),min(image.height,y.max()+3)))
    image.thumbnail((300,21),Image.Resampling.LANCZOS)
    alpha=np.array(image)
    alpha[alpha<=5]=0
    alpha[alpha>=240]=255
    return [put(tim,rect,alpha,target['labels'][0]['en'])]
