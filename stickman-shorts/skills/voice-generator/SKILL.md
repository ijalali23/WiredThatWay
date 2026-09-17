# Voice Generator

Generate per-scene WAV audio files from the narration script using the selected TTS engine.

## Input

- `video-project.json` — selected voice engine
- `narration-script.json` — scene narration text

## Engine Hierarchy

| Engine | Quality | Speed | Cost | Local? | Script |
|---|---|---|---|---|---|
| **Kokoro-82M** (default) | Flat/limited range — only a speed control | Realtime | Free | Yes | `scripts/kokoro_tts.py` |
| **Coqui XTTS v2** | Wider pitch/energy range (verified: ~138Hz pitch range vs Kokoro's ~95Hz on the same line) | ~2x realtime | Free, non-commercial CPML unless you hold a Coqui commercial license | Yes | `scripts/xtts_tts.py` (`requirements-xtts.txt`) |
| **Gemini TTS** | Good | Fast | Free (quota) | No | `mcp__gemini-media__generate_audio` |
| **ElevenLabs V3** | Best | Fast | Freemium | No | ElevenLabs API |

Set the engine via `config.voice` in `video-project.json` (`"kokoro"` or `"xtts"`) — `src/pipeline/orchestrator.js`'s `voice` step picks the matching script automatically. Pick the specific voice/speaker with `config.voiceId`.

## Process

1. For each scene, extract narration text
2. Generate WAV using selected engine — both `kokoro_tts.py` and `xtts_tts.py` split narration into clauses themselves and stitch them with explicit, punctuation-tuned silence (`scripts/_tts_pacing.py`); neither engine's own sentence splitter produces comedically-timed pauses on its own
3. Save to `projects/{slug}/audio/scene-{NN}.wav`
4. Validate audio file exists and has non-zero duration

## Output

- `projects/{slug}/audio/scene-01.wav` through `scene-NN.wav`
- Updates `video-project.json` step status
