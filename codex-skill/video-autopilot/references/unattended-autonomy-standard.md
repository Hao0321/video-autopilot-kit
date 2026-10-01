# 無人值守剪輯標準

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
