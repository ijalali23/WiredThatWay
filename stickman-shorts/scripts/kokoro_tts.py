#!/usr/bin/env python3
"""Kokoro-82M TTS wrapper for the Stickman Animation Agent pipeline.

Reads a project's narration-script.json and synthesizes one WAV file per
scene via Kokoro. Invoked by src/pipeline/orchestrator.js's `voice` step:

    python scripts/kokoro_tts.py --script <project>/scripts/narration-script.json --output <project>/audio

Kokoro's KPipeline only splits input on `split_pattern` (default: newlines),
so handing it a whole multi-sentence scene as one string produces one
undifferentiated pass with no real pause control — comedic beats (an
ellipsis, an em dash, a punchline) get whatever pacing Kokoro infers from
punctuation alone, which is subtle. This wrapper instead splits each
scene's narration into clauses itself and stitches them with explicit,
punctuation-tuned silence, and maps each scene's `emotion` field to a
speed multiplier.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

SAMPLE_RATE = 24000
DEFAULT_VOICE = "af_heart"
DEFAULT_LANG_CODE = "a"  # American English, matches af_* / am_* voices

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

# Scene `emotion` -> Kokoro speed multiplier. Unrecognized/missing emotions
# fall back to 1.0. Values are deliberately mild — Kokoro's own prosody
# degrades if pushed too far from 1x.
EMOTION_SPEED = {
    "determined": 0.95,
    "excited": 1.08,
    "panicked": 1.15,
    "explaining": 0.92,
    "stunned": 0.95,
}

CLAUSE_SPLIT_RE = re.compile(r"(\.\.\.|--|—|[.!?])")


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def resolve_voice(script_path: Path) -> str:
    """Resolve the Kokoro voice for this project.

    Checks the project's own video-project.json config.voiceId first (a
    per-project override), then the template's default voice, then falls
    back to DEFAULT_VOICE — the voice step should never hard-fail just
    because of a missing config.
    """
    project_dir = script_path.parent.parent
    repo_root = Path(__file__).resolve().parent.parent

    try:
        project = load_json(project_dir / "video-project.json")
        config = project.get("config", {})
        if config.get("voiceId"):
            return config["voiceId"]
        template_name = config.get("template", "whiteboard")
        template = load_json(repo_root / "templates" / template_name / "template.json")
        return template.get("voice", {}).get("defaultVoice", DEFAULT_VOICE)
    except Exception:
        return DEFAULT_VOICE


def resolve_speed(emotion: str | None) -> float:
    if not emotion:
        return 1.0
    emotion = emotion.lower().strip()
    if emotion in EMOTION_SPEED:
        return EMOTION_SPEED[emotion]
    # Multi-word emotions like "smug then shocked" — match on any known word.
    for word, speed in EMOTION_SPEED.items():
        if word in emotion:
            return speed
    return 1.0


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
                # Keep the delimiter in the spoken clause — Kokoro reads
                # terminal punctuation for sentence-final intonation, the
                # explicit pause on top is purely for comedic timing.
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


SILENCE_THRESHOLD = 0.01  # fraction of full scale; audio is float32 in [-1, 1]
SILENCE_MARGIN_SEC = 0.03  # keep a small cushion so trimming doesn't clip attack/decay


def trim_silence(audio: np.ndarray) -> np.ndarray:
    """Strip Kokoro's own leading/trailing silence from one clause's audio.

    Each Kokoro call pads short utterances with ~0.6-0.9s of silence on its
    own — synthesizing a scene clause-by-clause means that padding would
    otherwise stack with our own explicit inter-clause pause at every
    boundary. Trimming here makes pause_after the only silence between
    clauses, so pacing is exactly what was asked for.
    """
    above = np.flatnonzero(np.abs(audio) > SILENCE_THRESHOLD)
    if above.size == 0:
        return audio
    margin = int(SILENCE_MARGIN_SEC * SAMPLE_RATE)
    start = max(0, above[0] - margin)
    end = min(len(audio), above[-1] + 1 + margin)
    return audio[start:end]


def synthesize_clause(pipeline, text: str, voice: str, speed: float) -> np.ndarray:
    # Kokoro yields torch tensors, not numpy arrays — normalize immediately
    # so every downstream consumer only ever deals with numpy.
    chunks = [
        np.asarray(audio.numpy() if hasattr(audio, "numpy") else audio, dtype=np.float32)
        for _graphemes, _phonemes, audio in pipeline(text, voice=voice, speed=speed)
    ]
    if not chunks:
        raise RuntimeError(f"Kokoro produced no audio for text: {text!r}")
    audio = np.concatenate(chunks) if len(chunks) > 1 else chunks[0]
    return trim_silence(audio)


def synthesize_scene(pipeline, text: str, voice: str, speed: float) -> np.ndarray:
    """Synthesize a scene clause-by-clause with explicit inter-clause pauses."""
    leading_pause, clauses = split_into_clauses(text)
    pieces = []
    if leading_pause > 0:
        pieces.append(np.zeros(int(leading_pause * SAMPLE_RATE), dtype=np.float32))
    for clause, pause_after in clauses:
        pieces.append(synthesize_clause(pipeline, clause, voice, speed))
        if pause_after > 0:
            pieces.append(np.zeros(int(pause_after * SAMPLE_RATE), dtype=np.float32))
    return np.concatenate(pieces)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate per-scene WAV narration via Kokoro-82M")
    parser.add_argument("--script", required=True, help="Path to narration-script.json")
    parser.add_argument("--output", required=True, help="Output directory for scene-NN.wav files")
    parser.add_argument("--voice", default=None, help="Override the Kokoro voice (default: read from project config / template)")
    args = parser.parse_args()

    script_path = Path(args.script).resolve()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    narration = load_json(script_path)
    scenes = narration.get("scenes", [])
    if not scenes:
        print("No scenes found in narration script.", file=sys.stderr)
        return 1

    voice = args.voice or resolve_voice(script_path)

    from kokoro import KPipeline

    print(f"[kokoro_tts] Loading Kokoro pipeline (lang={DEFAULT_LANG_CODE}, voice={voice})...")
    pipeline = KPipeline(lang_code=DEFAULT_LANG_CODE)

    for scene in scenes:
        scene_id = scene["id"]
        text = scene.get("narration", "").strip()
        if not text:
            print(f"[kokoro_tts] Scene {scene_id}: no narration text, skipping.")
            continue

        speed = resolve_speed(scene.get("emotion"))
        print(f"[kokoro_tts] Scene {scene_id}: synthesizing ({len(text)} chars, speed={speed})...")
        audio = synthesize_scene(pipeline, text, voice, speed)

        out_path = output_dir / f"scene-{scene_id}.wav"
        sf.write(str(out_path), audio, SAMPLE_RATE)
        duration = len(audio) / SAMPLE_RATE
        print(f"[kokoro_tts] Scene {scene_id}: wrote {out_path.name} ({duration:.2f}s)")

    print(f"[kokoro_tts] Done: {len(scenes)} scene(s) -> {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
