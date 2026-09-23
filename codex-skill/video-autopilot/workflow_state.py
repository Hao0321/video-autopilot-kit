"""Atomic storage, path boundaries, DAG expansion, and run bindings."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

SKILL_PATH_ENV = "EDITKIN_VIDEO_AUTOPILOT_SKILL"
DEFAULT_SKILL_RELATIVE = Path(".codex") / "skills" / "video-autopilot" / "SKILL.md"
STATE_SCHEMA = "hao.video-autopilot.workflow-run/v1"
RECEIPT_SCHEMA = "hao.video-autopilot.workflow-receipt/v1"
CURRENT_PLAN_SCHEMA = "hao.video-autopilot.edit-plan/v4"
STATE_NAME = "workflow-state.json"
SHA256_RE = re.compile(r"^[a-f0-9]{64}$", re.IGNORECASE)
SAFE_ID_RE = re.compile(r"[^a-z0-9_-]+")


class WorkflowError(RuntimeError):
    """Expected contract or state violation."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    handle, raw = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temporary = Path(raw)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _js_json(value: Any) -> str:
    from workflow_json import json_stringify
    try: return json_stringify(value)
    except ValueError as error: raise WorkflowError(str(error)) from error


def plan_sha256(plan: dict[str, Any]) -> str:
    """Canonical Editkin plans; preserve legacy cue/semantic wire digests.

    Object insertion order may change at the MCP/Zod boundary. Plans therefore
    share Editkin's UTF-8-key canonical JSON; ordered arrays are never sorted.
    This helper also has historic non-plan callers whose wire hash must not move.
    """
    if isinstance(plan, dict) and str(plan.get("schema", "")).startswith("hao.video-autopilot.edit-plan/"):
        from workflow_json import json_sha256
        try:
            return json_sha256(plan, canonical=True)
        except ValueError as error:
            raise WorkflowError(str(error)) from error
    return hashlib.sha256(_js_json(plan).encode("utf-8")).hexdigest()


def slugify(value: str, fallback: str = "run") -> str:
    ascii_value = value.strip().lower().encode("ascii", "ignore").decode("ascii")
    result = SAFE_ID_RE.sub("-", ascii_value).strip("-_")
    if not result:
        result = f"{fallback}-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:8]}"
    return result[:64]


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def require_sha(value: Any, label: str) -> str:
    text = str(value or "").lower()
    if not SHA256_RE.fullmatch(text):
        raise WorkflowError(f"{label} must be a SHA-256 hex digest")
    return text


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WorkflowError(f"{label} must be a JSON object")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise WorkflowError(f"{label} must be a JSON array")
    return value


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


def within_workspace(workspace: Path, raw: str | os.PathLike[str], *, must_exist: bool = False) -> Path:
    candidate = Path(raw).expanduser()
    resolved = candidate.resolve() if candidate.is_absolute() else (workspace / candidate).resolve()
    if not is_within(resolved, workspace):
        raise WorkflowError(f"Path must stay inside workspace {workspace}: {resolved}")
    if must_exist and not resolved.exists():
        raise WorkflowError(f"Path does not exist: {resolved}")
    return resolved


def relative_path(workspace: Path, path: Path) -> str:
    return path.resolve().relative_to(workspace.resolve()).as_posix()


def resolve_canonical_skill(
    *, env: Mapping[str, str] | None = None, home: Path | None = None
) -> tuple[Path, str]:
    """Resolve the same live Skill source used by Editkin.

    An explicit environment path is useful for tests and non-default Codex
    installations.  Without it, the only authority is the user's canonical
    Codex Skill; a workspace copy is never considered.
    """
    environment = os.environ if env is None else env
    explicit = str(environment.get(SKILL_PATH_ENV, "")).strip()
    if explicit:
        candidate = Path(explicit).expanduser()
        if not candidate.is_absolute():
            raise WorkflowError(f"{SKILL_PATH_ENV} must be an absolute SKILL.md path")
        locator = f"env:{SKILL_PATH_ENV}"
    else:
        home_path = Path.home() if home is None else Path(home).expanduser()
        candidate = home_path / DEFAULT_SKILL_RELATIVE
        locator = "codex-home"
    skill_path = candidate.resolve()
    if not skill_path.is_file():
        raise WorkflowError(f"Canonical video-autopilot SKILL.md is missing: {skill_path}")
    skill_text = skill_path.read_text(encoding="utf-8-sig")
    if not re.search(r"^name:\s*video-autopilot\s*$", skill_text, re.MULTILINE):
        raise WorkflowError(f"Canonical Skill is not video-autopilot: {skill_path}")
    return skill_path, locator


def load_contract(skill_path: Path | None = None) -> tuple[dict[str, Any], str]:
    resolved_skill = skill_path.resolve() if skill_path else resolve_canonical_skill()[0]
    contract_path = resolved_skill.with_name("workflow_contract.json")
    if not contract_path.is_file():
        raise WorkflowError(f"Canonical workflow contract is missing beside SKILL.md: {contract_path}")
    contract = require_mapping(read_json(contract_path), "workflow contract")
    if contract.get("schema") != "hao.video-autopilot.workflow-contract/v1":
        raise WorkflowError("Unsupported workflow contract schema")
    if contract.get("contract_revision") != 5:
        raise WorkflowError("Workflow contract requires revision 5; install matching controller and start a new run")
    limits = require_mapping(contract.get("limits"), "workflow limits")
    for key, expected in {"keyframes_per_call": 4, "keyframe_bytes_per_call": 1000000, "material_poll_interval_ms": 10000}.items():
        if type(limits.get(key)) is not int or limits[key] != expected:
            raise WorkflowError(f"Workflow limit {key} must match the product contract: {expected}")
    if contract.get("plan_schema") != CURRENT_PLAN_SCHEMA or contract.get("legacy_plan_policy") != "reject":
        raise WorkflowError("Workflow contract must pin v4 and reject legacy plans")
    return contract, sha256_json(contract)


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


def validated_transcript_policy(value: Any) -> str:
    if value not in ("required", "visual-only"):
        raise WorkflowError("Transcript policy must be required or explicitly visual-only; failures never imply silence")
    return value


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


def validated_keyframe_times(value: Any, duration: float | None = None) -> list[float]:
    if (not isinstance(value, list) or not 1 <= len(value) <= 12
            or any(type(t) not in (int, float) or not math.isfinite(t) or t < 0
                   or (duration is not None and t >= duration)
                   or (i > 0 and t <= value[i - 1]) for i, t in enumerate(value))):
        raise WorkflowError("keyframe times require 1..12 finite, nonnegative, strictly increasing clip-relative seconds within the material")
    return list(value)


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
                 materials: list[dict[str, Any]], max_retries: int, task_class: str, priority: str) -> dict[str, Any]:
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
    binding_core = {
        "project_path": relative_path(workspace, project_file), "project_initial_sha256": project_sha,
        "source_set_sha256": source_sha, "contract_sha256": contract_sha, "skill_sha256": skill_sha,
    }
    binding_sha = sha256_json(binding_core)
    now = utc_now()
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
        },
        "binding": {**binding_core, "binding_sha256": binding_sha, "project_current_sha256": project_sha,
                    "output_path": relative_path(workspace, output_file), "materials": materials},
        "inference_request": {"task_class": task_class, "priority": priority},
        "plan": {"schema": None, "plan_sha256": None, "artifact": None, "artifact_sha256": None},
        "review": None, "steps": expand_steps(contract, materials, max_retries),
        "events": [{"at": now, "event": "run_created", "detail": {"binding_sha256": binding_sha}}],
    }


def create_run(workspace: Path, *, run_id: str, run_dir_raw: str | None, project_raw: str,
               output_raw: str | None, material_values: list[str], max_retries: int,
               task_class: str, priority: str, keyframe_values: list[str] | None = None,
               transcript_values: list[str] | None = None) -> tuple[Path, dict[str, Any]]:
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
    run_dir.mkdir(parents=True, exist_ok=False)
    state = create_state(workspace, run_id=safe_run_id, run_dir=run_dir, project_file=project_file,
                         output_file=output_file, materials=materials, max_retries=max_retries,
                         task_class=task_class, priority=priority)
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
    skill_path, _ = resolve_canonical_skill()
    contract, current_sha = load_contract(skill_path)
    if state.get("contract", {}).get("sha256") != current_sha:
        raise WorkflowError("Workflow contract changed after run creation; start a new run or migrate explicitly")
    snapshot = run_dir / state["contract"]["snapshot"]
    if not snapshot.is_file() or sha256_json(read_json(snapshot)) != current_sha:
        raise WorkflowError("Workflow contract snapshot is missing or corrupt")
    if state.get("controller") != contract.get("controller"):
        raise WorkflowError("Workflow controller identity mismatch")
    return state


def material_for(state: dict[str, Any], key: str | None) -> dict[str, Any]:
    for item in state["binding"]["materials"]:
        if item["key"] == key:
            return item
    raise WorkflowError(f"Unknown material key: {key}")


def step_material(state: dict[str, Any], step: dict[str, Any]) -> dict[str, Any] | None:
    return material_for(state, step["material_key"]) if step.get("material_key") else None


def verify_immutable_sources(state: dict[str, Any], workspace: Path, *, full: bool = False) -> list[dict[str, Any]]:
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


def project_file(state: dict[str, Any], workspace: Path) -> Path:
    return within_workspace(workspace, state["binding"]["project_path"], must_exist=True)


def verify_project_binding(state: dict[str, Any], workspace: Path, *, allow_inflight_apply: bool = False) -> str:
    actual = sha256_file(project_file(state, workspace))
    apply = state["steps"]["apply"]
    if allow_inflight_apply and apply["status"] in {"running", "reconcile_required"}:
        return actual
    if actual != state["binding"]["project_current_sha256"]:
        raise WorkflowError("Editkin project changed outside the recorded workflow binding")
    return actual


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
