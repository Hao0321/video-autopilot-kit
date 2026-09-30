"""Creator-authorized, artifact-bound agent reference review. Never human approval."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

DIMENSIONS = (
    "typography", "readability", "focus", "color", "spacing",
    "source_semantics", "occlusion", "edges", "motion", "section_flow",
)


def validate_agent_review(review: dict[str, Any], policy: dict[str, Any]) -> dict:
    errors = []
    if policy.get("mode") != "agent_reference_comparison" or not str(policy.get("authorization", "")).strip():
        errors.append("explicit creator authorization for agent reference review is required")
    if review.get("schema") != "video-autopilot.agent-art-review/v1" or review.get("reviewer") != "agent":
        errors.append("agent review schema/reviewer is missing")
    if review.get("status") not in ("PASSED", "REVIEW", "BLOCKED"):
        errors.append("review must retain PASSED/REVIEW/BLOCKED")
    if not review.get("rendererIdentity") or not review.get("projectSha256"):
        errors.append("project and renderer identities are required")
    try:
        path = Path(review["outputPath"])
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != review.get("outputSha256"):
            errors.append("reviewed output has changed")
    except (OSError, KeyError, TypeError):
        errors.append("reviewed output is unavailable")
    coverage = review.get("coverage") or {}
    frame_count = coverage.get("totalFrames")
    if not isinstance(frame_count, int) or isinstance(frame_count, bool) or frame_count < 1:
        errors.append("valid full-section frame count is required")
    if coverage.get("fullDecodeExitCode") != 0 or coverage.get("decodedFrames") != frame_count:
        errors.append("full decode must cover the same artifact")
    if not coverage.get("continuousMotionObserved") or not coverage.get("reviewedAt"):
        errors.append("continuous motion observation and timestamp are required")
    references = review.get("references") or []
    if not references or any(not isinstance(ref, str) or not ref.strip() for ref in references):
        errors.append("actual reference observations are required")
    observations = review.get("observations") or []
    for name in DIMENSIONS:
        rows = [row for row in observations if isinstance(row, dict) and row.get("dimension") == name]
        if not rows:
            errors.append("missing observation: " + name)
        for row in rows:
            start, end = row.get("startFrame"), row.get("endFrame")
            if (not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool)
                    or not isinstance(frame_count, int) or not 0 <= start <= end < frame_count):
                errors.append("invalid observation frame range: " + name)
            if row.get("verdict") not in ("PASS", "REVISE", "BLOCK") or not str(row.get("detail", "")).strip():
                errors.append("specific visual finding required: " + name)
    verdicts = {row.get("verdict") for row in observations if isinstance(row, dict)}
    if review.get("status") == "PASSED" and (errors or verdicts != {"PASS"}):
        errors.append("a passing review cannot contain gaps or visible defects")
    status = "BLOCKED" if review.get("status") == "BLOCKED" or "BLOCK" in verdicts else "REVIEW" if errors or "REVISE" in verdicts else review.get("status", "REVIEW")
    return {"status": status, "completed": not errors and status == "PASSED", "reviewer": "agent",
            "mode": "agent_reference_comparison", "errors": errors, "outputSha256": review.get("outputSha256"),
            "observations": observations, "references": references}
