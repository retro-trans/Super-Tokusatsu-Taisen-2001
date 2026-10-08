"""Inventory/export concatenated PSX STR clips without changing game data.

python tools/movies.py scan
python tools/movies.py export --ffmpeg <path> [--ids 65,66]
Raw source/transcripts stay under work/source; review MP4s under work/output.
FFmpeg's STR demuxer uses a nominal 15 Hz time base; these movies play at
12 fps, as verified from frame counts and 18.9 kHz stereo XA audio sectors.
"""
import argparse
import collections
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "work/source/disc/MOVIE.STR.raw2352"
SOURCE = ROOT / "work/source/movies"
OUTPUT = ROOT / "work/output/movies_v0.3.4_preview"
SECTOR = 2352


def scan():
    rows, current = [], None
    with RAW.open("rb") as f:
        for n in range(RAW.stat().st_size // SECTOR):
            s = f.read(SECTOR)
            typ = s[18] & 14
            if typ in (2, 8) and s[24:28] == b"\x60\x01\x01\x80":
                chunk, chunks, frame, size, w, h = struct.unpack_from("<HHIIHH", s, 28)
                if chunk == 0 and frame == 1:
                    if current:
                        current["end_sector"] = n
                        rows.append(current)
                    current = {"id": len(rows)+1, "start_sector": n,
                               "width": w, "height": h, "frames": 0,
                               "audio_sectors": 0, "fps": 12, "sample_rate": 18900}
                if chunk == 0:
                    current["frames"] += 1
            if current and typ == 4:
                if s[19] != 5:
                    raise ValueError("unexpected XA audio coding")
                current["audio_sectors"] += 1
    if current:
        current["end_sector"] = RAW.stat().st_size // SECTOR
        rows.append(current)
    for row in rows:
        row["video_seconds"] = round(row["frames"] / 12, 6)
        row["audio_seconds"] = round(row["audio_sectors"] * 2016 / 18900, 6)
        row["type"] = "battle_clip" if row["width"] == 160 else "movie"
    return rows


def export(ffmpeg, rows):
    SOURCE.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "original").mkdir(parents=True, exist_ok=True)
    frames = ROOT / "work/ui/movies"
    frames.mkdir(parents=True, exist_ok=True)
    manifest = scan()
    (SOURCE / "inventory.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    for row in rows:
        name = "movie_%03d" % row["id"]
        raw = SOURCE / (name + ".str")
        with RAW.open("rb") as f:
            f.seek(row["start_sector"] * SECTOR)
            raw.write_bytes(f.read((row["end_sector"]-row["start_sector"])*SECTOR))
        mp4 = OUTPUT / "original" / (name + ".mp4")
        log = SOURCE / (name + "_decode.log")
        args = [ffmpeg, "-hide_banner", "-loglevel", "warning", "-y", "-f", "psxstr",
                "-i", str(raw), "-map", "0:v:0", "-map", "0:a:0", "-vf",
                "setpts=(PTS-STARTPTS)*15/12", "-af", "asetpts=PTS-STARTPTS",
                "-r", "12", "-c:v", "libx264", "-preset", "fast", "-crf", "16",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart", str(mp4)]
        with log.open("w", encoding="utf-8") as f:
            subprocess.run(args, check=True, stdout=f, stderr=f)
        # ASR input uses original XA decode, with no AAC recompression.
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "psxstr",
                        "-i", str(raw), "-map", "0:a:0", "-ac", "1", "-ar", "16000",
                        "-c:a", "pcm_s16le", str(SOURCE / (name + ".wav"))], check=True)
        seek = min(row["video_seconds"]*0.45, 8)
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", str(seek),
                        "-i", str(mp4), "-frames:v", "1", "-update", "1",
                        str(frames / (name + ".png"))], check=True)
        print("Exported %s: %dx%d, %d frames, %.2fs audio" %
              (name, row["width"], row["height"], row["frames"], row["audio_seconds"]), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("scan", "export"))
    p.add_argument("--ffmpeg", default="C:/Program Files/ShareX/ffmpeg.exe")
    p.add_argument("--ids")
    args = p.parse_args()
    rows = scan()
    if args.ids:
        ids = {int(x) for x in args.ids.split(",")}
        rows = [r for r in rows if r["id"] in ids]
    if args.action == "scan":
        print(json.dumps(rows, indent=2))
        print("%d clips, %.2fs total; no files written" %
              (len(rows), sum(r["audio_seconds"] for r in rows)))
    else:
        export(args.ffmpeg, rows)


if __name__ == "__main__":
    main()
