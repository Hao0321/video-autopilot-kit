# Quality 95：從可交付到高品質

## 核心定義

95 分不是自我宣稱，也不是所有測試綠燈的別名。認證條件固定為：

1. `score >= 95`。
2. 無 `BLOCK` 或 `REVIEW` 負面回歸。
3. 已由 Hao 完成時間碼審片；手機或電腦都可使用，但審片責任不隨裝置改變。
4. 審片評分已回寫，Creator Aesthetic Standard 狀態為 `PASSED`，問題已修正或明確接受。

機器負責擋已知爛法；人負責判斷美感、節奏、情緒與剪點是否順暢。
美感改用 `hao-aesthetic-standard.md` 的十維量表，Shorts 與長片共用母標準、採不同時間權重；其中 MrBeast 資訊能量與影視颶風電影工藝為正式 benchmark。缺任一維都維持 `REVIEW`。

## 整套專案驗收

公開安裝以 `python src/system_health.py` 與 CI gate 驗收。

這是系統架構驗收，不能拿來宣稱某支影片已經好看；影片仍照下方流程逐支簽核。

## 每支片的輸出

- `_out/_qa/QUALITY_95.json`：分數、證據、負面案例命中。
- `_out/_qa/QUALITY_95.md`：人類可讀摘要。
- `_out/_review/review.html`：Hao 人工審片頁（響應式，手機／電腦皆可）。
- `_out/_review/review.json`：時間碼、問題類別、評分。
- `_out/_review/finalized.json`：回寫記憶後的認證結果。

## Shorts

Shorts 技術 QA 通過後，用 `quality_95.py score` 建立 provisional 報告、`review_loop.py create` 建立 Hao 審片頁。
尚未審片不是刪除技術成片的理由，但狀態只能是 `REVIEW`，不能冒充 `CERTIFIED_95`。

```powershell
python src/review_loop.py serve "videos/_INBOX/vertical/N/_out/_review"
# 手機同 Wi-Fi 開啟終端顯示的網址，送出後：
python src/review_loop.py finalize "videos/_INBOX/vertical/N/_out/_review"
```

## 長片

`final_delivery_qa(..., sheets_dir=qa_dir)` 在原有技術 QA 後建立同一份 Quality-95 報告與審片頁。
長片不使用花俏逐句字幕；巨字、數字、Tracking 只在 Hook、Proof、轉折與 Payoff 選擇性出現。

## 已鎖死的負面回歸

- 無內容關聯的全螢幕模板卡。
- 把網格當所有題材的預設開場。
- 播出 `HOOK`、`LOWER THIRD`、`SHAPE / PLAY`、`TRAVEL / JOURNAL` 等模板角色字。
- 沒有鏡頭運動、遮擋或資訊理由的幾何轉場。
- 文字被切、貼邊、超出安全區。
- 非地點影片長駐假地址條。
- 無證據的 Tracking 標籤。
- 同題材只換素材、敘事幾乎相同。
- 同一素材或音樂在近期內容出現過密。
- 美術家族與題材衝突、照抄參考構圖或同時焦點過多。

## 素材疲勞

素材使用記憶分成 lifetime 與最近 20 支內容。選材只按近期密度與連續使用扣分，不會因為一個好素材
歷史總使用量高就永久封殺。高疲勞是 `REVIEW`，可用具體創作理由保留，不是死規則。

## 回饋如何記死

Hao 審片的每個問題都帶影片、秒數、類別與文字說明。`finalize` 會呼叫
`knowledge_lifecycle.record_feedback()` 去重入帳；已知技術失敗直接由 corpus 回歸，主觀偏好仍是 scoped soft rule。
這樣新的訓練能融合舊記憶，同時不把記憶庫與 Token 一直撐大。
