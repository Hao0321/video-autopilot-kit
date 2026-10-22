"""Public privacy reference starters; canonical implementation."""
from __future__ import annotations

import re
from public_privacy_legacy import PUBLIC_FIXTURE, _between, _generalize_identity, _generalize_project_ids, _lf


PUBLIC_BOUNDARY = (
    "> **PUBLIC_FIXTURE / privacy boundary:** creator-specific reference counts, "
    "dated reviews, project metrics, local paths and private preference evidence "
    "are excluded. Calibrate defaults with creator-owned evidence."
)


PUBLIC_UNATTENDED_AUTONOMY = '''# 無人值守剪輯標準

> **PUBLIC_FIXTURE / privacy boundary:** 公開版不預先授權任何審片身分；
> 主觀簽核必須由創作者明確配置，未配置時 fail closed。

## 目標與邊界

創作者不必一直守在螢幕前，系統仍能完成分析、剪輯、機器 QA、可逆修復、
手機／電腦待審包與發佈中樞登記。自動化不等於審美：機器結果只能標為
`CREATOR_REVIEW_REQUIRED` 且 `publish_allowed=false`；未經人工完成時間碼審片，
不得取得 `CERTIFIED_95`、不得標示可發布，也不得對外發布。

## 單一狀態機

- `BLOCKED`：技術 QA、真實性、勝負、隱私、授權、來源、文字安全區或 Quality-95 硬錯誤。停止交付，仍把證據放進待審列。
- `REVIEW_QUEUED`：沒有硬錯，但缺少視覺系統、審片包或機器覆蓋不足；等待已配置的人工 reviewer。
- `AUTO_CANDIDATE`：技術全綠、剪輯／設計／調色系統齊全、非人工維度覆蓋至少 95%，且沒有硬錯。仍然只進待審列。
- `CERTIFIED_95`：只有人工 reviewer 完成時間碼審片與美感量表後，才能由 finalize 工作流產生。

## 可自動修復白名單

自動修復只能降低風險，不得改變事實或創作意圖：

1. 缺鏡頭配對、動作峰值、方向或遮擋證據的轉場退回 `clean_cut`。
2. 缺 tracking、matte、frame QA、貨幣、來源或授權證據的資訊特效停用。
3. 3D 前提不完整時停用執行，只保留已誠實標示的 2D／2.5D fallback。
4. motion cue 明確標為 pending／blocked／rejected 時移除。
5. Log／input transform 不明時停用創意 Look，只允許中性正規化並回報缺口。

禁止自動臆造：勝負、正版／仿製品身份、字幕內容、Tracking 路徑、物件遮罩、
來源、授權、貨幣、價格、地點、素材、配樂理由、3D camera solve 或人工審片結論。

## 集中待審佇列與 actor 授權

佇列固定在 `videos/_PUBLISH_HUB/_STATE/hao_review_queue.json`。鍵值由 content ID、
artifact revision 與 SHA-256 組成：同檔重跑為 `IDEMPOTENT`，同 content ID 新雜湊
會把舊項標為 `SUPERSEDED`。原子寫入加 lockfile 防止多個長短片同時完成時互相覆蓋。

公開版預設沒有任何合法 actor。要解析主觀待審項目，必須先設定逗號分隔的 allowlist：

```powershell
$env:VIDEO_AUTOPILOT_REVIEW_ACTORS='creator,editor'
```

```bash
export VIDEO_AUTOPILOT_REVIEW_ACTORS='creator,editor'
```

actor 比對會忽略大小寫與前後空白；空 allowlist、空 actor 或未列入的 bot 一律 fail closed。
只有列在 `VIDEO_AUTOPILOT_REVIEW_ACTORS` 的 actor 可以把項目設為 `RESOLVED`，
`resolved_by` 會記錄去除前後空白後的 actor 值。

## 持續擴充

每次待審結果分為三類：機械可測錯誤加入 golden／negative fixture；重複且可逆的修法
才加入白名單；主觀美感只進 taste pairwise，不得直接升級成硬規則。新增能力先寫可證偽
驗收、正反例、並行寫入或重跑測試，再接進 `system_health.py`、
Cleanup promotion 與公開版 release fixture。
'''


def _unattended_autonomy(_: str) -> str:
    return PUBLIC_UNATTENDED_AUTONOMY


def _mark_markdown(text: str) -> str:
    text = _lf(text)
    if PUBLIC_FIXTURE in text:
        return text
    heading = re.search(r"(?m)^# .+$", text)
    if not heading:
        return PUBLIC_BOUNDARY + "\n\n" + text
    return text[:heading.end()] + "\n\n" + PUBLIC_BOUNDARY + text[heading.end():]


def _replace_local_paths(text: str) -> str:
    public = re.sub(r"`[A-Za-z]:\\[^`\r\n]+`", "`<LOCAL_PATH>`", _lf(text))
    return re.sub(r"(?<![A-Za-z0-9])[A-Za-z]:\\[^\s\r\n]+", "<LOCAL_PATH>", public)


def _reference_base(text: str) -> str:
    public = _generalize_project_ids(_generalize_identity(_lf(text)))
    public = re.sub(
        r"\b\d+\s*張(?:私人|使用者)?(?:視覺)?參考(?:圖)?",
        "curated creator reference set",
        public,
    )
    public = re.sub(r"\b\d+\s*圖(?=\s*`design_system_v6`)", "curated references", public)
    public = re.sub(
        r"(?im)^.*(?:\u4e0d\u9732\u81c9|\x6e\x6f[- ]?\x66\x61\x63\x65).*(?:\n|$)",
        "",
        public,
    )
    public = re.sub(r"creator\s*主力題材", "profile-selected primary format", public)
    return _replace_local_paths(public)


PUBLIC_EDITING_MASTER = '''# Editing craft master reference

> **PUBLIC_FIXTURE / privacy boundary:** this public guide contains no maintainer
> channel baseline, private project result, dated verdict or face preference.
> Numeric thresholds are configurable starter defaults, never promised outcomes.

## 1. Evidence and intent

- Every cut, overlay, transition and generated asset must answer a narrative or information need.
- Bind claims to approved footage, transcript cues or verified sources; uncertainty becomes a clean hold.
- Compile intent into structured commands, audit, apply atomically, render, run delivery QA and require human review.

## 2. Opening and retention

- Fulfil the title/thumbnail promise early with the strongest verified visual.
- Remove empty lead-in, establish an open question and show what the viewer will gain.
- Use proof, contrast, progress and payoff as interrupts; do not insert effects on a fixed timer.
- Compare retention only across the creator's own platform, duration band and equal measurement window.

## 3. Pacing and continuity

- Alternate information-dense beats with comprehension holds; constant speed creates fatigue.
- Cut on action, preserve screen direction and use J/L cuts only when audio continuity supports the edit.
- Vary shot length around a profile-calibrated baseline and retain a deliberate contrast gap before payoff.
- Transition defaults to a clean cut; whip, match, occlusion and speed ramps require source-pair evidence.

## 4. Typography and graphics

- One display voice and one utility voice per frame; the primary reading path must remain obvious.
- Caption timing comes from approved word timestamps, safe-area checks and readable dwell.
- Tracking needs a verified start box or keyframes; lost confidence hides the graphic instead of guessing.
- Numbers, prices, scores and telemetry are factual claims and require source evidence.

## 5. Audio

- Dialogue leads the mix; music and SFX support a visible beat and never mask speech.
- Use room tone or a short crossfade to avoid digital silence at dialogue edits.
- Verify loudness, peak, full-duration music coverage and the absence of accidental dead zones.
- Do not inherit another creator's speaking rate, noise profile or outro phrase.

## 6. Color and delivery

- Identify input color space, correct exposure/white balance, apply at most one creative look, then add graphics.
- Compare adjacent shots by content class; UI, real footage and structural cards are not one homogeneous sample.
- Verify range metadata, clipping, shot match and subtitle color integrity on the rendered artifact.
- Machine checks can block known failures but cannot certify taste; a designated reviewer owns the final decision.
'''


PUBLIC_AESTHETIC_STANDARD = '''# Creator Aesthetic Standard

> **PUBLIC_FIXTURE / privacy boundary:** the public standard is derived from an
> anonymous, curated reference set. It contains no original reference images,
> private review scores, dated verdicts or maintainer preference history.

## Reference roles

- `layout_only` contributes composition, hierarchy and image/text placement only.
- `art_direction` may contribute color, typography, material and motion principles.
- `full_style` is allowed only when provenance and learning scope are explicit.
- Never copy a recognizable layout, logo, character, protected font or source asset.

## Shared dimensions

Evaluate hierarchy, typography, color discipline, subject integration, evidence clarity,
rhythm, material finish, originality, information energy and cinematic craft. Weights may
differ by format: short-form emphasizes first-frame readability and time design, while
long-form emphasizes sustained hierarchy, subject integration and viewing comfort.

## Hard negatives

- generic full-screen templates replacing usable footage;
- unreadable or clipped text, decorative overlays without semantic targets;
- unsupported tracking, telemetry or authenticity claims;
- copied reference layouts, mixed visual families and uncontrolled density;
- effects leaking outside a verified subject matte;
- machine success presented as human aesthetic approval.

## Human review contract

The active project selects a designated reviewer and scoring profile. A missing review
remains `REVIEW`; machine gates cannot issue aesthetic certification. Pairwise outcomes
may tune the local creator profile only after repeated comparable evidence and must never
be exported as another creator's universal preference.
'''


def _editing_master(_: str) -> str:
    return PUBLIC_EDITING_MASTER


def _aesthetic_standard(_: str) -> str:
    return PUBLIC_AESTHETIC_STANDARD


PUBLIC_ASSET_WORKSHOP = '''# Asset Workshop
> **PUBLIC_FIXTURE / privacy boundary:** no private taste history, dated review,
> rejected result, local path or maintainer reference set; art direction stays local.
## Reality hierarchy
- Approved real footage and verified screen recordings are primary evidence.
- Licensed stock, diagrams and generated assets may clarify an idea but retain provenance.
- Decorative assets support hierarchy; they never replace missing proof or footage.
## Production loop
1. Define the semantic need, intended shot, aspect ratio and review question.
2. Search the approved library before generating anything new.
3. Approve a small direction board, produce the minimum viable asset and test it in context.
4. Register provenance, rights, role, version, review state and allowed reuse scope.
## Roles and review
- `vfx_overlay` needs blend/matte intent; `illustrative_cutout` needs a synthetic label; `background` needs safe-area/duration; `texture` needs scale/blend; `ui_annotation` receives UI-only coverage.
- Deliver the authoritative playable asset through the configured secure remote-review route; contact sheets are supporting cross-frame QA only.
- Persist decisions to the project receipt. Pending/rejected assets remain unselectable, and a failed public route leaves delivery incomplete.
## VFX and hard gates
- Preserve masters and create reversible derivatives; inspect fringe, spill, premultiplication, motion physics, occlusion and safe areas.
- A subject-attached effect requires a verified matte and track. Block unlicensed/private input, missing provenance, unsafe crop, unreadable type and broken alpha.
- Block generated facts presented as evidence, bulk generation before direction approval and assets that do not answer the shot's information need.
'''


def _asset_workshop(_: str) -> str:
    return PUBLIC_ASSET_WORKSHOP


PUBLIC_P0_CALIBRATION = '''## Public P0 calibration

- Real footage remains primary; editable type, tracked arrows, subject-matte sheen and edge HUD are optional information layers.
- A proof must show one complete information arc on the authoritative cut.
- Centre locks are opt-in, brief and blocked when they obscure action.
- Contact sheets are QA evidence, not creative deliverables.
- PUBLIC_FIXTURE contains no private rating, date, approval or rejected project result.'''


def _mrbeast_source_map(text: str) -> str:
    public = _reference_base(text)
    public = _between(public, "## creator-verified P0 calibration", "## 1.", PUBLIC_P0_CALIBRATION)
    public = re.sub(r"(?m)^版本：.*?機器可讀母檔：", "機器可讀母檔：", public)
    return _mark_markdown(public)
