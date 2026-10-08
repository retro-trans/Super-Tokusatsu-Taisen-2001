# Handoff: Japanese text inside images (graphics translation)

Status: **resumed 2026-10-08; first graphics batch implemented in local v0.3.4**.
The text translation is handled separately (see `docs/translator_brief.md`, `tools/insert.py`).

## Current progress

- 98 TIM targets translated: all 90 episode cards EVENT #52-#141; disclaimer #45; narration #174; title-menu encyclopedia label in MAPMAIN #22 and #23 block 1; options #26 block 0; encyclopedia frames BATTLE #535/#536 and the ten selected-tab glyph cells in #537 F0 row 0.
- English definitions, mapping IDs and allowed pixel rectangles: `work/translation/en/graphics.en.json`.
- Exported native assets: `work/translation/en/graphics/*.tim`. Before/after previews and verification: `work/ui/graphics/`. The contact sheets are texture previews, not emulator screenshots.
- `tools/gfx_translate.py --dry-run` renders and validates without writing; `--write` exports assets and previews. `insert.build_all()` applies the same patches after English font insertion. Unchanged compressed blocks keep their exact bytes.
- Confirmed visually: #72 is the extra Fushigi World card; #97 is the extra Jun card; #99 is a small-font duplicate of #52; #102 is a duplicate of #78 (Superalloy Baronium, database row 1330). Database row 1351 has no separate card in this inventory.
- Episode digits remain byte-for-byte intact. The prefix sprite reads EP; the suffix sprite is blank. Longer title text uses two lines. A few database abbreviations are expanded for the cards without changing the database labels.
- Encyclopedia tabs use A/KA/SA/TA/NA/HA/MA/YA/RA/WA. They continue to group entries by Japanese reading, not by the English alphabet. Only the first ten 16x16 F0 cells in BATTLE #537 are changed; all F1 pixels, other kana cells and English font cells are preserved.
- Structural checks cover CLUTs, TIM headers, payload lengths, allowed rectangles, episode digits and font layers. `tools/check_graphics_build.py 0.3.4 0.3.3` verifies complete built archives and unchanged game files against the previous English build.
- **Verification passed 2026-10-08:** all 98 targets in the final v0.3.4 image match the intended patches. BATTLE/EVENT/MAPMAIN archives match completely; the nine unrelated disc files match v0.3.3 exactly. Disc directory records match the build table. The build reports zero problems. Results: `work/output/STT2001_EN_v0.3.4_graphics_verification.json`. The matching 4x font pack is generated with installation notes.
- **Remaining:** battle labels MAPMAIN #17/#25 block 5 (confirm actual sprite UV rectangles before fitting English); artwork name logos EVENT #230/#231 (restore artwork beneath lettering); low-priority placeholder portrait labels; optional copyright romanization. The title logo is retained. FMV remains outside this TIM pass.
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
| EVENT #45 | Disclaimer card | 320x240, 8bpp | この物語はフィクションです。実在の人物・団体とは関係ありません。 |
| EVENT #174 | Narration card | 320x240, 8bpp | そして、12年の歳月が流れようとしていた… |
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
- Use only the OFL Gen'ei font for new lettering (it is already used). Don't ship Windows system fonts rendered into images.
- Keep each image's palette, and keep text inside the original sprite rectangles. Many UI images are drawn as sub-rectangles of a texture page.
