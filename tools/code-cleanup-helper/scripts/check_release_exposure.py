#!/usr/bin/env python3
"""Read-only exposure triage of exact delivered files; never executes a target."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import sys

from sync_safety import SECRET_PATTERNS, link_like
from exposure_formats import credential_candidate, opaque_container, path_offsets, source_map

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_FILES = 20000


def finding(code: str, path: str, *, offset: int | None = None) -> dict:
    # Never reflect recovered strings, keys, source contents, or user identities.
    return {"status": "REVIEW", "code": code, "path": path, "offset": offset}


def pe_facts(data: bytes) -> dict:
    if len(data) < 64:
        raise ValueError("truncated DOS header")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if pe + 24 > len(data) or data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("invalid PE signature or bounds")
    size = struct.unpack_from("<H", data, pe + 20)[0]
    optional = pe + 24
    if size < 72 or optional + size > len(data):
        raise ValueError("truncated PE optional header")
    magic = struct.unpack_from("<H", data, optional)[0]
    if magic not in {0x10B, 0x20B}:
        raise ValueError("unsupported PE optional header")
    flags = struct.unpack_from("<H", data, optional + 70)[0]
    return {"authority": "declared-header-flags-only", "pe_kind": "PE32+" if magic == 0x20B else "PE32",
            "aslr": bool(flags & 0x40), "nx_compatible": bool(flags & 0x100),
            "high_entropy_va": bool(flags & 0x20), "guard_cf": bool(flags & 0x4000),
            "runtime_enforcement": "NOT_CHECKED"}


def inspect_file(path: Path, relative: str, data: bytes) -> tuple[list[dict], dict, list[str]]:
    rows, facts, gaps = [], {}, []
    for offset in path_offsets(data):
        rows.append(finding("embedded-private-path", relative, offset=offset))
    if credential_candidate(data, SECRET_PATTERNS):
        rows.append(finding("credential-shaped-content", relative))
    if path.suffix.casefold() in {".pdb", ".debug"}:
        rows.append(finding("debug-symbol-artifact", relative))
    if b"sourceMappingURL=" in data:
        rows.append(finding("source-map-reference", relative))
    if path.suffix.casefold() == ".map":
        found, missing = source_map(data)
        gaps.extend(missing)
        if found:
            rows.append(finding("source-map-original-source", relative))
    if data.startswith(b"MZ"):
        try:
            facts["pe"] = pe_facts(data)
        except (ValueError, struct.error):
            gaps.append("pe-header-unparsed")
        else:
            if not facts["pe"]["aslr"] or not facts["pe"]["nx_compatible"]:
                rows.append(finding("pe-mitigation-header-review", relative))
    if opaque_container(path, data):
        gaps.append("container-payload-not-extracted")
    return rows, facts, gaps


def enumerate_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if not target.is_dir():
        raise ValueError("target is not an existing file or directory")
    result = []
    for directory, names, files in os.walk(target, topdown=True, followlinks=False, onerror=_unreadable):
        base = Path(directory)
        if any(link_like(base / n) for n in names):
            raise ValueError("directory link/reparse rejected")
        for name in files:
            result.append(base / name)
            if len(result) > MAX_FILES:
                raise ValueError("file-count bound exceeded")
    return sorted(result)


def audit(target: Path) -> dict:
    if link_like(target):
        raise ValueError("target link rejected")
    target = target.resolve()
    base = target.parent if target.is_file() else target
    rows, inventory, gaps, total = [], [], [], 0
    files = enumerate_files(target)
    for path in files:
        name = path.relative_to(base).as_posix()
        if link_like(path):
            raise ValueError("file link/reparse rejected")
        size = path.stat().st_size
        if size > MAX_FILE_BYTES or total + size > MAX_TOTAL_BYTES:
            gaps.append({"path": name, "code": "byte-bound-unscanned"})
            continue
        with path.open("rb") as handle:
            before = os.fstat(handle.fileno())
            data = handle.read(MAX_FILE_BYTES + 1)
            after = os.fstat(handle.fileno())
        if len(data) != size or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError("input changed during inspection")
        total += len(data)
        found, facts, missing = inspect_file(path, name, data)
        rows.extend(found)
        gaps.extend({"path": name, "code": x} for x in missing)
        inventory.append({"path": name, "bytes": size, "sha256": hashlib.sha256(data).hexdigest(), "facts": facts})
    if not files:
        gaps.append({"path": ".", "code": "empty-scope"})
    return {"schema_version": 1, "evidence_class": "static-release-exposure-only",
            "status": "NOT_CHECKED" if gaps else "REVIEW" if rows else "PASS",
            "summary": {"enumerated": len(files), "inspected": len(inventory), "bytes": total,
                        "review": len(rows), "not_checked": len(gaps)},
            "inventory": inventory, "findings": rows, "gaps": gaps,
            "limitations": ["No target execution, decompilation, unpacking, or network access",
                            "No finding is not proof of secrecy or reverse-engineering resistance",
                            "Header flags are declarations, not runtime mitigation proof",
                            "Findings are candidates requiring project policy and semantic review"]}


def _unreadable(error: OSError) -> None:
    raise error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    try:
        report = audit(args.target)
    except (OSError, ValueError) as exc:
        report = {"schema_version": 1, "status": "FAIL", "code": "inspection-incomplete", "reason": type(exc).__name__}
    sys.stdout.buffer.write((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return {"PASS": 0, "REVIEW": 1, "NOT_CHECKED": 3, "FAIL": 1}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
