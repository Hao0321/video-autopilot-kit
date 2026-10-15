"""Zero-dependency regression and malformed-input tests for issues #15/#16."""
from __future__ import annotations

import ast
import builtins
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "longform_maker"))
from shorts_gate import assert_shorts, gate_shorts  # noqa: E402
from shorts_gate_validation import CAPTION_COLOR_KEYS  # noqa: E402


class ShortsGateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="shorts-gate-input-")
        self.addCleanup(self.directory.cleanup)
        self.clip = Path(self.directory.name) / "clip.mp4"
        self.clip.write_bytes(b"synthetic stand-in; no decoding")
        self.spec = {
            "name": "fixture", "place": "P", "what": "W", "addr": "A",
            "segs": [(str(self.clip), 4.0, 2.0), (str(self.clip), 8.0, 3.2),
                     (str(self.clip), 12.0, 3.2), (str(self.clip), 16.0, 3.4),
                     (str(self.clip), 2.4, 1.6)],
            "caps_by_seg": [(0, [("P", "gold")], "hook"), (0, [("W", "white")], "sub"),
                            (1, [("one", "white")], "sub"), (2, [("two", "white")], "sub"),
                            (3, [("end", "white")], "sub")],
        }

    def blocked(self, spec, token=None):
        ok, report = gate_shorts(spec)
        self.assertIs(ok, False)
        self.assertIs(report["ok"], False)
        self.assertTrue(report["fails"])
        self.assertIsInstance(report["warns"], list)
        self.assertTrue(all(isinstance(message, str) for message in report["fails"]))
        json.dumps(report, allow_nan=False)
        if token:
            self.assertTrue(any(token in message for message in report["fails"]), report)
        return report

    def test_reported_missing_segs(self):
        spec = {"name": "x", "platform": "yt_shorts", "place": "P", "what": "W",
                "addr": "A", "caps_by_seg": [], "loop_policy": "forbidden",
                "persistent_label_policy": "required", "bgm_folder": "_x"}
        self.assertIn("required: segs", self.blocked(spec)["fails"])

    def test_missing_fields_and_wrong_top_level(self):
        for key in ("place", "what", "addr", "segs", "caps_by_seg"):
            with self.subTest(key=key):
                spec = copy.deepcopy(self.spec)
                del spec[key]
                self.blocked(spec, key)
        for spec in (None, [], (), "spec", 1, True):
            with self.subTest(type=type(spec).__name__):
                self.blocked(spec, "spec")
                with self.assertRaisesRegex(AssertionError, "Shorts gate FAIL"):
                    assert_shorts(spec)

    def test_invalid_identity_and_policy_types(self):
        for key in ("place", "what", "addr", "platform", "loop_policy",
                    "persistent_label_policy", "name", "location_chip"):
            for value in (None, [], {}, True, 1, " "):
                with self.subTest(key=key, value=value):
                    self.blocked(dict(self.spec, **{key: value}), key)

    def test_segment_shapes_paths_and_times(self):
        for segs in (None, [], "segments", {}, 1, [None], [()], [("x", 0)], [("x", 0, 2, 3)]):
            with self.subTest(segs=segs):
                self.blocked(dict(self.spec, segs=segs), "segs")
        for source in (None, 1, True, {}, [], "", "nul\x00path", b"path"):
            with self.subTest(source=source):
                self.blocked(dict(self.spec, segs=[(source, 0, 14)]), "source")
        for value in (None, "1", True, [], {}, -1, float("nan"), float("inf"), -float("inf"), 10**1000):
            for slot in (1, 2):
                with self.subTest(slot=slot, type=type(value).__name__):
                    row = [str(self.clip), 0, 14]
                    row[slot] = value
                    self.blocked(dict(self.spec, segs=[row]), "segs")
        self.blocked(dict(self.spec, segs=[(str(self.clip), 0, 0)]), "duration")
        huge = [(str(self.clip), 0, 1e308), (str(self.clip), 0, 1e308)]
        self.blocked(dict(self.spec, segs=huge), "total segment duration")
        self.blocked(dict(self.spec, segs=[(str(self.clip), 1e308, 1e308)]), "endpoint")

    def test_caption_structure_and_indexes(self):
        for captions in (None, "captions", {}, 1, [None], [()], [(0, [])]):
            with self.subTest(captions=captions):
                self.blocked(dict(self.spec, caps_by_seg=captions), "caps_by_seg")
        for index in (-1, 5, 0.0, True, "0", None, [], {}):
            with self.subTest(index=index):
                self.blocked(dict(self.spec, caps_by_seg=[(index, [("P", "white")], "sub")]), "S-F")
        for blocks in (None, [], "text", {}, [None], [("P",)], [("P", "white", "extra")],
                       [(None, "white")], [("P", [])], [("", "white")], [("P", " ")]):
            with self.subTest(blocks=blocks):
                self.blocked(dict(self.spec, caps_by_seg=[(0, blocks, "hook")]), "blocks")
        for kind in (None, [], {}, 1):
            self.blocked(dict(self.spec, caps_by_seg=[(0, [("P", "white")], kind)]), "kind")

    def test_optional_structure_and_evidence_types(self):
        for key in ("evidence", "battle_matchup", "battle_edit_contract", "tracked_graphics", "battle_result"):
            for value in ([], "data", 1, False):
                with self.subTest(key=key, value=value):
                    self.blocked(dict(self.spec, **{key: value}), key)
        malformed = [
            {"evidence": {"claim": None}}, {"evidence": {"claim": True}},
            {"battle_matchup": {"left": "name"}},
            {"battle_matchup": {"left": {"name": None}}},
            {"battle_edit_contract": {"showcase_segments": "0"}},
            {"battle_edit_contract": {"showcase_segments": [0, "1"]}},
            {"battle_edit_contract": {"result_segments": [True]}},
            {"battle_edit_contract": {"result_segments": [-1]}},
            {"battle_edit_contract": {"result_segments": [5]}},
            {"battle_edit_contract": {"result_once": "false"}},
            {"tracked_graphics": {"tracked_labels": [None]}},
            {"tracked_graphics": {"tracked_labels": [{"text": "P", "evidence": None}]}},
            {"tracked_graphics": {"mask_sheens": ["sheen"]}},
            {"tracked_graphics": {"hud": {"items": [None]}}},
            {"battle_result": {"human_verified": "false"}},
            {"battle_result": {"evidence": {"sequence_reviewed": "false"}}},
            {"battle_result": {"evidence": {"confidence": float("nan")}}},
        ]
        for index, updates in enumerate(malformed):
            with self.subTest(case=index):
                self.blocked(dict(self.spec, **updates), "invalid:")

    def test_packing_is_a_block_even_without_name(self):
        spec = dict(self.spec, caps_by_seg=self.spec["caps_by_seg"] + [(1, [("x", "white")], "sub")] * 20)
        del spec["name"]
        self.blocked(spec, "S-F")
        with self.assertRaisesRegex(AssertionError, "Shorts gate FAIL"):
            assert_shorts(spec)

    def test_invalid_structure_stops_before_media_io(self):
        with patch("shorts_gate_validation.os.path.isfile") as file_check:
            spec = dict(self.spec, segs=[(str(self.clip), 0, float("nan"))])
            self.blocked(spec)
            file_check.assert_not_called()

    def test_valid_inputs_and_real_rule_failures(self):
        original = copy.deepcopy(self.spec)
        ok, report = gate_shorts(self.spec)
        self.assertIs(ok, True)
        self.assertEqual(self.spec, original)
        self.assertTrue(report["caps"])
        ready = assert_shorts(self.spec)
        self.assertTrue(any(caption[3] == "addr" for caption in ready["caps"]))
        spec = copy.deepcopy(self.spec)
        spec["segs"] = tuple((self.clip, start, duration) for _source, start, duration in spec["segs"])
        del spec["name"]
        self.assertIs(gate_shorts(spec)[0], True)
        del spec["addr"]
        spec["persistent_label_policy"] = "omit"
        self.assertIs(gate_shorts(spec)[0], True)
        self.blocked(dict(self.spec, platform="unknown"), "S-B")
        self.blocked(dict(self.spec, loop_policy="unknown"), "S-D")
        self.blocked(dict(self.spec, caps_by_seg=[]), "S-A")
        missing_file = [(str(self.clip) + ".missing", start, duration)
                        for _source, start, duration in self.spec["segs"]]
        self.blocked(dict(self.spec, segs=missing_file), "素材不存在")
        risky = copy.deepcopy(self.spec)
        risky["caps_by_seg"][1] = (0, [("全部", "white")], "sub")
        self.blocked(risky, "S-P")
        self.assertIs(gate_shorts(dict(risky, evidence={"全部": "synthetic reviewed frame"}))[0], True)

    def test_malformed_advisory_scan_does_not_crash(self):
        sidecar = self.clip.parent / "_scan.json"
        payloads = [[], {"clips": None}, {"clips": [None]}, {"clips": [{"rows": [None]}]},
                    {"clips": [{"rows": [{"bright": "128"}]}]},
                    {"clips": [{"rows": [{"sharp": []}]}]},
                    {"clips": [{"rows": [{"t": float("nan")}]}]}]
        for payload in payloads:
            with self.subTest(payload=payload):
                sidecar.write_text(json.dumps(payload), encoding="utf-8")
                self.assertIs(gate_shorts(self.spec)[0], True)

    def test_color_contract_matches_renderer_without_executing_it(self):
        renderer = ROOT / "src" / "silent_vlog_maker" / "shorts_vertical.py"
        tree = ast.parse(renderer.read_text(encoding="utf-8"))
        palettes = {}
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in {"COLOR_VARIETY", "COLOR_ALIAS"}:
                        palettes[target.id] = ast.literal_eval(node.value)
        self.assertEqual(CAPTION_COLOR_KEYS, set(palettes["COLOR_VARIETY"]) | set(palettes["COLOR_ALIAS"]))
        spec = copy.deepcopy(self.spec)
        spec["caps_by_seg"][0] = (0, [("P", "white")], "hook")
        for key in CAPTION_COLOR_KEYS:
            with self.subTest(color=key):
                spec["caps_by_seg"][-1] = (3, [("end", key)], "sub")
                self.assertIs(gate_shorts(spec)[0], True)
        spec["caps_by_seg"][-1] = (3, [("end", "unknown-color")], "sub")
        self.blocked(spec, "顏色鍵")

    def test_gate_never_imports_the_media_package(self):
        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name.startswith("silent_vlog_maker"):
                raise AssertionError("pure gate imported the media package")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", guarded_import):
            self.assertIs(gate_shorts(self.spec)[0], True)

    def test_example_without_site_packages_from_another_directory(self):
        environment = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        result = subprocess.run([sys.executable, "-S", str(ROOT / "examples" / "04_shorts_gate.py")],
                                cwd=self.directory.name, env=environment, capture_output=True,
                                text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for verdict in ("1) BROKEN spec -> BLOCK", "2) FIXED spec -> PASS",
                        "3) 31s spec on yt_shorts -> BLOCK", "4) same 31s spec on ig_reels -> PASS"):
            self.assertIn(verdict, result.stdout)


if __name__ == "__main__":
    unittest.main()
