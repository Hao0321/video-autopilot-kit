# 🎬 video-autopilot-kit

> 一套**框架式**的 YouTube / 短影音自動化工具 + 方法論模板。
> 給你純程式 ffmpeg pipeline + CapCut 自動化的程式碼，加上一份「問卷」——
> 你回答關於**你自己頻道**的問題，它就變成屬於你的系統。
>
> ⚠️ **不含任何人的私人數據** —— 後台讀數 / 個人檔案 / 別人的帳號名一律不進 repo（例外：LICENSE 與 README 的作者署名）（`profiles/`、`config.py` 是 gitignored 本機檔）。
> voice 詞表、KPI 門檻與社群欄位要嘛是**空白模板**（`<fill in>` / `______` / 產出檔的 `{你的…}` 佔位字樣），要嘛**標示為「範例值」**，你填你的。
> 反過來說：`knowledge/` 裡的方法論**是**原作者的實戰結論，那是刻意開源的部分 —— 是「怎麼想」，不是「他的數字」。

## 🧭 我該走哪條路？（3 秒決策樹）

- **用 Mac / Linux？** → **Path 1 Programmatic**（純程式，跨平台，不碰 CapCut）
- **要 CapCut 的特效 / 花字 / 雲端模板？** → **Path 2 CapCut-assisted**（Windows 優先；**版本敏感**，先看 [TROUBLESHOOTING](TROUBLESHOOTING.md) 的版本相容矩陣）
- **只想全自動、不想開任何 GUI？** → **Path 1 Programmatic**

## ▶️ 60 秒看它跑（不用 CapCut、不用真素材）

想先看它**真的會動**？`examples/` 裡有自包含、可直接跑的 demo —— 用 ffmpeg 合成測試素材，不需要任何真實影片或 CapCut：

```bash
python examples/01_vertical_short.py      # 合成素材 → 完整 1080x1920 直式 Short
python examples/02_caption_broll_match.py # 零設定：b-roll 用內容命名就自動對位字幕
python examples/04_shorts_gate.py         # 直式 Shorts 閘門：壞剪法被擋 → 修好放行 → 換你的門檻再放行
python examples/05_interview_plan.py      # 訪談來賓閘門：沒來源的數據在「錄影之前」就被擋下
```

需求：Python 3.9+。**04 / 05 連 ffmpeg 都不用**（純 Python、零 `pip install`、零素材）；01 需要
`ffmpeg`/`ffprobe`，03 另需 Pillow + numpy。細節見 [`examples/README.md`](examples/README.md)。

## 為什麼不一樣

市面上的「creator 系統」要嘛賣你**某個人的設定**（抄了對你沒用、還可能誤導），
要嘛太通用沒有方法論。這個 kit 給你**骨架**（經實戰的結構），
`SETUP.md` 一區一區**問你問題**，用你的答案填滿它 —— 這樣它才真的是**你的**系統。

## 🆕 v0.10.0 新增 — 三條**同構**的生產線

以前這個 kit 只回答一件事：「怎麼把**一支長片**做好。」現在是三條生產線 ——
而且刻意長成**同一個形狀**：**知識層（為什麼這樣做）→ 機械閘門（不靠任何人記得）→ 一鍵驅動（幾個指令跑完）**。
學會一條就等於學會三條；要加第四條（Podcast？教程系列？）也照這個骨架接。

| 生產線 | 知識層（為什麼） | 機械閘門（擋在前面） | 一鍵驅動 |
|---|---|---|---|
| **教學長片** | `knowledge/premium-motion-fx.md`＋`knowledge/meta-lessons.md` | `plan_gate` → `script_gate` → `delivery_qa(profile='teaching_longform')` | `src/longform_maker/` 各模組 |
| **直式 Shorts** | [`knowledge/shorts-mastery-2026.md`](knowledge/shorts-mastery-2026.md) | [`src/longform_maker/shorts_gate.py`](src/longform_maker/shorts_gate.py)　九條結構／字幕規則（其餘三條靠人看畫面），**純 Python** | [`src/shorts_autopilot.py`](src/shorts_autopilot.py)　`scan` → 看畫面填字 → `build`（含自動 QA 驗證圖） |
| **線上訪談** | [`knowledge/interview-show-playbook.md`](knowledge/interview-show-playbook.md) | [`src/interview_gate.py`](src/interview_gate.py)　I-A~I-E：**沒來源的來賓數據不上鏡** | [`src/interview_autopilot.py`](src/interview_autopilot.py)　`invite` → `plan`（產 7 件套）→ `build` |

- **閘門共用外殼** [`src/longform_maker/gate_core.py`](src/longform_maker/gate_core.py) —— 回傳結構 / `assert` 訊息 / self-test 印法一致，
  你自己加的閘門 import 三個函式就跟內建的行為一模一樣（**判定規則各自留在自己的檔**，不集中才不會互相污染）
- **經營層**（v0.9 起）：`src/channel_tracker.py` D2/D7/D28 快照排程＋待辦、`src/system_health.py` 一鍵 GREEN/RED 健檢
  → 接線指南 [`knowledge/ops-automation.md`](knowledge/ops-automation.md)；爆款定義框架 [`knowledge/viral-playbook-framework.md`](knowledge/viral-playbook-framework.md)
- ⚠️ 兩道閘門裡的**門檻數字都是範例校準值，不是宇宙常數** —— Shorts 片長帶 / 首刀秒數 / 非白字上限請用**你自己**的 3-5 支片重算
  （做法見 [SETUP.md](SETUP.md) 的「Shorts 規則校準」）

## 內容 —— 兩條 first-class path

這個 kit 有**兩條同等地位的路**，不是「主力 vs 次要」：

> 跟上面的「三條生產線」是**不同的軸**：生產線＝你在做**哪種片**（長片 / Shorts / 訪談）；
> path＝你用**什麼方式**做（純程式 vs CapCut）。三條生產線都可以走 Path 1。

| 路徑 | 模組 | 是什麼 | 平台 |
|---|---|---|---|
| ⭐ **Path 1 — Programmatic**（推薦採用者預設） | `src/longform_maker/` | **教學長片模組** —— `fx_lib` premium 動態引擎（亞像素 Ken Burns / 雙層 bloom / light sweep / easing / 合成 SFX）、`word_captions` 字級時間字幕（M105）、`screen_clean` 螢幕錄影機械化清理（M104）。參數真值 → `knowledge/premium-motion-fx.md` | Win / Mac / Linux |
| ⭐ **Path 1 — Programmatic** | `src/silent_vlog_maker/` | **純 ffmpeg pipeline** —— 直式 Shorts（多色字幕 / BGM 高光起點 / 正規化）、靜音 vlog、素材清理 | Win / Mac / Linux |
| ⭐ **Path 1 — Programmatic**（v0.10） | `src/shorts_autopilot.py` + `src/longform_maker/shorts_gate.py` | **直式 Shorts 生產線** —— `scan` 正規化 9:16 + 抽接觸表 + 產 `_plan.py` 骨架 → 你（或 AI）**看畫面填字** → `build` 過閘門、成片、自動 QA 出驗證圖。閘門本身純 Python（連 ffmpeg 都不用）| Win / Mac / Linux |
| ⭐ **Path 1 — Programmatic**（v0.10） | `src/interview_autopilot.py` + `src/interview_gate.py` + `templates/interview/` | **線上訪談生產線** —— 來賓資訊 → 邀約訊息 / 主持台本 / 訪綱 / 準備包 / 授權書 / 錄製 checklist / 發布套件 / Shorts 切條，全部從模板 render；來賓數據沒來源就擋在錄製前 | Win / Mac / Linux |
| ⭐ **Path 1 — Programmatic**（v0.10） | `src/longform_maker/gate_core.py`、`src/av_util.py` | **共用底座** —— 所有閘門的統一外殼（report / assert / self-test）＋ autopilot 共用機械動作（subprocess / ffprobe 時長 / 抽幀 / 接觸表）| Win / Mac / Linux |
| ⭐ **Path 1 — Programmatic** | `src/capcut_helpers/` 的 **QA gates** | **交付前機械化 QA**（`delivery_qa`：頻閃·死空檔·caption-sync·全幀掃描 M91-M95 / `broll_audit` 占比 / `caption_broll_matcher` 對位）—— 純 ffmpeg/Python，**不需要 CapCut**，兩條 path 的成品都該過這關 | Win / Mac / Linux |
| **Path 2 — CapCut-assisted**（作者本人主用） | `src/capcut_helpers/` 其餘 | **CapCut Desktop 自動化** —— 草稿 JSON 直改（draft I/O / 4-level 靜音 / 花字 / AI 字幕校正）+ **AI 助手 + Computer Use 操作 CapCut 視窗**（套模板 / 匯出）。**版本敏感** → [TROUBLESHOOTING](TROUBLESHOOTING.md) | Windows-first |
| 共用 | `knowledge/` | **影片製作知識庫** —— M1-M111 避坑大全 + 演算法 + SOP + 剪輯心法 | — |
| 共用 | ▶️ `examples/` | **自包含可跑 demo** —— ffmpeg 合成素材，60 秒看 pipeline 真的動（不用 CapCut/真素材）| — |
| 共用 | ⭐ `SETUP.md` | **從這開始** —— 回答問題讓系統變成你的 | — |
| 共用 | `templates/` | voice / 品牌 / 演算法 / 社群 的**空白填寫**模板；v0.10 加 `show_profile`（節目設定）與 `templates/interview/` 11 份訪談交付模板 —— **改話術改模板，不要改程式** | — |
| 共用 | `config.example.py` | 路徑設定範例（複製成 `config.py` 填你的，**範例不含任何帳號名**）| — |

> **誠實聲明**：原作者的私人流程以 **Path 2（CapCut）** 為主 —— 但那是因為他的素材、模板、肌肉記憶都在 CapCut 上。
> 開源採用者**多數應該從 Path 1 開始**：跨平台、無 CapCut 依賴、不吃 CapCut 版本變動、全程可重現。
> 需要 CapCut 的花字/雲端模板時再上 Path 2。

### Platform support

| 模組 | Windows | macOS |
|---|---|---|
| Programmatic（`longform_maker` / `silent_vlog_maker` / QA gates） | ✅ | ✅（路徑/字型由 `src/platform_compat.py` 探測；Linux 同） |
| CapCut 草稿 JSON 直改（`capcut_helpers` draft I/O） | ✅ 本機親測 | ⚠️ 路徑已支援（`CAPCUT_USER_DATA` env override + `detect_draft_format()`），自動化未在 Mac 實測 |
| Computer Use GUI 自動化（套模板 / 匯出） | ✅ | ❌（CapCut Mac 無 AppleScript dictionary；見 [TROUBLESHOOTING](TROUBLESHOOTING.md) 的 Mac 節） |

## 🚀 快速開始

1. 讀 **`SETUP.md`** → 照問題把 `templates/*.template.md` 填成 `profiles/*.md`
   （或把整個 repo 丟給 Claude / ChatGPT，說「照 SETUP.md 問我問題，幫我生成 profiles/」）
2. `cp config.example.py config.py` → 填你的素材 / 匯出路徑（走 Path 2 才需要 CapCut 路徑）
3. 選路：**Path 1** 裝好 Python + ffmpeg 就能跑；**Path 2** 額外裝 CapCut Desktop + 開啟 AI 助手的 Computer Use（見下方需求）
4. 開始用 `src/` 的工具

## 需求

**Path 1 — Programmatic（推薦採用者預設；Win / Mac / Linux）**
- Python 3.9+
- `ffmpeg` / `ffprobe`（在 PATH 上）
- **不需要 CapCut、不需要 Computer Use** —— 整條 pipeline 都是可重現的程式碼
- Mac/Linux：系統路徑與 CJK 字型由 `src/platform_compat.py` 自動探測（不要 hardcode 系統字型路徑）
- 唯一需要 pip 套件的是 **`src/shorts_autopilot.py`**（一鍵直式 Shorts 流程）：**Pillow + numpy**
  —— 用來分析畫面品質、拼接觸表、抽 QA 驗證圖。
  規則閘門 `src/longform_maker/shorts_gate.py` **這個檔案本身**是純 Python（連 ffmpeg 都不用），
  只想用閘門就不必裝任何東西 → `python examples/04_shorts_gate.py`。
  ⚠️ 但**要平面 import**（把 `src/longform_maker/` 加進 `sys.path` 再 `from shorts_gate import …`，
  範例 04 就是這樣寫的）；走 `from longform_maker.shorts_gate import …` 會經過套件 `__init__`，
  那裡會載入 `fx_lib`（需要 numpy + Pillow）。或直接把 `shorts_gate.py` + `gate_core.py` 複製走。
- 訪談生產線（`src/interview_autopilot.py` / `src/interview_gate.py`）的**訪前企劃全程純 Python**
  —— 產 7 件套不需要 ffmpeg 也不需要 pip 套件；ffmpeg 只有錄完 `build` 才用得到
  → `python examples/05_interview_plan.py`

**Path 2 — CapCut-assisted（作者本人主用；Windows-first、版本敏感）**
- **CapCut Desktop 國際版**（有 Pro 更好）—— 剪輯 / 套字幕 / 套模板在這。⚠️ **版本敏感**：草稿 JSON 直改對版本有相容矩陣（剪映 CN 6.0+ 已加密不可直改）—— 動手前先讀 [TROUBLESHOOTING](TROUBLESHOOTING.md)，並用 `detect_draft_format()` 驗明文
- **AI 助手 + Computer Use**（Claude Desktop / Claude Code 等）—— GUI 自動化（套雲端模板 / 匯出）必需；**Mac 上沒有可用的等效機制**（見 TROUBLESHOOTING 的 Mac 節）
- Python 3.9+ 與 `ffmpeg` / `ffprobe` —— 匯出後的後製：BGM loop / 修剪到人聲尾 / player-safe 重編

*(選用)* AI 助手（Claude / ChatGPT）也能照 `SETUP.md` 自動把你的答案生成 profiles。

## 設計理念

一套創作系統最值錢的是**結構與方法論**，不是某個人的私人數字。
所以這個 repo 給你骨架，你用自己的血肉填滿。

## License

MIT — 保留標註即可自由使用 / 修改 / 商用。

## Author

Hao0321 Studio — 從一套實戰的個人創作系統抽出來的開源框架。

