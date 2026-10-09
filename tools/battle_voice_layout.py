"""Move short-frame battle text six pixels up; retain map/story positions."""
import struct

# The shared command handlers copy four Y origins from this EXE table.
# Short battle frames select entries 0/1; taller map/story frames select 2/3.
POSITIONS = ((0xADAFC, 50, 44), (0xADAFE, 182, 176))


def patch_exe(data):
    out = bytearray(data)
    for offset, old, new in POSITIONS:
        value = struct.unpack_from('<H', out, offset)[0]
        assert value in (old, new), (hex(offset), value)
        struct.pack_into('<H', out, offset, new)
    return bytes(out)


if __name__ == '__main__':
    import mips
    original = mips.load()
    patch_exe(original)
    print('Dry run: short battle-frame text Y=50/182 -> 44/176; map/story Y=22/154 unchanged.')
