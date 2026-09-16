---
name: publish-video
description: Queue, reschedule, or immediately publish a finished short to this channel's connected platforms via CP_Posting (Upload-Post). Use whenever posting, scheduling, rescheduling, or checking what's live/queued — including after generating a new short-N or vox-N video, or when the user says "schedule this", "post now", "what's scheduled", or asks about the posting queue. Exists because a real incident happened without it on a sibling project: a Drive file ID recalled from conversation memory was reused for the wrong video, posting one short's content under another's title across all three platforms.
---

# publish-video — never post from memory

Every step below exists because skipping it already caused a real mistake once. Do not
shortcut this because "the URL is right there a few messages up" — that exact belief is what
posted vox-3's video under vox-2's title on three platforms simultaneously.

## The registry: `publishing/registry.json`

The single source of truth for which Drive file ID belongs to which video. Before ANY
`upload_video` or `edit_scheduled` call:

1. Look up the video's entry by `id`. If it has no entry yet, that's step 0 — see below.
2. `curl -sS -L -D - -o /dev/null "https://drive.google.com/uc?export=download&id=<drive_file_id>"`
   and confirm `content-length` equals the registry's `local_size_bytes` EXACTLY. A mismatch
   means the wrong file — stop, do not post, re-derive the correct ID.
3. Only then call `upload_video` with that verified URL.

Never substitute a URL "remembered" from earlier in the conversation without doing step 2
against the registry first — memory across a long conversation with several similar-looking
Drive links is exactly what failed last time.

## Step 0 — registering a new video before its first post

When a short/vox video is rendered and ready to post for the first time:
1. Get its exact local byte size: `ls -la remotion/out/<Id>-voiced-delivery.mp4` (or whichever
   file is actually being uploaded — the delivery-encoded one, not the raw voiced render).
2. Ask the user for the Drive link, then verify it (step 2 above) BEFORE using it for anything.
3. Add a new entry to `publishing/registry.json`: `id`, `title`, `local_file`, `local_size_bytes`,
   `drive_file_id`, `posts: []`.
4. Only now proceed to `upload_video`.

## After every post — close the loop, don't assume

`upload_video` on a slow upload returns `status: "processing"` with a `request_id`, not a
finished result. Poll `get_status` until every platform shows `completed`/`success`, then:
1. Confirm `media_size_bytes` in the result matches the registry's `local_size_bytes`. This is
   the actual guardrail against a repeat of the incident — a title can be right while the file
   is wrong, and only the byte size (or a content check) catches that.
2. Append the result to that video's `posts[]` in the registry: `platform`, `job_id`, `post_id`,
   `url`, `status: "live"`, `posted_at`, `verified_size_bytes`.
3. Only then report success to the user. "Upload initiated" is not "posted."

## An MCP error does not mean the action failed

If `upload_video` or any CP_Posting call errors (e.g. "MCP server session expired"), the
request can still have completed server-side before the response was lost — this happened
three times in one session and produced three duplicate scheduled posts. Before retrying any
CP_Posting call after an error:
1. Call `list_scheduled` and/or `get_history` and check whether the action already went
   through (matching title/description/timestamp close to now).
2. Only retry if it demonstrably did not.
3. If unsure, ask rather than retry blind.

## Duplicate check before scheduling anything

Before every `upload_video` call (not just after an error): run `list_scheduled` and confirm
this video isn't already queued. Before every `edit_scheduled` call: confirm the `jobId`
you're targeting still exists and belongs to the video you think it does (title match).

## Deleting a wrong post

`unpublish_post` only supports `facebook, youtube, x, linkedin, threads` — **not Instagram or
TikTok**. If a wrong video needs removing from those two, it requires manual deletion by the
user; say so plainly and give the direct post URL rather than implying it's handled.

## Scheduling timezone

Audience is India-based — default to IST (`Asia/Kolkata`, UTC+5:30) for any "post at Xpm"
request unless the user says otherwise. Always convert explicitly and state both the local
and UTC time back to the user so a wrong assumption is easy to catch (e.g. "4pm IST = 10:30
UTC"). This was asked once and should not need re-asking — treat it as the standing default.
