#!/usr/bin/env python3
"""Compare two Cleanup audit inventories and reject stale repository evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path
from typing import Any


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class SnapshotError(ValueError):
    """An audit report cannot support a deterministic inventory comparison."""


def load_report(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise SnapshotError(f"report root must be an object: {path}")
    return value


def inventory_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    inventory = report.get("inventory")
    if not isinstance(inventory, list):
        raise SnapshotError("report.inventory must be an array")
    result: dict[str, dict[str, Any]] = {}
    casefolded: dict[str, str] = {}
    for index, item in enumerate(inventory):
        if not isinstance(item, dict):
            raise SnapshotError(f"inventory[{index}] must be an object")
        path = item.get("path")
        lines = item.get("lines")
        size = item.get("bytes")
        sha256 = item.get("sha256")
        if not isinstance(path, str) or not path or "\\" in path:
            raise SnapshotError(f"inventory[{index}].path must be a non-empty POSIX path")
        candidate = Path(path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise SnapshotError(f"inventory[{index}].path escapes the target: {path}")
        if not isinstance(lines, int) or lines < 0:
            raise SnapshotError(f"inventory[{index}].lines must be a non-negative integer")
        if not isinstance(size, int) or size < 0:
            raise SnapshotError(f"inventory[{index}].bytes must be a non-negative integer")
        if not isinstance(sha256, str) or not SHA256_PATTERN.fullmatch(sha256):
            raise SnapshotError(f"inventory[{index}].sha256 must be lowercase SHA-256")
        folded = path.casefold()
        if folded in casefolded:
            raise SnapshotError(f"case-insensitive duplicate inventory path: {casefolded[folded]} / {path}")
        casefolded[folded] = path
        result[path] = {"path": path, "lines": lines, "bytes": size, "sha256": sha256}
    return result


def snapshot(entries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    digest = hashlib.sha256()
    for path in sorted(entries, key=str.casefold):
        item = entries[path]
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(item["lines"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(item["bytes"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(item["sha256"].encode("ascii"))
        digest.update(b"\0")
    return {
        "algorithm": "cleanup-inventory-sha256-v1",
        "files": len(entries),
        "lines": sum(item["lines"] for item in entries.values()),
        "bytes": sum(item["bytes"] for item in entries.values()),
        "sha256": digest.hexdigest(),
    }


def compare_reports(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_entries = inventory_map(before)
    after_entries = inventory_map(after)
    before_paths = set(before_entries)
    after_paths = set(after_entries)
    added = sorted(after_paths - before_paths, key=str.casefold)
    removed = sorted(before_paths - after_paths, key=str.casefold)
    changed = sorted(
        (path for path in before_paths & after_paths if before_entries[path] != after_entries[path]),
        key=str.casefold,
    )
    return {
        "schemaVersion": 1,
        "status": "FRESH" if not (added or removed or changed) else "STALE",
        "before": snapshot(before_entries),
        "after": snapshot(after_entries),
        "changes": {"added": added, "removed": removed, "changed": changed},
    }


def fixture_report(entries: list[tuple[str, bytes]]) -> dict[str, Any]:
    return {
        "inventory": [
            {
                "path": path,
                "lines": data.count(b"\n"),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            for path, data in entries
        ]
    }


def run_self_test() -> None:
    clean = fixture_report([("src/app.py", b"value = 1\n"), ("README.md", b"# App\n")])
    same = json.loads(json.dumps(clean))
    if compare_reports(clean, same)["status"] != "FRESH":
        raise AssertionError("identical inventory was not fresh")
    changed = fixture_report([("src/app.py", b"value = 2\n"), ("README.md", b"# App\n")])
    if compare_reports(clean, changed)["changes"]["changed"] != ["src/app.py"]:
        raise AssertionError("changed bytes were not detected")
    added = fixture_report([("src/app.py", b"value = 1\n"), ("README.md", b"# App\n"), ("new.txt", b"new\n")])
    if compare_reports(clean, added)["changes"]["added"] != ["new.txt"]:
        raise AssertionError("added file was not detected")
    removed = fixture_report([("src/app.py", b"value = 1\n")])
    if compare_reports(clean, removed)["changes"]["removed"] != ["README.md"]:
        raise AssertionError("removed file was not detected")
    malformed = json.loads(json.dumps(clean))
    malformed["inventory"][0]["sha256"] = "invalid"
    try:
        compare_reports(malformed, clean)
    except SnapshotError:
        pass
    else:
        raise AssertionError("malformed inventory identity was accepted")
    with tempfile.TemporaryDirectory(prefix="cleanup-snapshot-") as raw:
        path = Path(raw) / "report.json"
        path.write_text(json.dumps(clean), encoding="utf-8")
        if load_report(path) != clean:
            raise AssertionError("snapshot report loader drifted")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", nargs="?", type=Path)
    parser.add_argument("after", nargs="?", type=Path)
    parser.add_argument("--format", choices=("json", "human"), default="human")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        run_self_test()
        print("audit snapshot self-test passed")
        return 0
    if not args.before or not args.after:
        parser.error("before and after reports are required unless --self-test is used")
    report = compare_reports(load_report(args.before), load_report(args.after))
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        changes = report["changes"]
        print(
            f"{report['status']}: added={len(changes['added'])} "
            f"removed={len(changes['removed'])} changed={len(changes['changed'])}"
        )
    return 0 if report["status"] == "FRESH" else 1


if __name__ == "__main__":
    raise SystemExit(main())
