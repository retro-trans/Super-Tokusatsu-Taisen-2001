"""CM compression (LZSS) used by the game (decompressor @ 0x80098534).

Block layout:
  +0  "CM"
  +2  u16 out_lo, +4 u16 out_hi        -> decompressed size
  +6  u16 len_lo, +8 u16 len_hi        -> byte length of the token stream
  +A  token stream (literal bytes and u16 copy tokens)
  +A+len  flag bits, one per token, LSB first: 1 = copy, 0 = literal
  copy token (u16 LE): offset = (t & 0xFFF) + 1 back from the output end,
                       length = (t >> 12) + 3
Blocks follow each other, each aligned to 4 bytes.

python tools/cm.py unpack <file.bin> <outdir>   -> block_00.bin, ...
"""
import os
import struct
import sys


def decompress(buf, pos=0):
    """Return (data, next_block_pos)."""
    assert buf[pos:pos + 2] == b"CM", "not a CM block"
    lo, hi, llo, lhi = struct.unpack_from("<4H", buf, pos + 2)
    size = lo | (hi << 16)
    slen = llo | (lhi << 16)
    src = pos + 0xA
    flags = pos + 0xA + slen
    out = bytearray()
    t = 0
    while len(out) < size:
        if (buf[flags + (t >> 3)] >> (t & 7)) & 1:
            tok = buf[src] | (buf[src + 1] << 8)
            src += 2
            off = (tok & 0xFFF) + 1
            n = (tok >> 12) + 3
            for _ in range(n):
                out.append(out[-off])
        else:
            out.append(buf[src])
            src += 1
        t += 1
    end = flags + ((t - 1) >> 3) + 1
    used = end - pos
    return bytes(out[:size]), pos + ((used + 3) & ~3)


def blocks(buf):
    pos, out = 0, []
    while pos + 10 <= len(buf) and buf[pos:pos + 2] == b"CM":
        data, pos = decompress(buf, pos)
        out.append(data)
    return out


def compress(data):
    """Greedy LZSS compressor producing a valid CM block."""
    toks, flagbits = bytearray(), []
    i, n = 0, len(data)
    # hash chains of 3-byte prefixes
    heads = {}
    while i < n:
        best_len, best_off = 0, 0
        if i + 3 <= n:
            key = data[i:i + 3]
            for j in reversed(heads.get(key, [])[-64:]):
                off = i - j
                if off > 4096:
                    break
                ln = 3
                while ln < 18 and i + ln < n and data[j + ln] == data[i + ln]:
                    ln += 1
                if ln > best_len:
                    best_len, best_off = ln, off
                    if ln == 18:
                        break
        if best_len >= 3:
            tok = ((best_len - 3) << 12) | (best_off - 1)
            toks += struct.pack("<H", tok)
            flagbits.append(1)
            step = best_len
        else:
            toks.append(data[i])
            flagbits.append(0)
            step = 1
        for k in range(i, min(i + step, n - 2)):
            heads.setdefault(data[k:k + 3], []).append(k)
        i += step
    fl = bytearray((len(flagbits) + 7) // 8)
    for k, b in enumerate(flagbits):
        if b:
            fl[k >> 3] |= 1 << (k & 7)
    hdr = b"CM" + struct.pack("<4H", len(data) & 0xFFFF, len(data) >> 16, len(toks) & 0xFFFF, len(toks) >> 16)
    blk = hdr + bytes(toks) + bytes(fl)
    return blk + bytes((-len(blk)) % 4)


if __name__ == "__main__":
    if sys.argv[1] == "unpack":
        buf = open(sys.argv[2], "rb").read()
        os.makedirs(sys.argv[3], exist_ok=True)
        for k, b in enumerate(blocks(buf)):
            open(os.path.join(sys.argv[3], "block_%02d.bin" % k), "wb").write(b)
            print(k, len(b), b[:16].hex(" "))
