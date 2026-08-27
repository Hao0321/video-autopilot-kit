# -*- coding: utf-8 -*-
"""Regression fixtures for :mod:`release_manager`.

The production release manager lazy-loads this module only for ``selftest``.
Keeping the fixtures here prevents release-only test orchestration from
inflating the updater's runtime module while retaining the exact public API
module instance used by both direct-script and imported execution.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import warnings
import zipfile
from pathlib import Path
from types import ModuleType


def _self_test_transaction_ids(manager: ModuleType) -> None:
    transaction_ids = [manager._new_transaction_id() for _ in range(128)]
    assert len(transaction_ids) == len(set(transaction_ids))
    assert all(
        re.fullmatch(r"\d{8}T\d{12}Z-[0-9a-f]{12}", value)
        for value in transaction_ids
    )


def _synthetic_archive(
    base: Path,
    name: str,
    entries: list[tuple[str, bytes]],
    rows: list[dict],
    include_index: bool = True,
) -> Path:
    target = base / name
    members = list(entries)
    if include_index:
        index_payload = json.dumps(
            {
                "schema_version": 1,
                "project_id": "video-autopilot-kit",
                "version": "0.0.0",
                "files": rows,
            }
        ).encode("utf-8")
        members.append(("release-index.json", index_payload))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as package:
            for relative, payload in members:
                package.writestr(relative, payload)
    return target


def _expect_archive_rule(manager: ModuleType, target: Path, rule: str) -> None:
    try:
        manager.verify_archive(target)
    except RuntimeError as exc:
        assert str(exc) == "archive verification failed: " + rule
        assert "private-looking-artifact" not in str(exc)
    else:
        raise AssertionError("tampered archive passed rule " + rule)


def _self_test_archive_verifier(manager: ModuleType, base: Path) -> None:
    payload = b"closed-world-fixture"
    row = {
        "path": "payload.txt",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size": len(payload),
    }
    cases = [
        (
            "duplicate-member.zip",
            [("payload.txt", payload), ("payload.txt", payload)],
            [row],
            True,
            "duplicate-zip-member",
        ),
        (
            "unsafe-member.zip",
            [("../private-looking-artifact.txt", b"private")],
            [],
            True,
            "unsafe-zip-member-path",
        ),
        (
            "unsafe-index-path.zip",
            [("payload.txt", payload)],
            [{**row, "path": "../private-looking-artifact.txt"}],
            True,
            "unsafe-index-path",
        ),
        (
            "duplicate-index-path.zip",
            [("payload.txt", payload)],
            [row, dict(row)],
            True,
            "duplicate-index-path",
        ),
        (
            "extra-member.zip",
            [("payload.txt", payload), ("private-looking-artifact.txt", b"private")],
            [row],
            True,
            "extra-unindexed-member",
        ),
        ("missing-member.zip", [], [row], True, "missing-indexed-member"),
        (
            "size-mismatch.zip",
            [("payload.txt", payload)],
            [{**row, "size": len(payload) + 1}],
            True,
            "indexed-size-mismatch",
        ),
        (
            "hash-mismatch.zip",
            [("payload.txt", payload)],
            [{**row, "sha256": "0" * 64}],
            True,
            "indexed-hash-mismatch",
        ),
        ("missing-index.zip", [], [], False, "missing-release-index"),
    ]
    for name, entries, rows, include_index, rule in cases:
        _expect_archive_rule(
            manager,
            _synthetic_archive(base, name, entries, rows, include_index),
            rule,
        )


def _self_test_release_privacy(
    manager: ModuleType, base: Path, source: Path
) -> None:
    license_probe = base / "license-probe"
    shutil.copytree(source, license_probe)
    secret_fixture = "github_" + "pat_" + "abcdefghijklmnopqrstuvwxyz123456"
    license_path = license_probe / "LICENSE"
    license_original = license_path.read_text(encoding="utf-8")
    license_path.write_text(
        license_original + "\n" + secret_fixture + "\n", encoding="utf-8"
    )
    try:
        manager.build_release(license_probe, base / "license-probe-dist")
    except RuntimeError as exc:
        message = str(exc)
        assert "secret-shaped-token" in message
        assert secret_fixture not in message
    else:
        raise AssertionError("release manager accepted a secret-shaped LICENSE")
    license_path.write_text(license_original, encoding="utf-8")
    private_name = "private.person" + "@" + "example.test.bin"
    (license_probe / "examples" / private_name).write_bytes(b"safe fixture")
    manifest = manager.read_json(license_probe / "release-manifest.json")
    errors = manager.validate_release_tree(
        license_probe,
        manifest,
        manager.collect_release_files(license_probe, manifest),
    )
    message = "\n".join(errors)
    assert "email-address" in message
    assert private_name not in message


def _self_test_legacy_adoption(
    manager: ModuleType, base: Path, built: dict
) -> None:
    install = base / "legacy"
    (install / "profiles").mkdir(parents=True)
    (install / "src").mkdir(parents=True)
    (install / "README.md").write_text("legacy install", encoding="utf-8")
    (install / "profiles" / "mine.md").write_text("private", encoding="utf-8")
    (install / "custom.txt").write_text("custom", encoding="utf-8")
    archive, digest = Path(built["archive"]), built["sha256"]
    assert manager.apply_release_archive(archive, install, digest, auto=True)[
        "status"
    ] == "CONFIRM_REQUIRED"
    assert manager.apply_release_archive(archive, install, digest, auto=False)[
        "status"
    ] == "UPDATED"
    assert (install / "profiles" / "mine.md").read_text(encoding="utf-8") == "private"
    assert (install / "custom.txt").read_text(encoding="utf-8") == "custom"
    state = manager.read_json(install / manager.STATE_DIR / "install-state.json")
    assert state["version"] == built["version"]
    assert manager.rollback(install)["status"] == "ROLLED_BACK"
    assert (install / "README.md").read_text(encoding="utf-8") == "legacy install"
    assert (install / "profiles" / "mine.md").is_file()
    assert not (install / manager.STATE_DIR / "install-state.json").exists()


def _run_workspace_migration(clean: Path) -> dict:
    migrated = subprocess.run(
        [
            sys.executable,
            str(clean / "src" / "workspace_migrator.py"),
            "apply",
            "--root",
            str(clean),
        ],
        cwd=clean,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert migrated.returncode == 0, migrated.stderr or migrated.stdout
    return json.loads(migrated.stdout)


def _self_test_modified_managed_update(
    manager: ModuleType, base: Path, source: Path, built: dict
) -> None:
    clean = base / "clean"
    archive, digest = Path(built["archive"]), built["sha256"]
    assert manager.apply_release_archive(archive, clean, digest, auto=False)[
        "status"
    ] == "UPDATED"
    completed = (
        clean
        / "videos"
        / "_INBOX"
        / "直式-vertical-Shorts-Reels"
        / "7"
        / "_out"
        / "current.mp4"
    )
    completed.parent.mkdir(parents=True)
    completed.write_bytes(b"fixture-completed-video")
    (completed.parents[1] / "_plan.py").write_text(
        "SPEC = {'name': 'fixture_7', 'what': 'fixture', 'niche': 'toy'}\nCOPY = {}\n",
        encoding="utf-8",
    )
    assert _run_workspace_migration(clean)["status"] == "MIGRATED"
    assert (clean / "00_發布中樞_從這裡開始.md").is_file()
    assert list((clean / "videos" / "_PUBLISH_HUB").rglob("publish.json"))
    assert _run_workspace_migration(clean)["status"] == "CURRENT"
    (clean / "README.md").write_text("my local edit", encoding="utf-8")
    manifest = manager.read_json(source / "release-manifest.json")
    current = manager.version_tuple(manifest["version"])
    assert current is not None
    manifest["version"] = "%d.%d.%d" % (current[0], current[1], current[2] + 1)
    manager.atomic_json(source / "release-manifest.json", manifest)
    next_release = manager.build_release(source, base / "dist2")
    blocked = manager.apply_release_archive(
        Path(next_release["archive"]), clean, next_release["sha256"], auto=True
    )
    assert blocked["status"] == "CONFIRM_REQUIRED"
    assert "README.md" in blocked["modified"]


def _build_previous_release(
    manager: ModuleType, base: Path
) -> tuple[dict, dict]:
    source = base / "previous-source"
    shutil.copytree(
        manager.ROOT,
        source,
        ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", "*.pyc"),
    )
    manifest = manager.read_json(source / "release-manifest.json")
    target = manager.version_tuple(manifest["version"])
    assert target is not None
    if target[2] > 0:
        previous = (target[0], target[1], target[2] - 1)
    else:
        assert target[1] > 0
        previous = (target[0], target[1] - 1, 0)
    manifest["version"] = "%d.%d.%d" % previous
    manifest["compatibility"]["maximum_exclusive"] = "%d.%d.%d" % (
        target[0],
        target[1] + 1,
        0,
    )
    manifest["migrations"] = [
        {
            "id": "selftest-previous-window",
            "from": "unversioned",
            "target_minimum": manifest["version"],
            "target_maximum_exclusive": "%d.%d.%d" % target,
            "idempotent": True,
            "automatic": False,
        }
    ]
    manager.atomic_json(source / "release-manifest.json", manifest)
    return manager.build_release(source, base / "old-dist"), manifest


def _self_test_compatible_upgrade(
    manager: ModuleType, base: Path, built: dict
) -> None:
    old_built, old_manifest = _build_previous_release(manager, base)
    upgrade = base / "compatible-upgrade"
    assert manager.apply_release_archive(
        Path(old_built["archive"]), upgrade, old_built["sha256"], auto=False
    )["status"] == "UPDATED"
    protected_media = upgrade / "videos" / "keep.mp4"
    protected_media.parent.mkdir(parents=True)
    protected_media.write_bytes(b"user-media")
    custom = upgrade / "my-local-notes.txt"
    custom.write_text("keep me", encoding="utf-8")
    archive, digest = Path(built["archive"]), built["sha256"]
    assert manager.apply_release_archive(archive, upgrade, digest, auto=True)[
        "status"
    ] == "UPDATED"
    assert protected_media.read_bytes() == b"user-media"
    assert custom.read_text(encoding="utf-8") == "keep me"
    assert manager.apply_release_archive(archive, upgrade, digest, auto=True)[
        "status"
    ] == "CURRENT"
    assert manager.rollback(upgrade)["status"] == "ROLLED_BACK"
    assert manager.detect_current_version(upgrade) == old_manifest["version"]
    assert protected_media.read_bytes() == b"user-media"
    assert custom.is_file()


def run_self_test(manager: ModuleType) -> None:
    """Run every release/update regression against the supplied module instance."""
    _self_test_transaction_ids(manager)
    with tempfile.TemporaryDirectory(
        prefix="video-autopilot-release-selftest-"
    ) as temporary:
        base = Path(temporary)
        source = base / "source"
        shutil.copytree(
            manager.ROOT,
            source,
            ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", "*.pyc"),
        )
        built = manager.build_release(source, base / "dist")
        verified = manager.verify_archive(Path(built["archive"]), built["sha256"])
        assert verified["version"] == built["version"]
        _self_test_archive_verifier(manager, base)
        _self_test_release_privacy(manager, base, source)
        _self_test_legacy_adoption(manager, base, built)
        _self_test_modified_managed_update(manager, base, source, built)
        _self_test_compatible_upgrade(manager, base, built)
    print("release_manager self-test GREEN")
