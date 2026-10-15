"""Closed-world ZIP and index verification, before any install mutation."""
from __future__ import annotations
import hashlib
import json
import re
import zipfile
from pathlib import Path, PurePosixPath
from typing import Optional

import importlib.util
import io
import tempfile

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

class ArchiveVerificationError(RuntimeError):
    pass

def _archive_fail(rule: str) -> None:
    # Archive-controlled names can contain private data.  Keep every
    # verification failure machine-stable and path-free.
    raise ArchiveVerificationError("archive verification failed: " + rule)

def _safe_archive_relative(value: object, rule: str) -> str:
    if not isinstance(value, str):
        _archive_fail(rule)
    try:
        relative = _canonical_portable_relative(value)
    except (TypeError, ValueError):
        _archive_fail(rule)
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
        _archive_fail(rule)
    return relative


def _verify_indexed_payloads(indexed, members, package):
    for relative, row in indexed.items():
        info = members[relative]
        if info.file_size != row["size"]:
            _archive_fail("indexed-size-mismatch")
        try:
            digest = hashlib.sha256()
            actual_size = 0
            with package.open(info) as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    actual_size += len(block)
                    digest.update(block)
        except Exception:
            _archive_fail("archive-member-read-failed")
        if actual_size != row["size"]:
            _archive_fail("indexed-size-mismatch")
        if digest.hexdigest().lower() != row["sha256"].lower():
            _archive_fail("indexed-hash-mismatch")


def _verify_archive_data(data: bytes, expected_hash: Optional[str] = None) -> dict:

    if expected_hash and hashlib.sha256(data).hexdigest().lower() != expected_hash.lower():
        _archive_fail("archive-sha256-mismatch")

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as package:
            members: dict[str, zipfile.ZipInfo] = {}
            member_keys: set[str] = set()
            for info in package.infolist():
                if info.orig_filename != info.filename or info.is_dir():
                    _archive_fail("unsafe-zip-member-path")
                relative = _safe_archive_relative(
                    info.orig_filename, "unsafe-zip-member-path"
                )
                member_key = relative.casefold()
                if member_key in member_keys:
                    _archive_fail("duplicate-zip-member")
                member_keys.add(member_key)
                members[relative] = info

            index_info = members.get("release-index.json")
            if index_info is None:
                _archive_fail("missing-release-index")
            try:
                index = json.loads(package.read(index_info).decode("utf-8"))
            except Exception:
                _archive_fail("invalid-release-index")
            if not isinstance(index, dict) or not isinstance(index.get("files"), list):
                _archive_fail("invalid-release-index")
            if index.get("project_id") != "video-autopilot-kit":
                _archive_fail("wrong-project-id")

            indexed: dict[str, dict] = {}
            indexed_keys: set[str] = set()
            for row in index["files"]:
                if not isinstance(row, dict) or not isinstance(row.get("path"), str):
                    _archive_fail("invalid-release-index")
                relative = _safe_archive_relative(row["path"], "unsafe-index-path")
                if relative.casefold() == "release-index.json":
                    _archive_fail("reserved-index-path")
                indexed_key = relative.casefold()
                if indexed_key in indexed_keys:
                    _archive_fail("duplicate-index-path")
                indexed_keys.add(indexed_key)
                size, digest = row.get("size"), row.get("sha256")
                if (
                    isinstance(size, bool)
                    or not isinstance(size, int)
                    or size < 0
                    or not isinstance(digest, str)
                    or not re.fullmatch(r"[0-9a-fA-F]{64}", digest)
                ):
                    _archive_fail("invalid-release-index")
                indexed[relative] = row

            expected_members = set(indexed) | {"release-index.json"}
            if set(members) - expected_members:
                _archive_fail("extra-unindexed-member")
            if set(indexed) - set(members):
                _archive_fail("missing-indexed-member")

            _verify_indexed_payloads(indexed, members, package)
    except ArchiveVerificationError:
        raise
    except Exception:
        _archive_fail("invalid-zip-container")
    return index


def _archive_bytes(archive: Path) -> bytes:
    """Bind validation and bootstrap extraction to the same bounded byte snapshot."""
    limit = 256 * 1024 * 1024
    try:
        with archive.open("rb") as stream:
            data = stream.read(limit + 1)
    except OSError:
        _archive_fail("unreadable-zip-container")
    if not data or len(data) > limit:
        _archive_fail("zip-container-size-limit")
    return data


def verify_archive(archive: Path, expected_hash: Optional[str] = None) -> dict:
    return _verify_archive_data(_archive_bytes(archive), expected_hash)


def load_bootstrap_install_component(archive: Path, expected_hash: Optional[str]):
    """Keep the original three-member bootstrap working with modular releases.

    Only the fixed installation component from the fully verified archive is
    loaded. The temporary file is owned by this invocation, and neither an
    installed program directory nor ambient PYTHONPATH selects the component.
    """
    data = _archive_bytes(archive)
    index = _verify_archive_data(data, expected_hash)
    member = "src/release_install.py"
    if member not in {item["path"] for item in index["files"]}:
        _archive_fail("missing-bootstrap-install-component")
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        source = package.read(member)
    with tempfile.TemporaryDirectory(prefix="video-kit-bootstrap-component-") as raw:
        path = Path(raw) / "release_install.py"
        path.write_bytes(source)
        spec = importlib.util.spec_from_file_location("_video_kit_bootstrap_install", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("release bootstrap component loader unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


def stage_verified_archive(archive: Path, stage: Path, expected_hash: Optional[str]):
    """Validate and extract one immutable snapshot before program-file mutation."""
    data = _archive_bytes(archive)
    index = _verify_archive_data(data, expected_hash)
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        package.extractall(stage)
    return index
