"""Render the redistributable Hao Video Autopilot Skill entrypoint.

The renderer deliberately treats the canonical Skill as an untrusted private
input.  It validates only the canonical frontmatter and then emits a fixed,
creator-neutral public skeleton.  Canonical body text is never copied,
summarized, interpolated, or used to choose public defaults.
"""

from __future__ import annotations

import re
from typing import Dict


SKILL_NAME = "video-autopilot"
PRODUCT_NAME = "Hao Video Autopilot"
PROJECT_URL = "https://github.com/Hao0321/video-autopilot-kit"
PUBLIC_DESCRIPTION = (
    "Plan, edit, caption, color-grade, review, package and publish YouTube long-form "
    "videos, Shorts/Reels and illustrated music videos with evidence-gated Editkin v4 "
    "workflows, creator memory and QA. Use for 剪片/剪輯、上字幕、調色、配樂/音效、"
    "做Shorts/Reels、做封面/縮圖、審片/品質檢查、發布文案、從成效學習."
)

# Every shipped reference is routed from the public entrypoint (task rows,
# benchmark-only rows or the history row).  Adding or removing a reference
# requires a reviewed source change here; arbitrary links from the canonical
# body can never enter the public Skill.
PUBLIC_REFERENCES = (
    "ai-evidence-canvas.md", "architecture-foundation-v6-3.md",
    "asset-intelligence-hub.md", "asset-workshop.md", "autopilot-modes.md",
    "benchmark-effect-parity.md", "beyblade-x-finish-judging.md",
    "bright-editorial-template-system.md", "calibration-learning-and-license.md",
    "camera-transition-and-value-visualization.md", "caption-art-direction.md",
    "cinematic-wave-and-domain-grammar-2026.md", "color-science-and-visual-master.md",
    "competitor-vertical-teardown-2026.md", "craft-index.md", "design-reference-dna-v6.md",
    "editing-craft-fundamentals.md", "editing-master-techniques.md",
    "editing-techniques-2026.md", "editing-wave5-finecut-2026.md", "editing-wave6-2026.md",
    "editkin-batch-workflow.md", "editkin-mobile-device-binding.md",
    "editkin-plugin-automation.md", "editkin-workflow-execution.md",
    "editorial-intelligence-contract.md", "filter-library.md", "genre-copy-grammar-2026.md",
    "genre-editing-craft-2026.md", "hao-aesthetic-standard.md", "knowledge-lifecycle.md",
    "mediastorm-craft-system.md", "model-and-context-adaptation.md",
    "motion-asset-library.md", "mrbeast-and-yingshi-benchmark.md",
    "mrbeast-production-source-map.md", "music-video-motion.md", "niche-editing-grammar.md",
    "niche-fonts-colors.md", "open-source-release-and-upgrade.md",
    "programmatic-motion-runtime.md", "publish-hub-and-remix.md", "quality-95-system.md",
    "script-retention-2026.md", "shorts-mastery-2026.md",
    "shorts_reels_2026_best_practices.md", "shot-selection-language.md",
    "storage-lifecycle.md", "template-compiler-v2.md", "ten-million-editorial-system.md",
    "three-d-and-subject-fx.md", "thumbnail-algorithm-score.md", "token-budget-system.md",
    "tracked-typography-and-challenge-ledger.md", "unattended-autonomy-standard.md",
    "visual-art-direction-2026.md",
)
# The aesthetic-standard filename predates the creator-neutral naming; it is the
# only reference link allowed to contain the brand stem.
BRANDED_REFERENCE_LINKS = ("references/hao-aesthetic-standard.md",)

_FRONTMATTER = re.compile(
    r"\A---[ \t]*\r?\n(?P<header>.*?)\r?\n---(?:[ \t]*\r?\n|\Z)",
    re.DOTALL,
)
_SKILL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_ANY_REFERENCE_LINK = re.compile(r"\]\(\s*(?:\./)?references/([^)\s]*)\)")
_REFERENCE_NAME = re.compile(r"[a-z0-9][a-z0-9_-]*\.md\Z")
_ABSOLUTE_PATH = re.compile(
    r"(?:\b[A-Za-z]:[\\/]|/(?:Users|home)/[^/\s]+/)", re.IGNORECASE
)
_DATED_EVENT = re.compile(r"\b(?:19|20)\d{2}[-/.]\d{1,2}[-/.]\d{1,2}\b")
_LOCAL_PROJECT_ID = re.compile(r"(?<!#)#\d{2,}\b|(?:longform|project)[-_ ]?\d{2,}\b", re.IGNORECASE)
_LOCAL_METRIC = re.compile(
    r"\b(?:ctr|avp|retention|views?|subscribers?|revenue)(?:\s*[:=]\s*|\s+)[+-]?\d",
    re.IGNORECASE,
)


def _plain_scalar(value: str, field: str) -> str:
    """Read the simple one-line YAML scalars used by Skill frontmatter."""
    value = value.strip()
    if not value or value in {"|", ">", "|-", ">-", "|+", ">+"}:
        raise ValueError(f"frontmatter {field!r} must be a non-empty one-line scalar")
    if value[:1] in {'"', "'"}:
        if len(value) < 2 or value[-1:] != value[:1]:
            raise ValueError(f"frontmatter {field!r} has an unterminated quote")
        value = value[1:-1]
    if "\n" in value or "\r" in value:
        raise ValueError(f"frontmatter {field!r} must be one line")
    return value.strip()


def validate_canonical_frontmatter(canonical_text: str) -> Dict[str, str]:
    """Validate the minimum canonical identity without reading its body."""
    if not isinstance(canonical_text, str):
        raise TypeError("canonical_text must be str")
    match = _FRONTMATTER.match(canonical_text.lstrip("\ufeff"))
    if not match:
        raise ValueError("canonical Skill must start with closed YAML frontmatter")

    fields: Dict[str, str] = {}
    for line in match.group("header").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or line[:1].isspace():
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"invalid top-level frontmatter line: {line!r}")
        key = key.strip()
        if key in fields:
            raise ValueError(f"duplicate frontmatter field: {key}")
        fields[key] = value.strip()

    if "name" not in fields or "description" not in fields:
        raise ValueError("canonical frontmatter requires name and description")
    name = _plain_scalar(fields["name"], "name")
    description = _plain_scalar(fields["description"], "description")
    if not _SKILL_NAME.fullmatch(name):
        raise ValueError("frontmatter name must use lowercase letters, digits, and hyphens")
    if name != SKILL_NAME:
        raise ValueError(f"unexpected canonical skill name: {name!r}")
    if not 20 <= len(description) <= 2048:
        raise ValueError("frontmatter description must be 20..2048 characters")
    if description.lower() in {"todo", "tbd", "placeholder"}:
        raise ValueError("frontmatter description is unfinished")
    return {"name": name, "description": description}


PUBLIC_SKILL_BODY = f"""# {PRODUCT_NAME}

Turn a content brief and creator-owned source material into reviewable video
artifacts and publishing packages: YouTube long-form, Shorts, Instagram Reels,
illustrated music videos and reusable image or motion assets. Nothing creative
is hard-coded for a maintainer: voice, face policy, captions, palette, outro,
channel links, performance baselines and taste come from the active creator's
profiles, learned memory or an explicit brief.

## Start every task

1. **Project root.** Find it from `AUTOPILOT_MANIFEST.json` or
   `release-manifest.json` (or `VIDEO_AUTOPILOT_ROOT`) and keep every output
   inside it; never invent sibling project folders. Commands below run from that
   root; `references/` sits beside this file.
2. **Creator memory first.** Read `profiles/voice.md`, `profiles/brand.md` and
   `profiles/style.md` (plus `profiles/show.md` for interviews) when they exist.
   If one is missing, say so and stay neutral; never invent a creator's voice,
   face policy, palette, outro or numbers.
3. **Context packet.** Run
   `python src/context_router.py route --mode <plan|build|audit|learn|outcome> --format <shorts|longform|vlog|interview> --topic "<brief>"`
   and work from that packet: it carries the learned rules for this format and
   topic, the creator-profile status and a short list of escalation sources.
   Read one more source only when a listed trigger fires.
4. **Route.** Open only the references in the matching row below. For large
   references read only the named section (`grep -n "^## "` lists them).
5. **Evidence before plans.** Inspect the actual footage, audio and transcript
   before planning. Claims about products, places, prices, results, licenses or
   identities need verifiable evidence; otherwise mark `ASSET_REQUIRED` and plan
   the capture.

## Route by task

| Task (typical requests) | Read | Run |
|---|---|---|
| Any edit, 剪片／剪輯 | [Editorial intelligence contract](references/editorial-intelligence-contract.md); [Workflow execution](references/editkin-workflow-execution.md) | `python scripts/hao_autopilot.py workflow create`, then `next`, `claim`, `complete`, `verify` |
| Batch runs, plugins, phone pairing | [Batch workflow](references/editkin-batch-workflow.md); [Plugin automation](references/editkin-plugin-automation.md); [Mobile device binding](references/editkin-mobile-device-binding.md) | Editkin MCP tools |
| Script, hook, 開場, 留存 | [Script and retention calibration](references/script-retention-2026.md); `knowledge/script-retention-craft.md` | `src/longform_maker/script_gate.py` |
| Shot choice, 選鏡 | [Shot selection language](references/shot-selection-language.md) | `python src/visual_director.py --shot-style <style>` |
| Opening, pacing, continuity, sound | [Craft index](references/craft-index.md); [Editing master techniques](references/editing-master-techniques.md); [Editing craft fundamentals](references/editing-craft-fundamentals.md) (one section) | `src/longform_maker/pace_gate.py` |
| Genre grammar (美食、旅遊、教學、demo) | [Genre editing craft](references/genre-editing-craft-2026.md); [Cinematic wave and domain grammar](references/cinematic-wave-and-domain-grammar-2026.md); [Niche editing grammar](references/niche-editing-grammar.md) (one domain section) | context packet domain card |
| Shorts／Reels | [Short-form mastery](references/shorts-mastery-2026.md) with `knowledge/shorts-mastery-2026.md`; [Shorts and Reels practices](references/shorts_reels_2026_best_practices.md); [Vertical teardown](references/competitor-vertical-teardown-2026.md) | `python src/shorts_autopilot.py scan <folder> --platform <yt_shorts or ig_reels or fb_reels>`, then `build <folder>` |
| 上字幕, captions, text effects | [Caption art direction](references/caption-art-direction.md); [Tracked typography](references/tracked-typography-and-challenge-ledger.md); [Niche fonts and colors](references/niche-fonts-colors.md) | caption gates run inside the build |
| 調色, color, LUT, filters | [Color science and Visual Master](references/color-science-and-visual-master.md); [Filter library](references/filter-library.md) | `python src/filter_runtime.py list`, `inspect`, `apply` |
| 美感, layout, templates | [Design reference DNA](references/design-reference-dna-v6.md); [Creator aesthetic standard](references/hao-aesthetic-standard.md); [Template compiler](references/template-compiler-v2.md); [Bright editorial templates](references/bright-editorial-template-system.md); [AI evidence canvas](references/ai-evidence-canvas.md) | `src/design_system_v6.py`, `src/aesthetic_score.py` |
| Motion, 2.5D/3D, tracking, transitions | [Programmatic motion runtime](references/programmatic-motion-runtime.md); [Motion asset library](references/motion-asset-library.md); [3D and subject FX](references/three-d-and-subject-fx.md); [Camera transitions and value visualization](references/camera-transition-and-value-visualization.md) | `src/composition_runtime.py`, `src/tracked_graphics.py` |
| Illustrated music video | [Illustrated music MV route](references/music-video-motion.md) | `python src/music_mv_preflight.py <song>` |
| 配樂, sound effects, assets, AI images | [Asset intelligence hub](references/asset-intelligence-hub.md); [Asset workshop](references/asset-workshop.md) | `src/asset_registry.py`, `src/imagegen_asset_gateway.py` |
| 做封面, thumbnails | [Thumbnail algorithm score](references/thumbnail-algorithm-score.md) | `python scripts/hao_autopilot.py thumbnail-score <evidence.json> --image <png> --output-dir <dir>` |
| 審片, QA, certification | [Quality 95 system](references/quality-95-system.md); [Unattended autonomy standard](references/unattended-autonomy-standard.md) | `python src/review_loop.py create`, `serve`, `finalize` |
| 發布, copy, remix | [Publish hub and remix](references/publish-hub-and-remix.md); [Genre copy grammar](references/genre-copy-grammar-2026.md) | `python src/publish_hub.py sync`, `audit` |
| Memory, outcomes, learning | [Knowledge lifecycle](references/knowledge-lifecycle.md); [Calibration, learning and license](references/calibration-learning-and-license.md); [Token budget](references/token-budget-system.md); [Model and context adaptation](references/model-and-context-adaptation.md) | `python scripts/hao_autopilot.py knowledge`, `learn` |
| Storage, release, update | [Storage lifecycle](references/storage-lifecycle.md); [Open-source release and upgrade](references/open-source-release-and-upgrade.md) | `python scripts/hao_autopilot.py dedupe-archive <root>` |
| Benchmarks (only when asked) | [MrBeast and Yingshi benchmark](references/mrbeast-and-yingshi-benchmark.md); [MrBeast production source map](references/mrbeast-production-source-map.md); [MediaStorm craft](references/mediastorm-craft-system.md); [Ten-million editorial](references/ten-million-editorial-system.md); [Benchmark effect parity](references/benchmark-effect-parity.md) | benchmark runtimes |
| Beyblade X battle Shorts (`battle_matchup` only) | [Beyblade X finish judging](references/beyblade-x-finish-judging.md) | `src/beyblade_x_rules.py` |
| History and backlog (not by default) | [Architecture foundation](references/architecture-foundation-v6-3.md); [Autopilot modes](references/autopilot-modes.md); [Editing techniques](references/editing-techniques-2026.md); [Fine-cut wave 5](references/editing-wave5-finecut-2026.md); [Editing wave 6 backlog](references/editing-wave6-2026.md); [Visual art direction, superseded by design DNA](references/visual-art-direction-2026.md) | none |

## Operating contract

1. Compile decisions into `hao.video-autopilot.edit-plan/v4`, audit the plan,
   apply it atomically through the workflow contract and keep the immutable
   receipts. Older plan versions may be imported for migration only.
2. Bind every review score and correction to its exact video and version; never
   transfer a rating or a complaint to another cut.
3. For narration, load the creator's voice profile and at least two
   creator-written scripts in the same format and register, and write the
   audience promise, evidence map and claim boundaries first. `script_gate`
   checks audience language and retention, not voice authenticity: compare the
   draft beat by beat with those samples or mark it `VOICE_REVIEW_REQUIRED`.
4. Shot styles decide which observed shots deserve review; they never prove
   performance, source rights or story fit and never edit a timeline by
   themselves.
5. Effects, tracking, masks, generated assets and transitions need a semantic
   purpose plus the evidence their adapters require; missing evidence falls
   back to a clean cut or clean hold. The kit runtime renders
   `hao.motion-composition/v1`; Editkin presets may use
   `hao.motion-composition/v2`, including editable 2.5D floating video frames,
   portrait perspective orbit and two rear portrait panels compiled by the
   read-only scene compiler into the audited v4 plan. These are perspective
   planes, never claimed as 3D meshes.
6. Illustrated music videos use original layered character and scene art,
   verified musical phrases and frame-aligned kinetic typography. Call
   `prepare_illustrated_music_video_draft` only when the connected Editkin lists
   it; otherwise stop at the storyboard plus `music_mv_preflight` evidence
   instead of faking a draft. Use `prepare_music_video_draft` only when the
   creator explicitly asks for live-action montage.
7. Render only after prerequisites pass. Package platform variants from one
   verified content truth: copy, aspect ratio, safe areas and metadata may
   differ, factual claims may not.
8. After creating or changing a long-form thumbnail, pair it with the proposed
   title and the actual opening, inspect a 168x94 preview, record evidence for
   all ten dimensions and run the thumbnail score before calling it the selected
   or upload-ready cover. Below the ready threshold, a weak critical dimension or
   any blocking or review signal means revise and rescore. It is an explainable
   pre-publish judgment, not a CTR prediction; validate the winner with real
   post-publish watch-time evidence.
9. The lifecycle is recorded as `hao.video-autopilot.workflow-contract/v1`
   receipts. Interrupted work resumes from verified state; an unknown apply state
   is reconciled before any retry.

## Definition of done

- **Technical QA passes rather than "unverified".** Every requested delivery
  check passes: loudness at the delivery target (default -14 LUFS integrated,
  true peak at or below -1 dBTP), no general flashing above three per second, no
  unintended black stretch, captions in sync and matching audio/video lengths. A
  check that could not run blocks delivery until it runs.
- **Readable on a phone.** Captions stay inside the platform safe area, are
  fitted or wrapped instead of clipped, break at word and clause boundaries
  without orphaned punctuation, and keep body text at a contrast of at least
  4.5:1 against what is behind it.
- **One look.** Grade once, before captions and graphics; one visual language
  per video; never stack a creative LUT on a creative LUT.
- **Human taste stays human.** Only the creator's (or a designated reviewer's)
  submission on the review page, stamped by the review server for this exact
  render, can certify. A passing test, an agent-written review or a review of
  an earlier render never certifies.

## Memory and learning

- **Where memory lives.** Learned rules in `data/knowledge_state.json` (seeded
  from the read-only `knowledge/runtime/state.json`), outcomes in
  `data/channel_state.json`, taste comparisons in `data/taste_model.json`, review
  evidence in each bundle's `_review/`. All of it stays local and outside
  release updates.
- **Promotion.** A rule starts as a soft observation and reaches the context
  packet only after support from at least three distinct videos or renders with
  no contradiction, or when the creator explicitly pins it. Repeating the same
  review of the same cut adds no support; two contradicting rules are both held
  back until the creator supersedes one.
- **Outcomes.** Compare like with like (same platform, format and snapshot
  window). Never pool Shorts with long-form, never treat a missing value as
  zero, and never turn a single preference or result into a default.
- **Record.** `python scripts/hao_autopilot.py learn --rule "..." --evidence "..." --source <content-id@sha12> --format <format> --domain <domain>`;
  audit with `python scripts/hao_autopilot.py knowledge`.

## Review delivery

Prefer local review: `python src/review_loop.py create <video> --content-id <id> --quality-json <QUALITY_95.json>`,
then `serve <bundle>` and open the printed local page on the same computer.
Remote phone review exposes creator media, so start it only when the creator asks
for it (`deliver` or `remote-start`), verify the page and media range response
from the public URL, keep the workstation online while review is active, share
the link only with the intended reviewer and stop it with `remote-stop` when
review is complete. If the secure runtime is unavailable, report
`SECURE_REVIEW_RUNTIME_REQUIRED` instead of falling back to a bearer link. A
review URL is access, not approval.

## Release and update

The public project is [{PROJECT_URL}]({PROJECT_URL}). Release archives are
manifest-driven, reproducible, checksummed and limited to redistributable
files. Creator media, accounts, local profiles, outcomes, credentials, private
paths and assets without redistribution rights never ship. Updates verify the
release channel and manifest, preserve protected local paths, back up managed
files before replacement and roll back on failure. Incompatible upgrades need
confirmation; unknown files are never deleted implicitly.

## Authorization boundaries

- Planning, local rendering, validation and creating review artifacts are part
  of an authorized build.
- Publishing, messaging, spending credits, installing external components or
  exposing a remote endpoint needs the authority appropriate to that action.
- Generated or illustrative media is never presented as documentary proof.
- Human review stays explicit and is never inferred from a passing test.
"""

PUBLIC_AGENT_YAML = """interface:
  display_name: "Hao Video Autopilot"
  short_description: "證據式剪輯、字幕、調色、QA 與發布；成品交由創作者審片"
  default_prompt: "Use $video-autopilot to plan, edit and QA my video from my own footage, then prepare a local review page; start a remote phone review only if I ask for it."
"""


def validate_public_skill(skill_text: str) -> Dict[str, str]:
    """Fail closed if the generated public Skill violates its fixed boundary."""
    identity = validate_canonical_frontmatter(skill_text)
    links = _ANY_REFERENCE_LINK.findall(skill_text)
    malformed = sorted({name for name in links if not _REFERENCE_NAME.fullmatch(name)})
    if malformed:
        raise ValueError(f"public reference link has an unsupported form: {malformed}")
    expected = set(PUBLIC_REFERENCES)
    if set(links) != expected:
        missing = sorted(expected - set(links))
        extra = sorted(set(links) - expected)
        raise ValueError(f"public reference inventory mismatch: missing={missing}, extra={extra}")
    if _ABSOLUTE_PATH.search(skill_text):
        raise ValueError("public Skill contains an absolute local path")
    if _DATED_EVENT.search(skill_text):
        raise ValueError("public Skill contains a dated local event")
    if _LOCAL_PROJECT_ID.search(skill_text):
        raise ValueError("public Skill contains a local project identifier")
    if _LOCAL_METRIC.search(skill_text):
        raise ValueError("public Skill contains a local performance metric")

    brand_neutral = skill_text.replace(PRODUCT_NAME, "")
    brand_neutral = brand_neutral.replace(PROJECT_URL, "")
    brand_neutral = brand_neutral.replace("hao.video-autopilot", "")
    brand_neutral = brand_neutral.replace("hao.motion-composition", "")
    for link in BRANDED_REFERENCE_LINKS:
        brand_neutral = brand_neutral.replace(link, "")
    if re.search(r"\bHao(?:0321)?\b", brand_neutral, re.IGNORECASE):
        raise ValueError("personal identity escaped outside approved product branding")
    return identity


def render_public_agent_yaml() -> str:
    """Return the fixed public agent card; the canonical card stays private."""
    return PUBLIC_AGENT_YAML


def render_public_skill(canonical_text: str) -> str:
    """Return a deterministic public Skill without consuming canonical body text."""
    validate_canonical_frontmatter(canonical_text)
    rendered = (
        "---\n"
        f"name: {SKILL_NAME}\n"
        f"description: {PUBLIC_DESCRIPTION}\n"
        "---\n\n"
        f"{PUBLIC_SKILL_BODY.rstrip()}\n"
    )
    validate_public_skill(rendered)
    return rendered


def _selftest() -> None:
    synthetic = """---
name: video-autopilot
description: Synthetic canonical fixture for testing the public renderer only.
metadata:
  short-description: ignored fixture metadata
---

# LOCAL_SENTINEL

This body must never appear in public output.
"""
    first = render_public_skill(synthetic)
    second = render_public_skill(synthetic.replace("LOCAL_SENTINEL", "SECOND_SENTINEL"))
    assert first == second
    assert "SENTINEL" not in first
    assert first.startswith("---\nname: video-autopilot\n")
    assert PRODUCT_NAME in first and PROJECT_URL in first
    validate_public_skill(first)

    invalid = (
        "description: Synthetic fixture missing a frontmatter fence.\n"
        "name: video-autopilot\n"
    )
    try:
        render_public_skill(invalid)
    except ValueError:
        pass
    else:  # pragma: no cover - regression assertion
        raise AssertionError("missing frontmatter fence must fail closed")

    for injected in ("[x](./references/private-notes.md)", "[x](references/private_notes.md)",
                     "[x](references/craft-index.md#section)"):
        try:
            validate_public_skill(first + "\n" + injected + "\n")
        except ValueError:
            pass
        else:  # pragma: no cover - regression assertion
            raise AssertionError("unlisted or malformed reference link accepted: " + injected)
    assert all(("](references/%s)" % name) in first for name in PUBLIC_REFERENCES)
    assert "Hao" not in render_public_agent_yaml().replace(PRODUCT_NAME, "")

    wrong_name = synthetic.replace("name: video-autopilot", "name: another-skill")
    try:
        render_public_skill(wrong_name)
    except ValueError:
        pass
    else:  # pragma: no cover - regression assertion
        raise AssertionError("unexpected skill name must fail closed")


if __name__ == "__main__":
    _selftest()
    print("public_skill_skeleton selftest OK")
