"""Public receipt integrity/binding only; Editkin alone authenticates issuerProof."""
import copy, hashlib, json, math, os
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path
from workflow_state import WorkflowError, CURRENT_PLAN_SCHEMA, require_mapping, require_sha, read_json, plan_sha256, within_workspace

def sha256_json(value):
    from workflow_json import json_sha256
    try: return json_sha256(value, canonical=True)
    except ValueError as error: raise WorkflowError(str(error)) from error

def validate_audit_binding(state, value):
    receipt = require_mapping(value, "auditReceipt")
    fields = {"schema", "status", "planSchema", "planSha256", "project", "invocation", "materialEvidenceSha256", "auditedAt", "receiptSha256", "issuerProof"}
    if set(receipt) != fields or receipt.get("schema") != "hao.video-autopilot.audit-receipt/v1" or receipt.get("status") != "ACCEPTED" or receipt.get("planSchema") != CURRENT_PLAN_SCHEMA:
        raise WorkflowError("Unsupported auditReceipt shape")
    for field in ("planSha256", "materialEvidenceSha256", "receiptSha256", "issuerProof"): require_sha(receipt.get(field), field)
    if receipt["planSha256"] != state["plan"]["plan_sha256"]: raise WorkflowError("Audit plan binding mismatch")
    base = {key: val for key, val in receipt.items() if key not in {"receiptSha256", "issuerProof"}}
    if sha256_json(base) != receipt["receiptSha256"]: raise WorkflowError("Audit public checksum mismatch")
    try: timestamp = datetime.fromisoformat(receipt["auditedAt"].replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError): raise WorkflowError("Invalid audit timestamp")
    if timestamp.tzinfo is None: raise WorkflowError("Audit timestamp requires timezone")
    age = (datetime.now(timezone.utc) - timestamp).total_seconds()
    if age < -5 or age >= 600: raise WorkflowError("Audit expired/future; re-audit required")
    workspace = Path(state["workspace"])
    path = within_workspace(workspace, state["binding"]["project_path"], must_exist=True)
    project = read_json(path)
    normalized = str(path).lower() if os.name == "nt" else str(path)
    expected = {"id": project.get("id"), "revision": project.get("revision"), "pathSha256": hashlib.sha256(normalized.encode()).hexdigest(), "contentSha256": sha256_json(project)}
    if receipt["project"] != expected or not expected["id"] or type(expected["revision"]) is not int or expected["revision"] < 0:
        raise WorkflowError("Audit project identity mismatch")
    invocation = require_mapping(receipt["invocation"], "audit invocation")
    if set(invocation) != {"schema", "skill", "workflow", "knowledge", "plugins", "bindingSha256"} or invocation.get("schema") != "editkin.video-autopilot.live-identity/v1": raise WorkflowError("Invalid audit invocation")
    shapes = {
        "skill": ({"id": "video-autopilot"}, {"revision": 0, "hardRuleCount": 1}, {"sha256"}),
        "workflow": ({"schema": "hao.video-autopilot.workflow-contract/v1", "planSchema": CURRENT_PLAN_SCHEMA, "legacyPlanPolicy": "reject"}, {"revision": 1}, {"sha256"}),
        "knowledge": ({"schema": "editkin.community-knowledge/v1"}, {"revision": 1, "includedModuleCount": 1, "stableRuleCount": 1}, {"packSha256", "stableRulesSha256"}),
        "plugins": ({"schema": "editkin.plugin-registry-identity/v1"}, {"pluginCount": 0, "diagnosticCount": 0}, {"sha256"}),
    }
    for name, (literals, integers, hashes) in shapes.items():
        part = require_mapping(invocation.get(name), name)
        if set(part) != set(literals) | set(integers) | hashes: raise WorkflowError("Invalid audit identity fields: " + name)
        for key, value in literals.items():
            if part[key] != value: raise WorkflowError("Invalid audit identity literal: " + key)
        for key, minimum in integers.items():
            if type(part[key]) is not int or not minimum <= part[key] <= 9007199254740991: raise WorkflowError("Invalid audit identity integer: " + key)
        for key in hashes: require_sha(part[key], key)
    if sha256_json({key: val for key, val in invocation.items() if key != "bindingSha256"}) != require_sha(invocation.get("bindingSha256"), "invocation binding"):
        raise WorkflowError("Audit invocation checksum mismatch")
    plan = read_json(within_workspace(workspace, state["plan"]["artifact"], must_exist=True))
    source = require_mapping(plan.get("source"), "plan source")
    mappings = {"skillSha256": ("skill", "sha256"), "revision": ("skill", "revision"), "workflowContractRevision": ("workflow", "revision"), "workflowContractSha256": ("workflow", "sha256"), "knowledgeRevision": ("knowledge", "revision"), "knowledgeSha256": ("knowledge", "packSha256"), "stableRulesSha256": ("knowledge", "stableRulesSha256"), "pluginRegistrySha256": ("plugins", "sha256")}
    for field, (section, key) in mappings.items():
        if field not in source or source[field] != require_mapping(invocation.get(section), section).get(key): raise WorkflowError("Audit source binding mismatch: " + field)
    if source.get("invocationBindingSha256") != invocation["bindingSha256"] or invocation["workflow"].get("sha256") != state["contract"]["sha256"] or invocation["skill"].get("sha256") != state["governance"]["skill_sha256"]:
        raise WorkflowError("Audit current workflow/skill binding mismatch")
    if sha256_json(plan.get("materialEvidence")) != receipt["materialEvidenceSha256"]:
        raise WorkflowError("Audit material evidence mismatch")
    return copy.deepcopy(receipt)
