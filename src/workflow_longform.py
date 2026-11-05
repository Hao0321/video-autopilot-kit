"""Long-form one timeline: chapters of one Editkin project, one set apply, one render.

This facade re-exports the long-form runtime (`workflow_longform_runtime.py`)
and keeps the synthetic, unsigned fixtures and the selftest. Only runs created
with `workflow_contract.py create-longform` use it; revision-6 `create` runs
never load it. Revision 6 (`workflow_contract.json`) stays the bound execution
contract with identical bytes, because Editkin seals its hash into every
chapter plan.

The fixtures below are synthetic and unsigned: never MCP authority, never an
Editkin audit, apply, render or art review. Fixtures that claim steps receive
the controller namespace (`host`, normally `vars(workflow_contract)`), so this
module never imports the CLI facade; run them with
`python src/workflow_contract.py selftest`.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workflow_primitives import CURRENT_PLAN_SCHEMA, WorkflowError, plan_sha256, project_file, read_json, within_workspace
from workflow_chapter_contract import REFUSED_COMMANDS, chapter_for, chapter_plan_path, plan_set_path, expected_chapter_receipts
from workflow_longform_runtime import (
    CONTRACT_NAME, CONTRACT_SCHEMA, SESSION_SCHEMA, SESSION_BINDING_SCHEMA, PLAN_SET_SCHEMA, AUDIT_RECEIPT_SCHEMA,
    MATERIAL_EVIDENCE_SCHEMA, LIMITS, AUDIT_RECEIPT_MAX_AGE_SECONDS, SESSION_MAX_BYTES, SEAL_TOOL, AUDIT_TOOL, APPLY_TOOL,
    _canonical, load_longform_contract, parse_session, bind_session, require_session_binding, validate_chapter_plan,
    expected_plan_set, validate_plan_set, bound_plan_set, set_chapter_plans, require_longform_capability,
    validate_longform_audit_binding, longform_audit, validate_longform_apply, longform_step_instruction,
)


# ---- synthetic fixtures for selftest and tests (unsigned; never Editkin authority) ----

def _wrap(value: dict[str, Any], images: list[bytes] | None = None) -> dict[str, Any]:
    content = [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}]
    content.extend({"type": "image", "data": base64.b64encode(data).decode("ascii"), "mimeType": "image/jpeg"} for data in images or [])
    return {"content": content}


def fixture_contract_payload(state: dict[str, Any]) -> dict[str, Any]:
    from workflow_binding_fixture import fixture_contract_payload as base
    payload = base(state)
    capability = dict(load_longform_contract()[0]["editkin_capability"])
    payload["contract"][capability.pop("key")] = capability
    return payload


def fixture_session_payload(state: dict[str, Any]) -> dict[str, Any]:
    workflow = ["prepare_ai_material", "view_material_keyframes", "get_material_context", "record_material_semantics",
                "resolve_autopilot_inference_route", "audit_autopilot_plan", "apply_autopilot_plan", "render_project",
                AUDIT_TOOL, APPLY_TOOL]
    return {"status": "GREEN", "clips": [{"clipId": item["clip_id"]} for item in state["binding"]["materials"]], "workflow": workflow}


def fixture_chapter_plan(state: dict[str, Any], chapter: dict[str, Any]) -> dict[str, Any]:
    from workflow_binding_fixture import fixture_live_invocation
    from workflow_receipt_store import receipt_for
    identity = fixture_live_invocation(state)
    start, end = chapter["range"]["startFrame"], chapter["range"]["endFrame"]
    return {
        "schema": CURRENT_PLAN_SCHEMA,
        "source": {"skillId": "video-autopilot", "revision": identity["skill"]["revision"], "skillSha256": identity["skill"]["sha256"],
                   "workflowContractRevision": identity["workflow"]["revision"], "workflowContractSha256": identity["workflow"]["sha256"],
                   "knowledgeRevision": 1, "knowledgeSha256": "a" * 64, "stableRulesSha256": "b" * 64,
                   "pluginRegistrySha256": "c" * 64, "invocationBindingSha256": identity["bindingSha256"]},
        "route": {"mode": "build", "format": "longform", "domain": "ai"},
        "materialEvidence": {"schema": MATERIAL_EVIDENCE_SCHEMA, "receipts": expected_chapter_receipts(state, chapter)},
        "inference": {"context": {"markdownRouterSha256": receipt_for(state, "route")["facts"]["markdown_router_sha256"]}},
        "editorial": {"narrative": {"beats": [{"id": f"{chapter['key']}-beat", "range": {"startFrame": start, "endFrame": end}}]},
                      "graphics": [{"id": f"{chapter['key']}-title", "range": {"startFrame": start, "endFrame": min(end, start + 30)}}],
                      "transitions": [{"id": f"{chapter['key']}-cut", "atFrame": start}],
                      "audio": {"impactFrames": [start], "breathFrames": []}, "color": {"exceptions": []}},
        "commands": [{"type": "add_caption", "text": f"synthetic {chapter['key']}"}],
    }


def fixture_seal_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    base = {key: value for key, value in receipt.items() if key not in {"receiptSha256", "issuerProof"}}
    return {**base, "receiptSha256": _canonical(base), "issuerProof": "0" * 64}


def fixture_set_audit(state: dict[str, Any], workspace: Path) -> dict[str, Any]:
    from workflow_binding_fixture import fixture_live_invocation
    plan_set = bound_plan_set(state, workspace)
    plans = set_chapter_plans(state, workspace, plan_set)
    path = project_file(state, workspace)
    project = read_json(path)
    normalized = str(path).lower() if os.name == "nt" else str(path)
    receipt = {"schema": AUDIT_RECEIPT_SCHEMA, "status": "ACCEPTED", "setSha256": state["plan"]["plan_sha256"],
               "project": {"id": project["id"], "revision": project["revision"],
                           "pathSha256": hashlib.sha256(normalized.encode()).hexdigest(), "contentSha256": _canonical(project)},
               "invocation": fixture_live_invocation(state),
               "chapters": [{"chapterId": row["chapterId"], "planSha256": row["planSha256"],
                             "materialEvidenceSha256": _canonical(plan["materialEvidence"]), "range": dict(row["range"])}
                            for row, plan in zip(plan_set["chapters"], plans)],
               "auditedAt": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")}
    return {"status": "ACCEPTED", "setSha256": receipt["setSha256"], "auditReceipt": fixture_seal_receipt(receipt)}


def fixture_set_apply(state: dict[str, Any], workspace: Path, *, revision_step: int = 1, before: int | None = None,
                      plan_schema: str = PLAN_SET_SCHEMA) -> dict[str, Any]:
    """Synthetic committed set apply: writes revision+step and one committed receipt file."""
    from workflow_receipt_store import receipt_for
    from workflow_primitives import utc_now, write_json_atomic
    plan_set = bound_plan_set(state, workspace)
    path = project_file(state, workspace)
    project = read_json(path)
    start = project["revision"] if before is None else before
    project["revision"] = start + revision_step
    write_json_atomic(path, project)
    audited = receipt_for(state, "audit")["facts"]["audit_receipt"]
    receipt = {"schema": "hao.video-autopilot.execution-receipt/v1", "planSchema": plan_schema, "planSha256": state["plan"]["plan_sha256"],
               "receiptId": "longform-r1", "receiptFile": "longform-r1.committed.json", "committedAt": utc_now(), "state": "committed",
               "projectRevisionBefore": start, "projectRevisionAfter": start + revision_step,
               "audit": {"receiptSha256": audited["receiptSha256"], "auditedAt": audited["auditedAt"],
                         "invocationBindingSha256": audited["invocation"]["bindingSha256"]},
               "longformSet": {"setSha256": state["plan"]["plan_sha256"], "baseProject": plan_set["baseProject"],
                               "chapters": [{"chapterId": row["chapterId"], "planSha256": row["planSha256"]} for row in plan_set["chapters"]]},
               "quality": {"inputState": "review_required", "outputState": "review_required", "certified": False}}
    write_json_atomic(path.parent / ".editkin-receipts" / receipt["receiptFile"], receipt)
    return {"status": "REVIEW_REQUIRED", "receipt": receipt}


def fixture_run_to_chapter_plans(host: dict[str, Any], state: dict[str, Any], workspace: Path) -> None:
    """contract -> session -> every material -> route and plugin-discovery (all synthetic)."""
    from workflow_receipts import complete_step
    claim_step = host["claim_step"]
    claim = claim_step(state, "contract", "machine", "longform-selftest", workspace)
    complete_step(state, state["steps"]["contract"], _wrap(fixture_contract_payload(state)), workspace, "machine", token=claim["claim_token"])
    claim = claim_step(state, "session", "machine", "longform-selftest", workspace)
    complete_step(state, state["steps"]["session"], _wrap(fixture_session_payload(state)), workspace, "machine", token=claim["claim_token"])
    host["_exercise_material_selftest"](state, workspace, _wrap)
    route = claim_step(state, "route", "machine", "longform-selftest", workspace)
    plugins = claim_step(state, "plugin-discovery", "machine", "longform-selftest", workspace)
    complete_step(state, state["steps"]["route"], _wrap({"status": "GREEN", "route": {"secondPassRequired": True, "executionMode": "audit_then_apply"},
        "context": {"protocol": "markdown-router+json-contract/v1", "markdown": "router", "markdownRouterSha256": hashlib.sha256(b"router").hexdigest()}}),
        workspace, "machine", token=route["claim_token"])
    complete_step(state, state["steps"]["plugin-discovery"], _wrap({"plugins": [{"id": "fixture", "capabilities": [
        {"id": "ready", "automationReady": True, "readiness": "AUTOMATION_READY"}]}]}), workspace, "machine", token=plugins["claim_token"])


def fixture_complete_chapter(host: dict[str, Any], state: dict[str, Any], workspace: Path, chapter: dict[str, Any],
                             plan: dict[str, Any] | None = None) -> dict[str, Any]:
    from workflow_receipts import complete_step
    from workflow_primitives import write_json_atomic
    step_id = f"plan:{chapter['key']}"
    claim = host["claim_step"](state, step_id, "machine", "longform-selftest", workspace)
    value = fixture_chapter_plan(state, chapter) if plan is None else plan
    path = Path(claim["instruction"]["request"]["artifactPath"])
    write_json_atomic(path, value)
    return complete_step(state, state["steps"][step_id], {"artifact": str(path), "plan_sha256": plan_sha256(value)},
                         workspace, "machine", token=claim["claim_token"])


def fixture_seal(host: dict[str, Any], state: dict[str, Any], workspace: Path) -> dict[str, Any]:
    from workflow_receipts import complete_step
    from workflow_primitives import write_json_atomic
    claim = host["claim_step"](state, "plan", "machine", "longform-selftest", workspace)
    request = claim["instruction"]["request"]
    write_json_atomic(Path(request["artifactPath"]), request["planSet"])
    return complete_step(state, state["steps"]["plan"], {"artifact": request["artifactPath"], "plan_sha256": request["planSetSha256"]},
                         workspace, "machine", token=claim["claim_token"])


def receipt_request(state: dict[str, Any], step_id: str) -> dict[str, Any]:
    from workflow_receipt_store import receipt_for
    return receipt_for(state, step_id)["request"]


def selftest(host: dict[str, Any], workspace: Path) -> dict[str, Any]:
    """Synthetic two-chapter session in a workspace whose canonical Skill the caller already pointed at a fixture."""
    from review_policy import review_checkpoint, reviewer_actor
    from workflow_receipts import complete_step, verify_run
    claim_step, fail_step, resume_run = host["claim_step"], host["fail_step"], host["resume_run"]
    from workflow_state import STATE_NAME, create_run
    from workflow_primitives import write_json_atomic
    workspace = Path(workspace).resolve()
    project = workspace / "longform-fixture.editkin.json"
    write_json_atomic(project, {"schemaVersion": 9, "id": "longform-fixture", "revision": 0, "fps": 30, "tracks": [], "assets": []})
    values = []
    for name in ("a", "b", "c"):
        (workspace / f"longform-{name}.mp4").write_bytes(f"synthetic long-form source {name}".encode())
        values.append(f"clip-{name}={workspace / f'longform-{name}.mp4'}")
    session = workspace / "longform-session.json"
    write_json_atomic(session, {"schema": SESSION_SCHEMA, "chapters": [
        {"chapterId": "intro", "range": {"startFrame": 0, "endFrame": 300}, "clipIds": ["clip-a", "clip-b"]},
        {"chapterId": "demo", "range": {"startFrame": 300, "endFrame": 900}, "clipIds": ["clip-b", "clip-c"]}]})
    run, state = create_run(workspace, run_id="longform-selftest", run_dir_raw=None, project_raw=str(project), output_raw=None,
                            material_values=values, max_retries=2, task_class="quality_critical", priority="quality",
                            longform_session_path=str(session))
    tools = [step["tool"] for step in state["steps"].values()]
    if (tools.count(APPLY_TOOL) != 1 or tools.count("render_project") != 1 or tools.count("write_v4_plan") != 2
            or state["steps"]["plan"]["depends_on"] != ["plan:intro", "plan:demo"] or state["steps"]["render"]["depends_on"] != ["apply"]):
        raise AssertionError("long-form DAG is not one set apply and one render")
    fixture_run_to_chapter_plans(host, state, workspace)
    if state["steps"]["session"]["claim"] is not None or receipt_request(state, "session") != {"projectPath": state["binding"]["project_path"], "clipLimit": 100}:
        raise AssertionError("long-form session request is not {projectPath, clipLimit:100}")
    claim = claim_step(state, "plan:intro", "machine", "longform-selftest", workspace)
    outside = fixture_chapter_plan(state, state["binding"]["longform_session"]["chapters"][0])
    outside["editorial"]["narrative"]["beats"][0]["range"] = {"startFrame": 290, "endFrame": 310}
    write_json_atomic(Path(claim["instruction"]["request"]["artifactPath"]), outside)
    try:
        complete_step(state, state["steps"]["plan:intro"], {"artifact": claim["instruction"]["request"]["artifactPath"],
                      "plan_sha256": plan_sha256(outside)}, workspace, "machine", token=claim["claim_token"])
    except WorkflowError as error:
        if "LONGFORM_CHAPTER_FRAME_OUTSIDE_RANGE" not in str(error):
            raise
    else:
        raise AssertionError("beat outside its chapter range accepted")
    fail_step(state, "plan:intro", claim["claim_token"], "synthetic beat outside its chapter range")
    for chapter in state["binding"]["longform_session"]["chapters"]:
        fixture_complete_chapter(host, state, workspace, chapter)
    sealed = fixture_seal(host, state, workspace)
    if state["plan"]["schema"] != PLAN_SET_SCHEMA or sealed["facts"]["chapter_count"] != 2:
        raise AssertionError("plan set was not sealed")
    claim = claim_step(state, "audit", "machine", "longform-selftest", workspace)
    if set(claim["instruction"]["request"]) != {"projectPath", "planSet"}:
        raise AssertionError("set audit request is not {projectPath, planSet}")
    complete_step(state, state["steps"]["audit"], fixture_set_audit(state, workspace), workspace, "machine", token=claim["claim_token"])
    claim_step(state, "apply", "machine", "longform-selftest", workspace)
    resume_run(state, workspace, None, None)
    if state["steps"]["apply"]["status"] != "reconcile_required":
        raise AssertionError("interrupted set apply was retried")
    resume_run(state, workspace, "not-applied", None)
    claim = claim_step(state, "apply", "machine", "longform-selftest", workspace)
    if set(claim["instruction"]["request"]) != {"projectPath", "planSet", "auditReceipt"}:
        raise AssertionError("set apply request is not {projectPath, planSet, auditReceipt}")
    complete_step(state, state["steps"]["apply"], fixture_set_apply(state, workspace), workspace, "machine", token=claim["claim_token"])
    output = within_workspace(workspace, state["binding"]["output_path"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"synthetic long-form mp4")
    claim = claim_step(state, "render", "machine", "longform-selftest", workspace)
    complete_step(state, state["steps"]["render"], {"status": "GREEN", "artifact": str(output), "duration": 30.0}, workspace, "machine", token=claim["claim_token"])
    actor = reviewer_actor(state["review_policy"])
    if actor != "human":
        raise AssertionError("long-form selftest expects the default human review policy")
    claim = claim_step(state, "visual-review", actor, "longform-selftest", workspace)
    complete_step(state, state["steps"]["visual-review"], {"review_id": "longform-fixture-1", "decision": "approved", "certified": False},
                  workspace, actor, token=claim["claim_token"])
    claim = claim_step(state, "outcome", "machine", "longform-selftest", workspace)
    complete_step(state, state["steps"]["outcome"], {"status": "RECORDED", "eventFile": "event.json",
                  "handoff": {"planSha256": state["plan"]["plan_sha256"], "checkpoint": review_checkpoint(state["review_policy"])}},
                  workspace, "machine", token=claim["claim_token"])
    write_json_atomic(run / STATE_NAME, state)
    report = verify_run(state, workspace)
    if state["status"] != "completed_approved" or report["status"] != "GREEN" or report["completed_steps"] != report["total_steps"]:
        raise AssertionError(report)
    return {"selftest": "GREEN", "completed_steps": report["completed_steps"], "chapters": 2, "one_set_apply": True,
            "one_render": True, "beat_outside_range_rejected": True, "interrupted_set_apply_requires_reconcile": True}

