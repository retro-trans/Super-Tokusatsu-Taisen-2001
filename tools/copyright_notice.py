"""Clean, antialiased copyright bitmap, using the original 16 grey colours.

The build uses checked-in line masks, so it needs no installed system font.
Regenerate masks explicitly with --font PATH when the notice wording changes.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT/'work/ui/copyright/lettering.en.json'


def make_masks(font_path, target):
    scale, size, height, baseline = 8, 16, 18, 14
    font = ImageFont.truetype(str(font_path), size*scale)
    rows = []
    for label in target['labels']:
        text = label['en']
        width = int(np.ceil(font.getlength(text)/scale))+1
        image = Image.new('L', (width*scale, height*scale))
        ImageDraw.Draw(image).text((0, baseline*scale), text, font=font, fill=255, anchor='ls')
        mask = np.asarray(image.resize((width, height), Image.Resampling.LANCZOS))
        rows.append(dict(text=text, width=width, height=height,
                         alpha=[line.tobytes().hex() for line in mask]))
    result = dict(style='plain-sans-aa-v1', font='Arial Regular', size=size,
                  baseline=baseline, row_height=height, supersampling=scale,
                  note='Rasterized notice lines only; no system-font file required by the build.', rows=rows)
    ASSET.parent.mkdir(parents=True, exist_ok=True)
    ASSET.write_bytes((json.dumps(result, indent=2, ensure_ascii=False)+'\n').encode('utf-8'))


def render(tim, target):
    asset = json.loads((ROOT/target['lettering_asset']).read_text(encoding='utf-8'))
    assert asset['style'] == target['lettering']
    assert len(asset['rows']) == len(target['labels']) == 6
    palette = np.array(tim.palette, dtype=np.int32)
    shades = np.arange(256, dtype=np.int32)[:, None, None]
    lut = ((shades-palette[None, :, :])**2).sum(axis=2).argmin(axis=1).astype(np.uint8)
    tim.fill(*target['regions'][0], int(lut[0]))
    labels = []
    for label, row in zip(target['labels'], asset['rows']):
        assert row['text'] == label['en'], 'Copyright wording changed; regenerate line masks'
        assert label['size'] == asset['size']
        x0,y0,x1,y1 = label['rect']
        width,height = row['width'],row['height']
        assert width <= x1-x0 and height == y1-y0 == asset['row_height']
        alpha = np.array([list(bytes.fromhex(line)) for line in row['alpha']], dtype=np.uint8)
        assert alpha.shape == (height,width)
        tim.idx[y0:y0+height,x0:x0+width] = lut[alpha]
        labels.append(dict(text=row['text'], font=asset['font'], font_size=asset['size'],
                           baseline=y0+asset['baseline'], bounds=[x0,y0,x0+width,y0+height],
                           antialiased=True))
    return labels


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', required=True, type=Path)
    args=parser.parse_args()
    from gfx_translate import load_manifest
    make_masks(args.font, next(t for t in load_manifest()['targets'] if t['kind']=='copyright'))
    print(ASSET)
