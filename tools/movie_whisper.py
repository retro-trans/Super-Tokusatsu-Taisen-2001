"""Japanese audio transcription using OpenAI Whisper via faster-whisper.

Run with tools/movie_env/Scripts/python.exe; model/cache and Japanese source
transcripts stay under work/source/movies. English subtitles are authored
separately after reviewing the audio and video.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/source/movies"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="large-v3")
    p.add_argument("--ids")
    p.add_argument("--device", default="cuda")
    p.add_argument("--force", action="store_true")
    p.add_argument("--no-vad", action="store_true")
    p.add_argument("--task", choices=("transcribe", "translate"), default="transcribe")
    args = p.parse_args()
    handles = []
    for lib in (Path(sys.prefix) / "Lib/site-packages/nvidia").glob("*/bin"):
        os.environ["PATH"] = str(lib) + os.pathsep + os.environ["PATH"]
        handles.append(os.add_dll_directory(str(lib)))
    from faster_whisper import WhisperModel
    print("Loading Whisper %s (%s)" % (args.model, args.device), flush=True)
    model = WhisperModel(args.model, device=args.device,
                         compute_type="int8_float16" if args.device == "cuda" else "int8",
                         download_root=str(SOURCE / "models"), cpu_threads=4)
    ids = [int(x) for x in args.ids.split(",")] if args.ids else list(range(65, 75))+list(range(1, 65))
    for clip in ids:
        name = "movie_%03d" % clip
        suffix = ".whisper.en.json" if args.task == "translate" else (
            ".whisper.novad.ja.json" if args.no_vad else ".whisper.ja.json")
        out = SOURCE / (name + suffix)
        if out.exists() and not args.force:
            continue
        start = time.time()
        segments, info = model.transcribe(str(SOURCE / (name + ".wav")), language="ja",
            task=args.task, beam_size=5, temperature=0,
            condition_on_previous_text=False, word_timestamps=True, vad_filter=not args.no_vad,
            vad_parameters={"min_silence_duration_ms": 400, "speech_pad_ms": 200},
            no_speech_threshold=0.5, log_prob_threshold=-1.0)
        rows = []
        for s in segments:
            key = "en" if args.task == "translate" else "jp"
            rows.append({"start": s.start, "end": s.end, key: s.text.strip(),
                         "avg_logprob": s.avg_logprob, "no_speech_prob": s.no_speech_prob,
                         "words": [{"start": w.start, "end": w.end, key: w.word,
                                    "probability": w.probability} for w in (s.words or [])]})
        result = {"id": clip, "engine": "faster-whisper", "model": args.model,
                  "language": "ja", "audio_seconds": info.duration, "segments": rows,
                  "task": args.task, "vad": not args.no_vad,
                  "seconds": round(time.time()-start, 2), "reviewed": False}
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        print("%s: %d segments, %.2fs processing" % (name, len(rows), time.time()-start), flush=True)


if __name__ == "__main__":
    main()
