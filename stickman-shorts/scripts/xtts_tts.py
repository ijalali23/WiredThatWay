#!/usr/bin/env python3
"""Coqui XTTS v2 wrapper for the Stickman Animation Agent pipeline.

Reads a project's narration-script.json and synthesizes one WAV file per
scene via XTTS v2. Same CLI contract as kokoro_tts.py:

    python scripts/xtts_tts.py --script <project>/scripts/narration-script.json --output <project>/audio

Used instead of kokoro_tts.py when config.voice == "xtts" in
video-project.json. XTTS v2 is a much larger autoregressive model than
Kokoro-82M — measurably wider pitch and energy range (checked directly:
~35Hz pitch stdev vs Kokoro's ~20Hz on the same line), at the cost of being
slower (roughly 2x realtime on CPU, no GPU needed but much faster with one)
and requiring acceptance of Coqui's non-commercial CPML license (or a paid
commercial license) to download the model — see COQUI_TOS_AGREED below.

Like Kokoro, XTTS's own default sentence splitting produces flat, uniform
~0.5s gaps between every sentence regardless of punctuation — it is not
comedically aware either. See _tts_pacing.py for the clause splitting and
pause logic shared with kokoro_tts.py.
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

from _tts_pacing import load_json, resolve_speed, synthesize_scene, trim_silence

SAMPLE_RATE = 24000
DEFAULT_SPEAKER = "Andrew Chipper"  # one of XTTS v2's 58 built-in speakers
DEFAULT_LANGUAGE = "en"
MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"

# Scene `emotion` -> XTTS speed multiplier. XTTS's own baseline pace is
# noticeably more deliberate than Kokoro's, so these lean faster across the
# board rather than reusing Kokoro's multipliers verbatim.
EMOTION_SPEED = {
    "determined": 1.05,
    "excited": 1.25,
    "panicked": 1.35,
    "explaining": 1.0,
    "stunned": 1.05,
}


def resolve_speaker(script_path: Path) -> str:
    """Resolve the XTTS speaker for this project.

    Checks the project's own video-project.json config.voiceId first (a
    per-project override), falling back to DEFAULT_SPEAKER — the voice step
    should never hard-fail just because of a missing config.
    """
    project_dir = script_path.parent.parent
    try:
        project = load_json(project_dir / "video-project.json")
        voice_id = project.get("config", {}).get("voiceId")
        if voice_id:
            return voice_id
    except Exception:
        pass
    return DEFAULT_SPEAKER


def synthesize_clause(tts, text: str, speaker: str, language: str, speed: float) -> np.ndarray:
    wav = tts.tts(text=text, speaker=speaker, language=language, speed=speed)
    audio = np.asarray(wav, dtype=np.float32)
    return trim_silence(audio, SAMPLE_RATE)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate per-scene WAV narration via Coqui XTTS v2")
    parser.add_argument("--script", required=True, help="Path to narration-script.json")
    parser.add_argument("--output", required=True, help="Output directory for scene-NN.wav files")
    parser.add_argument("--speaker", default=None, help="Override the XTTS speaker (default: read from project config)")
    parser.add_argument("--language", default=DEFAULT_LANGUAGE, help=f"XTTS language code (default: {DEFAULT_LANGUAGE})")
    args = parser.parse_args()

    script_path = Path(args.script).resolve()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    narration = load_json(script_path)
    scenes = narration.get("scenes", [])
    if not scenes:
        print("No scenes found in narration script.", file=sys.stderr)
        return 1

    speaker = args.speaker or resolve_speaker(script_path)

    # XTTS ships under Coqui's non-commercial CPML unless you hold a
    # commercial license (licensing@coqui.ai) — this only skips the
    # interactive confirmation prompt, it does not itself grant a license.
    os.environ.setdefault("COQUI_TOS_AGREED", "1")
    from TTS.api import TTS

    print(f"[xtts_tts] Loading XTTS v2 (speaker={speaker}, language={args.language})...")
    tts = TTS(MODEL_NAME)

    for scene in scenes:
        scene_id = scene["id"]
        text = scene.get("narration", "").strip()
        if not text:
            print(f"[xtts_tts] Scene {scene_id}: no narration text, skipping.")
            continue

        speed = resolve_speed(scene.get("emotion"), EMOTION_SPEED)
        print(f"[xtts_tts] Scene {scene_id}: synthesizing ({len(text)} chars, speed={speed})...")
        audio = synthesize_scene(
            lambda clause: synthesize_clause(tts, clause, speaker, args.language, speed),
            text,
            SAMPLE_RATE,
        )

        out_path = output_dir / f"scene-{scene_id}.wav"
        sf.write(str(out_path), audio, SAMPLE_RATE)
        duration = len(audio) / SAMPLE_RATE
        print(f"[xtts_tts] Scene {scene_id}: wrote {out_path.name} ({duration:.2f}s)")

    print(f"[xtts_tts] Done: {len(scenes)} scene(s) -> {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
