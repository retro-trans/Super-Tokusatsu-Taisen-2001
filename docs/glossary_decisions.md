# Glossary and style decisions

## Compact terrain labels (v0.3.10)

The user requested readable labels within the existing one-glyph terrain slots. Unit and weapon terrain ratings now use AIR (Air), LND (Land), SEA (Sea), SPC (Space), KAI (Kaima World), GEN (Genmu World), and FUS (Fushigi World). These are display abbreviations for the existing terms; canonical glossary names are unchanged. Database-index aliases prevent the Air/Sea badges from replacing the full map terrain names that share their original strings. The Terrain heading uses two compact glyphs, preserving the 24px space before the first grade pair.

The sources are `work/glossary/names.json` (names, units, attacks, terms) and `docs/library_glossary.md`. The library one is built by `tools/build_library.py` from the translated in-game encyclopedia, BATTLE #540.

## Name conventions
- People are written in Western order, romanized in Hepburn: Takeshi Hongo, Hayato Ichimonji, Dan Moroboshi.
- Official or long-standing English fandom spellings are used where they exist:
  - Akarenger, Gavan, Sharivan, Shaider, Kikaider, Bijinder, Hakaider, Waruder, Inazuman.
  - One-Seven / One-Eight, Red Baron.
  - Alien Baltan, Zetton, Kingsaurus III, Doktor G, Ambassador Hell, Colonel Zol, Doctor Death, General Black.
- Titles: 隊長 = Captain, 博士 = Dr., 長官 = Director, 参謀 = Staff Officer, 隊員 = Officer (UCMA members).
- Nicknames: the Riders call Tobei Tachibana "Oyassan"; the Science Patrol call Muramatsu "Cap".

## Specific decisions
The Shocker monster name uses **Man Spider** by the user's explicit correction (2026-10-09, local v0.3.16). This replaces the previous project spelling throughout dialogue, unit labels, encyclopedia text and both glossary aliases. A global insertion replacement also catches the older spelling or hyphenated variant in future text. This user-requested project terminology takes precedence over the previous glossary wording.

| Term | Decision | Reason |
|---|---|---|
| 融機鋼 (decoded as 轟機鋼) | **Fusion Steel** | The logo art (EVENT #230) reads 融機鋼. 轟 was a glyph misread. Older outputs that say "Roaring Steel" are fixed by `work/translation/en/replacements.json`. |
| 飛龍 / 飛鷭 | **Hiryu** | Kenichiro Kurenai's robot (Red Baron). The stage text and the glossary use Hiryu. The library row said "Hien"; a replacement pass fixes it. |
| 変身 / 蒸着 / 赤射 / 焼結 | "Henshin!" / "Johchaku!" / "Sekisha!" / "Shoketsu!" when shouted | These are the shows' own calls. Narration uses "transform". |
| 怪人 | Monster | Glossary wording, used consistently. |
| UCMA | kept as "UCMA" | The acronym the game uses on screen. |
| Robot katakana speech (One-Seven, One-Eight, Battle Hopper, Jinbe) | CAPITALS | Keeps the mechanical voice the katakana gives. |
| 迫水 / 叶 written as plain text | kept as "Sakomizu" / "Kanou" | The Japanese has the surname as fixed text rather than [HERO1], so the original also shows it unchanged after a rename. |
| Choice rows (two or three 「」 options) | Each option in "double quotes" on its own line | The game shows the options as separate lines. `tools/insert.py` puts each quoted option on its own line, and `work/translation/en/overrides.json` holds shortened versions where an option was too wide. |
| 気力 | **Will** | The Super Robot Wars English term (akurasu). It is also short enough for the 24 px stat labels. Applied by replacements.json. |
| イーッ (Shocker combatants' cry) | **Eeee** | The combatants' trademark cry. The earlier "Iiiih" read as "liiiih" in this font. |
| Unit names in map windows | shortened where over ~134 px | Beret Combatant, Mask Combatant, K. Rider 1/2 (New), K. Rider BLACK (RX), King Gamagon, Cmdr. Hessler, W. Eagle Musasabi, Birugenia, Type 75 SP How. Only the database copy is shortened ("@MAPMAIN0002:offset" in overrides.json); the encyclopedia keeps the full name. |
| Episode title cards | "Stage" + number | User requested Chapter/Stage instead of EP; all 90 cards use Stage in local v0.3.7. |

### Dialogue display labels (v0.3.7)

Canonical glossary terms are unchanged. Eight speaker headers exceeded the 220 px dialogue margin, so dialogue alone uses shorter display labels from `work/translation/en/dialogue_layout.en.json`. General Jark's rank is abbreviated to Cmdr.; MAT officers omit the station qualifier; disguised Nackle headers use a shorter parenthetical; Granzairus uses his Kaima Beastman name without the superlative title. These are display aliases, not replacements for canonical names or wiki terms. The emperor and policeman labels are rephrased with the same meaning.

## Text noise
The Japanese was decoded from font images (13 scene sheets plus a battle sheet), so some kanji are misread. Translators corrected these from context and listed them as `glyph_suspects` in their batch reports. Insertion never re-decodes for meaning: it re-encodes the English at the original string locations, so leftover misreads don't affect the game.
