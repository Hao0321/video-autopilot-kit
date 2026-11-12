# Ops Automation — 懶人自動化經營接線指南

> 目標：頻道經營不靠「記得」。狀態機知道今天該做什麼、健檢一鍵知道系統有沒有壞、三道閘門把生產線包住；要知道今天該做什麼時，手動跑一次就好，不另外排每日自動任務。

## 四件套

1. **`src/channel_tracker.py` — 經營狀態機**
   - `data/channel_state.json`（`data/` 已在 `.gitignore`；首次把 `examples/channel_state.example.json` 複製過去）＝單一真理：每支已發布影片的 D2/D7/D28 快照排程＋待辦清單（owner/due）。
   - `python src/channel_tracker.py` → 今日到期報告；`--date` 模擬任一天。
   - 新片發布時 `add_video()` 一次，三窗快照自動排程。

2. **`src/system_health.py` — 一鍵健檢**
   - 跑全部模組 self-test＋核心檔案存在檢查 → 單一 GREEN/RED。
   - `--quick` 跳過 ffmpeg 重測試。任何大改動後跑一次。

3. **三道閘門（生產線包夾）**
   - 規劃：`src/longform_maker/plan_gate.py`（框架/機器歸屬/≥8 組包裝配對/合規/cluster 關鍵字，缺=不准動筆）
   - 腳本：`src/longform_maker/script_gate.py`（voice+觀眾語言+節奏，PASS 才錄音）
   - 交付：`src/media_delivery_qa.py` 的 `final_delivery_qa()`（全 gate 綠才出貨）

4. **按需經營檢查（不排程）**
   - 想知道今天該做什麼時，請 AI 助手跑一次 `python src/channel_tracker.py`：無到期→一行結束；有到期→機器可做的直接做（判讀／回填記錄／標 done），要人做的出 ≤5 行清單。
   - 不需要排程：狀態機本身記得到期日，跑一次只要幾秒。
   - **安全鐵則照舊**：絕不動已發布影片的標題／縮圖、絕不代發布、絕不做破壞性操作、拿不到的數據標「待截圖」不編造。

## 節奏建議

- 開工時：需要時手動跑一次 tracker（不排程）。
- 每支片：發布日 `add_video()` → D2/D7/D28 快照到期時，跑 tracker 就會列出 → 數據判讀寫回 video log。
- 每週一：手動跑一次 tracker，看上週變化＋本週到期，挑一個下一步。
- 大改動後：`system_health.py` 全跑一次。
