# Running Timeless Narrations in the cloud

Use a Linux development environment with Python 3.11, network access to PyPI, GitHub and Hugging Face, and enough workspace disk for the model and temporary PCM audio. A GitHub Codespace for this repo already runs the bootstrap.

1. If `.venv/bin/python` is absent, run `bash scripts/bootstrap.sh`.
2. Run `bash scripts/demo.sh` to verify the default demo. Deliver `out/a-call-before-rain.m4b` as a downloadable artifact.
3. For user-supplied material, write the script and cast into `inputs/` in a private workspace. Use the input format in the README. Preserve the wording and chapter order. Assign a voice only when the speaker is identifiable and tell the user about any ambiguous roles.
4. Run `.venv/bin/python -m timeless inputs/book.md out/book.m4b --cast inputs/book.cast.json`. Monitor the job through the final JSON summary and return the file. Keep the same input path, inputs and `.timeless-work/` directory when resuming after an interruption.
5. Keep user manuscripts, full books, model files and generated private audio out of Git. The public demo workflow renders the original examples in `samples/`.
