# Mode A：Cleanup audit

用於 codebase、prompt、SKILL.md 與 reference 的結構清理。Audit 只掃描與報告；單獨診斷時等待修復授權，R&D 已獲明確修改授權時則把證據交回 orchestrator。

## 五個維度

1. **重複內容**：找跨檔案相同長段落。相同邏輯不同措辭仍需人工判讀，不把 keyword 高頻直接當 bug。
2. **命名一致性**：檢查 R／F／Case 等永久 ID、重複 heading、同概念多種名稱。
3. **可抽模組**：以重複段落、共用 schema、重複 CLI 流程為候選；沒有第三次使用就不要硬抽象。
4. **檔案長度**：預設警告線如下，可由 `audit.config.json` 覆寫。
5. **架構依賴**：以 Python AST 建立內部 import graph，檢查 SCC 循環、設定式 layer violation、禁止依賴、fan-in／out 熱點、長函式與跨檔案相同函式 body。
6. **跨元件狀態語意**：追查同一衍生概念（例如是否已有真實輸入、目前流程步驟、能否交付）在各 call site 的判斷是否一致。Fixture、demo、placeholder 或 seed data 不得在部分元件被當成使用者資料、在另一部分卻被排除；這類候選需用狀態矩陣與 runtime 負向測試確認，不由字串掃描直接判成 bug。

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
- D3 對「三次以上 exact 跨檔案重用」輸出 deterministic PASS／REVIEW，讓 closed-world gate 能分辨已檢查與未檢查；共用 schema、相似 CLI 流程等 semantic 候選仍需人工閱讀，不可由 D3 PASS 推論不存在。
- 架構報告的 `architecture.edges` 是可重現證據；layer 規則必須來自目標 repo 的 `audit.config.json`，通用工具不得猜層級。
- 動態 import、plugin registry、subprocess 與跨語言依賴回報 `NOT_CHECKED` 或由人工補查，不得用 AST 綠燈宣稱整套架構正確。Audit 會盤點 JavaScript／TypeScript、Rust、C／C++、Swift、Kotlin、Java 與 Go 來源檔；只要存在這些檔案，就以 `cross-language-architecture-not-checked` 和逐語言檔案數保留量測邊界，即使同一 repo 的 Python 圖已通過。
- 跨元件狀態語意檢查至少列出衍生概念、來源資料、各 consumer 與預期狀態。若只能看到靜態 call site 而沒有 runtime／journey 證據，回報 `REVIEW` 或 `NOT_CHECKED`，不得因單一元件判斷正確就宣稱整條 UX 流程一致。
