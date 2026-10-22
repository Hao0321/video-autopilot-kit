# Open-source suite map

The public Video Autopilot system is a small suite with explicit ownership and licensing boundaries.
Since v0.25.0 the split is simple: **VA plans, judges and checks; Editkin renders.** See
[ARCHITECTURE.md](ARCHITECTURE.md) for the one-page overview.

| Component | Delivery | License | Update policy |
|---|---|---|---|
| `video-autopilot-core` (VA) | Primary release zip from this repository | MIT | Hash-verified updates you run yourself (`install_or_upgrade.py` or `python src/release_manager.py auto`); compatible releases only in automatic mode |
| `video-autopilot-codex-skill` | Bundled under `codex-skill/` | MIT | Managed-marker synchronization (`--install-skill` / `release_manager.py install-skill`) |
| Editkin | Separate desktop editor, [github.com/Hao0321/Editkin](https://github.com/Hao0321/Editkin) | GPL-3.0 (or later, per Editkin's LICENSE) | Public as source today; official downloads will be announced on [Editkin releases](https://github.com/Hao0321/Editkin/releases). Never bundled, vendored or updated by this kit |

Editkin is a companion, not a component of the release archive. VA reaches it only through the
Editkin v4 workflow contract (`src/workflow_contract.py` + `workflow_contract.json`) and the MCP
tools an agent calls on its behalf. The Editkin Motion Library (text animations, transitions and
backgrounds) needs an Editkin build that includes it; the [Editkin public preview](https://github.com/Hao0321/Editkin/releases/tag/v0.15.0-preview.20261022) includes it.

Private user footage, faces, music, profiles, credentials, analytics, outcome history, project files
and assets without explicit redistribution permission are intentionally not components of the public
suite. That exclusion is required for a complete, trustworthy open-source release.

The machine-readable source of truth is `release-manifest.json`. Release assets must report their
version, license and SHA-256 where they are project-hosted. Missing license or provenance is
fail-closed.

## What “complete” means

Complete means every generally reusable public capability declared by this repository ships in the
release archive, while every companion has an explicit owner, license, delivery method and update
policy. It does **not** mean copying a creator's private workspace or silently vendoring every
dependency.

- Core release: the Editkin v4 workflow controller, rhythm-scene planning, context routing, the
  long-form/Shorts/script/pacing/voice-over gates, caption-quality scanning, editor-neutral delivery
  QA, the review server, publish hub, outcome learning, interview planning and gates, teardown,
  storage lifecycle, channel tracking, public knowledge, empty templates, examples and the Codex Skill.
- Rendering: Editkin is the sole renderer and the sole editor contract. Plans are audited as
  `hao.video-autopilot.edit-plan/v4` and applied atomically. The Python/FFmpeg renderers that earlier
  releases shipped were retired in v0.25.0; they are not release dependencies or fallback runtimes.
  The last release containing them is tag `v0.24.1`.
- Code cleanup: no longer bundled. The Cleanup tool lives in its own repository,
  [claude-skill-code-cleanup](https://github.com/Hao0321/claude-skill-code-cleanup).
- Private adaptation: user profiles, footage, analytics, outcomes, credentials, project drafts and
  licensed media remain local. Empty examples and schemas are the public interface for those data.

If a future public feature is added, it must first enter `required_paths` or an explicitly versioned
suite component. Documentation alone is not considered shipped functionality.
