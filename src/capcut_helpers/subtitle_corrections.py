"""
capcut_helpers.subtitle_corrections — M69 — 教學影片 AI 字幕通用校正字典 (2026-05-25).

CapCut AI 智能字幕在繁體中文混英文 / 專有名詞 / 品牌名常見錯字 — 永遠先跑這個再 Export。

支援四類誤判（實際條目見下面的字典，此處**刻意不重述詞條**）：
- 中文同音字錯誤（同音別字 → 正確用字）
- 英文品牌/專有名詞被聽成相近的常見英文單字
- 中文音譯誤判（品牌名被音譯成中文詞）
- 技術縮寫誤判（縮寫 → 展開後的正確詞）

⚠️ 下面的字典是**示意範例**（預設不啟用），而且刻意**只放單詞、不放整句**：
   一整條同音「詞組」等於把講者的原句攤在公開程式碼裡。條目的挑選來自某一位講者
   （某種中文口音 + 某組主題）的 ASR 誤判傾向，**不是通用真理** —— 請 copy 一份
   改成你自己的常見誤字。

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
# EXAMPLE correction dict — one speaker's ASR mishears (NOT universal).
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
    "clear": "Claude",       # ASR 誤判
    "Clear": "Claude",
    "crowd": "Claude",
    "Crowd": "Claude",
    "克拉奧": "Claude",       # 中文音譯
    "克勞德": "Claude",
    "可好": "Claude",         # 同音誤判
    # 🚨 2026-05-27 bug fix (audit found): "靠的" 之前同時 map 到 Claude 與 Code (dict key collision)
    # → Python 永遠保留後者 ("Code")，但「靠的」單純看上下文無法判別。
    # 移除 dict entry，改由用戶 case-by-case 手工 Edit JSON 校正
    # (若 "靠的" 出現在「Claude」brand 區段 → 手工改成 Claude；在 "Code" 區段 → 手工改成 Code)

    # Code / Debug / 程式
    "扣的": "Code",          # 同音誤判
    "迪bug": "Debug",        # 同音誤判
    "迪Bug": "Debug",
    "地bug": "Debug",
    "地Bug": "Debug",

    # Brand names — example: lowercase ASR → your brand casing (replace with your own)
    "mybrand": "MyBrand",     # brand-name case fix (example)
    "MYBRAND": "MyBrand",

    # 🆕 English translation 誤判 (AI translate 從中文翻成英文時的常見錯誤)
    # 示意：中文同音字先被聽錯，再被翻成完全不相干的英文字 —— 換成你自己遇到的那組。
    "wrongword": "RightWord",     # translation artifact (example)
    "wrong word": "RightWord",

    # tech-term mishear example (RN → Render)
    "RN的動畫": "Render 的動畫",  # 縮寫誤判
    "RN 的": "Render 的",
    "rn 的": "Render 的",
    "RN animation": "Render animation",
    "RN animations": "Render animations",
}

# Chinese typos — same Mandarin pronunciation but wrong character.
# ⚠️ 合成示意樣本，不是任何真人講稿的片段 —— 一整條同音「詞組」等於把講者的
#    原句攤在公開程式碼裡，請只放你自己逐字稿裡真的出現過的詞，且以單詞為主。
CHINESE_HOMOPHONE_CORRECTIONS = {
    "在說一次": "再說一次",      # 同音誤判（在 vs 再）— example
    "在接再厲": "再接再厲",      # 同音誤判（在 vs 再）— example
}

# Context corrections — whole-phrase fixes (single word looks fine, the phrase doesn't).
# ⚠️ 這一格**最容易外洩**：phrase 條目 = 講者原句的片段。內建這條是**合成句**
#    （拿常見的「的/得」誤判造的，不是任何人的逐字稿）。你自己的 phrase 條目請留在
#    `extra_corrections={...}` 或你自己的私有檔，不要 commit 進公開 repo。
PHRASE_CORRECTIONS = {
    "跑的比預期還快": "跑得比預期還快",   # 的 → 得 (synthetic example)
}


def apply_subtitle_corrections(
    draft: dict,
    extra_corrections: Optional[dict] = None,
    verbose: bool = True,
    use_builtin_corrections: bool = False,  # 公開版預設關（內建字典只是示範樣本）
) -> dict:
    """M69 — Apply subtitle corrections to all text materials.

    ⚠️ 內建的 BRAND/CHINESE/PHRASE 字典只是**示意樣本**（"Claude" 常被
    聽成 cloud/crowd/clear、「再」常被聽成「在」…）。對別人的影片這些是**誤改**
    （"cloud computing"→"Claude computing"）。採用者請：
      - `use_builtin_corrections=False` + 用 `extra_corrections={你的}` 傳自己的，或
      - 把內建字典當 EXAMPLE 抄去改。
    (2026-06-10 adopter fix — 之前內建字典強制套用無法關)

    Args:
        draft: full draft dict (load_draft output)
        extra_corrections: optional dict {wrong: right} for project-specific fixes
        verbose: print every change
        use_builtin_corrections: True=套用內建示範字典（範例，非通用）；False=只用 extra

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

    # Order: longest first (so a longer phrase fires before its substring)
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
            # 純 ASCII 詞 (clear/crowd/cloud/mybrand…) 必須 word-boundary，
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

    ⚠️ 這組 pattern 對應的是上面那本**示意字典**（同一組單詞，不含任何整句 pattern）。
    它是 EXAMPLE，不是通用偵測器 —— 換成你自己的誤判詞再用，否則對別人的稿子只會誤報。
    """
    suspect_patterns = [
        (r"\bcloud\b", "→ likely Claude"),
        (r"\bclouds\b", "→ likely Claude"),
        (r"\bclear\b", "→ likely Claude"),
        (r"\bcrowd\b", "→ likely Claude"),
        (r"\bmybrand\b", "→ likely MyBrand (case) — replace with your own brand"),
        (r"\bRN\b", "→ likely Render"),
        (r"扣的", "→ likely Code"),
        (r"克[拉勞]奧?", "→ likely Claude"),
        (r"可好", "→ likely Claude"),
        (r"迪\s*[bB]ug", "→ likely Debug"),
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
