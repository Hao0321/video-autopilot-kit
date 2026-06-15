"""
capcut_helpers.caption_broll_matcher — AP15 (2026-05-26).

Land AP15 from Mode C #3: Build script 必做 caption-to-broll content matching audit.

Root cause of #006 v3→v4 bug:
- Caption「首先這是我的Studio網站」at t=48s landed on book b-roll (mismatch)
- Root: build_capcut_draft.py 順序填 b-roll，沒檢查 caption topic vs asset content

Solution = this module:
- `score_broll_for_caption()` — keyword-based scorer
- `match_brolls_to_captions()` — for each caption, suggest best broll
- `audit_caption_broll_mismatch()` — read existing draft, find existing mismatches
- `HAO_CAPTION_KEYWORD_MAP` — default topic→keyword map (extensible)

Usage:
    from capcut_helpers import (
        load_draft, audit_caption_broll_mismatch, match_brolls_to_captions,
        HAO_CAPTION_KEYWORD_MAP,
    )

    # BEFORE build — match captions to brolls
    captions = [{'text': '首先這是我的Studio網站', 'start_us': 48_600_000, 'duration_us': 3_000_000}]
    brolls = [Path('seg_02_studio.mp4'), Path('seg_01_book.mp4'), ...]
    matches = match_brolls_to_captions(captions, brolls)
    for m in matches:
        print(f'{m["caption_text"]!r} → {m["best_broll"]} (score {m["score"]:.2f})')

    # AFTER build — audit existing draft for mismatches
    draft = load_draft('My-Project')
    report = audit_caption_broll_mismatch(draft)
    print(f'Mismatches: {len(report["mismatches"])} / {report["total_captions"]} captions')
    for m in report['mismatches']:
        print(f'  t={m["caption_start_sec"]:.1f}s {m["caption_text"]!r} '
              f'on {m["current_broll"]} → should be {m["suggested_broll"]}')
"""
import json
import re
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────────────────────────────
# EXAMPLE keyword map (author's topics) — DEFAULT is empty {} + filename matching
# Extensible: 用 extra_map kwarg 加新 topic 或 override
# ─────────────────────────────────────────────────────────────────────

# EXAMPLE only — functions DEFAULT to filename↔caption token matching (zero config).
# Copy this structure for your own topics, OR name b-roll after content. Pass keyword_map=YOURS.
EXAMPLE_KEYWORD_MAP = {
    "studio_website": {
        "caption_keywords": [
            "Studio網站", "Studio 網站", "我的網站",
            "首頁", "3D Render", "3D 質感",
        ],
        "broll_keywords": [
            "studio",
        ],
        "topic_label": "Studio 網站 demo",
    },
    "game_hall": {
        "caption_keywords": [
            "遊戲大廳", "14款", "14 款", "原創小遊戲",
            "にゃんこ", "突擊", "策略", "動作", "益智", "卡牌", "桌遊",
            "HAO SURVIVOR", "吸血鬼",
        ],
        "broll_keywords": [
            "game", "遊戲",
        ],
        "topic_label": "Game hall demo",
    },
    "player_system": {
        "caption_keywords": [
            "玩家系統", "金幣", "簽到", "徽章", "Streak", "連勝", "排行",
            "個人資料", "50金幣", "7天", "成就", "任務系統",
        ],
        "broll_keywords": [
            "player", "profile", "徽章",
        ],
        "topic_label": "Player profile / 玩家系統",
    },
    "code_editing": {
        "caption_keywords": [
            "Code", "Debug", "架構", "UI", "寫過 Code", "沒寫過Code", "把 Claude 當",
            "團隊", "工程師", "提示詞", "prompt",
        ],
        "broll_keywords": [
            "code", "editor", "vscode", "cursor", "ide", "debug",
        ],
        "topic_label": "Code / Debug",
    },
    "research_learning": {
        "caption_keywords": [
            "研究", "學習", "一頭栽進去", "學會了", "誤打誤撞", "外行人",
            "從零", "幾個月", "90 天", "90天",
        ],
        "broll_keywords": [
            "book", "study", "research", "reading", "page", "flip",
        ],
        "topic_label": "Research / 研究 / 學習",
    },
    "reflection_lifestyle": {
        "caption_keywords": [
            "感觸", "到這邊", "結束", "掰掰", "我們下", "社群",
            "歡迎", "留言", "討論", "創作者", "開發者",
        ],
        "broll_keywords": [
            "coffee", "meeting", "roundtable", "lifestyle", "talk",
        ],
        "topic_label": "Reflection / 收尾 / 反思",
    },
    "intro_generic": {
        "caption_keywords": [
            "今天這一支", "大家好", "訂閱", "看到最後", "瘋狂",
            "我跟你們說", "你們說",
        ],
        "broll_keywords": [
            "laptop", "typing", "hand", "intro",
        ],
        "topic_label": "Intro / generic talking",
    },
    "food_dish": {
        # For #004-style food vlogs
        "caption_keywords": [
            "拉麵", "湯頭", "叉燒", "鹽味", "醬油", "麵條", "配料",
            "好吃", "美味", "招牌",
        ],
        "broll_keywords": [
            "ramen", "noodle", "bowl", "food", "dish", "soup",
        ],
        "topic_label": "Food / 菜品",
    },
    "shop_info": {
        # For #004-style food vlogs — outro store info
        "caption_keywords": [
            "店", "店家", "地址", "營業時間", "電話", "淡水",
            "中山路", "重建街", "分店",
        ],
        "broll_keywords": [
            "storefront", "shop", "exterior", "sign",
        ],
        "topic_label": "Shop info / 店家",
    },
}


# ─────────────────────────────────────────────────────────────────────
HAO_CAPTION_KEYWORD_MAP = EXAMPLE_KEYWORD_MAP  # back-compat alias


# Language-agnostic ZERO-CONFIG fallback (2026-06-10 — adopter bug report)
# 沒有 keyword_map（或非中文 / 非 Hao 主題）時，靠「caption 文字 ↔ b-roll 檔名」
# 共同 token 對位 —— 採用者只要把素材用內容命名 (coffee.mp4 / sunset.mov)
# 就能對齊旁白，完全不用設定 keyword map。
# ─────────────────────────────────────────────────────────────────────

_FILENAME_STOP = {
    "seg", "clip", "video", "vid", "final", "raw", "broll", "cleaned",
    "output", "out", "tmp", "copy", "edit", "scene", "shot", "take",
    "mp4", "mov", "mkv", "webm", "m4v", "the", "and", "for", "with",
}


def _stem(w: str) -> str:
    """極輕量詞幹化（無依賴）：砍常見英文字尾，讓 pour↔pouring / sunset↔sunsets 對得上。"""
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def _content_tokens(s: str) -> set:
    """語言無關 content token：拉丁詞(≥2 字母,含詞幹) + CJK 單字 + CJK bigram。"""
    s = str(s).lower()
    words = re.findall(r"[a-z][a-z0-9]{1,}", s)
    latin = set(words) | {_stem(w) for w in words}   # 原詞 + 詞幹 → 容時態/單複數
    cjk = [ch for ch in s if "一" <= ch <= "鿿"]
    bigrams = {cjk[i] + cjk[i + 1] for i in range(len(cjk) - 1)}
    return latin | set(cjk) | bigrams


def _filename_caption_overlap(caption_text: str, broll_identifier: str) -> float:
    """Zero-config fallback：caption 文字 ↔ 檔名共同 token 比例 → 0.0–0.6。
    讓採用者用內容命名素材就能對位，不必設 keyword map。"""
    import os
    name = os.path.splitext(os.path.basename(str(broll_identifier)))[0]
    cap = _content_tokens(caption_text)
    broll = _content_tokens(name) - _FILENAME_STOP
    broll = {t for t in broll if not t.isdigit()}  # 丟掉 uuid / seg 編號
    if not cap or not broll:
        return 0.0
    shared = cap & broll
    if not shared:
        return 0.0
    return min(0.6, 0.3 + 0.1 * len(shared))


# ─────────────────────────────────────────────────────────────────────
# Scoring + matching functions
# ─────────────────────────────────────────────────────────────────────


def score_broll_for_caption(
    caption_text: str,
    broll_identifier: str,
    keyword_map: Optional[dict] = None,
) -> tuple[float, str]:
    """Score how well a b-roll matches a caption (0.0-1.0).

    Args:
        caption_text: The caption text (Chinese / English mix OK)
        broll_identifier: Filename, asset name, OR path basename of the broll
        keyword_map: Optional override of HAO_CAPTION_KEYWORD_MAP

    Returns: (score, matched_topic_label)
        Score logic:
          - 1.0 = caption keyword AND broll keyword both match SAME topic (perfect)
          - 0.7 = strong caption topic match but broll keyword only partial
          - 0.5 = broll matches but caption is generic (no topic keyword)
          - 0.3 = caption matches but broll is generic
          - 0.0 = no match

    Example:
        >>> score_broll_for_caption('首先這是我的Studio網站', 'studio.mp4')
        (1.0, 'Studio 網站 demo')
        >>> score_broll_for_caption('首先這是我的Studio網站', 'seg_01_book-flip.mp4')
        (0.3, '')  # caption matches studio topic, broll matches research topic — mismatch
    """
    km = keyword_map if keyword_map is not None else {}  # 公開版預設純 filename↔caption 對位
    # coerce 到 str — 採用者常傳 pathlib.Path（glob 出來的）；docstring 範例也是 Path
    # 之前直接 .lower() → AttributeError 'WindowsPath' (2026-06-10 adopter fix)
    caption_text = str(caption_text)
    broll_identifier = str(broll_identifier)
    caption_lower = caption_text.lower()
    broll_lower = broll_identifier.lower()

    caption_topic_hits = {}  # topic_id → count of caption keyword matches
    broll_topic_hits = {}    # topic_id → count of broll keyword matches

    for topic_id, spec in km.items():
        for kw in spec.get("caption_keywords", []):
            if kw.lower() in caption_lower:
                caption_topic_hits[topic_id] = caption_topic_hits.get(topic_id, 0) + 1
        for kw in spec.get("broll_keywords", []):
            if kw.lower() in broll_lower:
                broll_topic_hits[topic_id] = broll_topic_hits.get(topic_id, 0) + 1

    # Find topics that BOTH caption + broll match → perfect
    both_match = set(caption_topic_hits.keys()) & set(broll_topic_hits.keys())
    if both_match:
        # Pick topic with strongest combined signal
        best_topic = max(both_match, key=lambda t: caption_topic_hits[t] + broll_topic_hits[t])
        return (1.0, km[best_topic]["topic_label"])

    # Caption matches a topic but broll doesn't — MISMATCH
    if caption_topic_hits:
        best_topic = max(caption_topic_hits.keys(), key=lambda t: caption_topic_hits[t])
        return (0.3, km[best_topic]["topic_label"])

    # Broll matches but caption is generic (acceptable filler)
    if broll_topic_hits:
        best_topic = max(broll_topic_hits.keys(), key=lambda t: broll_topic_hits[t])
        return (0.5, km[best_topic]["topic_label"])

    # Neither keyword-matches — zero-config fallback: caption↔filename token overlap
    # (讓沒設 keyword_map / 非中文 / 非 Hao 主題的採用者也能對位)
    fb = _filename_caption_overlap(caption_text, broll_identifier)
    if fb > 0:
        return (fb, "filename↔caption match")
    return (0.0, "")


def match_brolls_to_captions(
    captions: list[dict],
    broll_identifiers: list[str],
    keyword_map: Optional[dict] = None,
) -> list[dict]:
    """For each caption, find best-matching b-roll from the available pool.

    Args:
        captions: [{text: str, start_us: int, duration_us: int}, ...]
        broll_identifiers: ['seg_00_laptop.mp4', 'seg_02_studio.mp4', ...]
        keyword_map: Optional override

    Returns: [
        {
            caption_idx: int,
            caption_text: str,
            caption_start_sec: float,
            best_broll: str,
            best_broll_idx: int,
            score: float,
            topic_label: str,
            alternatives: [(broll, score), ...],  # top 3 sorted desc
        },
        ...
    ]
    """
    results = []
    for c_idx, c in enumerate(captions):
        text = c.get("text", "")
        if not text:
            continue
        scores = []
        for b_idx, b in enumerate(broll_identifiers):
            sc, label = score_broll_for_caption(text, b, keyword_map)
            scores.append((b_idx, b, sc, label))

        # Sort by score desc
        scores.sort(key=lambda x: -x[2])
        best = scores[0]

        results.append({
            "caption_idx": c_idx,
            "caption_text": text,
            "caption_start_sec": c.get("start_us", 0) / 1e6,
            "best_broll": best[1],
            "best_broll_idx": best[0],
            "score": best[2],
            "topic_label": best[3],
            "alternatives": [(b[1], b[2]) for b in scores[1:4]],
        })
    return results


def audit_caption_broll_mismatch(
    draft: dict,
    keyword_map: Optional[dict] = None,
    score_threshold: float = 0.5,
) -> dict:
    """Read existing draft → audit each caption against the b-roll currently shown at its timestamp.

    Args:
        draft: Loaded CapCut draft dict (from load_draft())
        keyword_map: Optional override
        score_threshold: Captions scoring BELOW this on current broll = flagged as mismatch

    Returns: {
        total_captions: int,
        matched_ok: int,        # score >= threshold
        mismatches: [
            {
                caption_idx: int,
                caption_text: str,
                caption_start_sec: float,
                current_broll: str,
                current_score: float,
                suggested_broll: str,
                suggested_score: float,
                score_diff: float,  # positive = suggested is better
            },
            ...
        ],
        summary_by_severity: {high: N, medium: N, low: N},
    }

    Use this AFTER build to catch caption-to-broll mismatches BEFORE Export
    (Mode C #3 AP15 落地 — 避免 v4-style「Studio caption 配 book」mismatch).
    """
    texts_by_id = {t.get("id"): t for t in draft.get("materials", {}).get("texts", [])}
    videos_by_id = {v.get("id"): v for v in draft.get("materials", {}).get("videos", [])}

    # Build video timeline
    video_timeline = []  # [(start_us, end_us, identifier), ...]
    for tr in draft.get("tracks", []):
        if tr.get("type") != "video":
            continue
        for seg in tr.get("segments", []):
            ttr = seg.get("target_timerange", {})
            ss = ttr.get("start", 0)
            se = ss + ttr.get("duration", 0)
            mat = videos_by_id.get(seg.get("material_id", ""), {})
            name = mat.get("material_name", mat.get("id", "?"))
            video_timeline.append((ss, se, name))

    def broll_at(t_us):
        for ss, se, name in video_timeline:
            if ss <= t_us < se:
                return name
        return "?"

    # Build broll identifier pool for "what could be better" suggestions
    broll_pool = list({name for _, _, name in video_timeline})

    # Walk all text segments (Chinese subtitle track is usually most informative)
    mismatches = []
    matched_ok = 0
    total = 0
    high = medium = low = 0

    # 中英雙軌時 audit 中文軌 — 真的用 CJK 字數挑軌（2026-06-10 audit 修正：
    # 之前只是 break 在第一條有字的軌，英文軌排前面就 audit 錯軌）
    def _track_cjk_count(tr):
        n = 0
        for seg in tr.get("segments", []):
            mat = texts_by_id.get(seg.get("material_id", ""), {})
            try:
                t = json.loads(mat.get("content", "{}")).get("text", "")
            except json.JSONDecodeError:
                continue
            n += sum(1 for ch in t if "一" <= ch <= "鿿")
        return n

    text_tracks = [(i, tr) for i, tr in enumerate(draft.get("tracks", []))
                   if tr.get("type") == "text" and tr.get("segments")]
    if text_tracks:
        text_tracks = [max(text_tracks, key=lambda it: _track_cjk_count(it[1]))]

    for tr_idx, tr in text_tracks:
        for seg in tr.get("segments", []):
            mat = texts_by_id.get(seg.get("material_id", ""), {})
            try:
                co = json.loads(mat.get("content", "{}"))
                text = co.get("text", "")
            except json.JSONDecodeError:
                continue
            if not text:
                continue
            ss = seg.get("target_timerange", {}).get("start", 0)
            current_broll = broll_at(ss)
            current_score, _ = score_broll_for_caption(text, current_broll, keyword_map)

            total += 1

            if current_score >= score_threshold:
                matched_ok += 1
                continue

            # Check if there's a better broll in the pool
            best_alt_score = current_score
            best_alt_broll = current_broll
            for candidate in broll_pool:
                if candidate == current_broll:
                    continue
                sc, _ = score_broll_for_caption(text, candidate, keyword_map)
                if sc > best_alt_score:
                    best_alt_score = sc
                    best_alt_broll = candidate

            if best_alt_score > current_score:
                diff = best_alt_score - current_score
                severity = "high" if diff >= 0.5 else ("medium" if diff >= 0.3 else "low")
                if severity == "high":
                    high += 1
                elif severity == "medium":
                    medium += 1
                else:
                    low += 1

                mismatches.append({
                    "caption_idx": len(mismatches),
                    "track_idx": tr_idx,
                    "caption_text": text,
                    "caption_start_sec": ss / 1e6,
                    "current_broll": current_broll,
                    "current_score": current_score,
                    "suggested_broll": best_alt_broll,
                    "suggested_score": best_alt_score,
                    "score_diff": diff,
                    "severity": severity,
                })

    return {
        "total_captions": total,
        "matched_ok": matched_ok,
        "mismatches": mismatches,
        "summary_by_severity": {"high": high, "medium": medium, "low": low},
    }


def print_mismatch_report(report: dict, max_show: int = 20) -> None:
    """Pretty-print the audit report from audit_caption_broll_mismatch()."""
    total = report["total_captions"]
    ok = report["matched_ok"]
    miss = len(report["mismatches"])
    sev = report["summary_by_severity"]

    print("=" * 78)
    print(f"📐 Caption-Broll Mismatch Audit (AP15)")
    print("=" * 78)
    print(f"Total captions: {total}")
    print(f"Matched OK:     {ok}  ({100*ok/max(total,1):.0f}%)")
    print(f"Mismatches:     {miss}  (high {sev['high']} / medium {sev['medium']} / low {sev['low']})")
    print()

    if not report["mismatches"]:
        print("✅ No mismatches — all captions align with b-roll content")
        return

    print(f"⚠️  Top {min(max_show, miss)} mismatches (sorted by severity):")
    sorted_m = sorted(report["mismatches"], key=lambda m: -m["score_diff"])
    for m in sorted_m[:max_show]:
        sev_icon = "🔴" if m["severity"] == "high" else ("🟡" if m["severity"] == "medium" else "🟠")
        print(f"  {sev_icon} t={m['caption_start_sec']:6.2f}s  "
              f"{m['caption_text'][:35]!r:38}  "
              f"on {m['current_broll'][:30]:32}  "
              f"→ {m['suggested_broll'][:30]} "
              f"(Δ{m['score_diff']:+.2f})")

    if miss > max_show:
        print(f"  ... and {miss - max_show} more")


# ─────────────────────────────────────────────────────────────────────
# 🆕 M75 (2026-05-26) — Build-time auto-sequencer
# 比 audit 進階：直接根據 caption topic + broll pool + total duration
# 算出 ordered video timeline 給 build_capcut_draft.py 用
# ─────────────────────────────────────────────────────────────────────

from dataclasses import dataclass, field


@dataclass
class BrollAssignment:
    """One slot in the auto-sequenced video timeline.

    Drop directly into build_capcut_draft.py Track[0]:
        for a in assignments:
            add_video_segment(
                broll_path=a.broll_id,
                target_start=a.start_us,
                target_duration=a.duration_us,
                source_start=a.source_trim_us[0],
                source_end=a.source_trim_us[1],
            )
    """
    broll_id: str                              # filename or asset identifier
    start_us: int                              # target timeline start
    duration_us: int                           # how long this broll plays in timeline
    source_trim_us: tuple                      # (start_us, end_us) — which portion of source to use
    captions_covered: list = field(default_factory=list)  # caption indices covered
    topic_label: str = ""                      # which topic this broll matched
    avg_score: float = 0.0                     # avg caption-broll score for covered captions
    is_filler: bool = False                    # True if this is generic filler (no topic match)


def _dominant_topic(caption_text: str, keyword_map: dict) -> tuple:
    """Find the dominant topic for a caption.

    Returns: (topic_id or 'generic', hit_count)
    """
    hits = {}
    text_lower = caption_text.lower()
    for topic_id, spec in keyword_map.items():
        cnt = sum(1 for kw in spec.get("caption_keywords", [])
                  if kw.lower() in text_lower)
        if cnt > 0:
            hits[topic_id] = cnt
    if not hits:
        return "generic", 0
    best = max(hits.keys(), key=lambda t: hits[t])
    return best, hits[best]


def _windowed_topic(caption_text_list: list, center_idx: int, window: int,
                    keyword_map: dict, decay: float = 0.5) -> tuple:
    """🆕 M75 v0.2 — Windowed look-ahead for narrative beat detection.

    Looks at caption[center_idx] AND surrounding ±window neighbours, weights
    hits by distance-decay. A caption fragment that scores weakly on its own
    can inherit topic from neighbouring strong-signal captions.

    Args:
        caption_text_list: full list of caption texts
        center_idx: index of caption under analysis
        window: how many neighbours each side (±window)
        keyword_map: HAO_CAPTION_KEYWORD_MAP
        decay: hit weight = decay**distance (e.g. 0.5 → ±1 neighbour worth half)

    Returns: (best_topic_id, weighted_score) — falls back to 'generic' if 0.
    """
    aggregate = {}
    for d in range(-window, window + 1):
        idx = center_idx + d
        if idx < 0 or idx >= len(caption_text_list):
            continue
        text_lower = caption_text_list[idx].lower()
        weight = decay ** abs(d)
        for topic_id, spec in keyword_map.items():
            cnt = sum(1 for kw in spec.get("caption_keywords", [])
                      if kw.lower() in text_lower)
            if cnt > 0:
                aggregate[topic_id] = aggregate.get(topic_id, 0.0) + cnt * weight
    if not aggregate:
        return "generic", 0.0
    best = max(aggregate.keys(), key=lambda t: aggregate[t])
    return best, aggregate[best]


def _best_broll_for_topic(topic_id: str, broll_pool: list, keyword_map: dict,
                          used_ids: set = None, allow_reuse: bool = True,
                          caption_hint: str = "") -> tuple:
    """Find best broll in pool matching a topic.

    caption_hint: 該段字幕文字 — topic 是 generic 時用它跟檔名 token 對位
    (zero-config fallback，讓沒 keyword_map 的採用者也對得上旁白)。

    Returns: (broll_id, broll_dict, score) or (None, None, 0.0) if nothing matches.
    """
    used_ids = used_ids or set()
    # pseudo-topic「__file__<id>」= tagging 階段綁定的素材，直接給回該支
    if topic_id.startswith("__file__"):
        want = topic_id[len("__file__"):]
        for b in broll_pool:
            if b["id"] == want and (allow_reuse or b["id"] not in used_ids):
                ov = _filename_caption_overlap(caption_hint, want) if caption_hint else 0.0
                return (b["id"], b, ov or 0.5)
        topic_id = "generic"  # 已用過且不可重用 → 退回 generic 內容比對
    if topic_id == "generic":
        # 1) zero-config content match：caption 文字 ↔ 檔名 token 重疊（最優先）
        if caption_hint:
            scored = [(b, _filename_caption_overlap(caption_hint, b["id"]))
                      for b in broll_pool
                      if allow_reuse or b["id"] not in used_ids]
            scored = [(b, ov) for b, ov in scored if ov > 0]
            if scored:
                scored.sort(key=lambda x: -x[1])
                return (scored[0][0]["id"], scored[0][0], scored[0][1])
        # 2) intro/laptop filler — pick anything not used (or laptop if reuse)
        intro_keywords = ["laptop", "typing", "hand", "intro", "coffee", "lifestyle"]
        candidates = [b for b in broll_pool
                      if any(kw in b["id"].lower() for kw in intro_keywords)
                      and (allow_reuse or b["id"] not in used_ids)]
        if candidates:
            return (candidates[0]["id"], candidates[0], 0.5)
        # 3) Fallback: anything unused
        for b in broll_pool:
            if allow_reuse or b["id"] not in used_ids:
                return (b["id"], b, 0.2)
        return (None, None, 0.0)

    # Topic-specific: score every broll against this topic's broll_keywords
    spec = keyword_map.get(topic_id, {})
    broll_kws = [kw.lower() for kw in spec.get("broll_keywords", [])]

    scored = []
    for b in broll_pool:
        if not allow_reuse and b["id"] in used_ids:
            continue
        b_lower = b["id"].lower()
        score = sum(1 for kw in broll_kws if kw in b_lower)
        if score > 0:
            scored.append((b, score))
    if not scored:
        return (None, None, 0.0)
    scored.sort(key=lambda x: -x[1])
    best = scored[0]
    return (best[0]["id"], best[0], 1.0)


def auto_sequence_brolls(
    captions: list,
    brolls: list,
    total_duration_us: int,
    keyword_map: Optional[dict] = None,
    allow_reuse: bool = True,
    min_segment_us: int = 5_000_000,
    consolidate_consecutive: bool = True,
    look_ahead_window: int = 2,
    look_ahead_decay: float = 0.5,
) -> list:
    """🆕 M75 v0.2 (2026-05-27) — Auto-sequence b-rolls + WINDOWED look-ahead.

    Args:
        captions: [{text: str, start_us: int, duration_us: int}, ...] sorted by start_us
        brolls: [{id: str, source_duration_us: int}, ...] — available b-roll pool
        total_duration_us: total timeline duration (= sum of all assignment durations)
        keyword_map: optional HAO_CAPTION_KEYWORD_MAP override
        allow_reuse: True = brolls can repeat / False = each used at most once
        min_segment_us: don't fragment below this (combine short clusters with neighbors)
        consolidate_consecutive: True = post-pass merge adjacent same-broll slots (recommended)

    Returns: list[BrollAssignment] sorted by start_us

    Algorithm (greedy topic-clustering + post-pass consolidation):
        1. Tag each caption with dominant topic (matches one or 'generic')
        2. Cluster consecutive captions with same topic into time spans
        3. Merge tiny clusters (< min_segment_us) into previous to avoid fragmentation
        4. For each cluster, allocate best-matching broll, capped at source duration
        5. If cluster > source duration, split & pick next-best broll for remainder
        6. Generic clusters → filler brolls (intro/laptop type)
        7. Always cover [0, total_duration_us] with no gaps
        8. Post-pass: consolidate consecutive same-broll assignments

    🆕 v0.2 ADDITIONS (2026-05-27):
        - WINDOWED look-ahead: each caption's topic considers ±N neighbours,
          weighted by `look_ahead_decay**distance`. Fixes v0.1 issue where a
          weak-signal caption between two strong-signal captions wrongly
          fell to 'generic'.
        - `look_ahead_window=0` → falls back to v0.1 per-caption greedy.

    ✅ v0.2 fixes (vs v0.1):
        - Cat Game OBS missed in #006 minute-2 zone (game-hall section)
          → expected: windowed mode now properly clusters the 「我做了 14 款小遊戲」+
          「免費玩」+「分類」captions into game-hall topic before they fragment.

    ⚠️  v0.2 STILL OPEN (v0.3 roadmap):
        - No "narrative arc" awareness — doesn't know hook→demo→cta structure.
        - `min_segment` merge always picks PREVIOUS cluster — should prefer keeping
          topic-specific small clusters and merging generic ones in/out.

        Workaround: use OUTPUT as FIRST DRAFT, then run audit_caption_broll_mismatch()
        on actual built draft to catch missed topic-broll matches, manually re-sequence
        (Path D) for problem spots.

    Use case (v0.2):
        ✅ "Is the build script using OBS recs at the right zones?" sanity check
        ✅ First-pass topic-broll placement (target 75-90% accurate, up from 50-80%)
        ⚠️  Not yet a fully autonomous build-time substitute for human review
    """
    km = keyword_map if keyword_map is not None else {}  # 公開版預設純 filename↔caption 對位
    if not captions or not brolls:
        return []

    # Step 1: tag each caption with dominant topic
    # 🆕 v0.2: use windowed look-ahead if window > 0, else fall back to v0.1 per-caption
    sorted_caps = sorted(captions, key=lambda c: c.get("start_us", 0))
    text_list = [c.get("text", "") for c in sorted_caps]
    tagged = []
    for i, c in enumerate(sorted_caps):
        text = text_list[i]
        if look_ahead_window > 0:
            topic, hits = _windowed_topic(text_list, i, look_ahead_window, km, look_ahead_decay)
        else:
            topic, hits = _dominant_topic(text, km)
        # 沒命中 keyword topic → 綁到「最 match 的素材檔名」當 pseudo-topic，
        # 這樣 generic 字幕不會併成一坨，會照各自內容拆 cluster（2026-06-10 adopter fix）
        if topic == "generic":
            best_id, best_ov = None, 0.0
            for b in brolls:
                ov = _filename_caption_overlap(text, b.get("id", ""))
                if ov > best_ov:
                    best_ov, best_id = ov, b.get("id")
            if best_id:
                topic = "__file__" + best_id
        tagged.append({
            "caption_idx": i,
            "text": text,
            "start_us": c.get("start_us", 0),
            "end_us": c.get("start_us", 0) + c.get("duration_us", 0),
            "topic": topic,
            "hits": hits,
        })

    # Step 2: cluster consecutive captions with same topic
    clusters = []  # [{topic, start_us, end_us, caption_idxs}]
    cur = None
    for tc in tagged:
        if cur is None or cur["topic"] != tc["topic"]:
            if cur is not None:
                clusters.append(cur)
            cur = {
                "topic": tc["topic"],
                "start_us": tc["start_us"],
                "end_us": tc["end_us"],
                "caption_idxs": [tc["caption_idx"]],
            }
        else:
            cur["end_us"] = tc["end_us"]
            cur["caption_idxs"].append(tc["caption_idx"])
    if cur is not None:
        clusters.append(cur)

    # Step 2b: merge tiny clusters into neighbors (avoid fragmentation)
    merged = []
    for cl in clusters:
        if merged and (cl["end_us"] - cl["start_us"]) < min_segment_us:
            prev = merged[-1]
            # 內容綁定到不同素材的 cluster 不合併 — 否則短字幕的逐段對位被吃掉
            # (2026-06-10 adopter fix：英文短字幕被 min_segment 合併成一坨 → 整片同一支)
            if (cl["topic"].startswith("__file__")
                    and prev["topic"].startswith("__file__")
                    and cl["topic"] != prev["topic"]):
                merged.append(cl)
                continue
            prev["end_us"] = cl["end_us"]
            prev["caption_idxs"].extend(cl["caption_idxs"])
        else:
            merged.append(cl)
    clusters = merged

    # Step 2c: fill INTER-cluster gaps (caption 間的空檔) — 否則 timeline 有洞，
    # 違反 docstring「cover [0,total] with no gaps」(2026-06-10 audit 實測抓到)
    # 小 gap (≤3s) 直接延長前一 cluster；大 gap 插 generic filler
    _GAP_EXTEND_US = 3_000_000
    gap_filled = []
    for cl in clusters:
        if gap_filled:
            prev_end = gap_filled[-1]["end_us"]
            gap = cl["start_us"] - prev_end
            if 0 < gap <= _GAP_EXTEND_US:
                gap_filled[-1]["end_us"] = cl["start_us"]
            elif gap > _GAP_EXTEND_US:
                gap_filled.append({
                    "topic": "generic", "start_us": prev_end,
                    "end_us": cl["start_us"], "caption_idxs": [],
                })
        gap_filled.append(cl)
    clusters = gap_filled

    # Step 3+4: assign brolls to clusters (greedy with split if cluster > source)
    assignments = []
    used_ids = set()
    t_cursor = 0

    # Prepend filler if first cluster doesn't start at 0
    if clusters and clusters[0]["start_us"] > 0:
        clusters = [{
            "topic": "generic",
            "start_us": 0,
            "end_us": clusters[0]["start_us"],
            "caption_idxs": [],
        }] + clusters
    # Append filler if last cluster doesn't reach total_duration
    if clusters and clusters[-1]["end_us"] < total_duration_us:
        clusters.append({
            "topic": "generic",
            "start_us": clusters[-1]["end_us"],
            "end_us": total_duration_us,
            "caption_idxs": [],
        })

    for cl in clusters:
        remaining_us = cl["end_us"] - cl["start_us"]
        seg_start = cl["start_us"]
        skip_topics_tried = set()
        # 該 cluster 的字幕文字 — 給 generic fallback 做 caption↔檔名對位
        cl_text = " ".join(text_list[i] for i in cl.get("caption_idxs", [])
                           if 0 <= i < len(text_list))

        while remaining_us > 0:
            topic_to_use = cl["topic"] if cl["topic"] not in skip_topics_tried else "generic"
            broll_id, broll, score = _best_broll_for_topic(
                topic_to_use, brolls, km, used_ids=used_ids, allow_reuse=allow_reuse,
                caption_hint=cl_text,
            )
            if broll is None:
                # Fall back to generic
                broll_id, broll, score = _best_broll_for_topic(
                    "generic", brolls, km, used_ids=used_ids, allow_reuse=allow_reuse,
                    caption_hint=cl_text,
                )
            if broll is None:
                # No broll at all — can't continue
                break

            source_dur = broll.get("source_duration_us", remaining_us)
            slot_dur = min(remaining_us, source_dur)

            assignments.append(BrollAssignment(
                broll_id=broll_id,
                start_us=seg_start,
                duration_us=slot_dur,
                source_trim_us=(0, slot_dur),
                captions_covered=list(cl["caption_idxs"]),
                topic_label=km.get(cl["topic"], {}).get(
                    "topic_label",
                    "content-match" if cl["topic"].startswith("__file__") else cl["topic"]),
                avg_score=score,
                is_filler=(cl["topic"] == "generic"),
            ))
            used_ids.add(broll_id)
            seg_start += slot_dur
            remaining_us -= slot_dur

            # If we used a topic broll but still need more, fall back to generic
            if remaining_us > 0:
                skip_topics_tried.add(cl["topic"])

    # Post-pass: consolidate consecutive assignments using the SAME broll_id
    # (avoids fragmentation when greedy clustering put adjacent same-broll slots)
    if consolidate_consecutive and len(assignments) > 1:
        consolidated = [assignments[0]]
        _src_by_id = {b.get("id"): b.get("source_duration_us") for b in brolls}
        for a in assignments[1:]:
            prev = consolidated[-1]
            # merge 後的 trim 不能超出 broll 真實 source 長度 — 否則 CapCut 卡格/黑畫面
            # (2026-06-10 audit 實測: 5s source 被 merge 成 12s trim)
            _src_dur = _src_by_id.get(prev.broll_id)
            _fits = (_src_dur is None or
                     prev.source_trim_us[0] + prev.duration_us + a.duration_us <= _src_dur)
            if (prev.broll_id == a.broll_id
                    and prev.start_us + prev.duration_us == a.start_us
                    and _fits):
                # Merge into prev
                prev.duration_us += a.duration_us
                prev.source_trim_us = (prev.source_trim_us[0],
                                        prev.source_trim_us[0] + prev.duration_us)
                prev.captions_covered.extend(a.captions_covered)
                # Keep prev.topic_label (or update to non-generic if either is topic)
                if prev.is_filler and not a.is_filler:
                    prev.topic_label = a.topic_label
                    prev.is_filler = False
                    prev.avg_score = max(prev.avg_score, a.avg_score)
            else:
                consolidated.append(a)
        assignments = consolidated

    # 大聲警告：幾乎全是低分 filler = b-roll 不會跟旁白對齊（adopter 最常見抱怨）
    if assignments:
        weak = sum(1 for a in assignments if a.avg_score < 0.3)
        if weak / len(assignments) >= 0.6 and len(captions) >= 3:
            import warnings as _w
            _w.warn(
                "auto_sequence_brolls: 多數片段沒對上內容 → 成品畫面不會跟旁白/字幕對齊。"
                "修法：(1) 把 b-roll 用內容命名（coffee.mp4 / studio.mp4），或 "
                "(2) 傳 keyword_map=你的主題表。見 TROUBLESHOOTING。",
                RuntimeWarning, stacklevel=2)

    return assignments


def print_sequence_plan(assignments: list, total_duration_us: int = None) -> None:
    """Pretty-print the auto-sequencer output."""
    print("=" * 88)
    print("🎬 Auto-Sequencer Plan (M75)")
    print("=" * 88)
    print(f"{'idx':<4} {'start':>7} {'end':>7} {'dur':>6} {'broll':<40} {'topic':<25} {'#caps':>5}")
    print("-" * 88)
    total = 0
    for i, a in enumerate(assignments):
        ss = a.start_us / 1e6
        se = (a.start_us + a.duration_us) / 1e6
        dur = a.duration_us / 1e6
        flag = "💭" if a.is_filler else "🎯"
        print(f"{i:<4} {ss:>7.2f} {se:>7.2f} {dur:>6.2f} "
              f"{flag} {a.broll_id[:36]:<38} {a.topic_label[:23]:<25} {len(a.captions_covered):>5}")
        total += a.duration_us
    print("-" * 88)
    print(f"Total assigned: {total/1e6:.2f}s", end="")
    if total_duration_us:
        delta = (total - total_duration_us) / 1e6
        print(f"  (target {total_duration_us/1e6:.2f}s, delta {delta:+.2f}s)")
    else:
        print()
