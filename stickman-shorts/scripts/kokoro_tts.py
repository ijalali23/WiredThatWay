#!/usr/bin/env python3
"""Kokoro-82M TTS wrapper for the Stickman Animation Agent pipeline.

Reads a project's narration-script.json and synthesizes one WAV file per
scene via Kokoro. Invoked by src/pipeline/orchestrator.js's `voice` step:

    python scripts/kokoro_tts.py --script <project>/scripts/narration-script.json --output <project>/audio

Kokoro's KPipeline only splits input on `split_pattern` (default: newlines),
so handing it a whole multi-sentence scene as one string produces one
undifferentiated pass with no real pause control — comedic beats (an
ellipsis, an em dash, a punchline) get whatever pacing Kokoro infers from
punctuation alone, which is subtle. See _tts_pacing.py for the clause
splitting and pause logic shared with xtts_tts.py.

Kokoro-82M is fast, free, and fully local, but architecturally has almost
no expressive range: its public API exposes only a `speed` multiplier, no
emotion/pitch/energy control, and each voice's style is a fixed vector
baked into its .pt file. For genuinely more expressive delivery, use
xtts_tts.py instead (config.voice = "xtts" in video-project.json).
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

from _tts_pacing import load_json, resolve_speed, synthesize_scene, trim_silence

SAMPLE_RATE = 24000
DEFAULT_VOICE = "af_heart"
DEFAULT_LANG_CODE = "a"  # American English, matches af_* / am_* voices

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
    return trim_silence(audio, SAMPLE_RATE)


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

        speed = resolve_speed(scene.get("emotion"), EMOTION_SPEED)
        print(f"[kokoro_tts] Scene {scene_id}: synthesizing ({len(text)} chars, speed={speed})...")
        audio = synthesize_scene(
            lambda clause: synthesize_clause(pipeline, clause, voice, speed),
            text,
            SAMPLE_RATE,
        )

        out_path = output_dir / f"scene-{scene_id}.wav"
        sf.write(str(out_path), audio, SAMPLE_RATE)
        duration = len(audio) / SAMPLE_RATE
        print(f"[kokoro_tts] Scene {scene_id}: wrote {out_path.name} ({duration:.2f}s)")

    print(f"[kokoro_tts] Done: {len(scenes)} scene(s) -> {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
