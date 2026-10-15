"""Public privacy legacy references; canonical implementation."""
from __future__ import annotations

import re
from public_privacy_syntax import _lf, _between, _generalize_identity


PUBLIC_FIXTURE = "PUBLIC_FIXTURE"


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

## 支柱 1：創作者自己的語氣與邏輯

先由使用者提供或授權讀取至少兩篇**同片型、同敘事模式**的本人原稿，保留來源、版本和使用範圍。草稿逐段比對：是否採用本人常用的第一人稱視角、現場帶看方式、能量與幽默，是否真的回答觀眾當下的問題；不要靠重複招牌詞、驚嘆號或通用留存公式假扮語氣。`script_gate` 的 PASS 不能標成 voice PASS。若缺同模式樣本，只能標 `VOICE_REVIEW_REQUIRED`。

寫稿前固定觀眾承諾、真素材證據與可宣稱的功能；缺畫面或尚未完成的成果標 `ASSET_REQUIRED`，不能寫成已完成。觀眾旁白講清楚操作、結果與前後因果；內部驗證項目留在製作表。人工評分和修正只適用其綁定的影片及版本，不能挪作另一支片的評價。

剪輯計畫同時檢查語意相符的畫面數量、動作連續、跨鏡頭調色、音樂連續與有理由的轉場；機械 QA 通過不代表審美通過。個人聲紋、原稿、素材和私人診斷器應保留在受保護的 creator profile，不進公開發行包。

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

載入 creator profile 與同模式原稿 → 鎖定證據／宣稱 → 起稿 → 逐段原稿比較 →
精簡 → 跑 `script_gate.gate(text)` → 人工處理 warnings 與語氣偏差 → 錄音。
只有使用者自己的 transcript/evaluation 能升級為其預設值。
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


PUBLIC_LONGFORM_PIPELINE = '''# Teaching long-form pipeline (public distribution)

> **PUBLIC_FIXTURE / privacy boundary:** no maintainer project title, local path,
> transcript excerpt, analytics screenshot value or dated evaluation ships here.

## 1. Control contract

Use the sole Editkin v4 workflow (controller revision 6). Bind actual sources
and transcript cues, audit the plan, apply once, render a candidate and run
complete delivery QA and the creator-bound visual review. Explicit creator
authority permits artifact-bound agent reference comparison; it never records
human approval. Retired direct-build pipelines cannot register a new current
film. Only the same verified artifact can enter the publishing hub as ready;
technical GREEN/PASS alone is insufficient. Shared media helpers remain tools
inside the audited plan and receipt chain.

## 2. Reusable stages

1. Load creator-owned voice samples in the same register, bind narration claims
   to this video's actual sources, and mark missing proof `ASSET_REQUIRED`.
   `script_gate.py` then checks hook, structure, audience language and rhythm;
   its PASS is not a voice or editorial-quality certificate.
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
