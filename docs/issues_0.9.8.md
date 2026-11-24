# Issue #5: Chapter 8B Battle Princess pronouns

Report: https://github.com/retro-trans/Super-Tokusatsu-Taisen-2001/issues/5.
Screenshots show Luciferd saying “He got away” and then “he was kind enough
to leave” after Atefarina retreats. The glossary already identifies
Atefarina the Battle Princess as female.

The source dump deduplicates identical speaker/body text. U01396 and U01397
occur in both STAGE0061 (the Apfaron branch) and STAGE0068 (the Atefarina
branch). The Japanese retreat line does not specify a gender; its shared
English translation assumed the male Apfaron referent. Replacing those UIDs
globally with she would introduce the opposite error in the Apfaron branch.

Use the inserter's existing per-occurrence override mechanism:

| Scene | UID | Original string offset | English pronouns |
|---|---|---:|---|
| STAGE0061, Apfaron | U01396 | 14352 | He / he, unchanged |
| STAGE0061, Apfaron | U01397 | 14420 | He / he, unchanged |
| STAGE0068, Atefarina | U01396 | 13758 | She / she |
| STAGE0068, Atefarina | U01397 | 13826 | She / she |

The two Atefarina rows represent the saved Metal hero name and the explicit
Luciferd speaker variants. Both must be corrected. Leave the shared batch
translation unchanged so other occurrences retain their original meaning.

All other he/him/his/man references in the reported chapter were inspected:
they refer to Gavan or Luciferd. Mentions of Atefarina alongside a male
pronoun elsewhere explicitly concern Satoru, the Metal hero, or Zephas's son;
they do not justify a global pronoun substitution.

The fix belongs in the next local v0.9.8 build. Verify the two compiled
female rows, the two untouched male rows, every other stage entry and the
compressed scene copy. Preserve pointer order, terminators and three-line
body limits, and confirm only the dialogue archive and exact automatic title
stamp change in the completed disc. No issue comment, closure or GitHub
release is authorized by this investigation alone.

Local v0.9.8 is built and checked. Both female variants use She/she; both
male variants remain byte-identical to v0.9.7. Only stage entries 68 and 639
change (overlay and its compressed container); all other compressed blocks,
dialogue words, pointer order, terminators and scene commands are preserved.
All 188 strings in the affected overlay pass the existing width/three-line
checks. The repaired box uses one body line on its first page and two on its
second page. The native text-packet reconstruction is saved as
`work/ui/issues/issue5-native-v0.9.8.png`; this is not an emulator screenshot.

The complete English-only rebuild matches the finished image. Both title
copies verify v0.9.8 and github.com/retro-trans. Every raw disc byte outside
the two audited archives is unchanged from v0.9.7; font, executable, movies
and audio remain identical. All 20,133 audited archive sectors pass EDC/ECC.
The 10,106-byte bare local upgrade patch passes a full decode/size/hash round
trip to `c2fb2d0aaf23a6b24c115aaa3e34ba81a2540996e50e3dcf07d36bbe4ac9df53`.
No new texture package is needed: the optional v0.9.7 package still matches.
Emulator playtesting is pending; no GitHub release or issue comment was made.
