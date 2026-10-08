# Disc layout and text format

## Disc (PS1, single MODE2/2352 track)
Extract with `tools/extract_iso.py` into `work/source/disc/`.

| File | Contents |
|---|---|
| SLPS_028.63 | Executable (load 0x80010000). Contains glyph-coded menu strings around file offset 0x9A900. |
| STAGE.DAT | 721 entries. Stages 0–89 use 7 entries each (map TIM, tiles, 2 TIMs, small data, **script overlay**, data). Entries 630+ are CM-compressed images. |
| BATTLE.DAT | 949 entries, mostly TIMs. **#540 = battle quotes** (u32 offset table). |
| MAPMAIN.DAT | 30 entries. **#2 = master database strings**, **#7 = font sheet**, **#27 = sound-test titles**. |
| EVENT.DAT | 805 TIMs (portraits/event art). |
| WAZA1-3.DAT | CM-compressed attack graphics. |
| SOUND.DAT, VORTEX.XA, MOVIE.STR | Audio and video. |

## DAT archive format
`u16 count`, then `count+1` u16 sector offsets (2048-byte sectors). Unpack with `tools/dat_archive.py`.
Entries that start with `"CM"` are compressed. The algorithm is not reversed yet.

## Text encoding
- u16 little-endian glyph codes. 0 = space.
- `FFFE` ends a string. `FFFB` = newline. `FFFC` = wait for a button, then a new page. `FFFD` = (seen as `FFFD 0000`).
- `FF33 <name> FF30` = speaker name tag at the start of a dialogue line.
- `FF31` / `FF32` … `FF30` = colour on/off. `FF02`, `FF04`, `FF06` = name/variable placeholders (they expand at runtime).
- Stage script overlays load at 0x800E0000 and start with a u32 pointer table. Their string block is contiguous.

## Font
- MAPMAIN #7, TIM 512x256 4bpp (an identical copy is EVENT #10). Each pixel packs two 2bpp layers: CLUT F0 reads bits 0-1, CLUT F1 reads bits 2-3 (0 transparent, 1 shadow, 2 mid, 3 bright).
- Lookup routine in the executable at 0x8004A7D8:
  - `code < 320`: 8x16 glyph at `x=(code%32)*8, y=(code//32)*16`. These are digits, kana, Latin and punctuation (`tools/kana_table.py`).
  - `320 <= code < 782`: 12x16 glyph. `a=code-110`, `page=a//336`, `r=a%336`, `x=page*256+(r%21)*12`, `y=(r//21)*16`, layer F0.
  - `782 <= code < 1454`: same formula, but `page-=2` and layer F1.
- The kanji table for codes 320 and up is still pending. Candidates come from `tools/font.py ocr2` and have to be checked by eye.

## VWF (v0.1.0)
- Text drawers: 0x8004A954 (string), 0x8004B92C (dialogue typewriter), 0x8004AEBC (menus), 0x8004CCF0 (numbers). Each one calls the glyph lookup 0x8004A7D8, then advances x by the sprite width (+8). Placement is done by 0x8004D834 (sprite, &x, &y, advance).
- The lookup is rewritten in tools/vwf_patch.py. The width table for codes 320-445 sits right after the code (0x8004A8B4).
- CLUT rows: F0/F1 + 2*colour (colours FF30-FF33 = 0-3). Each layer is 2bpp: 0 transparent, 1 shadow, 2 mid, 3 bright.
- English encoding: work/font/vwf_table.json ("encode": char -> code). Space = 4px.
