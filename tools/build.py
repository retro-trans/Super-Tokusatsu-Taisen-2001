"""Build the English disc image.

python tools/build.py <version> [--keep-font] [--movies]

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
Output: work/output/STT2001_EN_v<version>.bin/.cue and a build report.
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
    t0 = time.time()
    if "--keep-font" not in sys.argv:
        import efont
        efont.build()
    import insert
    import repack
    import vwf_patch
    files, tr = insert.build_all()
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
    insert.check_default_names(files)
    files["SLPS_028.63"] = exe
    os.makedirs(os.path.join(ROOT, "work", "output"), exist_ok=True)
    name = "STT2001_EN_v%s" % version
    out_bin = os.path.join(ROOT, "work", "output", name + ".bin")
    repack.rebuild(SRC_BIN, out_bin, files)
    movies = None
    if "--movies" in sys.argv:
        import movie_patch
        movies = movie_patch.patch(out_bin)
    with open(out_bin[:-4] + ".cue", "w") as c:
        c.write('FILE "%s.bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n' % name)
    report = {"version": version, "stats": dict(insert.STATS), "problems": insert.PROBLEMS,
              "graphics": insert.GRAPHICS_REPORT, "movies": movies, "emulator_verified": False,
              "seconds": round(time.time() - t0)}
    json.dump(report, open(os.path.join(ROOT, "work", "output", name + "_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("built", name, dict(insert.STATS), "problems:", len(insert.PROBLEMS))
    if "--no-texpack" not in sys.argv:
        import texpack
        texpack.build(files, version)


if __name__ == "__main__":
    main()
