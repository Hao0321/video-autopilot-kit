"""Release bootstrap selftest; canonical implementation."""
from __future__ import annotations

if __package__:
    from .release_test_support import _directory_alias, _remove_directory_alias
else:
    from release_test_support import _directory_alias, _remove_directory_alias
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from types import ModuleType


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


def _self_test_bootstrap_runtime_boundaries(base, built, source):
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
    assert manager_path.with_name("release_archive.py").is_file()
    assert manager_path.with_name("release_integrity.py").is_file()
    assert manager_path.with_name("release_install.py").is_file()
    assert callable(bootstrap._load_manager(manager_path).apply_release_archive)
    # The original public bootstrap extracted only these three core members.
    # Its already-verified archive must supply the new installation component.
    manager_path.with_name("release_install.py").unlink()
    bridge = bootstrap._load_manager(manager_path)
    legacy_target = base / "three-member-bootstrap-install"
    legacy_result = bridge.apply_release_archive(
        Path(built["archive"]), legacy_target, built["sha256"], auto=False)
    assert legacy_result["status"] == "UPDATED"
    assert bridge.detect_current_version(legacy_target) == built["version"]

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
    return bootstrap, bootstrap_path


def _self_test_fresh_bootstrap(
    manager: ModuleType, base: Path, source: Path, built: dict
) -> None:
    bootstrap, bootstrap_path = _self_test_bootstrap_runtime_boundaries(base, built, source)

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
