# craft refs 索引（六本剪輯研究檔的導航台）

> **本檔不含任何技法內容，只回答一件事：這次該讀哪一本、哪一節。**
> 六本合計 ~330KB（≈128k tokens），整批讀進來會炸 context——先在這裡定位，再只開需要的那一本那一節。
> 內容一字未動，六本全文照舊（研究成果保留全文，本檔只做路由）。
>
> ⚠ 這六本**不是**這些主題的 SoT，別在這裡找：
> 　・剪輯教訓 / 決策 canon → `meta-lessons-canon.md`（任何剪輯決策先查 canon）
> 　・教學長片 10-stage 流程 → `hao-teaching-longform-method.md`
> 　・直式 Shorts 規則 → `shorts-mastery-2026.md`（+ 字體配色 `niche-fonts-colors.md`）
> 　・Hao 招牌 / 視覺鐵則 → `hao_editing_signatures.md`（記憶檔）
> 　・演算法 / 包裝 KPI → `yt-algorithm-mastery/`
> 　・影視颶風取向的能量波＋18 領域新語法 → `cinematic-wave-and-domain-grammar-2026.md`
> 　・MrBeast 資訊能量／追蹤圖形／物件遮罩閃光＋影視颶風正式評分 → `mrbeast-and-yingshi-benchmark.md`
> 　・33 張參考圖設計 DNA／長短片 reflow → `design-reference-dna-v6.md`
> 　・物件 matte 高光／2.5D／true 3D／camera solve → `three-d-and-subject-fx.md`

---

## 0. 六本一句話定位 + 讀取成本

| 檔 | 一句話 | 大小 | ≈tokens | 什麼時候開 |
|---|---|---|---|---|
| `editing-craft-fundamentals.md` | **業餘→pro 的基本功總表**（調色/音訊/節奏/B-roll/轉場/字/敘事 七大塊，每條「一眼看出爛的 tell → pro 怎麼修」+ 數值） | 77KB | ~30k | 成品「就是看起來很業餘」但講不出哪裡爛 |
| `editing-master-techniques.md` | **competent→master 的判斷哲學 + 高槓桿進階技**（Murch/隱形剪輯/配樂/sound design/二級調色/縮圖/story） | 88KB | ~34k | 基本功都做了但「沒感覺、不抓人」 |
| `niche-editing-grammar.md` | **各題材專屬文法**（美食/旅遊/重機/教學長片不露臉/軟體 AI demo 五個 niche） | 54KB | ~21k | 拍的是特定題材，要那個題材的規矩 |
| `editing-wave5-finecut-2026.md` | **2026 wave5 37 條：細剪執行層**（retention/dataviz/2026 工具/finecut 四主題，條條帶數值+落地模組） | 43KB | ~17k | 要「可機械化的數字」而不是概念 |
| `editing-wave6-2026.md` | **2026 wave6 31 條：wave5 沒碰的三維度**（音訊時間軸 W6A / 疊加層動畫語法 W6B / 教學型結構 W6C） | 47KB | ~18k | 混音、動畫規格、教學片結構要細規格 |
| `editing-techniques-2026.md` | **最早的量化速查（Shorts/長片/字幕音訊三塊）+ 六路深研計畫表** | 26KB | ~10k | 想快速掃一遍量化門檻；或查 wave 系列的來龍去脈 |

> tokens 為估算值（依本 repo 實測基準 ≈2.6 bytes/token 換算，非精算）。

---

## 1. 症狀 → 直接跳哪本哪節（主路由表）

| 症狀 / 情境 | 主讀 | 補充讀（有需要才開） |
|---|---|---|
| **開場鉤子沒力、前 30 秒掉一半** | wave5 §TOPIC: retention #1-#5（開場 30 秒鎖三段／5 秒靜止掃描／payoff 節拍器／章節卡逃生門／open loop 視覺化） | master §腳本 story-for-retention（開場黃金公式 Result-First Hook・殺手句黑名單）／fundamentals §敘事剪輯（第一分鐘是懸崖・Cold Open） |
| **中段流失、AVP 低（CTR 好但看不完）** | wave5 §finecut #1 雙模式節奏波・#8 pattern interrupt 時刻表 | master §腳本（re-engagement hook 每 30-60s・value-per-second）／wave6 W6A-7（音訊層 interrupt 五型）／techniques-2026 §波2 節奏結構 |
| **畫面一眼就業餘（色偏／髒／過飽和）** | fundamentals §⚡ 速查表 → §🎨 調色（一級校色 5 步順序・LUT 強度・scope・ffmpeg chain） | master §進階二級調色（HSL qualifier／power window／shot matching）⚠ 見下方「不適用警告」 |
| **聲音悶／吵／BGM 蓋掉人聲** | fundamentals §🔊 音訊混音（4 軌 dB 階梯・highpass・de-ess・compressor・sidechain・room tone・-14LUFS） | wave6 §TOPIC: audio W6A-4/5/6（BGM 選曲頻譜否決・voice pocket EQ・SFX 音量分層）／master §進階 Sound Design（哲學層） |
| **SFX 太多太吵／每個 cut 都 whoosh** | wave6 W6A-1/2/3（SFX 事件預算 density cap・防重複輪替・方向性 pan） | fundamentals §音訊（whoosh 同幀對齊） |
| **剪點卡卡、接不順、跳接明顯** | fundamentals §✂️ 節奏 Pacing（cut on action／J-cut／L-cut／match on action／刪贅 vs 留白／shot length 變化） | master §🎬 Murch（Rule of Six・blink theory・repeat-cut 測試）＋§🪡 隱形剪輯（180 度線・eyeline・30 度規則・buffer shot） |
| **轉場又醜又多** | fundamentals §🔀 轉場（hard cut 主力・motivated 原則・黑名單・長度硬規則） | wave5 §finecut #7 轉場語意表（何時准用，機械可查）／wave6 W6B-1（章節 motion 轉場的方向鎖+剪點執行規格） |
| **字卡醜／動畫很廉價** | fundamentals §🔤 動態圖文 Typography（換字體・丟純黑陰影・階層・stagger・easing・安全邊距・克制原則） | `mrbeast-and-yingshi-benchmark.md`（資訊事件才開特效／tracking 證據／mask sheen）＋ wave6 W6B-2/9/10 |
| **MrBeast 視覺衝擊不足／影視颶風節奏與質感不足** | `mrbeast-and-yingshi-benchmark.md`（兩套各 10 分子項／A-B-C 可行性／效果預算／遮罩邊界） | `cinematic-wave-and-domain-grammar-2026.md`（能量波）／master §Murch＋隱形剪輯 |
| **螢幕錄影教學片乾、悶、沒人看得下去** | niche §🎓 教學長片(不露臉) ＋ §💻 軟體/AI demo | wave6 §TOPIC: structure W6C（demo 三速表・之字剪 timelapse・等待段三選一・screencast 主從律） |
| **戰績／後台數據截圖上鏡沒說服力** | wave5 §TOPIC: dataviz 全 10 條（4 拍 staging・0:20-0:30 首張 proof・counter 規格・停留公式・多數字對比） | wave6 W6B-3/4（圖表上鏡三刪鐵則・動畫語意對照表） |
| **b-roll 像在鋪壁紙** | fundamentals §🎥 B-roll（5-shot method・sequential vs illustrative・cut on the word・時長分級・雙軸） | wave5 §finecut #10 B-roll 兩軸定位法（量化版）／wave6 W6B-6（遞減節奏 accelerate into reveal） |
| **音樂沒感覺／接歌難聽／卡點卡死** | master §🎵 配樂剪輯精修（equal-power crossfade・cut on phrase not beat・spotting・build-and-release・anticipation cut） | fundamentals §節奏（踩拍剪但別每拍都踩） |
| **縮圖 CTR 低 / 包裝弱** | master §🖼️ 縮圖+包裝 CTR（package-before-produce・非冗餘原則・資訊缺口・灰階 120px 剪影測試・T&C 顯著性） | 頻道級策略另見 `yt-algorithm-mastery/`；反應臉鐵則見記憶 `hao_editing_signatures.md` |
| **拍的是美食 / 旅遊 / 重機** | niche §🍜 美食 ／ §✈️ 旅遊 ／ §🏍️ 重機 motovlog | fundamentals 對應塊（基本功不因題材改變） |
| **要升級工具 / pipeline（ffmpeg・字幕・自動切）** | wave5 §TOPIC: tools2026（ffmpeg 8.1 drawvg／whisper af／whisperx pin／faster-whisper batched／auto-editor 31.3／管線順序鐵則） | wave6 W6C-11（AI 輔助剪輯工作流 2026 定位：pre-edit + 文字化 EDL） |
| **想把某條規則變成機械 gate** | wave6 §落地優先序（31 條分三堆：可掛現有 helper／需新模組／只能 flag） | wave5 每條的「落地」欄位 |
| **只想快速掃量化門檻** | techniques-2026 §A/§B/§C（Shorts・長片・字幕音訊三張速查） | — |

---

## 2. 六本各自的路標（代表性小節，找不到就照這裡跳）

### `editing-craft-fundamentals.md` — 業餘→pro 基本功（7 大塊）
- `## ⚡ 業餘→pro 速查表` — 依觀感影響排序，**永遠先讀這張**
- `## 🎨 調色 Color`（15 條：校色 5 步順序 / LUT 50-70% / vectorscope 膚色線 / 4-6 IRE / ffmpeg chain / HaldCLUT）
- `## 🔊 音訊混音 + Sound Design`（原文標「最大業餘 tell」，16 條全是可直接抄的 ffmpeg 參數）
- `## ✂️ 節奏 Pacing + 剪接點`（cut on action / J-cut / L-cut / match on action / ASL baseline / tension build）
- `## 🎥 B-roll + 視覺覆蓋 Coverage`（5-shot / 雙軸 / 4-6 倍量化拍攝門檻）
- `## 🔀 轉場 Transitions`（含轉場黑名單）
- `## 🔤 動態圖文 + Typography`（11 條）
- `## 📖 敘事剪輯 Story Structure`（paper edit / audio-first / open loop / 第一分鐘懸崖）

### `editing-master-techniques.md` — master 級判斷 + 高槓桿技
- `## 🥇 Master moves 速查`（competent 不會、master 會）
- `## 🎬 Murch《剪輯之道》Rule of Six + Blink Theory` — 剪接判斷的最高層
- `## 🪡 隱形剪輯 / 連戲 continuity`（180 度線 / eyeline / 30 度規則 / graphic match）
- `## 🎵 配樂剪輯精修` — 原文標「一秒變專業最大槓桿」
- `## 🔊 進階 Sound Design`（worldizing / two-and-a-half / synchresis / silence as a tool）
- `## 🎨 進階二級調色 secondary`（qualifier / power window / day-for-night / halation）
- `## 🖼️ 縮圖 + 包裝 CTR`
- `## 📝 腳本 / story-for-retention`（re-engagement hook / open loop / result-first / 殺手句黑名單）
- `## 🏆 頂尖剪輯師招牌技法` + `## 🎯 最該內化的 must-bake`
- ⚠ **檔頭有對抗驗證註記必讀**：Rule of Six 百分比是修辭優先序不是可加總公式；blink/cut-rate 是啟發式不是定律；**film grain / teal&orange / 4-6 IRE / vignette 對 Hao 主力（M78 不露臉螢幕教學片）相關度低甚至有害**。

### `niche-editing-grammar.md` — 各題材文法（5 個 niche）
- `## 🍜 美食`（sizzle 開場 / 留食物原聲 / hero shot / 暖白平衡）
- `## ✈️ 旅遊`（establishing / wide-medium-detail / 故事弧取代時間順序 / match cut 接地點 / hyperlapse）
- `## 🏍️ 重機 motovlog`（Linear+HL 拍攝端 / Gyroflow / 風切三層防護 / RAW audio 旁檔 / telemetry overlay）
- `## 🎓 教學長片(不露臉)` — **Hao 主力題材**（錄製 ≥1440p / punch-in 2x 規格 / zoom 頻率天花板 / 游標平滑 / 乾淨取景 / 每 15-25s 視覺斷點 / 章節 / 留存基準）
- `## 💻 軟體/AI demo`（click-triggered auto zoom / 30fps 反直覺 / spotlight dim / callout / 裝置外框 / before-after 倒敘 / 克制式剪輯）

### `editing-wave5-finecut-2026.md` — 2026 細剪 37 條（每條帶數值+落地模組）
- `## TOPIC: retention`（8 條：開場 30 秒三段 / 5 秒靜止掃描 gate / 90 秒 payoff 節拍器 / 章節卡 ≤2s / open loop 視覺錨 / 靜默 ≤0.5s / 結尾防衰減 / 48-72h 留存急救）
- `## TOPIC: dataviz`（10 條：**真截圖與數字上鏡的唯一主寫處**）
- `## TOPIC: tools2026`（9 條：**2026 工具鏈的唯一主寫處**，含管線順序鐵則）
- `## TOPIC: finecut`（10 條：雙模式節奏波 / J·L-cut 帶數字 / 句尾 5-6 割 / 同源 30% 變化率 / 反 slideshow 事件預算 / 轉場語意表 / interrupt 時刻表 / 3-frame flash / b-roll 兩軸）

### `editing-wave6-2026.md` — 2026 wave6 31 條（補 wave5 三個沒碰的維度）
- `## 快查表（31 條一行索引）` — **先讀這張再決定跳哪條**
- `## TOPIC: audio`（W6A 1-9：SFX 密度上限 / 變體輪替 / 方向 pan / BGM 頻譜否決 / voice pocket / 音量分層 / 音訊 interrupt / 資產台帳 / montage cadence）
- `## TOPIC: visual`（W6B 1-10：轉場執行規格 / kinetic 克制 / 圖表三刪 / 圖表動畫語意 / 混剪亮度連續性 / b-roll 遞減 / callout 位置 / zoom settle-before-read / 時長階梯 / 文字 pattern 白名單）
- `## TOPIC: structure`（W6C 1-12：demo 三速 / 之字剪 timelapse / 等待段三選一 / PiP / 章節命名 / 章節數×片長 / auto-zoom 藍圖 / 錄製即遙測 / 成品先行開場 / screencast 主從律 / AI 剪輯工作流 / 章節=檢索資產）
- `## 落地優先序（31 條分三堆）` — 要動工先看這裡
- ⚠ 檔頭數字警語：閾值類數字（YAVG>40、ramp≤2 次、10s 窗 ≥3 SFX）是方向性起始值，實測後校準。

### `editing-techniques-2026.md` — 最早的量化速查 + 深研計畫表
- `## A. 短影音 Shorts/Reels` — ⚠ **Shorts 規則已由 `shorts-mastery-2026.md` 接手當 SoT**，本節當歷史底稿讀
- `## B. 長片 YouTube` / `## C. 字幕 + 音訊`
- `## 🚀 2026-07-09 六路深研升級計畫`（波1 接線 / 波2 節奏 / 波3 簽名 / **⛔ 明確不做清單 skip list**）
- `## → wave5 深研（2026-07-23）` — 通往 wave5 的接口

---

## 3. 跨檔重複主題對照（查一本就夠，別六本都翻）

> 規則：**先讀「主寫」那一本；只有需要那個角度時才開「補充」。** 內容全部保留，這裡只標分工。

| 主題 | 主寫在 | 補充（只在需要該角度時開） |
|---|---|---|
| **開場 hook / 前 30 秒**（六本都寫，最嚴重的重複） | **wave5 §retention #1-#5**（最新、帶數值、三段結構） | master §腳本＝公式與心理學根據（result-first / 資訊缺口）｜wave6 W6C-9＝coding·工具片的「成品先行 30 秒」結構｜niche §教學長片＝不露臉版「5-15 秒給結果」｜techniques-2026 §A＝Shorts 版前 3 秒｜fundamentals §敘事＝cold open 概念層 |
| **J-cut / L-cut（split edit）** | **fundamentals §節奏**（定義＋兩軌操作） | wave5 §finecut #2＝帶數字版（段內 b-roll 全走 L-cut 邏輯）｜master §進階 Sound Design＝sound bridge 縫合觀點｜niche §旅遊＝套用範例 |
| **轉場** | **fundamentals §轉場**（種類・長度・黑名單） | wave5 §finecut #7＝「何時准用」語意表（機械可查）｜wave6 W6B-1＝章節 motion 轉場的方向鎖與剪點執行 |
| **調色** | **fundamentals §調色**（一級 primary，含 ffmpeg） | master §進階二級調色（secondary：局部/追蹤/風格化）— ⚠ 對不露臉螢幕教學片相關度低 |
| **音訊混音** | **fundamentals §音訊混音**（軌道結構＋ffmpeg 參數） | wave6 §W6A＝2026 機械 gate 化的量化規格（密度/頻譜/分層）｜master §進階 Sound Design＝創意與哲學層 |
| **BGM 讓路人聲** | **fundamentals（sidechaincompress ducking）** | wave6 W6A-4/5＝選曲階段的頻譜否決 + 常駐 voice pocket EQ（duck 救不了的部分）｜niche §重機＝引擎聲版 |
| **B-roll 雙軸定位** | **fundamentals §B-roll**（概念＋分層） | wave5 §finecut #10＝同一概念的量化版（sequential 3-7s/clip 等）— 兩處講同一件事，讀一處即可 |
| **Pattern interrupt** | **wave5 §finecut #8 時刻表**（25-35s 第一個，之後 30-60s） | wave6 W6A-7＝音訊層五型（成本最低的單獨用法）｜techniques-2026 §A＝ROI 排序｜master §腳本＝呼吸曲線 |
| **Typography / kinetic 字** | **fundamentals §動態圖文**（字體・階層・easing・安全邊距） | wave6 W6B-2/9/10＝克制規格・時長階梯・pattern 白名單（2026 補強） |
| **punch-in zoom / auto-zoom** | **niche §軟體 AI demo ＋ §教學長片**（頻率天花板・ease・游標） | wave6 W6C-7＝開源 auto-zoom 演算法藍圖｜wave6 W6B-8＝zoom 要先落定再讀（settle-before-read）｜techniques-2026 §A＝Shorts 版 |
| **章節 chapters** | **wave6 W6C-5/6/12**（命名・數量×片長・檢索資產三條最完整） | wave5 §retention #4＝章節卡的剪輯處理（≤2s、BGM 不斷）｜niche §教學長片＝章節當小標題鉤子 |
| **刪靜默 / 砍死空檔** | **wave5 §retention #6**（≤0.5s 硬值） | wave5 §tools #6＝auto-editor 機械執行｜fundamentals §節奏＝「刪贅 vs 留白」判斷｜niche §軟體 demo＝教學片別切太碎 |
| **match cut / 隱形剪接** | **master §隱形剪輯**（180 度線・eyeline・30 度・buffer shot） | fundamentals §轉場＝基礎版（物體遮擋/whip pan）｜niche §旅遊＝接地點用法 |
| **圖表 / 數字上鏡** | **wave5 §dataviz**（10 條完整） | wave6 W6B-3/4＝圖表本身的設計（三刪鐵則＋動畫語意配對） |
| **節奏 / cut rate** | **fundamentals §節奏**（ASL baseline・shot length 變化） | master §Murch＝cut-rate↔blink-rate 校準心法（非硬門檻）｜wave5 §finecut #1/#3/#4＝雙模式波・句尾 5-6 割・30% 變化率 |

---

## 4. 用法備忘

1. **先 canon 後 craft**：任何剪輯決策先查 `meta-lessons-canon.md`；canon 沒有答案才進這六本。
2. **一次只開一本**：照 §1 路由表跳，讀完那一節就停；六本平均一本 ≈20k tokens，開錯成本很高。
3. **數字分級**：wave5/wave6 的閾值是方向性起始值（各檔頭有警語）；master 的百分比是修辭優先序不是公式。
4. **Hao 專屬不適用清單**：不露臉螢幕教學片請跳過 film grain／teal&orange／vignette／PiP 臉 cam 類條目（各檔已標，別照抄）。
5. 新增第七本研究檔時：回本檔加一列到 §0 與 §1，並在 §3 標好與既有檔的分工。

---

## §5 競品實測對照（2026-07-28 新增）

[`competitor-vertical-teardown-2026.md`](competitor-vertical-teardown-2026.md) —
**5 支市面直式短片的逐幀機械量測**（非目測）：刀速/刀距標準差/換句速率/字幕停留/
字體與位置/貼文文案五種原型/前台互動比例。

何時讀：
- 「這支直式節奏怪」→ §2（節奏主體是換句不是剪點）、§3（兩種節奏原型）
- 「字幕該用什麼字體/放哪」→ §4（背景亂度決定字體，不是好不好看）
- 「貼文文案怎麼寫」→ §5（五種原型全文）
- 「CTA 該寫什麼」→ §6（探店寫分享 CTA、開箱寫提問 CTA）
- 「片長規則跟我的 gate 打架」→ §7（26-44s 死區僅限 YT Shorts）

⚠️ 邊界見 §9：n=5、四美食一開箱、無後台數據、無失敗對照組。
