# 模型、推理等級與 Context 契約

## 核心原則

不同模型與 reasoning effort 可能改變規劃深度、指令遵循、延遲與成本，但模型名稱不是品質證明。任何模型 × 推理等級只有在相同素材、brief、Skill revision、context packet、evaluator 與硬體／服務條件下完成可重跑評測後，才可標成 `measured`；官方定位只能用來設定初始路由，不能冒充 Editkin 的比較結果。

## Markdown 與 JSON 的分工

- Markdown 適合短而有層級的語意路由：目標、素材摘要、選中的規則、不可違反條件與判斷順序。它提高可讀性與注意力配置，不會單獨保證準確。
- JSON 是唯一可執行真相：schema、時間碼、command、asset hash、model／effort provenance、限制、狀態與 receipt 都必須結構化驗證。
- 每次 Build 只產生 bounded Markdown router；保存其 SHA-256，並在 `edit-plan/v4` 驗證與 JSON contract 相符。禁止把整本 Skill、全部記憶或素材庫全文塞入 prompt。
- 人類規則、JSON schema、負例 gate、執行收據與語意複核共同決定可靠性；把相同規則同時散落在 prompt、UI、程式與 installer 會造成漂移。

## 預設路由（尚未量測時）

以下只是依官方產品定位建立的安全起點，狀態固定為 `official_positioning_only_quality_unmeasured`：

- 大量低風險分類、摘要與候選排序：Luna `medium`。
- 一般 rough cut、常規組裝與互動操作：Terra `medium`。
- 敘事、Hook、節奏、標題／縮圖假設與 editorial plan：Sol `medium`。
- 關鍵品質複核、發佈前 audit、複雜錯誤修復：Sol `high`；只有 frozen benchmark 證明額外收益時才升 `xhigh`／`max`。

若指定的模型／effort 不可用，系統必須重新產生 route receipt，不能默默降級。`low`／`none` 可用於 latency-sensitive 候選工作，但不得因此跳過 current schema、素材權利、真實性、安全或語意 audit。

## `edit-plan/v4` 必填來源

每個 plan 必須記錄：

- provider、model ID、model tier、reasoning effort；
- task class、quality priority、route policy ID；
- bounded Markdown router hash 與 JSON contract schema；
- workflow run ID、workflow contract hash、project revision、真實 source hashes 與 material／semantic receipts；
- plugin registry manifest hash、獲選 capability 與編譯進 plan 的 atomic commands；
- evaluation state、suite／receipt（若 measured）；
- safeguards 與第二次語意複核要求。

任何 `unmeasured` cell 都不得 `direct_apply`。editorial、quality-critical、audit 或 publish-adjacent 工作至少進第二個語意 pass；被 audit 拒絕時只准依 rejection 修復一次，再失敗就交 Hao 審查，禁止循環燒 Token。

## 評測與升級

1. 凍結代表性 longform／shorts／reels 素材、brief 與 ground truth。
2. 同一批資料逐格測 Sol／Terra／Luna × `none|low|medium|high|xhigh|max`；不可拿不同專案結果橫比。
3. 同時計錄 schema adherence、semantic rejection、editorial blind score、修復次數、Token、延遲與成本。
4. 每一個 measured cell 必須綁定 suite ID、evaluator SHA、raw evidence 與 promotion receipt；資料不足維持 `unmeasured`。
5. 每次 Skill、模型版本、schema、evaluator 或選中記憶規則變更後，相關 cell 失效並重跑。
