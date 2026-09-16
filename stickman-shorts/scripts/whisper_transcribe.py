#!/usr/bin/env python3
"""faster-whisper word-timestamp extraction for the Stickman Animation Agent pipeline.

Reads a project's audio/scene-*.wav files and writes word-level timestamp
JSON per scene, matching skills/transcriber/SKILL.md's documented schema.
Invoked by src/pipeline/orchestrator.js's `timestamps` step:

    python scripts/whisper_transcribe.py --audio-dir <project>/audio --output <project>/timestamps
"""

import argparse
import json
import re
import sys
from pathlib import Path

from faster_whisper import WhisperModel

SCENE_WAV_PATTERN = re.compile(r"^scene-(\d{2,3})\.wav$")
DEFAULT_MODEL = "base.en"


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract word-level timestamps via faster-whisper")
    parser.add_argument("--audio-dir", required=True, help="Directory containing scene-NN.wav files")
    parser.add_argument("--output", required=True, help="Output directory for scene-NN.json timestamp files")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"faster-whisper model size (default: {DEFAULT_MODEL})")
    args = parser.parse_args()

    audio_dir = Path(args.audio_dir).resolve()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    wav_files = sorted(
        (f for f in audio_dir.iterdir() if SCENE_WAV_PATTERN.match(f.name)),
        key=lambda f: f.name,
    )
    if not wav_files:
        print(f"No scene-NN.wav files found in {audio_dir}", file=sys.stderr)
        return 1

    print(f"[whisper_transcribe] Loading faster-whisper model '{args.model}' (CPU, int8)...")
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    for wav_path in wav_files:
        scene_id = SCENE_WAV_PATTERN.match(wav_path.name).group(1)
        print(f"[whisper_transcribe] Scene {scene_id}: transcribing {wav_path.name}...")

        segments, info = model.transcribe(str(wav_path), word_timestamps=True)

        words = []
        for segment in segments:
            for word in segment.words:
                words.append({
                    "word": word.word.strip(),
                    "start": round(word.start, 3),
                    "end": round(word.end, 3),
                })

        result = {
            "sceneId": scene_id,
            "duration": round(info.duration, 3),
            "words": words,
        }

        out_path = output_dir / f"scene-{scene_id}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")

        print(f"[whisper_transcribe] Scene {scene_id}: wrote {out_path.name} ({len(words)} words)")

    print(f"[whisper_transcribe] Done: {len(wav_files)} scene(s) -> {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
