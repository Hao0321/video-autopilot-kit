#!/usr/bin/env python3
"""One-command, resumable AI short-drama production orchestrator."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from drama_pipeline.editor import approve_publish, build_all
from drama_pipeline.planner import ingest_pack, run_codex_plan, validate_pack
from drama_pipeline.store import ProjectStore, write_json_atomic
from drama_pipeline.tasks import (
    claim_task,
    compile_queue,
    complete_task,
    drain_mock,
    fail_task,
    next_task,
    queue_summary,
)
from project_paths import discover_project_root


def _workspace() -> Path:
    root = discover_project_root(Path(__file__))
    if root is None:
        raise RuntimeError("Video workspace is unavailable")
    return root


def _store(project: str) -> ProjectStore:
    return ProjectStore.open(_workspace(), project)


def _print(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def _create(args: argparse.Namespace) -> ProjectStore:
    return ProjectStore.create(
        _workspace(), topic=args.topic, project_id=args.project_id,
        episodes=args.episodes, duration=args.duration, format_name=args.format,
        market=args.market, surface=args.surface, aspect=args.aspect,
        resolution=args.resolution, provider=args.provider, model=args.media_model,
        max_retries=args.max_retries, references=args.reference,
    )


def _ensure_plan(store: ProjectStore, args: argparse.Namespace) -> None:
    if store.pack_path.is_file():
        return
    if getattr(args, "pack", None):
        ingest_pack(store, Path(args.pack))
    else:
        run_codex_plan(store, model=getattr(args, "planner_model", None), timeout_seconds=args.timeout)


def _ensure_validated(store: ProjectStore) -> dict[str, Any]:
    report = validate_pack(store)
    if not report["valid"]:
        raise RuntimeError(f"Production pack validation failed: {report['error_count']} error(s)")
    return report


def _ensure_queue(store: ProjectStore) -> None:
    if not store.queue_path.is_file():
        compile_queue(store)


def _browser_handoff(store: ProjectStore) -> dict[str, Any]:
    task = next_task(store)
    if task:
        store.set_stage("generate", "waiting", f"browser executor task: {task['id']}")
        return {
            "status": "waiting_for_browser_executor",
            "project": str(store.root),
            "next_task": task,
            "loop": [
                "claim the task",
                "generate on the named provider using ai-media-generator",
                "inspect identity, motion, audio and end-state",
                "complete with qc_passed or fail with a reason",
                "repeat until the queue is complete, then run build",
            ],
        }
    summary = queue_summary(store.queue())
    if summary.get("blocked") or summary.get("running") or summary.get("pending"):
        raise RuntimeError(f"No runnable task; queue is not complete: {summary}")
    return build_all(store)


def cmd_init(args: argparse.Namespace) -> dict[str, Any]:
    return _create(args).summary()


def cmd_plan(args: argparse.Namespace) -> dict[str, Any]:
    store = _store(args.project)
    if args.pack:
        ingest_pack(store, Path(args.pack))
    else:
        run_codex_plan(store, model=args.planner_model, timeout_seconds=args.timeout)
    return _ensure_validated(store)


def cmd_compile(args: argparse.Namespace) -> dict[str, Any]:
    store = _store(args.project)
    _ensure_validated(store)
    return compile_queue(store)


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    store = _store(args.project) if args.project else _create(args)
    _ensure_plan(store, args)
    _ensure_validated(store)
    _ensure_queue(store)
    if store.config()["provider"] == "mock":
        drain_mock(store)
        return build_all(store)
    return _browser_handoff(store)


def cmd_next(args: argparse.Namespace) -> dict[str, Any]:
    store = _store(args.project)
    task = next_task(store)
    return {"project": str(store.root), "next_task": task, "queue": queue_summary(store.queue())}


def cmd_claim(args: argparse.Namespace) -> dict[str, Any]:
    return claim_task(_store(args.project), args.task_id)


def cmd_complete(args: argparse.Namespace) -> dict[str, Any]:
    return complete_task(
        _store(args.project), args.task_id, Path(args.file), qc_passed=args.qc_passed,
        provider=args.provider_name, note=args.note, cost=args.cost,
    )


def cmd_fail(args: argparse.Namespace) -> dict[str, Any]:
    return fail_task(_store(args.project), args.task_id, args.reason)


def cmd_build(args: argparse.Namespace) -> dict[str, Any]:
    return build_all(_store(args.project))


def cmd_status(args: argparse.Namespace) -> dict[str, Any]:
    return _store(args.project).summary()


def cmd_approve(args: argparse.Namespace) -> dict[str, Any]:
    return approve_publish(_store(args.project), confirmed=args.confirm)


def _fixture_pack() -> dict[str, Any]:
    shot_common = {
        "entities": ["lin_an", "old_phone"], "camera": "穩定中近景，輕微前推",
        "audio": "安靜室內底噪與手機震動，無配樂", "dialogue": [],
        "continuity": "人物灰色外套、舊手機與桌面位置固定",
        "negative": "變臉、手指錯誤、跳切、字幕、Logo、浮水印",
    }
    shot_one = {
        **shot_common, "id": "ep001_shot01", "duration_target": 5,
        "frame_intent": "受辱前的壓抑近景", "observable_action": "林安低頭擦桌，舊手機突然亮起紅色倒數",
        "end_state": "林安手指停在手機上方，紅色倒數仍亮著",
    }
    shot_two = {
        **shot_common, "id": "ep001_shot02", "duration_target": 5,
        "frame_intent": "隱藏力量首次可見", "observable_action": "林安抬眼，玻璃杯在無接觸下停止墜落並回到桌面",
        "end_state": "玻璃杯穩立桌面，旁人尚未察覺異常",
    }
    return {
        "project": {"title": "倒數歸零前", "market": "zh-TW social", "format": "ai_live_action", "episode_duration_seconds": 15, "planned_episodes": 1},
        "greenlight": {
            "hook_clarity": 5, "information_gap": 5, "payoff_frequency": 4, "escalation_room": 4,
            "character_engine": 4, "production_feasibility": 4, "freshness": 4, "seriality": 4,
            "total": 34, "decision": "greenlight", "rationale": "首秒可見異常，十秒內完成一次小反轉。",
        },
        "premise_contract": {
            "public_identity": "被店員使喚的臨時工", "hidden_truth": "可讓物體回溯五秒的失蹤實驗者",
            "engine": "隱藏大佬與代價型時間能力", "season_question": "他能否在記憶消失前找回身分？",
            "fresh_twist": "每次回溯都會永久遺失一段私人記憶",
        },
        "characters": [{
            "id": "lin_an", "name": "林安", "public_identity": "沉默臨時工", "hidden_truth": "失蹤實驗者",
            "desire": "找回妹妹", "visual_anchor": "二十七歲臺灣男性，短黑髮，灰色舊外套，左眉細疤",
            "performance_anchor": "動作小、視線精準、情緒不外放", "voice_anchor": "低沉、短句、慢半拍",
        }],
        "locations": [{"id": "tea_shop", "name": "老茶店", "visual_anchor": "深木吧台、磨石地、午後側窗光，空間拓撲固定"}],
        "props": [{"id": "old_phone", "name": "舊手機", "visual_anchor": "黑色裂屏手機，紅色五秒倒數介面，不顯示品牌"}],
        "episodes": [{
            "id": "ep_001", "title": "五秒", "hook": "手機出現不可能的倒數", "turn": "臨時工在無人察覺下改變墜落結果",
            "payoff": "玻璃杯被回溯救回", "progress": "時間能力與代價第一次被建立", "cliffhanger": "手機跳出妹妹姓名",
            "characters": ["lin_an"], "locations": ["tea_shop"], "state_delta": ["觀眾確認林安能回溯物體"],
            "debts_opened": [{"id": "memory_cost", "due_episode": 1}], "debts_paid": ["memory_cost"],
            "continuation_capsule": "林安衣著與舊手機固定；下一集由妹妹姓名與記憶缺口續接。",
            "scenes": [{
                "id": "ep001_scene01", "purpose": "建立弱者表象並露出能力", "location_id": "tea_shop", "characters": ["lin_an"],
                "state_before": "林安被當作無足輕重的臨時工", "event": "倒數啟動且玻璃杯墜落", "state_after": "林安秘密回溯玻璃杯",
                "turn": "看似無能者掌握違反物理的能力", "end_hook": "手機顯示妹妹姓名", "shots": [shot_one, shot_two],
            }],
        }],
    }


def cmd_selftest(_args: argparse.Namespace) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="drama-autopilot-") as temp:
        workspace = Path(temp)
        (workspace / "AUTOPILOT_MANIFEST.json").write_text("{}", encoding="utf-8")
        store = ProjectStore.create(workspace, topic="自動化測試", episodes=1, duration=15, resolution="360x640", provider="mock")
        store.save_pack(_fixture_pack())
        report = validate_pack(store)
        if not report["valid"]:
            raise AssertionError(report)
        compile_queue(store)
        retry = next_task(store)
        if not retry:
            raise AssertionError("expected a ready task")
        claim_task(store, retry["id"])
        failed = fail_task(store, retry["id"], "synthetic retry test")
        if failed["status"] != "pending" or failed["attempts"] != 1:
            raise AssertionError("retry state did not persist")
        drain_mock(store)
        package = build_all(store)
        current = Path(package["episodes"][0]["current"])
        if not current.is_file() or not package["episodes"][0]["qa"]["all_green"]:
            raise AssertionError("end-to-end current.mp4 or QA is missing")
        try:
            approve_publish(store, confirmed=False)
        except ValueError:
            pass
        else:
            raise AssertionError("publish approval gate accepted a missing confirmation")
        approval = approve_publish(store, confirmed=True)
        if not approval["approved"]:
            raise AssertionError("explicit approval was not recorded")
        return {"selftest": "GREEN", "queue": queue_summary(store.queue()), "episode_sha256": package["episodes"][0]["sha256"]}


def _add_create_args(parser: argparse.ArgumentParser, *, require_topic: bool) -> None:
    parser.add_argument("--topic", required=require_topic)
    parser.add_argument("--project-id")
    parser.add_argument("--episodes", type=int, default=3)
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--format", default="ai_live_action")
    parser.add_argument("--market", default="zh-TW social")
    parser.add_argument("--surface", default="TikTok/Reels/Shorts")
    parser.add_argument("--aspect", default="9:16")
    parser.add_argument("--resolution", default="1080x1920")
    parser.add_argument("--provider", choices=["browser", "mock"], default="browser")
    parser.add_argument("--media-model", default="seedance-2.5-capability-gated")
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--reference", action="append", default=[])


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init"); _add_create_args(init, require_topic=True); init.set_defaults(func=cmd_init)
    plan = sub.add_parser("plan"); plan.add_argument("project"); plan.add_argument("--pack"); plan.add_argument("--planner-model"); plan.add_argument("--timeout", type=int, default=900); plan.set_defaults(func=cmd_plan)
    compile_cmd = sub.add_parser("compile"); compile_cmd.add_argument("project"); compile_cmd.set_defaults(func=cmd_compile)
    run = sub.add_parser("run"); _add_create_args(run, require_topic=False); run.add_argument("--project"); run.add_argument("--pack"); run.add_argument("--planner-model"); run.add_argument("--timeout", type=int, default=900); run.set_defaults(func=cmd_run)
    nxt = sub.add_parser("next"); nxt.add_argument("project"); nxt.set_defaults(func=cmd_next)
    claim = sub.add_parser("claim"); claim.add_argument("project"); claim.add_argument("task_id"); claim.set_defaults(func=cmd_claim)
    complete = sub.add_parser("complete"); complete.add_argument("project"); complete.add_argument("task_id"); complete.add_argument("file"); complete.add_argument("--qc-passed", action="store_true"); complete.add_argument("--provider-name", default="browser"); complete.add_argument("--note", default=""); complete.add_argument("--cost", type=float); complete.set_defaults(func=cmd_complete)
    fail = sub.add_parser("fail"); fail.add_argument("project"); fail.add_argument("task_id"); fail.add_argument("--reason", required=True); fail.set_defaults(func=cmd_fail)
    build = sub.add_parser("build"); build.add_argument("project"); build.set_defaults(func=cmd_build)
    status = sub.add_parser("status"); status.add_argument("project"); status.set_defaults(func=cmd_status)
    approve = sub.add_parser("approve"); approve.add_argument("project"); approve.add_argument("--confirm", action="store_true"); approve.set_defaults(func=cmd_approve)
    selftest = sub.add_parser("selftest"); selftest.set_defaults(func=cmd_selftest)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "run" and not args.project and not args.topic:
        parser().error("run requires --topic for a new project or --project to resume one")
    try:
        result = args.func(args)
    except Exception as exc:
        _print({"ok": False, "error": type(exc).__name__, "detail": str(exc)})
        return 1
    _print({"ok": True, "result": result})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
