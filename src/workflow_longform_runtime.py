"""One-timeline long-form contract, plan-set validation and execution instructions.

Only runs created with `workflow_contract.py create-longform` import this module
(lazily); revision-6 `create` runs never load it. Revision 6
(`workflow_contract.json`) stays the bound execution contract with identical
bytes, because Editkin seals its hash into every chapter plan. The session DAG
comes from `workflow_longform_contract.json` (revision 1): one sealed
edit-plan/v4 per chapter against the same base project, a local deterministic
plan-set seal, one atomic `apply_longform_plan_set` and the existing single
`render_project`.

Editkin alone authenticates issuerProof, single use and TTL. Like
workflow_audit_binding, this module checks only public shape and the binding to
this run. Synthetic fixtures and the selftest live in workflow_longform.py.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workflow_json import json_sha256
from workflow_primitives import (CURRENT_PLAN_SCHEMA, WorkflowError, _artifact, _plugin_references, plan_sha256, project_file,
                                 read_json, relative_path, require_list, require_mapping, require_sha, sha256_file,
                                 sha256_json, verify_project_binding, within_workspace)
from workflow_contract_source import load_contract, resolve_canonical_skill
from workflow_chapter_contract import (chapter_for, chapter_plan_path, plan_set_path, expected_chapter_receipts,
                                       _refused_command, chapter_frame_violations)

CONTRACT_NAME = "workflow_longform_contract.json"
SEAL_TOOL, AUDIT_TOOL, APPLY_TOOL = "seal_longform_plan_set", "audit_longform_plan_set", "apply_longform_plan_set"
CONTRACT_SCHEMA = "hao.video-autopilot.longform-session-contract/v1"
SESSION_SCHEMA = "hao.video-autopilot.longform-session/v1"
SESSION_BINDING_SCHEMA = "hao.video-autopilot.longform-session-binding/v1"
PLAN_SET_SCHEMA = "hao.video-autopilot.longform-plan-set/v1"
AUDIT_RECEIPT_SCHEMA = "hao.video-autopilot.longform-audit-receipt/v1"
MATERIAL_EVIDENCE_SCHEMA = "hao.editkin.material-intelligence/v1"
LIMITS = {"chapters_max": 16, "session_material_count": 96, "per_plan_materials": 32}
# Editkin's set-receipt TTL is authoritative; the v1 session caps it at 20 minutes.
# This public check only rejects receipts older than that ceiling or from the future.
AUDIT_RECEIPT_MAX_AGE_SECONDS = 1200
SESSION_MAX_BYTES = 64 * 1024
CHAPTER_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?$")
AUDIT_RECEIPT_FIELDS = {"schema", "status", "setSha256", "project", "invocation", "chapters",
                        "auditedAt", "receiptSha256", "issuerProof"}
AUDIT_CHAPTER_FIELDS = {"chapterId", "planSha256", "materialEvidenceSha256", "range"}
SOURCE_BINDINGS = {"skillSha256": ("skill", "sha256"), "revision": ("skill", "revision"),
                   "workflowContractRevision": ("workflow", "revision"), "workflowContractSha256": ("workflow", "sha256"),
                   "knowledgeRevision": ("knowledge", "revision"), "knowledgeSha256": ("knowledge", "packSha256"),
                   "stableRulesSha256": ("knowledge", "stableRulesSha256"), "pluginRegistrySha256": ("plugins", "sha256")}


def _same(left: Any, right: Any) -> bool:
    """Type-exact JSON equality: 16 differs from 16.0 and from True."""
    return json.dumps(left, sort_keys=True, ensure_ascii=False) == json.dumps(right, sort_keys=True, ensure_ascii=False)


def _canonical(value: Any) -> str:
    try:
        return json_sha256(value, canonical=True)
    except ValueError as error:
        raise WorkflowError(str(error)) from error


# ---- revision-1 session contract and the create-longform session ----

def load_longform_contract(skill_path: Path | None = None) -> tuple[dict[str, Any], str]:
    """The revision-1 session contract beside the canonical SKILL.md; revision 6 must still load."""
    skill = skill_path.resolve() if skill_path else resolve_canonical_skill()[0]
    path = skill.with_name(CONTRACT_NAME)
    if not path.is_file():
        raise WorkflowError(f"LONGFORM_CONTRACT_MISSING: {path}; the bound Skill predates create-longform. "
                            "Update it to this kit (python src/release_manager.py install-skill) and start a new run")
    contract = require_mapping(read_json(path), "long-form session contract")
    if (contract.get("schema") != CONTRACT_SCHEMA or not _same(contract.get("revision"), 1)
            or not _same(contract.get("base_contract_revision"), 6) or contract.get("session_schema") != SESSION_SCHEMA
            or contract.get("plan_set_schema") != PLAN_SET_SCHEMA or contract.get("audit_receipt_schema") != AUDIT_RECEIPT_SCHEMA
            or contract.get("plan_set_hash_algorithm") != "sha256-canonical-json-utf8-keys-v1"):
        raise WorkflowError("LONGFORM_CONTRACT_INVALID: unsupported long-form session contract identity")
    if not _same(contract.get("limits"), LIMITS):
        raise WorkflowError("LONGFORM_CONTRACT_INVALID: v1 caps are 16 chapters, 96 session materials and 32 per plan")
    base, _ = load_contract(skill)
    templates = [require_mapping(item, "long-form step") for item in require_list(contract.get("steps"), "long-form steps")]
    steps = {str(item.get("id")): item for item in templates}
    expected = ({str(item["id"]) for item in base["steps"]} - {"original:{source}"}) | {"plan:{chapter}"}
    if set(steps) != expected or len(steps) != len(templates):
        raise WorkflowError("LONGFORM_CONTRACT_INVALID: steps must keep the revision-6 ids plus plan:{chapter}")
    renders = [item for item in templates if item.get("tool") in {"render_project", "render_original_motion_project"}]
    chapter = steps["plan:{chapter}"]
    if (chapter.get("fanout") != "chapters" or chapter.get("tool") != "write_v4_plan"
            or any(item.get("fanout") == "chapters" for item in templates if item is not chapter)
            or steps["plan"].get("tool") != SEAL_TOOL or steps["plan"].get("depends_on") != ["plan:*"]
            or steps["audit"].get("tool") != AUDIT_TOOL or steps["apply"].get("tool") != APPLY_TOOL
            or steps["apply"].get("retry") != "reconcile_only" or steps["apply"].get("atomic") is not True
            or len(renders) != 1 or renders[0].get("id") != "render" or renders[0].get("tool") != "render_project"
            or renders[0].get("depends_on") != ["apply"]):
        raise WorkflowError("LONGFORM_CONTRACT_INVALID: the set must audit and apply once and render once, with no per-chapter render")
    capability = require_mapping(contract.get("editkin_capability"), "long-form Editkin capability")
    if capability.get("key") != "longformPlanSet" or capability.get("schema") != PLAN_SET_SCHEMA:
        raise WorkflowError("LONGFORM_CONTRACT_INVALID: unexpected Editkin capability declaration")
    return contract, sha256_json(contract)


def parse_session(value: Any, materials: list[dict[str, Any]], limits: dict[str, Any] = LIMITS) -> list[dict[str, Any]]:
    """1..16 slug chapters with ordered, disjoint integer [startFrame, endFrame) ranges over bound clips."""
    session = require_mapping(value, "long-form session")
    if set(session) != {"schema", "chapters"} or session["schema"] != SESSION_SCHEMA:
        raise WorkflowError(f"LONGFORM_SESSION_INVALID: a session is exactly {{schema: {SESSION_SCHEMA}, chapters}}")
    rows = require_list(session["chapters"], "long-form session chapters")
    if not 1 <= len(rows) <= limits["chapters_max"]:
        raise WorkflowError(f"LONGFORM_SESSION_CHAPTER_COUNT: a session needs 1..{limits['chapters_max']} chapters")
    by_clip = {item["clip_id"]: item["key"] for item in materials}
    chapters: list[dict[str, Any]] = []
    previous_end: int | None = None
    for row in rows:
        row = require_mapping(row, "long-form chapter")
        if set(row) != {"chapterId", "range", "clipIds"}:
            raise WorkflowError("LONGFORM_SESSION_INVALID: a chapter is exactly {chapterId, range, clipIds}")
        chapter_id = row["chapterId"]
        if not isinstance(chapter_id, str) or not CHAPTER_ID_RE.fullmatch(chapter_id):
            raise WorkflowError(f"LONGFORM_SESSION_CHAPTER_ID: chapterId must be a 1..32 character slug: {chapter_id!r}")
        if any(item["key"] == chapter_id for item in chapters):
            raise WorkflowError(f"LONGFORM_SESSION_CHAPTER_ID: duplicate chapterId {chapter_id}")
        frame_range = require_mapping(row["range"], f"chapter {chapter_id} range")
        start, end = frame_range.get("startFrame"), frame_range.get("endFrame")
        if set(frame_range) != {"startFrame", "endFrame"} or type(start) is not int or type(end) is not int or not 0 <= start < end:
            raise WorkflowError(f"LONGFORM_SESSION_RANGE: chapter {chapter_id} needs integer frames 0 <= startFrame < endFrame")
        if previous_end is not None and start < previous_end:
            raise WorkflowError(f"LONGFORM_SESSION_RANGE: chapter {chapter_id} overlaps or precedes the previous chapter")
        clips = require_list(row["clipIds"], f"chapter {chapter_id} clipIds")
        if (not 1 <= len(clips) <= limits["per_plan_materials"] or len(set(map(str, clips))) != len(clips)
                or any(not isinstance(clip, str) or not clip for clip in clips)):
            raise WorkflowError(f"LONGFORM_SESSION_CLIPS: chapter {chapter_id} needs 1..{limits['per_plan_materials']} unique clipIds")
        unknown = [clip for clip in clips if clip not in by_clip]
        if unknown:
            raise WorkflowError(f"LONGFORM_SESSION_CLIPS: chapter {chapter_id} names clips that are not bound materials: {unknown}")
        chapters.append({"key": chapter_id, "range": {"startFrame": start, "endFrame": end},
                         "clip_ids": list(clips), "material_keys": [by_clip[clip] for clip in clips]})
        previous_end = end
    return chapters


def bind_session(workspace: Path, raw_path: str | os.PathLike[str], materials: list[dict[str, Any]], *,
                 skill_path: Path | None = None) -> dict[str, Any]:
    contract, contract_sha = load_longform_contract(skill_path)
    path = within_workspace(workspace, raw_path, must_exist=True)
    if not path.is_file() or not 0 < path.stat().st_size <= SESSION_MAX_BYTES:
        raise WorkflowError(f"LONGFORM_SESSION_INVALID: --session must be a JSON file of at most {SESSION_MAX_BYTES} bytes")
    data = path.read_bytes()
    try:
        value = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WorkflowError(f"LONGFORM_SESSION_INVALID: {error}") from error
    return {"schema": SESSION_BINDING_SCHEMA, "contract_revision": 1, "contract_sha256": contract_sha,
            "session_path": relative_path(workspace, path), "session_sha256": hashlib.sha256(data).hexdigest(),
            "chapters": parse_session(value, materials, contract["limits"])}


def require_session_binding(binding: Any, materials: list[dict[str, Any]], *, skill_path: Path | None = None) -> dict[str, Any]:
    """Recheck a binding before it enters a run; it must re-derive from its own chapters."""
    binding = require_mapping(binding, "long-form session binding")
    if (set(binding) != {"schema", "contract_revision", "contract_sha256", "session_path", "session_sha256", "chapters"}
            or binding["schema"] != SESSION_BINDING_SCHEMA or not _same(binding["contract_revision"], 1)):
        raise WorkflowError("LONGFORM_SESSION_BINDING_INVALID: unsupported long-form session binding")
    contract, contract_sha = load_longform_contract(skill_path)
    if binding["contract_sha256"] != contract_sha:
        raise WorkflowError("LONGFORM_SESSION_BINDING_INVALID: the long-form session contract changed")
    require_sha(binding["session_sha256"], "long-form session sha256")
    rows = [{"chapterId": item.get("key"), "range": item.get("range"), "clipIds": item.get("clip_ids")}
            for item in (require_mapping(chapter, "bound chapter") for chapter in require_list(binding["chapters"], "bound chapters"))]
    if parse_session({"schema": SESSION_SCHEMA, "chapters": rows}, materials, contract["limits"]) != binding["chapters"]:
        raise WorkflowError("LONGFORM_SESSION_BINDING_INVALID: chapters do not re-derive from the bound materials")
    return binding


# ---- write_v4_plan per chapter ----

def validate_chapter_plan(state: dict[str, Any], step: dict[str, Any], workspace: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """The revision-6 plan rules for one chapter; never sets state["plan"]."""
    from workflow_receipt_store import receipt_for
    chapter = chapter_for(state, step)
    artifact = _artifact(workspace, payload.get("artifact"), "chapter plan", ".json")
    expected_path = chapter_plan_path(state, chapter).resolve()
    if artifact != expected_path:
        raise WorkflowError(f"LONGFORM_CHAPTER_ARTIFACT: chapter {chapter['key']} must be sealed at {expected_path}")
    plan = require_mapping(read_json(artifact), "chapter plan")
    if plan.get("schema") != CURRENT_PLAN_SCHEMA:
        raise WorkflowError("Legacy autopilot plans are forbidden; only edit-plan/v4 may continue")
    source = require_mapping(plan.get("source"), "chapter plan source")
    if require_sha(source.get("skillSha256"), "chapter plan source.skillSha256") != state["governance"]["skill_sha256"]:
        raise WorkflowError("Chapter plan was generated from a different video-autopilot skill hash")
    if require_mapping(plan.get("route"), "chapter plan route").get("format") != "longform":
        raise WorkflowError("LONGFORM_CHAPTER_ROUTE: chapter plans require route.format == longform")
    if "originalMotionEvidence" in plan:
        raise WorkflowError("LONGFORM_V1_ORIGINAL_SOURCES_REFUSED: chapter plans cannot carry Original Motion sources")
    evidence = require_mapping(plan.get("materialEvidence"), "chapter plan materialEvidence")
    if evidence.get("schema") != MATERIAL_EVIDENCE_SCHEMA:
        raise WorkflowError("Chapter plan is missing current material intelligence evidence")
    receipts = require_list(evidence.get("receipts"), "chapter plan materialEvidence.receipts")
    ids = [str(item.get("materialId", "")) for item in receipts if isinstance(item, dict)]
    if len(ids) != len(receipts) or len(set(ids)) != len(ids):
        raise WorkflowError("Chapter plan materialEvidence contains invalid or duplicate material IDs")
    key = lambda item: str(item["materialId"])
    if sorted(receipts, key=key) != sorted(expected_chapter_receipts(state, chapter), key=key):
        raise WorkflowError(f"LONGFORM_CHAPTER_RECEIPTS: chapter {chapter['key']} materialEvidence must equal exactly its own semantic receipts")
    refused = _refused_command(plan.get("commands"))
    if refused:
        raise WorkflowError(f"{refused}: chapter {chapter['key']} carries a command that v1 sets refuse")
    plugin_facts = require_mapping(receipt_for(state, "plugin-discovery").get("facts"), "plugin receipt facts")
    verified = {(item["plugin_id"], item["capability_id"]) for item in plugin_facts["verified_candidates"]}
    unverified = _plugin_references(plan) - verified
    if unverified:
        raise WorkflowError(f"Chapter plan references unverified plugin capabilities: {sorted(unverified)}")
    route = require_mapping(receipt_for(state, "route").get("facts"), "route receipt facts")
    inference = require_mapping(plan.get("inference"), "chapter plan inference")
    if require_mapping(inference.get("context"), "chapter plan inference.context").get("markdownRouterSha256") != route["markdown_router_sha256"]:
        raise WorkflowError("Chapter plan inference router hash does not match route receipt")
    issues = chapter_frame_violations(plan, chapter["range"])
    if issues:
        bounds = chapter["range"]
        raise WorkflowError(f"LONGFORM_CHAPTER_FRAME_OUTSIDE_RANGE: chapter {chapter['key']} "
                            f"[{bounds['startFrame']}, {bounds['endFrame']}) holds {issues[:8]}")
    computed = plan_sha256(plan)
    if require_sha(payload.get("plan_sha256"), "plan_sha256") != computed:
        raise WorkflowError("Submitted chapter planSha256 does not match the canonical plan hash")
    return {"chapter_id": chapter["key"], "plan_schema": CURRENT_PLAN_SCHEMA, "plan_sha256": computed,
            "artifact": relative_path(workspace, artifact), "artifact_sha256": sha256_file(artifact),
            "knowledge_sha256": require_sha(source.get("knowledgeSha256"), "chapter plan source.knowledgeSha256"),
            "material_receipt_count": len(receipts), "material_evidence_sha256": _canonical(evidence),
            "range": dict(chapter["range"])}


# ---- local seal_longform_plan_set ----

def expected_plan_set(state: dict[str, Any], workspace: Path) -> dict[str, Any]:
    """Deterministic set from the completed chapter receipts and the unchanged base project."""
    from workflow_receipt_store import receipt_for
    project = require_mapping(read_json(project_file(state, workspace)), "long-form base project")
    if not isinstance(project.get("id"), str) or not project["id"] or type(project.get("revision")) is not int or project["revision"] < 0:
        raise WorkflowError("LONGFORM_BASE_PROJECT: the base project needs an id and an integer revision")
    chapters = []
    for chapter in state["binding"]["longform_session"]["chapters"]:
        facts = require_mapping(receipt_for(state, f"plan:{chapter['key']}").get("facts"), "chapter plan receipt facts")
        path = within_workspace(workspace, facts["artifact"], must_exist=True)
        if (path != chapter_plan_path(state, chapter).resolve() or sha256_file(path) != facts["artifact_sha256"]
                or plan_sha256(require_mapping(read_json(path), "sealed chapter plan")) != facts["plan_sha256"]):
            raise WorkflowError(f"LONGFORM_CHAPTER_CHANGED: sealed chapter plan {chapter['key']} changed after its receipt")
        chapters.append({"chapterId": chapter["key"], "range": dict(chapter["range"]),
                         "planPath": str(path), "planSha256": facts["plan_sha256"]})
    return {"schema": PLAN_SET_SCHEMA,
            "baseProject": {"id": project["id"], "revision": project["revision"], "contentSha256": _canonical(project)},
            "chapters": chapters}


def validate_plan_set(state: dict[str, Any], workspace: Path, payload: dict[str, Any]) -> dict[str, Any]:
    verify_project_binding(state, workspace)
    artifact = _artifact(workspace, payload.get("artifact"), "plan set", ".json")
    if artifact != plan_set_path(state).resolve():
        raise WorkflowError(f"LONGFORM_PLAN_SET_ARTIFACT: the set must be sealed at {plan_set_path(state)}")
    expected = expected_plan_set(state, workspace)
    if require_mapping(read_json(artifact), "plan set") != expected:
        raise WorkflowError("LONGFORM_PLAN_SET_MISMATCH: the artifact is not the deterministic set of the sealed chapters")
    digest = _canonical(expected)
    if require_sha(payload.get("plan_sha256"), "plan set sha256") != digest:
        raise WorkflowError("LONGFORM_PLAN_SET_SHA: submitted set sha does not match the canonical set hash")
    return {"plan_schema": PLAN_SET_SCHEMA, "plan_sha256": digest, "artifact": relative_path(workspace, artifact),
            "artifact_sha256": sha256_file(artifact), "chapter_count": len(expected["chapters"]),
            "chapters": [{"chapter_id": item["chapterId"], "plan_sha256": item["planSha256"], "range": item["range"]}
                         for item in expected["chapters"]],
            "base_project": expected["baseProject"]}


def bound_plan_set(state: dict[str, Any], workspace: Path) -> dict[str, Any]:
    binding = require_mapping(state.get("plan"), "sealed plan set binding")
    if binding.get("schema") != PLAN_SET_SCHEMA:
        raise WorkflowError("LONGFORM_PLAN_SET_UNSEALED: this run has no sealed long-form plan set")
    path = within_workspace(workspace, binding.get("artifact") or "", must_exist=True)
    value = require_mapping(read_json(path), "sealed plan set")
    if (sha256_file(path) != binding.get("artifact_sha256") or value.get("schema") != PLAN_SET_SCHEMA
            or _canonical(value) != binding.get("plan_sha256")):
        raise WorkflowError("LONGFORM_PLAN_SET_CHANGED: the sealed plan set file changed")
    return value


def set_chapter_plans(state: dict[str, Any], workspace: Path, plan_set: dict[str, Any]) -> list[dict[str, Any]]:
    plans = []
    for row, chapter in zip(require_list(plan_set.get("chapters"), "set chapters"), state["binding"]["longform_session"]["chapters"]):
        path = within_workspace(workspace, row["planPath"], must_exist=True)
        plan = require_mapping(read_json(path), "set chapter plan")
        if path != chapter_plan_path(state, chapter).resolve() or plan_sha256(plan) != row["planSha256"]:
            raise WorkflowError(f"LONGFORM_CHAPTER_CHANGED: chapter plan {row['chapterId']} no longer matches the sealed set")
        plans.append(plan)
    if len(plans) != len(state["binding"]["longform_session"]["chapters"]):
        raise WorkflowError("LONGFORM_PLAN_SET_CHANGED: the sealed set lost a chapter")
    return plans


# ---- Editkin capability, audit and apply bindings ----

def require_longform_capability(contract: dict[str, Any]) -> dict[str, Any]:
    """Fail at the first contract, before any material preparation, when Editkin lacks the set tools."""
    expected = dict(load_longform_contract()[0]["editkin_capability"])
    key = expected.pop("key")
    actual = contract.get(key)
    if not isinstance(actual, dict):
        raise WorkflowError("LONGFORM_CAPABILITY_MISSING: the actual Editkin runtime lacks contract.longformPlanSet; "
                            "activate the matching generation before preparing materials")
    mismatched = sorted(field for field, value in expected.items() if not _same(actual.get(field), value))
    if mismatched:
        raise WorkflowError("LONGFORM_CAPABILITY_MISMATCH: contract.longformPlanSet differs from the v1 session contract: "
                            + ", ".join(mismatched))
    return {"longform_plan_set": {"schema": actual["schema"], "audit_tool": actual["auditTool"], "apply_tool": actual["applyTool"],
                                  "render_tool": actual["renderTool"], "max_chapters": actual["maxChapters"]}}


def validate_longform_audit_binding(state: dict[str, Any], value: Any) -> dict[str, Any]:
    """Public shape and run binding of the set audit receipt; Editkin authenticates it."""
    from workflow_audit_binding import validate_live_invocation
    from workflow_receipt_store import receipt_for
    receipt = require_mapping(value, "long-form auditReceipt")
    if not AUDIT_RECEIPT_FIELDS <= set(receipt) <= AUDIT_RECEIPT_FIELDS | {"planSchema"}:
        raise WorkflowError("LONGFORM_AUDIT_RECEIPT_SHAPE: unsupported long-form auditReceipt fields")
    if receipt["schema"] != AUDIT_RECEIPT_SCHEMA or receipt.get("planSchema", PLAN_SET_SCHEMA) != PLAN_SET_SCHEMA:
        raise WorkflowError(f"LONGFORM_AUDIT_RECEIPT_SCHEMA: a plan set needs {AUDIT_RECEIPT_SCHEMA}, never a single-plan receipt")
    if receipt["status"] != "ACCEPTED":
        raise WorkflowError("LONGFORM_AUDIT_RECEIPT_SHAPE: only an ACCEPTED set audit can enter apply")
    for field in ("setSha256", "receiptSha256", "issuerProof"):
        require_sha(receipt[field], field)
    workspace = Path(state["workspace"])
    plan_set = bound_plan_set(state, workspace)
    if receipt["setSha256"] != state["plan"]["plan_sha256"]:
        raise WorkflowError("LONGFORM_AUDIT_SET: the audit receipt is not for the sealed plan set")
    if _canonical({key: item for key, item in receipt.items() if key not in {"receiptSha256", "issuerProof"}}) != receipt["receiptSha256"]:
        raise WorkflowError("LONGFORM_AUDIT_CHECKSUM: the audit receipt public checksum does not match")
    try:
        timestamp = datetime.fromisoformat(str(receipt["auditedAt"]).replace("Z", "+00:00"))
    except ValueError as error:
        raise WorkflowError("Invalid long-form audit timestamp") from error
    if timestamp.tzinfo is None:
        raise WorkflowError("Long-form audit timestamp requires a timezone")
    age = (datetime.now(timezone.utc) - timestamp).total_seconds()
    if age < -5 or age >= AUDIT_RECEIPT_MAX_AGE_SECONDS:
        raise WorkflowError("Long-form audit expired or from the future; re-audit required")
    path = project_file(state, workspace)
    project = require_mapping(read_json(path), "long-form audited project")
    normalized = str(path).lower() if os.name == "nt" else str(path)
    identity = {"id": project.get("id"), "revision": project.get("revision"),
                "pathSha256": hashlib.sha256(normalized.encode()).hexdigest(), "contentSha256": _canonical(project)}
    if (not _same(receipt["project"], identity)
            or not _same({key: identity[key] for key in ("id", "revision", "contentSha256")}, plan_set["baseProject"])):
        raise WorkflowError("LONGFORM_AUDIT_BASE_IDENTITY: the audited project is not the sealed base project")
    runtime_sha = None
    if state["steps"]["contract"]["status"] == "completed":
        runtime_sha = receipt_for(state, "contract")["facts"]["runtime_sha256"]
    invocation = validate_live_invocation(receipt["invocation"], engine_sha256=runtime_sha,
                                          workflow_sha256=state["contract"]["sha256"], skill_sha256=state["governance"]["skill_sha256"])
    rows = require_list(receipt["chapters"], "long-form audit chapters")
    plans = set_chapter_plans(state, workspace, plan_set)
    if len(rows) != len(plan_set["chapters"]):
        raise WorkflowError("LONGFORM_AUDIT_CHAPTERS: the audit receipt does not cover exactly the sealed chapters")
    first_source = None
    for row, chapter, plan in zip(rows, plan_set["chapters"], plans):
        row = require_mapping(row, "long-form audit chapter")
        if set(row) != AUDIT_CHAPTER_FIELDS or row["chapterId"] != chapter["chapterId"] or not _same(row["range"], chapter["range"]):
            raise WorkflowError("LONGFORM_AUDIT_CHAPTERS: audited chapter id or range differs from the sealed set")
        if row["planSha256"] != chapter["planSha256"]:
            raise WorkflowError(f"LONGFORM_AUDIT_CHAPTER_SHA: audited chapter {chapter['chapterId']} plan differs from the sealed set")
        if row["materialEvidenceSha256"] != _canonical(plan["materialEvidence"]):
            raise WorkflowError(f"LONGFORM_AUDIT_EVIDENCE: audited chapter {chapter['chapterId']} material evidence differs")
        source = require_mapping(plan.get("source"), "chapter plan source")
        for field, (section, key) in SOURCE_BINDINGS.items():
            if field not in source or source[field] != require_mapping(invocation.get(section), section).get(key):
                raise WorkflowError("LONGFORM_AUDIT_SOURCE: chapter source binding mismatch: " + field)
        if source.get("invocationBindingSha256") != invocation["bindingSha256"]:
            raise WorkflowError("LONGFORM_AUDIT_SOURCE: chapter source is not bound to the audited invocation")
        if first_source is not None and not _same(source, first_source):
            raise WorkflowError("LONGFORM_AUDIT_SOURCE: every chapter must carry the identical plan source")
        first_source = source
    if invocation["workflow"].get("sha256") != state["contract"]["sha256"] or invocation["skill"].get("sha256") != state["governance"]["skill_sha256"]:
        raise WorkflowError("Long-form audit current workflow/skill binding mismatch")
    return copy.deepcopy(receipt)


def longform_audit(state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """The audit step of a long-form run, selected by the bound plan-set schema."""
    if str(payload.get("status", "")).upper() != "ACCEPTED":
        raise WorkflowError("Long-form audit must be ACCEPTED")
    if state["plan"].get("schema") != PLAN_SET_SCHEMA:
        raise WorkflowError("Audit receipt is not for the bound long-form plan set")
    receipt = validate_longform_audit_binding(state, payload.get("auditReceipt"))
    for field in ("setSha256", "planSha256"):  # optional unsigned summaries must still agree
        if field in payload and payload[field] != state["plan"]["plan_sha256"]:
            raise WorkflowError(f"LONGFORM_AUDIT_SET: audit response {field} differs from the sealed set")
    return {"plan_sha256": state["plan"]["plan_sha256"], "set_sha256": receipt["setSha256"],
            "chapter_count": len(receipt["chapters"]), "legacy": False, "audit_receipt": receipt}


def validate_longform_apply(state: dict[str, Any], workspace: Path, receipt: dict[str, Any], committed: dict[str, Any]) -> dict[str, Any]:
    """Extra set checks after the generic apply checks (schema, sha, +1 revision, committed file)."""
    from workflow_receipt_store import receipt_for
    plan_set = bound_plan_set(state, workspace)
    if committed.get("planSchema") != PLAN_SET_SCHEMA:
        raise WorkflowError("LONGFORM_APPLY_SCHEMA: the committed receipt is not for the long-form plan set")
    base_revision = plan_set["baseProject"]["revision"]
    if receipt.get("projectRevisionBefore") != base_revision or committed.get("projectRevisionBefore") != base_revision:
        raise WorkflowError("LONGFORM_APPLY_BASE: the apply did not start from the sealed base project revision")
    audited = require_mapping(receipt_for(state, "audit").get("facts"), "long-form audit facts")["audit_receipt"]
    record = committed.get("audit")
    if not isinstance(record, dict) or record.get("receiptSha256") != audited["receiptSha256"]:
        raise WorkflowError("LONGFORM_APPLY_AUDIT: the committed receipt does not bind the accepted set audit")
    block = committed.get("longformSet")
    if not isinstance(block, dict) or ("longformSet" in receipt and receipt["longformSet"] != block):
        raise WorkflowError("LONGFORM_APPLY_SET: the committed receipt lacks a consistent longformSet block")
    return {"set_sha256": state["plan"]["plan_sha256"], "base_project_revision": base_revision,
            "chapter_count": len(plan_set["chapters"])}


# ---- step instructions ----

def longform_step_instruction(state: dict[str, Any], step: dict[str, Any], workspace: Path) -> dict[str, Any]:
    tool, project_path = step["tool"], state["binding"]["project_path"]
    if tool == "start_ai_editing_session":
        request = {"projectPath": project_path, **load_longform_contract()[0]["session_request"]}
        return {"tool": tool, "request": request,
                "note": "Long-form session: every bound clip must be on this one page (clipLimit 100 fits the 96-material cap). "
                        f"The returned workflow must list {AUDIT_TOOL} and {APPLY_TOOL}."}
    if tool == "write_v4_plan" and step.get("chapter_key"):
        chapter = chapter_for(state, step)
        request: dict[str, Any] = {
            "schema": CURRENT_PLAN_SCHEMA, "artifactPath": str(chapter_plan_path(state, chapter)),
            "chapter": {"chapterId": chapter["key"], "range": dict(chapter["range"]), "clipIds": list(chapter["clip_ids"])},
            "route": {"format": "longform"},
            "materialEvidence": {"schema": MATERIAL_EVIDENCE_SCHEMA, "receipts": expected_chapter_receipts(state, chapter)},
        }
        return {"tool": tool, "request": request, "note": (
            "Write one complete edit-plan/v4 for this chapter only, against the unchanged base project, and complete with "
            "{artifact,plan_sha256}. route.format is longform; materialEvidence.receipts is exactly the listed chapter receipts; "
            "every beat, graphic, transition, audio accent and colour exception frame stays inside the chapter's integer "
            "[startFrame, endFrame). Read get_autopilot_design_brief and all of its pages for this chapter's beats exactly as for a "
            "single plan and bind designEvidence. No ripple edits: pause and retake cuts must already be in the base project. "
            "Original Motion sources, owner revisions and relink_asset_source are refused in v1. Do not render a chapter.")}
    if tool == SEAL_TOOL:
        plan_set = expected_plan_set(state, workspace)
        return {"tool": tool, "request": {"artifactPath": str(plan_set_path(state)), "planSet": plan_set,
                                          "planSetSha256": _canonical(plan_set)},
                "note": "Local step, no MCP call: write planSet verbatim to artifactPath, then complete with "
                        "{artifact, plan_sha256: planSetSha256}. The controller recomputes the set from the sealed chapter "
                        "receipts; a changed chapter file or base project is rejected."}
    if tool in {AUDIT_TOOL, APPLY_TOOL}:
        request = {"projectPath": str(within_workspace(workspace, project_path)), "planSet": bound_plan_set(state, workspace)}
        note = "Audit the whole sealed set against the same base project; the receipt binds every chapter plan and range."
        if tool == APPLY_TOOL:
            from workflow_receipt_store import receipt_for
            request["auditReceipt"] = longform_audit(state, receipt_for(state, "audit")["payload"])["audit_receipt"]
            note = ("One atomic set apply only: exactly one project revision and one committed receipt. If interrupted, do not "
                    "retry; reconcile first. An expired or process-restarted audit needs a new run, never a fabricated receipt.")
        return {"tool": tool, "request": request, "note": note}
    raise WorkflowError(f"No long-form instruction for {tool}")
