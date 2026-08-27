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
from typing import Any, Iterator

CONTRACT_FILE = Path(__file__).with_name("workflow_contract.json")
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
    if value is None: return "null"
    if value is True: return "true"
    if value is False: return "false"
    if isinstance(value, str): return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, int): return str(value)
    if isinstance(value, float):
        if not math.isfinite(value): raise WorkflowError("JSON value contains a non-finite number")
        if value.is_integer(): return str(int(value))
        return repr(value).replace("e+", "e")
    if isinstance(value, list): return "[" + ",".join(_js_json(item) for item in value) + "]"
    if isinstance(value, dict): return "{" + ",".join(_js_json(str(key)) + ":" + _js_json(item) for key, item in value.items()) + "}"
    raise WorkflowError(f"Unsupported JSON value: {type(value).__name__}")


def plan_sha256(plan: dict[str, Any]) -> str:
    """Match createHash('sha256').update(JSON.stringify(value)) for JSON values."""
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


def load_contract() -> tuple[dict[str, Any], str]:
    contract = require_mapping(read_json(CONTRACT_FILE), "workflow contract")
    if contract.get("schema") != "hao.video-autopilot.workflow-contract/v1":
        raise WorkflowError("Unsupported workflow contract schema")
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
    } for item in materials])


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
    contract, contract_sha = load_contract()
    if max_retries < 0 or max_retries > int(contract["limits"]["max_retries"]):
        raise WorkflowError(f"max_retries must be between 0 and {contract['limits']['max_retries']}")
    if task_class not in {"bulk_analysis", "rough_cut", "editorial_plan", "quality_critical", "contract_audit"}:
        raise WorkflowError(f"Unsupported inference task class: {task_class}")
    if priority not in {"economy", "balanced", "quality"}:
        raise WorkflowError(f"Unsupported inference priority: {priority}")
    source_sha = source_set_sha(materials)
    project_sha = sha256_file(project_file)
    skill_path = workspace / ".claude" / "skills" / "video-autopilot" / "SKILL.md"
    if not skill_path.is_file():
        raise WorkflowError(f"Canonical SKILL.md is missing: {skill_path}")
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
        "governance": {"skill_path": relative_path(workspace, skill_path), "skill_sha256": skill_sha},
        "binding": {**binding_core, "binding_sha256": binding_sha, "project_current_sha256": project_sha,
                    "output_path": relative_path(workspace, output_file), "materials": materials},
        "inference_request": {"task_class": task_class, "priority": priority},
        "plan": {"schema": None, "plan_sha256": None, "artifact": None, "artifact_sha256": None},
        "review": None, "steps": expand_steps(contract, materials, max_retries),
        "events": [{"at": now, "event": "run_created", "detail": {"binding_sha256": binding_sha}}],
    }


def create_run(workspace: Path, *, run_id: str, run_dir_raw: str | None, project_raw: str,
               output_raw: str | None, material_values: list[str], max_retries: int,
               task_class: str, priority: str) -> tuple[Path, dict[str, Any]]:
    contract, _ = load_contract()
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
    run_dir.mkdir(parents=True, exist_ok=False)
    state = create_state(workspace, run_id=safe_run_id, run_dir=run_dir, project_file=project_file,
                         output_file=output_file, materials=materials, max_retries=max_retries,
                         task_class=task_class, priority=priority)
    write_json_atomic(run_dir / state["contract"]["snapshot"], read_json(CONTRACT_FILE))
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
    contract, current_sha = load_contract()
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
    skill = within_workspace(workspace, state["governance"]["skill_path"], must_exist=True)
    if sha256_file(skill) != state["governance"]["skill_sha256"]:
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
