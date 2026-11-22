"""Read chaptered prose and dialogue with named characters."""
import json
import re

from .casting import assign_voice

SPEAKER = re.compile(r"^([^:\n]{1,50}):\s+(.+)$", re.S)


def parse_markdown(path, cast):
    title = path.stem.replace("-", " ").title()
    chapters = []
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig").strip()):
        text = " ".join(line.strip() for line in block.splitlines())
        if block.startswith("# "):
            title = block[2:].strip()
            continue
        if block.startswith("## "):
            heading = block[3:].strip()
            chapters.append({"title": heading, "lines": [{"text": heading, "speaker": "narrator", "kind": "heading"}]})
            continue
        if not chapters:
            chapters.append({"title": "Opening", "lines": []})
        match = SPEAKER.match(text)
        name = match[1].lower() if match else ""
        if match and name in cast:
            chapters[-1]["lines"].append({"text": match[2], "speaker": name, "kind": "body"})
        else:
            chapters[-1]["lines"].append({"text": text, "speaker": "narrator", "kind": "body"})
    return {"title": title, "cast": cast, "chapters": chapters}


def read_book(path, cast_path):
    if path.suffix.lower() == ".json":
        book = json.loads(path.read_text(encoding="utf-8"))
    else:
        cast = json.loads(cast_path.read_text(encoding="utf-8")) if cast_path else {}
        book = parse_markdown(path, {name.lower(): profile for name, profile in cast.items()})
    if not book.get("chapters") or any(not chapter.get("lines") or not chapter.get("title") for chapter in book["chapters"]):
        raise ValueError("Every chapter needs a title and at least one line")
    return book


def voice_for(speaker, book):
    def fallback(key, profiles, engine, gender):
        if key != "narrator":
            raise ValueError(f"Set age and gender or a voice override for {speaker!r}")
        return "am_puck"

    return assign_voice(speaker, {"scores": book.get("cast", {})}, "kokoro", "male", fallback)
