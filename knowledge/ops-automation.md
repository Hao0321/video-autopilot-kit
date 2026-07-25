# Ops Automation — 懶人自動化經營接線指南

> 目標：頻道經營不靠「記得」。狀態機知道今天該做什麼、健檢一鍵知道系統有沒有壞、三道閘門把生產線包住、排程巡檢每天自動跑。

## 四件套

1. **`src/channel_tracker.py` — 經營狀態機**
   - `channel_state.json`（repo root；首次用複製 `examples/channel_state.example.json`）＝單一真理：每支已發布影片的 D2/D7/D28 快照排程＋待辦清單（owner/due）。
   - `python src/channel_tracker.py` → 今日到期報告；`--date` 模擬任一天。
   - 新片發布時 `add_video()` 一次，三窗快照自動排程。

2. **`src/system_health.py` — 一鍵健檢**
   - 跑全部模組 self-test＋核心檔案存在檢查 → 單一 GREEN/RED。
   - `--quick` 跳過 ffmpeg 重測試。任何大改動後跑一次。

3. **三道閘門（生產線包夾）**
   - 規劃：`plan_gate.py`（框架/機器歸屬/≥8 組包裝配對/合規/cluster 關鍵字，缺=不准動筆）
   - 腳本：`script_gate.py`（voice+觀眾語言+節奏，PASS 才錄音）
   - 交付：`delivery_qa.py`（全 gate 綠才出貨）

4. **排程巡檢（把 AI 排成鬧鐘）**
   - 用你的 AI 助手排每日排程任務，prompt 核心：
     「跑 `python src/channel_tracker.py`；無到期→輸出一行結束；有到期→機器可做的直接做（判讀/回填記錄/標 done），要人做的出 ≤5 行清單；週一加週報。」
   - **安全鐵則寫死進 prompt**：絕不動已發布影片的標題/縮圖（浪上紀律）、絕不代發布、絕不做破壞性操作、拿不到的數據標「待截圖」不編造。

## 節奏建議

- 每日：巡檢自動跑（人只看卡片）。
- 每支片：發布日 `add_video()` → D2/D7/D28 快照到期自動提醒 → 數據判讀寫回 video log。
- 每週一：自動週報（上週變化＋本週到期＋一個建議）。
- 大改動後：`system_health.py` 全跑一次。
