"""Resolve speaker aliases, assign distinct voices, and describe the cast."""
from collections import Counter
import math

from .casting import DEEP_NARRATOR, KOKORO_CAST, PERSONAS, Voice

MALE_VOICES = ("am_michael", "am_fenrir", "am_onyx", "am_echo", "am_eric",
               "am_liam", "am_adam", "am_puck", "am_santa")
FEMALE_VOICES = ("af_heart", "af_sarah", "af_bella", "af_nova", "af_alloy",
                 "af_jessica", "af_kore", "af_river", "af_aoede", "af_nicole", "af_sky")
VOICE_IDS = frozenset(MALE_VOICES + FEMALE_VOICES)


def key(name):
    return name.strip().casefold()


def cast_names(cast):
    names = {"narrator": "narrator"}
    for speaker, profile in cast.items():
        for alias in [speaker, *profile.get("aliases", [])]:
            normalized = key(alias)
            previous = names.setdefault(normalized, speaker)
            if previous != speaker:
                raise ValueError(f"Speaker alias {alias!r} is shared by {previous!r} and {speaker!r}")
    return names


def preferred_voice(profile):
    if chosen := profile.get("kokoro_voice"):
        return Voice(chosen, float(profile.get("pitch_semitones", 0)))
    if persona := profile.get("persona"):
        if persona not in PERSONAS:
            raise ValueError(f"Unknown voice persona {persona!r}")
        preferred = PERSONAS[persona]
    else:
        preferred = KOKORO_CAST.get((profile.get("gender"), profile.get("age")), Voice("am_michael"))
    return Voice(preferred.name, float(profile.get("pitch_semitones", preferred.semitones)))


def next_voice(preferred, profile, occupied):
    if preferred.name not in {voice.name for voice in occupied}:
        return preferred
    if profile.get("gender") == "female" or preferred.name.startswith("af_"):
        pool = FEMALE_VOICES
    elif profile.get("gender") == "male" or profile.get("persona"):
        pool = MALE_VOICES
    else:
        pool = MALE_VOICES + FEMALE_VOICES
    used_ids = {voice.name for voice in occupied}
    for voice in pool:
        if voice not in used_ids:
            return Voice(voice, preferred.semitones)
    # Distinct pitch styles expand the cast if every suitable base voice is in use.
    for delta in (0, 1.5, -1.5, 3, -3, 4.5, -4.5):
        pitch = preferred.semitones + delta
        if abs(pitch) > 6:
            continue
        for voice in pool:
            if all(v.name != voice or abs(v.semitones - pitch) >= 1.25 for v in occupied):
                return Voice(voice, pitch)
    raise ValueError("Too many speaking roles for distinct voices. Use a smaller cast per render.")


def plan_cast(book):
    cast = book.get("cast", {})
    names = cast_names(cast)
    counts = Counter()
    for chapter in book["chapters"]:
        for line in chapter["lines"]:
            raw = line.get("speaker", "narrator")
            speaker = names.get(key(raw), key(raw))
            if speaker != "narrator" and speaker not in cast:
                raise ValueError(f"Add {raw!r} to the cast or mark its lines as narration.")
            line["speaker"] = speaker
            counts[speaker] += 1
    preferred = {}
    fixed = {}
    for speaker in counts:
        profile = cast.get(speaker, {})
        if speaker == "narrator":
            choice = book.get("narrator", "deep-narrator")
            voice = PERSONAS.get(choice, Voice(choice))
        else:
            voice = preferred_voice(profile)
        if voice.name not in VOICE_IDS or not math.isfinite(voice.semitones) or abs(voice.semitones) > 6:
            raise ValueError(f"Invalid voice or pitch for {speaker!r}: {voice}")
        preferred[speaker] = voice
        if speaker == "narrator" or profile.get("kokoro_voice"):
            if voice in fixed.values():
                raise ValueError(f"{speaker!r} has the same voice and pitch as another locked role. Choose a distinct profile.")
            fixed[speaker] = voice
    chosen = dict(fixed)
    # Preserve every unclaimed first choice before assigning collision alternatives.
    for speaker, voice in preferred.items():
        if speaker not in chosen and voice.name not in {v.name for v in chosen.values()}:
            chosen[speaker] = voice
    for speaker, voice in preferred.items():
        if speaker not in chosen:
            chosen[speaker] = next_voice(voice, cast.get(speaker, {}), chosen.values())
    report = []
    for speaker, count in counts.items():
        profile = cast.get(speaker, {})
        voice = chosen[speaker]
        persona = next((name for name, setting in PERSONAS.items() if setting == voice), None)
        report.append({"speaker": profile.get("display_name", speaker), "speaker_id": speaker,
                       "description": profile.get("description", ""),
                       "age": profile.get("age"), "gender": profile.get("gender"),
                       "persona": persona, "voice_id": voice.name, "pitch_semitones": voice.semitones,
                       "alternate": voice != preferred[speaker], "passages": count})
    return chosen, report
