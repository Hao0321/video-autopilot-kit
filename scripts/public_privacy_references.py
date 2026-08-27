#!/usr/bin/env python3
"""Creator-neutral public transforms for references and runtime knowledge."""
from __future__ import annotations

import json
import re

from public_privacy_legacy import (
    PUBLIC_FIXTURE,
    _between,
    _generalize_identity,
    _generalize_project_ids,
    _genre_copy_reference as _legacy_genre_copy_reference,
    _lf,
)


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
驗收、正反例、並行寫入或重跑測試，再接進 `system_health.py`、`project_quality_95.py`、
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


PUBLIC_TRACKING_CALIBRATION = '''## Public motion-review calibration

- Show the complete information arc on the authoritative cut unless the brief isolates one shot.
- A centre lock is opt-in and requires verified state plus a no-occlusion review.
- Prefer object-attached type, arrows, an edge HUD, brief subject-matte sheen or no graphic.
- Contact sheets are used only when cross-frame consistency is the review question.
- PUBLIC_FIXTURE contains no private review date, duration or correction history.'''


def _tracked_typography(text: str) -> str:
    public = _reference_base(text)
    public = _between(public, "## creator motion-review correction", "## 1.", PUBLIC_TRACKING_CALIBRATION)
    return _mark_markdown(public)


def _color_science(text: str) -> str:
    public = _reference_base(text)
    public = re.sub(r"(?m)^# creator 視覺大師", "# Creator Visual Master", public)
    public = public.replace("creator 人工審片", "designated human review")
    public = public.replace("交給 creator 審片", "交給指定人工作最後審查")
    return _mark_markdown(public)


PUBLIC_NICHE_FONTS = '''# Shorts typography and color routing
> **PUBLIC_FIXTURE / privacy boundary:** no private palette verdict, dated feedback,
> local font inventory or maintainer preference; projects supply reviewed tokens.
## Semantic color roles
| Token | Purpose |
|---|---|
| `<TEXT_PRIMARY>` | normal captions with verified contrast |
| `<ACCENT_FACT>` | a price, measurement, place or key fact |
| `<ACCENT_ACTION>` | a single action or state change |
| `<SURFACE>` | restrained support panel when footage contrast varies |
| `<DANGER>` | verified warning or destructive action only |
## Routing and QA
- Start with one text color and one accent; add a role only when it carries distinct information. Test representative bright, dark and textured frames.
- Select fonts by language coverage, license, weight range, renderer support and small-screen legibility; use at most one display and one utility family with deterministic fallbacks.
- Niche is an input to tone, not a fixed palette. Map the brief to qualities such as warm, technical, playful, restrained or documentary, then choose project tokens.
- Verify family resolution, glyph fallback, line breaks, clipping, safe areas, dwell, contrast and color conversion on the final render.
- Record selected font files and tokens in the project receipt for reproducible rerenders.
'''
def _niche_fonts(_: str) -> str:
    return PUBLIC_NICHE_FONTS


PUBLIC_W6_PIP = '''### W6C-4. PiP profile contract
PiP face policy comes from the active project profile. No-face, face-cam, terminal comparison,
before/after and waiting-state PiP are separate semantic roles. Keep a stable corner, matching
aspect, safe margins and no overlap with captions or the active UI. PUBLIC_FIXTURE does not
encode a maintainer face preference or channel result.'''

PUBLIC_W6_CHAPTERS = '''### W6C-6. Chapter count by duration
Choose chapter count from duration, search intent and navigation value. Meet platform syntax,
keep titles unique and review whether chapters help the creator's own comparable releases.
PUBLIC_FIXTURE contains no maintainer duration band, channel baseline or prescribed count.'''

PUBLIC_W6_DEMO = '''### W6C-9. Result-first demo opening
For build/tool tutorials, a short verified result demo may establish the endpoint before the
walkthrough. Its duration and proof mix come from the brief and source evidence, not another
creator's opening pattern or project history.'''

PUBLIC_W6_SCREENCAST = '''### W6C-10. Screencast as B-roll
Record clean source video and drive timing from the approved narration or task structure.
Keep pointer movement intentional, preserve GUI continuity across cuts and retime only with
transparent evidence. The active profile decides whether live narration or separate voice is used.'''

PUBLIC_W6_EDL = '''### W6C-11. Auditable assisted-edit workflow
Pre-edit may synchronize, transcribe, detect silence and organize media. Decisions become a
diffable EDL/JSON proposal; waveform and transcript evidence remain inspectable, and automation
does not apply a cut before audit. PUBLIC_FIXTURE carries no private time-savings claim.'''

PUBLIC_W6_SEARCH = '''### W6C-12. Chapters as retrieval assets
Use auto chapters as a draft, then verify and rewrite labels from the approved script. Inspect
platform search/key-moment behavior after publishing with the creator's own evidence window.
PUBLIC_FIXTURE contains no private CTR, ranking or publishing result.'''


def _wave6(text: str) -> str:
    # Replace private sections before the generic base pass.  The base pass
    # deliberately drops appearance-policy lines, and one legacy section uses
    # that policy in its heading; running it first would erase the anchor.
    public = _replace_local_paths(
        _generalize_project_ids(_generalize_identity(_lf(text)))
    )
    for start, end, replacement in (
        ("### W6C-4.", "### W6C-5.", PUBLIC_W6_PIP),
        ("### W6C-6.", "### W6C-7.", PUBLIC_W6_CHAPTERS),
        ("### W6C-9.", "### W6C-10.", PUBLIC_W6_DEMO),
        ("### W6C-10.", "### W6C-11.", PUBLIC_W6_SCREENCAST),
        ("### W6C-11.", "### W6C-12.", PUBLIC_W6_EDL),
        ("### W6C-12.", "## 落地優先序", PUBLIC_W6_SEARCH),
    ):
        public = _between(public, start, end, replacement)
    public = re.sub(
        r"(?m)^\| W6C-4 \|.*$",
        "| W6C-4 | PiP face policy and placement come from the active project profile | profile + safe-area gate | ◐ review |",
        public,
    )
    return _mark_markdown(_reference_base(public))


PUBLIC_AUDIO_FIXTURE = '''> **PUBLIC_FIXTURE:** audio-chain defaults are configurable starters. Public docs do not
> include a private implementation folder, project loudness result, speed result or dated validation.
> Calibrate room tone, crossfade, loudness, ducking and speed from creator-owned media.'''


def _editing_craft(text: str) -> str:
    public = _reference_base(text)
    public = re.sub(r"(?m)^> ✅ \*\*上表 4 個音訊修正.*$", PUBLIC_AUDIO_FIXTURE, public)
    public = public.replace("creator 工作流必做", "when the active workflow removes speech errors")
    public = public.replace("creator pipeline", "the active creator pipeline")
    return _mark_markdown(public)


PUBLIC_CRAFT_INDEX = '''# Editing craft index
> **PUBLIC_FIXTURE / privacy boundary:** reusable methods only; private signatures,
> review history, outcomes and exclusions stay in the local profile/evidence ledger.
## Read by task
| Task | Primary reference | Supporting reference |
|---|---|---|
| opening, retention and pacing | `editing-master-techniques.md` | `editing-wave5-finecut-2026.md` |
| continuity, audio and color | `editing-craft-fundamentals.md` | `color-science-and-visual-master.md` |
| tracked type and motion evidence | `tracked-typography-and-challenge-ledger.md` | `editing-wave6-2026.md` |
| asset generation and registration | `asset-workshop.md` | `template-compiler-v2.md` |
| short-form structure and QA | `shorts-mastery-2026.md` | `competitor-vertical-teardown-2026.md` |
| typography and color tokens | `niche-fonts-colors.md` | `hao-aesthetic-standard.md` |
| genre-specific routing | `genre-editing-craft-2026.md` | `genre-copy-grammar-2026.md` |
## Application order
1. Establish the claim, audience promise and evidence available in the project.
2. Choose the smallest relevant method set from the table above.
3. Compile a diffable plan with provenance/confidence, audit it, render and run delivery QA.
4. Require designated human review, then log comparable outcomes locally; promote only repeated evidence.
Project truth and platform requirements outrank style. Missing footage, transcript cues, rights or capability create an explicit hold, never a guessed substitution.
'''
def _craft_index(_: str) -> str:
    return PUBLIC_CRAFT_INDEX


def _template_compiler(text: str) -> str:
    return _mark_markdown(_reference_base(text))


PUBLIC_WAVE5 = '''# Fine-cut and retention craft
> **PUBLIC_FIXTURE / privacy boundary:** no maintainer outcome, private benchmark,
> dated correction, local sample or tool decision; numeric gates use project evidence.
## Fine-cut pass order
1. **Truth pass:** align every claim, caption and graphic with approved evidence.
2. **Story pass:** remove duplicated setup, preserve causality and make the payoff legible.
3. **Continuity pass:** check action, eyeline, screen direction, ambience and GUI state.
4. **Rhythm pass:** vary density around comprehension needs; do not cut on a fixed timer.
5. **Polish/delivery:** add only motivated sound, motion, color and type; render, inspect representative frames, audit audio and verify the artifact.
## Retention, evidence and audio
- Fulfil the packaging promise early; use questions, contrast, progress, proof and payoff as semantic interrupts, with comprehension holds after dense information.
- Bind each number/state to a source and time range. Tracking starts verified and hides on lost confidence; comparisons use matched scales, units and windows.
- Dialogue leads; preserve room tone/crossfades. Caption timing follows approved word timestamps and readable dwell, then passes line-break, safe-area, glyph and contrast QA.
- Store release conditions and measurement windows locally. One result is an observation; defaults stay reviewable and reversible until repeated evidence supports promotion.
'''
def _wave5(_: str) -> str:
    return PUBLIC_WAVE5


PUBLIC_AUTOPILOT_MODES = '''# Video Autopilot operating modes
> **PUBLIC_FIXTURE / privacy boundary:** no personal voice/CTA, local project ID,
> outcome baseline, dated verdict or retired-editor history; projects configure modes.
## Mode A — Plan
Input a topic, source inventory and targets. Produce an evidence-aware brief, script/shot/edit plan, packaging options, review contract and publish checklist. Required sources, rights and truth constraints must resolve before render.
## Mode B — Log outcome
Record release, platform, duration band, packaging variant, measurement window and available metrics locally. Preserve missing values as unknown.
## Mode C — Optimize patterns
Compare compatible releases only. Propose a reversible default with evidence, counterexamples and review condition; human approval is required.
## Build transaction
1. Bind the project contract, source hashes, knowledge version and output target.
2. Prepare bounded media evidence and derive semantics without mutating source files.
3. Audit a structured proposal, atomically apply one accepted plan, render and run technical QA.
4. Deliver the authoritative artifact for secure remote review, persist the receipt and publish only after approval.
Original media stays read-only; intermediates are disposable; current output updates atomically; history stores metadata/receipts. Private profiles, tokens, paths and ledgers are excluded. Missing capability creates a bounded hold and cannot bypass audit.
'''
def _autopilot_modes(_: str) -> str:
    return PUBLIC_AUTOPILOT_MODES


PUBLIC_COMPETITOR_TEARDOWN = '''# Vertical-video teardown method
> **PUBLIC_FIXTURE / privacy boundary:** no private sample inventory, source-account
> list, dated snapshot or verdict; retain only lawfully accessible project evidence.
## Research contract
1. Define platform, niche, duration band, audience intent and observation window.
2. Record a public source locator, capture date, visible interaction fields and uncertainty.
3. Separate observed facts from editorial inference; never estimate hidden analytics.
4. Compare matched cohorts and preserve weak/negative examples to reduce survivorship bias.
## Shot-level schema
For each segment record time range, shot role, subject, framing, motion, text role, caption dwell, transition, audio cue, claim evidence and confidence. Derive cut/information density and semantic interrupts.
## Analysis lenses
- **Opening:** first comprehensible promise, proof and unresolved question.
- **Pacing:** variation, comprehension holds and whether cuts follow meaning or action.
- **Typography:** hierarchy, safe-area use, line length, contrast and motion semantics.
- **Audio:** dialogue priority, music structure, effects and intentional silence.
- **Payoff:** whether the ending resolves the promise and supports an optional loop.
Extract functions, not identity. Rebuild with original layout, typography, assets and voice. Patterns stay hypotheses until tested against comparable creator-owned outcomes; never promise results.
Return an evidence table, uncertainty list, reusable hypotheses, blocked claims and a small experiment plan. Do not redistribute captured media, private notes or source lists.
'''
def _competitor_reference(_: str) -> str:
    return PUBLIC_COMPETITOR_TEARDOWN


def _genre_copy_reference(text: str) -> str:
    return _mark_markdown(_reference_base(_legacy_genre_copy_reference(text)))


PUBLIC_GENRE_EDITING = '''# Genre editing craft
> **PUBLIC_FIXTURE / privacy boundary:** reusable routes only; no preference profile,
> private source set, outcome, local path, appearance rule or dated review.
## Route by viewer job
| Viewer job | Editorial spine | Visual priority | Audio priority |
|---|---|---|---|
| learn a process | result → steps → verification | readable actions and proof | clear explanation |
| evaluate a product | claim → test → trade-off | matched comparisons | neutral continuity |
| experience a place | orientation → detail → reflection | location truth and sensory detail | natural ambience |
| understand a story | setup → change → consequence | causality and character state | motivated perspective |
| follow a challenge | rule → progress → obstacle → payoff | state and progress clarity | escalating contrast |
| watch an interview | premise → answer → evidence → implication | speaker/context clarity | speech continuity |
## Shared craft rules
- Establish the viewer job and packaging promise before selecting a genre style.
- Prefer verified footage and clean holds over unrelated generic B-roll.
- Use graphics for state, comparison, location or explanation, never decoration alone.
- Keep transitions motivated by movement, shape, time, place or narrative change.
- Let density follow comprehension and block unsupported claims at plan/render stages.
Each project may set tone, palette, typography, narration and pacing with local evidence and review. When rules conflict, viewer job, source truth and accessibility win.
Audit opening promise, evidence coverage, continuity, caption readability, audio intelligibility, rights, delivery and human approval. Log matched outcomes before proposing a default.
'''
def _genre_editing_reference(_: str) -> str:
    return PUBLIC_GENRE_EDITING


PUBLIC_SHORTS_MASTERY = '''# Short-form video mastery
> **PUBLIC_FIXTURE / privacy boundary:** no private channel samples, source locations,
> results, dated feedback or preference; thresholds are project configuration.
## Define the promise
Write one sentence naming what the viewer will understand, feel or see resolved. Bind opening, captions and payoff to it; narrow the promise when footage cannot support it.
## Segment contract
Each segment records source, valid time range, subject, role, claim evidence, caption, audio role and transition intent. Captions bind to segments and never guess unreadable facts.
## Opening
- Make the subject and value legible immediately with a verified close or clear state.
- Avoid logo-only lead-ins, unexplained atmosphere and promises whose proof appears too late.
- Cut on change in action, information or perspective; validate phone-sized with sound on/off.
## Pacing and loops
- Use shot changes, caption changes and audio beats as separate rhythm channels.
- Alternate density with comprehension holds. A loop is optional, preserves join continuity and never hides a false claim; calls to action follow the brief.
## Captions and graphics
- Use short, spoken-language lines with verified dwell, contrast, safe area and glyph coverage.
- Highlight semantic roles only. Persistent facts use a dedicated layer; generated telemetry, reconstructed signs and decorative UI are not evidence.
Duration, safe areas, metadata, music rights and link behavior are platform-specific; do not reuse one platform's heuristic as another's hard gate.
## QA and learning
1. Audit source/claim alignment, caption timing, continuity, audio and delivery settings.
2. Render the authoritative candidate and inspect opening, densest beat, payoff and loop join.
3. Require designated human approval, log comparable outcomes locally and promote only repeated matched evidence with reversible defaults.
'''
def _shorts_mastery(_: str) -> str:
    return PUBLIC_SHORTS_MASTERY


def _cleanup_changelog(text: str) -> str:
    return _mark_markdown(_replace_local_paths(text))


def _quality_corpus(text: str) -> str:
    data = json.loads(_lf(text))
    for case in data.get("negative_cases", []):
        if case.get("id") == "design-dna-not-compiled":
            case["message"] = "視覺計畫未經 creator-configured reference-set DNA 路由；需補題材、角色與畫幅 reflow。"
        elif case.get("id") == "unapproved-imagegen-selected":
            case["message"] = "Imagegen 生成物在 creator approval 前必須 human_review=pending、selectable=false；不得進正式渲染或自動路由。"
    data["public_distribution"] = "PUBLIC_FIXTURE: creator-specific review evidence is excluded."
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _design_trend_radar(text: str) -> str:
    data = json.loads(_lf(text))
    rules = list(data.get("hao_fusion_rules") or [])
    if len(rules) < 2:
        raise ValueError("design trend radar requires its compatibility rule list")
    rules[1] = "Creator-configured aesthetic hierarchy, typography and color discipline remain the base standard."
    data["hao_fusion_rules"] = rules
    data["public_distribution"] = "PUBLIC_FIXTURE: no private profile attribution or review outcome."
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


SANITIZERS = {
    "codex-skill/video-autopilot/references/unattended-autonomy-standard.md": _unattended_autonomy,
    "codex-skill/video-autopilot/references/editing-master-techniques.md": _editing_master,
    "codex-skill/video-autopilot/references/hao-aesthetic-standard.md": _aesthetic_standard,
    "codex-skill/video-autopilot/references/asset-workshop.md": _asset_workshop,
    "codex-skill/video-autopilot/references/mrbeast-production-source-map.md": _mrbeast_source_map,
    "codex-skill/video-autopilot/references/tracked-typography-and-challenge-ledger.md": _tracked_typography,
    "codex-skill/video-autopilot/references/color-science-and-visual-master.md": _color_science,
    "codex-skill/video-autopilot/references/niche-fonts-colors.md": _niche_fonts,
    "codex-skill/video-autopilot/references/editing-wave6-2026.md": _wave6,
    "codex-skill/video-autopilot/references/editing-craft-fundamentals.md": _editing_craft,
    "codex-skill/video-autopilot/references/craft-index.md": _craft_index,
    "codex-skill/video-autopilot/references/template-compiler-v2.md": _template_compiler,
    "codex-skill/video-autopilot/references/editing-wave5-finecut-2026.md": _wave5,
    "codex-skill/video-autopilot/references/autopilot-modes.md": _autopilot_modes,
    "codex-skill/video-autopilot/references/competitor-vertical-teardown-2026.md": _competitor_reference,
    "codex-skill/video-autopilot/references/genre-copy-grammar-2026.md": _genre_copy_reference,
    "codex-skill/video-autopilot/references/genre-editing-craft-2026.md": _genre_editing_reference,
    "codex-skill/video-autopilot/references/shorts-mastery-2026.md": _shorts_mastery,
    "knowledge/runtime/quality_corpus.json": _quality_corpus,
    "knowledge/runtime/design_trend_radar.json": _design_trend_radar,
    "tools/code-cleanup-helper/CHANGELOG.md": _cleanup_changelog,
}
