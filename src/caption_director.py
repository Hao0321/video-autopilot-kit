# -*- coding: utf-8 -*-
"""跨片型字幕美術導演。

目的不是把每句話都做成特效，而是把「哪一句值得被設計」變成可重現的決策：

* 長片：逐句白字黑底，永遠 clean-only；
* Shorts/Reels：白字為底，語意詞可用至多兩種強調色；
* 巨字、票券字卡、2.5D 浮空字只用在 hook／轉折／數字／payoff；
* 所有規則 deterministic，視覺導演、renderer 與 QA 共用同一份 plan。

參考視覺只抽象成「巨字層級、票券／飄帶、cobalt+lime、Neo-Bauhaus 模組、
前後景漂浮」等設計語法，不複製第三方 Logo、文案或特定版面。
"""
from __future__ import annotations

import math
import re


SHORT_MODES = frozenset({"clean", "impact", "ribbon", "float_left", "float_right"})
KINETIC_MODES = frozenset({"impact", "ribbon", "float_left", "float_right"})
RENDER_KINDS = frozenset({
    "main", "hook", "sub", "addr", "impact", "ribbon", "float_left", "float_right",
})

MODE_CHAR_LIMIT = {"impact": 12, "ribbon": 10, "float_left": 8, "float_right": 8}

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?(?:%|倍|萬|千|元|秒|分|顆|款|個|次)?", re.I)
_STEP = re.compile(r"第\s*[一二三四五六七八九十\d]+\s*[步點]|首先|接著|再來|最後|重點|結論")
_SURPRISE = re.compile(r"但是|結果|竟然|居然|原來|沒想到|反而|直接")
_OUTCOME = re.compile(r"成功|完成|提升|省下|加快|贏|有效|正版|通過|解決")
_RISK = re.compile(r"失敗|錯誤|問題|風險|不要|踩雷|危險|盜版|卡住")
_TECH = re.compile(r"AI|Claude|GPT|Token|模型|自動|工具|提示詞|工作流", re.I)

_DOMAIN_SECONDARY = {
    "ai": "sky", "teaching": "sky", "business": "sky", "product": "sky",
    "food": "coral", "cafe": "coral", "dessert": "coral",
    "travel": "sky", "nature": "mint", "architecture": "sky",
    "toy": "pink", "unboxing": "pink", "fashion": "pink",
    "game": "mint", "gaming": "mint", "fitness": "mint",
    "documentary": "orange", "interview": "orange", "automotive": "orange",
    "music": "pink", "diy": "orange",
}

GLOW_PACK_MANIFEST = "community/hao-motion-kit/assets/glow_text/imagegen/manifest.json"


def _glow_asset_hint(text: str) -> str | None:
    """Return only human-reviewed imagegen assets; never fall back to low-fidelity text."""
    value = str(text or "")
    if re.search(r"\bVS\b|對決|對打", value, re.I):
        return "imagegen_vs_electric_clash"
    return None


def _nchars(text: str) -> int:
    return sum(1 for ch in str(text) if not ch.isspace())


def _energy_at(t: float, curve: list[dict]) -> float:
    for act in curve or []:
        if float(act["start"]) <= t < float(act["end"]):
            return float(act["energy"])
    return float((curve or [{"energy": .5}])[-1]["energy"])


def _first_match(pattern: re.Pattern, text: str) -> str:
    match = pattern.search(text)
    return match.group(0) if match else ""


def _highlight_terms(text: str, domain: str) -> list[dict]:
    """選最多兩個語意詞；顏色總集合固定為 gold + 題材副色。"""
    secondary = _DOMAIN_SECONDARY.get(domain, "sky")
    candidates: list[tuple[int, str, str, str]] = []
    for priority, pattern, color, reason in (
        (5, _NUMBER, "gold", "number_or_metric"),
        (4, _OUTCOME, secondary, "result"),
        (4, _RISK, secondary, "risk_or_conflict"),
        (3, _TECH, secondary, "topic_term"),
        (2, _SURPRISE, secondary, "turn"),
    ):
        term = _first_match(pattern, text)
        if term:
            candidates.append((priority, term, color, reason))
    chosen, spans = [], []
    for priority, term, color, reason in sorted(candidates, reverse=True):
        start = text.find(term)
        end = start + len(term)
        # 整句上色不是「關鍵詞強調」；超過六成也會破壞 white-first。
        if start < 0 or _nchars(term) >= max(4, math.ceil(_nchars(text) * .60)):
            continue
        if any(not (end <= a or start >= b) for a, b in spans):
            continue
        spans.append((start, end))
        chosen.append({"text": term, "color": color, "reason": reason, "priority": priority})
        if len(chosen) == 2:
            break
    return sorted(chosen, key=lambda item: text.find(item["text"]))


def segment_text(text: str, highlights: list[dict] | None = None) -> list[tuple[str, str]]:
    """把文字轉成 renderer 可吃的 white-first segments。"""
    text = str(text)
    marks = []
    occupied = []
    for item in highlights or []:
        term = str(item.get("text", ""))
        start = text.find(term)
        end = start + len(term)
        if not term or start < 0 or any(not (end <= a or start >= b) for a, b in occupied):
            continue
        occupied.append((start, end))
        marks.append((start, end, str(item.get("color", "gold"))))
    if not marks:
        return [(text, "white")]
    out, cursor = [], 0
    for start, end, color in sorted(marks):
        if start > cursor:
            out.append((text[cursor:start], "white"))
        out.append((text[start:end], color))
        cursor = end
    if cursor < len(text):
        out.append((text[cursor:], "white"))
    return [(part, color) for part, color in out if part]


def _mode_for(row: dict, index: int, energy: float) -> tuple[str, int, str]:
    text = row["text"]
    n = _nchars(text)
    source_kind = str(row.get("source_kind", ""))
    if source_kind == "addr":
        return "clean", 99, "persistent_address"
    if source_kind == "hook" and n <= MODE_CHAR_LIMIT["impact"]:
        return "impact", 6, "short_hook"
    if _STEP.search(text) and n <= MODE_CHAR_LIMIT["ribbon"]:
        return "ribbon", 4, "step_or_label"
    if (_SURPRISE.search(text) or _RISK.search(text)) and n <= 8 and energy >= .64:
        side = "float_left" if index % 2 == 0 else "float_right"
        return side, 5, "turn_callout"
    if (_NUMBER.search(text) or _OUTCOME.search(text)) and n <= 10 and energy >= .82:
        return "impact", 5, "metric_or_payoff"
    return "clean", 1, "supporting_caption"


def _budgets(duration: float, content_count: int) -> dict:
    return {
        "kinetic_total": min(4, max(1, math.ceil(content_count * .40))),
        "impact": min(2, max(1, math.ceil(duration / 18.0))),
        "float": min(2, max(1, math.ceil(duration / 16.0))),
        "ribbon": min(2, max(1, math.ceil(duration / 20.0))),
        "colored_events": min(3, max(1, math.ceil(content_count * .35))),
    }


def _longform_emphasis_overlays(rows: list[dict], duration: float, domain: str) -> tuple[list[dict], int]:
    """長片的 MrBeast 類文字效果是獨立 overlay，不改動逐句字幕。"""
    budget = min(8, max(2, math.ceil(float(duration) / 60.0 * 2)))
    secondary = _DOMAIN_SECONDARY.get(domain, "sky")
    candidates = []
    for row in rows:
        if str(row.get("source_kind", "")) == "addr":
            continue
        text = str(row["text"])
        number = _first_match(_NUMBER, text)
        keyword = (_first_match(_OUTCOME, text) or _first_match(_RISK, text) or
                   _first_match(_SURPRISE, text) or _first_match(_TECH, text))
        if number:
            label, mode, color, priority = number, "number", "gold", 6
        elif keyword:
            label, mode, color, priority = keyword, "keyword", secondary, 4
        else:
            continue
        if _nchars(label) > 10:
            continue
        start = float(row["start"])
        asset_hint = _glow_asset_hint(text)
        candidates.append({
            "start": round(start, 3), "end": round(min(float(row["end"]), start + 1.25), 3),
            "text": label, "mode": mode, "color": color,
            "reason": "proof_metric" if number else "semantic_emphasis", "priority": priority,
            "source_text": text[:42],
            "material": "imagegen_premium" if asset_hint else "imagegen_required",
            "asset_hint": asset_hint,
            "asset_manifest": GLOW_PACK_MANIFEST, "render_fallback": "clean_hold",
        })
    selected = []
    for candidate in sorted(candidates, key=lambda item: (-item["priority"], item["start"])):
        if any(abs(candidate["start"] - prior["start"]) < 7.5 for prior in selected):
            continue
        selected.append(candidate)
        if len(selected) == budget:
            break
    return sorted(selected, key=lambda item: item["start"]), budget


def plan_caption_system(rows: list[dict], duration: float, format_kind: str,
                        domain: str, energy_curve: list[dict]) -> dict:
    rows = sorted((dict(row) for row in rows or []), key=lambda row: float(row["start"]))
    if format_kind == "longform":
        overlays, overlay_budget = _longform_emphasis_overlays(rows, duration, domain)
        events = [{
            "start": float(row["start"]), "end": float(row["end"]), "text": row["text"],
            "source_kind": row.get("source_kind", "main"), "mode": "clean", "highlights": [],
            "reason": "longform_clean_lock", "priority": 0,
        } for row in rows]
        return {
            "version": 1, "profile": "longform_clean_locked", "format": "longform",
            "base_color": "white", "max_nonwhite_colors": 0,
            "motion": "none_on_subtitle_layer", "events": events,
            "emphasis_overlay_profile": "longform_selective_impact",
            "emphasis_overlay_budget": overlay_budget,
            "emphasis_overlays": overlays,
            "glow_asset_manifest": GLOW_PACK_MANIFEST,
            "glow_generator": "Codex imagegen skill; human review required",
            "rules": [
                "逐句字幕維持白字＋黑色半透明底框",
                "巨型數字／關鍵字只走獨立 overlay，不污染逐句字幕",
                "overlay 只在 hook／轉折／proof／payoff 使用，至少間隔 7.5 秒",
            ],
        }

    content_count = sum(str(row.get("source_kind", "")) != "addr" for row in rows)
    budgets = _budgets(duration, content_count)
    used = {"kinetic_total": 0, "impact": 0, "float": 0, "ribbon": 0, "colored_events": 0}
    events = []
    for index, row in enumerate(rows):
        energy = _energy_at(float(row["start"]), energy_curve)
        mode, priority, reason = _mode_for(row, index, energy)
        bucket = "float" if mode.startswith("float_") else mode
        if mode in KINETIC_MODES:
            if used["kinetic_total"] >= budgets["kinetic_total"] or used[bucket] >= budgets[bucket]:
                mode, priority, reason = "clean", 1, "kinetic_budget_exhausted"
            else:
                used["kinetic_total"] += 1
                used[bucket] += 1
        highlights = []
        if str(row.get("source_kind", "")) != "addr" and used["colored_events"] < budgets["colored_events"]:
            highlights = _highlight_terms(str(row["text"]), domain)
            if highlights:
                used["colored_events"] += 1
        asset_hint = (_glow_asset_hint(str(row["text"]))
                      if mode in {"impact", "float_left", "float_right"} else None)
        events.append({
            "start": round(float(row["start"]), 3), "end": round(float(row["end"]), 3),
            "text": str(row["text"]), "source_kind": row.get("source_kind", "main"),
            "mode": mode, "highlights": highlights, "reason": reason,
            "priority": priority, "energy": round(energy, 2),
            "material": (("imagegen_premium" if asset_hint else "imagegen_required")
                         if mode in {"impact", "float_left", "float_right"}
                         else "flat_editorial"),
            "asset_hint": asset_hint,
        })
    plan = {
        "version": 1, "profile": "shorts_semantic_kinetic", "format": "short",
        "base_color": "white", "accent_palette": ["gold", _DOMAIN_SECONDARY.get(domain, "sky")],
        "max_nonwhite_colors": 2, "budgets": budgets, "events": events,
        "glow_asset_manifest": GLOW_PACK_MANIFEST,
        "glow_generator": "Codex imagegen skill; human review required",
        "rules": [
            "白字為底，只有語意詞上色", "巨字只給 hook／數字／payoff",
            "浮空字只給短反差詞且左右交替", "票券字卡只給步驟／標籤",
            "動態字卡不得遮產品、操作、proof 或平台 UI",
        ],
    }
    errors = validate_caption_system(plan, duration)
    if errors:
        raise AssertionError("caption plan invalid: " + "; ".join(errors))
    return plan


def validate_caption_system(plan: dict, duration: float) -> list[str]:
    if not plan:
        return ["missing caption system"]
    bad, events = [], plan.get("events") or []
    if plan.get("format") == "longform":
        if plan.get("profile") != "longform_clean_locked":
            bad.append("longform caption profile is not locked")
        if any(event.get("mode") != "clean" for event in events):
            bad.append("longform contains kinetic caption")
        if any(event.get("highlights") for event in events):
            bad.append("longform contains colored keyword")
        overlays = plan.get("emphasis_overlays") or []
        if len(overlays) > int(plan.get("emphasis_overlay_budget", 0)):
            bad.append("longform emphasis overlay budget exceeded")
        for i, overlay in enumerate(overlays):
            if overlay.get("mode") not in {"number", "keyword"}:
                bad.append("unknown longform overlay mode")
            if _nchars(str(overlay.get("text", ""))) > 10:
                bad.append("longform overlay text too long")
            if float(overlay.get("start", 0)) < 0 or float(overlay.get("end", 0)) > float(duration) + .05:
                bad.append("longform overlay outside duration")
            if float(overlay.get("end", 0)) <= float(overlay.get("start", 0)):
                bad.append("longform overlay has non-positive duration")
            if i and float(overlay["start"]) - float(overlays[i - 1]["start"]) < 7.49:
                bad.append("longform overlays are too dense")
        return bad
    kinetic = 0
    colors = set()
    for event in events:
        mode = event.get("mode")
        text = str(event.get("text", ""))
        if mode not in SHORT_MODES:
            bad.append("unknown caption mode %r" % mode)
            continue
        if float(event.get("start", 0)) < 0 or float(event.get("end", 0)) > float(duration) + .05:
            bad.append("caption outside duration")
        if mode in KINETIC_MODES:
            kinetic += 1
            if _nchars(text) > MODE_CHAR_LIMIT[mode]:
                bad.append("%s caption too long" % mode)
        for highlight in event.get("highlights") or []:
            colors.add(highlight.get("color"))
            if str(highlight.get("text", "")) not in text:
                bad.append("highlight not found in caption")
    budgets = plan.get("budgets") or {}
    if kinetic > int(budgets.get("kinetic_total", kinetic)):
        bad.append("kinetic caption budget exceeded")
    if len(colors) > int(plan.get("max_nonwhite_colors", 2)):
        bad.append("caption accent palette exceeded")
    return bad


def _find_event(events: list[dict], start: float, text: str) -> dict | None:
    exact = [event for event in events if event.get("text") == text and
             abs(float(event.get("start", 0)) - float(start)) <= .03]
    return exact[0] if exact else None


def apply_caption_system(caps: list, plan: dict) -> list:
    """把 caption plan 套到已展開的 Shorts caps；保留舊 tuple schema。"""
    if plan.get("format") != "short":
        return list(caps)
    events = plan.get("events") or []
    staged = []
    for start, end, pieces, source_kind in caps:
        text = "".join(str(part) for part, _color in pieces)
        event = _find_event(events, start, text)
        if source_kind == "addr" or not event:
            staged.append([start, end, [(text, "white")], source_kind, 99])
            continue
        mode = event.get("mode", "clean")
        if mode == "clean":
            # Authoring hints such as ribbon/float may be downgraded by the
            # kinetic budget.  The legacy renderer has no `clean` kind, so a
            # downgraded hint must become an ordinary main caption.
            kind = source_kind if source_kind in {"main", "hook", "sub"} else "main"
        else:
            kind = mode
        styled = segment_text(text, event.get("highlights"))
        staged.append([start, end, styled, kind, int(event.get("priority", 0))])

    # renderer 與舊 S-I gate 使用 token 比例；若切詞後超過 35%，從低優先級事件退回白字。
    def ratio() -> float:
        tokens = [token for row in staged for token in row[2]]
        return sum(color not in ("white", "w") for _text, color in tokens) / max(1, len(tokens))

    for row in sorted(staged, key=lambda item: item[4]):
        if ratio() <= .35:
            break
        if any(color not in ("white", "w") for _text, color in row[2]):
            row[2] = [("".join(text for text, _color in row[2]), "white")]
    result = [(start, end, pieces, kind) for start, end, pieces, kind, _priority in staged]
    errors = audit_render_caps(result)
    if errors:
        raise AssertionError("render captions invalid: " + "; ".join(errors))
    return result


def audit_render_caps(caps: list) -> list[str]:
    bad, colors, kinetic = [], set(), 0
    for _start, _end, pieces, kind in caps:
        text = "".join(str(part) for part, _color in pieces)
        if kind not in RENDER_KINDS:
            bad.append("unknown render kind %r" % kind)
        if kind in MODE_CHAR_LIMIT and _nchars(text) > MODE_CHAR_LIMIT[kind]:
            bad.append("%s exceeds %d chars" % (kind, MODE_CHAR_LIMIT[kind]))
        if kind in KINETIC_MODES:
            kinetic += 1
        colors.update(color for _text, color in pieces if color not in ("white", "w"))
    if len(colors) > 2:
        bad.append("more than two non-white caption colors")
    if kinetic > max(2, math.ceil(sum(kind != "addr" for *_rest, kind in caps) * .40)):
        bad.append("too many kinetic captions")
    return bad


def _self_test() -> None:
    curve = [{"start": 0, "end": 3, "energy": .96},
             {"start": 3, "end": 9, "energy": .72},
             {"start": 9, "end": 15, "energy": .92}]
    rows = [
        {"start": .2, "end": 1.6, "text": "AI 快了 3 倍", "source_kind": "hook"},
        {"start": 3.2, "end": 5.0, "text": "第 1 步先看結果", "source_kind": "sub"},
        {"start": 9.2, "end": 10.5, "text": "結果成功了", "source_kind": "sub"},
        {"start": .2, "end": 14.8, "text": "地址", "source_kind": "addr"},
    ]
    short = plan_caption_system(rows, 15, "short", "ai", curve)
    assert short["profile"] == "shorts_semantic_kinetic" and not validate_caption_system(short, 15)
    assert any(event["mode"] == "impact" for event in short["events"])
    assert any(event["mode"] == "ribbon" for event in short["events"])
    assert len({h["color"] for e in short["events"] for h in e["highlights"]}) <= 2
    long = plan_caption_system(rows, 180, "longform", "ai", curve)
    assert all(e["mode"] == "clean" and not e["highlights"] for e in long["events"])
    assert long["emphasis_overlays"] and long["emphasis_overlays"][0]["mode"] == "number"
    caps = [(r["start"], r["end"], [(r["text"], "white")], r["source_kind"]) for r in rows]
    rendered = apply_caption_system(caps, short)
    assert any(kind == "impact" for _s, _e, _p, kind in rendered)
    assert not audit_render_caps(rendered)
    downgraded = apply_caption_system(
        [(0, 1.5, [("普通標籤", "white")], "ribbon")],
        {"format": "short", "events": [{"start": 0, "text": "普通標籤", "mode": "clean"}]},
    )
    assert downgraded[0][3] == "main" and not audit_render_caps(downgraded)
    print("caption_director self-test OK")


if __name__ == "__main__":
    _self_test()
