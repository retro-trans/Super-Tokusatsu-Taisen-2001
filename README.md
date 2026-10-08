# Super Tokusatsu Taisen 2001 — translation project

An open toolchain for translating **Super Tokusatsu Taisen 2001**
(スーパー特撮大戦2001, PlayStation, **SLPS-02863**), plus the English
translation built with it.

## Contribute

The text is translated end to end, but nobody has played through it yet.
Bug reports (with a screenshot, if you can), proofreading and playtesting are
all welcome. Please open an issue on this repository.

## Play it

**There is no public release yet.** Local test builds are being checked in
DuckStation first. When a release is published, it will be a bare `.xdelta`
patch for the Japanese disc (SLPS-02863), listed in
[Retro Trans](https://github.com/retro-trans/retro-trans-tools). You need your
own copy of the game.

### Apply (once a release exists)

**The easiest way:** [Retro Trans](https://github.com/retro-trans/retro-trans-tools)
is a desktop app for applying translation patches. Download it from its
Releases page, open the **Automatic** tab and select your game image (.bin,
.cue or .chd). Wait for it to analyse the image, then click Patch.

**Other ways:** [DeltaPatcher](https://github.com/marco-calautti/DeltaPatcher)
accepts the same `.xdelta` file. Select the unpacked `.bin` as the original file.

**Command line:** get [xdelta3](https://github.com/jmacd/xdelta).

```
xdelta3 -d -s "Super Tokusatsu Taisen 2001 (Japan).bin" STT2001-English-vX.Y.Z.xdelta "STT2001 English vX.Y.Z.bin"
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

Each build also produces a **4x font texture pack** for DuckStation. It
redraws the English font at 4x, with a fine drop shadow, in every text colour.
Copy its `SLPS-02863` folder into DuckStation's `textures` folder. Then enable
**Settings → Graphics → Texture Replacement → Enable Texture Cache** and
**Enable Texture Replacements**, and use 4x internal resolution.

The pack's `config.yaml` sets `MaxVRAMWriteSplits: true`. Without it the font
isn't replaced in story scenes, because the game overwrites half of its font
sheet there. Each pack only matches the build it was made with.

## What is translated

| Part | Status |
|---|---|
| Story dialogue (stage scripts) | 26,261 strings (16,179 unique), 100% |
| Battle quotes | 12,617 strings (3,102 unique), 100% |
| Character Encyclopedia (キャラクター辞典) | 914 strings, 100% |
| Units, weapons, abilities, menus, episode titles (database) | 2,914 strings |
| Music titles, executable menus, memory-card save title | done |
| Graphics: 90 episode title cards, disclaimer, narration card, title-menu and option labels, encyclopedia frames and tabs | 98 images |
| Movies: 26 captioned clips and both credit rolls | English subtitles over the Japanese audio |

Still in Japanese: the battle labels strip (Shield, Parry, Afterimage…), the
two name logos, the copyright screen, and the title logo (kept on purpose). A
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
builds outside the movie data; this was checked for v0.3.6.

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

English font: **Gen'ei LateGo P** by [okoneya](https://okoneya.jp/font/genei-latin.html)
(SIL Open Font License 1.1, Latin glyphs from Linux Biolinum).

Translation passes, tooling and reverse engineering were done with Claude
(Anthropic), directed by binhlt0402. The README and release layout follow
[retro-trans/SRW-Z](https://github.com/retro-trans/SRW-Z).
