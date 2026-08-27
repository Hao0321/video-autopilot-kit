# -*- coding: utf-8 -*-
"""One-command health check for a clean public Video Autopilot install."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
PYTHON = sys.executable

# label, relative script, argv, slow
TESTS = (
    ("platform", "src/platform_compat.py", (), False),
    ("sync-receipt", "scripts/sync_canonical.py", ("--verify-receipt", "--repository", "."), False),
    ("health-manifest", "src/system_health.py", ("--selftest",), False),
    ("paths", "src/project_paths.py", (), False),
    ("context-router", "src/context_router.py", ("selftest",), False),
    ("workflow-contract", "src/workflow_contract.py", ("selftest",), False),
    ("bundled-workflow-contract", "codex-skill/video-autopilot/workflow_contract.py", ("selftest",), False),
    ("design-system-v6", "src/design_system_v6.py", ("selftest",), False),
    ("template-compiler", "src/template_compiler.py", ("selftest",), False),
    ("mediastorm-craft", "src/mediastorm_craft.py", ("selftest",), False),
    ("mrbeast-editing", "src/mrbeast_editing_system.py", ("selftest",), False),
    ("mrbeast-source-map", "src/mrbeast_source_map.py", ("selftest",), False),
    ("three-d-system", "src/three_d_system.py", ("selftest",), False),
    ("asset-workshop", "src/asset_workshop.py", ("selftest",), False),
    ("vfx-keyer", "src/vfx_keyer.py", ("selftest",), False),
    ("asset-registry", "src/asset_registry.py", ("selftest",), False),
    ("knowledge", "src/knowledge_lifecycle.py", ("selftest",), False),
    ("editorial", "src/editorial_templates.py", (), False),
    ("motion", "src/motion_asset_pack.py", (), False),
    ("visual-director", "src/visual_director.py", (), False),
    ("visual-master", "src/visual_master.py", ("selftest",), False),
    ("color", "src/color_calibration_lab.py", ("selftest",), False),
    ("aesthetic", "src/aesthetic_score.py", ("selftest",), False),
    ("thumbnail", "src/thumbnail_algorithm_score.py", ("selftest",), False),
    ("quality-corpus", "src/quality_corpus.py", ("selftest",), False),
    ("quality-95", "src/quality_95.py", ("selftest",), False),
    ("review-loop", "src/review_loop.py", ("selftest",), False),
    ("tracking", "src/tracked_graphics.py", ("selftest",), False),
    ("outcomes", "src/outcome_learning.py", ("selftest",), False),
    ("publishing-copy", "src/publishing_copy.py", ("selftest",), False),
    ("publish-contract", "src/publish_contract.py", (), False),
    ("publish-hub", "src/publish_hub.py", ("selftest",), False),
    ("workspace-migrator", "src/workspace_migrator.py", ("selftest",), False),
    ("longform-delivery", "src/longform_maker/delivery.py", (), False),
    ("shorts", "src/shorts_autopilot.py", ("selftest",), False),
    ("interview", "src/interview_autopilot.py", ("--selftest",), False),
    ("storage", "src/storage_lifecycle.py", ("selftest",), False),
    ("architecture-gate", "src/architecture_gate.py", ("selftest", "--require-evaluator"), False),
    ("project-quality", "src/project_quality_95.py", ("selftest",), False),
    ("cleanup-helper", "tools/code-cleanup-helper/scripts/self_test.py", (), False),
    ("project-kernel", "src/project_kernel.py", ("selftest",), False),
    ("release-manager", "src/release_manager.py", ("selftest",), True),
    ("word-captions", "src/longform_maker/word_captions.py", (), True),
    ("delivery-qa", "src/media_delivery_qa.py", (), True),
)

MANIFEST_NAMES = ("AUTOPILOT_MANIFEST.json", "release-manifest.json")


def _is_safe_required_path(value: object) -> bool:
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    if "\\" in value or "\x00" in value or any(char in value for char in "*?[]"):
        return False
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value or not path.parts:
        return False
    if any(part in {"", ".", ".."} or ":" in part for part in path.parts):
        return False
    return True


def _required_path_inventory(root: Path) -> tuple[list[str], list[dict]]:
    """Read both manifest contracts without making module import fallible."""
    required = set(MANIFEST_NAMES)
    checks = []
    for name in MANIFEST_NAMES:
        path = root / name
        check_id = "manifest-required:" + name
        if not path.is_file():
            checks.append({"id": check_id, "status": "RED", "detail": "manifest missing"})
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError):
            checks.append({"id": check_id, "status": "RED", "detail": "manifest unreadable"})
            continue
        except json.JSONDecodeError:
            checks.append({"id": check_id, "status": "RED", "detail": "manifest JSON malformed"})
            continue
        if not isinstance(payload, dict):
            checks.append({"id": check_id, "status": "RED", "detail": "manifest root is not an object"})
            continue
        values = payload.get("required_paths")
        if not isinstance(values, list):
            checks.append({"id": check_id, "status": "RED", "detail": "required_paths is not a list"})
            continue
        seen = set()
        issues = []
        for index, value in enumerate(values):
            if not isinstance(value, str):
                issues.append("entry[%d]:non-string" % index)
                continue
            if value in seen:
                issues.append("entry[%d]:duplicate" % index)
                continue
            seen.add(value)
            if not _is_safe_required_path(value):
                issues.append("entry[%d]:unsafe-relative-path" % index)
                continue
            required.add(value)
        checks.append({
            "id": check_id,
            "status": "RED" if issues else "GREEN",
            "detail": "; ".join(issues[:8]) if issues else "%d unique required paths" % len(seen),
        })
    return sorted(required), checks


def _required_file_check(root: Path, relative: str) -> dict:
    """Require a real file whose resolved target remains inside ``root``."""
    check_id = "file:" + relative
    try:
        resolved_root = root.resolve(strict=True)
        candidate = root.joinpath(*PurePosixPath(relative).parts)
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(resolved_root)
    except FileNotFoundError:
        return {"id": check_id, "status": "RED", "detail": relative + ": missing"}
    except (OSError, RuntimeError):
        return {"id": check_id, "status": "RED", "detail": relative + ": unresolvable"}
    except ValueError:
        return {
            "id": check_id,
            "status": "RED",
            "detail": relative + ": resolved outside repository",
        }
    if not resolved.is_file():
        return {"id": check_id, "status": "RED", "detail": relative + ": not a file"}
    return {"id": check_id, "status": "GREEN", "detail": relative}


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="system-health-manifest-") as temporary:
        base = Path(temporary)
        root = base / "repository"
        root.mkdir()
        valid = {"required_paths": ["src/example.py"]}
        for name in MANIFEST_NAMES:
            (root / name).write_text(json.dumps(valid), encoding="utf-8")
        required, checks = _required_path_inventory(root)
        assert required == sorted((*MANIFEST_NAMES, "src/example.py"))
        assert all(row["status"] == "GREEN" for row in checks)

        (root / MANIFEST_NAMES[0]).write_text("{", encoding="utf-8")
        _required, checks = _required_path_inventory(root)
        assert any(row["status"] == "RED" and "malformed" in row["detail"] for row in checks)

        (root / MANIFEST_NAMES[0]).write_text(
            json.dumps({"required_paths": "src/example.py"}), encoding="utf-8")
        _required, checks = _required_path_inventory(root)
        assert any(row["status"] == "RED" and "not a list" in row["detail"] for row in checks)

        bad = {"required_paths": ["safe.txt", "../escape.txt", "safe.txt", 7]}
        (root / MANIFEST_NAMES[0]).write_text(json.dumps(bad), encoding="utf-8")
        _required, checks = _required_path_inventory(root)
        detail = next(row["detail"] for row in checks if row["id"].endswith(MANIFEST_NAMES[0]))
        assert "unsafe-relative-path" in detail and "duplicate" in detail and "non-string" in detail

        outside = base / "outside"
        outside.mkdir()
        (outside / "target.txt").write_text("outside", encoding="utf-8")
        link = root / "link"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            # Some Windows hosts deny symlink creation.  The same containment
            # predicate must still reject a resolved path outside the root.
            status = _required_file_check(root, "../outside/target.txt")
        else:
            status = _required_file_check(root, "link/target.txt")
        assert status["status"] == "RED"
        assert status["detail"].endswith(
            ("resolved outside repository", "unresolvable", "missing")
        )
    print("system health manifest self-test GREEN")


def _run(label: str, relative: str, args: tuple[str, ...]) -> dict:
    path = ROOT / relative
    if not path.is_file():
        return {"id": label, "status": "RED", "detail": "missing " + relative}
    try:
        result = subprocess.run(
            [PYTHON, str(path), *args], cwd=ROOT, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=420,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"id": label, "status": "RED", "detail": str(exc)}
    output = ((result.stdout or "") + (result.stderr or "")).strip().splitlines()
    return {
        "id": label,
        "status": "GREEN" if result.returncode == 0 else "RED",
        "returncode": result.returncode,
        "detail": output[-1][:180] if output else "no output",
    }


def audit(*, quick: bool = False) -> dict:
    required_paths, manifest_checks = _required_path_inventory(ROOT)
    checks = list(manifest_checks)
    for relative in required_paths:
        checks.append(_required_file_check(ROOT, relative))
    compile_result = subprocess.run(
        [PYTHON, "-m", "compileall", "-q", "src", "scripts"], cwd=ROOT,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    checks.append({"id": "compileall", "status": "GREEN" if compile_result.returncode == 0 else "RED",
                   "detail": (compile_result.stderr or "compiled").strip()[-180:]})
    for label, relative, args, slow in TESTS:
        if quick and slow:
            checks.append({"id": label, "status": "SKIP", "detail": "slow test"})
        else:
            checks.append(_run(label, relative, args))
    failed = [row["id"] for row in checks if row["status"] == "RED"]
    return {"schema_version": 1, "status": "GREEN" if not failed else "RED",
            "quick": quick, "failed": failed, "checks": checks}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        self_test()
        return 0
    report = audit(quick=args.quick)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=" * 66)
        print("VIDEO AUTOPILOT HEALTH  quick=%s" % args.quick)
        print("=" * 66)
        for row in report["checks"]:
            print("[%-5s] %-30s %s" % (row["status"], row["id"][:30], row["detail"]))
        print("=" * 66)
        print("HEALTH %s%s" % (report["status"],
              " -> " + ", ".join(report["failed"]) if report["failed"] else ""))
    return 0 if report["status"] == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
