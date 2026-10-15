#!/usr/bin/env python3
"""Verify that a build receipt still matches live input and output files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _file_signature(item, *, with_ctime: bool = True) -> tuple:
    identity = (item.st_dev, item.st_ino, stat.S_IFMT(item.st_mode),
                item.st_size, item.st_mtime_ns,
                getattr(item, "st_file_attributes", 0) & 0x400)
    return (*identity, item.st_ctime_ns) if with_ctime else identity


def file_identity(path: Path) -> dict[str, Any]:
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or getattr(before, "st_file_attributes", 0) & 0x400:
        raise ValueError("identity requires a regular non-reparse file")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        size = 0
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
        after = os.fstat(handle.fileno())
    final_path = path.lstat()
    # Windows can report different ctime meanings through stat and fstat.
    # Preserve the full timestamp check within each API, and bind the path to
    # the same opened object using type, identity, size, mtime and reparse flags.
    if (_file_signature(before) != _file_signature(final_path)
            or _file_signature(opened) != _file_signature(after)
            or _file_signature(before, with_ctime=False) != _file_signature(opened, with_ctime=False)
            or _file_signature(after, with_ctime=False) != _file_signature(final_path, with_ctime=False)
            or size != after.st_size):
        raise ValueError("file changed while its identity was measured")
    return {"bytes": size, "sha256": digest.hexdigest()}


def _safe_path(root: Path, value: Any) -> tuple[Path | None, str | None]:
    if not isinstance(value, str) or not value or "\\" in value:
        return None, "paths must be non-empty repo-relative POSIX strings"
    relative = PurePosixPath(value)
    if not relative.parts or relative.is_absolute() or ".." in relative.parts or value != relative.as_posix() or ":" in relative.parts[0]:
        return None, "paths must remain inside the project root"
    current = root
    for part in relative.parts:
        current = current / part
        if current.exists() or current.is_symlink():
            metadata = current.lstat()
            if current.is_symlink() or getattr(metadata, "st_file_attributes", 0) & 0x400:
                return None, "symlink or reparse-point paths are unsupported"
    candidate = (root / Path(*relative.parts)).resolve()
    if candidate != root and root not in candidate.parents:
        return None, "path resolves outside the project root"
    return candidate, None


def evaluate(document: dict[str, Any], root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []

    def fail(code: str, message: str, **details: Any) -> None:
        findings.append({"status": "FAIL", "code": code, "message": message, **details})

    if not isinstance(document, dict):
        fail("invalid-document", "receipt must be a JSON object")
        document = {}
    if type(document.get("schemaVersion")) is not int or document.get("schemaVersion") != 1:
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
            if type(expected_bytes) is not int or expected_bytes < 0 or not isinstance(expected_sha, str) or not SHA256_RE.fullmatch(expected_sha):
                fail("invalid-identity", f"invalid bytes or SHA-256 for {value}", section=section, path=value)
                continue
            if not candidate.exists():
                fail("missing-file", f"receipt file is missing: {value}", section=section, path=value)
                continue
            if candidate.is_symlink() or not candidate.is_file():
                fail("unsupported-file", f"receipt path must be a regular non-symlink file: {value}", section=section, path=value)
                continue
            try:
                actual = file_identity(candidate)
            except (OSError, ValueError) as error:
                fail("identity-read", f"cannot establish stable file identity: {value}: {error}", section=section, path=value)
                continue
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


def load_document(path: Path) -> Any:
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    with path.open("rb") as handle:
        payload = handle.read(8 * 1024 * 1024 + 1)
    if len(payload) > 8 * 1024 * 1024:
        raise ValueError("receipt exceeds the 8 MiB metadata limit")
    return json.loads(payload.decode("utf-8-sig"), object_pairs_hook=unique_keys,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON value: {value}")))


def _identity_api_controls(path: Path) -> None:
    from types import SimpleNamespace
    from unittest.mock import patch

    native_fstat = os.fstat

    def changed(info, **values):
        fields = {name: getattr(info, name) for name in (
            "st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")}
        fields["st_file_attributes"] = getattr(info, "st_file_attributes", 0)
        return SimpleNamespace(**{**fields, **values})

    def offset_fstat(fd):
        info = native_fstat(fd)
        return changed(info, st_ctime_ns=info.st_ctime_ns + 1000000)

    expected = {"bytes": 6, "sha256": hashlib.sha256(b"source").hexdigest()}
    with patch.object(os, "fstat", side_effect=offset_fstat):
        assert file_identity(path) == expected

    info = path.lstat()
    for target, values in (
        ("handle", [changed(info, st_ctime_ns=info.st_ctime_ns + 1),
                    changed(info, st_ctime_ns=info.st_ctime_ns + 2)]),
        ("path", [info, changed(info, st_ctime_ns=info.st_ctime_ns + 1)]),
        ("handle", [changed(info, st_ino=info.st_ino + 1)] * 2),
        ("handle", [changed(info, st_mtime_ns=info.st_mtime_ns + 1)] * 2),
        ("path", [info, changed(info, st_mode=stat.S_IFLNK | 0o777)]),
        ("path", [info, changed(info, st_file_attributes=0x400)]),
    ):
        owner, name = (os, "fstat") if target == "handle" else (Path, "lstat")
        with patch.object(owner, name, side_effect=values):
            try:
                file_identity(path)
            except ValueError:
                pass
            else:
                raise AssertionError("changed identity boundary was accepted")


def _identity_replacement_control(path: Path) -> None:
    from unittest.mock import patch
    native_lstat, calls = Path.lstat, 0
    original = path.stat()

    def replace_before_final_stat(current):
        nonlocal calls
        calls += 1
        if calls == 2:
            replacement = path.with_suffix(".replacement")
            replacement.write_bytes(b"source")
            os.utime(replacement, ns=(original.st_atime_ns, original.st_mtime_ns))
            os.replace(replacement, path)
        return native_lstat(current)

    with patch.object(Path, "lstat", autospec=True, side_effect=replace_before_final_stat):
        try:
            file_identity(path)
        except ValueError:
            pass
        else:
            raise AssertionError("same-byte same-mtime path replacement was accepted")


def run_self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="cleanup-build-receipt-") as raw:
        root = Path(raw)
        (root / "src").mkdir()
        (root / "dist").mkdir()
        (root / "src/input.txt").write_text("source", encoding="utf-8")
        (root / "dist/output.bin").write_bytes(b"output")
        _identity_api_controls(root / "src/input.txt")
        _identity_replacement_control(root / "src/input.txt")
        valid = make_receipt(root)
        assert evaluate(valid, root)["status"] == "GREEN"
        for value in (True, 1.0, "1"):
            malformed = json.loads(json.dumps(valid))
            malformed["schemaVersion"] = value
            assert evaluate(malformed, root)["status"] == "BLOCK"
        (root / "src/input.txt").write_bytes(b"")
        empty = make_receipt(root)
        assert evaluate(empty, root)["status"] == "GREEN"
        empty["inputs"][0]["bytes"] = False
        assert evaluate(empty, root)["status"] == "BLOCK"
        (root / "src/input.txt").write_text("source", encoding="utf-8")
        assert evaluate([], root)["status"] == "BLOCK"
        duplicate_json = root / "duplicate.json"
        duplicate_json.write_text('{"schemaVersion":0,"schemaVersion":1}', encoding="utf-8")
        try:
            load_document(duplicate_json)
        except ValueError:
            pass
        else:
            raise AssertionError("duplicate JSON keys were accepted")
        link = root / "input-link.txt"
        try:
            link.symlink_to(root / "src/input.txt")
        except OSError:
            link = None
        if link is not None:
            aliased = json.loads(json.dumps(valid))
            aliased["inputs"][0]["path"] = "input-link.txt"
            assert evaluate(aliased, root)["status"] == "BLOCK"

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
    try:
        report = evaluate(load_document(receipt_path), root)
    except (OSError, ValueError, UnicodeError) as error:
        report = {"schemaVersion": 1, "status": "BLOCK", "root": str(root), "checked": {"inputs": 0, "outputs": 0},
                  "findings": [{"status": "FAIL", "code": "invalid-receipt-json", "message": str(error)}]}
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(f"{report['status']}: inputs={report['checked']['inputs']} outputs={report['checked']['outputs']}")
        for finding in report["findings"]:
            print(f"[{finding['status']}] {finding['code']}: {finding['message']}")
    return 0 if report["status"] == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
