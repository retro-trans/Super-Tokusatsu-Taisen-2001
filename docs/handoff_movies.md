# Movie translation handoff

Updated 2026-10-08. Review set: v0.3.4, preview revision 2. Integrated local game build: v0.3.5.

## Integration into v0.3.5

The user approved putting the movies into the game after viewing the MP4 previews and adjusting caption holds. The local v0.3.5 build includes 26 captioned movie clips and both credit rolls, with 4,722 edited video frames. The other 46 movies are unchanged. The approved draft lyrics/calls and omitted unclear sections are retained; the review-only Draft lyric translation stamp is omitted from the game. This approval is for game integration, not publication or a final release.

`tools/movie_insert.py` decodes original STR frames, draws native captions at 9 px for 160x128 clips and 12 px for 320x240 clips, and uses jPSXdec v2.1 beta to encode only frames needing captions/credits. Each frame fits its existing sector slots. English credit frames are reduced from the approved MP4 to 320x240. The original frame count, movie offsets, sector count and all XA audio bytes remain unchanged. The partial-macroblock method was tried and rejected because its STR-v3 quantization dimmed fine lettering; full changed-frame encoding retained bright readable text. Quantization scales selected ranged from 1 to 5, with 3,707 of 4,722 frames at scale 1.

`tools/movie_patch.py` validates every prepared stream against the current manifest and original source, then inserts the encoded raw sectors in the new image. `tools/build.py --movies` invokes this after rebuilding the existing text/graphics translation. `tools/check_movie_build.py` verifies the real image, not merely the working streams: source audio/nonvideo sectors, unedited frames/movies, exact inserted stream bytes, native video decoding, sector EDC/ECC, original ISO directory/LBAs and all bytes outside MOVIE.STR.

Outputs are `work/output/STT2001_EN_v0.3.5.bin/.cue`, build report, movie verification report and the matching optional 4x font pack. No GitHub release was created. Emulator/hardware playback is not verified by the offline decoder checks.

Completed v0.3.5 verification: 28 inserted movies fully decode at their original native dimensions/frame counts. All source XA audio, nonvideo sectors, untargeted frames and the 46 unedited movie clips remain unchanged. All 46,587 changed video sectors pass EDC/ECC verification. All bytes outside MOVIE.STR match v0.3.4 exactly, including the ISO directory, file offsets and sizes. The image is 725,316,816 bytes and the build reports zero problems. The actual-disc verification record is `work/output/STT2001_EN_v0.3.5_movie_verification.json`.

Reproduce the movie integration:

```powershell
& tools/movie_env/Scripts/python.exe tools/movie_insert.py
python tools/build.py 0.3.5 --keep-font --movies
& tools/movie_env/Scripts/python.exe tools/check_movie_build.py 0.3.5 0.3.4
```

The encoder is the unmodified [jPSXdec v2.1 beta release](https://github.com/m35/jpsxdec/releases/tag/v2.1), downloaded to incoming and unpacked under tools/jpsxdec. It requires Java 17 (already present). Preserve its bundled licenses when redistributing the tool; it is not included in the game image. Source replacement frames/XML/STRs and encoder logs stay under work/source/movies/encoded. The original disc and v0.3.4 build are preserved.

Revision 2 implements the user's subtitle timing preference: every spoken/sung subtitle stays visible for at least 0.5 seconds after its voice-end bound, unless the next subtitle begins sooner. Existing longer holds remain. `voice_end` is stored separately from the display `end`, making repeated renders idempotent. Prior display ends are conservative voice-end bounds where exact split-line ASR timing was not available; clip 27's final voice end is 12.66 seconds from the source recognition. All 26 clips containing captions and both combined reels were rebuilt. Credit pages retain their original timing.

All 71 caption timings were checked: 42 have at least the full 0.5-second hold, and 29 are interrupted by the next caption. None is cut short by the end of a movie. Reapplying the timing rule produces identical values. `work/ui/movies/narration_en_hold_qa.png` shows the last narration subtitle at 53.83 seconds, after its previous display end of 53.55 seconds.

Revision 2 verification passed for all 76 MP4s and 34,724 decoded video frames, including exact generated ASS/SRT timing checks. The current verification record reports preview revision 2 and a 0.5-second post-voice hold.

## Delivered review material

- `work/output/movies_v0.3.4_preview/original/`: all 74 exported source MP4s.
- `work/output/movies_v0.3.4_preview/english/`: all 74 individual review MP4s at 960x720, 12 fps, H.264/AAC, with original Japanese audio.
- `main_movies_en.mp4`: chaptered reel of movies 65-74, approximately 12 minutes.
- `battle_movies_en.mp4`: chaptered reel of movies 1-64, approximately 12 minutes.
- `work/translation/en/movies.en.json`: English subtitle text, visible credit translation and per-clip review notes. Japanese personal names are retained only when their readings have not been verified; these are permitted name entries.
- `work/translation/en/movies/`: editable ASS and SRT subtitle files. ASS also contains credit-layout events; SRT contains spoken/sung subtitle lines only.
- `work/ui/movies/`: source posters, contact sheets and selected rendered QA frames.
- `work/output/movies_v0.3.4_preview/verification.json`: full decode and timing verification record.

The preview phase did not replace movies in the disc or publish a release. The user asked to see MP4 results first and subsequently approved the v0.3.5 local integration described above.

Revision 1 verification completed successfully: 76 MP4s fully decoded, with 34,724 total video frames (17,362 original frames in the individual clips and the same frames again in the reels). Every individual clip matches the source inventory frame count. Audio/video duration differences are below 0.25 seconds; stream timestamps are monotonic. The main reel contains 10 chapters and the battle reel 64. Subtitle widths fit the measured screen budget, and representative narration, lyric and credit frames were visually checked. Revision 2 additionally checks subtitle hold/non-overlap and the generated ASS/SRT timing against the manifest; its current result is recorded in verification.json.

## Source and timing

Source: `work/source/disc/MOVIE.STR.raw2352`, 383,093,760 bytes. There are 162,880 raw 2352-byte sectors containing 74 concatenated PSX STR/XA clips. A video chunk-zero/frame-one header identifies a clip boundary.

Clips 1-64 are 160x128 battle/transform scenes; 65-74 are 320x240 movies. The actual playback rate is 12 fps, corroborated by frame counts and decoded audio-sector durations. FFmpeg's STR demuxer assumes 15 fps, so the exporter scales video timestamps by 15/12. XA coding byte 5 is stereo, 4-bit, 18.9 kHz, with 2016 decoded stereo samples per audio sector. An early 24 fps export was replaced; it is not the delivered preview.

The review renderer preserves the source aspect ratio and pads to 960x720. Source MDEC video is full-range, so the renderer explicitly converts to limited-range output before drawing credits. Credit masks sit in the source's black text regions. The English text uses Gen'ei LateGo P v2 from the existing OFL-licensed font collection. Credit pages begin at 5 seconds and advance every four seconds, ending at 93 seconds.

The early source contact sheets and `credits/01.png`-`51.png` were sampled before the frame-rate correction: their displayed seek times are half the correct playback time. They are valid visual evidence but must not be used as subtitle timings. The rendered `_en_qa.png` frames and the MP4s use the corrected timeline.

The combined reels place each clip on its video-frame timeline and resample audio against timestamps to remove small XA/AAC tail overlaps at joins. Every original video frame must survive. Chapters identify clip numbers and names.

## Whisper and translation review

Whisper large-v3 ran locally through faster-whisper on the RTX 3070 Ti, using int8_float16. No audio or source script was submitted to an external transcription service. A 64-bit Python environment lives in `tools/movie_env/`; the old system Python is 32-bit and cannot run this model.

Private source records under `work/source/movies/` include:

- `movie_NNN.wav`: mono 16 kHz PCM decoded directly from XA, avoiding AAC transcription artifacts.
- `movie_NNN.whisper.ja.json`: unprompted Japanese recognition with VAD.
- `movie_NNN.whisper.novad.ja.json`: unprompted Japanese recognition without VAD.
- `movie_NNN.whisper.en.json`: an independent English translation pass for selected spoken/sung clips.
- `asr_crops.ja.json`: independent short-window checks.
- `prompted_asr/`: rejected early output with a list-of-names prompt. This prompt caused false recognition in nonspeech clips and must not be used.

Repeated model outputs such as thanks for watching, Ending, fabricated fan-sub credits and song-production claims were rejected when they occurred over music/effects. ASR scores alone did not reliably distinguish these hallucinations.

The English text was compared across recognition passes, existing glossary/movie-list entries and visible frames. **It has not received a human listening check.** Whisper does not read visible Japanese credit text; those headings and company names were translated from frames. Narration 65 is the most dependable translation in this set.

Existing transformation calls remain Johchaku, Sekisha, Goriki Shorai and Choriki Shorai. Narration uses ordinary English transform. Babylos, Solar Metal, Grand Birth, Laser Blade and attack names follow the existing glossary. The movie-list order is recorded in batch B0266, entries U21309-U21372; it resolves garbled proper nouns but does not prove an unclear utterance.

## Remaining listening checks

- 3: short distorted cries left untranslated.
- 4: short opening call is uncertain.
- 5: Mido Puncher is supported by the movie-list identity; Doppan Shoot needs confirmation.
- 6: relay phrase around 13 seconds needs confirmation; an unclear call at 16.7-18 seconds is omitted.
- 19: distorted Kikaider counting/calls at 1.5-5.7 seconds are omitted; only Change is provisionally subtitled.
- 27: Warrior of Freedom title is partly obscured.
- 33: Rider Kick is partly inferred from the named movie and visible action.
- 39: V3 transformation call is unresolved and omitted; the models returned unreliable text.
- 43: Child of the Sun and Kamen Rider are recognized; BLACK RX comes from scene identity.
- 47: Whisper consistently recognizes Rider Power, while the movie list calls the scene Rider Punch. This disagreement remains open.
- 74: v0.3.36 adds "We get rainbow!" at 95.4-98.18, using the user's Spotify lyric screenshot and explicit approval, superseding the earlier omission. It retains v0.3.33's recovered verse at 26.34-39.42 and romaji, with 23 cues in total. The supplied YouTube Topic upload is a later self-cover without captions; Spotify's lyric panel was not independently retrieved. Earlier English wording around 57-60 and 84-95 has not received human listening confirmation. See `docs/opening_song.md` for the current audit and completed-image evidence.
- Credits 71/72: verified readings were used for Tetsuo Kudo, Yasuharu Takanashi, Akira Kushida, Koji Tsurunaga and Hiroshi Yoneyama. Other personal names retain the credited Japanese form. Company names and every section heading are English. The game's unusual credited spellings were preserved.

Credit frames are the primary evidence. The staff transcription at [Raido](https://raido.moe/staff/ps1/ps1_super_tokusatsu_taisen_2001.html) corroborates the names. Director/programmer readings were checked against their game-credit records at [MobyGames: Koji Tsurunaga](https://www.mobygames.com/person/485515/koji-tsurunaga/) and [MobyGames: Hiroshi Yoneyama](https://www.mobygames.com/person/236321/hiroshi-yoneyama/). [GDRI: Wavedge](https://gdri.smspower.org/wiki/index.php/Wavedge) corroborates the CG company's English name.

## Reproduction

Use `tools/movie_env/Scripts/python.exe` for Whisper, the subtitle renderer and verification. The movie exporter itself has no extra Python dependencies. FFmpeg is `C:/Program Files/ShareX/ffmpeg.exe`.

```powershell
& tools/movie_env/Scripts/python.exe tools/movies.py export --ffmpeg 'C:/Program Files/ShareX/ffmpeg.exe'
& tools/movie_env/Scripts/python.exe tools/movie_whisper.py
& tools/movie_env/Scripts/python.exe tools/movie_whisper.py --no-vad
& tools/movie_env/Scripts/python.exe tools/movie_subtitles.py
& tools/movie_env/Scripts/python.exe tools/movie_subtitles.py --reels
& tools/movie_env/Scripts/python.exe tools/movie_verify.py
```

Edit the English manifest directly for future revisions; do not regenerate it with the private one-off authoring helper after making edits. Raw Japanese transcripts, scripts, models and runtime dependencies are ignored. Commit only stripped English translation JSON, never Japanese source dialogue or song lyrics. No commit was made in this session.

## Local v0.3.33 follow-up

The actual game manifest now carries the opening English/romaji revision, matching `work/translation/en/opening_song.en.json`. The updated MP4 is `work/output/opening_song_review_v0.3.33/movie_074_en.mp4`; the canonical individual preview and main reel have been refreshed too. Gold romaji is above, white English below. At 95.4-95.7 the previous cue can finish its required hold; the unclear refrain itself has no caption.

Only movie 74 was re-encoded. Before editing the manifest, every old prepared stream passed the full-manifest hash, original/encoded hash, frame-slot and XA-audio checks. The other 27 prepared streams then received per-clip render fingerprints from their unchanged inputs; the old whole-manifest hash remains provenance. Future edits to one clip no longer invalidate unrelated streams. Never restamp a changed clip without re-encoding it.

Build with `C:/Python/python.exe tools/build.py 0.3.33 --keep-font --movies --no-texpack`. Movie 74 must already be prepared with `tools/movie_env/Scripts/python.exe tools/movie_insert.py --ids 74`. The v0.3.32 texture payload remains an exact match because all font copies are unchanged. Completed-image verification uses `tools/movie_env/Scripts/python.exe tools/check_movie_build.py 0.3.33 0.3.32 --title-update --changed-ids 74`; the title exception requires the exact automatic stamp and verifies all other raw disc bytes. Public-source verification and the local patch packager provide separate evidence. No GitHub release is authorized.

## Local v0.3.36 follow-up

The user supplied a Spotify lyric screenshot, then authorized adding the refrain to the MP4 and game. Current canonical/focused manifests contain 23 cues, including "We get rainbow!" from 95.4 to 98.18 seconds; the previous cue ends at 95.4. The extra verse in the full recording is absent from this game cut. Source attribution and remaining limits are in `docs/opening_song.md`; do not claim an independent human listening approval. The MP4-only intermediate manifest remains as a historical review artifact.

Validated all 28 prepared streams before changing the manifest; the private prior manifest is `work/source/movies/song_audit/movies_before_v0.3.36.en.json`. Re-encoded movie 74 only and rebuilt v0.3.36 with `--keep-font --movies --no-texpack`. Completed-disc comparison against v0.3.35 proves the exact opening/title-only change and original audio; all 28 native movies decode, 48,603 sectors pass parity, and the public English-only rebuild matches with zero problems. All 23 subtitle cues and all 76 review MP4s/reels pass. Both title copies show v0.3.36 and the Retro Trans credit. The v0.3.35 texture payload still matches. No GitHub release authorized; emulator/PSP confirmation pending.

## Local v0.3.37 follow-up

The user requested lower romaji because the top is clipped during gameplay. Clip 74 now stores `romaji_top: 16`, versus the legacy native y=5. `movie_insert.caption` accepts the position; `movie_subtitles` scales it to a 48px review margin (legacy MP4 margin was 24px). The position participates in the per-clip native fingerprint, preventing stale render reuse. All other clip fingerprints retain the old format. Text, timing, English placement and original audio remain unchanged. Prior manifest/opening backups are private under `work/source/movies/song_audit/`.

Prepare opening 74, build v0.3.37 with `--keep-font --movies --no-texpack`, compare against v0.3.36 with `check_movie_build.py --title-update --changed-ids 74`, verify the public-source rebuild, and package with `package_movie_update.py 0.3.37 --source 0.3.36`. The packager follows unchanged-texture provenance back to the v0.3.35 font verification. The same 756-image font payload still matches. No GitHub release is authorized.

Completed all of those steps: only opening/title differ from v0.3.36; all 28 native streams decode, original audio is intact, 48,603 sectors pass parity, public-source rebuild is exact with zero problems, all 76 previews decode, and Retro Trans Tools round-trip matches target SHA-256 `c6d4cca35fd8c2e072ca2377d758240ec76de1c740b722c8ea7f3f6036d38281`. Actual encoded old/new frames were inspected with a simulated top crop; all 20 bilingual cue layouts retain their romaji after 12 native lines are cropped. Both completed title copies verify v0.3.37 and credit. Emulator/PSP confirmation remains pending.

## Local v0.3.38 follow-up

The user also requested raising English captions. Clip 74 now stores `english_bottom: 16`, versus the legacy 5px inset, lifting all 23 English captions by 11 native pixels. Romaji stays at y=16. Native and MP4 renderers read the field; the MP4 uses 48px top/bottom margins. The English inset participates in the native fingerprint, so opening 74 is re-encoded while other clips reuse their checked streams. Text, timing, font sizes and audio remain unchanged. Prior manifest/opening backups are private under `work/source/movies/song_audit/`.

All 23 English caption layouts survive cropping 12 native lines from the bottom, and all 20 bilingual cues retain romaji after the same top crop. The previous English positions clipped under that simulation; the new English raster is exactly the old one shifted up 11px. Inspected actual encoded old/new frames in `work/ui/movies/song_review/english_position_v0.3.38.png`. This is a crop simulation, not emulator playback confirmation. Build v0.3.38 with `--keep-font --movies --no-texpack`, compare against v0.3.37, verify the public-source rebuild, and package with `package_movie_update.py 0.3.38 --source 0.3.37`. The v0.3.35 texture payload still matches; no GitHub release authorized.

Completed-disc checks pass for v0.3.38: only opening/title differ from v0.3.37; all 73 other movie streams and unrelated raw bytes are identical, XA audio/allocations are unchanged, all 28 inserted streams decode, and 48,603 sectors pass EDC/ECC. Both title copies verify v0.3.38/credit. The English-only source rebuild matches with zero problems, all 76 previews decode, and the 16,560,868-byte bare upgrade round-trips through Retro Trans Tools to SHA-256 `4adadf7e78f79ef42c1e76ed012b513984a1914c9ce071b9d18a0b1b0f784a9a`. The matching texture package contains the unchanged 756-image payload. No GitHub release created; emulator/PSP confirmation pending.
