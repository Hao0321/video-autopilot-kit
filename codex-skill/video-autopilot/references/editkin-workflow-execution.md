# Editkin v4 可續跑執行流程

本頁是操作者說明；唯一機器真相是同層的 `workflow_contract.json`，狀態轉移由 `workflow_contract.py` 驗證。任何 prompt、UI 文案或 MCP starter text 若順序不同，都以這份 contract 為準並視為 drift。

## 固定 DAG

1. `get_autopilot_contract`：鎖定 current schema、Skill／knowledge／workflow contract hash 與限制。若 `planHashAlgorithm` 缺失或不符，先重新啟動已更新的 Editkin MCP；在分析素材前拒絕舊 runtime，不浪費整輪分析。
2. `start_ai_editing_session`：建立 run/session，保存 project revision 與 brief hash。
3. 每份來源素材各自走 `prepare_ai_material` → `view_material_keyframes` → `get_material_context` → `record_material_semantics`。不同素材可有界平行；同一素材不可跳步。關鍵幀依 prepare 的實際 `bytes` 保持順序分批，每批同時最多四張、1,000,000 image bytes；缺大小需重新 prepare，單張超限需可驗證的較小代理圖，不能猜大小、提高上限或省略圖片。context 必須有界，每份 semantics 至少引用一個真實影像或逐字稿證據。
4. 全部 semantics 完成後，`resolve_autopilot_inference_route` 與只讀 plugin discovery 可並行。外掛只列候選並編譯進 plan，不在 audit 前改專案。
5. 產生 `hao.video-autopilot.edit-plan/v4` 前，呼叫 `get_autopilot_design_brief`，request 帶當前片型／題材、成片 duration 及每個 narrative beat 的 id、energy、primaryFocus（作為 subject）與設計 role。分頁讀 `context` 和每個 `beat:<id>` 到 `hasMore=false`，將 request、projectSha256／sourceSha256／briefSha256、每段 recipeSha256、application 及實際視覺／聲音 commandIndexes 寫入 `designEvidence`。這會直接編譯目前私有的 47 圖設計 DNA、學習記憶、影視颶風 craft 與資訊節奏；只寫美感 metadata 不算整合。十類 `editorial.motionTreatment` 都須明確 use／omit 並說明原因。再綁全部 source／material／semantic receipts、route、plugin manifest、Skill／knowledge／contract hash 與 project revision。v1–v3 只可匯入或檢視。設計 brief 可在主機重啟後重新讀取；來源或記憶改變須開新 run，不可改寫 sealed plan。
6. `audit_autopilot_plan`：輸出綁定 plan SHA-256 與 project revision 的 accepted receipt。

   計畫 hash 採 `sha256-canonical-json-utf8-keys-v1`：object keys 依 UTF-8 bytes 排序，array 順序保留，使用 ECMAScript JSON 數值／字串表示。不能對原始插入順序或 pretty JSON 直接 hash。非 plan 的 cue／semantic wire hash 保持原契約。新 algorithm 會改變 workflow contract hash，既有 sealed run 不改寫、不接納舊 audit；新建 current run 後重新 audit。
7. `apply_autopilot_plan`：只接受上一項 receipt，一次原子提交。若中斷後無法判定是否 committed，run 進入 reconcile，不得自動重套。
8. `render_project`：只對 committed project revision 產生 candidate 與 artifact hash；技術 QA 綠後才可升格 current。
9. 手機人工審片：機器永遠不得代替 Hao 標成已審或 certified。
10. `record_autopilot_outcome`：先記 human review event，D2／D7／D28 到期再追加，不覆寫舊事件。

Skill source precedence 與 Editkin 完全一致：明確 invocation path →
`EDITKIN_VIDEO_AUTOPILOT_SKILL`（絕對 `SKILL.md`）→
`~/.codex/skills/video-autopilot/SKILL.md`；workflow contract 永遠取該 Skill 同層檔案。
workspace `.claude` 相容副本不得自動成為 governance source。

## 快速與續跑規則

- 建立 run 時直接 hash 真實素材 bytes；同路徑換檔會使來源失效，不能只信舊 metadata。
- `prepare_ai_material` 可依 source hash 命中 cache；命中不等於可跳過 evidence view、bounded context 或本次 brief 的 semantics。
- 全片抽樣不足以辨識短暫動作時，建立新的分析 run，`create --keyframe-times "CLIP_ID=23,23.25,23.5,24"` 可指定 1–12 個严格遞增的片段來源相對秒數（`0 <= t < clip.duration`）。不是時間軸秒數，也不要加 `sourceStart`；不指定就維持全片抽樣。選擇納入 source-set／run binding，prepare 發出相同 `keyframeTimes` 與數量；回傳 requestedSamples、實際 decoded time、顯示正規化 receipt 與逐張圖片須一致。改時間點建立新 run／material receipt，不改寫既有已完成證據；既有合法逐字稿與分鏡 cache 可重用。這是精看入口，不表示看過未抽到的畫面，後續 context、semantics、audit/apply 仍不可跳過。
- 長素材回 `RUNNING` 時保留同一 prepare claim，以回傳的 `job.jobId` 呼叫 `get_material_preparation_job`，間隔至少十秒。只有最終 `GREEN/PARTIAL` sealed packet 才可 complete；`RUNNING/CANCELLING` 或沒有 packet 的 `COMPLETED` 都不是完成。觀察逾時不代表 job 停止，不可重開一份。取消須等 `CANCELLED`；中斷後以新鮮的原 prepare request 加 `resumeJobId` 續跑已驗證快取，不能跳過後續看片與語意判讀。
- Contract revision 4 新增 byte-bound 分批與背景完成規則；revision 3 舊 run/receipts 保留歷史，不改寫為新流程，須建立新的 current run。
- 語意 receipt 的 `transcriptEvidence` 由已驗證 context pages 重建：引用 cue 按 index 去重排序，逐項绑定 start／end 與 `JSON.stringify({start,end,text})` 的 SHA-256，再納入整份 semantic hash。不能只對 request 本身算舊 hash，也不能從額外未讀逐字稿補內容；缺 cue、跨頁同 index 內容不一致或字句被替換一律拒絕。
- `next` 可一次回傳同一平行群組的多份素材工作；每個完成 receipt 仍獨立落帳。
- 中斷後 `resume` 只重開可重入的 read-only／render 步驟。`apply` 狀態不明一律停在人工 reconcile。
- retry 只影響失敗 step；已完成且 binding 未變的 receipt 不重跑。brief、source、Skill、knowledge、plugin manifest 或 project revision 漂移時，相關下游 receipt 必須失效。
- 已完成 render 的技術 QA 退件可用 `workflow reject-render <run> --evidence <json>`：只在 apply/render 已完成、human-review/outcome 尚未開始且 review 為 null 時允許。證據 schema 為 `hao.video-autopilot.render-technical-rejection/v1`，必填 machine actor、artifact、artifactSha256、非空 failures（type 為 black_frame/shot_boundary_mismatch/missing_frame/audio_mismatch/decode_failure；每項含有效 frame、evidenceFile、evidenceSha256）。這是機器技術證據，不是人審或美感認證。
- 退件重驗來源、project、plan、apply、影片與歷史證據；不可變 rejection/history 保留原 receipt 和影片，只將 render 重開。下一次 claim 派生同目錄 `preview.attempt-002.mp4`（後續依 attempt 編號）與獨立 receipt，沿用原 max_retries，不重 apply、不覆寫失敗片。檔名碰撞或寫入失敗停止；verify 也驗完整歷史鏈。人審與 outcome 綁最新成功 render。此為私有研發 attempt，不能分發為新作品；current 主檔的原子 promotion 另行處理。

## CLI

退件寫入遇 I/O 錯誤時，只有原 state bytes 未變且新 rejection 檔與本次寫入的完整 bytes 一致，才回收本次未提交檔供重試；讀取失敗、檔案被換或 state 已提交均保留證據並報錯，不自動刪除或覆寫。render complete 若僅 state 寫入失敗，應以原 token 與完全相同 submission 重送 complete，不先 resume 丟棄 claim。

統一入口：`python scripts/hao_autopilot.py workflow ...`。每個 run 放在專案內 `videos/_AUTOPILOT/editkin-v4/`，不得在 D 槽根目錄另建資料夾。常用順序是 `create` → `next` → `claim` → 執行對應 MCP tool → `complete --receipt ...`；失敗用 `fail`，重啟後用 `resume`，交付前用 `verify`。

狀態檔只保存 plan／receipt／artifact 的 hash、步驟狀態與必要 identity；不複製原始影片、不保存私人 Skill 全文，也不把舊成片當 ground truth。

Claim token 保留 192-bit 隨機值並加上 `wf_` 前綴，避免以 `-` 開頭時被 CLI 當選項。既有 token 的 SHA 驗證仍相容；對舊 token 傳參可使用 `--token=<value>`，不得把原 token 寫進 log／receipt。
