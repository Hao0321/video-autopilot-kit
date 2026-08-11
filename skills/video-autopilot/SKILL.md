---
name: video-autopilot
description: 將主題、文件或既有素材一條龍製作成可修改、可驗收的教學影片，包含腳本、圖像先行分鏡、9:16 取景、繁中口白、字幕、ACE-Step 配樂、混音、MP4 QA 與版本交付。用於「一句話生成影片」「文件轉影片」「影音一條龍」或需要修正裁切、配樂、口白與音畫品質的任務。
---

# Video Autopilot

把內容轉成可重跑、可驗收的影片專案。保留 `script.md` 與 `storyboard.md` 作為共同控制表，不把畫面、口白、字幕、配樂與 QA 決策散落在聊天記錄中。

## 固定交付

每個專案至少保留：

- `source_digest.md`
- `video_brief.md`
- `script.md`
- `storyboard.md`
- `assets_manifest.md`
- `image_generation_plan.md`
- `hyperframes_prompt.md`
- `audio_plan.md`
- `QA.md`
- `revision_notes.md`
- `final_handoff.md`
- `output/final_v[N].mp4`

## 工作流程

1. 確認片長、比例、語言／地區、是否需要口白、配樂、動畫與發布；機敏文件先在本機遮罩。
2. 先產生摘要、腳本、朗讀稿、字幕稿，再做連續分鏡總圖與逐幕素材。
3. 讀取分鏡總圖的實際寬高；量測白線／分隔線，裁出內容矩形。禁止猜測 3×3 格線、直接採平均格寬，或在未檢查下使用中心 crop。先輸出 panel contact sheet，確認沒有鄰格 sliver、主體被切掉或構圖偏移。
4. 依指定比例輸出；9:16 優先保留完整內容，只有已知焦點時才 cover crop。正式判斷必須使用正式 MP4 抽幀。
5. 口白指定明確 voice，例如台灣中文 `zh-TW`。先做 20～30 秒試聽，內容包含中文、數字、專業名詞與自然停頓；互動模式先取得使用者確認，再批次產生。每幕一個有序音檔，實測時長，最後一幕單獨計算可用時間，避免句尾被截斷。
6. 使用者指出配樂死板、嗡聲或忽大忽小時，路由至 YT_music 的 ACE-Step 流程。先做 3 首約 30 秒候選，排除人聲、刺耳高頻、低頻轟鳴、爆音、隨機噪音與突然結束；只採用 `summary.json` 的 `status=ok` 且 `technical_qc=pass` 候選，實際試聽後選曲。保留 job、config、brief、raw／ready 與 summary。
7. 混音時口白優先，配樂降為背景；短配樂以 loop、交叉淡化與片尾 fade 延長。不要用固定和弦程序音掩蓋「配樂太死板」的問題。
8. 正式輸出前抽查片頭、中段、高潮、片尾；修正版使用新檔名，不覆蓋舊版。

## 強制 QA

- `ffprobe`：檢查解析度、9:16、幀率、片長、音訊軌、48kHz。
- `audio_qa.py`：整體約 `-18～-14 LUFS`、True Peak 不高於 `-1 dBFS`、最長非預期靜音不超過 3 秒。
- `ffmpeg -v error -i final.mp4 -f null NUL`：正式 MP4 必須完整解碼。
- 由正式 MP4 產生 opening／middle／ending 與 scene contact sheet；檢查字幕重疊、黑畫面、閃爍、抖動、突然跳切及取景 sliver。
- `QA.md` 記錄實際數值、音樂候選與選曲、voice ID、使用者試聽確認、版本差異及仍需注意事項。

## 不可違反

1. 不得跳過口白試聽關卡。
2. 不得把未量測的分鏡格線當成正確座標。
3. 不得只因音檔存在就宣稱配樂品質通過。
4. 雲端 TTS 只傳送朗讀文字，不傳原始私人文件；須先取得明確同意。
5. 場景、字幕與口白段數必須可追溯且一致。
6. 發布是對外行為；未明確確認標題、可見度、頻道前不得上架。

詳細取景、配樂、口白與驗收規則見 [references/portrait-crop-music-voice-qa.md](references/portrait-crop-music-voice-qa.md)。
