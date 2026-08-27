# Model、reasoning 與 Markdown／JSON contract audit

用於產品或 Skill 宣稱會依 Sol／Terra／Luna、reasoning effort、prompt／Markdown 或 context router 自動提高品質、降低 Token 或跨模型一致時。

## 判讀

1. 模型與推理等級是 invocation provenance，不是 trust level。執行 receipt 必須保留 provider、model ID、effort、task class、route policy、context hash 與 evaluation state。
2. `.md`／prompt 檔存在只證明 component presence。Markdown 可改善語意層級與可讀性，但可執行欄位必須由 JSON schema、typed command、negative gate 與 receipt 關閉。
3. 每個 model × effort 是獨立 cell。官方定位、手感、單一成功案例或不同素材的結果都不能標 `measured`；同一 frozen dataset／Skill revision／context／evaluator／環境才可比較。
4. `unmeasured` 模型不得因名稱、價格或 reasoning 高低跳過 current schema、權利、安全、真實性或 semantic audit。低風險候選與可逆操作可以降級，但 direct apply 與發佈相鄰工作必須有明確 safeguards。
5. 同一規則若在 Markdown、JSON schema、UI、程式與 installer 各有一份未綁 revision/hash 的真相，標 `REVIEW rule-drift`；若產品會直接執行且無 schema／negative control，標 `FAIL model-context-bypass`。
6. measured cell 必須有 suite ID、raw evidence、evaluator hash 與 fresh promotion receipt；任一來源變更使證據 stale。

## Cleanup 邊界

Mode B 可驗證路由檔、schema、matrix、hash、link、版本與 freshness；Mode A 可檢查 policy 是否散落、重複或繞過執行邊界。模型實際剪輯品質、Token／延遲收益與跨模型等價性需要 project-native benchmark；缺少時標 `NOT_CHECKED model-quality-evaluation`，不得由零 finding 翻譯成品質 GREEN。
