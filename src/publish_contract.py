# -*- coding: utf-8 -*-
"""Closed-world delivery contract for completed video artifacts.

Package validation alone is an open-world check: it proves that packages which
exist are internally valid, but it cannot prove that every completed render was
registered.  This module closes that gap for Shorts and keeps the rule small,
pure and task-shaped enough to regression-test without a real media library.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Iterable


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def desired_short_status(qa: dict[str, Any]) -> str:
    """Return the honest hub bucket for a successful technical build.

    Human review is evidence, not decoration.  A technically green build is
    registered immediately so it is discoverable, but it remains ``review``
    until the quality ledger is certified.
    """
    if qa.get("all_green") is not True and qa.get("deliver_ok") is not True:
        raise RuntimeError("Video build is not technically green; delivery is blocked")
    autonomy = qa.get("autonomy") or {}
    if autonomy.get("publish_allowed") is True and str(
            autonomy.get("certification") or "") == "CREATOR_REVIEW_REQUIRED":
        raise RuntimeError("unattended assessment cannot authorize publishing")
    quality_status = str((qa.get("quality_95") or {}).get("status") or "REVIEW").upper()
    # Only the explicit certified ledger status is certification; GREEN/PASS are machine words.
    return "ready" if quality_status == "CERTIFIED_95" else "review"


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _folder_content_id(folder: str, content_prefix: str, split_ids: bool) -> str | None:
    """Map ``7`` to ``S007`` and, when enabled, split-battle ``12-1`` to ``S012-1``."""
    if folder.isdigit():
        return f"{content_prefix}{int(folder):03d}"
    head, sep, tail = folder.partition("-")
    if split_ids and sep and head.isdigit() and tail and all(
            part.isdigit() for part in tail.split("-")):
        return f"{content_prefix}{int(head):03d}-{tail}"
    return None


def canonical_completion_failures(*, root: Path, media_root: Path,
                                  manifests: Iterable[Path], format_name: str,
                                  content_prefix: str,
                                  split_ids: bool = False) -> list[dict[str, Any]]:
    """Report orphan, duplicate, stale and split-source completed artifacts.

    The authoritative completed artifact is ``<id>/_out/current.mp4``.  Every
    such file must have exactly one hub manifest with the same content hash and
    canonical source path.  Other working media are negative controls and are
    intentionally ignored.  ``split_ids`` includes split-battle folders
    (``12-1`` -> ``S012-1``) exactly as the publishing hub registers them.
    """
    by_id: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    for manifest in manifests:
        try:
            row = json.loads(manifest.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue  # package validation owns malformed JSON reporting
        if str(row.get("format") or "").lower() != format_name.lower():
            continue
        by_id.setdefault(str(row.get("content_id") or ""), []).append((manifest, row))

    failures: list[dict[str, Any]] = []
    candidates = sorted(media_root.glob("*/_out/current.mp4")) if media_root.exists() else []
    for current in candidates:
        content_id = _folder_content_id(current.parent.parent.name, content_prefix, split_ids)
        if content_id is None:
            continue  # not a hub content id (working folder); never a publish obligation
        packages = by_id.get(content_id, [])
        if not packages:
            failures.append({
                "id": content_id,
                "error": "completed current.mp4 is not registered in the publishing hub",
                "source": _relative(current, root),
            })
            continue
        if len(packages) != 1:
            failures.append({
                "id": content_id,
                "error": "completed output resolves to multiple publishing packages",
                "packages": [_relative(path.parent, root) for path, _row in packages],
            })
            continue
        manifest, row = packages[0]
        actual_hash = sha256(current)
        if str(row.get("sha256") or "").lower() != actual_hash:
            failures.append({
                "id": content_id,
                "error": "publishing package is stale relative to current.mp4",
                "source": _relative(current, root),
                "package": _relative(manifest.parent, root),
            })
        expected_source = _relative(current, root)
        if str(row.get("canonical_source") or "") != expected_source:
            failures.append({
                "id": content_id,
                "error": "publishing package points at a non-canonical completed source",
                "expected": expected_source,
                "actual": row.get("canonical_source"),
            })
    return failures


def completion_failures(*, root: Path, shorts_root: Path,
                        manifests: Iterable[Path]) -> list[dict[str, Any]]:
    """Compatibility wrapper for the Shorts closed-world contract (base and split-battle ids)."""
    return canonical_completion_failures(
        root=root, media_root=shorts_root, manifests=manifests,
        format_name="shorts", content_prefix="S", split_ids=True,
    )


def longform_completion_failures(*, root: Path, longform_root: Path,
                                 manifests: Iterable[Path]) -> list[dict[str, Any]]:
    return canonical_completion_failures(
        root=root, media_root=longform_root, manifests=manifests,
        format_name="longform", content_prefix="L",
    )


def selftest() -> None:
    with tempfile.TemporaryDirectory(prefix="publish-contract-") as temporary:
        root = Path(temporary)
        shorts = root / "videos" / "_INBOX" / "vertical"
        current = shorts / "7" / "_out" / "current.mp4"
        current.parent.mkdir(parents=True)
        current.write_bytes(b"gold-render")

        # Positive failure fixture: an existing completed render cannot vanish
        # merely because the package validator only sees existing packages.
        missing = completion_failures(root=root, shorts_root=shorts, manifests=[])
        assert len(missing) == 1 and missing[0]["id"] == "S007"

        package = root / "videos" / "_PUBLISH_HUB" / "READY" / "shorts" / "ready" / "S007"
        package.mkdir(parents=True)
        manifest = package / "publish.json"
        manifest.write_text(json.dumps({
            "content_id": "S007", "format": "shorts", "sha256": sha256(current),
            "canonical_source": _relative(current, root),
        }), encoding="utf-8")
        assert completion_failures(root=root, shorts_root=shorts, manifests=[manifest]) == []

        # Stale-package fixture plus a real negative control.  Non-current
        # working files must not become fake publish obligations.
        (current.parent / "preview.mp4").write_bytes(b"negative-control")
        current.write_bytes(b"new-render")
        stale = completion_failures(root=root, shorts_root=shorts, manifests=[manifest])
        assert len(stale) == 1 and "stale" in stale[0]["error"]

    assert desired_short_status({"all_green": True, "quality_95": {"status": "REVIEW"}}) == "review"
    assert desired_short_status({"all_green": True, "quality_95": {"status": "REVIEW"},
                                 "autonomy": {"status": "AUTO_CANDIDATE",
                                              "certification": "CREATOR_REVIEW_REQUIRED",
                                              "publish_allowed": False}}) == "review"
    try:
        desired_short_status({"all_green": True, "quality_95": {"status": "REVIEW"},
                              "autonomy": {"certification": "CREATOR_REVIEW_REQUIRED",
                                           "publish_allowed": True}})
    except RuntimeError:
        pass
    else:
        raise AssertionError("unattended assessment must never authorize publishing")
    assert desired_short_status({"all_green": True, "quality_95": {"status": "CERTIFIED_95"}}) == "ready"
    try:
        desired_short_status({"all_green": False})
    except RuntimeError:
        pass
    else:
        raise AssertionError("red build must not enter publishing hub")
    _selftest_closed_world()
    print("publish_contract self-test GREEN")


def _selftest_closed_world() -> None:
    """Only CERTIFIED_95 certifies; split-battle renders are obligations, work dirs are not."""
    for machine_word in ("GREEN", "PASS", "CERTIFIED", "APPROVED"):
        assert desired_short_status({"all_green": True,
                                     "quality_95": {"status": machine_word}}) == "review"
    with tempfile.TemporaryDirectory(prefix="publish-contract-split-") as temporary:
        root = Path(temporary)
        shorts = root / "videos" / "_INBOX" / "vertical"
        for folder, payload in (("12-1", b"split-render"), ("draft", b"working-folder")):
            render = shorts / folder / "_out" / "current.mp4"
            render.parent.mkdir(parents=True)
            render.write_bytes(payload)
        orphans = completion_failures(root=root, shorts_root=shorts, manifests=[])
        assert [row["id"] for row in orphans] == ["S012-1"], orphans
        split = shorts / "12-1" / "_out" / "current.mp4"
        manifest = root / "hub" / "S012-1" / "publish.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({
            "content_id": "S012-1", "format": "shorts", "sha256": sha256(split),
            "canonical_source": _relative(split, root),
        }), encoding="utf-8")
        assert completion_failures(root=root, shorts_root=shorts, manifests=[manifest]) == []
        # Long-form ids stay numeric; split folders are a Shorts-only identity.
        assert longform_completion_failures(root=root, longform_root=shorts, manifests=[]) == []


if __name__ == "__main__":
    selftest()
