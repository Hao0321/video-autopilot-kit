# Editkin Plugin Automation

只在 Editkin Build 需要尋找可重用工具、效果、轉場、分析器或素材／知識包時讀本頁。目標是讓 Skill 動態使用已安裝能力，不把外掛目錄灌進 context，也不讓外掛先於主計畫改動專案。

## 低 Token 呼叫順序

1. 所有素材的語意 receipt 完成後，呼叫 `list_installed_plugins`，預設 `automationReadyOnly=true`；可用 `kind` 限縮效果、轉場、分析或 workflow tool。一次 run 只掃一次 registry，並保存 manifest SHA-256。
2. 依 `semanticRoles`、`formats` 排除無關候選。每個剪輯意圖最多深讀三個候選，避免把整個 registry 載入 context。
3. 對候選呼叫 `get_plugin_capability`，檢查 `requires`、`avoidWhen`、權限、參數與 `automationReady`。缺逐鏡前提時不用。
4. 把選中的 capability、參數、manifest SHA-256 與預期 EditGraph command 編譯進同一份 `edit-plan/v4`；此階段只規劃，不得先呼叫會改專案的 tool。
5. `audit_autopilot_plan` 通過後，外掛 command 與其餘剪輯 command 由 `apply_autopilot_plan` 一次原子提交；receipt 必須綁 plugin/version、capability、manifest SHA-256、plan SHA-256 與 project revision。
6. 重新 preview／render 並走既有技術 QA 與人工審片。工具呼叫 GREEN 只證明操作成功，不證明畫面好看。

## Readiness 語意

- `AUTOMATION_READY`：可由 Skill 透過受限 EditGraph command 原子套用並 Undo。`gpu_effect_graph` 與 `gpu_effect_module` 只有 resident DX12 預覽、獨立畫素 oracle、正式輸出同源序列與負向安全 gate 全綠，而且作者宣告 `assisted`／`full` 時才屬此級；module 必須先確定性編譯到既有 runtime ABI，不能把作者原始碼直接送入 GPU。
- `RUNTIME_READY`：可人工套用但不可由 Skill 自動執行；包括作者宣告 `manual`，或只有檔案／ABI 可載入、尚未證實完整產品路徑的能力。
- `MANUAL_ONLY`：作者要求人工操作。
- `BLOCKED`：平台、hash、manifest、資源或安全驗證失敗。

未知參數、超界值、重複外掛 ID、越過外掛根目錄、library hash 不符、不支援的 command、GPU binding 缺失／孤兒、identity／parameters／program hash 漂移、未知 opcode、單一 graph 超過四個 operations、同片超過四個 GPU graphs、合計超過十六個 operations、順序 receipt 不一致或 CPU/GPU runtime 混用都要 fail-closed。不得改用 Computer Use 繞過 readiness；只有該能力完全沒有結構化介面、且工作本身已獲授權時，才可走既有有界 GUI fallback。

外掛平台／商城只負責發現、下載、授權與販售；本流程只依本機已安裝 manifest 工作，不假定中心化網站存在，也不把開源／付費模式寫死。
