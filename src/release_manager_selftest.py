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


_StageResult = TypeVar("_StageResult")


def _runtime_category(exc: RuntimeError) -> str:
    message = str(exc)
    if message.startswith("release validation failed:"):
        return "release-validation"
    if message.startswith("release sync-receipt parity failed:"):
        return "sync-receipt-parity"
    if message.startswith("archive verification failed:"):
        return "archive-verification"
    return "runtime"


def _run_stage(label: str, action: Callable[[], _StageResult]) -> _StageResult:
    """Emit path-free progress while preserving the original failure type."""
    print(f"release_manager self-test START: {label}", flush=True)
    try:
        result = action()
    except Exception as exc:
        category = (
            _runtime_category(exc) if isinstance(exc, RuntimeError)
            else type(exc).__name__
        )
        # Report only a public fixture line number, never exception text or a
        # temporary path that could contain a copied capability or secret.
        fixture_frames = [frame for frame in traceback.extract_tb(exc.__traceback__)
                          if Path(frame.filename).name == "release_manager_selftest.py"]
        site = f" line {fixture_frames[-1].lineno}" if fixture_frames else ""
        print(
            f"release_manager self-test RED: {label} ({category}{site})",
            flush=True,
        )
        raise
    print(f"release_manager self-test GREEN: {label}", flush=True)
    return result


def _directory_alias(link: Path, target: Path) -> None:
    if os.name == "nt":
        completed = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30,
        )
        assert completed.returncode == 0, completed.stderr or completed.stdout
    else:
        link.symlink_to(target, target_is_directory=True)


def _remove_directory_alias(link: Path) -> None:
    if os.name == "nt":
        os.rmdir(link)
    else:
        link.unlink()


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
    (shadow / "release_integrity.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n"
        "raise RuntimeError('shadow module executed')\n",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join((str(shadow), str(manager.ROOT)))
    completed = subprocess.run(
        [sys.executable, "-c", "import src.release_manager; print('GREEN')"],
        cwd=manager.ROOT, env=environment, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "GREEN"
    assert not marker.exists(), "package import executed a shadow integrity module"


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


def _self_test_release_privacy(
    manager: ModuleType, base: Path, source: Path
) -> None:
    hidden_codex = ".co" + "dex"
    assert manager._matches(hidden_codex + "/sessions/run.jsonl", [hidden_codex + "/**"])
    assert not manager._matches("codex-skill/SKILL.md", [hidden_codex + "/**"])
    assert not manager._matches("videos-archive/keep.md", ["videos/**"])
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

    # A copied runtime review bundle under a broad managed include must stop
    # the build even though the file type itself looks harmless.  Never echo
    # the bearer URL from a failure message.
    review_probe = base / "review-runtime-artifact-probe"
    shutil.copytree(source, review_probe)
    capability = (
        "https://" + "fixture-review-capability" + ".trycloudflare.com/"
        + "AbCdEfGhIjKlMnOpQrStUvWxYz012345" + "/review.html"
    )
    review_bundle = review_probe / "src" / "_review"
    review_bundle.mkdir()
    manager.atomic_json(
        review_bundle / "remote_session.json",
        {"status": "ACTIVE", "url": capability},
    )
    try:
        manager.build_release(review_probe, base / "review-runtime-artifact-dist")
    except RuntimeError as exc:
        message = str(exc)
        assert "private-runtime-artifact-path" in message
        assert capability not in message
    else:
        raise AssertionError("release manager accepted a runtime review artifact")

    manifest = manager.read_json(review_probe / "release-manifest.json")
    private_patterns = manager._private_release_path_patterns(manifest)
    for relative in (
        "src/_review/review.html",
        "src/_review/review.json",
        "src/_review/manifest.json",
        "src/leaked/remote_delivery.json",
        "src/leaked/remote_daemon.stdout.log",
        "src/leaked/remote_daemon.stderr.log",
        "src/leaked/remote_tunnel.log",
        "src/leaked/" + ".co" + "dex/sessions/2099/fixture.jsonl",
        "src/leaked/codex-remote" + "-attachments/fixture.txt",
        "SRC/_REVIEW/REMOTE_SESSION.JSON",
    ):
        assert manager._is_private_release_path(relative, private_patterns), relative
    for relative in (
        "src/example/manifest.json",
        "src/example/review.html",
        "src/example/review.json",
        "src/example/.codex/editor-support.json",
        "src/example/.claude/editor-support.json",
    ):
        assert not manager._is_private_release_path(relative, private_patterns), relative

    # Content scanning independently rejects a copied capability, its bare
    # bearer path, and a Codex session path even when the filename is ordinary.
    content_probe = base / "review-capability-content-probe"
    shutil.copytree(source, content_probe)
    bearer_path = "/" + "ZyXwVuTsRqPoNmLkJiHgFeDcBa987654" + "/media/0"
    codex_session = ".co" + "dex/sessions/2099/fixture.jsonl"
    remote_attachment = "codex-remote" + "-attachments/fixture.bin"
    fixture_path = content_probe / "examples" / "PLAN_TEMPLATE.md"
    fixture_path.write_text(
        fixture_path.read_text(encoding="utf-8")
        + "\n" + capability + "\n" + bearer_path + "\n" + codex_session
        + "\n" + remote_attachment + "\n",
        encoding="utf-8",
    )
    try:
        manager.build_release(content_probe, base / "review-capability-content-dist")
    except RuntimeError as exc:
        message = str(exc)
        assert "quick-tunnel-url" in message
        assert "review-capability-path" in message
        assert "codex-session-artifact-path" in message
        assert "codex-remote-attachment-path" in message
        assert capability not in message
        assert bearer_path not in message
        assert codex_session not in message
        assert remote_attachment not in message
    else:
        raise AssertionError("release manager accepted review capability residue")

    # In a real checkout, broad include globs are narrowed to Git's tracked
    # inventory. A clean tracked framework file passes; an untracked neighbor
    # fails closed instead of being silently packed.
    tracking_probe = base / "release-tracking-probe"
    tracked_file = tracking_probe / "src" / "framework.py"
    tracked_file.parent.mkdir(parents=True)
    tracked_file.write_text("FRAMEWORK = True\n", encoding="utf-8")
    clean_manifest = tracking_probe / "src" / "example" / "manifest.json"
    clean_manifest.parent.mkdir()
    clean_manifest.write_text('{"schema_version": 1}\n', encoding="utf-8")
    tracking_manifest = {
        "managed_include": ["src/**"],
        "exclude_globs": [],
        "protected_globs": [],
        "privacy": {"deny_path_globs": []},
    }
    original_tracking = manager._git_tracked_release_paths
    manager._git_tracked_release_paths = lambda _root: {
        "src/example/manifest.json",
        "src/framework.py",
    }
    try:
        collected = manager.collect_release_files(tracking_probe, tracking_manifest)
        # The collector resolves its root; hosted temp directories may be aliases.
        assert {
            path.relative_to(tracking_probe.resolve(strict=True)).as_posix() for path in collected
        } == {"src/example/manifest.json", "src/framework.py"}
        (tracking_probe / "src" / "untracked.py").write_text(
            "PRIVATE = True\n", encoding="utf-8"
        )
        try:
            manager.collect_release_files(tracking_probe, tracking_manifest)
        except RuntimeError as exc:
            assert str(exc) == (
                "public privacy gate failed: untracked-release-candidate"
            )
        else:
            raise AssertionError("release manager accepted an untracked candidate")
    finally:
        manager._git_tracked_release_paths = original_tracking


def _self_test_privacy_gate_containment(
    manager: ModuleType, base: Path, source: Path
) -> None:
    probe = base / "privacy-gate-containment-probe"
    shutil.copytree(source, probe)
    marker = base / "outside-gate-executed.txt"
    outside = base / "outside-privacy-gate.py"
    outside.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n"
        "def assert_global_public_text_safe(relative, text):\n    return None\n",
        encoding="utf-8",
    )
    manifest_path = probe / "release-manifest.json"
    manifest = manager.read_json(manifest_path)
    manifest["privacy"]["semantic_gate"] = str(outside.resolve())
    manager.atomic_json(manifest_path, manifest)
    files = manager.collect_release_files(probe, manifest)
    errors = manager.validate_release_tree(probe, manifest, files)
    message = "\n".join(errors)
    assert "public privacy gate path is unsafe or unavailable" in message
    assert str(outside.resolve()) not in message
    assert not marker.exists(), "release validator executed an external privacy gate"


def _self_test_staged_receipt_parity(
    manager: ModuleType, base: Path, source: Path
) -> None:
    content_probe = base / "receipt-content-probe"
    shutil.copytree(source, content_probe)
    managed = content_probe / "src" / "system_health.py"
    managed.write_text(
        managed.read_text(encoding="utf-8") + "\n# receipt parity fixture\n",
        encoding="utf-8",
    )
    try:
        manager.build_release(content_probe, base / "receipt-content-dist")
    except RuntimeError as exc:
        message = str(exc)
        assert "release sync-receipt parity failed" in message
        assert "staged sync receipt payload mismatch: src/system_health.py" in message
    else:
        raise AssertionError("release accepted content that drifted from sync receipt")

    semantics_probe = base / "receipt-semantics-probe"
    shutil.copytree(source, semantics_probe)
    receipt_path = semantics_probe / "sync-receipt.json"
    receipt = manager.read_json(receipt_path)
    receipt["output_hash_semantics"] = "unsupported-fixture"
    manager.atomic_json(receipt_path, receipt)
    try:
        manager.build_release(semantics_probe, base / "receipt-semantics-dist")
    except RuntimeError as exc:
        assert "staged sync receipt hash semantics mismatch" in str(exc)
    else:
        raise AssertionError("release accepted unsupported receipt hash semantics")

    omission_probe = base / "receipt-omission-probe"
    shutil.copytree(source, omission_probe)
    receipt_path = omission_probe / "sync-receipt.json"
    receipt = manager.read_json(receipt_path)
    omitted = "AUTOPILOT_MANIFEST.json"
    receipt["outputs"].pop(omitted)
    receipt["output_count"] = len(receipt["outputs"])
    manager.atomic_json(receipt_path, receipt)
    (omission_probe / omitted).write_text(
        "{}\n", encoding="utf-8"
    )
    try:
        manager.build_release(omission_probe, base / "receipt-omission-dist")
    except RuntimeError as exc:
        assert "staged sync receipt output key set mismatch" in str(exc)
    else:
        raise AssertionError("release accepted omitted receipt coverage and payload drift")

    alias_probe = base / "receipt-alias-probe"
    shutil.copytree(source, alias_probe)
    receipt_path = alias_probe / "sync-receipt.json"
    receipt = manager.read_json(receipt_path)
    original = "AUTOPILOT_MANIFEST.json"
    receipt["outputs"]["./" + original] = receipt["outputs"].pop(original)
    manager.atomic_json(receipt_path, receipt)
    try:
        manager.build_release(alias_probe, base / "receipt-alias-dist")
    except RuntimeError as exc:
        message = str(exc)
        assert "staged sync receipt output key set mismatch" in message
        assert "staged sync receipt contains non-canonical output path" in message
    else:
        raise AssertionError("release accepted a non-canonical receipt path alias")


def _self_test_release_link_containment(
    manager: ModuleType, base: Path, source: Path
) -> None:
    probe = base / "release-link-probe"
    shutil.copytree(source, probe)
    outside = base / "outside-link-target.py"
    outside.write_text("SAFE_FIXTURE = True\n", encoding="utf-8")
    link = probe / "src" / "link-probe.py"
    try:
        link.symlink_to(outside)
    except OSError:
        try:
            manager._assert_contained_release_path(probe, outside, require_file=True)
        except RuntimeError as exc:
            assert "outside root" in str(exc)
        else:
            raise AssertionError("release containment accepted an outside path")
        return
    manifest = manager.read_json(probe / "release-manifest.json")
    try:
        manager.collect_release_files(probe, manifest)
    except RuntimeError as exc:
        message = str(exc)
        assert "link/reparse point" in message
        assert "src/link-probe.py" in message
        assert str(outside) not in message
    else:
        raise AssertionError("release collector followed a managed symlink")


def _self_test_apply_mutation_boundaries(
    manager: ModuleType, base: Path, built: dict, outside: Path, marker: Path
) -> None:
    archive, digest = Path(built["archive"]), built["sha256"]

    state_type_install = base / "state-type-install"
    state_type_path = state_type_install / manager.STATE_DIR / "install-state.json"
    state_type_path.mkdir(parents=True)
    state_type_readme = state_type_install / "README.md"
    state_type_readme.write_text("legacy unchanged\n", encoding="utf-8")
    try:
        manager.apply_release_archive(archive, state_type_install, digest, auto=False)
    except RuntimeError as exc:
        assert "not a regular file" in str(exc)
        assert str(outside) not in str(exc)
    else:
        raise AssertionError("updater treated an install-state directory as absent")
    assert state_type_readme.read_text(encoding="utf-8") == "legacy unchanged\n"
    assert not (state_type_install / manager.STATE_DIR / "backups").exists()

    install = base / "junction-install"
    install.mkdir()
    alias = install / "src"
    _directory_alias(alias, outside)
    try:
        try:
            manager.apply_release_archive(archive, install, digest, auto=False)
        except RuntimeError as exc:
            message = str(exc)
            assert "link/reparse point" in message and "src/" in message
            assert str(outside) not in message
        else:
            raise AssertionError("updater wrote through a managed directory alias")
        assert sorted(path.name for path in outside.iterdir()) == ["marker.txt"]
        assert not (install / manager.STATE_DIR).exists()
    finally:
        _remove_directory_alias(alias)

    state_install = base / "state-traversal-install"
    first = manager.apply_release_archive(archive, state_install, digest, auto=False)
    state_path = state_install / manager.STATE_DIR / "install-state.json"
    state = manager.read_json(state_path)
    state["managed_files"].append("../../outside-state.txt")
    state["managed_hashes"]["../../outside-state.txt"] = "0" * 64
    manager.atomic_json(state_path, state)
    (state_install / "README.md").write_text("repair fixture\n", encoding="utf-8")
    backups = state_install / manager.STATE_DIR / "backups"
    before_backups = sorted(path.name for path in backups.iterdir())
    try:
        manager.apply_release_archive(archive, state_install, digest, auto=False)
    except RuntimeError as exc:
        assert "persisted path inventory is invalid" in str(exc)
        assert "outside-state" not in str(exc)
    else:
        raise AssertionError("updater trusted a traversal path from install state")
    assert marker.read_text(encoding="utf-8") == "unchanged"
    assert sorted(path.name for path in backups.iterdir()) == before_backups

    pending_install = base / "pending-transaction-install"
    manager.apply_release_archive(archive, pending_install, digest, auto=False)
    pending_readme = pending_install / "README.md"
    pending_readme.write_text("pending rollback fixture\n", encoding="utf-8")
    pending_backups = pending_install / manager.STATE_DIR / "backups"
    before_pending = {path.name for path in pending_backups.iterdir()}
    original_replace = manager.os.replace

    def interrupt_after_readme_replace(source, destination):
        original_replace(source, destination)
        if (
            Path(destination).resolve() == pending_readme.resolve()
            and str(source).endswith(".update-tmp")
        ):
            raise KeyboardInterrupt("simulated process interruption")

    manager.os.replace = interrupt_after_readme_replace
    try:
        try:
            manager.apply_release_archive(archive, pending_install, digest, auto=False)
        except KeyboardInterrupt:
            pass
        else:
            raise AssertionError("interruption fixture did not stop the update")
    finally:
        manager.os.replace = original_replace
    pending_ids = {path.name for path in pending_backups.iterdir()} - before_pending
    assert len(pending_ids) == 1
    pending_id = pending_ids.pop()
    pending_record = manager.read_json(
        pending_backups / pending_id / "transaction.json"
    )
    assert pending_record["status"] == "PENDING"
    assert "README.md" in pending_record["replaced"], pending_record
    assert manager.rollback(pending_install, pending_id)["status"] == "ROLLED_BACK"
    assert pending_readme.read_text(encoding="utf-8") == "pending rollback fixture\n"
    assert first["status"] == "UPDATED"


def _self_test_rollback_mutation_boundaries(
    manager: ModuleType, base: Path, built: dict, outside: Path, marker: Path
) -> None:
    archive, digest = Path(built["archive"]), built["sha256"]
    rollback_install = base / "rollback-traversal-install"
    applied = manager.apply_release_archive(
        archive, rollback_install, digest, auto=False
    )
    transaction = applied["transaction"]
    record_path = (
        rollback_install / manager.STATE_DIR / "backups" / transaction
        / "transaction.json"
    )
    record = manager.read_json(record_path)
    record["created"].append("../../outside-rollback.txt")
    manager.atomic_json(record_path, record)
    installed_readme = (rollback_install / "README.md").read_bytes()
    try:
        manager.rollback(rollback_install, transaction)
    except RuntimeError as exc:
        assert "persisted path inventory is invalid" in str(exc)
        assert "outside-rollback" not in str(exc)
    else:
        raise AssertionError("rollback trusted a traversal path from transaction state")
    assert (rollback_install / "README.md").read_bytes() == installed_readme
    assert marker.read_text(encoding="utf-8") == "unchanged"

    rollback_alias_install = base / "rollback-junction-install"
    rollback_alias_result = manager.apply_release_archive(
        archive, rollback_alias_install, digest, auto=False
    )
    rollback_alias = rollback_alias_install / "src"
    shutil.rmtree(rollback_alias)
    _directory_alias(rollback_alias, outside)
    alias_readme = (rollback_alias_install / "README.md").read_bytes()
    try:
        try:
            manager.rollback(
                rollback_alias_install, rollback_alias_result["transaction"]
            )
        except RuntimeError as exc:
            message = str(exc)
            assert "link/reparse point" in message and "src/" in message
            assert str(outside) not in message
        else:
            raise AssertionError("rollback mutated through a managed directory alias")
        assert (rollback_alias_install / "README.md").read_bytes() == alias_readme
        assert sorted(path.name for path in outside.iterdir()) == ["marker.txt"]
    finally:
        _remove_directory_alias(rollback_alias)

    rollback_state_install = base / "rollback-state-install"
    rollback_state_result = manager.apply_release_archive(
        archive, rollback_state_install, digest, auto=False
    )
    rollback_state_path = (
        rollback_state_install / manager.STATE_DIR / "install-state.json"
    )
    manager.atomic_json(rollback_state_path, {})
    rollback_state_readme = (rollback_state_install / "README.md").read_bytes()
    try:
        manager.rollback(rollback_state_install, rollback_state_result["transaction"])
    except RuntimeError as exc:
        assert "managed inventory is missing" in str(exc)
    else:
        raise AssertionError("rollback mutated before validating current install state")
    assert (rollback_state_install / "README.md").read_bytes() == rollback_state_readme
    rollback_state_path.unlink()
    rollback_state_path.mkdir()
    try:
        manager.rollback(rollback_state_install, rollback_state_result["transaction"])
    except RuntimeError as exc:
        assert "not a regular file" in str(exc)
    else:
        raise AssertionError("rollback treated a current-state directory as absent")
    assert (rollback_state_install / "README.md").read_bytes() == rollback_state_readme
    rollback_state_path.rmdir()
    try:
        manager.rollback(rollback_state_install, rollback_state_result["transaction"])
    except RuntimeError as exc:
        assert "current-state presence is inconsistent" in str(exc)
    else:
        raise AssertionError("rollback accepted a missing committed install state")
    assert (rollback_state_install / "README.md").read_bytes() == rollback_state_readme

    rollback_payload_install = base / "rollback-payload-install"
    manager.apply_release_archive(archive, rollback_payload_install, digest, auto=False)
    rollback_payload_readme = rollback_payload_install / "README.md"
    rollback_payload_readme.write_text("same-version repair fixture\n", encoding="utf-8")
    repair = manager.apply_release_archive(
        archive, rollback_payload_install, digest, auto=False
    )
    repair_backup = (
        rollback_payload_install / manager.STATE_DIR / "backups" / repair["transaction"]
    )
    missing_backup = repair_backup / "files" / "README.md"
    missing_payload = missing_backup.read_bytes()
    missing_backup.unlink()
    repaired_readme = rollback_payload_readme.read_bytes()
    try:
        manager.rollback(rollback_payload_install, repair["transaction"])
    except RuntimeError as exc:
        assert "managed mutation file is missing" in str(exc)
    else:
        raise AssertionError("rollback mutated before validating every backup source")
    assert rollback_payload_readme.read_bytes() == repaired_readme
    missing_backup.write_bytes(missing_payload)

    previous_state_path = repair_backup / "previous-install-state.json"
    previous_state_path.unlink()
    previous_state_path.mkdir()
    try:
        manager.rollback(rollback_payload_install, repair["transaction"])
    except RuntimeError as exc:
        assert "not a regular file" in str(exc)
    else:
        raise AssertionError("rollback treated a previous-state directory as absent")
    assert rollback_payload_readme.read_bytes() == repaired_readme
    previous_state_path.rmdir()
    try:
        manager.rollback(rollback_payload_install, repair["transaction"])
    except RuntimeError as exc:
        assert "previous-state presence is inconsistent" in str(exc)
    else:
        raise AssertionError("rollback accepted a missing declared previous state")
    assert rollback_payload_readme.read_bytes() == repaired_readme
    manager.atomic_json(previous_state_path, {})
    try:
        manager.rollback(rollback_payload_install, repair["transaction"])
    except RuntimeError as exc:
        assert "managed inventory is missing" in str(exc)
    else:
        raise AssertionError("rollback mutated before validating previous install state")
    assert rollback_payload_readme.read_bytes() == repaired_readme


def _self_test_skill_mutation_boundaries(
    manager: ModuleType, base: Path, outside: Path, marker: Path
) -> None:
    skill = base / "junction-skill"
    skill.mkdir()
    skill_alias = skill / "references"
    _directory_alias(skill_alias, outside)
    try:
        try:
            manager.sync_codex_skill(manager.ROOT, skill, adopt=True)
        except RuntimeError as exc:
            message = str(exc)
            assert "link/reparse point" in message and "references/" in message
            assert str(outside) not in message
        else:
            raise AssertionError("Skill sync wrote through a managed directory alias")
        assert sorted(path.name for path in outside.iterdir()) == ["marker.txt"]
        assert not (skill / ".video-autopilot-skill.json").exists()
    finally:
        _remove_directory_alias(skill_alias)

    marker_type_skill = base / "marker-type-skill"
    marker_type_skill.mkdir()
    marker_type = marker_type_skill / ".video-autopilot-skill.json"
    marker_type.mkdir()
    marker_keep = marker_type_skill / "keep.txt"
    marker_keep.write_text("unchanged", encoding="utf-8")
    try:
        manager.sync_codex_skill(manager.ROOT, marker_type_skill, adopt=True)
    except RuntimeError as exc:
        assert "not a regular file" in str(exc)
    else:
        raise AssertionError("Skill sync treated a marker directory as absent")
    assert marker_keep.read_text(encoding="utf-8") == "unchanged"

    marker_skill = base / "marker-traversal-skill"
    assert manager.sync_codex_skill(manager.ROOT, marker_skill, adopt=True)[
        "status"
    ] == "SYNCED"
    skill_state_path = marker_skill / ".video-autopilot-skill.json"
    skill_state = manager.read_json(skill_state_path)
    manager.atomic_json(skill_state_path, {})
    try:
        manager.sync_codex_skill(manager.ROOT, marker_skill, adopt=True)
    except RuntimeError as exc:
        assert "managed inventory is missing" in str(exc)
    else:
        raise AssertionError("Skill sync accepted a truncated marker")
    manager.atomic_json(skill_state_path, skill_state)
    skill_state["managed_files"].append("../../outside-skill.txt")
    skill_state["managed_hashes"]["../../outside-skill.txt"] = "0" * 64
    manager.atomic_json(skill_state_path, skill_state)
    try:
        manager.sync_codex_skill(manager.ROOT, marker_skill, adopt=True)
    except RuntimeError as exc:
        assert "persisted path inventory is invalid" in str(exc)
        assert "outside-skill" not in str(exc)
    else:
        raise AssertionError("Skill sync trusted a traversal path from its marker")
    assert marker.read_text(encoding="utf-8") == "unchanged"


def _self_test_mutation_boundaries(
    manager: ModuleType, base: Path, built: dict
) -> None:
    outside = base / "mutation-boundary-outside"
    outside.mkdir()
    marker = outside / "marker.txt"
    marker.write_text("unchanged", encoding="utf-8")
    _self_test_apply_mutation_boundaries(manager, base, built, outside, marker)
    _self_test_rollback_mutation_boundaries(manager, base, built, outside, marker)
    _self_test_skill_mutation_boundaries(manager, base, outside, marker)


def _run_bootstrap(bootstrap_path: Path, channel: str, install: Path, command: str, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(bootstrap_path), "--channel", channel,
         "--install-root", str(install), command],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=kwargs.pop("timeout", 120), **kwargs,
    )


def _self_test_nested_bootstrap(bootstrap: ModuleType, manager: ModuleType, base: Path, built: dict) -> None:
    outer_workspace = base / "nested-bootstrap-outer"
    outer_workspace.mkdir()
    outer_manifest = outer_workspace / "AUTOPILOT_MANIFEST.json"
    outer_manifest.write_text("{}\n", encoding="utf-8")
    outer_manifest_bytes = outer_manifest.read_bytes()
    nested_install = outer_workspace / ".rd" / "nested-install"
    installed = manager.apply_release_archive(Path(built["archive"]), nested_install, built["sha256"], auto=False)
    assert installed["status"] == "UPDATED"
    package = nested_install / "videos" / "_PUBLISH_HUB" / "READY" / "shorts" / "review" / "S001_fixture"
    package.mkdir(parents=True)
    video = package / "S001_fixture.mp4"
    video.write_bytes(b"fixture-video")
    (package / "發布文案_可複製.md").write_text("fixture\n", encoding="utf-8")
    manager.atomic_json(package / "publish.json", {"schema_version": 2, "artifact_revision": 1, "content_id": "S001", "format": "shorts", "status": "review", "video": video.name, "sha256": "0" * 64, "bytes": 13, "hub_path": package.relative_to(nested_install).as_posix()})
    module_names = ("publish_hub", "publish_hub_layout", "workspace_migrator")
    saved_modules = {name: sys.modules.pop(name, None) for name in module_names}
    previous_root = os.environ.get("VIDEO_AUTOPILOT_ROOT")
    source_root = str(nested_install / "src")
    sys.path.insert(0, source_root)
    outer_entries = sorted(path.name for path in outer_workspace.iterdir() if path.name != ".rd")
    try:
        os.environ["VIDEO_AUTOPILOT_ROOT"] = str(outer_workspace)
        __import__("publish_hub_layout")
        result = bootstrap._migrate_workspace(nested_install)
    finally:
        if previous_root is None:
            os.environ.pop("VIDEO_AUTOPILOT_ROOT", None)
        else:
            os.environ["VIDEO_AUTOPILOT_ROOT"] = previous_root
        sys.path.remove(source_root)
        for name, module in saved_modules.items():
            sys.modules.pop(name, None)
            if module is not None:
                sys.modules[name] = module
    assert result["status"] == "ATTENTION"
    assert any(row.get("error") == "sha256 mismatch" for row in result["remaining_failures"])
    migrated_root = Path(result["workspace"]).resolve()
    assert migrated_root == nested_install.resolve()
    assert (nested_install / "videos" / "_PUBLISH_HUB" / "START_HERE.md").is_file()
    assert (nested_install / "00_發布中樞_從這裡開始.md").is_file()
    assert outer_manifest.read_bytes() == outer_manifest_bytes
    assert outer_entries == sorted(path.name for path in outer_workspace.iterdir() if path.name != ".rd")


def _self_test_fresh_bootstrap(
    manager: ModuleType, base: Path, source: Path, built: dict
) -> None:
    bootstrap_path = source / "install_or_upgrade.py"
    spec = importlib.util.spec_from_file_location(
        "_video_autopilot_bootstrap_selftest", bootstrap_path
    )
    assert spec is not None and spec.loader is not None
    bootstrap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bootstrap)
    with zipfile.ZipFile(Path(built["archive"])) as package:
        runtime_root = base / "bootstrap-runtime"
        manager_path = bootstrap._extract_bootstrap_runtime(package, runtime_root)
    assert manager_path.is_file()
    assert manager_path.with_name("release_integrity.py").is_file()
    incomplete = base / "bootstrap-incomplete.zip"
    with zipfile.ZipFile(incomplete, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("src/release_manager.py", manager_path.read_bytes())
    with zipfile.ZipFile(incomplete) as package:
        try:
            bootstrap._extract_bootstrap_runtime(package, base / "bootstrap-negative")
        except RuntimeError as exc:
            assert str(exc) == "release bootstrap runtime is incomplete"
        else:
            raise AssertionError("bootstrap accepted an incomplete updater runtime")
    junction_install = base / "bootstrap-junction-install"
    junction_outside = base / "bootstrap-junction-outside"
    junction_install.mkdir()
    junction_outside.mkdir()
    shutil.copy2(manager_path, junction_outside / "release_manager.py")
    shutil.copy2(
        manager_path.with_name("release_integrity.py"),
        junction_outside / "release_integrity.py",
    )
    runtime_alias = junction_install / "src"
    _directory_alias(runtime_alias, junction_outside)
    try:
        assert not bootstrap._local_runtime_complete(junction_install)
    finally:
        _remove_directory_alias(runtime_alias)

    install = base / "fresh-bootstrap-install"
    completed = _run_bootstrap(bootstrap_path, built["channel"], install, "--apply")
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "UPDATED"
    installed_integrity = install / "src" / "release_integrity.py"
    assert installed_integrity.is_file()
    assert manager.detect_current_version(install) == built["version"]
    installed_integrity.unlink()
    check = _run_bootstrap(bootstrap_path, built["channel"], install, "--check", timeout=60)
    assert check.returncode == 0, check.stderr
    check_result = json.loads(check.stdout)
    assert check_result["status"] == "BOOTSTRAP_AVAILABLE"
    assert check_result["repair"] is True
    assert str(install) not in check.stderr
    repair = _run_bootstrap(bootstrap_path, built["channel"], install, "--apply")
    assert repair.returncode == 0, repair.stderr
    assert json.loads(repair.stdout)["status"] == "UPDATED"
    assert installed_integrity.is_file()

    readme = install / "README.md"
    expected_readme = readme.read_bytes()
    readme.write_text("same-version drift fixture\n", encoding="utf-8")
    check = _run_bootstrap(bootstrap_path, built["channel"], install, "--check", timeout=60)
    assert check.returncode == 0, check.stderr
    check_result = json.loads(check.stdout)
    assert check_result["status"] == "REPAIR_AVAILABLE"
    assert "README.md" in check_result["modified"]

    automatic = _run_bootstrap(bootstrap_path, built["channel"], install, "--auto")
    assert automatic.returncode == 0, automatic.stderr
    automatic_result = json.loads(automatic.stdout)
    assert automatic_result["status"] == "CONFIRM_REQUIRED"
    assert "README.md" in automatic_result["modified"]
    assert readme.read_text(encoding="utf-8") == "same-version drift fixture\n"

    explicit = _run_bootstrap(bootstrap_path, built["channel"], install, "--apply")
    assert explicit.returncode == 0, explicit.stderr
    assert json.loads(explicit.stdout)["status"] == "UPDATED"
    assert readme.read_bytes() == expected_readme
    _self_test_nested_bootstrap(bootstrap, manager, base, built)


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
            lambda: shutil.copytree(
                manager.ROOT,
                source,
                ignore=shutil.ignore_patterns(
                    ".git", "dist", "__pycache__", "*.pyc"
                ),
            ),
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
        )
        for label, action in stages:
            _run_stage(label, action)
    print("release_manager self-test GREEN")
