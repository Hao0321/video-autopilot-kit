"""Explicit creator authority shared by context routing and the v4 controller."""
from __future__ import annotations

import hashlib
import json
import errno
import os
import stat
from pathlib import Path

CREATOR_POLICY_PATH = Path(".autopilot/creator-review-policy.json")
MAX_CREATOR_POLICY_BYTES = 8192


def _is_link_or_reparse(metadata) -> bool:
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _file_identity(metadata) -> tuple:
    return (metadata.st_dev, metadata.st_ino, metadata.st_mode, metadata.st_size,
            metadata.st_mtime_ns, metadata.st_ctime_ns)


def _path_handle_identity(metadata) -> tuple:
    # Compare object binding across APIs; keep complete modification snapshots within each API.
    return (metadata.st_dev, metadata.st_ino, stat.S_IFMT(metadata.st_mode), metadata.st_size)


def _policy_directories(directory: Path) -> list[tuple[Path, tuple]]:
    identities = []
    for current in [*reversed(directory.parents), directory]:
        metadata = current.lstat()
        if _is_link_or_reparse(metadata) or not stat.S_ISDIR(metadata.st_mode):
            raise ValueError("creator review policy authority must use real directories without links or junctions")
        # File creation elsewhere in an ancestor is unrelated; bind directory identity, not its contents.
        identity = (metadata.st_dev, metadata.st_ino, metadata.st_mode, getattr(metadata, "st_file_attributes", 0))
        identities.append((current, identity))
    return identities


def load_creator_review_policy(workspace: Path, explicit: dict | None = None) -> dict:
    if explicit is not None:
        return normalize_review_policy(explicit)
    path = Path(os.path.abspath(workspace)) / CREATOR_POLICY_PATH
    try:
        directories = _policy_directories(path.parent)
        before = path.lstat()
    except OSError as error:
        if error.errno == errno.ENOENT:
            return normalize_review_policy()
        raise
    if _is_link_or_reparse(before) or not stat.S_ISREG(before.st_mode):
        raise ValueError("creator review policy must be a regular local configuration file")
    if before.st_size > MAX_CREATOR_POLICY_BYTES:
        raise ValueError("creator review policy exceeds its bounded configuration size")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or _path_handle_identity(opened) != _path_handle_identity(before):
            raise ValueError("creator review policy changed before its bounded read: "
                             f"pathBinding={_path_handle_identity(before)!r}, handleBinding={_path_handle_identity(opened)!r}; "
                             f"pathMetadata={_file_identity(before)!r}, handleMetadata={_file_identity(opened)!r}")
        payload = stream.read(MAX_CREATOR_POLICY_BYTES + 1)
        after = os.fstat(stream.fileno())
        if len(payload) > MAX_CREATOR_POLICY_BYTES or after.st_size > MAX_CREATOR_POLICY_BYTES:
            raise ValueError("creator review policy exceeds its bounded configuration size")
        if _file_identity(after) != _file_identity(opened) or len(payload) != after.st_size:
            raise ValueError("creator review policy changed during its bounded read: "
                             f"openedMetadata={_file_identity(opened)!r}, afterMetadata={_file_identity(after)!r}; "
                             f"readBytes={len(payload)}, afterBytes={after.st_size}")
        current = path.lstat()
        if (_is_link_or_reparse(current) or _file_identity(current) != _file_identity(before)
                or _path_handle_identity(current) != _path_handle_identity(after)):
            raise ValueError("creator review policy path changed during its bounded read: "
                             f"beforePathMetadata={_file_identity(before)!r}, currentPathMetadata={_file_identity(current)!r}; "
                             f"currentBinding={_path_handle_identity(current)!r}, handleBinding={_path_handle_identity(after)!r}; "
                             f"currentAlias={_is_link_or_reparse(current)!r}")
        current_directories = _policy_directories(path.parent)
        if current_directories != directories:
            raise ValueError("creator review policy directory authority changed during its bounded read: "
                             f"before={directories!r}, current={current_directories!r}")
    value = json.loads(payload.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("creator review policy configuration must be a JSON object")
    return normalize_review_policy(value)


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
