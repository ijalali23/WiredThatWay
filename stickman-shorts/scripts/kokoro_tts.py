#!/usr/bin/env python3
"""Kokoro-82M TTS wrapper for the Stickman Animation Agent pipeline.

Reads a project's narration-script.json and synthesizes one WAV file per
scene via Kokoro. Invoked by src/pipeline/orchestrator.js's `voice` step:

    python scripts/kokoro_tts.py --script <project>/scripts/narration-script.json --output <project>/audio
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

SAMPLE_RATE = 24000
DEFAULT_VOICE = "af_heart"
DEFAULT_LANG_CODE = "a"  # American English, matches af_* / am_* voices


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def resolve_voice(script_path: Path) -> str:
    """Read the project's template config for the default Kokoro voice.

    Falls back to DEFAULT_VOICE if the project or template can't be found —
    the voice step should never hard-fail just because of a missing config.
    """
    project_dir = script_path.parent.parent
    repo_root = Path(__file__).resolve().parent.parent

    try:
        project = load_json(project_dir / "video-project.json")
        template_name = project.get("config", {}).get("template", "whiteboard")
        template = load_json(repo_root / "templates" / template_name / "template.json")
        return template.get("voice", {}).get("defaultVoice", DEFAULT_VOICE)
    except Exception:
        return DEFAULT_VOICE


def synthesize_scene(pipeline, text: str, voice: str) -> np.ndarray:
    """Run Kokoro over one scene's narration text and concatenate all chunks.

    Kokoro's pipeline yields one chunk per internal sentence split; scenes
    with multiple sentences need every chunk stitched back into one clip.
    """
    chunks = [audio for _graphemes, _phonemes, audio in pipeline(text, voice=voice)]
    if not chunks:
        raise RuntimeError(f"Kokoro produced no audio for text: {text!r}")
    return np.concatenate(chunks) if len(chunks) > 1 else chunks[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate per-scene WAV narration via Kokoro-82M")
    parser.add_argument("--script", required=True, help="Path to narration-script.json")
    parser.add_argument("--output", required=True, help="Output directory for scene-NN.wav files")
    parser.add_argument("--voice", default=None, help="Override the Kokoro voice (default: read from template)")
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

        print(f"[kokoro_tts] Scene {scene_id}: synthesizing ({len(text)} chars)...")
        audio = synthesize_scene(pipeline, text, voice)

        out_path = output_dir / f"scene-{scene_id}.wav"
        sf.write(str(out_path), audio, SAMPLE_RATE)
        duration = len(audio) / SAMPLE_RATE
        print(f"[kokoro_tts] Scene {scene_id}: wrote {out_path.name} ({duration:.2f}s)")

    print(f"[kokoro_tts] Done: {len(scenes)} scene(s) -> {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
