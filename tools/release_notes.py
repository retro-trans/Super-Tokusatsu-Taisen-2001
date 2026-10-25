"""Public release notes following the SRW-Z release layout."""


def render_release_notes(version, previous_version, target_sha256, texture_count):
    return '''English translation of **Super Tokusatsu Taisen 2001** for PlayStation, Japanese release **SLPS-02863**.

Version v{v} includes the new font, saved-name and dialogue repairs, and revised opening subtitles. Translation covers the game end to end; campaign playtesting and fluent review remain in progress.

### Apply

**Recommended:** Download [Retro Trans Tools](https://github.com/retro-trans/retro-trans-tools/releases/latest). In **Automatic**, select your BIN/CUE or supported CHD, refresh the catalog, and apply the suggested patch route. You can also open this release URL in the app.

**Other options:** [DeltaPatcher](https://github.com/marco-calautti/DeltaPatcher) and [xdelta3](https://github.com/jmacd/xdelta) accept the bare `.xdelta` files below. Apply one patch to the exact source BIN it requires.

| Your source image | Patch |
|---|---|
| Original Japanese SLPS-02863, single MODE2/2352 BIN | `STT2001-English-v{v}.xdelta` |
| Published English v{previous} BIN | `STT2001-English-v{previous}-to-v{v}.xdelta` |

**Original Japanese disc:**

```
xdelta3 -d -s "Super Tokusatsu Taisen 2001 (Japan).bin" STT2001-English-v{v}.xdelta "STT2001_EN_v{v}.bin"
```

**Upgrade from public v{previous}:**

```
xdelta3 -d -s "STT2001_EN_v{previous}.bin" STT2001-English-v{previous}-to-v{v}.xdelta "STT2001_EN_v{v}.bin"
```

For older English versions, refresh Retro Trans Tools' catalog so it can select intermediate public upgrades, or patch your original Japanese disc. Local test builds may differ from public builds bearing the same label. Keep source verification enabled; source hashes are listed in `BUILD-MANIFEST.json`.

If applying manually, download `STT2001_EN_v{v}.cue.txt`, remove the final `.txt`, and place the resulting CUE beside `STT2001_EN_v{v}.bin`. Cold boot the CUE and load an ordinary in-game save. Old emulator save states retain previous code and text in RAM. PSP users can convert the patched BIN/CUE with their usual PS1 EBOOT workflow.

For manual CHD extraction, use `chdman` from [MAME](https://www.mamedev.org/release.html):

```
chdman extractcd -i "your-game.chd" -o game.cue -ob game.bin
```

Both patches produce the same 725,316,816-byte image. Output SHA-256: `{sha}`.

### What changed since v{previous}

- **New native font:** Skies of Arcadia bitmap font using the Rayblade/Riot Stars approach, with a matching optional texture pack.
- **Existing save names repaired:** Campaigns started before the font change retain their character names.
- **Text rendering repaired:** Fixed flashing when dialogue clears, corrupt HP/EN digits from reused text slots, and weapon badges appearing as white blocks.
- **Opening lyrics restored:** Added missing lines, romaji and the approved "We get rainbow!" refrain. English and romaji sit farther inside the picture to reduce edge clipping. Original audio is preserved.
- Includes earlier translation/UI fixes and **Intermission > Difficulty: Default / Gentle / Story**. The title displays **v{v}** and **github.com/retro-trans**.

### Testing and known issues

Both retained patches were applied and checked against the exact target image through Retro Trans Tools. Checks also cover native font copies, saved names, number rendering, dialogue clearing, difficulty modes, purchases/rewards, save checksums/load, the English-only source rebuild and movie decoding. Opening captions pass simulated top/bottom cropping.

A full campaign and emulator/PSP playback remain unverified. Some encyclopedia descriptions clip, the reported Kaimen Green corruption remains unreproduced, and some battle callouts/logos remain Japanese. Translation and song transcription still need fluent human review. Reports should include the title-screen version, platform and a screenshot or ordinary save where possible.

### What's included

- One patch for the original Japanese disc and one upgrade from the previous public release, v{previous}.
- Matching **STT2001-4x-font-pack-v{v}.zip**, containing {count} replacement PNGs and configuration.
- CUE text template, installation instructions, changelog, source/build verification, manifest, checksums and patch validation.

**Optional sharper font in DuckStation:**

1. Open **Tools > Open Data Directory**.
2. Extract the font ZIP there, merging `textures/SLPS-02863/`. Keep `config.yaml` and the `replacements/` directory together.
3. Enable **Texture Cache** and **Texture Replacements**, then use 2x/4x internal resolution.
4. Reload replacements or restart DuckStation.

Public v0.3.29 and older packs alone do not match this font. Local v0.3.35-v0.3.38 packs contain the same texture payload. Native text also works without replacements.

**Difficulty:** Default uses the original rules. Gentle gives 1.5x XP/rewards and +10% ally / -10% enemy attack and armor. Story gives 3x XP, 2x rewards and +25% ally / -25% enemy attack and armor. Both assistance modes give 25% cheaper S-unit / 50% cheaper L-unit upgrades and refill ammo at a fresh stage. HP/EN, movement, hit rates and saved base stats are unchanged. Circle applies, Cross cancels; the mode is saved. Switching back retains earned progress.

### How it was translated

The English text was produced with large language models and then edited. It still needs proofreading by fluent readers and playtesting across the campaign. Translation sources and build tools are available in the repository.

### Credits and acknowledgements

- **pow** — Project lead
- **Karnik** — Playtester
- **Retro Trans** — Translation project and tools
- **SEGA / Overworks** — Skies of Arcadia font artwork, integrated through the Seireiki Rayblade / Riot Stars font work
- **okoneya** — GenEi Latin fallback font (SIL Open Font License 1.1 included)

Thank you to everyone reporting bugs and helping review the translation. No new license for the Skies of Arcadia artwork is granted.

### Source code

GitHub's **Source code (zip/tar.gz)** downloads contain the repository snapshot at the release tag. Use the `.xdelta` assets to patch the game. The manifest identifies the verified game output; later release-note and packaging updates are recorded in the [project repository](https://github.com/retro-trans/Super-Tokusatsu-Taisen-2001).

### Contribute

Bug reports, proofreading and playtesting are welcome through [GitHub issues](https://github.com/retro-trans/Super-Tokusatsu-Taisen-2001/issues).

---

No game image is included. Use your own disc image. This fan translation is free; please do not sell it.
'''.format(v=version, previous=previous_version, sha=target_sha256,
           count=texture_count)
