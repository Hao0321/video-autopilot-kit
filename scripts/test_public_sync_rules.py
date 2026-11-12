"""Public sync rules: reference pointers, maintainer dates and the rewrite rules added in v0.28.0."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "scripts"
REFERENCES = ROOT / "codex-skill" / "video-autopilot" / "references"
sys.path.insert(0, str(HERE))

import sync_canonical  # noqa: E402
from public_sync_support import _copy_public_autopilot_config  # noqa: E402
from public_sync_transforms import (  # noqa: E402
    MODULE_REPLACEMENTS,
    PUBLIC_SHOT_SELECTION_TEXT,
    _SIBLING_MARKDOWN_LINK,
    drop_unshipped_reference_paragraphs as drop,
)

SHIPPED = frozenset({"kept.md", "other.md"})


class UnshippedReferenceFilter(unittest.TestCase):
    def test_paragraph_with_unshipped_link_is_left_out(self) -> None:
        text = ("# Title\n\nUses [kept](kept.md) and [other](./other.md#part \"Other\").\n\n"
                "Details live in [hidden](not-shipped.md).\n\nClosing line.\n")
        self.assertEqual(drop(text, SHIPPED),
                         "# Title\n\nUses [kept](kept.md) and [other](./other.md#part \"Other\").\n\n"
                         "Closing line.\n")

    def test_link_forms_are_detected(self) -> None:
        for link in ("[h](hidden.md)", "[h](./hidden.md)", "[h](hidden.md#a)",
                     "[h](hidden.md \"t\")", "[id]: ./hidden.md"):
            self.assertEqual(drop("Body.\n\n" + link + "\n", SHIPPED), "Body.\n", link)

    def test_trailing_block_and_missing_final_newline(self) -> None:
        self.assertEqual(drop("Body.\n\nSee [x](x.md).\n", SHIPPED), "Body.\n")
        self.assertEqual(drop("Body.\n\nSee [x](x.md).", SHIPPED), "Body.")
        self.assertEqual(drop("See [x](x.md).\n\nBody.\n", SHIPPED), "Body.\n")

    def test_only_the_offending_list_item_table_row_or_definition_goes(self) -> None:
        listing = "- one [k](kept.md)\n- two [x](x.md)\n  continued\n- three\n"
        self.assertEqual(drop(listing, SHIPPED), "- one [k](kept.md)\n- three\n")
        table = "| a | b |\n|---|---|\n| 1 | [k](kept.md) |\n| 2 | [x](x.md) |\n"
        self.assertEqual(drop(table, SHIPPED), "| a | b |\n|---|---|\n| 1 | [k](kept.md) |\n")
        definitions = "[k]: kept.md\n[x]: x.md\n"
        self.assertEqual(drop(definitions, SHIPPED), "[k]: kept.md\n")

    def test_fenced_code_is_never_changed(self) -> None:
        text = "Intro.\n\n```md\nexample [x](x.md)\n\nmore [x](x.md)\n```\n\nEnd.\n"
        self.assertEqual(drop(text, SHIPPED), text)

    def test_text_without_unshipped_links_is_byte_identical(self) -> None:
        for text in ("", "plain\n", "a\n\n\n\n[k](kept.md)\r\n", "external [s](https://example.com/a.md)\n",
                     "nested [n](../other/x.md)\n", "mention `x.md` only\n"):
            self.assertEqual(drop(text, SHIPPED), text)

    def test_sync_copy_applies_the_filter_to_references_only(self) -> None:
        shipped = sorted(sync_canonical._shipped_reference_names())
        self.assertTrue(shipped)
        text = f"Keep [s]({shipped[0]}).\n\nDrop [p](not-a-shipped-reference.md).\n"
        with tempfile.TemporaryDirectory(prefix="ref-pointer-test-") as temp:
            source = Path(temp) / "source.md"
            source.write_text(text, encoding="utf-8")
            reference = Path(temp) / "reference.md"
            sync_canonical._copy_text(
                source, reference, sync_canonical.PUBLIC_REFERENCE_PREFIX + "pointer-fixture.md")
            self.assertEqual(reference.read_text(encoding="utf-8"), f"Keep [s]({shipped[0]}).\n")
            other = Path(temp) / "other.md"
            sync_canonical._copy_text(source, other, "knowledge/pointer-fixture.md")
            self.assertEqual(other.read_text(encoding="utf-8"), text)

    def test_maintainer_dates_leave_comments_or_stop_the_sync(self) -> None:
        cleaned = sync_canonical._transform("x = 1\n    # guard note (2030-01-02).\n", "skill_sync.py")
        self.assertEqual(cleaned, "x = 1\n    # guard note.\n")
        with self.assertRaisesRegex(ValueError, "maintainer change date"):
            sync_canonical._transform('NOTE = "kept in a string (2030-01-02)."\n', "skill_sync.py")
        with self.assertRaisesRegex(ValueError, "maintainer change date"):
            sync_canonical._transform("# moved since 2030-01-02\n", "project_paths.py")

    def test_shot_selection_reference_is_the_fixed_public_text(self) -> None:
        for source in ("# T\n\nIntro line.\n\n## A\n\n1. x\n\n## B\n\n| a | b |\n| --- | --- |\n",
                       "no heading at all\n", ""):
            self.assertEqual(sync_canonical._transform(source, "shot-selection-language.md"),
                             PUBLIC_SHOT_SELECTION_TEXT)
        shipped = (REFERENCES / "shot-selection-language.md").read_text(encoding="utf-8")
        self.assertEqual(shipped, PUBLIC_SHOT_SELECTION_TEXT)
        self.assertEqual(PUBLIC_SHOT_SELECTION_TEXT.count("\n## "), 1)
        self.assertNotRegex(PUBLIC_SHOT_SELECTION_TEXT, r"(?m)^\s*\|")

    def test_shot_selection_guard_stops_the_sync_without_the_rule(self) -> None:
        saved = MODULE_REPLACEMENTS["shot-selection-language.md"]
        MODULE_REPLACEMENTS["shot-selection-language.md"] = ()
        try:
            with self.assertRaisesRegex(ValueError, "fixed public text"):
                sync_canonical._transform("# T\n\nIntro line.\n", "shot-selection-language.md")
        finally:
            MODULE_REPLACEMENTS["shot-selection-language.md"] = saved

    def test_shipped_references_link_only_shipped_siblings(self) -> None:
        shipped = sync_canonical._shipped_reference_names()
        dangling = []
        for path in sorted(REFERENCES.glob("*.md")):
            self.assertIn(path.name, shipped, f"unregistered public reference: {path.name}")
            for match in _SIBLING_MARKDOWN_LINK.finditer(path.read_text(encoding="utf-8")):
                target = match.group(1) or match.group(2)
                if target not in shipped:
                    dangling.append(f"{path.name} -> {target}")
        self.assertEqual(dangling, [])



def _module_rules(name: str, text: str) -> str:
    for pattern, replacement in MODULE_REPLACEMENTS[name]:
        text = pattern.sub(replacement, text)
    return text


class PublicRewriteRules(unittest.TestCase):
    def test_rules_added_in_this_release_fire(self) -> None:
        fallback = "PROJECT_ROOT = discover_project_root(ROOT, required=False) or ROOT.parents[2]\n"
        cases = (
            ("skill_sync.py", '        assert result["declared_files"] >= 180, "x"\n',
             '        assert result["declared_files"] >= 60, "x"\n'),
            ("skill_sync.py", "        # guard note (2030-01-02).\n", "        # guard note.\n"),
            ("project_kernel.py", "    # guard note (2030-01-02). More.\n", "    # guard note. More.\n"),
            ("project_kernel_commands.py", 'ArgumentParser(description="Maintainer Autopilot manifest control plane")\n',
             'ArgumentParser(description="Video Autopilot manifest control plane")\n'),
            ("project_kernel_commands.py", '    env_name = "ABC_KERNEL_SELFTEST_CANONICAL"\n',
             '    env_name = "VA_KERNEL_SELFTEST_CANONICAL"\n'),
            ("project_paths.py", 'os.environ["ABC_PATHS_SELFTEST_SKILL"] = value\n',
             'os.environ["VA_PATHS_SELFTEST_SKILL"] = value\n'),
            ("project_paths.py", "a Skill (the canonical copy lives outside the\n    workspace since 2030-01-02); other",
             "a Skill (for example a canonical Skill kept outside\n    the workspace); other"),
            ("asset_license_governance.py", fallback, fallback.replace("ROOT.parents[2]", "ROOT.parent")),
            ("caption_grouping.py", "        # \u6578\u5b57\u8170\u65ac\uff1a\u4f8b\uff081|2\u842c\u30019.|9%\uff09\n",
             "        # \u6578\u5b57\u8170\u65ac\uff1a\u4f8b\uff083|50\u842c\u30011,|234\u300187.|5%\uff09\n"),
            ("publish_hub_context.py", 'STATE_PATH = HERE / "channel_state.json"\n',
             'STATE_PATH = HERE.parent / "data" / "channel_state.json"\n'),
        )
        for name, before, after in cases:
            self.assertEqual(_module_rules(name, before), after, name)

    def test_code_strings_are_not_rewritten(self) -> None:
        line = 'NOTE = "kept (2030-01-02)."\n'
        self.assertEqual(_module_rules("skill_sync.py", line), line)


class PublicCleanupConfig(unittest.TestCase):
    def _public_reason(self, reason: str) -> str:
        payload = {"exclude": [], "architecture": {"layers": [], "module_hotspot_exceptions": [
            {"path": "project_paths.py", "max_fan_in": 40, "max_out_degree": 0, "reason": reason}]}}
        with tempfile.TemporaryDirectory(prefix="cleanup-config-test-") as temp:
            source = Path(temp) / "audit.config.json"
            source.write_text(json.dumps(payload), encoding="utf-8")
            destination = Path(temp) / "public.json"
            _copy_public_autopilot_config(source, destination)
            rules = json.loads(destination.read_text(encoding="utf-8"))["architecture"]["module_hotspot_exceptions"]
        self.assertEqual([rule["path"] for rule in rules], ["src/project_paths.py"])
        return rules[0]["reason"]

    def test_dated_change_note_is_left_out(self) -> None:
        self.assertEqual(self._public_reason("Stable foundation. 2030-01-02: three modules moved (fan-in 1 -> 2)"),
                         "Stable foundation")
        self.assertEqual(self._public_reason("Stable foundation"), "Stable foundation")

    def test_any_other_dated_reason_stops_the_sync(self) -> None:
        with self.assertRaisesRegex(ValueError, "dated note"):
            self._public_reason("Stable foundation; reviewed 2030-01-02")


if __name__ == "__main__":
    unittest.main()
