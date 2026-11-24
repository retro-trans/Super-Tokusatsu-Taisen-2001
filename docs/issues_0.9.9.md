# Issue #6: Father objective text clipping

Report: https://github.com/retro-trans/Super-Tokusatsu-Taisen-2001/issues/6.
The Chapter 14, Father, Victory panel cuts off the warning at “Machiko”.

The text is U02575, at original offset 25754 in STAGE0117. It has one frozen
occurrence. Its original English wraps into two pages at the current
220-pixel/three-line limit. The screenshot exactly matches the first page;
the continuation says “Shirakawa will die!”. The native low-level objective
drawer does not advance this dialogue page marker: the reconstructed third
row retains the continuation beyond the text area's right edge. This static
panel cannot show a paginated dialogue continuation in the reported flow.

Use one concise English override, preserving all conditions and the full name:

> Defeat all Makuu and Shocker forces! Machiko Shirakawa dies if an Executive
> Monster beats Gavan to the Makuu base.

The objective remains defeating every Makuu/Shocker enemy. The base race is
a warning about Machiko's fate; do not turn it into an additional win/loss
condition. Retain Gavan, the Makuu base, Executive Monster and Machiko
Shirakawa. The defeat conditions and every scene command remain unchanged.

This is the next local v0.9.9 build and includes the unreleased v0.9.8 issue
#5 fix. Check the compiled objective has one page, at most three body lines
and no more than 220 pixels per line; verify all unrelated strings, pointer
order, terminators, compressed blocks, native assets and raw movie/audio
data against v0.9.8. The published release remains v0.9.7 until explicitly
requested. No GitHub comment or issue closure is authorized by this work.

Local v0.9.9 is built and verified. Execute `tools/check_issue6.py` against
the completed image to reproduce the old overflow and inspect the actual
native retained text positions. The old row extends to x=328; the repaired
rows end at x=203, 205 and 218. No page marker remains in the objective, and
Machiko's full name and death warning are retained. The reconstruction at
`work/ui/issues/issue6-native-v0.9.9.png` shows the repaired text in the native
font; it is not an emulator screenshot.

Exactly one string changes in STAGE0117, plus its compressed copy at entry
646. All other 322 strings in that overlay remain byte-identical. Every
other stage entry, compressed block, scene command, pointer order and
terminator is preserved. All raw disc bytes outside STAGE/MAPMAIN match
v0.9.8; MAPMAIN differs only in the exact automatic v0.9.9 title stamp.
Movies, audio, font, executable and the prior issue #5 repair are unchanged.
The English-only rebuild and both title copies verify, and 20,133 native
archive sectors pass EDC/ECC.

The local upgrades from public v0.9.7 (14,677 bytes) and local v0.9.8 (8,318
bytes) each decode to the same 725,316,816-byte image, SHA-256
`894c64cc62527e7c8362cd1db276e3521c21d235046257deb4fc7b548b7881aa`.
The optional v0.9.7 texture package still matches; no new pack is necessary.
Emulator playtesting remains pending. No GitHub release, comment or closure
was made.
