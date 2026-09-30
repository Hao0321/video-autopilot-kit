"""Explicit creator authority shared by context routing and the v4 controller."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

CREATOR_POLICY_PATH = Path(".autopilot/creator-review-policy.json")


def load_creator_review_policy(workspace: Path, explicit: dict | None = None) -> dict:
    if explicit is not None:
        return normalize_review_policy(explicit)
    path = workspace / CREATOR_POLICY_PATH
    if path.is_file():
        if path.is_symlink() or path.parent.resolve() != workspace.resolve() / '.autopilot':
            raise ValueError("creator review policy must be a local configuration file")
        if path.stat().st_size > 8192:
            raise ValueError("creator review policy exceeds its bounded configuration size")
        return normalize_review_policy(json.loads(path.read_text(encoding="utf-8")))
    return normalize_review_policy()


def normalize_review_policy(value: dict | None = None) -> dict:
    policy = value if value is not None else {"mode": "human"}
    if not isinstance(policy, dict) or set(policy) - {"mode", "authorization"}:
        raise ValueError("review policy must contain only mode and authorization")
    mode = policy.get("mode")
    if mode not in {"human", "agent_reference_comparison"}:
        raise ValueError("unsupported visual review mode")
    authorization = policy.get("authorization", "")
    if not isinstance(authorization, str) or len(authorization) > 2000:
        raise ValueError("review authorization must be bounded text")
    authorization = authorization.strip()
    if mode == "agent_reference_comparison" and not authorization:
        raise ValueError("agent reference review requires explicit creator authorization")
    return {"mode": mode, **({"authorization": authorization} if authorization else {})}


def policy_sha256(policy: dict) -> str:
    normalized = normalize_review_policy(policy)
    return hashlib.sha256(json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def reviewer_actor(policy: dict) -> str:
    return "agent" if normalize_review_policy(policy)["mode"] == "agent_reference_comparison" else "human"


def review_checkpoint(policy: dict) -> str:
    return "agent_review" if reviewer_actor(policy) == "agent" else "human_review"
