"""Validator-owned live input snapshot profile for security receipts."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from security_assessment_shared import (
    MAX_EVIDENCE_BYTES,
    SHA256_RE,
    FailureSink,
    closed_fields,
    file_identity,
    link_like,
    safe_path,
)
from security_assessment_v2_common import canonical_sha256, load_json_evidence


SNAPSHOT_PROFILE = "cleanup-security-input/v1"
SNAPSHOT_EXCLUDED_ROOTS = frozenset({
    ".git",
    ".rd",
    ".cleanup-evidence",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "out",
    "target",
    "venv",
})
MAX_SNAPSHOT_MANIFEST_BYTES = 4 * 1024 * 1024
MAX_SNAPSHOT_FILES = 20_000
MAX_SNAPSHOT_FILE_BYTES = 64 * 1024 * 1024
MAX_SNAPSHOT_TOTAL_BYTES = 256 * 1024 * 1024
MAX_SNAPSHOT_OBJECTS = 50_000
MAX_ALTERNATE_STREAMS_PER_FILE = 64


def snapshot_payload(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "profile": SNAPSHOT_PROFILE,
        "entries": sorted(entries, key=lambda item: item["path"].casefold()),
    }


def snapshot_sha256(entries: list[dict[str, Any]]) -> str:
    return canonical_sha256(snapshot_payload(entries))


def _excluded(relative: Path) -> bool:
    return len(relative.parts) == 1 and relative.parts[0].casefold() in SNAPSHOT_EXCLUDED_ROOTS


def _inside_excluded(relative: Path) -> bool:
    return bool(relative.parts and relative.parts[0].casefold() in SNAPSHOT_EXCLUDED_ROOTS)


def _alternate_stream_error(path: Path) -> str | None:
    """Reject hidden NTFS streams; non-Windows filesystems have no Win32 ADS API."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class Win32FindStreamData(ctypes.Structure):
            _fields_ = [
                ("StreamSize", ctypes.c_longlong),
                ("cStreamName", wintypes.WCHAR * (260 + 36)),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        find_first = kernel32.FindFirstStreamW
        find_first.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.POINTER(Win32FindStreamData),
            wintypes.DWORD,
        ]
        find_first.restype = wintypes.HANDLE
        find_next = kernel32.FindNextStreamW
        find_next.argtypes = [wintypes.HANDLE, ctypes.POINTER(Win32FindStreamData)]
        find_next.restype = wintypes.BOOL
        find_close = kernel32.FindClose
        find_close.argtypes = [wintypes.HANDLE]
        find_close.restype = wintypes.BOOL

        data = Win32FindStreamData()
        handle = find_first(str(path), 0, ctypes.byref(data), 0)
        if handle == wintypes.HANDLE(-1).value:
            return "input snapshot stream enumeration failed"
        try:
            streams = 0
            while True:
                streams += 1
                if streams > MAX_ALTERNATE_STREAMS_PER_FILE:
                    return "input snapshot exceeds the alternate-stream ceiling"
                if data.cStreamName != "::$DATA":
                    return "input snapshot contains an alternate data stream"
                if find_next(handle, ctypes.byref(data)):
                    continue
                if ctypes.get_last_error() == 38:  # ERROR_HANDLE_EOF
                    return None
                return "input snapshot stream enumeration failed"
        finally:
            find_close(handle)
    except (AttributeError, OSError, TypeError, ValueError):
        return "input snapshot stream enumeration failed"


def _live_entries(root: Path, fail: FailureSink) -> list[dict[str, Any]] | None:
    entries: list[dict[str, Any]] = []
    directories = [root]
    objects = 0
    total_bytes = 0
    while directories:
        directory = directories.pop()
        try:
            children = []
            with os.scandir(directory) as iterator:
                for child in iterator:
                    objects += 1
                    if objects > MAX_SNAPSHOT_OBJECTS:
                        fail("snapshot-object-limit", "input snapshot exceeds the object ceiling")
                        return None
                    children.append(child)
        except OSError:
            fail("snapshot-read", "input snapshot directory cannot be enumerated")
            return None
        children.sort(key=lambda item: item.name.casefold())
        for child in children:
            candidate = Path(child.path)
            relative = candidate.relative_to(root)
            if directory == root and _excluded(relative):
                continue
            relative_text = relative.as_posix()
            checked, error = safe_path(root, relative_text)
            if error or checked is None or checked != candidate.resolve() or link_like(candidate):
                fail("snapshot-unsafe-object", "input snapshot contains an unsafe path or link")
                return None
            try:
                if child.is_dir(follow_symlinks=False):
                    directories.append(candidate)
                    continue
                if not child.is_file(follow_symlinks=False):
                    fail("snapshot-unsafe-object", "input snapshot contains a non-regular object")
                    return None
                stream_error = _alternate_stream_error(candidate)
                if stream_error:
                    fail("snapshot-alternate-stream", stream_error)
                    return None
                actual_size = candidate.stat().st_size
            except OSError:
                fail("snapshot-read", "input snapshot object cannot be inspected")
                return None
            if actual_size < 0 or actual_size > MAX_SNAPSHOT_FILE_BYTES:
                fail("snapshot-file-limit", "input snapshot file exceeds the byte ceiling")
                return None
            remaining = MAX_SNAPSHOT_TOTAL_BYTES - total_bytes
            if actual_size > remaining:
                fail("snapshot-total-limit", "input snapshot exceeds the aggregate byte ceiling")
                return None
            if len(entries) >= MAX_SNAPSHOT_FILES:
                fail("snapshot-file-count", "input snapshot exceeds the file-count ceiling")
                return None
            try:
                identity = file_identity(candidate, max_bytes=min(MAX_SNAPSHOT_FILE_BYTES, remaining))
            except (OSError, ValueError):
                fail("snapshot-read", "input snapshot file changed or exceeded bounds while hashing")
                return None
            if identity["bytes"] != actual_size:
                fail("snapshot-file-changed", "input snapshot file changed while hashing")
                return None
            stream_error = _alternate_stream_error(candidate)
            if stream_error:
                fail("snapshot-alternate-stream", stream_error)
                return None
            total_bytes += actual_size
            entries.append({"path": relative_text, **identity})
    return sorted(entries, key=lambda item: item["path"].casefold())


def _manifest_entries(document: dict[str, Any], root: Path, fail: FailureSink) -> list[dict[str, Any]] | None:
    closed_fields(document, {"schemaVersion", "profile", "entries"}, "snapshot-manifest", fail)
    if document.get("schemaVersion") != 1 or document.get("profile") != SNAPSHOT_PROFILE:
        fail("snapshot-profile", "snapshot manifest uses an unsupported validator profile")
        return None
    raw_entries = document.get("entries")
    if not isinstance(raw_entries, list) or len(raw_entries) > MAX_SNAPSHOT_FILES:
        fail("snapshot-manifest", "snapshot manifest has an invalid entry list")
        return None
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_entries):
        if not isinstance(raw, dict):
            fail("snapshot-manifest", "snapshot manifest entry is not an object")
            return None
        closed_fields(raw, {"path", "bytes", "sha256"}, f"snapshot-entry[{index}]", fail)
        path = raw.get("path")
        candidate, error = safe_path(root, path)
        size = raw.get("bytes")
        digest = raw.get("sha256")
        if (
            error
            or candidate is None
            or not isinstance(path, str)
            or _inside_excluded(Path(path))
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
            or size > MAX_SNAPSHOT_FILE_BYTES
            or not isinstance(digest, str)
            or not SHA256_RE.fullmatch(digest)
        ):
            fail("snapshot-manifest", "snapshot manifest entry is invalid")
            return None
        key = path.casefold()
        if key in seen:
            fail("snapshot-manifest", "snapshot manifest contains duplicate paths")
            return None
        seen.add(key)
        entries.append({"path": path, "bytes": size, "sha256": digest})
    return sorted(entries, key=lambda item: item["path"].casefold())


def validate_snapshot(
    root: Path,
    target: dict[str, Any],
    evidence: dict[str, dict[str, Any]],
    fail: FailureSink,
) -> bool:
    if target.get("snapshotProfile") != SNAPSHOT_PROFILE:
        fail("snapshot-profile", "target snapshot profile is not validator-owned")
        return False
    evidence_id = target.get("snapshotManifestEvidenceId")
    record = evidence.get(evidence_id.casefold()) if isinstance(evidence_id, str) else None
    expected_manifest_sha = target.get("snapshotManifestSha256")
    if (
        not isinstance(record, dict)
        or not isinstance(expected_manifest_sha, str)
        or not SHA256_RE.fullmatch(expected_manifest_sha)
        or record.get("sha256") != expected_manifest_sha
    ):
        fail("snapshot-manifest-binding", "target does not bind the snapshot manifest evidence")
        return False
    document = load_json_evidence(
        record,
        root,
        expected_kind="snapshot-manifest",
        max_bytes=MAX_SNAPSHOT_MANIFEST_BYTES,
        fail=fail,
        code="snapshot-manifest-binding",
    )
    if document is None:
        return False
    manifest = _manifest_entries(document, root, fail)
    live = _live_entries(root, fail)
    if manifest is None or live is None:
        return False
    if not manifest:
        fail("snapshot-empty", "security promotion requires at least one included input file")
        return False
    manifest_by_path = {item["path"].casefold(): item for item in manifest}
    live_by_path = {item["path"].casefold(): item for item in live}
    if set(live_by_path) - set(manifest_by_path):
        fail("snapshot-file-added", "live input contains files absent from the frozen manifest")
    if set(manifest_by_path) - set(live_by_path):
        fail("snapshot-file-missing", "frozen input files are absent from the live target")
    if any(manifest_by_path[key] != live_by_path[key] for key in set(manifest_by_path) & set(live_by_path)):
        fail("snapshot-file-changed", "live input bytes differ from the frozen manifest")
    computed = snapshot_sha256(manifest)
    if target.get("snapshotSha256") != computed:
        fail("snapshot-hash-drift", "target snapshot hash differs from the canonical manifest")
    return manifest == live and target.get("snapshotSha256") == computed
