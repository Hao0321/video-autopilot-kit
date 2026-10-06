#!/usr/bin/env python3
"""Deterministic fixtures for ``canonical_backport.py`` (needs only git).

The module under test is injected by ``run_self_test`` so the static import
graph stays acyclic, mirroring ``src/release_manager_selftest.py``.
"""
from __future__ import annotations

import importlib
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

backport = None  # injected by run_self_test

BOM = b"\xef\xbb\xbf"
SKILL = "codex-skill/video-autopilot/"
GIT = ("git", "-c", "user.name=fixture", "-c", "user.email=fixture",
       "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false")
BASE_FILES = {
    "src/aesthetic_score.py": "alpha\nbeta\ngamma\ndelta\nepsilon\n",
    SKILL + "references/craft-index.md": "x\n",
    "knowledge/runtime/filter_library.json": '{"v": 1}\n',
    "src/workflow_json.py": "w = 1\n",
    SKILL + "workflow_json.py": "w = 1\n",
    "src/workflow_state.py": "s = 1\n",
    SKILL + "workflow_state.py": "s = 1\n",
    "src/visual_master.py": "k = 1\n",
    "README.md": "readme\n",
    "knowledge/runtime/state.json": "{}\n",
    SKILL + "references/knowledge-lifecycle.md": "old\n",
    SKILL + "SKILL.md": "skill\n",
    "tools/code-cleanup-helper/SKILL.md": "cleanup\n",
    SKILL + "references/quality-95-system.md": "private wording approves\nkeep\n",
    SKILL + "references/filter-library.md": "metric 12K MARKER\n",
    "scripts/sync_canonical.py": "def _transform(text, name):\n    return text\n",
    "scripts/public_privacy_sanitizer.py": "def sanitize_public_text(relative, text):\n    return text\n",
}
HEAD_CHANGES = {
    "src/aesthetic_score.py": "alpha\nbeta\ngamma\nDELTA\nepsilon\n",
    SKILL + "references/craft-index.md": "y\n",
    "knowledge/runtime/filter_library.json": '{"v": 2}\n',
    "src/workflow_json.py": "w = 2\n",
    SKILL + "workflow_json.py": "w = 2\n",
    "src/workflow_state.py": "s = 2\n",
    SKILL + "workflow_state.py": "s = 3\n",
    "src/visual_master.py": "k = 2\n",
    "README.md": "readme 2\n",
    "knowledge/runtime/state.json": '{"records": []}\n',
    SKILL + "references/knowledge-lifecycle.md": None,
    SKILL + "references/token-budget-system.md": "new\n",
    SKILL + "SKILL.md": "skill 2\n",
    "tools/code-cleanup-helper/SKILL.md": "cleanup 2\n",
    # A new public-only rewrite rule plus one real edit in the same file.
    "scripts/sync_canonical.py": ("def _transform(text, name):\n"
                                  "    return (text.replace('private wording', 'public wording')\n"
                                  "            .replace('metric 3.2M', 'metric 12K'))\n"),
    # A sanitizer-only change: the canonical already projects to the new head.
    SKILL + "references/filter-library.md": "metric 12K\n",
    SKILL + "references/quality-95-system.md": "public wording approves\nkeep\nnew line\n",
}
CANONICAL = {
    "SKILL.md": b"---\nname: video-autopilot\n---\nprivate body\n",
    "workflow_contract.json": b"{}\n",
    "aesthetic_score.py": BOM + b"PRIVATE\r\nalpha\r\nbeta\r\ngamma\r\ndelta\r\nepsilon\r\n",
    "references/craft-index.md": b"x\n",
    "knowledge/filter_library.json": b'{"v": 2}\n',
    "workflow_json.py": b"w = 1\r\n",
    "workflow_state.py": b"s = 1\n",
    "visual_master.py": b"k = 3\n",
    "references/knowledge-lifecycle.md": b"old\r\n",
    "references/quality-95-system.md": b"private wording approves\r\nkeep\r\n",
    "references/filter-library.md": b"metric 3.2M\r\n",
}
EXPECTED = {
    "aesthetic_score.py": "MERGED", "references/craft-index.md": "FAST_FORWARD",
    "knowledge/filter_library.json": "ALREADY_APPLIED", "workflow_json.py": "FAST_FORWARD",
    "workflow_state.py": "ERROR", "visual_master.py": "CONFLICT",
    "references/knowledge-lifecycle.md": "DELETE", "references/token-budget-system.md": "CREATE",
    "references/quality-95-system.md": "MERGED",
    "references/filter-library.md": "ALREADY_APPLIED",
}


def _write_tree(root: Path, files: dict) -> None:
    for relative, payload in files.items():
        path = root / relative
        if payload is None:
            if path.exists():
                path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload if isinstance(payload, bytes) else payload.encode("utf-8"))


def _commit(repository: Path, message: str) -> str:
    subprocess.run([*GIT, "add", "-A"], cwd=str(repository), check=True, capture_output=True)
    subprocess.run([*GIT, "commit", "-q", "-m", message], cwd=str(repository), check=True, capture_output=True)
    return subprocess.run([*GIT, "rev-parse", "HEAD"], cwd=str(repository), check=True,
                          capture_output=True).stdout.decode("ascii").strip()


def _snapshot(root: Path) -> dict:
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted(root.rglob("*")) if path.is_file()}


def _fixture(temp: Path) -> tuple:
    repository, canonical = temp / "public", temp / "canonical"
    repository.mkdir()
    subprocess.run([*GIT, "init", "-q"], cwd=str(repository), check=True, capture_output=True)
    _write_tree(repository, BASE_FILES)
    base = _commit(repository, "base")
    _write_tree(repository, HEAD_CHANGES)
    head = _commit(repository, "head")
    _write_tree(canonical, CANONICAL)
    return repository, canonical, base, head


def _check_classification() -> None:
    assert backport.classify("src/system_health.py").kind == "public-owned"
    assert backport.classify(SKILL + "SKILL.md").kind == "generated"
    assert backport.classify("knowledge/runtime/state.json").kind == "projection"
    assert backport.classify("docs/OPEN_SOURCE_SUITE.md").kind == "repo-native"
    longform = backport.classify("src/longform_maker/shorts_gate.py")
    assert (longform.kind, longform.relative) == ("derived", "longform_maker/shorts_gate.py")
    cleanup = backport.classify("tools/code-cleanup-helper/scripts/audit.py")
    assert (cleanup.root, cleanup.relative) == ("cleanup", "scripts/audit.py")
    assert backport.public_paths_for("canonical", "workflow_json.py") == [
        "src/workflow_json.py", SKILL + "workflow_json.py"]


def _check_plan(repository: Path, canonical: Path, base: str, head: str) -> None:
    items = backport.plan(repository, base, head, {"canonical": canonical})
    derived = {item.target.relative: item.status for item in items if item.target.kind == "derived"}
    cleanup = [item for item in items if item.target.root == "cleanup"]
    assert {key: derived[key] for key in EXPECTED} == EXPECTED, derived
    assert cleanup and cleanup[0].status == "SKIPPED" and "--cleanup-helper" in cleanup[0].detail
    skipped = {item.sources[0]: item.target.kind for item in items if item.status == "SKIPPED"}
    assert skipped["README.md"] == "repo-native" and skipped[SKILL + "SKILL.md"] == "generated"
    assert skipped["knowledge/runtime/state.json"] == "projection"


def _check_apply(repository: Path, canonical: Path, base: str, temp: Path) -> None:
    items = backport.plan(repository, base, "HEAD", {"canonical": canonical})
    before = _snapshot(canonical)
    try:
        backport.apply(items, {"canonical": canonical}, temp / "refused", partial=False)
    except RuntimeError as exc:
        assert "--partial" in str(exc)
    else:
        raise AssertionError("conflicting backport applied without --partial")
    assert _snapshot(canonical) == before
    backup = temp / "backup"
    backport.apply(items, {"canonical": canonical}, backup, partial=True)
    after = _snapshot(canonical)
    assert after["aesthetic_score.py"] == BOM + b"PRIVATE\r\nalpha\r\nbeta\r\ngamma\r\nDELTA\r\nepsilon\r\n"
    assert after["references/craft-index.md"] == b"y\n" and after["workflow_json.py"] == b"w = 2\r\n"
    assert after["references/token-budget-system.md"] == b"new\n"
    assert after["references/filter-library.md"] == b"metric 3.2M\r\n", "sanitizer-only change leaked"
    assert after["references/quality-95-system.md"] == b"private wording approves\r\nkeep\r\nnew line\r\n", \
        "a public-only rewrite rule must not be written back into the canonical"
    assert "references/knowledge-lifecycle.md" not in after
    assert after["visual_master.py"] == b"k = 3\n" and after["workflow_state.py"] == b"s = 1\n"
    assert (backup / "canonical/references/knowledge-lifecycle.md").read_bytes() == b"old\r\n"
    assert b"<<<<<<<" in (backup / "conflicts/canonical/visual_master.py.conflict").read_bytes()
    replay = backport.plan(repository, base, "HEAD", {"canonical": canonical})
    statuses = {item.target.relative: item.status for item in replay if item.target.kind == "derived"}
    assert statuses["aesthetic_score.py"] == statuses["references/token-budget-system.md"] == "ALREADY_APPLIED"
    assert statuses["references/knowledge-lifecycle.md"] == "ALREADY_APPLIED"


def _check_rollback(repository: Path, temp: Path, base: str, head: str) -> None:
    canonical = temp / "rollback"
    _write_tree(canonical, CANONICAL)
    before = _snapshot(canonical)
    items = backport.plan(repository, base, head, {"canonical": canonical})
    real_write, calls = backport._atomic_write, []

    def failing_write(path, payload):
        calls.append(path)
        if len(calls) == 3:
            raise OSError("injected write failure")
        real_write(path, payload)

    with patch.object(backport, "_atomic_write", failing_write):
        try:
            backport.apply(items, {"canonical": canonical}, temp / "rollback-backup", partial=True)
        except OSError:
            pass
        else:
            raise AssertionError("injected failure did not abort the backport")
    assert _snapshot(canonical) == before, "failed backport was not rolled back"


def _check_cli(repository: Path, canonical: Path, base: str, temp: Path) -> None:
    report = temp / "plan.json"
    assert backport.main(["--canonical", str(canonical), "--base", base,
                          "--repository", str(repository), "--report", str(report)]) == 1
    assert '"CONFLICT"' in report.read_text(encoding="utf-8")
    inside = repository / "codex-skill"
    _write_tree(inside, {"SKILL.md": b"x\n", "workflow_contract.json": b"{}\n"})
    assert backport.main(["--canonical", str(inside), "--base", base, "--repository", str(repository)]) == 2
    assert backport.main(["--canonical", str(canonical), "--base", "0" * 40,
                          "--repository", str(repository)]) == 2


def run_self_test(module) -> None:
    global backport
    backport = module
    _check_classification()
    with tempfile.TemporaryDirectory(prefix="canonical-backport-test-") as raw:
        temp = Path(raw)
        repository, canonical, base, head = _fixture(temp)
        _check_plan(repository, canonical, base, head)
        _check_rollback(repository, temp, base, head)
        _check_cli(repository, canonical, base, temp)
        _check_apply(repository, canonical, base, temp)
    print("canonical_backport self-test GREEN")


if __name__ == "__main__":
    run_self_test(importlib.import_module("canonical_backport"))
