# Open-issue repair audit: v0.9.1

Reviewed every open issue and comment on 2026-11-16: **#2, #3 and #4**.
Initially prepared as a local test build; now published as
[v0.9.1](https://github.com/retro-trans/Super-Tokusatsu-Taisen-2001/releases/tag/v0.9.1).
See [the publication record](releases/v0.9.1.md). No issue comments or closure
messages were posted.

| Report | Repair | Verification |
|---|---|---|
| [#2: Lucifard](https://github.com/retro-trans/Super-Tokusatsu-Taisen-2001/issues/2) | Luciferd in English text, glossary, UI, music/movie names and Fusion Steel artwork | Scan compiled dialogue, battle quotes, encyclopedia and database; compare completed artwork with the renderer |
| #2 comment: vd / rd | Full Evade / Defend response labels | Reproduce old pointers skipping the first character; execute native text allocation, lookup and finalization from the repaired pointers |
| [#3: maximum-level overlap](https://github.com/retro-trans/Super-Tokusatsu-Taisen-2001/issues/3) | Max Lv. label ends before the live numeric value | Execute original upgrade descriptors for 0, 1, 9, 10, 15 and 99; reproduce old overlap |
| #3: Eva. / Acc. overlap | Current-font punctuation spacing | Execute Stats bytecode for 25 base/bonus cases; retain all values/limits and place brackets at x=195/225 |
| #3 comment: Continued | Continue | Decode the completed database's Intermission entry |
| [#4: untranslated words](https://github.com/retro-trans/Super-Tokusatsu-Taisen-2001/issues/4) | Transform / Transform!, Pops / Mr. Tachibana | Scan compiled English for old terms; compare all story/battle content with only recorded replacements allowed; re-encode captions in clips 31/34 |

The selected-response table entries at executable file offsets `0x9AD2C`
and `0x9AD30` pointed to `0x800AA338` / `0x800AA340`, the second words of
the translated in-place strings. Complete labels now occupy reserved padding
at `0x800DD330` and `0x800DDFF0`, each guarded by a 16-byte bound and empty
padding check. The completed executable equals the v0.9.0 executable plus
only this label/pointer patch. Gameplay instructions and save layout are exact.

The previous Stats punctuation assumed wider spaces. Current space advances
are 3px; the new sequence keeps the original x=156 draw position and all
number coordinates, placing the opening bracket after the bonus's reserved
24px span and the closing bracket after the total's reserved 24px span.

`tools/check_issue_fixes.py --version 0.9.1` exercises the actual native
drawers and records an offline before/after reconstruction in
`work/ui/issues/stats-v0.9.1.png` (old above, repaired below). This is not an
emulator capture. `work/ui/issues/luciferd-v0.9.1.png` is extracted from the
completed native artwork. Issue attachments are retained locally under
ignored `incoming/github-issues-2026-11-16/`.

Completed-disc reports are under ignored `work/output/STT2001_EN_v0.9.1_*`.
They cover all 18 font copies and replacement IDs, 622 tokens, 1,192 font
packets, full-pool bounds, native numeric reuse, dialogue clearing, public
saved-name codes and save checksum/load round trips, Default/Gentle/Story,
price/reward/purchase behavior, PS1 instruction delays, and the exact public
English-only rebuild. Movie checks require only clips 31/34 to differ,
decode every inserted stream, preserve original audio/allocations and check
EDC/ECC for the movie changes and all five changed native files. All other
raw disc bytes remain identical to v0.9.0.

The optional texture payload is identical to v0.9.0: 756 PNGs plus config.
A renamed local matching package can include updated installation notes;
an already installed v0.9.0 pack remains valid. Cold boot the new CUE and
load an ordinary save; old emulator states retain previous code/text.

Full emulator/hardware confirmation and a campaign playthrough remain pending.
Previously documented encyclopedia clipping and other untranslated artwork
outside these three open issues are not claimed repaired by this build.

## Local test package

Source fixes are committed at `c4555dd`. The local package is in ignored
`work/output/test-v0.9.1/`: a bare public-v0.9.0 upgrade, matching font ZIP,
CUE text template, instructions, build manifest, validation and checksums.
The current Retro Trans Tools builder accepts this game's existing registered
package ID and round-trips the 920,441-byte patch against the complete BIN.
Target SHA-256: `363356615fcca99fd595ed5f8ab866c1786b84a0b49fa2969c71d6a9db025c6e`.
The font ZIP contains all 756 PNGs/configuration and the fallback license;
its embedded README and all asset checksums verify. This initial test package remains local; the public release includes the
original-disc patch and updated release instructions as well.
