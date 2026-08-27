#!/usr/bin/env python3
"""Verify that a build receipt still matches live input and output files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def file_identity(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _safe_path(root: Path, value: Any) -> tuple[Path | None, str | None]:
    if not isinstance(value, str) or not value or "\\" in value:
        return None, "paths must be non-empty repo-relative POSIX strings"
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts or "." in relative.parts:
        return None, "paths must remain inside the project root"
    candidate = (root / Path(*relative.parts)).resolve()
    if candidate != root and root not in candidate.parents:
        return None, "path resolves outside the project root"
    return candidate, None


def evaluate(document: dict[str, Any], root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []

    def fail(code: str, message: str, **details: Any) -> None:
        findings.append({"status": "FAIL", "code": code, "message": message, **details})

    if document.get("schemaVersion") != 1:
        fail("schema-version", "schemaVersion must be 1")

    seen_all: dict[str, str] = {}
    checked = {"inputs": 0, "outputs": 0}
    for section in ("inputs", "outputs"):
        entries = document.get(section)
        if not isinstance(entries, list) or not entries:
            fail("empty-section", f"{section} must be a non-empty array", section=section)
            continue
        seen_section: set[str] = set()
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                fail("invalid-entry", f"{section}[{index}] must be an object", section=section, index=index)
                continue
            value = entry.get("path")
            candidate, path_error = _safe_path(root, value)
            if path_error:
                fail("unsafe-path", f"{section}[{index}] {path_error}", section=section, index=index, path=value)
                continue
            assert candidate is not None and isinstance(value, str)
            key = value.casefold()
            if key in seen_section:
                fail("duplicate-entry", f"duplicate case-insensitive path in {section}: {value}", section=section, path=value)
                continue
            seen_section.add(key)
            prior = seen_all.get(key)
            if prior and prior != section:
                fail("input-output-overlap", f"path is declared as both input and output: {value}", path=value)
                continue
            seen_all[key] = section

            expected_bytes = entry.get("bytes")
            expected_sha = entry.get("sha256")
            if not isinstance(expected_bytes, int) or expected_bytes < 0 or not isinstance(expected_sha, str) or not SHA256_RE.fullmatch(expected_sha):
                fail("invalid-identity", f"invalid bytes or SHA-256 for {value}", section=section, path=value)
                continue
            if not candidate.exists():
                fail("missing-file", f"receipt file is missing: {value}", section=section, path=value)
                continue
            if candidate.is_symlink() or not candidate.is_file():
                fail("unsupported-file", f"receipt path must be a regular non-symlink file: {value}", section=section, path=value)
                continue
            actual = file_identity(candidate)
            checked[section] += 1
            if actual != {"bytes": expected_bytes, "sha256": expected_sha}:
                code = "stale-build-input" if section == "inputs" else "stale-build-output"
                fail(code, f"live {section[:-1]} no longer matches receipt: {value}", section=section, path=value, expected={"bytes": expected_bytes, "sha256": expected_sha}, actual=actual)

    return {
        "schemaVersion": 1,
        "status": "BLOCK" if findings else "GREEN",
        "root": str(root),
        "checked": checked,
        "findings": findings or [{
            "status": "PASS",
            "code": "build-receipt-current",
            "message": "all declared build inputs and outputs match live bytes",
        }],
    }


def make_receipt(root: Path) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "inputs": [{"path": "src/input.txt", **file_identity(root / "src/input.txt")}],
        "outputs": [{"path": "dist/output.bin", **file_identity(root / "dist/output.bin")}],
    }


def run_self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="cleanup-build-receipt-") as raw:
        root = Path(raw)
        (root / "src").mkdir()
        (root / "dist").mkdir()
        (root / "src/input.txt").write_text("source", encoding="utf-8")
        (root / "dist/output.bin").write_bytes(b"output")
        valid = make_receipt(root)
        assert evaluate(valid, root)["status"] == "GREEN"

        stale_input = json.loads(json.dumps(valid))
        (root / "src/input.txt").write_text("changed", encoding="utf-8")
        report = evaluate(stale_input, root)
        assert any(item["code"] == "stale-build-input" for item in report["findings"])
        (root / "src/input.txt").write_text("source", encoding="utf-8")

        stale_output = json.loads(json.dumps(valid))
        (root / "dist/output.bin").write_bytes(b"changed")
        report = evaluate(stale_output, root)
        assert any(item["code"] == "stale-build-output" for item in report["findings"])
        (root / "dist/output.bin").write_bytes(b"output")

        unsafe = json.loads(json.dumps(valid))
        unsafe["inputs"][0]["path"] = "../escape.txt"
        assert any(item["code"] == "unsafe-path" for item in evaluate(unsafe, root)["findings"])

        duplicate = json.loads(json.dumps(valid))
        duplicate["inputs"].append({**duplicate["inputs"][0], "path": "SRC/INPUT.TXT"})
        assert any(item["code"] == "duplicate-entry" for item in evaluate(duplicate, root)["findings"])

        overlap = json.loads(json.dumps(valid))
        overlap["outputs"].append(dict(overlap["inputs"][0]))
        assert any(item["code"] == "input-output-overlap" for item in evaluate(overlap, root)["findings"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", nargs="?")
    parser.add_argument("--receipt")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        run_self_test()
        print("build receipt self-test passed")
        return 0
    if not args.target or not args.receipt:
        parser.error("target and --receipt are required unless --self-test is used")
    root = Path(args.target).resolve()
    receipt_path, error = _safe_path(root, args.receipt)
    if error or receipt_path is None or not receipt_path.is_file():
        parser.error(f"invalid receipt path: {error or args.receipt}")
    report = evaluate(json.loads(receipt_path.read_text(encoding="utf-8")), root)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(f"{report['status']}: inputs={report['checked']['inputs']} outputs={report['checked']['outputs']}")
        for finding in report["findings"]:
            print(f"[{finding['status']}] {finding['code']}: {finding['message']}")
    return 0 if report["status"] == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
