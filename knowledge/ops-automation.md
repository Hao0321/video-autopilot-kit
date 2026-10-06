# Ops Automation — 懶人自動化經營接線指南

> 目標：頻道經營不靠「記得」。狀態機知道今天該做什麼、健檢一鍵知道系統有沒有壞、三道閘門把生產線包住、排程巡檢每天自動跑。

## 四件套

1. **`src/channel_tracker.py` — 經營狀態機**
   - `data/channel_state.json`（首次把 `examples/channel_state.example.json` 複製成這個檔）＝單一真理：每支已發布影片的 D2/D7/D28 快照排程＋待辦清單（owner/due）。待辦依 state 裡實際出現的 owner 名稱分組列出。
   - `python src/channel_tracker.py` → 今日到期報告；`--date` 模擬任一天。state 不存在或讀壞時印 `STATE_MISSING`／`STATE_CORRUPT` 並以非 0 結束。
   - 新片發布時 `add_video(..., fmt="shorts"|"longform"|"live")` 一次，三窗快照自動排程；同名或同 `video_id` 直接拒絕（請更新原紀錄）。沒有 `format` 的舊紀錄回報為 `format_unknown`，不進任何基準。
   - 回填數據用 `record_metrics(..., window, captured_on="讀取日", 欄位=數值)`：窗只收 D2/D7/D28；同窗再錄是合併、不會清掉先前欄位；布林、文字、NaN/inf 直接拒收。讀取日要落在到期日起 D2 +1／D7 +2／D28 +4 天內，過早、過晚或沒有日期的值照樣保存，但 `outcome_learning.py` 不拿來算基準，並列在 `data_quality.excluded`。基準只比同平台＋同 format＋同窗，樣本數算不重複的 `video_id`。
   - 會改檔的程式用 `with channel_tracker.edit_state() as st:`（鎖檔＋原子寫入），不要自己 load 再 save。`outcome_learning.py refresh` 遇到缺檔／壞檔回 `STATE_MISSING`／`STATE_CORRUPT`（exit 1），不覆寫既有 playbook。

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
