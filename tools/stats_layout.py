"""Space the pilot Stats base + bonus (total) fields without changing values."""
import struct

# GUI bytecode at 0x800AA8C0. Packed positions use x/2 in the low byte.
# Preserve the commands, three-digit limits, Y coordinates and stat formulas.
POSITIONS = [
    (0x9B104, 0x7542, 0x7541),  # Eva. base: 132 -> 130
    (0x9B108, 0x8D42, 0x8D41),  # Acc. base
    (0x9B110, 0x7562, 0x7564),  # Eva. total: 196 -> 200
    (0x9B114, 0x8D62, 0x8D64),  # Acc. total
    (0x9B12C, 0x7552, 0x7554),  # Eva. bonus: 164 -> 168
    (0x9B130, 0x8D52, 0x8D54),  # Acc. bonus
]
PUNCTUATION = '+       (       )'


def patch_exe(exe):
    result = bytearray(exe)
    for offset, before, after in POSITIONS:
        actual = struct.unpack_from('<H', result, offset)[0]
        assert actual == before, (hex(offset), hex(actual), hex(before))
        struct.pack_into('<H', result, offset, after)
    return bytes(result)


if __name__ == '__main__':
    import mips
    patch_exe(mips.load())
    for offset, before, after in POSITIONS:
        print('0x%X: x=%d -> %d, y=%d' % (
            offset, (before & 255)*2, (after & 255)*2, before >> 8))
    print('Dry run: six coordinate words; stat values and formulas unchanged.')
