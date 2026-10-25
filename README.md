# Super Tokusatsu Taisen 2001 — translation project

An open toolchain for translating **Super Tokusatsu Taisen 2001**
(スーパー特撮大戦2001, PlayStation, **SLPS-02863**), plus the English
translation built with it.

## Contribute

The text is translated end to end. Playtesting is in progress; a full playthrough remains unverified.
Bug reports (with a screenshot, if you can), proofreading and playtesting are
all welcome. Please open an issue on this repository.

## Play it

The latest release is **[v0.9.0](https://github.com/retro-trans/Super-Tokusatsu-Taisen-2001/releases/tag/v0.9.0)**
for the Japanese PlayStation disc (**SLPS-02863**). It includes the latest
font and saved-name repairs, fixed dialogue clearing, correct HP/EN digits,
readable weapon badges, and the revised opening with English/romaji captions.
Both caption rows sit farther inside the picture for gameplay visibility.
Original audio is preserved. See [song audit](docs/opening_song.md) and
[font implementation](docs/rayblade_font.md).

The native Skies of Arcadia font follows the Rayblade/Riot Stars approach:
retain a 2x atlas and draw at half size. Use 2x/4x internal resolution in
DuckStation for extra detail. Install the included optional v0.9.0 texture
pack when using replacements; public v0.3.29 and older packs alone do not
match this font. Local v0.3.35-v0.3.38 packs share the current payload.

**Intermission > Difficulty** offers **Default / Gentle / Story**. Use Up/Down to
choose, Circle to apply, or Cross to cancel. The panel shows the saved mode.
Default uses the original rules and is initially selected. Gentle gives 1.5x battle XP/rewards and chapter rewards,
25% cheaper S-unit / 50% cheaper L-unit upgrades, +10% ally / -10% enemy attack
and armor, and fresh-stage ammo refill. HP/EN, movement and hit rates are
unchanged. Story gives 3x XP, 2x battle/chapter funds/materials, +25% ally /
-25% enemy attack and armor, and Gentle's discounts and ammo refill.
Switching back keeps earned progress. See [implementation and testing](docs/runtime_balance.md).

Use [Retro Trans Tools](https://github.com/retro-trans/retro-trans-tools/releases/latest)
with this release's `BUILD-MANIFEST.json`, checksums and validation report.
Refresh the catalog, or open the release URL directly. You need your own
game image; a full disc is not distributed.

| Your source image | Patch |
|---|---|
| Original Japanese SLPS-02863 single BIN (MODE2/2352) | `STT2001-English-v0.9.0.xdelta` |
| Published English v0.3.29 BIN | `STT2001-English-v0.3.29-to-v0.9.0.xdelta` |

Each release includes only the original-disc patch and the previous-public-version
upgrade. Older English builds can follow intermediate releases through Retro Trans
Tools after refreshing its catalog, or start from the original Japanese disc.
If applying a patch manually, name the output `STT2001_EN_v0.9.0.bin`.
Download `STT2001_EN_v0.9.0.cue.txt` from the release, remove the final
`.txt`, and place the resulting CUE beside the BIN.
Cold boot the new disc and load an ordinary in-game save; old emulator save
states keep the previous executable in RAM. The v0.3.26 missing-label/erased
footer defect is fixed in v0.3.27.

The patch checks its source. The original `.bin` is 725,316,816 bytes, with
SHA-256 `219d9c4f64caf670b5e400612fa19677ed9a3f59a7ebdb72c12c425412795465`.

### Apply

**The easiest way:** [Retro Trans](https://github.com/retro-trans/retro-trans-tools)
is a desktop app for applying translation patches. Download it from its
Releases page, open the **Automatic** tab and select your game image (.bin,
.cue or .chd). Wait for it to analyse the image, then click Patch.

**Other ways:** [DeltaPatcher](https://github.com/marco-calautti/DeltaPatcher)
accepts the same `.xdelta` file. Select the unpacked `.bin` as the original file.

**Command line:** get [xdelta3](https://github.com/jmacd/xdelta).

```
xdelta3 -d -s "Super Tokusatsu Taisen 2001 (Japan).bin" STT2001-English-v0.9.0.xdelta "STT2001_EN_v0.9.0.bin"
```

Keep the `.cue` next to the patched `.bin` and point its `FILE` line at the
new name. The disc is a single MODE2/2352 track.

**If you have a `.chd`**, unpack it first (`chdman.exe` comes with
[MAME](https://www.mamedev.org/release.html); you don't need to install or run
MAME):

```
chdman extractcd -i "your-game.chd" -o game.cue -ob game.bin
```

### Sharper font (optional, DuckStation)

Download **STT2001-4x-font-pack-v0.9.0.zip** from the release. It
provides the matching English font at 4x in every text colour.
Extract its `textures/SLPS-02863` folder into DuckStation's data folder (Tools → Open Data Directory), merging it with existing files. Then enable
**Settings → Graphics → Texture Replacement → Enable Texture Cache** and
**Enable Texture Replacements**, and use 4x internal resolution.

The pack's `config.yaml` sets `MaxVRAMWriteSplits: true`. Without it the font
isn't replaced in story scenes, because the game overwrites half of its font
sheet there. Restart DuckStation or reload replacements after installing.
Public v0.3.29 and older packs alone do not match the new font. Packs are
matched by texture contents: text-only builds can share a pack, while font
changes require new IDs. Local v0.3.35-v0.3.38 packs already match v0.9.0.

Weapon markers use **D** for Direct and **I** for Indirect; these are attack categories, while Rng shows the range. Attribute badges read BLT (Bullet), ELC (Electric), BEM (Beam), WTR (Water), FIR (Fire), and SPL (Special). P and MAP retain their existing functions.

## What is translated

The native Default/Gentle/Story setting supersedes the separate v0.3.22 economy
prototype. Native sprite/menu, save, gameplay and patch round-trip checks
pass; complete emulator/PSP campaign and visual testing remain pending.
Some encyclopedia descriptions still clip, and the reported Kaimen Green
text corruption remains unreproduced. See [the report](docs/encyclopedia_report.md).

| Part | Status |
|---|---|
| Story dialogue (stage scripts) | 26,261 strings (16,179 unique), 100% |
| Battle quotes | 12,617 strings (3,102 unique), 100% |
| Character Encyclopedia (キャラクター辞典) | 914 strings, 100% |
| Units, weapons, abilities, menus, episode titles (database) | 2,914 strings |
| Music titles, executable menus, memory-card save title | done |
| Graphics: 90 stage title cards, disclaimer, narration card, title-menu and option labels, encyclopedia frames/tabs, Fusion Steel card and Critical callouts | 101 images |
| Movies: 26 captioned clips and both credit rolls | English subtitles over the Japanese audio |

Still in Japanese: some battle labels (Shield, Parry, Afterimage…), remaining
name logos, the copyright screen, and the title logo (kept on purpose). A
few unclear shouts in the movies are left unsubtitled. See
[docs/handoff_graphics.md](docs/handoff_graphics.md) and
[docs/handoff_movies.md](docs/handoff_movies.md).

## How it was translated

This is a **machine translation**, produced with large language models and
then checked by scripts, not a hand translation by a fluent translator. No
human proofreading has been done yet.

The Japanese was decoded from the game's own font images. A few kanji were
misread there; translators fixed them from context and listed them in their
batch reports. Names and terms follow [docs/glossary_decisions.md](docs/glossary_decisions.md)
and `work/glossary/names.json`.

## Build it

Each new build automatically stamps its version and `github.com/retro-trans` on
the native title screen and verifies both artwork copies in the completed disc.
From v0.3.20, crisp bitmap lettering on dark backing improves readability.
See [title-screen footer](docs/title_footer.md) for placement and verification.

You need your own disc image, `Super Tokusatsu Taisen 2001 (Japan).bin/.cue`,
in the project root, plus Python 3 with `numpy`, `pillow`, `capstone`,
`keystone-engine` and `xxhash`.

```sh
python tools/extract_iso.py                                  # disc files -> work/source/disc/
for f in work/source/disc/*.DAT; do python tools/dat_archive.py "$f"; done   # -> work/source/unpacked/
python tools/build.py 0.x.y --keep-font     # build work/output/STT2001_EN_v0.x.y.bin/.cue (+ 4x font pack)
```

`--movies` also inserts the subtitled movies. It needs the movie pipeline
(jPSXdec and the exported streams); see [docs/handoff_movies.md](docs/handoff_movies.md).

The build writes a report with any problems: text that doesn't fit, RAM
limits, name buffers, and so on. A release is only made from a build that
reports none.

The working translation files contain Japanese and are not in git. This
repository holds only the stripped `*.en.json` copies, made by
`python tools/strip_jp.py`, and no game data or dump of the Japanese script.
Instead, `work/script/occurrences.json` records where each translated string
sits on the disc (file, offset, font and ID, with no text). In a checkout
without the Japanese files, the inserter decodes those strings from your own
disc. A build from this repository is byte-identical to the project's own
builds outside the movie data; this is checked by `tools/check_public_build.py`. Release patches are separately round-tripped against the complete disc, including the approved movies.

## What is here

| Path | Contents |
|---|---|
| `tools/` | extractor, archive and CM (LZSS) codecs, font OCR, script dumper, inserter, VWF patch, disc re-layout with EDC/ECC, graphics and movie pipelines, 4x texture-pack generator |
| `work/translation/en/**/*.en.json` | the English translation (batches, translator outputs, overrides, menu and graphics text) |
| `work/translation/en/movies/` | English movie subtitles (.ass/.srt) |
| `work/glossary/` | names and terms; the encyclopedia library glossary |
| `work/font/` | English font metrics and glyph cells (Gen'ei LateGo P), font decoding maps |
| `docs/text_format.md` | disc layout, text encoding, font lookup, containers |
| `docs/translator_brief.md` | rules the translators followed |
| `docs/glossary_decisions.md`, `docs/library_glossary.md` | terminology decisions |
| `docs/handoff_graphics.md`, `docs/handoff_movies.md` | image and movie work, and what remains |
| `CHANGELOG.md` | every build: what changed and what broke |

## Do not sell this

This patch is free. Do not sell it, and do not sell anything made with it:
no pre-patched discs or images, no loaded memory cards or consoles, no
paywalled or ad-gated downloads.

It is an unofficial fan translation. Super Tokusatsu Taisen 2001 is © BANPRESTO
2001, and its characters belong to their rights holders (Ishimori Pro, Toei,
Tsuburaya Pro, Senkosha, Hikari Pro and others).

## Credits

- **pow** — Project lead
- **Karnik** — Playtester

Native font: **Skies of Arcadia** by SEGA/Overworks, following the Seireiki
Rayblade / Riot Stars implementation. Latin fallback: **Gen'ei LateGo P** by [okoneya](https://okoneya.jp/font/genei-latin.html)
(SIL Open Font License 1.1, Latin glyphs from Linux Biolinum).

Translation passes, tooling and reverse engineering were done with Claude
(Anthropic), directed by binhlt0402. The README and release layout follow
[retro-trans/SRW-Z](https://github.com/retro-trans/SRW-Z).
