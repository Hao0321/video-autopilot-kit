"""Public sync rules: reference pointers, maintainer dates, provenance and the rewrite rules (v0.28.0, v0.28.1)."""
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
from public_sync_renderers import _validate_broll_interface  # noqa: E402
from public_sync_support import _copy_public_autopilot_config  # noqa: E402
import public_privacy_legacy  # noqa: E402
from public_reference_filter import (  # noqa: E402
    _SIBLING_MARKDOWN_LINK,
    drop_unshipped_reference_paragraphs as drop,
    leftover_pointers,
)
from public_sync_transforms import (  # noqa: E402
    MODULE_REPLACEMENTS,
    PRIVACY_PATTERNS,
    PUBLIC_SHOT_SELECTION_TEXT,
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

    def test_fenced_code_without_commands_is_unchanged(self) -> None:
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

    def test_inline_code_pointers_to_private_or_unshipped_files_are_left_out(self) -> None:
        private = frozenset({"private-notes.md"})
        modules = frozenset({"shipped_tool.py"})
        text = ("1. First step `shipped_tool.py`.\n"
                "   - nested `references/not-shipped.md` pointer\n"
                "   - nested kept line\n"
                "2. Second step `private_tool.py`.\n"
                "3. Third step.\n\n"
                "Mentions `private-notes.md` here.\n\nKeeps `config.example.json` output names.\n")
        self.assertEqual(drop(text, SHIPPED, private, modules),
                         "1. First step `shipped_tool.py`.\n   - nested kept line\n2. Third step.\n\n"
                         "Keeps `config.example.json` output names.\n")
        self.assertEqual(drop("Uses `references/kept.md`.\n", SHIPPED, private, modules),
                         "Uses `references/kept.md`.\n")

    def test_prose_goes_by_paragraph_and_other_pointer_forms_count(self) -> None:
        private = frozenset({"private_tool.py"})
        modules = frozenset({"shipped_tool.py"})
        # A paragraph goes whole: no sentence is cut out of the middle of a thought.
        self.assertEqual(drop("Keep.\n\nFirst sentence. Then `private_tool.run()` does it. Last.\n", SHIPPED,
                              private, modules), "Keep.\n")
        for pointer in ("`python private_tool.py selftest`", "`other-program/render.tsx`",
                        "`private_tool.plan(x)`", "`scripts/unshipped_helper.py`"):
            self.assertEqual(drop("Keep.\n\nUses " + pointer + ".\n", SHIPPED, private, modules), "Keep.\n", pointer)
        self.assertEqual(drop("Keep `shipped_tool.run()` and `config.example.json`.\n", SHIPPED, private, modules),
                         "Keep `shipped_tool.run()` and `config.example.json`.\n")

    def test_commands_for_unshipped_modules_and_emptied_headings_go(self) -> None:
        modules = frozenset({"shipped_tool.py"})
        text = ("# T\n\n## Already empty\n\n## Run\n\n```bash\npython scripts/unshipped_helper.py --x\n```\n\n"
                "## Keep\n\n```bash\npython src/shipped_tool.py selftest\n```\n")
        self.assertEqual(drop(text, SHIPPED, frozenset(), modules),
                         "# T\n\n## Already empty\n\n## Keep\n\n```bash\npython src/shipped_tool.py selftest\n```\n")
        self.assertEqual(drop("## Notes\nUses `unshipped_helper.py`.\n\n## Next\n\nKeep.\n", SHIPPED, frozenset(),
                              modules), "## Next\n\nKeep.\n")

    def test_only_the_unshipped_commands_leave_a_fence(self) -> None:
        modules = frozenset({"shipped_tool.py"})
        private = frozenset({"private_planner.py"})
        mixed = ("```bash\npython shipped_tool.py audit\n\n# then the private step:\npython private_planner.py x\n\n"
                 "python shipped_tool.py selftest\n```\n")
        self.assertEqual(drop(mixed, SHIPPED, private, modules),
                         "```bash\npython shipped_tool.py audit\n\npython shipped_tool.py selftest\n```\n")
        shared = "```bash\n# both steps:\npython private_planner.py x\npython shipped_tool.py y\n```\n"
        self.assertEqual(drop(shared, SHIPPED, private, modules),
                         "```bash\n# both steps:\npython shipped_tool.py y\n```\n")
        for line in ("python -X utf8 scripts/unshipped_helper.py", "python src\\unshipped_helper.py a",
                     'python3 "unshipped_helper.py"', "python -m private_planner run"):
            self.assertEqual(drop("```bash\n" + line + "\npython shipped_tool.py y\n```\n", SHIPPED, private, modules),
                             "```bash\npython shipped_tool.py y\n```\n", line)
        chained = "```bash\ncd work &&\npython private_planner.py x\npython shipped_tool.py y\n```\n"
        self.assertEqual(drop("Keep.\n\n" + chained, SHIPPED, private, modules), "Keep.\n")
        javascript = "```js\nimport private_planner from './x.js'\n```\n"
        self.assertEqual(drop(javascript, SHIPPED, private, modules), javascript)
        for fence in ("```python\nfrom private_planner import plan\nplan()\n```\n",
                      "```bash\npython private_planner.py \\\n  --x 1\npython shipped_tool.py a\n```\n"):
            self.assertEqual(drop("Keep.\n\n" + fence, SHIPPED, private, modules), "Keep.\n", fence)
        stdlib = "```python\nimport json\nfrom pathlib import Path\n```\n"
        self.assertEqual(drop(stdlib, SHIPPED, private, modules), stdlib)

    def test_intro_line_stays_with_its_remaining_items(self) -> None:
        modules = frozenset({"shipped_tool.py"})
        self.assertEqual(drop("Steps:\n- `shipped_tool.py`\n- `unshipped_helper.py`\n", SHIPPED, frozenset(),
                              modules), "Steps:\n- `shipped_tool.py`\n")
        self.assertEqual(drop("Keep.\n\nSteps:\n- `unshipped_helper.py`\n", SHIPPED, frozenset(), modules),
                         "Keep.\n")

    def test_markdown_structure_survives_the_filter(self) -> None:
        modules = frozenset({"shipped_tool.py"})

        def check(source: str, expected: str) -> None:
            self.assertEqual(drop(source, SHIPPED, frozenset(), modules), expected, source)

        # An intro whose code block went goes with it; the next paragraph is not glued on.
        check("Para.\n\nRun this:\n```bash\npython gone_tool.py\n```\n\nKeep.\n", "Para.\n\nKeep.\n")
        check("Steps:\n\n- `gone_tool.py`\n\nKeep.\n", "Keep.\n")
        check("Intro.\n```bash\npython gone_tool.py\n```\nNext.\n", "Intro.\n\nNext.\n")
        # A heading that itself points at something missing takes its section with it.
        check("## A\n\nok\n\n## Run `gone_tool.py`\n\nBody text.\n\n### Sub\n\nMore.\n\n## B\n\nb\n",
              "## A\n\nok\n\n## B\n\nb\n")
        # Loose lists: a dropped item takes its continuation paragraph; numbering closes up, restarts stay.
        check("- a\n- b `gone_tool.py`\n\n  continuation of b\n- c\n", "- a\n- c\n")
        check("1. a\n\n2. b `gone_tool.py`\n\n3. c\n", "1. a\n\n2. c\n")
        check("1. a\n2. `gone_tool.py`\n3. c\n\n1. x\n2. y\n", "1. a\n2. c\n\n1. x\n2. y\n")
        # An intro directly above a table keeps the table minus the offending row.
        check("Summary:\n| a | b |\n|---|---|\n| 1 | ok |\n| 2 | `gone_tool.py` |\n",
              "Summary:\n| a | b |\n|---|---|\n| 1 | ok |\n")

    def test_what_counts_as_a_pointer(self) -> None:
        private = frozenset({"kernel.py", "private_notes.md"})
        modules = frozenset({"shipped_tool.py"})
        for word in ("`kernel.run()`",
                     "`private_notes.md`", "`render.tsx`"):
            self.assertEqual(drop("Keep.\n\nUses " + word + ".\n", SHIPPED, private, modules), "Keep.\n", word)
        for word in ("`kernel`", "`kernel/`", "`*.py`", "`.ts`", "`{aspect}_{profile}.py`", "`kernel.json`", "`os.path`", "`videos/_INBOX/vertical`",
                     "`assets/index.json`", "`community/kit/assets/manifest.json`", "`clip_tool.run`"):
            text = "Uses " + word + ".\n"
            self.assertEqual(drop(text, SHIPPED, private, modules), text, word)
        self.assertEqual(drop("Keep.\n\nSee [x](<hidden.md>).\n", SHIPPED), "Keep.\n")

    def test_headings_intros_and_items_that_introduce(self) -> None:
        modules = frozenset({"shipped_tool.py"})

        def check(source: str, expected: str) -> None:
            self.assertEqual(drop(source, SHIPPED, frozenset(), modules), expected, source)

        # Headings without blank lines between them are still checked one by one.
        check("## A\na\n### B `gone_tool.py`\nbody\n## C\nc\n", "## A\na\n## C\nc\n")
        check("## A `gone_tool.py`\n## B\nb\n", "## B\nb\n")
        # Text above an emptied list stays unless it is a line ending in a colon.
        check("Para without colon.\n- `gone_tool.py`\n", "Para without colon.\n")
        check("Rule: keep sources.\nRun this:\n- `gone_tool.py`\n\nNext.\n", "Rule: keep sources.\n\nNext.\n")
        check("Rule one.\nRun this:\n```bash\npython gone_tool.py\n```\n\nNext.\n", "Rule one.\n\nNext.\n")
        # An item that only introduced its nested items goes with them.
        check("- Steps:\n  - `gone_tool.py`\n- other\n", "- other\n")
        check("- Steps:\n  - `gone_tool.py`\n  - kept\n", "- Steps:\n  - kept\n")

    def test_command_and_import_forms(self) -> None:
        modules = frozenset({"shipped_tool.py"})
        private = frozenset({"private_planner.py"})
        for line in ("py -3 unshipped_helper.py", "uv run unshipped_helper.py"):
            self.assertEqual(drop("```bash\n" + line + "\npython shipped_tool.py y\n```\n", SHIPPED, private, modules),
                             "```bash\npython shipped_tool.py y\n```\n", line)
        for fence in ("```pycon\n>>> from private_planner import plan\n```\n",
                      "```python title=x\nimport os, private_planner\n```\n"):
            self.assertEqual(drop("Keep.\n\n" + fence, SHIPPED, private, modules), "Keep.\n", fence)
        prose = "The old build_tool.py step and python notes stay as plain text.\n"
        self.assertEqual(drop(prose, SHIPPED, private, modules), prose)

    def test_wrapped_and_list_item_intros(self) -> None:
        modules = frozenset({"shipped_tool.py"})

        def check(source: str, expected: str) -> None:
            self.assertEqual(drop(source, SHIPPED, frozenset(), modules), expected, source)

        check("Keep this sentence.\nThis list shows the commands that\nthe maintainer runs:\n- `gone_tool.py`\n",
              "Keep this sentence.\n")
        check("1. First.\n2. Then run:\n\n```bash\npython gone_tool.py\n```\n\nAfter.\n", "1. First.\n\nAfter.\n")

    def test_pointer_forms_with_locations_placeholders_and_packages(self) -> None:
        modules = frozenset({"shipped_tool.py"})
        private = frozenset({"private_mod.py"})
        for word in ("`gone_tool.py:42`", "`gone_tool.py::main`", "`<repo>/src/gone_tool.py`", "`$ROOT/gone_tool.py`",
                     "`longform_maker.private_mod`", "`python -m longform_maker.private_mod`",
                     "`from longform_maker import private_mod`", "[x](gone.md 'T')", "[x](gone.md (T))"):
            self.assertEqual(drop("Keep.\n\nUses " + word + ".\n", SHIPPED, private, modules), "Keep.\n", word)
        kept = "Uses `references/kept.md#part` and `shipped_tool.py:3`.\n"
        self.assertEqual(drop(kept, SHIPPED, private, modules), kept)
        for fence in ("```bash\n./gone_tool.py --x\npython shipped_tool.py\n```\n",):
            self.assertEqual(drop(fence, SHIPPED, private, modules), "```bash\npython shipped_tool.py\n```\n")
        heredoc = "```bash\npython gone_tool.py <<'EOF'\n{}\nEOF\npython shipped_tool.py\n```\n"
        self.assertEqual(drop("Keep.\n\n" + heredoc, SHIPPED, private, modules), "Keep.\n")
        javascript = "```js\nimport private_mod from './x.js'\n```\n"
        self.assertEqual(leftover_pointers(javascript, SHIPPED, private, modules), [])

    def test_a_pointer_the_filter_leaves_stops_the_copy(self) -> None:
        with tempfile.TemporaryDirectory(prefix="leftover-test-") as temp:
            source = Path(temp) / "source.md"
            source.write_text("- item\n\n        python gone_tool_xyz.py\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "left 1 pointer"):
                sync_canonical._copy_text(source, Path(temp) / "out.md",
                                          sync_canonical.PUBLIC_REFERENCE_PREFIX + "fixture.md",
                                          frozenset(), frozenset({"shipped_tool.py"}))

    def test_intros_imports_links_and_continuations(self) -> None:
        modules = frozenset({"shipped_tool.py"})
        private = frozenset({"private_mod.py", "private-notes.md"})

        def check(source: str, expected: str) -> None:
            self.assertEqual(drop(source, SHIPPED, private, modules), expected, source)

        # An intro that starts mid-line keeps the complete sentence before it.
        check("規則一是保留來源。下面是維護者\n的指令：\n- `gone_tool.py`\n", "規則一是保留來源。\n")
        check("Keep sources. Run this:\n- `gone_tool.py`\n", "Keep sources.\n")
        # Multi-line, `python -c` and here-document imports of a private module take their block.
        for fence in ("```python\nfrom private_mod import (\n    a,\n)\n```\n",
                      "```bash\npython -c \"from private_mod import plan\"\n```\n",
                      "```bash\npython - <<'EOF'\nfrom private_mod import plan\nEOF\n```\n"):
            check("Keep.\n\n" + fence, "Keep.\n")
        # Location suffixes, relative links and a leading-pipe continuation.
        for word in ("`gone_tool.py:main`", "[x](../../src/gone_tool.py)", "[x](../private-notes.md)", "[x](私人.md)"):
            check("Keep.\n\nUses " + word + ".\n", "Keep.\n")
        check("Keep.\n\n```powershell\npython gone_tool.py --x\n  | Out-File log.txt\npython shipped_tool.py\n```\n", "Keep.\n")
        kept = "See [docs](../docs/ARCHITECTURE.md) and ![x](img/a.png).\n"
        check(kept, kept)

    def test_placeholders_unparsable_imports_and_numbering(self) -> None:
        modules = frozenset({"shipped_tool.py"})
        private = frozenset({"private_mod.py"})

        def check(source: str, expected: str) -> None:
            self.assertEqual(drop(source, SHIPPED, private, modules), expected, source)

        for word in ("`private_mod.<function>`", "`private_mod.plan(**kw)`", "`private_mod.DOMAINS[\"x\"]`",
                     "`from private_mod import ...`"):
            check("Keep.\n\nUses " + word + ".\n", "Keep.\n")
        for fence in ("```bash\npython -c \"from private_mod import plan; plan(<x>)\"\n```\n",
                      "```pycon\n>>> from private_mod import (\nself-test GREEN\n```\n"):
            check("Keep.\n\n" + fence, "Keep.\n")
        kept = "See [the Skill](../SKILL.md).\n"
        check(kept, kept)
        check("1. First.\n2. Then run:\n\n```bash\npython gone_tool.py\n```\n\n3. After.\n4. Last.\n",
              "1. First.\n\n2. After.\n3. Last.\n")
        check("Use the shipped tool, e.g. run:\n```bash\npython gone_tool.py\n```\n\nNext.\n", "Next.\n")

    def test_definitions_video_files_anchors_and_python_use(self) -> None:
        modules = frozenset({"shipped_tool.py"})
        private = frozenset({"private_mod.py", "private-notes.md"})

        def check(source: str, expected: str) -> None:
            self.assertEqual(drop(source, SHIPPED, private, modules), expected, source)

        for definition in ("[p]: ../src/gone_tool.py", "[p]: ../private-notes.md", "[p]: 私人.md"):
            check("[k]: kept.md\n" + definition + "\n", "[k]: kept.md\n")
        video = "OBS 錄成 `recording.ts` 後先 remux 成 mp4。\n"
        check(video, video)
        check("- [Run](#run)\n- [Keep](#keep)\n\n## Run\n\nUses `gone_tool.py`.\n\n## Keep\n\nok\n",
              "- [Keep](#keep)\n\n## Keep\n\nok\n")
        check("Keep.\n\n```powershell\ncd src\npython gone_tool.py analyze x.mp4\n```\n", "Keep.\n")
        check("Keep.\n\n```python\nplan = private_mod.plan(x=1)\n```\n", "Keep.\n")
        diagram = "```text\n├── _plan.py / project files\n```\n"
        check(diagram, diagram)

    def test_kit_files_are_checked_for_private_text(self) -> None:
        import re
        with tempfile.TemporaryDirectory(prefix="kit-text-test-") as temp:
            repository = Path(temp)
            (repository / "docs").mkdir()
            (repository / "docs" / "a.md").write_text("fine\n", encoding="utf-8")
            sync_canonical._assert_kit_files_free_of_private_text(repository, (re.compile("fixture-term"),))
            (repository / "docs" / "b.md").write_text("has fixture-term\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "docs/b.md"):
                sync_canonical._assert_kit_files_free_of_private_text(repository, (re.compile("fixture-term"),))
            self.assertTrue((repository / "docs" / "b.md").exists())  # hand-written files are reported, not removed

    def test_a_failed_sync_removes_outputs_with_private_text(self) -> None:
        import re
        from unittest import mock
        with tempfile.TemporaryDirectory(prefix="failed-sync-path-") as temp:
            repository = Path(temp)
            control = {"terms": ("fixture-term",), "patterns": (re.compile("fixture-term"),)}

            def failing(canonical, repo, source, ctrl):
                (repo / "AUTOPILOT_MANIFEST.json").write_text("fixture-term\n", encoding="utf-8")
                raise RuntimeError("stopped later")

            with mock.patch.object(sync_canonical, "_assert_public_workflow_derivation"), \
                    mock.patch.object(sync_canonical, "validate_canonical_inventory", return_value=control), \
                    mock.patch.object(sync_canonical, "_sync_with_control", side_effect=failing):
                with self.assertRaisesRegex(RuntimeError, "stopped later"):
                    sync_canonical.sync(repository, repository, repository)
            self.assertFalse((repository / "AUTOPILOT_MANIFEST.json").exists())
            self.assertEqual(public_privacy_legacy._PRIVATE_TERMS, [])

    def test_shipped_references_hold_no_recognised_pointer(self) -> None:
        modules = sync_canonical._shipped_module_names(ROOT)
        shipped = sync_canonical._shipped_reference_names()
        for path in sorted(REFERENCES.glob("*.md")):
            self.assertEqual(leftover_pointers(path.read_text(encoding="utf-8"), shipped, frozenset(), modules), [],
                             path.name)

    def test_leftover_pointers_are_reported(self) -> None:
        modules = frozenset({"shipped_tool.py"})
        private = frozenset({"private_planner.py"})
        self.assertEqual(leftover_pointers("Keep `shipped_tool.py`.\n", SHIPPED, private, modules), [])
        self.assertTrue(leftover_pointers("Uses `private_planner.run()`.\n", SHIPPED, private, modules))
        self.assertTrue(leftover_pointers("- item\n\n        python unshipped_helper.py\n", SHIPPED, private, modules))
        self.assertEqual(leftover_pointers("Prose about build_tool.py.\n", SHIPPED, private, modules), [])

    def test_import_guard_covers_import_forms(self) -> None:
        private = frozenset({"helper_mod.py", "audit.py"})
        for source in ("def f():\n    from helper_mod import x\n", "import os, helper_mod\n",
                       "from longform_maker.helper_mod import x\n", "from longform_maker import helper_mod\n",
                       "import importlib\nimportlib.import_module('helper_mod')\n", "from . import helper_mod\n"):
            with self.assertRaisesRegex(ValueError, "imports modules the kit does not ship"):
                sync_canonical._assert_no_private_imports("example_module.py", source, private)
        for source in ("import json\nfrom pathlib import Path\n", "from shipped_ops import audit\n"):
            sync_canonical._assert_no_private_imports("example_module.py", source, private)
        sync_canonical._assert_no_private_imports("notes.md", "from helper_mod import x\n", private)

    def test_a_failed_sync_leaves_no_private_text(self) -> None:
        import re
        with tempfile.TemporaryDirectory(prefix="failed-sync-test-") as temp:
            repository = Path(temp)
            (repository / "a.md").write_text("fine\n", encoding="utf-8")
            (repository / "b.md").write_text("has fixture-term\n", encoding="utf-8")
            removed = sync_canonical._remove_private_outputs(
                repository, ["a.md", "b.md", "missing.md"], (re.compile("fixture-term"),))
            self.assertEqual(removed, ["b.md"])
            self.assertTrue((repository / "a.md").exists())

    def test_private_terms_are_replaced_only_during_a_sync(self) -> None:
        public_privacy_legacy.set_private_terms(["fixture-term"])
        try:
            self.assertEqual(public_privacy_legacy._replace_private_terms("a fixture-term b", "x"), "a x b")
        finally:
            public_privacy_legacy.set_private_terms(())
        self.assertEqual(public_privacy_legacy._replace_private_terms("a fixture-term b", "x"), "a fixture-term b")

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
    for rule in MODULE_REPLACEMENTS[name]:
        text = rule[0].sub(rule[1], text)
    return text


class PublicRewriteRules(unittest.TestCase):
    def test_rules_added_in_this_release_fire(self) -> None:
        fallback = "PROJECT_ROOT = discover_project_root(ROOT, required=False) or ROOT.parents[2]\n"
        cases = (
            ("skill_sync.py", '        assert result["declared_files"] >= 999, "x"\n',
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
            ("effect_source_map.py", fallback, fallback.replace("ROOT.parents[2]", "ROOT.parent")),
            ("publish_hub_context.py", 'SHORTS_ROOT = VIDEOS / "_INBOX" / "old-vertical-name"\n',
             'SHORTS_ROOT = VIDEOS / "_INBOX" / "vertical"\n'),
            ("publish_hub_context.py", 'LONGFORM_ROOT = VIDEOS / "_INBOX" / "old-landscape"\n',
             'LONGFORM_ROOT = VIDEOS / "_INBOX" / "landscape-longform"\n'),
            ("publish_hub_context.py", 'LEGACY_READY = VIDEOS / "_oldShorts"\n',
             'LEGACY_READY = VIDEOS / "_ready-shorts"\n'),
            ("publish_hub_ops.py", 'LEGACY_READY = VIDEOS / "_oldShorts"\n',
             'LEGACY_READY = VIDEOS / "_ready-shorts"\n'),
            ("quality-95-system.md", '"videos/_INBOX/old-vertical-name/N/_out"',
             '"videos/_INBOX/vertical/N/_out"'),
            ("storage-lifecycle.md", "`_oldShorts`", "`_ready-shorts`"),
            ("editkin-workflow-execution.md", "整理私有的 5 張設計 DNA。", "整理設計 DNA。"),
            ("editkin-workflow-execution.md", "結果用 `x_mod.py merge` 平鋪併入 plan（M9，見 `references/x-y.md`）。",
             "結果平鋪併入 plan。"),
            ("publish_hub_context.py",
             '    a = 1\n    p = VIDEOS / "_planning" / "x"\n'
             '    matches = sorted(p.glob("*"))\n'
             '    if matches:\n        return matches[0]\n    b = 2\n',
             "    a = 1\n    b = 2\n"),
            ("camera-transition-and-value-visualization.md", "- 母檔：`assets/x/y.png`，z。\n- next\n", "- next\n"),
            ("camera-transition-and-value-visualization.md", "## 5. 美元粒子資產\n\n- a\n",
             "## 5. 美元粒子資產\n\n以下是美元粒子 overlay 資產的驗收規格（aspect＝landscape／portrait）；"
             "資產需自行製作並通過這些驗收。\n\n- a\n"),
            ("caption-art-direction.md", "- 第一個核准素材是 `X`；索引在 `assets/i.json`。\n- next\n", "- next\n"),
            ("caption-art-direction.md", "- Imagegen 素材索引：`x/y.json`\n- next\n", "- next\n"),
            ("caption-art-direction.md", "impact 必存在 `some_track` 獨立軌", "impact 必存在獨立 overlay 軌"),
            ("color-science-and-visual-master.md", "Abc 的 12 張參考圖所提煉出的x",
             "[公開設計種子](design-reference-dna-v6.md)所提煉出的x"),
            ("color-science-and-visual-master.md", "- 預設交付為 Rec.709 SDR。`x_tool.py analyze` 讀取 primaries、transfer、matrix、range。",
             "- 預設交付為 Rec.709 SDR。"),
            ("color-science-and-visual-master.md", "M9 之後正式剪輯都在 Editkin v4 run 裡完成；上面的 `x_tool.py` FFmpeg Look 只供故障重現。",
             "上面的 Look 規格是設計規範；正式剪輯與實際套色都在 Editkin v4 run 裡完成。"),
            ("color-science-and-visual-master.md", '用 `x_mod.find_modules(kind="look", role=<下表 role>)` 取出 `family` 為 `film_look_v2` 的 variant。',
             "用 `list_editkin_modules` 取出 role 對應下表、`family` 為 `film_look_v2` 的 `look.color` variant。"),
            ("color-science-and-visual-master.md", "這是 9 個 Abc Film Look v2，已", "這些 Film Look v2 已"),
            ("calibration-learning-and-license.md", "- `x-y` 只輸出 ±1 EV 與 gain 建議，不抹平。\n", "- 鏡頭匹配建議限 ±1 EV 與 gain，不抹平。\n"),
            ("calibration-learning-and-license.md", "- `x-a` 產生來源、waveform、vectorscope 三聯圖；`y-b` 由 X",
             "- 用來源、waveform、vectorscope 三聯圖檢查；A/B 審片由 X"),
            ("token-budget-system.md", "x。舊 `some_log.md` 不再直接追加，以免重複。\n", "x。\n"),
            ("architecture-foundation-v6-3.md", "A. `run_ops.py` owns claim/retry/resume operations. B.", "A. B."),
            ("architecture-foundation-v6-3.md",
             "A. Planning validation uses `plan_check.py`, while the planning CLI may call the context router. B.", "A. B."),
            ("architecture-foundation-v6-3.md", "Both planning and routing use x.", "Context routing uses x."),
            ("asset-intelligence-hub.md", "；3 個程式生成 SFX 已有\n`assets/sfx/manifest.json` 與 48 kHz PCM 格式聲明，但授權仍是 `pending-x`。",
             "；程式生成 SFX 須在 `assets/sfx/manifest.json` 宣告 48 kHz PCM 格式與授權；授權未定的素材不得對外散布。"),
            ("cinematic-wave-and-domain-grammar-2026.md", "`x_tool.py` 會輸出每段時間、能量、意圖與 shot-duration range。",
             "節奏規劃要標出每段時間、能量、意圖與 shot-duration range。"),
            ("cinematic-wave-and-domain-grammar-2026.md", "輸出不可只被當成參考文件：", "這些節奏規則要落到 plan 裡，不可只被當成參考文件："),
            ("cinematic-wave-and-domain-grammar-2026.md", "- Shorts renderer 會實際插入語意字卡，x", "- Shorts 要實際插入語意字卡，x"),
            ("quality-95-system.md", "`x_tool.py build N` 會在技術 QA 後自動建立 provisional 報告與 Hao 審片頁。",
             "Shorts 技術 QA 通過後，用 `quality_95.py score` 建立 provisional 報告、`review_loop.py create` 建立 Hao 審片頁。"),
            ("quality-95-system.md", "預設不會因「某某」把技術成片刪除，但", "尚未審片不是刪除技術成片的理由，但"),
            ("quality-95-system.md", "# Quality 95：從「某某」到「某某某」\n", "# Quality 95：從可交付到高品質\n"),
            ("quality-95-system.md", "## X\n\n維護者工作區的整套專案驗收會重跑 9 個檢查：a、b。\n報告寫到 x。公開版不附這個驗收入口；公開安裝以 y 驗收。",
             "## X\n\n公開安裝以 y 驗收。"),
            ("mediastorm-craft-system.md", "調色的品味與轉場「某某某某某」不能由機器綠燈代替。", "調色的品味與轉場是否恰當不能由機器綠燈代替。"),
            ("cinematic-wave-and-domain-grammar-2026.md", "## 2. 「某某某」拆成七條可執行規則\n", "## 2. 流暢節奏拆成七條可執行規則\n"),
            ("calibration-learning-and-license.md", "這份文件是 Abc Def 的證據層；平時由程式讀取，不載入 context packet。\n",
             "這份文件記錄校色、成效學習、授權與封存的規則；相機 profile 與 ColorChecker 規則由你的調色流程執行。\n"),
            ("quality-95-system.md", "## 整套專案的 9.5 驗收\n", "## 整套專案驗收\n"),
            ("quality-95-system.md", "python review_loop.py serve x\n", "python src/review_loop.py serve x\n"),
            ("editkin-workflow-execution.md", "可用 `workflow reject-render <run>`", "可用 `python src/workflow_contract.py reject-render <run>`"),
            ("benchmark-effect-parity.md", "## 4. 現有能力矩陣\n\n| a |\n",
             "## 4. 現有能力矩陣\n\n表中狀態是能力分級參考；實際可用的工具以 Editkin 與本 kit 提供的為準。\n\n| a |\n"),
            ("quality-95-system.md", "人負責判斷美感、情緒與「某某某某」。", "人負責判斷美感、情緒與剪點是否順暢。"),
            ("mediastorm-craft-system.md", "基準從一句「某某某」改成", "基準從流暢這種模糊目標改成"),
            ("cinematic-wave-and-domain-grammar-2026.md", "目的：把「某某某」翻成可執行", "目的：把流暢這種模糊目標翻成可執行"),
            ("color-science-and-visual-master.md", "## 強度與「某某某某」素材\n", "## 強度與低對比（霧感）素材\n"),
            ("color-science-and-visual-master.md", "獨立套色會產生 `.grade.json`，偵測到既有 sidecar 時預設拒絕重疊。",
             "獨立套色應保留 `.grade.json` sidecar；已有 sidecar 時不得重疊套色。"),
            ("color-science-and-visual-master.md",
             "Variant id 不寫死，一律以匯出的 registry 為準：`references/x.json`。\n它由 X `y` 產生，用 `--check` 驗漂移。",
             "Variant id 不寫死，一律以當次 `list_editkin_modules` 回傳為準。"),
            ("mediastorm-craft-system.md", "3D 先走 `x_tool.py` 的 capability gate", "3D 先過 capability gate"),
            ("three-d-and-subject-fx.md", "缺前提時 `x_tool.py` 會輸出 `DOWNGRADED`", "缺前提時要標 `DOWNGRADED`"),
            ("editing-wave6-2026.md", "落地(機械化): `longform_maker/input_logger.py`：pynput", "落地(機械化): 新模組 input_logger：pynput"),
        )
        for name, before, after in cases:
            self.assertEqual(_module_rules(name, before), after, name)

    def test_every_v0281_reference_rewording_is_required(self) -> None:
        names = ("architecture-foundation-v6-3.md", "asset-intelligence-hub.md", "calibration-learning-and-license.md",
                 "caption-art-direction.md", "camera-transition-and-value-visualization.md",
                 "cinematic-wave-and-domain-grammar-2026.md", "color-science-and-visual-master.md",
                 "editing-wave6-2026.md", "mediastorm-craft-system.md", "three-d-and-subject-fx.md",
                 "token-budget-system.md")
        for name in names:
            for rule in MODULE_REPLACEMENTS[name]:
                self.assertTrue(len(rule) == 3 and rule[2], name + ": " + rule[0].pattern[:40])

    def test_required_rules_stop_the_sync_when_they_no_longer_match(self) -> None:
        with self.assertRaisesRegex(ValueError, "required public rewrite"):
            sync_canonical._transform("Nothing to rewrite here.\n", "three-d-and-subject-fx.md")
        with self.assertRaisesRegex(ValueError, "no longer matches|non-default folder"):
            sync_canonical._transform('X = VIDEOS / "_planning" / "x"\n', "publish_hub_context.py")

    def test_privacy_patterns_are_structural(self) -> None:
        def flagged(text):
            return any(pattern.search(text) for pattern in PRIVACY_PATTERNS)
        self.assertTrue(flagged("open " + "Q" + ":" + "\\" + "Some_Private_Workspace" + "\\" + "videos"))
        self.assertFalse(flagged("open X:\\my-videos\\_planning"))
        self.assertTrue(flagged("videos/_INBOX/\u67d0\u8cc7\u6599\u593e/101"))
        self.assertFalse(flagged("videos/_INBOX/vertical/101"))
        self.assertTrue(flagged('VIDEOS / "_INBOX" / "\u67d0\u8cc7\u6599\u593e"'))
        self.assertTrue(flagged('os.path.join(ROOT, "_INBOX", "\u67d0\u8cc7\u6599\u593e")'))
        self.assertFalse(flagged('VIDEOS / "_INBOX" / "vertical"'))
        for name in ("\u30c6\u30b9\u30c8", "\ud14c\uc2a4\ud2b8"):  # kana and hangul folder names
            self.assertTrue(flagged("videos/_INBOX/" + name + "/101"), name)

    def test_broll_report_labels_are_rewritten_exactly(self) -> None:
        from public_sync_renderers import neutral_broll_labels
        source = ('    print("x (通用 < 某某某主素材 + 無重複畫面)")\n        tag = "@主 " if role == "main" else "y"\n'
                  '    print(f"  某主素材 main    : {s}")\n    note = "拿來當主素材"\n')
        self.assertEqual(neutral_broll_labels(source),
                         '    print("x (通用 < 主素材 + 無重複畫面)")\n        tag = "\U0001f3af主 " if role == "main" else "y"\n'
                         '    print(f"  主素材 main    : {s}")\n    note = "拿來當主素材"\n')
        with self.assertRaisesRegex(ValueError, "labels drifted"):
            neutral_broll_labels("nothing here\n")

    def test_broll_renderer_rejects_a_creator_keyword_map(self) -> None:
        public = (ROOT / "src" / "broll_qa.py").read_text(encoding="utf-8")
        _validate_broll_interface(public, public=True)
        for extra in ("\nABC_BROLL_CONTENT_KEYWORDS = {}\n", "\n_ABC_BROLL_CONTENT_KEYWORDS = {}\n",
                      "\nif True:\n    CREATOR_KEYWORDS = {}\n"):
            with self.assertRaisesRegex(ValueError, "keyword map"):
                _validate_broll_interface(public + extra, public=True)

    def test_private_text_hit_removes_the_output(self) -> None:
        import re
        with tempfile.TemporaryDirectory(prefix="private-text-test-") as temp:
            repository = Path(temp)
            (repository / "clean.md").write_text("clean\n", encoding="utf-8")
            (repository / "hit.md").write_text("has a private-term here\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hit.md"):
                sync_canonical._assert_no_private_text(
                    repository, ["clean.md", "hit.md"], (re.compile("private-term"),))
            self.assertFalse((repository / "hit.md").exists())
            self.assertTrue((repository / "clean.md").exists())

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
