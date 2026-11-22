# Timeless Narrations

Turn a manuscript into an audiobook in a cloud workspace. Pick a deep or warm narrator, give each character a voice, and export MP3, chaptered M4B, and MP4 with a title card.

## Listen to the samples

Press play on either sample. Both are set to **90% of the original pace** with the same voices and pitch.

### A Call Before the Rain

Deep narrator, adult woman, and older woman.

https://github.com/user-attachments/assets/8bff7fc0-91a8-4ec2-93f0-ae7fb9018650

[Script](samples/a-call-before-rain.md) · [MP3](samples/a-call-before-rain.mp3) · [M4B](samples/a-call-before-rain.m4b) · [MP4](samples/a-call-before-rain.mp4)

### The Early Train

Deep narrator, a boy, and his grandfather.

https://github.com/user-attachments/assets/a54a759e-978a-47f0-b053-4a6156df5426

[Script](samples/the-early-train.md) · [MP3](samples/the-early-train.mp3) · [M4B](samples/the-early-train.m4b) · [MP4](samples/the-early-train.mp4)

## Drop in a file and ask your coding agent

Connect your agent to this repository and open its Linux cloud workspace, or [open the repo in GitHub Codespaces](https://codespaces.new/sahilsapra391/timeless-narrations?quickstart=1). Attach your PDF, EPUB, DOCX, TXT, or Markdown manuscript privately. Paste this prompt.

> Read AGENTS.md. Turn my attached file into a full audiobook at 90% pace with the deep narrator. Analyze the manuscript for speaking characters and named narrators. Give each one a distinct voice, including people of the same age or gender. Keep aliases together and preserve the wording and chapters. Give me downloadable MP3, M4B, and MP4 files and a cast table with each person’s voice and the final pace.

The agent identifies speakers from dialogue tags, headings, and context. It resolves aliases, prepares the cast, renders the files, and tells you who got which voice, the configured pace, the measured words per minute, and the chapter count and runtime. For a scanned PDF, it needs an OCR tool in the workspace and should check the recovered text before rendering. For long books, use a workspace that can stay running and keep the workspace files so the agent can resume. Setup and voice-model downloads run in the cloud. No local setup, GPU, or speech API key is needed.

## Run it yourself in the browser

1. [Open in Codespaces](https://codespaces.new/sahilsapra391/timeless-narrations?quickstart=1) and wait for setup.
2. Upload the manuscript into `inputs/` in the file browser.
3. Run this in the Codespace terminal with your filename.

   ```sh
   bash scripts/render-book.sh inputs/book.pdf
   ```

4. Right-click each file in `out/` and select **Download**.

To try the shorter demo first, run `bash scripts/demo.sh`. People with workflow access can also run the original demos on the [Actions tab](https://github.com/sahilsapra391/timeless-narrations/actions/workflows/demo.yml). The browser terminal and hosted runs use your cloud workspace allowance.

## Set the pace, narrator, and formats

Tell your agent the settings in plain language, or pass the switches directly.

```sh
bash scripts/render-book.sh inputs/book.epub \
  --pace 0.90 --narrator warm-narrator --chapter-pause 3 \
  --formats mp3 m4b mp4
```

| To change | Ask your agent | Flag |
|---|---|---|
| Overall pace | “Make it 10% slower” | `--pace 0.90`. Use `1.00` for the baseline or `1.10` for 10% faster. |
| Reading rate | “Use about 155 words per minute” | `--wpm 155 --pace 1.00`. Set WPM to `0` for the model’s native pacing. |
| Narrator | “Use the warm narrator” | `--narrator warm-narrator`. Browse the personas below. |
| Chapter break | “Pause three seconds between chapters” | `--chapter-pause 3`. Applies before the overall pace adjustment. |
| Download formats | “Give me an M4B and an MP3” | `--formats m4b mp3`. Request any combination in a single render. |

Use **M4B** for audiobook players and chapter navigation, **MP3** for general audio players, and **MP4** for a shareable title-card video.

## Voice personas

| Persona | Delivery | Voice ID |
|---|---|---|
| `deep-narrator` | Lower-register American English narrator | `am_puck`, −2 semitones |
| `warm-narrator` | Warm adult female narration or dialogue | `af_heart` |
| `conversational-adult` | Conversational adult male | `am_michael` |
| `older-woman` | Mature woman with a gentler, lower pitch | `af_sarah`, −0.75 semitones |
| `older-man` | Lower-register older man | `am_onyx`, −0.75 semitones |
| `young-girl` | Light, higher character voice | `af_sky`, +1 semitone |
| `young-boy` | Brighter boy character voice | `am_puck`, +1.5 semitones |
| `bright-adult` | Bright adult female character | `af_bella` |
| `energetic-adult` | Energetic adult male character | `am_fenrir` |

For dialogue, your agent can create Markdown with `##` chapter headings and character lines such as `Leo: Did we miss it?`. Leave a blank line between turns. It can assign these voices in a cast file.

```json
{
  "leo": {"persona": "young-boy"},
  "grandpa": {"persona": "older-man"},
  "mara": {"kokoro_voice": "af_heart", "pitch_semitones": 0.5}
}
```

Pass it with `--cast inputs/book.cast.json`. Profiles can also use `age` (`child`, `adult`, or `elderly`) and `gender` (`male` or `female`). A character keeps the same voice throughout the book. The renderer assigns different voices when characters share a preferred persona. It looks for an unused voice in the same voice category when one is specified, then uses distinct pitch variants in larger casts. You can add `display_name`, `description`, and `aliases` to a profile. A `kokoro_voice` override locks the voice and pitch for that role.

Ordinary paragraphs use the narrator. The coding agent analyzes unlabeled dialogue and attributes it where the context identifies the speaker. It can inspect the cast before spending time on audio synthesis.

```sh
.venv/bin/python -m timeless inputs/book.md out/book.m4b \
  --cast inputs/book.cast.json --pace 0.90 --plan-only
```

A completed render writes `out/book.cast-report.json` beside the audio. It lists the final voice ID, persona when applicable, pitch, role details, and passage count for each speaker. It also records the pace settings, measured words per minute, chapter gap, runtime, and output paths.

## Resume or check a render

Run the same command again in the same workspace to reuse completed narration. The renderer checks that the exported audio decodes and verifies the M4B chapter titles. For an optional transcript comparison, run the following with your actual filenames and add `--cast` when applicable.

```sh
.venv/bin/python -m pip install -r requirements-verify.txt
.venv/bin/python -m timeless.verify inputs/book.pdf out/book.m4b
```

The report lists differences to spot-check, including possible transcription errors on names and interjections. See [AGENTS.md](AGENTS.md) for the complete cloud workflow.

Timeless Narrations uses Kokoro with Misaki and eSpeak NG, plus FFmpeg for mastering and export. Source code is available under [GPL-3.0](LICENSE). Voice weights follow their upstream licenses.
