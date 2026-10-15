"""Synthetic unsigned test fixture. Never a real MCP audit/apply receipt."""
from __future__ import annotations
import argparse
from typing import Any
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


def _selftest_binding_drift(_host, a, contract_path, run, skill, state, workspace):
    original = a.read_bytes()
    a.write_bytes(b"tampered")
    try:
        _host['verify_immutable_sources'](state, workspace, full=True)
    except _host['WorkflowError']:
        pass
    else:
        raise AssertionError("source drift accepted")
    a.write_bytes(original)

    original_skill = skill.read_bytes()
    skill.write_bytes(original_skill + b"tampered\n")
    try:
        _host['verify_immutable_sources'](state, workspace, full=True)
    except _host['WorkflowError']:
        pass
    else:
        raise AssertionError("canonical Skill drift accepted")
    skill.write_bytes(original_skill)

    original_contract = contract_path.read_bytes()
    changed_contract = _host['read_json'](contract_path)
    changed_contract["contract_revision"] = int(changed_contract["contract_revision"]) + 1
    _host['write_json_atomic'](contract_path, changed_contract)
    _host['load_state'](run, workspace)  # historical snapshot remains readable
    try:
        _host['verify_immutable_sources'](state, workspace)
    except _host['WorkflowError']:
        pass
    else:
        raise AssertionError("canonical workflow contract drift accepted")
    contract_path.write_bytes(original_contract)


def _selftest_canonical_precedence(_host, default_skill, fake_home, skill, workspace):
    resolved, locator = _host['resolve_canonical_skill']()
    if resolved != skill.resolve() or locator != f"env:{_host['SKILL_PATH_ENV']}":
        raise AssertionError("explicit canonical Skill precedence failed")
    resolved_default, default_locator = _host['resolve_canonical_skill'](env={}, home=fake_home)
    if resolved_default != default_skill.resolve() or default_locator != "codex-home":
        raise AssertionError("default Codex Skill resolution failed")
    try:
        _host['resolve_canonical_skill'](env={_host['SKILL_PATH_ENV']: str(workspace / "missing" / "SKILL.md")})
    except _host['WorkflowError']:
        pass
    else:
        raise AssertionError("missing explicit canonical Skill accepted")


def cmd_selftest(_host, _args: argparse.Namespace) -> dict[str, Any]:
    with _host['tempfile'].TemporaryDirectory(prefix="editkin-v4-workflow-") as raw:
        workspace = _host['Path'](raw).resolve()
        canonical_root = workspace / "canonical-skill"
        canonical_root.mkdir()
        skill = canonical_root / "SKILL.md"
        skill.write_text("---\nname: video-autopilot\n---\nM999 fixture rule\n", encoding="utf-8")
        contract_path = canonical_root / "workflow_contract.json"
        _host['shutil'].copy2(_host['Path'](_host['__file__']).with_name("workflow_contract.json"), contract_path)
        for name in _host['WORKFLOW_EXECUTABLE_SOURCES']:
            _host['shutil'].copy2(_host['Path'](_host['__file__']).with_name(name), canonical_root / name)

        fake_home = workspace / "fake-home"
        default_root = fake_home / ".codex" / "skills" / "video-autopilot"
        default_root.mkdir(parents=True)
        default_skill = default_root / "SKILL.md"
        default_skill.write_text("---\nname: video-autopilot\n---\nM998 default fixture\n", encoding="utf-8")
        _host['shutil'].copy2(_host['Path'](_host['__file__']).with_name("workflow_contract.json"), default_root / "workflow_contract.json")
        for name in _host['WORKFLOW_EXECUTABLE_SOURCES']:
            _host['shutil'].copy2(_host['Path'](_host['__file__']).with_name(name), default_root / name)

        previous_env = _host['os'].environ.get(_host['SKILL_PATH_ENV'])
        _host['os'].environ[_host['SKILL_PATH_ENV']] = str(skill)
        try:
            _host['_selftest_canonical_precedence'](default_skill, fake_home, skill, workspace)

            stale = workspace / ".claude" / "skills" / "video-autopilot"
            stale.mkdir(parents=True)
            (stale / "SKILL.md").write_text(
                "---\nname: video-autopilot\n---\nM997 retired workspace fixture\n", encoding="utf-8"
            )
            project = workspace / "fixture.editkin.json"
            _host['write_json_atomic'](project, {"schemaVersion": 9, "id": "synthetic-fixture", "revision": 0, "tracks": [], "assets": []})
            a, b = workspace / "a.mp4", workspace / "b.mp4"
            a.write_bytes(b"source-a")
            b.write_bytes(b"source-b")
            run, state = _host['create_run'](
                workspace, run_id="selftest", run_dir_raw=None, project_raw=str(project), output_raw=None,
                material_values=[f"clip-a={a}", f"clip-b={b}"], max_retries=2,
                task_class="quality_critical", priority="quality",
            )
            if _host['Path'](state["governance"]["skill_path"]).resolve() != skill.resolve():
                raise AssertionError("workspace Skill copy hijacked canonical governance")
            _host['exercise_selftest'](state, workspace)
            _host['write_json_atomic'](run / _host['STATE_NAME'], state)
            report = _host['verify_run'](state, workspace)
            if report["status"] != "GREEN" or report["completed_steps"] != report["total_steps"]:
                raise AssertionError(report)
            agent_project = workspace / "agent-fixture.editkin.json"
            _host['write_json_atomic'](agent_project, {"schemaVersion": 9, "id": "agent-synthetic-fixture", "revision": 0, "tracks": [], "assets": []})
            _, agent_state = _host['create_run'](workspace, run_id="agent-selftest", run_dir_raw=None,
                project_raw=str(agent_project), output_raw=None, material_values=[f"clip-a={a}"], max_retries=2,
                task_class="quality_critical", priority="quality",
                review_policy={"mode": "agent_reference_comparison", "authorization": "Synthetic creator delegated reference comparison for this controller fixture."})
            _host['exercise_selftest'](agent_state, workspace)
            if _host['verify_run'](agent_state, workspace)["status"] != "GREEN" or agent_state["review"]["human_review_complete"]:
                raise AssertionError("agent workflow failed or fabricated human review")

            _host['_selftest_binding_drift'](a, contract_path, run, skill, state, workspace)

            return {
                "selftest": "GREEN", "completed_steps": report["completed_steps"], "parallel_prepare": True,
                "parallel_route_plugin": True, "contract_downgrade_rejected": True, "audio_zero_keyframes": True,
                "legacy_plan_rejected": True, "oversized_keyframe_batch_rejected": True,
                "tampered_keyframe_rejected": True, "unviewed_semantic_evidence_rejected": True,
                "interrupted_apply_requires_reconcile": True, "machine_human_review_rejected": True,
                "authorized_agent_workflow": True, "agent_never_claims_human_review": True,
                "non_approved_terminal_state": True, "source_drift_rejected": True,
                "explicit_skill_precedence": True, "default_codex_skill": True,
                "workspace_skill_hijack_rejected": True, "skill_drift_rejected": True,
                "contract_drift_rejected": True,
            }
        finally:
            if previous_env is None:
                _host['os'].environ.pop(_host['SKILL_PATH_ENV'], None)
            else:
                _host['os'].environ[_host['SKILL_PATH_ENV']] = previous_env
