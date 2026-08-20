# Mode A：Cleanup audit

用於 codebase、prompt、SKILL.md 與 reference 的結構清理。Audit 只掃描與報告；單獨診斷時等待修復授權，R&D 已獲明確修改授權時則把證據交回 orchestrator。

## 五個維度

1. **重複內容**：找跨檔案相同長段落。相同邏輯不同措辭仍需人工判讀，不把 keyword 高頻直接當 bug。
2. **命名一致性**：檢查 R／F／Case 等永久 ID、重複 heading、同概念多種名稱。
3. **可抽模組**：以重複段落、共用 schema、重複 CLI 流程為候選；沒有第三次使用就不要硬抽象。
4. **檔案長度**：預設警告線如下，可由 `audit.config.json` 覆寫。
5. **架構依賴**：以 Python AST 建立內部 import graph，檢查 SCC 循環、設定式 layer violation、禁止依賴、fan-in／out 熱點、長函式與跨檔案相同函式 body。

| 類型 | 警告 | 嚴重 |
|---|---:|---:|
| SKILL.md | 200 | 400 |
| references/*.md | 400 | 800 |
| .py／.js／.ts | 500 | 1,000 |

函式採三態判級：warning 以下不報、warning 到 severe 為 `REVIEW`、超過 severe 才為 `FAIL`。`REVIEW` 不阻擋交付；先讀責任、分支與測試再決定是否拆分。

## 執行

```powershell
$env:PYTHONUTF8='1'
python scripts/audit.py <target> --mode a
python scripts/audit.py <target> --mode architecture --format json
```

需要完整證據時改用 `--format json`。只有 CI／明確要求 exit code 時才加 `--strict`。

## 判讀

- `PASS`：有執行且通過。
- `FAIL`：有可定位的問題，不代表可以自動修改。
- `REVIEW`：超過提醒線或有期限例外，需要人工判斷，但不是硬性失敗。
- `NOT_CHECKED`：缺少 repo、設定或外部能力；不得寫成通過。
- 重複偵測只抓 exact normalized paragraph；semantic duplicate 仍由 agent 讀上下文判斷。
- 架構報告的 `architecture.edges` 是可重現證據；layer 規則必須來自目標 repo 的 `audit.config.json`，通用工具不得猜層級。
- 動態 import、plugin registry、subprocess 與跨語言依賴回報 `NOT_CHECKED` 或由人工補查，不得用 AST 綠燈宣稱整套架構正確。
