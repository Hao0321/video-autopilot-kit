# Editkin v4 可續跑執行流程

本頁是操作者說明；唯一機器真相是同層的 `workflow_contract.json`，狀態轉移由 `workflow_contract.py` 驗證。任何 prompt、UI 文案或 MCP starter text 若順序不同，都以這份 contract 為準並視為 drift。

## 固定 DAG

1. `get_autopilot_contract`：鎖定 current schema、Skill／knowledge／workflow contract hash 與限制。
2. `start_ai_editing_session`：建立 run/session，保存 project revision 與 brief hash。
3. 每份來源素材各自走 `prepare_ai_material` → `view_material_keyframes` → `get_material_context` → `record_material_semantics`。不同素材可有界平行；同一素材不可跳步。關鍵幀每批最多四張，context 必須有界，每份 semantics 至少引用一個真實影像或逐字稿證據。
4. 全部 semantics 完成後，`resolve_autopilot_inference_route` 與只讀 plugin discovery 可並行。外掛只列候選並編譯進 plan，不在 audit 前改專案。
5. 產生 `hao.video-autopilot.edit-plan/v4`；必須綁全部 source／material／semantic receipts、route、plugin manifest、Skill／knowledge／contract hash 與 project revision。v1–v3 只可匯入或檢視。
6. `audit_autopilot_plan`：輸出綁定 plan SHA-256 與 project revision 的 accepted receipt。
7. `apply_autopilot_plan`：只接受上一項 receipt，一次原子提交。若中斷後無法判定是否 committed，run 進入 reconcile，不得自動重套。
8. `render_project`：只對 committed project revision 產生 candidate 與 artifact hash；技術 QA 綠後才可升格 current。
9. 手機人工審片：機器永遠不得代替 Hao 標成已審或 certified。
10. `record_autopilot_outcome`：先記 human review event，D2／D7／D28 到期再追加，不覆寫舊事件。

## 快速與續跑規則

- 建立 run 時直接 hash 真實素材 bytes；同路徑換檔會使來源失效，不能只信舊 metadata。
- `prepare_ai_material` 可依 source hash 命中 cache；命中不等於可跳過 evidence view、bounded context 或本次 brief 的 semantics。
- `next` 可一次回傳同一平行群組的多份素材工作；每個完成 receipt 仍獨立落帳。
- 中斷後 `resume` 只重開可重入的 read-only／render 步驟。`apply` 狀態不明一律停在人工 reconcile。
- retry 只影響失敗 step；已完成且 binding 未變的 receipt 不重跑。brief、source、Skill、knowledge、plugin manifest 或 project revision 漂移時，相關下游 receipt 必須失效。

## CLI

統一入口：`python scripts/hao_autopilot.py workflow ...`。每個 run 放在專案內 `videos/_AUTOPILOT/editkin-v4/`，不得在 D 槽根目錄另建資料夾。常用順序是 `create` → `next` → `claim` → 執行對應 MCP tool → `complete --receipt ...`；失敗用 `fail`，重啟後用 `resume`，交付前用 `verify`。

狀態檔只保存 plan／receipt／artifact 的 hash、步驟狀態與必要 identity；不複製原始影片、不保存私人 Skill 全文，也不把舊成片當 ground truth。
