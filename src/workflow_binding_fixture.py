"""Synthetic unsigned test fixture. Never a real MCP audit/apply receipt."""
import hashlib, os
from datetime import datetime, timezone
from pathlib import Path
from workflow_primitives import sha256_json, plan_sha256, read_json, within_workspace
from workflow_audit_binding import sha256_json
from engine_continuity import engine_continuity_sha256

def fixture_engine(state):
    """Synthetic declaration only; never actual runtime or art evidence."""
    from copy import deepcopy
    runtime = deepcopy(state["binding"]["engine_continuity"]["floor"])
    runtime["projectSchemas"] = [9, 10]
    return runtime

def fixture_live_invocation(state, runtime=None):
    runtime = fixture_engine(state) if runtime is None else runtime
    identity = {"schema": "editkin.video-autopilot.live-identity/v1",
        "skill": {"id": "video-autopilot", "revision": 999, "sha256": state["governance"]["skill_sha256"], "hardRuleCount": 1},
        "workflow": {"schema": "hao.video-autopilot.workflow-contract/v1", "revision": 6, "sha256": state["contract"]["sha256"], "planSchema": "hao.video-autopilot.edit-plan/v4", "legacyPlanPolicy": "reject"},
        "knowledge": {"schema": "editkin.community-knowledge/v1", "revision": 1, "packSha256": "a"*64, "stableRulesSha256": "b"*64, "includedModuleCount": 1, "stableRuleCount": 1},
        "plugins": {"schema": "editkin.plugin-registry-identity/v1", "sha256": "c"*64, "pluginCount": 0, "diagnosticCount": 0},
        "engine": {"schema": "editkin.engine-continuity-pin/v1", "sha256": engine_continuity_sha256(runtime)}}
    identity["bindingSha256"] = sha256_json(identity)
    return identity

def fixture_audit(state, plan):
    identity = fixture_live_invocation(state)
    plan["source"].update({"skillId": "video-autopilot", "revision": 999, "skillSha256": identity["skill"]["sha256"], "workflowContractRevision": 6, "workflowContractSha256": identity["workflow"]["sha256"], "knowledgeRevision": 1, "knowledgeSha256": "a"*64, "stableRulesSha256": "b"*64, "pluginRegistrySha256": "c"*64, "invocationBindingSha256": identity["bindingSha256"]})
    path = within_workspace(Path(state["workspace"]), state["binding"]["project_path"], must_exist=True)
    project = read_json(path)
    normalized = str(path).lower() if os.name == "nt" else str(path)
    receipt = {"schema": "hao.video-autopilot.audit-receipt/v1", "status": "ACCEPTED", "planSchema": plan["schema"], "planSha256": plan_sha256(plan), "project": {"id": project["id"], "revision": project["revision"], "pathSha256": hashlib.sha256(normalized.encode()).hexdigest(), "contentSha256": sha256_json(project)}, "invocation": identity, "materialEvidenceSha256": sha256_json(plan["materialEvidence"]), "auditedAt": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")}
    receipt["receiptSha256"] = sha256_json(receipt)
    receipt["issuerProof"] = "0"*64
    return {"status": "ACCEPTED", "planSha256": receipt["planSha256"], "coverage": {"legacy": False}, "commandCount": 3, "auditReceipt": receipt}
