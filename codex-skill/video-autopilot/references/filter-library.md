# Hao Filter Library v2

## 定位

`filter_runtime.py` 是長片、Shorts 與 Reels 共用的濾鏡中樞，提供像剪輯軟體一樣的 `list`、`inspect`、`apply`、`transition`、`gallery` 與 `doctor`，但所有自動套用都受素材證據、色彩流程與 Hao 審片約束。

濾鏡不是一個模糊名詞，而是四種不同運算：

1. `grade`：素材級色彩處理，只能在字幕、Logo、Tracking、VFX 與圖形之前套一個 Visual Master Look。
2. `temporal`：單鏡的時間性外觀，例如黑白網點、掃描、影印、色差撞擊、失焦彈回與受控柔光。
3. `transition`：兩顆真實鏡頭之間的合成效果；需要剪點、方向、語意與聲音動機。
4. `subject`：只作用於追蹤主體的效果；沒有 editor-verified matte 就不得渲染。

## v2 素材化濾鏡庫

- 10 組 grade：去霧、電影暖柔、明亮 Vlog、Podcast 膚色、旅行、美食、玩具、競技玩具、AI、夜景。
- 14 組 temporal：網點、Xerox、掃描、色差、blur snap、暖回憶、冷紀實、高調柔光、底片顆粒、水墨、CMYK、精緻類比印刷、實拍光學稜鏡掠光、日系和紙柔質。
- 10 組 transition：三種撕紙、網點撕紙、墨水暈染、film burn、lens blur、chromatic whip、luma fade、光學稜鏡閃切。
- 4 組 subject：全黑轉彩、主體網點、輪廓脈衝、主體保彩背景去色。

## Imagegen 材質契約

需要 premium 固定圖像的濾鏡不可只靠程序圖形假裝完成。`filter_materials.py` 只解析 `knowledge/filter_materials.json` 登錄的材質；當材質缺失或尚未通過 Hao 審核時，正式渲染一律回傳 `IMAGEGEN_REQUIRED` 並 fail-closed。

目前六個材質家族為：真紙纖維撕邊、真底片灼光／漏光、墨水毛細擴散 luma matte、光學玻璃／稜鏡反射、Xerox／網點／Riso 印刷紋理、日系和紙自然纖維。全部先由 OpenAI 內建 Imagegen 產 atlas，再登錄 Asset Workshop。`human_review=pending` 只可用 `--allow-pending-materials` 產生候選 gallery，永遠不可用於 production 或自動路由。

若所缺圖片牽涉真實地址、價格、商品、戰績或實測證據，`imagegen_asset_gateway.py` 必須輸出 `VERIFIED_SOURCE_REQUIRED`，禁止 Imagegen 製造假證據。一般語意素材缺口才輸出 `IMAGEGEN_REQUIRED`；生成失敗或未核准時保留 clean hold／clean cut，不能用泛用 ICON、blob、漸層、程序噪點或舊模板代替。

## 撕紙轉場契約

撕紙轉場不是「直接套一個濾鏡」的單鏡運算。它由 outgoing shot、incoming shot、時間 alpha、經 Hao 核准的真紙纖維 Imagegen atlas、陰影、可選 halftone monochrome 中層與 tear SFX 組成。只有照片、紙張、檔案、章節、歷史或版面翻頁等語意成立時使用；一般景點切換仍以 clean cut、match cut、J/L-cut 或真實遮擋為優先。

## CLI

```powershell
python filter_runtime.py list
python filter_runtime.py list --category transition
python filter_runtime.py inspect torn_paper_vertical
python filter_runtime.py apply input.mp4 output.mp4 --preset travel_airy_local
python filter_runtime.py apply input.mp4 output.mp4 --preset scanline_focus --strength 0.3
python filter_runtime.py apply input.mp4 output.mp4 --preset subject_black_to_color --matte subject.mp4
python filter_runtime.py transition a.mp4 b.mp4 transition.mp4 --preset torn_paper_vertical --motivation "照片翻頁進入下一站" --evidence two_real_source_shots --evidence paper_or_chapter_semantics --evidence audio_transient_or_tear_sfx
python filter_runtime.py gallery a.mp4 gallery --source-b b.mp4
# 僅供 Hao 審查未核准材質，禁止 production：
python filter_runtime.py gallery a.mp4 gallery --source-b b.mp4 --allow-pending-materials
python filter_runtime.py selftest
```

Hao 明確指定某個轉場時，CLI 可用 `--manual-approved` 越過自動 evidence completeness，但仍必須填 `--motivation`，且成品繼續需要 Quality-95 與 Hao 審片。

## 自動選用

- `clean_cut` 永遠是預設與缺證據 fallback。
- 同一支片只能有一個 grade Look；不同鏡頭可先各自做一級校正，但不能疊創意 LUT。
- Shorts 動態濾鏡通常只維持 0.2–0.9 秒；長片以章節標點或語意節點使用，不可成為全片皮膚。
- transition 使用量仍受 `mediastorm_craft.py` expressive transition budget 控制。
- subject filters 必須檢查首／中／尾 matte 邊緣、遮擋、手指／臉部誤吃與 track loss。

## QA

1. `imagegen_asset_gateway.py selftest` 驗證缺圖與真實證據分流。
2. `filter_materials.py selftest` 驗證材質登錄、人工審核狀態與不可選用閘門。
3. `filter_runtime.py selftest` 驗證 38 組 preset、所有 renderer style 與 fail-closed 決策。
4. `composition_runtime.py selftest` 驗證 filter adapter 能進入整數 frame render graph。
5. `mediastorm_craft.py selftest` 驗證撕紙缺證據時退 clean cut。
6. 真素材 `gallery` 產生 contact sheet 與逐 preset MP4；pending 材質只能形成候選審查版。
7. 所有新 gallery 或視覺成品固定執行 `review deliver`，交給 Hao 手機／電腦人工審核。
