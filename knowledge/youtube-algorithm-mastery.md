# YouTube Algorithm Mastery — Deep Playbook

> 來自 video-autopilot-kit 開源知識庫 · MIT 授權

> YT 演算法深度 + MrBeast 戰術，**為混合型教學頻道（軟體教學 / AI 工具教學 / 旅遊 Vlog）改寫**
> 來源：MrBeast 內部洩漏文件、Joe Rogan / Lex Fridman / Colin & Samir 訪談、Creator Insider (Todd Beaupré)、Paddy Galloway 分析、Retention Rabbit 2025 benchmarks
> 標記：[TRANSFERS] / [PARTIAL — adapt] / [DOESN'T TRANSFER, MrBeast-specific]
>
> ⭐ **2026 重大 supplement 要點**：
> - Dec 2025 Browse 砍長片 -80%（每週 1 部撐不過 2026）
> - 部分地區 Hype button beta（提早卡位 = unfair advantage）
> - Travel Vlog 長片大塌方（AVD -19%）→ Shorts 必轉
> - Satisfaction stack：**External Share 比 like 強 5-8x**
> - Tutorial retention 修正：**45-55%**（不是 42.1%），good abandonment 2026 不罰
>
> 📚 **Niche-specific playbook 方向**：
> - 🎓 教學軌道（軟體 + AI 工具）：AI 工具 48h ship / pillar 內容定期重做 / Auto-dub 多語 / 螢幕錄影 retention 工程
> - 🎒 旅遊 Vlog：Shorts 主力 / 精準地點 tag / 雙語 caption
>
> 🎰 **規劃任何一支片之前先讀 → §2b 雙機器作戰模型（推薦機 vs 搜尋機）**：
> 兩台機器的曲線形狀／壽命／判讀指標／修法完全不同，用同一組 KPI 看會得出互相矛盾的結論。
> 內含「用你自己的 3-5 支片校準門檻」的 SOP（§2b-5）。
>
> 🛡️ **AI 內容合規（發布前必跑）** → [`ai-content-compliance.md`](ai-content-compliance.md)
> （R26-R38 + 發布前 10 項 checklist；法源 53 條在
> [`ai-content-compliance-sources.md`](ai-content-compliance-sources.md)）

---

## 🎯 TL;DR — 每週 KPI 表（**格子留空，你自己填**）

> 📏 **這張表刻意沒有數字。** CTR／AVP／1-min 留存／結尾留存**全都是後台讀數**——
> 第三方看不到別人頻道的這些值，所以任何一個「沒有出處的具體門檻」在定義上就是**某個人的 Studio 讀數**。
> 本 kit 不刊任何頻道（包括原作者的）的 analytics 讀數
> → 規矩全文見 [`viral-playbook-framework.md`](viral-playbook-framework.md) 檔頭「本檔的數字規矩」第 1 類。
>
> 早期版本這裡印過一組具體門檻（每個 niche 一列 CTR/AVP/留存），並標成「工作門檻，不是公開基準」。
> **換標籤不是移除** —— 數字原封不動留在原地，照抄的人一樣會拿它判死自己的片。所以現在整組改成 `<fill in>`。
>
> **怎麼填**：§2b-5「用你自己的 3-5 支片跑同一組對照」——
> 把已發布影片按「有沒有被演算法接走」分兩堆，看兩堆的讀數在哪裡分界，分界值就是你的門檻。
> 樣本 <5 支標 ⚠️ PLAUSIBLE，當 checklist 用、不當鐵閘；每累積 3 支重算一次。
>
> 🚩 **Shorts 那格特別提醒**：流傳的「留存 70% 以下壓全頻道分發」那一族數字經查證**查無任何官方出處**，
> 是第三方部落格自行歸納的（→ [`ai-content-compliance-sources.md`](ai-content-compliance-sources.md) `§algo-11`，
> 以及 [`ai-content-compliance.md`](ai-content-compliance.md) **R35：只引用有官方出處的數字**）。
> **不要把它寫進你的教學內容，也不要拿它判死自己的片。**
> Shorts 的續看率門檻請按 [`viral-playbook-framework.md`](viral-playbook-framework.md) §1b 用自己的 3-5 支片校準。

| 影片類型 | CTR | AVD/AVP | 1-min 留存 | 結尾留存 |
|---|---|---|---|---|
| **長片（5-10 min 教學）** | `<fill in>` | `<fill in>` | `<fill in>` | `<fill in>` |
| **長片（10+ min 教學）** | `<fill in>` | `<fill in>` | `<fill in>` | `<fill in>` |
| **長片（旅遊 Vlog）** | `<fill in>` | `<fill in>`（注意 niche 已塌方 -19%，別沿用舊值） | `<fill in>` | `<fill in>` |
| **Shorts** | n/a（無縮圖可點 → 看首幀+前 1 秒） | `<fill in>` 續看率 | n/a | `<fill in>` 循環率 |

唯一帶出處的一行：教學類 **45-55% retention 健康範圍**（[Hootsuite 2026](https://blog.hootsuite.com/youtube-algorithm/) — 比 Retention Rabbit 2025 的 42.1% 提高）。
這是**跨頻道的產業區間**，不是你的門檻——拿它當方向感，門檻仍然照上表自己量。

⚠️ **旅遊 Vlog niche 警告**：8+ min travel vlog AVD YoY **-19%**，CTR -22%；travel Shorts +214%。**行程類素材優先剪 5-8 個 Shorts 而不是 12 min 長片**。

---

## 1. MrBeast 戰術（已標明哪些能移植）

### 「Title + Thumbnail 先寫，影片再拍」[TRANSFERS DIRECTLY]
- MrBeast 內部公開法則：**先決定 title+thumbnail，再設計影片去 deliver**
- 反向工程：用「我想做這個 thumbnail」推回「那影片該長什麼樣」
- 應用：開拍前先寫 3 個 title 變體 + 1 個 thumbnail concept，**沒有想到強的就不拍**

### 「前 5 秒 = 完整 premise」[TRANSFERS]
- MrBeast：「hey guys welcome back」零容忍。重寫 intro **數十次**直到 5 秒內塞完整 premise
- Joe Rogan #1788：「minute 1 wins/loses retention」
- 應用：**第一幀直接秀完成的成果**（例：「這個提示詞 12 秒寫出爆款 Shorts 腳本 — 看下去」），不要「今天我要來教大家...」鋪陳

### Minute 1-3「crazy progression」[PARTIAL — adapt]
- MrBeast 公式：minute 1 抓住 → minute 1-3 用「progression」鎖投資 → minute 3 第一次「re-engagement spectacle」→ halfway 第二次
- **教學頻道改寫**：
  - Minute 1 = 秀完成品
  - Minute 3 = 第二個工具 / 意外轉折 reveal
  - Halfway = before/after 對比

### 「One Face, One Object, One Question」thumbnail 規則 [TRANSFERS]
- 看不清楚 = 失敗
- **Thumbnail 文字 ≠ Title 重複**，要當第二個 hook
- 應用：thumbnail 至少做 3-5 variant，用 YT Test & Compare 跑

### 「I Spent 50 Hours in Ketchup」題目原則 [TRANSFERS]
- 「I Spent 50 Hours In My Front Yard」= 不能點
- 「I Spent 50 Hours In Ketchup」= 100x viral
- 差異：**具體數字 + 荒謬反差**
- 應用：
  - ✗「我做了一個 AI 工具」
  - ✓「我讓 AI 在 1 小時內蓋完整個 YouTube 頻道」（具體數字 + 具體工具 + 具體結果）

### MrBeast 3 個唯一在意的指標 [TRANSFERS]
**CTR + AVD + AVP**（Average View Duration + Average View Percentage）— 不管讚數、留言、訂閱

### 「$10K wow factor budget rule」[PARTIAL]
- 「花超過 $10K 在不會出現在畫面上的東西，三思」
- 應用：**每分鐘的製作工時都要對應到觀眾看得到的東西**。不要花 4 小時做炫炮 intro 動畫，把時間花在 30 秒 demo clip 上

### MrBeast 招牌格式 [PARTIAL — adapt for AI tutorials]
- 原版：「last to leave」「stair stepping」「vs comparisons」「time-pressure challenges」
- 教學移植：
  - 「免費 AI vs $200/月 AI」（stair stepping）
  - 「我給 5 個 AI 同一個任務」（vs）
  - 「AI in 1hr vs 10hr vs 100hr」（time pressure）
  - 「最後一個沒當機的 AI 勝出」（last to leave）

### 不要移植的 [DOESN'T TRANSFER]
- 6 人 thumbnail 團隊
- $500K 單支影片預算
- A/B/C player 換人法
- $10K 一張 thumbnail

---

## 2. YouTube 算法內部機制 2024-2026

### 4 個流量面（surfaces）

| Surface | 主要訊號 | 對你的意義 |
|---|---|---|
| **Browse（主頁）** | 個人歷史 + 相似觀眾互動 + freshness | 主要靠**現有粉絲 + 相似頻道粉**；thumbnail 是門票 |
| **Suggested（推薦）** | 別人看完 X 後看了什麼 → 你被推 | 影片是 sequencing chain 中一個 node；競爭對手影片的「下一支」就是你 |
| **Search（搜尋）** | Title/description/transcript keyword + watch-time-per-impression | **教學頻道的複利引擎**，evergreen 影片靠這個 |
| **Notifications/Subs** | 鈴鐺點擊率 + 推送訂閱比例 | <5% impressions for most channels，satisfaction proxy |

→ 教學頻道**健康 mix**：Suggested 30-40% / Search 20-30% / Browse 15-25% / 其他 split

### 2024-2026 算法權重位移（Marketing Agent 2025 分析）

| 訊號 | 2023 權重 | 2025 權重 | 變化 |
|---|---|---|---|
| CTR | 35% | 20% | ↓ |
| AVD | 35% | 25% | ↓ |
| **Viewer Satisfaction** | 15% | **35%** | ⭐ 最大上升 |
| Returning Sessions (7d) | 10% | 15% | ↑ |

→ **Satisfaction signals 現在比 CTR 還重要**
- 來源：YT 官方「Valued Watch Time」概念（2024 中）— 觀眾事後評分 4-5 星才算「valued」
- 你不能直接看到 satisfaction，但可以透過：**減少「題騙肉鬆」**（thumbnail 承諾→影片不兌現的落差越小越好）

### 2024-2026 確定算法變化

- ⚠️ **2024 中**：Satisfaction surveys 正式高過 raw watch time
- ⚠️ **2024 末**：AI content 強制揭露；沒標的 AI 內容被降推
- ⭐ **2025 末**：**Shorts 跟長片完全去耦**
  - 多發 Shorts 不再傷長片（也不再餵長片）
  - Shorts 的訂閱仍計入 monetization 門檻
  - 但**不會自動把 Shorts 觀眾餵給長片** → Shorts 現在是獨立 funnel
- ⛔ **2025-12-21**：**Browse feed 長片 slot 砍 -80%**（12 → 2 個）→ 整體觀看 -30%（[Dataslayer](https://www.dataslayer.ai/blog/youtubes-december-2025-algorithm-update-browse-feed-cut-long-videos-by-80)）
  - 沒砍：Subscribed feed / Suggested / Search
  - 砍的：冷流量 Browse = 新觀眾入口
  - **對你影響**：每週 1 部撐不過 2026，必須轉 1 長片+3-4 Shorts/週（特別 Vlog niche）
- 🔥 **2026 起 Hype button 分批開放**（先在少數國家 beta，2026-07 已擴到數十國 — 見 `youtube-algorithm-2026.md` R25）→ 先確認你的地區在不在名單，在就提早卡位 = unfair advantage
- ⚠️ **2026/1**：YT AI label 強執法 — 一波下架 16 channels (4.7B views/$10M/yr)。AI 工具教學的生成片段**必 disclose**
- ⚠️ **2026 二月**：Browse feed 從 broad topic clusters 轉 micro-niche history clustering → niche 頻道反而獲利

### Exploration phase + 「48h vs day-14」判死時序 ⚖️ **本 kit 的單一真值來源**

> 這一段是 kit 內**唯一**的發布後判死時序定義。
> `youtube-algorithm-overview.md`（Cheat Sheet #4 / Mode E）、`youtube-algorithm-2026.md`（R18）、
> `viral-playbook-framework.md`（§2 站6）全部以本段為準；讀到別處有更早的判死線，以這裡為準。

**機制**：新片先進一個小 seed 池，給訂閱者 + 相似興趣觀眾測試；表現好才逐輪擴圈。
（承 `youtube-algorithm-2026.md` R18 的「100-1,000 impressions」量級 —— ⚠️ **那是社群歸納的量級不是官方公布值**，
依頻道規模差很多；**你自己的 seed 池上緣自己量** → §2b-5。）

**⚠️ 「48h 定生死」是過時說法**（官方口徑已澄清）：評估期會**持續數週**，不是兩天。
早期版本的本檔寫過「頭 48h flop → 很難再起來」，**那條已作廢**。

**所以發布後的時序是**：

| 時間 | 做什麼 | **不要做什麼** |
|---|---|---|
| day-0（1h 內） | 餵熱 seed：自有社群一則 + 平台原生入口（社群貼文 / Shorts 入口） | — |
| 0-48h | **只觀察，不動包裝** | ❌ **禁 panic 換標題／縮圖** —— 會污染 Test & Compare 樣本，等於把正在跑的測試自己重置 |
| day-14 | 跑決策樹（見下） | ❌ 別在這之前判死一支慢燒的片 |

**day-14 決策樹**：
- 曝光**停滯** + CTR **在你的點火帶以上** → 問題在留存，修留存不動包裝
- CTR **低於點火帶** → 這時才動包裝（Test & Compare 跑標題+縮圖組合）

**唯一的提前判死例外 —— seed fail 三聯徵**（三個訊號**同時**亮才算）：
首 48h「曝光停滯在 `<fill in>` 以下 **＋** CTR 低於你的點火帶 **＋** Browse 佔比趨近 0」。
三個一起亮 = 這支根本沒被發出去，不是慢燒，可以直接啟動包裝重測、不必苦等 14 天。
**只亮一兩個不算** —— 那正是慢燒推薦浪的常見長相。門檻值自己量（→ §2b-5）。

### Dislike 怎麼處理
- 不再硬扣分
- 演算法用 *為什麼* 不喜歡（survey + sentiment）
- ⚠️ **「Not interested」/「Don't recommend channel」是真的會壓制的訊號**

---

## 2b. 雙機器作戰模型（推薦機 vs 搜尋機）

> 上面 §2 的「4 個流量面」是**平台怎麼分發**；這一節是**你怎麼下注**。
> 把四個 surface 收斂成兩台機器，是因為它們的**曲線形狀、壽命、判讀指標、修法**完全不同 ——
> 用同一組 KPI 去看兩台機器，會得出互相矛盾的結論（「這支明明留存最好卻沒量」多半就是搞混了）。
>
> ⚠️ **模型可移植，數字不可移植。** 本節不刊任何頻道的 analytics 讀數；
> 所有門檻寫 `<fill in>`，附「怎麼用你自己的 3-5 支片校準」的方法段（§2b-4）。

### 2b-1 兩台機器的形狀

| | **推薦機**（Browse / 首頁 / Suggested） | **搜尋機**（Search / 平台內搜尋） |
|---|---|---|
| 誰發動 | **演算法主動推** | **人主動找** |
| 曲線形狀 | **burst**：曝光短時間內指數放大，衝完就掉 | **平台期**：單日量小，但**月量不衰** |
| 壽命 | **短**（浪有頭有尾，用你自己的曝光曲線量 → §2b-4） | **長**（evergreen 庫存，發完很久還在跑） |
| 單片天花板 | 高（爆的都是這台） | 低（但**會累積**：每多一支可搜題就多一份庫存） |
| 主要閘門 | **CTR 過閘 → 才放量**（沒過閘，留存再好也不分發） | **詞根卡位 + 內容真的答到那個問題** |
| 適合的題型 | 成就故事 / 蛻變 / 反差 / 賭注型 | 工具教學 / 具體問題 / how-to / 版本更新 |
| 你贏的方式 | 包裝賭 CTR + 前 30s 留存 + 進對 cluster | 標題前段押詞根 + 字幕 + 章節 + 持續補庫存 |
| 你輸的方式 | 包裝弱 → 卡在測試池上不去 | 沒人搜這題 / 題目撞大頻道的既有排名 |

**兩條容易搞錯的事**：

1. **同一個框架，在兩台機器上命運可能相反。**
   「工具名 + 教學」框架在搜尋機是長尾贏家（有人真的在搜那個工具名），
   在推薦機常是 CTR 輸家（首頁上沒有人在找工具名，他們在找**故事**）。
   → 所以「這個標題框架好不好」是個沒有答案的問題，**要先問餵哪台機器**。
2. **爆量與資產是兩種不同的下注，別混在同一個 KPI 裡。**
   推薦機負責「爆」，搜尋機負責「囤」。
   一支搜尋型影片的首週數字**天生就比推薦型難看**——那不是它失敗，是它還沒開始跑。

### 2b-2 怎麼判斷一支片被哪台機器接走（判讀指標）

發布後看**流量結構**，不要看 views —— **views 會騙人，流量結構不會**。

| 徵狀 | 判讀 | 下一步 |
|---|---|---|
| 曝光突破你頻道的默認測試池上緣（上緣值 `<fill in>`）且**持續上升**，Browse/首頁佔比翻轉成主導 | **推薦機點火** | 進「浪上紀律」：**絕不動標題縮圖**，只做加法 |
| 曝光平、但**搜尋佔比持續爬升**、月量不衰 | **搜尋機接住** | 補詞根：同題再出一支鄰近查詢，把詞根做深 |
| 曝光卡在測試池上緣不動、CTR 低於你的點火帶、Browse 佔比趨近 0 | **兩台都沒接**（雙殺） | 包裝重測（判死條件見下面「48h vs day-14」） |
| views 不低，但**直接 + 外部流量佔比 >50%** | **自推假爆**：這是你自己的社群在看，不是演算法 | 不要拿它當成功樣本去複製 |

> 更完整的點火判定（含 Expected Views 快篩、CTR×AVP 雙門檻、Shorts 的等價指標）
> → [`viral-playbook-framework.md`](viral-playbook-framework.md) §1 / §1b。

### 2b-3 交叉點：第一關鍵字 = cluster 方向盤

**標題／縮圖的第一關鍵字同時決定「搜尋排名」與「推薦分區」** —— 這是兩台機器唯一的共用零件。

- 把副題材（遊戲 / DIY / 生活）放在第一關鍵字 → 演算法把你分去那個區 →
  你原本的觀眾 cluster 接不到 → 推薦欄旁邊全是不相干的影片 → CTR 崩。
- **每支片的第一關鍵字必須錨在你的主 cluster**，副題材只能當第二關鍵字。
- 不肯讓位的題材 = 你接受它是**隨意發的副線**（那也完全可以，只是別期待它有主線的分發）。

**怎麼驗證你進對 cluster**：發布數天後去看「推薦這部影片的內容」清單 ——
列出來的如果是你的同類影片，方向盤打對了；如果是完全不相干的題材，第一關鍵字錨錯了。

### 2b-4 四格 checklist（**不是方程式**）

規劃每支片先填這四格：

```
包裝 CTR（目標 = 你自己的點火帶 <fill in>）
  × cluster 歸屬（第一關鍵字錨在主 cluster？）
  × 點火（發布日的外部/站內冷啟動動作做了沒）
  × 留存（AVP ≥ <fill in>；0:30 存活 ≥ <fill in>）
```

> ⚠️ **這四格曾經被寫成乘法方程式，現在降級為 checklist** —— 誠實原因有三：
> ① 四個變數沒有任何一個被單獨（單變量）驗證過；
> ② 門檻值是**事後從自己樣本回歸出來的**，不是自然常數（曾出現 AVP 低於門檻照樣爆的反例）；
> ③ 效應量（「CTR 差 X% ＝ 曝光差 N 倍」這類 Nx 倍數）多半來自 **n=1 的配對**，只能當方向、不能當係數。
> **四格全勾 = 好徵兆，不是充分條件。** 分級標示法見 [`viral-playbook-framework.md`](viral-playbook-framework.md) §3。

### 2b-5 校準 SOP：用你自己的 3-5 支片跑同一組對照

模型是通用的，**分界值是你的**。原始版本這一節掛的是單一頻道的三片對照數據 ——
那組數字對你毫無用處（題材／語言市場／頻道成熟度不同，整組會平移）。以下是**產生你自己那組數字**的步驟：

1. **選樣本**：挑 3-5 支已發布 ≥28 天的長片，**盡量涵蓋你認為的贏家與輸家**（只挑贏家 = 倖存者偏差，得不出分界）。
2. **統一量測窗**：每支都讀 **D2 / D7 / D28** 三個固定窗（`src/channel_tracker.py` 可自動排程）。
   **跨片比較只准同窗** —— 拿 D2 的數字對比 D37 的數字是自欺。
3. **每支記六欄**：曝光（含曲線形狀）／CTR／AVD／AVP／**流量來源佔比**／轉訂率。
4. **分兩堆**：按「有沒有被演算法接走」（看流量結構翻轉，不是看 views）分成「接走」與「沒接走」。
5. **讀出四個 `<fill in>`**：
   - **測試池上緣** = 沒接走那堆的曝光高原值
   - **CTR 點火帶** = 兩堆的 CTR **分界值**；**引爆帶** = 接走那堆的 CTR
   - **AVP 底線** = 接走那堆的最低 AVP（注意：AVP **單獨不充分**，見下）
   - **推薦浪壽命** = 接走那支的曝光曲線從起飛到躺平幾天、峰值落在第幾天
6. **標分級**：樣本 <5 支就標 ⚠️ PLAUSIBLE，當 checklist 用、不當鐵閘。每累積 3 支重算一次。

**校準時最常踩的三個坑**：
- **CTR 要等曝光 >1k 才讀數**。早期的高 CTR 是訂閱者池的假讀數（幾百次曝光時的 7% 沒有意義）。
- **AVP 單獨無效**。「留存最好的那幾支反而沒量」是常見結果 —— 因為 **CTR 是必要條件，它在留存前面**。
  正確的因果順序是：**CTR 過閘 → 才有量 → 留存才升格為下一個瓶頸**。
- **別把「搜尋型片首週數字難看」當失敗**。搜尋機的成績要用**月量趨勢**讀，不是首週。

### 2b-6 兩張清單（分機器執行）

**推薦機清單**（賭爆量）
- 縮圖 / 標題賭 CTR：用 Test & Compare 跑「標題 + 縮圖組合」，判贏看 watch-time share 不是裸 CTR（→ `youtube-algorithm-2026.md` R15）
- 前 30 秒留存工程（→ §3）
- 系列互推 + 播放清單（end screen 第一格永遠是同簇上一支）
- 發布日冷啟動：自有社群一則 + 平台原生入口（→ `youtube-algorithm-2026.md` R18/R21）

**搜尋機清單**（囤資產）
- 標題**前段**押詞根（用你自己 Studio 的搜尋詞報表挑，不是抄別人的）
- **CC 字幕必上**（字幕是平台 AI 檢索的原料 → `youtube-algorithm-2026.md` R22）
- 說明欄自然關鍵字 + 章節回填**真實 offsets**，章節名寫成完整查詢句式
- evergreen 工具教學持續補庫存 + 大版本更新時重做 pillar

**兩台都要的白撿分**（常見漏分帳單）：CC 沒上、片尾元素沒掛、置頂留言沒放 ——
這幾項不分機器，補上就是立即加分。

---

## 3. Retention Engineering

### 平台基準（2025 → 2026 修正）

- 平台平均：**23.7%**（Retention Rabbit 2025）
- Top 1-in-6：>50%
- ⭐ **教學/How-To 2025 baseline：42.1%** → **2026 健康範圍：45-55%**（[Hootsuite 2026](https://blog.hootsuite.com/youtube-algorithm/) 修正）
- 5-10 min 影片：平均 31.5%，**軟體 / AI 教學目標 50%+**
- ⭐ **2026 新規 Good Abandonment**：教學影片觀眾找到答案後跳走**不再被罰** → chapter 切細 + 答案前置可以放心做（[OutlierKit Updates](https://outlierkit.com/resources/youtube-algorithm-updates/)）

### 教學頻道 checkpoint 目標（5-10 min）—— **值自己填**

> 📏 留存曲線的形狀是通則，**曲線落在哪個高度是你的頻道特性**（隨題材／語言市場／訂閱者比例整組平移）。
> 所以這裡只固定「該在哪幾個時點讀」，不給高度 —— 後台讀數型門檻一律 `<fill in>`
> （規矩 → [`viral-playbook-framework.md`](viral-playbook-framework.md) 檔頭第 1 類）。
>
> **量法**：取近 3-5 支同型長片，每支在下面 5 個時點各讀一次留存，
> 分成「有被演算法接走／沒被接走」兩堆 → **兩堆的分界值就是你的 checkpoint 門檻**。
> 每累積 3 支重算。真正該追的是**跨片同時點的相對變化**（這支 30s 比上支掉了 → hook 退步），
> 不是追某個絕對數字。

| 時間點 | 你的目標留存 | 沒過的意思 |
|---|---|---|
| 30s | `<fill in>` | hook 沒兌現包裝承諾 → 重寫前 30 秒（→ `premium-motion-fx.md` #8） |
| 1 min | `<fill in>` | 價值主張太晚給 |
| 3 min | `<fill in>` | 缺 pattern interrupt |
| 5 min | `<fill in>` | 中段資訊密度失衡 |
| 結尾 | `<fill in>` AVP | 結構太長／結尾沒有 payoff |

### 常見 drop-off pattern + 修法

**① 60-秒懸崖（55% 觀眾在 60s 前走光）**
- 修：前 15s 直接給具體價值（→ 60s 留存 +18%）
- 8 秒法則：8s 內決定要不要繼續 — 秀**outcome**而非介紹

**② 中段沉沒（55-65% mark 流失 15%）**
- 修：pattern interrupt — 新工具揭露 / before-after / 文字突然彈出 / 配音語調變化

**③ 結尾棄船（只 16% 看到最後 10s）**
- 修：**「Subscribe」拜託點放 80% mark，不要放結尾**
- 結尾 end screen 給「下一支」而不是 CTA

**④ AI 配音流失（45s 內掉 35% vs 真人）**
- 修：**AI 教學也要真人配音**

### Open loop / 好奇心缺口工程

- 公式：說 outcome → tease「但第 3 個工具讓一切崩盤」→ 3-min mark 解開 → 開新 loop「但有個 nobody-using 的修法」
- MrBeast 內部文件：**每 30-60 秒一個新 mini-promise**
- 教學專屬：「最強的提示詞在最後」— 開頭 + 3-min mark 各 tease 一次，逼住尾段留存

### Pacing 規則

- **每 3-5 秒一刀**（教學 niche）— MrBeast「wow」段落 1.5-3s
- **每段配樂變一次** — 配樂進/出在 reveal 前；**reveal 前的靜音 = 留存 spike**
- **文字 overlay 1-2 秒**（Galloway rule）— 別貼太久
- **B-roll ≥ 每 5 秒 1 個視覺變化** — 螢幕錄影 + cursor 強調算

---

## 4. CTR / Packaging Science

### CTR 評級帶（**同 §TL;DR：這組沒有可點的出處**）

> ⚠️ 沒有出處就不是 benchmark。這是一組**方向感**的分帶，別拿任何一格當你的判死線；
> 也**別把任何單一頻道的實際 CTR** 寫進這張表當「該達到的值」。
> 自己校準：把已發布影片按「有沒有被演算法接走」分兩堆，看兩堆的 CTR 在哪裡分界。

| CTR | 評級（**只是方向感，不是你的目標**） |
|---|---|
| 2-4% | 弱 |
| 4-6% | 堪用 |
| 6-10% | 好 |
| 10%+ | 神（此帶多為頭部頻道的主頁流量，本檔不引用未附出處的個案數字） |

**你真正要用的兩個值（自己量，本檔不給）**：

| 你的值 | 定義 | 怎麼量 |
|---|---|---|
| **點火帶 CTR** | `<fill in>` | 已發布影片分「有被接走／沒被接走」兩堆，**兩堆的分界值** |
| **引爆帶 CTR** | `<fill in>` | 你真正點火那幾支的 CTR |

⚠️ 上面那張分帶表**不能**當成你的點火帶代用值 —— 門檻隨題材／語言市場／頻道成熟度整組平移，
用別人的帶會得到錯的判死線（同 [`viral-playbook-framework.md`](viral-playbook-framework.md) §1 的 CTR×AVP 雙門檻）。

### Paddy Galloway 5 大 title 心理框架

1. **好奇心**：「The AI Setting That Nobody Talks About」
2. **好處 + 具體**：「Build a YouTube Channel in 1 Hour with AI」
3. **規模/賭注**：「I Tested Every AI Tool So You Don't Have To」
4. **地位**：「How Top 1% AI Creators Use This Tool」
5. **對比/比較**：「AI Tool A vs B vs C for YouTube Scripts (2026)」 — Galloway 指 vs / 3 步比較**持續 outperform**

⭐ **Galloway 公開原則**：「**30% 的時間花在 ideation + packaging**」— 多數小頻道只花 5%

### Thumbnail 2025 規則

- **高情緒臉**（驚訝/興奮/不可置信）：+30% CTR
- **粗對比配色**（黃/橙前景 + 藍/紫背景）：+20-30% CTR
- **文字 3-5 字 max**，≥30pt 行動裝置可讀
- **mobile 168×94px** 預覽 — 70% 觀看來自手機
- **數字**只在表達**規模或賭注**時有效（「$0 vs $200 AI」），亂塞數字無感

### YouTube Test & Compare（2025 原生 A/B）

- 2025-12 起：A/B/C 測 3 個 title / 3 個 thumbnail / 組合
- 並行測（不是 sequential）
- ⭐ **優化 watch-time-per-impression 不只 CTR** — 已 satisfaction-weighted
- 跑 ~2 週自動套用贏家
- ⚠️ **Shorts 沒有此功能**
- 策略：每次測必有 1 個 safe + 1 個 bold variant

### 「Clickbait but truthful」紅線

- MrBeast 內部：thumbnail/title 承諾 → 影片不兌現 → 第一分鐘 click-away → 算法讀「low quality」
- **「Quality Click Ratio」**：高 CTR + 低 AVD = 比低 CTR + 高 AVD **更糟**
- 你的紅線：thumbnail 寫「12 秒寫腳本」→ 影片必須真的 12 秒內展示

---

## 5. Topic Selection / Compound Growth

### 70/30 evergreen/trending 黃金比例

- 60%+ evergreen 的頻道 → 12 個月訂閱保留率 **2.3 倍**
- [TRANSFERS DIRECTLY] AI 教學完美適配

### Compounding（搜尋驅動）— 推薦長片 70%

- 「How to use [工具] for [enduring use case]」
  - 「How to use AI for YouTube scripts」「How to use AI for thumbnails」
- 「[工具] vs [工具] for [use case]」 — compound 12-24 個月
- 「[工具] 新手入門」 — 搜尋需求永不死
- **Workflow 影片**（「我完整的 AI YouTube workflow」）— 高 session contribution

### Spiky（演算法驅動）— 長片 30%、但 Shorts 80%

- 新模型 / 新工具發表（新一代 LLM、影片生成模型、圖像生成模型等）— 7 天 spike，3 週衰退
- 「我測試了 [新功能] 發布日」— 24-72h window
- 新發布 vs 比較

### Format-Topic-Packaging 三位一體（Galloway）

- 三者都對 → 28M views
- 好題目+爛包裝 → 1M views
- ⭐ **三者必須全部對齊**

---

## 6. YT Studio Analytics Decode

### 真正重要的指標（2025-2026）

| 指標 | 重要性 |
|---|---|
| **AVD + Retention 曲線形狀** | ⭐⭐⭐ 最重要 |
| **Returning Viewer %**（忠誠度 proxy） | ⭐⭐⭐ 2025 大幅加重 |
| **Session Time per video**（看完還看幾支） | ⭐⭐⭐ |
| Survey responses（看不到但餵推薦） | ⭐⭐ |
| Like-to-View ratio | ⭐ ≥2% 健康 / ≥4% 強 satisfaction |

### Vanity metrics（不要看）

- 純 view count
- 純訂閱數（除非 return rate 高）
- 純留言數（不看 sentiment）
- 純 CTR（沒搭 AVD 看）

### Retention 曲線形狀解讀

| 曲線形狀 | 意義 | 修法 |
|---|---|---|
| **前 30 秒陡崖** | Title/Thumbnail mismatch 或 intro 太慢 | 第一幀直接秀 outcome |
| **中段正向凸起** | 觀眾倒帶 = 「wow 時刻」 | **複製這個技法** |
| **平坦** | 理想，sustained engagement | 維持 |
| **章節斷點 step-down** | 觀眾拿到答案就走（教學特有） | 「最強的在最後」尾段 promise |

### Traffic source 怎麼讀（2026 update）

| 來源高 | 意義 |
|---|---|
| **Browse 高** | thumbnail 對現有觀眾有效（⚠️ Dec 2025 砍 -80%，預期降低） |
| **Suggested 高** | 算法背書你，跟競爭對手影片鏈接好 |
| **Search 高** | ⭐ Compounding evergreen winner — 軟體 / AI 工具教學長期目標 |
| **External 高** | ⭐⭐⭐ **最強槓桿之一** — 自有社群（聊天社群 / 訊息群組 / 線下場合 / Newsletter）。Quality community traffic = 強正向 signal（沒懲罰），External Share 在 2026 satisfaction stack **權重 88**（vs CTR 38）。把每片發布串到自有社群動員（如 T+0/24/48/7d 節奏），是 Browse 砍量後的 #1 對沖 |
| **Notification 高** | 訂閱基礎強但新觀眾觸及有限 |

### New vs Returning Viewer

- **60%+ new** = 算法在推你給新觀眾（成長期理想）
- **60%+ returning** = 忠誠度強但 reach 卡關
- **50/50** = 永續成長期目標

### Realtime tab

- 只在發布頭 2 小時有用（看 impression 有沒有 fire）
- 之後看 48h dashboard 更準

---

## 7. Iteration Mindset (MrBeast-tier)

### Post-publish title/thumbnail 換掉

- **不會 reset 算法**，只是換給算法的 data
- ⚖️ **時機以 §2「48h vs day-14」為準**：**0-48h 內不換**（污染 T&C 樣本），
  除非 seed fail 三聯徵同時亮；否則等 **day-14 決策樹**（CTR 低於你的點火帶才動包裝）
- 換完等 1-3 週看新 traffic 效果
- MrBeast 最多換 **10 次**；你 2-3 次合理
- ⭐ 新片直接用 YT Test & Compare 跑組合測試（判贏看 watch-time share）

### Reupload 策略 [PARTIAL]

- 完全 duplicate = 標 repetitious，丟舊 watch time
- 2026 算法**特別打擊** templated/near-duplicate
- 若要 reupload：unlist 原版 + 大改（新 intro + 新結構 + 新 b-roll）當新片發
- **教學頻道通常不值得 reupload**

### 刪除 / Unlist underperformers

- 沒文件證明刪掉有算法好處
- **Unlist 可逆，比較安全**
- 「爛影片」沒你想像中拖累頻道（2025 解耦後更不會）

### 「Test fast, kill fast」[PARTIAL — 時序已依 2026 官方口徑修正]

- 追蹤頭 48h CTR + 頭 1-min retention，但 ⚖️ **48h 只讀不動**（§2）
- **day-14 決策樹**才決定換不換；例外只有 seed fail 三聯徵
- 2 次換還沒救起來 → **放掉**，別再投時間
- 維護一份「kill list」：flop 過的格式/題目不重複
- ⚠️ MrBeast 的「kill fast」出自一個**每支片曝光量級極大**的頻道 —— 他的 48h 樣本比小頻道的 14 天還多。
  小頻道照抄那個節奏，是拿雜訊當訊號。

### MrBeast 內部 review 機制 [PARTIAL]

- 多支影片同樣時間點 drop → 團隊找原因 → 下支修
- 你的應用：**追蹤你影片總是掉在第幾分鐘**，那就是要修的點
- 例：「retention 一直在 4:12 掉」→ 找你 4:12 都做什麼（慢轉場？多餘 recap？）→ 砍掉

### 「Top 1%」filter

- 發布前問：**能贏 niche 中前 1% 的影片嗎？**（Outlier Index >2x 頻道平均）
- 工具：Spotter Studio / VidIQ / OutlierKit 找對應 niche 中 5-10x outperform 的格式
  - 軟體教學 niche 找：對應軟體（3D / 設計 / 開發工具）教學頻道
  - AI 工具教學 niche 找：對應 AI 工具教學頻道
  - 旅遊 Vlog niche 找：同地區 / 同主題 vlog
- ⚠️ 別 copy — 抽**模式**（「具體數字 + 荒謬語境 + 具體結果」），應用到你的題目
- ⭐ **過 Top 1% filter 的片才動員社群子彈（如 Hype button / 社群推播）** — 稀缺資源不浪費在 baseline 片上

---

## 📋 你的頻道週週可執行 KPI

每週發布前 self-check：

**長片（5-10 min 教學）目標**：
- [ ] Title 寫了 3 個變體 + 1 個 thumbnail concept？
- [ ] Title 套上 Galloway 5 大框架之一？
- [ ] 第一幀直接秀 outcome（非「今天我要分享」）？
- [ ] 開頭 15 秒講完價值主張？
- [ ] 設好 3 個 open loop（minute 1 / minute 3 / halfway）？
- [ ] 用了 YT Test & Compare 跑 2-3 thumbnail variant？
- [ ] Description 前 125 字含 keyword + benefit？
- [ ] Chapters 加好（10 min+ 必加）？
- [ ] 結尾「Subscribe」拜託點放 80% mark 而非結尾？

**Shorts 目標**：
- [ ] 第 1 幀就是視覺 hook？
- [ ] 加字幕（假設靜音觀看）？
- [ ] Loop 結構（末尾接首幀）？
- [ ] 長度落在雙峰其一（13-25s 短帶 / 45-60s 長帶），**沒有落進 26-44s 死區**？
- [ ] 發文時間挑頻道實測有效的高峰時段（用 YT Studio 數據驗證自己的時段）？

**發布後 48-72h check**（⚠️ 只讀不動 —— 決策時點是 day-14，見 §2「48h vs day-14」）：
- [ ] CTR 有沒有到**你自己的點火帶** `<fill in>`？（量法 → §4）
- [ ] 1-min retention 有沒有到**你自己的 checkpoint** `<fill in>`？（量法 → §3）
- [ ] 兩者都過 → 維持；兩者都低於你的線 → day-14 才換 thumbnail/title
- [ ] 2 次換沒效 → kill，移動到下一支

---

## Sources

### MrBeast 內部 + 訪談
- [Simon Willison: MrBeast Leaked PDF Analysis](https://simonwillison.net/2024/Sep/15/how-to-succeed-in-mrbeast-production/)
- [Tubefilter: Leaked MrBeast Production Guide](https://www.tubefilter.com/2024/09/17/mrbeast-internal-production-guide-leaked-key-points/)
- [Protunesone: MrBeast Strategy Breakdown](https://protunesone.com/blog/leaked-mrbeast-document-on-his-youtube-strategies/)
- [Future Social: How to Go Viral via MrBeast](https://futuresocial.beehiiv.com/p/mr-beasts-how-to-viral)
- [Joe Rogan Experience #1788 — MrBeast](https://open.spotify.com/episode/5lokpznqvSrJO3gButgQvs)
- [Lex Fridman Podcast #351 — MrBeast](https://lexfridman.com/mrbeast/)
- [Colin and Samir × MrBeast 訪談 transcript](https://singjupost.com/colin-and-samir-show-with-mrbeast-transcript/)

### 算法內部 + 2024-2026 變化
- [Marketing Agent: 2025 Algorithm Breakdown](https://marketingagent.blog/2025/11/04/youtubes-recommendation-algorithm-satisfaction-signals-what-you-can-control/)
- [Search Engine Journal: 2025 Recommendation Guide](https://www.searchenginejournal.com/how-youtubes-recommendation-system-works-in-2025/538379/)
- [Outlierkit: Algorithm Updates Log](https://outlierkit.com/resources/youtube-algorithm-updates/)
- [Adoutreach: Beaupré 2025 Summary](https://adoutreach.beehiiv.com/p/how-youtube-s-algorithm-really-works-in-2025-straight-from-youtube-s-director-of-growth)
- [YouTube Help: Valued Watch Time](https://support.google.com/youtube/answer/16089387)

### Retention + Packaging
- [Retention Rabbit: 2025 Audience Retention Benchmarks](https://www.retentionrabbit.com/blog/2025-youtube-audience-retention-benchmark-report)
- [Colin & Samir: Paddy Galloway New Rules](https://www.colinandsamir.com/resources/the-new-rules-of-youtube-from-paddy-galloway)
- [YouTube Test & Compare Announcement](https://support.google.com/youtube/answer/16391400)
- [SocialMediaToday: Title Testing](https://www.socialmediatoday.com/news/youtube-adds-title-testing-youtube-studio/753015/)
- [Hootsuite: 2025 Algorithm Guide](https://blog.hootsuite.com/youtube-algorithm/)

### Topic + Outlier Tools
- [Subscribr: Evergreen vs Trending](https://subscribr.ai/p/evergreen-vs-trending-youtube-topics)
- [Spotter Studio: Outliers](https://www.spotterstudio.com/blog/youtube-growth-hacks-how-spotter-studios-outliers-can-grow-your-channel)
- [OutlierKit](https://outlierkit.com/)
