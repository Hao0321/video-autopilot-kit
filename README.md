# 🎬 video-autopilot-kit

> 一套**框架式**的 YouTube / 短影音自動化工具 + 方法論模板。
> 給你純程式 ffmpeg pipeline + CapCut 自動化的程式碼，加上一份「問卷」——
> 你回答關於**你自己頻道**的問題，它就變成屬於你的系統。
>
> ⚠️ **不含任何原作者的私人數據** —— voice / 策略 / 社群數字全部是**空白模板**，你填你的。

## 🧭 我該走哪條路？（3 秒決策樹）

- **用 Mac / Linux？** → **Path 1 Programmatic**（純程式，跨平台，不碰 CapCut）
- **要 CapCut 的特效 / 花字 / 雲端模板？** → **Path 2 CapCut-assisted**（Windows 優先；**版本敏感**，先看 [TROUBLESHOOTING](TROUBLESHOOTING.md) 的版本相容矩陣）
- **只想全自動、不想開任何 GUI？** → **Path 1 Programmatic**

## ▶️ 60 秒看它跑（不用 CapCut、不用真素材）

想先看它**真的會動**？`examples/` 裡有自包含、可直接跑的 demo —— 用 ffmpeg 合成測試素材，不需要任何真實影片或 CapCut：

```bash
python examples/01_vertical_short.py      # 合成素材 → 完整 1080x1920 直式 Short
python examples/02_caption_broll_match.py # 零設定：b-roll 用內容命名就自動對位字幕
```

需求：Python 3.9+ 與 `ffmpeg`/`ffprobe`（只有 example 01 需要 ffmpeg）。細節見 [`examples/README.md`](examples/README.md)。

## 為什麼不一樣

市面上的「creator 系統」要嘛賣你**某個人的設定**（抄了對你沒用、還可能誤導），
要嘛太通用沒有方法論。這個 kit 給你**骨架**（經實戰的結構），
`SETUP.md` 一區一區**問你問題**，用你的答案填滿它 —— 這樣它才真的是**你的**系統。

## 🤖 v0.9 新增 — 經營自動化（ops autopilot）

拍片只是一半，另一半是「經營不靠記得」：

- **`src/channel_tracker.py`** 狀態機：每支片 D2/D7/D28 快照自動排程＋待辦追蹤，一鍵「今天該做什麼」
- **`src/system_health.py`** 一鍵健檢：全模組 self-test + 核心檔案，單一 GREEN/RED
- **三道閘門**：`plan_gate`（規劃：包不出 8 組標題×縮圖=砍題）→ `script_gate` v2（腳本：voice+觀眾語言+節奏）→ `delivery_qa`（交付）
- 接線指南＋每日 AI 排程巡檢範本 → `knowledge/ops-automation.md`；爆款定義框架 → `knowledge/viral-playbook-framework.md`

## 內容 —— 兩條 first-class path

這個 kit 有**兩條同等地位的路**，不是「主力 vs 次要」：

| 路徑 | 模組 | 是什麼 | 平台 |
|---|---|---|---|
| ⭐ **Path 1 — Programmatic**（推薦採用者預設） | `src/longform_maker/` | **教學長片模組** —— `fx_lib` premium 動態引擎（亞像素 Ken Burns / 雙層 bloom / light sweep / easing / 合成 SFX）、`word_captions` 字級時間字幕（M105）、`screen_clean` 螢幕錄影機械化清理（M104）。參數真值 → `knowledge/premium-motion-fx.md` | Win / Mac / Linux |
| ⭐ **Path 1 — Programmatic** | `src/silent_vlog_maker/` | **純 ffmpeg pipeline** —— 直式 Shorts（多色字幕 / BGM 高光起點 / 正規化）、靜音 vlog、素材清理 | Win / Mac / Linux |
| ⭐ **Path 1 — Programmatic** | `src/capcut_helpers/` 的 **QA gates** | **交付前機械化 QA**（`delivery_qa`：頻閃·死空檔·caption-sync·全幀掃描 M91-M95 / `broll_audit` 占比 / `caption_broll_matcher` 對位）—— 純 ffmpeg/Python，**不需要 CapCut**，兩條 path 的成品都該過這關 | Win / Mac / Linux |
| **Path 2 — CapCut-assisted**（作者本人主用） | `src/capcut_helpers/` 其餘 | **CapCut Desktop 自動化** —— 草稿 JSON 直改（draft I/O / 4-level 靜音 / 花字 / AI 字幕校正）+ **AI 助手 + Computer Use 操作 CapCut 視窗**（套模板 / 匯出）。**版本敏感** → [TROUBLESHOOTING](TROUBLESHOOTING.md) | Windows-first |
| 共用 | `knowledge/` | **影片製作知識庫** —— M1-M110 避坑大全 + 演算法 + SOP + 剪輯心法 | — |
| 共用 | ▶️ `examples/` | **自包含可跑 demo** —— ffmpeg 合成素材，60 秒看 pipeline 真的動（不用 CapCut/真素材）| — |
| 共用 | ⭐ `SETUP.md` | **從這開始** —— 回答問題讓系統變成你的 | — |
| 共用 | `templates/` | voice / 品牌 / 演算法 / 社群 的**空白填寫**模板 | — |
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

