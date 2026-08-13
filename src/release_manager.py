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
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable, Optional


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHANNEL = (
    "https://github.com/Hao0321/video-autopilot-kit/releases/latest/"
    "download/release-channel.json"
)
STATE_DIR = ".video-autopilot"
TEXT_EXTENSIONS = {".py", ".md", ".json", ".yaml", ".yml", ".toml", ".txt"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def _safe_relative(value: str) -> str:
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("unsafe release path: %r" % value)
    return path.as_posix()


def collect_release_files(root: Path, manifest: dict) -> list[Path]:
    includes = manifest["managed_include"]
    excludes = manifest["exclude_globs"]
    protected = manifest["protected_globs"]
    found = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if not _matches(relative, includes) or _matches(relative, excludes):
            continue
        if _matches(relative, protected):
            raise RuntimeError("protected path entered release: " + relative)
        found.append(path)
    return sorted(found, key=lambda item: item.relative_to(root).as_posix())


def validate_release_tree(root: Path, manifest: dict, files: list[Path]) -> list[str]:
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
    for path in files:
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if path == root / "release-manifest.json":
            # The manifest intentionally contains the deny-pattern declarations.
            # Remove that one field before scanning the rest of the manifest so
            # declarations are not mistaken for leaked values.
            sanitized_manifest = read_json(path)
            sanitized_manifest.get("privacy", {}).pop("deny_text_patterns", None)
            text = json.dumps(sanitized_manifest, ensure_ascii=False)
        for pattern in deny_patterns:
            if pattern.search(text):
                errors.append(
                    "private/path token %r in %s"
                    % (pattern.pattern, path.relative_to(root).as_posix())
                )
    return errors


def _release_payload(path: Path) -> bytes:
    payload = path.read_bytes()
    if path.suffix.lower() in TEXT_EXTENSIONS or path.name in {"LICENSE", ".gitignore"}:
        text = payload.decode("utf-8-sig")
        return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return payload


def _deterministic_zip(source: Path, archive: Path) -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
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
    root = root.resolve()
    manifest = read_json(root / "release-manifest.json")
    version = manifest["version"]
    files = collect_release_files(root, manifest)
    errors = validate_release_tree(root, manifest, files)
    if errors:
        raise RuntimeError("release validation failed:\n- " + "\n- ".join(errors))
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
    state = install_root / STATE_DIR / "install-state.json"
    if state.is_file():
        return read_json(state).get("version")
    manifest = install_root / "release-manifest.json"
    if manifest.is_file():
        return read_json(manifest).get("version")
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
    if expected_hash and sha256_path(archive).lower() != expected_hash.lower():
        raise RuntimeError("release archive SHA-256 mismatch")
    with zipfile.ZipFile(archive) as package:
        names = set(package.namelist())
        for name in names:
            _safe_relative(name)
        if "release-index.json" not in names:
            raise RuntimeError("release-index.json missing from archive")
        index = json.loads(package.read("release-index.json").decode("utf-8"))
        if index.get("project_id") != "video-autopilot-kit":
            raise RuntimeError("archive belongs to another project")
        for row in index.get("files", []):
            relative = _safe_relative(row["path"])
            if relative not in names:
                raise RuntimeError("indexed file missing: " + relative)
            digest = hashlib.sha256(package.read(relative)).hexdigest()
            if digest.lower() != row["sha256"].lower():
                raise RuntimeError("file hash mismatch: " + relative)
    return index


def _backup_file(source: Path, backup_root: Path, relative: str) -> None:
    target = backup_root / "files" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _rollback_record(install_root: Path, record: dict, backup_root: Path) -> None:
    for relative in reversed(record.get("created", [])):
        target = install_root / relative
        if target.is_file() or target.is_symlink():
            target.unlink()
    for relative in record.get("replaced", []) + record.get("removed", []):
        source = backup_root / "files" / relative
        target = install_root / relative
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def _restore_previous_state(install_root: Path, backup_root: Path) -> None:
    state_path = install_root / STATE_DIR / "install-state.json"
    previous = backup_root / "previous-install-state.json"
    if previous.is_file():
        state_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(previous, state_path)
    elif state_path.is_file():
        state_path.unlink()


def locally_modified_managed_files(install_root: Path, state: dict) -> list[str]:
    expected = state.get("managed_hashes", {})
    changed = []
    for relative, digest in expected.items():
        target = install_root / relative
        if not target.is_file() or sha256_path(target).lower() != str(digest).lower():
            changed.append(relative)
    return sorted(changed)


def apply_release_archive(
    archive: Path,
    install_root: Path,
    expected_hash: Optional[str] = None,
    auto: bool = False,
) -> dict:
    archive = archive.resolve()
    install_root = install_root.resolve()
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
        if current_tuple and target_tuple and target_tuple <= current_tuple:
            return {"status": "CURRENT", "current": current, "latest": index["version"]}
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
        managed = [_safe_relative(row["path"]) for row in index["files"]]
        bad = [relative for relative in managed if _matches(relative, protected)]
        if bad:
            raise RuntimeError("release attempts to manage protected paths: " + ", ".join(bad))
        state_dir = install_root / STATE_DIR
        previous_state_path = state_dir / "install-state.json"
        previous_state = read_json(previous_state_path) if previous_state_path.is_file() else {}
        legacy_nonempty = not previous_state_path.is_file() and install_root.exists() and any(install_root.iterdir())
        if auto and legacy_nonempty:
            return {
                "status": "CONFIRM_REQUIRED",
                "current": current or "unversioned",
                "latest": index["version"],
                "reason": "one explicit bootstrap is required before automatic updates can own legacy files",
            }
        modified = locally_modified_managed_files(install_root, previous_state)
        if auto and modified:
            return {
                "status": "CONFIRM_REQUIRED",
                "current": current or "unversioned",
                "latest": index["version"],
                "reason": "locally modified managed files would be replaced",
                "modified": modified,
            }
        previous_managed = set(previous_state.get("managed_files", []))
        transaction = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
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
            "status": "PENDING",
        }
        backup_root.mkdir(parents=True, exist_ok=False)
        if previous_state_path.is_file():
            shutil.copy2(previous_state_path, backup_root / "previous-install-state.json")
        atomic_json(backup_root / "transaction.json", record)
        try:
            for relative in managed:
                source = stage / relative
                target = install_root / relative
                if target.exists() and not target.is_file():
                    raise RuntimeError("managed file conflicts with directory: " + relative)
                if target.is_file() or target.is_symlink():
                    _backup_file(target, backup_root, relative)
                    record["replaced"].append(relative)
                else:
                    record["created"].append(relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary_target = target.with_name(target.name + ".update-tmp")
                shutil.copy2(source, temporary_target)
                os.replace(temporary_target, target)
            stale = sorted(previous_managed - set(managed))
            for relative in stale:
                if _matches(relative, protected):
                    continue
                target = install_root / relative
                if target.is_file() or target.is_symlink():
                    _backup_file(target, backup_root, relative)
                    target.unlink()
                    record["removed"].append(relative)
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
    state_dir = install_root.resolve() / STATE_DIR
    backups = state_dir / "backups"
    candidates = sorted(path for path in backups.glob("*") if path.is_dir())
    if not candidates:
        raise RuntimeError("no update backup is available")
    backup_root = backups / transaction if transaction else candidates[-1]
    record = read_json(backup_root / "transaction.json")
    if record.get("status") not in {"COMMITTED", "PENDING"}:
        raise RuntimeError("transaction cannot be rolled back: " + str(record.get("status")))
    _rollback_record(install_root.resolve(), record, backup_root)
    _restore_previous_state(install_root.resolve(), backup_root)
    state_path = state_dir / "install-state.json"
    state = read_json(state_path) if state_path.is_file() else {}
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
    channel, source = load_channel(channel_value)
    latest = channel["latest"]
    current = detect_current_version(install_root)
    current_tuple, latest_tuple = version_tuple(current), version_tuple(latest["version"])
    available = current_tuple is None or (latest_tuple is not None and latest_tuple > current_tuple)
    return {
        "status": "UPDATE_AVAILABLE" if available else "CURRENT",
        "current": current or "unversioned",
        "latest": latest["version"],
        "channel": source,
        "asset": resolve_channel_asset(latest["url"], source),
        "sha256": latest["sha256"],
    }


def update_from_channel(channel_value: str, install_root: Path, apply: bool, auto: bool) -> dict:
    plan = check_update(channel_value, install_root)
    if plan["status"] == "CURRENT" or not apply:
        return plan
    with tempfile.TemporaryDirectory(prefix="video-autopilot-download-") as temporary:
        archive = Path(temporary) / "release.zip"
        payload, _resolved = _read_url_or_path(plan["asset"], plan["channel"])
        archive.write_bytes(payload)
        return apply_release_archive(archive, install_root, plan["sha256"], auto=auto)


def sync_codex_skill(repo_root: Path, destination: Path, adopt: bool = False) -> dict:
    manifest = read_json(repo_root / "release-manifest.json")
    source = repo_root / manifest["codex_skill"]["source"]
    marker = destination / ".video-autopilot-skill.json"
    if destination.exists() and not marker.is_file() and not adopt:
        return {
            "status": "ADOPT_REQUIRED",
            "destination": str(destination),
            "reason": "existing skill is not managed by video-autopilot-kit",
        }
    destination.mkdir(parents=True, exist_ok=True)
    marker_state = read_json(marker) if marker.is_file() else {"managed_files": []}
    modified = locally_modified_managed_files(destination, marker_state)
    if modified and not adopt:
        return {
            "status": "CONFIRM_REQUIRED",
            "destination": str(destination),
            "reason": "locally modified managed Skill files would be replaced",
            "modified": modified,
        }
    managed = []
    for path in sorted(source.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(source).as_posix()
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        managed.append(relative)
    for relative in set(marker_state.get("managed_files", [])) - set(managed):
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
    cache = install_root / STATE_DIR / "update-cache.json"
    if cache.is_file():
        age = time.time() - cache.stat().st_mtime
        if age < max_age_hours * 3600:
            return {"status": "CACHED", "next_check_seconds": round(max_age_hours * 3600 - age)}
    try:
        result = update_from_channel(channel, install_root, apply=True, auto=True)
        atomic_json(cache, {"checked_at": utc_now(), "result": result})
        return result
    except Exception as exc:  # network/update failure must not block editing work
        atomic_json(cache, {"checked_at": utc_now(), "status": "CHECK_FAILED", "error": str(exc)})
        return {"status": "CHECK_FAILED", "error": str(exc), "non_blocking": True}


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="video-autopilot-release-selftest-") as temporary:
        base = Path(temporary)
        source = base / "source"
        shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", "*.pyc"))
        dist = base / "dist"
        built = build_release(source, dist)
        assert verify_archive(Path(built["archive"]), built["sha256"])["version"] == built["version"]
        install = base / "legacy"
        (install / "profiles").mkdir(parents=True)
        (install / "src").mkdir(parents=True)
        (install / "README.md").write_text("legacy install", encoding="utf-8")
        (install / "profiles" / "mine.md").write_text("private", encoding="utf-8")
        (install / "custom.txt").write_text("custom", encoding="utf-8")
        blocked_legacy = apply_release_archive(Path(built["archive"]), install, built["sha256"], auto=True)
        assert blocked_legacy["status"] == "CONFIRM_REQUIRED"
        result = apply_release_archive(Path(built["archive"]), install, built["sha256"], auto=False)
        assert result["status"] == "UPDATED"
        assert (install / "profiles" / "mine.md").read_text(encoding="utf-8") == "private"
        assert (install / "custom.txt").read_text(encoding="utf-8") == "custom"
        assert read_json(install / STATE_DIR / "install-state.json")["version"] == built["version"]
        rolled = rollback(install)
        assert rolled["status"] == "ROLLED_BACK"
        assert (install / "README.md").read_text(encoding="utf-8") == "legacy install"
        assert (install / "profiles" / "mine.md").is_file()
        assert not (install / STATE_DIR / "install-state.json").exists()

        # A managed local edit is never silently overwritten by automatic mode.
        clean = base / "clean"
        first = apply_release_archive(Path(built["archive"]), clean, built["sha256"], auto=False)
        assert first["status"] == "UPDATED"
        completed = clean / "videos" / "_INBOX" / "直式-vertical-Shorts-Reels" / "7" / "_out" / "current.mp4"
        completed.parent.mkdir(parents=True)
        completed.write_bytes(b"fixture-completed-video")
        plan_path = completed.parents[1] / "_plan.py"
        plan_path.write_text(
            "SPEC = {'name': 'fixture_7', 'what': 'fixture', 'niche': 'toy'}\nCOPY = {}\n",
            encoding="utf-8",
        )
        migrated = subprocess.run(
            [sys.executable, str(clean / "src" / "workspace_migrator.py"),
             "apply", "--root", str(clean)],
            cwd=clean, capture_output=True, encoding="utf-8", errors="replace", timeout=60,
        )
        assert migrated.returncode == 0, migrated.stderr or migrated.stdout
        migrated_payload = json.loads(migrated.stdout)
        assert migrated_payload["status"] == "MIGRATED"
        assert (clean / "00_發布中樞_從這裡開始.md").is_file()
        assert list((clean / "videos" / "_PUBLISH_HUB").rglob("publish.json"))
        migrated_again = subprocess.run(
            [sys.executable, str(clean / "src" / "workspace_migrator.py"),
             "apply", "--root", str(clean)],
            cwd=clean, capture_output=True, encoding="utf-8", errors="replace", timeout=60,
        )
        assert migrated_again.returncode == 0
        assert json.loads(migrated_again.stdout)["status"] == "CURRENT"
        (clean / "README.md").write_text("my local edit", encoding="utf-8")
        source_manifest = read_json(source / "release-manifest.json")
        current_tuple = version_tuple(source_manifest["version"])
        assert current_tuple is not None
        source_manifest["version"] = "%d.%d.%d" % (
            current_tuple[0], current_tuple[1], current_tuple[2] + 1
        )
        atomic_json(source / "release-manifest.json", source_manifest)
        built2 = build_release(source, base / "dist2")
        blocked = apply_release_archive(Path(built2["archive"]), clean, built2["sha256"], auto=True)
        assert blocked["status"] == "CONFIRM_REQUIRED"
        assert "README.md" in blocked["modified"]

        # A real N-1 managed install auto-upgrades, preserves workspace data,
        # becomes idempotently CURRENT, and can roll back to the older code.
        previous_source = base / "previous-source"
        shutil.copytree(ROOT, previous_source,
                        ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", "*.pyc"))
        previous_manifest = read_json(previous_source / "release-manifest.json")
        target_version = version_tuple(previous_manifest["version"])
        assert target_version is not None and target_version[2] == 0 and target_version[1] > 0
        previous_manifest["version"] = "%d.%d.%d" % (
            target_version[0], target_version[1] - 1, 0
        )
        previous_manifest["compatibility"]["maximum_exclusive"] = "%d.%d.%d" % (
            target_version[0], target_version[1] + 1, 0
        )
        previous_manifest["migrations"] = [{
            "id": "selftest-previous-window",
            "from": "unversioned",
            "target_minimum": previous_manifest["version"],
            "target_maximum_exclusive": "%d.%d.%d" % (
                target_version[0], target_version[1], 0
            ),
            "idempotent": True,
            "automatic": False,
        }]
        atomic_json(previous_source / "release-manifest.json", previous_manifest)
        old_built = build_release(previous_source, base / "old-dist")
        upgrade = base / "compatible-upgrade"
        first_old = apply_release_archive(Path(old_built["archive"]), upgrade,
                                          old_built["sha256"], auto=False)
        assert first_old["status"] == "UPDATED"
        protected_media = upgrade / "videos" / "keep.mp4"
        protected_media.parent.mkdir(parents=True)
        protected_media.write_bytes(b"user-media")
        custom = upgrade / "my-local-notes.txt"
        custom.write_text("keep me", encoding="utf-8")
        compatible = apply_release_archive(Path(built["archive"]), upgrade,
                                           built["sha256"], auto=True)
        assert compatible["status"] == "UPDATED"
        assert protected_media.read_bytes() == b"user-media"
        assert custom.read_text(encoding="utf-8") == "keep me"
        second = apply_release_archive(Path(built["archive"]), upgrade,
                                       built["sha256"], auto=True)
        assert second["status"] == "CURRENT"
        restored = rollback(upgrade)
        assert restored["status"] == "ROLLED_BACK"
        assert detect_current_version(upgrade) == previous_manifest["version"]
        assert protected_media.read_bytes() == b"user-media"
        assert custom.is_file()
    print("release_manager self-test GREEN")


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
    raise SystemExit(main())
