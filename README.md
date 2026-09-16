# wired-that-way

**Wired That Way** — a faceless-shorts channel on the neuroscience behind everyday behavior,
built on the faceless-shorts factory pipeline (originally from
[claude-faceless-shorts-creator](https://github.com/hassancs91/claude-faceless-shorts-creator),
MIT licensed) driven with [Claude Code](https://claude.com/claude-code).

**A faceless YouTube-Shorts factory you drive with [Claude Code](https://claude.com/claude-code).**
Four production tracks in one repo — you just describe the video, and the right pipeline runs:

| You say… | Track | The pixels |
|---|---|---|
| *"make a short about the ×11 trick"* | **TSX** (`/make-short`) | 100% code — a [Remotion](https://remotion.dev) composition, no footage, no stock |
| *"make an AI video short with blue-man"* | **Generative** (`/make-ai-short`) | a fal video model animating a **locked recurring character** |
| *"make a vox-style short about coffee"* | **Collage** (`/make-vox`) | Vox-documentary paper collage — AI-image layers, die-cuts, a traveling camera |
| *"make a stickman animation about procrastination"* | **Stickman** (`/stickman-animation`) | deterministic SVG/GSAP compositor ([HyperFrames](https://github.com/chrisaswain/stickman-animation-agent)), no video model |

Every track shares the same backbone: ElevenLabs voice with **word-exact synced captions**,
frame-by-frame QA at phone scale, a reusable self-growing SFX/music library, seamless
frame-0==last-frame loops, and no dated engagement-CTA outros.

## 📖 Read the guide

I wrote up the whole system on my site, including the six-beat grammar that decides whether a
40-second short is worth finishing:
**[Make Faceless YouTube Shorts With Claude Code](https://learnwithhasan.com/guide/how-to-make-faceless-youtube-shorts-with-claude-code/?utm_source=github&utm_medium=readme&utm_campaign=claude-faceless-shorts-creator&utm_content=body)**

Free to read, no login. More build guides at
**[learnwithhasan.com/guides](https://learnwithhasan.com/guides/?utm_source=github&utm_medium=readme&utm_campaign=claude-faceless-shorts-creator&utm_content=body)**.

## This channel

**Wired That Way** covers the neuroscience behind everyday behavior — built from real people
actually talking about it (researchers, clinicians, podcasters), turned into short-form video.
This repo starts from the faceless-shorts engine (the tracks below still work exactly as
documented) but ships with no example videos yet — `shorts/`, `ai-shorts/`, `vox-shorts/`, and
`stickman-shorts/projects/` are empty until the first episode is produced here. See
`publishing/registry.json` for the posting history once episodes start going out.

## The fourth track: stickman-shorts

`stickman-shorts/` is a separate, self-contained pipeline vendored from
[chrisaswain/stickman-animation-agent](https://github.com/chrisaswain/stickman-animation-agent):
topic → script → characters → voice → timestamps → storyboard → compose → enhance → render →
publish, with pixel-perfect recurring SVG characters rendered via headless Chrome (HyperFrames)
instead of a video model. It has its own Node.js/Python toolchain, its own `.claude/skills/`
(discovered by Claude Code as directory-scoped skills, e.g. `stickman-shorts:stickman-animation`),
and does not share `tools/`, `media/`, or `remotion/` with the three tracks above. See
`stickman-shorts/README.md` and `stickman-shorts/CLAUDE.md` for setup (`bootstrap.ps1` needs a
Linux/macOS equivalent — see its requirements) and usage.

## How a short gets made

```
topic ──▶ script.md + beats.json      the beat grammar: HOOK (frame 0 = the thumbnail)
                │                      → SETUP → QUIZ → REVEAL → TWIST → seamless LOOP
                ▼
        the visuals                    TSX composition / video-model clips / collage layers
                │                      (per track — but always ONE Remotion timeline)
                ▼
        frame-by-frame QA              Claude renders PNGs at phone scale and READS them
                │
                ▼
        gen_voice.py                   ElevenLabs TTS per line → REAL per-word timestamps
                │                      → captions highlight on the exact spoken word
                ▼
        sfx-plan.json + mix_sfx.py     library-first sound design, audition mix, your ear
                │                      is the final gate (optional music bed: mix_music.py)
                ▼
        <track>/<project>/output/*-sfx.mp4
```

Five Claude Code **skills** encode the craft:

- **`/make-short`** — the TSX pipeline: hook grammar, no-CTA outros, caption safe areas,
  Sequence-local frame math, loop-into-intro endings.
- **`/make-ai-short`** — the generative pipeline and its three iron rules: never regenerate a
  locked character from text, state the cost before spending it, loop by end-frame constraint.
- **`/make-vox`** — scene dissection into layers, cheapest-source layer production
  (gen_image + rembg cutouts, HTML→PNG, SVG-in-TSX), CollageBoard camera choreography.
- **`/vidtsx-2d-generator`** — the TSX authoring rules that keep Remotion renders from crashing.
- **`/suggest-sfx`** — taste-encoded sound design: function-first cues, layered hero moments,
  measured audibility (RMS-diff, not hope), a library that compounds across videos.

`brand.md` is the style contract (palette, type, motion, SFX taste) — swap it for your own
brand and every future short follows it.

## Quickstart

Requirements: [Claude Code](https://claude.com/claude-code) · Node 18+ · Python 3.10+ ·
`ffmpeg` on PATH · an [ElevenLabs](https://elevenlabs.io) key (voice/SFX/music). For the
generative track add a [fal.ai](https://fal.ai) key; for collage layer production:
`pip install pillow rembg playwright && playwright install chromium` (the only pip installs
in the repo — everything else is stdlib).

```bash
git clone https://github.com/hassancs91/claude-faceless-shorts-creator
cd claude-faceless-shorts-creator
cp .env.example .env          # add your keys
cd remotion && npm install && npm run gen && cd ..

claude                        # open the repo in Claude Code, then:
```

> **make a short about &lt;your topic&gt;** · **make an AI video short about &lt;idea&gt;** ·
> **make a vox-style short about &lt;story&gt;**

…or rebuild an example: *"re-render short-5 and regenerate its voice"*.

To just explore the compositions visually: `cd remotion && npm run studio`.

## Repo layout

```
.claude/skills/   the six TSX/collage/generative skills (this is where the "editor" lives)
tools/            Python: gen_voice, gen_sfx, gen_music, mix_sfx, mix_music, gen_image,
                  gen_clip, bakeoff_clip, cutout, capture_web, gen_chords
remotion/         the Remotion project — shared kits in src/lib/ (incl. collage.tsx),
                  one folder per video in src/shots/
media/library/    reusable assets: SFX clips + music beds (catalogued, loudness-normalized)
media/projects/   media for one specific video — incl. committed AI clips & collage layers
shorts/           the TSX track — empty until the first episode is produced here
ai-shorts/        the generative track: IDEAS.md (cost tables) — empty until the first episode
vox-shorts/       the collage track: DESIGN.md (the visual language) — empty until the first episode
stickman-shorts/  the fourth track (self-contained, own toolchain) — see its own README/CLAUDE.md
brand.md          the style contract — make it yours
IDEAS.md          the TSX-shorts niche/idea bank
```

## License

MIT — see [LICENSE](LICENSE). Bundled SFX/music clips and example AI media were generated by
the repo author (ElevenLabs / fal / Gemini) and are redistributed here; per-clip provenance is
recorded in `media/library/*/catalog.json` and the per-shot `.json` sidecars.

<!-- lwh-footer -->

---

## 📘 The free book

This repo is one thing I built with AI. The book is the system underneath it.

**[Vibe Engineering Blocks](https://learnwithhasan.com/blocks/?utm_source=github&utm_medium=readme&utm_campaign=claude-faceless-shorts-creator&utm_content=footer)** is my free 74-page book.
47 building blocks for shipping real apps with AI. One block per page, each with the exact
prompt to hand your AI.

Built by **[Hasan Aboul Hasan](https://learnwithhasan.com/?utm_source=github&utm_medium=readme&utm_campaign=claude-faceless-shorts-creator&utm_content=footer)**. I build real products with AI and
write down exactly how.
[Guides](https://learnwithhasan.com/guides/?utm_source=github&utm_medium=readme&utm_campaign=claude-faceless-shorts-creator&utm_content=footer) &nbsp;·&nbsp;
[YouTube](https://www.youtube.com/@HasanAboulHasan) &nbsp;·&nbsp;
[Community](https://learnwithhasan.com/community/?utm_source=github&utm_medium=readme&utm_campaign=claude-faceless-shorts-creator&utm_content=footer)
