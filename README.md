# Super Tokusatsu Taisen 2001 — translation project

An open toolchain for translating **Super Tokusatsu Taisen 2001**
(PlayStation, **SLPS-02863**), plus the English translation built with it.

## Contribute

The text is translated end to end, but a complete campaign and every route
have not been tested. Fluent proofreading, bug reports and playtesting are
welcome. Join the Retro Trans Discord:

**[discord.gg/MssepShjmB](https://discord.gg/MssepShjmB)**

You can also [open an issue](https://github.com/retro-trans/Super-Tokusatsu-Taisen-2001/issues).
For bugs, include the title-screen version, platform/emulator, a screenshot
and an ordinary in-game save if available.

## Play it

The latest release is **[v0.9.0](https://github.com/retro-trans/Super-Tokusatsu-Taisen-2001/releases/tag/v0.9.0)**,
with a full patch for the original Japanese disc and an upgrade from public
English **v0.3.29**. It includes the new Skies of Arcadia font, saved-name
repairs, fixed dialogue clearing, correct HP/EN digits, readable weapon
badges and revised English/romaji opening subtitles. Original audio is
preserved. See the release notes for verification and remaining issues.

### Apply

**The easiest way:** Download [Retro Trans Tools](https://github.com/retro-trans/retro-trans-tools/releases/latest),
open **Automatic**, select your source BIN/CUE or supported CHD, and let the
app identify it before clicking **Patch**. Refresh the catalog to see the
latest release; you can also open the release URL in the app.

**Other ways:** [DeltaPatcher](https://github.com/marco-calautti/DeltaPatcher)
accepts the same bare `.xdelta` files. Select the unpacked BIN as the source
and choose the patch matching its version.

**Command line:** Get [xdelta3](https://github.com/jmacd/xdelta).
For CHD extraction, `chdman` comes with [MAME](https://www.mamedev.org/release.html);
you do not need to install or run MAME.

You need your own Japanese disc image or the exact published English
v0.3.29 output. Each release includes only the original-to-current and
previous-public-to-current patches.

| Your source image | Patch |
|---|---|
| Original Japanese SLPS-02863, single MODE2/2352 BIN | `STT2001-English-v0.9.0.xdelta` |
| Published English v0.3.29 BIN | `STT2001-English-v0.3.29-to-v0.9.0.xdelta` |

**Original Japanese disc:**

```sh
xdelta3 -d -s "Super Tokusatsu Taisen 2001 (Japan).bin" STT2001-English-v0.9.0.xdelta "STT2001_EN_v0.9.0.bin"
```

**Already on public v0.3.29?** Use the smaller upgrade patch:

```sh
xdelta3 -d -s "STT2001_EN_v0.3.29.bin" STT2001-English-v0.3.29-to-v0.9.0.xdelta "STT2001_EN_v0.9.0.bin"
```

Older English versions can follow intermediate public upgrades through
Retro Trans Tools after refreshing its catalog, or start from the original
Japanese disc. Local test builds may differ from published builds bearing
the same label. If source verification fails, check the version and hashes
in `BUILD-MANIFEST.json`; keep verification enabled.

Both patches produce the same 725,316,816-byte image:

| Image | SHA-256 |
|---|---|
| Original Japanese BIN | `219d9c4f64caf670b5e400612fa19677ed9a3f59a7ebdb72c12c425412795465` |
| English v0.9.0 BIN | `000762aaaa9b16416546e4c11e97177175bd4a5be95155b2ab262c7243d82c8a` |

For manual patching, download `STT2001_EN_v0.9.0.cue.txt` from the release,
remove the final `.txt`, and place the resulting CUE beside
`STT2001_EN_v0.9.0.bin`. Cold boot the CUE, then load an ordinary in-game
save. Old emulator save states retain the previous executable and text in
RAM. PSP users can convert the patched BIN/CUE with their usual PS1 EBOOT
workflow.

**If you have a CHD**, extract it before applying a patch manually:

```sh
chdman extractcd -i "your-game.chd" -o game.cue -ob game.bin
```

### Sharper font (optional, DuckStation)

The native font is included in the patches. The optional
**STT2001-4x-font-pack-v0.9.0.zip** provides matching 4x replacements in
every text colour.

1. In DuckStation, open **Tools > Open Data Directory**.
2. Extract the ZIP there, merging `textures/SLPS-02863/`. Keep `config.yaml`
   beside the `replacements/` directory containing all 756 PNGs.
3. Enable **Texture Cache** and **Texture Replacements** in the graphics
   settings, and use 2x/4x internal resolution.
4. Reload replacements or restart DuckStation.

The configuration includes `MaxVRAMWriteSplits: true`, which is needed when
story scenes overwrite part of the font sheet. Public v0.3.29 and older
packs alone do not match this font. Local v0.3.35–v0.3.38 packs contain the
same texture payload as v0.9.0. Text-only builds can share a pack; changes
to font textures can require new replacement IDs. See
[font implementation](docs/rayblade_font.md).

### Difficulty and weapon markers

**Intermission > Difficulty** offers **Default / Gentle / Story**. Use
Up/Down to choose, Circle to apply, or Cross to cancel. The panel displays
the saved mode, and Default is initially selected.

| Setting | Default | Gentle | Story |
|---|---|---|---|
| XP | Original | 1.5× | 3× |
| Battle/chapter funds and materials | Original | 1.5× | 2× |
| Ally attack and armor | Original | +10% | +25% |
| Enemy attack and armor | Original | −10% | −25% |
| S-unit / L-unit upgrade costs | Original | 25% / 50% cheaper | 25% / 50% cheaper |
| Ammo at a fresh stage | Original | Refilled | Refilled |

HP/EN, movement, hit rates and saved base stats are unchanged. Ammo is not
refilled when resuming a stage. Switching back keeps earned progress.
See [difficulty implementation and testing](docs/runtime_balance.md).

Weapon prefixes **D** (Direct) and **I** (Indirect) identify attack categories;
**Rng** shows range. Attribute badges are **BLT** (Bullet), **ELC** (Electric),
**BEM** (Beam), **WTR** (Water), **FIR** (Fire) and **SPL** (Special).
P and MAP retain their existing functions.

## Check the translation

Read the English in `work/translation/en/**/*.en.json`. When suggesting a
correction, include the line ID and surrounding scene. Names and terminology
are documented in [glossary decisions](docs/glossary_decisions.md) and
[the library glossary](docs/library_glossary.md).

Japanese script text is decoded from your own disc during extraction and
building. The repository stores English translations and source offsets.
Layout, pointer and byte checks support review; fluent readers are needed
to judge the wording and meaning.

After preparing the extracted files and a completed local image, compare
an English-only source rebuild against that image with:

```sh
python tools/check_public_build.py 0.9.0 --verify
```

This checks rebuilt archives and executable data. Movie verification is
separate; release patches are round-tripped against the complete disc.

## Translate it

Fork the project to improve the English or start another language. Begin
with the [translator brief](docs/translator_brief.md),
[text format](docs/text_format.md) and existing English batches.
Preserve name placeholders, control tags and weapon icons.

In a public checkout, edit the `*.en.json` translation files. Maintainers
with local Japanese-source working files regenerate their English-only
copies with `python tools/strip_jp.py` before committing. Keep Japanese
script dumps and game data out of git.

Spoken dialogue must fit its frame with no more than three body lines per
box. Continue longer dialogue in another box or shorten it without losing
meaning. Resolve the build's layout and memory errors before release.

## What is here

| Path | Contents |
|---|---|
| `tools/` | Disc/archive codecs, font and text tools, inserter, renderer patches, graphics/movie pipelines and verifiers |
| `work/translation/en/**/*.en.json` | English batches, corrections, menus, graphics and subtitle records |
| `work/translation/en/movies/` | English movie subtitle files |
| `work/script/occurrences.json` | Source locations and IDs without Japanese text |
| `work/glossary/` | Names, terminology and library references |
| `work/font/` | Font metrics, glyph cells and decoding maps |
| `work/ui/` | In-game screenshots, layout descriptions and verification views |
| `work/output/` | Local test images, texture packages and verification reports; not distributed in git |
| `docs/translator_brief.md`, `docs/text_format.md` | Translation rules, disc layout, encoding and containers |
| `docs/rayblade_font.md`, `docs/title_footer.md` | Font rendering and automatic title credits/version |
| `docs/handoff_graphics.md`, `docs/handoff_movies.md` | Graphics/movie work and remaining tasks |
| `docs/runtime_balance.md`, `docs/opening_song.md` | Difficulty modes and song-subtitle audit |
| `CHANGELOG.md` | Build history, repairs and validation limits |

## Using these tools

You need your own `Super Tokusatsu Taisen 2001 (Japan).bin/.cue` in the
project root, plus Python 3 with `numpy`, `pillow`, `capstone`,
`keystone-engine` and `xxhash`. The movie pipeline also needs jPSXdec and
prepared streams; see [movie instructions](docs/handoff_movies.md).

For example, in PowerShell, extract the disc and unpack its DAT archives:

```powershell
python tools/extract_iso.py
Get-ChildItem work/source/disc/*.DAT | ForEach-Object { python tools/dat_archive.py $_.FullName }
```

Build with a version such as `0.x.y`, replacing it with the actual build
number. `--keep-font` reuses prepared font assets; `--movies` includes the
prepared subtitled movies:

```sh
python tools/build.py 0.x.y --keep-font --movies
```

Output goes to `work/output/STT2001_EN_v0.x.y.bin/.cue`, with reports and a
matching texture package. Every build automatically stamps its exact
version and `github.com/retro-trans` credit on the native title screen and
verifies both copies in the completed image. Preparing or testing a local
build does not publish a release.

## Do not sell this

This patch is free. Do not sell it or anything made with it: pre-patched
discs/images, loaded memory cards or consoles, or paywalled/ad-gated downloads.

This is an unofficial fan translation. Super Tokusatsu Taisen 2001 is
© BANPRESTO 2001; its characters belong to their rights holders, including
Ishimori Pro, Toei, Tsuburaya Pro, Senkosha and Hikari Pro.

## Credits

| Role | Contributor |
|---|---|
| Project lead | **pow** |
| Playtesting | **Karnik** |

The native **Skies of Arcadia** font artwork is by **SEGA / Overworks**,
integrated through the Seireiki Rayblade / Riot Stars font work. The Latin
fallback is **Gen'ei LateGo P** by [okoneya](https://okoneya.jp/font/genei-latin.html),
under SIL Open Font License 1.1, with Latin glyphs from Linux Biolinum.
No new license for the Skies of Arcadia artwork is granted.

Translation passes, tooling and reverse engineering began with Claude
(Anthropic), directed by pow. The text is machine-translated and then
edited; it still needs fluent human review. Names and terminology follow
the project's glossary decisions.

The README and release-note layout follow
[retro-trans/SRW-Z](https://github.com/retro-trans/SRW-Z).

## Status

The text is translated end to end. Coverage counts below describe inserted
English, not completed human proofreading or campaign testing.

| Part | Coverage |
|---|---|
| Story dialogue | 26,261 strings (16,179 unique) |
| Battle quotes | 12,617 strings (3,102 unique) |
| Character encyclopedia | 914 strings |
| Units, weapons, abilities, menus and episode titles | 2,914 database strings |
| Music titles, executable menus and memory-card save title | Translated |
| Stage cards, interface labels and other graphics | 101 images, including 90 stage title cards |
| Movies | 26 captioned clips and both credit rolls, over original Japanese audio |

### Testing and remaining work

Native font/menu rendering, saved names, dialogue clearing, number/badge
rendering, difficulty/rewards/purchases, save round trips and complete-disc
patch verification pass. Movie decoding and simulated opening-subtitle
cropping also pass. A full campaign, every route and emulator/PSP visual
confirmation remain pending.

Some encyclopedia descriptions still clip; the reported Kaimen Green text
corruption remains unreproduced. See [the encyclopedia report](docs/encyclopedia_report.md).
Some battle callouts and name logos remain Japanese. The copyright screen
and title logo remain Japanese, and a few unclear movie shouts are
unsubtitled. The opening has English and romaji; see
[the song audit](docs/opening_song.md) for its scope.

### Human proofreading

The translation was produced with large language models and edited with
automated checks and reported corrections. A counted, comprehensive human
proofreading audit is not available. Contributions from fluent readers
are welcome; technical verification does not establish translation accuracy.

[CHANGELOG.md](CHANGELOG.md) records shipped builds, reported defects,
repairs and the limits of each verification.
