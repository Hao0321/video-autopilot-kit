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


PUBLIC_FIXTURE = "PUBLIC_FIXTURE"


def _path(value: str | Path) -> str:
    return PurePosixPath(str(value).replace("\\", "/")).as_posix().lstrip("./")


def _lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _replace_lines(text: str, start: int, end: int, replacement: str) -> str:
    lines = _lf(text).splitlines(keepends=True)
    body = _lf(replacement).rstrip("\n") + "\n"
    lines[start - 1:end] = [body]
    return "".join(lines)


def _tree(text: str) -> ast.Module:
    return ast.parse(_lf(text))


def _function(text: str, name: str) -> ast.FunctionDef:
    for node in _tree(text).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise ValueError(f"public sanitizer expected function {name!r}")


def _replace_function(text: str, name: str, replacement: str) -> str:
    node = _function(text, name)
    return _replace_lines(text, node.lineno, node.end_lineno or node.lineno, replacement)


def _replace_module_docstring(text: str, replacement: str) -> str:
    tree = _tree(text)
    if not tree.body or not isinstance(tree.body[0], ast.Expr):
        raise ValueError("public sanitizer expected a module docstring")
    node = tree.body[0]
    if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
        raise ValueError("public sanitizer expected a module docstring")
    return _replace_lines(text, node.lineno, node.end_lineno or node.lineno, replacement)


def _replace_function_docstring(text: str, name: str, replacement: str) -> str:
    node = _function(text, name)
    if not node.body or not isinstance(node.body[0], ast.Expr):
        raise ValueError(f"public sanitizer expected a docstring in {name!r}")
    doc = node.body[0]
    if not isinstance(doc.value, ast.Constant) or not isinstance(doc.value.value, str):
        raise ValueError(f"public sanitizer expected a docstring in {name!r}")
    return _replace_lines(text, doc.lineno, doc.end_lineno or doc.lineno, replacement)


def _replace_top_assignment(text: str, name: str, replacement: str) -> str:
    for node in _tree(text).body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                return _replace_lines(text, node.lineno, node.end_lineno or node.lineno, replacement)
    raise ValueError(f"public sanitizer expected assignment {name!r}")


def _replace_local_assignment(text: str, function: str, name: str, replacement: str) -> str:
    scope = _function(text, function)
    for node in ast.walk(scope):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                return _replace_lines(text, node.lineno, node.end_lineno or node.lineno, replacement)
    raise ValueError(f"public sanitizer expected {function}.{name}")


def _drop_stateful_selftest(text: str, function: str) -> str:
    scope = _function(text, function)
    for node in ast.walk(scope):
        if not isinstance(node, ast.If):
            continue
        segment = ast.get_source_segment(_lf(text), node) or ""
        if "STATE_PATH" in segment and "load_state" in segment:
            return _replace_lines(
                text, node.lineno, node.end_lineno or node.lineno,
                "    # PUBLIC_FIXTURE: no maintainer state file is inspected by public self-tests.",
            )
    raise ValueError("public sanitizer expected the stateful channel self-test block")


def _between(text: str, start_prefix: str, end_prefix: str, replacement: str) -> str:
    text = _lf(text)
    start = re.search(rf"(?m)^{re.escape(start_prefix)}.*$", text)
    if not start:
        raise ValueError(f"public sanitizer expected heading {start_prefix!r}")
    end = re.search(rf"(?m)^{re.escape(end_prefix)}.*$", text[start.end():])
    if not end:
        raise ValueError(f"public sanitizer expected heading {end_prefix!r}")
    end_pos = start.end() + end.start()
    return text[:start.start()] + _lf(replacement).rstrip() + "\n\n" + text[end_pos:]


_PRIVATE_IDENTITY_DIGESTS = frozenset({
    "11c37e60e9124b0c55788eab3faf8955165c4d348fbff040200176e3beaa1778",
    "627f99a6fdfb53953c9edee95c030c33bef3ab488c62a0355e244021c0af10f4",
})
_PRIVATE_COMMUNITY_DIGEST = "ef57dc5839f9f74b7ecc0df6017a85a69ee17edb1e4f3a245ebc3adf492ac2a1"


def _token_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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


def _generalize_identity(text: str) -> str:
    """Replace private identity tokens by digest while preserving the public repo URL."""
    protected: list[str] = []

    def protect(match: re.Match[str]) -> str:
        protected.append(match.group(0))
        return f"__PUBLIC_AUTHOR_URL_{len(protected) - 1}__"

    public = re.sub(
        r"https://github\.com/[A-Za-z0-9_.-]+/video-autopilot-kit",
        protect,
        text,
    )

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        return "creator" if _token_digest(token) in _PRIVATE_IDENTITY_DIGESTS else token

    public = re.sub(r"\b[A-Za-z][A-Za-z0-9]*\b", replace, public)
    public = re.sub(r"\bcreator\s+Studio\b", "creator brand", public)
    for index, url in enumerate(protected):
        public = public.replace(f"__PUBLIC_AUTHOR_URL_{index}__", url)
    return public


def _generalize_project_ids(text: str) -> str:
    public = re.sub(r"(?i)\breference_impl_longform0[1-9]\b", "reference_impl_demo", text)
    public = re.sub(r"(?i)\blongform0[1-9]\b", "demo_longform", public)
    return re.sub(r"長片0[1-9]", "示範長片", public)


def _channel_tracker(text: str) -> str:
    text = _replace_module_docstring(text, '''"""Channel publishing state machine (public distribution).

The JSON state stores D2/D7/D28 scheduling and pending actions.  It does not
ship a maintainer state file or maintainer analytics.  Examples in this module
are synthetic and exist only to exercise the public API.

PUBLIC_FIXTURE: channel metrics examples are synthetic.
"""''')
    text = _replace_function_docstring(text, "record_metrics", '''    """Store only metrics explicitly supplied by the caller.

    Platforms can have different scales, so missing fields remain absent rather
    than being filled or inferred.  The numbers used by the self-test are
    illustrative fixtures, never copied channel analytics.
    """''')
    return _drop_stateful_selftest(text, "_selftest")


PUBLIC_DEMO_PLAN_FUNCTION = '''def create_miaoli_remix_plan() -> dict[str, Any]:
    """Compatibility entrypoint that writes a synthetic public demo route."""
    output = VIDEOS / "_planning" / "remix" / "R001_public-demo-day-trip"
    plan = {
        "schema_version": 1, "content_id": "R001", "status": "planned",
        "format": "shorts", "target_seconds": 52,
        "title": "示範一日遊 4 站｜從晨間市集走到河畔公園",
        "source_rule": "使用 S101-S104 的示範原始素材，不串接已上字幕成片",
        "sources": [
            {"content_id": "S101", "stop": "晨光市場", "folder": "videos/_INBOX/demo/101", "range": "00:03-00:12"},
            {"content_id": "S102", "stop": "綠徑公園", "folder": "videos/_INBOX/demo/102", "range": "00:12-00:23"},
            {"content_id": "S103", "stop": "工藝車站", "folder": "videos/_INBOX/demo/103", "range": "00:23-00:35"},
            {"content_id": "S104", "stop": "河畔步道", "folder": "videos/_INBOX/demo/104", "range": "00:35-00:47"},
        ],
        "beats": [
            {"range": "00:00-00:03", "purpose": "四站 payoff 快閃", "caption": "示範一日遊・4 站"},
            {"range": "00:03-00:47", "purpose": "依示範順序走完四站", "caption": "每站只留地名與一個體驗重點"},
            {"range": "00:47-00:52", "purpose": "路線回顧與回圈", "caption": "這條示範路線你會先去哪站？"},
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


PUBLIC_REMIX_KEY_FUNCTION = '''def _key(row: dict) -> list[tuple[str, str]]:
    """Build generic grouping keys without hard-coded maintainer projects."""
    out = []
    niche = str(row.get("niche") or "").lower()
    place = str(row.get("place") or "").strip()
    series = str(row.get("series") or "").strip()
    if place:
        out.append(("place", place))
    if niche and niche not in {"auto", "general"}:
        out.append(("niche", niche))
    if series:
        out.append(("series", series))
    return out'''


PUBLIC_REMIX_SELFTEST = '''def _selftest() -> None:
    rows = [
        {"content_id": "S901", "niche": "travel", "place": "示範城", "series": "public-demo-series"},
        {"content_id": "S902", "niche": "travel", "place": "示範城", "series": "public-demo-series"},
    ]
    groups = defaultdict(list)
    for row in rows:
        for key in _key(row):
            groups[key].append(row)
    assert len(groups[("series", "public-demo-series")]) == 2
    assert len(groups[("place", "示範城")]) == 2
    print("remix_planner self-test GREEN (PUBLIC_FIXTURE)")'''


def _remix_planner(text: str) -> str:
    text = _replace_function(text, "_key", PUBLIC_REMIX_KEY_FUNCTION)
    return _replace_function(text, "_selftest", PUBLIC_REMIX_SELFTEST)


def _asset_registry(text: str) -> str:
    result, count = re.subn(
        r'(?m)^(\s*semantic_target=)"[^"]*"(,\s*)$',
        r'\1"示範城旅行用的精緻紙張地理標籤"\2  # PUBLIC_FIXTURE',
        _lf(text), count=1,
    )
    if count != 1:
        raise ValueError("public sanitizer expected one asset-registry semantic fixture")
    return result


_DATED_QUOTED_FEEDBACK_COMMENT = re.compile(
    r"(?im)^(?P<indent>[ \t]*)#[^\r\n]*"
    r"20\d{2}[-/.]\d{2}[-/.]\d{2}"
    r"[^\r\n]{0,80}[\u300c\u300e\"'][^\r\n]{1,120}[\u300d\u300f\"']"
    r"[^\r\n]{0,80}(?:\u56de\u994b|feedback)[^\r\n]*$"
)


def _shorts_vertical(text: str) -> str:
    pattern = re.compile(
        r"(?ms)^    _[A-Za-z0-9_]+_lines = _split_caption_lines\(\n"
        r"        \[\([^\n]+\n"
        r"    assert len\(_[A-Za-z0-9_]+_lines\) == 2 and "
        r"_caption_units\(_[A-Za-z0-9_]+_lines\[1\]\) == 8\.0\n"
    )
    replacement = (
        "    # PUBLIC_FIXTURE: synthetic caption used only for safe-area regression.\n"
        "    _demo_route_lines = _split_caption_lines(\n"
        "        [('示範城一天跑 4 站', 'w'), ('\\n一路散步走到河畔', 'r')], 6)\n"
        "    assert len(_demo_route_lines) == 2 and _caption_units(_demo_route_lines[1]) == 8.0\n"
    )
    result, count = pattern.subn(
        lambda _match: replacement, _generalize_identity(_lf(text)), count=1
    )
    if count != 1:
        raise ValueError("public sanitizer expected one two-line caption regression fixture")
    result = _DATED_QUOTED_FEEDBACK_COMMENT.sub(
        lambda match: (
            match.group("indent")
            + "# PUBLIC_FIXTURE: caption size is a configurable starter constrained by safe-area geometry."
        ),
        result,
    )
    result = re.sub(
        r"(?m)^[ \t]*#[^\r\n]*20\d{2}[-/.]\d{2}[-/.]\d{2}[^\r\n]*(?:palette|\u914d\u8272)[^\r\n]*\n"
        r"[ \t]*#[^\r\n]*(?:creator|user|\u7528\u6236)[^\r\n]*(?:\u56de\u994b|feedback)[^\r\n]*$",
        "    # PUBLIC_FIXTURE: use a high-contrast outlined accent palette and validate it on source frames.",
        result,
        flags=re.I,
    )
    result = re.sub(
        r"(?m)^[ \t]*#[^\r\n]*(?:creator|user|\u7528\u6236)[^\r\n]*"
        r"20\d{2}[-/.]\d{2}[-/.]\d{2}[^\r\n]*white-first[^\r\n]*$",
        "# PUBLIC_FIXTURE: use white-first captions; reserve accents for verified emphasis and key facts.",
        result,
        flags=re.I,
    )
    result = re.sub(
        r"(?ms)^#\s*\u597d\u8a18\u7684\u5225\u540d[^\r\n]*20\d{2}[-/.]\d{2}[-/.]\d{2}.*?(?=^COLOR_ALIAS\s*=)",
        "# PUBLIC_FIXTURE: aliases prevent full-name palette tokens from silently falling back; verify emitted ASS colors.\n",
        result,
    )
    result = re.sub(
        r"(?m)^#\s*\u2500\u2500\s*\u591a\u8272\u91cd\u9ede\u5b57.*$",
        "# ── Profile-selected emphasis colors use valid ASS inline BGR tags ──",
        result,
    )
    result = re.sub(
        r"(?m)^#\s*\u2500\u2500\s*niche\s*→\s*\u914d\u8272\s*/\s*\u5b57\u9ad4\s*\u5c0d\u7167.*$",
        "# ── Niche palette/font starter map; project profiles may override it ──",
        result,
        flags=re.I,
    )
    return result


def _silent_vlog_constants(text: str) -> str:
    public = re.sub(
        r"(?m)^#\s*M\d+\s*\(20\d{2}[-/.]\d{2}[-/.]\d{2}\):[^\r\n]*"
        r"(?:creator|user|\u7528\u6236)[^\r\n]*$",
        "# PUBLIC_FIXTURE: use a readable sans hierarchy; narrative serif is an optional profile-selected contrast.",
        _lf(text),
        flags=re.I,
    )
    return re.sub(
        r"(?m)^#[^\r\n]*(?:creator|user|\u7528\u6236)\s+v\d+[^\r\n]*"
        r"(?:->|\u2192)\s*v\d+[^\r\n]*$",
        "# PUBLIC_FIXTURE: keep portrait captions in one stable center-lower lane inside platform safe zones.",
        public,
        flags=re.I,
    )


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
    return text


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


def _script_gate(text: str) -> str:
    text = _replace_module_docstring(text, PUBLIC_SCRIPT_GATE_DOC)
    text = _replace_top_assignment(text, "CPM_DEFAULT", "CPM_DEFAULT = 250  # PUBLIC_FIXTURE generic starter chars/min")
    text = _replace_top_assignment(text, "CPM_OK_RANGE", "CPM_OK_RANGE = (220, 300)  # calibrate from creator-owned recordings")
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
    return _replace_local_assignment(
        text, "_longform_candidates", "legacy",
        "    legacy: list[tuple[int, Path, str]] = []  # PUBLIC_FIXTURE: no maintainer legacy paths",
    )


PUBLIC_GRADE_DOC = '''"""Color-grade calibration runner (public distribution).

Populate ``REGRESSION`` with creator-owned videos that should pass and
``BASELINE`` with videos that are measurement-only.  The public kit deliberately
ships both lists empty: maintainer paths, scores and dated evaluations are not
fixtures for another creator's thresholds.

PUBLIC_FIXTURE: local calibration media are excluded.
"""'''


def _grade_calibrate(text: str) -> str:
    text = _replace_module_docstring(text, PUBLIC_GRADE_DOC)
    text = _replace_top_assignment(text, "REGRESSION", "REGRESSION = []  # PUBLIC_FIXTURE: add creator-owned approved samples")
    text = _replace_top_assignment(text, "BASELINE", "BASELINE = []  # PUBLIC_FIXTURE: add creator-owned measurement samples")
    text = _generalize_identity(text)
    text = text.replace("長片 / vlog", "long-form / vlog")
    return text


PUBLIC_AUTOPILOT_CHEATSHEET = '''## ⚡ Cheat Sheet — public defaults

> **PUBLIC_FIXTURE / privacy boundary:** this distribution contains no maintainer
> posting schedule, channel KPI, private voice phrases, project status or
> analytics.  Fill those values from your own creator profile and evidence.

1. A one-line topic can start Mode A; ask only for missing facts that change the route.
2. Choose either a true long-form plan or a vertical short.  Duration, outro, community CTA and visual density come from the active creator profile.
3. Script and visuals are evidence-anchored: quote narration cues, inspect source frames and never invent a project fact.
4. Do not ship universal KPI thresholds.  Record the first 3-5 comparable releases, compare identical windows, then calibrate creator-owned gates.
5. Posting time is ``<fill in from platform analytics>``.  Never inherit another channel's hour or timezone.
6. The edit route is the structured Editkin workflow: bind evidence, audit a plan, apply atomically, render, run delivery QA, then require human review.
7. A deliverable is complete only when the current render, technical QA, mobile review entry and human decision refer to the same artifact.
8. Every preference or evaluation becomes a generalized rule only after privacy review; private quotes and project evidence stay canonical-only.'''


def _autopilot_modes(text: str) -> str:
    text = _between(text, "## ⚡ Cheat Sheet", "## 3 個 Mode", PUBLIC_AUTOPILOT_CHEATSHEET)
    return _generalize_identity(text)


PUBLIC_REVENUE_SECTION = '''## §12 ⚠️ 收益宣稱：手法可學，數字必須驗證

> **PUBLIC_FIXTURE / privacy boundary:** the maintainer's RPM, audience geography
> and channel screenshots are intentionally excluded.

收益案例只能分成三類：平台第一方規則、創作者自己可驗證的後台，以及第三方假設。
競品把觀看數乘上一個網路 RPM 只能算情境試算，不能當成實績。分析時保留下列檢查：

1. 畫面是否真的顯示該頻道自己的收益後台？
2. RPM 的市場、內容型態、期間與受眾地區是否相同？
3. 觀看數、匯率與分潤是否都標成假設？
4. 標題與口播是否把試算誤寫成已賺到的金額？

公開規則只保留驗證方法；任何單一頻道數字都必須由使用者自己的 evidence ledger 提供。'''


def _competitor_reference(text: str) -> str:
    text = _between(text, "## §12", "## §13", PUBLIC_REVENUE_SECTION)
    return _generalize_identity(text)


PUBLIC_SCRIPT_RETENTION = '''# 腳本三支柱＋留存節奏（public calibration guide）

> **PUBLIC_FIXTURE / privacy boundary:** no maintainer transcript, sample count,
> dated evaluation, speaking-rate measurement or private voice quote is included.

三支柱是語氣、觀眾語言與留存節奏。語氣從使用者自己的 voice profile 讀取；
觀眾語言與節奏由 `src/longform_maker/script_gate.py` 提供 generic starter checks。

## 支柱 2：觀眾語言

公開版四層詞表只是示範結構：

| 層 | 用途 |
|---|---|
| SPOKEN_OK | 已由使用者自己的逐字稿或受眾研究證明可直接使用 |
| SUBSTITUTE | 有更清楚本地語言時，要求換成白話 |
| NEED_PAIR | 術語可以出現，但同一 beat 必須附白話解釋 |
| HARD_BAN | 內部工程詞不進旁白 |

新詞先以 warning 出現，再由人工依自有逐字稿判級。不要把公開 starter list
宣稱成任何特定創作者的受眾證據。

## 支柱 3：留存節奏

- cold open 先給結果或懸念，不用自介拖延。
- 每個中段 beat 要有問題、轉折或新 payoff。
- 長 beat 應拆段，並穿插短句打點。
- re-hook 與 pattern interrupt 的落點依實際字速與片長計算。
- 片尾只保留一個主要動作，並把已開的 loop 關完。

所有字速、句長和時間門檻都是可覆寫的 starter defaults。先用自己的錄音量測，
再將 profile、樣本範圍與變更理由寫入 evidence ledger。

## 交付流程

載入 creator profile → 起稿 → 精簡 → 跑 `script_gate.gate(text)` →
人工處理 warnings → 錄音。只有使用者自己的 transcript/evaluation 能升級為其預設值。
'''


def _script_retention(_: str) -> str:
    return PUBLIC_SCRIPT_RETENTION


PUBLIC_WAVE_PREAMBLE = '''# 剪輯技法 wave5 — 細剪 / 留存 / 數據呈現 / 工具

> **PUBLIC_FIXTURE / privacy boundary:** maintainer project names, channel AVP,
> dated evaluations and local calibration paths are excluded.  Numeric claims
> below that cite external sources remain research leads, not creator defaults.

所有落地先編譯成 structured edit commands，再經 audit、atomic apply、render、
delivery QA 與 human review；media primitives 不得形成旁路。'''


PUBLIC_RETENTION_RULES = '''### 6. 靜默間隙與句長瘦身
落地：以可設定的 silence threshold 收緊無內容停頓；句長 lint 只提示，不改語意。
機制：刪除無價值時間可提高資訊密度。公開版不附單一頻道 AVP，成效以使用者自己的 comparable window 驗證。

### 7. 結尾防衰減
落地：讓旁白與音樂跨過 end-screen 邊界，CTA 只留一個主要動作；outro 內容由 creator profile 提供。
機制：避免用告別真空向觀眾發出提早離場訊號。

### 8. 發布後留存診斷
落地：在固定窗口讀平台留存圖，將明顯 dip 對回時間軸，再提出可逆的 trim 方案。
機制：只與使用者自己的歷史片及相同窗口比較；PUBLIC_FIXTURE 不包含私有百分比或專案狀態。'''


PUBLIC_FINECUT_INTERRUPT = '''### 8. Pattern interrupt 時刻表
第一個刻意 interrupt、後續 major reset 與 midpoint format change 都應由片長和內容結構算出，
不是繼承另一支片的時間表。`script_gate` 驗證計畫落點，delivery QA 對照成片時間軸；
誤差門檻由專案 profile 設定。

機制：注意力會在無變化時衰減，但過度 reset 也會破壞理解。PUBLIC_FIXTURE 不包含
維護者的 AVP 或私有留存曲線。'''


def _editing_wave(text: str) -> str:
    text = _lf(text)
    first_topic = text.find("## TOPIC: retention")
    if first_topic < 0:
        raise ValueError("public sanitizer expected wave5 retention topic")
    text = PUBLIC_WAVE_PREAMBLE + "\n\n" + text[first_topic:]
    text = _between(text, "### 6. 靜默間隙", "SKIP:", PUBLIC_RETENTION_RULES)
    text = _between(text, "SKIP:", "## TOPIC: dataviz", "SKIP: Do not inherit another creator's audience assumptions or private calibration values.")
    finecut = text.find("## TOPIC: finecut")
    if finecut < 0:
        raise ValueError("public sanitizer expected wave5 finecut topic")
    prefix, suffix = text[:finecut], text[finecut:]
    suffix = _between(suffix, "### 8. Pattern interrupt", "### 9.", PUBLIC_FINECUT_INTERRUPT)
    return _generalize_identity(prefix + suffix)


PUBLIC_EDITING_TECHNIQUES = '''# Editing techniques — public quick reference

> **PUBLIC_FIXTURE / privacy boundary:** no maintainer project, channel metric,
> transcript example, audience baseline or private style verdict is included.
> Numeric defaults must be calibrated from creator-owned comparable evidence.

## A. Shorts / Reels

- Put the strongest verified visual and promise first; remove empty lead-in.
- Bind captions and cuts to inspected source evidence, not guessed timestamps.
- Use punch-ins, text emphasis and sound only when they clarify a beat.
- A loop must preserve visual continuity and cannot hide a false claim.
- Evaluate identical platform, duration and D2/D7/D28 windows before changing a gate.

## B. Long-form

- Diagnose retention by mapping dips and replays back to the exact timeline.
- The opening must visually fulfill title/thumbnail expectations early.
- Use narrative progress, proof and questions as pattern interrupts; do not cut on a timer alone.
- Chapters, B-roll and transitions describe structure, not decoration.
- Compare only against the creator's own calibrated baseline and retain the evidence receipt.

## C. Captions and audio

- Keep text inside platform safe zones with verified contrast and readable dwell.
- Generate line timing from approved word timestamps; preserve transcript meaning.
- Duck music around speech, verify full-duration coverage and run delivery loudness QA.
- Tie SFX to a visible event and cap repetition.

## D. Execution contract

Compile each edit into structured commands with source evidence and bounds, audit the plan,
apply atomically, render, run delivery QA, then require human review.  PUBLIC_FIXTURE
parameters are examples only; creator profile and project evidence remain the authority.
'''


def _editing_techniques(_: str) -> str:
    return PUBLIC_EDITING_TECHNIQUES


PUBLIC_SHORTS_DIAGNOSTICS = '''## §1 頻道診斷（自有 evidence only）

> **PUBLIC_FIXTURE / privacy boundary:** the maintainer's views, retention,
> subscription conversion, audience mix and RPM are excluded.

Short-form 表現可能同時來自推薦與搜尋。公開版不附生死百分比：

1. 固定 D2/D7/D28 窗口記錄自己的 views、engaged views、續看、重看與來源。
2. 只比較相同平台、片長帶與窗口；低續看先查首幀與前兩秒，但不能單指標宣判影片死亡。
3. 搜尋流量要另看 query 與長尾；推薦流量要另看首幀、早期流失和 replay。
4. 任何 threshold 都由至少 3-5 支 comparable releases 校準，並保留樣本與版本。

Shorts 是拉新或變現工具，必須由自己的收入與轉換資料判斷，不能繼承另一頻道 RPM。'''


PUBLIC_READING_RULE = '''- **S-R 閱讀速率（profile-calibrated）**：
  每條字幕用「可讀字數 ÷ 停留秒數」檢查；舒適值與 fail 值由 creator profile 提供。
  先保證讀得完，再追求換句密度。PUBLIC_FIXTURE 不包含私有抱怨原句、批次片數或實測 pace。'''


PUBLIC_FACT_BOUNDARY = '''### S-J 事實邊界

可讀物（價格、品名、招牌文字）必須由畫面或核准來源自證；歷史、地理與規格可以由
最新的可信外部來源查證。畫面看不清就不要猜，查不到就使用有限敘述。
PUBLIC_FIXTURE 不包含維護者的旅行地點或路線。'''


def _shorts_mastery(text: str) -> str:
    text = _between(text, "## §1", "## §2", PUBLIC_SHORTS_DIAGNOSTICS)
    text = re.sub(
        r"(?m)^\| 判斷生死看什麼？ \|.*$",
        "| 判斷生死看什麼？ | 用自己的 comparable windows 校準；公開版不附門檻 |",
        text,
    )
    text = _between(text, "- **S-R 閱讀速率", "- **S-S 字幕美術模式", PUBLIC_READING_RULE)
    text = _between(text, "### S-J 邊界裁定", "### 技術基礎", PUBLIC_FACT_BOUNDARY)
    text = re.sub(r"(?m)^## §3 .*?$", "## §3 剪輯鐵則（public generalized rules）", text)
    return _generalize_identity(text)


def _publish_remix_reference(text: str) -> str:
    text = re.sub(
        r"(?m)^短片：.*?版本由 `publish\.json` 管，不使用 `final_final_v3`。$",
        "短片：`S021_demo-short.mp4`。長片：`L001_demo-topic.mp4`。再製片：`R001_demo-route.mp4`。檔名只放可辨識內容；PUBLIC_FIXTURE 不含維護者專案名稱。",
        _lf(text),
    )
    text = _between(
        text, "## 已發佈素材的再製", "## 去重",
        '''## 已發佈素材的再製

已發佈不等於封存。系統可按使用者提供的區域、旅程、系列或題材 metadata 產生候選。
再製必須回到原始片段重建 Hook、順序、字幕與節奏，禁止串接帶燒錄字幕的發布檔。

PUBLIC_FIXTURE 使用 S101-S104 的合成四站路線示範 schema；不包含真實地點、來源範圍或行程。''',
    )
    return _generalize_identity(text)


PUBLIC_GENRE_READABILITY = '''## 第五刀：讀得完

每條字幕用「可讀字數 ÷ 停留秒數」檢查；舒適值與 fail 值由 creator profile 設定。
先決定畫面能停多久，再決定能放多少字。PUBLIC_FIXTURE 不包含私有抱怨原句、
店家專案或批次 pace。'''


PUBLIC_FOOD_COPY = '''### 🍜 美食（public generalized examples）
- 字幕優先寫畫面可證實的品名、價格與動作；慾望詞只在 payoff 使用。
- hook 先給具體口感、製程或反差，不預設任何真實店名。
- 價格可獨立成大字，但必須由畫面、菜單或核准來源驗證。
- 文案用具體名詞取代空泛形容，CTA 只留一個可回答或可分享的動作。

PUBLIC_FIXTURE: examples are synthetic and contain no maintainer restaurant project.'''


PUBLIC_TRAVEL_COPY = '''### 🏞️ 旅遊/景點（public generalized examples）
- hook 使用可由畫面或查證來源支持的意外性與反差。
- 用人物、道路或建築作比例尺；地名、歷史與交通資訊先查證。
- 畫面上的路牌、刻字與告示只有在可讀時才能引用。
- 結尾給一個行動；搜尋字詞由使用者自己的地點與研究 catalog 提供。

PUBLIC_FIXTURE: no maintainer route, backend sample or private travel transcript is included.'''


PUBLIC_GENRE_COPY_INTRO = '''# 分類型文字語法（字幕＋文案共用）

> **PUBLIC_FIXTURE / privacy boundary:** public rules exclude maintainer raw quotes,
> dated incidents, internal draft wording and local outcome examples.
> Build attractive copy from verified concrete nouns, visible actions, contrast and payoff;
> reorder true facts for interest, but never invent a claim.'''


def _genre_copy_reference(text: str) -> str:
    text = _between(text, "# 分類型文字語法", "## 通用四刀", PUBLIC_GENRE_COPY_INTRO)
    text = _between(text, "## 第五刀", "## 分類型語法", PUBLIC_GENRE_READABILITY)
    text = _between(text, "### 🍜 美食", "### 🏞️ 旅遊/景點", PUBLIC_FOOD_COPY)
    text = _between(text, "### 🏞️ 旅遊/景點", "### 📦 開箱", PUBLIC_TRAVEL_COPY)
    return _generalize_identity(text)


_GPS_MEASURED_OUTCOME_LINE = re.compile(
    r"(?im)^(?=[^\r\n]*(?:\u5be6\u6e2c|measured|outcome|result))"
    r"(?=[^\r\n]*GPS)(?=[^\r\n]*\d+(?:\.\d+)?\s*%\s*coverage\b)[^\r\n]*$"
)


def _autopilot_workflow(text: str) -> str:
    public = _GPS_MEASURED_OUTCOME_LINE.sub(
        "PUBLIC_FIXTURE：Scene Timeline 可依時間間隔或 GPS 距離分群；實際 coverage 與拍攝時間正確性必須用創作者自己的素材驗證。",
        _lf(text),
    )
    if PUBLIC_FIXTURE not in public:
        public = "<!-- PUBLIC_FIXTURE: maintainer GPS outcomes are excluded. -->\n\n" + public
    return public


def _silent_vlog_checklists(text: str) -> str:
    text, first = re.subn(
        r'(?m)^(\s*)"🌪️ TIM PAN[^\n]*",$',
        r'\1"PUBLIC_FIXTURE: reference craft may be integrated, but outro, face policy, palette, voice, loudness and community proof come from the active creator profile",',
        _lf(text), count=1,
    )
    text, second = re.subn(
        r'(?m)^(\s*)"VERIFY 0 \(TIM PAN[^\n]*",$',
        r'\1"VERIFY 0 (PUBLIC_FIXTURE): verify the active creator profile for opening grammar, slogan-card use, loudness, face policy, outro and CTA; no maintainer defaults ship",',
        text, count=1,
    )
    if first != 1 or second != 1:
        raise ValueError("public sanitizer expected two private-profile checklist entries")
    return text


PUBLIC_SHORTS_TEMPLATE_DOC = '''"""Reusable no-face vertical template (public distribution).

The template preserves structural energy while sourcing face policy, palette,
voice, outro and CTA from the active creator profile.  It ships no maintainer
brand phrase, community count or private sign-off.

PUBLIC_FIXTURE: profile-specific outro and community defaults are excluded.
"""'''


def _shorts_template(text: str) -> str:
    text = _replace_module_docstring(text, PUBLIC_SHORTS_TEMPLATE_DOC)
    text = _generalize_identity(text)
    text = re.sub(r"creator brand\s+彩色 outro 卡", "creator-configured outro card", text)
    text = re.sub(r"軟尾掰掰\s*\+\s*SUBSCRIBE\s*\+\s*[A-Za-z]+", "creator-configured CTA", text)
    return _generalize_project_ids(text)


PUBLIC_LONGFORM_PIPELINE = '''# Teaching long-form pipeline (public distribution)

> **PUBLIC_FIXTURE / privacy boundary:** no maintainer project title, local path,
> transcript excerpt, analytics screenshot value or dated evaluation ships here.

## 1. Control contract

Bind approved sources and transcript cues, compile an edit plan, audit it, apply
once, render to a candidate, run delivery QA, atomically publish `current.mp4`,
then require a human review receipt.  A media helper may implement a command but
must not bypass the plan/receipt chain.

## 2. Reusable stages

1. `script_gate.py` checks hook, structure, audience language and rhythm.
2. `audio_chain.py` trims, aligns, mixes and verifies full-duration coverage.
3. `word_captions.py` builds semantic caption groups from approved word timing.
4. `visual_director.py` and `video_handlers.py` bind evidence to visual beats.
5. `proof_stage.py` presents approved evidence without inventing results.
6. `delivery.py` registers only the current, QA-bound artifact in Publish Hub.

## 3. Project inputs

Keep per-video narration, source mappings, offsets, scene plans, generated
graphics and publish copy inside that video's workspace.  Reusable modules stay
in `src/longform_maker/`; do not copy them into a build directory.

## 4. Calibration

Speaking rate, caption density, color thresholds, music level, pacing and KPI
comparisons must come from creator-owned evidence.  Public defaults are starter
fixtures only.  Record the sample set, comparison window and reason whenever a
threshold changes.

## 5. Delivery gates

- source facts and transcript cues are approved and traceable;
- captions preserve meaning, safe area and readability;
- audio covers the full video and satisfies the selected delivery profile;
- the render SHA matches technical QA and the mobile review entry;
- human review remains uncertified machine state until a person decides;
- only `_out/current.mp4` is the active render; versions live in metadata.

Run module self-tests plus the repository quick/system-health gates before a
release.  Missing private calibration media is expected in the public kit and
must not be treated as a passing real-corpus regression.
'''


def _longform_pipeline(_: str) -> str:
    return PUBLIC_LONGFORM_PIPELINE


SANITIZERS = {
    "src/channel_tracker.py": _channel_tracker,
    "src/publish_hub_ops.py": lambda text: _replace_function(text, "create_miaoli_remix_plan", PUBLIC_DEMO_PLAN_FUNCTION),
    "src/remix_planner.py": _remix_planner,
    "src/asset_registry.py": _asset_registry,
    "src/silent_vlog_maker/checklists.py": _silent_vlog_checklists,
    "src/silent_vlog_maker/shorts_template.py": _shorts_template,
    "src/silent_vlog_maker/shorts_vertical.py": _shorts_vertical,
    "src/silent_vlog_maker/constants.py": _silent_vlog_constants,
    "src/longform_maker/shorts_gate.py": _shorts_gate,
    "knowledge/runtime/topic_research_catalog.json": _topic_catalog,
    "src/longform_maker/script_gate.py": _script_gate,
    "src/longform_maker/word_captions.py": _word_captions,
    "src/publish_hub.py": _publish_hub,
    "src/longform_maker/grade_calibrate.py": _grade_calibrate,
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
