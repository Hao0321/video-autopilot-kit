> 來自 video-autopilot-kit 開源知識庫 · MIT 授權

# Video Craft Overview（跨平台剪輯技法總覽）

策略 + 結構 + 演算法 — for YT 長片 / YT Shorts / IG Reels。本知識檔是**廣度 / 快速版**。**深度 YT-only + 頂級創作者級**請用對應的深度版知識檔。

## 🎯 該用哪個知識檔？（3-檔決策樹）

| 任務 | 知識檔 | Mode |
|---|---|---|
| 學新樣本 / 砍贅詞 / 從主題寫腳本 | 腳本風格檔 | A / B / C / D |
| **本檔**：跨平台規劃 / Title+Thumbnail 快速版 | 本檔（video-craft-overview） | **A / B** |
| **本檔**：長片改剪 Shorts/Reels / 跨平台 audit | 本檔（video-craft-overview） | **C / D** |
| 拍前頂級 Top 1% filter / 留存深度診斷 | 演算法深度檔 | A / B |
| 頂級 title+thumbnail（深度版）/ YT 數據深度 decode | 演算法深度檔 | C / D |
| 該不該換 thumbnail / kill 影片 | 演算法深度檔 | E |

## ⚡ Quick Cheat Sheet — 5 條鐵則

1. **Hook 前 3 秒定生死** — Shorts: VVSA 70-90%；Reels: 60%+ 3-sec hold；長片: 5 秒驗證 thumbnail 承諾
2. **YT 長片甜蜜點 7-15min**；**短影音片長是雙峰不是單一帶** —— 13-25s（梗/單一驚奇）或 45-60s（教學/demo）；**26-44s 是死區**（兩頭不沾：太長沒有梗的節奏、太短講不完一件事）（→ `shorts-mastery-2026.md` §2 S8）
3. **Loop Shorts replays 計 view**（2025-03 起）— 末尾無縫接首幀
4. **Shorts 跟長片 2025 末去耦** — 多發 Shorts 不傷主頻道
5. **跨平台貼必移除水印 + 重編 hook + 重切 safe zone + 錯開 60-90 min 發布**

## 📚 Reference Playbooks（深度技法 — 拍 short / 教學前必讀）

- **爆款短影片 Playbook** — 以一支高表現的教學類短影片 frame-by-frame 反推 7 大爆款剪輯技法（節奏 / 視覺層疊 / 權威堆疊 / 聲音設計 / promise 結構 / 情感收束 / 極端化）+ steal-and-apply 範本

---

## 4 個 Mode

### Mode A — Plan（前期規劃）

**觸發**：「幫我規劃一支關於 X 的影片」「我想拍 X 該怎麼開」「這個題目要怎麼下手」「該選 long-form 還是 Shorts」「該怎麼包這個題目」

**步驟**：
1. 讀規則本體 + 自驗數據檔
2. 釐清 4 個維度（不夠清楚就問用戶）：
   - **題目**：要講什麼
   - **平台**：YT long / YT Shorts / IG Reels / 多平台矩陣
   - **目標受眾**：本地中文 vs 全球（英文 dub）
   - **KPI 目標**：discovery / 留存 / 訂閱 / 變現
3. 推薦：
   - **平台選擇** + 理由（搭配自驗數據的「主題、循環動畫、地區」規則）
   - **長度建議**（依平台甜蜜帶）
   - **Hook 點子 3 個變體**（3 秒 hook，依平台規則）
   - **結構框架**（Hook → Value bomb → CTA 或 walkthrough）
   - **發文時間**（自己實測時段優先；外部基準補充）
4. 跟腳本風格檔配合：若用戶要直接生草稿，建議「規劃完接腳本風格檔的草稿生成 Mode」

**輸出格式**：
1. Plan 一頁摘要（平台 / 長度 / 結構 / 時間）
2. Hook 變體 3 個
3. 結構大綱（分段 + 每段秒數估算）
4. 可選下一步（接草稿生成 / 接 metadata 包裝）

### Mode B — Package（發布前包裝）

**觸發**：「幫我想 title」「幫我想 thumbnail」「幫我寫 description」「幫我選 hashtag」「這支該打什麼 tag」「該怎麼包裝這支影片」

**步驟**：
1. 讀規則本體
2. 確認：平台 / 影片主題 / 主要 keyword / 目標 audience
3. 給出：
   - **Title 3-5 個變體**（依平台格式：長片 60 字內 + keyword、Shorts 短而 hook、Reels caption≤150 字）
   - **Thumbnail brief**（≤5 字 + 臉部表情 + 配色 + 高對比）
   - **Description**（200-300 字、前 125 字含 keyword、含 chapters 若 ≥10 min）
   - **Hashtag**（YT 長片 3-5 / Shorts 3-5 含 #Shorts / Reels 2-3 高度相關）
   - **發文時間建議**（依平台 + 目標地區）
   - **CTA placement 建議**（Pinned comment hub / end screen）

**輸出格式**：條列清單，每項可直接複製貼上

### Mode C — Repurpose（跨平台改寫）

**觸發**：「這支長片可以剪幾支 Shorts」「我想把這個發到 IG Reels」「幫我從 long-form 找 Shorts 素材」「Shorts 跟 Reels 該怎麼差異化」

**步驟**：
1. 讀規則本體的 Cross-Platform 段
2. 看用戶提供的長片內容（章節 / timestamps / 重點）
3. **識別可剪段**：每段需可獨立成片（單一 tip / demo / hot take / 情緒反應）
4. **為每段重編 hook**（不能直接從中間剪 — 前 3 秒必須是新的 hook）
5. **差異化建議**：
   - Shorts 版：#Shorts、口播念 keyword、Loop 結構考量、片長取雙峰其一（13-25s 或 45-60s，避開 26-44s）
   - Reels 版：IG-native audio、Caption 第一行 hook、shares-friendly CTA
   - 共用：移除其他平台水印、safe zone 重切、錯開 60-90 分鐘發布
6. **引流回長片**：Pinned comment + end screen 建議

**輸出格式**：
1. 可剪段清單（每段標 timestamp + 適用平台 + 重編 hook 建議）
2. 差異化 cheat sheet（Shorts vs Reels 差異）

### Mode D — Audit（事後檢討）

**觸發**：「這支表現如何分析一下」「我這支 Shorts 流量為什麼差」「幫我看 retention 為什麼掉」「為什麼 CTR 那麼低」「這支該不該推類似的」

**步驟**：
1. 讀規則本體 + 自驗數據檔
2. **收集數據**（向用戶要）：CTR / AVD / VVSA / Completion rate / Likes-per-view / DM shares（依平台）
3. **跟基準對齊**（規則本體的數字）
4. **診斷可能原因**：
   - Hook（前 3 秒）— swipe-away / drop-off
   - Retention 中段 — pacing / 結構
   - Title/Thumbnail — CTR
   - SEO — discovery
   - Timing — 排隊到 dead zone
   - Niche consistency
5. **給 3-5 個具體下次改進建議**（可直接動作）

**輸出格式**：
1. 數據 vs 基準對照表
2. 診斷（最可能 2-3 個原因）
3. 改進清單（每條一行可動作）

---

## 核心原則

- **用戶實測 > 外部 best practice**：自驗數據（自己測過的最佳 Shorts 開頭長度、自己測過的發文時段、地區排序）優先於通用 best practice
- **跟腳本風格檔互補**：
  - 腳本本體（voice、招牌、boilerplate）→ 腳本風格檔
  - Title / Thumbnail / Description / Hashtag / Timing / 平台策略 → 本檔
  - 完整寫一支新影片 = Plan（本檔 Mode A）→ Generate（腳本風格檔草稿生成）→ Package（本檔 Mode B）
- **跨平台一致性**：同一題目可規劃 long + Shorts + Reels 矩陣，但每平台需獨立 hook + caption + safe zone
- **Lean preference 跨檔**：title / description 也偏 lean，不要堆關鍵字
- **回報要短**：Plan 給摘要 + 3 變體；Audit 給診斷 + 改進清單；不貼整 playbook

---

## 檔案結構

```
knowledge/
├── video-craft-overview.md   ← 本檔（4 模式 + 觸發）
└── video-craft-playbook.md   ← 規則本體（外部 2024-2026 best practices）
```

> 另外建議你自己開一份「我實測過的數據」檔（放你自己的工作資料夾，**不入公開 repo**）：
> 你自己頻道量到的數字權重應該高於任何外部 best practice。本 kit 不出貨這種檔——
> 別人的實測值套到你頻道上沒有意義。

## 在 end-to-end workflow 中的位置

本檔是 end-to-end workflow 的**第 2 + 7 步**（跨平台 Plan + Description/Hashtag Package），由 autopilot 主檔自動 orchestrate。

用戶說「規劃我下一支X」會自動觸發 autopilot，autopilot 會呼叫本檔的 Mode A + B。

> 💡 若用戶要**單一決策片段**（例如只要規劃跨平台不要完整套件）— 直接觸發本檔任一 Mode；要 end-to-end 才用 autopilot。
