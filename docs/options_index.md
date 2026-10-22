# Options titles and encyclopedia index — v0.3.23

Local test build, 2026-10-20. No GitHub release created.

## Options title offsets

MAPMAIN entry 27 starts with catalog metadata, followed by a relative u16
offset table with 197 entries. Its first u32 locates that table. The former
inserter treated everything following the first u32 offset as a sequential
string stream, preserving the old offset table while the translated strings
changed length. The native resolver at `0x80040F38` therefore read from stale
positions. This explains both missing initial letters and incorrect titles
from neighboring records.

`tools/options_layout.py` rebuilds the title payload and remaps every relative
offset, including duplicates and pointers to empty terminators. Catalog
metadata, track/demo IDs, selection order and playback code are retained.

## Encyclopedia labels

The index draws two columns at x=24 and x=160, each with a 128px text allowance
and an 8px gap. Forty-four names exceeded that allowance. Their compact labels
are listed in `work/ui/encyclopedia/index_labels.en.json`; examples include
`CH-47J Heli`, `Type 75 SP How.` and abbreviated ranks. These labels also appear
in the encyclopedia detail heading because it shares the same name records.
Canonical translations, gameplay names, descriptions and glossary terms remain
unchanged. The changes are display abbreviations, not terminology corrections.

## Verification

`python tools/check_options_index.py 0.3.23 0.3.22 --verify` checks the completed
disc using its native title resolver, Options drawer, index command builder and
GUI interpreter. Graphics submission is modeled. All 197 title lookups, 134
selectable music/demo draws and 431 index labels pass. All 1,715 encyclopedia
pointer records are compared: only the intended 44 name records change. The
description records remain byte-identical.

The EXE and gameplay data are unchanged. Both title-art copies show the exact
v0.3.23 version and `github.com/retro-trans`; the completed title asset was also
visually inspected. Both raw and compressed copies contain the previously
prepared Black Cross objective clarification; scenario code is unchanged.
Unrelated files, movie sectors and all 757 font-package files match v0.3.22.
The stripped public sources rebuild all five modified files exactly. Build
reports zero problems. Actual PSP/POPS appearance has not been verified.

The earlier encyclopedia body clipping, narrow series-label layout and Kaimen
Green corruption are still open; this build does not claim to fix them.

## Local test files

The bare `work/output/STT2001-English-v0.3.18-to-v0.3.23.xdelta` upgrades the
published v0.3.18 `.bin`. Its 28,433 bytes were created and decoded using the
verified Retro Trans Tools engine; the round trip matches the completed image
SHA-256 `ff82d45d62ee7a67cd81eec90460036b3d3b33bbe78b61b3ec3a8e02cfec9c6b`.
See `work/output/STT2001_EN_v0.3.23_README.txt` for application instructions.

Load `work/output/STT2001_EN_v0.3.23.cue` with its matching `.bin` beside it.
For PSP conversion, use the new disc image. This is a standard gameplay build;
it does not enable the optional economy prototype.

DuckStation users can reuse the matching v0.3.18 through v0.3.22 font pack, or
extract `STT2001_EN_v0.3.23_4x_font.zip` into DuckStation's textures directory
so it contains `textures/SLPS-02863/replacements/`. Enable texture replacements
and restart/reload the game. The ZIP contains the same verified 756 PNGs and
configuration file; copying it cumulatively preserves older IDs. This menu
repair requires the new game image and cannot be applied through textures alone.
