> 來自 video-autopilot-kit 開源知識庫 · MIT 授權

# Script Style Framework — 學會「你自己」的 YT 腳本風格

這份框架教你怎麼用一個 4-mode 流程，把「你自己的」影片腳本風格學起來、存成可重用的 profile，然後用它優化既有草稿或從零 ghost-write 新稿。

**重要：本文只發框架。任何具體的 `style_profile.md` 內容與 `samples/` 樣本都屬於原作者個人聲音，不在本知識庫內。**
**你必須自己餵自己的腳本、建立你自己的 profile 與樣本庫。** 下面所有「招牌詞 / particle / 開場 Pattern」都是「示意佔位」——它們示範的是**該抓哪一類特徵**，不是要你照抄某個人的口頭禪。請把它們替換成你自己稿子裡實際反覆出現的東西。

---

## 📍 這份檔在腳本三支柱的哪一柱

一份腳本有三個**互相獨立**的失敗軸，別把它們混在一起修：

| 支柱 | 壞掉長什麼樣 | 去哪 |
|---|---|---|
| 1. **語氣** | 很順，但**不像你**寫的 | **本檔**（4-mode 流程）＋填空骨架 [`../templates/style_profile.template.md`](../templates/style_profile.template.md) |
| 2. **觀眾語言** | 像你，但**路人聽不懂** | [`script-retention-craft.md`](script-retention-craft.md) §1（四層詞表怎麼從自己樣本建） |
| 3. **留存節奏** | 聽得懂，但**看不下去** | [`script-retention-craft.md`](script-retention-craft.md) §2 |
| 機械層 | 以上三柱能自動化的部分 | [`../src/longform_maker/script_gate.py`](../src/longform_maker/script_gate.py) — 錄音前 `gate(text)` PASS 才錄 |

本檔只管**支柱 1**：怎麼把「你自己的聲音」變成可重用、可累積的 profile。

---

## 0. 路徑與資料原則（請改成你自己的）

- 所有 profile 與樣本存在你自己的工作資料夾，例如 `<你的專案>/skills/script-style/`。
- **資料留在本地**：profile 與樣本只存本地，不上傳。
- **累積，不覆蓋**：每次 Learn 都疊加，除非你明說要刪。
- **樣本檔簡潔**：只放原文，不存分析。

建議檔案結構：

```
script-style/
├── SKILL.md              ← 指令 + 贅詞辨識準則（本框架）
├── style_profile.md      ← 你累積的 style profile（會頻繁更新；自己建）
│                            填空骨架 → templates/style_profile.template.md
├── audience_vocab.json   ← 觀眾語言四層詞表（script_gate 吃這個）
│                            骨架 → templates/audience_vocab.example.json
└── samples/              ← 你的原始腳本存檔（YYYY-MM-DD_NN.md；自己餵）
```

---

## 🎯 該用哪個 mode？（決策樹）

| 任務 | Mode |
|---|---|
| 學新樣本 / 看 voice profile | **A / C** |
| 砍腳本贅詞 / 從主題寫腳本 | **B / D** |

（在更大的影片製作流程裡，這個腳本框架通常負責 Generate + Optimize 兩步；跨平台規劃、title、留存診斷、thumbnail 等屬於其他模組的範疇。）

## ⚡ Quick Cheat Sheet — 6 條鐵則（這裡的「X」是佔位，填你自己的）

1. **找出你自己的 fingerprint 詞 / particle** — 那些你每篇都會冒出來的口頭禪、語尾助詞、強斷言句式，是招牌，**絕對保留**。
2. **Lean：砍 20-25% 贅詞但招牌不動**（多數人會偏好 leaner output）。
3. **早期樣本降權**：你最早期的稿子風格還沒定型，Generate 時主要拉「風格已穩定」那批近期樣本（時序權重）。
4. **Sign-off / Boilerplate 通常有數個變體**（例如：乾淨版 / 帶你個人 typo 的版本 / 含社群 CTA 的版本 / 早期已過時的版本）——把仍在用的整段保留不動，過時的別套。
5. **個人化 typo / 慣性錯字**（每個人都有自己常打錯的字）已成個人標誌——註解可以但不必每次強制修。
6. **像你 ≠ 可以交稿**：本框架只保證支柱 1。交稿前還要過**觀眾語言**與**留存節奏**兩柱
   → [`script-retention-craft.md`](script-retention-craft.md)，機械檢查 → `script_gate.gate(text)` PASS。

---

## 四個模式

### Mode A — Learn（學習樣本）

**觸發**：你貼上腳本並表示「學這篇」「加入樣本」「分析這篇」「餵腳本」。

**步驟**：
1. 讀取 `style_profile.md`（沒有就新建空檔）。
2. 從新樣本提取：
   - **Mode 判定**：把你的內容分成幾個 sub-mode（例如：高能量 Demo / 反思分享 / 產品更新 / 脆弱開箱 / 實用教學 / 生活推薦 / Vlog——請依你頻道實際內容類型自訂這套分類）。
   - **開場 Pattern**（給每種開場法編號，累積成你自己的 Pattern 庫）
   - **慣用句式 / 節奏 / particle / 結尾**
   - **新詞彙 / slang / typo 模式**
   - 區分**贅詞 vs 招牌**（見下方準則）
3. **合併，不覆蓋**寫入 `style_profile.md`。衝突 → 標 ⚠️。
4. 原文存 `samples/YYYY-MM-DD_NN.md`，只存原文不存分析。
5. 更新樣本記錄。
6. 簡短回報：**3-5 個最關鍵新特徵 + 總樣本數**。不貼整 profile。
7. 若順便要求「也清一下」→ 接 Mode B。

### Mode B — Optimize（優化既有草稿）

**觸發**：你提供草稿並表示「依我風格優化」「刪贅詞」「改寫這篇」「優化用詞」。

**步驟**：
1. 讀 `style_profile.md`。
2. 樣本數 < 3 篇先警告（profile 還不夠穩，優化會不準）。
3. **Mode 判定**：判定草稿屬於哪個 sub-mode，告知後依該 mode 規則優化。
4. 應用優化（依下方贅詞辨識準則）：
   - 刪真贅詞
   - 用偏好詞彙替換泛用/通稿詞
   - 重整節奏向典型句長靠攏
   - **保留招牌**
5. **輸出格式**：
   1. 修改後全文
   2. 關鍵改動清單（每條一行：改什麼 → 為什麼）
   3. 刻意保留清單（哪些招牌不動 + 為什麼）
6. **避免過度優化**：失去辨識度寧可不改，在保留清單說明理由。

### Mode D — Generate from topic（依主題 ghost-write 新草稿）

**觸發**：你提供主題/想法/截圖 + 「依我風格幫我寫一篇關於 X 的草稿」「ghost-write」「我想寫一篇 X 主題」「幫我從零寫一支影片」。

**步驟**：
1. 讀 `style_profile.md`。
2. **Mode 判定**：依主題對應你自訂的 sub-mode。下表是一個**範例對應表**，請替換成你自己的內容類型與對應 mode：

   | 主題類型（範例） | Mode（範例） |
   |---|---|
   | 工具 demo | 高能量 Demo |
   | 自家產品 bug/更新溝通 | 產品更新（道歉結構） |
   | 頻道經營/創作者反思/數據分享 | 反思分享 |
   | 興趣開箱/個人 hobby | 脆弱開箱 |
   | DIY/居家/實用教學 | 實用教學 |
   | 食物/生活推薦 | 生活推薦 |
   | 旅遊紀錄/日常 Vlog | Vlog（時間戳結構） |

3. **選開場 Pattern**（下面是開場法的**功能分類**，不是要你照唸的句子。
   每一類你都要回自己的樣本裡撈一句真的講過的，填進 `style_profile.md` §4.1 的 Pattern 庫）：
   - **宣告型**：直接說出今天要給什麼，再 reveal 主角（多數情況的主力）
   - **警示型**：先製造「這件事你需要知道」的緊迫感（重大更新／開箱）
   - **致歉型 cold-open**：先處理久未更新／進度落後，再進主題
   - **轉向型**：明說「這支跟平常不一樣」，替新類型鋪路
   - **共識型**：先建立「這個東西你應該聽過」，再往進階推（續集／進階教學）
   - **賽事型 hype**：把新品／新版本框成一次大事件
   - **反問型 reverse hook**：用一個問句接住前一段畫面或前情提要
4. **選結構**（可混搭）：
   - 線性 walkthrough（介面／流程導覽型內容多半必用）
   - Origin story 公式（講自己做的東西：痛點 → 動機 → 成果）
   - 平衡式評論（評第三方產品，含缺點段）
   - 更新／修正溝通結構（自己交付的東西出問題時的 accountability 版）
   - 比較測試 framing（多個對象同條件測試）
   - Preemptive concession（先承認對手強項，再重新定義評選標準）
   - 時間戳 narrative（Vlog 必）
5. **依招牌密度寫稿**（見下方密度表）。
6. **結尾**：
   - 高能量 → 帶你個人風格的 Boilerplate 變體，或乾淨版
   - 低能量 → 短 sign-off，或「任務完成」型收尾（做完一件事就收）
   - Vlog → 通常開放結尾（連載）
   - 反思分享 → Inspirational CTA（把觀眾放進成功位置的那種收尾）
7. **輸出格式**：
   1. 完整草稿
   2. 招牌使用清單（map 到 profile 條目，解釋為什麼這樣寫）
   3. 可調整方向（3-5 個明確 iterate 維度，如「能量過高/低」「Pattern 替換」「篇幅」）

### Mode C — Review（檢視 profile）

**觸發**：「看一下我的風格 profile」「目前學到什麼」「review style」「我的腳本風格現在長怎樣」。

**步驟**：讀 `style_profile.md`，做條列重點摘要。重點：總樣本數、Mode 分布、最具辨識度的 3 個招牌、最該砍的 3 個贅詞、最該替換的 3 組詞。

---

## ⭐ 贅詞辨識準則（Mode B / D 必讀）

這套準則是**通用的**，不依賴任何特定作者的詞——它教你怎麼分辨「砍掉不掉 voice 的填充」vs「砍了會掉 voice 的招牌」。

### 真贅詞（可砍，砍了不掉 voice）

- **同句重複 intensifier**：兩個以上的程度副詞疊在同一個形容詞前 → 留最強的那一個
- **緊鄰評估堆疊**：兩三個形容詞連發 → 留 1
- **重複代名詞**：同一個短句裡連續 2-3 個第一人稱
- **重複時間標記**：同段出現兩個指向同一時點的時間狀語
- **純連接虛詞連發**：同一段裡同一個連接詞出現 3+ 次 → 砍 1-2
- **通用心靈雞湯**：任何抽掉主題後仍然成立的勵志句
- **過長 self-flex**：超過 1 句的自誇
- **超量列舉**：選單列 8 項 → 留 5-6；舉例 4 個 → 留 2-3
- **結尾 community flex**：boilerplate 已經有社群 CTA，正文不要再重述一次社群近況
- **冗餘 wrapper**：「我全都做了」＋列舉＋「整合起來」→ 列舉本身已經表達完整性，砍掉包裝句

### 招牌（必保留，砍了會掉 voice）

**這裡列的是「要去你 profile 裡找哪一類東西」，全部是分類名稱，沒有例句 ——
刻意的：一放例句你就會照抄，而那會是別人的聲音。每一格的答案只在你自己的舊稿裡。**

**詞彙類（找你自己的高頻 fingerprint）**：
- 你最強的 fingerprint 副詞 / 動詞（多數人有一兩個每篇必出現的）
- 你的強斷言句式（你把「這個很好」推到最高級時的固定講法）
- 你破第四面牆的親密語（你從敘述切換成「直接跟觀眾講話」時用的那句）
- 你的 accessibility 用語（你用來把門檻講低的那組詞：不用會、不用懂、自己也能做…）
- 你的 emphasis 句式（你替一段畫重點時的固定開頭）
- 你的 origin formula（你講「怎麼開始的」時的慣用框架）
- 你的 identity slogan（你反覆用來定義自己 / 頻道身分的那句話）

**Particle / Punctuation（找你自己的語尾與標點習慣）**：
- 你慣用的語尾助詞（華語圈創作者多半有 3-5 個固定的，去逐字稿數哪幾個最常出現）
- 你慣用的驚嘆／波浪／全形半形習慣（含密度：一篇大概幾次）
- 你的慣性 typo / 錯字（每個人都有；已成個人標誌就不必每次都修）

**結構**：
- 線性 walkthrough（逐段帶看介面／流程時的固定句型）
- 時間戳 narrative（Vlog）
- Sign-off Boilerplate 整段（保留仍在用的變體；過時的早期版本不要套）
- 物件擬人化（你會不會拿指人的代名詞去指工具／軟體／公司——若這是你的習慣就保留）

### 密度上限參考（單篇）

下表的「招牌」欄是**範例佔位**——請把它換成你自己 profile 裡的招牌，並依你自己稿子校準合理密度。重點是「招牌也有過量警訊：超過某個次數就從特色變稀釋」這個原則。

| 招牌（範例） | 建議密度 | 過多警訊 |
|---|---|---|
| 你的主 fingerprint 副詞 | 4-8 次 | OK（招牌） |
| 你的高頻強斷言詞 | 4-6 次 | 9+ 次過密 |
| 你的驚嘆／語尾標點 | 6-10 次 | 全篇每句必加過密 |
| 你的破第四面牆句 | 1-2 次 | 3+ 次過密 |
| 你的 accessibility 招牌句 | 1-2 次 | 3+ 次重複 |
| theme word（單篇主題詞） | 2-3 次 | 4+ 次稀釋 |
| 同一招牌句重複 | ≤ 2 次 | 3+ 次過密 |

---

## 核心原則

- **累積，不覆蓋**：每次 Learn 都疊加，除非你明說刪。
- **辨識度 > 整潔度**：贅詞與招牌邊界模糊時，傾向保留。
- **★ Lean preference**：
  - 多數人偏好 leaner output
  - Mode B / D 可主動砍 20-25% bloat
  - 但招牌必須保留
  - 若覺得「贅詞太多」→ 再瘦一輪，目標再減 15-25%
  - **Mode D 第一版就直接走 lean 路線**，不要先給太肥版本
- **資料留在本地**：profile 與樣本只存本地，不上傳。
- **樣本檔簡潔**：只放原文。
- **回報要短**：Learn 不貼整 profile；Optimize/Generate 列關鍵清單即可。

---

## 怎麼開始（給第一次用的人）

1. 建好上面的檔案結構，把 [`../templates/style_profile.template.md`](../templates/style_profile.template.md) 複製成你的 `style_profile.md`（全部留白）。
2. 跑 Mode A，餵你 **5 篇左右**過去寫過、你自己最滿意的腳本。
3. 跑 Mode C 看 profile 抓到了什麼——校準、刪掉抓錯的、補上漏掉的招牌。
4. 累積到 **10 篇以上**，profile 才夠穩，Mode B / D 才會準。
5. 做一次**觀眾語言詞表審計**（模板 §5，30-60 分鐘），導出 `audience_vocab.json`
   → 從此「觀眾聽不懂」變成 `script_gate` 擋得下來的東西，不再靠你當下記得。
6. 之後每寫一篇新稿就回頭 Mode A 餵進去，順手把 gate 報的 `lang.unknown_term` 新詞判級入表。

---

## 相關

- [`script-retention-craft.md`](script-retention-craft.md) — 支柱 2＋3：觀眾語言四層詞表怎麼建、留存節奏 craft
- [`../templates/style_profile.template.md`](../templates/style_profile.template.md) — 本框架的填空骨架（含詞表審計工作表）
- [`../templates/voice_profile.template.md`](../templates/voice_profile.template.md) — 5 分鐘最小版 voice profile（先開工用）
- [`../src/longform_maker/script_gate.py`](../src/longform_maker/script_gate.py) — 機械層
