"""Public CLI engine-floor controls; synthetic files are never product/art receipts."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(1, str(ROOT / "scripts"))
from engine_continuity import EngineContinuityError, engine_continuity_sha256, parse_engine_continuity, require_engine_continuity
from workflow_audit_binding import sha256_json as wire_sha, validate_audit_binding
from workflow_binding_fixture import fixture_audit, fixture_engine, fixture_live_invocation
from workflow_state import STATE_NAME, WORKFLOW_EXECUTABLE_SOURCES, WorkflowError, read_json, sha256_json, write_json_atomic
from sync_canonical import PUBLIC_WORKFLOW_ADAPTERS, _assert_public_workflow_derivation, sync
from public_adapter_test_support import canonical_adapter_fixture, public_distribution_fixture
from public_workflow_distribution import ADAPTER_MODULES, render_forwarder
from public_sync_paths import _text_sha256


class PublicEngineContinuityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="public-engine-floor-")
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name).resolve()
        self.skill_root = self.workspace / "canonical"
        self.skill_root.mkdir()
        self.skill = self.skill_root / "SKILL.md"
        self.skill.write_text("---\nname: video-autopilot\n---\nSynthetic public test authority.\n", encoding="utf-8")
        for name in (*WORKFLOW_EXECUTABLE_SOURCES, "workflow_contract.json"):
            shutil.copyfile(SRC / name, self.skill_root / name)
        self.project = self.workspace / "original-fixture.editkin.json"
        write_json_atomic(self.project, {"schemaVersion": 9, "id": "original-fixture", "revision": 0, "tracks": [], "assets": []})
        self.source = self.workspace / "fixture.mp4"
        self.source.write_bytes(b"original unit material bytes; not a rendered film")
        self.run = self.workspace / "run"
        self.environment = {**os.environ, "EDITKIN_VIDEO_AUTOPILOT_SKILL": str(self.skill), "PYTHONDONTWRITEBYTECODE": "1"}
        self.cli_path = SRC / "workflow_contract.py"

    def cli(self, *arguments, success=True):
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(self.cli_path), "--workspace", str(self.workspace), *map(str, arguments)],
            env=self.environment, capture_output=True, text=True, encoding="utf-8", timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.assertEqual(result.returncode, 0 if success else 1, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["ok"], success)
        return payload["result"] if success else payload

    def create(self, *extra, success=True):
        return self.cli("create", "--run-id", "engine-floor", "--run-dir", self.run,
            "--project", self.project, "--material", "clip-fixture=" + str(self.source), *extra, success=success)

    def state(self):
        return read_json(self.run / STATE_NAME)

    def contract_payload(self, state, runtime=None):
        runtime = fixture_engine(state) if runtime is None else runtime
        return {"status": "GREEN", "contract": {
            "schemaVersion": 4, "planSchema": "hao.video-autopilot.edit-plan/v4",
            "planHashAlgorithm": "sha256-canonical-json-utf8-keys-v1", "productVersion": "synthetic-public-test",
            "legacyPlanSchemas": ["v3"], "sourcePolicy": {"dynamicCanonicalSkill": True, "packagePrivateSkillOrMemory": False},
            "designExecution": {"tool": "get_autopilot_design_brief", "schema": "editkin.autopilot-design-evidence/v1"},
            "visualReview": {"step": "visual-review", "policyBound": True, "modes": ["human", "agent_reference_comparison"], "outcomeCheckpoints": ["human_review", "agent_review"]},
            "engineContinuity": runtime}, "liveInvocation": fixture_live_invocation(state, runtime)}

    def complete_contract(self, payload, token, success=True):
        path = self.workspace / "synthetic-contract-response.json"
        write_json_atomic(path, payload)
        return self.cli("complete", self.run, "contract", "--token", token, "--receipt", path, success=success)

    def seal_contract(self, runtime=None):
        claim = self.cli("claim", self.run, "contract")
        payload = self.contract_payload(self.state(), runtime)
        return self.complete_contract(payload, claim["claim_token"])

    def test_public_packaging_mirrors_match_without_claiming_private_original_lane(self):
        from release_integrity import collect_skill_sources
        manifest = read_json(ROOT / "release-manifest.json")
        materialized = dict(collect_skill_sources(ROOT, ROOT / "codex-skill/video-autopilot",
            manifest["codex_skill"]["materialize_from"]))
        for name in (*WORKFLOW_EXECUTABLE_SOURCES, "workflow_contract.json"):
            with self.subTest(name=name):
                if name in ADAPTER_MODULES:
                    self.assertEqual((ROOT / "codex-skill/video-autopilot" / name).read_text(encoding="utf-8"),
                                     render_forwarder(name, tuple(WORKFLOW_EXECUTABLE_SOURCES)))
                self.assertEqual((SRC / name).read_bytes(), materialized[name].read_bytes())
        self.assertEqual(_text_sha256(SRC / "engine_continuity.py"),
            "6fcb7beda7a310822d9eba74bb8277bea6e9553c5ce2875899a08f103aafbfea")
        self.assertFalse((SRC / "workflow_original_sources.py").exists())

    def test_neutral_parser_rejects_unknown_and_estimated_engine_capabilities(self):
        floor = read_json(SRC / "workflow_contract.json")["engine_continuity_floor"]
        parsed = parse_engine_continuity(floor)
        parsed["projectSchemas"].append(10)
        self.assertEqual(floor["projectSchemas"], [9])
        for field, value in (("textPreparation", "estimated-text"), ("templateAuthoring", "generation1"),
                             ("visualReviewPolicyBound", False), ("engineId", "legacy-engine")):
            candidate = copy.deepcopy(floor); candidate[field] = value
            with self.subTest(field=field), self.assertRaises(EngineContinuityError):
                parse_engine_continuity(candidate)
        candidate = copy.deepcopy(floor); candidate["callerApproved"] = True
        with self.assertRaises(EngineContinuityError): parse_engine_continuity(candidate)

    def test_schema10_requires_actual_runtime_support_and_does_not_raise_minimum_floor(self):
        floor = read_json(SRC / "workflow_contract.json")["engine_continuity_floor"]
        with self.assertRaises(EngineContinuityError): require_engine_continuity(floor, floor, 10)
        runtime = copy.deepcopy(floor); runtime["projectSchemas"] = [9, 10]
        facts = require_engine_continuity(runtime, floor, 10)
        self.assertEqual(facts["required_project_schema"], 10)
        self.assertEqual(facts["floor_sha256"], engine_continuity_sha256(floor))
        self.assertEqual(floor["projectSchemas"], [9])

    def test_actual_src_cli_create_binds_both_execution_roots_before_ready_contract(self):
        self.create()
        state = self.state()
        self.assertEqual(state["binding"]["engine_continuity"]["required_project_schema"], 9)
        self.assertEqual(state["binding"]["engine_continuity"]["floor"]["projectSchemas"], [9])
        rows = {key: state["governance"][key] for key in ("executable_sources", "controller_executable_sources")}
        for collection in rows.values():
            self.assertEqual({row["path"] for row in collection}, set(WORKFLOW_EXECUTABLE_SOURCES))
        self.assertEqual(state["binding"]["workflow_executable_sha256"], sha256_json({"canonical": rows["executable_sources"], "controller": rows["controller_executable_sources"]}))
        self.assertEqual([item["step"] for item in self.cli("next", self.run)["ready"]], ["contract"])

    def test_actual_contract_preflight_blocks_missing_scene_glyph_floating_and_generation_floor(self):
        self.create(); token = self.cli("claim", self.run, "contract")["claim_token"]
        valid = self.contract_payload(self.state())
        candidates = []
        missing = copy.deepcopy(valid); missing["contract"].pop("engineContinuity"); candidates.append(missing)
        for key, value in (("textPreparation", "estimated-text"), ("templateAuthoring", "generation1"),
                           ("motionSchemas", ["hao.motion-composition/v1"]), ("visualReviewPolicyBound", False)):
            candidate = copy.deepcopy(valid); candidate["contract"]["engineContinuity"][key] = value; candidates.append(candidate)
        for key, value in (("schema", "editkin.floating-video-frame/v1"), ("mediaFit", "cover"), ("clock", "seconds"), ("geometry", "canvas_aspect_ratio")):
            candidate = copy.deepcopy(valid); candidate["contract"]["engineContinuity"]["floatingFrame"][key] = value; candidates.append(candidate)
        for candidate in candidates:
            self.complete_contract(candidate, token, success=False)
            self.assertEqual(self.state()["steps"]["contract"]["status"], "running")
            self.assertEqual(self.state()["steps"]["session"]["status"], "pending")
            self.assertEqual(self.cli("next", self.run)["ready"], [])

    def test_first_contract_engine_pin_is_required_even_with_recomputed_wire_checksum(self):
        self.create(); token = self.cli("claim", self.run, "contract")["claim_token"]
        valid = self.contract_payload(self.state())
        for mode in ("missing", "foreign", "old-revision"):
            candidate = copy.deepcopy(valid); invocation = candidate["liveInvocation"]
            if mode == "missing": invocation.pop("engine")
            elif mode == "foreign": invocation["engine"]["sha256"] = "d" * 64
            else: invocation["workflow"]["revision"] = 3
            invocation["bindingSha256"] = wire_sha({key: value for key, value in invocation.items() if key != "bindingSha256"})
            with self.subTest(mode=mode): self.complete_contract(candidate, token, success=False)
        self.assertEqual(self.state()["steps"]["contract"]["status"], "running")

    def test_successful_contract_seals_real_response_facts_before_session(self):
        self.create(); completion = self.seal_contract()
        self.assertEqual(completion["facts"]["runtime_sha256"], engine_continuity_sha256(fixture_engine(self.state())))
        self.assertEqual(completion["facts"]["required_project_schema"], 9)
        self.assertEqual([item["step"] for item in self.cli("next", self.run)["ready"]], ["session"])
        state = self.state()
        self.assertEqual(state["steps"]["prepare:" + state["binding"]["materials"][0]["key"]]["status"], "pending")

    def test_old_run_snapshot_is_readable_but_next_claim_and_complete_are_stopped(self):
        self.create(); state = self.state(); state["binding"].pop("engine_continuity")
        write_json_atomic(self.run / STATE_NAME, state)
        before = (self.run / STATE_NAME).read_bytes()
        self.cli("status", self.run)
        for args in (("next", self.run), ("claim", self.run, "contract"),
                     ("complete", self.run, "contract", "--token", "untrusted", "--receipt", "{}")):
            self.cli(*args, success=False)
        self.assertEqual((self.run / STATE_NAME).read_bytes(), before)

    def test_contract_generation_change_preserves_historical_read_only_status(self):
        self.create()
        path = self.skill_root / "workflow_contract.json"
        contract = read_json(path); contract["limits"]["context_tokens_per_page"] += 1; write_json_atomic(path, contract)
        self.cli("status", self.run)
        self.assertIn("historical runs are read-only", self.cli("next", self.run, success=False)["detail"])
        self.cli("claim", self.run, "contract", success=False)

    def test_canonical_helper_byte_drift_blocks_even_when_original_mtime_is_restored(self):
        self.create(); path = self.skill_root / "workflow_transport.py"; before = path.stat()
        path.write_bytes(path.read_bytes() + b"\n# synthetic changed execution byte\n")
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertIn("executable source changed", self.cli("claim", self.run, "contract", success=False)["detail"])

    def test_actual_controller_clone_drift_is_not_hidden_by_unchanged_canonical_skill(self):
        controller = self.workspace / "executed-controller"; controller.mkdir()
        for name in (*WORKFLOW_EXECUTABLE_SOURCES, "workflow_contract.json"):
            shutil.copyfile(SRC / name, controller / name)
        self.cli_path = controller / "workflow_contract.py"
        self.create()
        helper = controller / "workflow_context_chain.py"; helper.write_bytes(helper.read_bytes() + b"\n# controlled drift\n")
        self.assertIn("executable source changed", self.cli("next", self.run, success=False)["detail"])

    def test_bound_floor_or_sealed_facts_cannot_be_rewritten_to_authorize_runtime(self):
        self.create(); self.seal_contract(); state = self.state()
        receipt_path = self.run / state["steps"]["contract"]["receipt"]["path"]
        envelope = read_json(receipt_path); envelope["facts"]["runtime_sha256"] = "e" * 64
        write_json_atomic(receipt_path, envelope)
        state["steps"]["contract"]["receipt"]["file_sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        write_json_atomic(self.run / STATE_NAME, state)
        self.assertIn("Sealed current-engine contract facts changed", self.cli("next", self.run, success=False)["detail"])

    def test_schema9_to10_apply_transition_requires_the_sealed_actual_runtime_support(self):
        self.create(); self.seal_contract()
        state = self.state(); state["steps"]["apply"]["status"] = "running"; write_json_atomic(self.run / STATE_NAME, state)
        project = read_json(self.project); project["schemaVersion"] = 10; write_json_atomic(self.project, project)
        self.cli("next", self.run)
        self.run = self.workspace / "unsupported-schema10-run"
        project["schemaVersion"] = 9; write_json_atomic(self.project, project)
        self.create(); runtime = fixture_engine(self.state()); runtime["projectSchemas"] = [9]
        self.seal_contract(runtime)
        state = self.state(); state["steps"]["apply"]["status"] = "running"; write_json_atomic(self.run / STATE_NAME, state)
        project = read_json(self.project); project["schemaVersion"] = 10; write_json_atomic(self.project, project)
        self.assertIn("runtime does not satisfy", self.cli("next", self.run, success=False)["detail"])

    def test_later_audit_engine_pin_must_match_sealed_contract_not_only_its_own_checksum(self):
        self.create(); self.seal_contract(); state = self.state()
        plan = {"schema": "hao.video-autopilot.edit-plan/v4", "source": {}, "materialEvidence": {"schema": "hao.editkin.material-intelligence/v1", "receipts": []}}
        audit = fixture_audit(state, plan)["auditReceipt"]
        plan_path = self.workspace / "synthetic.plan.json"; write_json_atomic(plan_path, plan)
        state["plan"].update({"artifact": str(plan_path), "plan_sha256": audit["planSha256"]})
        self.assertEqual(validate_audit_binding(state, audit)["invocation"]["engine"]["sha256"], engine_continuity_sha256(fixture_engine(state)))
        changed = copy.deepcopy(audit); invocation = changed["invocation"]; invocation["engine"]["sha256"] = "d" * 64
        invocation["bindingSha256"] = wire_sha({key: value for key, value in invocation.items() if key != "bindingSha256"})
        plan["source"]["invocationBindingSha256"] = invocation["bindingSha256"]; write_json_atomic(plan_path, plan)
        from workflow_state import plan_sha256
        state["plan"]["plan_sha256"] = changed["planSha256"] = plan_sha256(plan)
        changed["receiptSha256"] = wire_sha({key: value for key, value in changed.items() if key not in {"receiptSha256", "issuerProof"}})
        with self.assertRaisesRegex(WorkflowError, "engine pin mismatch"): validate_audit_binding(state, changed)

    def test_public_media_requirement_and_creator_review_authorization_are_not_bypassed(self):
        self.cli("create", "--run-dir", self.run, "--project", self.project, success=False)
        self.assertFalse(self.run.exists())
        policy = self.workspace / "unauthorized-policy.json"
        write_json_atomic(policy, {"mode": "agent_reference_comparison", "authorization": ""})
        self.create("--review-policy", policy, success=False)
        self.assertFalse(self.run.exists())

    def test_real_media_public_run_does_not_invent_canonical_original_source_fanout(self):
        path = self.skill_root / "workflow_contract.json"; contract = read_json(path)
        contract["steps"].insert(2, {"id": "original:{source}", "tool": "prepare_original_motion_source",
            "depends_on": ["session"], "fanout": "original_sources", "retry": "safe", "actor": "machine"})
        write_json_atomic(path, contract)
        self.create(); state = self.state()
        self.assertFalse(any(step["tool"] == "prepare_original_motion_source" for step in state["steps"].values()))
        self.assertEqual(sum(step["tool"] == "prepare_ai_material" for step in state["steps"].values()), 1)
        self.seal_contract()
        self.assertEqual([item["step"] for item in self.cli("next", self.run)["ready"]], ["session"])

    def test_floor_schema10_is_not_forced_and_missing_helper_prevents_run_directory_creation(self):
        path = self.skill_root / "workflow_contract.json"; contract = read_json(path)
        contract["engine_continuity_floor"]["projectSchemas"] = [9, 10]; write_json_atomic(path, contract)
        self.create(success=False); self.assertFalse(self.run.exists())
        shutil.copyfile(SRC / "workflow_contract.json", path)
        (self.skill_root / "engine_continuity.py").unlink()
        self.create(success=False); self.assertFalse(self.run.exists())

    def public_distribution_fixture(self, directory):
        return public_distribution_fixture(ROOT, directory)

    def test_sync_preflight_accepts_equal_current_adapters_without_certifying_a_sync(self):
        before = {name: hashlib.sha256((SRC / name).read_bytes()).hexdigest() for name in PUBLIC_WORKFLOW_ADAPTERS}
        with canonical_adapter_fixture(ROOT, self.workspace / "canonical-analogue") as canonical:
            self.assertIsNone(_assert_public_workflow_derivation(canonical, ROOT))
        self.assertEqual(before, {name: hashlib.sha256((SRC / name).read_bytes()).hexdigest() for name in PUBLIC_WORKFLOW_ADAPTERS})
        self.create(); self.seal_contract()
        self.assertEqual([item["step"] for item in self.cli("next", self.run)["ready"]], ["session"])

    def test_sync_blocks_untransformed_adapter_before_existing_or_absent_target_mutation(self):
        target = self.workspace / "existing-sync-target"; target.mkdir()
        marker = target / "preserve.json"; marker.write_bytes(b'{"original":true}\n')
        before = {path.relative_to(target).as_posix(): path.read_bytes() for path in target.rglob("*") if path.is_file()}
        absent = self.workspace / "absent-sync-target"
        with canonical_adapter_fixture(ROOT, self.workspace / "canonical-analogue") as canonical:
            helper = canonical / "workflow_transport.py"
            helper.write_bytes(helper.read_bytes() + b"\n# synthetic changed canonical analogue\n")
            for destination in (target, absent):
                with self.assertRaisesRegex(ValueError, "canonical analogue changed"):
                    sync(canonical, destination, ROOT)
        self.assertEqual(before, {path.relative_to(target).as_posix(): path.read_bytes() for path in target.rglob("*") if path.is_file()})
        self.assertFalse(absent.exists())

    def test_sync_guard_and_actual_dry_run_cli_block_identical_private_original_dependencies(self):
        distribution = self.public_distribution_fixture(self.workspace / "false-public-distribution")
        source = (SRC / "workflow_state.py").read_bytes() + b"\nfrom workflow_original_sources import parse_original_sources\n"
        for path in (self.skill_root / "workflow_state.py", distribution / "src/workflow_state.py",
                     distribution / "codex-skill/video-autopilot/workflow_state.py"):
            path.write_bytes(source)
        target = self.workspace / "dry-run-target"; target.mkdir()
        marker = target / "preserve.json"; marker.write_bytes(b'{"unchanged":true}\n')
        with self.assertRaisesRegex(ValueError, "undistributed branch"):
            sync(self.skill_root, target, distribution)
        command = subprocess.run([sys.executable, "-B", "-X", "utf8", str(ROOT / "scripts/sync_canonical.py"),
            "--canonical", str(self.skill_root), "--repository", str(target), "--distribution-source", str(distribution), "--dry-run"],
            env=self.environment, capture_output=True, text=True, encoding="utf-8", timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.assertNotEqual(command.returncode, 0)
        self.assertIn("undistributed branch", command.stderr)
        self.assertEqual({path.relative_to(target).as_posix(): path.read_bytes() for path in target.rglob("*") if path.is_file()},
                         {"preserve.json": b'{"unchanged":true}\n'})
        self.assertEqual(_text_sha256(SRC / "engine_continuity.py"),
                         "6fcb7beda7a310822d9eba74bb8277bea6e9553c5ce2875899a08f103aafbfea")

    def test_sync_new_target_does_not_bypass_missing_source_or_stale_public_mirror(self):
        distribution = self.public_distribution_fixture(self.workspace / "incomplete-public-distribution")
        selected = distribution / "src/workflow_audit_binding.py"; selected.unlink()
        target = self.workspace / "new-sync-target"
        with self.assertRaises(FileNotFoundError): sync(self.skill_root, target, distribution)
        self.assertFalse(target.exists())
        shutil.copyfile(SRC / "workflow_audit_binding.py", selected)
        mirror = distribution / "codex-skill/video-autopilot/workflow_audit_binding.py"
        mirror.write_bytes(mirror.read_bytes() + b"\n# stale public mirror\n")
        with self.assertRaisesRegex(ValueError, "forwarder drift"):
            sync(self.skill_root, target, distribution)
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
