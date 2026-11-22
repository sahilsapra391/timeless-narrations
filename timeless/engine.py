"""CPU Kokoro synthesis with explicit pronunciation fallback."""
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.request import urlretrieve

from .casting import kokoro_pronunciation

MODEL_URL = "https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX/resolve/main/"
VOICES = {"am_puck", "am_michael", "am_onyx", "am_fenrir", "af_heart", "af_sarah", "af_sky", "af_bella"}
SAMPLE_RATE = 24000


def asset(cache, name):
    path = cache / Path(name).name
    if not path.is_file():
        cache.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=cache, delete=False) as temporary:
            scratch = Path(temporary.name)
        try:
            urlretrieve(MODEL_URL + name, scratch)
            scratch.replace(path)
        finally:
            scratch.unlink(missing_ok=True)
    return path


def prepare(cache, voices):
    asset(cache, "onnx/model_quantized.onnx")
    asset(cache, "tokenizer.json")
    for voice in sorted(voices):
        if voice not in VOICES:
            raise ValueError(f"Unknown Kokoro voice {voice!r}. Available: {', '.join(sorted(VOICES))}")
        asset(cache, f"voices/{voice}.bin")


class Engine:
    def __init__(self, cache, threads=1):
        import espeakng_loader
        import numpy as np
        import onnxruntime as ort
        from phonemizer.backend.espeak.wrapper import EspeakWrapper
        from misaki import en, espeak

        os.environ["ESPEAK_DATA_PATH"] = espeakng_loader.get_data_path()
        EspeakWrapper.set_data_path(espeakng_loader.get_data_path())
        self.g2p = en.G2P(british=False, fallback=espeak.EspeakFallback(british=False), unk="❓")
        self.np = np
        self.cache = cache
        self.vocab = json.loads((cache / "tokenizer.json").read_text())["model"]["vocab"]
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(cache / "model_quantized.onnx"), options,
                                           providers=["CPUExecutionProvider"])

    @lru_cache(maxsize=12)
    def embedding(self, name):
        return self.np.fromfile(self.cache / f"{name}.bin", dtype="<f4").reshape(-1, 256)

    def phonemes(self, text):
        text = kokoro_pronunciation(text).replace("…", "...")
        text = re.sub(r"(?<=[a-z])\s+-\s+(?=[a-z])", ", ", text, flags=re.I)
        phones, tokens = self.g2p(text)
        if "❓" in phones or not phones.strip():
            unknown = [t.text for t in (tokens or []) if getattr(t, "phonemes", None) is None and any(c.isalpha() for c in t.text)]
            raise ValueError(f"Pronunciation fallback failed for {unknown or text[:40]!r}")
        return phones

    def synthesize(self, text, name, rate):
        np = self.np
        ids = [self.vocab[c] for c in self.phonemes(text) if c in self.vocab]
        if len(ids) > 480:
            cuts = [m.end() for m in re.finditer(r"[,;:]\s+|\s+", text)]
            if not cuts:
                raise ValueError("An utterance contains a word longer than the model window")
            middle = min(cuts, key=lambda cut: abs(cut - len(text) / 2))
            left = self.synthesize(text[:middle].strip(), name, rate)
            right = self.synthesize(text[middle:].strip(), name, rate)
            return np.concatenate((left, np.zeros(1650, dtype=np.float32), right))
        style = self.embedding(name)
        out = self.session.run(None, {"input_ids": np.array([[0, *ids, 0]], np.int64),
                                      "style": style[len(ids):len(ids)+1],
                                      "speed": np.array([rate], np.float32)})[0].reshape(-1)
        active = np.flatnonzero(np.abs(out) > .004)
        if len(active) < 100 or not np.isfinite(out).all() or len(out) < SAMPLE_RATE * .09:
            raise ValueError("The voice returned an empty or invalid utterance")
        start = max(0, active[0] - 1200)
        end = min(len(out), active[-1] + 1800)
        return out[start:end]
