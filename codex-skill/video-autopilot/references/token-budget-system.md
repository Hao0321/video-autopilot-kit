# Autocut Token Budget System

## 目的

自動剪輯要「記得住」又不能每次把全部歷史餵給模型。系統把記憶分成三層：

| 層 | 放什麼 | Token 成本 | 更新條件 |
|---|---|---:|---|
| T0 code／gate | 真實、安全、字幕區、輸出、容量與技術 QA | 0 推理 Token | 可客觀驗證且不能違反 |
| T1 context packet | mode／format／domain + 最多 6 條 pinned memory | 650–1,100 | runtime 真的需要 |
| T2 reference | 一份深度研究或 canon row | 按需 | 出現衝突、新題材或連續 QA 失敗 |

`context_router.py` 預設建立 `current_context_packet.json`。同一路由內容不變就 cache hit；新任務覆寫
同一個檔案，不產生版本樹。packet 只附 source hash 和升級路徑，不複製研究全文。

## 護欄與創意的界線

硬規則：不得編造、不得刪原始素材、current-only、音訊／字幕／缺幀／重複鏡頭 gate、Token 上限。

軟規則：構圖、色彩、景別、字卡、動態、剪點、轉場、留白、情緒曲線。這些使用題材卡與偏好權重，
可被素材證據或使用者新回饋覆寫。若把軟規則改成 assert，系統應視為過度硬編碼。

## 使用

```powershell
python context_router.py route --mode build --format shorts --domain auto --topic "拉麵實測" --output-dir "工作目錄"
python context_router.py audit
python context_router.py selftest
```

`visual_director.write_visual_plan()` 會自動建立 packet，並在 plan 寫入 `context_budget`。只要 estimated
超過 max，build 在計畫階段直接失敗，不把超量上下文帶進後續剪輯。

## 學習回饋

1. 單支片回饋先記成 soft preference，不進 gate。
2. 至少跨三支片重複成立，拿舊 corpus 做正反回歸。
3. 通過後只更新一個 SoT：題材路由、domain card、格式卡、偏好權重或 gate 五選一。
4. 新規則必填適用範圍、反例、優先級、驗證方式、是否可覆寫。
5. 研究全文留 reference；只把可執行摘要放進 T1。

新回饋一律先走 `knowledge_lifecycle.py record`。相同規則用 fingerprint 合併；支持數達 3、沒有
contradiction 才進 pinned card。舊 `optimization_log.md` 不再直接追加，避免「學越多、每次載越多」。

## 量測口徑

`audit` 的 reduction 是相對「整批讀取 references」的最壞情況，用來證明路由上限；它不是歷史 API
帳單。實際工作應記錄 packet estimated tokens、max tokens、cache hit 與是否升級讀取 T2。
