"""Shared clause-splitting, pause, and silence-trimming logic for TTS wrappers.

Used by both kokoro_tts.py and xtts_tts.py. Neither engine's own sentence
splitter produces comedically-tuned pacing on its own: Kokoro synthesizes a
whole multi-sentence scene as one undifferentiated pass unless split on
newlines, and XTTS's default sentence splitter inserts a uniform ~0.5s gap
at every boundary regardless of punctuation. Both need the same fix — split
narration into clauses ourselves and stitch them with explicit,
punctuation-tuned silence.
"""

import json
import re
from pathlib import Path

import numpy as np

# Clause boundary -> silence duration (seconds). Longer, more deliberate
# punctuation gets a longer beat; checked longest-match-first.
PAUSE_DURATIONS = [
    ("...", 0.45),
    ("--", 0.40),
    ("—", 0.40),
    ("!", 0.22),
    ("?", 0.22),
    (".", 0.18),
]

CLAUSE_SPLIT_RE = re.compile(r"(\.\.\.|--|—|[.!?])")

SILENCE_THRESHOLD = 0.01  # fraction of full scale; audio is float32 in [-1, 1]
SILENCE_MARGIN_SEC = 0.03  # keep a small cushion so trimming doesn't clip attack/decay


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def split_into_clauses(text: str) -> tuple[float, list[tuple[str, float]]]:
    """Split narration into a leading pause plus (clause, pause_after) pairs.

    Each clause keeps its terminating punctuation; pause_after is how much
    silence to insert before the next clause, chosen from PAUSE_DURATIONS
    by the punctuation that ended this clause. A delimiter with nothing
    before it yet (e.g. a leading "..." as in "...Wait, why—") has no
    clause of its own — its pause folds into the gap before whatever
    clause comes next (or the scene's leading pause, if it comes first).
    The final clause gets no trailing pause (inter-scene silence handles that).
    """
    parts = CLAUSE_SPLIT_RE.split(text)
    clauses: list[tuple[str, float]] = []
    buffer = ""
    leading_pause = 0.0

    for part in parts:
        if not part:
            continue
        is_delimiter = any(part == p for p, _ in PAUSE_DURATIONS)
        if is_delimiter:
            pause = next(d for p, d in PAUSE_DURATIONS if p == part)
            if buffer.strip():
                # Keep the delimiter in the spoken clause — most TTS engines
                # read terminal punctuation for sentence-final intonation;
                # the explicit pause on top is purely for comedic timing.
                clauses.append(((buffer + part).strip(), pause))
            elif clauses:
                prev_clause, prev_pause = clauses[-1]
                clauses[-1] = (prev_clause, prev_pause + pause)
            else:
                leading_pause += pause
            buffer = ""
        else:
            buffer += part

    tail = buffer.strip()
    if tail:
        clauses.append((tail, 0.0))

    if clauses:
        clauses[-1] = (clauses[-1][0], 0.0)
    else:
        clauses = [(text, 0.0)]

    return leading_pause, clauses


def trim_silence(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """Strip an engine's own leading/trailing silence from one clause's audio.

    Synthesizing a scene clause-by-clause means each engine's own inherent
    per-call padding would otherwise stack with our explicit inter-clause
    pause at every boundary. Trimming here makes pause_after the only
    silence between clauses, so pacing is exactly what was asked for.
    """
    above = np.flatnonzero(np.abs(audio) > SILENCE_THRESHOLD)
    if above.size == 0:
        return audio
    margin = int(SILENCE_MARGIN_SEC * sample_rate)
    start = max(0, above[0] - margin)
    end = min(len(audio), above[-1] + 1 + margin)
    return audio[start:end]


def resolve_speed(emotion: str | None, emotion_speed: dict[str, float]) -> float:
    if not emotion:
        return 1.0
    emotion = emotion.lower().strip()
    if emotion in emotion_speed:
        return emotion_speed[emotion]
    # Multi-word emotions like "smug then shocked" — match on any known word.
    for word, speed in emotion_speed.items():
        if word in emotion:
            return speed
    return 1.0


def synthesize_scene(synthesize_clause, text: str, sample_rate: int) -> np.ndarray:
    """Synthesize a scene clause-by-clause with explicit inter-clause pauses.

    `synthesize_clause` is a callable taking one clause's text and returning
    its (already engine-trimmed) numpy audio — the caller supplies it bound
    to whichever engine, voice, and speed are in play.
    """
    leading_pause, clauses = split_into_clauses(text)
    pieces = []
    if leading_pause > 0:
        pieces.append(np.zeros(int(leading_pause * sample_rate), dtype=np.float32))
    for clause, pause_after in clauses:
        pieces.append(synthesize_clause(clause))
        if pause_after > 0:
            pieces.append(np.zeros(int(pause_after * sample_rate), dtype=np.float32))
    return np.concatenate(pieces)
