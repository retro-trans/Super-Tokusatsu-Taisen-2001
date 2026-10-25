# Opening-song audit and romaji

## Release v0.9.0 (2026-10-25)

The user requested publishing the completed v0.3.38 revision as v0.9.0. All movie streams and subtitle content/layout remain unchanged; only the automatic native title stamp changes. The focused/canonical manifests and copied review metadata identify v0.9.0. Current MP4: `work/output/opening_song_review_v0.9.0/movie_074_en.mp4`. The private pre-rename manifest is under `work/source/movies/song_audit/`. Full campaign and emulator/PSP playback confirmation remain pending.

Completed-disc comparison proves all 74 movie streams and all other raw bytes match v0.3.38 except the exact automatic title stamp. All 28 inserted streams decode and 48,603 caption/credit sectors pass parity. Native title copies verify v0.9.0/credit and the completed image was inspected. The 23-cue review/crop checks and exact English-only source rebuild pass. Target SHA-256: `000762aaaa9b16416546e4c11e97177175bd4a5be95155b2ab262c7243d82c8a`.

## Game v0.3.38 (2026-10-25)

At the user's request, opening English subtitles move up 11 native pixels using `english_bottom: 16`, replacing the legacy 5px inset. The MP4/ASS bottom margin increases from 32px to 48px; romaji retains native y=16 and the MP4 48px top margin. Preserve all lyric text/timing, font sizes and original audio. The English inset participates in movie 74's native render fingerprint; other clips retain their checked layout/fingerprints. Current review: `work/output/opening_song_review_v0.3.38/movie_074_en.mp4`, with ASS/SRT and verification alongside it. Earlier build records below are historical.

All 23 English caption layouts pass the 12-line bottom-crop simulation (all 23 old positions clipped), and all 20 bilingual cues still pass the corresponding top crop. English ink lies at y=210..223 with romaji at y=16..29. The native English raster is precisely the old one shifted up 11px. Inspected actual encoded frames in `work/ui/movies/song_review/english_position_v0.3.38.png`. MP4 compressed audio, all lyric/timing records and the romaji position match v0.3.37. All 76 MP4/reel previews decode (34,724 frames). Emulator/PSP confirmation remains pending.

Completed-disc comparison against v0.3.37 confirms only opening 74 and the exact automatic title stamp changed. All 73 other movies, original XA audio, allocations and unrelated raw bytes are unchanged. All 28 inserted streams decode and 48,603 sectors pass EDC/ECC. Both completed title copies verify v0.3.38 and credit; the exact English-only source rebuild matches with zero problems. The same 756-image texture payload remains compatible.

The 16,560,868-byte bare v0.3.37 upgrade round-trips through Retro Trans Tools to SHA-256 `4adadf7e78f79ef42c1e76ed012b513984a1914c9ce071b9d18a0b1b0f784a9a`. Matching texture ZIP and installation instructions are included locally; no GitHub release created.

## Game v0.3.37 (2026-10-25)

The user reported romaji being cut off at the top during gameplay. The opening now places its romaji at native y=16 instead of y=5 (11px lower). The corresponding MP4/ASS margin is 48px instead of 24px on the 960x720 review canvas. This preserves caption font sizes, English placement, all 23 cue texts/timings and the original game cut/audio. The native position is explicit in clip 74's `romaji_top` field and included in its render fingerprint; only that clip is re-encoded. Other movies retain their previous checked fingerprints.

Current review: `work/output/opening_song_review_v0.3.37/movie_074_en.mp4`; ASS/SRT and verification are alongside it. All 20 distinct bilingual cues pass a simulated crop of the top 12 native lines, with visible romaji ink at y=16..29 and English pixels unchanged. This simulation does not replace actual emulator/PSP playback confirmation. Both canonical and focused manifests describe v0.3.37, and the canonical individual preview/main reel are updated. Native title version and Retro Trans credit are generated automatically. The earlier build records below are historical.

Completed-disc comparison against v0.3.36 verifies only opening 74 and the exact automatic title stamp changed; all 73 other movies, original XA audio, frame/sector allocations and unrelated raw bytes are identical. All 28 inserted movies decode and 48,603 sectors pass EDC/ECC. Inspected the completed v0.3.37 title/credit and `work/ui/movies/song_review/romaji_position_v0.3.37.png`, showing actual old/new encoded frames before/after a simulated 12-line top crop. MP4 compressed audio and all lyric cue text/timing match v0.3.36, and the stored position correctly invalidates the old render fingerprint.

All 76 MP4/reel previews decode (34,724 frames); the exact English-only source rebuild matches with zero build problems. Optional textures are unchanged from v0.3.35/v0.3.36.

The bare v0.3.36-to-v0.3.37 upgrade is 15,284,851 bytes; Retro Trans Tools encode/decode verified target SHA-256 `c6d4cca35fd8c2e072ca2377d758240ec76de1c740b722c8ea7f3f6036d38281`. Matching texture ZIP and installation instructions are included locally; no GitHub release created.

## Game v0.3.36 (2026-10-25)

The approved MP4-only refrain below is now adopted into the native movie manifest for local v0.3.36. `work/translation/en/opening_song.en.json` matches movie 74 in `work/translation/en/movies.en.json`; both contain 23 cues. The current review MP4 and ASS/SRT are in `work/output/opening_song_review_v0.3.36/`. The canonical individual preview and main review reel are also updated. Original game audio and the shortened opening cut are retained.

Only movie 74 is re-encoded; its existing frame counts and sector capacities remain fixed. The automatic title footer identifies v0.3.36 and github.com/retro-trans. The v0.3.35 font/texture payload is reused. Build command: `C:/Python/python.exe tools/build.py 0.3.36 --keep-font --movies --no-texpack`. Movie preparation must precede it: `tools/movie_env/Scripts/python.exe tools/movie_insert.py --ids 74`. The following v0.3.33 audit is historical; its deliberate refrain omission is superseded by the user's later Spotify screenshot and authorization.

Completed-disc checks pass: `tools/check_movie_build.py 0.3.36 0.3.35 --title-update --changed-ids 74` verifies all 28 inserted streams, 73 other movies unchanged, original XA audio, fixed allocations, exact unrelated disc bytes and 48,603 sectors' EDC/ECC. Both title copies pass the automatic v0.3.36/credit comparison; inspected `work/output/STT2001_EN_v0.3.36_title_preview.png` and native encoded transitions in `work/ui/movies/song_review/refrain_encoded_v0.3.36.png`. All 23 cues pass `tools/check_song_review.py --version 0.3.36`; all 76 MP4/reel previews decode (34,724 frames). `tools/check_public_build.py 0.3.36 --verify` matches the English-only source build exactly, with zero build problems. Emulator/PSP confirmation remains pending.

`tools/package_movie_update.py 0.3.36 --source 0.3.35` produced the 672,357-byte bare upgrade, matching texture ZIP and installation instructions. All 756 texture images/config are byte-identical to v0.3.35. Retro Trans Tools encode/decode verified target SHA-256 `6217d49adda8dcfbe797e71a3f224fc1839e749b112ec9b7e27ed69815cd0d7c`. No GitHub release created.

## MP4-only revision 4 (2026-10-25)

The user supplied a Spotify lyric screenshot and authorized adding "We get rainbow!" to the MP4. The separate review is `work/output/opening_song_review_v0.3.35_r4/movie_074_en.mp4`, with ASS/SRT alongside it in `subtitles/` and its source in `work/translation/en/opening_song_mp4.en.json`. The new cue runs from 95.4 to 98.18 seconds (voice end 97.68), truncating the preceding caption at its start and retaining the half-second hold before the next line. Sung English is displayed once, following the existing style. All other lyric wording and the original game cut/audio are retained.

References: [user's Spotify track](https://open.spotify.com/track/5Rizd2UNChsPcFeIHM3N8A) and [official YouTube Topic self-cover](https://www.youtube.com/watch?v=u5CTg9cnsOY). The screenshot is the user's written reference; Spotify's lyrics panel could not be independently retrieved, and the YouTube upload has no captions. The additional verse in the full song is absent from the game cut, so it is not added. Existing game images, canonical native movie manifest and v0.3.33 review remain unchanged. The historical audit below describes that earlier build and its deliberate omission.

Verification passed: full decoding of 1,485 frames at 960x720/12 fps, all 23 subtitle cues within bounds and the post-voice hold rule, sung English displayed once, and compressed audio identical to the previous MP4. Inspected four actual MP4 frames around the new cue and following transition in `refrain_timing.png`; results are in the same folder's `verification.json`.

## Historical v0.3.33 audit

The opening has two previously omitted lyric lines at 26.34-31.9 and 33.66-39.4 seconds. They now have English translations and romaji. All 22 known lyric cues carry romaji, with sung English displayed once rather than duplicated. Gold romaji sits above the picture; white English sits below. Subtitles remain for at least 0.5 seconds after each line, except when the next cue begins sooner.

The English phrase at 95.4-97.68 could not be transcribed reliably. Independent models disagreed even after source separation and English-only retries. The user requested ignoring it, so it has no subtitle or uncertainty marker. The previous known cue still finishes its hold at 95.7. Instrumental sections have no lyric captions.

## Evidence and limits

Whisper large-v2 and large-v3 ran locally on original game XA audio and UVR-separated vocals. Both support the recovered Japanese verse; raw Japanese transcripts, models and stems remain private under ignored `work/source/movies/song_audit/`. English and ASCII Hepburn romaji are in `work/translation/en/movies.en.json`, with a focused copy in `work/translation/en/opening_song.en.json`. The romaji writes long vowels as ou/uu/aa. This is model-assisted transcription, not a human listening approval.

The opening theme is Kimi wa Senkou THUNDERBOLT, sung by Akira Kushida, with lyrics by Tetsuo Kudo and music/arrangement by Yasuharu Takanashi. The game's staff credits and the [official album retail listing](https://ototoy.jp/_/default/p/645030) corroborate those credits.

The Metal and Bio staff-roll movies (71/72, 105.5 seconds) have exactly identical source audio, SHA-256 `78b67e33213eaaecb1f0b6b2514fab2cd0187d61ea2d87bc92a457a89b20ef41`. Their isolated-vocal/mix RMS ratio is 0.00398; the short ending (73, 24 seconds) is 0.00367, compared with 0.51570 for the vocal opening. Ending recognition yielded nonspeech hallucinations rather than consistent lyrics. These three endings appear instrumental; no separate vocal ending was found in them. The audit does not establish whether all 135 BGM tracks contain vocals.

## Review files

- MP4: `work/output/opening_song_review_v0.3.33/movie_074_en.mp4` (2:03.75, 960x720, 12 fps).
- ASS/SRT: the same folder's `subtitles/` and canonical `work/translation/en/movies/movie_074.*`.
- Review checks: `work/output/opening_song_review_v0.3.33/verification.json`.
- Native encoded frame examples: `work/ui/movies/song_review/encoded_00330.png`, `encoded_00420.png`, `encoded_00600.png`, `encoded_01152.png`. These decode the actual replacement STR; they are not emulator screenshots.
- Game: `work/output/STT2001_EN_v0.3.33.bin` and matching CUE. Only opening movie 74 and the title version/credit differ from v0.3.32. All other movies, original XA audio, font, executable, gameplay and saved-name handling remain unchanged.

## Verification and reproduction

`tools/check_song_review.py` checks all preview frames/audio, 22 cue timings, the hold rule, English/romaji widths and native-size caption layouts. The main movie reel was refreshed from the updated individual preview. `tools/movie_verify.py` decodes all individual/reel previews and verifies subtitle records.

`tools/check_movie_build.py 0.3.33 0.3.32 --title-update --changed-ids 74` checks the actual image: all 28 prepared movies decode; 73 movie streams remain byte-identical to the prior build; original audio and untargeted frames are unchanged; disc directories, frame/sector allocations and other raw bytes remain identical, allowing only the exact automatic title update. All 48,251 changed movie sectors pass EDC/ECC. Both title copies show v0.3.33 and github.com/retro-trans. `tools/check_public_build.py 0.3.33 --verify` matches an English-only source rebuild with zero build problems.

Use the 64-bit `tools/movie_env/Scripts/python.exe` for media tools, and `C:/Python/python.exe` for the ordinary game builder. `tools/package_movie_update.py 0.3.33` packages the verified local v0.3.32 upgrade, unchanged matching texture payload and installation instructions; it verifies a Retro Trans Tools encode/decode round trip. No GitHub release has been created. Human listening, emulator and PSP playback confirmation remain pending.
