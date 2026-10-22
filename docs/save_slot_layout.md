# Save/load slot captions — local v0.3.25

The reported screenshot shows the stage number overwriting `Stage`, an
excessive gap before `cleared`, and two counters both translated as `Turns`.
The second original label means **total turns**. These are separate saved
fields, not an accidental duplicate draw of the current-turn value.

The shared native renderer starts at `0x800493B8` and is called from five
save/load screen paths. Its quick-load variant draws one slot; regular pages
draw three. Stage titles use their own title ID, while the displayed number
uses the saved route counter plus the existing in-progress flag. The fix
retains this distinction, including optional/branched chapters.

## Repair

`tools/save_slot_layout.py` patches rendering only, after the runtime Balance
module. Code and private English labels occupy `0x800DD000..0x800DD330`, inside
the already loaded and heap-reserved `0x800DE000` limit. No extra executable
growth or disc relocation is needed beyond the v0.3.24 arrangement.

- Replace the fixed Stage/digit/title/completion draws with one caption at
  x=64, y=96/136/176, within a 244px budget ending at x=308.
- Format `Stage N: Title`, with the original stage selection and route number.
  Cleared slots retain their status. Prefer the full ` cleared` suffix;
  use ` Clr.` when the complete caption needs more room. If a title remains
  too long, keep whole native glyphs and append `...` before the status.
  The full chapter title remains available elsewhere and in the database.
- Measure each English glyph through the existing VWF lookup at
  `0x8004A7D8`, including native numeric glyphs. The old width estimator at
  `0x80030010` uses fixed 8/12px advances and caused the oversized suffix gap.
  That shared estimator is unchanged for unrelated screens.
- Use private `Turn` and `Total` labels at x=148 and x=224. Their four-digit
  value fields begin at x=184 and x=268, ending at x=216 and x=300. The native
  numeric formatter still draws the original values. Timestamps, portraits,
  slot numbers and empty-slot behavior are unchanged.
- The caption helper has its own 272-byte stack frame and 128-byte text area,
  keeping temporary text away from the caller's sprite and row-data buffers.
  It preserves saved registers and observes PS1 load/HI-LO delays.

## Verification

Run from the repository root:

```powershell
C:/Python/python.exe tools/check_save_slot_layout.py
C:/Python/python.exe tools/build.py 0.3.25 --keep-font --movies --no-texpack
C:/Python/python.exe tools/check_save_slot_layout.py --verify
C:/Python/python.exe tools/check_runtime_balance.py --version 0.3.25 --verify
C:/Python/python.exe tools/check_public_build.py 0.3.25 --verify
```

The save-slot harness executes the original renderer, the native numeric
formatter and actual VWF lookup. Sprite allocation/submission is modeled.
It reproduces the two reported captions and an empty slot, checks every
chapter title with completed/in-progress states and multiple number widths,
and exercises later pages and quick load. It verifies the four-digit spans,
header width, buffer size, return/stack safety and unchanged slot metadata.
The screenshot and native-font comparison reconstruction are kept in
`work/ui/save_slots/`; the reconstruction is not an emulator capture.

Completed-disc verification and actual emulator/PSP appearance are recorded
separately; do not treat the native harness as a full gameplay test.

Completed checks: 1,092 three-slot cases, 3,276 caption draws, six additional
page/quick-load cases, native numeric formatting, save-metadata preservation
and load/HI-LO delays all pass. Maximum caption width is exactly 244px.
The completed executable equals the proposed patch, and all unrelated game
files retain their v0.3.24 hashes. The stripped public-source rebuild is exact;
runtime Balance and native save/checksum/load regressions also pass.
The completed title asset was inspected for v0.3.25 and the full credit.

Local packaging also passes: bare patches for clean Japanese, public
v0.3.18 and local v0.3.23/v0.3.24 images all decode through Retro Trans Tools
to SHA-256 `f6749d6ef90704e61a2d5bae5e5ef494bc43c2b3e3f6a14911f96ca3a03fc9c5`.
The v0.3.24 upgrade patch is 7,081 bytes. The matching font ZIP, CUE and
installation notes are in `work/output/`; existing v0.3.24 fonts remain
compatible. No GitHub release has been created.
