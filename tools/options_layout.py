"""Relocate every Options title pointer after translating MAPMAIN #27.

The first u32 points to a relative u16 string table, not to a string stream.
Keeping that table unchanged can land inside a different translated title.
"""
import struct


def rebuild(buf, tr):
    import insert
    base = struct.unpack_from('<I', buf)[0]
    count = struct.unpack_from('<H', buf, base)[0] // 2
    table = struct.unpack_from('<%dH' % count, buf, base)
    first = base + min(table)
    out = bytearray(buf[:first])
    remap = {}
    pos = first
    while pos + 2 <= len(buf):
        q = pos
        while q + 2 <= len(buf) and struct.unpack_from('<H', buf, q)[0] not in (0xFFFE, 0xFFFD):
            q += 2
        if q + 2 > len(buf):
            break
        words = list(struct.unpack_from('<%dH' % ((q-pos)//2), buf, pos))
        term = struct.unpack_from('<H', buf, q)[0]
        remap[pos] = len(out)-base
        # A few records have a pointer to their empty terminator too.
        replacement = tr.words_for('music', words, '11', ('MAPMAIN0027', pos)) if words and insert.D.is_text(words) else None
        out += insert.pack_words(replacement if replacement is not None else words)
        remap[q] = len(out)-base
        out += struct.pack('<H', term)
        pos = q+2
        if not any(buf[pos:]):
            break
    relocated = []
    for value in table:
        address = base + value
        if address not in remap:
            raise ValueError('Options title offset is not a record boundary: 0x%X' % address)
        offset = remap[address]
        assert offset < 0x10000
        relocated.append(offset)
    struct.pack_into('<%dH' % count, out, base, *relocated)
    return bytes(out)+bytes((-len(out)) % 4)
