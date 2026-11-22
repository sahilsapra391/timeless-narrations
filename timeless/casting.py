"""Speaker-aware Kokoro casting for the multi-voice renderer (GPL-3.0)."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Voice:
    name: str
    semitones: float = 0.0


# Synthetic voices performing roles. Age describes the character in the book.
KOKORO_CAST = {
    ('female', 'child'): Voice('af_sky', 1.0),
    ('male', 'child'): Voice('am_puck', 1.5),
    ('female', 'adult'): Voice('af_heart'),
    ('male', 'adult'): Voice('am_michael'),
    ('female', 'elderly'): Voice('af_sarah', -0.75),
    ('male', 'elderly'): Voice('am_onyx', -0.75),
}
DEEP_NARRATOR = Voice('am_puck', -2)
QUOTED = re.compile(r'("[^"]+"|“[^”]+”)')


def assign_voice(speaker, profiles, engine, narrator_gender, fallback):
    """Use age and gender when available; keep legacy engine and score maps."""
    key = speaker.strip().lower()
    if engine.lower() == 'kokoro':
        if key == 'narrator' and narrator_gender.lower() == 'male':
            return DEEP_NARRATOR
        if key != 'narrator':
            info = profiles.get('scores', {}).get(key, {})
            override = info.get('kokoro_voice')
            if override:
                return Voice(override, float(info.get('pitch_semitones', 0)))
            cast = KOKORO_CAST.get((info.get('gender'), info.get('age')))
            if cast:
                return cast
    return Voice(fallback(key, profiles, engine, narrator_gender))


def spoken_parts(row, narrator, character):
    """Keep reported speech tags with the narrator and utterances with the speaker."""
    line = row['line'].strip()
    role = row.get('kind')
    if role == 'narration' or row['speaker'].strip().lower() == 'narrator':
        return [(line, narrator)]
    if role == 'dialogue' or not QUOTED.search(line):
        return [(line, character)]
    return [(part, character if QUOTED.fullmatch(part) else narrator)
            for part in QUOTED.split(line) if part.strip()]


def kokoro_pronunciation(text):
    # Kokoro can return silence for the out-of-vocabulary spelling "Hmmm".
    return re.sub(r'\b([Hh])m{3,}\b', r'\1mm', text)
