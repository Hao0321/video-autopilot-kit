# Mode B：Repo audit

用於 release 前、私公版同步與 skill 交接。先確認目標是否為 Git repo，以及是否存在 `audit.config.json`。

## 五個維度

5. **私公版 sync**：只依 `sync.public_root` 與 allow／ignore 設定比較，不猜路徑。未設定或路徑不存在回報 `NOT_CHECKED`。
6. **Release 一致性**：比較 Git tag 與 README／CHANGELOG 的最新 semver。目標不是 repo 時不假裝通過。
7. **Cross-link**：檢查相對 Markdown 連結。外部 URL 預設不打網路，需使用者要求才另查。
8. **版本與事實漂移**：自動比較 R1–RN、F1–FN、Cases 1–N 與實際最大 ID；專案特有事實用 `drift_assertions`。
9. **Skill／handoff 健檢**：檢查 frontmatter、`agents/openai.yaml`、長 reference 的導航與 privacy token。

## 執行

```powershell
$env:PYTHONUTF8='1'
python scripts/audit.py <target> --mode b
python scripts/check_links.py <target>
python scripts/check_drift.py <target>
python scripts/check_sync.py <target>
```

`check_sync.py` exit code：0=同步、1=有差異、3=未能檢查。完整 audit 的 0 預設代表程式成功執行，不代表零發現；CI 要以 FAIL 中止時加 `--strict`。

## 修改閘門

Audit 本身永遠 read-only。報告後列出最小修復順序，等待使用者明確確認；確認範圍之外不改、不 commit、不 push、不 publish release。
