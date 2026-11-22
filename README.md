# Timeless Narrations

Create a chaptered audiobook from a script with a deep narrator and a different voice for each character. Timeless Narrations runs on a cloud CPU and exports an M4B you can play in an audiobook app.

## Listen first

| Sample | Cast |
|---|---|
| [A Call Before the Rain](samples/a-call-before-rain.m4b) | Deep narrator, adult woman and older woman |
| [The Early Train](samples/the-early-train.m4b) | Deep narrator, a boy and his grandfather |

Both are original short scenes. Their scripts and character profiles are in [samples](samples).

## Run it in your browser

[**Open in GitHub Codespaces**](https://codespaces.new/sahilsapra391/timeless-narrations?quickstart=1)

1. Sign in to GitHub and create the codespace. Wait for its setup to finish in the browser.
2. Run the demo in the terminal.

   ```sh
   bash scripts/demo.sh
   ```

3. Find `out/a-call-before-rain.m4b` in the file browser. Right-click it and select **Download** to keep the audiobook.

The first render fetches the voice model inside the Codespace. It uses your Codespaces allowance and requires no local installs, GPU, or speech API key. You can also run the original demos from the repo’s [Actions tab](https://github.com/sahilsapra391/timeless-narrations/actions/workflows/demo.yml) if you have permission to dispatch a workflow.

## Hand it to your coding agent

Connect your agent to this GitHub repository and open a **Linux cloud workspace** for it. In a Codespace, use an agent that can run commands in the Codespace terminal. In a hosted coding agent, use its repository connection and cloud terminal. Give it this prompt.

> Read AGENTS.md, run the A Call Before the Rain demo in this cloud workspace, wait for the render to finish, and give me the M4B as a downloadable artifact.

For your own book, attach the manuscript to a private agent workspace and ask it to prepare a chaptered script and cast, render the file, and return the M4B. The [agent guide](AGENTS.md) gives it the commands. Use a workspace with enough continuous runtime for long books. Allow GitHub, PyPI, and Hugging Face downloads during setup if the workspace restricts network access.

## Render your own script

Put your script at `inputs/book.md`. Use a single `#` for the book title, `##` for each chapter, and blank lines between paragraphs or speaker turns. A new chapter gets a longer breath before the next reading begins.

```md
# A New Book

## The First Chapter

The train slipped past the platform as the lights came on.

Leo: Did we miss it?

Grandpa: That one goes north. Ours comes in three minutes.
```

Create `inputs/book.cast.json` with one profile per speaker.

```json
{
  "leo": {"age": "child", "gender": "male"},
  "grandpa": {"age": "elderly", "gender": "male"}
}
```

```sh
.venv/bin/python -m timeless inputs/book.md out/book.m4b --cast inputs/book.cast.json
```

Ordinary paragraphs use the deep narrator. A character keeps the same voice throughout the book. Supported ages are `child`, `adult`, and `elderly`. To distinguish similar characters, set `kokoro_voice` and optionally `pitch_semitones` in the profile. To fine-tune pacing, add `--wpm 175` for a measured average, or `--wpm 0` to keep the model’s pace with the configured pauses. Run the same command again to reuse completed lines after an interruption.

For an existing cloud VM, clone this repository in that VM and run `bash scripts/bootstrap.sh` with Python 3.11. A coding agent can prepare a script from accessible source documents. The renderer takes Markdown or chaptered JSON. Use a JSON object with `title`, optional `author`, `cast`, and `chapters`. Each chapter has `title` and `lines`, and each line has `text`, `speaker`, and an optional `kind` of `heading`.

## How it works

The renderer uses Kokoro, Misaki and eSpeak NG to synthesize each line. FFmpeg sets the speaking pace, normalizes loudness, and adds chapter markers. It verifies the finished audio by decoding it and reading back its chapter titles and timestamps. Character casting uses the speaker labels and profiles in your script. Plan for several minutes per chapter on a small CPU workspace.

The source is available under [GPL-3.0](LICENSE). Model files have their own upstream licenses and are fetched at runtime.
