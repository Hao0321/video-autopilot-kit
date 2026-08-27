#!/usr/bin/env python3
"""Deterministic renderers for canonical-derived public distribution modules."""
from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path


def _lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _function(text: str, name: str) -> ast.FunctionDef:
    tree = ast.parse(text)
    matches = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(matches) != 1:
        raise ValueError(f"expected one public renderer source function: {name}")
    return matches[0]


def _replace_function_docstring(text: str, name: str, replacement: str) -> str:
    node = _function(text, name)
    if not node.body or not isinstance(node.body[0], ast.Expr):
        raise ValueError(f"canonical function lacks required docstring: {name}")
    value = node.body[0].value
    if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
        raise ValueError(f"canonical function lacks required docstring: {name}")
    lines = text.splitlines()
    start = node.body[0].lineno - 1
    end = (node.body[0].end_lineno or node.body[0].lineno)
    rendered = [*lines[:start], *replacement.splitlines(), *lines[end:]]
    return "\n".join(rendered) + "\n"


_BROLL_PREFIX = '''"""Creator-neutral b-roll ratio and narration-alignment audit helpers.

This public module is deterministically rendered from the canonical algorithm.
It contains generic starter labels only; pass creator-owned paths and keyword
maps explicitly when auditing a project.
"""

import math

# M86: generic b-roll duration must remain below creator-owned main footage.
# A generic source may appear at most ``max_uses`` times; the canonical default
# is two uses, while reaching the cap remains a warning.
_GENERIC_PATH_HINTS = ("broll", "transitions", "/stock", "b-roll")
_MAIN_PATH_HINTS = (
    "_cleaned", "screen", "obs", "dashboard", "website", "demo",
    "main", "hero", "product", "interview", "tutorial", "recording",
)
'''


_BROLL_CONTENT_BLOCK = '''# M87: narration-to-b-roll checks use explicit semantic labels, not filenames.
# These are neutral examples only.  The public default is an empty map so an
# omitted creator map warns about unchecked labels instead of vacuously passing.
EXAMPLE_BROLL_CONTENT_KEYWORDS = {
    "topic_product": ["產品", "網站", "首頁", "選單", "服務", "作品", "demo", "介面"],
    "topic_feature": ["功能", "系統", "設定", "流程", "選項", "面板"],
    "topic_code": ["code", "debug", "架構", "ui", "工具", "指令", "prompt"],
    "topic_food": ["美食", "好吃", "招牌", "風味", "湯頭", "配料"],
    "generic": [],
}
'''


def _validate_broll_interface(text: str, *, public: bool) -> None:
    tree = ast.parse(text)
    functions = {
        node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    required = {
        "_broll_basename", "_source_key", "classify_broll_role",
        "audit_broll_main_ratio", "print_broll_ratio_report",
        "narration_broll_sync_report", "print_narration_sync_report",
    }
    missing = sorted(required - set(functions))
    if missing:
        raise ValueError("b-roll canonical interface drift: " + ", ".join(missing))
    audit = functions["audit_broll_main_ratio"]
    names = [argument.arg for argument in audit.args.args]
    if names != ["segments", "strict", "max_uses"]:
        raise ValueError("b-roll ratio interface must expose segments, strict, max_uses")
    if len(audit.args.defaults) != 2:
        raise ValueError("b-roll ratio interface defaults drifted")
    max_default = audit.args.defaults[-1]
    if not isinstance(max_default, ast.Constant) or max_default.value != 2:
        raise ValueError("b-roll ratio canonical default max_uses must remain 2")
    source = ast.get_source_segment(text, audit) or ""
    if "v > max_uses" not in source or "v == max_uses" not in source:
        raise ValueError("b-roll ratio implementation lost max_uses enforcement/warning")
    if "math.isfinite(dur)" not in source or "dur <= 0" not in source:
        raise ValueError("b-roll ratio implementation lost finite-positive duration gate")
    role_source = ast.get_source_segment(text, functions["classify_broll_role"]) or ""
    if "isinstance(is_main, bool)" not in role_source:
        raise ValueError("b-roll role implementation lost bool/None contract")
    narration_source = ast.get_source_segment(
        text, functions["narration_broll_sync_report"]
    ) or ""
    if 'strict and not result["passed"]' not in narration_source:
        raise ValueError("narration sync strict mode must fail on unchecked labels")
    if public:
        forbidden = ("HAO_BROLL", "用戶原話", "官網", "gamehall", "Claude 當團隊")
        hits = [token for token in forbidden if token in text]
        if hits:
            raise ValueError("private b-roll vocabulary survived public renderer: " + ", ".join(hits))
        if "km = keyword_map if keyword_map is not None else {}" not in text:
            raise ValueError("public b-roll audit must fail visibly without a creator keyword map")


def render_public_broll(text: str) -> str:
    """Render the canonical algorithm while removing local examples and feedback."""
    source = _lf(text)
    _validate_broll_interface(source, public=False)
    first_function = source.find("def _broll_basename")
    if first_function < 0:
        raise ValueError("canonical b-roll provenance lost first helper")
    source = _BROLL_PREFIX + "\n" + source[first_function:]
    marker = source.find("# M87")
    narration = source.find("def narration_broll_sync_report")
    if marker < 0 or narration < 0 or marker >= narration:
        raise ValueError("canonical b-roll provenance lost M87 section")
    source = source[:marker] + _BROLL_CONTENT_BLOCK + "\n" + source[narration:]
    source = _replace_function_docstring(
        source,
        "_source_key",
        '    """Normalize a source key by removing a generated ``seg_NN_`` prefix and extension."""',
    )
    source = _replace_function_docstring(
        source,
        "classify_broll_role",
        '    """Return ``main`` or ``generic``; an explicit ``is_main`` value wins.\n\n'
        '    Unknown paths fail closed as generic instead of inflating main-footage coverage.\n'
        '    """',
    )
    source = _replace_function_docstring(
        source,
        "audit_broll_main_ratio",
        '    """Audit duration ratio and generic-source reuse on the edit timeline.\n\n'
        '    ``max_uses`` defaults to two.  A source at the cap warns; a source above\n'
        '    the cap fails.  ``strict=True`` raises on any failed invariant.\n'
        '    """',
    )
    source = _replace_function_docstring(
        source,
        "narration_broll_sync_report",
        '    """Check explicit b-roll content labels against captions in each time window.\n\n'
        '    Supply ``keyword_map`` from creator-owned project semantics.  An omitted\n'
        '    map marks non-generic labels unchecked and fails closed.\n'
        '    """',
    )
    source, count = re.subn(
        r"km = keyword_map if keyword_map is not None else HAO_BROLL_CONTENT_KEYWORDS",
        "km = keyword_map if keyword_map is not None else {}",
        source,
        count=1,
    )
    if count != 1:
        raise ValueError("canonical b-roll keyword-map default provenance drifted")
    source = source.replace("官網主素材", "主素材").replace("官網影片", "主素材")
    source = source.replace("🌐主 ", "🎯主 ")
    _validate_broll_interface(source, public=True)
    return source if source.endswith("\n") else source + "\n"


_EDITORIAL_INTERFACE = (
    "ASPECTS", "CATALOG_PATH", "MANIFEST_PATH", "ROLES", "STYLES", "TEMPLATE_ROOT",
    "build_catalog", "build_library", "infer_topic", "pick", "render_background",
    "render_template", "resolve_style",
)


def _canonical_editorial_interface(text: str) -> tuple[str, ...]:
    source = _lf(text)
    tree = ast.parse(source)
    imports = [
        node for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "template_engine"
    ]
    if len(imports) != 1:
        raise ValueError("canonical editorial provenance must import one template_engine interface")
    names = tuple(alias.name for alias in imports[0].names)
    if names != _EDITORIAL_INTERFACE:
        raise ValueError("canonical editorial template interface drifted")
    if "single source of truth" not in source or 'os.path.join(PROJECT_ROOT, "community", "hao-motion-kit")' not in source:
        raise ValueError("canonical editorial Motion Kit provenance drifted")
    if _function(source, "self_test").name != "self_test":
        raise ValueError("canonical editorial self-test provenance drifted")
    media_contract_tokens = (
        "without_media.tobytes() != with_media.tobytes()",
        "invalid editorial media path must fail closed",
        "unsupported editorial media must fail closed",
    )
    if any(token not in source for token in media_contract_tokens):
        raise ValueError("canonical editorial media-contract self-test drifted")
    return names


def render_public_editorial_templates(text: str) -> str:
    """Render the canonical bridge as an optional-kit public adapter with fallback."""
    names = _canonical_editorial_interface(text)
    imported = ", ".join(names[:6]) + ",\n        " + ", ".join(names[6:])
    public = f'''# -*- coding: utf-8 -*-
"""Bridge to the optional Bright Editorial Motion Kit.

The separately downloadable Motion Kit is preferred when installed.  The core
ships a procedural fallback so planning and basic rendering remain operational.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from PIL import Image

PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
KIT_CANDIDATES = (
    os.environ.get("VIDEO_AUTOPILOT_MOTION_KIT"),
    os.path.join(PROJECT_ROOT, "community", "hao-motion-kit"),
    os.path.join(PROJECT_ROOT, "hao-motion-kit"),
)
KIT_ROOT = next((os.path.abspath(path) for path in KIT_CANDIDATES
                 if path and os.path.isfile(os.path.join(path, "template_engine.py"))), None)
if KIT_ROOT:
    sys.path.insert(0, KIT_ROOT)

try:
    if not KIT_ROOT:
        raise ImportError("optional Motion Kit is not installed")
    from template_engine import (  # type: ignore  # noqa: E402,F401
        {imported},
    )
    ENGINE = "motion-kit"
except (ImportError, ModuleNotFoundError):
    from editorial_template_fallback import (  # noqa: E402,F401
        {imported},
    )
    ENGINE = "procedural-fallback"


def self_test() -> None:
    assert resolve_style("AI 教學")["key"] == "ai_chalk_grid"
    assert resolve_style("旅遊日記")["key"] == "travel_journal"
    assert resolve_style("抹茶冰淇淋")["key"] == "matcha_fresh"
    assert resolve_style("傳統海鮮料理")["key"] == "food_heritage"
    image = render_template("hook", "公開版模板", "SHORTS", topic="AI 教學", aspect="portrait")
    assert image.size == ASPECTS["portrait"] and image.mode == "RGB"
    with tempfile.TemporaryDirectory(prefix="editorial-bridge-") as temporary:
        media_path = Path(temporary) / "face.png"
        Image.new("RGB", (320, 520), (238, 37, 122)).save(media_path)
        without_media = render_template(
            "hook", "媒體契約", "TEST", aspect="portrait", seed=77)
        with_media = render_template(
            "hook", "媒體契約", "TEST", aspect="portrait",
            media_paths=(media_path,), seed=77)
        assert without_media.tobytes() != with_media.tobytes()
        try:
            render_template(
                "hook", "媒體契約", aspect="portrait",
                media_paths=(Path(temporary) / "missing.png",), seed=77)
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("invalid editorial media path must fail closed")
        unsupported_path = Path(temporary) / "unsupported.txt"
        unsupported_path.write_text("not an image", encoding="utf-8")
        try:
            render_template(
                "hook", "媒體契約", aspect="portrait",
                media_paths=(unsupported_path,), seed=77)
        except ValueError:
            pass
        else:
            raise AssertionError("unsupported editorial media must fail closed")
    print("editorial_templates bridge self-test OK (%s)" % ENGINE)


if __name__ == "__main__":
    self_test()
'''
    tree = ast.parse(public)
    modules = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    if "template_engine" not in modules or "editorial_template_fallback" not in modules:
        raise ValueError("public editorial renderer lost optional-kit/fallback imports")
    if "VIDEO_AUTOPILOT_MOTION_KIT" not in public or 'PROJECT_ROOT, "community", "hao-motion-kit"' not in public:
        raise ValueError("public editorial renderer lost configurable Motion Kit provenance")
    return public


def self_test_public_renderers(repository: Path) -> None:
    broll_path = repository / "src" / "broll_qa.py"
    editorial_path = repository / "src" / "editorial_templates.py"
    if not broll_path.is_file() or not editorial_path.is_file():
        raise FileNotFoundError("public renderer outputs are required for self-test")
    broll = broll_path.read_text(encoding="utf-8-sig")
    _validate_broll_interface(broll, public=True)
    namespace: dict = {}
    exec(compile(broll, str(broll_path), "exec"), namespace)
    audit = namespace["audit_broll_main_ratio"]
    assert inspect.signature(audit).parameters["max_uses"].default == 2
    twice = [
        {"name": "main/demo.mp4", "duration_s": 10, "is_main": True},
        {"name": "stock/clip.mp4", "duration_s": 1},
        {"name": "stock/clip.mp4", "duration_s": 1},
    ]
    assert audit(twice)["passed"] and not audit(twice)["repeats"]
    assert not audit(twice, max_uses=1)["passed"]
    assert not audit([*twice, {"name": "stock/clip.mp4", "duration_s": 1}])["passed"]
    for invalid_duration in (-1, 0, float("inf"), float("nan")):
        try:
            audit([{"name": "main/demo.mp4", "duration_s": invalid_duration}])
        except ValueError:
            pass
        else:
            raise AssertionError("invalid duration bypassed b-roll audit")
    try:
        audit([{"name": "main/demo.mp4", "duration_s": 1, "is_main": "false"}])
    except TypeError:
        pass
    else:
        raise AssertionError("non-boolean is_main bypassed b-roll audit")
    narration = namespace["narration_broll_sync_report"]
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        unchecked = narration(
            [(0, "demo")], [(0, 1, "unknown-topic")], keyword_map={}
        )
        assert not unchecked["passed"] and unchecked["unchecked"] == ["unknown-topic"]
        try:
            narration(
                [(0, "demo")], [(0, 1, "unknown-topic")], keyword_map={}, strict=True
            )
        except AssertionError:
            pass
        else:
            raise AssertionError("strict narration audit passed an unchecked label")
    editorial = editorial_path.read_text(encoding="utf-8-sig")
    tree = ast.parse(editorial)
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert {"template_engine", "editorial_template_fallback"} <= imports
    assert "VIDEO_AUTOPILOT_MOTION_KIT" in editorial
    assert "without_media.tobytes() != with_media.tobytes()" in editorial
    assert "invalid editorial media path must fail closed" in editorial
    assert "unsupported editorial media must fail closed" in editorial
    print("public sync renderer self-test GREEN")


if __name__ == "__main__":
    self_test_public_renderers(Path(__file__).resolve().parents[1])
