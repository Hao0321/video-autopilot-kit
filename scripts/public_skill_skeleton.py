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
    "Plan, build, review, package, release, and improve long-form videos and "
    "vertical shorts with evidence-gated, creator-configurable workflows."
)

# This is intentionally a small, explicit subset of the canonical public
# reference inventory.  Adding a link requires a reviewed source change here;
# arbitrary links from the canonical body can never enter the public Skill.
PUBLIC_REFERENCES = (
    "asset-workshop.md",
    "editorial-intelligence-contract.md",
    "editkin-mobile-device-binding.md",
    "editkin-plugin-automation.md",
    "editkin-workflow-execution.md",
    "model-and-context-adaptation.md",
    "open-source-release-and-upgrade.md",
    "publish-hub-and-remix.md",
    "script-retention-2026.md",
    "storage-lifecycle.md",
    "token-budget-system.md",
)

_FRONTMATTER = re.compile(
    r"\A---[ \t]*\r?\n(?P<header>.*?)\r?\n---(?:[ \t]*\r?\n|\Z)",
    re.DOTALL,
)
_SKILL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_REFERENCE_LINK = re.compile(r"\]\(references/([a-z0-9][a-z0-9-]*\.md)\)")
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

The public project is [{PROJECT_URL}]({PROJECT_URL}). Release archives must be
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
"""


def validate_public_skill(skill_text: str) -> Dict[str, str]:
    """Fail closed if the generated public Skill violates its fixed boundary."""
    identity = validate_canonical_frontmatter(skill_text)
    links = set(_REFERENCE_LINK.findall(skill_text))
    expected = set(PUBLIC_REFERENCES)
    if links != expected:
        missing = sorted(expected - links)
        extra = sorted(links - expected)
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
    if re.search(r"\bHao(?:0321)?\b", brand_neutral, re.IGNORECASE):
        raise ValueError("personal identity escaped outside approved product branding")
    return identity


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
