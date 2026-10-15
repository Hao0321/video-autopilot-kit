"""Canonical authority and media-only public runtime admission."""
from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Any, Mapping
from engine_continuity import EngineContinuityError, parse_engine_continuity

from workflow_primitives import WorkflowError, CURRENT_PLAN_SCHEMA, require_mapping, read_json, sha256_json

SKILL_PATH_ENV = "EDITKIN_VIDEO_AUTOPILOT_SKILL"

DEFAULT_SKILL_RELATIVE = Path(".codex") / "skills" / "video-autopilot" / "SKILL.md"

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
    if contract.get("contract_revision") != 6:
        raise WorkflowError("Workflow contract requires revision 6; retired execution runs are read-only. Start a new v4 run with the bound visual review policy.")
    limits = require_mapping(contract.get("limits"), "workflow limits")
    for key, expected in {"keyframes_per_call": 4, "keyframe_bytes_per_call": 1000000, "material_poll_interval_ms": 10000}.items():
        if type(limits.get(key)) is not int or limits[key] != expected:
            raise WorkflowError(f"Workflow limit {key} must match the product contract: {expected}")
    if contract.get("plan_schema") != CURRENT_PLAN_SCHEMA or contract.get("legacy_plan_policy") != "reject":
        raise WorkflowError("Workflow contract must pin v4 and reject legacy plans")
    try:
        floor = parse_engine_continuity(contract.get("engine_continuity_floor"))
        if floor["projectSchemas"] != [9]:
            raise EngineContinuityError("Workflow engine floor requires schema9; schema10 is runtime optional")
    except EngineContinuityError as error:
        raise WorkflowError(str(error)) from error
    return contract, sha256_json(contract)

from engine_continuity import EngineContinuityError, require_engine_continuity

def _contract_status(payload: dict[str, Any], allowed: set[str] | None = None) -> str:
    value = str(payload.get("status", "")).upper()
    permitted = allowed or {"GREEN"}
    if value not in permitted:
        raise WorkflowError(f"Receipt status {value or '<missing>'} is not one of {sorted(permitted)}")
    return value

def _contract(payload: dict[str, Any], review_policy: dict | None = None, state: dict | None = None) -> dict[str, Any]:
    _contract_status(payload)
    contract = require_mapping(payload.get("contract"), "get_autopilot_contract.contract")
    policy = require_mapping(contract.get("sourcePolicy"), "get_autopilot_contract.contract.sourcePolicy")
    if (review_policy or {}).get("mode") == "agent_reference_comparison":
        visual = contract.get("visualReview") or {}
        if (visual.get("step") != "visual-review" or visual.get("policyBound") is not True or
                "agent_reference_comparison" not in visual.get("modes", []) or
                "agent_review" not in visual.get("outcomeCheckpoints", [])):
            raise WorkflowError("This Editkin runtime lacks authorized agent visual-review support; activate a matching verified generation before preparing materials")
    if contract.get("planHashAlgorithm") != "sha256-canonical-json-utf8-keys-v1":
        raise WorkflowError("Editkin plan hash algorithm is outdated or incompatible; restart the updated Editkin MCP runtime before preparing materials")
    design = contract.get("designExecution") or {}
    if design.get("tool") != "get_autopilot_design_brief" or design.get("schema") != "editkin.autopilot-design-evidence/v1":
        raise WorkflowError("Editkin current private design compiler is missing; restart the updated runtime before preparing materials")
    if (contract.get("schemaVersion") != 4 or contract.get("planSchema") != CURRENT_PLAN_SCHEMA
            or not str(contract.get("productVersion", "")).strip()
            or policy.get("dynamicCanonicalSkill") is not True
            or policy.get("packagePrivateSkillOrMemory") is not False):
        raise WorkflowError("Editkin contract is downgraded or does not enforce the canonical v4 source policy")
    if state is None:
        raise WorkflowError("Actual contract validation requires a bound current-engine run")
    binding = require_mapping(state["binding"].get("engine_continuity"), "bound engine continuity")
    try:
        engine = require_engine_continuity(contract.get("engineContinuity"), binding.get("floor"), binding.get("required_project_schema"))
    except EngineContinuityError as error:
        raise WorkflowError(str(error)) from error
    if engine["floor_sha256"] != binding.get("floor_sha256"):
        raise WorkflowError("Contract current-engine floor hash mismatch")
    from workflow_audit_binding import validate_live_invocation
    validate_live_invocation(payload.get("liveInvocation"), engine_sha256=engine["runtime_sha256"],
        workflow_sha256=state["contract"]["sha256"], skill_sha256=state["governance"]["skill_sha256"])
    return {"schema_version": 4, "plan_schema": CURRENT_PLAN_SCHEMA,
            "product_version": str(contract["productVersion"]), "legacy_schemas": contract.get("legacyPlanSchemas", []),
            "dynamic_canonical_skill": True, "package_private_skill_or_memory": False, **engine}
