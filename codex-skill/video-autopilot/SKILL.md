---
name: video-autopilot
description: End-to-end open-source video planning, editing, QA, publishing-package, outcome-learning, and safe self-upgrade workflow for YouTube long-form, Shorts, Reels, interviews, tutorials, travel, food, podcasts, product demos, unboxings, and challenge videos. Use when the user asks to plan, cut, improve, review, package, publish, learn from, or update an automated video workflow.
---

# Video Autopilot

Treat the repository as executable source of truth. Keep each user's media, credentials, profiles,
analytics, feedback, outcomes and local paths private. The bundled knowledge is a reusable starting
standard, not permission to invent evidence or claim guaranteed performance.

## Start safely

1. Locate `release-manifest.json` and `src/`. Preserve unrelated user files.
2. When managed install state exists, run at most once per 24 hours:
   `python src/release_manager.py auto --install-root .`
   Network failure is non-blocking; hash or compatibility failure is blocking.
3. Route context before opening many references:
   `python src/context_router.py route --request "<request>" --format auto`
4. Inspect source media and project state before changing anything. Originals stay read-only.
5. For a clean install, run `python src/system_health.py --quick`.
6. To score the complete architecture contract, run `python src/project_quality_95.py`.

## Route the production line

- YouTube long-form, tutorials and reviews: `src/longform_maker/` plus script, plan, pace, grade,
  proof and delivery gates.
- Shorts and Reels: `src/shorts_autopilot.py`, Shorts gate, rendered-frame review and delivery QA.
- Interviews/no-face shows: interview pipeline and no-face documentary grammar.
- Existing-video teardown: `src/teardown.py`; measured facts and inference must remain separate.
- Storage/publishing: `src/storage_lifecycle.py` and `src/publish_hub.py`.
- AI short drama is opt-in only; never route ordinary video work there because the module exists.
- Install/update/release: read `references/open-source-release-and-upgrade.md` completely.

## Production contract

For every format:

1. Audit inputs, licenses, aspect ratio, platform and evidence limits.
2. Identify hook, promise, progression, proof, payoff and one intended viewer action.
3. Write a time-coded plan before rendering; route visual, caption, sound and color systems by topic.
4. Fill gaps in this order: verified source footage, semantic B-roll, topic motion, concise card,
   then a clean hold. Never substitute unrelated stock for a factual claim.
5. Use clean cuts by default. Any special transition needs two real shots plus visible motion,
   occlusion or documented edit motivation. A particle/flash/shape overlay is not itself a transition.
6. Correct exposure and white balance per shot, then apply one restrained look before graphics.
   Unknown log footage blocks grading until an input transform is known. Never hard-stack LUTs.
7. Run the line-specific gates, then inspect the rendered video/frames—not only logs.
8. Put approved output, copy and metadata in one clearly named ready-to-publish package.
9. Record audience outcomes only from real same-platform/same-window evidence. Keep subjective taste
   learning separate from traffic learning.

## Visual quality contract

- Use MrBeast as an information-energy benchmark and Yingshi Hurricane as a cinematic-craft
  benchmark for both long and short video. They are scoring directions, not permission to claim
  pixel-identical reproduction, copy protected assets or guarantee results.
- Design grammar is topic-dependent. A grid is an optional information surface, never a universal
  opener. Empty template screens, unrelated cards and transition-as-filler are release blockers.
- Long-form captions stay calm; large tracked words/numbers are selective emphasis. Vertical
  captions may be more kinetic but stay white-first, semantically colored and inside safe areas.
- Tracking needs a verified anchor, confidence history, occlusion handling and loss behavior.
  Freeze briefly, fade or reacquire; never let a label or arrow drift.
- Original brand-like typography, logos, thick outlines, glossy 3D text and cartoon sticker
  grammar are allowed when the topic supports them and asset licensing is clear.
- Authentic-vs-counterfeit content labels only what evidence proves. Official-vs-official
  comparisons use product names without redundant authenticity badges.

## Learning that persists

- Durable rules live in the bounded knowledge lifecycle, not an ever-growing chat transcript.
- New feedback starts as candidate evidence; promote only after contradiction checks and enough
  examples. Hard negative rules require reproducible failure evidence.
- Compact/supersede older records instead of appending endless versions.
- Use `src/taste_model.py` for pairwise visual preferences and `src/outcome_learning.py` for
  audience metrics. Do not let one silently overwrite the other.

## Fail-closed release gates

Block release on clipped text, tracker drift, dead/black filler, unrelated template/grid scenes,
unsupported claims, missing redistributable provenance, failed duration/audio/aspect/export checks,
unknown log transforms, or private data in a public package. Warnings remain visible but do not
pretend to be blockers.

## Open-source and upgrade contract

- `release-manifest.json` is the only public ownership boundary.
- Unknown and protected local files are never deleted by updates.
- Verify archive and per-file SHA-256 before replacing managed files; back up first and roll back
  transactionally on failure.
- Compatible patch updates may auto-apply. Major/incompatible updates and locally modified managed
  files require confirmation.
- Skill sync may remove only files named in its own managed marker. Never silently adopt an
  unrelated `~/.codex/skills/video-autopilot`.
- The optional Motion Kit enhances full template/media rendering; the core must remain functional
  with its procedural fallback.

## Core commands

```bash
python src/system_health.py --quick
python src/context_router.py selftest
python src/quality_95.py selftest
python src/release_manager.py check
python src/release_manager.py update                 # preview
python src/release_manager.py update --apply         # verified manual update
python src/release_manager.py auto                    # compatible auto-update
python src/release_manager.py rollback
python src/release_manager.py install-skill
```

Legacy copies without the release manager use `install_or_upgrade.py` once.

## Reference routing

- Visual standard and scoring: `references/hao-aesthetic-standard.md`,
  `references/quality-95-system.md`, `references/color-science-and-visual-master.md`
- Editing grammar and benchmarks: `references/editing-master-techniques.md`,
  `references/mrbeast-and-yingshi-benchmark.md`, `references/camera-transition-and-value-visualization.md`
- Captions/tracking: `references/caption-art-direction.md`,
  `references/tracked-typography-and-challenge-ledger.md`
- Topic routing/assets: `references/niche-editing-grammar.md`,
  `references/asset-intelligence-hub.md`, `references/motion-asset-library.md`
- Memory/token/storage/publishing: `references/knowledge-lifecycle.md`,
  `references/token-budget-system.md`, `references/storage-lifecycle.md`,
  `references/publish-hub-and-remix.md`

Open only the references needed for the routed request.
