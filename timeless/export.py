"""Write portable audio and caption-card video from the mastered audiobook."""
from pathlib import Path
import subprocess
import textwrap

FORMATS = ("mp3", "m4b", "mp4")


def cover_image(title, author, path):
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1280, 720), "#111e24")
    draw = ImageDraw.Draw(image)
    draw.rectangle((80, 76, 1200, 642), outline="#546b68", width=2)
    draw.rectangle((125, 139, 190, 143), fill="#edc68b")
    label = ImageFont.load_default(26)
    draw.text((124, 170), "TIMELESS NARRATIONS", font=label, fill="#edc68b")
    lines = textwrap.wrap(title, width=29, max_lines=3, placeholder="…")
    headline = ImageFont.load_default(67 if len(lines) < 3 else 59)
    spacing = 82 if len(lines) < 3 else 70
    for index, line in enumerate(lines):
        draw.text((120, 258 + spacing * index), line, font=headline, fill="#f6f0e4")
    if author:
        draw.text((124, 552), author, font=ImageFont.load_default(33), fill="#b9c7bf")
    image.save(path)


def make_additional_exports(command, source, formats, book, folder):
    """Render additional files in a staging directory before publishing them."""
    exports = {}
    if "mp3" in formats:
        path = folder / "book.mp3"
        subprocess.run(command("-i", source, "-map", "0:a:0", "-map_metadata", "0", "-map_chapters", "0",
                               "-c:a", "libmp3lame", "-q:a", 2, "-id3v2_version", 3, path), check=True)
        exports["mp3"] = path
    if "mp4" in formats:
        path = folder / "book.mp4"
        cover = folder / "cover.png"
        cover_image(book["title"], book.get("author", ""), cover)
        subprocess.run(command("-loop", 1, "-framerate", 2, "-i", cover, "-i", source,
                               "-map", "0:v:0", "-map", "1:a:0", "-map_metadata", "1", "-map_chapters", "1",
                               "-c:v", "libx264", "-tune", "stillimage", "-preset", "fast", "-crf", 22,
                               "-pix_fmt", "yuv420p", "-g", 20, "-threads", 2, "-c:a", "copy", "-shortest",
                               "-movie_timescale", "1000", "-video_track_timescale", "24000",
                               "-movflags", "+faststart", path), check=True)
        exports["mp4"] = path
    for kind, path in exports.items():
        stream_map = ["-map", "0:v:0"] if kind == "mp4" else []
        subprocess.run(command("-xerror", "-i", path, "-map", "0:a:0", *stream_map,
                               "-f", "null", "-"), check=True)
    return exports
