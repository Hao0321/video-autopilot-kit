# -*- coding: utf-8 -*-
"""Integrity-checked release builder, updater, migration ledger and rollback.

The updater owns only files declared by release-index.json. Unknown files and
all release-manifest protected paths are never deleted or overwritten.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable, Optional

if __package__:
    from .release_integrity import (
        assert_contained_release_path as _assert_contained_release_path,
        assert_transaction_id as _assert_transaction_id,
        assert_safe_mutation_path as _assert_safe_mutation_path,
        canonical_portable_relative as _canonical_portable_relative,
        canonical_persisted_hashes as _canonical_persisted_hashes,
        load_sync_inventory_contract as _load_sync_inventory_contract,
        preflight_apply_paths as _preflight_apply_paths,
        preflight_rollback_paths as _preflight_rollback_paths,
        resolve_mutation_root as _resolve_mutation_root,
        staged_sync_receipt_errors as _staged_sync_receipt_errors,
        validated_install_state as _validated_install_state,
        validated_transaction_record as _validated_transaction_record,
    )
else:
    _integrity_path = Path(__file__).resolve().with_name("release_integrity.py")
    _integrity_spec = importlib.util.spec_from_file_location(
        "_video_autopilot_release_integrity", _integrity_path
    )
    if _integrity_spec is None or _integrity_spec.loader is None:
        raise RuntimeError("release integrity module loader unavailable")
    _integrity_module = importlib.util.module_from_spec(_integrity_spec)
    _integrity_spec.loader.exec_module(_integrity_module)
    _assert_contained_release_path = _integrity_module.assert_contained_release_path
    _assert_transaction_id = _integrity_module.assert_transaction_id
    _assert_safe_mutation_path = _integrity_module.assert_safe_mutation_path
    _canonical_portable_relative = _integrity_module.canonical_portable_relative
    _canonical_persisted_hashes = _integrity_module.canonical_persisted_hashes
    _load_sync_inventory_contract = _integrity_module.load_sync_inventory_contract
    _preflight_apply_paths = _integrity_module.preflight_apply_paths
    _preflight_rollback_paths = _integrity_module.preflight_rollback_paths
    _resolve_mutation_root = _integrity_module.resolve_mutation_root
    _staged_sync_receipt_errors = _integrity_module.staged_sync_receipt_errors
    _validated_install_state = _integrity_module.validated_install_state
    _validated_transaction_record = _integrity_module.validated_transaction_record


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHANNEL = "https://github.com/Hao0321/video-autopilot-kit/releases/latest/download/release-channel.json"
STATE_DIR = ".video-autopilot"
TEXT_EXTENSIONS = {".css", ".csv", ".html", ".ini", ".js", ".json", ".md", ".mjs", ".py", ".svg", ".toml", ".ts", ".txt", ".yaml", ".yml"}
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_transaction_id() -> str:
    """Return a sortable, collision-resistant backup transaction identifier."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{timestamp}-{uuid.uuid4().hex[:12]}"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def version_tuple(value: Optional[str]) -> Optional[tuple[int, int, int]]:
    if not value:
        return None
    match = re.search(r"(?:^|v)(\d+)\.(\d+)\.(\d+)", str(value))
    return tuple(map(int, match.groups())) if match else None


def declared_migration(current: Optional[str], target: str, manifest: dict) -> Optional[dict]:
    """Return the explicit idempotent migration covering this version pair."""
    current_value = version_tuple(current)
    target_value = version_tuple(target)
    if target_value is None:
        return None
    for row in manifest.get("migrations", []):
        if not row.get("idempotent"):
            continue
        target_minimum = version_tuple(row.get("target_minimum"))
        target_maximum = version_tuple(row.get("target_maximum_exclusive"))
        if not target_minimum or not target_maximum:
            continue
        if not (target_minimum <= target_value < target_maximum):
            continue
        if current_value is None:
            if row.get("from") == "unversioned":
                return row
            continue
        from_minimum = version_tuple(row.get("from_minimum"))
        from_maximum = version_tuple(row.get("from_maximum_exclusive"))
        if from_minimum and from_maximum and from_minimum <= current_value < from_maximum:
            return row
    return None


def _matches(relative: str, patterns: Iterable[str]) -> bool:
    value = relative.replace("\\", "/").lstrip("./")
    for pattern in patterns:
        pattern = pattern.replace("\\", "/").lstrip("./")
        if pattern.endswith("/**") and (
            value == pattern[:-3].rstrip("/")
            or value.startswith(pattern[:-3])
        ):
            return True
        if fnmatch.fnmatchcase(value, pattern):
            return True
    return False


def collect_release_files(root: Path, manifest: dict) -> list[Path]:
    root = root.resolve(strict=True)
    includes = manifest["managed_include"]
    excludes = manifest["exclude_globs"]
    protected = manifest["protected_globs"]
    found = []
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if not _matches(relative, includes) or _matches(relative, excludes):
            continue
        _assert_contained_release_path(root, path)
        if not path.is_file():
            continue
        _assert_contained_release_path(root, path, require_file=True)
        if _matches(relative, protected):
            raise RuntimeError("protected path entered release: " + relative)
        found.append(path)
    return sorted(found, key=lambda item: item.relative_to(root).as_posix())


def validate_release_tree(root: Path, manifest: dict, files: list[Path]) -> list[str]:
    root = root.resolve(strict=True)
    errors = []
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", str(manifest.get("release_date", ""))):
        errors.append("release_date must be a deterministic UTC timestamp")
    if not manifest.get("migrations"):
        errors.append("at least one explicit migration declaration is required")
    included = {path.relative_to(root).as_posix() for path in files}
    for relative in manifest.get("required_paths", []):
        if relative not in included:
            errors.append("required release file missing: " + relative)
    deny_patterns = [
        re.compile(pattern, re.I)
        for pattern in manifest.get("privacy", {}).get("deny_text_patterns", [])
    ]
    privacy_gate = None
    privacy_gate_relative = manifest.get("privacy", {}).get(
        "semantic_gate", "scripts/public_privacy_gate.py"
    )
    try:
        privacy_gate_path = root / _canonical_portable_relative(
            privacy_gate_relative
        )
        _assert_contained_release_path(root, privacy_gate_path, require_file=True)
    except (TypeError, ValueError, RuntimeError):
        errors.append("public privacy gate path is unsafe or unavailable")
        privacy_gate_path = None
    if privacy_gate_path is not None:
        try:
            spec = importlib.util.spec_from_file_location(
                "_video_autopilot_public_privacy_gate", privacy_gate_path
            )
            if spec is None or spec.loader is None:
                raise RuntimeError("module loader unavailable")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            privacy_gate = module.assert_global_public_text_safe
        except Exception as exc:
            errors.append("public privacy gate unavailable: %s" % type(exc).__name__)
    for path in files:
        try:
            _assert_contained_release_path(root, path, require_file=True)
        except RuntimeError as exc:
            errors.append(str(exc))
            continue
        relative = path.relative_to(root).as_posix()
        text = ""
        is_text = path.suffix.lower() in TEXT_EXTENSIONS or path.name == "LICENSE"
        if is_text:
            text = path.read_text(encoding="utf-8", errors="replace")
            if path == root / "release-manifest.json":
                # The manifest intentionally contains deny-pattern declarations.
                # Remove that field before scanning so declarations are not
                # mistaken for leaked values.
                sanitized_manifest = read_json(path)
                sanitized_manifest.get("privacy", {}).pop("deny_text_patterns", None)
                text = json.dumps(sanitized_manifest, ensure_ascii=False)
            for pattern in deny_patterns:
                if pattern.search(text):
                    errors.append("public privacy gate failed: manifest-deny-text-pattern")
        if privacy_gate is not None:
            try:
                privacy_gate(relative, text)
            except ValueError as exc:
                errors.append(str(exc))
    return errors


def _release_payload(path: Path) -> bytes:
    payload = path.read_bytes()
    if path.suffix.lower() in TEXT_EXTENSIONS or path.name in {"LICENSE", ".gitignore"}:
        text = payload.decode("utf-8-sig")
        return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return payload


def _deterministic_zip(source: Path, archive: Path) -> None:
    source = source.resolve(strict=True)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        for path in sorted(source.rglob("*")):
            _assert_contained_release_path(source, path)
            if not path.is_file():
                continue
            _assert_contained_release_path(source, path, require_file=True)
            relative = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            out.writestr(info, _release_payload(path))


def build_release(
    root: Path = ROOT,
    dist: Optional[Path] = None,
    base_url: Optional[str] = None,
) -> dict:
    root = root.resolve(strict=True)
    manifest_path = root / "release-manifest.json"
    _assert_contained_release_path(root, manifest_path, require_file=True)
    manifest = read_json(manifest_path)
    version = manifest["version"]
    files = collect_release_files(root, manifest)
    errors = validate_release_tree(root, manifest, files)
    if errors:
        raise RuntimeError("release validation failed:\n- " + "\n- ".join(errors))
    sync_inventory_contract = _load_sync_inventory_contract(root)
    dist = (dist or root / "dist").resolve()
    archive_name = "video-autopilot-kit-v%s.zip" % version
    archive = dist / archive_name
    with tempfile.TemporaryDirectory(prefix="video-autopilot-release-") as temporary:
        stage = Path(temporary) / "release"
        for source in files:
            relative = source.relative_to(root)
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            # Canonicalize public text before per-file hashes are computed.
            target.write_bytes(_release_payload(source))
        receipt_errors = _staged_sync_receipt_errors(stage, sync_inventory_contract)
        if receipt_errors:
            raise RuntimeError(
                "release sync-receipt parity failed:\n- "
                + "\n- ".join(receipt_errors)
            )
        indexed = []
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                indexed.append(
                    {
                        "path": path.relative_to(stage).as_posix(),
                        "sha256": sha256_path(path),
                        "size": path.stat().st_size,
                    }
                )
        index = {
            "schema_version": 1,
            "project_id": manifest["project_id"],
            "version": version,
            "generated_at": manifest["release_date"],
            "files": indexed,
        }
        atomic_json(stage / "release-index.json", index)
        _deterministic_zip(stage, archive)
    archive_hash = sha256_path(archive)
    channel = {
        "schema_version": 1,
        "project_id": manifest["project_id"],
        "latest": {
            "version": version,
            "url": (base_url.rstrip("/") + "/" + archive_name) if base_url else archive_name,
            "sha256": archive_hash,
            "release_notes": "https://github.com/Hao0321/video-autopilot-kit/releases/tag/v%s" % version,
        },
    }
    atomic_json(dist / "release-channel.json", channel)
    (dist / (archive_name + ".sha256")).write_text(
        archive_hash + "  " + archive_name + "\n", encoding="ascii"
    )
    return {
        "status": "GREEN",
        "version": version,
        "archive": str(archive),
        "sha256": archive_hash,
        "managed_files": len(files),
        "channel": str(dist / "release-channel.json"),
    }


def _read_url_or_path(value: str, base: Optional[str] = None) -> tuple[bytes, str]:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme in {"http", "https"}:
        with urllib.request.urlopen(value, timeout=30) as response:  # nosec B310
            return response.read(), value
    path = Path(value)
    if not path.is_absolute() and base and urllib.parse.urlparse(base).scheme not in {"http", "https"}:
        path = Path(base).parent / path
    return path.resolve().read_bytes(), str(path.resolve())


def load_channel(value: str) -> tuple[dict, str]:
    payload, resolved = _read_url_or_path(value)
    channel = json.loads(payload.decode("utf-8"))
    if channel.get("project_id") != "video-autopilot-kit":
        raise ValueError("update channel belongs to another project")
    return channel, resolved


def resolve_channel_asset(url: str, channel_source: str) -> str:
    if urllib.parse.urlparse(url).scheme in {"http", "https"}:
        return url
    if urllib.parse.urlparse(channel_source).scheme in {"http", "https"}:
        return urllib.parse.urljoin(channel_source, url)
    return str((Path(channel_source).parent / url).resolve())


def detect_current_version(install_root: Path) -> Optional[str]:
    install_root = _resolve_mutation_root(install_root)
    state = install_root / STATE_DIR / "install-state.json"
    _assert_safe_mutation_path(install_root, install_root / STATE_DIR)
    _assert_safe_mutation_path(install_root, state, require_file=True)
    if state.is_file():
        payload = read_json(state)
        if not isinstance(payload, dict):
            raise RuntimeError("install state is invalid")
        _validated_install_state(payload)
        return payload.get("version")
    manifest = install_root / "release-manifest.json"
    _assert_safe_mutation_path(install_root, manifest, require_file=True)
    if manifest.is_file():
        payload = read_json(manifest)
        if not isinstance(payload, dict):
            raise RuntimeError("installed release manifest is invalid")
        return payload.get("version")
    try:
        result = subprocess.run(
            ["git", "-C", str(install_root), "describe", "--tags", "--abbrev=0"],
            capture_output=True, encoding="utf-8", errors="replace", timeout=5
        )
        if result.returncode == 0 and version_tuple(result.stdout.strip()):
            return result.stdout.strip().lstrip("v")
    except (OSError, subprocess.SubprocessError):
        pass
    for name in ("README.md", "CHANGELOG.md"):
        path = install_root / name
        if path.is_file():
            match = re.search(r"v(\d+\.\d+\.\d+)", path.read_text(encoding="utf-8", errors="replace"))
            if match:
                return match.group(1)
    return None


def compatible_upgrade(current: Optional[str], target_manifest: dict) -> bool:
    policy = target_manifest["compatibility"]
    current_tuple = version_tuple(current)
    migration = declared_migration(current, target_manifest.get("version", ""), target_manifest)
    if current_tuple is None:
        return bool(policy.get("allow_unversioned_legacy") and migration)
    minimum = version_tuple(policy["minimum"])
    maximum = version_tuple(policy["maximum_exclusive"])
    return bool(minimum and maximum and minimum <= current_tuple < maximum and migration)


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


def _backup_file(
    install_root: Path, source: Path, backup_root: Path, relative: str
) -> None:
    relative = _canonical_portable_relative(relative)
    target = backup_root / "files" / relative
    _assert_safe_mutation_path(install_root, source, require_file=True, allow_missing=False)
    _assert_safe_mutation_path(install_root, target, require_file=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _rollback_record(install_root: Path, record: dict, backup_root: Path) -> None:
    transaction = _assert_transaction_id(backup_root.name)
    record = _validated_transaction_record(record, transaction)
    _preflight_rollback_paths(install_root, record, backup_root)
    for relative in reversed(record["created"]):
        target = install_root / relative
        if target.is_file() or target.is_symlink():
            target.unlink()
    for relative in record["replaced"] + record["removed"]:
        source = backup_root / "files" / relative
        target = install_root / relative
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + ".rollback-tmp")
            shutil.copy2(source, temporary)
            os.replace(temporary, target)


def _restore_previous_state(install_root: Path, backup_root: Path) -> None:
    state_path = install_root / STATE_DIR / "install-state.json"
    previous = backup_root / "previous-install-state.json"
    _assert_safe_mutation_path(install_root, state_path, require_file=True)
    _assert_safe_mutation_path(install_root, state_path.with_name(state_path.name + ".tmp"), require_file=True)
    _assert_safe_mutation_path(install_root, previous, require_file=True)
    if previous.is_file():
        state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = state_path.with_name(state_path.name + ".tmp")
        shutil.copy2(previous, temporary)
        os.replace(temporary, state_path)
    elif state_path.is_file():
        state_path.unlink()


def locally_modified_managed_files(install_root: Path, state: dict) -> list[str]:
    install_root = _resolve_mutation_root(install_root)
    if not isinstance(state, dict):
        raise RuntimeError("install state is invalid")
    expected = _canonical_persisted_hashes(state.get("managed_hashes", {}))
    changed = []
    for relative, digest in expected.items():
        target = install_root / relative
        _assert_safe_mutation_path(install_root, target)
        if not target.is_file() or sha256_path(target).lower() != str(digest).lower():
            changed.append(relative)
    return sorted(changed)


def apply_release_archive(archive: Path, install_root: Path, expected_hash: Optional[str] = None, auto: bool = False) -> dict:
    archive = archive.resolve()
    install_root = _resolve_mutation_root(install_root)
    _assert_safe_mutation_path(install_root, install_root / STATE_DIR)
    _assert_safe_mutation_path(install_root, install_root / STATE_DIR / "install-state.json", require_file=True)
    _assert_safe_mutation_path(install_root, install_root / "release-manifest.json", require_file=True)
    index = verify_archive(archive, expected_hash)
    with tempfile.TemporaryDirectory(prefix="video-autopilot-update-") as temporary:
        stage = Path(temporary) / "release"
        with zipfile.ZipFile(archive) as package:
            package.extractall(stage)
        manifest = read_json(stage / "release-manifest.json")
        if manifest["version"] != index["version"]:
            raise RuntimeError("manifest/index version mismatch")
        current = detect_current_version(install_root)
        current_tuple, target_tuple = version_tuple(current), version_tuple(index["version"])
        if current_tuple and target_tuple and target_tuple < current_tuple:
            return {"status": "CURRENT", "current": current, "latest": index["version"]}
        if current_tuple and target_tuple and target_tuple == current_tuple:
            target_state = {
                "managed_hashes": {
                    _canonical_portable_relative(row["path"]): row["sha256"]
                    for row in index["files"]
                }
            }
            target_drift = locally_modified_managed_files(install_root, target_state)
            if not target_drift:
                return {"status": "CURRENT", "current": current, "latest": index["version"]}
            if auto:
                return {
                    "status": "CONFIRM_REQUIRED", "current": current,
                    "latest": index["version"],
                    "reason": "same-version managed files require explicit repair",
                    "modified": target_drift,
                }
        migration = declared_migration(current, index["version"], manifest)
        is_compatible = compatible_upgrade(current, manifest)
        if auto and (not is_compatible or not migration or not migration.get("automatic")):
            return {
                "status": "CONFIRM_REQUIRED",
                "current": current or "unversioned",
                "latest": index["version"],
                "reason": "release is outside the declared automatic-migration window",
            }
        protected = manifest["protected_globs"]
        managed = [_canonical_portable_relative(row["path"]) for row in index["files"]]
        bad = [relative for relative in managed if _matches(relative, protected)]
        if bad:
            raise RuntimeError("release attempts to manage protected paths: " + ", ".join(bad))
        state_dir = install_root / STATE_DIR
        previous_state_path = state_dir / "install-state.json"
        has_previous_state = previous_state_path.is_file()
        previous_state = read_json(previous_state_path) if has_previous_state else {}
        previous_managed, previous_hashes = _validated_install_state(previous_state) if has_previous_state else ([], {})
        legacy_nonempty = (
            not has_previous_state
            and install_root.exists()
            and any(install_root.iterdir())
        )
        if auto and legacy_nonempty:
            return {
                "status": "CONFIRM_REQUIRED",
                "current": current or "unversioned",
                "latest": index["version"],
                "reason": "one explicit bootstrap is required before automatic updates can own legacy files",
            }
        modified = locally_modified_managed_files(
            install_root, {"managed_hashes": previous_hashes}
        )
        if auto and modified:
            return {
                "status": "CONFIRM_REQUIRED",
                "current": current or "unversioned",
                "latest": index["version"],
                "reason": "locally modified managed files would be replaced",
                "modified": modified,
            }
        transaction = _new_transaction_id()
        backup_root = state_dir / "backups" / transaction
        record = {
            "schema_version": 1,
            "transaction": transaction,
            "started_at": utc_now(),
            "from_version": current or "unversioned",
            "to_version": index["version"],
            "migration": migration["id"] if migration else "explicit-unmanaged-upgrade",
            "replaced": [],
            "created": [],
            "removed": [],
            "had_previous_state": has_previous_state,
            "status": "PENDING",
        }
        _preflight_apply_paths(
            install_root, managed, previous_managed, backup_root
        )
        backup_root.mkdir(parents=True, exist_ok=False)
        if has_previous_state:
            shutil.copy2(previous_state_path, backup_root / "previous-install-state.json")
        atomic_json(backup_root / "transaction.json", record)
        try:
            for relative in managed:
                source = stage / relative
                target = install_root / relative
                _assert_contained_release_path(stage, source, require_file=True)
                if target.exists() and not target.is_file():
                    raise RuntimeError("managed file conflicts with directory: " + relative)
                if target.is_file() or target.is_symlink():
                    _backup_file(install_root, target, backup_root, relative)
                    record["replaced"].append(relative)
                else:
                    record["created"].append(relative)
                atomic_json(backup_root / "transaction.json", record)
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary_target = target.with_name(target.name + ".update-tmp")
                shutil.copy2(source, temporary_target)
                os.replace(temporary_target, target)
            stale = sorted(set(previous_managed) - set(managed))
            for relative in stale:
                if _matches(relative, protected):
                    continue
                target = install_root / relative
                if target.is_file() or target.is_symlink():
                    _backup_file(install_root, target, backup_root, relative)
                    record["removed"].append(relative)
                    atomic_json(backup_root / "transaction.json", record)
                    target.unlink()
            state = {
                "schema_version": 1,
                "project_id": "video-autopilot-kit",
                "version": index["version"],
                "installed_at": utc_now(),
                "managed_files": managed,
                "managed_hashes": {
                    relative: sha256_path(install_root / relative) for relative in managed
                },
                "last_transaction": transaction,
                "last_migration": record["migration"],
                "auto_update_compatible": is_compatible,
            }
            atomic_json(previous_state_path, state)
            record["status"] = "COMMITTED"
            record["finished_at"] = utc_now()
            atomic_json(backup_root / "transaction.json", record)
        except Exception:
            _rollback_record(install_root, record, backup_root)
            _restore_previous_state(install_root, backup_root)
            record["status"] = "ROLLED_BACK"
            record["finished_at"] = utc_now()
            atomic_json(backup_root / "transaction.json", record)
            raise
    return {
        "status": "UPDATED",
        "from": current or "unversioned",
        "to": index["version"],
        "managed_files": len(managed),
        "transaction": transaction,
        "backup": str(backup_root),
        "migration": record["migration"],
    }


def rollback(install_root: Path, transaction: Optional[str] = None) -> dict:
    install_root = _resolve_mutation_root(install_root)
    state_dir = install_root / STATE_DIR
    backups = state_dir / "backups"
    _assert_safe_mutation_path(install_root, state_dir)
    _assert_safe_mutation_path(install_root, backups)
    if transaction is not None:
        selected = _assert_transaction_id(transaction)
        backup_root = backups / selected
        _assert_safe_mutation_path(install_root, backup_root)
        candidates = [backup_root] if backup_root.is_dir() else []
    else:
        candidates = []
        if backups.is_dir():
            for path in backups.iterdir():
                _assert_safe_mutation_path(install_root, path)
                if path.is_dir():
                    _assert_transaction_id(path.name)
                    candidates.append(path)
        candidates.sort()
    if not candidates:
        raise RuntimeError("no update backup is available")
    backup_root = candidates[-1]
    transaction = _assert_transaction_id(backup_root.name)
    transaction_path = backup_root / "transaction.json"
    _assert_safe_mutation_path(install_root, transaction_path, require_file=True, allow_missing=False)
    record = _validated_transaction_record(read_json(transaction_path), transaction)
    if record.get("status") not in {"COMMITTED", "PENDING"}:
        raise RuntimeError("transaction cannot be rolled back in its current state")
    _preflight_rollback_paths(install_root, record, backup_root)
    state_path = state_dir / "install-state.json"
    has_current_state = state_path.is_file()
    current_state = read_json(state_path) if has_current_state else {}
    if has_current_state: _validated_install_state(current_state)
    previous_state_path = backup_root / "previous-install-state.json"
    has_previous_state = previous_state_path.is_file()
    previous_state = read_json(previous_state_path) if has_previous_state else {}
    _validated_transaction_record(record, transaction, current_state_present=has_current_state, previous_state_present=has_previous_state)
    if has_previous_state: _validated_install_state(previous_state, record.get("from_version"))
    _rollback_record(install_root, record, backup_root)
    _restore_previous_state(install_root, backup_root)
    state = dict(previous_state)
    if state:
        state.update(
            {
                "version": record["from_version"],
                "rolled_back_at": utc_now(),
                "rolled_back_transaction": record["transaction"],
            }
        )
        atomic_json(state_path, state)
    record["status"] = "MANUALLY_ROLLED_BACK"
    record["finished_at"] = utc_now()
    atomic_json(backup_root / "transaction.json", record)
    return {"status": "ROLLED_BACK", "to": record["from_version"], "transaction": record["transaction"]}


def check_update(channel_value: str, install_root: Path) -> dict:
    install_root = _resolve_mutation_root(install_root)
    channel, source = load_channel(channel_value)
    latest = channel["latest"]
    current = detect_current_version(install_root)
    current_tuple, latest_tuple = version_tuple(current), version_tuple(latest["version"])
    available = current_tuple is None or (latest_tuple is not None and latest_tuple > current_tuple)
    state_path = install_root / STATE_DIR / "install-state.json"
    _assert_safe_mutation_path(install_root, install_root / STATE_DIR)
    _assert_safe_mutation_path(install_root, state_path, require_file=True)
    state = read_json(state_path) if state_path.is_file() else {}
    modified = locally_modified_managed_files(install_root, state) if state else []
    status = "UPDATE_AVAILABLE" if available else (
        "REPAIR_AVAILABLE" if modified else "CURRENT"
    )
    return {
        "status": status,
        "current": current or "unversioned",
        "latest": latest["version"],
        "channel": source,
        "asset": resolve_channel_asset(latest["url"], source),
        "sha256": latest["sha256"],
        "modified": modified,
    }


def update_from_channel(channel_value: str, install_root: Path, apply: bool, auto: bool) -> dict:
    plan = check_update(channel_value, install_root)
    if not apply:
        return plan
    with tempfile.TemporaryDirectory(prefix="video-autopilot-download-") as temporary:
        archive = Path(temporary) / "release.zip"
        payload, _resolved = _read_url_or_path(plan["asset"], plan["channel"])
        archive.write_bytes(payload)
        return apply_release_archive(archive, install_root, plan["sha256"], auto=auto)


def sync_codex_skill(repo_root: Path, destination: Path, adopt: bool = False) -> dict:
    repo_root = repo_root.resolve(strict=True)
    manifest_path = repo_root / "release-manifest.json"
    _assert_contained_release_path(repo_root, manifest_path, require_file=True)
    manifest = read_json(manifest_path)
    source = repo_root / _canonical_portable_relative(manifest["codex_skill"]["source"])
    _assert_contained_release_path(repo_root, source)
    destination = _resolve_mutation_root(destination)
    marker = destination / ".video-autopilot-skill.json"
    _assert_safe_mutation_path(destination, marker, require_file=True)
    _assert_safe_mutation_path(destination, marker.with_name(marker.name + ".tmp"), require_file=True)
    has_marker = marker.is_file()
    if destination.exists() and not has_marker and not adopt:
        return {
            "status": "ADOPT_REQUIRED",
            "destination": str(destination),
            "reason": "existing skill is not managed by video-autopilot-kit",
        }
    marker_state = read_json(marker) if has_marker else {}
    previous_managed, previous_hashes = _validated_install_state(marker_state) if has_marker else ([], {})
    modified = locally_modified_managed_files(
        destination, {"managed_hashes": previous_hashes}
    )
    if modified and not adopt:
        return {
            "status": "CONFIRM_REQUIRED",
            "destination": str(destination),
            "reason": "locally modified managed Skill files would be replaced",
            "modified": modified,
        }
    sources: list[tuple[str, Path]] = []
    for path in sorted(source.rglob("*")):
        _assert_contained_release_path(repo_root, path)
        if "__pycache__" in path.parts or not path.is_file():
            continue
        _assert_contained_release_path(repo_root, path, require_file=True)
        relative = _canonical_portable_relative(path.relative_to(source).as_posix())
        sources.append((relative, path))
    managed = [relative for relative, _path in sources]
    stale = sorted(set(previous_managed) - set(managed))
    for relative in sorted(set(managed) | set(previous_managed)):
        target = destination / relative
        _assert_safe_mutation_path(destination, target, require_file=True)
        if target.exists() and not target.is_file():
            raise RuntimeError("managed Skill file conflicts with directory: " + relative)
        if relative in managed:
            _assert_safe_mutation_path(
                destination, target.with_name(target.name + ".skill-tmp"), require_file=True
            )
    destination.mkdir(parents=True, exist_ok=True)
    for relative, path in sources:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".skill-tmp")
        shutil.copy2(path, temporary)
        os.replace(temporary, target)
    for relative in stale:
        target = destination / relative
        if target.is_file():
            target.unlink()
    atomic_json(
        marker,
        {
            "schema_version": 1,
            "managed_by": "video-autopilot-kit",
            "repo_root": str(repo_root.resolve()),
            "version": manifest["version"],
            "managed_files": managed,
            "managed_hashes": {
                relative: sha256_path(destination / relative) for relative in managed
            },
            "synced_at": utc_now(),
        },
    )
    return {"status": "SYNCED", "destination": str(destination), "managed_files": len(managed)}


def auto_update(channel: str, install_root: Path, max_age_hours: float) -> dict:
    install_root = _resolve_mutation_root(install_root)
    cache = install_root / STATE_DIR / "update-cache.json"
    _assert_safe_mutation_path(install_root, install_root / STATE_DIR)
    _assert_safe_mutation_path(install_root, cache, require_file=True)
    _assert_safe_mutation_path(install_root, cache.with_name(cache.name + ".tmp"), require_file=True)
    if cache.is_file():
        age = time.time() - cache.stat().st_mtime
        if age < max_age_hours * 3600:
            return {"status": "CACHED", "next_check_seconds": round(max_age_hours * 3600 - age)}
    try:
        result = update_from_channel(channel, install_root, apply=True, auto=True)
        atomic_json(cache, {"checked_at": utc_now(), "result": result})
        return result
    except Exception as exc:  # network/update failure must not block editing work
        atomic_json(cache, {"checked_at": utc_now(), "status": "CHECK_FAILED", "error": "update failed: " + type(exc).__name__})
        return {"status": "CHECK_FAILED", "error": "update failed: " + type(exc).__name__, "non_blocking": True}


def self_test() -> None:
    """Lazy-load release fixtures without a circular or duplicate module import."""
    if __package__:
        from .release_manager_selftest import run_self_test
    else:
        from release_manager_selftest import run_self_test

    run_self_test(sys.modules[__name__])


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Safe release and upgrade manager")
    subs = parser.add_subparsers(dest="command", required=True)
    build = subs.add_parser("build")
    build.add_argument("--root", default=str(ROOT))
    build.add_argument("--dist")
    build.add_argument("--base-url")
    check = subs.add_parser("check")
    check.add_argument("--channel", default=DEFAULT_CHANNEL)
    check.add_argument("--install-root", default=str(ROOT))
    update = subs.add_parser("update")
    update.add_argument("--channel", default=DEFAULT_CHANNEL)
    update.add_argument("--install-root", default=str(ROOT))
    update.add_argument("--apply", action="store_true")
    update.add_argument("--auto", action="store_true")
    automatic = subs.add_parser("auto")
    automatic.add_argument("--channel", default=DEFAULT_CHANNEL)
    automatic.add_argument("--install-root", default=str(ROOT))
    automatic.add_argument("--max-age-hours", type=float, default=24)
    back = subs.add_parser("rollback")
    back.add_argument("--install-root", default=str(ROOT))
    back.add_argument("--transaction")
    skill = subs.add_parser("install-skill")
    skill.add_argument("--repo-root", default=str(ROOT))
    skill.add_argument("--destination", default=str(Path.home() / ".codex" / "skills" / "video-autopilot"))
    skill.add_argument("--adopt", action="store_true")
    subs.add_parser("selftest")
    args = parser.parse_args(argv)
    if args.command == "build":
        result = build_release(Path(args.root), Path(args.dist) if args.dist else None, args.base_url)
    elif args.command == "check":
        result = check_update(args.channel, Path(args.install_root))
    elif args.command == "update":
        result = update_from_channel(args.channel, Path(args.install_root), args.apply, args.auto)
    elif args.command == "auto":
        result = auto_update(args.channel, Path(args.install_root), args.max_age_hours)
    elif args.command == "rollback":
        result = rollback(Path(args.install_root), args.transaction)
    elif args.command == "install-skill":
        result = sync_codex_skill(Path(args.repo_root), Path(args.destination), args.adopt)
    else:
        self_test()
        return 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get("status") in {"CHECK_FAILED"} and not result.get("non_blocking") else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "error": "release command failed: " + type(exc).__name__}))
        raise SystemExit(1) from None
