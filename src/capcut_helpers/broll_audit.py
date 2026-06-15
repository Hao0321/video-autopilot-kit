"""
broll_audit.py — M86 (通用占比) + M87 (旁白↔畫面對位) b-roll audit helpers.

2026-06-01 audit「拆」: 從 caption_broll_matcher.py 抽出（該檔逼近 1000 行）。
純搬移、零行為改變；capcut_helpers/__init__ re-export 這些名字，外部 import 不受影響。
自我包含（_broll_basename / _source_key / *_PATH_HINTS / HAO_BROLL_CONTENT_KEYWORDS 都在本檔）。
"""

# ════════════════════════════════════════════════════════════════════════════
# M86 (2026-05-30): 通用 b-roll 占比 MUST < 官網主素材占比 — ratio cap + enforce
# ----------------------------------------------------------------------------
# 用戶原話：「這些通用素材的占比不能超越我官網的主素材」+「太多重複畫面了」
# 同 M60v2 / M79 / M81 / M85「規則→自動機制」家族：規則寫進 SKILL ≠ enforced，
# 必須機械式 assert（by timeline duration，不是 segment 數），不靠記憶/brief 提醒。
# 兩個 invariant 一起驗：
#   (1) sum(generic_dur) < sum(main_dur)         — 占比上限
#   (2) 同一 source clip 出現次數 ≤ 1（generic）  — 重複畫面 flag（laptop ×3 case）
# ════════════════════════════════════════════════════════════════════════════

# 路徑啟發式：transitions/ broll/ stock = 通用素材；_cleaned/raw 螢幕錄影/官網 demo = 主素材
_GENERIC_PATH_HINTS = ("broll", "transitions", "/stock", "b-roll")
_MAIN_PATH_HINTS = ("_cleaned", "screen", "studio", "obs", "dashboard",
                    "gamehall", "game-hall", "player", "website", "官網", "demo",
                    # 通用主素材 hint（2026-06-10 adopter fix：英文主素材不再全被當 generic）
                    "main", "hero", "product", "interview", "tutorial", "recording", "demo")


def _broll_basename(path_or_name: str) -> str:
    return str(path_or_name).replace("\\", "/").rsplit("/", 1)[-1]


def _source_key(path_or_name: str) -> str:
    """正規化成「來源 clip key」用來抓重複畫面 —
    剝掉 build 加的 `seg_NN_` 前綴 + 副檔名，讓 seg_00_laptop / seg_05_laptop /
    seg_08_laptop 都歸成同一 key `laptop-typing-hand-6`（=laptop ×3 真重複會被抓到）。"""
    b = _broll_basename(path_or_name).lower().rsplit(".", 1)[0]
    if b.startswith("seg_"):
        parts = b.split("_", 2)  # ['seg','00','laptop-typing-hand-6']
        if len(parts) == 3 and parts[1].isdigit():
            b = parts[2]
    return b


def classify_broll_role(path_or_name: str, is_main=None) -> str:
    """回傳 'main' (官網主素材) 或 'generic' (通用 b-roll)。顯式 is_main 優先。
    未知來源 → 保守歸 'generic'（不灌水 main 占比）。"""
    if is_main is not None:
        return "main" if is_main else "generic"
    p = str(path_or_name).lower()
    if any(h in p for h in _GENERIC_PATH_HINTS):
        return "generic"
    if any(h in p for h in _MAIN_PATH_HINTS):
        return "main"
    return "generic"


def audit_broll_main_ratio(segments: list, strict: bool = False) -> dict:
    """M86 — 官網影片 b-roll 占比 + 重複 audit（by timeline duration）。

    segments: list of dict，每個含：
        name/path/source : str  — 用來分類 + 抓 basename 判重複
        duration_s/duration : float — 該 segment 在 timeline 的秒數
        is_main : bool (optional) — 顯式標主素材，覆蓋路徑啟發式
    回傳 {main_s, generic_s, total_s, generic_pct, main_pct, ratio_ok,
          no_repeat, passed, repeats, verdict, rows}。
      ratio_ok = generic_s < main_s（嚴格小於）
      repeats  = {basename: count} 對 count>1 的 generic source（重複畫面 = ❌）
    strict=True 且未過 → raise AssertionError（build-time gate）。
    """
    main_s = generic_s = 0.0
    seen, rows = {}, []
    for s in segments:
        name = s.get("name") or s.get("path") or s.get("source") or "?"
        dur = float(s.get("duration_s", s.get("duration", 0)) or 0)
        role = classify_broll_role(name, s.get("is_main"))
        if role == "main":
            main_s += dur
        else:
            generic_s += dur
            key = _source_key(name)
            seen[key] = seen.get(key, 0) + 1
        rows.append((_broll_basename(name), round(dur, 1), role))
    total = main_s + generic_s
    repeats = {k: v for k, v in seen.items() if v > 1}
    ratio_ok = generic_s < main_s
    no_repeat = not repeats
    verdict = []
    verdict.append("✅ generic < main" if ratio_ok
                   else f"❌ generic {generic_s:.1f}s ≥ main {main_s:.1f}s — 違反 M86 占比")
    verdict.append("✅ 無重複 clip" if no_repeat else f"❌ 重複畫面：{repeats}")
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
    print("🎯 M86 b-roll 占比 audit (通用 < 官網主素材 + 無重複畫面)")
    print("=" * 80)
    for name, dur, role in audit["rows"]:
        tag = "🌐主 " if role == "main" else "🔁通用"
        print(f"  {tag}  {dur:5.1f}s  {name[:52]}")
    print("-" * 80)
    print(f"  官網主素材 main    : {audit['main_s']:6.1f}s ({audit['main_pct']}%)")
    print(f"  通用 b-roll generic: {audit['generic_s']:6.1f}s ({audit['generic_pct']}%)")
    print(f"  {audit['verdict']}")
    print("=" * 80)


# ════════════════════════════════════════════════════════════════════════════
# M87 (2026-05-30): 旁白↔b-roll 內容對位 audit — content-map driven，不被檔名騙
# ----------------------------------------------------------------------------
# 用戶看 t=120「字幕跟聲音還有畫面都沒對上」。根因：M86 占比 swap 把寫程式段的
# coding 畫面換成 studio 遊戲牆，旁白卻在講「把 Claude 當團隊用」→ 語意錯位；
# 且 in-place swap 留舊檔名騙過 filename-keyed 的 AP15。
# 此 helper 吃「顯式 content-label」(非檔名) → 對每段 b-roll 檢查其內容主題是否
# 出現在該段字幕裡。M86(占比) AND M87(對位) 都要 green 才能 ship。
# ════════════════════════════════════════════════════════════════════════════

# content-label → 該主題在字幕裡會出現的關鍵詞（演示型旁白）。'generic' 配反思/填充段，永遠 OK。
# EXAMPLE only — pass your own keyword_map; empty default warns instead of vacuous-pass.
EXAMPLE_BROLL_CONTENT_KEYWORDS = {
    "studio":   ["網站", "studio", "首頁", "選單", "服務", "作品", "工坊", "部落格", "3d", "render", "網域", "架站"],
    "gamehall": ["遊戲", "大廳", "款", "小遊戲", "免費", "策略", "動作", "卡牌", "桌遊", "玩法", "上癮"],
    "player":   ["玩家", "系統", "金幣", "簽到", "成就", "勳章", "任務", "連勝", "排行", "獎"],
    "coding":   ["claude", "團隊", "架構", "ui", "debug", "code", "寫", "工具", "加速", "關鍵", "提示詞", "坑"],
    "generic":  [],  # reflective / filler / outro — 配任何旁白都算 OK
}
HAO_BROLL_CONTENT_KEYWORDS = EXAMPLE_BROLL_CONTENT_KEYWORDS  # back-compat alias


def narration_broll_sync_report(captions: list, segments: list,
                                keyword_map: dict = None, strict: bool = False) -> dict:
    """M87 — 旁白↔b-roll 內容對位（content-map driven，不靠檔名）。

    captions: list of (start_s: float, text: str)
    segments: list of (start_s, end_s, content_label) — content_label 是**顯式**內容主題
              ('studio'/'gamehall'/'player'/'coding'/'generic'...)，**不是檔名**
    keyword_map: {content_label: [關鍵詞...]}；預設 HAO_BROLL_CONTENT_KEYWORDS。
    回傳 {rows:[{window, content, caps, matched, reason}], n_mismatch, passed}。
      matched=False 當該段 content 的關鍵詞一個都沒出現在該段字幕裡（generic 永遠 True）。
    strict=True 且有 mismatch → raise（build/swap gate）。
    """
    # `or` → `if is not None`：空 {} 不會被作者預設表蓋掉（2026-06-10 adopter fix，
    # 對齊 caption_broll_matcher；採用者傳 {} = 沒給 content map → 下面警告而非假性 pass）
    km = keyword_map if keyword_map is not None else {}  # 公開版：沒給 map → 警告非假性pass
    rows, n_mis = [], 0
    _unknown = set()
    for (vs, ve, content) in segments:
        caps = [t for (st, t) in captions if vs <= st < ve]
        joined = " ".join(caps).lower()
        kws = km.get(content, None)
        if kws is None:
            if content != "generic":
                _unknown.add(content)
            matched, reason = True, f"未知 content '{content}' — 跳過（無對應 keyword）"
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
    if _unknown and len(_unknown) >= max(1, len(set(c for _, _, c in segments)) - 1):
        import warnings as _w
        _w.warn(
            f"narration_broll_sync_report: content label {sorted(_unknown)} 不在 keyword_map 裡 → "
            "這些段沒被實際檢查（passed 不代表真的對位）。請傳 keyword_map={你的 content→關鍵詞} "
            "或用 'generic' 標填充段。",
            RuntimeWarning, stacklevel=2)
    result = {"rows": rows, "n_mismatch": n_mis, "passed": n_mis == 0,
              "unchecked": sorted(_unknown)}
    if strict and n_mis:
        raise AssertionError(f"M87 narration-broll sync: {n_mis} 段錯位")
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
