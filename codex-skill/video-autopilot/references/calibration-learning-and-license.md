# Calibration, Outcome Learning, License and Archive Contract

這份文件是 Visual Master 的證據層；平時由程式讀取，不載入 context packet。

## 1. 相機校準與調色順序

固定順序：相機／輸入辨識 → 已驗證一級校正 → HDR/Log input transform → 單一創意 LUT → 字幕／Logo／Tracking → scope、grade gate 與 Hao A/B 審片。

- `color_calibration_lab.py inspect` 量亮度、對比、飽和、剪裁、色偏與廣義膚色候選。
- 只有 `knowledge/camera_color_profiles.json` 內 exact `camera_id` 且 `status=verified` 的 Rec.709 profile 能自動套用。
- 未知機型、推測 profile、未知 Log、HLG/PQ 不得套相機矩陣；未知 Log 必須先取得 input transform。
- ColorChecker 入口使用人工／校色軟體量出的 patch JSON。最少 18 色塊，保存前後 ΔE76、矩陣與時間；不宣稱未驗證的自動色卡偵測。
- `shot-match` 只輸出 ±0.35 EV、0.88–1.12 飽和與 channel gain 建議，不自動抹平刻意的日夜、冷暖與場景差異。
- `scopes` 產生來源、waveform、vectorscope 三聯圖；`ab-review` 由 Hao 決定膚色、白平衡、層次與風格是否更好。

## 2. 審美與觀眾成效分流

`taste_model.py` 只學 Hao 的 A/B 選擇：候選需附 path、label 與可解釋 feature；同一比較只能投一次。單一偏好不升格，feature 至少 5 次比較才進 preference summary。

`outcome_learning.py` 只學真實平台結果：

- 僅比較同平台、同 D2/D7/D28 視窗；缺資料是 unknown，不補 0。
- 每組至少 5 支才建立 baseline；剪輯 feature 也需 5 個同窗樣本，且只標 correlation，不宣稱因果。
- Hao 喜歡不等於觀眾喜歡；兩套證據可以同時保留，衝突時進人工實驗，不互相覆寫。
- 現有不足門檻時必須輸出 `INSUFFICIENT_EVIDENCE` 與到期快照，不得假裝已學會。

## 3. 授權治理

`asset_license_governance.py` 採 fail-closed：

- 公開 manifest 僅包含政策列出的 redistributable license，而且必須有 provenance。
- 不明、pending、無來源或未識別授權一律排除，不猜 Creative Commons。
- 私人臉部、使用者拍攝、只供專案使用或購買音樂不進社群包。
- 覆寫只能寫入 `knowledge/asset_license_overrides.json`，需要 license、provenance 與 note。

## 4. 缺片段素材與重混

`domain_broll_pack.py` 生成 documentary／interview／fitness／fashion 的橫直式原創 filler。它們是語意 B-roll：不是轉場、不是網格開場、不是 proof，也不得遮住真素材或受訪聲音。

`remix_planner.py` 從 READY／PUBLISHED 找同旅程、同系列候選；新片回原始素材，至少新增敘事、旁白或未發布鏡頭，禁止把燒好字幕的 Shorts 串成合集。

`storage_optimizer.py preview` 只列出 `_archive`／`_planning` 的大型衍生檔。`_INBOX`、`_READY_TO_PUBLISH`、`_PUBLISHED` 永遠受保護；真正冷歸檔需明確外部 target、逐檔 SHA-256 與 manifest，系統不自動刪除。

## 5. 最小命令

```powershell
python color_calibration_lab.py inspect input.mp4
python color_calibration_lab.py scopes input.mp4 scopes.jpg
python color_calibration_lab.py shot-match a.mp4 b.mp4 --output match.json
python outcome_learning.py refresh
python taste_model.py review taste_review.html
python asset_license_governance.py audit
python asset_license_governance.py export-public public_assets.json
python remix_planner.py create
python storage_optimizer.py preview
```
