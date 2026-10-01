# R&D integration contract

把 Cleanup 當成 deterministic、read-only evaluator；把 `run-benchmark-driven-rd` 當成唯一決策、修改與 promotion orchestrator。不要複製 Cleanup detector 到 R&D。

## Modular boundary

Cleanup and R&D are integrated through a provider／adapter contract, not merged into one mutating system. Cleanup is the independent read-only measurement kernel. R&D owns project profiles, falsifiable claims, candidate changes, experiment memory, capability closure and external release decisions. This separation is mandatory for audit-only semantics and for distinguishing evaluator failure from product failure.

For mixed projects, R&D composes `skill`, `web`, `database`, `game`, `software` and cross-cutting modules into a frozen route. The route may select Cleanup mode and required evidence dimensions, but it must invoke Cleanup through `run_cleanup_gate.py`; direct provider output is not promotion evidence. Project-local findings remain in that project's `.rd/` workspace. Only anonymized, replayable, cross-project detector improvements with positive and negative fixtures may be promoted back into Cleanup.

## Provider invocation

每次 invocation 都從 active private `code-cleanup-helper` 目錄重新讀取規格並解析 provider root；public mirror、先前 turn 摘要與其他專案工作副本不是執行來源。不要等待其他 Session：只採用已落入 canonical private tree 的 bytes。先用 `check_skill_revision.py capture` 做雙掃描快照，handoff 前 `verify`；若 canonical bytes 已改變就重讀當下最新版並重新 capture downstream evidence。

每個 baseline 或 promotion 都先執行 evaluator self-test，再輸出一份 JSON：

```powershell
$env:PYTHONUTF8='1'
python scripts/self_test.py
python scripts/audit.py <target> --mode architecture --format json
```

依任務選擇 `architecture`、`a`、`b` 或 `all`。不要在 baseline 加 `--strict`；既有 FAIL 是待比較的證據，不是 evaluator 啟動失敗。

Audit repository 時若目標根目錄已有 `audit.config.json`，優先使用它；provider skill 的設定檔只用於 provider 自身。正式全掃描前先 sanity-check inventory：若意外納入 `node_modules`、`dist`、`target`、vendored runtime 或 evidence output，這是 config-scope measurement failure，不能把數千個第三方 finding 當成產品 baseline／promotion。

## Machine contract

接受報告前驗證：

- stdout 恰好是一份可解析 JSON，沒有前後雜訊；
- `schema_version` 是 consumer 明確支援的版本；
- provider schema `1.2` 必備欄位為 `target`、`mode`、`config`、`summary`、`inventory`、`architecture`、`update_coverage`、`findings`；所有 mode 必須恰有一筆 D11，classification 只能是 `managed／check-only／safe-auto-update／manual-only／no-origin`；
- finding status 只能是 `PASS`、`FAIL`、`REVIEW`、`NOT_CHECKED`；
- `summary` 的四種狀態數量與 `findings` 完全相等；
- target 與 mode 等於本次 frozen invocation；
- evaluator hash 涵蓋 `audit.py`、`audit_core.py`、`self_test.py`；使用設定檔時另存 config hash。
- evaluator hash 也涵蓋 self-test 直接校準的 `check_build_receipt.py`、`check_audit_snapshot.py` 與 `check_skill_revision.py`；R&D adapter 另存自己的 hash。
- contract `1.2` 的 provider 與 adapter 都保存完整 canonical Skill-tree revision snapshot，不只保存少數 evaluator script hash；缺少 revision 的舊 envelope 必須 recapture。
- adapter 會拒絕任何不等於 active private canonical root 的 `--cleanup-root`；不得用 public mirror、舊 worktree 或快取複本覆蓋最新版 provider。
- revision snapshot 必須具備完整 algorithm／root／file／byte／SHA-256 identity；部分、畸形或替換演算法的保存證據一律 measurement-block。

任何一項不成立都分類為 `measurement` failure，停止產品變更並先修 evaluator。

Provider／test／build 的 process launch 也是 machine contract。父層 shell 回傳 0 不足以證明 child executable 曾啟動；PowerShell command-not-found 可能是 non-terminating error，並保留舊的 `$LASTEXITCODE`。Promotion 必須由 R&D `command_execution_gate.py` 或等價的 shell-free launcher 保存 invocation path、physical executable identity、child exit code 與預期成功 marker；alias-sensitive proxy／symlink 必須從原呼叫路徑啟動，不能解析成 target 後改變 `argv[0]` 語意。找不到 executable、timeout、缺 marker 或 child 非零都屬 `measurement` failure；不得把 wrapper 假綠燈轉成 Cleanup PASS，也不得把 secret 放進保存的 argv。

Interpreter／runtime 版本也是 launch identity。Windows `.cmd/.bat/.ps1` 不是 shell-free executable；應直接執行符合專案 version floor 的 `node.exe`／`python.exe` 加 script entry，不能只 hash wrapper 後讓它暗中選到舊 runtime。

若測試器使用只在 declared runtime floor 存在的內建 API，舊 runtime 的 `ReferenceError` 是 launcher measurement failure，不是產品 regression，也不能被忽略成 PASS。保存失敗嘗試後，必須以精確、合規的 interpreter 重播同一 harness 並綁定 child-level receipt；這只證明 promotion 使用受支援 runtime，不代表舊 runtime 相容。

## Phase semantics

- **Baseline**：有效報告即可保存；現有 `FAIL` 不阻止建立 baseline。
- **Promotion**：任何 `FAIL` 阻擋 promotion。
- **REVIEW**：普通 audit 保持可見但不自動阻擋；由 orchestrator 做語意判斷。使用者要求完整收尾或 release closure 時，adapter 必須以 `--review-policy block` 要求零未解 REVIEW，不得靠調高門檻或新增 ignore 消音。
- **NOT_CHECKED**：永遠標記 `unmeasured`；若屬本次 required dimension，阻擋 promotion。

用相同 evaluator hash、config hash、mode 與 target 比較 before／after。若量尺改變，先重跑 baseline，不可直接比較舊新分數。

將完整 contract envelope 保存到 `.rd/benchmarks/`；在 `.rd/DECISIONS.md` 記錄 promotion，在 `.rd/FAILURES.md` 記錄量尺缺陷。

## Snapshot freshness

Cleanup 的 `scripts/check_audit_snapshot.py` 是 inventory 新鮮度的唯一 provider detector。它驗證路徑、行數、bytes、SHA-256 與 case-insensitive uniqueness，並比較 added／removed／changed 檔案；R&D 不得複製這套語意。

Promotion adapter 必須凍結 provider evaluator hash、config hash、adapter hash、Cleanup/R&D 完整 Skill revision 與 `cleanup-inventory-sha256-v1` target snapshot。若 evidence output 位於 target 內，它的資料夾必須由 `audit.config.json` 排除；否則第二次 audit 會讓報告自我引用，分類為 `measurement` failure。

```powershell
python scripts/run_cleanup_gate.py <target> --mode all --phase promotion --review-policy block --output <target>/.rd/benchmarks/cleanup-promotion.json --quiet
python scripts/verify_cleanup_evidence.py <target>/.rd/benchmarks/cleanup-promotion.json
```

Capture 在寫入 envelope 後立即重跑 provider，證明掃描期間沒有其他變更。Freshness verifier 用保存的 raw report 對 live target 重跑；evaluator、config 或 adapter identity 改變時回 `MEASUREMENT_BLOCK`，檔案 bytes／集合改變時回 `STALE`。最後一次程式、測試、設定、文件或 packaging 修改後才可執行最終驗證；驗證後再修改就必須重跑。

## Authorization boundary

Cleanup 不取得修改權，也不執行修復。若使用者只要求 audit／分析，orchestrator 必須停在報告。若原始請求已明確要求實作、重構或修復，該請求可供 R&D 在既定範圍內繼續，不需要因 Cleanup 被調用而要求第二次確認。

本契約只涵蓋本地證據。外部 create、publish、rename、archive、delete、transfer、permission change、登入與授權都必須另走 R&D external-change gate。
