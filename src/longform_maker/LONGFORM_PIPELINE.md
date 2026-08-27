# Teaching long-form pipeline (public distribution)

> **PUBLIC_FIXTURE / privacy boundary:** no maintainer project title, local path,
> transcript excerpt, analytics screenshot value or dated evaluation ships here.

## 1. Control contract

Bind approved sources and transcript cues, compile an edit plan, audit it, apply
once, render to a candidate, run delivery QA, atomically publish `current.mp4`,
then require a human review receipt.  A media helper may implement a command but
must not bypass the plan/receipt chain.

## 2. Reusable stages

1. `script_gate.py` checks hook, structure, audience language and rhythm.
2. `audio_chain.py` trims, aligns, mixes and verifies full-duration coverage.
3. `word_captions.py` builds semantic caption groups from approved word timing.
4. `visual_director.py` and `video_handlers.py` bind evidence to visual beats.
5. `proof_stage.py` presents approved evidence without inventing results.
6. `delivery.py` registers only the current, QA-bound artifact in Publish Hub.

## 3. Project inputs

Keep per-video narration, source mappings, offsets, scene plans, generated
graphics and publish copy inside that video's workspace.  Reusable modules stay
in `src/longform_maker/`; do not copy them into a build directory.

## 4. Calibration

Speaking rate, caption density, color thresholds, music level, pacing and KPI
comparisons must come from creator-owned evidence.  Public defaults are starter
fixtures only.  Record the sample set, comparison window and reason whenever a
threshold changes.

## 5. Delivery gates

- source facts and transcript cues are approved and traceable;
- captions preserve meaning, safe area and readability;
- audio covers the full video and satisfies the selected delivery profile;
- the render SHA matches technical QA and the mobile review entry;
- human review remains uncertified machine state until a person decides;
- only `_out/current.mp4` is the active render; versions live in metadata.

Run module self-tests plus the repository quick/system-health gates before a
release.  Missing private calibration media is expected in the public kit and
must not be treated as a passing real-corpus regression.
