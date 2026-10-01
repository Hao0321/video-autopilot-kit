> 來自 video-autopilot-kit 開源知識庫 · MIT 授權

# Editkin-first 長片 build／fix pipeline

> Editkin v4 是唯一現行 editor execution contract。Python／ffmpeg 工具只負責素材
> 正規化、可重現的媒體處理、證據產生與成品 QA；它們不是第二條剪輯器 fallback。
> 黃金律：每一步都產 receipt／hash／probe 證據，最後跑 `final_delivery_qa()`，
> 不讓觀眾代替製作端抓錯。

## 0. 固定執行邊界

所有 editable timeline 修改都走：

1. `get_autopilot_contract`
2. `start_ai_editing_session`
3. 每份素材的 prepare → keyframes → bounded context → semantics
4. route + plugin discovery
5. `hao.video-autopilot.edit-plan/v4`
6. audit receipt
7. atomic apply
8. render candidate
9. 技術 QA + 真人審片
10. outcome event

狀態由 `src/workflow_contract.py` 驗證。舊 editor GUI、draft JSON、Path A-E 只屬
benchmark-only 歷史，不是安裝需求、現行 route 或失敗時的 fallback。

## 1. 素材入庫與正規化

- raw 放在專案既有 `videos/` 架構內；不得在磁碟根目錄另建工作資料夾。
- b-roll 進 Editkin 前先 ffprobe codec／resolution／rotation／fps／audio；不符 timeline fps
  才 normalize，避免 metadata 假 30fps 造成速度 bug。
- screen recording 先裁掉 OS chrome、分頁、側欄、浮窗與私人後台；全螢幕錄影預設有毒。
- 每個 `--material CLIP_ID=SOURCE_FILE` 綁真實 source bytes。相同路徑換檔會使下游
  receipts 失效，不能只信 mtime 或檔名。
- Windows 背景執行明確把 stdout／stderr／subprocess 設成 UTF-8，避免 cp950 redirect
  遇到非 ASCII log 才崩潰。

## 2. 人聲、字幕與三軌同步修剪

- whisper／faster-whisper 對 clean narration 產 word／sentence timing。
- 專有名詞校正後，同步更新所有依賴文字長度的 range／word metadata。
- 長停頓只從 clean narration 判斷；決定 cut 後，人聲、畫面與字幕必須用同一組
  ranges 重映射。

```python
from media_delivery_qa import (
    detect_long_pauses,
    trim_dead_air_ranges,
    cut_audio_segments,
    cut_video_segments,
    remap_time,
)

pauses = detect_long_pauses("master_voice.m4a", min_sec=1.5)
cuts = trim_dead_air_ranges(pauses, keep=0.5)
cut_audio_segments("master_voice.m4a", "voice_cut.wav", cuts)
cut_video_segments("visual_nocap.mp4", "visual_cut.mp4", cuts)
# 每個字幕 block.start/end = remap_time(t, cuts)
```

音訊移段用 `atrim+concat`，影像用 `select+setpts`；不要讓不同軌各算一套 cuts。

## 3. 先看證據，再決定 b-roll

每份來源素材都依 contract 完成 keyframe view、bounded context 與 semantics。語意 receipt
至少引用一個本次真正看過的 frame 或 transcript cue。畫面選擇遵守：

- 旁白點名具體 artifact → 用同一個真實 artifact，不用 generic stock。
- 內容抽象時才可用 stock，但主素材時長必須高於通用 b-roll，且同一 clip 不重複。
- 避開 strobe／爆擊等頻閃段；亮暗相鄰也要看轉場是否造成 flash 感。
- 不能以檔名取代看畫面；檔名只可協助索引，不是語意證據。

## 4. 產生、稽核與套用 edit-plan/v4

plan 必須綁定全部 source／material／semantic receipts、route、plugin manifest、Skill／
knowledge／contract hash 與目前 project revision。plugin 在 audit 前只能 discovery／compile，
不可先改專案。

`audit_autopilot_plan` 接受後，`apply_autopilot_plan` 一次原子提交。若中斷後無法判定
committed，run 進 reconcile；禁止自動重套。render 只接受 committed revision，並產生
candidate 與 artifact hash。

CLI 入口：

```bash
python scripts/hao_autopilot.py workflow create --project <project.editkin.json> \
  --material clip-01=<real-source.mp4>
python scripts/hao_autopilot.py workflow next <run>
python scripts/hao_autopilot.py workflow verify <run>
```

## 5. 圖片／截圖入片（M91／M92）

非滿版圖片使用 editor-neutral helper 先做靜止 blurred-fill clip；禁死黑邊、禁會 pixel
抖動的 zoompan，且先裁到只剩內容區。

```python
from delivery_media_ops import still_blurfill

still_blurfill("clean_timeline.png", "timeline_clip.mp4", dur=6)
```

## 6. 字幕與音訊交付規格

- ASS `[Events] Format` 必含 `Name`；雙語上下位置固定，避免互撞與跳位。
- 句內換氣用可驗證的 line-break 規則，不准改逐字稿語意。
- 人聲先 high-pass + compressor；BGM 由 narration sidechain duck，並 loop/crossfade
  覆蓋到實際畫面結尾。
- 最終以 two-pass loudnorm 對目標平台校準；尾端 fade 對齊 video duration，不讓
  `-shortest` 在非零音量硬切。

## 7. 交付前 QA（必跑）

```python
from media_delivery_qa import final_delivery_qa

report = final_delivery_qa(
    "current_candidate.mp4",
    voice="voice_cut.wav",
    ass="captions_cut.ass",
    sheets_dir="qa/fullframe",
    contact_out="qa/contact.png",
    profile="teaching_longform",
)
assert report["deliver_ok"]
```

機械項包含 M92 border、M93 flash、M95 dead air、M103 audio/A-V、M105 caption sync、
M108 line breaks、M79 BGM coverage。全幀 sheets 還必須真人逐張檢查 M91 chrome／隱私、
M94 artifact 對位與字幕美術。機器不得替真人寫 approved 或 certified。

QA 綠後才把 candidate 原子升格為 current；同一支片不要自動堆 `v2/v3/FINAL`。
