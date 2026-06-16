# 🎬 video-autopilot-kit

> 一套**框架式**的 YouTube / 短影音自動化工具 + 方法論模板。
> 給你 CapCut 自動化 + ffmpeg pipeline 的程式碼，加上一份「問卷」——
> 你回答關於**你自己頻道**的問題，它就變成屬於你的系統。
>
> ⚠️ **不含任何原作者的私人數據** —— voice / 策略 / 社群數字全部是**空白模板**，你填你的。

## 為什麼不一樣

市面上的「creator 系統」要嘛賣你**某個人的設定**（抄了對你沒用、還可能誤導），
要嘛太通用沒有方法論。這個 kit 給你**骨架**（經實戰的結構），
`SETUP.md` 一區一區**問你問題**，用你的答案填滿它 —— 這樣它才真的是**你的**系統。

## 內容

| 資料夾 | 是什麼 |
|---|---|
| ⭐ `src/capcut_helpers/` | **主力剪輯路徑** —— CapCut Desktop 自動化（草稿 I/O / 4-level 靜音 / 花字 / post-export ffmpeg / AI 字幕校正 / b-roll 占比+對位 audit / **交付前 QA `delivery_qa`：頻閃·死空檔·圖片排版·chrome 自檢 M91-M95**）。**靠 AI 助手 + Computer Use 操作 CapCut 視窗**（見下方需求）|
| `src/silent_vlog_maker/` | **次要路徑（非主力）** —— 純 ffmpeg pipeline，**只給「無口播的靜音 vlog」+ CapCut 匯出後的後製**用（內容路由 / 素材正規化 / 字幕燒錄）。平常剪輯請用 CapCut |
| ⭐ `SETUP.md` | **從這開始** —— 回答問題讓系統變成你的 |
| `templates/` | voice / 品牌 / 演算法 / 社群 的**空白填寫**模板 |
| `config.example.py` | 路徑設定範例（複製成 `config.py` 填你的，**範例不含任何帳號名**）|

## 🚀 快速開始

1. 讀 **`SETUP.md`** → 照問題把 `templates/*.template.md` 填成 `profiles/*.md`
   （或把整個 repo 丟給 Claude / ChatGPT，說「照 SETUP.md 問我問題，幫我生成 profiles/」）
2. `cp config.example.py config.py` → 填你的 CapCut / 素材 / 匯出路徑
3. **裝好 CapCut Desktop + 開啟 AI 助手的 Computer Use** —— 主力剪輯是 AI 實際操作 CapCut 視窗，**沒開 Computer Use 跑不了**（見下方需求）
4. 開始用 `src/` 的工具

## 需求

> ⚠️ **這套系統的主力是 CapCut，不是 ffmpeg。** CapCut 沒有公開 API，自動化是靠 **AI 助手透過 Computer Use 實際操作 CapCut 的視窗**（點按鈕、套模板、匯出）。ffmpeg 只負責「匯出後的後製」與「純靜音 vlog」。

**主力路徑（CapCut —— 平常都用這條）**
- **CapCut Desktop**（有 Pro 更好）—— 主要剪輯 / 套字幕 / 套模板都在這
- **AI 助手 + Computer Use**（Claude Desktop / Claude Code 等）—— ⚠️ **必需**。CapCut 自動化 = AI 透過 Computer Use 操作 GUI；**沒開 Computer Use，`capcut_helpers` 的自動化無法驅動 CapCut**
- Python 3.9+
- `ffmpeg` / `ffprobe`（在 PATH 上）—— CapCut 匯出後的後製：BGM loop / 修剪到人聲尾 / player-safe 重編

**次要路徑（純 ffmpeg —— 只做無口播靜音 vlog 才需要）**
- 只有要做「沒有口播的靜音 vlog」時才用 `silent_vlog_maker`。**這條不是主力**，一般影片請走 CapCut。

*(選用)* AI 助手（Claude / ChatGPT）也能照 `SETUP.md` 自動把你的答案生成 profiles。

## 設計理念

一套創作系統最值錢的是**結構與方法論**，不是某個人的私人數字。
所以這個 repo 給你骨架，你用自己的血肉填滿。

## License

MIT — 保留標註即可自由使用 / 修改 / 商用。

## Author

Hao0321 Studio — 從一套實戰的個人創作系統抽出來的開源框架。
