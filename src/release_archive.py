"""Closed-world ZIP and index verification, before any install mutation."""
from __future__ import annotations
import hashlib
import json
import re
import zipfile
from pathlib import Path, PurePosixPath
from typing import Optional

import importlib.util

if __package__:
    from .release_integrity import canonical_portable_relative as _canonical_portable_relative, _sha256_path as sha256_path
else:
    _path = Path(__file__).with_name("release_integrity.py").resolve()
    _spec = importlib.util.spec_from_file_location("_video_autopilot_archive_integrity", _path)
    if _spec is None or _spec.loader is None:
        raise RuntimeError("release archive integrity loader unavailable")
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)
    _canonical_portable_relative = _module.canonical_portable_relative
    sha256_path = _module._sha256_path

def verify_archive(archive: Path, expected_hash: Optional[str] = None) -> dict:
    class ArchiveVerificationError(RuntimeError):
        pass

    def fail(rule: str) -> None:
        # Archive-controlled names can contain private data.  Keep every
        # verification failure machine-stable and path-free.
        raise ArchiveVerificationError("archive verification failed: " + rule)

    def safe_archive_relative(value: object, rule: str) -> str:
        if not isinstance(value, str):
            fail(rule)
        try:
            relative = _canonical_portable_relative(value)
        except (TypeError, ValueError):
            fail(rule)
        reserved = {"CON", "PRN", "AUX", "NUL"} | {
            "%s%d" % (prefix, number)
            for prefix in ("COM", "LPT")
            for number in range(1, 10)
        }
        parts = PurePosixPath(relative).parts
        if relative != value or any(
            not part
            or ":" in part
            or part.endswith((" ", "."))
            or part.split(".", 1)[0].upper() in reserved
            or any(ord(character) < 32 for character in part)
            for part in parts
        ):
            fail(rule)
        return relative

    if expected_hash and sha256_path(archive).lower() != expected_hash.lower():
        fail("archive-sha256-mismatch")

    try:
        with zipfile.ZipFile(archive) as package:
            members: dict[str, zipfile.ZipInfo] = {}
            member_keys: set[str] = set()
            for info in package.infolist():
                if info.orig_filename != info.filename or info.is_dir():
                    fail("unsafe-zip-member-path")
                relative = safe_archive_relative(
                    info.orig_filename, "unsafe-zip-member-path"
                )
                member_key = relative.casefold()
                if member_key in member_keys:
                    fail("duplicate-zip-member")
                member_keys.add(member_key)
                members[relative] = info

            index_info = members.get("release-index.json")
            if index_info is None:
                fail("missing-release-index")
            try:
                index = json.loads(package.read(index_info).decode("utf-8"))
            except Exception:
                fail("invalid-release-index")
            if not isinstance(index, dict) or not isinstance(index.get("files"), list):
                fail("invalid-release-index")
            if index.get("project_id") != "video-autopilot-kit":
                fail("wrong-project-id")

            indexed: dict[str, dict] = {}
            indexed_keys: set[str] = set()
            for row in index["files"]:
                if not isinstance(row, dict) or not isinstance(row.get("path"), str):
                    fail("invalid-release-index")
                relative = safe_archive_relative(row["path"], "unsafe-index-path")
                if relative.casefold() == "release-index.json":
                    fail("reserved-index-path")
                indexed_key = relative.casefold()
                if indexed_key in indexed_keys:
                    fail("duplicate-index-path")
                indexed_keys.add(indexed_key)
                size, digest = row.get("size"), row.get("sha256")
                if (
                    isinstance(size, bool)
                    or not isinstance(size, int)
                    or size < 0
                    or not isinstance(digest, str)
                    or not re.fullmatch(r"[0-9a-fA-F]{64}", digest)
                ):
                    fail("invalid-release-index")
                indexed[relative] = row

            expected_members = set(indexed) | {"release-index.json"}
            if set(members) - expected_members:
                fail("extra-unindexed-member")
            if set(indexed) - set(members):
                fail("missing-indexed-member")

            for relative, row in indexed.items():
                info = members[relative]
                if info.file_size != row["size"]:
                    fail("indexed-size-mismatch")
                try:
                    digest = hashlib.sha256()
                    actual_size = 0
                    with package.open(info) as handle:
                        for block in iter(lambda: handle.read(1024 * 1024), b""):
                            actual_size += len(block)
                            digest.update(block)
                except Exception:
                    fail("archive-member-read-failed")
                if actual_size != row["size"]:
                    fail("indexed-size-mismatch")
                if digest.hexdigest().lower() != row["sha256"].lower():
                    fail("indexed-hash-mismatch")
    except ArchiveVerificationError:
        raise
    except Exception:
        fail("invalid-zip-container")
    return index
