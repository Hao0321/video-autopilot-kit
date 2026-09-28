# Illustrated music MV route

An illustrated music MV uses an original character, layered scenes, graphic
symbols, expressive typography and musical editing. A live-action montage
with lyric cards is a separate route. Existing videos may inform the rhythm
and visual grammar; do not copy their characters, costumes, logos, song,
shots or exact layouts.

## Required inputs

- A song the creator may use, with verified duration and musical sections.
- Original or licensed background, character poses and foreground art with
  provenance and distribution scope. Character and foreground layers need
  usable alpha. Do not substitute unrelated stock footage for missing art.
- Lyrics verified against the audio. A title or graphic word can come from
  the creative brief; unverified words cannot be labeled as lyrics.
- A storyboard with section boundaries, framing changes, emotional purpose,
  colour progression, text events and cut or transition evidence.

## Editkin plan

1. Analyse beat candidates, then listen to confirm downbeats, phrases,
   syncopation and holds. Avoid cutting on every beat by default.
2. Make contiguous, frame-aligned sections. Route original background,
   character, optional silhouette and transparent foreground accents to
   separate editable tracks. Use distinct poses and expressions at musical
   turns, with meaningful camera and depth motion. Same-aspect, high-resolution
   cels can use evidence-bound `characterFrame` positioning to preserve soft
   alpha edges and space for text.
3. Use `prepare_illustrated_music_video_draft` for a read-only command
   candidate. The tool requires image rights, alpha, continuous music and
   explicit evidence references. Its source project remains unchanged.
4. Bind its flat commands plus title and verified lyric events into one
   `hao.video-autopilot.edit-plan/v4`; audit, apply atomically and render.
   Preserve the command receipt and re-open the project before export.
5. Animate text at the phrase and syllable level where warranted: staggered
   character entrances, brief beat words, `impact` or center-out `ripple`
   treatment, exit timing, negative space and contrast that remain legible over
   the character. A short `accent_flash` needs evidence on both sides of a
   musical cut and frame-by-frame overexposure review. Transitions, silhouette
   reveals and foreground effects should accent scene meaning.

## Acceptance

Inspect the rendered video and delivered native editor project. Verify every
cut, silhouette edge, text motion, colour handoff, effect and musical accent
against the storyboard; check frame count, audio continuity, decode, preview
responsiveness, render time and memory. Technical success is not art approval.
Keep the result in review until a person assesses character consistency,
posing, compositing, typography and the complete viewing rhythm. A short
engineering sample cannot be reported as a finished MV.
