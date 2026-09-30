# 參與 video-autopilot-kit

歡迎提出功能、修正、文件、測試與審查。完整分工與邀請規則見 [團隊協作計畫](COLLABORATION.md)。

## 開始一項貢獻

1. 先找現有 Issue，或使用 [任務表單](https://github.com/Hao0321/video-autopilot-kit/issues/new?template=task.yml) 說明目標、範圍與驗收條件。
2. 社群貢獻者 fork；Write 協作者在工作分支開發。
3. 提交一個範圍明確的 PR，填寫變更與驗證證據，等待 CI 與維護者審查。
4. 合併 main 後才納入正式程式碼；正式 Release 由維護者另行發布。

AI 輔助貢獻也需要作者讀過 diff、理解行為並提供真實測試結果。PR 中說明 AI 協助範圍，移除未經確認的引用與不必要的檔案。

## 在哪裡改檔案

- 功能程式通常在 `src/`；方法論與說明在 `knowledge/`、`docs/`；任務與 GitHub 流程在 `.github/`。
- `codex-skill/` 與 bundled tools 有 canonical 同步與 receipt 邊界。相關變更請先在 Issue 說明來源；不要手動修改 receipt 來繞過失敗。維護者負責整合同步。
- `.github/` 的協作文件不包含在使用者的 Release 安裝包內。
- 保留 Python 3.9+、Windows／macOS／Linux 的相容性；新增依賴必須說明必要性與授權。

## 驗證

先讀 [安裝指南](../SETUP.md)，使用合成或已去識別化的測試資料。依改動選擇相關檢查，例如：

```text
python tools/code-cleanup-helper/scripts/check_links.py . --config audit.config.json
python tools/code-cleanup-helper/scripts/check_drift.py . --config audit.config.json
python scripts/public_privacy_gate.py --self-test --repository .
python scripts/sync_canonical.py --verify-receipt --repository .
python src/architecture_gate.py audit
python src/system_health.py --quick
python src/release_manager.py selftest
```

PR CI 會在三種作業系統與兩個 Python 版本驗證，另有可重現建置檢查。測試通過只代表已覆蓋的條件；未測的環境、資安或媒體品質應如實列出。

## 隱私與安全

不要提交 `config.py`、`profiles/`、`projects/`、頻道後台資料、客戶資訊、未公開影片、API key／token、session 紀錄或帶存取權限的遠端審片連結。範例使用虛構資料，證據先去識別化。

安裝／更新、執行外部指令、網路傳輸、依賴、workflow、發布、隱私或授權相關改動，請在 PR 勾選安全相關變更並說明影響。漏洞回報依 [安全政策](SECURITY.md) 使用私密入口。

## 授權與署名

本儲存庫使用 [MIT 授權](../LICENSE)。請只提交自己有權提供的程式碼、文件與素材；第三方內容須保留授權與來源。貢獻沿用 MIT，不要求轉讓版權。不要為了貢獻新增股權或分潤承諾。

提交作者與合併 PR 是主要紀錄；共同作者在取得同意後使用 `Co-authored-by`，可採 GitHub noreply email。設計、測試與審查工作也可在 PR 中署名。
