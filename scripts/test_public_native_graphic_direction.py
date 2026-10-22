"""Literal public recipe-consumption controls; no private imports or product claims.

CLI children are sequential, directly owned, reaped with communicate(), and their
actual bytes/PIDs are retained for the independent evaluator. Small owned fixture
trees are deliberately retained: this module never deletes a fixture or runs sync.
"""
from __future__ import annotations

import ast
import base64
import copy
import hashlib
import importlib.util
import json
import math
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "codex-skill/video-autopilot"
HERE = ROOT / "scripts"
HELPER = SKILL / "native_graphic_direction.py"
sys.path.insert(0, str(HERE))

TEMPLATES = (
    "strike_reframe", "level_bridge", "comparison_pair", "context_stack",
    "evidence_takeover", "focus_wall", "brand_recap", "kinetic_network",
)
PALETTE = {"surface": "#f7f9fc", "text": "#172033", "accent": "#2a73df",
           "muted": "#56657d", "separator": "#dce5ef"}
AGENT = {"mode": "agent_reference_comparison",
         "authorization": "Synthetic neutral public control authority; not an artifact review."}
CONTROL_NAMES = (
    "test_all_eight_templates_and_both_cadences_have_exact_owned_normalized_values",
    "test_actual_cli_consumes_normalized_direction_in_recipe_not_only_request",
    "test_actual_cli_default_speed_and_finite_boundary_speeds_are_normalized",
    "test_actual_cli_omitted_direction_preserves_recipe_and_context",
    "test_actual_cli_binds_human_and_authorized_agent_without_completed_review",
    "test_actual_cli_rejects_invalid_envelope_and_malformed_direction",
    "test_unknown_nested_fields_and_missing_required_direction_fields_block",
    "test_speed_booleans_nonfinite_and_out_of_range_values_block",
    "test_exact_palette_rgb_keys_and_required_contrast_block_unsafe_values",
    "test_typography_requires_bounded_nonempty_text_and_exact_keys",
    "test_supported_formats_and_whole_board_longform_rejection",
    "test_returned_direction_does_not_alias_input_nested_values",
    "test_helper_real_bytes_bind_source_identity_and_mutation_changes_hash",
    "test_actual_public_owned_regeneration_retains_helper_and_recipe_behavior",
    "test_source_guard_rejects_metadata_only_bridge_and_missing_dependency",
    "test_neutral_import_privacy_and_current_engine_media_only_derivation_floor_remain",
)
CLI_OBSERVATIONS: list[dict] = []
OWNED_FIXTURES: list[Path] = []
FIXTURE_BASE: Path | None = None
EXECUTION_DEADLINE: float | None = None
CAPTURED_BYTES = 0
MAX_CLI_CAPTURE = 256 * 1024
MAX_TOTAL_CAPTURE = 4 * 1024 * 1024
MAX_FIXTURE_BYTES = 16 * 1024 * 1024
_NORMALIZER = None


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def direction(template="brand_recap", cadence="brisk", speed=1):
    return {"templateId": template, "graphicCadence": cadence,
            "style": {"palette": dict(PALETTE),
                      "typography": {"headingFamily": "  Noto Sans TC  ", "bodyFamily": " Fredoka "},
                      "animationSpeed": speed}}


def expected_direction(template="brand_recap", cadence="brisk", speed=1):
    # Literal expectation is independent of the production normalizer.
    return {"templateId": template, "graphicCadence": cadence,
            "style": {"palette": dict(PALETTE),
                      "typography": {"headingFamily": "Noto Sans TC", "bodyFamily": "Fredoka"},
                      "animationSpeed": speed}}


def request(raw=None, *, format="shorts"):
    beat = {"id": "promise", "role": "first_frame", "energy": 0.4, "subject": "Read the point before the handoff"}
    if raw is not None:
        beat["nativeTemplateDirection"] = copy.deepcopy(raw)
    return {"format": format, "domain": "general", "topic": "Original neutral cadence control",
            "duration": 12, "beats": [beat, {"id": "payoff", "role": "payoff", "energy": 0.2,
                                            "subject": "Keep the next information readable"}]}


def load_normalizer():
    global _NORMALIZER
    if _NORMALIZER is None:
        spec = importlib.util.spec_from_file_location("public_native_direction_under_test", HELPER)
        if spec is None or spec.loader is None:
            raise AssertionError("actual public helper cannot be loaded")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _NORMALIZER = module.normalize_native_graphic_direction
    return _NORMALIZER


def source_files(bridge=SKILL / "editkin_design_bridge.py"):
    tree = ast.parse(bridge.read_text(encoding="utf-8-sig"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "SOURCE_FILES" for target in node.targets):
            value = ast.literal_eval(node.value)
            if not isinstance(value, tuple) or not all(isinstance(item, str) for item in value):
                raise AssertionError("SOURCE_FILES is not a literal tuple")
            return value
    raise AssertionError("actual bridge has no SOURCE_FILES")


def owned_fixture(label):
    global FIXTURE_BASE
    if FIXTURE_BASE is None:
        FIXTURE_BASE = Path(tempfile.mkdtemp(prefix="public-native-direction-")).resolve()
        OWNED_FIXTURES.append(FIXTURE_BASE)
    target = FIXTURE_BASE / (str(len(list(FIXTURE_BASE.iterdir()))) + "-" + label)
    target.mkdir(exist_ok=False)
    return target


def fixture_inventory():
    rows, total = [], 0
    for root in OWNED_FIXTURES:
        for path in sorted(root.rglob("*")):
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise AssertionError("owned fixture contains an alias")
            if stat.S_ISREG(info.st_mode):
                data = path.read_bytes(); total += len(data)
                rows.append({"path": str(path.resolve()), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
            elif not stat.S_ISDIR(info.st_mode):
                raise AssertionError("owned fixture contains a nonregular entry")
    if total > MAX_FIXTURE_BYTES:
        raise AssertionError("retained owned fixture bytes exceed 16 MiB")
    return {"roots": [str(root) for root in OWNED_FIXTURES], "bytes": total, "files": rows,
            "retained": True, "cleanupPerformed": False}


def clone_skill(label, *, bridge_bytes=None):
    target = owned_fixture(label) / "video-autopilot"
    target.mkdir()
    for relative in source_files():
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SKILL / relative, destination)
    if bridge_bytes is not None:
        (target / "editkin_design_bridge.py").write_bytes(bridge_bytes)
    fixture_inventory()
    return target


def invoke(actual_request, policy=None, *, skill=SKILL, control="direct_cli"):
    """Observe a direct Python child, never infer closure from a cleared handle."""
    global CAPTURED_BYTES
    if CAPTURED_BYTES >= MAX_TOTAL_CAPTURE:
        raise AssertionError("owned CLI raw evidence budget exhausted before child start")
    arguments = [sys.executable, "-B", "-X", "utf8", str(skill / "editkin_design_bridge.py"),
                 "--request-json", json.dumps(actual_request, ensure_ascii=False, allow_nan=False)]
    if policy is not None:
        arguments += ["--review-policy-json", json.dumps(policy, ensure_ascii=False, allow_nan=False)]
    timeout = 30.0
    if EXECUTION_DEADLINE is not None:
        timeout = min(timeout, EXECUTION_DEADLINE - time.monotonic() - 5.0)
        if timeout <= 0:
            raise AssertionError("evaluator deadline exhausted before CLI child start")
    start = time.monotonic()
    child = subprocess.Popen(arguments, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    timed_out, stdout, stderr, reap_error = False, b"", b"", None
    try:
        stdout, stderr = child.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        if child.poll() is None:
            try:
                child.kill()  # Exact still-owned direct child; no unrelated PID or tree operation.
            except OSError as error:
                reap_error = "owned timeout kill failed: " + repr(error)
        try:
            stdout, stderr = child.communicate(timeout=5)
        except subprocess.TimeoutExpired as error:
            stdout, stderr = error.output or b"", error.stderr or b""
            reap_error = "direct child did not close after the owned kill"
    elapsed = (time.monotonic() - start) * 1000
    count = len(stdout) + len(stderr)
    remaining = max(0, min(MAX_CLI_CAPTURE, MAX_TOTAL_CAPTURE - CAPTURED_BYTES))
    captured_stdout = stdout[:remaining]
    captured_stderr = stderr[:max(0, remaining - len(captured_stdout))]
    CAPTURED_BYTES += len(captured_stdout) + len(captured_stderr)
    truncated = count != len(captured_stdout) + len(captured_stderr)
    observation = {"control": control, "pid": child.pid, "argv": arguments, "timeoutMs": round(timeout * 1000),
                   "elapsedMs": elapsed, "code": child.poll(), "closed": child.returncode is not None,
                   "reaped": child.returncode is not None and reap_error is None, "timedOut": timed_out,
                   "stdoutBytes": len(stdout), "stderrBytes": len(stderr), "truncated": truncated,
                   "stdoutBase64": base64.b64encode(captured_stdout).decode("ascii"),
                   "stderrBase64": base64.b64encode(captured_stderr).decode("ascii"), "reapError": reap_error}
    CLI_OBSERVATIONS.append(observation)
    if timed_out or reap_error or truncated:
        raise AssertionError("actual CLI timeout/reap/raw-byte budget failure: " + control)
    return child.returncode, stdout, stderr


def decode_success(result):
    code, stdout, stderr = result
    if code != 0:
        raise AssertionError("actual CLI failed: " + stderr.decode("utf-8", errors="replace"))
    if stderr:
        raise AssertionError("successful CLI emitted unexpected stderr")
    return json.loads(stdout.decode("utf-8"))


def assert_consumed(brief, expected):
    if brief.get("request", {}).get("beats", [{}])[0].get("nativeTemplateDirection") is None:
        raise AssertionError("directed request metadata is missing")
    recipes = brief.get("recipes")
    if not isinstance(recipes, list) or len(recipes) != 2:
        raise AssertionError("actual recipe pair is missing")
    if recipes[0].get("beatId") != "promise" or recipes[0].get("recipe", {}).get("nativeTemplateDirection") != expected:
        raise AssertionError("recipe did not consume the exact normalized direction")
    if "nativeTemplateDirection" in recipes[1].get("recipe", {}):
        raise AssertionError("undirected payoff silently gained a direction")


def rejection_matrix():
    rows = []
    for key in ("templateId", "graphicCadence", "style"):
        raw = direction(); del raw[key]; rows.append(("missing-" + key, raw))
    for key, value in (("templateId", "retired_slides"), ("graphicCadence", "fast"), ("callerApproved", True)):
        raw = direction(); raw[key] = value; rows.append(("unknown-" + key, raw))
    for value in (True, False, float("nan"), float("inf"), -float("inf"), .49, 2.01, "1", None):
        raw = direction(); raw["style"]["animationSpeed"] = value; rows.append(("bad-speed-" + repr(value), raw))
    for value in ("#fff", "red", "#ffffff00", "#gggggg", None, True):
        raw = direction(); raw["style"]["palette"]["accent"] = value; rows.append(("bad-color-" + repr(value), raw))
    raw = direction(); raw["style"]["palette"]["text"] = PALETTE["surface"]; rows.append(("text-contrast", raw))
    raw = direction(); raw["style"]["palette"]["muted"] = PALETTE["surface"]; rows.append(("muted-contrast", raw))
    for value in ("", "   ", "x" * 81, None, True, ["Noto Sans TC"]):
        raw = direction(); raw["style"]["typography"]["headingFamily"] = value; rows.append(("bad-family-" + repr(value), raw))
    for owner in ("style", "palette", "typography"):
        raw = direction(); target = raw["style"] if owner == "style" else raw["style"][owner]
        target["callerApproval"] = True; rows.append(("unknown-nested-" + owner, raw))
    return rows


def metadata_only_bridge(text):
    tree = ast.parse(text)
    matches = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Name) and target.value.id == "recipe"
                and isinstance(target.slice, ast.Constant) and target.slice.value == "nativeTemplateDirection"
                for target in node.targets):
            matches.append(node)
    if len(matches) != 1:
        raise AssertionError("expected one actual recipe direction assignment")
    node = matches[0]
    lines = text.splitlines(keepends=True)
    indent = lines[node.lineno - 1][:len(lines[node.lineno - 1]) - len(lines[node.lineno - 1].lstrip())]
    lines[node.lineno - 1:node.end_lineno] = [indent + "pass  # controlled metadata-only negative\n"]
    return "".join(lines)


class PublicNativeGraphicDirectionTests(unittest.TestCase):
    def cli(self, raw_request, policy=None, skill=SKILL):
        return invoke(raw_request, policy, skill=skill, control=self._testMethodName)

    def test_all_eight_templates_and_both_cadences_have_exact_owned_normalized_values(self):
        normalize = load_normalizer()
        for template in TEMPLATES:
            for cadence in ("legacy", "brisk", "kinetic"):
                with self.subTest(template=template, cadence=cadence):
                    self.assertEqual(normalize(direction(template, cadence)), expected_direction(template, cadence))

    def test_actual_cli_consumes_normalized_direction_in_recipe_not_only_request(self):
        for template, cadence in (("brand_recap", "brisk"), ("comparison_pair", "legacy"),
                                  ("kinetic_network", "kinetic")):
            brief = decode_success(self.cli(request(direction(template, cadence)), AGENT))
            assert_consumed(brief, expected_direction(template, cadence))
            self.assertEqual(brief["request"], request(direction(template, cadence)))

    def test_actual_cli_default_speed_and_finite_boundary_speeds_are_normalized(self):
        for speed in (None, .5, 2):
            raw = direction()
            if speed is None: del raw["style"]["animationSpeed"]
            else: raw["style"]["animationSpeed"] = speed
            brief = decode_success(self.cli(request(raw)))
            assert_consumed(brief, expected_direction(speed=1 if speed is None else speed))

    def test_actual_cli_omitted_direction_preserves_recipe_and_context(self):
        omitted = decode_success(self.cli(request(), AGENT))
        directed = decode_success(self.cli(request(direction()), AGENT))
        recipes = copy.deepcopy(directed["recipes"])
        del recipes[0]["recipe"]["nativeTemplateDirection"]
        self.assertEqual(recipes, omitted["recipes"])
        self.assertEqual(directed["context"], omitted["context"])
        self.assertEqual(directed["reviewPolicy"], omitted["reviewPolicy"])
        self.assertEqual(directed["reviewPolicySha256"], omitted["reviewPolicySha256"])
        self.assertTrue(all("nativeTemplateDirection" not in row["recipe"] for row in omitted["recipes"]))

    def test_actual_cli_binds_human_and_authorized_agent_without_completed_review(self):
        for policy, expected, actor in ((None, {"mode": "human"}, "human"),
                ({**AGENT, "authorization": "  " + AGENT["authorization"] + "  "}, AGENT, "agent")):
            brief = decode_success(self.cli(request(direction()), policy))
            review = brief["context"]["review"]
            self.assertEqual(brief["reviewPolicy"], expected)
            self.assertEqual(brief["reviewPolicySha256"], digest(expected))
            self.assertEqual(review["policy"], expected)
            self.assertEqual(review["policySha256"], digest(expected))
            self.assertEqual(review["actor"], actor)
            self.assertEqual(review["checkpoint"], "agent_review" if actor == "agent" else "human_review")
            self.assertTrue(review["required"]); self.assertFalse(review["completed"])
            self.assertIn("continuous_motion", review["requirements"])
            self.assertNotIn("learning", brief["context"]); self.assertNotIn("craft", brief["context"])

    def test_actual_cli_rejects_invalid_envelope_and_malformed_direction(self):
        raw = direction(); raw["style"]["animationSpeed"] = True
        for requested, policy in ((request(raw), AGENT), (request(direction()), {"mode": "agent_reference_comparison"})):
            code, stdout, stderr = self.cli(requested, policy)
            self.assertNotEqual(code, 0); self.assertEqual(stdout, b""); self.assertTrue(stderr)

    def test_unknown_nested_fields_and_missing_required_direction_fields_block(self):
        normalize = load_normalizer()
        for label, raw in rejection_matrix():
            if label.startswith(("missing-", "unknown-")):
                with self.subTest(label=label), self.assertRaises(ValueError): normalize(raw)
        for raw in (None, [], "brand_recap", {"templateId": "brand_recap"}):
            with self.subTest(raw=raw), self.assertRaises(ValueError): normalize(raw)
        raw = direction(); del raw["style"]["palette"]
        with self.assertRaises(ValueError): normalize(raw)
        raw = direction(); del raw["style"]["typography"]
        with self.assertRaises(ValueError): normalize(raw)

    def test_speed_booleans_nonfinite_and_out_of_range_values_block(self):
        for label, raw in rejection_matrix():
            if label.startswith("bad-speed-"):
                with self.subTest(label=label), self.assertRaises(ValueError): load_normalizer()(raw)

    def test_exact_palette_rgb_keys_and_required_contrast_block_unsafe_values(self):
        for label, raw in rejection_matrix():
            if label.startswith("bad-color-") or label in ("text-contrast", "muted-contrast", "unknown-nested-palette"):
                with self.subTest(label=label), self.assertRaises(ValueError): load_normalizer()(raw)
        raw = direction(); del raw["style"]["palette"]["separator"]
        with self.assertRaises(ValueError): load_normalizer()(raw)

    def test_typography_requires_bounded_nonempty_text_and_exact_keys(self):
        for label, raw in rejection_matrix():
            if label.startswith("bad-family-") or label == "unknown-nested-typography":
                with self.subTest(label=label), self.assertRaises(ValueError): load_normalizer()(raw)
        raw = direction(); del raw["style"]["typography"]["bodyFamily"]
        with self.assertRaises(ValueError): load_normalizer()(raw)
        raw = direction(); raw["style"]["typography"]["headingFamily"] = "x" * 80
        self.assertEqual(load_normalizer()(raw)["style"]["typography"]["headingFamily"], "x" * 80)

    def test_supported_formats_and_whole_board_longform_rejection(self):
        for format in ("shorts", "reels", "vlog", "ai_short_drama"):
            self.assertEqual(load_normalizer()(direction(), format=format), expected_direction())
        for format in ("longform", "podcast", "interview", "unknown", None, True, 12):
            with self.subTest(format=format), self.assertRaises(ValueError): load_normalizer()(direction(), format=format)
        code, stdout, stderr = self.cli(request(direction(), format="longform"), AGENT)
        self.assertNotEqual(code, 0); self.assertEqual(stdout, b""); self.assertIn(b"whole-board", stderr)
        plain = decode_success(self.cli(request(format="longform"), AGENT))
        self.assertTrue(all("nativeTemplateDirection" not in row["recipe"] for row in plain["recipes"]))

    def test_returned_direction_does_not_alias_input_nested_values(self):
        raw = direction(); original = copy.deepcopy(raw)
        normalized = load_normalizer()(raw)
        self.assertEqual(raw, original)
        raw["style"]["palette"]["accent"] = "#000000"
        raw["style"]["typography"]["headingFamily"] = "changed"
        self.assertEqual(normalized, expected_direction())
        normalized["style"]["palette"]["text"] = "#ffffff"
        self.assertEqual(raw["style"]["palette"]["text"], PALETTE["text"])

    def test_helper_real_bytes_bind_source_identity_and_mutation_changes_hash(self):
        cloned = clone_skill("dependency-mutation")
        before = decode_success(self.cli(request(direction()), AGENT, cloned))
        dependency = cloned / "native_graphic_direction.py"
        before_sha = hashlib.sha256(dependency.read_bytes()).hexdigest()
        self.assertEqual({row["path"]: row["sha256"] for row in before["sources"]}[dependency.name], before_sha)
        self.assertEqual(before["sourceSha256"], digest(before["sources"]))
        dependency.write_bytes(dependency.read_bytes() + b"\n# Owned neutral dependency byte-drift control.\n")
        after = decode_success(self.cli(request(direction()), AGENT, cloned))
        self.assertNotEqual(before["sourceSha256"], after["sourceSha256"])
        self.assertEqual(before["recipes"], after["recipes"])
        self.assertEqual(before["reviewPolicySha256"], after["reviewPolicySha256"])
        for brief in (before, after):
            self.assertTrue(any(row["path"] == "native_graphic_direction.py" for row in brief["sources"]))

    def test_actual_public_owned_regeneration_retains_helper_and_recipe_behavior(self):
        from public_sync_inventory import PUBLIC_OWNED_PATHS
        from sync_canonical import _copy_public_owned, sync_expected_output_paths
        destination = owned_fixture("owned-regeneration")
        copied = _copy_public_owned(ROOT, destination)
        helper_relative = "codex-skill/video-autopilot/native_graphic_direction.py"
        self.assertIn(helper_relative, PUBLIC_OWNED_PATHS)
        self.assertIn(helper_relative, sync_expected_output_paths())
        self.assertEqual(copied, list(PUBLIC_OWNED_PATHS))
        self.assertEqual((destination / helper_relative).read_bytes(), HELPER.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8"))
        skill = destination / "codex-skill/video-autopilot"
        for relative in source_files():
            target = skill / relative
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(SKILL / relative, target)
        regenerated = decode_success(self.cli(request(direction()), AGENT, skill))
        assert_consumed(regenerated, expected_direction())
        actual = decode_success(self.cli(request(direction()), AGENT))
        self.assertEqual(regenerated["recipes"], actual["recipes"])
        self.assertEqual(regenerated["context"], actual["context"])
        self.assertFalse((skill / "workflow_original_sources.py").exists())
        for row in regenerated["sources"]:
            self.assertEqual(row["sha256"], hashlib.sha256((skill / row["path"]).read_bytes()).hexdigest())
        fixture_inventory()

    def test_source_guard_rejects_metadata_only_bridge_and_missing_dependency(self):
        from sync_canonical import _assert_public_design_bridge_contract, _assert_public_native_direction_helper, _copy_public_owned
        text = (SKILL / "editkin_design_bridge.py").read_text(encoding="utf-8-sig")
        _assert_public_design_bridge_contract(text)
        metadata_only = metadata_only_bridge(text)
        missing_dependency = text.replace('    "native_graphic_direction.py",\n', "")
        self.assertNotEqual(missing_dependency, text)
        for invalid in (metadata_only, missing_dependency):
            with self.assertRaises(ValueError): _assert_public_design_bridge_contract(invalid)
        distribution = owned_fixture("metadata-only-distribution")
        from public_adapter_test_support import owned_source_fixture
        owned_source_fixture(ROOT, distribution)
        bridge = distribution / "codex-skill/video-autopilot/editkin_design_bridge.py"
        bridge.write_text(metadata_only, encoding="utf-8")
        shutil.copyfile(HELPER, bridge.parent / HELPER.name)
        target = owned_fixture("metadata-only-target")
        with self.assertRaises(ValueError): _copy_public_owned(distribution, target)
        self.assertEqual(list(target.rglob("*")), [])
        with self.assertRaises(ValueError): _assert_public_native_direction_helper("def normalize_native_graphic_direction(raw, *, format='shorts'):\n    return raw\n")

    def test_neutral_import_privacy_and_current_engine_media_only_derivation_floor_remain(self):
        from sync_canonical import PUBLIC_WORKFLOW_ADAPTERS, _assert_public_workflow_derivation
        text = HELPER.read_text(encoding="utf-8")
        tree = ast.parse(text)
        imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imports |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        self.assertLessEqual(imports, {"__future__", "math", "re"})
        self.assertNotIn(chr(67) + ":/" + "Users/", text); self.assertNotIn(chr(67) + ":" + chr(92) + "Users" + chr(92), text)
        self.assertNotIn(".codex/skills", text); self.assertNotIn("film_quality_learning", text)
        self.assertNotIn("open", {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)})
        canonical = owned_fixture("synthetic-public-controller")
        from public_adapter_test_support import canonical_adapter_fixture
        with canonical_adapter_fixture(ROOT, canonical) as source:
            _assert_public_workflow_derivation(source, ROOT)
            changed = source / "workflow_state.py"
            changed.write_bytes(changed.read_bytes() + b"\n# Controlled unregistered adapter delta.\n")
            with self.assertRaisesRegex(ValueError, "canonical analogue changed"):
                _assert_public_workflow_derivation(source, ROOT)
        contract = json.loads((ROOT / "src/workflow_contract.json").read_text(encoding="utf-8"))
        floor = contract["engine_continuity_floor"]
        self.assertEqual(contract["contract_revision"], 6)
        self.assertEqual(floor["projectSchemas"], [9]); self.assertEqual(floor["planSchema"], "hao.video-autopilot.edit-plan/v4")
        self.assertEqual(floor["textPreparation"], "physical-glyph-binary/v1")
        self.assertEqual(floor["templateAuthoring"], "async-generation2")
        self.assertEqual(floor["floatingFrame"]["schema"], "editkin.floating-video-frame/v2")
        self.assertEqual(floor["floatingFrame"]["mediaFit"], "contain")
        self.assertFalse((ROOT / "src/workflow_original_sources.py").exists())
        fixture_inventory()


if __name__ == "__main__":
    EXECUTION_DEADLINE = time.monotonic() + 90
    unittest.main()
