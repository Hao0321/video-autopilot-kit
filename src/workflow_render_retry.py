"""Bounded technical render rejection; never a human review or project reapply."""
from __future__ import annotations
import copy, json, math, os
from pathlib import Path
from workflow_state import (STATE_NAME, WorkflowError, add_event, load_state, plan_sha256,
    project_file, read_json, relative_path, require_mapping, require_sha, resolve_run,
    sha256_file, sha256_json, state_lock, utc_now, verify_immutable_sources,
    verify_project_binding, within_workspace, write_json_atomic)
from workflow_material_receipts import receipt_for

EVIDENCE_SCHEMA = "hao.video-autopilot.render-technical-rejection/v1"
FAILURES = {"black_frame", "shot_boundary_mismatch", "missing_frame", "audio_mismatch", "decode_failure"}

def output_for_attempt(state, workspace, attempt):
    base = within_workspace(workspace, state["binding"]["output_path"])
    return base if attempt == 1 else base.with_name(f"{base.stem}.attempt-{attempt:03d}{base.suffix}")

def active_render_output(state, workspace):
    step = state["steps"]["render"]
    # Legacy first renders retain their original path, even after transport retries.
    if not state.get("render_history"):
        return within_workspace(workspace, state["binding"]["output_path"])
    attempt = step["attempts"] + (1 if step["status"] == "pending" else 0)
    return output_for_attempt(state, workspace, attempt)

def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

def write_exclusive_json(path, value):
    data = _json_bytes(value)
    created = False
    try:
        with path.open("xb") as handle:
            created = True
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
    except BaseException:
        if created: path.unlink(missing_ok=True)
        raise

def _envelope(state, record):
    run = Path(state["run_dir"]).resolve()
    path = (run / record["path"]).resolve()
    if not path.is_relative_to(run / "receipts") or sha256_file(path) != record["file_sha256"]:
        raise WorkflowError("Render history receipt path/hash mismatch")
    value = require_mapping(read_json(path), "render receipt")
    for key, expected in (("run_id", state["run_id"]), ("binding_sha256", state["binding"]["binding_sha256"]),
                          ("source_set_sha256", state["binding"]["source_set_sha256"]), ("plan_sha256", state["plan"]["plan_sha256"])):
        if value.get(key) != expected: raise WorkflowError(f"Render receipt {key} mismatch")
    for field in ("payload", "submission", "request"):
        if sha256_json(value.get(field)) != value.get(field + "_sha256"):
            raise WorkflowError(f"Render receipt {field} hash mismatch")
    if value.get("step_id") != "render" or value.get("tool") != "render_project" or value.get("actor_type") != "machine":
        raise WorkflowError("Invalid render receipt provenance")
    return value

def _artifact(state, workspace, envelope, expected):
    facts = require_mapping(envelope.get("facts"), "render facts")
    path = within_workspace(workspace, facts["artifact"], must_exist=True)
    if path != expected or sha256_file(path) != facts.get("artifact_sha256") or path.stat().st_size != facts.get("bytes"):
        raise WorkflowError("Render artifact path/bytes/SHA changed")
    if within_workspace(workspace, envelope["request"]["outputPath"]) != path:
        raise WorkflowError("Render request output does not match artifact")
    applied = receipt_for(state, "apply")["facts"]
    if facts.get("plan_sha256") != state["plan"]["plan_sha256"] or facts.get("apply_receipt_id") != applied["receipt_id"]:
        raise WorkflowError("Render no longer binds plan/apply")
    return facts

def validate_evidence(state, workspace, evidence, facts):
    value = require_mapping(evidence, "technical rejection evidence")
    if set(value) != {"schema", "actor", "artifact", "artifactSha256", "failures"} or value["schema"] != EVIDENCE_SCHEMA or value["actor"] != "machine":
        raise WorkflowError("Expected strictly typed machine technical rejection evidence")
    if within_workspace(workspace, value["artifact"], must_exist=True) != within_workspace(workspace, facts["artifact"], must_exist=True) or require_sha(value["artifactSha256"], "artifactSha256") != facts["artifact_sha256"]:
        raise WorkflowError("Rejection evidence is for another artifact")
    failures = value["failures"]
    if not isinstance(failures, list) or not 1 <= len(failures) <= 100:
        raise WorkflowError("Rejection requires 1..100 evidenced failures")
    fps = read_json(project_file(state, workspace)).get("fps")
    if isinstance(fps, bool) or not isinstance(fps, (int, float)) or not math.isfinite(fps) or fps <= 0:
        raise WorkflowError("Project must provide finite positive fps for frame evidence")
    frames = math.ceil(float(facts["duration"]) * fps)
    for failure in failures:
        if not isinstance(failure, dict) or set(failure) != {"type", "frame", "evidenceFile", "evidenceSha256"} or failure["type"] not in FAILURES:
            raise WorkflowError("Unknown technical failure schema/type")
        if type(failure["frame"]) is not int or not 0 <= failure["frame"] < frames:
            raise WorkflowError("Failure frame outside rendered duration")
        path = within_workspace(workspace, failure["evidenceFile"], must_exist=True)
        if path == within_workspace(workspace, facts["artifact"]) or not path.is_file() or path.stat().st_size == 0 or sha256_file(path) != require_sha(failure["evidenceSha256"], "evidenceSha256"):
            raise WorkflowError("Missing/changed independent technical evidence file")

def verify_render_chain(state, workspace):
    history = state.get("render_history", [])
    if not isinstance(history, list): raise WorkflowError("Invalid render history")
    previous = 0
    for index, item in enumerate(history):
        attempt = item["attempt"]
        if type(attempt) is not int or attempt <= previous or attempt > state["steps"]["render"]["max_retries"]:
            raise WorkflowError("Render history attempt order/budget invalid")
        envelope = _envelope(state, item["receipt"])
        expected = within_workspace(workspace, state["binding"]["output_path"]) if index == 0 else output_for_attempt(state, workspace, attempt)
        facts = _artifact(state, workspace, envelope, expected)
        if envelope["attempt"] != attempt: raise WorkflowError("Historical render attempt mismatch")
        run = Path(state["run_dir"]).resolve(); path = (run / item["rejection"]["path"]).resolve()
        if not path.is_relative_to(run / "receipts") or sha256_file(path) != item["rejection"]["file_sha256"]:
            raise WorkflowError("Machine rejection receipt changed")
        rejection = read_json(path)
        expected_binding = {"run_id": state["run_id"], "attempt": attempt, "render_receipt": item["receipt"],
            "previous_rejection_sha256": history[index-1]["rejection"]["file_sha256"] if index else None,
            "project_sha256": state["binding"]["project_current_sha256"], "plan": state["plan"],
            "apply_receipt": state["steps"]["apply"]["receipt"], "source_set_sha256": state["binding"]["source_set_sha256"]}
        if any(rejection.get(k) != v for k,v in expected_binding.items()) or rejection.get("schema") != "hao.video-autopilot.machine-render-rejection-receipt/v1":
            raise WorkflowError("Machine rejection history binding mismatch")
        validate_evidence(state, workspace, rejection["evidence"], facts)
        previous = attempt
    step = state["steps"]["render"]
    if history and (step["attempts"] < previous or (step["status"] == "completed" and step["attempts"] <= previous)):
        raise WorkflowError("Active render does not follow rejected attempts")
    if step["status"] == "completed":
        envelope = _envelope(state, step["receipt"])
        if envelope["attempt"] != step["attempts"]: raise WorkflowError("Active render attempt mismatch")
        _artifact(state, workspace, envelope, active_render_output(state, workspace))

def verify_render_inputs(state, workspace):
    verify_immutable_sources(state, workspace, full=True); verify_project_binding(state, workspace)
    plan = state["plan"]; path = within_workspace(workspace, plan["artifact"], must_exist=True)
    if sha256_file(path) != plan["artifact_sha256"] or plan_sha256(read_json(path)) != plan["plan_sha256"]:
        raise WorkflowError("Bound plan artifact changed")
    applied = receipt_for(state, "apply"); facts = applied["facts"]
    committed_path = (project_file(state, workspace).parent / ".editkin-receipts" / facts["receipt_file"]).resolve()
    if not committed_path.is_relative_to((project_file(state, workspace).parent / ".editkin-receipts").resolve()):
        raise WorkflowError("Apply receipt escapes committed directory")
    committed = read_json(committed_path)
    payload = applied["payload"]["receipt"]
    # Editkin adds receiptFile to its returned transport after writing the committed file.
    # It is a locator, not persisted receipt content; require exact bound basename separately.
    if payload.get("receiptFile") != facts["receipt_file"] or Path(facts["receipt_file"]).name != facts["receipt_file"]:
        raise WorkflowError("Committed apply receipt locator mismatch")
    if any(committed.get(k) != v for k,v in payload.items() if k != "receiptFile") or committed.get("receiptFile", facts["receipt_file"]) != facts["receipt_file"] or committed.get("state") != "committed" or read_json(project_file(state, workspace)).get("revision") != facts["project_revision_after"]:
        raise WorkflowError("Committed apply receipt/project changed")
    verify_render_chain(state, workspace)

def guard_retry_claim(state, workspace):
    if not state.get("render_history"): return
    verify_render_inputs(state, workspace)
    step = state["steps"]["render"]
    if step["attempts"] > step["max_retries"]:
        raise WorkflowError("Render retry budget exhausted")
    target = active_render_output(state, workspace)
    receipt = Path(state["run_dir"]) / "receipts" / f"render-attempt-{step['attempts']+1:03d}.json"
    if target.exists() or receipt.exists(): raise WorkflowError("Retry output/receipt collision; existing bytes preserved")

def reject_render(workspace, raw_run, evidence, *, verify_run_fn):
    run = resolve_run(workspace, raw_run)
    with state_lock(run):
        state = load_state(run, workspace)
        if state["steps"]["render"]["status"] != "completed" or state["steps"]["apply"]["status"] != "completed":
            raise WorkflowError("Technical rejection requires completed apply and render")
        if state.get("review") is not None or any(state["steps"][key]["status"] != "pending" or state["steps"][key].get("claim") is not None or state["steps"][key].get("receipt") is not None or state["steps"][key]["attempts"] != 0 for key in ("human-review", "outcome")):
            raise WorkflowError("Human review/outcome already started; cannot reopen render")
        if verify_run_fn(state, workspace)["status"] != "GREEN": raise WorkflowError("Workflow receipt verification failed")
        verify_render_inputs(state, workspace)
        step = state["steps"]["render"]; attempt = step["attempts"]
        if attempt > step["max_retries"]: raise WorkflowError("Render retry budget exhausted")
        facts = receipt_for(state, "render")["facts"]; validate_evidence(state, workspace, evidence, facts)
        candidate = copy.deepcopy(state); history = candidate.setdefault("render_history", [])
        path = run / "receipts" / f"render-rejection-{attempt:03d}.json"
        rejection = {"schema": "hao.video-autopilot.machine-render-rejection-receipt/v1", "run_id": state["run_id"],
            "attempt": attempt, "render_receipt": copy.deepcopy(step["receipt"]), "project_sha256": state["binding"]["project_current_sha256"],
            "plan": copy.deepcopy(state["plan"]), "apply_receipt": copy.deepcopy(state["steps"]["apply"]["receipt"]),
            "source_set_sha256": state["binding"]["source_set_sha256"], "evidence": copy.deepcopy(evidence), "rejected_at": utc_now(),
            "previous_rejection_sha256": history[-1]["rejection"]["file_sha256"] if history else None}
        next_output = output_for_attempt(state, workspace, attempt+1)
        next_receipt = run / "receipts" / f"render-attempt-{attempt+1:03d}.json"
        if next_output.exists() or next_receipt.exists() or path.exists():
            raise WorkflowError("Retry output/receipt collision; no overwrite permitted")
        old_bytes = (run / STATE_NAME).read_bytes()
        rejection_bytes = _json_bytes(rejection)
        write_exclusive_json(path, rejection)
        try:
            record = {"path": path.relative_to(run).as_posix(), "file_sha256": sha256_file(path)}
            history.append({"attempt": attempt, "receipt": copy.deepcopy(step["receipt"]), "rejection": record})
            candidate["steps"]["render"].update(status="pending", claim=None, receipt=None, last_error="Machine technical QA rejected the rendered artifact")
            add_event(candidate, "render_technically_rejected", {"attempt": attempt, "rejection": record, "next_output": relative_path(workspace, next_output)})
            write_json_atomic(run / STATE_NAME, candidate)
        except BaseException:
            # The exclusive write above returned successfully, so this operation
            # owns these exact serialized bytes. Do not rely on the failing hash
            # reader for ownership, or delete evidence after an ambiguous commit.
            try:
                if (run / STATE_NAME).read_bytes() == old_bytes and path.read_bytes() == rejection_bytes:
                    path.unlink()
            except OSError:
                # Unreadable state/file or failed cleanup: retain the evidence and
                # original exception; never guess that a transaction did not commit.
                pass
            raise
        return {"status": "RENDER_RETRY_PENDING", "rejection": record, "next_output": relative_path(workspace, next_output), "human_review": "pending"}
