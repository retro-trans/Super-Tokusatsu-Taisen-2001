# Native title artwork and ending credits

Local revision: v0.9.7. These are disc bitmap/movie edits; no texture replacement is required.

v0.9.7 intertitles: the narration at EVENT 174 now uses a generated sentence-case line. All 90 episode cards use a shared image-generated uppercase glyph sheet for title wording, STAGE and the changing numbers. This gives every chapter the same appearance without generating slightly different typefaces for each title. `tools/image_intertitles.py` locates the eight rows of the source sheet, samples 45 verified glyphs, fits titles into at most two lines and converts the antialiased coverage to each TIM's existing native colours. Numerals stay within their 12-pixel sprite samples; the STAGE prefix fits its existing 52-pixel sample. Source images, prompts and layout audits live in `work/ui/intertitles/`. No scripts or stage-number behavior change.

v0.9.6 appearance update: the copyright notice now uses plain Arial Regular with antialiased edges quantized to the original 16 grey levels. Six 18-pixel rows share the same baseline offset. `tools/copyright_notice.py` consumes the rasterized line masks in `work/ui/copyright/lettering.en.json`; the build does not need an installed system font. Only spacing around the unchanged copyright dates was adjusted.

Both character cards now use image-generated, transparent title wordmarks instead of the previous gameplay-font lettering. The white italic wordmarks have smaller supporting titles and dark outlines/shadows; their originals and prompts are in `work/ui/title_cards/`. At insertion, trim barely visible alpha specks, fit the title into its measured central band, alpha composite and quantize to the unchanged native palette. The background illustration and all pixels outside the band remain unchanged. The new design supersedes the v0.9.5 type treatment described below.

The copyright notice is MAPMAIN entry 20 (256×240), separate from the main logo at entry 19 and its compressed copy in entry 23. Translate all six owner lines and retain their original years. The notice retains Ishimori Pro./Toei, Senkosha/NTV, Tsuburaya Pro., Toei, Hikari Pro./Toei, and Banpresto.

EVENT 230 and 231 are character introduction cards, not the main game title screen. The first reads **Fusion Steel Luciferd**. Its previous English bitmap split the name and subtitle awkwardly and used an older font. Render it as one coherent title using the aligned Latin source used by the game. The second reads **EATER — Test Subject 003**; its Japanese lettering was baked into the illustration and had been missed by text insertion. Restore only the central lettering band, then render the English title there. Use flat white lettering, a black outline and a small shadow. Preserve native resolution, palettes, TIM metadata and every source pixel outside the specified band.

Inventory: 90 episode cards, two character cards, and 50 unused EVENT 242–291 placeholder cards. The latter now read Dummy 151–200 without altering their numbers. The original Japanese main game brand logo remains intentional. Inventories and source contact sheets are under `work/ui/graphics/audit-v0.9.5/`. All 153 graphics targets pass their individual size, palette, region and sprite checks.

The EATER clean background was produced with an image edit, reduced to 320×240 and used only within the original text region. The full-resolution intermediate is local under `work/source/graphics/`; the build input is `work/translation/en/graphics/EVENT_0231_background_v0.9.5.png`. The surrounding source illustration is not replaced. Prompt/provenance is recorded with the audit artifacts.

There are two ending-credit STR movies: 71 (Metal) and 72 (Bio), each 1,266 frames at 12 fps (105.5 seconds). Both use the same 22 credit pages. Roles and company names already had English translations; v0.9.5 adds 15 verified personal-name readings. Fourteen personal names remain in their original Japanese spelling until their readings can be verified. Sources and the remaining queue are in `work/translation/en/credits_readings.en.json`; do not infer a person's reading from the most common pronunciation of their characters.

English review MP4s are `work/output/movies_v0.3.4_preview/english/movie_071_en.mp4` and `movie_072_en.mp4`. Only frames 60–1116 of each original STR are re-encoded, retaining frame slots, duration and original XA audio. Review all 22 pages, then verify the final inserted streams and complete disc with `tools/check_movie_build.py`.

Build: `C:/Python/python.exe tools/build.py 0.9.5 --keep-font --movies --no-texpack`.

Verify native art with `tools/check_title_artwork.py`; verify inserted movies against v0.9.4 with changed IDs 71,72 and changed files MAPMAIN.DAT,EVENT.DAT. Also run the English-only public source rebuild. These checks do not replace emulator or hardware playtesting. No GitHub release is authorized for this revision.
