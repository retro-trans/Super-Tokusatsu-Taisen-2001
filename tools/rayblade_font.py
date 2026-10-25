"""Read Rayblade's current Skies Latin bitmap; adapt it to PS1 2bpp cells.

The local source is not distributed. ASCII shapes and 4x advances come from
the verified Rayblade medium bank, without per-letter stretching. Accents
and symbols absent from that bank retain the existing GenEi fallback.
"""
import hashlib
import json
import struct
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image,ImageFont

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'work/source/font/rayblade-skies.bin'
SOURCE=ROOT.parent/'Seireiki Rayblade/work/output/0.1.44/WIN00.AFS'
EXPECTED='5fe1480136b8c7d2bb15a32b17588edc0459fcf9c1079c9aa4b1075e11a4d181'
ASCII=''.join(chr(c) for c in range(32,127))
MEDIUM=' '+'ABCDEFGHIJKLMNOPQRSTUVWXYZ'+'abcdefghijklmnopqrstuvwxyz'+' '+'0123456789'
MEDIUM+=''.join(c for c in ASCII if c not in MEDIUM)
LEVELS=np.array([0,85,187,255],np.uint8)


@lru_cache(maxsize=1)
def source_font():
    if CACHE.exists():
        blob=CACHE.read_bytes()
    else:
        archive=SOURCE.read_bytes()
        offset,size=struct.unpack_from('<II',archive,8)
        blob=archive[offset:offset+size]
        assert len(blob)==99072 and hashlib.sha256(blob).hexdigest()==EXPECTED
        CACHE.parent.mkdir(parents=True,exist_ok=True)
        CACHE.write_bytes(blob)
    assert blob[:8]==b'RBLF4X\0\4' and hashlib.sha256(blob).hexdigest()==EXPECTED
    return blob


class Font:
    def __init__(self):
        import vwf_font as V
        self.blob=source_font()
        name,index=V.FACES[V.DEFAULT_FACE]
        self.fallback=ImageFont.truetype(str(Path(V.FONT_DIR)/name),V.DEFAULT_SIZE,index=index)
        self.cache={}

    def hires(self,ch):
        if ch in self.cache:return self.cache[ch].copy()
        if ch not in ASCII:
            # Retain the existing vector source for the few unsupported marks.
            from texpack import HiFont
            glyph=HiFont(legacy=True).char(ch)
        else:
            index=MEDIUM.index(ch)
            rows=np.frombuffer(self.blob,dtype='<u4',count=128,offset=0x8200+index*512).reshape(64,2)
            glyph=np.zeros((64,48),np.uint8)
            for x in range(32):
                glyph[:,x]=(rows[:,x//16]>>(30-2*(x%16)))&3
        self.cache[ch]=glyph
        return glyph.copy()

    def render_cell(self,ch):
        if ch not in ASCII:
            import vwf_font as V
            return V.render_char(self.fallback,ch)
        # A single, common 4:1 area reduction fits the game's 12x16 cells.
        # The optional 4x pack retains the original Rayblade mask exactly.
        alpha=LEVELS[self.hires(ch)]
        low=np.asarray(Image.fromarray(alpha).resize((12,16),Image.Resampling.BOX),dtype=np.int16)
        cell=np.argmin(abs(low[:,:,None]-LEVELS.astype(np.int16)),axis=2).astype(np.uint8)
        return cell,int(self.blob[0xa0+MEDIUM.index(ch)])


def provenance(native_2x=False):
    source_font()
    return {'family':'rayblade-skies','source_game':'Seireiki Rayblade English v0.7.0 (same bank as local 0.1.44)',
        'original_art':'Skies of Arcadia USA Dreamcast Latin bitmap',
        'rayblade_font_sha256':EXPECTED,'ascii_characters':95,'source_cell':[32,64],
        'native_cell':[24,32] if native_2x else [12,16],'texture_cell':[48,64],
        'native_sampling':('Original doubled ASCII samples, half-size FT4; half-blended faint edges and opaque ink' if native_2x
            else 'Uniform 4:1 area reduction, nearest of four 2bpp levels'),
        'texture_sampling':'Exact Rayblade medium-bank masks, padded to 48 pixels; no stretching',
        'non_ascii_fallback':'Existing GenEi Latin accents and symbols',
        'standalone_source_font_distributed':False}
