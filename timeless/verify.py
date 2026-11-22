"""Compare a completed audiobook with its script using on-device transcription."""
import argparse
import difflib
import json
import os
from pathlib import Path
import re
import unicodedata

from .manuscript import read_book


def words(text):
    # Ignore case, typography and number formatting before comparing transcripts.
    from num2words import num2words

    text = unicodedata.normalize("NFKC", text).casefold().replace("’", "'")
    text = re.sub(r"\$(\d+)(?![\d.])", r"\1 dollars", text)
    text = re.sub(r"\b\d+\b", lambda m: num2words(int(m[0])), text)
    return re.findall(r"[^\W_]+(?:'[^\W_]+)*", text, flags=re.UNICODE)


def compare(expected, recognized):
    a = words(expected)
    b = words(recognized)
    result = difflib.SequenceMatcher(None, a, b, autojunk=False)
    differences = []
    for kind, start, end, actual_start, actual_end in result.get_opcodes():
        if kind != "equal":
            differences.append({"expected_word": start + 1, "expected": " ".join(a[start:end]),
                                "recognized": " ".join(b[actual_start:actual_end])})
    return {"source_words": len(a), "recognized_words": len(b),
            "agreement": round(result.ratio(), 4), "differences": differences}


def main():
    from faster_whisper import WhisperModel
    from mutagen.mp4 import MP4

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--cast", type=Path)
    parser.add_argument("--model", default="base.en", help="Whisper model name or cache path")
    args = parser.parse_args()
    book = read_book(args.script, args.cast)
    audiobook = MP4(args.audio)
    chapters = list(audiobook.chapters or [])
    if [chapter.title for chapter in chapters] != [chapter["title"] for chapter in book["chapters"]]:
        raise SystemExit("The M4B chapter titles do not match the script.")
    expected = " ".join(line["text"] for chapter in book["chapters"] for line in chapter["lines"])
    model = WhisperModel(args.model, device="cpu", compute_type="int8", cpu_threads=min(4, os.cpu_count() or 1))
    segments, _ = model.transcribe(str(args.audio), language="en", beam_size=5)
    report = compare(expected, " ".join(segment.text.strip() for segment in segments))
    report["chapter_count"] = len(chapters)
    report["seconds"] = round(audiobook.info.length, 2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
