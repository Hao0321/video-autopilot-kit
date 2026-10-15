"""Release privacy selftest; canonical implementation."""
from __future__ import annotations
import json

import shutil
from pathlib import Path
from types import ModuleType


def _self_test_tracked_release_scope(base, manager):
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


def _self_test_review_capability_content(base, capability, manager, source):
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


def _self_test_review_artifact_exclusion(base, manager, source):
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
    return capability


def _self_test_license_and_name_privacy(base, manager, source):
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


def _self_test_release_privacy(
    manager: ModuleType, base: Path, source: Path
) -> None:
    _self_test_catalog_data_contract(manager, base, source)
    hidden_codex = ".co" + "dex"
    assert manager._matches(hidden_codex + "/sessions/run.jsonl", [hidden_codex + "/**"])
    assert not manager._matches("codex-skill/SKILL.md", [hidden_codex + "/**"])
    assert not manager._matches("videos-archive/keep.md", ["videos/**"])
    _self_test_license_and_name_privacy(base, manager, source)

    # A copied runtime review bundle under a broad managed include must stop
    # the build even though the file type itself looks harmless.  Never echo
    # the bearer URL from a failure message.
    capability = _self_test_review_artifact_exclusion(base, manager, source)

    # Content scanning independently rejects a copied capability, its bare
    # bearer path, and a Codex session path even when the filename is ordinary.
    _self_test_review_capability_content(base, capability, manager, source)

    # In a real checkout, broad include globs are narrowed to Git's tracked
    # inventory. A clean tracked framework file passes; an untracked neighbor
    # fails closed instead of being silently packed.
    _self_test_tracked_release_scope(base, manager)


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


def _self_test_catalog_data_contract(manager, base, source):
    """Detached loads use sibling JSON, rejecting missing and duplicate keys."""
    probe = base / "catalog-contract-probe"
    scripts = probe / "scripts"
    scripts.mkdir(parents=True)
    for name in ("public_sync_inventory.py", "public_sync_catalog.json"):
        shutil.copy2(source / "scripts" / name, scripts / name)
    expected = manager._load_sync_inventory_contract(source)["expected_outputs"]
    assert manager._load_sync_inventory_contract(probe)["expected_outputs"] == expected
    catalog = scripts / "public_sync_catalog.json"
    original = catalog.read_text(encoding="utf-8")
    data = json.loads(original)
    missing = dict(data)
    missing.pop("ROOT_MODULES")
    cases = [json.dumps(missing), '{"ROOT_MODULES": [],' + original.lstrip()[1:]]
    for candidate in cases:
        catalog.write_text(candidate, encoding="utf-8")
        try:
            manager._load_sync_inventory_contract(probe)
        except RuntimeError as exc:
            assert str(exc) == "release sync inventory contract is unavailable: ValueError"
            assert str(probe) not in str(exc)
        else:
            raise AssertionError("malformed sibling catalog accepted")
    catalog.write_text(original, encoding="utf-8")
    assert manager._load_sync_inventory_contract(probe)["expected_outputs"] == expected
