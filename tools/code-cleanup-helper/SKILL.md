---
name: code-cleanup-helper
description: Read-only code／architecture／repo／release／Skill 審計器；重複、依賴、分層、長責任、sync、資安、資產、Token、GitHub 安全更新與舊版淘汰；R&D measurement provider。
---

# Code Cleanup Helper

## Contract

1. Active private Skill 是唯一權威。開始 `check_skill_revision.py capture`，最終 `verify`；`UNSTABLE` 不混用，`STALE` 重讀重驗。
2. Audit 永遠 read-only。純診斷先報告等授權；已授權實作只取證，不重複詢問；不自行外部或破壞性 mutation。
3. `FAIL`=已證明阻擋、`REVIEW`=人工判斷、`NOT_CHECKED`=量尺／環境／證據缺口、`PASS`=僅已執行維度；未量測不得包裝為 PASS。
4. 外部檢查要保存 child executable identity、真實啟動、child exit 與 success marker；父 shell exit 0 不代表通過。
5. 解析目標絕對路徑；修後重跑同 audit，報告綁定 revision、config、route 與 JSON evidence。
6. Cleanup 是獨立 provider；選 mode／config 不等於通過。修改、promotion、外部 mutation、完成宣告歸 orchestrator。
7. 每次分類更新覆蓋（managed／check-only／safe-auto-update／manual-only／no-origin）；URL／檔案不證明或授權更新能力。
8. Security v2 每個 target 必須覆蓋六控制 planned/executed cells；零 finding、generic check 或自結不補缺格。
9. 階段收尾／大型產物前查 workspace＋system temp 空間；依 `references/disk-hygiene.md` 交付清理清單。

## 路由

讀適用列；歧義／缺失／超 budget 明示 legacy fallback，保留 critical rule。

| 任務 | 讀取 |
|---|---|
| duplicate／命名／架構／依賴／長函式 | `references/mode-a.md` |
| sync／release／link／drift／handoff | `references/mode-b.md` |
| config、例外、machine report、資產配對 | `references/config-and-report.md` |
| R&D baseline／promotion／freshness | `references/rd-integration.md` |
| capability／完整收尾 | `references/capability-obligations.md` |
| build／installer receipt | `references/build-receipt-audit.md` |
| security／scanner receipt／secret／extracted payload | `references/security-and-release-hygiene.md` + `references/security-assessment-contract.md` |
| model／prompt／Token claim | `references/model-context-contract-audit.md` + `references/topics/context-routing-and-memory.md` |
| 一般跨系統 journey | `references/topics/cross-system-core.md` |
| 專業媒體／Timeline／成片 | `references/topics/media-workstation.md` |
| 3D／UV／Unreal | `references/topics/character-3d-audit.md` |
| 視覺／UI／材質品質 | `references/topics/visual-quality-audit.md` |
| desktop runtime／背景 job | `references/topics/desktop-runtime.md` |
| Codex／Claude／MCP 產品流程 | `references/topics/session-native-ai.md` |
| GitHub updater／回滾／淘汰舊版 | `references/topics/secure-self-update.md`；helper／installer／簽章再加 security＋build |

跨類合併必要列；legacy `references/cross-system-integration-audit.md` 記錄原因／成本。維護讀 `references/maintenance.md`。

## 執行

```powershell
python scripts/audit.py <target> --mode all --format json
```

僅 CI／fail-fast 加 `--strict`。普通 `REVIEW` 不阻擋；完整收尾由 R&D 收斂 review、freshness、obligations。未解析的非 Python graph 保持 `NOT_CHECKED`。輸出 3–10 個最高優先 finding，完整清單留 JSON；GitHub URL 不授權下載執行。
