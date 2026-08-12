# Hao 字幕與文字效果系統

> 適用：YouTube 長片、YouTube Shorts、Instagram／Facebook Reels。
> 原則：字幕負責「讀得懂」，文字效果負責「記得住」。兩者不可混成同一層。

## 1. 這批參考圖提煉出的設計語法

只吸收可泛化的構圖原理，不複製第三方 Logo、字樣或特定版面：

1. **票券／飄帶**：狹長色塊承載步驟、標籤、日期與短命令；可斜入、輕彎、前後層交錯。
2. **巨型字層級**：主詞或數字可以大到成為畫面結構；其他資訊退到小字與留白。
3. **Cobalt＋Lime**：高明度藍底配螢光綠，適合 AI、科技、教學與數據；白字維持主閱讀層。
4. **物件去背＋UI 碎片**：主體跨過大字，搭配 selection box、箭頭、標籤與卡片，建立前中後景。
5. **Neo-Bauhaus 模組格**：用方格、圓、漸層與框線建立資訊節奏，適合背景與章節卡，不拿來塞滿字幕區。

## 2. 三層架構

| 層 | 職責 | 長片 | 短片 |
|---|---|---|---|
| Spoken captions | 逐句旁白／對白可讀性 | 白字黑底、固定字級與位置 | 白字為底，可局部語意上色 |
| Emphasis overlays | Hook、數字、條件、轉折、Proof、Payoff | 允許選擇性巨字／數字 pop | impact／ribbon／float |
| Editorial graphics | 題材背景、卡片、箭頭、物件與圖形 | 章節與證據輔助 | 建立前中後景與 pattern interrupt |

**硬邊界**：長片可以有很強的文字／數字效果，但不得把逐句字幕整條染色、放大或逐字彈跳。
巨字效果必須走獨立 overlay 軌；底層字幕持續正常顯示。

## 3. Shorts／Reels 模式

| kind | 用途 | 字數上限 | 動態 |
|---|---|---:|---|
| `hook` / `sub` / `main` | 一般閱讀字幕 | 依 S-R 讀速 | 固定、輕淡入 |
| `impact` | 結果先給、數字、短 Payoff | 12 | 70%→112%→100% pop＋擠壓陰影 |
| `ribbon` | 第 N 步、標籤、短命令 | 14 | 斜向滑入＋色塊底 |
| `float_left/right` | 反差詞、短吐槽、局部註解 | 8 | 左右交替上浮＋旋轉＋2.5D 陰影 |
| `addr` | 地點／地址 | 次要資訊 | 底部安全區常駐 |

使用頻率：動態模式最多約內容字幕的 40%，常態 15–25 秒短片只會有 1–2 顆強效果。
相鄰兩顆強效果之間優先插入 clean hold；不可每句都 pop。

## 4. 長片選擇性 Impact

- 逐句字幕：沿用 M68，白字＋70% 黑底、固定位置；`emphasize=True` 直接被程式擋下。
- Impact overlay：只在 Hook、轉折、挑戰規則、真實數字／Proof、Payoff 出現。
- 密度：最多約每分鐘 2 顆，全片上限 8 顆；兩顆至少間隔 7.5 秒。
- 類型：`number`（大數字）、`keyword`（短主詞／結果詞）；每顆 1–10 字、約 1.0–1.25 秒。
- 位置：畫面上半部；不得壓住底部逐句字幕、產品操作、真實後台數據或人物關鍵表情。
- Proof 數字若代表真實戰績，底層仍須露出真後台或可驗來源；自繪巨字只是注意力層，不是證據本身。

### Imagegen Premium 材質層

- 高價值 `impact／float／number／keyword` 只可升級為經人眼審核的 `imagegen_premium`；其餘維持乾淨 editorial。
- 第一個核准素材是 `VS Electric Clash`；黑底以 Screen／濾色疊片。索引在 `assets/glow_text/imagegen/manifest.json`。
- 沒有核准 Image 素材時必須標記 `imagegen_required` 或 clean hold，不能回退到程式描邊字、廉價 ASS 2.5D 或錯誤預製詞。
- 合格視覺應具有可信的材質、倒角、表面紋理、深度擠壓、受控光暈與電影級照明；不是粗體＋描邊＋外發光。
- 發光字是「語意標點」不是證據；數據仍需真畫面／真來源。兩個強發光效果之間仍遵守密度與呼吸規則。

## 5. 語意上色

- **白字永遠是底**；整支最多兩種非白色：`gold`＋該題材副色。
- 數字／百分比／價格：gold。
- AI／科技：sky；美食：coral；玩具／潮流：pink；遊戲／成功：mint；紀錄／訪談：orange。
- 只上色詞，不上色整句；一個詞若占整句六成以上就取消上色。
- 顏色不等於情緒亂配：同一語意在同支片內保持同色。

## 6. 對 MrBeast 文字節奏的吸收方式

MrBeast 團隊公開職缺仍把 hyper-fast pacing、visual pop-ups、kinetic typography 與 tracking graphics
列為剪輯能力，但 MrBeast 也公開主張離開無止境的過度刺激、讓故事與場景有呼吸。兩者合併後的 Hao
規則是：**保留高辨識文字標點，不把刺激密度當故事本身。**

- [MrBeast 官方剪輯職缺](https://job-boards.greenhouse.io/mrbeastyoutube/jobs/6128701004)
- [The Washington Post：MrBeast 談放慢過度刺激剪輯](https://www.washingtonpost.com/technology/2024/03/30/video-editing-mrbeast-retention/)

## 7. 機械 QA

1. S-I：非白 token ≤35%，非白色 ≤2 種。
2. S-R：中文 ≤5 字／秒舒適、>7 直接擋。
3. S-S：kind 合法、強效果字數與密度過關；未知模式直接擋。
4. 長片：逐句 caption plan 全部 `clean` 且沒有 highlight；impact 必存在 `emphasis_overlays` 獨立軌。
5. 真 ffmpeg 燒字測試，不以「ASS 文字檔看起來對」取代實際 render。
6. 人眼看：手機尺寸可讀、主體不被遮、動態不抖／不閃、色彩與題材一致、強效果真的落在語意節點。

## 8. 程式入口

- 決策與記憶：`caption_director.py`
- Shorts ASS：`silent_vlog_maker/shorts_vertical.py`
- Shorts gate：`longform_maker/shorts_gate.py`（S-S）
- 長片逐句字幕：`longform_maker/word_captions.py`
- 長片巨字／數字：`longform_maker/emphasis_overlays.py`
- 共用 visual plan：`visual_director.py` → `caption_system`
- Imagegen 素材索引：`community/hao-motion-kit/assets/glow_text/imagegen/manifest.json`
- Deprecated 程式字：`community/hao-motion-kit/glow_text_assets.py`（不可自動選用）
