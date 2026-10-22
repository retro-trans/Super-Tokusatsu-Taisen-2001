# Black Cross: objective clarity and chapter numbering

Investigated 2026-10-18 after the user's Stage 38 report. English correction
prepared for the next build; existing v0.3.22 images and packages are unchanged.

## Numbering

The [GameFAQs entry](https://gamefaqs.gamespot.com/ps/584485-super-tokusatsu-taisen-2001/faqs/82565/scenario-41b)
labels this chapter 41B. Its contents list has four alternatives at slot 41
and reaches 60E. These are guide labels, not a promise that every route plays
every numbered slot. The [Akurasu route chart](https://www.akurasu.net/wiki/Super_Tokusatsu_Wars_2001/Complete_Chart)
also places Black Cross at slot 41 and documents optional chapters that may be
skipped, including route-specific and choice-dependent omissions.

The original game does not hardcode 41 into this chapter's title card.
STAGE #433 reads the chapter counter at player state +0x5A9, increments it,
then the card routine reads that counter to select numeral sprites. Executing
the original commands at +0x3894..0x38A8 gives 37 -> 38 or 40 -> 41 depending
on the incoming counter. The title-card translation changes sprite artwork
and positions, not these counter commands.

Thus Stage 38 is consistent with a route that has counted three fewer
chapters than the guide's slot numbering. The exact skipped chapters cannot
be identified from this report alone. Do not renumber this chapter to 41:
that would mix a guide convention with the game's own route counter.

## Objective

This is internal stage record 61: STAGE #432 holds text, #433 event commands,
and #691 the compressed text/program copies (blocks 4/5). EVENT #113 is the
Black Cross title artwork; its database title index is 1364.

The native objective setter is opcode 29 at 0x8007C24C. It copies the script
accumulator into player state +0x52F for the victory label or +0x530 for the
defeat label. The menu reads these indices at 0x80045BB0 and displays the
corresponding stage-overlay string. Three phase-setting sequences execute as:

| Program offset | Victory text index | English UID | Existing instruction |
|---|---:|---|---|
| 0x1EA4 | 0 | U11023 | Defeat the Zolder soldiers and Black Cross Ninja Corps |
| 0x2AC8 | 1 | U11024 | Defeat those troops and take down Navaron |
| 0x368C | 2 | U11025 | Defeat Magman and the remaining troops |

The Japanese middle objective also gives the broad instruction to overcome
Navaron, without spelling out the positioning action. This is an objective
clarity issue carried into the English wording. The English dialogue at
U10984 explains that Red, Blue and Green approach the three rooms. The
walkthrough likewise describes adjacency triggering the three room scenes.

Only U11024 is clarified, after the plan has been revealed:

> Move Red, Blue and Green next to Navaron. Defeat all Zolders and Black Cross Ninjas!

The wording preserves the troop requirement and names the otherwise hidden
action. Earlier objectives remain unchanged, so the plan is not revealed in
the initial holding phase. The final Magman phase keeps its own objective.
This changes displayed guidance, not movement, battle or victory conditions.

## Verification and limits

`tools/check_black_cross.py` is a dry run by default. It executes original
MIPS chapter-counter and objective-selector commands, then rebuilds the text
overlay in memory. All 606 pointer entries resolve correctly; only pointer
index 1's text changes. The new objective fits one page with three lines,
each within the current 220-pixel width. `--write` applies the unique UID
override to the local working JSON, regenerates its English-only copy through
`strip_jp.clean`, and saves `work/ui/objectives/black_cross.en.json`.

The precise adjacency predicates, permitted sides/form states, full mission
playthrough and actual menu screenshot have not yet been verified. The user's
playthrough and matching walkthrough support the instruction, but should not
be treated as native execution coverage of those event conditions. A completed
future build must check raw/compressed copies and the actual menu before this
is described as an in-game verified fix. No new build or release was created.

### Local v0.3.23 follow-up, 2026-10-20

The clarification is now included in local v0.3.23. Completed-disc comparison
allows changes only in STAGE #432 and compressed entry #691 block 4; their text
payloads match, including zero padding in the raw entry. Program #433 and the
other compressed blocks retain their previous bytes. The English-only rebuild
also matches the completed archive exactly. Actual menu appearance and a full
mission playthrough remain unverified. No GitHub release created.
