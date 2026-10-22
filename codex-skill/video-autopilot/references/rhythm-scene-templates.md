# 節奏場景模板：長片與短片

只在任務需要多場景節奏模板、品牌 Motion、montage，或使用者指定約 2–5 秒換景時啟用。一般教學、訪談、操作證據與表演仍以內容為準；需要連續看的操作不可為了湊切點打斷。

## 先選對系統

先查當次 Editkin 的 `list_editkin_modules` 與當前素材庫的認證／revision，不靠歷史清單推斷可用效果。Motion Library 的文字、轉場、背景是不同種類；不要把舊 `graphic.motion_design_v3` 或零散的舊 reference card 當成整套新庫。

預期的原生入口是 `graphic.text_motion`、`transition.motion_pair`、`background.motion_loop`，需要內含 Motion Library 的 Editkin 版本。名稱由當次能力發現核對；模組缺失就記錄 `NEW_MOTION_RUNTIME_REQUIRED`，不得默默回退舊字卡、捏造已安裝，或修改正式環境來掩蓋落差。編舞與字體來自 Editkin，不在 Skill 另寫動畫引擎。

`rhythm_templates.py` 是前置規劃與檢查工具，不是 renderer，也不執行 Editkin mutation。它接受當前 Editkin 匯出的 item id、tags、kind、implemented、artStatus、revision、showcasePlate 與 engineVersion；自動選型由 catalog tags 決定，只選已認證項目，沒有寫死的預設效果白名單。明確指定的候選項目也必須已實作且認證 revision 相符。

## 編排

- `shorts.rhythm`：9:16；較快的 hook → 概念交換／重點 → payoff／品牌。預設 720×1280，可指定同畫幅 1080×1920 等解析度。
- `longform.rhythm`：16:9；chapter → concept → emphasis → recap。預設 1280×720，可指定同畫幅 1920×1080 等解析度。長片逐章維持同一專案；不是把短片裁寬，也不是先把章節燒成影片再匯入。
- 約 2–5 秒是一個有內容的場景預算，畫面內仍可有逐字、翻面、標題交換等多個動作。文字須讀得完。每個新場景都要有敘事目的，不是同一張卡反覆換字或定格十秒。
- **30 秒的節奏影片預設 8–12 個有意義的場景**；使用者較新的明確要求優先，不能把「10 景」當硬上限。指定 15 景等明確編排時，story 用 `sceneCountOverride: {count: 15, reason: "當次使用者明確要求與範圍"}`，plan 保留並重驗相同數量；閱讀時間、2–5 秒、覆蓋、revision 和認證護欄照舊。這是創意參數，不能當外部動作或美術認證授權。
- 所有時間轉成整數 frame。場景完整覆蓋 `[0,totalFrames)`；尾數重新分配，不能留下黑洞、單幀尾卡或複製 filler。素材不夠就補有效內容或報缺口，不把圖形強行撐長。
- `proof`／`presenter` 的連續停留可明列 `holdReason` 與精確時長。這是保留真實證據的例外，不能用來繞過品牌 Motion 的節奏要求。
- 同一段片只維持一套有主次的色彩與字體系統。效果服務文字動詞與畫面意義；不是每刀都轉場。背景、文字與轉場需依 catalog kind 使用。

## 使用與接回 v4

```powershell
python rhythm_templates.py plan --story story.json --catalog current-motion-catalog.json --out rhythm-plan.json
python rhythm_templates.py check --plan rhythm-plan.json --catalog current-motion-catalog.json
```

story 的形狀如下（30 秒直式示範；`itemId` 對應 Motion Library 的文字項目，文案是 Editkin 動態示範用的原創字句，**不是所有影片的預設文案**）：

```json
{
  "profile": "shorts.rhythm", "durationSeconds": 30, "fps": "30",
  "scenes": [
    {"id": "count-in", "role": "hook", "itemId": "T48", "lines": ["3", "2", "1", "開始"], "durationSeconds": 2, "meaning": "以倒數建立開場節拍"},
    {"id": "brand-open", "role": "brand", "itemId": "T01", "lines": ["Editkin"], "durationSeconds": 3, "meaning": "品牌第一次完整出現"},
    {"id": "type-stack", "role": "concept", "itemId": "T05", "lines": ["文字", "開始跳", "起來"], "durationSeconds": 3, "meaning": "三行逐拍堆疊"},
    {"id": "brand-close", "role": "brand", "itemId": "T01", "lines": ["Editkin"], "durationSeconds": 3, "plate": "bg", "meaning": "回到品牌，以深色底收尾"}
  ]
}
```

示範只列四景以說明欄位；實際 30 秒片仍需 8–12 個有內容的場景並完整覆蓋時長。一般製片的文字、數字、來源與 beat 依舊來自該片證據。catalog 的 revision 或 engine 改變後須重排、重驗，不能拿舊 SHA 的編排當新來源。

plan 中 `groups` 僅是規劃分組；實際命令數仍以 Editkin prepare 結果與 v4 容量判斷。完整流程仍是當次能力／語意與 inference → prepare 模組 → 同一 v4 audit → atomic apply → 同一 revision render。長片使用 longform session 與 chapter plan set，一個專案最後 render 一次；不要將逐景 ProRes 素材快取誤稱為原生可編輯文字，也不要把 sidecar 編排冒稱已整合的時間軸功能。

## 交付前審查

1. 看實際輸出的動作、換景、字體閱讀與聲畫，不只看命令成功或中間格。對照任務給的參考效果。全片解碼、精確 frame、色彩與音訊另記收據。
2. 拒絕 10 秒定格、空缺、重複填充、文字不足閱讀時間，以及沒有對上當前 revision 的素材。程式測試與動態抽樣都不等於人類美感驗收。
3. 新編排保留 `ART_PENDING_REVIEW`，等創作者審查；未認證候選不進正式預設。手機安全交付、雲端授權與發布限制沿用原契約，不能因為這個模板略過。

## 流暢度與效果的操作教訓

- 先查當次庫的實作／revision／認證：例如 T25 是 Split Flap、T26 是整卡翻面，不能混稱。art pending 的項目只能放在隔離的研發候選，不能升為正式預設；`rhythm_templates.py` 的一般選型只用已認證項目。
- 流暢度同時檢查剪接與動作：獨立模板進出場的空段應剪掉，用有內容的 active window 接鏡；保留實際 source window 和 frame clock，不以補幀／重複格的 60 fps 封裝冒充連續動畫。
- 完整名稱標籤應選可整組停留的模板，不能誤選只顯示單字／單字母的 sequence。閃光只用在有理由的切點，檢查實際峰值與回落。
- 純 3D 原始幾何慢轉展示的感知流暢度常輸給 2D 字體節奏；3D 用在有用途的翻牌看板、立體字或空間切換。Split Flap、Glitch 或閃光不是每支片必加的通用規則。
- 素材數、幀率、效果數量和照片接觸表都不能代替動態美感審查。需要 2D／3D 混合的動態海報時，讀 [editorial hybrid motion](editorial-hybrid-motion.md)，先把每景 job、缺口與實際操作路徑寫清楚；不能只替舊片換色，也不能把那套美術風格套用到一般影片。
