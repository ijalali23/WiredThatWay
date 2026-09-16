# GoogleFlow Gen — standing lessons (read before building the next video)

This is the process notes file for the AI-generated-visuals pipeline ("GoogleFlow Gen" —
16-phase VOX-STYLE documentary framework, visuals made in Google Flow, voiceover + final
stitch done in this repo). First run: `googleflow-1-earthrise` (Apollo 8 Earthrise story),
2026-09-13. Read this before starting the next one.

## The mistake (EP01/Earthrise) — root cause and fix

**What happened:** the still-image prompts (Phase 7/8) correctly specified "no humans, no
animals" and the generated STILL images were clean. But 6 of the 14 ANIMATED clips introduced
human figures partway through the 6-second clip that were never in the source still or the
image prompt — a hand entering to hold tape/a pen, a camera move/cross-dissolve revealing a
background photo of people, an astronaut-in-spacesuit photo appearing as the "camera" pulled
back. All of this happened AFTER the first 1-3 seconds, so a quick look at each clip's first
frame or a thumbnail did not catch it — full-duration frame sampling (not just t=0) is what
caught it.

**Root cause:** the image-generation prompt's negative instructions ("no humans, no animals")
were never repeated in the Phase 9 UNIVERSAL ANIMATION PROMPT. The animation/video-generation
step is a separate model call from the still-image generation, and it does not automatically
inherit the still image's own negative constraints — left alone, it can invent new elements
during the "motion" it synthesizes (a hand, a revealed background, an extra photo) that were
never in the source frame or its prompt.

**Fix for every future GoogleFlow video — two changes, both mandatory:**

1. **Repeat the full negative-instruction list inside the animation prompt itself**, not just
   the still-image prompt. Every animation-prompt call (Phase 9's universal prompt, or any
   per-beat variant) must explicitly state: "Do not introduce any new object, person, animal,
   hand, face, or background element that is not already visible in the source still image.
   No humans or animals may enter frame at any point during the clip, including via camera
   movement, cross-dissolve, parallax reveal, or background focus pull." Treat this as a
   persistent constraint carried through the ENTIRE generation, not a one-time image property.
2. **QC every clip across its FULL duration before trusting it**, not just the first frame.
   Sample at minimum 6 evenly-spaced timestamps across the whole clip length. A clip that's
   compliant at t=0 is not evidence the clip is compliant at t=3s or t=5s — several of this
   episode's violations only appeared after 2-3 seconds specifically because a reveal/pan/
   dissolve motion exposed background content the still frame never showed.

## Secondary lesson — "locked" consistency assets need the actual file, not just a text instruction

Phase 6/7 called for beats 5, 11, and 12 to reuse the identical window-frame + Earthrise photo
asset. Describing this in the prompt text ("reuse the locked reference asset from Beat 05") was
not enough — beat 11 came back with a completely different window design, and beat 12's Earth
image was a different (nadir/cloud-swirl) shot, not the crescent-over-horizon composition from
beat 5. **Fix:** when a beat is supposed to reuse an earlier beat's visual asset, actually attach
that earlier beat's OUTPUT IMAGE FILE as a reference/ingredient in the later generation call —
in Flow, add it to the project's Ingredients and reference it directly, don't just redescribe it
in words. A text description of "the same window" is not the same input as the same file.

## Tertiary — watch for template/placeholder leakage

Beat 6 came back with a literal leftover label baked into the frame: "LOCKED NAMEPLATE CARD —
TEMPLATE" printed above the actual "ANDERS, LMP" text — an artifact of how the consistency
instruction was phrased (calling it a "locked template" in the prompt caused the model to
render that phrase as on-screen text). Fix: keep internal/process language like "locked",
"reference", "template", "consistency asset" OUT of the actual image/animation prompt text —
say what the frame contains, not how our own pipeline is managing it.

## What shipped anyway (EP01/Earthrise) — for the record

6 of 14 beats (5, 9, 10, 11, 13, 14) had their compliant window trimmed and freeze-frame
padded out to the full target duration rather than regenerated, per an explicit "go with what
we have" call — a real quality compromise (those beats hold a still image for part of their
runtime instead of the intended assembly motion), accepted knowingly for this first run rather
than delaying. Beat 11's "same window" and beat 12's "same Earth image" continuity with beat 5
also did NOT get fixed for this episode — the payoff is weaker than scripted. Future episodes
should regenerate flagged beats rather than defaulting to freeze-frame padding, now that the
root cause (missing negative instructions in the animation prompt) is understood and fixable
at generation time instead of at the edit.

## EP02 (3I/ATLAS) — chaining doesn't work, don't rely on it

Clips 3a→3b and 5a→5b were generated as "image-to-video, starting image = last frame of the
prior clip," meant to be continuations of one shot. Flow did not honor this — both pairs came
back as completely unrelated scenes (different subjects, different framing) rather than
continuations. Root cause on Flow's side was never diagnosed (mode not respected, or the
reference frame wasn't actually used). **Fix: don't design a multi-clip beat around chaining
for continuity.** Treat every "take A"/"take B" of a beat as an independently-composed shot
from the start — write each prompt to stand alone, and only rely on shared style-anchor text
(same lighting language, same color grade, same subject matter) for visual continuity between
them. This is what EP03's prompts did from the outset and it worked fine.

## EP02 — footage-reallocation technique (when a clip fails and a redo isn't worth it)

Clip 2 (context beat) failed compliance outright — a human hand was visible for the clip's
entire duration. Per the user's explicit "no redo, use what we have" call, the fix was precise
arithmetic: total raw seconds across the remaining usable clips vs. total narration-beat
seconds actually needed, then reallocating *spare* seconds from beats with surplus footage
(borrowing trimmed pieces of 3b and 5b to extend beat 1/2's coverage) — all real motion, no
freeze-frames. One clip (beat 4) needed a small uniform speed stretch (~9%, under the ~10%
ceiling) to close its own remaining gap. This is the correct way to absorb a dropped clip
without spending more credits; freeze-frame padding (EP01's approach) is the fallback of last
resort and visibly reads as "lag" to viewers — avoid it when a reallocation is arithmetically
possible.

## Flow / Veo 3.1 pricing and duration — always request the max

Flow/Veo 3.1 charges a **flat cost per generation, not per second** — a 4s, 6s, or 8s clip
costs the same (confirmed via Veo 3.1 Fast at 20 credits/generation regardless of duration).
**Always request the maximum 8 seconds on every clip** — there is no credit-saving reason to
ask for less, and the extra seconds are free trim buffer for the edit (this is what let EP02
absorb its dropped clip 2 without a regenerate, and gave EP03 comfortable surplus on every
beat with 2 takes).

## Credit economy: fallback plan + cadence target

Once this month's Google AI Pro / Flow credits run out, generation moves to **Higgsfield** as
the fallback video-generation tool — same pipeline otherwise (I still do VO/QC/compositing/
registry/scheduling). Overall cadence target: **1 video per day**. Keep this in mind when
choosing shot count and take count per beat — more takes = more credits = fewer videos/month.

## EP03 (Indonesia peat fires) — a "wrong" clip isn't always worth a redo

Clip 4a (revelation beat, "invisible fire made visible" macro shot) was prompted as an ember
glow with no open flame ("a real ember glow seen through soil, not a flame... no open flame
(glow and smoke only)"), but came back showing clearly visible, consistent open flame for the
full 8 seconds — a real prompt-compliance miss on a shot meant to reinforce the video's "you
can't see it" thesis. Flagged to the user with a recommended regenerate (20 credits, stricter
"no flicker, steady glow only" wording); user chose to keep it as-is rather than spend the
redo. Lesson: flag compliance/thesis mismatches like this clearly and let the user weigh
credit cost vs. narrative fit — a visible flame breaking through cracked soil is still a
usable, dramatic image against a "once it gets underground it won't stop" narration line, even
though it undercuts the pure "invisible" angle. Don't assume a spec miss is unusable.

## ElevenLabs quota running low mid-project — per-line model override

Mid-EP03, the ElevenLabs account hit its character quota with 4 of 5 VO lines already
generated under `eleven_v3` (with delivery-style audio tags like `[grave]`, `[hushed]`). The
last line needed more credits than were left. **Fix, now built into `tools/gen_voice.py`:**
each `vo[]` entry in `beats.json` can carry an optional `"model"` field that overrides
`--model` for that line only — the cache-hash includes the model, so already-generated lines
are never re-billed just because a later line needs a cheaper fallback model
(`eleven_multilingual_v2` is ~10% cheaper per character than `eleven_v3` and was enough to
close a ~15-credit gap once combined with trimming the line's wording). Audio delivery tags
(`[somber]`, `[unresolved]`) only work on `eleven_v3`-family models — strip them from a line's
`tts` field before falling back to a non-v3 model, or they'll be read aloud as literal text.

## Repo-wide render blocker: self-hosted fonts (fixed 2026-09-14)

`remotion/src/fonts.ts` used to call `@remotion/google-fonts`'s `loadFont()`, which makes the
headless-Chrome render process fetch each font file live from `fonts.gstatic.com` on every
render. In this sandbox, that browser process doesn't trust the outbound proxy's TLS-
terminating CA (curl and Node do, via `NODE_EXTRA_CA_CERTS`; the ephemeral Chrome render
profile doesn't) — every render failed with `ERR_CERT_AUTHORITY_INVALID` and a fatal
`NetworkError`, including for already-shipped compositions (confirmed by re-rendering EP02,
which broke the same way). **Fixed by self-hosting the exact same font files/weights/family
names locally** (`media/fonts/*.woff2`, referenced via `staticFile()` and a manually-injected
`<style>` tag in `fonts.ts`) instead of fetching them at render time — zero visual or API
change for any consumer, since every component still imports the same `FONT_BODY`/
`FONT_DISPLAY`/etc. string constants. If a *new* Google Font ever needs to be added to that
file, download its exact woff2(s) via `curl` (works fine — it's specifically the browser
that doesn't trust the proxy CA, not curl/Node) rather than reaching for
`@remotion/google-fonts` again.

## Connector reference — Upload-Post (CP_Posting) and Higgsfield

Both are account-level tool connections (MCP servers), not repo code — they work the same
regardless of which project/repo Claude is in. Documented here so the workflow is explicit
rather than tribal knowledge.

**Upload-Post (CP_Posting) — posting and pulling profile data**
- `list_users` — pulls every Upload-Post profile on the account and which social accounts are
  connected under each, plus per-platform capabilities (e.g. whether a TikTok connection
  supports music/location/draft mode). This is "pulling data from the profile."
- Uploading a **local** file is a 3-step stage: `create_media_upload` (get a signed PUT URL) →
  `curl -X PUT` the actual bytes to it → `complete_media_upload` (returns a `media_url` good
  for ~6 hours). Only then call `upload_video` with that URL. A public HTTPS URL can skip
  straight to `upload_video`.
- `upload_video` is the actual publish/schedule call (platforms, caption, optional
  `scheduledDate`) — returns a `request_id` immediately; the upload itself is async.
- `get_status` — poll with the `request_id` until every platform shows `completed`. This is
  what confirms it's actually live, not just "queued."
- `list_scheduled` / `get_history` — dedup checks and audit trail.
- **Discipline layered on top, see `.claude/skills/publish-video/SKILL.md`:** never trust a
  Drive URL from memory — always re-verify the file's `content-length` against
  `publishing/registry.json`'s recorded size via curl before posting, and record every real
  result back into the registry after `get_status` confirms it.

**Higgsfield — generation + the sandbox**
- `generate_video` / `generate_image` / `generate_audio` are the core generation calls — pick
  a model, pass a prompt + reference media, get a job back. Local files need
  `media_upload_widget` first, never raw shell access to attachments.
- The **sandbox** (`sandbox_exec`) is a separate thing from generation: a real remote Linux box
  (ffmpeg, ImageMagick, sox, python3, node, Playwright, caption fonts preinstalled) for editing
  work generation alone can't do — trimming, concatenating, compositing, captioning. Two things
  make it unusual: it's **ephemeral** (wiped ~10s after each call returns, so a multi-step edit
  must be chained into one command with `&&`, or inputs need re-downloading next call), and
  **outputs must be uploaded before the command exits** (`media_upload` first, then
  `curl -X PUT` inside that SAME command, before it returns).
- `get_workflow_instructions` — for structured multi-step jobs (UGC ads, ad-multiplier,
  character sheets, branded assets, website builder), loads a bundled step-by-step SKILL.md
  before touching generation directly, rather than freelancing the sequence.
- **Status as of this writing:** Higgsfield is the documented *fallback* generator once
  Flow/Google AI Pro credits run out (see "Credit economy" above) — it has not actually been
  used for a real episode yet. All three GoogleFlow Gen episodes so far used Google Flow for
  generation and this repo's own Remotion engine (not Higgsfield's sandbox) for editing and
  captions.
