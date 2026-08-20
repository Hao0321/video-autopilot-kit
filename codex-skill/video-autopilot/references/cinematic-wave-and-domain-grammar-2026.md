# Hao Cinematic Wave＋跨領域剪輯語法（2026-08-08）

## 導航

- 研究邊界與影視颶風拆解
- Macro／Meso／Micro 節奏模型
- 跨領域語法／自動剪輯 contract／學習閉環

> 目的：把「像影視颶風一樣流暢」翻成可執行、可測試的節奏系統。這裡學的是公開作品中可觀察的
> 高階原理與通用電影文法，不複製影視颶風的 logo、字卡版式、音效包、逐鏡腳本或品牌素材。

## 1. 研究邊界：哪些是資料，哪些是推論

- 影視颶風官方公開的後期流程影片說明，直接確認其作品是以完整後期流程與多種工具協作完成；
  旗下前期工具「閃電分鏡」也把分鏡、通告、場景與場記視為同一條流程。由此可確定：高質感不是
  剪輯軟體裡臨時加轉場，而是前製到後製的整體設計。
- 影視颶風官方課程頁把「剪出和影視颶風一樣的視頻」與「音樂處理、音效設計思維」列為獨立單元。
  可確定聲音不是最後補上的裝飾。
- 「result-first、景別組句、能量波、payoff 前呼吸」是對公開成片的編輯分析，屬於本專案的
  **可驗證推論**，不是影視颶風官方宣稱的內部公式。
- Adobe 官方把 J-cut／L-cut定義為音畫不同時切換、用來維持場景流動；Blackmagic 官方訓練把
  訪談、劇情、紀錄片、音樂表演、變速與 Fairlight sound design 分開教。這支持本專案「領域不能
  共用同一刀速」的架構。
- YouTube 官方 retention 說明把前 30 秒、top moments、spikes、dips 分開；若亮點在後段，建議把
  compelling content 提早。落地成 cold open 與發布後的 retention 回灌，而不是迷信固定秒數。

## 2. 「影視颶風感」拆成七條可執行規則

1. **先兌現、再解釋**：第一鏡用結果、後果、最強動作或最有代價的一句話；logo 不擋前面。
2. **鏡頭不是單顆，是句子**：一組至少三種功能：context wide、action medium、detail／reaction。
3. **快慢必須成波**：cold open 高能，context 降，兩輪 build 上升，payoff 前先 breath，再進高潮。
4. **剪點要有動機**：情緒、資訊、動作、視線、聲音至少命中一項；沒有就不切。
5. **聲音先把場景縫好**：用 J-cut 讓下一場先被聽見、L-cut 讓上一場留有餘韻；現場聲／foley
   優先於每刀 whoosh。
6. **轉場服從方向**：動作、運鏡、人物視線與畫面幾何要連續；whip、ramp、glitch 只在內容真的
   提供動機時使用。
7. **高潮前要敢安靜**：payoff 前縮音樂約 8 dB，但保留 room tone、呼吸或主體聲；「無」要靠
   前後的「有」才會成立。

## 3. 三層節奏模型

### Macro：整片能量波

Shorts 預設：`cold_open → promise → build → turn → breath → payoff → resolve`。

長片預設：`cold_open → promise → context → build_1 → reset → build_2 → breath → payoff → resolve`。

`visual_director.py` 會輸出每段時間、能量、意圖與 shot-duration range。高能段縮短鏡頭、低能段
拉長；不是全片越快越好。

### Meso：鏡頭組句

每個 act 都有 `sequence_plan`：

- establishing/context：觀眾知道在哪裡、誰在做什麼。
- medium/action：主動詞發生。
- detail：質地、手部、UI、材料、數字或關鍵證據。
- reaction/consequence：動作為什麼重要。
- return/resolve：回到人物、成品或空間，讓一句話結束。

### Micro：剪點與聲音

- `events`：只在語意轉折、證據、價格、問題、步驟與 payoff 插卡；不得等距。
- `audio_plan.bridges`：章節／場景邊界安排 J-cut 與 L-cut。
- `audio_plan.pre_payoff_space`：payoff 前建立短呼吸。
- `pace_gate.py` D-E：鏡頭長度變異 CV 過低時警告「節拍器式等長剪」。

## 4. 十八領域語法速查

| domain | 第一鏡 | 鏡頭組句 | 聲音主角 | 禁忌 |
|---|---|---|---|---|
| `ai` | 完成結果／反直覺操作 | result→screen→cursor action→proof | click、keyboard、乾淨 voice | 每個 click 都 zoom、假 UI |
| `food` | 牽絲／切面／起鍋／入口 | place→action→texture→reaction | sizzle、knife、crunch | BGM 蓋食物聲、全程俯拍 |
| `travel` | 目的地最值畫面 | reveal→wide→human scale→POV→detail | 當地 wild track | 漂亮空鏡無地理關係 |
| `toy` | 完成品機關／局部懸念 | package→seal→macro→assembly→reveal | 包材 ASMR、snap | 規格念完才拆 |
| `product` | 測試結果／真問題 | result→context→feature→measurement→limit | 機械操作、proof tick | 規格代替實測 |
| `game` | 勝負／失誤／impact | impact→context→input→consequence→reaction | 原遊戲瞬態、反應 | HUD 被遮、glitch 連發 |
| `diy` | after／最大反差 | after→before→material→action→mistake→fix | tool、material contact | 全程縮時、沒有原速錨點 |
| `cafe` | 沖煮／切甜點／空間光 | quiet hook→space→ritual→texture→sip | pour、cup、room | 為快而快、每刀 whoosh |
| `documentary` | 行動後果／人物選擇 | consequence→place→person→evidence→reaction | production sound、room tone | 旁白塞滿、不讓人物呼吸 |
| `interview` | 最有代價的一句 | quote→reaction→two shot→close→context B-roll | clean dialogue、breath | 每句 jump cut、BGM 催情 |
| `automotive` | 引擎＋動態 | engine→wide→control→POV→pass-by→reaction | engine、gear、tire、wind | 方向跳軸、ramp 每個彎都用 |
| `fitness` | 最好一次動作／結果 | goal→setup→wide form→detail→effort→finish | breath、落地、器材 | 只剪肌肉特寫看不懂姿勢 |
| `fashion` | 完成 look／輪廓 | hero→full body→fabric→movement→accessory | fabric、footstep | 轉場比衣服搶、姿勢不連 |
| `architecture` | 空間核心光／尺度 | exterior→entry→wide→human scale→material→light | space tone、footstep | 無方向漫遊、只拍超廣角 |
| `business` | 數字反差／決策後果 | result→problem→case→metric→decision→constraint | clean voice、data tick | 一張圖塞五個結論 |
| `nature` | 動物正在選擇／遇到問題 | behavior→habitat→subject→wait→turn→result | wild track、自然動作 | 罐頭音效擬人過量 |
| `music` | 副歌／招牌動作 | peak→stage wide→lead→instrument→audience→lead | 現場表演 mix | 每一拍都切、失去樂句 |
| `general` | 直接兌現題目 | result→context→action→detail→reaction | production→room→foley→music | 抽象背景代替內容 |

## 5. 自動剪輯 contract

```python
from visual_director import infer_domain, plan_visual_rhythm, write_visual_plan

domain = infer_domain("重機試駕：山路過彎與煞車測試", hint="auto")
plan = plan_visual_rhythm(
    duration=180,
    captions=[(0, 3, "這次最意外的不是速度")],
    genre=domain,
    format="longform",
    seed="episode-17",
)
```

輸出不可只被當成參考文件：

- Shorts renderer 會實際插入語意字卡，並在 payoff 前對 BGM 做平滑 -8 dB 呼吸。
- `shorts_autopilot.auto_plan()` 會使用變長鏡頭波，而非平均分配每段。
- `pace_gate.py` 會對全等長鏡頭列 D-E 警告。
- 長片 PLAN 應把 `sequence_plan` 的 shot function 寫進 shot list，再由 `pace_gate` 驗。

## 6. 發布後學習閉環

1. 上片後讀前 30 秒 retention、top moments、spikes、dips。
2. dip 對回當時 act、鏡頭功能、字幕句與聲音事件。
3. 若 top moment 在後段，把同類 payoff 提早；若 spike 來自看不懂，先修清晰度，不把重播誤當喜歡。
4. 只調對應 domain 的 profile，不用一支遊戲片去改訪談刀速。
5. 累積至少 5 支同領域樣本再改預設範圍；單支只記 hypothesis。

## 7. 來源（2026-08-08 查）

- 影視颶風官方：月更 10 期的後期流程與工具
  - https://www.youtube.com/watch?v=QfOzAdUN6FM
- 影視颶風官方：短片製作幕後與預算限制
  - https://www.youtube.com/watch?v=haS0wpKZpBY
- 影視颶風旗下「閃電分鏡」：前期分鏡／通告／場景／場記流程
  - https://www.mediastory.cc/
- 影視颶風剪輯課程頁：剪輯單元與音樂／音效設計
  - https://www.bilibili.com/cheese/play/ep2561244
- Adobe：J-cut／L-cut 以音畫錯開保持場景流動
  - https://helpx.adobe.com/jp/premiere/desktop/edit-projects/trim-clips/perform-j-cuts-and-l-cuts.html
- Blackmagic Design：DaVinci Resolve 20 官方剪輯、訪談、紀錄片、音樂表演與 Fairlight 訓練
  - https://www.blackmagicdesign.com/products/davinciresolve/training
- YouTube 官方：前 30 秒、top moments、spikes、dips 的 retention 判讀
  - https://support.google.com/youtube/answer/9314415?hl=en-GB
- Taiwan Cinema 聲音講座：聲音、攝影、剪接的律動；先有聲才能凸顯無聲
  - https://taiwancinema.bamid.gov.tw/Articles/ArticlesContent/?ContentUrl=92070
- Nikon：美食影片的故事、動作、構圖、場景與 shot list
  - https://www.nikonusa.com/learn-and-explore/c/tips-and-techniques/beautiful-food-captured-beautifully-in-video-by-elke-talbot
