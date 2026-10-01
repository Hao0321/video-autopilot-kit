# Capability obligation audit

用於多回合產品、跨平台應用與使用者問「還缺什麼」時。這是 read-only semantic audit；Cleanup 不替產品決定需求，也不修改 ledger。

## Canonical source

先找 repository 明確宣告的 machine-readable capability ledger，例如 `product-capabilities.json`。不得從 README、聊天摘要、測試數量或目錄名稱反推「全部需求」。若沒有 ledger，回報 `NOT_CHECKED capability-obligation-unconfigured`，交由已獲實作授權的 orchestrator 建立；audit-only 任務則停在報告。

Ledger 至少要能表達：

- stable obligation ID 與人類可讀名稱；
- `verified`、`blocked_external`、`planned`、`unmeasured` 等不混淆的狀態；
- `internal`、`public`、`parity` 等完成 scope；
- verified 的產品版本與可重跑 evidence；
- external blocker 的 owner、condition、next action；
- planned／unmeasured 的 next experiment；
- required obligation ID closed-world list，刪除一項也必須被 gate 偵測。

## Audit procedure

1. 執行 ledger 自帶的 project-native self-test與 gate；若沒有，標 `NOT_CHECKED`，不要用 Cleanup regex 代替產品語意。
2. 負向 fixture 至少覆蓋 missing obligation、duplicate ID、version drift、stale verification、missing evidence、incomplete blocker 與 private path。
3. 對本次宣告的 scope 執行 gate。`internal` 綠燈不可寫成 `public` 或 `parity` 完成。
4. 隨機抽查一項 verified evidence 是否真的存在且可重跑；靜態檔案存在不等於行為證據。
5. 將 open obligations 依狀態回報。外部憑證／裝置／權利人決策不得被自動改成 verified。
6. 對跨 Skill／Agent／MCP／runtime／installer／人審／發布的義務，要求同一 source revision/hash 的版本化 handoff 與真實 journey。檔案、模組或工具各自存在不能作為這類 obligation 的唯一 verified evidence；細節讀 `cross-system-integration-audit.md`。
7. 對 batch／queue／mass-production 義務，先區分 multi-import、單一時間軸組片與真正 fan-out。後者必須用 closed-world source/group → stable job → editable project → render → receipt 對應，驗證隔離失敗、逐支重試、重啟續跑、來源處理前後 hash 與 open-in-editor；N 個來源只得到 1 個專案或成片時不得標 batch verified。
8. 對自動剪輯／動態圖卡義務，把「可編輯 graph 存在」與「最終編碼後肉眼可見且語意正確」拆開。Verified evidence 必須抽查宣稱時段的 decoded frames、safe-area／可讀性與跨取樣穩定度，並證明 domain-defined evidence ranges（例如耐久賽的持續旋轉、沉默等待、結果確認）未被通用 silence／low-motion 規則誤刪；只列 graphic／track ID 或保留時間長度不足以關閉義務。
9. 對單一長來源拆 Shorts／Reels，來源 cardinality 與 editorial-unit cardinality 必須分開。先凍結由獨立證據或人工標註產生的 deliverable map（每單位含 promise、setup、payoff 與來源範圍），再驗證 `1 source → N semantic units → N editable projects → N decoded renders → N receipts`。舊系統成片與候選成片只能是 benchmark observations，不能互相充當 ground truth。若輸出單一合輯、遺失單位、重用同一 source range、或 recut fingerprint 未改變，回報 false green。

Cleanup 的程式架構 PASS 與 capability gate 是兩個獨立量尺；任一 `NOT_CHECKED` 都保持可見。

另檢查 claim granularity：可執行的功能整合與真實世界品質驗收必須拆成不同 obligation。若功能只在單一 fixture 可用，產品卻宣稱多語言、多裝置、大規模或人工品質，沒有獨立 corpus／acceptance evidence 的較強宣稱一律回報 `NOT_CHECKED`。

市場領先還要再拆成「comparison instrument 可用」與「claim cells 已量測」。前者可以 verified，後者在 baseline×surface 矩陣未閉合前必須維持 `unmeasured`；0 個實測 cell 的誠實 gate 不得被摘要為贏過競品。

若另有細粒度 Skill→產品能力矩陣，必須使用 stable IDs 與 closed-world required list，且將 `native verified`、`contract enforced`、`orchestrator handoff`、`unmeasured`、`blocked external` 分開。Legacy schema 可保留相容，但不得算 current workflow closure；需在 receipt／flow 明示 current schema，並對缺少必要語意欄位建立負向 fixture。免費社群散布仍是 public redistribution scope，owner-only 內部素材不可因售價為零而升格。
