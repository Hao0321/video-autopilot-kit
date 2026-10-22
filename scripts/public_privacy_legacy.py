#!/usr/bin/env python3
"""Legacy deterministic transforms for generated public kit text.

The canonical skill is allowed to contain maintainer analytics, project routes,
dated evaluations and local calibration media.  Public synchronization calls
``sanitize_public_text`` *after* its normal compatibility transforms and writes
only the returned text.  The transforms below are structural: private values are
not copied into this module as a replacement dictionary.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path, PurePosixPath


from public_privacy_legacy_references import (
    PUBLIC_FIXTURE,
    PUBLIC_AUTOPILOT_CHEATSHEET,
    _autopilot_modes,
    PUBLIC_REVENUE_SECTION,
    _competitor_reference,
    PUBLIC_SCRIPT_RETENTION,
    _script_retention,
    PUBLIC_WAVE_PREAMBLE,
    PUBLIC_RETENTION_RULES,
    PUBLIC_FINECUT_INTERRUPT,
    _editing_wave,
    PUBLIC_EDITING_TECHNIQUES,
    _editing_techniques,
    PUBLIC_SHORTS_DIAGNOSTICS,
    PUBLIC_READING_RULE,
    PUBLIC_FACT_BOUNDARY,
    _shorts_mastery,
    _publish_remix_reference,
    PUBLIC_GENRE_READABILITY,
    PUBLIC_FOOD_COPY,
    PUBLIC_TRAVEL_COPY,
    PUBLIC_GENRE_COPY_INTRO,
    _genre_copy_reference,
    _GPS_MEASURED_OUTCOME_LINE,
    _autopilot_workflow,
    PUBLIC_LONGFORM_PIPELINE,
    _longform_pipeline,
)


from public_privacy_syntax import (
    _path,
    _lf,
    _replace_lines,
    _tree,
    _function,
    _replace_function,
    _replace_module_docstring,
    _replace_function_docstring,
    _replace_top_assignment,
    _replace_local_assignment,
    _drop_stateful_selftest,
    _between,
    _PRIVATE_IDENTITY_DIGESTS,
    _token_digest,
    _generalize_identity,
    _generalize_project_ids,
    _append_module_docstring_note,
    _replace_main_block,
    _subn_once,
)
from public_privacy_fixtures import (
    PUBLIC_SHORTS_SP_COMMENT,
    PUBLIC_SHORTS_SPEC_EXAMPLE,
    PUBLIC_SHORTS_SQ_COMMENT,
    PUBLIC_WORD_CAPTIONS_SELFTEST,
)


_PRIVATE_COMMUNITY_DIGEST = "ef57dc5839f9f74b7ecc0df6017a85a69ee17edb1e4f3a245ebc3adf492ac2a1"


def _contains_private_identity(text: str) -> bool:
    return any(
        _token_digest(match.group(0)) in _PRIVATE_IDENTITY_DIGESTS
        for match in re.finditer(r"\b[A-Za-z][A-Za-z0-9]*\b", text)
    )


def _replace_hashed_span(text: str, *, width: int, digest: str, replacement: str) -> str:
    """Replace a fixed-width private token without storing its plaintext."""
    out: list[str] = []
    cursor = 0
    while cursor < len(text):
        candidate = text[cursor:cursor + width]
        if len(candidate) == width and _token_digest(candidate) == digest:
            out.append(replacement)
            cursor += width
        else:
            out.append(text[cursor])
            cursor += 1
    return "".join(out)


from public_privacy_plans import (
    _channel_tracker,
    PUBLIC_REMIX_KEY_FUNCTION,
    PUBLIC_REMIX_SELFTEST,
    _remix_planner,
    _asset_registry,
)


PUBLIC_DEMO_PLAN_FUNCTION = '''def create_demo_remix_plan() -> dict[str, Any]:
    """Compatibility entrypoint that writes a synthetic public demo route."""
    output = VIDEOS / "_planning" / "remix" / "R001_public-demo-day-trip"
    plan = {
        "schema_version": 1, "content_id": "R001", "status": "planned",
        "format": "shorts", "target_seconds": 52,
        "title": "示範一日遊 4 站｜從晨間市集走到河畔公園",
        "source_rule": "只用 S101-S104 的示範原始素材，不拼接已燒字幕的成片",
        "sources": [
            {"content_id": "S101", "stop": "晨光市場", "folder": "videos/_INBOX/demo/101", "range": "00:03-00:12"},
            {"content_id": "S102", "stop": "綠徑公園", "folder": "videos/_INBOX/demo/102", "range": "00:12-00:23"},
            {"content_id": "S103", "stop": "工藝車站", "folder": "videos/_INBOX/demo/103", "range": "00:23-00:35"},
            {"content_id": "S104", "stop": "河畔步道", "folder": "videos/_INBOX/demo/104", "range": "00:35-00:47"},
        ],
        "beats": [
            {"range": "00:00-00:03", "purpose": "四站 payoff 快閃", "caption": "示範一日遊・4 站"},
            {"range": "00:03-00:47", "purpose": "依示範順序走完四站", "caption": "每站保留地名與一個可驗證的體驗"},
            {"range": "00:47-00:52", "purpose": "路線回顧與回圈", "caption": "這條示範路線你最想先去哪一站？"},
        ],
        "research_topic": "demo_day_trip", "candidate_score": 80,
        "score_basis": ["synthetic fixture", "four distinct demo stops", "original-source rule exercised"],
        "fixture_origin": "PUBLIC_FIXTURE: demo_day_trip",
        "updated_at": _now(),
    }
    _atomic_json(output / "remix_plan.json", plan)
    copy = build_publish_copy(
        {"niche": "travel", "place": "示範城", "what": "示範一日遊 四站"},
        {"yt_title": plan["title"],
         "text": "從晨光市場出發，依序走綠徑公園、工藝車站，最後到河畔步道。這是公開版的合成示範資料。\\n#示範一日遊 #旅行Shorts"},
    )
    _atomic_text(output / "發布文案_可複製.md", render_copy_markdown(copy))
    return plan'''


def _shorts_gate(text: str) -> str:
    text, count = re.subn(
        r"(?ms)^# ── S-R 閱讀速率.*?(?=^SR_WARN\s*=)",
        "# ── S-R reading rate (PUBLIC_FIXTURE generic starter)\n"
        "# Measure readable characters per display second.  The starter warn/fail\n"
        "# values are configurable and carry no maintainer quote or project result.\n",
        _lf(text), count=1,
    )
    if count != 1:
        raise ValueError("public sanitizer expected the S-R calibration comment block")
    text = _subn_once(r"(?<=直式 Shorts 機械閘門)（20\d{2}-\d{2}-\d{2}[^）\n]*）", "（公開版）",
                      text, "dated shorts-gate origin note")
    text = _subn_once(r"(?ms)^spec 結構（一支 Short）:\n    \{\n.*?^    \}\n",
                      PUBLIC_SHORTS_SPEC_EXAMPLE, text, "shorts spec example")
    text = _subn_once(r"(?ms)^# ── S-P 高風險宣稱 lint.*?(?=^RISKY_PATTERNS\s*=)",
                      PUBLIC_SHORTS_SP_COMMENT, text, "S-P calibration comment")
    text = _subn_once(r"(?ms)^# ── S-Q 首幀技術品質.*?(?=^SQ_RATIO\s*=)",
                      PUBLIC_SHORTS_SQ_COMMENT, text, "S-Q calibration comment")
    text = _subn_once(r"(?m)^(SQ_RATIO = [0-9.]+[^\n]*?)（[^）\n]*）$",
                      lambda match: match.group(1).rstrip(), text, "S-Q measured example")
    # Dated incident notes ("…lesson", "…audit") are maintainer history.
    return re.sub(r"（20\d{2}-\d{2}-\d{2}[^）\n]*(?:教訓|稽核|抓到)[^）\n]*）", "", text)


def _topic_catalog(text: str) -> str:
    data = json.loads(_lf(text))
    topics = data.get("topics")
    if not isinstance(topics, dict):
        raise ValueError("topic catalog requires an object at topics")
    public_topics = {}
    # Product rules backed by public manufacturer sources are safe to retain.
    if isinstance(topics.get("beyblade_x"), dict):
        retained = json.loads(json.dumps(topics["beyblade_x"], ensure_ascii=False))
        retained["notes"] = [_generalize_identity(str(note)) for note in retained.get("notes", [])]
        # Keep franchise-level routing terms only; specific tops are collection data.
        retained["aliases"] = [
            alias for alias in retained.get("aliases", [])
            if re.search(r"(?i)陀螺|beyblade", str(alias))
        ]
        public_topics["beyblade_x"] = retained
    public_topics["demo_day_trip"] = {
        "aliases": ["示範城", "晨光市場", "綠徑公園", "工藝車站", "河畔步道"],
        "last_verified": "2000-01-01",
        "refresh_days": 90,
        "copy_terms": ["示範一日遊", "四站路線", "河畔步道"],
        "hashtags": ["#示範一日遊", "#旅行Shorts"],
        "notes": [
            "PUBLIC_FIXTURE: this route and every stop are synthetic.",
            "Replace the fixture with sources verified for the creator's own footage before publishing.",
        ],
        "sources": [
            {"title": "Example tourism source", "url": "https://example.com/tourism", "kind": "fixture"}
        ],
    }
    data["topics"] = public_topics
    data["public_distribution"] = "PUBLIC_FIXTURE: private project topics are excluded by allowlist."
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


PUBLIC_SCRIPT_GATE_DOC = '''"""Mechanical narration-script checks (public distribution).

Input is plain narration text; beat headers use ``**[mm:ss-mm:ss title]**``.
The public vocabulary and speaking-rate values are generic starter fixtures.
Creators must calibrate them from recordings they own; no private transcript
counts, dated evaluations or channel performance values ship in this module.

PUBLIC_FIXTURE: script calibration is synthetic and creator-neutral.
"""'''


PUBLIC_CLEAN_SCRIPT_FIXTURE = '''def _clean_script_fixture():
    # PUBLIC_FIXTURE: invented narration used only for deterministic gate tests.
    clean = (
        "**[00:00-00:30 cold open]**\\n\\n"
        "這支示範影片曝光達到 12345，訂閱增加 67，"
        "我只用了 3 個小時就完成。\\n\\n"
        "你猜最關鍵的一步是什麼？\\n\\n"
        "**[00:30-02:00 method]**\\n\\n"
        "第一步是把腳本交給機械檢查，先估時長再看鉤子，"
        "最後掃一遍章節結構，確認每一章都有讓人停下來的理由。\\n\\n"
        "但是這裡有個陷阱，為什麼大家都忽略？"
        "因為多數人以為腳本寫完就等於準備好了，"
        "結果錄完音才發現開場拖了整整 40 秒還沒進重點。\\n\\n"
        "答案是留存曲線前 30 秒很重要，"
        "所以錄音之前就要把這些問題全部攔下來，"
        "而不是等剪輯的時候才回頭救火。\\n\\n"
        "**[02:00-02:30 outro]**\\n\\n"
        "覺得有用就訂閱，也歡迎來示範社群聊。\\n"
    )
    return clean'''


def _script_gate_commands(text: str) -> str:
    text = _append_module_docstring_note(
        text, "PUBLIC_FIXTURE: CTA fixtures name a demo community and a demo host.")
    text = _replace_hashed_span(
        text, width=4, digest=_PRIVATE_COMMUNITY_DIGEST, replacement="示範社群",
    )
    text = re.sub(r"大家好，我是[^，。！!？?\s\"\\]+", "大家好，我是示範主持人", text)
    return _generalize_project_ids(_generalize_identity(text))


def _script_gate(text: str) -> str:
    text = _replace_module_docstring(text, PUBLIC_SCRIPT_GATE_DOC)
    text = _replace_top_assignment(
        text, "SPOKEN_OK",
        '''SPOKEN_OK = {  # PUBLIC_FIXTURE generic starter vocabulary
    "ai", "app", "youtube", "google", "shorts", "short", "vlog", "api",
    "windows", "mac", "wifi", "email", "podcast", "diy", "hook", "loop",
    "mp3", "wav", "excel", "chrome", "github",
}''',
    )
    text = _replace_top_assignment(
        text, "_CTA_COMMUNITY_RE",
        '_CTA_COMMUNITY_RE = re.compile(r"社群|留言|下一支")  # PUBLIC_FIXTURE configurable CTA classes',
    )
    text = _replace_function(text, "_clean_script_fixture", PUBLIC_CLEAN_SCRIPT_FIXTURE)
    text = re.sub(r"大家好，我是[^，。！!？?\\n]+", "大家好，我是示範主持人", text)
    text = _replace_hashed_span(
        text, width=4, digest=_PRIVATE_COMMUNITY_DIGEST, replacement="示範社群",
    )
    cleaned = []
    for line in text.splitlines():
        if line.lstrip().startswith("#") and (
                _contains_private_identity(line)
                or re.search(r"(?:\d+\s*篇|長片0[1-9]|20\d{2}-\d{2}-\d{2})", line)):
            continue
        cleaned.append(line)
    public = "\n".join(cleaned) + "\n"
    public = _generalize_identity(public)
    return _generalize_project_ids(public)


PUBLIC_WORD_CAPTIONS_DOC = '''"""Word-timed caption grouping (public distribution).

Caption timing comes from approved word timestamps while line breaks follow
punctuation, pauses and semantic constraints.  Project transcript excerpts,
maintainer correction history and private sign-off phrases are not documentation
fixtures in the public module.

PUBLIC_FIXTURE: caption regressions use synthetic narration only.
"""'''


PUBLIC_GROUP_WORDS_DOC = '''    """Convert word timing into caption lines.

    Apply fixes before grouping; prefer punctuation and verified pauses, avoid
    dangling particles and protected word splits, and honor caller-provided
    semantic ``force_break_after`` hints.  Line start/end always use the first
    and last word timing.  PUBLIC_FIXTURE examples are creator-neutral.
    """'''


def _word_captions(text: str) -> str:
    text = _replace_module_docstring(text, PUBLIC_WORD_CAPTIONS_DOC)
    text = _replace_function_docstring(text, "group_words", PUBLIC_GROUP_WORDS_DOC)
    text = _replace_main_block(text, PUBLIC_WORD_CAPTIONS_SELFTEST)
    text = _subn_once(r"(?m)^(# 阿拉伯數字\+單位)（[^）\n]*）",
                      lambda match: match.group(1) + "（12.3萬 / 12.5% / $12.34 / 12,345）",
                      text, "emphasis number examples")
    text = _subn_once(r"(?m)^(# 行首禁用的方向補語（M108：)[^\n]*$",
                      lambda match: match.group(1) + "方向補語當行頭 = 上一行被腰斬）",
                      text, "direction-complement example")
    text = _subn_once(r"(# M108b：語段 pivot)（[^）\n]*）",
                      lambda match: match.group(1) + "（片尾收尾語多在句首）",
                      text, "sign-off pivot example")
    text = _replace_hashed_span(
        text, width=4, digest=_PRIVATE_COMMUNITY_DIGEST, replacement="示範",
    )
    cleaned = []
    for line in text.splitlines():
        if line.lstrip().startswith("#") and (
                _contains_private_identity(line)
                or re.search(r"(?:長片0[1-9]|20\d{2}-\d{2}-\d{2})", line)):
            continue
        cleaned.append(line)
    public = "\n".join(cleaned) + "\n"
    public = _generalize_identity(public)
    return _generalize_project_ids(public)


def _publish_hub(text: str) -> str:
    tree = ast.parse(text)
    candidates = next((node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_longform_candidates"), None)
    if candidates is None:
        raise ValueError("public sanitizer expected _longform_candidates")
    has_legacy = any(isinstance(node, ast.Name) and node.id == "legacy" for node in ast.walk(candidates))
    if not has_legacy:
        return text + "\n# PUBLIC_FIXTURE: retired legacy routing contains no maintainer media paths.\n"
    return _replace_local_assignment(
        text, "_longform_candidates", "legacy",
        "    legacy: list[tuple[int, Path, str]] = []  # PUBLIC_FIXTURE: no maintainer legacy paths",
    )


SANITIZERS = {
    "src/longform_maker/script_rhythm.py": lambda text: _script_rhythm(text),
    "src/channel_tracker.py": _channel_tracker,
    "src/publish_hub_ops.py": lambda text: _replace_function(text, "create_demo_remix_plan", PUBLIC_DEMO_PLAN_FUNCTION),
    "src/remix_planner.py": _remix_planner,
    "src/asset_registry.py": _asset_registry,
    "src/longform_maker/shorts_gate.py": _shorts_gate,
    "knowledge/runtime/topic_research_catalog.json": _topic_catalog,
    "src/longform_maker/script_gate.py": _script_gate,
    "src/longform_maker/script_gate_commands.py": _script_gate_commands,
    "src/longform_maker/word_captions.py": _word_captions,
    "src/publish_hub_context.py": _publish_hub,
    "src/longform_maker/LONGFORM_PIPELINE.md": _longform_pipeline,
    "knowledge/autopilot-workflow.md": _autopilot_workflow,
    "codex-skill/video-autopilot/references/autopilot-modes.md": _autopilot_modes,
    "codex-skill/video-autopilot/references/competitor-vertical-teardown-2026.md": _competitor_reference,
    "codex-skill/video-autopilot/references/editing-techniques-2026.md": _editing_techniques,
    "codex-skill/video-autopilot/references/script-retention-2026.md": _script_retention,
    "codex-skill/video-autopilot/references/editing-wave5-finecut-2026.md": _editing_wave,
    "codex-skill/video-autopilot/references/genre-copy-grammar-2026.md": _genre_copy_reference,
    "codex-skill/video-autopilot/references/shorts-mastery-2026.md": _shorts_mastery,
    "codex-skill/video-autopilot/references/publish-hub-and-remix.md": _publish_remix_reference,
}


def _script_rhythm(text: str) -> str:
    text = _replace_top_assignment(text, "CPM_DEFAULT", "CPM_DEFAULT = 250  # PUBLIC_FIXTURE generic starter chars/min")
    text = _replace_top_assignment(text, "CPM_OK_RANGE", "CPM_OK_RANGE = (220, 300)  # calibrate from creator-owned recordings")
    return _generalize_identity(text)
