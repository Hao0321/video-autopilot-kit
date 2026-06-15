"""
capcut_helpers.subtitle_corrections — M69 — Hao 影片 AI 字幕通用校正字典 (2026-05-25).

CapCut AI 智能字幕在台灣中文混英文 / 專有名詞 / 品牌名常見錯字 — 永遠先跑這個再 Export。

支援：
- 中文同音字錯誤 (扣的 → Code / 網易 → 網域)
- 英文品牌名誤判 (cloud → Claude / studio → Studio)
- 中文音譯誤判 (克拉奧 → Claude / 可好 → Claude)
- 動詞誤判 (加過 → 架過 / 磕 → 刻)

Usage:
    from capcut_helpers import (
        safe_kill_then_verify, load_draft, save_draft_with_sync,
        apply_subtitle_corrections,
    )
    safe_kill_then_verify()  # M20
    draft = load_draft(project_name)
    stats = apply_subtitle_corrections(draft)
    save_draft_with_sync(project_name, draft)
"""
import json
import re
from typing import Optional

# 🆕 2026-05-27: AP12 真正落地 — 用 @validate_invariants decorator 取代 inline range fix
from .invariants import validate_invariants, TEXT_MATERIAL_INVARIANTS, TEXT_MATERIAL_AUTO_FIX


# ─────────────────────────────────────────────────────────────────────
# EXAMPLE correction dict — the author's personal mishears (NOT universal).
# Default is OFF (use_builtin_corrections=False); copy + edit for your own.
# 永遠 grow this dict as new errors found
# ─────────────────────────────────────────────────────────────────────

# Critical brand / proper noun typos — ASCII keys are word-boundary matched (\b) in _mutate_one_text
BRAND_CORRECTIONS = {
    # Claude — most common mishear
    "cloud": "Claude",
    "Cloud": "Claude",
    "clouds": "Claude",
    "Clouds": "Claude",
    "CLOUD": "CLAUDE",
    "clear": "Claude",       # [63] 搭配 clear → 搭配 Claude
    "Clear": "Claude",
    "crowd": "Claude",
    "Crowd": "Claude",
    "克拉奧": "Claude",       # 中文音譯
    "克勞德": "Claude",
    "可好": "Claude",         # [73] 可好的玩法 → Claude 的玩法
    # 🚨 2026-05-27 bug fix (audit found): "靠的" 之前同時 map 到 Claude 與 Code (dict key collision)
    # → Python 永遠保留後者 ("Code")，但「靠的」單純看上下文無法判別。
    # 移除 dict entry，改由用戶 case-by-case 手工 Edit JSON 校正
    # (若 "靠的" 出現在「Claude」brand 區段 → 手工改成 Claude；在 "Code" 區段 → 手工改成 Code)

    # Code / Debug / 程式
    "扣的": "Code",          # [8] 沒寫過扣的 → 沒寫過 Code
    "迪bug": "Debug",        # [56] 負責迪bug → Debug
    "迪Bug": "Debug",
    "地bug": "Debug",
    "地Bug": "Debug",

    # Brand names
    "studio": "Studio",       # [22] 我的 studio 網站 (case fix)
    "STUDIO": "Studio",

    # 🆕 2026-05-26 English translation 誤判 (AI translate 從中文翻成英文時的常見錯誤)
    "deductions": "Code",     # 沒寫過 Code → wrote about deductions (#006 v6b 抓到)
    "deduction": "Code",
    "NetEase": "a domain",    # 買了網域 → bought NetEase (#006 v6b 抓到)
    "net ease": "a domain",

    # 渲染 (Render mishear)
    "RN的動畫": "Render 的動畫",  # [中] 3D RN 的動畫 → 3D Render 的動畫
    "RN 的": "Render 的",
    "rn 的": "Render 的",
    "3D RN ": "3D Render ",      # [英] 3D RN animation → 3D Render animation
    "3D rn ": "3D Render ",
    "RN animation": "Render animation",
    "RN animations": "Render animations",
}

# Chinese typos — same Mandarin pronunciation but wrong character
CHINESE_HOMOPHONE_CORRECTIONS = {
    "網易": "網域",            # [5] 買了網易上架 → 買了網域上架
    "加過網站": "架過網站",      # [9] 沒加過網站 → 沒架過網站
    "從無到有磕": "從無到有刻",   # [30] 磕出來 → 刻出來
    "見拜拜": "見 掰掰",        # [82] 影片見拜拜 → 影片見 掰掰
}

# Context corrections — usually whole-phrase fixes
PHRASE_CORRECTIONS = {
    # [49] 那個體驗非常完整 → 整個體驗非常完整 (那→整)
    "那個體驗非常完整": "整個體驗非常完整",
    # [47] but unsure — 但是 might be intentional
}


def apply_subtitle_corrections(
    draft: dict,
    extra_corrections: Optional[dict] = None,
    verbose: bool = True,
    use_builtin_corrections: bool = False,  # 公開版預設關（內建字典是原作者個人口誤）
) -> dict:
    """M69 — Apply subtitle corrections to all text materials.

    ⚠️ 內建的 BRAND/CHINESE/PHRASE 字典是**作者個人的口誤**（他講 Claude 常被聽成
    cloud/crowd/clear、買「網域」被聽成網易…）。對別人的影片這些是**誤改**
    （"cloud computing"→"Claude computing"）。採用者請：
      - `use_builtin_corrections=False` + 用 `extra_corrections={你的}` 傳自己的，或
      - 把內建字典當 EXAMPLE 抄去改。
    (2026-06-10 adopter fix — 之前內建字典強制套用無法關)

    Args:
        draft: full draft dict (load_draft output)
        extra_corrections: optional dict {wrong: right} for project-specific fixes
        verbose: print every change
        use_builtin_corrections: True=套用內建作者字典（Hao 用）；False=只用 extra

    Returns:
        {'total_fixes': N, 'fixes_per_kind': {brand: N, chinese: N, phrase: N},
         'changes': [(text_idx, original, corrected, kind), ...]}
    """
    all_corrections = []
    if use_builtin_corrections:
        all_corrections.extend([(k, v, "brand") for k, v in BRAND_CORRECTIONS.items()])
        all_corrections.extend([(k, v, "chinese") for k, v in CHINESE_HOMOPHONE_CORRECTIONS.items()])
        all_corrections.extend([(k, v, "phrase") for k, v in PHRASE_CORRECTIONS.items()])
    if extra_corrections:
        all_corrections.extend([(k, v, "extra") for k, v in extra_corrections.items()])

    # Order: longest first (so "從無到有磕" fires before "磕")
    all_corrections.sort(key=lambda x: -len(x[0]))

    texts = draft.get("materials", {}).get("texts", [])
    changes = []
    fixes_per_kind = {"brand": 0, "chinese": 0, "phrase": 0, "extra": 0}

    # 🆕 AP12 落地 (2026-05-27): wrap text mutation with @validate_invariants
    # Decorator handles M73 styles[].range sync automatically — no more inline fix.
    @validate_invariants(
        invariants=TEXT_MATERIAL_INVARIANTS,
        auto_fix=TEXT_MATERIAL_AUTO_FIX,
        on_violation="warn",
    )
    def _mutate_one_text(co: dict, corrections_list: list, idx: int) -> dict:
        """Apply correction list to co["text"] in-place. Wrapper auto-syncs styles[].range."""
        text = co.get("text", "")
        orig_iter = text
        for wrong, right, kind in corrections_list:
            # 純 ASCII 詞 (clear/crowd/cloud/studio…) 必須 word-boundary，
            # 否則 "clearly"→"Claudely" / "crowded"→"Claudeed" (2026-06-10 audit)
            if wrong.isascii() and wrong.replace(" ", "").isalnum():
                new_text, n = re.subn(rf"\b{re.escape(wrong)}\b", right, text)
                if n == 0:
                    continue
                text = new_text
            elif wrong in text:
                text = text.replace(wrong, right)
            else:
                continue
            fixes_per_kind[kind] += 1
            changes.append((idx, orig_iter, text, kind, wrong, right))
            if verbose:
                print(f'  [{idx:3}] {kind}: {wrong!r} → {right!r}')
                print(f'        BEFORE: {orig_iter[:80]}')
                print(f'        AFTER:  {text[:80]}')
            orig_iter = text
        co["text"] = text
        return co

    for i, t in enumerate(texts):
        try:
            co = json.loads(t.get("content", "{}"))
        except json.JSONDecodeError:
            continue
        if not co.get("text"):
            continue
        text_before = co.get("text", "")

        _mutate_one_text(co, all_corrections, i)  # auto-syncs range via decorator

        if co.get("text", "") != text_before:
            t["content"] = json.dumps(co, ensure_ascii=False, separators=(",", ":"))

    return {
        "total_fixes": len(changes),
        "fixes_per_kind": fixes_per_kind,
        "changes": changes,
    }


def scan_potential_errors(draft: dict) -> dict:
    """Scan for likely AI errors without modifying. Returns suspect text list.

    Useful for pre-flight review before applying corrections.
    """
    suspect_patterns = [
        (r"\bcloud\b", "→ likely Claude"),
        (r"\bclouds\b", "→ likely Claude"),
        (r"\bclear\b", "→ likely Claude"),
        (r"\bcrowd\b", "→ likely Claude"),
        (r"\bstudio\b", "→ likely Studio (case)"),
        (r"\bRN\b", "→ likely Render"),
        (r"扣的", "→ likely Code"),
        (r"網易", "→ likely 網域"),
        (r"克[拉勞]奧?", "→ likely Claude"),
        (r"可好", "→ likely Claude"),
        (r"加過", "→ likely 架過"),
        (r"迪\s*[bB]ug", "→ likely Debug"),
        (r"拜拜", "→ likely 掰掰"),
        (r"磕出", "→ likely 刻出"),
    ]

    suspects = []
    texts = draft.get("materials", {}).get("texts", [])
    for i, t in enumerate(texts):
        try:
            text = json.loads(t.get("content", "{}")).get("text", "")
        except json.JSONDecodeError:
            continue
        if not text:
            continue
        for pat, note in suspect_patterns:
            if re.search(pat, text, re.IGNORECASE):
                suspects.append({"text_idx": i, "text": text, "pattern": pat, "note": note})

    return {"total_suspects": len(suspects), "suspects": suspects}
