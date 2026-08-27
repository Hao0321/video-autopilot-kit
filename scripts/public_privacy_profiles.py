#!/usr/bin/env python3
"""Creator-profile privacy transforms for the public release.

This module is intentionally independent from the main public sanitizer so it
can be reviewed and tested as a small, closed set.  Its fixtures are synthetic;
the implementation does not retain the private values it is designed to remove.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Callable


PUBLIC_FIXTURE = "PUBLIC_FIXTURE"


def _lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _replace_string_node(text: str, node: ast.Constant, replacement: str) -> str:
    """Replace one parsed string literal while preserving all surrounding code."""
    lines = _lf(text).splitlines(keepends=True)
    start = node.lineno - 1
    end = node.end_lineno
    indent = re.match(r"\s*", lines[start]).group(0)
    literal = indent + repr(replacement) + "\n"
    return "".join(lines[:start]) + literal + "".join(lines[end:])


def _module_docstring_node(tree: ast.Module) -> ast.Constant | None:
    if not tree.body:
        return None
    first = tree.body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
        if isinstance(first.value.value, str):
            return first.value
    return None


def _replace_module_docstring(text: str, replacement: str) -> str:
    public = _lf(text)
    tree = ast.parse(public)
    node = _module_docstring_node(tree)
    if node is None:
        raise ValueError("managed Python file must have a module docstring")
    return _replace_string_node(public, node, replacement)


def _replace_function_docstring(text: str, function_name: str, replacement: str) -> str:
    public = _lf(text)
    tree = ast.parse(public)
    target: ast.Constant | None = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            if node.body and isinstance(node.body[0], ast.Expr):
                value = node.body[0].value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    target = value
                    break
    if target is None:
        raise ValueError(f"managed function {function_name!r} must have a docstring")
    return _replace_string_node(public, target, replacement)


def _blank_voice_profile(mode: str) -> dict:
    return {
        "primary_sample": f"{PUBLIC_FIXTURE} synthetic_sample",
        "tone_persona": "",
        "opening_pattern": {
            "template": "",
            "example_from_sample": f"{PUBLIC_FIXTURE} synthetic opening",
            "structure": "",
        },
        "punctuation": {},
        "pronouns": [],
        "wandering_verbs": [],
        "hedged_evaluations": [],
        "evaluation_template": "",
        "evaluation_examples": [],
        "sign_off": {
            "uses_boilerplate": False,
            "reason": "",
            "alternatives": [],
        },
        "avoid_strict": [],
        "on_screen_text_rules": {},
        "example_overlays_template": [],
        "signature_phrases": [],
        "mode": mode,
    }


def _sanitize_voice_profiles(_text: str) -> str:
    modes = ("vlog", "high-demo", "high-reflective", "low-diy")
    payload = {
        "_meta": {
            "schema_version": 1,
            "description": "Creator-neutral public voice-profile schema.",
            "fixture": PUBLIC_FIXTURE,
            "contains_creator_data": False,
            "instructions": "Populate locally from material you are authorized to use.",
        },
        **{mode: _blank_voice_profile(mode) for mode in modes},
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


_MODULE_DOCS = {
    "src/silent_vlog_maker/__init__.py": (
        "Silent-vlog and vertical-video preprocessing helpers.\n\n"
        f"{PUBLIC_FIXTURE}: public documentation contains no maintainer episode history."
    ),
    "src/silent_vlog_maker/audit.py": (
        "Pre-flight source audit for capture metadata, camera, audio and timing.\n\n"
        f"{PUBLIC_FIXTURE}: examples are creator-neutral and synthetic."
    ),
    "src/silent_vlog_maker/frame_audit.py": (
        "Frame extraction, contact-sheet generation and description caching.\n\n"
        f"{PUBLIC_FIXTURE}: no private episode or review outcomes are included."
    ),
    "src/silent_vlog_maker/scene_audit.py": (
        "Chronological and location-aware scene clustering for generic media sets.\n\n"
        f"{PUBLIC_FIXTURE}: public documentation uses no maintainer trip history."
    ),
}


def _sanitize_module_doc(relative_path: str, text: str) -> str:
    return _replace_module_docstring(text, _MODULE_DOCS[relative_path])


def _sanitize_teardown(text: str) -> str:
    public = _replace_module_docstring(
        text,
        "Competitor vertical-video teardown utilities.\n\n"
        "The OCR path is suitable for extracting candidate captions from burned-in text, "
        "but visible product claims still require human verification.\n\n"
        f"{PUBLIC_FIXTURE}: documentation and tests use synthetic examples only.",
    )
    public = _replace_function_docstring(
        public,
        "cuts",
        "Detect scene changes while retaining the ffmpeg diagnostic stream required by showinfo.",
    )
    public = _replace_function_docstring(
        public,
        "_near_dup",
        "Compare adjacent OCR strings with an order-sensitive similarity metric.",
    )
    lines = []
    for line in public.splitlines():
        if re.match(r"^\s*#.*(?:20\d{2}-\d{2}-\d{2}|(?:local|human)\s+(?:test|review))", line, re.I):
            indent = re.match(r"\s*", line).group(0)
            lines.append(indent + f"# {PUBLIC_FIXTURE}: behavior is covered by synthetic tests.")
        else:
            lines.append(line)
    return "\n".join(lines) + "\n"


def _sanitize_plan_gate(text: str) -> str:
    public = _lf(text)
    warning = re.compile(
        r'warns\.append\("W2\s+[^"\n]*?CTR\s+\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?%[^"\n]*"\)'
    )
    replacement = (
        'warns.append("W2 framing and recommendation conflict: "'
        f' "{PUBLIC_FIXTURE} uses no maintainer analytics")'
    )
    public, count = warning.subn(replacement, public)
    if count != 1:
        raise ValueError(f"expected one private plan-gate metric, replaced {count}")
    return public


_LARGE_REACH = re.compile(r"\d+(?:[.,]\d+)?\s*萬\s*(?:瀏覽)?")
_EXTREME_PERCENT = re.compile(r"\+\s*(?:\d{1,3}(?:,\d{3})+|\d{3,})%")


def _sanitize_synthetic_metrics(text: str) -> str:
    public = _LARGE_REACH.sub(f"12K {PUBLIC_FIXTURE}", _lf(text))
    public = _EXTREME_PERCENT.sub(f"+37% {PUBLIC_FIXTURE}", public)
    return public


PROFILE_TRANSFORMS: dict[str, Callable[[str], str]] = {
    "src/silent_vlog_maker/voice_profiles.json": _sanitize_voice_profiles,
    **{
        path: (lambda text, path=path: _sanitize_module_doc(path, text))
        for path in _MODULE_DOCS
    },
    "src/teardown.py": _sanitize_teardown,
    "src/longform_maker/plan_gate.py": _sanitize_plan_gate,
    "src/longform_maker/thumb_template.py": _sanitize_synthetic_metrics,
    "src/longform_maker/emphasis_overlays.py": _sanitize_synthetic_metrics,
    "src/render_caption_showcase.py": _sanitize_synthetic_metrics,
    "src/visual_director.py": _sanitize_synthetic_metrics,
}


def sanitize_public_profile_text(relative_path: str, text: str) -> str:
    """Return a deterministic public transform for one managed path."""
    path = relative_path.replace("\\", "/")
    transform = PROFILE_TRANSFORMS.get(path)
    return transform(text) if transform else _lf(text)


_PRIVATE_SHAPES = (
    re.compile(r"(?<![A-Za-z0-9])#[0-9]{3}(?![A-Za-z0-9])"),
    re.compile(r"(?<![A-Za-z0-9])[SLR][0-9]{3}(?![A-Za-z0-9])"),
    re.compile(r"(?i)\bCTR\s+\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?%"),
    re.compile(r"\d+(?:[.,]\d+)?\s*萬\s*(?:瀏覽)?"),
    re.compile(r"\+\s*(?:\d{1,3}(?:,\d{3})+|\d{3,})%"),
    re.compile(
        r"(?i)(?:private|outcome|human\s+review|primary_sample).{0,80}"
        r"\b\d{2,}\s*(?:files?|clips?|samples?)\b"
    ),
    re.compile(r"\b\d+[\d,]*\s*(?:訂閱|粉絲|觀看)"),
)


def assert_public_profile_text_safe(relative_path: str, text: str) -> None:
    """Fail closed when a managed output retains creator-history shaped data."""
    path = relative_path.replace("\\", "/")
    if path not in PROFILE_TRANSFORMS:
        return
    if PUBLIC_FIXTURE not in text:
        raise AssertionError(f"{path}: missing synthetic public-fixture marker")
    for pattern in _PRIVATE_SHAPES:
        if pattern.search(text):
            raise AssertionError(f"{path}: creator-history shaped value remains")
    if path.endswith(".py"):
        ast.parse(text)
    if path.endswith("voice_profiles.json"):
        payload = json.loads(text)
        meta = payload.get("_meta", {})
        if meta.get("contains_creator_data") is not False:
            raise AssertionError(f"{path}: public profile must explicitly exclude creator data")
        for mode in ("vlog", "high-demo", "high-reflective", "low-diy"):
            if mode not in payload or payload[mode].get("primary_sample") != (
                f"{PUBLIC_FIXTURE} synthetic_sample"
            ):
                raise AssertionError(f"{path}: missing neutral {mode} schema")


def _self_test() -> None:
    synthetic_module = '''"""Private episode DEMO-909 at Demo Harbor had 77 clips and a failed review."""\nVALUE = 1\n'''
    for path in _MODULE_DOCS:
        out = sanitize_public_profile_text(path, synthetic_module)
        assert "Demo Harbor" not in out and "77 clips" not in out
        assert_public_profile_text_safe(path, out)

    voice_input = json.dumps({
        "creator": "Synthetic Person",
        "primary_sample": "DEMO-909 private sample",
        "subscriber_result": "123 synthetic subscribers",
    })
    voice_out = sanitize_public_profile_text(
        "src/silent_vlog_maker/voice_profiles.json", voice_input
    )
    assert "Synthetic Person" not in voice_out and "DEMO-909" not in voice_out
    assert_public_profile_text_safe("src/silent_vlog_maker/voice_profiles.json", voice_out)

    teardown_input = '''# -*- coding: utf-8 -*-\n"""Private DEMO-909 outcome at Demo Harbor."""\ndef cuts(path):\n    """A local test incorrectly returned nine cuts."""\n    return path\ndef _near_dup(a, b):\n    """A private review compared twenty-two captions."""\n    return a == b\n# 2099-01-02 synthetic local test result\n'''
    teardown_out = sanitize_public_profile_text("src/teardown.py", teardown_input)
    assert "Demo Harbor" not in teardown_out and "twenty-two" not in teardown_out
    assert_public_profile_text_safe("src/teardown.py", teardown_out)

    plan_input = '''def gate(warns):\n    warns.append("W2 synthetic combination (CTR 3.1-4.2% synthetic history)")\n'''
    plan_out = sanitize_public_profile_text("src/longform_maker/plan_gate.py", plan_input)
    assert "3.1" not in plan_out and "4.2" not in plan_out
    assert_public_profile_text_safe("src/longform_maker/plan_gate.py", plan_out)

    metric_input = 'CAPTION = "456萬 瀏覽"\nBADGE = "+789%"\n'
    for path in (
        "src/longform_maker/thumb_template.py",
        "src/longform_maker/emphasis_overlays.py",
        "src/render_caption_showcase.py",
        "src/visual_director.py",
    ):
        out = sanitize_public_profile_text(path, metric_input)
        assert "456" not in out and "789" not in out
        assert_public_profile_text_safe(path, out)

    print(f"PUBLIC PROFILE PRIVACY SELFTEST GREEN: {len(PROFILE_TRANSFORMS)} managed outputs")


def _repository_test(root: Path) -> None:
    for relative_path in sorted(PROFILE_TRANSFORMS):
        source = root / relative_path
        if not source.is_file():
            raise AssertionError(f"missing managed source: {relative_path}")
        public = sanitize_public_profile_text(relative_path, source.read_text(encoding="utf-8"))
        assert_public_profile_text_safe(relative_path, public)
        print(f"[PASS] {relative_path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--repository", type=Path)
    args = parser.parse_args()
    if not args.self_test and args.repository is None:
        parser.error("use --self-test and/or --repository ROOT")
    if args.self_test:
        _self_test()
    if args.repository is not None:
        _repository_test(args.repository.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
