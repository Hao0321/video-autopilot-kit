# -*- coding: utf-8 -*-
"""Regression fixtures for :mod:`release_manager`.

The production release manager lazy-loads this module only for ``selftest``.
Keeping the fixtures here prevents release-only test orchestration from
inflating the updater's runtime module while retaining the exact public API
module instance used by both direct-script and imported execution.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
import warnings
import zipfile
from pathlib import Path
from types import ModuleType
from typing import Callable, TypeVar


if __package__:
    from .release_test_support import _runtime_category, _run_stage, _directory_alias, _remove_directory_alias
    from .release_mutation_selftest import _self_test_apply_mutation_boundaries, _self_test_rollback_mutation_boundaries, _self_test_skill_mutation_boundaries, _self_test_mutation_boundaries
else:
    from release_test_support import _runtime_category, _run_stage, _directory_alias, _remove_directory_alias
    from release_mutation_selftest import _self_test_apply_mutation_boundaries, _self_test_rollback_mutation_boundaries, _self_test_skill_mutation_boundaries, _self_test_mutation_boundaries

def _self_test_transaction_ids(manager: ModuleType) -> None:
    transaction_ids = [manager._new_transaction_id() for _ in range(128)]
    assert len(transaction_ids) == len(set(transaction_ids))
    assert all(
        re.fullmatch(r"\d{8}T\d{12}Z-[0-9a-f]{12}", value)
        for value in transaction_ids
    )
    assert manager._assert_transaction_id("20260827T103100Z") == "20260827T103100Z"


def _self_test_package_import_shadowing(manager: ModuleType, base: Path) -> None:
    shadow = base / "shadow-import"
    shadow.mkdir()
    marker = base / "shadow-import-executed.txt"
    for name in ("release_integrity.py", "release_archive.py", "release_install.py", "release_build.py", "public_sync_catalog.py"):
        (shadow / name).write_text(
            f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n"
            "raise RuntimeError('shadow module executed')\n",
            encoding="utf-8",
        )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join((str(shadow), str(manager.ROOT)))
    completed = subprocess.run(
        [sys.executable, "-c", "import src.release_manager as manager; manager._load_sync_inventory_contract(manager.ROOT); print('GREEN')"],
        cwd=manager.ROOT, env=environment, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "GREEN"
    assert not marker.exists(), "package import executed a shadow integrity module"
    direct = subprocess.run(
        [sys.executable, str(manager.ROOT / "src" / "release_manager.py"), "--help"],
        cwd=shadow, env=environment, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=30,
    )
    assert direct.returncode == 0, direct.stderr
    assert "Safe release and upgrade manager" in direct.stdout
    assert not marker.exists(), "direct script executed a shadow release helper"


def _self_test_path_free_failures(manager: ModuleType, base: Path) -> None:
    canonical_parent = base / "canonical-mutation-parent"
    canonical_parent.mkdir()
    parent_alias = base / "mutation-parent-alias"
    _directory_alias(parent_alias, canonical_parent)
    try:
        resolved = manager._resolve_mutation_root(parent_alias / "install")
        assert resolved == (canonical_parent / "install").resolve()
    finally:
        _remove_directory_alias(parent_alias)

    private_channel = base / "private-owner" / "missing-channel.json"
    private_channel.parent.mkdir()
    private_label = str(private_channel)
    original_update = manager.update_from_channel

    def fail_update(*_args, **_kwargs):
        raise FileNotFoundError(private_label)

    manager.update_from_channel = fail_update
    try:
        result = manager.auto_update(private_label, base / "cache-install", 0)
    finally:
        manager.update_from_channel = original_update
    cache = manager.read_json(
        base / "cache-install" / manager.STATE_DIR / "update-cache.json"
    )
    assert result["error"] == "update failed: FileNotFoundError"
    assert private_label not in json.dumps({"result": result, "cache": cache})

    commands = [
        [
            sys.executable, str(Path(manager.__file__).resolve()), "check",
            "--channel", private_label, "--install-root", str(base / "cli-install"),
        ],
        [
            sys.executable, str(manager.ROOT / "install_or_upgrade.py"),
            "--channel", private_label, "--install-root", str(base / "bootstrap-install"),
            "--check",
        ],
    ]
    for command in commands:
        completed = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30,
        )
        assert completed.returncode == 1
        payload = json.loads(completed.stdout)
        assert payload["status"] == "FAILED"
        combined = completed.stdout + completed.stderr
        assert private_label not in combined and "Traceback" not in combined


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


if __package__:
    from .release_privacy_selftest import _self_test_tracked_release_scope, _self_test_review_capability_content, _self_test_review_artifact_exclusion, _self_test_license_and_name_privacy, _self_test_release_privacy, _self_test_privacy_gate_containment, _self_test_staged_receipt_parity, _self_test_release_link_containment
else:
    from release_privacy_selftest import _self_test_tracked_release_scope, _self_test_review_capability_content, _self_test_review_artifact_exclusion, _self_test_license_and_name_privacy, _self_test_release_privacy, _self_test_privacy_gate_containment, _self_test_staged_receipt_parity, _self_test_release_link_containment


if __package__:
    from .release_bootstrap_selftest import _run_bootstrap, _self_test_nested_bootstrap, _self_test_bootstrap_runtime_boundaries, _self_test_fresh_bootstrap
else:
    from release_bootstrap_selftest import _run_bootstrap, _self_test_nested_bootstrap, _self_test_bootstrap_runtime_boundaries, _self_test_fresh_bootstrap


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
    target_manifest = manager.read_json(manager.ROOT / "release-manifest.json")
    migration = manager.declared_migration(
        old_manifest["version"], built["version"], target_manifest
    )
    assert migration is not None
    automatic = manager.apply_release_archive(archive, upgrade, digest, auto=True)
    if migration.get("automatic"):
        assert automatic["status"] == "UPDATED"
    else:
        # A release that retires runtimes an older entry point may re-execute
        # after an automatic update must wait for an explicit upgrade.
        assert automatic["status"] == "CONFIRM_REQUIRED", automatic
        assert "automatic-migration window" in automatic["reason"]
        assert manager.detect_current_version(upgrade) == old_manifest["version"]
        assert manager.apply_release_archive(archive, upgrade, digest, auto=False)[
            "status"
        ] == "UPDATED"
    assert manager.detect_current_version(upgrade) == built["version"]
    assert protected_media.read_bytes() == b"user-media"
    assert custom.read_text(encoding="utf-8") == "keep me"
    assert manager.apply_release_archive(archive, upgrade, digest, auto=True)[
        "status"
    ] == "CURRENT"
    assert manager.rollback(upgrade)["status"] == "ROLLED_BACK"
    assert manager.detect_current_version(upgrade) == old_manifest["version"]
    assert protected_media.read_bytes() == b"user-media"
    assert custom.is_file()


def _self_test_automatic_patch_upgrade(
    manager: ModuleType, base: Path, built: dict
) -> None:
    """Patch releases inside the current window still update automatically."""
    source = base / "next-patch-source"
    _copy_current_release_source(manager, source)
    manifest = manager.read_json(source / "release-manifest.json")
    current = manager.version_tuple(manifest["version"])
    assert current is not None
    manifest["version"] = "%d.%d.%d" % (current[0], current[1], current[2] + 1)
    migration = manager.declared_migration(built["version"], manifest["version"], manifest)
    assert migration is not None and migration.get("automatic") is True
    manager.atomic_json(source / "release-manifest.json", manifest)
    next_release = manager.build_release(source, base / "next-patch-dist")
    install = base / "automatic-patch-upgrade"
    assert manager.apply_release_archive(
        Path(built["archive"]), install, built["sha256"], auto=False
    )["status"] == "UPDATED"
    assert manager.apply_release_archive(
        Path(next_release["archive"]), install, next_release["sha256"], auto=True
    )["status"] == "UPDATED"
    assert manager.detect_current_version(install) == manifest["version"]
    assert manager.rollback(install)["status"] == "ROLLED_BACK"
    assert manager.detect_current_version(install) == built["version"]


def _copy_current_release_source(manager: ModuleType, destination: Path) -> None:
    """Snapshot only the current manifest-owned source for release fixtures.

    collect_release_files enforces containment, privacy and tracked ownership.
    Unknown media, .rd evidence and older dist directories are never copied.
    """
    manifest = manager.read_json(manager.ROOT / "release-manifest.json")
    files = manager.collect_release_files(manager.ROOT, manifest)
    for source in files:
        target = destination / source.relative_to(manager.ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def run_self_test(manager: ModuleType) -> None:
    """Run every release/update regression against the supplied module instance."""
    _run_stage("transaction-ids", lambda: _self_test_transaction_ids(manager))
    with tempfile.TemporaryDirectory(
        prefix="video-autopilot-release-selftest-"
    ) as temporary:
        base = Path(temporary)
        _run_stage(
            "package-import-shadowing",
            lambda: _self_test_package_import_shadowing(manager, base),
        )
        _run_stage(
            "path-free-failures",
            lambda: _self_test_path_free_failures(manager, base),
        )
        source = base / "source"
        _run_stage(
            "source-copy",
            lambda: _copy_current_release_source(manager, source),
        )
        built = _run_stage(
            "release-build",
            lambda: manager.build_release(source, base / "dist"),
        )
        verified = _run_stage(
            "archive-verify",
            lambda: manager.verify_archive(
                Path(built["archive"]), built["sha256"]
            ),
        )
        assert verified["version"] == built["version"]
        stages = (
            ("archive-verifier", lambda: _self_test_archive_verifier(manager, base)),
            (
                "release-privacy",
                lambda: _self_test_release_privacy(manager, base, source),
            ),
            (
                "privacy-gate-containment",
                lambda: _self_test_privacy_gate_containment(manager, base, source),
            ),
            (
                "staged-receipt-parity",
                lambda: _self_test_staged_receipt_parity(manager, base, source),
            ),
            (
                "release-link-containment",
                lambda: _self_test_release_link_containment(manager, base, source),
            ),
            (
                "mutation-boundaries",
                lambda: _self_test_mutation_boundaries(manager, base, built),
            ),
            (
                "fresh-bootstrap",
                lambda: _self_test_fresh_bootstrap(manager, base, source, built),
            ),
            (
                "legacy-adoption",
                lambda: _self_test_legacy_adoption(manager, base, built),
            ),
            (
                "modified-managed-update",
                lambda: _self_test_modified_managed_update(
                    manager, base, source, built
                ),
            ),
            (
                "compatible-upgrade",
                lambda: _self_test_compatible_upgrade(manager, base, built),
            ),
            (
                "automatic-patch-upgrade",
                lambda: _self_test_automatic_patch_upgrade(manager, base, built),
            ),
        )
        for label, action in stages:
            _run_stage(label, action)
    print("release_manager self-test GREEN")
