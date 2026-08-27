# Editkin × video-autopilot editorial intelligence contract

## 目的

Editkin 是本 Skill 的主要剪輯執行器；Skill 保留會持續更新的路由、個人記憶與品質判斷，產品保留穩定、低 Token、可驗證的執行契約。兩者不得各自複製一份規則後漂移。

## 當前契約

- Current schema：`hao.video-autopilot.edit-plan/v4`
- Legacy compatibility：`hao.video-autopilot.edit-plan/v3`、`v2` 與 `v1` 只准讀取／匯入並標 `legacy_compatibility_only`；不得 apply，也不得關閉 current workflow。
- 唯一機器順序：`workflow_contract.json`；耐久狀態與 receipt 驗證：`workflow_contract.py`。Markdown 與 starter prompt 不得另寫一套順序。
- MCP：`get_autopilot_contract` → `start_ai_editing_session` → 每素材 `prepare_ai_material` → `view_material_keyframes` → `get_material_context` → `record_material_semantics` → `resolve_autopilot_inference_route` ＋只讀 plugin discovery → 產生 v4 plan → `audit_autopilot_plan` → `apply_autopilot_plan` → `render_project` → human review → `record_autopilot_outcome`。
- Build v4 必填：Skill、knowledge 與 workflow contract revision/hash、run/session、真實 source hash、material／semantic receipts、route、bounded budget、assurances、quality、editorial plan、inference provenance、plugin manifest、structured commands 與 audit receipt。
- Editorial plan 必填：brief、ordered beats、setup/payoff、1–3 packaging hypotheses、caption contract、semantic graphics、motivated transitions、audio layers、single look、semantic asset order、platform variants、D2/D7/D28。
- Build 至少有 `promise` 與 `payoff` beat；beat 必須 frame-ordered 且不可重疊。J/L cut 必須由 audio 證據驅動；match/action/wipe/whip/ramp 必須有切點兩側證據。tracked label 缺 track、subject sheen 缺 matte 直接拒絕。

## 執行與證據

1. 建立 durable run；brief、Skill、knowledge、workflow contract、project revision 與每份來源素材的真實 bytes SHA-256 組成 binding。來源同路徑換檔也必須被抓到。
2. 素材 prepare 可依 source hash 命中 cache並有界平行；keyframe/context/semantics 仍逐素材留下證據 receipt，不能因 cache hit 跳過。
3. 候選 EditGraph、外掛 actions 與一般 commands 編譯進同一份 v4 plan；audit 前不得先呼叫會改專案的外掛工具。
4. Audit receipt 必須綁 plan SHA-256、project revision、全部 source／semantic hashes 與 plugin manifest；apply 沒拿到這份 accepted receipt 就拒絕。
5. Apply 先建立 pending receipt，專案只做一次原子寫入，成功後改 committed。若 crash 後無法判定是否寫入，run 進入 reconcile，禁止盲目 retry。
6. Render 只讀 committed revision 並產生 candidate；probe 與技術 QA 綠後才可原子升格 current，RED 時保留上一版。
7. 所有結果強制 `REVIEW_REQUIRED`、`machine_certified=false`；只有 Hao 的時間碼人審可進 Quality95。
8. Outcome 以 immutable `hao.video-autopilot.learning-event/v1` 保存；human review 或 D2/D7/D28 事件交回當次最新 Learn／Outcome lifecycle。單一事件不得自動 pin。

## 低 Token 與最新版本

- 每次先讀 current contract，不把完整 Skill 或 77+ 條記憶塞進模型。
- Context ≤1100 tokens、selected memory ≤6、asset candidates ≤64、commands ≤100、plan ≤256 KiB。
- Installer 不包含私人 Skill、私人記憶全文或本機路徑；來源 revision/hash 由當次 invocation 提供。
- Skill、knowledge、workflow contract、plugin manifest、brief、source 或 project revision 更新後，受影響的下游 receipt 必須失效並重新產 v4 plan；禁止把安裝包內舊快照冒充最新版。
- Markdown 只承載 bounded semantic router；JSON schema 才是執行真相。router hash、模型／推理等級、evaluation state 與第二次語意複核都寫入 receipt；完整契約讀 [model-and-context-adaptation](model-and-context-adaptation.md)。

## 78 項能力帳本

Editkin 根目錄 `autopilot-capabilities.json` 是 Skill→產品的封閉世界盤點，狀態只允許：

- `native_verified`：產品本機可重跑證據。
- `contract_enforced`：v4 schema／gate 能拒絕錯誤計畫。
- `orchestrator_handoff`：由當次最新 Skill 執行，產品有穩定交接面。
- `unmeasured`：模組存在但真人／真片品質未證明。
- `blocked_external`：需要授權、平台、硬體或發行身分。

新增 Skill 能力時必須先增 stable ID、狀態、evidence 或 next experiment，再改程式；legacy adapter、UI 按鈕或檔案存在不能單獨關閉能力義務。

## 免費社群版邊界

免費不等於可任意再散布。Hao 自有、以付費 AI 點數生成並由 Hao 明確授權社群再散布的素材，可在逐檔 SHA-256 manifest、owner attestation 與授權文字都存在時進 community installer；來源不明或含第三方權利的音樂、SFX、字體、Stock、模型與素材仍 fail-closed。平台條款與第三方權利不得由「付過點數」自動推定。
