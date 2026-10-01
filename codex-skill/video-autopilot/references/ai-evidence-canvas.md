# AI Evidence Canvas（AI 證據畫布）

這是一套**資訊呈現文法**，不是固定美術模板。來源是 Hao 明確喜歡的 AI 教學參考影片；只抽象學習其空間敘事、證據層級與節奏，不複製原影片的畫面、字型、平台 UI 或版式。

## 1. 選用條件

同時滿足以下三點才啟用：

1. 內容有三份以上可視化真證據：介面、提示詞、文件、資料表、流程圖或成品。
2. 旁白在解釋資產之間的關係，而不只是示範單一按鈕。
3. 工作台能幫觀眾維持空間記憶；拿掉後會更難理解順序或關係。

若內容是逐步點擊、真人口播、實景 Vlog 或只有抽象概念，改走乾淨 screencast、真人／實景或題材專屬美術，不啟用本 grammar。

## 2. 核心原則

- **Outcome first**：先給成果，再展開資產與方法。
- **Evidence is the hero**：真實截圖、真實輸出、真實檔案是主體；背景只提供空間座標。
- **One active focus**：同時可以看到多張卡片，但只能有一個可讀主焦點。
- **Zoom means hierarchy**：縮放代表「現在讀這裡」，不是裝飾或假轉場。
- **Full bleed proves payoff**：講成果、人物情緒或實際操作時，畫面必須離開工作台，由真素材全畫面接管。
- **Grid is optional scaffolding**：格線可以協助深度與定位，但不是 AI 開場標誌；沒有功能就移除。

## 3. 狀態機

| state | 任務 | 必要證據 | 離場條件 |
|---|---|---|---|
| `hero_result` | 先兌現標題 | 最強成品／before-after | 觀眾已知道結果值得看 |
| `asset_cluster` | 建立 3–5 份資產的地圖 | 真實檔案／截圖縮圖 | 開始解釋其中一份 |
| `focus_evidence` | 放大一張證據並逐點標註 | 可讀主卡＋單一焦點框 | 該論點證明完畢 |
| `compare_or_sequence` | 顯示差異或流程 | A/B 或 1→2→3 | 關係已理解 |
| `full_bleed_payoff` | 展示操作、人物或成片 | 真 screencast／真影片 | 新章節或回顧 |

不得建立 `empty_title_card`、`generic_transition_card` 或「只有背景＋模板角色標籤」的狀態。

## 4. 畫面與動畫

- 工作台主題由題材 token 決定：`dark_neutral`、`cobalt_clean`、`paper_bright`；黑網格不是預設值。
- 卡片 8–16 px 圓角或直角皆可，但同片一致；陰影只負責分層，不做廉價厚描邊。
- 進場 180–320 ms；camera reframe 240–420 ms；annotation 120–220 ms。
- 每次 reframe 必須停穩後再開始讀小字；長片最少保留可讀時間，不能為了節奏縮短證據。
- Shorts 同時最多 3 張可辨識卡；長片總覽最多 5 張，進入細節後只留 1 主＋1 輔。
- J/L cut、click、paper tick、subtle whoosh 可用；禁止無語意圓形、波紋或幾何遮罩轉場。

## 5. 字幕

- Shorts：一行或兩行白字；單句最多一個關鍵詞色；顏色取自主題 accent。
- 長片：常規字幕不花俏；巨字、數字或 tracked label 只在真正的數據／挑戰節點使用。
- 文件內小字與字幕不可同時搶讀；需要讀文件時，字幕縮短或延後。
- 所有中文先轉繁體並跑語意斷句、safe-area 與燒錄後 OCR／frame QA。

## 6. 低 Token scene plan

規劃器只輸出 grammar、theme 與狀態，不逐幀重寫排版：

```json
{
  "grammar": "ai_evidence_canvas",
  "theme": "cobalt_clean",
  "beats": [
    {"state": "hero_result", "evidence": "output_01"},
    {"state": "asset_cluster", "evidence": ["prompt", "workflow", "result"]},
    {"state": "focus_evidence", "evidence": "workflow", "focus": "step_2"},
    {"state": "full_bleed_payoff", "evidence": "screen_demo"}
  ]
}
```

渲染層從固定 motion token、safe-area、題材色票與字體 fallback 執行；同一畫面只讓一個 focus active。

## 7. QA Gate

- [ ] 開頭是成果／問題證據，不是空網格。
- [ ] 每張卡都能指出來源，沒有白紙圖示冒充內容。
- [ ] 每次縮放都對應旁白新焦點。
- [ ] 真操作與最終成果有全畫面段落。
- [ ] 無平台 UI、私人通知、工作列、帳號與敏感資訊。
- [ ] 沒有模板角色名稱、假 HUD、無因果幾何轉場。
- [ ] 手機尺度能讀主訊息；文件小字另有放大狀態。
- [ ] 長片沒有把工作台當永久皮膚。
