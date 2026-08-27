# MrBeast × 影視颶風正式評分與動態效果路由

兩者是跨長短片的工藝標竿，不是固定濾鏡或逐幀仿作：MrBeast 評資訊能量與視覺回報，影視颶風評鏡頭、剪點、聲音、調色與轉場工藝。題材語法與 Hao 美感仍優先。

## 導航

- [1 評分邊界](#1-評分邊界) · [2 能力分級](#2-動態效果能力分級) · [3 物件遮罩高光](#3-mask_sheen-物件遮罩高光) · [3.1 高資訊事件](#31-高資訊事件註冊)
- [4 節奏與頻率](#4-節奏與使用頻率) · [5 研究依據](#5-研究依據與校準) · [6 可追溯研究更新](#6-2026-08-22-可追溯研究更新) · [可反駁推論](#本-skill-的可反駁推論)

## 1. 評分邊界

### MrBeast 資訊能量（10 分）

| 子項 | 分數 | 通過證據 |
|---|---:|---|
| 承諾與 stakes | 1.5 | 開場立即看懂主體、衝突、規模或結果問題 |
| 狀態可視化 | 1.5 | HUD、倒數、進度、金額、勝負會隨事件更新，不是裝飾 |
| 焦點引導 | 1.5 | 箭頭、Tracking、遮罩、尺度或光線真的指向當下主體 |
| 尺度／價值對比 | 1.0 | 對比物、相對大小、數字與證據同框，沒有虛構價值 |
| Pattern interrupt | 1.0 | 只在資訊轉折、笑點、揭露或注意力下滑風險點出現 |
| Payoff 回報 | 1.5 | 結果比鋪陳更清楚，畫面、字、音效同步落點 |
| 節奏波 | 1.0 | 快慢有對比；不是每格都動、每句都放大 |
| 完成度 | 1.0 | 中英數品質、遮罩邊緣、掃描紋、光暈、安全區均成熟 |

### 影視颶風電影工藝（10 分）

| 子項 | 分數 | 通過證據 |
|---|---:|---|
| 鏡頭動機 | 1.5 | 推拉搖移、速度變化或重構圖跟情緒／資訊一致 |
| 剪點與連續性 | 1.5 | 動作、方向、視線、形狀、遮擋或聲音能跨鏡頭接續 |
| 聲畫節奏 | 1.5 | J/L-cut、音橋、靜默、impact 與音樂 phrase 有設計 |
| 調色與曝光 | 1.5 | 先校正霧感與 shot match，再低強度風格化；膚色／產品色可信 |
| 光影與材質 | 1.0 | 局部高光、景深、顆粒、halation 有理由且不蓋真實細節 |
| 空間與尺度 | 1.0 | wide-medium-detail、前後景、視差或運鏡建立空間 |
| 敘事能量波 | 1.0 | 建立、累積、釋放、留白有清楚波形 |
| 克制與隱形工藝 | 1.0 | 沒有為展示模板而插入無動機轉場或空白字卡 |

成片總美感仍按 `hao-aesthetic-standard.md` 十維加權。任一 benchmark 低於 7/10 只能 `REVIEW`；硬性失敗直接 `BLOCKED`。長片加重影視颶風，Shorts 加重 MrBeast，但兩軸都不能缺席。

## 2. 動態效果能力分級

| 等級 | 能力 | 執行條件 |
|---|---|---|
| A：可穩定自動化 | 中英數立體／發光／掃描紋字牌、關鍵幀 Tracking、有限 CSRT、挑戰 HUD、勝負／價格狀態牌、競技區鎖定、圓形／多邊形物件高光、計數器 | 真片、時間碼、證據、bbox／matte、QA 報告齊全 |
| B：需人工關鍵幀 | 不規則人物／車輛遮罩、Roto 邊緣、物件切出、遮擋前後層、平面替換、透視 Tracking、whip／match／occlusion cut、3D 視差 | 人工確認 mask path、剪點、方向與至少首中尾關鍵幀 |
| C：不得自動猜 | 高速旋轉物單體 Tracking、沒有第二顆 shot 卻宣稱 match cut、假 3D／假 CGI 變形、偽造價值、無證據勝負、全景 AI relight | 改用固定競技區、clean cut、clean hold 或標記人工 VFX |

## 3. `mask_sheen` 物件遮罩高光

- 分類固定為 object overlay，不是 transition。
- 光帶只准存在於人工驗證的 ellipse、rectangle、polygon 或外部 alpha matte 內。
- 建議 0.25–0.60 秒、每物件每次展示最多一次、opacity 0.45–0.68、羽化邊緣。
- 先取得 bbox/mask path，再讓斜向光帶穿越；不得整格閃白或刷到背景／手部。
- 不規則人物與車輛若沒有可靠 matte，降級 clean hold，不用大橢圓假裝去背。
- QA 必看開始、中段、結束三格；檢查 matte leakage、跳位、過曝、UI／字幕遮擋。
- 它的正確合成順序是：追蹤／關鍵幀 → subject alpha／polygon matte → 材質 profile → 斜角 core band＋secondary bloom → matte 相乘 → 合回已校正 footage。不得用全畫面白片或 graphic transition 替代。

## 3.1 高資訊事件註冊

`mrbeast_editing_system.py` 將可驗證功能收斂成 promise cold open、value label、challenge ledger、tracked callout、subject sheen、money burst、scale ladder、subject occlusion cut、whip replacement、fast pullback reveal、proof freeze 與 breath reset。每個事件都有前置 evidence、可讀時間、effect budget 與 contrast gap；缺證據時只記 blocked reason，不生成假效果。這是 Hao 自有事件文法，不搬用對方 Logo、專屬資產、逐鏡時間線或頻道識別。

## 4. 節奏與使用頻率

- 效果不是固定密度 KPI。先標事件：promise、proof、state change、reveal、payoff；沒有事件就不加。
- 同一視覺語法不得連續兩次；連續三個效果節點後至少留一次 clean hold。
- 長片普通段落以素材與聲音推進；巨字、遮罩與 HUD 只在 Hook、Proof、轉折、Payoff。
- Shorts 可以更密，但同一時刻仍只保留一個主焦點；追蹤字牌、普通字幕、HUD 不得重複講同一句。
- 每個光效必須有明度 headroom；已過曝、白色產品或霧面無反射材質要降低 opacity 或禁用。

## 5. 研究依據與校準

- MrBeast 官方影片 `$1 vs $100,000,000 Car!`：價值階梯、物件標籤、狀態 HUD、尺度與 payoff 的公開樣本。
- MrBeast 團隊公開 editor 職缺：明列 kinetic typography、custom tracking graphics、keyframing、motion tracking、masking 與高節奏 comedic timing。
- Adobe After Effects 官方 Mask Tracker／Roto Brush 文件：mask 需逐格檢查漂移；position、scale、rotation、skew、perspective 應依物件變化選法。
- Blender 官方 Tracking／Shadow Catcher 文件：true 3D 合成必須解鏡頭、校正場景方向並用 shadow catcher 建立接觸；缺資料不可拿 2D 假裝。
- Hao 提供的實拍與逐次回饋是本專案最高優先校準資料；外部樣本只補充技法，不覆蓋已 pinned 的負面規則。

## 6. 2026-08-22 可追溯研究更新

以下把「團隊直接說明」「官方頁面可見內容」與「本 Skill 推論」分開；不得把推論寫成對方的官方公式。

### MrBeast／Beast Games：直接團隊證據

- [Boris FX — Art of the Cut: Beast Games](https://borisfx.com/blog/aotc/art-of-the-cut-beast-games/) 是 2025-05-29 對 lead editor、MrBeast senior editor 與 post 團隊的直接訪談。可確認核心不是一直快切，而是 clarity 與 stimulation：先建立位置、規則、stakes、單一概念／情緒，再加入混亂 montage。
- 同一訪談可確認 `backbone → evidence pull → enrichment` 工作法：先用主攝影機建立故事骨架，Timeline 以 text slug 標記仍缺的反應／證據，再由助理找可選鏡頭；不是先把全部素材塞進 Timeline。
- 結構以 setup／payoff 分工；聲音以 build → 抽空 → hit 讓高潮成立，對話、音樂與效果可依 BPM 微調，但這不等於每個 cut 都放 whoosh。
- 高成本 graphic 先寫 script、錄 temp VO、放 rough footage／wireframe，確認時間與 handles 後才進 3D／AE；因此本 Skill 的 expensive VFX gate 固定在 animatic 後。
- 以上只證明該團隊公開描述的流程；不代表每支 MrBeast 影片使用同一 cut 密度、字體、插件或秒數模板。

### 影視颶風：官方工作流與課程表面

- [官方《月更10期？！影视飓风用什么做视频？》](https://www.youtube.com/watch?v=QfOzAdUN6FM) 明確定位為後期流程與常用工具介紹；[Bilibili 官方同片](https://www.bilibili.com/video/BV1mv411e7DE/) 另標記後期、插件、調色與工作流。這支持「拍攝／收音／剪輯／AE／調色／編碼是連續管線」，不支持憑空推定固定 LUT 或轉場密度。
- [官方剪輯課程頁](https://www.bilibili.com/cheese/play/ep2561240) 公開列出綜藝包裝、進階平面跟蹤、多機位訪談、Vlog 結構與色彩等單元。Editkin 因此把它們分成 graphics／tracking／multicam-dialogue／story-color 能力，不以單一「影視颶風風格」濾鏡取代。
- 對官方頻道成片可做 observable shot audit（wide/medium/detail、J/L cut、sound bridge、shot match、graphic restraint），但未獲團隊說明的部分一律標為本 Skill 推論，不寫成內部標準。

### 平台官方：包裝與回填

- [YouTube 官方推薦系統說明](https://support.google.com/youtube/answer/16559650?hl=en) 將內容表現分成 appeal、engagement、satisfaction，並要求開場立即兌現 title／thumbnail 的承諾。本 Skill 因此把 `openingFulfillment` 設為必填，而不是只追 CTR。
- [YouTube 官方 Test & Compare](https://support.google.com/youtube/answer/13861714?hl=en-on) 與官方 title/thumbnail A/B/C 公告允許最多三個差異足夠的假設，勝者依 watch-time share；流量不足或差異太小可能沒有 winner。低曝光只做 2 個清楚假設，不能把無顯著差異寫成成功公式。

### 本 Skill 的可反駁推論

1. `clarity before stimulation`：locate／rules／stakes 未清楚前，chaos、Meme、密集字幕與 VFX 都延後。
2. `one idea + one emotion + one focus`：同一 beat 的字幕、圖形、聲音與鏡頭只服務一個 primary focus。
3. `skeleton before polish`：先鎖 backbone、setup/payoff 與證據缺口，再加反應、B-roll、motion、SFX 與高成本 VFX。
4. `contrast makes impact`：能量不是單調上升；breath／silence 必須在 plan 中可見，高潮才有相對差。
5. 這五條必須接受 Hao 審片與 D2/D7/D28 outcome 推翻；單一公開訪談或單支影片不能直接升格成永久個人偏好。
