"""Render audio in resumable chunks and export MP3, M4B or MP4."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import wave

from .cast_plan import plan_cast

from .engine import Engine, SAMPLE_RATE, prepare
from .export import FORMATS, make_additional_exports
from .manuscript import read_book

RENDER_FORMAT = 2
ENGINE = None
FFMPEG = None


def ffmpeg_command(*args):
    return [FFMPEG, "-nostdin", "-hide_banner", "-v", "error", "-y", *map(str, args)]


def begin_worker(cache):
    import imageio_ffmpeg

    global ENGINE, FFMPEG
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
    ENGINE = Engine(cache)


def raw_wave(path, audio):
    with wave.open(str(path), "wb") as dest:
        dest.setparams((1, 2, SAMPLE_RATE, 0, "NONE", ""))
        dest.writeframes(audio)


def render_line(item):
    index, text, voice, rate, destination = item
    try:
        samples = ENGINE.synthesize(text, voice.name, rate)
        pcm = (ENGINE.np.clip(samples, -.98, .98) * 32767).astype("<i2").tobytes()
        with tempfile.TemporaryDirectory(dir=destination.parent) as scratch:
            temporary = Path(scratch) / "line.wav"
            if voice.semitones:
                shifted = round(SAMPLE_RATE * 2 ** (voice.semitones / 12))
                effects = f"asetrate={shifted},aresample={SAMPLE_RATE},atempo={SAMPLE_RATE / shifted}"
                subprocess.run(ffmpeg_command("-f", "s16le", "-ar", SAMPLE_RATE, "-ac", 1, "-i", "pipe:",
                                              "-af", effects, "-threads", 1, temporary), input=pcm, check=True)
            else:
                raw_wave(temporary, pcm)
            temporary.replace(destination)
    except Exception as exc:
        raise RuntimeError(f"Line {index + 1} could not render with {voice.name}: {exc}") from exc
    return index


def work_key(book, rate):
    payload = json.dumps([RENDER_FORMAT, rate, book], sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()[:20]


def chapter_text(title):
    return title.replace("\\", "\\\\").replace("=", "\\=").replace(";", "\\;").replace("#", "\\#").replace("\n", " ")


def assemble(book, jobs, output, formats, wpm, pace, chapter_pause):
    from mutagen.mp4 import MP4

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as scratch:
        folder = Path(scratch)
        pcm = folder / "book.wav"
        position = 0
        starts = []
        index = 0
        word_count = 0
        with wave.open(str(pcm), "wb") as dest:
            dest.setparams((1, 2, SAMPLE_RATE, 0, "NONE", ""))
            for chapter in book["chapters"]:
                starts.append((position, chapter["title"]))
                dest.writeframesraw(bytes(2 * round(.55 * SAMPLE_RATE)))
                position += round(.55 * SAMPLE_RATE)
                for line in chapter["lines"]:
                    word_count += len(line["text"].split())
                    with wave.open(str(jobs[index][-1]), "rb") as clip:
                        if (clip.getnchannels(), clip.getsampwidth(), clip.getframerate()) != (1, 2, SAMPLE_RATE):
                            raise ValueError(f"Unexpected audio format in line {index + 1}")
                        frames = clip.getnframes()
                        dest.writeframesraw(clip.readframes(frames))
                    pause = 1.25 if line.get("kind") == "heading" else .24
                    if index + 1 == len(jobs):
                        pause = .9
                    if line is chapter["lines"][-1] and index + 1 < len(jobs):
                        pause = chapter_pause
                    gap = round(pause * SAMPLE_RATE)
                    dest.writeframesraw(bytes(2 * gap))
                    position += frames + gap
                    index += 1
        raw_duration = position / SAMPLE_RATE
        tempo = (raw_duration / (60 * word_count / wpm) if wpm else 1.0) * pace
        if not .6 <= tempo <= 1.55:
            raise ValueError(f"Target WPM requires an extreme adjustment ({tempo:.2f}×). Choose a closer pace.")
        audio = folder / "audio.m4a"
        subprocess.run(ffmpeg_command("-i", pcm, "-af", f"atempo={tempo},loudnorm=I=-18:TP=-2:LRA=10",
                     "-ar", SAMPLE_RATE, "-c:a", "aac", "-b:a", "72k", "-metadata", "media_type=2",
                     "-metadata", "title=" + book["title"], "-metadata", "artist=" + book.get("author", ""),
                     "-f", "mp4", audio), check=True)
        end_ms = round(MP4(audio).info.length * 1000)
        points = [round(frames / SAMPLE_RATE / tempo * 1000) for frames, _ in starts] + [end_ms]
        metadata = folder / "chapters.txt"
        entries = [";FFMETADATA1"]
        for i, (_, title) in enumerate(starts):
            entries.extend(("[CHAPTER]", "TIMEBASE=1/1000", f"START={points[i]}",
                            f"END={points[i + 1]}", "title=" + chapter_text(title)))
        metadata.write_text("\n".join(entries)+"\n", encoding="utf-8")
        complete = folder / "book.m4b"
        subprocess.run(ffmpeg_command("-i", audio, "-f", "ffmetadata", "-i", metadata, "-map", "0:a:0",
                     "-c:a", "copy", "-map_metadata", "0", "-map_chapters", "1", "-movie_timescale", "1000",
                     "-movflags", "+faststart", "-brand", "M4B ", "-f", "mp4", complete), check=True)
        subprocess.run(ffmpeg_command("-xerror", "-i", complete, "-map", "0:a", "-f", "null", "-"), check=True)
        book_audio = MP4(complete)
        chapters = list(book_audio.chapters or [])
        if [c.title for c in chapters] != [t for _, t in starts]:
            raise RuntimeError("Chapter metadata failed verification")
        if any(abs(c.start * 1000 - value) > 30 for c, value in zip(chapters, points)):
            raise RuntimeError("Chapter timestamps failed verification")
        results = make_additional_exports(ffmpeg_command, complete, formats, book, folder)
        if "m4b" in formats:
            results["m4b"] = complete
        paths = {}
        for kind in formats:
            destination = output.with_suffix("." + kind)
            results[kind].replace(destination)
            paths[kind] = str(destination)
    return {"output": paths.get("m4b", next(iter(paths.values()))), "outputs": paths,
            "chapters": len(starts), "lines": len(jobs),
            "seconds": round(book_audio.info.length, 2), "words": word_count,
            "measured_wpm": round(60 * word_count / book_audio.info.length, 1),
            "chapter_pause_after_pacing_seconds": round(chapter_pause / tempo, 2)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path, help="PDF, EPUB, DOCX, TXT, Markdown, or chaptered JSON")
    parser.add_argument("output", type=Path, help="Destination file or basename for multiple formats")
    parser.add_argument("--formats", nargs="+", choices=FORMATS, help="One render, multiple output formats")
    parser.add_argument("--pace", type=float, default=1.0, help="Final playback multiplier, e.g. 0.90 for 10%% slower")
    parser.add_argument("--plan-only", action="store_true", help="Print cast and requested pacing without synthesis")
    parser.add_argument("--narrator", help="Narrator persona name or Kokoro voice ID")
    parser.add_argument("--chapter-pause", type=float, default=2.25, help="Seconds of pause between chapters at native pace")
    parser.add_argument("--cast", type=Path, help="Character profiles for Markdown")
    parser.add_argument("--cache", type=Path, default=Path(".models"), help="Voice model cache")
    parser.add_argument("--work-dir", type=Path, default=Path(".timeless-work"), help="Resumable line audio")
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--speed", type=float, default=1.02, help="Kokoro speaking speed")
    parser.add_argument("--wpm", type=float, default=189.6, help="Target average words/min. Use 0 for native pacing.")
    args = parser.parse_args()
    if not 1 <= args.workers <= 32 or not math.isfinite(args.speed) or not .5 <= args.speed <= 1.6 or not 0 <= args.wpm <= 300:
        parser.error("Use 1 to 32 workers, speed 0.5 to 1.6, and WPM 0 to 300")
    if not .6 <= args.pace <= 1.55 or not 0 <= args.chapter_pause <= 15:
        parser.error("Use a pace between 0.6 and 1.55 and a chapter gap between 0 and 15 seconds")
    suffix = args.output.suffix.lower().lstrip(".")
    if not args.formats and suffix not in FORMATS:
        parser.error("Choose an output ending in .mp3, .m4b or .mp4, or use --formats")
    if args.formats and suffix and suffix not in FORMATS:
        parser.error("Use a basename or a supported extension with --formats")
    formats = tuple(dict.fromkeys(args.formats or [suffix]))
    book = read_book(args.script, args.cast)
    if args.narrator:
        book["narrator"] = args.narrator
    try:
        voices, cast = plan_cast(book)
    except ValueError as exc:
        parser.error(str(exc))
    requested = {"title": book["title"], "cast": cast, "pace_multiplier": args.pace,
                 "configured_wpm": args.wpm or None, "chapter_pause_seconds": args.chapter_pause,
                 "requested_formats": formats}
    if args.plan_only:
        print(json.dumps(requested, ensure_ascii=False, indent=2))
        return
    import imageio_ffmpeg

    global FFMPEG
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
    work = args.work_dir / work_key(book, args.speed)
    work.mkdir(parents=True, exist_ok=True)
    jobs = []
    for chapter in book["chapters"]:
        for line in chapter["lines"]:
            idx = len(jobs)
            voice = voices[line["speaker"]]
            rate = args.speed * (.91 if line.get("kind") == "heading" else 1.0)
            jobs.append((idx, line["text"], voice, rate, work / f"{idx:06d}.wav"))
    prepare(args.cache, {job[2].name for job in jobs if not job[-1].is_file()})
    pending = [job for job in jobs if not job[-1].is_file()]
    print(f"Rendering {len(pending)} lines. Resuming {len(jobs)-len(pending)} saved lines.", flush=True)
    if pending:
        with ProcessPoolExecutor(args.workers, initializer=begin_worker, initargs=(args.cache,)) as pool:
            for count, _ in enumerate(pool.map(render_line, pending), 1):
                if count % 25 == 0 or count == len(pending):
                    print(f"Rendered {count}/{len(pending)}", flush=True)
    result = assemble(book, jobs, args.output, formats, args.wpm, args.pace, args.chapter_pause)
    report = {**requested, **result}
    report_path = args.output.with_suffix(".cast-report.json")
    report["report"] = str(report_path)
    with tempfile.NamedTemporaryFile(dir=report_path.parent, mode="w", encoding="utf-8", delete=False) as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        temporary = Path(stream.name)
    temporary.replace(report_path)
    print(json.dumps(report, ensure_ascii=False), flush=True)
