"""Build the English disc image.

python tools/build.py <version> [--keep-font] [--movies] [--balance] [--dry-run]

Steps
  1. tools/efont.py build   English font (single + double glyphs) from the
                            current translations (skipped with --keep-font)
  2. tools/insert.py        English into STAGE/BATTLE/MAPMAIN/EVENT.DAT
  3. exe                    VWF routine (tools/vwf_patch.py) + menu strings
  4. tools/repack.py        disc re-layout (files may grow into DUMMY.DAT)
  5. tools/texpack.py       4x font texture pack for DuckStation (skip: --no-texpack)
With --movies, insert the approved pre-encoded STR frames in their original
sector slots after disc rebuilding (prepare with tools/movie_insert.py).
English TIM graphics from work/translation/en/graphics.en.json are included
by build_all after font insertion and verified against sprite boundaries.
Both native title-art copies receive the requested build version and Retro
Trans address. --dry-run validates the footer/options without building a disc.
Output: work/output/STT2001_EN_v<version>.bin/.cue and a build report.
--balance enables the experimental economy profile, adds a native title marker,
and uses a separate STT2001_EN_v<version>_balance output name. Default gameplay
retains the original tables. Both variants use the same matching font package.
From v0.3.24 onward this separate variant is replaced by the native in-game
Balance setting (default OFF). From v0.3.26 use Intermission > Difficulty;
the earlier state-0 Select hook did not target the actual root menu.
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

SRC_BIN = os.path.join(ROOT, "Super Tokusatsu Taisen 2001 (Japan).bin")
DISC = os.path.join(ROOT, "work", "source", "disc")


def main():
    version = sys.argv[1]
    import title_footer
    title_footer.validate_version(version)
    balanced = '--balance' in sys.argv
    runtime = tuple(map(int, version.split('.'))) >= (0,3,24)
    if runtime and balanced:
        raise ValueError('v0.3.24+ uses the in-game Balance setting; omit --balance')
    if balanced and tuple(map(int, version.split('.'))) < (0, 3, 22):
        raise ValueError('optional balance builds start at 0.3.22')
    if '--dry-run' in sys.argv:
        from pathlib import Path
        original = Path(DISC).parent / 'unpacked/MAPMAIN/0019.bin'
        edited, labels = title_footer.apply(original.read_bytes(), version, balanced)
        title_footer.verify(original.read_bytes(), edited, version, balanced)
        if balanced:
            import balance
            print(json.dumps({'balance': balance.profile(), 'price_halfwords': len(balance.plan()),
                              'first_change': balance.plan()[0]}, indent=1))
        print(json.dumps({'version': version, 'title_footer': labels,
                          'movies': '--movies' in sys.argv, 'dry_run': True}, indent=1))
        return
    t0 = time.time()
    if "--keep-font" not in sys.argv:
        import efont
        efont.build()
    import insert
    import repack
    import vwf_patch
    files, tr = insert.build_all()
    footer_report = title_footer.patch_files(files, version, balanced)
    ef = json.load(open(os.path.join(ROOT, "work", "font", "efont.json"), encoding="utf-8"))
    exe, tab = vwf_patch.patch_exe(open(os.path.join(DISC, "SLPS_028.63"), "rb").read(), ef["t_uni"], ef["t_bi"], ef["t_ex"])
    exe = insert.patch_exe_strings(exe, tr)
    exe = insert.patch_save_title(exe)
    exe = insert.patch_hero_select(exe)
    exe = insert.patch_var6(exe)
    import turn_popup
    exe = turn_popup.patch_exe(exe)
    import stats_layout
    exe = stats_layout.patch_exe(exe)
    import growth_layout
    exe = growth_layout.patch_exe(exe)
    import battle_voice_layout
    exe = battle_voice_layout.patch_exe(exe)
    import intermission_layout
    exe = intermission_layout.patch_exe(exe)
    if tuple(map(int, version.split('.'))) >= (0, 3, 21):
        import command_menu
        exe = command_menu.patch_exe(exe)
    balance_report = None
    if runtime:
        import runtime_balance
        exe,balance_report = runtime_balance.patch_exe(exe,report=True,support_stronger=tuple(map(int,version.split('.'))) >= (0,3,28))
    save_slot_report = None
    if tuple(map(int, version.split('.'))) >= (0,3,25):
        import save_slot_layout
        exe,save_slot_report = save_slot_layout.patch_exe(exe,report=True)
    difficulty_report = None
    if tuple(map(int, version.split('.'))) >= (0,3,26):
        import difficulty_menu
        exe,difficulty_report = difficulty_menu.patch_exe(exe,report=True,support_stronger=tuple(map(int,version.split('.'))) >= (0,3,28),story_labels=tuple(map(int,version.split('.'))) >= (0,3,29))
    difficulty_render_report = None
    if (0,3,27) <= tuple(map(int, version.split('.'))) < (0,3,28):
        import difficulty_render
        exe,difficulty_render_report = difficulty_render.patch_exe(exe,report=True)
    if balanced:
        import balance
        original_exe = exe
        exe = balance.patch_exe(exe)
        balance_report = balance.verify(original_exe, exe)
    insert.check_default_names(files)
    files["SLPS_028.63"] = exe
    os.makedirs(os.path.join(ROOT, "work", "output"), exist_ok=True)
    name = "STT2001_EN_v%s%s" % (version, '_balance' if balanced else '')
    out_bin = os.path.join(ROOT, "work", "output", name + ".bin")
    repack.rebuild(SRC_BIN, out_bin, files)
    movies = None
    if "--movies" in sys.argv:
        import movie_patch
        movies = movie_patch.patch(out_bin)
    footer_verified = title_footer.verify_disc(out_bin, version, balanced)
    with open(out_bin[:-4] + ".cue", "w") as c:
        c.write('FILE "%s.bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n' % name)
    report = {"version": version, "stats": dict(insert.STATS), "problems": insert.PROBLEMS,
              "graphics": insert.GRAPHICS_REPORT, "title_footer": footer_report,
              "title_footer_verified": footer_verified,
              "movies": movies, "balance": balance_report, "save_slot_layout":save_slot_report, "difficulty_menu":difficulty_report, "difficulty_render":difficulty_render_report, "difficulty_menu":difficulty_report, "difficulty_render":difficulty_render_report,
              "emulator_verified": False,
              "seconds": round(time.time() - t0)}
    json.dump(report, open(os.path.join(ROOT, "work", "output", name + "_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("built", name, dict(insert.STATS), "problems:", len(insert.PROBLEMS))
    if "--no-texpack" not in sys.argv:
        import texpack
        texpack.build(files, version)


if __name__ == "__main__":
    main()
