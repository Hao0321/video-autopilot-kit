#!/usr/bin/env python3
"""CLI and coordinator for the durable Editkin v4 autopilot workflow."""
from __future__ import annotations

import argparse, base64, hashlib, json, secrets, tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from workflow_receipts import claim_token_valid, complete_step, plan_sha256, prepared_facts, receipt_for, receipt_payload, semantic_facts, terminal_state, verify_run
from workflow_state import (
    CURRENT_PLAN_SCHEMA, STATE_NAME, WorkflowError, add_event, create_run, load_state, project_file,
    ready_steps, read_json, resolve_run, sha256_file, sha256_json, state_lock, state_summary, utc_now,
    verify_immutable_sources, verify_project_binding, within_workspace, workspace_path, write_json_atomic,
)


def step_instruction(state: dict[str, Any], step: dict[str, Any], workspace: Path) -> dict[str, Any]:
    project_path = state["binding"]["project_path"]
    material = next((item for item in state["binding"]["materials"] if item["key"] == step.get("material_key")), None)
    tool, inputs = step["tool"], {}
    note = "Submit the tool response; the controller accepts CallToolResult or decoded JSON."
    if tool == "start_ai_editing_session":
        inputs = {"projectPath": project_path}
    elif tool == "prepare_ai_material":
        inputs = {"projectPath": project_path, "clipId": material["clip_id"], "language": "auto", "includeTranscript": True, "maxKeyframes": 8}
    elif tool == "view_material_keyframes":
        facts = prepared_facts(state, material); frames = facts["frame_ids"]
        batches = [frames[index:index + 4] for index in range(0, len(frames), 4)]
        inputs = {"calls": [{"tool": tool, "arguments": {"materialId": facts["material_id"], "frameIds": batch}} for batch in batches]}
        note = ("Audio has no visual keyframes; submit {status:'N/A',batches:[]}." if not frames else
                "Run every listed call. Complete with {status:'GREEN',batches:[{request:<exact arguments>,result:<raw CallToolResult>}...]}; image bytes are hash-verified and not persisted.")
    elif tool == "get_material_context":
        facts, windows, cursor = prepared_facts(state, material), [], 0.0
        while cursor < float(facts["duration"]):
            end = min(float(facts["duration"]), cursor + 120.0)
            windows.append({"materialId": facts["material_id"], "start": cursor, "end": end, "maxCues": 200}); cursor = end
        inputs = {"calls": [{"tool": tool, "arguments": window} for window in windows]}
        note = "Run every listed bounded call. Complete with {status:'GREEN',windows:[{request:<exact arguments>,result:<raw CallToolResult>}...]} ."
    elif tool == "record_material_semantics":
        facts = prepared_facts(state, material)
        viewed = receipt_for(state, f"keyframes:{material['key']}")["facts"]["frame_ids"]
        cues = receipt_for(state, f"context:{material['key']}")["facts"]["cue_indexes"]
        segment = {"start": 0, "end": float(facts["duration"]), "summary": "TODO: replace with an evidence-backed summary",
                   "subjects": [], "actions": [], "objects": [], "importance": 0.5,
                   "evidenceFrameIds": viewed[:1], "transcriptCueIndexes": [] if viewed else cues[:1]}
        inputs = {"materialId": facts["material_id"], "sourceSha256": material["source_sha256"],
                  "overallTopic": "TODO: replace with the actual topic", "contentType": "TODO: replace with the actual content type",
                  "language": "auto", "people": [], "locations": [], "segments": [segment]}
        note = ("Replace every TODO and create evidence-backed segments using only verified frame IDs or loaded cue indexes. "
                "Call record_material_semantics with the completed request, then submit {request:<exact request>,result:<raw CallToolResult>}.")
    elif tool == "resolve_autopilot_inference_route":
        inputs = {"taskClass": state["inference_request"]["task_class"], "priority": state["inference_request"]["priority"]}
    elif tool == "list_installed_plugins":
        inputs = {"kind": "all", "automationReadyOnly": True}; note = "Discovery only; do not invoke a plugin."
    elif tool == "write_v4_plan":
        inputs = {"schema": CURRENT_PLAN_SCHEMA, "artifactPath": str(Path(state["run_dir"]) / "plan.v4.json")}
        note = "Write the exact v4 plan; submit {artifact,plan_sha256}. Legacy schemas are rejected."
    elif tool in {"audit_autopilot_plan", "apply_autopilot_plan"}:
        plan = read_json(within_workspace(workspace, state["plan"]["artifact"], must_exist=True))
        inputs = {"plan": plan}
        if tool == "apply_autopilot_plan":
            inputs["projectPath"] = project_path; note = "One atomic call only. If interrupted, do not retry; reconcile first."
    elif tool == "render_project":
        inputs = {"projectPath": project_path, "outputPath": state["binding"]["output_path"]}
    elif tool == "human_review":
        inputs = {"artifact": state["binding"]["output_path"], "requiredActor": "human"}
        note = "A human must inspect the render and submit review_id, decision, notes, certified=false."
    elif tool == "record_autopilot_outcome":
        review = state.get("review") or {}
        inputs = {"projectPath": project_path, "outcome": {"schema": "hao.video-autopilot.learning-event/v1",
            "planSha256": state["plan"]["plan_sha256"], "checkpoint": "human_review", "platform": "archive",
            "artifactId": receipt_for(state, "render")["facts"]["artifact_sha256"], "selectedMemoryRuleIds": [], "metrics": {},
            "review": {"accepted": review.get("decision") == "approved", "severeError": review.get("decision") == "rejected", "note": review.get("notes", "")}}}
    return {"tool": tool, "request": inputs, "note": note}


def claim_step(state: dict[str, Any], step_id: str | None, actor: str, worker: str, workspace: Path) -> dict[str, Any]:
    ready = ready_steps(state)
    if step_id is None:
        if not ready: raise WorkflowError("No workflow step is currently ready")
        step = ready[0]
    else:
        if step_id not in state["steps"]: raise WorkflowError(f"Unknown workflow step: {step_id}")
        step = state["steps"][step_id]
        if step not in ready: raise WorkflowError(f"Step is not ready: {step_id} ({step['status']})")
    if step["required_actor"] != actor: raise WorkflowError(f"Step {step['id']} requires actor type {step['required_actor']}")
    instruction, token = step_instruction(state, step, workspace), secrets.token_urlsafe(24)
    step["attempts"] += 1; step["status"] = "running"
    step["claim"] = {"worker": worker, "actor_type": actor, "claimed_at": utc_now(),
                     "token_sha256": hashlib.sha256(token.encode()).hexdigest(), "instruction": instruction,
                     "instruction_sha256": sha256_json(instruction), "request_sha256": sha256_json(instruction["request"])}
    step["last_error"] = None
    add_event(state, "step_claimed", {"step": step["id"], "attempt": step["attempts"], "worker": worker})
    return {"step": step["id"], "claim_token": token, "attempt": step["attempts"], "instruction": instruction}


def fail_step(state: dict[str, Any], step_id: str, token: str, reason: str) -> dict[str, Any]:
    if step_id not in state["steps"]: raise WorkflowError(f"Unknown workflow step: {step_id}")
    step = state["steps"][step_id]
    if step["status"] != "running" or not claim_token_valid(step, token): raise WorkflowError("Step is not running under this claim token")
    step["last_error"] = reason
    if step["retry"] == "reconcile_only":
        step["status"] = "reconcile_required"; add_event(state, "step_reconcile_required", {"step": step_id, "reason": reason})
    elif step["attempts"] <= step["max_retries"]:
        step["status"], step["claim"] = "pending", None; add_event(state, "step_retry_scheduled", {"step": step_id, "reason": reason})
    else:
        step["status"], step["claim"], state["status"] = "failed", None, "blocked"; add_event(state, "step_failed", {"step": step_id, "reason": reason})
    return {"step": step_id, "status": step["status"], "attempts": step["attempts"], "last_error": reason}


def resume_run(state: dict[str, Any], workspace: Path, resolution: str | None, payload: dict[str, Any] | None) -> dict[str, Any]:
    reset, reconcile = [], []
    for step in state["steps"].values():
        if step["status"] != "running": continue
        if step["retry"] == "reconcile_only":
            step["status"], step["last_error"] = "reconcile_required", "Interrupted atomic mutation; reconcile before retry"; reconcile.append(step["id"])
        else:
            step["status"], step["claim"], step["last_error"] = "pending", None, "Interrupted claim released by resume"; reset.append(step["id"])
    apply, result = state["steps"]["apply"], None
    if apply["status"] == "reconcile_required" and resolution:
        if resolution == "not-applied":
            actual, expected = sha256_file(project_file(state, workspace)), state["binding"]["project_current_sha256"]
            if actual != expected: raise WorkflowError("Project differs from pre-apply binding; cannot declare not-applied")
            apply.update({"status": "pending", "claim": None, "last_error": None}); result = {"apply": "not-applied", "status": "pending"}
            add_event(state, "apply_reconciled_not_applied", {"project_sha256": actual})
        elif resolution == "committed":
            if payload is None: raise WorkflowError("Committed apply reconciliation requires --receipt")
            result = complete_step(state, apply, payload, workspace, "machine", token=None, reconciled=True)
    elif resolution: raise WorkflowError("There is no reconcile_required apply step")
    add_event(state, "run_resumed", {"reset": reset, "reconcile_required": reconcile, "resolution": resolution})
    return {"reset_to_pending": reset, "reconcile_required": reconcile, "resolution": result}


def mutate(workspace: Path, raw_run: str, action: Callable[[dict[str, Any]], Any]) -> Any:
    run_dir = resolve_run(workspace, raw_run)
    with state_lock(run_dir):
        state = load_state(run_dir, workspace); verify_immutable_sources(state, workspace); result = action(state)
        write_json_atomic(run_dir / STATE_NAME, state); return result


def cmd_create(args: argparse.Namespace) -> dict[str, Any]:
    workspace = workspace_path(args.workspace)
    run_dir, state = create_run(workspace, run_id=args.run_id or datetime.now().strftime("%Y%m%d-%H%M%S"), run_dir_raw=args.run_dir,
        project_raw=args.project, output_raw=args.output, material_values=args.material, max_retries=args.max_retries,
        task_class=args.task_class, priority=args.priority)
    return {"run_dir": str(run_dir), "state": state_summary(state)}


def cmd_status(args: argparse.Namespace) -> dict[str, Any]:
    workspace = workspace_path(args.workspace); state = load_state(resolve_run(workspace, args.run), workspace)
    return state if args.full else state_summary(state)


def cmd_next(args: argparse.Namespace) -> dict[str, Any]:
    workspace = workspace_path(args.workspace); state = load_state(resolve_run(workspace, args.run), workspace)
    return {"ready": [{"step": item["id"], "tool": item["tool"], "parallel_group": item["parallel_group"], "material_key": item["material_key"]} for item in ready_steps(state)[:args.limit]]}


def cmd_claim(args: argparse.Namespace) -> dict[str, Any]:
    workspace = workspace_path(args.workspace)
    def action(state: dict[str, Any]) -> dict[str, Any]:
        verify_project_binding(state, workspace, allow_inflight_apply=True); return claim_step(state, args.step, args.actor_type, args.worker, workspace)
    return mutate(workspace, args.run, action)


def cmd_complete(args: argparse.Namespace) -> dict[str, Any]:
    workspace, payload = workspace_path(args.workspace), receipt_payload(args.receipt)
    def action(state: dict[str, Any]) -> dict[str, Any]:
        if args.step not in state["steps"]: raise WorkflowError(f"Unknown workflow step: {args.step}")
        step = state["steps"][args.step]; verify_project_binding(state, workspace, allow_inflight_apply=step["template_id"] == "apply")
        return complete_step(state, step, payload, workspace, args.actor_type, token=args.token)
    return mutate(workspace, args.run, action)


def cmd_fail(args: argparse.Namespace) -> dict[str, Any]:
    workspace = workspace_path(args.workspace); return mutate(workspace, args.run, lambda state: fail_step(state, args.step, args.token, args.reason))


def cmd_resume(args: argparse.Namespace) -> dict[str, Any]:
    workspace = workspace_path(args.workspace); payload = receipt_payload(args.receipt) if args.receipt else None
    return mutate(workspace, args.run, lambda state: resume_run(state, workspace, args.apply_resolution, payload))


def cmd_verify(args: argparse.Namespace) -> dict[str, Any]:
    workspace = workspace_path(args.workspace); run = resolve_run(workspace, args.run)
    with state_lock(run): return verify_run(load_state(run, workspace), workspace)


def test_complete(state: dict[str, Any], workspace: Path, step_id: str, payload: dict[str, Any], actor: str = "machine") -> None:
    claim = claim_step(state, step_id, actor, "selftest", workspace); complete_step(state, state["steps"][step_id], payload, workspace, actor, token=claim["claim_token"])


def _exercise_material_selftest(state: dict[str, Any], workspace: Path,
                                wrap: Callable[[dict[str, Any], list[bytes] | None], dict[str, Any]]) -> None:
    claims = [claim_step(state, f"prepare:{item['key']}", "machine", "parallel-test", workspace) for item in state["binding"]["materials"]]
    frame_bytes: dict[str, dict[str, bytes]] = {}
    for index, (item, claim) in enumerate(zip(state["binding"]["materials"], claims), start=1):
        raw_frames = {} if index == 2 else {f"kf-{n}": f"f{index}-{n}".encode() for n in range(1, 6)}
        frame_bytes[item["key"]] = raw_frames
        frames = [{"id": frame_id, "time": n, "sha256": hashlib.sha256(data).hexdigest()} for n, (frame_id, data) in enumerate(raw_frames.items(), start=1)]
        payload = {"status": "GREEN", "cacheHit": index == 1, "packet": {"materialId": hashlib.sha256(f"m{index}".encode()).hexdigest(), "source": {"sourceSha256": item["source_sha256"], "clipId": item["clip_id"], "assetId": f"asset-{index}", "duration": 12, "kind": "audio" if index == 2 else "video"}, "keyframes": frames}}
        complete_step(state, state["steps"][claim["step"]], payload, workspace, "machine", token=claim["claim_token"])
    for item in state["binding"]["materials"]:
        facts = prepared_facts(state, item); frames = [{"id": fid, "sha256": facts["frame_hashes"][fid]} for fid in facts["frame_ids"]]
        claim = claim_step(state, f"keyframes:{item['key']}", "machine", "selftest", workspace)
        if not frames:
            complete_step(state, state["steps"][claim["step"]], {"status": "N/A", "batches": []}, workspace, "machine", token=claim["claim_token"])
        else:
            issued = claim["instruction"]["request"]["calls"]
            def frame_call(spec: dict[str, Any], extra: list[str] | None = None) -> dict[str, Any]:
                request = spec["arguments"]; ids = list(request["frameIds"]) + (extra or [])
                viewed = [{"id": frame_id, "sha256": facts["frame_hashes"][frame_id]} for frame_id in ids]
                images = [frame_bytes[item["key"]][frame_id] for frame_id in ids]
                return {"request": request, "result": wrap({"status": "GREEN", "materialId": facts["material_id"], "frames": viewed}, images)}
            bad_calls = [frame_call(spec, [issued[1]["arguments"]["frameIds"][0]] if index == 0 and len(issued) > 1 else None) for index, spec in enumerate(issued)]
            try: complete_step(state, state["steps"][claim["step"]], {"status": "GREEN", "batches": bad_calls}, workspace, "machine", token=claim["claim_token"])
            except WorkflowError as error:
                if "1..4" not in str(error): raise
            else: raise AssertionError("oversized keyframe batch accepted")
            tampered_calls = [frame_call(spec) for spec in issued]
            tampered_calls[0]["result"]["content"][1]["data"] = base64.b64encode(b"tampered-image").decode("ascii")
            try: complete_step(state, state["steps"][claim["step"]], {"status": "GREEN", "batches": tampered_calls}, workspace, "machine", token=claim["claim_token"])
            except WorkflowError as error:
                if "do not match" not in str(error): raise
            else: raise AssertionError("tampered keyframe image accepted")
            complete_step(state, state["steps"][claim["step"]], {"status": "GREEN", "batches": [frame_call(spec) for spec in issued]}, workspace, "machine", token=claim["claim_token"])
        context_claim = claim_step(state, f"context:{item['key']}", "machine", "selftest", workspace)
        windows = []
        for spec in context_claim["instruction"]["request"]["calls"]:
            request = spec["arguments"]
            context = {"materialId": facts["material_id"], "sourceSha256": item["source_sha256"],
                       "window": {"start": request["start"], "end": request["end"]},
                       "transcript": {"cues": [{"index": 0, "start": 0, "end": 1, "text": "fixture"}], "hasMore": False}}
            windows.append({"request": request, "result": wrap({"status": "GREEN", "context": context})})
        complete_step(state, state["steps"][context_claim["step"]], {"status": "GREEN", "windows": windows}, workspace, "machine", token=context_claim["claim_token"])
        semantic_claim = claim_step(state, f"semantics:{item['key']}", "machine", "selftest", workspace)
        semantic_request = json.loads(json.dumps(semantic_claim["instruction"]["request"]))
        semantic_request["overallTopic"], semantic_request["contentType"] = "Fixture topic", "fixture"
        semantic_request["segments"][0]["summary"] = "Evidence-backed fixture segment"
        bad_request = json.loads(json.dumps(semantic_request))
        bad_request["segments"][0]["evidenceFrameIds"] = ["kf-999"]
        bad_request["segments"][0]["transcriptCueIndexes"] = []
        bad_sha = plan_sha256({"schema": "hao.editkin.material-semantics/v1", **bad_request})
        bad_result = wrap({"status": "GREEN", "receipt": {"schema": "hao.editkin.material-semantics/v1",
            "materialId": facts["material_id"], "sourceSha256": item["source_sha256"],
            "semanticReceiptSha256": bad_sha, "segmentCount": 1}})
        try: complete_step(state, state["steps"][semantic_claim["step"]], {"request": bad_request, "result": bad_result}, workspace, "machine", token=semantic_claim["claim_token"])
        except WorkflowError as error:
            if "did not view" not in str(error): raise
        else: raise AssertionError("unviewed semantic evidence accepted")
        semantic_sha = plan_sha256({"schema": "hao.editkin.material-semantics/v1", **semantic_request})
        semantic_result = wrap({"status": "GREEN", "receipt": {"schema": "hao.editkin.material-semantics/v1",
            "materialId": facts["material_id"], "sourceSha256": item["source_sha256"],
            "semanticReceiptSha256": semantic_sha, "segmentCount": 1}})
        complete_step(state, state["steps"][semantic_claim["step"]], {"request": semantic_request, "result": semantic_result}, workspace, "machine", token=semantic_claim["claim_token"])


def exercise_selftest(state: dict[str, Any], workspace: Path) -> None:
    def wrap(value: dict[str, Any], images: list[bytes] | None = None) -> dict[str, Any]:
        content = [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}]
        content.extend({"type": "image", "data": base64.b64encode(data).decode("ascii"), "mimeType": "image/jpeg"} for data in images or [])
        return {"content": content}
    contract_claim = claim_step(state, "contract", "machine", "selftest", workspace)
    contract_payload = {"status": "GREEN", "contract": {
        "schemaVersion": 3, "planSchema": CURRENT_PLAN_SCHEMA, "productVersion": "test", "legacyPlanSchemas": ["v3"],
        "sourcePolicy": {"dynamicCanonicalSkill": True, "packagePrivateSkillOrMemory": False}}}
    downgraded = json.loads(json.dumps(contract_payload)); downgraded["contract"]["schemaVersion"] = 2
    try: complete_step(state, state["steps"]["contract"], wrap(downgraded), workspace, "machine", token=contract_claim["claim_token"])
    except WorkflowError: pass
    else: raise AssertionError("downgraded Editkin contract accepted")
    complete_step(state, state["steps"]["contract"], wrap(contract_payload), workspace, "machine", token=contract_claim["claim_token"])
    test_complete(state, workspace, "session", wrap({"status": "GREEN", "clips": [{"clipId": item["clip_id"]} for item in state["binding"]["materials"]], "workflow": ["prepare_ai_material", "view_material_keyframes", "get_material_context", "record_material_semantics", "resolve_autopilot_inference_route", "audit_autopilot_plan", "apply_autopilot_plan", "render_project"]}))
    _exercise_material_selftest(state, workspace, wrap)
    route, plugins = claim_step(state, "route", "machine", "parallel-test", workspace), claim_step(state, "plugin-discovery", "machine", "parallel-test", workspace)
    complete_step(state, state["steps"]["route"], wrap({"status": "GREEN", "route": {"secondPassRequired": True, "executionMode": "audit_then_apply"}, "context": {"protocol": "markdown-router+json-contract/v1", "markdown": "router", "markdownRouterSha256": hashlib.sha256(b"router").hexdigest()}}), workspace, "machine", token=route["claim_token"])
    complete_step(state, state["steps"]["plugin-discovery"], wrap({"plugins": [{"id": "fixture", "capabilities": [{"id": "ready", "automationReady": True, "readiness": "AUTOMATION_READY"}]}]}), workspace, "machine", token=plugins["claim_token"])
    claim = claim_step(state, "plan", "machine", "selftest", workspace); plan_path = Path(state["run_dir"]) / "plan.v4.json"; write_json_atomic(plan_path, {"schema": "hao.video-autopilot.edit-plan/v3"}); legacy_sha = hashlib.sha256(b"legacy").hexdigest()
    try: complete_step(state, state["steps"]["plan"], {"artifact": str(plan_path), "plan_sha256": legacy_sha}, workspace, "machine", token=claim["claim_token"])
    except WorkflowError as error:
        if "Legacy" not in str(error): raise
    else: raise AssertionError("legacy plan accepted")
    evidence = []
    for item in state["binding"]["materials"]:
        facts = semantic_facts(state, item); evidence.append({"materialId": facts["material_id"], "sourceSha256": facts["source_sha256"], "assetId": facts["asset_id"], "clipId": facts["clip_id"], "semanticReceiptSha256": facts["semantic_receipt_sha256"]})
    router = receipt_for(state, "route")["facts"]["markdown_router_sha256"]
    plan = {"schema": CURRENT_PLAN_SCHEMA, "source": {"skillSha256": state["governance"]["skill_sha256"], "knowledgeSha256": hashlib.sha256(b"k").hexdigest()}, "materialEvidence": {"schema": "hao.editkin.material-intelligence/v1", "receipts": evidence}, "inference": {"context": {"markdownRouterSha256": router}}}; plan_sha = plan_sha256(plan); write_json_atomic(plan_path, plan)
    complete_step(state, state["steps"]["plan"], {"artifact": str(plan_path), "plan_sha256": plan_sha}, workspace, "machine", token=claim["claim_token"])
    test_complete(state, workspace, "audit", {"status": "GREEN", "planSha256": plan_sha, "coverage": {"legacy": False}, "commandCount": 3})
    claim_step(state, "apply", "machine", "selftest", workspace); resume_run(state, workspace, None, None)
    if state["steps"]["apply"]["status"] != "reconcile_required": raise AssertionError("apply auto-retried")
    resume_run(state, workspace, "not-applied", None); claim = claim_step(state, "apply", "machine", "selftest", workspace)
    project = project_file(state, workspace); data = read_json(project); data["revision"] = 1; write_json_atomic(project, data)
    applied = {"status": "REVIEW_REQUIRED", "receipt": {"planSchema": CURRENT_PLAN_SCHEMA, "planSha256": plan_sha, "receiptId": "r1", "receiptFile": "r1.committed.json", "committedAt": utc_now(), "state": "committed", "projectRevisionBefore": 0, "projectRevisionAfter": 1, "quality": {"outputState": "review_required", "certified": False}}}; committed = project.parent / ".editkin-receipts/r1.committed.json"; write_json_atomic(committed, {**applied["receipt"], "state": "committed"})
    complete_step(state, state["steps"]["apply"], applied, workspace, "machine", token=claim["claim_token"])
    output = within_workspace(workspace, state["binding"]["output_path"]); output.parent.mkdir(parents=True, exist_ok=True); output.write_bytes(b"mp4"); test_complete(state, workspace, "render", {"status": "GREEN", "artifact": str(output), "duration": 1.0})
    try: claim_step(state, "human-review", "machine", "selftest", workspace)
    except WorkflowError: pass
    else: raise AssertionError("machine claimed human review")
    test_complete(state, workspace, "human-review", {"review_id": "human-1", "decision": "approved", "certified": False}, "human")
    test_complete(state, workspace, "outcome", {"status": "RECORDED", "eventFile": "event.json", "handoff": {"planSha256": plan_sha, "checkpoint": "human_review"}})
    if state["status"] != "completed_approved": raise AssertionError("approved review did not produce completed_approved")
    if terminal_state("changes_requested") != "changes_requested" or terminal_state("rejected") != "rejected":
        raise AssertionError("non-approved human review was reported as completed")


def cmd_selftest(_args: argparse.Namespace) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="editkin-v4-workflow-") as raw:
        workspace = Path(raw).resolve(); skill = workspace / ".claude/skills/video-autopilot"; skill.mkdir(parents=True); (skill / "SKILL.md").write_text("---\nname: video-autopilot\n---\n", encoding="utf-8")
        project = workspace / "fixture.editkin.json"; write_json_atomic(project, {"revision": 0, "tracks": [], "assets": []}); a, b = workspace / "a.mp4", workspace / "b.mp4"; a.write_bytes(b"source-a"); b.write_bytes(b"source-b")
        run, state = create_run(workspace, run_id="selftest", run_dir_raw=None, project_raw=str(project), output_raw=None, material_values=[f"clip-a={a}", f"clip-b={b}"], max_retries=2, task_class="quality_critical", priority="quality")
        exercise_selftest(state, workspace); write_json_atomic(run / STATE_NAME, state); report = verify_run(state, workspace)
        if report["status"] != "GREEN" or report["completed_steps"] != report["total_steps"]: raise AssertionError(report)
        original = a.read_bytes(); a.write_bytes(b"tampered")
        try: verify_immutable_sources(state, workspace, full=True)
        except WorkflowError: pass
        else: raise AssertionError("source drift accepted")
        a.write_bytes(original)
        return {"selftest": "GREEN", "completed_steps": report["completed_steps"], "parallel_prepare": True,
                "parallel_route_plugin": True, "contract_downgrade_rejected": True, "audio_zero_keyframes": True,
                "legacy_plan_rejected": True, "oversized_keyframe_batch_rejected": True,
                "tampered_keyframe_rejected": True, "unviewed_semantic_evidence_rejected": True,
                "interrupted_apply_requires_reconcile": True, "machine_human_review_rejected": True,
                "non_approved_terminal_state": True, "source_drift_rejected": True}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__); root.add_argument("--workspace"); sub = root.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create"); create.add_argument("--run-id"); create.add_argument("--run-dir"); create.add_argument("--project", required=True); create.add_argument("--output"); create.add_argument("--material", action="append", default=[], metavar="CLIP_ID=SOURCE_FILE", help="Repeat once for every Editkin clip and its real source file"); create.add_argument("--max-retries", type=int, default=2); create.add_argument("--task-class", default="editorial_plan", choices=["bulk_analysis", "rough_cut", "editorial_plan", "quality_critical", "contract_audit"]); create.add_argument("--priority", default="quality", choices=["economy", "balanced", "quality"]); create.set_defaults(func=cmd_create)
    status = sub.add_parser("status"); status.add_argument("run"); status.add_argument("--full", action="store_true"); status.set_defaults(func=cmd_status)
    nxt = sub.add_parser("next"); nxt.add_argument("run"); nxt.add_argument("--limit", type=int, default=32); nxt.set_defaults(func=cmd_next)
    claim = sub.add_parser("claim"); claim.add_argument("run"); claim.add_argument("step", nargs="?"); claim.add_argument("--actor-type", choices=["machine", "human"], default="machine"); claim.add_argument("--worker", default="local-session"); claim.set_defaults(func=cmd_claim)
    complete = sub.add_parser("complete"); complete.add_argument("run"); complete.add_argument("step"); complete.add_argument("--token", required=True); complete.add_argument("--receipt", required=True); complete.add_argument("--actor-type", choices=["machine", "human"], default="machine"); complete.set_defaults(func=cmd_complete)
    fail = sub.add_parser("fail"); fail.add_argument("run"); fail.add_argument("step"); fail.add_argument("--token", required=True); fail.add_argument("--reason", required=True); fail.set_defaults(func=cmd_fail)
    resume = sub.add_parser("resume"); resume.add_argument("run"); resume.add_argument("--apply-resolution", choices=["not-applied", "committed"]); resume.add_argument("--receipt"); resume.set_defaults(func=cmd_resume)
    verify = sub.add_parser("verify"); verify.add_argument("run"); verify.set_defaults(func=cmd_verify); test = sub.add_parser("selftest"); test.set_defaults(func=cmd_selftest); return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try: result = args.func(args)
    except Exception as error: print(json.dumps({"ok": False, "error": type(error).__name__, "detail": str(error)}, ensure_ascii=False, indent=2)); return 1
    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2, default=str)); return 0


if __name__ == "__main__": raise SystemExit(main())
