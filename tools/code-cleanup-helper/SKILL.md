---
name: code-cleanup-helper
description: 以跨平台、read-only 審計器掃描 codebase、prompt、SKILL.md、repository、release security 與設定式生成資產集合，建立 Python 依賴圖並找循環依賴、分層違規、責任熱點、重複函式、過長函式／檔案、命名漂移、配對資產缺漏、私公版 sync、本地 release readiness、broken links、skill metadata、debug／secret payload 與隱私外洩。使用者要求「清理 code 前先盤點」「分析架構」「依賴圖」「找重複」「重構前審計」「skill 太長」「audit repo」「私公版 diff」「版本對齊」「release 前盤點」「防拆包」「資安」「生成檔有沒有漏」「規則漂移」等診斷時使用；也在 run-benchmark-driven-rd 需要可重現的 repository baseline 或 promotion evidence 時作為 read-only evaluator 使用。
---

# Code Cleanup Helper

以可重複執行的 Python 審計取代臨時 Bash 指令。支援 Windows、macOS、Linux；所有檔案以 UTF-8 讀取。

每次呼叫都以目前 active private skill 目錄為唯一權威，重新從磁碟讀取本 `SKILL.md` 與當次路由 references。不得從公開 mirror、聊天摘要、複製的舊 prompt 或先前 evaluator hash 執行，也不要等待、輪詢或合併其他專案中尚未落入 canonical private tree 的工作副本；已經落盤的內容就是本次最新版。

讀取前用 `scripts/check_skill_revision.py capture` 對 canonical Skill tree 做兩次一致性掃描；做出最終判斷前用 `verify` 重驗。同一次 capture 的兩次掃描不一致時回 `UNSTABLE`，不得使用混合 revision；verify 回 `STALE` 時立即重讀當下最新版並重跑受影響 gate，不等待其他 Session 結束。

## 硬規則

- Audit 引擎永遠 read-only。
- 單獨診斷時先報告，再等使用者明確授權修復範圍。
- 被 R&D 或其他 orchestrator 於使用者已明確要求修改的工作中調用時，只回傳證據，不新增第二次確認；後續修改權限與範圍仍由 orchestrator 和原始請求決定。
- 未能執行的維度標 `NOT_CHECKED`，不包裝成通過。
- 外部檢查器必須證明 child executable 確實啟動並保存 child exit／成功 marker；父層 shell exit 0、PowerShell non-terminating command-not-found 或舊 `$LASTEXITCODE` 都不能當作 PASS。
- 不改 `.git/`、測試／CI、license、package metadata，除非使用者明確把它們放進修復範圍。
- 不 commit、push、force reset、publish release。

當 R&D 組合模組化專案路由時，Cleanup 仍是獨立的唯讀 measurement kernel。只透過版本化 R&D adapter 接受所選 audit mode／config，保留 Cleanup 自己的狀態語意，且不可把「已選模組」當成「已通過驗證」。provider／orchestrator 邊界與跨專案學習規則見 [R&D integration](references/rd-integration.md)。

## 路由

| 使用者意圖 | Mode | 讀取 |
|---|---|---|
| 重複、命名、架構、依賴、模組、函式／檔案太長 | A | `references/mode-a.md` |
| sync、release、link、drift、handoff | B | `references/mode-b.md` |
| 完整健檢 | A+B | 兩份都讀 |
| 要設定例外／機器報告 | 任一 | `references/config-and-report.md` |
| R&D baseline／promotion gate | 依任務 | `references/rd-integration.md` |
| 長期產品「還缺什麼」、跨回合 handoff、完成宣告 | A+B | `references/capability-obligations.md` |
| installer／binary／generated output 可能過期、build receipt 新鮮度 | 專用 | `references/build-receipt-audit.md` |
| 防拆包、release security、secret／source map／額外 executable、簽章或 restricted pack | A+B | `references/security-and-release-hygiene.md` |
| 兩組生成／來源資產需一對一、禁止殘留格式、納入 freshness inventory | B | `references/config-and-report.md` |
| promotion 後又修改、證據是否仍新鮮、完整收尾 | 專用 | `references/rd-integration.md` |
| Skill／Agent／MCP／runtime／installer／人審／發布是否真的串成同一流程 | A+B | `references/cross-system-integration-audit.md` |
| Sol／Terra／Luna、reasoning effort、Markdown prompt、JSON contract、Token／品質路由 | A+B | `references/model-context-contract-audit.md` |

## 標準流程

1. 解析目標絕對路徑；確認存在，不猜 repo。
2. 執行審計器。Windows 先設 `PYTHONUTF8=1`。
3. 讀 JSON 證據或人類摘要；需要 semantic 判斷時再讀相關檔案。
4. 回報 FAIL、REVIEW、NOT_CHECKED、影響與最小修復順序。`REVIEW` 是提醒人工判斷，不是阻擋。
5. 單獨診斷請求要停下等待修復授權；若原始請求已明確授權 R&D／實作變更，將報告交回 orchestrator，不要求重複確認。
6. 修完重跑相同 audit；不能只靠肉眼說完成。

當 orchestrator 要宣告「完整收尾」時，`REVIEW` 不再只是列出：必須使用 R&D adapter 的 strict review policy 收斂為零，並在最後一次檔案修改後重驗 promotion freshness。普通 audit 仍保留 REVIEW 的非阻擋語意。

長期產品若沒有 canonical capability obligation ledger，或 ledger 沒有 project-native gate，完整健檢必須把「需求閉環」標成 `NOT_CHECKED`；零 code finding 不可被翻譯成產品完成。具體判讀見 [capability obligations](references/capability-obligations.md)。

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
python scripts/check_build_receipt.py <target> --receipt <repo-relative-receipt.json> --format json
python scripts/check_audit_snapshot.py <before-report.json> <after-report.json> --format json
python scripts/check_skill_revision.py capture --root <active-private-skill-root> --output <temporary-revision.json> --quiet
python scripts/check_skill_revision.py verify --evidence <temporary-revision.json>
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
- 函式例外必須含 path、function name、max lines、理由、到期日；模組熱點例外必須含 path、max fan-in、max out-degree、理由、到期日。例外仍顯示為 `REVIEW`，超標或逾期恢復 `FAIL`，不會隱藏技術債。
- Semantic duplicate、架構是否值得抽象、公開文件是否講清楚，必須由 agent 讀上下文判斷。
- 動態 import、執行期 service lookup、跨語言呼叫與資料流責任不在 Python AST 圖內；未另查不得宣稱完整架構通過。
- 非 Python repository 不再只回報空圖：量尺會盤點 JavaScript／TypeScript、Rust、C／C++、Swift、Kotlin、Java 與 Go 來源檔，並用 `cross-language-architecture-not-checked` 明列未解析的語言與檔案數。專案原生架構 gate 可補足證據，但不得把 Cleanup 的這項 `NOT_CHECKED` 改寫成 PASS。
- PASS 數量不等於架構最優。若理應存在的依賴邊沒有出現在圖上，先把它當量測失敗；用 `required_dependencies` 加正／負 fixture，修解析器後才繼續產品重構。
- 平台／API／法律等時效事實不靠本地 regex 宣稱正確；需要時另查權威來源。
- Cleanup 的 release 檢查只證明本地 repo metadata；外部發布目標、登入、scope、sudo／2FA 與發布後 API 驗證由 R&D external-change gate 負責。
- HTML／CSS／JS 字串掃描無法證明 Modal 真正位於 backdrop 上方、手機沒有裁切、焦點有回復或觸控目標夠大。這些是 runtime product claims，必須交給 R&D 的同版 browser geometry／journey gate；Cleanup 綠燈不得被翻譯為介面驗收通過。
- Build receipt 綠燈只證明 receipt 已列出的 input／output bytes 仍一致；實際 installer payload、delivered executable、內嵌 receipt 與 packaged journey 由 project-native evaluator 加 R&D delivery gate 證明。不得把 build-directory executable 當成交付權威。
- React／Vue 等狀態更新 callback 內呼叫會拋錯的 domain command 時，外層 `try/catch` 通常接不到 deferred updater 例外；這是整個 UI root 被卸載的 release blocker。必須以 pure safe-dispatch boundary 回傳原狀態＋錯誤、對邊界操作補 fixture，並在 delivered journey 收集 `error`／`unhandledrejection`／root-empty 證據。測試控制通道逾時後也必須丟棄舊連線再建，不能重用已卡死的 CDP socket。
- 安裝包剛解開時，防毒／公證掃描、runtime 首啟與素材索引可能比暖機慢很多。不得用一個會 `await` 多項服務的 monolithic CDP／WebDriver expression 驗收，否則單一逾時無法區分產品、控制器或哪個 stage。先以短 UI heartbeat 驗證 root、Timeline 與主要操作在背景工作 pending 時仍可回應，再逐段等待素材庫、媒體分析、更新等 bounded promise，保留每段 elapsed／controller miss／error trace。功能成功要讀回 project duration、Autosave、輸出 bytes 等耐久不變量；共用狀態列文字會被其他背景 job 合法覆寫，只能作診斷，不能作唯一 promotion assertion。
- 桌面 journey harness 若共用操作者的 app state 或 WebView／瀏覽器 user-data profile、靠翻譯後顯示文字找控制項、或以固定 sleep 代替 bounded readiness predicate，標為 `REVIEW`；若因此連到舊程序、要求關閉使用者視窗或產生假 BLOCK／假 PASS，升為 `FAIL`。UI 密度不得只報總控制數：保留完整 inventory，將 enabled 決策與 disabled 流程提示分開設上限，並對兩種超量各有負控制。
- Skill、Agent、MCP tool、runtime 模組、素材庫或 installer payload 各自存在，只是 component-presence evidence。跨系統宣稱必須有同一來源 revision/hash、版本化 handoff、executor receipt、真實輸出與所宣稱 review/publish/outcome state 的單一 journey；缺邊時標 `NOT_CHECKED cross-system-integration`，詳見 [cross-system integration audit](references/cross-system-integration-audit.md)。
- 私人記憶要轉成可公開的通用 Knowledge Pack 時，必須把來源目錄當 closed world：每個來源檔都要落入 include 或帶理由的 exclude，公開模組綁定來源／內容 SHA-256，並對姓名、帳號、Email、私人路徑、密鑰、未匿名成效與可回推身分事件跑正負控制。只掃已挑中的 allowlist 會漏掉新增私人檔；一次載入全文則是 privacy 與 Token false green。產品只以 schema 化、有界分頁讀取通用模組，最新私人 Skill 與人工審片仍維持動態邊界。
- Orchestrator 若在文字或 routing 中直接引用其他 Skill，Cleanup 必須從當前 canonical Skill bytes 動態建立直接依賴集合，與 stable integration ledger 一對一比對，驗證每個 dependency 的整合模式、證據、隱私邊界與安裝狀態。手寫舊數量或只檢查 ledger 自己不得宣稱最新版已整合；來源 Skill 新增／移除依賴後，漏映射與幽靈映射都要阻擋。
- 大型匿名知識包、preset registry 或模板集合即使隱私與功能 gate 全綠，也可能被靜態 import 拖入主 UI bundle。Cleanup 應檢查 `full pack → server/MCP bounded reader` 與 `hash-bound compact summary → browser main` 的依賴方向，並要求大型 registry／builder 走使用時 dynamic chunk、main JS/gzip/CSS 固定預算與 lazy-path 真實 journey。只提高 bundle budget、刪掉預覽或讓摘要和全文 hash 漂移都屬 false green。
- 「MCP add exit 0」只證明設定命令被接受，不等於使用者已能工作。Session-native AI onboarding 的 audit 必須分開追蹤：入口可發現性、精確 CLI／shim 解析、user-level 設定、只針對 canonical server ID 的既有／過期設定處理、官方 `get`／`list` 讀回、命令與 args／env 精確核對、真實 protocol health、重啟／新 session 提示、第一句可複製任務，以及 CLI 缺失或 health 失敗時的人話備援。只能讀回設定的 client 標 `configured`，實際握手成功才標 `connected`；兩者不得混寫成同一個「已連線」。產品不得要求、複製或保存 provider API key／登入 token，也不得因備援指令已進剪貼簿就宣稱成功。
- 模型名稱、reasoning effort 或 Markdown 檔不能當品質證據。每次 invocation 要有模型／effort／context hash／evaluation receipt，Markdown 只做 bounded semantic router、JSON 才是可執行真相；缺同 provenance model×effort benchmark 時標 `NOT_CHECKED model-quality-evaluation`，詳見 [model context contract audit](references/model-context-contract-audit.md)。
- 「Evaluator 綠燈且 claimStatus=unmeasured」只證明沒有造假，不能翻譯成產品或市場 parity。完整／領先宣稱的 baseline×surface cells 未封閉時保持 open obligation。
- 專業媒體工作站不能用 component-presence 代替成片與互動證據：Timeline planner benchmark 不等於 UI viewport／materialized DOM／input-to-state 延遲；字型檔存在不等於 exporter 真正選字；source-frame scopes 不等於 decoded output 或校色顯示 parity；machine-ready 導演狀態不等於真人核准。詳見 [cross-system integration audit](references/cross-system-integration-audit.md) 的 professional media workstation contract。
- 內容 profile／template 的 UI 選項不是功能閉環。審計必須追到 persisted project schema、migration、batch session restart、agent/MCP handoff、decision receipt、renderer 與輸出 fingerprint；任一層默認回 `auto` 或只改 UI 時標 `NOT_CHECKED profile-propagation`。雙人物框選亦不能由兩個 track／按鈕存在就宣稱 active-speaker：需另查 activity／speech evidence、confidence、hysteresis、不確定 split fallback、Undo 與 Preview／render crop parity；visual activity 被描述成 diarization 時列 truthfulness FAIL。
- Closed-world capability ledger 新增 obligation／flow／tool 時，資料檔、consumer 的固定 required set、正控制與「漏一項必擋」負控制必須同版更新；只讓 JSON 自己的兩個陣列互相比對會漏掉 evaluator constant 漂移。TypeScript 的 `import type` 仍是 ownership edge；若形成循環，應把共用型別下沉到較低階模組並重跑 native graph，不得因執行期不載入就把 cycle 靜音。
- 長來源自動拆片要同時審計 editorial-unit cardinality：一個來源可包含 N 個完整 promise/payoff，預期 N 就必須由同一 source hash 對到 N 個獨立 editable projects、renders 與 receipts。舊候選輸出只能當 benchmark，不得自我標註 ground truth；單一合輯、同 fingerprint 重渲染或只建立 N 個空專案都屬 false green。
- 靜態掃描能找到 release config、source map、secret-shaped bytes、環境變數 executable override 與 owner-only metadata，但不能證明 unpacked payload、Authenticode、PE exploit mitigations、HTTP Origin/CSP 行為或 updater runtime 拒絕。沒有 project-native extracted-artifact／runtime negative gate 時必須標 `NOT_CHECKED`，詳見 [security and release hygiene](references/security-and-release-hygiene.md)。

## 維護

- 多 Session 同步更新時，先重讀要修改的當前私版檔案，把變更語意合併到最新內容，再用 context-sensitive patch 寫入；不得用公開副本、其他專案副本或舊暫存檔覆蓋私版，也不等待尚未落盤的工作。公開同步永遠是 private → public 單向。
- Skill 編輯與 public sync 完成後，先對 canonical private tree 跑 self-test、strict Cleanup promotion 與 sync check，再重放所有引用本 evaluator 的產品 promotion。任何 evaluator/config/adapter hash drift 都要求重新 capture，不能沿用舊綠燈。
- Public sync 必須使用 managed manifest 與寫入前 privacy preflight；dry-run 的 `stale`／`changed` 都要在 release 前歸零。Cleanup 本身仍不 commit／push；當輪使用者已明確要求公開 release 時，把通過的鏡像交給 R&D external-change gate，推送後以遠端 branch／tag hash 驗證。沒有當輪授權時只回報 release pending，不延用舊授權。

- 新的 deterministic 檢查先加到 `scripts/audit_core.py`，再補 `self_test.py`；量測本身沒有對應 fixture 時不得拿來阻擋重構。
- 子目錄可直接執行的 Python script 常用 bare sibling import；解析時先保留真正 top-level absolute import，再 fallback 到同目錄 module。兩種情境都必須有 fixture，避免修一邊壞另一邊。
- Cleanup 也必須檢查「檢查器的計分與輸出合約」：新增／移除 gate 後，分數分母必須由實際 max points 計算；宣稱 JSON 的 CLI 只能輸出一份可解析文件。任何會製造假滿分、吞掉失敗或污染 JSON 的問題都先修量尺、補回歸測試，再繼續產品開發。
- Promotion inventory comparison must detect changed bytes, added files, removed files, malformed identities and case-insensitive duplicate paths. The R&D adapter owns blocking decisions, but must consume this provider checker instead of reimplementing Cleanup inventory semantics.
- Artifact-set gates must reject vacuous empty sets, missing positive expected counts, duplicate assertion IDs, key patterns without a capture group, overlapping left/right files, forbidden residuals, undersized bytes and symlinks. Pairing membership is not visual/content/rights proof.
- Public sync preview and D5 must share the same text-normalization policy so LF／CRLF alone cannot create an endless false diff while semantic changes remain blocking.
- `artifact_set_assertions` 是 closed-world 檔案集合量尺：它必須檢查左右 key 一對一、預期數量、最小 bytes、禁用殘留格式、symlink 與 case-insensitive duplicate，並把通過集合的二進位 bytes 放入 audit inventory；不得只比檔案數。
- 專案特有事實放目標 repo 的 `audit.config.json`，不要 hardcode 到通用引擎。
- Audit repo 時優先使用目標 repo 自己的 `audit.config.json`；skill 根目錄設定只適用於 skill 本身。若 inventory 意外納入 `node_modules`、`dist`、`target`、vendored runtime 或 evidence output，先標為量測設定污染，不把第三方檔案的 FAIL／REVIEW 誤算成產品技術債。
- UI smoke 在 `document.body` 尚未建立或 lazy route landmark 尚未出現時就讀 DOM，屬於 harness 啟動競態；工具列已 mount 不代表新手首頁／剪輯工作區 ready。應使用有界語意 predicate，再量 onboarding、密度與可發現性。
- 重構把簽章、IPC、權限或更新責任從入口檔拆出去時，檢查 evaluator 是否仍只掃舊入口檔。安全控制必須按實際註冊／組合責任覆蓋完整 module set，並保留「漏掉 extracted module 必須失敗」的 negative fixture。
- `agents/openai.yaml` 或 skill metadata 改動後重新跑 skill-creator 的 `quick_validate.py`；Windows／非 UTF-8 locale 使用 `python -X utf8 ...quick_validate.py <skill-folder>`，避免把啟動器解碼錯誤誤判為 skill 內容失敗。
