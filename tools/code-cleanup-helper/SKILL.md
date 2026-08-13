---
name: code-cleanup-helper
description: 以跨平台、read-only 審計器掃描 codebase、prompt、SKILL.md 與 repository，建立 Python 依賴圖並找循環依賴、分層違規、責任熱點、重複函式、過長函式／檔案、命名漂移、私公版 sync、release、broken links、skill metadata 與隱私外洩。使用者說「清理 code」「分析架構」「依賴圖」「找重複」「重構」「skill 太長」「audit repo」「私公版 diff」「版本對齊」「release 前盤點」「規則漂移」時使用。
---

# Code Cleanup Helper

以可重複執行的 Python 審計取代臨時 Bash 指令。支援 Windows、macOS、Linux；所有檔案以 UTF-8 讀取。

## 硬規則

- Audit 永遠 read-only。
- 永遠先報告，再等使用者明確確認修復範圍。
- 未能執行的維度標 `NOT_CHECKED`，不包裝成通過。
- 不改 `.git/`、測試／CI、license、package metadata，除非使用者明確把它們放進修復範圍。
- 不 commit、push、force reset、publish release。

## 路由

| 使用者意圖 | Mode | 讀取 |
|---|---|---|
| 重複、命名、架構、依賴、模組、函式／檔案太長 | A | `references/mode-a.md` |
| sync、release、link、drift、handoff | B | `references/mode-b.md` |
| 完整健檢 | A+B | 兩份都讀 |
| 要設定例外／機器報告 | 任一 | `references/config-and-report.md` |

## 標準流程

1. 解析目標絕對路徑；確認存在，不猜 repo。
2. 執行審計器。Windows 先設 `PYTHONUTF8=1`。
3. 讀 JSON 證據或人類摘要；需要 semantic 判斷時再讀相關檔案。
4. 回報 FAIL、REVIEW、NOT_CHECKED、影響與最小修復順序。`REVIEW` 是提醒人工判斷，不是阻擋。
5. 停下等待確認。使用者回「全做／執行／做」後，才在已報告範圍內修改。
6. 修完重跑相同 audit；不能只靠肉眼說完成。

```powershell
$env:PYTHONUTF8='1'
python scripts/audit.py <target> --mode all
python scripts/audit.py <target> --mode all --format json
python scripts/audit.py <target> --mode architecture --format json
```

只有 CI 或使用者要求 fail-fast 時加 `--strict`。預設 exit 0 只代表 audit 成功跑完。

## 專用檢查器

```powershell
python scripts/check_links.py <target>
python scripts/check_drift.py <target>
python scripts/check_sync.py <target>
python scripts/self_test.py
```

## 報告格式

用短表格輸出：

| 狀態 | 維度 | 發現 | 證據 | 建議 |
|---|---|---|---|---|

只列最高優先的 3–10 筆；完整清單留在 JSON。結尾必須是單一 next action，例如「回『修 P0』後我才修改」。

## 判讀邊界

- Exact duplicate、Python import cycle、設定式 layer violation、broken link、ID range、sync diff 可由 script 判定。
- 超過 severe 門檻才是 `FAIL`；warning 至 severe 之間是 `REVIEW`。不要為了消除提醒而機械式拆函式。
- 例外必須含 path、function name、max lines、理由、到期日；例外仍顯示為 `REVIEW`，不會隱藏技術債。
- Semantic duplicate、架構是否值得抽象、公開文件是否講清楚，必須由 agent 讀上下文判斷。
- 動態 import、執行期 service lookup、跨語言呼叫與資料流責任不在 Python AST 圖內；未另查不得宣稱完整架構通過。
- PASS 數量不等於架構最優。若理應存在的依賴邊沒有出現在圖上，先把它當量測失敗；用 `required_dependencies` 加正／負 fixture，修解析器後才繼續產品重構。
- 平台／API／法律等時效事實不靠本地 regex 宣稱正確；需要時另查權威來源。

## 維護

- 新的 deterministic 檢查先加到 `scripts/audit_core.py`，再補 `self_test.py`；量測本身沒有對應 fixture 時不得拿來阻擋重構。
- 子目錄可直接執行的 Python script 常用 bare sibling import；解析時先保留真正 top-level absolute import，再 fallback 到同目錄 module。兩種情境都必須有 fixture，避免修一邊壞另一邊。
- Cleanup 也必須檢查「檢查器的計分與輸出合約」：新增／移除 gate 後，分數分母必須由實際 max points 計算；宣稱 JSON 的 CLI 只能輸出一份可解析文件。任何會製造假滿分、吞掉失敗或污染 JSON 的問題都先修量尺、補回歸測試，再繼續產品開發。
- 專案特有事實放目標 repo 的 `audit.config.json`，不要 hardcode 到通用引擎。
- `agents/openai.yaml` 改動後重新跑 skill-creator 的 `quick_validate.py`。
