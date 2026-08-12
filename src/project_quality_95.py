# -*- coding: utf-8 -*-
"""Deterministic project-level acceptance audit for architecture version 6.3.

This grades the production system, not the taste of an individual video.  A
video can only become CERTIFIED_95 after its own timestamped human review.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from project_paths import discover_project_root
from quality_corpus import load_corpus


HERE = Path(__file__).resolve().parent
ROOT = discover_project_root(HERE)
MANIFEST = ROOT / "AUTOPILOT_MANIFEST.json"


def _command(*parts: str, timeout: int = 120) -> dict[str, Any]:
    result = subprocess.run(list(parts), cwd=ROOT, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=timeout)
    return {"ok": result.returncode == 0, "returncode": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr[-2000:]}


def _check(identifier: str, title: str, passed: bool, evidence: Any,
           *, critical: bool = False) -> dict[str, Any]:
    return {"id": identifier, "title": title, "passed": bool(passed),
            "points": 5 if passed else 0, "max_points": 5,
            "critical": critical, "evidence": evidence}


def _acceptance_commands() -> dict[str, dict[str, Any]]:
    return {
        "health": _command(sys.executable, str(HERE / "system_health.py"), "--quick"),
        "architecture_gate": _command(sys.executable, str(HERE / "architecture_gate.py"), "audit"),
        "quality": _command(sys.executable, str(HERE / "quality_95.py"), "selftest"),
        "aesthetic": _command(sys.executable, str(HERE / "aesthetic_score.py"), "selftest"),
        "thumbnail": _command(sys.executable, str(HERE / "thumbnail_algorithm_score.py"), "selftest"),
        "visual_master": _command(sys.executable, str(HERE / "visual_master.py"), "selftest"),
        "calibration": _command(sys.executable, str(HERE / "color_calibration_lab.py"), "selftest"),
        "outcome": _command(sys.executable, str(HERE / "outcome_learning.py"), "selftest"),
        "taste": _command(sys.executable, str(HERE / "taste_model.py"), "selftest"),
        "licenses": _command(sys.executable, str(HERE / "asset_license_governance.py"), "selftest"),
        "domain_broll": _command(sys.executable, str(HERE / "domain_broll_pack.py"), "selftest"),
        "remix": _command(sys.executable, str(HERE / "remix_planner.py"), "selftest"),
        "storage_optimizer": _command(sys.executable, str(HERE / "storage_optimizer.py"), "selftest"),
        "corpus": _command(sys.executable, str(HERE / "quality_corpus.py"), "selftest"),
        "context": _command(sys.executable, str(HERE / "context_router.py"), "selftest"),
        "design": _command(sys.executable, str(HERE / "design_system_v6.py"), "selftest"),
        "information": _command(sys.executable, str(HERE / "mrbeast_editing_system.py"), "selftest"),
        "three_d": _command(sys.executable, str(HERE / "three_d_system.py"), "selftest"),
        "tracking": _command(sys.executable, str(HERE / "tracked_graphics.py"), "selftest"),
        "shorts": _command(sys.executable, str(HERE / "shorts_autopilot.py"), "selftest"),
        "longform": _command(
            sys.executable,
            str(HERE / "capcut_helpers" / "delivery_qa.py"), "selftest"),
        "publishing": _command(sys.executable, str(HERE / "publish_hub.py"), "selftest"),
        "template_compiler": _command(
            sys.executable, str(HERE / "template_compiler.py"), "selftest"),
        "mediastorm_craft": _command(
            sys.executable, str(HERE / "mediastorm_craft.py"), "selftest"),
    }


def _acceptance_source_paths() -> dict[str, Path]:
    return {
        "quality": HERE / "quality_95.py",
        "aesthetic": HERE / "aesthetic_score.py",
        "thumbnail": HERE / "thumbnail_algorithm_score.py",
        "visual_master": HERE / "visual_master.py",
        "visual_director": HERE / "visual_director.py",
        "calibration": HERE / "color_calibration_lab.py",
        "outcome": HERE / "outcome_learning.py",
        "taste": HERE / "taste_model.py",
        "licenses": HERE / "asset_license_governance.py",
        "domain_broll": HERE / "domain_broll_pack.py",
        "remix": HERE / "remix_planner.py",
        "storage_optimizer": HERE / "storage_optimizer.py",
        "short": HERE / "shorts_autopilot.py",
        "long": HERE / "capcut_helpers" / "delivery_qa.py",
        "asset": HERE / "asset_usage.py",
        "review": HERE / "review_loop.py",
        "tracking": HERE / "tracked_graphics.py",
        "design": HERE / "design_system_v6.py",
        "information": HERE / "mrbeast_editing_system.py",
        "three_d": HERE / "three_d_system.py",
        "typography": HERE / "tracked_typography.py",
        "delivery": HERE / "shorts_delivery.py",
        "publishing": HERE / "publish_hub.py",
        "publishing_layout": HERE / "publish_hub_layout.py",
        "template_compiler": HERE / "template_compiler.py",
        "mediastorm_craft": HERE / "mediastorm_craft.py",
    }


def _gather_evidence() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    required = [ROOT / path for path in manifest.get("required_paths", [])]
    doctor_run = _command(sys.executable, str(HERE / "project_kernel.py"), "doctor", "--json")
    try:
        doctor = json.loads(doctor_run["stdout"])
    except (TypeError, ValueError):
        doctor = {}
    commands = _acceptance_commands()
    try:
        architecture_result = json.loads(commands["architecture_gate"]["stdout"])
    except (TypeError, ValueError):
        architecture_result = {}
    source_paths = _acceptance_source_paths()
    return {
        "manifest": manifest,
        "missing": [str(path.relative_to(ROOT)) for path in required if not path.exists()],
        "doctor": doctor,
        "commands": commands,
        "architecture_result": architecture_result,
        "sources": {name: path.read_text(encoding="utf-8")
                    for name, path in source_paths.items()},
        "negative_ids": {row.get("id") for row in load_corpus().get("negative_cases", [])},
    }


def _foundation_checks(data: dict[str, Any], severe: list[dict[str, Any]]) -> list[dict[str, Any]]:
    manifest, doctor = data["manifest"], data["doctor"]
    commands = data["commands"]
    return [
        _check("architecture", "架構版本與六平面",
               manifest.get("architecture_version") == "6.3" and
               set(manifest.get("planes") or {}) == {
                   "control", "decision", "design", "asset", "execution", "evidence"
               },
               {"version": manifest.get("architecture_version"),
                "planes": sorted((manifest.get("planes") or {}).keys())}, critical=True),
        _check("required-paths", "必要模組完整", not data["missing"], data["missing"], critical=True),
        _check("architecture-gate", "校準後的架構閘門",
               commands["architecture_gate"]["ok"] and
               data["architecture_result"].get("status") == "GREEN",
               data["architecture_result"] or commands["architecture_gate"]["stdout"],
               critical=True),
        _check("project-doctor", "專案核心 Doctor", doctor.get("status") == "GREEN",
               {"status": doctor.get("status"), "errors": doctor.get("errors")}, critical=True),
        _check("system-health", "快速系統測試", commands["health"]["ok"],
               commands["health"]["stdout"], critical=True),
        _check("source-health", "無嚴重過長來源", not severe, severe),
        _check("sync", "安裝版與專案版同步",
               (doctor.get("sync") or {}).get("status") == "GREEN",
               doctor.get("sync")),
        _check("golden-negative", "黃金／負面案例回歸", commands["corpus"]["ok"],
               commands["corpus"]["stdout"], critical=True),
    ]


def _acceptance_checks(data: dict[str, Any]) -> list[dict[str, Any]]:
    manifest, doctor = data["manifest"], data["doctor"]
    commands, sources, negative_ids = data["commands"], data["sources"], data["negative_ids"]
    source_audit = doctor.get("source_audit") or {}
    severe = [row for group in ("large_files", "large_functions")
              for row in source_audit.get(group, []) if row.get("level") == "severe"]
    videos = (doctor.get("storage") or {}).get("videos") or {}
    video_gb = float(videos.get("gb", 0))
    storage_budget = manifest["budgets"]["storage_gb"]
    return _foundation_checks(data, severe) + [
        _check("aesthetic-standard", "跨長短片美感與封面演算法評分",
               commands["aesthetic"]["ok"] and commands["thumbnail"]["ok"] and
               commands["design"]["ok"] and commands["information"]["ok"] and
               commands["mediastorm_craft"]["ok"] and
               commands["visual_master"]["ok"] and commands["calibration"]["ok"] and
               len(negative_ids) >= 12 and
               all(token in sources["aesthetic"] for token in
                   ("format_multipliers", "resolve_style_route", "score_review")) and
               all(token in sources["design"] for token in
                   ("design_reference_dna.json", "reference_count", "format_reflow")) and
               all(token in sources["information"] for token in
                   ("subject_sheen", "contrast_gap_too_short", "blocked_substitutions")) and
               all(token in sources["mediastorm_craft"] for token in
                   ("resolve_transition", "expressive_transition_budget_exhausted",
                    "shot_match", "generic whoosh on every cut")) and
               all(token in sources["visual_master"] for token in
                   ("one_look_only", "source_before_graphics", "BLOCK_UNKNOWN_LOG")) and
               all(token in sources["thumbnail"] for token in
                   ("minimum_critical_value", "score_thumbnail", "PACKAGING_READY", "Test & Compare")),
               {"selftest": commands["aesthetic"]["stdout"],
                "design": commands["design"]["stdout"],
                "information": commands["information"]["stdout"],
                "mediastorm_craft": commands["mediastorm_craft"]["stdout"],
                "thumbnail": commands["thumbnail"]["stdout"],
                "visual_master": commands["visual_master"]["stdout"],
                "calibration": commands["calibration"]["stdout"],
                "negative_ids": sorted(str(value) for value in negative_ids)}),
        _check("quality-fail-closed", "Quality-95 人工簽核 fail-closed",
               commands["quality"]["ok"], commands["quality"]["stdout"], critical=True),
        _check("short-integration", "短片交付整合", commands["shorts"]["ok"] and
               all(token in sources["short"] for token in ("short_evidence", "create_review_bundle")),
               commands["shorts"]["stdout"]),
        _check("long-integration", "長片交付整合", commands["longform"]["ok"] and "final_delivery_qa" in sources["long"],
               commands["longform"]["stdout"]),
        _check("owner-review", "創作者人工時間碼審片閉環",
               all(token in sources["review"] for token in
                   ("review.html", "currentTime", "/api/review", "finalize")),
               "review HTML + POST + finalize"),
        _check("learning-loop", "主觀審美與觀眾成效分流學習",
               "record_feedback" in sources["review"] and "record_narrative" in sources["quality"] and
               commands["outcome"]["ok"] and commands["taste"]["ok"] and
               all(token in sources["outcome"] for token in ("INSUFFICIENT_EVIDENCE", "same_window_samples", "taste_feedback_is_not_audience_outcome")) and
               "add_comparison" in sources["taste"],
               {"outcome": commands["outcome"]["stdout"], "taste": commands["taste"]["stdout"]}),
        _check("asset-fatigue", "近期資產疲勞與授權 fail-closed 治理",
               all(token in sources["asset"] for token in
                   ("recent_content_window", "fatigue_score", "consecutive_content_streak")) and
               commands["licenses"]["ok"] and commands["domain_broll"]["ok"] and
               all(token in sources["licenses"] for token in ("redistributable", "blocked_missing_provenance", "fail_closed")),
               {"license": commands["licenses"]["stdout"], "domain_broll": commands["domain_broll"]["stdout"]}),
        _check("token-budget", "低 Token 路由", commands["context"]["ok"],
               commands["context"]["stdout"]),
        _check("tracking", "真實 Tracking、物件遮罩閃光與 3D 真實性",
               commands["tracking"]["ok"] and commands["three_d"]["ok"] and
               all(token in sources["tracking"] for token in
                   ("lost_hold_frames", "matte_clip_enforced", "full_frame_flash_possible")) and
               all(token in sources["three_d"] for token in
                   ("DOWNGRADED", "camera_solved_composite", "shadow catcher")),
               {"tracking": commands["tracking"]["stdout"],
                "three_d": commands["three_d"]["stdout"]}),
        _check("typography", "中英數值發光文字與掃描紋",
               all(token in sources["typography"] for token in
                   ("CJK_RE", "scanlines", "neon_value_green", "animate_text_plate")),
               "editable CJK/Latin/numeric typography"),
        _check("anti-template", "禁止空白模板／網格開場／怪轉場",
               {"generic-fullscreen-template", "grid-default-opener",
                "unmotivated-geometric-transition"}.issubset(negative_ids) and
               commands["template_compiler"]["ok"] and
               all(token in sources["template_compiler"] for token in
                   ("content_safe", "recent_signatures", "full_screen_card", "compact_instruction")) and
               "hao-template-compiler-v2" in sources["visual_director"],
               {"negative_ids": sorted(str(value) for value in negative_ids),
                "template_compiler": commands["template_compiler"]["stdout"]}),
        _check("storage-lifecycle", "目前成片單一真相、分類發佈中樞與原子發佈",
               commands["publishing"]["ok"] and commands["remix"]["ok"] and commands["storage_optimizer"]["ok"] and
               all(token in sources["publishing"] for token in
                   ("publish_hub_layout", "hardlink", "longform", "shorts")) and
               all(token in sources["publishing_layout"] for token in
                   ("exactly one delivery video", "sha256")) and
               "finalize_success" in sources["short"] and "atomic_publish" in sources["delivery"],
               {"publishing": commands["publishing"]["stdout"], "remix": commands["remix"]["stdout"],
                "cold_archive": commands["storage_optimizer"]["stdout"]}),
        _check("storage-headroom", "影片庫低於警戒容量",
               video_gb < float(storage_budget["videos_warning"]),
               {"physical_gb": video_gb, "warning_gb": storage_budget["videos_warning"],
                "max_gb": storage_budget["videos_max"],
                "hardlink_saved_gb": round(float(videos.get("hardlink_saved_bytes", 0)) /
                                           1024 ** 3, 3)}),
    ]


def audit() -> dict[str, Any]:
    checks = _acceptance_checks(_gather_evidence())
    earned_points = sum(row["points"] for row in checks)
    possible_points = sum(row["max_points"] for row in checks)
    if possible_points <= 0:
        raise RuntimeError("quality evaluator has no scored checks")
    # Normalize instead of assuming there will always be exactly twenty 5-point
    # checks.  This prevents a newly-added gate from making a failing report look
    # like a perfect 100/100 result.
    score = round(100.0 * earned_points / possible_points, 1)
    critical_failures = [row["id"] for row in checks if row["critical"] and not row["passed"]]
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": "project architecture and delivery system; not an individual video's taste",
        "score": score, "max_score": 100, "target": 95,
        "earned_points": earned_points, "possible_points": possible_points,
        "status": "ACCEPTED_95" if score >= 95 and not critical_failures else "BLOCKED",
        "critical_failures": critical_failures,
        "checks": checks,
        "video_certification_rule":
            "Every video still requires QUALITY_95.json plus creator-owned timestamped review.",
    }


def self_test() -> None:
    synthetic = [
        {"points": 5, "max_points": 5, "critical": False, "passed": True, "id": "pass"},
        {"points": 0, "max_points": 5, "critical": False, "passed": False, "id": "fail"},
    ]
    earned = sum(row["points"] for row in synthetic)
    possible = sum(row["max_points"] for row in synthetic)
    assert round(100.0 * earned / possible, 1) == 50.0
    synthetic.append(
        {"points": 5, "max_points": 5, "critical": False, "passed": True, "id": "new"}
    )
    earned = sum(row["points"] for row in synthetic)
    possible = sum(row["max_points"] for row in synthetic)
    assert round(100.0 * earned / possible, 1) == 66.7
    print("project_quality_95 self-test GREEN")


def write_report(report: dict[str, Any], output_dir: str | Path) -> tuple[Path, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = output / "PROJECT_QUALITY_95.json", output / "PROJECT_QUALITY_95.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Project Quality 95", "",
             "- 狀態：**%s**" % report["status"],
             "- 架構驗收：**%s / %s**" % (report["score"], report["max_score"]), "",
             "## 驗收表", ""]
    lines.extend("- [%s] %s：%s / %s" %
                 ("x" if row["passed"] else " ", row["title"],
                  row["points"], row["max_points"]) for row in report["checks"])
    lines += ["", "> 此分數驗收的是系統；每支影片仍須由創作者完成時間碼審片，才可標記 CERTIFIED_95。手機或電腦都只是審片工具。", ""]
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, markdown_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("audit", "selftest"), nargs="?", default="audit")
    parser.add_argument("--output-dir", default=str(ROOT / "reports"))
    args = parser.parse_args(argv)
    if args.command == "selftest":
        self_test()
        return 0
    report = audit()
    json_path, markdown_path = write_report(report, args.output_dir)
    print(json.dumps({"status": report["status"], "score": report["score"],
                      "json": str(json_path), "markdown": str(markdown_path),
                      "critical_failures": report["critical_failures"]},
                     ensure_ascii=False, indent=2))
    return 0 if report["status"] == "ACCEPTED_95" else 1


if __name__ == "__main__":
    raise SystemExit(main())
