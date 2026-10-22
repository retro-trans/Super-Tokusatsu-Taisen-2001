# Map command menu width

The user supplied three handheld photos showing vehicle commands extending past the map command frame: Double Machine, Grand Birth / Moto-Sharian, and Battle Hopper. Their full labels are retained. The menu also needs room for Riderman Machine, which is 122 native pixels wide.

From local v0.3.21, `tools/command_menu.py` changes the primary command object's text/highlight width at `0x800A7204 + 14` from 64 to 128 pixels. Its outer frame grows from 96 to 160 pixels. The existing special +16 width adjustment remains in the caller, so it is counted once for the frame and once for the selection highlight.

The frame helper at `0x8003D988..0x8003DA4C` is rewritten within its original 196-byte allocation. Only the primary object's horizontal geometry changes. It clamps the text origin to at least x=24 and at most `328 - frame_width`, which puts the frame inside x=8..312. It writes this origin back into the menu object before the existing cursor initializer and text drawer use it. Other menu objects retain their original frame dimensions and positions. Vertical clamping, text y, frame height, renderer depth and row spacing retain the original behavior.

`tools/check_command_menu.py` runs a dry check by default. It executes the actual old/new MIPS helper for 3,402 combinations of three menu objects, edge positions, vertical anchors, row counts and width adjustments; unrelated submenu results and vertical placement must match exactly. It additionally checks all three load instructions for PS1 load-delay hazards, which Unicorn does not model. It executes the actual cursor initializer through its width submission, then the native command drawer for 90 static-command, vehicle and transformation states. All 56 encountered labels must retain their original codes, order and positions; the longest is 122px within the 128px budget. The five reported/longest names are required to appear in these checks.

With `--verify`, the checker audits the completed v0.3.21 image against v0.3.20. It permits only the executable frame/width patch and the automatic title version update. Database contents, command names, other game files, raw movie sectors and the matching 757-file font package must remain identical. A second public-source check uses only the stripped English translations. The normal builder retains all approved movies and automatically stamps and verifies v0.3.21 with the Retro Trans title credit.

Original user photos and a comparison using the completed disc's native glyphs are kept under `work/ui/command_menu/`. The comparison is a layout reconstruction, not an emulator capture; `layout.en.json` records widths and labels. Native routine checks do not establish physical handheld rendering or a full playthrough.

Verification completed 2026-10-16: all 3,402 native frame cases, 90 command-drawer cases, the actual highlight-width submission and three PS1 load-delay checks passed. The completed disc matches the intended executable patch and automatic title update exactly. All ten unrelated files, database strings, raw movie sectors and all 757 matching font-package files are unchanged from v0.3.20. The public-source rebuild matches every rebuilt file; the build reports zero problems. Reports: `work/output/STT2001_EN_v0.3.21_command_menu_verification.json` and `work/output/STT2001_EN_v0.3.21_public_source_verification.json`. The native-font preview was visually inspected. Actual emulator and physical handheld appearance remain unverified. This is a local test build, with no release authorization.

Follow-up report, 2026-10-20: `reported_riderman.png` shows Riderman Machine
overflowing the frame. The photograph's build number is unverified. Public
v0.3.18 was checked directly and still contains the original 64px text budget
and original frame helper. Completed local v0.3.23 contains the exact v0.3.21
menu repair. Re-executing all 3,402 placement cases and 90 native command cases
against that completed EXE passed; Riderman Machine is 122px within the 128px
budget and 160px base frame. No additional build is needed for this report.
Use the v0.3.18-to-v0.3.23 local test patch, then reconvert the resulting image
for PSP. Texture replacement alone cannot widen the native menu. Actual PSP
appearance remains unverified. Audit:
`work/output/STT2001_EN_v0.3.23_riderman_verification.json`.
