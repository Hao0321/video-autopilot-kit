> 來自 video-autopilot-kit 開源知識庫 · MIT 授權

# YouTube Algorithm Mastery Skill

YT 演算法深度 + MrBeast 戰術，為**教學頻道改寫**。本 skill 是 **YT-only 深度 / MrBeast 級版**。**跨平台廣度 / 快速版**請用 `video-craft-playbook`。

**資料位置**：放在你自己的 skills 目錄底下（建議用本機資料碟，不要寫到系統碟）。

## 🎯 該用哪個 skill？（3-skill 決策樹）

| 任務 | Skill | Mode |
|---|---|---|
| 學新樣本 / 砍贅詞 / 從主題寫腳本 | `yt-script-style` | A / B / C / D |
| 跨平台規劃 / Title+Thumbnail 快速版 / 改剪 Shorts/Reels / 跨平台 audit | `video-craft-playbook` | A / B / C / D |
| **本 skill**：拍前 MrBeast Top 1% filter | `yt-algorithm-mastery` | **A** |
| **本 skill**：留存曲線深度診斷 | `yt-algorithm-mastery` | **B** |
| **本 skill**：MrBeast 級 title+thumbnail（深度版）| `yt-algorithm-mastery` | **C** |
| **本 skill**：YT Studio 數據深度 decode | `yt-algorithm-mastery` | **D** |
| **本 skill**：該不該換 thumbnail / kill 影片 | `yt-algorithm-mastery` | **E** |

## ⚡ Quick Cheat Sheet — 7 條鐵則

1. **Title + Thumbnail 先寫，影片再拍**（MrBeast 鐵則，不可協商）
2. **Satisfaction signals 權重 35% > CTR 20%**（2025 大反轉）— 不為 CTR 犧牲 deliver
3. **「Quality Click Ratio」紅線**：高 CTR + 低 AVD = 比低 CTR + 高 AVD **更糟**
4. **Test fast, kill fast —— 但時序是 48h 只讀不動、day-14 才決策**
   ⚖️ 「48h 定生死」已作廢（評估期持續數週）。0-48h 內換標題/縮圖會污染 Test & Compare 樣本；
   唯一的提前例外是 **seed fail 三聯徵同時亮**。完整時序定義（單一真值來源）
   → [youtube-algorithm-mastery.md](youtube-algorithm-mastery.md) §2「48h vs day-14」。2 次換沒救 → kill。
5. **先問「這題餵哪台機器」**：推薦機（快·爆·會斷）vs 搜尋機（量小·長尾複利）——
   同一個標題框架在兩台機器上命運可能相反 → [youtube-algorithm-mastery.md](youtube-algorithm-mastery.md) §2b
6. **你的 KPI 門檻一律自己量**：CTR `<fill in>` / AVP `<fill in>` / 1-min retention `<fill in>` / 結尾 `<fill in>`
   —— 這四個全是**後台讀數**，第三方看不到別人頻道的值，所以任何「沒有出處的具體門檻」在定義上就是某個人的 Studio 讀數。
   本 kit 不刊任何頻道（包括原作者的）的 analytics 讀數。校準 SOP → [youtube-algorithm-mastery.md](youtube-algorithm-mastery.md) §TL;DR + §2b-5。
7. **合規是 gate 不是建議**：發布前跑 [ai-content-compliance.md](ai-content-compliance.md) 的 10 項 checklist；
   深偽三不（R29）是刑法級紅線，選題階段就擋。

---

## 5 個 Mode

### Mode A — Pre-flight Checklist（拍前過 MrBeast filter）

**觸發**：「我要拍 X 該做哪些 check」「這題目能爆嗎」「拍前 checklist」「過 Top 1% filter」「先 packaging 再拍片」

**步驟**：
1. 讀 [youtube-algorithm-mastery.md](youtube-algorithm-mastery.md)（特別是 §1 MrBeast 戰術 + §5 Topic + §4 Packaging）
2. **強制執行 MrBeast 內部法則**：**先寫 title+thumbnail，再規劃影片**
3. 跑 Top 1% filter：
   - Title 套上 Galloway 5 大框架（好奇/好處/規模/地位/對比）— **挑 1 個主框架**
   - Thumbnail concept 1 個（One Face, One Object, One Question）
   - 跟 OutlierKit / Spotter Studio 的 niche outlier 比較（如果有用這些工具）
   - 評分：**這支會贏 niche 前 1% 嗎**？不會就重想題目或重想 packaging
4. 規劃影片結構（Hook → minute 1-3 progression → minute 3 reveal → halfway pivot → 結尾）
5. 提醒接 `yt-script-style` Mode D 生草稿

**輸出**：
1. Title 3 變體 + 1 個 thumbnail concept
2. Top 1% filter 評分 + 改進建議（若沒過）
3. 影片結構大綱（含 open loop 設計）
4. 下一步建議

### Mode B — Retention Surgery（留存曲線診斷 + 修補）

**觸發**：「我的留存掉在第 X 秒」「幫我看 retention curve」「這支腳本可能會掉在哪」「retention 怎麼救」「為什麼觀眾流失這麼快」

**步驟**：
1. 讀 [youtube-algorithm-mastery.md](youtube-algorithm-mastery.md) §3 Retention Engineering
2. 對齊 checkpoint 目標（30s / 1min / 3min / 5min / 結尾 五個時點，**門檻值全部 `<fill in>`** —— 用你自己近 3-5 支片校準，量法見 mastery §3）
3. 識別 drop-off pattern：
   - 前 30s 陡崖 → title/thumbnail mismatch 或 intro 太慢
   - 中段沉沒（55-65% mark） → 缺 pattern interrupt
   - 章節斷點 step-down → 觀眾拿到答案就走（教學特有）
   - AI 配音流失 → 換真人
4. 套 fix：
   - 前 15s 直接秀 outcome
   - 每 30-60s 一個新 open loop / mini-promise
   - 「最強的提示詞在最後」尾段 promise
   - 每 3-5 秒一刀
   - 配樂變化 + reveal 前靜音
5. 若是腳本草稿 → 列點建議重寫位置

**輸出**：
1. 留存曲線診斷（哪個 checkpoint 沒達標 + 原因）
2. 具體修補建議（哪句話/哪段改成什麼）
3. 開頭 + 中段 + 尾段 3 個 open loop 建議

### Mode C — Packaging War Room（MrBeast-tier title + thumbnail）

**觸發**：「幫我想標題 like MrBeast」「thumbnail 該怎麼設計」「title 要 A/B 哪幾個」「YT Test & Compare 該放哪 3 個」「我這個題目該怎麼包」

**步驟**：
1. 讀 [youtube-algorithm-mastery.md](youtube-algorithm-mastery.md) §4 Packaging
2. 套 MrBeast「Title + Thumbnail 先寫」法則
3. 生 **5-7 個 title 變體**，每個標明套了哪個 Galloway 框架（好奇/好處/規模/地位/對比）
4. 給「I Spent 50 Hours in Ketchup」test：每個 title 是否「具體數字 + 荒謬反差」？
5. **Thumbnail brief 3 個 variant**：
   - 1 個 safe（穩定 CTR）
   - 1 個 bold（高 CTR 嘗試）
   - 1 個對比/comparison（成本/工具/結果對比）
6. YT Test & Compare 設定建議（哪 3 個一起跑）
7. CTR 預測（依 niche outlier 跟你過去平均比較）

**輸出**：
1. 5-7 個 title 變體（標框架）
2. 3 個 thumbnail brief（含 One Face / One Object / One Question 對應）
3. YT Test & Compare 建議組合
4. 「Quality Click Ratio」紅線檢查（title/thumbnail 承諾 vs 影片 deliver 一致性）

### Mode D — Analytics Decode（YT Studio 數據判讀）

**觸發**：「這支表現怎麼判讀」「我的 CTR 太低」「為什麼觀眾不互動」「traffic source 都是 X 為什麼」「impressions 高但點擊低」「returning viewer % 怎麼解」「該不該放更多這種類型」

**步驟**：
1. 讀 [youtube-algorithm-mastery.md](youtube-algorithm-mastery.md) §6 Analytics Decode + §2 算法內部
2. 向用戶要數據（依需要）：
   - 影片表現：CTR / AVD / AVP / Retention curve / Like-to-view
   - Traffic source 分布：Browse / Search / Suggested / External / Notifications
   - New vs Returning viewer %
   - Realtime（若 <2hr 內）
3. **跟門檻對齊**（跟**你自己的**中位數比；本 kit 不提供代用數字 —— 後台讀數型門檻一律自填，見 [youtube-algorithm-mastery.md](youtube-algorithm-mastery.md) §TL;DR）：
   - CTR `<fill in>`、AVP `<fill in>`、1-min retention `<fill in>`、結尾 `<fill in>`
   - 流量結構：Suggested `<fill in>` / Search `<fill in>` / Browse `<fill in>`
     —— **重點是看「翻轉」不是看絕對佔比**：把點火片與沒點火片的結構並排，兩者應該是兩個世界
4. 診斷 root cause：
   - 高 impressions + 低 CTR → packaging 問題
   - 高 CTR + 低 AVD → 「Quality Click Ratio」紅線（克扣賺到的點擊）
   - 高 Browse / 低 Search → 仰賴粉絲，evergreen 沒打到
   - 高 Returning / 低 New → 觸及天花板，需要新題目或包裝
   - 中段 retention 沉沒 → 缺 pattern interrupt
5. 給 3-5 個具體下次改進

**輸出**：
1. 數據 vs 基準對照表（可視化哪裡達標/沒達標）
2. Root cause 診斷（最可能 2-3 個原因）
3. 下次改進清單（每條可動作）

### Mode E — Iteration Engine（事後迭代決策）

**觸發**：「這支發了一週 該不該換 thumbnail」「underperforming 該怎麼處理」「reupload 值不值得」「該不該刪這支」「該不該 unlist」「kill 還是繼續優化」

**步驟**：
1. 讀 [youtube-algorithm-mastery.md](youtube-algorithm-mastery.md) §7 Iteration Mindset
2. 確認時間窗口（⚖️ 定義以 [youtube-algorithm-mastery.md](youtube-algorithm-mastery.md) §2「48h vs day-14」為準）：
   - **0-48h：只讀不動**（換包裝會污染 Test & Compare 樣本）
   - **day-14 決策樹**：曝光停滯 + CTR 在點火帶以上 → 修留存；CTR 低於點火帶 → 才動包裝
   - **提前判死唯一例外**：seed fail 三聯徵（曝光停滯 + CTR 低於點火帶 + Browse 佔比趨近 0）**同時**亮
3. 應用「Test fast, kill fast」框架：
   - 2 次 swap 沒救起來 → **放掉，移動到下一支**
   - 不要刪除（unlist 比較安全）
   - 重點：知道**哪些題目/格式 flop 過**，加進 kill list
4. 若是長期 underperforming：
   - Reupload 通常不值得（2026 算法打擊 duplicate）
   - 例外：unlist 原版 + 大改（新 intro + 新結構）當新片發
5. MrBeast「Fix retention drop video-over-video」：
   - 看過往 5-10 支影片
   - 找共同 drop point（例「都掉在 4:12」）
   - 找這些影片 4:12 都做什麼 → 下支砍掉

**輸出**：
1. 動作建議（swap / kill / unlist / 繼續觀察）
2. 若 swap → 新 title/thumbnail 建議（含為什麼）
3. 若 kill → 為什麼，加進「kill list」（記住下次別重複）
4. 長期 pattern 觀察（若有多支數據）

---

## 核心原則

### 跟其他 skill 的觸發優先級

→ 對照表只維護一份：本檔頂部「該用哪個 skill」決策樹 + `autopilot-workflow.md`（完整 9 步 workflow）。

### 在 9 步 workflow 中的位置

本 skill 是 end-to-end workflow 的**第 1 + 5 + 6 + 8 + 9 步**（最多參與 — 包含 Pre-flight、Retention Surgery、Packaging War Room、Analytics Decode、Iteration），由 `video-autopilot` 自動 orchestrate。

→ **完整 9 步 workflow → 詳見 [autopilot-workflow.md](autopilot-workflow.md)**

用戶說「規劃我下一支X」會自動觸發 autopilot，autopilot 會呼叫本 skill 的 Mode A + B + C + D + E。

> 💡 若要**單一深度任務**（例如只要做留存診斷不要完整套件）— 直接觸發本 skill 任一 Mode；要 end-to-end 才用 autopilot。

### 核心心法

- ⭐ **Title + Thumbnail 先寫，影片再拍**（MrBeast 法則，不可協商）
- ⭐ **先問餵哪台機器**：推薦機 vs 搜尋機，兩台的 KPI／壽命／修法都不同（§2b）
- ⭐ **Satisfaction signals 現在 > CTR**（2025-2026 算法權重）
- ⭐ **Quality Click Ratio 紅線**：thumbnail 承諾 ≠ 影片兌現 = 比低 CTR 更糟
- ⭐ **Test fast, kill fast**：**48h 只讀、day-14 才決策**；2 次 swap 沒救 = 放掉
- ⭐ **只引用有出處的數字**（R35）：查無官方出處的門檻數字永不進稿，也不拿來判死自己的片
- ⭐ **KPI 門檻自己量**：CTR / AVP / 1-min retention / 結尾全部 `<fill in>`（後台讀數不外流，也不給代用值 —— 承上一條 R35）
- ⭐ **Shorts 跟長片去耦了**（2025 末確認）— 放心發 Shorts，不傷主頻道

### 跨 skill 一致性

- **Lean preference** 跨 skill：title 也偏 lean，不要堆 keyword
- **自己實測 > 外部 best practice**：已驗證的招牌數據（例如某長度 Shorts、實測過的發文時間、自家社群動員）優先於通用建議
- **資料留本地**：放本機資料碟，不要寫系統碟

---

## 檔案結構

```
knowledge/
├── youtube-algorithm-overview.md         ← 本檔（5 模式 + 觸發）
├── youtube-algorithm-mastery.md          ← 深度 playbook（MrBeast 戰術 + 算法內部 + §2b 雙機器模型
│                                            + retention/packaging/topic/analytics/iteration）
├── youtube-algorithm-2026.md             ← 2026 演算法變化（R15-R25）
├── viral-playbook-framework.md           ← 爆款判定三層 + 六站命中率系統 + 對抗驗證分級
├── ai-content-compliance.md              ← AI 內容合規 R26-R38 + 發布前 10 項 checklist
└── ai-content-compliance-sources.md      ← 53 條分級法源（查證用附錄，日常不必讀）
```
