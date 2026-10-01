# video-autopilot 團隊協作計畫

## 現階段的分工

儲存庫由 Hao0321 管理。社群透過 Issue、fork 與 Pull Request（PR）參與；需要持續開發的團隊夥伴，再由 Hao 邀請成為協作者。

| 角色 | 工作方式 | 權限與責任 |
| --- | --- | --- |
| 社群貢獻者 | fork → 分支 → PR | 不需要協作者邀請；可提出功能、修正、文件與測試證據 |
| 團隊開發者 | 儲存庫內的工作分支 → PR | Write；可推送工作分支，正常流程須取得 Hao 的審核才可合併 main |
| 資安／品質夥伴 | 審查 PR、提供重現方式與修補建議 | 先透過 PR 與私密漏洞回報合作；持續開發時再授予 Write |
| 維護者 Hao0321 | 任務排序、審核、合併與正式發布 | 管理邀請、撤銷存取、main 保護與版本標籤 |

這是個人帳號的儲存庫：協作者沒有可單獨選擇的 Read、Triage、Maintain 等級。若未來需要獨立的團隊權限、審查職責與管理者分級，再規劃遷移至 GitHub Organization。

## 邀請順序

1. 先完成一個小型 PR，確認夥伴能遵守隱私邊界、提供驗證證據並回應審查。
2. 經常參與開發的團隊夥伴由 Hao 授予 Write；邀請前確認 GitHub 帳號本人，建議開啟雙因素驗證。
3. 初期由 Hao 擔任所有檔案的 Code Owner。邀請不代表取得管理權、所有權或主分支繞過權限。
4. 團隊擴大後再決定模組負責人；變更 CODEOWNERS 本身也需要 Hao 審核。

Hao 可以撤銷協作者存取，但已經下載的公開程式碼仍可依 MIT 授權使用。撤銷權限不會消除既有提交、fork、發布檔案或已發生的外洩；出現事件時應檢查紀錄，並撤銷受影響的憑證。

### 第一批任務建議

先檢查現有 Issue，選一項開任務；下列分工是建議，不代表已指派任何人或承諾交付日期。

| 方向 | 第一個任務 | 驗收證據 |
| --- | --- | --- |
| 開發夥伴 | 以乾淨、隔離的環境走一次公開安裝流程，改善遇到的一個問題 | 版本、環境、重現步驟；若有修正，附修正前後的結果 |
| 資安夥伴 | 審查安裝／更新的一個輸入邊界，例如來源 URL 或路徑處理 | 具體行為、受影響位置、去識別化重現與修補建議；漏洞先私密回報 |
| 創作者／QA | 用合成素材或已有公開授權的素材，重現一個字幕或剪輯問題 | 預期／實際畫面、最小步驟與素材來源；不提交未公開影片 |

第一個 PR 完成後再擴大任務。敏感核心的合併與版本發布由 Hao 維護。

## 每一項工作的流程

1. **開任務**：使用 [任務表單](https://github.com/Hao0321/video-autopilot-kit/issues/new?template=task.yml)，寫清楚目標、範圍、驗收條件與驗證方式。
2. **領任務**：在 Issue 留下承接範圍，由維護者協調避免重工。AI agent 也遵循同一份驗收條件。
3. **開分支**：例如 `feat/123-caption-timing`、`fix/124-path-handling`、`docs/125-setup`。每個 PR 聚焦一個可檢查的問題。
4. **提交 PR**：連結 Issue，說明變更、實際驗證結果、風險與回復方式。不要將尚未執行的測試寫成通過。
5. **檢查與審核**：CI 通過、所有討論解決、Hao 審核通過後才能依正常流程合併 main。新增提交會撤銷舊的核准；最後推送者不能核准自己的最新變更。
6. **合併與紀錄**：維護者確認驗收條件後合併；保留 PR、提交作者與驗證證據。
7. **正式版本**：Hao 確認 main 與版本號，建立 `v*` 標籤，經 Release workflow 的檢查與可重現建置發布。合併 PR 不會自動變成正式 Release。

## 邀請前必須生效的保護

- main 要求 PR、1 位核准、Code Owner 審查、最新提交重新核准與討論解決。
- main 禁止強制推送與刪除，並要求分支更新至 main 及以下 7 個 GitHub Actions 檢查通過：
  - `verify (ubuntu-latest, 3.9)`
  - `verify (ubuntu-latest, 3.12)`
  - `verify (windows-latest, 3.9)`
  - `verify (windows-latest, 3.12)`
  - `verify (macos-latest, 3.9)`
  - `verify (macos-latest, 3.12)`
  - `reproducible-release`
- `.github/CODEOWNERS` 指定所有檔案由 `@Hao0321` 審核；必須合併到 main 才生效。
- `v*` 版本標籤的建立、更新與刪除限定規則中的 Hao0321 繞過者。
- PR CI 使用 GitHub 託管 runner、唯讀 token 與固定 SHA 的 Actions，不在 checkout 中保留 GitHub 憑證。
- 漏洞透過 GitHub 的私密回報入口處理。

保留儲存庫擁有者的緊急繞過能力。正常工作仍走 PR；緊急繞過時應記錄原因、採取的變更及後續驗證，並補上可追溯的 PR 或事件紀錄。

### Write 權限的實際界線

GitHub 個人儲存庫的 Write 協作者可以管理 Releases。main 與標籤保護能限制程式碼合併和版本標籤，**不能完全禁止 Write 協作者修改 Release 說明或資產**。授予 Write 代表信任其共同維護發布內容；若需要讓開發者完全無法操作正式發布，應先設計獨立的發布儲存庫及其存取權限，再邀請。

## 安全審查的重點

- 安裝／更新程式、依賴、網路傳輸、外部指令、GitHub Actions、發布、隱私規則與授權變更，PR 必須明列用途、輸入來源、權限與驗證證據。
- 未審查的 PR 先讀 diff；需要執行時使用隔離、無私人憑證的環境。不要直接在含真實頻道資料與媒體的工作目錄執行。
- 不提交 API key、token、個人設定、未公開媒體、客戶資料、後台數字或私密遠端審片入口；細節見 [貢獻指南](CONTRIBUTING.md)。
- CI、code-cleanup-helper 與 R&D 的測量可以提供證據；本流程沒有完成惡意程式的動態沙箱分析或全面滲透測試，不能宣稱已驗證沒有惡意程式碼。
- 發現漏洞依 [安全政策](SECURITY.md) 私密回報，不將可利用細節貼到公開 Issue。

## 貢獻度如何留下

- 功能、修正與文件：以合併的 PR、提交作者、Issue 與 Release notes 作為紀錄。
- 測試、設計、素材與審查：在相關 PR 記錄實際工作與證據，經當事人同意再署名。
- 共同撰寫提交時，取得同意後加入 `Co-authored-by`。Squash 合併時維護者確認共同作者沒有遺失；作者可使用 GitHub 的 noreply email。
- GitHub 的貢獻圖與 Contributors 頁面有自己的計算條件，不能代表所有非程式貢獻，也不等同品質或貢獻排名。
- 本專案採用 [MIT 授權](../LICENSE)。提交貢獻表示願意以專案既有授權提供變更；保留作者署名，不要求版權轉讓。
- 這些紀錄不會自動產生股權、薪資或分潤比例。日後若有贊助或委託案，應先另訂預算、分工與分配約定，再開始付費工作。

## 維護者的邀請前清單

- [ ] 確認這份計畫、CODEOWNERS 與 PR／Issue 表單已在 main。
- [ ] 在 GitHub Settings 檢查 main 保護及 `v*` 標籤規則生效，7 個必要檢查名稱仍與 CI 一致。
- [ ] 確認對方 GitHub 帳號、工作範圍與 Write 對 Releases 的權限；只邀請需要直接開發的人。
- [ ] 提供第一個小型 Issue，完成一次 PR 與審查流程。
- [ ] 定期檢視協作者、GitHub Apps、workflow 與發布紀錄。

參考：[個人儲存庫權限](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/permission-levels-for-a-personal-account-repository)、[主分支保護](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)、[Code Owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)。
