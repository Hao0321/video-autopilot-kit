#!/usr/bin/env python3
"""Facade for deterministic private-to-public text sanitization."""
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path, PurePosixPath

from public_privacy_legacy import (
    PUBLIC_FIXTURE,
    SANITIZERS as LEGACY_SANITIZERS,
    _contains_private_identity,
    _generalize_identity,
    _generalize_project_ids,
    _lf,
)
from public_privacy_profiles import (
    PROFILE_TRANSFORMS,
    assert_public_profile_text_safe,
)
from public_privacy_references import SANITIZERS as REFERENCE_SANITIZERS
from public_privacy_sources import SANITIZERS as SOURCE_SANITIZERS


def _path(value: str | Path) -> str:
    return PurePosixPath(str(value).replace("\\", "/")).as_posix().lstrip("./")


SANITIZERS = {
    **LEGACY_SANITIZERS,
    **REFERENCE_SANITIZERS,
    **SOURCE_SANITIZERS,
    **PROFILE_TRANSFORMS,
}
REQUIRED_MARKERS = {path: PUBLIC_FIXTURE for path in SANITIZERS}


def generalize_private_identity(text: str) -> str:
    """Remove hashed maintainer identity tokens while preserving public URLs."""
    return _generalize_identity(_lf(text))


def contains_private_identity(text: str) -> bool:
    """Return whether a hashed maintainer identity token is present."""
    return _contains_private_identity(text)


_STRUCTURAL_BLOCKERS = (
    re.compile(r"長片0[1-9]|(?i:\blongform0[1-9]\b|\breference_impl_longform0[1-9]\b)"),
    re.compile(r"\b\d+\s*張(?:私人|使用者)?(?:視覺)?參考(?:圖)?"),
    re.compile(r"(?i)\bcreator.{0,80}(?:AVP|CTR).{0,40}\d+(?:\.\d+)?%"),
    re.compile(r"`[A-Za-z]:\\[^`\r\n]+`"),
    re.compile(
        r"20\d{2}[-/.]\d{2}[-/.]\d{2}[^\r\n]{0,80}"
        r"[\u300c\u300e\"'][^\r\n]{1,120}[\u300d\u300f\"']"
        r"[^\r\n]{0,80}(?:\u56de\u994b|feedback)",
        re.I,
    ),
    re.compile(
        r"(?m)^(?=[^\r\n]*(?:\u5be6\u6e2c|measured|outcome|result))"
        r"(?=[^\r\n]*GPS)(?=[^\r\n]*\d+(?:\.\d+)?\s*%\s*coverage\b)[^\r\n]*$",
        re.I,
    ),
    re.compile(
        r"(?m)^[ \t]*#(?!#)(?=[^\r\n]*(?:creator|user|\u7528\u6236))"
        r"(?=[^\r\n]*(?:\u56de\u994b|\u6279\u8a55|challenge|\u9435\u5247|\u5acc))"
        r"(?=[^\r\n]*[\u300c\u300e\"'][^\r\n]+[\u300d\u300f\"'])[^\r\n]*$",
        re.I,
    ),
    re.compile(
        r"(?m)^#[^\r\n]*20\d{2}[-/.]\d{2}[-/.]\d{2}[^\r\n]*"
        r"(?:creator|user|\u7528\u6236)[^\r\n]*(?:\u5acc|\u6279\u8a55|feedback)[^\r\n]*$",
        re.I,
    ),
    re.compile(
        r"(?m)^#[^\r\n]*(?:\u5be6\u6e2c|measured)[^\r\n]*\d+\s*"
        r"(?:\u652f|clips?)[^\r\n]*(?:\u4e2d\u62db|affected|failed)[^\r\n]*$",
        re.I,
    ),
    re.compile(r"(?m)^>\s*(?:\u8d77\u56e0|\u6839\u56e0\u8a3a\u65b7|\u5e02\u9762\u5be6\u6e2c\u6a23\u672c)\s*[：:].*$"),
    # A dated note that quotes the creator/user verbatim (an instruction or complaint).
    re.compile(
        r"20\d{2}[-/.]\d{2}[-/.]\d{2}[^\r\n]{0,60}"
        r"(?:creator|user|\u4f7f\u7528\u8005|\u7528\u6236)\s*[\u300c\u300e]",
        re.I,
    ),
    # A concrete street address (city/county + district/township + road + number).
    re.compile(
        r"[\u4e00-\u9fff]{1,4}[\u5e02\u7e23][\u4e00-\u9fff]{1,4}[\u5340\u9109\u93ae\u5e02]"
        r"[\u4e00-\u9fff]{1,8}[\u8def\u8857\u9053](?:[\u4e00-\u9fff0-9]+\u6bb5)?"
        r"(?:\d+\u5df7)?(?:\d+\u5f04)?\d+\u865f"
    ),
)


def _private_identity_outside_public_url(text: str) -> bool:
    scrubbed = re.sub(
        r"https://github\.com/[A-Za-z0-9_.-]+/video-autopilot-kit",
        "https://github.com/PUBLIC_AUTHOR/video-autopilot-kit",
        text,
    )
    return _contains_private_identity(scrubbed)


def assert_public_text_safe(relative_path: str | Path, text: str) -> None:
    """Fail closed for every managed high-risk public output."""
    name = _path(relative_path)
    if name not in SANITIZERS:
        return
    if REQUIRED_MARKERS[name] not in text:
        raise ValueError(f"privacy marker missing from {name}")
    if _private_identity_outside_public_url(text):
        raise ValueError(f"private identity token survived sanitization in {name}")
    for pattern in _STRUCTURAL_BLOCKERS:
        if pattern.search(text):
            raise ValueError(f"private-shaped fixture survived sanitization in {name}")
    if name == "knowledge/runtime/topic_research_catalog.json":
        data = json.loads(text)
        keys = set((data.get("topics") or {}).keys())
        if not keys.issubset({"beyblade_x", "demo_day_trip"}) or "demo_day_trip" not in keys:
            raise ValueError("public topic catalog escaped its explicit allowlist")
    if name in PROFILE_TRANSFORMS:
        assert_public_profile_text_safe(name, text)
    if name.endswith(".py"):
        try:
            ast.parse(text)
        except SyntaxError as exc:
            raise ValueError(f"public Python syntax invalid in {name}: {exc}") from exc
    elif name.endswith(".json"):
        json.loads(text)


def sanitize_public_text(relative_path: str | Path, text: str) -> str:
    """Return deterministic public text for a repository-relative destination."""
    name = _path(relative_path)
    transform = SANITIZERS.get(name)
    if transform is None:
        return _lf(text)
    if PUBLIC_FIXTURE in text:
        public = _lf(text)
    else:
        public = _lf(transform(_lf(text)))
    public = _generalize_project_ids(_generalize_identity(public))
    assert_public_text_safe(name, public)
    return public


def _expect_rejected(relative: str, text: str) -> None:
    try:
        assert_public_text_safe(relative, text)
    except ValueError:
        return
    raise AssertionError(f"private-shaped negative fixture was accepted: {relative}")


def _negative_fixture_test() -> None:
    dated_source = '''# Profile-selected emphasis colors.
    # 2099-10-31 synthetic palette revision.
    # creator「synthetic palette complaint」feedback.
# creator 2099-09-30 white-first policy：「synthetic color policy」。
# 好記的別名 2099-08-29：synthetic silent fallback incident.
# measured 9 clips affected.
COLOR_ALIAS = {}
# MAIN 91px（2099/12/31「synthetic reviewer note」feedback; previous 17）。
if __name__ == "__main__":
    _sample_lines = _split_caption_lines(
        [("合成甲", "w"), ("\\n合成乙", "r")], 6)
    assert len(_sample_lines) == 2 and _caption_units(_sample_lines[1]) == 8.0
'''
    # The renderer-specific transforms these fixtures once exercised were
    # retired with that renderer; the structural blockers are path-independent
    # and must still reject the same shapes on any managed Python output.
    managed_python = "src/longform_maker/shorts_gate.py"
    assert managed_python in SANITIZERS
    _expect_rejected(managed_python, f"# {PUBLIC_FIXTURE}\n" + dated_source)

    constants_source = '''# M88 (2099-07-28): user disliked synthetic generic font.
FONT_NARRATIVE = "serif"
# user v91 -> v92 challenge：「synthetic moving caption complaint」。
SUBTITLE_CENTER_Y = 999
'''
    _expect_rejected(managed_python, f"# {PUBLIC_FIXTURE}\n" + constants_source)

    gps_source = "# Workflow\n\n實測：synthetic media → GPS 73% coverage / timestamp result.\n"
    gps_public = sanitize_public_text("knowledge/autopilot-workflow.md", gps_source)
    assert "73%" not in gps_public and "synthetic media" not in gps_public
    _expect_rejected(
        "knowledge/autopilot-workflow.md",
        f"<!-- {PUBLIC_FIXTURE} -->\n" + gps_source,
    )

    genre_source = '''# 分類型文字語法（合成輸入）
> 起因：creator 2099-11-30 批評「synthetic private quote」。
> 根因診斷：我的內部草稿用了「synthetic actual wording」。
> 市面實測樣本：「synthetic outcome wording」。
## 通用四刀
「小吃店」→「synthetic shop name」。
## 第五刀
私人閱讀結果。
## 分類型語法
### 🍜 美食
私人例子。
### 🏞️ 旅遊/景點
私人路線。
### 📦 開箱
保留後續章節。
### 🤖 AI 教學（合成）
hook：synthetic star count 9,999。
### 🐾 寵物/生態
保留。
## 落地位置
- synthetic incident folder 9 and synthetic_memory_file.md
'''
    genre_path = "codex-skill/video-autopilot/references/genre-copy-grammar-2026.md"
    genre_public = sanitize_public_text(genre_path, genre_source)
    for token in ("2099-11-30", "synthetic private quote", "synthetic actual wording",
                  "synthetic shop name", "synthetic star count", "synthetic incident folder",
                  "synthetic_memory_file.md"):
        assert token not in genre_public
    assert "### 🐾" in genre_public and "## 落地位置" in genre_public
    _expect_rejected(genre_path, f"> {PUBLIC_FIXTURE}\n" + genre_source)
    _derived_fixture_test(managed_python)
    _route_fixture_test()
    print("PUBLIC PRIVACY NEGATIVE FIXTURES GREEN: feedback, GPS outcome, raw genre quotes, "
          "dated quotes, addresses, derived fixtures, routes")


def _derived_fixture_test(managed_python: str) -> None:
    """Synthetic canonical-shaped inputs for the derived-file sanitizers."""
    _expect_rejected(managed_python, f"# {PUBLIC_FIXTURE}\n"
                     "# synthetic gate (2099-01-02 landed; creator「synthetic raw instruction」)\n")
    _expect_rejected(managed_python, f"# {PUBLIC_FIXTURE}\n"
                     'ADDR = "合成店｜合成市合成區合成街99號"\n')
    assert_public_text_safe(managed_python, f"# {PUBLIC_FIXTURE}\n"
                            'ADDR = "示範烘焙｜示範市示範路 1 號"\n')

    shorts_source = '''# -*- coding: utf-8 -*-
"""shorts_gate.py — 直式 Shorts 機械閘門（2099-01-02 落地；creator「synthetic raw instruction」）

spec 結構（一支 Short）:
    {
      "place": "合成市 合成店",
      "addr":  "合成店｜合成市合成區合成街99號",
    }
"""
# ── S-R 閱讀速率（synthetic calibration quote）
SR_WARN = 5.0
# ── S-P 高風險宣稱 lint（2099-01-02：synthetic audit overturned 99 captions）
# 實例：「synthetic claim」實際 9 隻。
RISKY_PATTERNS = ()
# ── S-Q 首幀技術品質（2099-01-02：synthetic incident）
SQ_RATIO = 0.6                     # warn（實案 9.9/99.0=0.10）
def expand_caps(spec):
    """synthetic note（2099-01-02 s99 synthetic 教訓）。"""
    return spec
'''
    shorts_public = sanitize_public_text(managed_python, shorts_source)
    for token in ("synthetic raw instruction", "合成區", "synthetic audit", "synthetic claim",
                  "實案", "s99", "synthetic incident", "synthetic calibration quote"):
        assert token not in shorts_public, token

    captions_source = '''"""Synthetic caption module."""
# 行首禁用的方向補語（M108：「synthetic|fragment」→ 下去 不能當行頭）
CLAUSE_HEADS = ("好啦",)   # M108b：語段 pivot（synthetic sign-off habit）
# 阿拉伯數字+單位（98.7萬 / 65.4% / $32.10 / 98,765）＝關鍵詞，優先於詞表
def group_words(words):
    """Synthetic private correction history."""
    return words
if __name__ == "__main__":
    assert group_words(["synthetic private narration"])
'''
    captions_public = sanitize_public_text("src/longform_maker/word_captions.py", captions_source)
    for token in ("synthetic|fragment", "synthetic sign-off habit", "98.7萬", "$32.10",
                  "synthetic private narration", "Synthetic private correction"):
        assert token not in captions_public, token

    commands_public = sanitize_public_text(
        "src/longform_maker/script_gate_commands.py",
        '"""Synthetic commands."""\nINTRO = "大家好，我是Synthetic，今天聊剪片。"\n')
    assert "Synthetic，" not in commands_public and "示範主持人" in commands_public


def _route_fixture_test() -> None:
    """Context routes must never target references that the kit does not ship."""
    router_source = '''"""Synthetic router."""
REFS = None
FORMAT_CARDS = {
    "longform": "16:9；synthetic private template rated 70 points",
}
REFERENCE_ROUTES = {
    "shorts": ("shorts-mastery-2026.md", "synthetic-private-baseline.md"),
    "longform": ("../../synthetic-skill/references/private.md", "script-retention-2026.md"),
}
TOPIC_ROUTES = (
    (r"synthetic", "synthetic-private-method.md"),
    (r"3D", "three-d-and-subject-fx.md"),
)
LAST = REFS / "synthetic-private-canon.md"
'''
    router_public = sanitize_public_text("src/context_router.py", router_source)
    for token in ("synthetic private template", "synthetic-private-baseline.md", "synthetic-skill",
                  "synthetic-private-method.md", "synthetic-private-canon.md"):
        assert token not in router_public, token
    assert "three-d-and-subject-fx.md" in router_public and "craft-index.md" in router_public
    try:
        sanitize_public_text("src/context_router.py",
                             router_source + 'EXTRA = "synthetic-unshipped-route.md"\n')
    except ValueError:
        pass
    else:
        raise AssertionError("context router accepted a non-shipped reference route")

    storage_public = sanitize_public_text(
        "codex-skill/video-autopilot/references/storage-lifecycle.md",
        "# Storage\n\n## 問題定義\n\n本專案 2099-01-02 基準盤點：| `videos/` | 9,999 | 99.9 GB |\n\n"
        "## 固定結構\n\nkept\n")
    assert "9,999" not in storage_public and "2099-01-02" not in storage_public


def self_test(repository: Path) -> int:
    failures: list[str] = []
    try:
        _negative_fixture_test()
    except Exception as exc:  # noqa: BLE001 - keep negative fixtures fail-closed
        failures.append(f"negative-fixtures: {exc}")
        print(f"[FAIL] negative-fixtures: {exc}")
    for relative in sorted(SANITIZERS):
        source = repository / relative
        try:
            original = source.read_text(encoding="utf-8-sig")
            public = sanitize_public_text(relative, original)
            again = sanitize_public_text(relative, public)
            if public != again:
                raise AssertionError("transform is not idempotent")
            assert_public_text_safe(relative, public)
            print(f"[PASS] {relative}")
        except Exception as exc:  # noqa: BLE001 - aggregate every managed output
            failures.append(f"{relative}: {exc}")
            print(f"[FAIL] {relative}: {exc}")
    if failures:
        print(f"PUBLIC PRIVACY SELFTEST RED: {len(failures)}")
        return 1
    print(f"PUBLIC PRIVACY SELFTEST GREEN: {len(SANITIZERS)} managed outputs")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deterministic public privacy transforms")
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.error("--self-test is required")
    return self_test(args.repository.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
