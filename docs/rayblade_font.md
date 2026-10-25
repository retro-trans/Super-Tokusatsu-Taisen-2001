# Rayblade font port — local v0.3.32

## Public v0.9.0

The v0.3.30-v0.3.38 font revisions below are included in v0.9.0. Current rendering uses the native 2x atlas, stable public saved-name codes, clipped dialogue clearing, allocator font-tag cleanup and original shared palettes with opaque font quads. The optional v0.9.0 package contains 756 PNGs plus configuration, with the same payload as local v0.3.35-v0.3.38; earlier public packs alone do not match. Font checks verify all 18 native copies and texture upload/palette IDs against the completed release disc. These earlier records are historical; actual emulator/PSP appearance remains pending playtesting.

## v0.3.32: stable saved-name codes

The user reported corrupted related-character names and confirmed the campaign
predated the font change. Saves store the hero's surname/given name as glyph
codes, not text characters. v0.3.30 retained the token inventory but resorted
its code assignments by the new widths. Thus the save structure and checksum
were valid while the stored name codes displayed different letters.

`work/font/encoding.en.json` freezes the exact public v0.3.29 assignments for
all 126 letters, 336 pairs and 160 word tokens. From v0.3.32 the builder enables
`stable_encoding`; never resort persisted IDs when changing fonts or metrics.
`native_font2x.stable_lookup()` replaces the native 380-byte glyph function
with a 360-byte routine which sums each decoded token's current atlas advances.
The old threshold tables are unused on this path. Native icon UVs, 8px values,
font pool markers and the caller's A0/A1 are retained. All text and font sheets
are rebuilt using the stable codes and existing Rayblade widths.

Existing public names, including custom names, therefore render correctly
without a save migration or writes to player state. New v0.3.32 campaigns use
the same public codes. A campaign started before the font change and continued
in v0.3.30/31 still holds its original names and is covered. A NEW campaign first
created in those unpublished builds used interim name codes; its names may need
renaming. No ambiguous code guesses or automatic name replacement are performed.

`check_saved_name_font.py --version 0.3.32` reproduces v0.3.31 corruption and
draws old default/custom names through the actual recursive FF01..FF04 drawer,
glyph allocation and polygon writer. It checks unchanged player bytes, the
native save checksum/pack/load round trip and PS1 instruction delays. The
comparison under `work/ui/font/saved-names-v0.3.32.png` reconstructs actual
emitted packets; it is not an emulator screenshot. Other completed font,
dialogue, gameplay/difficulty and public-source checks cover the rebuilt disc.

Build with `python tools/build.py 0.3.32 --movies`; direct generation adds
`--stable-encoding` to the v0.3.31 command below. Existing public font IDs are
permanent even if a future font needs different widths. Matching texture IDs
change again; use the v0.3.32 optional pack. Cold boot and load an ordinary
save. No GitHub release requested; latest public remains v0.3.29.

## v0.3.31: follow Riot Stars' native rendering

The user rejected v0.3.30's thin, jagged output and requested a comparison
with `../Riot Stars` (the sibling directory is plural). That game's
`tools/font_atlas.py`, `tools/skies_font.py` and `docs/VWF.md` retain a 2x
Skies atlas and render half-size POLY_FT4 glyphs. Its faintest edge is
semi-transparent with blend mode 0; solid ink is opaque. The old STT port
had reduced the bitmap before rendering, losing that source detail.

`tools/native_font2x.py` now follows this method. The original Skies ASCII
samples fit a 24x32 maximum cell, with twice the existing logical advance.
Pack 126 glyphs into 224 rows of the existing 256x256 left F1 page. Expand
336 pair and 160 word tokens into individual FT4 glyphs at draw time; the
stored text codes, VWF advances and 255 retained-object slots stay intact.
The 23 native value/D/I glyphs are centered in their original slots. GenEi
still supplies unsupported characters and the compact terrain/weapon icons.

The glyph lookup marks objects only within the native font pool. The fast
sprite sorter redirects marked font objects to the polygon writer; other
sprites retain the original sorter. Preserve retired-object behavior, RGB,
screen offsets, CLUT colors and ordering-table depth. Reuse original VRAM
areas and the old Select helper's unused space. Code/data end exactly at
the existing heap boundary, 0x800DE000. Check the shared primitive-buffer
limit on every polygon; a full 255-object/1,275-glyph frame uses 51,000
bytes, below the 98,304-byte font limit and 114,688-byte buffer size.

Build with `python tools/build.py 0.3.31 --movies`. Direct font generation
uses `python tools/efont.py build --rayblade --keep-glyphs --native-2x`.
The builder applies this path for v0.3.31+, retaining v0.3.30 behavior for
historical rebuilds. All 18 native font copies and scene F1 palettes are
updated; F0 pixels/palettes and upload extents are preserved. The optional
matching texture ZIP contains 882 images plus configuration. Native F1
atlas replacements use integer scaling, without contour filters.

Run `check_native_font2x.py --version 0.3.31 --verify` for actual token
decoder/polygon execution, all fixed-width markers, full-pool/OT stress,
register preservation, bounds, fallback and blending checks. It reconstructs
the Intermission comparison from actual retained objects and emitted GPU
packets. This is an offline preview, not an emulator screenshot. The
completed-image font, content/layout, public-source, gameplay/difficulty,
save/checksum and PS1 delay checks pass. Title v0.3.31/full credit inspected.
See `work/output/STT2001_EN_v0.3.31_*verification.json`.

Use 2x or 4x internal resolution in DuckStation to display the additional
native detail without replacement textures. Original-resolution PS1/PSP
output is still constrained by its pixel grid. Hardware/emulator appearance
and performance remain pending playtesting. Cold boot the new CUE and load
an ordinary save. A bare v0.3.30 upgrade and matching optional texture ZIP
are under `work/output/`; installation instructions accompany them.
No GitHub release has been requested for this build. The latest public
release remains v0.3.29. Both sibling repositories were read without edits.

## v0.3.30: original reduction (superseded locally)

The user requested the font currently used in `../Seireiki Rayblade` on
2026-10-25. That project's public v0.7.0 uses the original Skies of Arcadia USA
Dreamcast Latin bitmap. Its font bank matches the local 0.1.44 `WIN00.AFS`
member: SHA-256 `5fe1480136b8c7d2bb15a32b17588edc0459fcf9c1079c9aa4b1075e11a4d181`.
The Rayblade project and original source files are read without modification.

`tools/rayblade_font.py` reads its 95 ASCII masks and medium-bank advances.
The source masks use four coverage levels. Original 32×64 masks are padded
to 48×64 for this game's 4x cells, preserving every source pixel. Native PS1
12×16 cells use the same 4:1 area reduction and four-level quantization for
every character. No letter receives an individual horizontal stretch.
Accents and symbols absent from the source retain the existing GenEi font.
Native palettes and the optional texture pack retain this game's text colors.
Actual Rayblade GPU blending is not reproduced or claimed.

The native game font, fixed-width UI values, D/I markers and optional 4x pack
share the selected family. Pre-rendered stage artwork, logos, movie captions
and the separate automatic title credit retain their existing presentation.
The title credit still displays the exact v0.3.30 and Retro Trans address.

Existing single-character/pair/word inventories are retained, with code
assignments sorted by the new widths. Rebuilding all text and font copies
updates their references together. Compiled dialogue uses the new advances;
working translations and wording are preserved. Every original font copy,
including scene-specific right pages, is rebuilt. The game runs natively
without texture replacement; 4x replacements provide the sharper source masks.

Build with `python tools/build.py 0.3.30 --movies`. This selects the new family
and regenerates its glyphs. `--keep-font` is accepted only if the cached family
matches the version. Direct regeneration:
`python tools/efont.py build --rayblade --keep-glyphs`.
The local source cache is ignored under `work/source/font/`; the original
game font is not bundled as a standalone font asset. GenEi fallback uses its
existing SIL Open Font License. The Skies glyph artwork remains SEGA/Overworks
game artwork; no new license is granted.

`tools/check_rayblade_font.py` checks the completed disc independently against
the source-bank words, all 18 font copies and native VWF execution. It audits
all 26,261 story strings and 12,617 battle quotes against v0.3.29 using that
build's saved encoding metadata, preserving visible content and pointer order.
Body lines fit 220px, with at most three story lines or two battle lines.
It validates every replacement upload/palette ID and compares source glyph
cores through all matching main-font palettes. Raw movies/audio and unrelated
sound/attack data remain exact. Completed-image public-source, difficulty,
gameplay, save/checksum/load and instruction-delay checks also pass.

Records live in `work/output/STT2001_EN_v0.3.30_*verification.json`.
The comparison and actual retained-glyph reconstructions are under
`work/ui/font/` and `work/ui/difficulty/`. These are offline reconstructions,
not emulator screenshots. Native PS1 output necessarily has less detail than
the 4x masks. Actual emulator/PSP appearance still needs playtesting.

Use the new matching texture ZIP with this build: older texture IDs alone
cannot replace the changed font. Cold boot the new CUE and load an ordinary
in-game save. No GitHub release has been requested for v0.3.30.

## v0.3.34: dialogue clear animation

The reported flashing at the top of the dialogue frame was a native 2x renderer regression. The original clear routine (`0x8004c2a4`) moves glyphs upward, clamps them at the top of the text area, advances their texture V, reduces their height and changes their color. v0.3.31-v0.3.33 still emitted a full-height quad for those objects, including objects whose native height was already zero. Several old lines therefore accumulated in one row and flashed as the color byte continued changing.

v0.3.34 respects the original zero-width/height visibility checks. For visible glyphs it adds twice the native cell's low-four-bit V crop to the 2x atlas V, uses the current native height for the quad, and samples twice that height in the atlas. The original clear routine, duration, text contents and saved-name encoding remain unchanged. The native 2x artwork and 882 replacement images/configuration are byte-identical to v0.3.32/v0.3.33, so either installed pack still matches.

The stable lookup has replaced its old trampoline since v0.3.32. Reclaim that unused trampoline for this repair, keeping the draw helper below the existing `0x800de000` heap boundary; it ends at `0x800ddff0`. Builders/public-source checks enable the repaired path only for v0.3.34+. Earlier versions retain the old draw-code generation for historical rebuilds.

`tools/check_font_transition.py --version 0.3.34 --verify` executes 35 frames of the original clear routine with retained glyphs. It reproduces 874 zero-height ghost observations in v0.3.33, checks 2,346 clipped packets in the repaired renderer, verifies an immediate clear and checks that the same speaker's next page has no old rows. Completed-disc checks require precisely the new draw helper/hook and automatic title stamp; every other raw disc byte, including the v0.3.33 opening-song update, remains exact. This uses the native text allocator/clear/draw code with controlled fixtures; it is not a full emulator capture.

The normal native-font verifier also checks six zero-size cases, 622 token expansions, fixed-width values, the full packet pool, registers and fallback. Saved-name checks, all story/battle bounds, texture IDs, difficulty/gameplay, PS1 instruction delays and the English-only source rebuild pass. Use `tools/check_rayblade_font.py --version 0.3.34 --movie-baseline 0.3.33` to compare the font/text against public v0.3.29 while independently retaining the approved opening revision. The completed title copies show v0.3.34 and github.com/retro-trans.

Local test files are `work/output/STT2001_EN_v0.3.34.bin/.cue`, the bare v0.3.33 upgrade and matching optional texture ZIP. Cold boot the new image and load an ordinary game save. The reconstructed comparison is `work/ui/font/clear-transition-v0.3.34.png`; emulator/PSP confirmation remains pending. No release was requested or published.

## v0.3.35: numeric-slot reuse and native weapon badges

The next report showed corrupt HP/EN digits and solid white weapon markers. The retained 8px number drawer (`0x8004cfa8`, reached through `0x8004ce30`) initializes native numeric UVs directly, without calling glyph lookup. Reusing an English text object therefore left the native 2x token/marker at offsets 0x18/0x1a in place. The font sorter interpreted the new number as its old English token. Clear the marker whenever `0x8004c0ec` returns an allocated/reused object; real text lookup marks it again. A 16-byte cleanup at `0x8004a940` fits the existing width-routine padding, with no new heap/VRAM allocation.

The white badges had a separate cause. Native F1 attribute glyphs share the palettes modified for the new font. Their gray level-1 badge backgrounds were brightened to the same shade as their lettering. Restore the exact original shared palettes in all 18 font copies. Keep the 2x atlas pixels and draw the font with opaque FT4 quads using the original palette shades, so the native STP flags cannot dim the font's solid strokes. Native badge drawing retains its original palette/behavior. The same glyph artwork and advances remain in place; this changes palette rendering rather than the font face.

`tools/check_native_ui_font.py --verify` executes both native numeric formatters and the real allocation/reuse/finalizer path. It covers 36 small/large number cases, same-group and retired-slot reuse, zero/multi-digit values, and English text after numeric reuse. All 18 old small-number corruption cases reproduce; repaired small-number packets equal the original native drawer byte for byte. Completed-image checks permit only the exact allocation/font-draw changes, palette restoration and automatic title stamp, requiring every other raw disc byte to match v0.3.34. All 17 native right-page icon sheets match the public v0.3.29 F1 artwork, and all 18 shared palettes match their original values.

The earlier static-font tests used freshly initialized objects and missed the number drawer's reuse of marked English objects. The native clear regression still passes for v0.3.35, including clipping and an empty old page; normal geometry remains identical, with the intentional opaque draw-mode change. Saved names, text bounds, glyph/pool limits, texture IDs, gameplay/difficulty, instruction delays and English-only source rebuild also pass. Source glyph pixels, text, gameplay and the v0.3.33 movie/audio update are preserved.

The local build is `work/output/STT2001_EN_v0.3.35.bin/.cue`, with a bare v0.3.34 upgrade and matching 756-image texture ZIP. Install this pack if replacements are enabled: the restored F1 palette hashes differ from v0.3.32-v0.3.34. The native badge reconstruction is `work/ui/font/native-ui-v0.3.35.png`; actual emulator/PSP playtesting remains pending. Both completed title copies show v0.3.35 and github.com/retro-trans. No GitHub release was requested or created.
