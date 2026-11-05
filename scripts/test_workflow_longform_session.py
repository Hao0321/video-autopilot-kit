"""Public long-form one-timeline session controls: synthetic, unsigned fixtures only.

Never an Editkin audit, apply, render or art review. Editkin authenticates the real receipts.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(1, str(ROOT / "scripts"))

import workflow_contract as controller  # noqa: E402
import workflow_longform as lf  # noqa: E402
import workflow_state as ws  # noqa: E402
from workflow_json import json_sha256  # noqa: E402
from workflow_receipts import _audit, _bound_plan_schema, complete_step, verify_run  # noqa: E402
from public_sync_paths import _text_sha256  # noqa: E402

# Revision 6 identity as released in v0.25.0; Editkin seals the contract hash into every plan.
REVISION6_TEXT_SHA256 = "71e9aa89a73fbc3ad412fdb810ff3bde476eaaad4596ab20afbdfdc034ee4f60"
REVISION6_CONTRACT_SHA256 = "f2a6bb9459f42097938b6c68679edd841846e1c9acd00a9c44431255ad710569"
HOST = vars(controller)  # claim/fail/resume come from the CLI facade; workflow_longform never imports it
LONGFORM_FILES = ("workflow_chapter_contract.py", "workflow_longform_runtime.py", "workflow_longform.py",
                  "workflow_longform_contract.json")


class LongformSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lf-test-")
        self.root = Path(self.temp.name).resolve()
        self.skill = self.root / "canonical"
        self.skill.mkdir()
        (self.skill / "SKILL.md").write_text("---\nname: video-autopilot\n---\nlong-form test fixture\n", encoding="utf-8")
        for name in ws.WORKFLOW_EXECUTABLE_SOURCES:
            shutil.copy2(SRC / name, self.skill / name)
        self.env = patch.dict(os.environ, {ws.SKILL_PATH_ENV: str(self.skill / "SKILL.md")})
        self.env.start()
        self.workspace = self.root / "ws"
        self.workspace.mkdir()
        ws.write_json_atomic(self.workspace / "project.editkin.json",
                             {"schemaVersion": 9, "id": "longform-test", "revision": 0, "fps": 30, "tracks": [], "assets": []})
        for name in "abc":
            (self.workspace / f"{name}.mp4").write_bytes(f"synthetic source {name}".encode())
        self.session = {"schema": lf.SESSION_SCHEMA, "chapters": [
            {"chapterId": "intro", "range": {"startFrame": 0, "endFrame": 300}, "clipIds": ["clip-a", "clip-b"]},
            {"chapterId": "demo", "range": {"startFrame": 300, "endFrame": 900}, "clipIds": ["clip-b", "clip-c"]}]}

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    # ---- helpers ----
    def create(self, session=None, **extra):
        ws.write_json_atomic(self.workspace / "session.json", self.session if session is None else session)
        arguments = dict(run_id="longform", run_dir_raw="run", project_raw="project.editkin.json", output_raw="out.mp4",
                         material_values=["clip-a=a.mp4", "clip-b=b.mp4", "clip-c=c.mp4"], max_retries=2,
                         task_class="editorial_plan", priority="quality", longform_session_path="session.json")
        arguments.update(extra)
        return ws.create_run(self.workspace, **arguments)

    def chapters(self, state):
        return state["binding"]["longform_session"]["chapters"]

    def to_chapter_plans(self):
        run, state = self.create()
        lf.fixture_run_to_chapter_plans(HOST, state, self.workspace)
        return run, state

    def sealed(self):
        run, state = self.to_chapter_plans()
        for chapter in self.chapters(state):
            lf.fixture_complete_chapter(HOST, state, self.workspace, chapter)
        lf.fixture_seal(HOST, state, self.workspace)
        return run, state

    def audited(self):
        run, state = self.sealed()
        claim = controller.claim_step(state, "audit", "machine", "test", self.workspace)
        complete_step(state, state["steps"]["audit"], lf.fixture_set_audit(state, self.workspace), self.workspace, "machine",
                      token=claim["claim_token"])
        return run, state

    def chapter_payload(self, state, chapter, plan, path=None):
        target = lf.chapter_plan_path(state, chapter) if path is None else path
        ws.write_json_atomic(target, plan)
        return {"artifact": str(target), "plan_sha256": ws.plan_sha256(plan)}

    # ---- revision 6 and packaging ----
    def test_revision6_contract_bytes_and_identity_are_unchanged(self):
        for relative in ("src/workflow_contract.json", "codex-skill/video-autopilot/workflow_contract.json"):
            with self.subTest(path=relative):
                self.assertEqual(_text_sha256(ROOT / relative), REVISION6_TEXT_SHA256)
        contract, contract_sha = ws.load_contract(self.skill / "SKILL.md")
        self.assertEqual((contract["contract_revision"], contract_sha), (6, REVISION6_CONTRACT_SHA256))
        _, state = self.create()
        self.assertEqual((state["contract"]["revision"], state["contract"]["sha256"]), (6, REVISION6_CONTRACT_SHA256))

    def test_longform_sources_are_bound_packaged_and_materialized(self):
        from public_workflow_distribution import ADAPTER_FILES, ADAPTER_MODULES, render_forwarder
        from release_integrity import collect_skill_sources
        manifest = ws.read_json(ROOT / "release-manifest.json")
        materialized = dict(collect_skill_sources(ROOT, ROOT / "codex-skill/video-autopilot",
                                                  manifest["codex_skill"]["materialize_from"]))
        for name in LONGFORM_FILES:
            with self.subTest(name=name):
                self.assertIn(name, ws.WORKFLOW_EXECUTABLE_SOURCES)
                self.assertIn(name, ADAPTER_FILES)
                self.assertIn(f"src/{name}", manifest["required_paths"])
                self.assertIn(f"codex-skill/video-autopilot/{name}", manifest["required_paths"])
                self.assertEqual((SRC / name).read_bytes(), materialized[name].read_bytes())
                if name in ADAPTER_MODULES:
                    self.assertEqual(manifest["codex_skill"]["materialize_from"][name], "src/" + name)
                    self.assertEqual((ROOT / "codex-skill/video-autopilot" / name).read_text(encoding="utf-8"),
                                     render_forwarder(name, tuple(ws.WORKFLOW_EXECUTABLE_SOURCES)))
        autopilot = ws.read_json(ROOT / "AUTOPILOT_MANIFEST.json")
        self.assertIn("workflow_longform_contract.json", autopilot["skills"][0]["include"])

    def test_skill_missing_the_session_contract_fails_before_a_run_directory(self):
        (self.skill / "workflow_longform_contract.json").unlink()
        with self.assertRaisesRegex(ws.WorkflowError, "LONGFORM_CONTRACT_MISSING"):
            self.create()
        self.assertFalse((self.workspace / "run").exists())

    # ---- DAG ----
    def test_dag_has_one_set_apply_one_render_and_no_chapter_render(self):
        _, state = self.create()
        steps = state["steps"]
        self.assertEqual([key for key in steps if key.startswith("plan")], ["plan:intro", "plan:demo", "plan"])
        self.assertEqual([step["id"] for step in steps.values() if step["tool"] == lf.APPLY_TOOL], ["apply"])
        self.assertEqual([step["id"] for step in steps.values() if step["tool"] == "render_project"], ["render"])
        self.assertEqual([key for key in steps if "render" in key], ["render"])
        self.assertEqual((steps["plan"]["tool"], steps["plan"]["depends_on"]), (lf.SEAL_TOOL, ["plan:intro", "plan:demo"]))
        self.assertEqual((steps["audit"]["tool"], steps["audit"]["depends_on"]), (lf.AUDIT_TOOL, ["plan"]))
        self.assertEqual((steps["apply"]["retry"], steps["render"]["depends_on"]), ("reconcile_only", ["apply"]))
        self.assertEqual({steps[key]["chapter_key"] for key in ("plan:intro", "plan:demo")}, {"intro", "demo"})
        self.assertEqual([key for key, step in steps.items() if "chapter_key" in step], ["plan:intro", "plan:demo"])
        self.assertEqual(state["contract"]["revision"], 6)
        self.assertEqual(self.chapters(state)[1]["material_keys"], ["m02-clip-b", "m03-clip-c"])

    def test_create_path_is_unchanged(self):
        _, state = ws.create_run(self.workspace, run_id="plain", run_dir_raw="plain", project_raw="project.editkin.json",
                                 output_raw=None, material_values=["clip-a=a.mp4"], max_retries=2, task_class="editorial_plan", priority="quality")
        contract, _ = ws.load_contract()
        self.assertNotIn("longform_session", state["binding"])
        self.assertEqual(list(state["steps"]), list(ws.expand_steps(contract, state["binding"]["materials"], 2)))
        self.assertFalse(any("chapter_key" in step for step in state["steps"].values()))
        self.assertEqual((state["steps"]["plan"]["tool"], state["steps"]["audit"]["tool"]), ("write_v4_plan", "audit_autopilot_plan"))
        request = controller.step_instruction(state, state["steps"]["session"], self.workspace)["request"]
        self.assertEqual(request, {"projectPath": state["binding"]["project_path"]})
        with self.assertRaisesRegex(ws.WorkflowError, "contract limit 32"):
            many = [f"clip-{index}=many/{index}.mp4" for index in range(33)]
            (self.workspace / "many").mkdir()
            for index in range(33):
                (self.workspace / "many" / f"{index}.mp4").write_bytes(b"x")
            ws.create_run(self.workspace, run_id="too-many", run_dir_raw="too-many", project_raw="project.editkin.json",
                          output_raw=None, material_values=many, max_retries=2, task_class="editorial_plan", priority="quality")

    def test_cli_create_longform_has_the_create_flags_plus_session(self):
        subcommands = controller.parser()._subparsers._group_actions[0].choices
        flags = lambda name: set(subcommands[name]._option_string_actions) - {"-h", "--help"}
        self.assertEqual(flags("create-longform"), flags("create") | {"--session"})
        ws.write_json_atomic(self.workspace / "session.json", self.session)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = controller.main(["--workspace", str(self.workspace), "create-longform", "--session", "session.json",
                                    "--project", "project.editkin.json", "--run-dir", "cli-run", "--material", "clip-a=a.mp4",
                                    "--material", "clip-b=b.mp4", "--material", "clip-c=c.mp4"])
        result = json.loads(output.getvalue())
        self.assertEqual((code, result["ok"]), (0, True))
        self.assertIn("plan:demo", ws.load_state(self.workspace / "cli-run", self.workspace)["steps"])

    # ---- session parsing ----
    def test_session_parser_rejects_invalid_sessions(self):
        def session(**changes):
            value = copy.deepcopy(self.session)
            for path, item in changes.items():
                index, field = path.split("__")
                value["chapters"][int(index)][field] = item
            return value
        cases = {
            "overlap": session(**{"1__range": {"startFrame": 299, "endFrame": 900}}),
            "unordered": {"schema": lf.SESSION_SCHEMA, "chapters": list(reversed(self.session["chapters"]))},
            "float": session(**{"0__range": {"startFrame": 0, "endFrame": 300.0}}),
            "empty-range": session(**{"0__range": {"startFrame": 10, "endFrame": 10}}),
            "slug": session(**{"0__chapterId": "Intro Chapter"}),
            "duplicate": session(**{"1__chapterId": "intro"}),
            "unknown-clip": session(**{"0__clipIds": ["clip-z"]}),
            "no-clips": session(**{"0__clipIds": []}),
            "repeat-clip": session(**{"0__clipIds": ["clip-a", "clip-a"]}),
            "extra-key": session(**{"0__note": "x"}),
            "schema": {**self.session, "schema": "other/v1"},
            "too-many": {"schema": lf.SESSION_SCHEMA, "chapters": [
                {"chapterId": f"c{index:02d}", "range": {"startFrame": index * 10, "endFrame": index * 10 + 10}, "clipIds": ["clip-a"]}
                for index in range(17)]},
        }
        for name, value in cases.items():
            with self.subTest(case=name), self.assertRaisesRegex(ws.WorkflowError, "LONGFORM_SESSION"):
                self.create(value, run_dir_raw=f"run-{name}")
            self.assertFalse((self.workspace / f"run-{name}").exists())

    def test_session_material_cap_is_96_for_longform_runs(self):
        (self.workspace / "many").mkdir()
        for index in range(97):
            (self.workspace / "many" / f"{index}.mp4").write_bytes(f"m{index}".encode())
        values = [f"clip-{index}=many/{index}.mp4" for index in range(97)]
        session = {"schema": lf.SESSION_SCHEMA, "chapters": [{"chapterId": "all", "range": {"startFrame": 0, "endFrame": 30}, "clipIds": ["clip-0"]}]}
        with self.assertRaisesRegex(ws.WorkflowError, "contract limit 96"):
            self.create(session, material_values=values)
        _, state = self.create(session, material_values=values[:96], run_dir_raw="run-96")
        self.assertEqual(len(state["binding"]["materials"]), 96)

    # ---- contract capability and session ----
    def test_contract_requires_the_longform_capability_before_material_preparation(self):
        _, state = self.create()
        claim = controller.claim_step(state, "contract", "machine", "test", self.workspace)
        missing = lf.fixture_contract_payload(state)
        del missing["contract"]["longformPlanSet"]
        drifted = lf.fixture_contract_payload(state)
        drifted["contract"]["longformPlanSet"]["maxChapters"] = 32
        for payload, code in [(missing, "LONGFORM_CAPABILITY_MISSING"), (drifted, "LONGFORM_CAPABILITY_MISMATCH")]:
            with self.subTest(code=code), self.assertRaisesRegex(ws.WorkflowError, code):
                complete_step(state, state["steps"]["contract"], lf._wrap(payload), self.workspace, "machine", token=claim["claim_token"])
        self.assertEqual(state["steps"]["contract"]["status"], "running")
        result = complete_step(state, state["steps"]["contract"], lf._wrap(lf.fixture_contract_payload(state)), self.workspace, "machine",
                               token=claim["claim_token"])
        self.assertEqual(result["facts"]["longform_plan_set"]["apply_tool"], lf.APPLY_TOOL)
        claim = controller.claim_step(state, "session", "machine", "test", self.workspace)
        self.assertEqual(claim["instruction"]["request"], {"projectPath": state["binding"]["project_path"], "clipLimit": 100})
        payload = lf.fixture_session_payload(state)
        payload["workflow"].remove(lf.APPLY_TOOL)
        with self.assertRaisesRegex(ws.WorkflowError, "missing tools"):
            complete_step(state, state["steps"]["session"], lf._wrap(payload), self.workspace, "machine", token=claim["claim_token"])

    # ---- chapter plans ----
    def test_chapter_plan_validator_rejections(self):
        _, state = self.to_chapter_plans()
        intro, demo = self.chapters(state)
        step = state["steps"]["plan:intro"]
        facts = lf.validate_chapter_plan(state, step, self.workspace, self.chapter_payload(state, intro, lf.fixture_chapter_plan(state, intro)))
        self.assertEqual((facts["chapter_id"], facts["material_receipt_count"]), ("intro", 2))

        def mutated(change):
            plan = lf.fixture_chapter_plan(state, intro)
            change(plan)
            return plan
        every_receipt = lf.expected_chapter_receipts(state, intro) + lf.expected_chapter_receipts(state, demo)[1:]
        cases = [
            ("receipt subset", "LONGFORM_CHAPTER_RECEIPTS", mutated(lambda p: p["materialEvidence"].update(receipts=p["materialEvidence"]["receipts"][:1]))),
            ("receipt superset", "LONGFORM_CHAPTER_RECEIPTS", mutated(lambda p: p["materialEvidence"].update(receipts=every_receipt))),
            ("non-longform route", "LONGFORM_CHAPTER_ROUTE", mutated(lambda p: p["route"].update(format="shorts"))),
            ("beat outside range", "LONGFORM_CHAPTER_FRAME_OUTSIDE_RANGE",
             mutated(lambda p: p["editorial"]["narrative"]["beats"][0].update(range={"startFrame": 250, "endFrame": 310}))),
            ("graphic outside range", "LONGFORM_CHAPTER_FRAME_OUTSIDE_RANGE",
             mutated(lambda p: p["editorial"]["graphics"][0].update(range={"startFrame": 300, "endFrame": 330}))),
            ("transition at the exclusive end", "LONGFORM_CHAPTER_FRAME_OUTSIDE_RANGE",
             mutated(lambda p: p["editorial"]["transitions"][0].update(atFrame=300))),
            ("impact outside range", "LONGFORM_CHAPTER_FRAME_OUTSIDE_RANGE", mutated(lambda p: p["editorial"]["audio"].update(impactFrames=[900]))),
            ("relink refused", "LONGFORM_V1_RELINK_REFUSED",
             mutated(lambda p: p["commands"].append({"type": "batch", "commands": [{"type": "relink_asset_source"}]}))),
            ("owner revision refused", "LONGFORM_V1_OWNER_REVISION_REFUSED",
             mutated(lambda p: p["commands"].append({"type": "revise_original_motion_scene_graphic"}))),
            ("original source refused", "LONGFORM_V1_ORIGINAL_SOURCES_REFUSED", mutated(lambda p: p.update(originalMotionEvidence={}))),
            ("legacy plan", "Legacy", mutated(lambda p: p.update(schema="hao.video-autopilot.edit-plan/v3"))),
        ]
        for name, code, plan in cases:
            with self.subTest(case=name), self.assertRaisesRegex(ws.WorkflowError, code):
                lf.validate_chapter_plan(state, step, self.workspace, self.chapter_payload(state, intro, plan))
        with self.assertRaisesRegex(ws.WorkflowError, "LONGFORM_CHAPTER_ARTIFACT"):
            payload = self.chapter_payload(state, intro, lf.fixture_chapter_plan(state, intro), Path(state["run_dir"]) / "plan.v4.json")
            lf.validate_chapter_plan(state, step, self.workspace, payload)
        lf.fixture_complete_chapter(HOST, state, self.workspace, intro)
        self.assertEqual(state["steps"]["plan:intro"]["status"], "completed")
        self.assertIsNone(state["plan"]["schema"])  # a chapter never seals state["plan"]

    def test_chapter_instruction_carries_artifact_range_and_clips(self):
        _, state = self.to_chapter_plans()
        claim = controller.claim_step(state, "plan:demo", "machine", "test", self.workspace)
        request = claim["instruction"]["request"]
        self.assertTrue(request["artifactPath"].endswith(str(Path("plans") / "demo.v4.json")))
        self.assertEqual(request["chapter"], {"chapterId": "demo", "range": {"startFrame": 300, "endFrame": 900}, "clipIds": ["clip-b", "clip-c"]})
        self.assertEqual(request["route"], {"format": "longform"})
        self.assertEqual(len(request["materialEvidence"]["receipts"]), 2)

    # ---- set seal ----
    def test_set_seal_is_deterministic_and_rejects_a_tampered_chapter(self):
        _, state = self.to_chapter_plans()
        for chapter in self.chapters(state):
            lf.fixture_complete_chapter(HOST, state, self.workspace, chapter)
        first, second = lf.expected_plan_set(state, self.workspace), lf.expected_plan_set(state, self.workspace)
        self.assertEqual(json_sha256(first, canonical=True), json_sha256(second, canonical=True))
        reordered = {"chapters": first["chapters"], "baseProject": first["baseProject"], "schema": first["schema"]}
        self.assertEqual(ws.plan_sha256(reordered), json_sha256(first, canonical=True))
        self.assertEqual([row["chapterId"] for row in first["chapters"]], ["intro", "demo"])
        path = lf.chapter_plan_path(state, self.chapters(state)[1])
        original = path.read_bytes()
        tampered = json.loads(original)
        tampered["commands"].append({"type": "add_caption", "text": "changed after its receipt"})
        ws.write_json_atomic(path, tampered)
        with self.assertRaisesRegex(ws.WorkflowError, "LONGFORM_CHAPTER_CHANGED"):
            controller.claim_step(state, "plan", "machine", "test", self.workspace)
        self.assertEqual(state["steps"]["plan"]["status"], "pending")
        path.write_bytes(original)
        claim = controller.claim_step(state, "plan", "machine", "test", self.workspace)
        request = claim["instruction"]["request"]
        wrong = copy.deepcopy(request["planSet"])
        wrong["chapters"].reverse()
        ws.write_json_atomic(Path(request["artifactPath"]), wrong)
        with self.assertRaisesRegex(ws.WorkflowError, "LONGFORM_PLAN_SET_MISMATCH"):
            complete_step(state, state["steps"]["plan"], {"artifact": request["artifactPath"], "plan_sha256": ws.plan_sha256(wrong)},
                          self.workspace, "machine", token=claim["claim_token"])
        ws.write_json_atomic(Path(request["artifactPath"]), request["planSet"])
        complete_step(state, state["steps"]["plan"], {"artifact": request["artifactPath"], "plan_sha256": request["planSetSha256"]},
                      self.workspace, "machine", token=claim["claim_token"])
        self.assertEqual((state["plan"]["schema"], state["plan"]["plan_sha256"]), (lf.PLAN_SET_SCHEMA, json_sha256(first, canonical=True)))

    # ---- audit / apply binding ----
    def test_audit_binding_rejections(self):
        _, state = self.sealed()
        claim = controller.claim_step(state, "audit", "machine", "test", self.workspace)
        self.assertEqual(set(claim["instruction"]["request"]), {"projectPath", "planSet"})
        good = lf.fixture_set_audit(state, self.workspace)
        self.assertEqual(_audit(state, good)["audit_receipt"], good["auditReceipt"])

        def receipt_case(change, reseal=True):
            payload = copy.deepcopy(good)
            change(payload["auditReceipt"])
            if reseal:
                payload["auditReceipt"] = lf.fixture_seal_receipt(payload["auditReceipt"])
            return payload
        expired = (datetime.now(timezone.utc) - timedelta(seconds=lf.AUDIT_RECEIPT_MAX_AGE_SECONDS + 60)).isoformat().replace("+00:00", "Z")
        cases = [
            ("wrong base revision", "LONGFORM_AUDIT_BASE_IDENTITY", receipt_case(lambda r: r["project"].update(revision=1))),
            ("wrong base content", "LONGFORM_AUDIT_BASE_IDENTITY", receipt_case(lambda r: r["project"].update(contentSha256="e" * 64))),
            ("wrong chapter sha", "LONGFORM_AUDIT_CHAPTER_SHA", receipt_case(lambda r: r["chapters"][1].update(planSha256="f" * 64))),
            ("wrong chapter range", "LONGFORM_AUDIT_CHAPTERS", receipt_case(lambda r: r["chapters"][0]["range"].update(endFrame=301))),
            ("missing chapter", "LONGFORM_AUDIT_CHAPTERS", receipt_case(lambda r: r["chapters"].pop())),
            ("wrong evidence", "LONGFORM_AUDIT_EVIDENCE", receipt_case(lambda r: r["chapters"][0].update(materialEvidenceSha256="d" * 64))),
            ("wrong receipt schema", "LONGFORM_AUDIT_RECEIPT_SCHEMA", receipt_case(lambda r: r.update(schema="hao.video-autopilot.audit-receipt/v1"))),
            ("single-plan shape", "LONGFORM_AUDIT_RECEIPT_SHAPE", receipt_case(lambda r: r.update(planSha256=r["setSha256"], materialEvidenceSha256="d" * 64))),
            ("wrong set", "LONGFORM_AUDIT_SET", receipt_case(lambda r: r.update(setSha256="c" * 64))),
            ("unsealed checksum", "LONGFORM_AUDIT_CHECKSUM", receipt_case(lambda r: r["project"].update(revision=1), reseal=False)),
            ("expired", "expired", receipt_case(lambda r: r.update(auditedAt=expired))),
        ]
        for name, code, payload in cases:
            with self.subTest(case=name), self.assertRaisesRegex(ws.WorkflowError, code):
                complete_step(state, state["steps"]["audit"], payload, self.workspace, "machine", token=claim["claim_token"])
        top = copy.deepcopy(good)
        top["setSha256"] = "c" * 64
        with self.assertRaisesRegex(ws.WorkflowError, "LONGFORM_AUDIT_SET"):
            complete_step(state, state["steps"]["audit"], top, self.workspace, "machine", token=claim["claim_token"])
        complete_step(state, state["steps"]["audit"], good, self.workspace, "machine", token=claim["claim_token"])
        self.assertEqual(state["steps"]["audit"]["status"], "completed")

    def test_apply_binding_rejections(self):
        _, state = self.audited()
        claim = controller.claim_step(state, "apply", "machine", "test", self.workspace)
        self.assertEqual(set(claim["instruction"]["request"]), {"projectPath", "planSet", "auditReceipt"})
        project = ws.project_file(state, self.workspace)
        original = project.read_bytes()
        committed = project.parent / ".editkin-receipts" / "longform-r1.committed.json"

        def attempt(code, **fixture):
            change = fixture.pop("change", None)
            payload = lf.fixture_set_apply(state, self.workspace, **fixture)
            if change:
                change(payload["receipt"])
                ws.write_json_atomic(committed, payload["receipt"])
            try:
                with self.assertRaisesRegex(ws.WorkflowError, code):
                    complete_step(state, state["steps"]["apply"], payload, self.workspace, "machine", token=claim["claim_token"])
            finally:
                project.write_bytes(original)
                committed.unlink()
        cases = [
            ("revision jump", "exactly one revision", {"revision_step": 2}),
            ("wrong receipt schema", "not for the bound", {"plan_schema": ws.CURRENT_PLAN_SCHEMA}),
            ("wrong base", "LONGFORM_APPLY_BASE", {"before": 5}),
            ("unbound audit", "LONGFORM_APPLY_AUDIT", {"change": lambda r: r["audit"].update(receiptSha256="0" * 64)}),
            ("missing set block", "LONGFORM_APPLY_SET", {"change": lambda r: r.pop("longformSet")}),
        ]
        for name, code, fixture in cases:
            with self.subTest(case=name):
                attempt(code, **fixture)
        complete_step(state, state["steps"]["apply"], lf.fixture_set_apply(state, self.workspace), self.workspace, "machine",
                      token=claim["claim_token"])
        facts = controller.receipt_for(state, "apply")["facts"]
        self.assertEqual((facts["project_revision_before"], facts["project_revision_after"]), (0, 1))
        self.assertEqual(facts["longform_set"]["chapter_count"], 2)

    def test_interrupted_set_apply_lands_in_reconcile_required(self):
        _, state = self.audited()
        controller.claim_step(state, "apply", "machine", "test", self.workspace)
        controller.resume_run(state, self.workspace, None, None)
        self.assertEqual(state["steps"]["apply"]["status"], "reconcile_required")
        with self.assertRaises(ws.WorkflowError):
            controller.claim_step(state, "apply", "machine", "test", self.workspace)
        reconciled = copy.deepcopy(state)
        controller.resume_run(reconciled, self.workspace, "not-applied", None)
        self.assertEqual(reconciled["steps"]["apply"]["status"], "pending")
        controller.resume_run(state, self.workspace, "committed", lf.fixture_set_apply(state, self.workspace))
        self.assertEqual(state["steps"]["apply"]["status"], "completed")
        self.assertEqual(ws.read_json(ws.project_file(state, self.workspace))["revision"], 1)

    # ---- drift ----
    def test_fingerprint_and_binding_drift_are_rejected(self):
        _, state = self.create()
        ws.verify_immutable_sources(state, self.workspace)
        for name in LONGFORM_FILES:
            path = self.skill / name
            original = path.read_bytes()
            path.write_bytes(original + b"\n")
            try:
                with self.subTest(source=name), self.assertRaisesRegex(ws.WorkflowError, "executable source changed"):
                    ws.verify_immutable_sources(state, self.workspace)
            finally:
                path.write_bytes(original)
        tampered = copy.deepcopy(state)
        tampered["binding"]["longform_session"]["chapters"][0]["range"]["endFrame"] = 299
        with self.assertRaisesRegex(ws.WorkflowError, "binding hash is corrupt"):
            ws.verify_immutable_sources(tampered, self.workspace)
        stripped = copy.deepcopy(state)
        del stripped["binding"]["longform_session"]
        with self.assertRaisesRegex(ws.WorkflowError, "binding hash is corrupt"):
            ws.verify_immutable_sources(stripped, self.workspace)
        ws.verify_immutable_sources(state, self.workspace)

    # ---- end to end ----
    def test_full_synthetic_session_verifies_green(self):
        result = lf.selftest(HOST, self.workspace)
        self.assertEqual((result["selftest"], result["one_set_apply"], result["one_render"]), ("GREEN", True, True))
        state = ws.load_state(self.workspace / "videos" / "_AUTOPILOT" / "editkin-v4" / "longform-selftest", self.workspace)
        self.assertEqual((state["status"], state["plan"]["schema"]), ("completed_approved", lf.PLAN_SET_SCHEMA))
        self.assertEqual(verify_run(state, self.workspace)["status"], "GREEN")
        plain = copy.deepcopy(state)
        del plain["binding"]["longform_session"]
        self.assertEqual((_bound_plan_schema(state), _bound_plan_schema(plain)), (lf.PLAN_SET_SCHEMA, ws.CURRENT_PLAN_SCHEMA))

    def test_controller_selftest_cli_runs_the_longform_session(self):
        import subprocess
        environment = {key: value for key, value in os.environ.items() if key != ws.SKILL_PATH_ENV}
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SRC / "workflow_contract.py"), "selftest"],
                                env=environment, capture_output=True, text=True, encoding="utf-8", timeout=120,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)["result"]
        self.assertEqual((report["selftest"], report["longform_session"]["selftest"]), ("GREEN", "GREEN"))
        self.assertTrue(report["longform_session"]["one_set_apply"] and report["longform_session"]["one_render"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
