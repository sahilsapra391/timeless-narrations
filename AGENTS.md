# Create an audiobook from an attachment

Use a Linux cloud workspace with Python 3.11 and access to GitHub, PyPI, and Hugging Face. GitHub Codespaces runs dependency setup automatically.

1. Put the attachment in `inputs/`. Timeless Narrations can read PDF text, EPUB, DOCX, TXT, Markdown, and chaptered JSON. Check for scanned or unreadable pages. Recover those with OCR in the workspace before rendering and check the recovered text.
2. Use the file directly for single-voice narration. For dialogue, identify speakers from the manuscript, keep the original wording and order, and write `inputs/book.md` with named turns and `inputs/book.cast.json` using the README’s format. Use the same profile for each character throughout. If a speaker is ambiguous, let the narrator read the passage and mention that in your handoff.
3. If the user gives no settings, use the deep narrator, 90% pace, the default chapter pauses, and all three formats. Run `bash scripts/render-book.sh inputs/book.pdf` with the correct file path. For a cast, append `--cast inputs/book.cast.json` to a prepared Markdown render. Use `--formats m4b`, `--pace 1.0`, or `--narrator warm-narrator` when requested.
4. Wait for the final JSON summary. Verify that the `outputs` paths exist and return each requested file through the workspace’s downloadable artifact feature. List chapter count and runtime. Use the optional transcription check when source accuracy needs extra review.
5. To resume, run the same command in the same workspace. Keep the input and completed line cache. Keep the source document, cast, and audio in the private workspace. Commit only code and authorized public examples.
