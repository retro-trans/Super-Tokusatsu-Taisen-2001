# In-game difficulty setting — local v0.3.27

Selected profile: Gentle, explicitly chosen by the user on 2026-10-22.
The standard image now includes the optional setting; no separate balance
image or re-patching is needed to switch rules. Published in v0.3.27 on 2026-10-22.

At **Intermission > Difficulty**, choose **Normal** (original rules) or
**Gentle**. Up/Down selects; Circle applies; Cross cancels without changing the
saved mode. The right panel always shows the current mode while the submenu
is closed. Normal is the default. The choice is stored in ordinary in-game
saves. Texture replacement is optional; every label uses native font glyphs.
Cold boot the new disc and load an in-game save; an old emulator save state
can retain the previous executable in RAM.

The v0.3.24/v0.3.25 Select shortcut incorrectly assumed menu state 0 was the
Intermission root. That state is a unit context menu; the photographed root
is state 22, reached by native type 6, with GUI script `0x800B2AD4`. Previous
synthetic state-0 tests checked the hook logic but did not establish its
connection to the actual screen. v0.3.26 removes that shortcut and its label
hook, preserves the gameplay hooks and uses a real sixth root-menu row.

| Category | ON (Gentle) | OFF |
|---|---|---|
| Purchased stat and weapon upgrades | S: 75% price; L: 50%; materials = discounted funds / 2 | Original prices |
| Battle XP | 150%, rounded down | Original award |
| Funds/materials | 150% battle and chapter-clear rewards | Original rewards |
| Ally combat stats | Attack and armor 110% in damage calculation | Original calculation |
| Enemy combat stats | Attack and armor 90% in damage calculation | Original calculation |
| Ammunition | Full magazines during fresh-stage setup | Original persistence |

Stat modifiers apply to working combat values, including normal attacks,
counterattacks and MAP damage, without writing boosted values into saves.
HP/EN maxima, movement, accuracy, evasion, skill, Will, base growth and unit
upgrade gains/caps are unchanged. Native player-roster units receive the ally
modifier; native enemy-roster units receive the enemy modifier, even when
attacking a target on the same side. Existing terrain, Will and critical
calculations continue to operate. Nonzero scaled attack/armor retain a minimum
of one. Scripted level-setting instructions do not receive bonus XP.

The XP-only non-kill reward path also receives the multiplier. Pending XP is
capped at 32,767 to fit the game's signed display field; the native 49,000
total-XP cap remains intact. Rewards shown use the same scaled values paid to
the wallet and pilots. Script-granted money/items are not multiplied.

Turning OFF changes future purchases/rewards and restores the original combat
rules. It does not reverse earned XP, rewards or upgrades. Ammo refill occurs
at the fresh-stage call only: loading a mid-stage save, transforming a unit or
calling the ordinary sentinel initializer does not trigger extra restocking.
The original roster has no ammo-limited weapon in slot seven, so the native
six-slot magazine loop is retained.

## Native implementation

`tools/runtime_balance.py` is applied by both the normal builder and the
stripped English-only source verifier for v0.3.24+. Historical `--balance`
builds remain reproducible; the option is rejected for new versions, which
always contain the toggle and start OFF.

- Exact marker `0x424D0001` at player-state `+0x218` means ON; every other value
  means OFF. This unused aligned word is within the original save packer's
  verbatim `+0..0x3C77` segment. Original native code has no accesses to the
  reserved word. The packer at `0x800428D4`, checksum and loader at
  `0x80042BE4` are executed in tests with both modes, including clearing the
  working state between packing and loading. Save file size/format are unchanged.
- From v0.3.26, `tools/difficulty_menu.py` replaces the two historical UI
  hooks after runtime Balance and save-slot patching. It appends a sixth row
  to state 22, extends only its left panel and adds a right status/options
  panel. The original five row IDs/actions remain unchanged. Circle on row
  six opens a two-choice modal; fresh button presses change/apply/cancel it.
  Every change invokes the full native renderer immediately. Held Confirm
  cannot apply, reopen or repeat the operation. Select has no difficulty role.
  Code/data occupy `0x800DD340..0x800DD71C`, within the existing DE000 heap
  reservation; the same saved marker and gameplay hooks are retained.
  `tools/check_difficulty_menu.py` derives the root from the native type and
  GUI tables, then executes config initialization, the actual input driver,
  wrapped native navigation, original confirms and full root rendering.
  Graphic allocation/submission and controller hardware are modeled; this
  is not an emulator screenshot or PSP playthrough.
- Synchronize both RAM price tables from independent original/discounted
  source pairs before each quote, affordability check and purchase. This
  restores the correct prices after toggles, loads and new games without
  compounding discounts. Table gains/caps are untouched.
- Scale pending battle payouts at `0x80047A18`, XP-only rewards at
  `0x80047AB4` and chapter rewards at `0x80026D6C`, before the native display
  and award routines use them. Native story-level setter `0x800790B8` is intact.
- Wrap only the fresh-stage ammo call at `0x8001815C`. The native resume branch
  at `0x8001809C` skips this section. Other calls to `0x8003D274` remain intact.
- Shared damage routine `0x800546B8` is used by normal and MAP attacks. Retain
  its original attacker/defender roster selectors, then scale attack/armor
  registers before its terrain/Will arithmetic at `0x80054ADC`. OFF executes
  the original calculation without modifications to those working values.
- Code/data occupy `0x800DC400` through the address recorded in the build
  report, above the native BSS end `0x800DC368`. The EXE load extends to
  `0x800DE000`, below stage overlays at `0x800E0000`. BIOS heap start advances
  to `0x800DE000`; BSS clearing remains unchanged. Test the actual startup
  clear and heap arguments. Caller registers and PS1 load/HI-LO delays are
  preserved; game hooks do not use kernel scratch registers.
- The original EXE's sector range ends immediately before the movie. The
  repacker relocates an enlarged PS-X EXE to the movable archive region and
  updates both endian copies of its ISO directory LBA/length. BIOS BOOT still
  resolves the unchanged SYSTEM.CNF filename. Movies and XA audio keep their
  original locations, and DUMMY absorbs the additional space.

## Verification and testing

Run from the repository root:

```powershell
C:/Python/python.exe tools/build.py 0.3.24 --keep-font --movies --no-texpack
C:/Python/python.exe tools/check_runtime_balance.py --verify
C:/Python/python.exe tools/check_public_build.py 0.3.24 --verify
```

The MIPS harness checks all 240 prices with OFF/ON/ON/OFF sequences, quote vs
payment, 960 purchases with identical gains and 1,920 rejected purchases with
unchanged player state. It exercises 114 native setting draws, old-state
default behavior, native save/checksum/load round trips, startup clearing,
reward display/payout, native XP capping, six-slot ammo at first/middle/last
roster positions and the complete damage formula for both sides. Rendering
submission is modeled; recorded labels/coordinates are in
`work/ui/balance/layout.en.json`. Generated previews are reconstructions.

Campaign behavior, PSP and actual emulator rendering remain unverified.
Forced-loss events and the other unresolved story-trigger reports in
[the investigation](balance_patch.md) have not been rewritten by this option.
Use an in-game save after starting the new image; an old emulator save state
contains the previous executable in RAM.

Completed local package: all three bare xdelta input routes (clean Japan,
public v0.3.18 and local v0.3.23) decode through the Retro Trans Tools engine
to SHA-256 `95ef11ea570f72e9849a9d22d2b0c9b99f7626d201ba09a45ef612d46c1cf3cc`.
Both completed title copies, exact stripped public-source rebuild, ISO boot
directory records, non-overlapping files, unchanged raw movie/XA sectors and
the matching 757-file texture package pass checks. The completed title asset
was visually inspected for v0.3.24 and the full credit. Use
`tools/package_runtime_balance.py 0.3.24 --write` to reproduce local packaging;
it never publishes a release.

## v0.3.26 completed validation

The completed image passes the real root config/input/full-render tests,
including automatic redraw from the input path (not manually calling a draw
helper), six-row wrap, original confirmations, cancel/apply and held input.
All 240 upgrade prices, 960 purchases, 1,920 rejected payments, combat,
rewards, ammo, save/checksum/load and PS1 instruction-delay regressions pass.
All 1,092 save-slot cases and six later-page cases also pass. The public
English-only rebuild is exact. Title copies carry v0.3.26 and full credit;
the completed title and native-font layout reconstruction were inspected.

Five local patches from Japan, v0.3.18, v0.3.23, v0.3.24 and v0.3.25 decode
through Retro Trans Tools to target SHA-256
`2e0b906bdda24f5ec69a9bf7f0fc1cfa5ae6af60ef392af9cfbfd99feca9921c`.
The v0.3.25 upgrade is 7,017 bytes. Matching textures/instructions are included;
all 757 texture files and raw movie/audio sectors retain their previous
bytes. Reports are `work/output/STT2001_EN_v0.3.26_*verification.json` and
layout artifacts are in `work/ui/difficulty/`. No emulator/PSP visual test or
GitHub publication is claimed.

## v0.3.27 retained-text repair

The user's v0.3.26 capture shows only a red arrow, with Difficulty/choices
and the stage footer missing. `0x8004C90C` calls raw text drawing and then
`0x8004BF8C`, which finalizes a complete reusable sprite group. Repeating
that wrapper for multiple labels in group 13 replaces earlier labels and
the footer. The earlier tests mocked finalization and checked requests,
which failed to catch this defect.

`tools/difficulty_render.py`, applied only from v0.3.27 after the historical
menu patch, redirects the eight custom draws to `0x8004A954` in group 18 and
finalizes once after the complete menu. The native renderer already clears
group 18 before each root draw. Footer group 13 is independent. Non-root
states do not finalize group 18. The new return stub occupies
`0x800DD720..0x800DD744`, within the existing reserved region. Yellow is native
color 3 / CLUT F6; color 1 / F2 was red.

`tools/check_difficulty_render.py` executes the actual text/glyph routines,
VWF lookup, positions, allocator, group reuse/clear and finalizer. It
reproduces the old one-arrow/no-footer state, then checks the retained
sprites, not just drawing requests. Normal/Gentle status retains 28 menu
sprites plus 23 footer sprites; the choices retain 36 plus 23. Cancellation,
application and repeated redraws retain the correct lines/arrow/color.
Graphics engine object registration and controller hardware are modeled;
this is not an emulator capture. The preview reconstructs actual retained
sprite UV/CLUT/position/size values from the completed font sheet. See
`work/ui/difficulty/reported_v0.3.26.png` and
`work/output/STT2001_EN_v0.3.27_difficulty_render_verification.json`.

Completed v0.3.27 passes the retained-sprite checker, native menu/controller
checks and all existing price/purchase/combat/reward/ammo/save/PS1-delay
regressions. The stripped public-source rebuild is exact; build problems
are zero. The completed title/full credit and native retained-sprite
reconstruction were visually inspected. Actual emulator/PSP appearance
remains unverified. Menu/save-slot logic and all previous fixes are retained.

All six local bare patch routes (Japan/v0.3.18/v0.3.23/v0.3.24/v0.3.25/v0.3.26)
round-trip through Retro Trans Tools to SHA-256
`fa4ddddacbfa9c6f3ae8dcc3ca5bdd3c82699fe745450e0c6a3f513d2f8732fa`. The v0.3.26 upgrade is 6,031 bytes.
Matching texture ZIP/instructions included; all 757 font files and raw
movie/audio sectors are unchanged. No GitHub release created.

## Publication

v0.3.27 was published on 2026-10-22 at https://github.com/retro-trans/Super-Tokusatsu-Taisen-2001/releases/tag/v0.3.27 .
All 15 uploaded assets match the verified local files. The live Retro Trans
Tools catalog includes the six routes and supports public v0.3.6 via v0.3.18.
Source/tag commit: `d0acb475a3ea634a3fbd3007deaa2346bdac1289`.
Release record: `work/output/github-release-v0.3.27.json`. Earlier local
validation notes retain their historical publication status.

### Release asset cleanup (2026-10-22)

At the user's request, removed the v0.3.23 and v0.3.24 upgrade assets because
those source builds were not public. The live release now has four active
patch routes and 13 assets, with updated manifest/validation/checksums and
instructions. Retro Trans Tools retains the two exact historical routes as
withdrawn identities, excluded from recognition and routing. Remaining
patch bytes and target output are unchanged. Current verification record:
`work/output/github-release-v0.3.27-withdrawal.json`.
