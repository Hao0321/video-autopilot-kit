# -*- coding: utf-8 -*-
"""One-command health check for a clean public Video Autopilot install."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
PYTHON = sys.executable

# label, relative script, argv, slow
TESTS = (
    ("platform", "src/platform_compat.py", (), False),
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

REQUIRED = (
    "LICENSE", "README.md", "SETUP.md", "release-manifest.json",
    "AUTOPILOT_MANIFEST.json", "install_or_upgrade.py", "scripts/sync_canonical.py",
    "audit.config.json", "src/architecture_gate.py", "src/asset_workshop.py",
    "src/vfx_keyer.py",
    "tools/code-cleanup-helper/SKILL.md",
    "tools/code-cleanup-helper/CHANGELOG.md",
    "tools/code-cleanup-helper/audit.config.json",
    "tools/code-cleanup-helper/audit.config.example.json",
    "tools/code-cleanup-helper/agents/openai.yaml",
    "tools/code-cleanup-helper/scripts/audit.py",
    "tools/code-cleanup-helper/scripts/audit_core.py",
    "tools/code-cleanup-helper/scripts/self_test.py",
    "tools/code-cleanup-helper/scripts/check_links.py",
    "tools/code-cleanup-helper/scripts/check_drift.py",
    "tools/code-cleanup-helper/scripts/check_sync.py",
    "tools/code-cleanup-helper/scripts/check_build_receipt.py",
    "tools/code-cleanup-helper/scripts/check_audit_snapshot.py",
    "tools/code-cleanup-helper/scripts/check_skill_revision.py",
    "tools/code-cleanup-helper/scripts/sync_public.py",
    "tools/code-cleanup-helper/references/mode-a.md",
    "tools/code-cleanup-helper/references/mode-b.md",
    "tools/code-cleanup-helper/references/config-and-report.md",
    "tools/code-cleanup-helper/references/rd-integration.md",
    "tools/code-cleanup-helper/references/capability-obligations.md",
    "tools/code-cleanup-helper/references/build-receipt-audit.md",
    "tools/code-cleanup-helper/references/security-and-release-hygiene.md",
    "tools/code-cleanup-helper/references/cross-system-integration-audit.md",
    "tools/code-cleanup-helper/references/model-context-contract-audit.md",
    "src/release_manager.py", "src/project_paths.py", "src/context_router.py",
    "src/workflow_contract.py", "src/workflow_state.py", "src/workflow_receipts.py", "src/workflow_material_receipts.py", "src/workflow_transport.py", "src/workflow_contract.json", "src/broll_qa.py",
    "src/design_system_v6.py", "src/template_compiler.py", "src/mediastorm_craft.py",
    "src/mrbeast_editing_system.py", "src/mrbeast_source_map.py", "src/three_d_system.py",
    "src/asset_registry.py", "src/asset_usage.py", "src/asset_index_migration.py",
    "src/battle_plan_components.py",
    "src/knowledge_lifecycle.py", "src/visual_director.py",
    "src/visual_master.py", "src/quality_95.py", "src/tracked_graphics.py",
    "src/publish_contract.py", "src/publish_hub.py", "src/startup_update.py",
    "src/workspace_migrator.py", "src/storage_lifecycle.py", "src/project_kernel.py",
    "src/project_quality_95.py",
    "knowledge/runtime/aesthetic_standard.json",
    "knowledge/runtime/design_reference_dna.json",
    "knowledge/runtime/mediastorm_craft_benchmark.json",
    "knowledge/runtime/mrbeast_effect_source_map.json",
    "knowledge/runtime/color_grading_profiles.json",
    "knowledge/runtime/publishing_copy_playbooks.json",
    "codex-skill/video-autopilot/SKILL.md",
    "codex-skill/video-autopilot/workflow_contract.py",
    "codex-skill/video-autopilot/workflow_state.py",
    "codex-skill/video-autopilot/workflow_receipts.py",
    "codex-skill/video-autopilot/workflow_material_receipts.py",
    "codex-skill/video-autopilot/workflow_transport.py",
    "codex-skill/video-autopilot/workflow_contract.json",
    "codex-skill/video-autopilot/references/template-compiler-v2.md",
    "codex-skill/video-autopilot/references/mediastorm-craft-system.md",
    "codex-skill/video-autopilot/references/mrbeast-production-source-map.md",
    "codex-skill/video-autopilot/references/asset-workshop.md",
    "codex-skill/video-autopilot/agents/openai.yaml",
)


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
    checks = []
    for relative in REQUIRED:
        checks.append({"id": "file:" + relative, "status": "GREEN" if (ROOT / relative).is_file() else "RED",
                       "detail": relative})
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
    args = parser.parse_args(argv)
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
