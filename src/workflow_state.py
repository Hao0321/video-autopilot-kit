"""Atomic storage, path boundaries, DAG expansion, and run bindings."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping
from engine_continuity import (ENGINE_CONTINUITY_BINDING_SCHEMA, EngineContinuityError,
                               engine_continuity_sha256, parse_engine_continuity, require_engine_continuity)

from workflow_primitives import WorkflowError, STATE_SCHEMA, RECEIPT_SCHEMA, CURRENT_PLAN_SCHEMA, STATE_NAME, SHA256_RE, SAFE_ID_RE, utc_now, read_json, write_json_atomic, sha256_file, sha256_json, _js_json, plan_sha256, slugify, is_within, require_sha, require_mapping, require_list, within_workspace, relative_path, validated_transcript_policy, validated_keyframe_times, material_for, step_material, project_file, verify_project_binding

from workflow_contract_source import SKILL_PATH_ENV, DEFAULT_SKILL_RELATIVE, resolve_canonical_skill, load_contract

from public_workflow_sources import source_fingerprints

WORKFLOW_EXECUTABLE_SOURCES = (
    'workflow_primitives.py', 'workflow_contract_source.py', 'workflow_receipt_store.py', 'public_workflow_sources.py',
    "workflow_contract.py", "workflow_state.py", "workflow_receipts.py",
    "workflow_material_receipts.py", "workflow_transport.py", "workflow_audit_binding.py",
    "workflow_context_chain.py", "workflow_json.py", "workflow_render_retry.py",
    "workflow_binding_fixture.py", "review_policy.py", "agent_art_review.py", "engine_continuity.py", "workflow_contract.json",
)
MAX_WORKFLOW_EXECUTABLE_BYTES = 1024 * 1024






























def workspace_default() -> Path:
    current = Path.cwd().resolve()
    if (current / "AUTOPILOT_MANIFEST.json").is_file():
        return current
    candidate = Path(__file__).resolve().parents[3]
    if (candidate / "AUTOPILOT_MANIFEST.json").is_file():
        return candidate
    raise WorkflowError("Cannot infer the project workspace; pass --workspace explicitly")


def workspace_path(raw: str | None) -> Path:
    root = Path(raw).expanduser().resolve() if raw else workspace_default()
    if not root.is_dir():
        raise WorkflowError(f"Workspace does not exist: {root}")
    return root










@contextmanager
def state_lock(run_dir: Path, timeout: float = 8.0) -> Iterator[None]:
    lock_path = run_dir / ".workflow-state.lock"
    deadline = time.monotonic() + timeout
    while True:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(descriptor, "w", encoding="ascii") as stream:
                stream.write(f"{os.getpid()} {time.time()}\n")
            break
        except FileExistsError:
            try:
                if time.time() - lock_path.stat().st_mtime > 120:
                    lock_path.unlink()
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise WorkflowError(f"Timed out waiting for workflow state lock: {lock_path}")
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def add_event(state: dict[str, Any], name: str, detail: dict[str, Any] | None = None) -> None:
    events = state.setdefault("events", [])
    events.append({"at": utc_now(), "event": name, "detail": detail or {}})
    if len(events) > 500:
        del events[:-500]
    state["updated_at"] = utc_now()


def source_set_sha(materials: list[dict[str, Any]]) -> str:
    return sha256_json([{
        "key": item["key"], "clip_id": item["clip_id"], "source_path": item["source_path"],
        "source_sha256": item["source_sha256"], "bytes": item["bytes"],
        **({"keyframe_times": validated_keyframe_times(item["keyframe_times"])} if "keyframe_times" in item else {}),
        **({"transcript_policy": validated_transcript_policy(item["transcript_policy"])} if "transcript_policy" in item else {}),
    } for item in materials])




def with_transcript_policies(materials: list[dict[str, Any]], values: list[str]) -> list[dict[str, Any]]:
    selected = [dict(item) for item in materials]
    by_clip = {item["clip_id"]: item for item in selected}
    seen: set[str] = set()
    for value in values:
        clip_id, separator, raw = value.partition("=")
        clip_id = clip_id.strip()
        if not separator or clip_id not in by_clip or clip_id in seen:
            raise WorkflowError("--transcript-policy requires one known, nonduplicate CLIP_ID=required|visual-only")
        by_clip[clip_id]["transcript_policy"] = validated_transcript_policy(raw.strip())
        seen.add(clip_id)
    return selected




def with_keyframe_selections(materials: list[dict[str, Any]], values: list[str]) -> list[dict[str, Any]]:
    selected = [dict(item) for item in materials]
    by_clip = {item["clip_id"]: item for item in selected}
    seen: set[str] = set()
    for value in values:
        clip_id, separator, raw = value.partition("=")
        clip_id = clip_id.strip()
        if not separator or clip_id not in by_clip or clip_id in seen:
            raise WorkflowError("--keyframe-times requires one known, nonduplicate CLIP_ID=SECONDS,SECONDS selection")
        try:
            times = [float(part.strip()) for part in raw.split(",")]
        except ValueError as error:
            raise WorkflowError("Invalid --keyframe-times numeric selection") from error
        by_clip[clip_id]["keyframe_times"] = validated_keyframe_times(times)
        seen.add(clip_id)
    return selected


def parse_materials(workspace: Path, values: list[str], limit: int) -> list[dict[str, Any]]:
    if not values:
        raise WorkflowError("create requires at least one --material CLIP_ID=SOURCE_FILE")
    if len(values) > limit:
        raise WorkflowError(f"Material count exceeds contract limit {limit}")
    materials: list[dict[str, Any]] = []
    seen_clips: set[str] = set()
    for index, value in enumerate(values, start=1):
        clip_id, separator, raw_path = value.partition("=")
        clip_id = clip_id.strip()
        if not separator or not clip_id or not raw_path.strip():
            raise WorkflowError(f"Invalid --material value: {value!r}; expected CLIP_ID=SOURCE_FILE")
        if clip_id in seen_clips:
            raise WorkflowError(f"Duplicate material clip ID: {clip_id}")
        seen_clips.add(clip_id)
        source = within_workspace(workspace, raw_path.strip(), must_exist=True)
        if not source.is_file():
            raise WorkflowError(f"Material source is not a file: {source}")
        stat = source.stat()
        materials.append({
            "key": f"m{index:02d}-{slugify(clip_id, 'clip')[:36]}", "clip_id": clip_id,
            "source_path": relative_path(workspace, source), "source_sha256": sha256_file(source),
            "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns,
        })
    return materials


def expand_steps(contract: dict[str, Any], materials: list[dict[str, Any]], max_retries: int) -> dict[str, dict[str, Any]]:
    expanded: list[tuple[dict[str, Any], dict[str, Any] | None, str]] = []
    for template in require_list(contract.get("steps"), "contract.steps"):
        template = require_mapping(template, "step template")
        # Public CLI currently admits real media only. Canonical original-source
        # fanout must not become one unresolved, unimplemented public step.
        if template.get("fanout") == "original_sources":
            continue
        if template.get("fanout") == "materials":
            expanded.extend((template, item, str(template["id"]).replace("{material}", item["key"])) for item in materials)
        else:
            expanded.append((template, None, str(template["id"])))
    all_ids = [item[2] for item in expanded]
    steps: dict[str, dict[str, Any]] = {}
    for order, (template, material, step_id) in enumerate(expanded):
        dependencies: list[str] = []
        for raw in require_list(template.get("depends_on", []), f"{step_id}.depends_on"):
            dependency = str(raw)
            if "{material}" in dependency:
                if material is None:
                    raise WorkflowError(f"Non-material step {step_id} has a material dependency")
                dependencies.append(dependency.replace("{material}", material["key"]))
            elif dependency.endswith(":*"):
                matches = [candidate for candidate in all_ids if candidate.startswith(dependency[:-1])]
                if not matches:
                    raise WorkflowError(f"Wildcard dependency {dependency} matched no steps")
                dependencies.extend(matches)
            else:
                dependencies.append(dependency)
        if step_id in steps:
            raise WorkflowError(f"Duplicate expanded step: {step_id}")
        steps[step_id] = {
            "id": step_id, "template_id": template["id"], "tool": template["tool"],
            "depends_on": dependencies, "parallel_group": template.get("parallel_group"),
            "retry": template.get("retry", "safe"), "required_actor": template.get("actor", "machine"),
            "material_key": material["key"] if material else None, "order": order, "status": "pending",
            "attempts": 0, "max_retries": max_retries, "claim": None, "receipt": None, "last_error": None,
        }
    for step in steps.values():
        missing = [item for item in step["depends_on"] if item not in steps]
        if missing:
            raise WorkflowError(f"Step {step['id']} has missing dependencies: {missing}")
    return steps


def create_state(workspace: Path, *, run_id: str, run_dir: Path, project_file: Path, output_file: Path,
                 materials: list[dict[str, Any]], max_retries: int, task_class: str, priority: str,
                 review_policy: dict | None = None) -> dict[str, Any]:
    from review_policy import CREATOR_POLICY_PATH, load_creator_review_policy, policy_sha256, reviewer_actor
    policy = load_creator_review_policy(workspace, review_policy)
    policy_origin = "explicit" if review_policy is not None else "creator_configuration" if (workspace / CREATOR_POLICY_PATH).is_file() else "default"
    skill_path, skill_locator = resolve_canonical_skill()
    contract_path = skill_path.with_name("workflow_contract.json")
    contract, contract_sha = load_contract(skill_path)
    if max_retries < 0 or max_retries > int(contract["limits"]["max_retries"]):
        raise WorkflowError(f"max_retries must be between 0 and {contract['limits']['max_retries']}")
    if task_class not in {"bulk_analysis", "rough_cut", "editorial_plan", "quality_critical", "contract_audit"}:
        raise WorkflowError(f"Unsupported inference task class: {task_class}")
    if priority not in {"economy", "balanced", "quality"}:
        raise WorkflowError(f"Unsupported inference priority: {priority}")
    source_sha = source_set_sha(materials)
    project_sha = sha256_file(project_file)
    skill_sha = sha256_file(skill_path)
    floor = parse_engine_continuity(contract["engine_continuity_floor"])
    project_schema = read_json(project_file).get("schemaVersion")
    if type(project_schema) is not int or project_schema not in {9, 10}:
        raise WorkflowError("Current engine run requires an actual saved schema9 or schema10 project")
    executable_sources = workflow_executable_fingerprints(skill_path)
    controller_sources = workflow_executable_fingerprints(skill_path, controller=True)
    binding_core = {
        "project_path": relative_path(workspace, project_file), "project_initial_sha256": project_sha,
        "source_set_sha256": source_sha, "contract_sha256": contract_sha, "skill_sha256": skill_sha,
        "review_policy_sha256": policy_sha256(policy),
        "review_policy_origin": policy_origin,
        "engine_continuity": {"schema": ENGINE_CONTINUITY_BINDING_SCHEMA, "floor": floor,
                              "floor_sha256": engine_continuity_sha256(floor), "required_project_schema": project_schema},
        "workflow_executable_sha256": sha256_json({"canonical": executable_sources, "controller": controller_sources}),
    }
    binding_sha = sha256_json(binding_core)
    now = utc_now()
    steps = expand_steps(contract, materials, max_retries)
    steps["visual-review"]["required_actor"] = reviewer_actor(policy)
    return {
        "schema": STATE_SCHEMA, "controller": contract["controller"], "run_id": run_id,
        "created_at": now, "updated_at": now, "status": "active", "workspace": str(workspace),
        "run_dir": str(run_dir),
        "contract": {"schema": contract["schema"], "revision": contract["contract_revision"], "sha256": contract_sha, "snapshot": "workflow-contract.snapshot.json"},
        "governance": {
            "skill_locator": skill_locator,
            "skill_path": str(skill_path),
            "skill_sha256": skill_sha,
            "workflow_contract_path": str(contract_path),
            "controller_root": str(Path(__file__).resolve().parent),
            "executable_sources": executable_sources,
            "controller_executable_sources": controller_sources,
        },
        "binding": {**binding_core, "binding_sha256": binding_sha, "project_current_sha256": project_sha,
                    "output_path": relative_path(workspace, output_file), "materials": materials},
        "inference_request": {"task_class": task_class, "priority": priority},
        "plan": {"schema": None, "plan_sha256": None, "artifact": None, "artifact_sha256": None},
        "review_policy": policy, "review": None, "steps": steps,
        "events": [{"at": now, "event": "run_created", "detail": {"binding_sha256": binding_sha}}],
    }


def create_run(workspace: Path, *, run_id: str, run_dir_raw: str | None, project_raw: str,
               output_raw: str | None, material_values: list[str], max_retries: int,
               task_class: str, priority: str, keyframe_values: list[str] | None = None,
               transcript_values: list[str] | None = None, review_policy: dict | None = None) -> tuple[Path, dict[str, Any]]:
    from review_policy import load_creator_review_policy
    load_creator_review_policy(workspace, review_policy)  # validate before creating a run directory
    skill_path, _ = resolve_canonical_skill()
    contract, _ = load_contract(skill_path)
    project_file = within_workspace(workspace, project_raw, must_exist=True)
    if not project_file.is_file() or not re.search(r"\.(?:editkin|haoedit)\.json$", project_file.name, re.I):
        raise WorkflowError("--project must be an existing .editkin.json or .haoedit.json file")
    safe_run_id = slugify(run_id, "editkin")
    run_dir = within_workspace(workspace, run_dir_raw) if run_dir_raw else within_workspace(workspace, Path(contract["default_run_root"]) / safe_run_id)
    if run_dir.exists():
        raise WorkflowError(f"Run directory already exists: {run_dir}")
    output_file = within_workspace(workspace, output_raw if output_raw else run_dir / "render" / "current.mp4")
    if output_file.suffix.lower() != ".mp4":
        raise WorkflowError("Render output must end in .mp4")
    materials = parse_materials(workspace, material_values, int(contract["limits"]["material_count"]))
    materials = with_keyframe_selections(materials, keyframe_values or [])
    materials = with_transcript_policies(materials, transcript_values or [])
    state = create_state(workspace, run_id=safe_run_id, run_dir=run_dir, project_file=project_file,
                         output_file=output_file, materials=materials, max_retries=max_retries,
                         task_class=task_class, priority=priority, review_policy=review_policy)
    run_dir.mkdir(parents=True, exist_ok=False)
    contract_snapshot = read_json(Path(state["governance"]["workflow_contract_path"]))
    if sha256_json(contract_snapshot) != state["contract"]["sha256"]:
        raise WorkflowError("Canonical workflow contract changed while the run was being created")
    write_json_atomic(run_dir / state["contract"]["snapshot"], contract_snapshot)
    write_json_atomic(run_dir / STATE_NAME, state)
    return run_dir, state


def resolve_run(workspace: Path, raw: str) -> Path:
    candidate = Path(raw).expanduser()
    if candidate.is_absolute() or any(separator in raw for separator in ("/", "\\")):
        run_dir = within_workspace(workspace, candidate, must_exist=True)
    else:
        contract, _ = load_contract()
        run_dir = within_workspace(workspace, Path(contract["default_run_root"]) / raw, must_exist=True)
    if not (run_dir / STATE_NAME).is_file():
        raise WorkflowError(f"Not an Editkin v4 workflow run: {run_dir}")
    return run_dir


def load_state(run_dir: Path, workspace: Path) -> dict[str, Any]:
    state = require_mapping(read_json(run_dir / STATE_NAME), "workflow state")
    if state.get("schema") != STATE_SCHEMA:
        raise WorkflowError("Unsupported workflow state schema")
    if Path(state.get("workspace", "")).resolve() != workspace.resolve() or Path(state.get("run_dir", "")).resolve() != run_dir.resolve():
        raise WorkflowError("Workflow workspace or run_dir binding mismatch")
    snapshot = run_dir / state["contract"]["snapshot"]
    if not snapshot.is_file() or sha256_json(read_json(snapshot)) != state["contract"].get("sha256"):
        raise WorkflowError("Workflow contract snapshot is missing or corrupt")
    contract = require_mapping(read_json(snapshot), "recorded workflow contract")
    if state.get("controller") != contract.get("controller"):
        raise WorkflowError("Workflow controller identity mismatch")
    return state






def verify_immutable_sources(state: dict[str, Any], workspace: Path, *, full: bool = False) -> list[dict[str, Any]]:
    from review_policy import load_creator_review_policy, policy_sha256, reviewer_actor
    policy = require_mapping(state.get("review_policy"), "bound visual review policy")
    if (policy_sha256(policy) != state["binding"].get("review_policy_sha256") or
            state["steps"]["visual-review"]["required_actor"] != reviewer_actor(policy)):
        raise WorkflowError("Visual review policy or reviewer changed after run creation")
    if (state["binding"].get("review_policy_origin") != "explicit" and
            policy_sha256(load_creator_review_policy(workspace)) != state["binding"]["review_policy_sha256"]):
        raise WorkflowError("Creator review authorization changed; start a new bound run")
    results: list[dict[str, Any]] = []
    governance = require_mapping(state.get("governance"), "workflow governance")
    if not governance.get("skill_locator"):
        raise WorkflowError(
            "Workflow run predates canonical Codex Skill binding; start a new run or migrate explicitly"
        )
    skill, _ = resolve_canonical_skill()
    recorded_skill = Path(str(governance.get("skill_path", ""))).expanduser()
    if not recorded_skill.is_absolute() or recorded_skill.resolve() != skill:
        raise WorkflowError("Canonical video-autopilot Skill source changed after run creation")
    recorded_contract = Path(str(governance.get("workflow_contract_path", ""))).expanduser()
    current_contract = skill.with_name("workflow_contract.json")
    if not recorded_contract.is_absolute() or recorded_contract.resolve() != current_contract:
        raise WorkflowError("Canonical video-autopilot workflow contract source changed after run creation")
    if sha256_file(skill) != governance["skill_sha256"]:
        raise WorkflowError("Canonical video-autopilot SKILL.md changed after run creation")
    contract, contract_sha = load_contract(skill)
    if contract_sha != state["contract"].get("sha256"):
        raise WorkflowError("Workflow contract changed; historical runs are read-only. Start a new bound run")
    binding = require_mapping(state["binding"].get("engine_continuity"), "current-engine binding; historical runs are read-only")
    if set(binding) != {"schema", "floor", "floor_sha256", "required_project_schema"} or binding.get("schema") != ENGINE_CONTINUITY_BINDING_SCHEMA:
        raise WorkflowError("Run predates the current-engine binding; start a new run")
    immutable_binding_keys = ("project_path", "project_initial_sha256", "source_set_sha256", "contract_sha256",
                              "skill_sha256", "review_policy_sha256", "review_policy_origin", "engine_continuity",
                              "workflow_executable_sha256")
    if sha256_json({key: state["binding"].get(key) for key in immutable_binding_keys}) != state["binding"].get("binding_sha256"):
        raise WorkflowError("Immutable run binding hash is corrupt")
    try:
        floor_sha = engine_continuity_sha256(binding.get("floor"))
        if (floor_sha != binding.get("floor_sha256")
                or floor_sha != engine_continuity_sha256(contract["engine_continuity_floor"])
                or type(binding.get("required_project_schema")) is not int or binding["required_project_schema"] not in {9, 10}):
            raise WorkflowError("Bound current-engine floor/project schema changed")
    except EngineContinuityError as error:
        raise WorkflowError(str(error)) from error
    actual_sources = workflow_executable_fingerprints(skill)
    controller_sources = workflow_executable_fingerprints(skill, controller=True)
    if (governance.get("controller_root") != str(Path(__file__).resolve().parent)
            or actual_sources != governance.get("executable_sources")
            or controller_sources != governance.get("controller_executable_sources")
            or sha256_json({"canonical": actual_sources, "controller": controller_sources}) != state["binding"].get("workflow_executable_sha256")):
        raise WorkflowError("Workflow executable source changed; start a new generation run")
    actual_project_schema = read_json(project_file(state, workspace)).get("schemaVersion")
    if state["steps"]["contract"]["status"] == "completed":
        from workflow_receipt_store import receipt_for
        from workflow_contract_source import _contract
        recorded = receipt_for(state, "contract")
        facts = _contract(require_mapping(recorded.get("payload"), "sealed contract payload"), state["review_policy"], state)
        if facts != recorded.get("facts"):
            raise WorkflowError("Sealed current-engine contract facts changed")
        try:
            require_engine_continuity(facts["runtime"], binding["floor"], actual_project_schema)
        except EngineContinuityError as error:
            raise WorkflowError(str(error)) from error
        if actual_project_schema != binding["required_project_schema"]:
            if not (binding["required_project_schema"] == 9 and actual_project_schema == 10
                    and state["steps"]["apply"]["status"] in {"running", "reconcile_required", "completed"}):
                raise WorkflowError("Saved schema changed outside the sealed apply transition")
    elif actual_project_schema != binding["required_project_schema"]:
        raise WorkflowError("Saved schema changed before the actual runtime contract was sealed")
    for item in state["binding"]["materials"]:
        source = within_workspace(workspace, item["source_path"], must_exist=True)
        stat = source.stat()
        changed_stat = stat.st_size != item["bytes"] or stat.st_mtime_ns != item["mtime_ns"]
        actual = sha256_file(source) if full or changed_stat else item["source_sha256"]
        if actual != item["source_sha256"]:
            raise WorkflowError(f"Material source changed: {item['source_path']}")
        results.append({"key": item["key"], "sha256": actual, "bytes": stat.st_size})
    if source_set_sha(state["binding"]["materials"]) != state["binding"]["source_set_sha256"]:
        raise WorkflowError("Source-set binding hash is corrupt")
    return results






def dependencies_complete(state: dict[str, Any], step: dict[str, Any]) -> bool:
    return all(state["steps"][item]["status"] == "completed" for item in step["depends_on"])


def ready_steps(state: dict[str, Any]) -> list[dict[str, Any]]:
    ready = [step for step in state["steps"].values() if step["status"] == "pending" and dependencies_complete(state, step)]
    return sorted(ready, key=lambda item: (item["order"], item["id"]))


def state_summary(state: dict[str, Any]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for step in state["steps"].values():
        counts[step["status"]] = counts.get(step["status"], 0) + 1
    return {
        "run_id": state["run_id"], "status": state["status"], "run_dir": state["run_dir"],
        "project": state["binding"]["project_path"], "binding_sha256": state["binding"]["binding_sha256"],
        "source_set_sha256": state["binding"]["source_set_sha256"], "plan": state["plan"],
        "counts": counts, "ready": [step["id"] for step in ready_steps(state)],
        "blocked": [{"step": step["id"], "status": step["status"], "error": step["last_error"]}
                    for step in state["steps"].values() if step["status"] in {"failed", "reconcile_required"}],
        "updated_at": state["updated_at"],
    }


def workflow_executable_fingerprints(skill_path: Path, *, controller: bool = False) -> list[dict[str, Any]]:
    root = Path(__file__).resolve().parent if controller else skill_path.parent
    return source_fingerprints(root)
