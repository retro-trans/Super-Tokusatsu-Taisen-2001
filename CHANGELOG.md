# Changelog

## Repository (2026-10-08)
- Published the toolchain to GitHub as a private repository, now in the retro-trans organization: retro-trans/Super-Tokusatsu-Taisen-2001 (created under binhlt0402, then transferred). There is no release; per AGENTS.md, releases wait for an explicit request. The README follows the layout of retro-trans/SRW-Z.
- New `tools/strip_jp.py` writes the git-safe `*.en.json` copies. It drops the Japanese source fields and blanks long Japanese runs, keeping names and UI terms. It also writes `work/script/occurrences.json`, where each string sits on the disc, with no text. `--check` audits a file list.
- `.gitignore` now also excludes disc images (`*.bin`, `*.cue`, `*.iso`, `*.chd`), edited TIMs, exported game graphics and frames, font-sheet atlases, `incoming/`, logs and the raw library glossary.
- Public build mode: without the Japanese working files (or with `STT_PUBLIC=1`), `tools/insert.py` uses the `*.en.json` copies and the occurrence map, and decodes the Japanese from the user's own disc. Checked: v0.3.6 built this way is byte-identical outside MOVIE.STR.

## 0.3.6 (local test build, not released)
- Story dialogue is verified 100% English. All 26,261 stage-script strings (16,179 unique) and all 12,617 battle quotes (3,102 unique) have English, and none still contains Japanese. A scan of every archive entry and compressed block on the built disc finds Japanese text only in MAPMAIN #3, an old database copy that no code loads (checked against all 66 calls to the file loader). The original disc has 58,833 Japanese strings in 656 entries.
- Encyclopedia: 85 entries were never translated, and now are (batch B0268). They use glyphs from the third battle-font page (codes 1454-1789), which the text dumper's `is_text()` skipped. The entries are recorded in work/script/ja/frozen_extra.json. Insertion accepts those codes (`is_text_battle`).
- Encyclopedia size: the English would have reached 0x801A7000, which the exe uses as a work area. Identical self-contained strings and tails are now shared (`rebuild_encyc`): 126,720 bytes, under the 0x1F000 limit. All 1,715 entries read back identically to the unshared layout. Strings chained with FFFD and the first entry keep their place.
- Music titles: the first title ("Banpresto Logo") shares a run with header data and was skipped. It is now translated (135 titles).
- Includes everything in 0.3.4 (graphics) and 0.3.5 (subtitled movies; the movie region is byte-identical to 0.3.5) and the 0.3.3 fixes. The 4x font pack is unchanged from 0.3.5.
- Build-number conflict, fixed: this work was first built as "0.3.4", which overwrote the graphics session's v0.3.4 image (13:01), its report and its 4x pack folder. The image was rebuilt from v0.3.5 with the original MOVIE.STR sectors; v0.3.5 is defined as v0.3.4 plus movies with every other byte identical. Movie sectors match the original disc, all other bytes match v0.3.5, and the image's sha256 is 141eb563…c085. The pack folder matches v0.3.5's file for file. The v0.3.4 report JSON could not be recovered.

## 0.3.5 (local movie-subtitle test build, not released)
- Integrated the approved movie preview translation into the game's original PlayStation STR movies: 26 captioned clips and both credit rolls, totaling 4,722 changed frames. The other 46 movies remain original.
- Native captions preserve all English text and the minimum 0.5-second post-voice hold, replacing the previous caption when the next line begins. Battle captions wrap at 160x128; larger movies use 320x240. Original Japanese XA audio, all frame counts, movie offsets and sector allocation are preserved.
- Added a reproducible jPSXdec encoding/insertion pipeline and a --movies build option. Only caption/credit frames are re-encoded to fit their existing slots. Full-frame encoding was selected after the partial-frame method dimmed lettering in STR-v3 frames. The review-only lyric draft stamp is omitted from the game; the approved draft lyrics and existing gaps are retained.
- The build retains v0.3.4's English text, 98 translated graphics and matching optional 4x font pack. Movie verification checks actual inserted streams, unchanged nonmovie disc bytes, native decoding and modified-sector EDC/ECC. Emulator/hardware playback still needs testing.
- Verification passed: all 28 inserted movies decode at their original native sizes/frame counts; all XA audio and 46 unedited movies match their originals. All 46,587 changed video sectors have valid EDC/ECC. The ISO directory, all file LBAs/sizes and every disc byte outside MOVIE.STR match v0.3.4. The build reports zero problems.

## 0.3.4 movie previews, revision 2 (2026-10-08, local review only)
- Subtitles now remain visible for at least 0.5 seconds after each voice line, ending sooner when the next subtitle begins. Existing longer holds are preserved.
- Recorded voice-end bounds separately so repeated rendering does not keep extending captions. Rebuilt affected individual MP4s and both reels; game image and credit-page timing are unchanged.
- Saved the subtitle timing preference in AGENTS.md and added verification of the post-voice hold and non-overlap.
- Verification passed for all 76 MP4s and 34,724 decoded frames. All 71 ASS/SRT caption timings satisfy the hold rule; 29 are replaced sooner by the following caption. A rendered narration frame confirms the longer hold.

## 0.3.4 movie previews, revision 1 (2026-10-08, local review only)
- Exported all 74 movies from the original PS1 STR/XA stream: 64 battle clips and 10 larger movies. Correct playback is 12 fps with 18.9 kHz stereo XA audio.
- Added local Whisper large-v3 transcription tools, independent VAD/non-VAD checks, short-window checks and an English subtitle manifest. Raw Japanese transcripts and model files remain in work/source/movies.
- Created MP4 previews with English narration, attack/transformation calls and draft opening-song lyrics. Translated both credit rolls' headings/company names; staff names without verified readings retain their credited Japanese form.
- Added original exports, 74 individual English review MP4s, chaptered main/battle reels, subtitles and reproducible rendering/verification tools. Uncertain calls/lyrics are recorded in the movie handoff; some unresolved words are omitted rather than fabricated.
- Verification passed for 76 MP4s: full video/audio decoding, all 17,362 original frames in the individual files and again in the two reels, monotonic timestamps, subtitle bounds and 74 reel chapters. Subtitle widths and representative narration, song and credit frames were checked visually.
- This is a video review set associated with v0.3.4; the game image is unchanged. No release or game movie insertion was performed.

## 0.3.4 (local test build, not released)
- First graphics translation batch: 98 TIM targets. All 90 episode title cards are in English, including the extra Fushigi World/Jun cards and duplicate cards. Episode digit sprites are preserved; the prefix reads EP and the suffix is blank.
- Translated the fiction disclaimer, twelve-year narration, title-menu encyclopedia label (both copies), option labels/help line, and encyclopedia Index/Appears in headings.
- Encyclopedia tabs use romanized Japanese-reading groups A/KA/SA/TA/NA/HA/MA/YA/RA/WA. Their selected-tab glyphs change only ten F0 cells; the existing English font and all F1 pixels are preserved.
- New reproducible graphics pipeline: `tools/gfx_translate.py`, `work/translation/en/graphics.en.json`, exported TIMs and visual previews. Builds apply graphics after font insertion, preserving every original palette and untouched compressed block.
- Added bounded lettering that fits measured regions and fails on overflow. Visual QA fixed residual Japanese pixels below the encyclopedia entry heading. Card #102 was verified as a duplicate of Superalloy Baronium.
- Verification passed for all 98 targets: headers, CLUTs, native sizes, sprite boundaries, digit sprites and font layers. All three edited archives match the intended patches, the nine unrelated disc files match v0.3.3, and disc directory records are valid. The build reports zero problems. The matching 4x font pack is included. Emulator appearance and behavior still need testing.
- Remaining image work: battle label strip, two artwork name logos, placeholder portrait labels and optional copyright romanization. Original title logo retained; FMV outside this pass.

## 0.3.3 (local test build, not released)
- New: a 4x font texture pack for DuckStation, work/output/STT2001_EN_v0.3.3_4x_font/ (README inside), made by tools/texpack.py and generated by every build.
  - DuckStation names a replacement by the XXH3-64 hash of the uploaded font sheet and of the 16-colour palette. This was checked against real dumps of v0.3.2.
  - The pack covers every font sheet, text colour, layer and blend mode (378 files).
  - English glyph cells are redrawn at 4x from Gen'ei LateGo with the same metrics. The other cells are upscaled with Scale4x.
  - The 4x English glyphs have a fine drop shadow: 2 hi-res px right and down, in each colour's own shadow shade (palette level 1). It is set by `SHADOW` in tools/texpack.py. The 1x font has no shadow, as since 0.3.2.
  - The pack ships a config.yaml with `MaxVRAMWriteSplits: true`. Story scenes upload their right font page over half of the main sheet, and with DuckStation's default of 0 splits the whole sheet stops being tracked, so the font was not replaced there. DuckStation reads this option as a bool, so the number 8 was rejected ("Unexpected non-bool value"). Found in testing.
- Hero-select screen: the hero's full name ran into the heroine's. The hero column moves from x=64 to 56 and the heroine column from 168 to 184 (exe layout table at 0x800B3434). The surname and given name are now joined by the 4 px English space instead of the 8 px code 0 (0x8005F50C).
- Default names: the save data has room for 8 codes per surname and 5 per given name. "Takuma" took 6 codes and ran into the heroine's name, which would have garbled [HERO2] in dialogue. The 24 px word glyphs are now written into every font sheet: main and battle fonts, plus the per-scene right pages EVENT #11-#23, which English no longer uses for kanji. The default-name list may use them, so "Takuma" is T-a-k-u-ma, 5 codes. The build checks the save-buffer limits (`insert.check_default_names`).
- Fixed: the regex term fixes in replacements.json never applied. JSON read `\b` as a backspace character. Hien→Hiryu, Kano→Kanou, Magmalizer→Magma Riser, Gelderm→Geldam, M78 Nebula→Nebula M78, Makai Castle→Demon Castle, Hell Valley→Jigokudani, Captain Salah→Captain Saller and the Unicorn Agency now apply.
- 気力 is now "Will", the Super Robot Wars English term (58 strings), which also fits the 24 px stat label. The Shocker combatants' cry is "Eeee" (21 strings).
- Battle forecast and unit windows: サイズ is "Sz." to fit its 24 px label. The enemy-phase command 反撃開始 is "Attack", to fit the 48 px cursor. The Effects options are "Circle: Normal" / "Square: Simple" (exe copies "Circ.: Normal" / "Sq.: Quick"); the old ○ code now shows part of a word glyph.
- Unit names in the map windows (about 134 px) are shortened for this one occurrence, using new "@FILE:offset" keys in overrides.json. The encyclopedia keeps the full names. Examples: Beret Combatant, Mask Combatant, K. Rider BLACK RX, Cmdr. Hessler, Type 75 SP How.

## 0.3.2 (local test build, not released)
- English font: removed the drop shadow, the dark pixel to the right of and below each stroke (`SHADOW = False` in tools/vwf_font.py). Glyph widths, glyph codes and the VWF width thresholds are unchanged, so line wrapping stays the same. Japanese glyphs (names, UI terms) keep their original shadow.
- Before/after previews: work/ui/font_shadow_before.png, work/ui/font_shadow_after.png.

## 0.3.1 (local test build, not released)
- Memory-card save title is now English: "STT2001 File n EPnn" in full-width Shift-JIS, as the BIOS needs. The code that fills in the title (0x80042e14) writes the slot digit 2 bytes earlier, and episodes 1-9 get a leading zero instead of a space. Added `insert.patch_save_title`, which the build calls.
- All non-image text is now English. The only Japanese left is inside images; that work is paused as asked (see docs/handoff_graphics.md).

## 0.3.0 (local test build, full text translation, not released)
- All dialogue and game text is now in English: 26,261 stage script strings, 12,617 battle quotes, 829 encyclopedia entries, 2,914 database strings (units, weapons, abilities, menus, episode titles), 134 music titles and 58 menu strings in the exe. The build reports 0 problems.
- All 267 translation batches are done (6 translator agents). Names follow work/glossary/names.json and docs/glossary_decisions.md, and replacements.json fixes the terms that were inconsistent across batches.
- Fixes found in QA: choice rows put each option on its own line; 188 list names that had been shortened are restored to the full name, and 14 that were too long are shortened by hand; menu width budgets now use the neighbouring strings instead of a strict limit per string; three weapon names that only exist in DB #24 were added to manual.json.
- Sizes are within the RAM limits. Largest stage overlay: 56,628 B (limit 76,800). Encyclopedia: 120,392 B (limit 126,976). Database: 37,712 B (limit 53,248).
- Still in Japanese: text drawn inside images (see docs/handoff_graphics.md; this work is paused) and the memory-card save title (fixed in 0.3.1).
- Not yet tested on hardware or in an emulator: boot after the disc re-layout, choice and menu field widths, the name-entry grid and the shortened exe menu labels.

## 0.3.0 development notes
- Encyclopedia: 24 px "word glyphs" (160 two-cell glyphs, codes 446-781, battle font BATTLE #538 only); the VWF routine gained a third range with a 24-entry width table (380/380 bytes). The English encyclopedia is ~120 KB, within its RAM window (0x80188000..0x801A8800).
- Library glossary: tools/build_library.py builds work/glossary/library.json + docs/library_glossary.md from the translated encyclopedia and fills character notes in names.json (now 1117 entries). docs/glossary_decisions.md records term decisions (Fusion Steel, Hiryu, transformation calls, choice rows...).
- Insertion: per-occurrence lookup against the frozen dump (work/script/ja/frozen_*.json); global term replacements (replacements.json, regex aware); per-uid overrides (overrides.json); choice rows rendered one quoted option per line; name-entry grid rows encoded with fixed-width 8 px Latin glyphs; leading colour code no longer mistaken for a speaker tag; words wrap only at spaces.
- Graphics (Japanese text inside images) surveyed and paused: see docs/handoff_graphics.md (tools/gfx.py, tools/gfx_cards.py, tools/contact.py).

## 0.2.0 (local test build, partial translation, not released)
- Full text pipeline: every text source is decoded with the right font (per-scene kanji sheets EVENT #11-#23, battle font BATTLE #538, map font for map-phase strings), dumped, translated in batches, and re-inserted with automatic word wrap and pagination.
- English font v2: 126 single glyphs (codes 320-445) + 336 two-letter glyphs (codes 782-1117), each range sorted by width; the VWF routine now computes widths from 12 thresholds per range (no width table), so every text drawer gets proportional spacing.
- Written into every font sheet: MAPMAIN #7 and #25, EVENT #10, BATTLE #537 and #538.
- Containers rebuilt with remapped pointers: stage script overlays (both the uncompressed copies and the CM-compressed STAGE #630-719), battle quote overlays (475 BATTLE entries), encyclopedia (BATTLE #540), database (MAPMAIN #2 and #24, incl. shared-suffix pointers), music titles (MAPMAIN #27), exe menu strings (in place).
- Disc re-layout: files from STAGE.DAT on are packed back to back and DUMMY.DAT (padding) shrinks to absorb growth; root directory records updated.
- New tools: cm.py (CM LZSS decompress/compress), fontsets.py, ocr_aa.py, fix_labels.py, dump_script.py, make_batches.py, check_batch.py, efont.py, insert.py, repack.py, preview_text.py.
- Translation in progress (6 translator agents); this build mixes English and Japanese.

## 0.1.1 (local test build, not released)
- Test text moved to where it shows first: the opening narration and Commander Sawa's line (STAGE #5 and #12, both hero routes) and the hero-select confirmation "Is this OK?" (MAPMAIN #2). The stage-1 Hongo lines and the end-phase prompt from 0.1.0 are kept.
- Unused slots in shortened test strings are padded with FF30 (no-op colour reset) and the original terminator stays in its place.

## 0.1.0 (local test build, not released)
- VWF: rewrote the glyph-lookup routine (SLPS_028.63 @ 0x8004A7D8) so the sprite width (which every text drawer uses as its x-advance) comes from a per-glyph width table for the English glyphs. Original 8/12px behaviour for all other codes was verified identical in a Python model.
- English font: Gen'ei LateGo P v2 (Latin glyphs from Linux Biolinum, SIL OFL 1.1) at 13px, drawn in the game's 2bpp style (core, anti-alias, drop shadow). 123 glyphs (ASCII + curly quotes, ellipsis, dashes, accents, ♪♥★☆) in codes 320-442. Written to both font sheet copies (MAPMAIN #7, EVENT #10).
- Test-only text: placeholder English over 8 stage-1 opening lines and the "end phase? Yes/No" prompt (`--test-text`).
- New tools: vwf_font.py, vwf_patch.py, discimage.py (in-place sector writer with EDC/ECC), build.py, mips.py.
- Note: English glyphs replace the kanji at codes 320-442, so untranslated Japanese text that uses those kanji shows Latin letters instead.

## Unreleased (pre-0.1.0, research)
- Set up the project folder layout (work/, docs/, tools/, incoming/).
- tools/extract_iso.py: extracts the disc files from the MODE2/2352 image.
- tools/dat_archive.py: unpacks the *.DAT sector archives.
- tools/tim2png.py: converts PS1 TIM images to PNG.
- tools/sjis_scan.py: finds Shift-JIS text runs. The game turned out to use its own glyph codes, not Shift-JIS.
- tools/font.py: cuts glyphs from the font sheet (MAPMAIN #7), builds atlases and suggests a character for each glyph.
- tools/kana_table.py: code-to-character table for codes 0–319 (kana, Latin, punctuation).
- tools/text_census.py: counts the text. Results are in docs/text_census.md.
- docs/text_format.md: disc layout, text encoding and font lookup.
