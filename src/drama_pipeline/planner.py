"""Structured planning and production-pack validation."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .schema_validation import validate_instance
from .store import ProjectStore, read_json, write_json_atomic


ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def locate_short_drama_skill() -> Path:
    candidates = []
    override = os.environ.get("AI_SHORT_DRAMA_SKILL")
    if override:
        candidates.append(Path(override))
    candidates.extend(
        [
            Path.home() / ".codex" / "skills" / "ai-short-drama",
            Path.cwd() / ".claude" / "skills" / "ai-short-drama",
        ]
    )
    for candidate in candidates:
        if (candidate / "SKILL.md").is_file():
            return candidate.resolve()
    raise FileNotFoundError("Cannot locate the installed ai-short-drama skill")


def schema_path() -> Path:
    path = locate_short_drama_skill() / "scripts" / "production_pack.schema.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing production pack schema: {path}")
    return path


def linter_path() -> Path:
    path = locate_short_drama_skill() / "scripts" / "drama_lint.py"
    if not path.is_file():
        raise FileNotFoundError(f"Missing production pack linter: {path}")
    return path


def planning_prompt(config: dict[str, Any]) -> str:
    references = config.get("references") or []
    reference_text = "\n".join(f"- {item}" for item in references) or "- none"
    return f"""Use $ai-short-drama to create a production-ready AI microdrama pilot.

Return only JSON that matches the supplied output schema. Do not create or edit files.
Write story content in Traditional Chinese; keep all ids lowercase ASCII snake_case.

User premise: {config['topic']}
Market: {config['market']}
Surface: {config['surface']}
Format: {config['format']}
Pilot episodes: exactly {config['episodes']}
Target duration per episode: {config['episode_duration_seconds']} seconds
Aspect: {config['aspect']}
Target generation provider/model: {config['provider']} / {config['model']}
User references:
{reference_text}

Hard requirements:
1. Use one primary trope engine and at most two auxiliary engines.
2. Add one concrete fresh mechanism and a real constraint/cost for the protagonist.
3. Score all eight Greenlight dimensions. If the concept is below 30/40, improve it before output.
4. Build reveal, antagonist and payoff-debt progression; pay at least one debt within the pilot.
5. Every episode has a different dominant turn, payoff or progress, cliffhanger and state delta.
6. Every scene has state_before, event and state_after. Every shot has one observable main event.
7. Keep each generated shot between 2 and 15 seconds. Shot durations should approximately fill the episode.
8. Include exact dialogue ownership and performance where needed; use an empty dialogue array otherwise.
9. Visual anchors describe immutable identity/location facts, not vague quality adjectives.
10. Do not copy identifiable characters, dialogue or events from existing IP.
"""


def _codex_executable() -> str:
    executable = shutil.which("codex") or shutil.which("codex.cmd")
    if not executable:
        raise FileNotFoundError("codex CLI is not installed or not on PATH")
    return executable


def run_codex_plan(
    store: ProjectStore,
    *,
    model: str | None = None,
    timeout_seconds: int = 900,
) -> dict[str, Any]:
    output = store.work_dir / "codex_production_pack.json"
    command = [
        _codex_executable(),
        "exec",
        "--skip-git-repo-check",
        "--ephemeral",
        "--sandbox",
        "read-only",
        "--output-schema",
        str(schema_path()),
        "--output-last-message",
        str(output),
        "--cd",
        str(store.root),
    ]
    if model:
        command.extend(["--model", model])
    command.append("-")

    store.set_stage("plan", "running", "Codex structured planning")
    try:
        run = subprocess.run(
            command,
            input=planning_prompt(store.config()),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        store.set_stage("plan", "failed", str(exc))
        raise RuntimeError(f"Codex planning failed: {exc}") from exc

    (store.work_dir / "codex_exec.stdout.log").write_text(run.stdout, encoding="utf-8")
    (store.work_dir / "codex_exec.stderr.log").write_text(run.stderr, encoding="utf-8")
    if run.returncode != 0 or not output.is_file():
        detail = f"codex exec exit={run.returncode}; see _work/codex_exec.stderr.log"
        store.set_stage("plan", "failed", detail)
        raise RuntimeError(detail)
    try:
        pack = read_json(output)
    except (OSError, json.JSONDecodeError) as exc:
        store.set_stage("plan", "failed", f"invalid structured output: {exc}")
        raise RuntimeError(f"Codex returned invalid JSON: {exc}") from exc
    store.save_pack(pack)
    store.set_stage("plan", "complete", "production_pack.json created")
    return pack


def ingest_pack(store: ProjectStore, source: Path) -> dict[str, Any]:
    try:
        pack = read_json(source.expanduser().resolve())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot ingest production pack: {exc}") from exc
    if not isinstance(pack, dict):
        raise ValueError("Production pack must be a JSON object")
    store.save_pack(pack)
    store.set_stage("plan", "complete", f"ingested {source}")
    return pack


def run_base_linter(store: ProjectStore) -> dict[str, Any]:
    command = [
        sys.executable,
        str(linter_path()),
        str(store.pack_path),
        "--production-ready",
        "--json",
    ]
    run = subprocess.run(command, text=True, encoding="utf-8", capture_output=True, check=False)
    try:
        report = json.loads(run.stdout)
    except json.JSONDecodeError as exc:
        return {
            "valid": False,
            "error_count": 1,
            "warning_count": 0,
            "findings": [{"level": "error", "path": "$", "message": str(exc)}],
        }
    return report


def run_schema_validation(store: ProjectStore) -> list[dict[str, str]]:
    schema = read_json(schema_path())
    return [
        _finding("error", "$schema", message)
        for message in validate_instance(store.pack(), schema)
    ]


def _finding(level: str, path: str, message: str) -> dict[str, str]:
    return {"level": level, "path": path, "message": message}


def _validate_shot(
    shot: Any,
    path: str,
    known_ids: set[str],
    seen: set[str],
    findings: list[dict[str, str]],
) -> float:
    if not isinstance(shot, dict):
        findings.append(_finding("error", path, "must be an object"))
        return 0.0
    shot_id = shot.get("id")
    if not isinstance(shot_id, str) or not ID_PATTERN.match(shot_id):
        findings.append(_finding("error", f"{path}.id", "must be lowercase ASCII snake_case"))
    elif shot_id in seen:
        findings.append(_finding("error", f"{path}.id", f"duplicate id: {shot_id}"))
    else:
        seen.add(shot_id)
    duration = shot.get("duration_target")
    if not isinstance(duration, (int, float)) or isinstance(duration, bool) or not 2 <= duration <= 15:
        findings.append(_finding("error", f"{path}.duration_target", "must be between 2 and 15 seconds"))
        duration = 0
    for field in ("frame_intent", "observable_action", "camera", "audio", "continuity", "end_state", "negative"):
        if not isinstance(shot.get(field), str) or not shot[field].strip():
            findings.append(_finding("error", f"{path}.{field}", "must be a non-empty string"))
    for index, entity_id in enumerate(shot.get("entities", [])):
        if entity_id not in known_ids:
            findings.append(_finding("error", f"{path}.entities[{index}]", f"unknown entity id: {entity_id}"))
    if not isinstance(shot.get("dialogue"), list):
        findings.append(_finding("error", f"{path}.dialogue", "must be an array"))
    return float(duration)


def automation_findings(pack: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    known_ids = {
        item.get("id")
        for key in ("characters", "locations", "props")
        for item in pack.get(key, [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    seen_shots: set[str] = set()
    target = float(pack.get("project", {}).get("episode_duration_seconds", 0) or 0)
    for ep_index, episode in enumerate(pack.get("episodes", [])):
        ep_path = f"episodes[{ep_index}]"
        scenes = episode.get("scenes") if isinstance(episode, dict) else None
        if not isinstance(scenes, list) or not scenes:
            findings.append(_finding("error", f"{ep_path}.scenes", "must contain at least one scene"))
            continue
        total = 0.0
        for scene_index, scene in enumerate(scenes):
            scene_path = f"{ep_path}.scenes[{scene_index}]"
            if not isinstance(scene, dict):
                findings.append(_finding("error", scene_path, "must be an object"))
                continue
            for field in ("id", "purpose", "state_before", "event", "state_after", "turn", "end_hook"):
                if not isinstance(scene.get(field), str) or not scene[field].strip():
                    findings.append(_finding("error", f"{scene_path}.{field}", "must be a non-empty string"))
            shots = scene.get("shots")
            if not isinstance(shots, list) or not shots:
                findings.append(_finding("error", f"{scene_path}.shots", "must contain at least one shot"))
                continue
            for shot_index, shot in enumerate(shots):
                total += _validate_shot(
                    shot,
                    f"{scene_path}.shots[{shot_index}]",
                    known_ids,
                    seen_shots,
                    findings,
                )
        if target and not 0.65 * target <= total <= 1.25 * target:
            findings.append(
                _finding(
                    "warning",
                    ep_path,
                    f"shot durations total {total:.1f}s versus {target:.1f}s target",
                )
            )
    return findings


def contract_findings(pack: dict[str, Any], config: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    project = pack.get("project", {})
    episodes = pack.get("episodes", [])
    expected_episodes = int(config.get("episodes", 0))
    if len(episodes) != expected_episodes:
        findings.append(_finding("error", "episodes", f"expected exactly {expected_episodes} pilot episodes"))
    if project.get("planned_episodes") != expected_episodes:
        findings.append(_finding("error", "project.planned_episodes", "must match the requested pilot count"))
    if float(project.get("episode_duration_seconds", 0) or 0) != float(config.get("episode_duration_seconds", 0)):
        findings.append(_finding("error", "project.episode_duration_seconds", "must match the requested duration"))

    greenlight = pack.get("greenlight", {})
    dimensions = (
        "hook_clarity", "information_gap", "payoff_frequency", "escalation_room",
        "character_engine", "production_feasibility", "freshness", "seriality",
    )
    score = sum(int(greenlight.get(key, 0) or 0) for key in dimensions)
    if greenlight.get("total") != score:
        findings.append(_finding("error", "greenlight.total", f"must equal dimension sum {score}"))
    if score < 30 or greenlight.get("decision") != "greenlight":
        findings.append(_finding("error", "greenlight", "Auto mode requires an improved greenlight score of at least 30/40"))
    return findings


def validate_pack(store: ProjectStore) -> dict[str, Any]:
    store.set_stage("validate", "running", "linting production pack")
    base = run_base_linter(store)
    findings = (
        list(base.get("findings", []))
        + run_schema_validation(store)
        + automation_findings(store.pack())
        + contract_findings(store.pack(), store.config())
    )
    errors = [item for item in findings if item.get("level") == "error"]
    warnings = [item for item in findings if item.get("level") == "warning"]
    report = {
        "valid": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "findings": findings,
    }
    write_json_atomic(store.root / "validation_report.json", report)
    if errors:
        store.set_stage("validate", "failed", f"{len(errors)} error(s)")
    else:
        store.set_stage("validate", "complete", f"{len(warnings)} warning(s)")
    return report
