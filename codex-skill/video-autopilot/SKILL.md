---
name: video-autopilot
description: End-to-end open-source video planning, editing, QA, publishing-package, outcome-learning, and safe self-upgrade workflow for YouTube long-form, Shorts, Reels, interviews, tutorials, travel, food, podcasts, product demos, unboxings, and challenge videos. Use when the user asks to plan, cut, improve, review, package, publish, learn from, or update an automated video workflow.
---

# Video Autopilot

Use the public repository as the executable source of truth. Keep the user's media, profiles,
credentials, analytics and learned outcomes local. Never copy the maintainer's private thresholds or
project paths into another user's installation.

## Start safely

1. Find the repository root by locating `release-manifest.json` and `src/`.
2. If `.video-autopilot/install-state.json` exists, run at most once per 24 hours:
   `python src/release_manager.py auto --install-root .`
   Treat network/update-check failure as non-blocking. Never bypass hash verification.
3. Read only the references needed by the routed production line. Do not load the whole knowledge
   library into context.
4. Inspect media and project state before changing files. Preserve unrelated user changes.

## Route the request

- YouTube long-form, tutorials, reviews, AI education: use `src/longform_maker/`, the plan/script/
  pace/grade gates, and long-form delivery QA.
- Shorts, Reels and vertical challenge clips: use `src/shorts_autopilot.py`,
  `src/longform_maker/shorts_gate.py`, visual inspection, and Shorts delivery QA.
- Interviews and no-face shows: use `src/interview_autopilot.py`, `src/interview_gate.py`, and the
  interview templates.
- Existing-video teardown: use `src/teardown.py`; distinguish measured facts from inference.
- Storage/release cleanup: use `src/storage_lifecycle.py`; never delete originals without explicit
  user scope and verified recoverability.
- Installation or update work: read `references/open-source-release-and-upgrade.md` completely.

## Universal production contract

Follow this order for every production line:

1. Audit inputs and constraints.
2. Identify story, hook, proof, payoff and platform.
3. Produce a time-coded plan before rendering.
4. Prefer real source footage and evidence. Fill missing footage with semantic B-roll, then
   domain-appropriate motion, then a concise card, then a clean hold.
5. Use cuts and motion only when they carry meaning. Never insert empty template screens, generic
   grid openers, unrelated full-screen cards or decorative transitions.
6. Apply restrained shot-aware color correction before stylized grading. Do not hard-stack LUTs.
7. Run the production-line gates and inspect rendered frames/video, not only logs.
8. Put approved deliverables in one clearly named ready-to-publish package with copy and metadata.
9. Record outcomes only from real platform evidence; send algorithm/traffic learning to the user's
   designated social analytics ledger.

## Visual and edit quality

- Treat MrBeast and Yingshi Hurricane as benchmark directions, never as a claim of pixel-identical
  reproduction or guaranteed performance.
- Optimize clarity, momentum, visual hierarchy, proof density, sound design and payoff.
- Long-form captions stay clean. Use large premium tracked words/numbers only for meaningful
  emphasis, value, stakes or progression.
- Vertical captions may use semantic emphasis and selective color, but must stay inside safe areas.
- Tracking must survive occlusion and loss. Freeze, fade or reacquire on low confidence; never let
  an arrow or label drift.
- Native/source-grounded transitions come first: action match, camera motion, foreground wipe,
  sound bridge, motivated flash or clean cut. A transition may not become a separate filler scene.
- Authentic-vs-counterfeit comparisons must label only what evidence establishes. Official-vs-
  official matchups use product names without redundant authenticity badges.

## Mechanical gates

Block release on:

- clipped captions or unsafe text;
- unreviewed tracker drift;
- dead/black filler frames;
- unrelated template or grid scenes;
- unsupported factual claims;
- missing license/provenance for redistributed assets;
- failed duration, audio, aspect-ratio or export checks;
- private paths, credentials, analytics or user media inside a public release.

Warnings do not equal failures. Preserve evidence and report the exact gate ID and remediation.

## Open-source behavior

- The repository release manifest is the only public ownership boundary.
- Unknown files and protected user paths are never removed by updates.
- Compatible releases may update automatically only after archive and per-file SHA-256 verification.
- Back up every replaced managed file. If an update fails, roll back the transaction.
- Major or compatibility-window-breaking releases require confirmation.
- Codex Skill synchronization may remove only files previously recorded in its managed marker.
- Never silently adopt or overwrite an unrelated existing `~/.codex/skills/video-autopilot`.

## Commands

```bash
python src/system_health.py --quick
python src/release_manager.py check
python src/release_manager.py update                 # preview
python src/release_manager.py update --apply         # verified manual update
python src/release_manager.py auto                    # compatible auto-update
python src/release_manager.py rollback
python src/release_manager.py install-skill
python src/release_manager.py build --base-url https://github.com/Hao0321/video-autopilot-kit/releases/download/vX.Y.Z
```

Use `install_or_upgrade.py` as the bootstrap for legacy copies that do not yet contain the release
manager.

## References

- Start/update/release details: `references/open-source-release-and-upgrade.md`
- Full system and production references live under the repository `knowledge/` directory. Route to
  the production line first, then open only the necessary chapters.
