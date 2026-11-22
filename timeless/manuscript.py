"""Read chaptered prose and dialogue with named characters."""
import json
import re

from .cast_plan import cast_names, key
from .importers import extract

SPEAKER = re.compile(r"^([^:\n]{1,50}):\s+(.+)$", re.S)


def parse_manuscript(path, cast):
    document = extract(path)
    title = document.title or path.stem.replace("-", " ").title()
    chapters = []
    names = cast_names(cast)
    for block in document.blocks:
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
        name = names.get(key(match[1])) if match else None
        if name:
            chapters[-1]["lines"].append({"text": match[2], "speaker": name, "kind": "body"})
        else:
            chapters[-1]["lines"].append({"text": text, "speaker": "narrator", "kind": "body"})
    return {"title": title, "author": document.author or "", "cast": cast, "chapters": chapters}


def read_book(path, cast_path):
    if path.suffix.lower() == ".json":
        book = json.loads(path.read_text(encoding="utf-8"))
    else:
        cast = json.loads(cast_path.read_text(encoding="utf-8")) if cast_path else {}
        book = parse_manuscript(path, {key(name): profile for name, profile in cast.items()})
    if not book.get("chapters") or any(not chapter.get("lines") or not chapter.get("title") for chapter in book["chapters"]):
        raise ValueError("Every chapter needs a title and at least one line")
    book["cast"] = {key(name): profile for name, profile in book.get("cast", {}).items()}
    return book
