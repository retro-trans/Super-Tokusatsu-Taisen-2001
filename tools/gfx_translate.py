"""Deterministic English TIM patches, preserving CLUTs and sprite boundaries.

python tools/gfx_translate.py --dry-run   inspect targets without writing
python tools/gfx_translate.py --write     export TIMs, previews and QA report
Build integration uses patch_files after English font insertion.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import cm
import gfx
import gfx_cards
import repack

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "work/translation/en/graphics.en.json"
PREVIEWS = ROOT / "work/ui/graphics"
EXPORT = ROOT / "work/translation/en/graphics"


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def source(target):
    data = (ROOT / "work/source/unpacked" / target["archive"] /
            ("%04d.bin" % target["entry"])).read_bytes()
    if "block" in target:
        data = cm.blocks(data)[target["block"]]
    if target["kind"] == "encyclopedia_tab_font":
        import insert
        data = insert.write_font(data)
    return data


def name_of(target):
    return "%s_%04d%s" % (target["archive"], target["entry"],
                           "_b%d" % target["block"] if "block" in target else "")


def render(data, target):
    kind = target["kind"]
    t = gfx.Tim(data)
    labels = []
    if kind == "episode":
        return gfx_cards.make_card(data, target["en"]), labels
    if kind in ("disclaimer", "narration"):
        t.fill(*target["regions"][0], int(t.idx[target["regions"][0][1], 5]))
        for row in target["labels"]:
            labels.append(t.label(row["rect"], row["en"], row["size"]))
    elif kind == "title_menu":
        box = target["regions"][0]
        t.fill(*box, 0)
        labels.append(t.label((0, 208, 160, 228), target["en"], 20, outline=1,
                              edge=(0, 80, 32), gradient=((238, 255, 238), (0, 160, 64))))
    elif kind == "options":
        for row in target["labels"]:
            t.fill(*row["rect"], t.nearest(row["background"]))
            labels.append(t.label(row["rect"], row["en"], row["size"],
                                  color=row["color"], bold=row.get("bold", 0)))
    elif kind == "battle_labels":
        for row in target["labels"]:
            t.fill(*row["rect"], 0)
            labels.append(t.label(row["rect"], row["en"], row["size"], color=(0, 189, 255)))
    elif kind == "encyclopedia_index":
        box = target["regions"][0]
        t.fill(*box, t.nearest((0, 8, 8)))
        labels.append(t.label(box, "Index", 16))
        # Row 51 contains clean paper underneath the kana glyphs.
        t.idx[35:52, 46:266] = t.idx[51:52, 46:266]
        for k, tab in enumerate(target["tabs"]):
            labels.append(t.label((46 + 22*k, 35, 68 + 22*k, 52), tab, 12,
                                  color=(16, 16, 16)))
    elif kind == "encyclopedia_entry":
        box = target["regions"][0]
        # Interpolate clean paper above/below the original label, by column.
        x0, y0, x1, y1 = box
        pal = np.array(t.palette, dtype=np.int32)
        top, bottom = pal[t.idx[y0-1, x0:x1]], pal[t.idx[y1, x0:x1]]
        for y in range(y0, y1):
            a = (y - y0 + 1) / (y1 - y0 + 1)
            rgb = (top*(1-a) + bottom*a).astype(np.int32)
            dist = ((rgb[:, None, :] - pal[None, :, :])**2).sum(axis=2)
            t.idx[y, x0:x1] = dist.argmin(axis=1)
        labels.append(t.label(box, "Appears in", 14, color=(65, 65, 57)))
    elif kind == "encyclopedia_tab_font":
        # Ten 16x16 tab cells in F0 only. Preserve every F1 pixel and all
        # remaining cells, including the English glyphs written by insert.
        for k, tab in enumerate(target["tabs"]):
            cell = np.zeros((16, 16), np.uint8)
            for size in range(14, 6, -1):
                mask = gfx.lettering(tab, size, shadow=True)
                h, w = mask.shape
                if w <= 16 and h <= 16:
                    break
            else:
                raise ValueError("tab cannot fit: %s" % tab)
            cell[(16-h)//2:(16-h)//2+h, (16-w)//2:(16-w)//2+w] = np.where(mask == 2, 3, mask)
            region = t.idx[:16, k*16:k*16+16]
            region[:] = (region & 12) | cell
            labels.append({"text": tab, "font_size": size,
                           "bounds": [k*16, 0, k*16+16, 16]})
    else:
        raise ValueError("unknown graphics kind: %s" % kind)
    return t.bytes(), labels


def verify(original, edited, target):
    a, b = gfx.Tim(original), gfx.Tim(edited)
    if len(original) != len(edited):
        raise AssertionError("TIM length changed")
    end = a.pix_off + a.idx.size // (2 if a.bpp == 0 else 1)
    if original[:a.pix_off] != edited[:b.pix_off] or original[end:] != edited[end:]:
        raise AssertionError("TIM header, CLUT or trailing data changed")
    allowed = np.zeros(a.idx.shape, bool)
    for x0, y0, x1, y1 in target["regions"]:
        allowed[y0:y1, x0:x1] = True
    changed = a.idx != b.idx
    if np.any(changed & ~allowed):
        raise AssertionError("pixels changed outside sprite rectangles")
    if target["kind"] == "episode":
        if not np.array_equal(a.idx[100:, :270], b.idx[100:, :270]):
            raise AssertionError("episode number sprites changed")
        if np.any(b.idx[100:, 297:] != a.idx[5, 5]):
            raise AssertionError("episode suffix not blank")
    if target["kind"] == "encyclopedia_tab_font":
        if np.any((a.idx & 12) != (b.idx & 12)):
            raise AssertionError("F1 font layer changed")
    return {"changed_pixels": int(changed.sum()), "palette_preserved": True,
            "sprite_bounds_preserved": True, "size": [b.w, b.h]}


def preview_image(data, target):
    t = gfx.Tim(data)
    if target["kind"] == "encyclopedia_tab_font":
        return Image.fromarray((t.idx[:16, :160] & 3)*85).convert("RGB")
    return t.rgb()


def patch_files(files):
    """Patch already-translated DAT files; preserve every untouched CM block."""
    import insert
    targets = load_manifest()["targets"]
    archives = {t["archive"] for t in targets}
    report = []
    for archive in sorted(archives):
        key = archive + ".DAT"
        entries = repack.dat_entries(files[key])
        for target in (t for t in targets if t["archive"] == archive):
            n = target["entry"]
            if "block" in target:
                k = target["block"]
                before = insert.cm_blocks_raw(entries[n])
                data = before[k][0]
                edited, labels = render(data, target)
                qa = verify(data, edited, target)
                entries[n] = insert.rebuild_cm(entries[n], {k: edited})
                after = insert.cm_blocks_raw(entries[n])
                if len(before) != len(after) or after[k][0] != edited:
                    raise AssertionError("CM round trip failed")
                if any(a[1] != b[1] for i, (a, b) in enumerate(zip(before, after)) if i != k):
                    raise AssertionError("untouched CM block changed")
            else:
                data = entries[n]
                edited, labels = render(data, target)
                qa = verify(data, edited, target)
                entries[n] = edited
            report.append({"asset": name_of(target), "kind": target["kind"], **qa,
                           "lettering": labels})
        files[key] = repack.dat_pack(entries)
    return report


def export():
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    EXPORT.mkdir(parents=True, exist_ok=True)
    report, cards, ui = [], [], []
    for target in load_manifest()["targets"]:
        data = source(target)
        edited, labels = render(data, target)
        qa = verify(data, edited, target)
        name = name_of(target)
        (EXPORT / (name + ".tim")).write_bytes(edited)
        before, after = preview_image(data, target), preview_image(edited, target)
        after.resize((after.width*2, after.height*2), Image.Resampling.NEAREST).save(
            PREVIEWS / (name + "_en.png"))
        pair = Image.new("RGB", (max(before.width, after.width)*2 + 12,
                                 max(before.height, after.height) + 20), (40, 40, 40))
        d = ImageDraw.Draw(pair)
        d.text((2, 2), name + " source", fill="yellow")
        d.text((before.width + 12, 2), "English", fill="yellow")
        pair.paste(before, (0, 20)); pair.paste(after, (before.width + 12, 20))
        (cards if target["kind"] == "episode" else ui).append((name, after, pair))
        report.append({"asset": name, "kind": target["kind"], **qa, "lettering": labels})
    for title, images in (("episode_cards_en", cards), ("ui_comparisons", ui)):
        cols = 4 if title == "episode_cards_en" else 1
        iw = 324 if cols == 4 else 656
        ih = 148 if cols == 4 else 276
        sheet = Image.new("RGB", (cols*iw, ((len(images)+cols-1)//cols)*ih), (40, 40, 40))
        draw = ImageDraw.Draw(sheet)
        for k, (name, after, pair) in enumerate(images):
            x, y = k%cols*iw, k//cols*ih
            if cols == 4:
                draw.text((x+2, y), name, fill="yellow");sheet.paste(after, (x, y+16))
            else:
                sheet.paste(pair, (x, y))
        sheet.save(PREVIEWS / (title + ".png"))
        if cols == 4:
            for page, y in enumerate(range(0, sheet.height, ih*8), 1):
                sheet.crop((0, y, sheet.width, min(y+ih*8, sheet.height))).save(
                    PREVIEWS / (title + "_%02d.png" % page))
    (PREVIEWS / "verification.json").write_text(json.dumps({"assets": len(report),
        "checks": report, "emulator_verified": False}, indent=2), encoding="utf-8")
    print("Exported %d verified TIMs and previews" % len(report))


def main():
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--write", action="store_true")
    args = ap.parse_args()
    if args.write:
        export()
    else:
        targets = load_manifest()["targets"]
        for target in targets:
            edited, labels = render(source(target), target)
            qa = verify(source(target), edited, target)
            print(name_of(target), target["kind"], target.get("en", ""), qa["changed_pixels"])
        print("%d targets verified; no files written" % len(targets))


if __name__ == "__main__":
    main()
