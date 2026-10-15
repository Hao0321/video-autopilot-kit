# -*- coding: utf-8 -*-
"""Manifest-driven control plane for Video Autopilot.

The kernel audits architecture, capacity and installed-skill drift.  It does
not edit or delete media.  Existing builders remain independent execution
modules behind this control plane.
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from project_paths import MANIFEST_NAMES, discover_project_root


from project_source_metrics import (
    ABSOLUTE_LITERAL,
    TEXT_EXTS,
    _read_json,
    _ignored,
    _line_count,
    _effective_function_lines,
    _literalish,
    _effective_module_lines,
    _directory_metrics,
    _python_metrics,
    _function_findings,
    _large_file_finding,
    source_audit as _source_audit,
)
SYNC_MARKER_NAME = ".video-autopilot-skill.json"
SKILL_PATH_ENV = "EDITKIN_VIDEO_AUTOPILOT_SKILL"


def load_manifest(root: str | os.PathLike | None = None) -> tuple[Path, dict]:
    workspace = Path(root).expanduser().resolve() if root else discover_project_root()
    path = next((workspace / name for name in MANIFEST_NAMES
                 if (workspace / name).is_file()), workspace / MANIFEST_NAMES[0])
    data = _read_json(path)
    if data.get("schema_version") != 2 or not data.get("project_id"):
        raise ValueError(f"Unsupported or incomplete manifest: {path}")
    return workspace, data


def source_audit(root: str | os.PathLike | None = None) -> dict:
    workspace, manifest = load_manifest(root)
    return _source_audit(workspace, manifest)


def inventory(root: str | os.PathLike | None = None) -> dict:
    workspace, manifest = load_manifest(root)
    rows = {}
    for key, relative in manifest.get("roots", {}).items():
        rows[key] = _directory_metrics(workspace / relative)
    return {"root": str(workspace), "roots": rows}


def knowledge_audit(root: str | os.PathLike | None = None) -> dict:
    workspace, manifest = load_manifest(root)
    rows = []
    for relative, policy in manifest.get("budgets", {}).get("knowledge_lines", {}).items():
        path = workspace / relative
        lines = _line_count(path) if path.is_file() else 0
        frozen = str(policy.get("policy", "")).startswith("legacy-freeze")
        rows.append({
            "path": relative,
            "lines": lines,
            "warning": int(policy["warning"]),
            "rotate": int(policy["rotate"]),
            "state": "FROZEN" if frozen else (
                "ROTATE" if lines >= int(policy["rotate"]) else (
                    "WARN" if lines >= int(policy["warning"]) else "OK"
                )
            ),
            "policy": policy.get("policy", "archive-before-rewrite"),
        })
    return {"files": rows}


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sync_hash(path: Path) -> str:
    """Compare Skill text portably across Git's LF/CRLF checkouts."""
    payload = path.read_bytes()
    if b"\x00" not in payload:
        payload = payload.replace(b"\r\n", b"\n")
    return hashlib.sha256(payload).hexdigest()


def _skill_source(workspace: Path, skill: dict) -> Path:
    authority = skill.get("source_authority")
    if not authority:
        return (workspace / skill["source"]).resolve()
    if not isinstance(authority, dict) or authority.get("kind") != "codex-canonical":
        raise ValueError(f"Unsupported Skill source authority for {skill.get('id')}: {authority!r}")
    env_name = str(authority.get("environment") or SKILL_PATH_ENV)
    explicit = str(os.environ.get(env_name, "")).strip()
    if explicit:
        skill_path = Path(explicit).expanduser()
        if not skill_path.is_absolute():
            raise ValueError(f"{env_name} must be an absolute SKILL.md path")
    else:
        skill_path = Path.home() / ".codex" / "skills" / str(skill["destination"]) / "SKILL.md"
    skill_path = skill_path.resolve()
    if not skill_path.is_file():
        raise FileNotFoundError(f"Canonical Skill is missing: {skill_path}")
    if not re.search(rf"^name:\s*{re.escape(str(skill['id']))}\s*$", skill_path.read_text(encoding="utf-8-sig"), re.MULTILINE):
        raise ValueError(f"Canonical Skill identity mismatch: {skill_path}")
    if skill["id"] == "video-autopilot" and not skill_path.with_name("workflow_contract.json").is_file():
        raise FileNotFoundError(f"Canonical workflow contract is missing beside SKILL.md: {skill_path.parent}")
    return skill_path.parent


def _sync_files(workspace: Path, skill: dict) -> list[Path]:
    source = _skill_source(workspace, skill)
    found: dict[str, Path] = {}
    for pattern in skill.get("include", []):
        for path in source.glob(pattern):
            if path.is_file():
                found[path.relative_to(source).as_posix()] = path
    return [found[key] for key in sorted(found)]


def _atomic_json(path: Path, payload: dict) -> None:
    """Write sync state without exposing a partially written marker."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _read_sync_marker(destination: Path) -> tuple[dict, str, str | None]:
    marker = destination / SYNC_MARKER_NAME
    if not marker.is_file():
        return {}, "MISSING", None
    try:
        state = _read_json(marker)
        hashes = state.get("managed_hashes")
        if not isinstance(hashes, dict):
            raise ValueError("managed_hashes must be an object")
        managed = state.get("managed_files")
        if not isinstance(managed, list) or not all(isinstance(item, str) for item in managed):
            raise ValueError("managed_files must be a string array")
        return state, "VALID", None
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        return {}, "INVALID", str(error)


def _sync_row_status(missing: list[str], drift: list[str], conflict: list[str]) -> str:
    if conflict:
        return "CONFLICT"
    if drift:
        return "DRIFT"
    if missing:
        return "MISSING"
    return "GREEN"


def _skill_sync_status(workspace: Path, skill: dict, destination: Path) -> dict:
    source = _skill_source(workspace, skill)
    same_tree = source.resolve() == destination.resolve()
    marker_state, marker_status, marker_error = _read_sync_marker(destination)
    baselines = marker_state.get("managed_hashes", {})
    missing, drift, conflict, different, metadata_drift = [], [], [], [], []
    matched = 0
    files = _sync_files(workspace, skill)
    declared = [path.relative_to(source).as_posix() for path in files]
    for src in files:
        relative = src.relative_to(source).as_posix()
        target = destination / relative
        if not target.is_file():
            # A missing managed file is safe to restore and is not treated as a
            # local edit. Destination-only content outside this list is untouched.
            missing.append(relative)
            continue
        source_hash = _sync_hash(src)
        target_hash = _sync_hash(target)
        if source_hash == target_hash:
            matched += 1
            if same_tree:
                baseline = baselines.get(relative)
                baseline = str(baseline).lower() if isinstance(baseline, str) else None
                if baseline not in {target_hash.lower(), _hash(target).lower()}:
                    metadata_drift.append(relative)
            continue
        different.append(relative)
        baseline = baselines.get(relative)
        baseline = str(baseline).lower() if isinstance(baseline, str) else None
        # release_manager.py records raw hashes while this kernel records
        # newline-normalized hashes for portable LF/CRLF sync. Accept either
        # representation so both writers remain marker-compatible.
        target_baselines = {target_hash.lower(), _hash(target).lower()}
        if baseline and baseline in target_baselines:
            # Only the canonical source changed since the last managed sync.
            drift.append(relative)
        else:
            # No baseline, a destination-only change, and a both-sides change
            # are deliberately indistinguishable from valuable local work.
            conflict.append(relative)
    metadata_scope_drift = []
    if same_tree and marker_status == "VALID":
        metadata_scope_drift = sorted(set(declared) ^ set(marker_state.get("managed_files", [])))
    status = _sync_row_status(missing, drift + metadata_drift + metadata_scope_drift, conflict)
    if same_tree and marker_status != "VALID" and status == "GREEN":
        status = "MISSING"
    return {
        "id": skill["id"],
        "status": status,
        "source": str(source),
        "destination": str(destination),
        "marker": str(destination / SYNC_MARKER_NAME),
        "marker_status": marker_status,
        "marker_error": marker_error,
        "declared_files": len(files),
        "matched": matched,
        "missing": missing,
        "drift": drift,
        "conflict": conflict,
        "metadata_drift": sorted(set(metadata_drift + metadata_scope_drift)),
        # Keep the legacy field for callers that only know matched/different.
        "different": different,
    }


def _aggregate_sync_status(results: list[dict]) -> str:
    statuses = {row["status"] for row in results}
    for status in ("CONFLICT", "DRIFT", "MISSING"):
        if status in statuses:
            return status
    return "GREEN" if results else "RED"


def sync_status(root: str | os.PathLike | None = None, skill_id: str | None = None) -> dict:
    workspace, manifest = load_manifest(root)
    results = []
    for skill in manifest.get("skills", []):
        if skill_id and skill["id"] != skill_id:
            continue
        destination = Path.home() / ".codex" / "skills" / skill["destination"]
        results.append(_skill_sync_status(workspace, skill, destination))
    return {
        "status": _aggregate_sync_status(results),
        "skills": results,
        "policy": (
            "additive and fail-closed; destination extras are never deleted; "
            "unbaselined or locally modified files require explicit source acceptance"
        ),
    }


def _skill_sync_apply(
    workspace: Path,
    skill: dict,
    destination: Path,
    *,
    accept_source_conflicts: bool = False,
) -> dict:
    before = _skill_sync_status(workspace, skill, destination)
    if before["conflict"] and not accept_source_conflicts:
        return {
            "status": "CONFLICT",
            "copied": 0,
            "blocked": before["conflict"],
            "accepted_source_conflicts": False,
        }

    source = _skill_source(workspace, skill)
    destination.mkdir(parents=True, exist_ok=True)
    copied = 0
    managed = []
    for src in _sync_files(workspace, skill):
        relative = src.relative_to(source).as_posix()
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file() or _sync_hash(src) != _sync_hash(target):
            shutil.copy2(src, target)
            copied += 1
        managed.append(relative)

    _atomic_json(
        destination / SYNC_MARKER_NAME,
        {
            "schema_version": 1,
            "managed_by": "hao-autopilot-project-kernel",
            "skill_id": skill["id"],
            "source": str(source.resolve()),
            "source_authority": skill.get("source_authority", {"kind": "workspace"}),
            "managed_files": managed,
            "managed_hashes": {
                relative: _sync_hash(destination / relative) for relative in managed
            },
            "synced_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    after = _skill_sync_status(workspace, skill, destination)
    return {
        "status": after["status"],
        "copied": copied,
        "blocked": [],
        "accepted_source_conflicts": bool(before["conflict"] and accept_source_conflicts),
    }


def sync_apply(
    root: str | os.PathLike | None = None,
    skill_id: str | None = None,
    *,
    accept_source_conflicts: bool = False,
) -> dict:
    workspace, manifest = load_manifest(root)
    copied, blocked, accepted = {}, {}, {}
    for skill in manifest.get("skills", []):
        if skill_id and skill["id"] != skill_id:
            continue
        destination = Path.home() / ".codex" / "skills" / skill["destination"]
        applied = _skill_sync_apply(
            workspace,
            skill,
            destination,
            accept_source_conflicts=accept_source_conflicts,
        )
        copied[skill["id"]] = applied["copied"]
        blocked[skill["id"]] = applied["blocked"]
        accepted[skill["id"]] = applied["accepted_source_conflicts"]
    result = sync_status(workspace, skill_id)
    result["copied"] = copied
    result["blocked"] = blocked
    result["accepted_source_conflicts"] = accepted
    return result


def _source_warnings(sources: dict) -> list[str]:
    warnings = []
    if sources["absolute_path_files"]:
        warnings.append(f"portable-path debt in {len(sources['absolute_path_files'])} active files")
    severe = [row for row in sources["large_files"] if row["level"] == "severe"]
    severe_functions = [row for row in sources["large_functions"] if row["level"] == "severe"]
    if severe:
        warnings.append(f"{len(severe)} source files exceed severe line budget")
    elif sources["large_files"]:
        warnings.append(f"{len(sources['large_files'])} modules/references remain above refactor warning budget")
    if severe_functions:
        warnings.append(f"{len(severe_functions)} functions exceed 100-line severe budget")
    return warnings


def _knowledge_warnings(knowledge: dict) -> list[str]:
    warnings = []
    rotate = [row for row in knowledge["files"] if row["state"] == "ROTATE"]
    warn_knowledge = [row for row in knowledge["files"] if row["state"] == "WARN"]
    if rotate:
        warnings.append(f"{len(rotate)} knowledge files reached rotation threshold")
    elif warn_knowledge:
        warnings.append(f"{len(warn_knowledge)} knowledge files near rotation threshold")
    return warnings


def _storage_warnings(sizes: dict, manifest: dict) -> list[str]:
    warnings = []
    storage_budget = manifest.get("budgets", {}).get("storage_gb", {})
    videos_gb = sizes["roots"].get("videos", {}).get("gb", 0)
    videos_logical_gb = sizes["roots"].get("videos", {}).get("logical_gb", videos_gb)
    videos_saved_gb = round(
        sizes["roots"].get("videos", {}).get("hardlink_saved_bytes", 0) / (1024 ** 3), 3
    )
    assets_gb = sizes["roots"].get("assets", {}).get("gb", 0)
    if videos_gb >= float(storage_budget.get("videos_warning", 12)):
        warnings.append(
            f"videos physical storage {videos_gb}GB reached warning budget "
            f"(logical {videos_logical_gb}GB; hardlinks save {videos_saved_gb}GB)"
        )
    if assets_gb >= float(storage_budget.get("assets_warning", 5)):
        warnings.append(f"assets storage {assets_gb}GB reached warning budget")
    return warnings


def doctor(root: str | os.PathLike | None = None, *, quick: bool = False) -> dict:
    workspace, manifest = load_manifest(root)
    errors = [
        f"missing required path: {relative}"
        for relative in manifest.get("required_paths", [])
        if not (workspace / relative).exists()
    ]
    sources = source_audit(workspace)
    knowledge = knowledge_audit(workspace)
    sizes = inventory(workspace)
    warnings = (
        _source_warnings(sources)
        + _knowledge_warnings(knowledge)
        + _storage_warnings(sizes, manifest)
    )

    sync = sync_status(workspace)
    if sync["status"] != "GREEN":
        warnings.append("installed skill copy is absent or differs; run project_kernel.py sync apply")

    return {
        "status": "GREEN" if not errors else "RED",
        "root": str(workspace),
        "architecture_version": manifest.get("architecture_version"),
        "errors": errors,
        "warnings": warnings,
        "source_audit": sources if not quick else {
            "scanned": sources["scanned"],
            "large_count": len(sources["large_files"]),
            "large_function_count": len(sources["large_functions"]),
            "absolute_path_count": len(sources["absolute_path_files"]),
        },
        "knowledge": knowledge,
        "storage": sizes["roots"],
        "sync": sync,
    }


def _self_test_sync(temp: Path) -> None:
    from project_kernel_commands import _self_test_sync as _implementation
    return _implementation(globals(), temp)


def self_test() -> None:
    from project_kernel_commands import self_test as _implementation
    return _implementation(globals())


def _print_human(result: dict, label: str) -> None:
    print(f"{label} {result.get('status', 'GREEN')}")
    if "architecture_version" in result:
        print(f"architecture={result['architecture_version']} root={result['root']}")
    for item in result.get("errors", []):
        print(f"[RED] {item}")
    for item in result.get("warnings", []):
        print(f"[WARN] {item}")


def main(argv: list[str] | None = None) -> int:
    from project_kernel_commands import main as _implementation
    return _implementation(globals(), argv)


if __name__ == "__main__":
    raise SystemExit(main())
