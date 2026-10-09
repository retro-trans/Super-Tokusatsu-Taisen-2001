# Handoff: Japanese text inside images (graphics translation)

Status: **v0.3.18 weapon markers and Parts menu built and verified; public release authorized, 2026-10-09**. The user explicitly requested a GitHub release with the new texture replacement package. Earlier local-build notes below preserve their authorization status at the time.
The text translation is handled separately (see `docs/translator_brief.md`, `tools/insert.py`).

v0.3.18 final verification passed: 17 native font copies, four Parts entries in each live database, 31 native menu draw cases / 80 labels, and all 756 replacement images. Exactly 360 replacement images have new marker pixels; pixels outside the marker cells remain identical. Executable, dialogue, weapon/gameplay data, graphics and movies match v0.3.17. Report: `work/output/STT2001_EN_v0.3.18_weapon_ui_verification.json`. The matching pack is installed cumulatively in the active local DuckStation texture folder; reload/restart to activate it. Actual emulator appearance remains unverified.

v0.3.18 translates the remaining weapon marker glyphs and shortens the popup's Upgrade Parts label to Parts. `tools/weapon_markers.py` changes F0 codes 277/278 to D/I (Direct/Indirect) in four main gameplay font copies and F1 codes 1433..1438 to BLT/ELC/BEM/WTR/FIR/SPL in all 17 right-page copies. Codes, eight-/twelve-pixel advances, palettes, P/MAP markers and weapon mechanics remain intact. The English font allocations and compact Terrain cells are disjoint. `texpack.hires_layers()` restores original shapes for Scale4x before inserting the independent high-resolution markers, including per-scene F1 matching, so neighboring pixels retain their old appearance. UI samples/legend are in `work/ui/weapons/`; the preview is a reconstruction. Parts uses 34px, replacing Upgrade Parts at DB A74/B12/B1E/D8F in both copies. `tools/check_weapon_markers.py --verify` checks allowed font/database differences, unchanged other game data, all 31 native menu draw combinations, and every replacement image. New texture IDs are required; install the 0.3.18 pack cumulatively with `tools/install_font_pack.py` and reload/restart DuckStation. Prior packs alone cannot match the changed font. Emulator appearance remains pending; no release authorization.

Local installation repair (2026-10-09): the user was still using an older pack (believed v0.3.6). DuckStation's log identifies v0.3.17 and only 517 installed replacements; the settings enable texture caching/replacements and the game's config already sets MaxVRAMWriteSplits true. The active data folder is `C:/Users/Binh/AppData/Local/DuckStation`; 720 of the current pack's 756 PNG IDs were absent. `tools/install_font_pack.py 0.3.17 --data-dir C:/Users/Binh/AppData/Local/DuckStation --write` installs missing files while keeping older IDs, verifies all source PNG bytes, and saves `work/output/STT2001_EN_v0.3.17_font_install.json`. The tool defaults to a dry run and backs up any overwrites. DuckStation must reload replacements or restart to rescan; actual emulator appearance still needs confirmation.

v0.3.17 completed-disc verification passed: only the intended executable changes and six labels in both live database copies differ from v0.3.16. The build reports zero problems. Fonts, dialogue, movies, gameplay data and other graphics remain identical; all 757 matching texture-pack files are byte-identical. Report: `work/output/STT2001_EN_v0.3.17_intermission_verification.json`. The preview is a reconstruction; emulator appearance remains unverified.

v0.3.17 fixes Intermission: Support Mecha becomes Mecha (DB D9F); the development row uses Unit/Wpn (D87/D88) and Grow/Upg. (D89/D8A), with positions x=176/204 and 242/270 at y=144. D89/D8A are shared suffix strings without unique frozen translation UIDs, so `intermission_layout.patch_database()` appends dedicated table-index aliases in both database copies; D8B/D8C Scrap options and other text remain intact. `tools/intermission_layout.py` also replaces the native stage-clear composer at 0x8006F8AC..0x8006F9CC: append digits after the complete Stage prefix, then colon/space, title and completion label. The completion string CF1 has a leading English space; captions with at least 28 codes before the suffix use `Clr.` to retain the full title. The caller at 0x80070D14 has a 136-byte caption buffer instead of 56. The footer stays at x=20,y=200. `tools/check_intermission_layout.py` executes the actual caller/composer for all 91 title IDs and numbers 0/1/9/10/90 (455 captions), all four mode combinations and both Mecha submenu/header scripts. Maximum caption advance 284px; maximum caption size 72 bytes. UI screenshots, metadata and reconstruction are in `work/ui/intermission/`. Font textures remain compatible with v0.3.15 packs. No release authorization; emulator testing remains pending.

v0.3.16 changes Spider Man to Man Spider throughout the English text and glossary at the user's explicit request. `tools/man_spider_name.py` applies the source updates and targeted stripped copies; replacements.json prevents the old spelling/hyphenated variant from reappearing during insertion. `tools/check_man_spider.py 0.3.16 0.3.15 --verify` checks 13 story mentions, 10 battle captions, one encyclopedia name and two labels in each database copy; all 26,261 story strings and 12,617 battle quotes retain their limits and unrelated text. Fonts, graphics, executable and raw movie sectors match v0.3.15. The pack is a byte-identical 757-file copy; v0.3.15 packs remain compatible. Report: `work/output/STT2001_EN_v0.3.16_name_verification.json`. No emulator check or release.

v0.3.15 verification passed: four font copies, 21 glyphs, 144 left-page texture variants and all 756 replacement files. Of those, 540 retain their names and bytes; 72 right-page images retain their bytes under new full-sheet hashes. A total of 216 replacement filenames change. Report: `work/output/STT2001_EN_v0.3.15_value_font_verification.json`.

v0.3.15 matches white native UI values to the English label font (GenEi LateGo face 1, 13px, baseline 12). `tools/ui_value_font.py` redraws 21 original F0 cells: digits, unknown marker, percentage sign, S/M/L sizes and A-F terrain grades. Codes, eight-pixel advance and 8x16 cells remain unchanged; wider glyphs fit horizontally inside seven ink columns. The native patch reaches MAPMAIN #7, #25 CM block 3, BATTLE #538 and EVENT #10. BATTLE #537 has encyclopedia tabs and is deliberately excluded; right-page scene fonts and F1 are unchanged. The completed disc differs only in those four font copies. Text, executable positions, formulae, voice timing, dialogue pagination, graphics and movies remain intact. `tools/check_ui_value_font.py 0.3.15 0.3.14 --verify` verifies the disc and the matching 4x pack, including every replacement pixel outside the selected cells. Scale4x uses the original value shapes as its base before independent high-resolution cells overwrite them, so neighboring icon edges stay identical. Font upload hashes change: install the complete v0.3.15 SLPS-02863 folder, including config.yaml. User screenshot, English metadata and native/4x reconstructions are in `work/ui/unit_stats/value_font*`; these are not emulator captures. Emulator appearance remains unverified.

v0.3.14 fixes the clipped second battle-caption body line by moving only the short-frame text origins six pixels up: y=50/182 to 44/176. The four-origin table at EXE offset 0xADAFC is copied by command handlers 0x8007348C / 0x80079EE4; mode 1 selects short battle-frame origins, other modes retain y=22/154 for taller map/story frames. `tools/battle_voice_layout.py` changes exactly two halfwords. The frame/portrait command uses separate origins, which remain untouched. `tools/check_battle_voice_layout.py 0.3.14 0.3.13` executes both actual command handlers (eight cases) and the actual typewriter/glyph lookup. The Lucifard caption uses y=176/192/208, with the last full 16px cell ending at y=224 inside the lower frame; upper rows are 44/60/76, ending at 92. All 12,617 battle quotes are audited; their text, timing and page breaks are unchanged. Other game files and the 757-file font pack match v0.3.13. Original screenshot, UI metadata and schematic reconstruction are in `work/ui/dialogue/battle_voice*`. Emulator appearance remains unverified.

v0.3.13 translates Critical in the shared battle/map strip: MAPMAIN #17 and #25 CM block 5, rectangle x=136..160 / y=0..8. `gfx_translate.callout_lettering()` uses an original 3x5 pixel alphabet (23x5 face plus a one-pixel shadow), because small font-derived lettering was unreadable at this fixed 24x8 size. Palette index 1 remains the face and 4 the shadow, preserving runtime colors. `tools/check_critical_labels.py 0.3.13 0.3.12` checks the completed disc, both copies, unchanged CM blocks, other game files and the identical 757-file font pack. UI metadata: `work/ui/critical.en.json`; original screenshots and reconstruction: `work/ui/graphics/critical_*`. The manifest now has 101 targets. The other battle-strip labels remain pending. Emulator appearance remains unverified.

v0.3.12 moves the Unit panel's Grow heading to x=18 and its two development icon/label groups to x=56. `tools/growth_layout.py` patches position words at EXE offsets 0x9B052 and 0x9B060; overrides U20942..U20945 remove the inter-group space. The body/weapon icons and all four Upg./Grow modes remain intact. `tools/check_growth_layout.py 0.3.12 0.3.11` checks both packed-table nibble paths through the actual MIPS interpreter (eight cases), all four combinations, completed-disc changes and native/4x reconstructions. Maximum right edge is x=146 within the x=148 panel boundary. Only these positions and four database separators differ from v0.3.11. The v0.3.12 texture pack is an identical copy of v0.3.11; older v0.3.10 packs also match. Reports and original screenshots are under `work/ui/unit_stats/` and `work/output/`.

Latest UI fix: v0.3.11 separates the Eva./Acc. base, bonus and total in the pilot Stats screen. `tools/stats_layout.py` moves six position words in the GUI script at EXE offset 0x9B0C0; U20965 / DB index 0xBC2 reserves English punctuation spacing. `tools/check_stats_layout.py 0.3.11 0.3.10` executes the actual MIPS interpreter for 25 cases / 50 rows and checks the completed-disc changes. Examples remain `134 + 68 (202)` and `128 + 68 (196)`. All stats and formulas are preserved. `tools/preview_stats_layout.py 0.3.11` uses the completed font and verified draw list; its previews are reconstructions, not emulator captures.

Terrain ratings on both Unit and pilot Stats screens use compact single-cell AIR/LND/SEA/SPC/KAI/GEN/FUS labels and a two-cell Terrain heading; Unit Stats reads Unit. `tools/ui_glyphs.py` patches database-index aliases and nine unused English F1 cells; `work/translation/en/ui_glyphs.en.json` contains the definitions. The pilot screen caches the first glyph from DB indices 0xAFE..0xB04 in startup code at 0x80013D2C, then 0x80049AE0 draws the cached labels with live grades. The v0.3.11 check verifies this complete path, including heading 0xB76 and all seven grades. Font textures are unchanged from v0.3.10, so the v0.3.11 pack is an identical copy; either works. Keep config.yaml. The v0.3.10 check verified 12 labels, 17 font copies and 160 texture variants. Original reports, metadata and previews are in `work/ui/unit_stats/`. Final emulator appearance remains unverified.

## Current progress

- v0.3.7 replaces EP with Stage on all 90 cards and redraws the numerals with the same regular OFL font. The prefix samples EVENT atlas x=256..308, y=104..128; each numeral uses the middle 12px of its original 24px cell. The suffix is reduced to a 1px blank sample at x=220 on screen, clear of the header. Original black texels are opaque, so overlapping empty quads would erase letters/digits. `tools/stage_cards.py` updates the exact opcode-57/59 signatures in all 90 scene scripts (STAGE entries 6, 13, ... 629). `insert.build_all()` also updates CM block 5 alongside the translated dialogue in block 4. Sprite positions center one- and two-digit stage labels; relative branches and script lengths stay intact.
- EVENT #230 is translated as Lucifard / The Fusion Steel, bringing the manifest to 99 graphics. The source image, generated restoration and final TIM are kept locally. Imagegen reconstructed the obscured artwork; native palette conversion is deterministic and retains the original black borders and all TIM metadata.
- `tools/check_dialogue_layout.py 0.3.7 0.3.6` checks actual built dialogue widths/line counts, complete English content apart from documented label/choice abbreviations, pointer order, terminators, raw/compressed card scripts, all 99 graphics, retained raw movie sectors, disc directory and unrelated files. `tools/preview_layout.py` reconstructs layouts from native pixels and source-script positions; its images are explicitly not emulator captures.
- Dialogue width is 220 px; story body pages have at most three lines, battle quotes two. Saved hero names reserve 96/60 px (surname/given name). Eight speaker aliases and seven shortened choices are documented in `work/translation/en/dialogue_layout.en.json`. Choice menus retain their original option count, including one four-option menu.
- Final built-disc verification passed: 26,261 story strings, 12,617 battle quotes, 90 raw/compressed card routines and 99 graphics. Movie sectors exactly match v0.3.6; MAPMAIN, executable and seven other unrelated files are unchanged. Results: `work/output/STT2001_EN_v0.3.7_layout_verification.json`. Native and optional 4x-font builds report zero problems. Pending: emulator/hardware testing of the new cards, page continuation and restored logo.

### Earlier graphics batch (v0.3.4, retained in v0.3.6)

- 98 TIM targets translated: all 90 episode cards EVENT #52-#141; disclaimer #45; narration #174; title-menu encyclopedia label in MAPMAIN #22 and #23 block 1; options #26 block 0; encyclopedia frames BATTLE #535/#536 and the ten selected-tab glyph cells in #537 F0 row 0.
- English definitions, mapping IDs and allowed pixel rectangles: `work/translation/en/graphics.en.json`.
- Exported native assets: `work/translation/en/graphics/*.tim`. Before/after previews and verification: `work/ui/graphics/`. The contact sheets are texture previews, not emulator screenshots.
- `tools/gfx_translate.py --dry-run` renders and validates without writing; `--write` exports assets and previews. `insert.build_all()` applies the same patches after English font insertion. Unchanged compressed blocks keep their exact bytes.
- Confirmed visually: #72 is the extra Fushigi World card; #97 is the extra Jun card; #99 is a small-font duplicate of #52; #102 is a duplicate of #78 (Superalloy Baronium, database row 1330). Database row 1351 has no separate card in this inventory.
- Episode digits remain byte-for-byte intact. The prefix sprite reads EP; the suffix sprite is blank. Longer title text uses two lines. A few database abbreviations are expanded for the cards without changing the database labels.
- Encyclopedia tabs use A/KA/SA/TA/NA/HA/MA/YA/RA/WA. They continue to group entries by Japanese reading, not by the English alphabet. Only the first ten 16x16 F0 cells in BATTLE #537 are changed; all F1 pixels, other kana cells and English font cells are preserved.
- Structural checks cover CLUTs, TIM headers, payload lengths, allowed rectangles, episode digits and font layers. `tools/check_graphics_build.py 0.3.4 0.3.3` verifies complete built archives and unchanged game files against the previous English build.
- **Verification passed 2026-10-08:** all 98 targets in the final v0.3.4 image match the intended patches. BATTLE/EVENT/MAPMAIN archives match completely; the nine unrelated disc files match v0.3.3 exactly. Disc directory records match the build table. The build reports zero problems. Results: `work/output/STT2001_EN_v0.3.4_graphics_verification.json`. The matching 4x font pack is generated with installation notes.
- **Remaining:** battle labels MAPMAIN #17/#25 block 5 (confirm actual sprite UV rectangles before fitting English); artwork name logo EVENT #231; low-priority placeholder portrait labels; optional copyright romanization. The title logo is retained. FMV remains outside this TIM pass.
- **Pending emulator checks:** boot/menu appearance, episode-number composition, option help line, encyclopedia tab selection and 4x texture replacements. No release is authorized.

## What is already known

All images are PS1 TIMs (4bpp or 8bpp, with a CLUT), either raw entries in the `*.DAT` archives or blocks inside CM-compressed entries.
- Unpacked entries: `work/source/unpacked/<DAT>/<NNNN>.bin`.
- Archive format, CM format and the disc layout: see `docs/text_format.md`.
- CM blocks: `tools/cm.py` (`blocks()` decompresses, `compress()` makes a valid block).
- To rebuild a CM entry after changing one block: `insert.rebuild_cm(buf, {block_index: new_bytes})`. Unchanged blocks keep their original bytes.

### Inventory of images with Japanese text (surveyed 2026-10-08)

| Where | What | Size / format | Notes |
|---|---|---|---|
| EVENT #52–#141 (90 entries) | Episode title cards | 320x128, 8bpp | Title band in rows 20–80; furigana in rows 28–38. Bottom strip (rows 100–127): digits 0–9 at a 24 px pitch (x 5–234), 第 at x 276–293, 話 at x 299–317. The game composes 第 + number + 話 from these. Planned English: title redrawn, 第 → "EP", 話 blanked. |
| EVENT #45 | Disclaimer card | 320x240, 8bpp | Fiction disclaimer; no connection to real people or organizations. |
| EVENT #174 | Narration card | 320x240, 8bpp | Twelve years were about to pass. |
| EVENT #230 | Name logo | 320x240, 8bpp | 融機鋼 ルシファード → "Lucifard, the Fusion Steel" (glossary) |
| EVENT #231 | Name logo | 320x240, 8bpp | EATER ～試験体003～ → "EATER ~Test Subject 003~" |
| EVENT #24–#28 | Face sheets with placeholder labels | 256x256, 8bpp | メタル兄/姉/父, バイオ兄/とうちゃん/カオリ/祖父 (bottom rows). Probably placeholder portraits; low priority. |
| MAPMAIN #22, plus the copy in MAPMAIN #23 (CM block 1) | Title menu | 256x256, 4bpp | キャラクター辞典 (character encyclopedia) above EXIT. Glossy green style like START/CONTINUE/OPTION/EXIT. |
| MAPMAIN #26 (CM block 0) | Option screen | 320x240, 8bpp | Yellow labels 音楽 / デモ映像 / 戦闘映像 (English words SOUND / DEMO MOVIE / BATTLE MOVIE are already beside them). Bottom line: ○ボタン：決定／再生 □ボタン：停止 |
| MAPMAIN #17 (and the copy in MAPMAIN #25, CM block 5) | Battle labels strip | 256x16, 4bpp | シールド 切り払い 分身 チェスト バリヤー クリティカル (Shield, Parry, Afterimage, Chest, Barrier, Critical). The sprite rectangles are fixed, so measure each label's x-range and keep inside it. |
| MAPMAIN #20 | Copyright | 8bpp | ©石森プロ・東映 / ©宣弘社・NTV / ©1966,67,71 円谷プロ / ©東映 / ©光プロ・東映 / ©BANPRESTO 2001. A romanized version is optional. |
| BATTLE #535, #536 | Encyclopedia window frames | 8bpp | 図鑑目次 (Index), kana tabs あかさたなはまやらわ, 登場作品 (Appears in). The kana tabs index entries by Japanese reading. |
| BATTLE #537 (F0 layer row 0) | Large kana tab glyphs | font sheet | あかさたなはまやらわ, used by the encyclopedia tabs. **Careful:** rows 10–15 of F0 and all of F1 now hold the English font (written by `insert.write_font`). |
| MAPMAIN #19, #23 (block 0) | Title logo スーパー特撮大戦2001 | 8bpp | Keep as is (logo). |

Checked and no Japanese found:
- STAGE images (map tiles, unit-number sheets).
- BATTLE #0–#59 (backgrounds).
- BATTLE #541+ (faces).
- WAZA1 sample (effects; "LOCK ON" is already English).
- EVENT #142–#241 (backgrounds, "START/CONTINUE").
- EVENT #242–#291 (だみー placeholders, unused).
- EVENT #292–#804 (unit renders, "NO DATA").
- MOVIE.STR (FMV) was not checked and is out of scope for TIM editing.

## Tools already written
- `tools/contact.py <DAT> <first> <last> <out.png> [thumb]`: contact sheet of every TIM, including CM blocks.
- `tools/tim2png.py`: TIM to PNG.
- `tools/gfx.py`: `Tim(bytes)` loads 4/8bpp with CLUT. It provides:
  - `.fill(x0,y0,x1,y1,index)`
  - `.text(x, y, s, size, rgb, outline=, shadow=, align="center", width=, bold=)`, which renders with Gen'ei LateGo P (SIL OFL 1.1) quantized to the nearest palette colour
  - `.bytes()`
  - `.nearest(rgb)`
  - `.rgb()` for a preview
- `tools/gfx_cards.py`: title-card renderer (`make_card(data, title)`). It was tested on EVENT #52: `python tools/gfx_cards.py "The Man Who Fell to Earth" out.png`.

## Card → title mapping (read from the contact sheets; verify #72, #97, #99 and #102 at full size)

Card numbers are EVENT entries. Numbers in brackets are database string indexes in MAPMAIN #2 (rows of `frozen_strings.json` with src="db", in order). Their English is the translated database row for that index.

- **#52–#71** = [1305]–[1324], in order.
- **#72** = 不思議界 (an extra card, not in the database). Translate as "The Fushigi World".
- **#73–#96** = [1325]–[1348], in order.
- **#97** = 新戦士ジュン登場 (extra card). "A New Warrior, Jun, Appears".
- **#98** = [1350].
- **#99** = small-font duplicate of 地球に堕ちてきた男 (test card). Use [1305].
- **#100** = [1352], **#101** = [1353].
- **#102** = visually confirmed duplicate of #78, 超合金バロニウム [1330]. [1351] has no separate card in this inventory.
- **#103** = [1355], **#104** = [1354].
- **#105–#110** = [1356]–[1361].
- **#111** = [1363], **#112** = [1362].
- **#113–#121** = [1364]–[1372].
- **#122–#128** = [1373]–[1379].
- **#129** = [1388], **#130** = [1381], **#131** = [1382], **#132** = [1383], **#133** = [1384].
- **#134** = [1385], **#135** = [1386], **#136** = [1387].
- **#137** = [1349], **#138** = [1380].
- **#139** = [1389], **#140** = [1390], **#141** = [1391].

## How to wire changes into the build

`tools/insert.py:build_all()` returns `files`, a dict of whole DAT files. Add a step there, or in `tools/build.py` before `repack.rebuild`, that:
1. Loads the entries with `repack.dat_entries(...)`. For EVENT.DAT, start from the already-patched entries: `build_all` already rewrites EVENT #10.
2. Replaces the edited TIMs (raw entries directly; CM entries via `insert.rebuild_cm`).
3. Repacks with `repack.dat_pack(...)`.

Entry sizes may change. The disc re-layout (`tools/repack.py`) handles that.

## Rules
- Follow `AGENTS.md`: version every build, write the changelog, no release without the user's go-ahead.
- Use the OFL Gen'ei font for font-derived lettering. The fixed 24x8 Critical sprite uses original handcrafted pixel lettering for readability. Don't ship Windows system fonts rendered into images.
- Keep each image's palette, and keep text inside the original sprite rectangles. Many UI images are drawn as sub-rectangles of a texture page.
