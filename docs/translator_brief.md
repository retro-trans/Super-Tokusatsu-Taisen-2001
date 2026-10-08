# Translator brief — Super Tokusatsu Taisen 2001 (PS1, Banpresto 2001)

A turn-based crossover strategy game (like Super Robot Wars) with Showa-era tokusatsu heroes. It includes:

- Ultraman, Ultraseven and Ultraman Jack
- Kamen Rider 1, 2, V3, Riderman, BLACK and BLACK RX
- Gorenger
- Space Sheriffs Gavan, Sharivan and Shaider
- Kikaider and Kikaider 01
- Inazuman
- Giant Robo, Daitetsujin 17 (One-Seven) and Red Baron

There are also original characters:
- The player's UCMA unit: Captain Sawa, Chief Kitakura and the officers.
- The player's hero and heroine: [HERO1] [HERO2] / [HERO3] [HERO4].
- The invaders of the space fortress Naager: Lucifard and Fadita.
- Steel Emperor Zephas and his people: Apfaron and Atefarina.

You translate the Japanese script into English. Everything you need is in this repo.

## Your job

You get a range of batch files, `work/translation/en/batches/B####.json`. Each one holds 80 consecutive rows in play order. For every batch in your range:

1. Read the batch. Before deciding who a line is aimed at, also read the rows either side. You can open the previous and next batch (`prev`/`next`) for context.
2. Write `work/translation/en/out/B####.json`. The format is below.
3. Run `python tools/check_batch.py B####`. Fix every ERROR it prints, then re-run it until it says OK. WARN lines are advice.
4. Move on to the next batch. If an output file already exists and passes the check, skip that batch. This lets you resume after an interruption.

When you finish your range, reply with a short summary: the batches done, plus anything you could not resolve.

### Output format
```json
{"batch": "B0123",
 "rows": [{"uid": "U01234", "en": "English text", "note": "optional, only when needed"}],
 "report": {"rows_in_slice": 80, "rows_examined": 80,
            "uncertain": ["U01240: who 'he' refers to is unclear; used 'that guy'"],
            "omissions_kept": ["U01250: speaker left implicit, the scene doesn't settle it"],
            "new_names": [{"jp": "...", "en": "...", "why": "not in glossary"}],
            "glyph_suspects": [{"uid": "U01260", "seen": "火菱", "likely": "火蓋"}]}}
```
Include every row of the batch, with the same `uid`.

## Input row fields
- `kind`:
  - `dialogue`: has a speaker.
  - `narration`: no speaker.
  - `quote`: a battle quote.
  - `encyclopedia`: database text.
  - `menu`: UI or database label.
  - `music`: a song title.
- `speaker_jp` / `speaker_en`: the speaker name is drawn from the glossary and inserted automatically. Do not put it in `en`. If `speaker_en` is null on a dialogue row, report it in `new_names`.
- `jp`: the Japanese text. `\n` is the original line break, which is just layout. `<p>` is a page break (the game waits for a button).
- `budget_px` (menu/music only): the original width in pixels. English letters are about 4–8 px each (average ~6). Keep `en` within that width. The checker measures it. If it is impossible, go as short as you can, abbreviate, and say so in `note`.

## Text format rules
- **Line breaks.** Write each page as running text, with no `\n`. The insert tool wraps the English to the box width and adds pages if needed. Keep `<p>` where the Japanese has a page break, if it still makes sense in English. You may drop one; never add more than the Japanese has, plus one.
- **Brackets.** Drop the 「 」 brackets around dialogue and narration. Turn 『 』 inner quotes into "double quotes". Keep （ ） for thoughts as ( ).
- **Characters.** Use only plain ASCII, plus … — – ’ ‘ “ ” é è ê ë à â ç ô ö ü ï É ♪ ♥ ★ ☆ × ° « » ・. No other characters: the font has nothing else. Use … for trailing off, and "--" or "—" for cut-off speech.
- **Keep these exactly as written** (same tag, and the same position relative to the words they belong to):
  - `[HERO1]` hero surname, `[HERO2]` hero given name, `[HERO3]` heroine surname, `[HERO4]` heroine given name.
  - `[VAR5]` and `[VAR6]` (a hero name the game inserts, e.g. "Inazuman").
  - `<c1>`/`<c2>`/`<c3>` … `</c>` colour; wrap them around the matching English words.
  - Icons: `{direct}` `{ranged}` `{bullet}` `{elec}` `{beam}` `{water}` `{fire}` `{special}` `{P}` `{M}` `{AP}` `{S}` `{L}` `{P2}` `{A2}` `{man}` `{sword}` `{c286}` `{c287}`, and any other `{....}`. Weapon names keep their prefix and suffix icons.
- Hero names come from the player. Use the placeholders, not "Takuma" or "Saki".

## Names and terms
- Look up every name in `work/glossary/names.json` (Japanese → `{en, kind, note}`). It covers characters, units, attacks and terms. Use the glossary spelling exactly. Do not invent alternatives. `work/translation/en/out/B0001.json` is a reference output.
- If a name is not in the glossary, romanize it (modified Hepburn; people in given-name-then-family-name order). Put it in `new_names`.
- Name conventions:
  - Ranks and titles: 隊長 = Captain, 博士 = Dr., 長官 = Director, 参謀 = Staff Officer.
  - The Riders call Tobei Tachibana "Oyassan".
  - The Science Patrol call Muramatsu "Cap".
  - Drop -san, -kun and -chan unless they carry meaning.
- Shouted transformation calls stay as the show's words: 変身 → "Henshin!", 蒸着 → "Johchaku!", 赤射 → "Sekisha!", 焼結 → "Shoketsu!". In narration, "transform" is fine.
- When attack names are shouted, use the glossary spelling ("Rider Kick!").

## Known text noise
The Japanese was decoded from the game's font images, so a few kanji may be wrong. Typically a similar-looking kanji appears (博土 for 博士, 責様 for 貴様). Translate what the context clearly means. Add each suspicious word to `glyph_suspects` with what you think it should be; this fixes it for everyone else.

## Style (house rules — follow all of them)
- Dialogue should sound spoken: lively, natural, colloquial. Do not drift into formal or literary English unless the character or the moment really calls for it (an officer giving a report, a villain's speech).
- **One row in, one row out.** Never merge two rows or split one row into two. When one sentence is cut across two rows, cut the English at the matching point. A line that deliberately trails off or is interrupted stays unfinished in English.
- **Pro-drop is grammar, not style.** Where the scene settles who, English takes the subject — write it. 「頼むぜ」 is "I'm counting on you", not "Count on you". Japanese also drops verbs: 「何か理由が？」 is "Is there some reason?", not "Some reason why?". Check that a verb survived, not just a subject. Only where the scene genuinely does not settle who should you keep the ambiguity, with a passive or an impersonal construction.
- **Check the direction before choosing that construction.** 頼む / よろしく is the speaker asking the listener. As a bare English imperative it flips to the speaker offering themselves ("Count on us" for 「よろしく頼むぜ」). Name who is asking whom, then pick the form.
- Restoring a subject is not padding. Do not drop one to save room. Wrapping is automatic.
- If the dialogue refers to another person, do not assume their gender unless the scene or glossary establishes who it is. Do not infer gender from a name. For someone unknown, use a gender-neutral term.
- Write the line in full first. Do not shorten while drafting because you think it won't fit. This applies to dialogue; only menu rows have a width budget.
- Translate what the player reads; leave what the game reads. Translate dialogue, narration, sound effects written as words, interjections (ぐわぁぁッ → "Gwaaah!"), proper nouns and terms in quotes or brackets. Leave tags, placeholders and icons in place.
- **Do not soften.** Carry over every detail and the full force of the original: insults, threats, crude or extreme lines are translated at the same strength.
- Before writing a row, settle two things briefly:
  - **Context:** who is speaking to whom, the tone, and which earlier line this one answers.
  - **Decisions:** how you handle any ambiguity or difficulty.
  Report any decision that was not obvious in `uncertain`.
- **Flag every line where you kept the source's omission** (`omissions_kept`). A dropped subject leaves a line that reads fine alone, so nobody reading only the English will catch it.
- An uncertainty reported is worth more than a clean report. Report the calls you were unsure of even when the row passes: a tie you had to break, a referent you inferred, an existing line that contradicted this brief.
- When the glossary or a previous batch shows how a similar line was handled, learn from it. Do not paste it in as the answer.

## Kinds of text
- **Battle quotes** (`quote`): short and punchy. They show in a 2-line battle box. The speaker is inside the quote text for some units (`name\n「line」`). Keep the name part as the glossary English, then the line.
- **Encyclopedia** (`encyclopedia`): reference entries for units, weapons and characters. Use neutral descriptive English.
- **Menus** (`menu`): standard SRPG terminology. HP, EN, Morale (気力), Mobility (運動力), Movement (移動力), Armor (耐久性), Accuracy (命中), Evasion (回避), Skill (技量), Range (射程), Ammo (弾数), Critical, Funds (資金), Materials (資材), Terrain (地形), Size, Phase End, Intermission. Keep them short.
- **Victory and defeat conditions:** victory goals are imperatives ("Defeat all enemies!"). Defeat conditions 「Xがやられたとき」 are written as "X is defeated", and 「味方が全滅させられたとき」 as "All allies are destroyed". Keep these consistent.
