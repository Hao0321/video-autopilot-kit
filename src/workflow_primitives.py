"""Public workflow values, path boundaries and stable hash semantics."""
from __future__ import annotations
import hashlib
import json
import math
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

def validated_transcript_policy(value: Any) -> str:
    if value not in ("required", "visual-only"):
        raise WorkflowError("Transcript policy must be required or explicitly visual-only; failures never imply silence")
    return value

def validated_keyframe_times(value: Any, duration: float | None = None) -> list[float]:
    if (not isinstance(value, list) or not 1 <= len(value) <= 12
            or any(type(t) not in (int, float) or not math.isfinite(t) or t < 0
                   or (duration is not None and t >= duration)
                   or (i > 0 and t <= value[i - 1]) for i, t in enumerate(value))):
        raise WorkflowError("keyframe times require 1..12 finite, nonnegative, strictly increasing clip-relative seconds within the material")
    return list(value)

def material_for(state: dict[str, Any], key: str | None) -> dict[str, Any]:
    for item in state["binding"]["materials"]:
        if item["key"] == key:
            return item
    raise WorkflowError(f"Unknown material key: {key}")

def step_material(state: dict[str, Any], step: dict[str, Any]) -> dict[str, Any] | None:
    return material_for(state, step["material_key"]) if step.get("material_key") else None

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
