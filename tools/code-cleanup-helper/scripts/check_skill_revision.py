#!/usr/bin/env python3
"""Capture or verify one consistent revision across canonical active-private Skill roots."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable


ALGORITHM = "skill-revision-sha256-v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
IGNORED_PARTS = {
    ".git", ".rd", "__pycache__", ".skill-staging", ".skill-proposals",
}
IGNORED_NAMES = {".DS_Store", "Thumbs.db"}
Scanner = Callable[[list[Path]], tuple[list[dict[str, Any]], dict[str, Any]]]


class RevisionError(RuntimeError):
    """The canonical Skill roots cannot produce a trustworthy stable revision."""


class RevisionUnstable(RevisionError):
    """Canonical bytes changed during every bounded two-pass capture."""


def _ignored(relative: Path) -> bool:
    return (
        any(part.casefold() in {item.casefold() for item in IGNORED_PARTS} for part in relative.parts)
        or relative.name.casefold() in {item.casefold() for item in IGNORED_NAMES}
        or relative.suffix.lower() in {".pyc", ".pyo"}
    )


def _tree(root: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    if not root.is_dir() or not (root / "SKILL.md").is_file():
        raise RevisionError(f"canonical Skill root is missing SKILL.md: {root}")
    inventory: list[dict[str, Any]] = []
    seen: dict[str, str] = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
        relative_path = path.relative_to(root)
        if _ignored(relative_path):
            continue
        if path.is_symlink():
            raise RevisionError(f"canonical Skill tree contains a symlink: {path}")
        if not path.is_file():
            continue
        relative = relative_path.as_posix()
        folded = relative.casefold()
        if folded in seen:
            raise RevisionError(
                f"case-insensitive duplicate Skill paths: {seen[folded]} and {relative}"
            )
        seen[folded] = relative
        before = path.stat()
        payload = path.read_bytes()
        after = path.stat()
        if (
            (before.st_size, before.st_mtime_ns, before.st_ino)
            != (after.st_size, after.st_mtime_ns, after.st_ino)
            or len(payload) != after.st_size
        ):
            raise RevisionUnstable(f"canonical Skill file changed while being read: {relative}")
        inventory.append({
            "path": relative,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
    digest = hashlib.sha256()
    for entry in inventory:
        digest.update(entry["path"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(entry["bytes"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(entry["sha256"].encode("ascii"))
        digest.update(b"\0")
    return {
        "root": str(root),
        "files": len(inventory),
        "bytes": sum(entry["bytes"] for entry in inventory),
        "sha256": digest.hexdigest(),
        "inventory": inventory,
    }


def scan_roots(roots: list[Path]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not roots:
        raise RevisionError("at least one canonical Skill root is required")
    resolved: dict[str, Path] = {}
    for root in roots:
        absolute = root.resolve(strict=True)
        key = os.path.normcase(str(absolute))
        if key in resolved:
            raise RevisionError(f"duplicate canonical Skill root: {absolute}")
        resolved[key] = absolute
    records = [_tree(root) for root in sorted(resolved.values(), key=lambda item: str(item).casefold())]
    digest = hashlib.sha256()
    for record in records:
        digest.update(record["root"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(record["sha256"].encode("ascii"))
        digest.update(b"\0")
    snapshot = {
        "algorithm": ALGORITHM,
        "roots": len(records),
        "files": sum(record["files"] for record in records),
        "bytes": sum(record["bytes"] for record in records),
        "sha256": digest.hexdigest(),
    }
    return records, snapshot


def capture_consistent(
    roots: list[Path], max_attempts: int = 3, scanner: Scanner = scan_roots
) -> tuple[list[dict[str, Any]], dict[str, Any], int]:
    if max_attempts < 1:
        raise RevisionError("max attempts must be positive")
    last: tuple[dict[str, Any], dict[str, Any]] | None = None
    for attempt in range(1, max_attempts + 1):
        first_roots, first = scanner(roots)
        second_roots, second = scanner(roots)
        if first == second and first_roots == second_roots:
            return second_roots, second, attempt
        last = (first, second)
    before = last[0].get("sha256") if last else "unknown"
    after = last[1].get("sha256") if last else "unknown"
    raise RevisionUnstable(
        f"canonical Skill roots changed during {max_attempts} bounded capture attempt(s): "
        f"{before} -> {after}"
    )


def capture_document(roots: list[Path], max_attempts: int = 3) -> dict[str, Any]:
    records, snapshot, attempts = capture_consistent(roots, max_attempts=max_attempts)
    return {
        "schemaVersion": 1,
        "status": "CAPTURED",
        "roots": records,
        "snapshot": snapshot,
        "captureAttempts": attempts,
        "ignoredProposalDirectories": [".skill-proposals", ".skill-staging"],
    }


def _changes(before_roots: list[dict[str, Any]], after_roots: list[dict[str, Any]]) -> dict[str, Any]:
    before = {os.path.normcase(item["root"]): item for item in before_roots}
    after = {os.path.normcase(item["root"]): item for item in after_roots}
    return {
        "addedRoots": sorted(after[key]["root"] for key in after.keys() - before.keys()),
        "removedRoots": sorted(before[key]["root"] for key in before.keys() - after.keys()),
        "changedRoots": sorted(
            after[key]["root"] for key in before.keys() & after.keys()
            if before[key]["sha256"] != after[key]["sha256"]
        ),
    }


def _valid_relative(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise RevisionError("saved inventory path must be a non-empty POSIX path")
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise RevisionError(f"saved inventory path escapes its Skill root: {value}")
    return value


def validate_evidence(evidence: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not isinstance(evidence, dict) or evidence.get("schemaVersion") != 1 or evidence.get("status") != "CAPTURED":
        raise RevisionError("saved Skill revision uses an unsupported contract")
    saved_roots = evidence.get("roots")
    saved_snapshot = evidence.get("snapshot")
    if not isinstance(saved_roots, list) or not saved_roots or not isinstance(saved_snapshot, dict):
        raise RevisionError("saved Skill revision is missing roots or snapshot")
    normalized: list[dict[str, Any]] = []
    seen_roots: set[str] = set()
    aggregate = hashlib.sha256()
    for index, record in enumerate(saved_roots):
        if not isinstance(record, dict):
            raise RevisionError(f"saved roots[{index}] must be an object")
        root = record.get("root")
        inventory = record.get("inventory")
        if not isinstance(root, str) or not Path(root).is_absolute() or not isinstance(inventory, list):
            raise RevisionError(f"saved roots[{index}] has an invalid root or inventory")
        root = str(Path(root).resolve())
        root_key = os.path.normcase(root)
        if root_key in seen_roots:
            raise RevisionError(f"saved revision has duplicate root: {root}")
        seen_roots.add(root_key)
        entries: list[dict[str, Any]] = []
        seen_paths: set[str] = set()
        tree_digest = hashlib.sha256()
        for entry_index, entry in enumerate(inventory):
            if not isinstance(entry, dict):
                raise RevisionError(f"saved inventory[{entry_index}] must be an object")
            relative = _valid_relative(entry.get("path"))
            size = entry.get("bytes")
            sha256 = entry.get("sha256")
            if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                raise RevisionError(f"saved inventory[{entry_index}].bytes is invalid")
            if not isinstance(sha256, str) or not SHA256_RE.fullmatch(sha256):
                raise RevisionError(f"saved inventory[{entry_index}].sha256 is invalid")
            folded = relative.casefold()
            if folded in seen_paths:
                raise RevisionError(f"saved revision has case-insensitive duplicate path: {relative}")
            seen_paths.add(folded)
            normalized_entry = {"path": relative, "bytes": size, "sha256": sha256}
            entries.append(normalized_entry)
            tree_digest.update(relative.encode("utf-8"))
            tree_digest.update(b"\0")
            tree_digest.update(str(size).encode("ascii"))
            tree_digest.update(b"\0")
            tree_digest.update(sha256.encode("ascii"))
            tree_digest.update(b"\0")
        tree_sha256 = tree_digest.hexdigest()
        expected = {
            "root": root,
            "files": len(entries),
            "bytes": sum(entry["bytes"] for entry in entries),
            "sha256": tree_sha256,
            "inventory": entries,
        }
        if record != expected:
            raise RevisionError(f"saved roots[{index}] summary does not match its inventory")
        normalized.append(expected)
    normalized.sort(key=lambda item: item["root"].casefold())
    for record in normalized:
        aggregate.update(record["root"].encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(record["sha256"].encode("ascii"))
        aggregate.update(b"\0")
    expected_snapshot = {
        "algorithm": ALGORITHM,
        "roots": len(normalized),
        "files": sum(record["files"] for record in normalized),
        "bytes": sum(record["bytes"] for record in normalized),
        "sha256": aggregate.hexdigest(),
    }
    if saved_snapshot != expected_snapshot:
        raise RevisionError("saved aggregate snapshot does not match its root inventories")
    return normalized, expected_snapshot


def verify_document(evidence: dict[str, Any], roots: list[Path] | None = None, max_attempts: int = 3) -> dict[str, Any]:
    saved_roots, saved_snapshot = validate_evidence(evidence)
    selected = roots or [Path(item["root"]) for item in saved_roots if isinstance(item, dict) and item.get("root")]
    current_roots, current_snapshot, attempts = capture_consistent(selected, max_attempts=max_attempts)
    status = "CURRENT" if current_snapshot == saved_snapshot and current_roots == saved_roots else "STALE"
    return {
        "schemaVersion": 1,
        "status": status,
        "roots": current_roots,
        "snapshot": current_snapshot,
        "captureAttempts": attempts,
        "changes": _changes(saved_roots, current_roots),
    }


def _write(path: Path | None, document: dict[str, Any], quiet: bool) -> None:
    payload = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if path:
        path = path.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        os.close(handle)
        temporary_path = Path(temporary)
        try:
            temporary_path.write_text(payload, encoding="utf-8")
            os.replace(temporary_path, path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
    if not quiet:
        print(payload, end="")


def run_self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="skill-revision-") as raw:
        base = Path(raw)
        first = base / "first"
        second = base / "second"
        for root, name in ((first, "first"), (second, "second")):
            (root / "references").mkdir(parents=True)
            (root / "SKILL.md").write_text(f"---\nname: {name}\n---\n", encoding="utf-8")
            (root / "references" / "rules.md").write_text("stable\n", encoding="utf-8")
        captured = capture_document([first, second])
        if verify_document(captured)["status"] != "CURRENT":
            raise AssertionError("unchanged multi-Skill revision was rejected")

        for ignored in (first / ".rd" / "evidence.json", first / ".skill-staging" / "draft.md"):
            ignored.parent.mkdir(parents=True, exist_ok=True)
            ignored.write_text("ignored\n", encoding="utf-8")
        if verify_document(captured)["status"] != "CURRENT":
            raise AssertionError("diagnostic or in-progress proposal entered canonical revision")

        (second / "references" / "rules.md").write_text("changed\n", encoding="utf-8")
        changed = verify_document(captured)
        if changed["status"] != "STALE" or changed["changes"]["changedRoots"] != [str(second.resolve())]:
            raise AssertionError(f"changed canonical Skill was not detected: {changed}")
        (second / "references" / "rules.md").write_text("stable\n", encoding="utf-8")
        (second / "references" / "added.md").write_text("added\n", encoding="utf-8")
        if verify_document(captured)["status"] != "STALE":
            raise AssertionError("added canonical Skill file was not detected")
        (second / "references" / "added.md").unlink()
        (second / "references" / "rules.md").unlink()
        if verify_document(captured)["status"] != "STALE":
            raise AssertionError("removed canonical Skill file was not detected")
        (second / "references" / "rules.md").write_text("stable\n", encoding="utf-8")

        malformed = json.loads(json.dumps(captured))
        malformed["roots"][0]["inventory"][0]["sha256"] = "invalid"
        try:
            verify_document(malformed)
        except RevisionError:
            pass
        else:
            raise AssertionError("malformed saved Skill identity was accepted")

        stable_records = [{"root": str(first), "files": 1, "bytes": 1, "sha256": "b" * 64, "inventory": []}]
        stable_snapshot = {"algorithm": ALGORITHM, "roots": 1, "files": 1, "bytes": 1, "sha256": "b" * 64}
        sequence = iter([
            ([], {**stable_snapshot, "sha256": "a" * 64}),
            (stable_records, stable_snapshot),
            (stable_records, stable_snapshot),
            (stable_records, stable_snapshot),
        ])
        records, snapshot, attempts = capture_consistent([first], scanner=lambda _roots: next(sequence))
        if records != stable_records or snapshot != stable_snapshot or attempts != 2:
            raise AssertionError("bounded revision capture did not converge on a stable attempt")

        counter = 0
        def never_stable(_roots: list[Path]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
            nonlocal counter
            counter += 1
            return [], {**stable_snapshot, "sha256": f"{counter:064x}"}
        try:
            capture_consistent([first], max_attempts=2, scanner=never_stable)
        except RevisionError:
            pass
        else:
            raise AssertionError("continuously changing canonical Skills were accepted")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=False)
    capture = subparsers.add_parser("capture")
    capture.add_argument("--root", action="append", type=Path, required=True)
    capture.add_argument("--max-attempts", type=int, default=3)
    capture.add_argument("--output", type=Path)
    capture.add_argument("--quiet", action="store_true")
    verify = subparsers.add_parser("verify")
    verify.add_argument("evidence_positional", nargs="?", type=Path)
    verify.add_argument("--evidence", type=Path)
    verify.add_argument("--root", action="append", type=Path)
    verify.add_argument("--max-attempts", type=int, default=3)
    verify.add_argument("--output", type=Path)
    verify.add_argument("--quiet", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.self_test:
        run_self_test()
        print("Skill revision self-test passed")
        return 0
    if args.command is None:
        raise SystemExit("capture or verify is required unless --self-test is used")
    if args.quiet and not args.output:
        raise SystemExit("--quiet requires --output")
    try:
        if args.command == "capture":
            report = capture_document(args.root, args.max_attempts)
        else:
            evidence_path = args.evidence or args.evidence_positional
            if evidence_path is None:
                raise RevisionError("verify requires an evidence path")
            evidence = json.loads(evidence_path.read_text(encoding="utf-8-sig"))
            report = verify_document(evidence, args.root, args.max_attempts)
    except RevisionUnstable as exc:
        report = {"schemaVersion": 1, "status": "UNSTABLE", "errors": [str(exc)]}
        _write(args.output, report, args.quiet)
        return 2
    except (OSError, UnicodeError, json.JSONDecodeError, RevisionError, KeyError) as exc:
        report = {"schemaVersion": 1, "status": "MEASUREMENT_BLOCK", "errors": [str(exc)]}
        _write(args.output, report, args.quiet)
        return 2
    _write(args.output, report, args.quiet)
    return 0 if report["status"] in {"CAPTURED", "CURRENT"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
