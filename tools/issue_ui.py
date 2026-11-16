"""v0.9.1 response-label repair, using reserved padding without moving code."""
import struct
import mips

# Save-slot code ends at DD330; Difficulty starts at DD340. Font code ends
# at DDFF0; the original heap starts at DE000. Reserve these two 16-byte gaps.
# The old table pointed at the second word of each in-place translation.
RESPONSES = (
    (0x9AD2C, 0x800AA338, 0x800DD330, 'Evade'),
    (0x9AD30, 0x800AA340, 0x800DDFF0, 'Defend'),
)


def patch_exe(exe):
    import insert
    out = bytearray(exe)
    for pointer, original, address, text in RESPONSES:
        assert struct.unpack_from('<I', out, pointer)[0] == original
        offset = mips.off(address)
        assert out[offset:offset+16] == bytes(16), 'Response padding already used'
        codes = insert.encode_line_tokens(insert.TOKEN.findall(text), {}) + [0xFFFE]
        payload = struct.pack('<%dH' % len(codes), *codes)
        assert len(payload) <= 16
        out[offset:offset+len(payload)] = payload
        struct.pack_into('<I', out, pointer, address)
    return bytes(out)
