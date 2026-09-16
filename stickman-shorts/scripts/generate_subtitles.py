#!/usr/bin/env python3
"""SRT subtitle generation for the Stickman Animation Agent pipeline.

Reads a project's timestamps/scene-*.json files (word-level timestamps from
whisper_transcribe.py) and writes one combined SRT file, offsetting each
scene's word times by the same cumulative-duration-plus-inter-scene-silence
math src/render/pipeline.js uses to concatenate the scene audio/video, so
subtitles land on the correct frame of the final assembled video.

Invoked by src/pipeline/orchestrator.js's `publish` step:

    python scripts/generate_subtitles.py --timestamps-dir <project>/timestamps --output <project>/output/<slug>.srt --pause 0.5
"""

import argparse
import json
import re
import sys
from pathlib import Path

SCENE_JSON_PATTERN = re.compile(r"^scene-(\d{2,3})\.json$")
MAX_CUE_CHARS = 42
MAX_CUE_DURATION = 4.5
SENTENCE_END = re.compile(r"[.!?]$")


def format_timestamp(seconds: float) -> str:
    total_ms = round(seconds * 1000)
    hours, rem_ms = divmod(total_ms, 3_600_000)
    minutes, rem_ms = divmod(rem_ms, 60_000)
    secs, ms = divmod(rem_ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def group_words_into_cues(words: list[dict]) -> list[dict]:
    """Greedily group words into readable subtitle cues.

    Breaks a cue when adding the next word would exceed MAX_CUE_CHARS or
    MAX_CUE_DURATION, or right after a word ending a sentence — whichever
    comes first — so cues stay short and land on natural phrase boundaries.
    """
    cues = []
    current: list[dict] = []

    def flush():
        if not current:
            return
        text = " ".join(w["word"] for w in current)
        cues.append({"start": current[0]["start"], "end": current[-1]["end"], "text": text})
        current.clear()

    for word in words:
        candidate_text = " ".join(w["word"] for w in current + [word])
        candidate_duration = word["end"] - current[0]["start"] if current else 0

        if current and (len(candidate_text) > MAX_CUE_CHARS or candidate_duration > MAX_CUE_DURATION):
            flush()

        current.append(word)

        if SENTENCE_END.search(word["word"]):
            flush()

    flush()
    return cues


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a combined SRT from per-scene word timestamps")
    parser.add_argument("--timestamps-dir", required=True, help="Directory containing scene-NN.json timestamp files")
    parser.add_argument("--output", required=True, help="Output .srt file path")
    parser.add_argument("--pause", type=float, default=0.5, help="Inter-scene silence in seconds (must match the render pipeline's value)")
    args = parser.parse_args()

    timestamps_dir = Path(args.timestamps_dir).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scene_files = sorted(
        (f for f in timestamps_dir.iterdir() if SCENE_JSON_PATTERN.match(f.name)),
        key=lambda f: f.name,
    )
    if not scene_files:
        print(f"No scene-NN.json timestamp files found in {timestamps_dir}", file=sys.stderr)
        return 1

    all_cues = []
    cumulative_offset = 0.0

    for scene_file in scene_files:
        with scene_file.open("r", encoding="utf-8") as f:
            scene = json.load(f)

        for cue in group_words_into_cues(scene.get("words", [])):
            all_cues.append({
                "start": cue["start"] + cumulative_offset,
                "end": cue["end"] + cumulative_offset,
                "text": cue["text"],
            })

        cumulative_offset += scene.get("duration", 0.0) + args.pause

    with output_path.open("w", encoding="utf-8") as f:
        for i, cue in enumerate(all_cues, start=1):
            f.write(f"{i}\n")
            f.write(f"{format_timestamp(cue['start'])} --> {format_timestamp(cue['end'])}\n")
            f.write(f"{cue['text']}\n\n")

    print(f"[generate_subtitles] Wrote {len(all_cues)} cue(s) from {len(scene_files)} scene(s) -> {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
