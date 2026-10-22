# Optional balance investigation and economy prototype

**Update (2026-10-22):** local v0.3.24 replaces the separate prototype image
with an in-game Gentle Balance toggle covering prices, XP, rewards, attack/
armor and fresh-stage ammo. See [current implementation](runtime_balance.md).
The following records describe the historical v0.3.22 cost-only prototype.

Investigation: 2026-10-17. Local build v0.3.22; no GitHub release created.

The request follows [issue #1](https://github.com/retro-trans/Super-Tokusatsu-Taisen-2001/issues/1)
and the user's saved NamuWiki article, `Super Special Forces 2001 - NamuWiki.htm`.
The article is a source of reports to investigate, not proof that every reported
bug occurs on every route. Its translated names are not glossary authority.
The separate linked problems page was not included in the saved article.

## First playable option

The default build keeps the original gameplay. Explicit `--balance` enables
the experimental `economy-v1` profile:

| Purchased upgrade | Original price paid | Material charge |
|---|---:|---:|
| Small unit stats or weapons | 75% | Half of the discounted funds price |
| Large unit stats or weapons | 50% | Half of the discounted funds price |

These are provisional tuning choices to reduce the cost of preparing a wider
roster, especially units that depend on purchased upgrades. All large units
use the L table, including giants as well as robots. Level-growth-only stats
remain level-growth-only. Existing purchases are not refunded.

Example: the first HP upgrade costs 1,500 funds / 750 materials for S units,
or 1,000 / 500 for L units, instead of 2,000 / 1,000. HP gains remain +3 and
+200 respectively. EN, mobility, armor and all four weapon-upgrade price
types receive the same size-based discount at every tier. The profile changes
240 price halfwords, without changing any upgrade gain or weapon power.

XP, rewards, enemy parameters, growth classes, stat caps, ammunition, deployment
rules and scenario scripts retain their original behavior. This first option
does not claim to fix all of the article's balance complaints or softlocks.
Cheaper upgrades can still make event participants stronger earlier; the
profile does not eliminate existing forced-defeat traps.

## Findings and remaining work

| Report | Evidence so far | Action/status |
|---|---|---|
| Purchased upgrades strain the early economy; robots need heavy investment | Located shared stat and weapon price tables and executed native quotes, affordability checks and purchases | Cost relief implemented; percentages need campaign feedback |
| Ammunition fails to replenish between stages | Original map setup restores HP/EN but preserves initialized ammo counts; reproduced with 0/8 and 7/8 magazines | Under investigation; no restocking change in this prototype |
| A six-slot refill loop might miss the seventh slot | Checked every original unit's first seven weapon slots; none has an ammo-limited weapon in slot 7 | Not the cause in the shipped unit data; do not apply an unrelated off-by-one fix |
| Jack's transformation/technique events can require defeat; overleveling can obstruct them | Article report; precise event predicates and route behavior not yet reproduced | Preserve XP/enemies/stats; next work is event tracing and controlled low/high-level cases |
| Early Lucifard victories can precede a turn-based technique event | Article report; event ordering not yet proved from script execution | Pending; no automatic unlock or turn-condition edits |
| Final enemy killed by an enemy-phase counterattack can skip an Atefarina event | Article report; no save or native event reproduction yet | Pending; compare player/enemy-phase final kills before changing victory checks |
| Forced MAT, Helen, Space Sheriff and Red Baron deployments can punish neglected units | Article reports specific roster/training and time-limit traps; all routes not reproduced | Cheaper upgrades help eligible units, but do not solve pilot-level gaps; deployment/event assistance remains pending |
| Blanket 3x XP and massive ally buffs/enemy nerfs would make the game easier | Requested in issue #1; no evidence that this preserves forced-defeat/event progression | Deferred while story conditions remain unresolved |
| Black Cross menu does not explain the three-Gorenger positioning action | User report and matching guide; native phase-specific objective selection and route counter executed | Clarified U11024 for the next build; see [Black Cross investigation](black_cross_objective.md). Existing v0.3.22 images are unchanged. |

The ammo finding is narrower than a complete stage-transition reproduction.
The traced initialization segment may be reached through several loading
paths. Before adding automatic restocking, distinguish a fresh stage from
resuming a mid-stage save and check whether scenario scripts subsequently
alter ammunition. A helper that fills only the `0xFF` sentinel is insufficient.

## Native evidence

Original PS1 executable: `SLPS_028.63`, RAM base `0x80010000`.

| Address | Meaning |
|---|---|
| `0x800AEF70` | Stat upgrade table: 15 rows, 32 bytes per row, eight `(u16 price, u16 gain)` pairs |
| `0x800AF150` | Weapon upgrade table: same layout; value halfwords are cumulative power thresholds |
| `0x800AF330` | Per-unit maximum stat-upgrade tier |
| `0x800665F0..0x80066628` | Native stat quote indexing and funds/material display fields |
| `0x80066B68..0x80066BB8` | Native weapon quote indexing and display fields |
| `0x80069080`, `0x80069900` | Stat affordability and purchase functions |
| `0x8006939C`, `0x80069F08` | Weapon affordability and purchase functions |
| `0x8003D274` | Initialize ammo slots carrying the `0xFF` sentinel; leaves other counts intact |
| `0x800180F8..0x80018174` | Map setup segment: restore HP/EN and call the ammo initializer |
| `0x8007A330` | Explicit scenario refill handler: mark slots as uninitialized, then initialize |

Table columns 0..3 are S, 4..7 L. Native classification is unit ID `<0xA9`
versus `>=0xA9`. Funds and materials are player-state offsets `+0x22C` and
`+0x234`. Native materials cost is the funds price shifted right once.
Only each pair's price halfword changes; adjacent gains, caps, instructions,
unit/weapon metadata and all scenario data remain unchanged. Original table
SHA-256 guards reject unexpected table data or a second application.

Ammo probe: original unit ID 2, weapon ID 6, slot index 1, capacity 8.
On map setup, sentinel 255 becomes 8; spent counts 0 and 7 remain 0 and 7.
In every case current HP/EN become their maxima. This is executable-level
evidence for persistence, not a claim that all transition paths were tested.

## Build and verification

Run all commands from the repository root. Dry-run first:

```powershell
C:/Python/python.exe tools/build.py 0.3.22 --keep-font --movies --no-texpack --dry-run
C:/Python/python.exe tools/build.py 0.3.22 --balance --keep-font --movies --no-texpack --dry-run
C:/Python/python.exe tools/check_balance.py
```

Then build both variants and check the finished discs:

```powershell
C:/Python/python.exe tools/build.py 0.3.22 --keep-font --movies --no-texpack
C:/Python/python.exe tools/build.py 0.3.22 --balance --keep-font --movies --no-texpack
C:/Python/python.exe tools/check_balance.py --verify
C:/Python/python.exe tools/check_public_build.py 0.3.22 --verify
C:/Python/python.exe tools/check_public_build.py 0.3.22 --balance --verify
```

The native harness tests all 15 tiers, S/L sizes, four stat categories and four
weapon price types. It runs 480 quote checks, 480 successful purchases, 1,440
insufficient-resource purchase attempts, 480 tier-cap attempts and 480 saturated
stat/power attempts, across original and balanced tables. Entire resulting
player states match between equal-tier original and discounted purchases.
Synthetic fixtures permit all 15 tiers and zero base stats to cover the entire
table; fixture changes are never included in the game image.

Finished-disc checks require the standard executable to match v0.3.21 exactly;
the optional executable must differ only in the intended price halfwords.
Only version/variant footer artwork may differ in MAPMAIN. All other game
files and full raw movie sectors must match. Both title copies are read back
and checked against the generated version and credit. Native lettering needs
no replacement textures. The shared 757-file texture pack is identical to
v0.3.21; older v0.3.18+ matching packs also work with these unchanged fonts.

Package locally, after verification:

```powershell
C:/Python/python.exe tools/package_balance.py 0.3.22
C:/Python/python.exe tools/package_balance.py 0.3.22 --write
```

This produces three bare `.xdelta` patches, source/target hashes, a matching
font ZIP, CUE and instructions in `work/output/balance-test-v0.3.22/`.
The inputs are the clean Japanese image, published v0.3.18, or standard local
v0.3.22, respectively; each produces the same optional v0.3.22 image. Each
patch is decoded using the Retro Trans Tools engine and checked against the
target SHA-256. Manual **Apply xdelta** supports these local files. No release
or automatic catalog entry is created.

## Gameplay validation still needed

Completed on 2026-10-17: both builds report zero problems, the native economic
checks and finished-disc isolation checks pass, and both stripped public-source
rebuilds match. All three local xdelta routes decode to the same balance image
SHA-256 `e525e13c24080e3c826525ab42c4b8af5bde706e725fd4ebb1785bfdf283b78a`.
All 757 matching texture-package files and their ZIP contents are checked.

Use in-game saves rather than emulator save states when changing builds.
Check prices and purchases on real S and L units, linked forms, low resources
and capped stats. Track early and middle campaign funds/materials and roster
use; assess whether the large-unit discount is too generous late in the game.
Keep pre-event saves for the Jack, early Lucifard, MAT, Helen and Atefarina
cases before adding scenario fixes. Existing upgrades/levels remain in saves;
switching back to the standard image restores normal future prices.

No full emulator, PSP or physical-console campaign has validated this prototype.
