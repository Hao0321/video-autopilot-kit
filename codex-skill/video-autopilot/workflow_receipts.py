from __future__ import annotations

import hashlib, json, math, re, secrets, sys
from pathlib import Path
from typing import Any

from workflow_state import (CURRENT_PLAN_SCHEMA, RECEIPT_SCHEMA, WorkflowError, add_event, plan_sha256, project_file, read_json, relative_path, require_list, require_mapping, require_sha, sha256_file, sha256_json, step_material, utc_now, verify_immutable_sources, verify_project_binding, within_workspace, write_json_atomic)
from workflow_material_receipts import prepared_facts, receipt_for, semantic_facts, validate_material_payload
from workflow_transport import normalize_step_submission


def receipt_payload(raw: str) -> dict[str, Any]:
    if raw == "-":
        return require_mapping(json.load(sys.stdin), "receipt payload")
    if raw.lstrip().startswith("{"):
        return require_mapping(json.loads(raw), "receipt payload")
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise WorkflowError(f"Receipt JSON does not exist: {path}")
    return require_mapping(read_json(path), "receipt payload")

def _status(payload: dict[str, Any], allowed: set[str] | None = None) -> str:
    value = str(payload.get("status", "")).upper()
    permitted = allowed or {"GREEN"}
    if value not in permitted:
        raise WorkflowError(f"Receipt status {value or '<missing>'} is not one of {sorted(permitted)}")
    return value


def _contract(payload: dict[str, Any]) -> dict[str, Any]:
    _status(payload)
    contract = require_mapping(payload.get("contract"), "get_autopilot_contract.contract")
    policy = require_mapping(contract.get("sourcePolicy"), "get_autopilot_contract.contract.sourcePolicy")
    if (contract.get("schemaVersion") != 3 or contract.get("planSchema") != CURRENT_PLAN_SCHEMA
            or not str(contract.get("productVersion", "")).strip()
            or policy.get("dynamicCanonicalSkill") is not True
            or policy.get("packagePrivateSkillOrMemory") is not False):
        raise WorkflowError("Editkin contract is downgraded or does not enforce the canonical v4 source policy")
    return {"schema_version": 3, "plan_schema": CURRENT_PLAN_SCHEMA,
            "product_version": str(contract["productVersion"]), "legacy_schemas": contract.get("legacyPlanSchemas", []),
            "dynamic_canonical_skill": True, "package_private_skill_or_memory": False}


def _session(state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    _status(payload)
    workflow = [str(item) for item in require_list(payload.get("workflow"), "session.workflow")]
    required = {"prepare_ai_material", "view_material_keyframes", "get_material_context",
                "record_material_semantics", "resolve_autopilot_inference_route",
                "audit_autopilot_plan", "apply_autopilot_plan", "render_project"}
    if not required.issubset(workflow):
        raise WorkflowError(f"Editkin session workflow is missing tools: {sorted(required - set(workflow))}")
    clips = require_list(payload.get("clips"), "session.clips")
    available = {str(item.get("clipId")) for item in clips if isinstance(item, dict)}
    expected = {item["clip_id"] for item in state["binding"]["materials"]}
    if not expected.issubset(available):
        raise WorkflowError(f"Session is missing bound clips: {sorted(expected - available)}")
    return {"clip_count": len(clips), "workflow": workflow}


def _issued_request(step: dict[str, Any]) -> dict[str, Any]:
    claim = require_mapping(step.get("claim"), "active claim")
    instruction = require_mapping(claim.get("instruction"), "claim instruction")
    request = require_mapping(instruction.get("request"), "claim request")
    if sha256_json(request) != claim.get("request_sha256"):
        raise WorkflowError("Claim request provenance hash is corrupt")
    return request


def _route(state: dict[str, Any], step: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    _status(payload)
    route = require_mapping(payload.get("route"), "inference route")
    context = require_mapping(payload.get("context"), "inference route context")
    request = _issued_request(step)
    expected = state["inference_request"]
    if request != {"taskClass": expected["task_class"], "priority": expected["priority"]}:
        raise WorkflowError("Inference route request does not match the run binding")
    if context.get("protocol") != "markdown-router+json-contract/v1" or not isinstance(context.get("markdown"), str):
        raise WorkflowError("Inference route is missing the bounded Markdown protocol")
    router_sha = require_sha(context.get("markdownRouterSha256"), "markdownRouterSha256")
    if hashlib.sha256(context["markdown"].encode("utf-8")).hexdigest() != router_sha:
        raise WorkflowError("Inference Markdown router hash does not match its content")
    return {"task_class": state["inference_request"]["task_class"], "priority": state["inference_request"]["priority"],
            "markdown_router_sha256": router_sha,
            "second_pass_required": bool(route.get("secondPassRequired", False)), "execution_mode": route.get("executionMode")}


def _plugins(step: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    request = _issued_request(step)
    if request.get("automationReadyOnly") is not True:
        raise WorkflowError("Plugin discovery request was not automationReadyOnly=true")
    if str(payload.get("status", "GREEN")).upper() not in {"GREEN", "EMPTY"}:
        raise WorkflowError("Plugin discovery did not complete successfully")
    plugins = require_list(payload.get("plugins", []), "plugin discovery.plugins")
    candidates: list[dict[str, str]] = []
    for plugin in plugins:
        plugin = require_mapping(plugin, "plugin")
        for capability in require_list(plugin.get("capabilities", []), "plugin.capabilities"):
            capability = require_mapping(capability, "plugin capability")
            if capability.get("automationReady") is not True or str(capability.get("readiness", "")).upper() != "AUTOMATION_READY":
                raise WorkflowError("Only AUTOMATION_READY plugin capabilities may enter candidates")
            candidates.append({"plugin_id": str(plugin.get("id", "")), "capability_id": str(capability.get("id", ""))})
    return {"plugin_count": len(plugins), "candidate_count": len(candidates), "verified_candidates": candidates, "invoked": False}


def _artifact(workspace: Path, raw: Any, label: str, suffix: str) -> Path:
    if not raw:
        raise WorkflowError(f"{label} artifact path is required")
    path = within_workspace(workspace, str(raw), must_exist=True)
    if not path.is_file() or path.suffix.lower() != suffix:
        raise WorkflowError(f"{label} artifact must be an existing {suffix} file")
    return path


def _plugin_references(value: Any) -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    if isinstance(value, dict):
        if "pluginId" in value and "capabilityId" in value:
            found.add((str(value["pluginId"]), str(value["capabilityId"])))
        for item in value.values(): found.update(_plugin_references(item))
    elif isinstance(value, list):
        for item in value: found.update(_plugin_references(item))
    return found


def _plan(state: dict[str, Any], workspace: Path, payload: dict[str, Any]) -> dict[str, Any]:
    artifact = _artifact(workspace, payload.get("artifact"), "plan", ".json")
    plan = require_mapping(read_json(artifact), "autopilot plan")
    if plan.get("schema") != CURRENT_PLAN_SCHEMA:
        raise WorkflowError("Legacy autopilot plans are forbidden; only edit-plan/v4 may continue")
    source = require_mapping(plan.get("source"), "plan.source")
    if require_sha(source.get("skillSha256"), "plan source.skillSha256") != state["governance"]["skill_sha256"]:
        raise WorkflowError("Plan was generated from a different video-autopilot skill hash")
    evidence = require_mapping(plan.get("materialEvidence"), "plan.materialEvidence")
    if evidence.get("schema") != "hao.editkin.material-intelligence/v1":
        raise WorkflowError("v4 plan is missing current material intelligence evidence")
    receipts = require_list(evidence.get("receipts"), "plan.materialEvidence.receipts")
    expected = []
    for material in state["binding"]["materials"]:
        facts = semantic_facts(state, material)
        expected.append({"materialId": facts["material_id"], "sourceSha256": facts["source_sha256"],
                         "assetId": facts["asset_id"], "clipId": facts["clip_id"],
                         "semanticReceiptSha256": facts["semantic_receipt_sha256"]})
    ids = [str(item.get("materialId", "")) for item in receipts if isinstance(item, dict)]
    if len(ids) != len(receipts) or len(set(ids)) != len(ids):
        raise WorkflowError("Plan materialEvidence contains invalid or duplicate material IDs")
    key = lambda item: str(item["materialId"])
    if sorted(receipts, key=key) != sorted(expected, key=key):
        raise WorkflowError("Plan materialEvidence does not exactly match completed semantic receipts")
    plugin_facts = require_mapping(receipt_for(state, "plugin-discovery").get("facts"), "plugin receipt facts")
    verified = {(item["plugin_id"], item["capability_id"]) for item in plugin_facts["verified_candidates"]}
    unverified = _plugin_references(plan) - verified
    if unverified:
        raise WorkflowError(f"Plan references unverified plugin capabilities: {sorted(unverified)}")
    route = require_mapping(receipt_for(state, "route").get("facts"), "route receipt facts")
    inference = require_mapping(plan.get("inference"), "plan.inference")
    if require_mapping(inference.get("context"), "plan.inference.context").get("markdownRouterSha256") != route["markdown_router_sha256"]:
        raise WorkflowError("Plan inference router hash does not match route receipt")
    computed_sha = plan_sha256(plan)
    if require_sha(payload.get("plan_sha256"), "plan_sha256") != computed_sha:
        raise WorkflowError("Submitted planSha256 does not match JSON.stringify(plan)")
    return {"plan_schema": CURRENT_PLAN_SCHEMA, "plan_sha256": computed_sha,
            "artifact": relative_path(workspace, artifact), "artifact_sha256": sha256_file(artifact),
            "knowledge_sha256": require_sha(source.get("knowledgeSha256"), "plan source.knowledgeSha256"),
            "material_receipt_count": len(receipts)}


def _audit(state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    _status(payload)
    plan_sha = require_sha(payload.get("planSha256"), "audit planSha256")
    if state["plan"]["schema"] != CURRENT_PLAN_SCHEMA or plan_sha != state["plan"]["plan_sha256"]:
        raise WorkflowError("Audit receipt is not for the bound v4 plan")
    coverage = require_mapping(payload.get("coverage"), "audit.coverage")
    count = int(payload.get("commandCount", 0))
    if coverage.get("legacy") is not False or count < 1:
        raise WorkflowError("Legacy or empty audit cannot enter apply")
    return {"plan_sha256": plan_sha, "command_count": count, "legacy": False}


def _apply(state: dict[str, Any], workspace: Path, payload: dict[str, Any]) -> dict[str, Any]:
    _status(payload, {"REVIEW_REQUIRED"})
    receipt = require_mapping(payload.get("receipt"), "apply.receipt")
    if receipt.get("planSchema") != CURRENT_PLAN_SCHEMA or require_sha(receipt.get("planSha256"), "apply planSha256") != state["plan"]["plan_sha256"]:
        raise WorkflowError("Apply receipt is not for the bound v4 plan")
    if not receipt.get("receiptId") or not receipt.get("committedAt") or not receipt.get("receiptFile") or receipt.get("state") not in {None, "committed"}:
        raise WorkflowError("Apply receipt is not committed")
    quality = require_mapping(receipt.get("quality"), "apply receipt.quality")
    if quality.get("outputState") != "review_required" or quality.get("certified") is not False:
        raise WorkflowError("Apply must remain review_required and uncertified")
    before, after = receipt.get("projectRevisionBefore"), receipt.get("projectRevisionAfter")
    if not isinstance(before, int) or not isinstance(after, int) or after != before + 1:
        raise WorkflowError("Apply receipt must advance the Editkin project by exactly one revision")
    project = project_file(state, workspace)
    actual_sha = sha256_file(project)
    if actual_sha == state["binding"]["project_current_sha256"] or read_json(project).get("revision") != after:
        raise WorkflowError("Local Editkin project does not prove the committed post-apply revision")
    receipt_path = project.parent / ".editkin-receipts" / str(receipt["receiptFile"])
    if not receipt_path.is_file():
        raise WorkflowError("Committed Editkin receipt file is missing")
    committed = require_mapping(read_json(receipt_path), "committed Editkin receipt file")
    if committed.get("state") != "committed" or committed.get("receiptId") != receipt["receiptId"] or committed.get("planSha256") != state["plan"]["plan_sha256"] or committed.get("projectRevisionAfter") != after:
        raise WorkflowError("Committed Editkin receipt file does not match the tool response")
    return {"plan_sha256": state["plan"]["plan_sha256"], "receipt_id": str(receipt["receiptId"]),
            "receipt_file": str(receipt["receiptFile"]), "project_revision_before": before,
            "project_revision_after": after, "committed_at": str(receipt["committedAt"]), "certified": False}


def _render(state: dict[str, Any], workspace: Path, payload: dict[str, Any]) -> dict[str, Any]:
    _status(payload, {"GREEN", "RENDERED", "COMPLETE", "COMPLETED"})
    path = _artifact(workspace, payload.get("artifact") or payload.get("outputPath") or payload.get("path") or payload.get("file"), "render", ".mp4")
    if path != within_workspace(workspace, state["binding"]["output_path"]):
        raise WorkflowError("Render artifact does not match bound output path")
    duration = float(payload.get("duration", 0))
    if path.stat().st_size <= 0 or not math.isfinite(duration) or duration <= 0:
        raise WorkflowError("Render must have non-zero bytes and positive probed duration")
    apply = require_mapping(receipt_for(state, "apply").get("facts"), "apply receipt facts")
    return {"artifact": relative_path(workspace, path), "artifact_sha256": sha256_file(path), "bytes": path.stat().st_size, "duration": duration,
            "plan_sha256": state["plan"]["plan_sha256"], "apply_receipt_id": apply["receipt_id"]}


def _review(payload: dict[str, Any], actor: str) -> dict[str, Any]:
    if actor != "human" or payload.get("certified") not in {None, False}:
        raise WorkflowError("Human review requires a human actor and certified=false")
    decision = str(payload.get("decision", ""))
    review_id = str(payload.get("review_id", "")).strip()
    if decision not in {"approved", "changes_requested", "rejected"} or not review_id:
        raise WorkflowError("Human review requires review_id and a valid decision")
    return {"review_id": review_id, "decision": decision, "certified": False, "notes": str(payload.get("notes", ""))}


def _outcome(state: dict[str, Any], step: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    _status(payload, {"RECORDED"})
    review = require_mapping(receipt_for(state, "human-review").get("facts"), "human review facts")
    if payload.get("review_id") not in {None, review["review_id"]} or not str(payload.get("eventFile", "")).strip():
        raise WorkflowError("Outcome does not bind the completed human review or immutable eventFile")
    handoff = require_mapping(payload.get("handoff"), "outcome.handoff")
    request = _issued_request(step)
    outcome = require_mapping(request.get("outcome"), "record_autopilot_outcome request.outcome")
    if request.get("projectPath") != state["binding"]["project_path"] or outcome.get("schema") != "hao.video-autopilot.learning-event/v1":
        raise WorkflowError("Outcome request does not bind the Editkin project and learning-event/v1")
    if outcome.get("planSha256") != state["plan"]["plan_sha256"] or outcome.get("checkpoint") != "human_review":
        raise WorkflowError("Outcome request does not bind the applied plan and human-review checkpoint")
    render_sha = receipt_for(state, "render")["facts"]["artifact_sha256"]
    if outcome.get("artifactId") != render_sha or outcome.get("review", {}).get("accepted") != (review["decision"] == "approved"):
        raise WorkflowError("Outcome request does not bind the reviewed render and decision")
    if require_sha(handoff.get("planSha256"), "outcome planSha256") != state["plan"]["plan_sha256"] or handoff.get("checkpoint") != "human_review":
        raise WorkflowError("Outcome handoff does not reference the applied plan")
    return {"event_file": str(payload["eventFile"]), "review_id": review["review_id"], "decision": review["decision"],
            "human_review_receipt_sha256": state["steps"]["human-review"]["receipt"]["file_sha256"]}


def validate_payload(state: dict[str, Any], step: dict[str, Any], payload: dict[str, Any], transport: dict[str, Any], workspace: Path, actor: str) -> dict[str, Any]:
    template = step["template_id"]
    if template in {"prepare:{material}", "keyframes:{material}", "context:{material}", "semantics:{material}"}:
        return validate_material_payload(state, step, payload, transport)
    validators = {"contract": lambda: _contract(payload), "session": lambda: _session(state, payload),
                  "route": lambda: _route(state, step, payload), "plugin-discovery": lambda: _plugins(step, payload),
                  "plan": lambda: _plan(state, workspace, payload), "audit": lambda: _audit(state, payload),
                  "apply": lambda: _apply(state, workspace, payload), "render": lambda: _render(state, workspace, payload),
                  "human-review": lambda: _review(payload, actor), "outcome": lambda: _outcome(state, step, payload)}
    if template not in validators:
        raise WorkflowError(f"No receipt validator for step template {template}")
    return validators[template]()


def claim_token_valid(step: dict[str, Any], token: str) -> bool:
    expected = str((step.get("claim") or {}).get("token_sha256", ""))
    return secrets.compare_digest(expected, hashlib.sha256(token.encode("utf-8")).hexdigest())


def terminal_state(decision: str) -> str:
    return {"approved": "completed_approved", "changes_requested": "changes_requested",
            "rejected": "rejected"}.get(decision, "rejected")


def complete_step(state: dict[str, Any], step: dict[str, Any], payload: dict[str, Any], workspace: Path,
                  actor: str, *, token: str | None, reconciled: bool = False) -> dict[str, Any]:
    if not reconciled:
        if step["status"] != "running" or token is None or not claim_token_valid(step, token):
            raise WorkflowError("Step is not running under this claim token")
    elif step["status"] != "reconcile_required":
        raise WorkflowError("Only reconcile_required steps can be reconciled as committed")
    if step["required_actor"] != actor:
        raise WorkflowError(f"Step {step['id']} requires actor type {step['required_actor']}")
    submission = payload
    response, transport, durable_submission = normalize_step_submission(step["template_id"], submission)
    facts = validate_payload(state, step, response, transport, workspace, actor)
    if step["template_id"] == "plan":
        state["plan"] = {"schema": facts["plan_schema"], "plan_sha256": facts["plan_sha256"],
                         "artifact": facts["artifact"], "artifact_sha256": facts["artifact_sha256"]}
    claim = step.get("claim") or {}
    instruction = claim.get("instruction") or {}
    envelope = {
        "schema": RECEIPT_SCHEMA, "run_id": state["run_id"], "step_id": step["id"], "tool": step["tool"],
        "binding_sha256": state["binding"]["binding_sha256"], "source_set_sha256": state["binding"]["source_set_sha256"],
        "plan_sha256": state["plan"]["plan_sha256"], "actor_type": actor, "attempt": step["attempts"],
        "claim_token_sha256": claim.get("token_sha256"), "instruction_sha256": claim.get("instruction_sha256"),
        "request": instruction.get("request"), "request_sha256": claim.get("request_sha256"),
        "transport": transport, "submission_sha256": sha256_json(durable_submission), "submission": durable_submission,
        "payload_sha256": sha256_json(response), "payload": response, "facts": facts,
        "completed_at": utc_now(), "reconciled": reconciled,
    }
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", step["id"])
    path = Path(state["run_dir"]) / "receipts" / f"{safe}.json"
    write_json_atomic(path, envelope)
    step.update({"status": "completed", "claim": None, "last_error": None,
                 "receipt": {"path": path.relative_to(Path(state["run_dir"])).as_posix(),
                             "file_sha256": sha256_file(path), "payload_sha256": envelope["payload_sha256"],
                             "completed_at": envelope["completed_at"]}})
    if step["template_id"] == "apply":
        state["binding"]["project_current_sha256"] = sha256_file(project_file(state, workspace))
    elif step["template_id"] == "human-review":
        state["review"] = facts
    elif step["template_id"] == "outcome":
        decision = str((state.get("review") or {}).get("decision", "rejected"))
        state["status"] = terminal_state(decision)
    add_event(state, "step_completed", {"step": step["id"], "receipt": step["receipt"]["path"], "reconciled": reconciled})
    return {"step": step["id"], "status": "completed", "receipt": step["receipt"], "facts": facts}


def verify_run(state: dict[str, Any], workspace: Path) -> dict[str, Any]:
    sources = verify_immutable_sources(state, workspace, full=True)
    project_sha = verify_project_binding(state, workspace, allow_inflight_apply=True)
    errors: list[str] = []
    for step in state["steps"].values():
        if step["status"] != "completed":
            continue
        missing = [item for item in step["depends_on"] if state["steps"][item]["status"] != "completed"]
        if missing:
            errors.append(f"{step['id']} completed before dependencies {missing}")
        try:
            envelope = receipt_for(state, step["id"])
            for key, expected in (("run_id", state["run_id"]), ("binding_sha256", state["binding"]["binding_sha256"]),
                                  ("source_set_sha256", state["binding"]["source_set_sha256"])):
                if envelope.get(key) != expected:
                    errors.append(f"{step['id']} receipt {key} mismatch")
            if step["order"] >= state["steps"]["plan"]["order"] and envelope.get("plan_sha256") != state["plan"]["plan_sha256"]:
                errors.append(f"{step['id']} receipt plan_sha256 mismatch")
            if sha256_json(envelope.get("payload")) != envelope.get("payload_sha256"):
                errors.append(f"{step['id']} receipt payload hash mismatch")
            if sha256_json(envelope.get("submission")) != envelope.get("submission_sha256"):
                errors.append(f"{step['id']} receipt submission hash mismatch")
            if envelope.get("tool") != step["tool"] or sha256_json(envelope.get("request")) != envelope.get("request_sha256"):
                errors.append(f"{step['id']} receipt tool/request provenance mismatch")
        except (OSError, ValueError, WorkflowError, json.JSONDecodeError) as error:
            errors.append(f"{step['id']} receipt invalid: {error}")
    if state["steps"]["human-review"]["status"] == "completed":
        envelope = receipt_for(state, "human-review")
        if envelope.get("actor_type") != "human" or envelope.get("facts", {}).get("certified") is not False:
            errors.append("human-review is not a human, uncertified receipt")
    if state["plan"]["schema"] not in {None, CURRENT_PLAN_SCHEMA}:
        errors.append("state contains a legacy plan schema")
    if any(step["status"] == "reconcile_required" for step in state["steps"].values()):
        errors.append("workflow has an unresolved atomic mutation")
    return {"status": "GREEN" if not errors else "RED", "errors": errors, "source_files": sources,
            "project_sha256": project_sha, "completed_steps": sum(step["status"] == "completed" for step in state["steps"].values()),
            "total_steps": len(state["steps"]),
            "reconcile_required": [step["id"] for step in state["steps"].values() if step["status"] == "reconcile_required"]}
