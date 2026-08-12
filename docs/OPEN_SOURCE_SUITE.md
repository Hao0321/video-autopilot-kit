# Open-source suite map

The full public Video Autopilot system is a suite with explicit ownership and licensing boundaries.

| Component | Delivery | License | Update policy |
|---|---|---|---|
| `video-autopilot-core` | Primary release zip | MIT | Compatible, hash-verified automatic updates |
| `video-autopilot-codex-skill` | Bundled under `codex-skill/` | MIT | Managed-marker synchronization |
| `hao-motion-kit` | Optional separate release asset | Code MIT; rendered assets CC BY 4.0 | Manual opt-in; never silently replace a 50MB media pack |
| CapCutAPI | External pinned dependency (`sun-guannan/CapCutAPI`, commit `9d6fcd3`) | Checked `LICENSE` is Apache-2.0; its `pyproject.toml` still declares MIT and points at another upstream | Manual opt-in only; never rebrand, silently vendor, or redistribute until the upstream metadata conflict is resolved |

Private user footage, faces, music, profiles, credentials, analytics, outcome history, project files
and assets without explicit redistribution permission are intentionally not components of the public
suite. That exclusion is required for a complete, trustworthy open-source release.

The machine-readable source of truth is `release-manifest.json`. Release assets must report their
version, license and SHA-256 where they are project-hosted. Missing license or provenance is
fail-closed.

## What “complete” means

Complete means every generally reusable public capability declared by this repository ships in the
release archive, while every optional companion has an explicit version, owner, license, delivery
method and update policy. It does **not** mean copying a creator's private workspace or silently
vendoring every dependency.

- Core release: long-form gates/effects/captions, Shorts/Reels scan/build/gates, interview planning
  and gates, no-face/silent-vlog tools, CapCut-assisted helpers, teardown, storage lifecycle,
  channel outcome logging, public knowledge, empty templates, examples and the Codex Skill.
- Optional visual library: Hao Motion Kit stays a separately licensed download because it is large
  media; the core can run without it.
- External editor bridge: CapCutAPI remains an upstream dependency until its own checked LICENSE
  and package metadata agree. The public kit links and pins it; it does not claim ownership.
- Private adaptation: user profiles, footage, analytics, outcomes, credentials, project drafts and
  licensed media remain local. Empty examples and schemas are the public interface for those data.

If a future public feature is added, it must first enter `required_paths` or an explicitly versioned
suite component. Documentation alone is not considered shipped functionality.
