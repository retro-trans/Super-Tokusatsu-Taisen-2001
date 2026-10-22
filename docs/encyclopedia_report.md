# Encyclopedia display report — 2026-10-20

Status: investigated; defects remain open. No game build or release created.

Follow-up: local v0.3.23 fixes the separately reported index-column overlap
using 44 compact display labels. See `docs/options_index.md`. The body clipping,
series-label width and photographed digit corruption discussed here remain open.

The user supplied a handheld photograph showing Kaimen Green (5/24) and
Retsu Ichijouji (3/24), and identified the expected patch as the latest public
version, v0.3.18. The reporter's actual image/version has not been independently
verified.

## Confirmed findings

- Kaimen Green's description contains apparent digits and overlapping fragments
  in the photograph. Its translation U19442, built description slot 583, and
  the extra-word glyph pixels in v0.3.18 are intact. This corruption has not
  been reproduced. A missing translation is not the cause of the stored text.
- Retsu's description U19351 (slot 538) wraps to eight lines. The native detail
  GUI command at `0x800B3714` draws at `(24,122)`, with 16px line spacing.
  Eight lines extend to y=250, beyond even the 240px screen. Six lines fit the
  description panel. The same audit finds 233 description slots exceeding six
  lines, so editing only Retsu would leave the broader problem unresolved.
- The series command at `0x800B3724` starts at `(24,61)`. The current insertion
  pipeline wraps all encyclopedia strings at 264px, including series names
  in the narrow left column. The photograph shows Space Sheriff Gavan running
  into the right image.
- The actual native glyph lookup was executed for all 491 English codes used
  by the built encyclopedia. Widths, texture pages and UV coordinates match
  the font metadata. All 160 extra-word cells match their intended pixels.
  These checks do not emulate the complete viewer or reproduce PSP rendering.
- Local v0.3.22 has the same encyclopedia text and font as public v0.3.18.
  It therefore does not resolve this report.

## Required fix and verification

1. Give names, series labels and body descriptions separate layout bounds.
2. Preserve complete descriptions through a bounded scrolling or paged viewer;
   the general dialogue page control is not implemented by this static drawer,
   so merely inserting it would hide the remainder.
3. Reproduce Kaimen's corruption through the full viewer. Check live text RAM,
   sprite allocation/reuse and font texture uploads while navigating entries.
   The intact static data does not establish which runtime subsystem is wrong.
4. Verify both reported entries, the longest descriptions (14 lines before
   repair), series labels, page navigation and repeated entry changes. Include
   native-font PSP/POPS verification before claiming the photographed defect
   fixed. Rebuild matching replacement textures if the font atlas changes.

Run `python tools/check_encyclopedia.py 0.3.18` for a read-only audit, or add
`--write` to update `work/ui/encyclopedia/report.en.json`. The report deliberately
states `defects_confirmed_not_fixed`; it is not a passing regression result.
