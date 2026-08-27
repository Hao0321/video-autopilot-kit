---
name: video-autopilot
description: Plan, build, review, package, release, and improve long-form videos and vertical shorts with evidence-gated, creator-configurable workflows.
---

# Hao Video Autopilot

Turn a content brief and creator-owned source material into reviewable video
artifacts and publishing packages. The workflow supports long-form video,
YouTube Shorts, Instagram Reels, and reusable image or motion assets. It does
not ship a maintainer profile: voice, face policy, captions, palette, outro,
channel links, performance baselines, and aesthetic choices come from the
active creator configuration or an explicit brief.

## Modes

- **Plan** — clarify the audience promise, evidence, format, platform,
  constraints, and packaging hypotheses; produce a script and edit plan.
- **Build** — inspect authoritative source material, bind every decision to
  evidence, apply an audited edit plan atomically, render, and run delivery QA.
- **Log Outcome** — record human review and comparable platform outcomes in
  the creator's protected local state; never treat missing values as zero.
- **Optimize Patterns** — propose reversible changes from repeated comparable
  evidence. A single preference or result cannot become a universal default.

## Operating contract

1. Discover the project root from its manifest and keep generated work inside
   the existing project structure. Do not invent sibling project directories.
2. Classify the requested format and load only the references needed for that
   route. Treat project media, accounts, drafts, outcomes, and creator profiles
   as local data unless the creator explicitly authorizes a separate action.
3. Inspect source material before planning. Claims about products, places,
   prices, results, licenses, or identities require verifiable evidence.
4. Compile decisions into `hao.video-autopilot.edit-plan/v4`, audit the plan,
   apply it atomically through the workflow contract, and retain immutable
   receipts. Older plan versions may be imported for migration but not applied
   as the current workflow.
5. Programmatic motion uses `hao.motion-composition/v1`; effects, tracking,
   masks, generated assets, and transitions require a semantic purpose and the
   evidence needed by their adapters. Missing evidence falls back to a clean
   cut or clean hold rather than a fabricated result.
6. Render only after prerequisites pass. Run technical QA, content-integrity
   checks, and a human review bundle. Machine checks may block known failures;
   they do not certify taste or authorize publication.
7. Package platform variants from one verified content truth. Platform copy,
   aspect ratio, safe areas, and metadata may differ without changing factual
   claims.

The workflow lifecycle is represented by
`hao.video-autopilot.workflow-contract/v1` receipts. Interrupted work resumes
from verified state; an unknown apply state must be reconciled before retrying.

## Remote review

When visual artifacts need review, create a manifest-bound review bundle for
the authoritative media. Local review is preferred when available. Remote
review may use a temporary secret HTTPS endpoint after verifying the page and
media range response from the public URL. Keep the workstation online while
review is active, share the URL only with the intended reviewer, and stop the
endpoint when review is complete. A review URL is access, not approval.

## Release and update

The public project is [https://github.com/Hao0321/video-autopilot-kit](https://github.com/Hao0321/video-autopilot-kit). Release archives must be
manifest-driven, reproducible, checksummed, and limited to redistributable
files. Exclude creator media, accounts, local profiles, outcomes, credentials,
private paths, and assets without redistribution rights. Updates verify the
release channel and manifest, preserve protected local paths, back up managed
files before replacement, and roll back on failure. Incompatible upgrades
require confirmation; unknown files are never deleted implicitly.

## Authorization boundaries

- Planning, local rendering, validation, and creation of review artifacts are
  implementation steps within an authorized build.
- Publishing, messaging, spending credits, installing external components,
  or exposing a remote endpoint requires the authority appropriate to that
  action.
- Generated or illustrative media cannot be presented as documentary proof.
- Human review remains explicit and cannot be inferred from a passing test.

## Public references

- [Editorial intelligence contract](references/editorial-intelligence-contract.md)
- [Workflow execution](references/editkin-workflow-execution.md)
- [Plugin automation](references/editkin-plugin-automation.md)
- [Mobile device binding](references/editkin-mobile-device-binding.md)
- [Model and context adaptation](references/model-and-context-adaptation.md)
- [Script and retention calibration](references/script-retention-2026.md)
- [Asset workshop](references/asset-workshop.md)
- [Publish hub and remix](references/publish-hub-and-remix.md)
- [Storage lifecycle](references/storage-lifecycle.md)
- [Token budget system](references/token-budget-system.md)
- [Open-source release and upgrade](references/open-source-release-and-upgrade.md)
