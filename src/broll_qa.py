"""Creator-neutral b-roll ratio and narration-alignment audit helpers.

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

def _broll_basename(path_or_name: str) -> str:
    return str(path_or_name).replace("\\", "/").rsplit("/", 1)[-1]


def _source_key(path_or_name: str) -> str:
    """Normalize a source key by removing a generated ``seg_NN_`` prefix and extension."""
    b = _broll_basename(path_or_name).lower().rsplit(".", 1)[0]
    if b.startswith("seg_"):
        parts = b.split("_", 2)  # ['seg','00','laptop-typing-hand-6']
        if len(parts) == 3 and parts[1].isdigit():
            b = parts[2]
    return b


def classify_broll_role(path_or_name: str, is_main=None) -> str:
    """Return ``main`` or ``generic``; an explicit ``is_main`` value wins.

    Unknown paths fail closed as generic instead of inflating main-footage coverage.
    """
    if is_main is not None:
        if not isinstance(is_main, bool):
            raise TypeError("is_main must be bool or None")
        return "main" if is_main else "generic"
    p = str(path_or_name).lower()
    if any(h in p for h in _GENERIC_PATH_HINTS):
        return "generic"
    if any(h in p for h in _MAIN_PATH_HINTS):
        return "main"
    return "generic"


def audit_broll_main_ratio(segments: list, strict: bool = False, max_uses: int = 2) -> dict:
    """Audit duration ratio and generic-source reuse on the edit timeline.

    ``max_uses`` defaults to two.  A source at the cap warns; a source above
    the cap fails.  ``strict=True`` raises on any failed invariant.
    """
    if not isinstance(max_uses, int) or isinstance(max_uses, bool) or max_uses < 1:
        raise ValueError("max_uses must be a positive integer")
    main_s = generic_s = 0.0
    seen, rows = {}, []
    for index, s in enumerate(segments):
        if not isinstance(s, dict):
            raise TypeError(f"segment {index} must be a dict")
        name = s.get("name") or s.get("path") or s.get("source") or "?"
        raw_duration = s.get("duration_s", s.get("duration", 0))
        if isinstance(raw_duration, bool):
            raise ValueError(f"segment {index} duration must be finite and > 0")
        try:
            dur = float(raw_duration)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"segment {index} duration must be finite and > 0") from exc
        if not math.isfinite(dur) or dur <= 0:
            raise ValueError(f"segment {index} duration must be finite and > 0")
        role = classify_broll_role(name, s.get("is_main"))
        if role == "main":
            main_s += dur
        else:
            generic_s += dur
            key = _source_key(name)
            seen[key] = seen.get(key, 0) + 1
        rows.append((_broll_basename(name), round(dur, 1), role))
    total = main_s + generic_s
    repeats = {k: v for k, v in seen.items() if v > max_uses}
    at_cap = {k: v for k, v in seen.items() if v == max_uses and max_uses > 1}
    ratio_ok = generic_s < main_s
    no_repeat = not repeats
    # M102：runtime 輸出一律 ASCII marker（cp950 console 印 emoji 會炸）
    verdict = []
    verdict.append("[OK] generic < main" if ratio_ok
                   else f"[FAIL] generic {generic_s:.1f}s >= main {main_s:.1f}s — 違反 M86 占比")
    verdict.append(f"[OK] 無 clip 超過 {max_uses} 次" if no_repeat
                   else f"[FAIL] 重複超限(>{max_uses})：{repeats}")
    if at_cap:
        verdict.append(f"[WARN] 已達上限 {max_uses} 次（理想 <=1）：{at_cap}")
    result = {
        "main_s": round(main_s, 1), "generic_s": round(generic_s, 1),
        "total_s": round(total, 1),
        "generic_pct": round(100 * generic_s / total, 1) if total else 0.0,
        "main_pct": round(100 * main_s / total, 1) if total else 0.0,
        "ratio_ok": ratio_ok, "no_repeat": no_repeat,
        "passed": ratio_ok and no_repeat,
        "repeats": repeats, "verdict": " | ".join(verdict), "rows": rows,
    }
    if strict and not result["passed"]:
        raise AssertionError(f"M86 violated → {result['verdict']}")
    return result


def print_broll_ratio_report(audit: dict) -> None:
    print("=" * 80)
    print("🎯 M86 b-roll 占比 audit (通用 < 主素材 + 無重複畫面)")
    print("=" * 80)
    for name, dur, role in audit["rows"]:
        tag = "🎯主 " if role == "main" else "🔁通用"
        print(f"  {tag}  {dur:5.1f}s  {name[:52]}")
    print("-" * 80)
    print(f"  主素材 main    : {audit['main_s']:6.1f}s ({audit['main_pct']}%)")
    print(f"  通用 b-roll generic: {audit['generic_s']:6.1f}s ({audit['generic_pct']}%)")
    print(f"  {audit['verdict']}")
    print("=" * 80)


# ════════════════════════════════════════════════════════════════════════════
# M87: narration-to-b-roll checks use explicit semantic labels, not filenames.
# These are neutral examples only.  The public default is an empty map so an
# omitted creator map warns about unchecked labels instead of vacuously passing.
EXAMPLE_BROLL_CONTENT_KEYWORDS = {
    "topic_product": ["產品", "網站", "首頁", "選單", "服務", "作品", "demo", "介面"],
    "topic_feature": ["功能", "系統", "設定", "流程", "選項", "面板"],
    "topic_code": ["code", "debug", "架構", "ui", "工具", "指令", "prompt"],
    "topic_food": ["美食", "好吃", "招牌", "風味", "湯頭", "配料"],
    "generic": [],
}

def narration_broll_sync_report(captions: list, segments: list,
                                keyword_map: dict = None, strict: bool = False) -> dict:
    """Check explicit b-roll content labels against captions in each time window.

    Supply ``keyword_map`` from creator-owned project semantics.  An omitted
    map marks non-generic labels unchecked and fails closed.
    """
    # `or` → `if is not None`：空 {} 不會被作者預設表蓋掉（2026-06-10 adopter fix，
    # 對齊 caption_broll_matcher；採用者傳 {} = 沒給 content map → 下面警告而非假性 pass）
    km = keyword_map if keyword_map is not None else {}
    rows, n_mis = [], 0
    _unknown = set()
    for (vs, ve, content) in segments:
        caps = [t for (st, t) in captions if vs <= st < ve]
        joined = " ".join(caps).lower()
        kws = km.get(content, None)
        if kws is None:
            if content != "generic":
                _unknown.add(content)
            matched = content == "generic"
            reason = ("generic（反思/填充段，配任何旁白）" if matched else
                      f"未知 content '{content}' — 未檢查，不能視為通過")
        elif not kws:  # generic
            matched, reason = True, "generic（反思/填充段，配任何旁白）"
        else:
            hit = [k for k in kws if k.lower() in joined]
            matched = bool(hit)
            reason = (f"命中 {hit[:4]}" if hit
                      else f"❌ '{content}' 關鍵詞全沒出現在字幕 → 畫面可能跟旁白錯位")
        if not matched:
            n_mis += 1
        rows.append({"window": (vs, ve), "content": content,
                     "caps": caps, "matched": matched, "reason": reason})
    # 多數 content label 不在 map 裡 → 這份 audit 其實沒在檢查（假性 pass）→ 大聲警告
    if _unknown:
        import warnings as _w
        _w.warn(
            f"narration_broll_sync_report: content label {sorted(_unknown)} 不在 keyword_map 裡 → "
            "這些段沒被實際檢查，因此 passed=False。請傳 keyword_map={你的 content→關鍵詞} "
            "或用 'generic' 標填充段。",
            RuntimeWarning, stacklevel=2)
    result = {"rows": rows, "n_mismatch": n_mis,
              "passed": n_mis == 0 and not _unknown,
              "unchecked": sorted(_unknown)}
    if strict and not result["passed"]:
        raise AssertionError(
            f"M87 narration-broll sync: {n_mis} 段錯位，{len(_unknown)} 個未檢查 label"
        )
    return result


def print_narration_sync_report(rep: dict) -> None:
    print("=" * 84)
    print("🔗 M87 旁白↔b-roll 內容對位 audit")
    print("=" * 84)
    for r in rep["rows"]:
        vs, ve = r["window"]
        flag = "✅" if r["matched"] else "❌"
        head = (r["caps"][0][:24] + "…") if r["caps"] else "(無字幕)"
        print(f"  {flag} [{vs:5.0f}-{ve:<5.0f}] {r['content']:<9} | {r['reason'][:40]}  〈{head}〉")
    print("-" * 84)
    v = "✅ 全段對位" if rep["passed"] else f"❌ {rep['n_mismatch']} 段旁白↔畫面錯位"
    print(f"  {v}")
    print("=" * 84)
