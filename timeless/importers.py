"""Extract readable text and chapter headings from common manuscript files."""
from dataclasses import dataclass
import re
import sys


@dataclass
class Manuscript:
    blocks: list[str]
    title: str = ""
    author: str = ""


CHAPTER = re.compile(r"^(?:CHAPTER|PART|SECTION)\s+(?:\d+|[IVXLCDM]+)\b.{0,75}$", re.I)


def text_blocks(text):
    blocks = []
    for paragraph in re.split(r"\n[ \t]*\n", text):
        if heading := paragraph.strip():
            lines = heading.splitlines()
            if CHAPTER.fullmatch(lines[0].strip()):
                blocks.append("## " + lines.pop(0).strip())
            if lines:
                blocks.append("\n".join(lines))
    return blocks


def pdf(path):
    from pypdf import PdfReader

    book = PdfReader(path)
    chunks = []
    empty = []
    for number, page in enumerate(book.pages, 1):
        text = (page.extract_text() or "").strip()
        if text:
            chunks.extend(text_blocks(text))
        else:
            empty.append(number)
    if not chunks:
        raise ValueError("The PDF has no selectable text. Use OCR, then render the recovered text.")
    if empty:
        print(f"Import notice: {len(empty)} PDF page(s) had no selectable text. Review them for scans or visual content.",
              file=sys.stderr)
    metadata = book.metadata
    return Manuscript(chunks, metadata.title if metadata else "", metadata.author if metadata else "")


def epub(path):
    from ebooklib import ITEM_DOCUMENT, epub as reader
    from lxml import html

    book = reader.read_epub(str(path), options={"ignore_ncx": True})
    blocks = []
    for identifier, linear in book.spine:
        item = book.get_item_with_id(identifier)
        if linear == "no" or item is None or item.get_type() != ITEM_DOCUMENT:
            continue
        if isinstance(item, reader.EpubNav):
            continue
        body = item.get_body_content()
        if not body.strip():
            continue
        tree = html.fromstring(body)
        for element in tree.xpath(".//h1|.//h2|.//h3|.//p|.//li[not(.//p)]"):
            text = " ".join(element.text_content().split())
            if text:
                blocks.append(("## " if element.tag.startswith("h") else "") + text)
    title = book.get_metadata("DC", "title")
    authors = book.get_metadata("DC", "creator")
    return Manuscript(blocks, title[0][0] if title else "", ", ".join(a[0] for a in authors))


def docx(path):
    from docx import Document

    document = Document(path)
    blocks = []
    for paragraph in document.paragraphs:
        line = paragraph.text.strip()
        if not line:
            continue
        style = paragraph.style.name if paragraph.style else ""
        if style == "Title":
            blocks.append("# " + line)
        elif style.startswith("Heading"):
            blocks.append("## " + line)
        else:
            blocks.append(line)
    return Manuscript(blocks, document.core_properties.title, document.core_properties.author)


def extract(path):
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return pdf(path)
    if suffix == ".epub":
        return epub(path)
    if suffix == ".docx":
        return docx(path)
    if suffix in {".md", ".markdown", ".txt"}:
        return Manuscript(text_blocks(path.read_text(encoding="utf-8-sig")))
    raise ValueError("Use a PDF, EPUB, DOCX, TXT, Markdown, or chaptered JSON file.")
