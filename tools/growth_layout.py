"""Fit the Unit panel's two development badges inside their original row."""
import struct

POSITIONS = [
    (0x9B052, 0x7B0C, 0x7B09),  # Grow heading: x=24 -> 18, y=123
    (0x9B060, 0x7B23, 0x7B1C),  # two icon/label groups: x=70 -> 56
]
TEXT = {
    'U20942': '{man}Grow{sword}Grow',
    'U20943': '{man}Grow{sword}Upg.',
    'U20944': '{man}Upg.{sword}Grow',
    'U20945': '{man}Upg.{sword}Upg.',
}


def patch_exe(exe):
    out = bytearray(exe)
    for offset,before,after in POSITIONS:
        actual = struct.unpack_from('<H',out,offset)[0]
        assert actual==before,(hex(offset),hex(actual),hex(before))
        struct.pack_into('<H',out,offset,after)
    return bytes(out)


if __name__=='__main__':
    import mips
    patch_exe(mips.load())
    for offset,before,after in POSITIONS:
        print('0x%X: x=%d -> %d, y=%d'%(offset,(before&255)*2,(after&255)*2,before>>8))
    for uid,text in TEXT.items():
        print(uid,text)
    print('Dry run: move two GUI positions and remove the inter-group space; labels and icons retained.')
