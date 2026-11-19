"""Export an optional exact-native font compatibility pack from a finished disc.

Unlike the older sharp-font exporter, this preserves every native palette,
antialiased ink sample, shadow and icon. It does not redraw any glyph.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import numpy as np
from PIL import Image
import xxhash

from check_graphics_build import directory,read_file
import cm
import repack
import texpack

ROOT=Path(__file__).resolve().parents[1]


def build(version):
    disc=ROOT/('work/output/STT2001_EN_v%s.bin'%version)
    table=directory(disc)
    mm,bt,ev=[repack.dat_entries(read_file(disc,table[n+'.DAT'])) for n in ('MAPMAIN','BATTLE','EVENT')]
    sheets=[mm[7],cm.blocks(mm[25])[3],bt[537],bt[538],ev[10]]+ev[11:24]
    parts=[texpack.tim_parts(t) for t in sheets]
    palettes=texpack.palettes([p[3] for p in parts])
    folder=ROOT/('work/output/STT2001_EN_v%s_native_font_pack/SLPS-02863'%version)
    (folder/'replacements').mkdir(parents=True,exist_ok=True)
    seen=set();records={};core=0
    for pixels,(iw,ih),upload,_ in parts:
        for page in range(pixels.shape[1]//256):
            block=pixels[:,page*256:(page+1)*256]
            if (upload,page) in seen:continue
            seen.add((upload,page))
            packed=(block[:,0::2] | (block[:,1::2]<<4)).astype(np.uint8).tobytes()
            keys={(upload,iw,page*256)}
            if iw>64:keys.add((xxhash.xxh3_64_intdigest(packed),64,0))
            for ph,(_,row) in palettes.items():
                for stp in (False,True):
                    lut=np.zeros((16,4),np.uint8)
                    for i,value in enumerate(row):
                        if value:
                            lut[i,:3]=texpack.c15(value)
                            lut[i,3]=texpack.STP_ALPHA if stp and value&0x8000 else 255
                    native=lut[block]
                    image=Image.fromarray(native,'RGBA').resize((1024,ih*4),Image.Resampling.NEAREST)
                    for kh,kw,kx in keys:
                        name='texupload-%s-%016X-%016X-%dx%d-%d-0-256x%d-P0-15.png'%('STP4' if stp else 'P4',kh,ph,kw,ih,kx,ih)
                        path=folder/'replacements'/name
                        image.save(path,optimize=True)
                        actual=np.asarray(Image.open(path).convert('RGBA'))
                        assert np.array_equal(actual,np.repeat(np.repeat(native,4,axis=0),4,axis=1)),name
                        core+=int(native.size//4)
                        records[name]=dict(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (folder/'config.yaml').write_bytes(b'# Optional exact-native font compatibility pack.\nMaxVRAMWriteSplits: true\n')
    assert len(list((folder/'replacements').glob('*.png')))==len(records)
    report=dict(version=version,source_disc_sha256=hashlib.sha256(disc.read_bytes()).hexdigest(),
                texture_images=len(records),font_copies=len(sheets),palettes=len(palettes),
                texture_upload_ids_checked=True,all_pixels_equal_native_nearest_4x=True,
                native_palette_samples_checked=core,native_shadows_and_icon_colours_preserved=True,
                generates_new_glyph_art=False,emulator_replacements_required=False,
                installed_or_enabled_by_this_tool=False,emulator_playtest=False,files=records)
    dest=ROOT/('work/output/STT2001_EN_v%s_texture_verification.json'%version)
    dest.write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print('PASS: %d exact-native optional replacement images; %d palette samples.'%(len(records),core),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('version');build(p.parse_args().version)
