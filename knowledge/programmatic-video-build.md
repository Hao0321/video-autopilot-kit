> 來自 video-autopilot-kit 開源知識庫 · MIT 授權

# 程式化長片 build/fix pipeline（端到端固化）

> 一支教學長片經多輪修正提煉的**純 ffmpeg 端到端**長片做法（不靠 CapCut GUI）。
> 每步對應 canon M-rule + `capcut_helpers` helper。Path A（CapCut Pro 模板）做不到 / GUI 太慢時走這條。
> **黃金律：每一步做完抽幀/probe 驗證，最後跑 `final_delivery_qa()`，不要讓用戶當 QA。**
> ⚙️ **執行環境（M102）**：Windows 背景/排程跑這些 script 前，每個檔頂端先 `for s in (sys.stdout, sys.stderr): try: s.reconfigure(encoding="utf-8") except: pass` + 子行程帶 `PYTHONIOENCODING=utf-8`；否則 stdout 被 redirect 時預設是 cp950，`print()` 含 `≤`/`✓`/emoji 會 `UnicodeEncodeError` 炸 build（互動跑不會遇到，背景跑才爆）。

## 0. 素材入庫
- 新 b-roll 丟 `assets/broll/` → `batch_normalize_broll_folder()`（M85：strip audio M29 + conform 30fps M81，備份 `_intake_bak/`）。
- **螢幕錄影/截圖**入庫前過 M91 chrome 審查（工具列/側欄/瀏覽器/後台金額）+ 裁到只剩內容區。全螢幕桌面錄影**預設有毒**。
- **要秀「操作某 app」當 b-roll（M101）**：**首選把目標 app maximize 全螢幕再錄**（直接蓋掉旁邊瀏覽器/AI 面板/IDE）→ 只裁 OS 工作列 → 滿版乾淨，**別事後 crop**（會切到面板、留模糊邊；app 自己的 UI 不算個資）。非得用既有錄影才事後摳：裁切量**量不要猜**（裁頂部 strip 放大量 chrome 底邊，1080p 常 ~150px）、錄影/浮窗 UI 常**頭尾兩端都有** → 逐秒掃找**中段乾淨窗**再 bound 進去、整頁瀏覽器播的「短影音」要 crop 到**中央播放器框**（去書籤列 + 別人影片側欄）、**低解析接觸表會漏 chrome → 每個主素材窗看一張全解析單格**。

## 1. 人聲 → 字幕 timing
- whisper / faster-whisper 對 `master_voice` → `caption_blocks.json`（start/end/zh per 句）。
- 套 `apply_subtitle_corrections()`（M69 同音字）+ 人工 CORR（whisper 誤聽的專有名詞／同音詞，逐支補）。

## 2. 句間死空檔修剪（M95）— 三軌同步
```python
from capcut_helpers import detect_long_pauses, trim_dead_air_ranges, cut_audio_segments, cut_video_segments, remap_time
pauses = detect_long_pauses("master_voice.m4a", min_sec=1.5)   # 抓 >1.5s 句間停頓
cuts   = trim_dead_air_ranges(pauses, keep=0.5)                # 各留 0.5s 呼吸 → 要砍的區間
cut_audio_segments("master_voice.m4a", "voice_cut.wav", cuts)  # 人聲：atrim+concat（**不要 aselect**）
cut_video_segments("visual_nocap.mp4", "visual_cut.mp4", cuts) # 影像：select+setpts
# 字幕時間：每個 block.start/end = remap_time(t, cuts)
```
**鐵則**：人聲/影像/字幕用**同一組 `cuts`** 砍/平移 → 自動對齊。移音訊段 atrim+concat、移影像段 select+setpts，**別混用**。

## 3. b-roll 對位排序（M87/M94）
- `auto_sequence_brolls()`（M75 build-time topic clustering）排好順序。
- **M94**：旁白點名具體東西 → 給**真實該物**：講到上一支影片→該專案真實素材；「拉時間軸/操作剪輯軟體」→真實 CapCut 時間軸截圖；「丟原始素材」→真實素材資料夾；「講到某個遊戲/作品」→真實該作品畫面。
- **M93**：選素材避開**頻閃**（動作遊戲爆擊/strobe）→ 選平台/解謎/選單等平穩畫面。

## 4. 段落蒙太奇 build（concat filter）
每段 normalize 後 concat（segs 已 30fps/1920x1080 也照 normalize 保險）：
```
[i:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=30[vi];
... concat=n=N:v=1:a=0[o]
```
- 各 clip 用 `-ss IN -t DUR` 取段 + `trim=duration=DUR,setpts=PTS-STARTPTS`。
- 暗素材夾在亮素材間會像閃（M93 亮度落差）→ 換亮素材或 `setpts` 放慢留在亮的部分。

## 5. 圖片/截圖入片（M92）
```python
from capcut_helpers import still_blurfill
still_blurfill("capcut_timeline.png", "tl.mp4", dur=6)  # 非滿版→模糊背景填滿+靜止(零抖動)
```
- **禁**死黑邊（用同圖放大模糊當底）、**禁** zoompan（pixel 抖動）、**裁**到只剩內容區（M91/M92）。
- 截 app 視窗：computer-use 帶不動前景 → PowerShell `ShowWindow(6→3)` + `CopyFromScreen` 存檔（把這段固定成你自己的截圖 SOP）。

## 6. ASS 雙語字幕生成（M68 + 字幕陷阱 1-3）
- `[Events] Format` **必含 `Name` 欄**（否則每句前導逗號）。
- 中上英下用 **`\pos(960,968)`/`\pos(960,1040)`** 鎖死（不靠 MarginV，避免碰撞反序）。
- 中文 BorderStyle=3 半透明黑底盒、英文 BorderStyle=1 黑框。
- **停頓點**：句內自然語氣處插**全形空格 `　`**（不是逗號）；M10 assert「去空格後==逐字稿」防誤改字。
- **gap-fill**：句間 `<0.5s` 空檔 → 前句 end 補到後句 start（黑底盒不閃）。

## 7. 燒字幕 + 混音
```
# 燒字幕（cwd=放 ass 的資料夾，用相對路徑避開 Windows 冒號跳脫）
ffmpeg -i visual_cut.mp4 -vf ass=captions_cut.ass -c:v libx264 -crf 18 -pix_fmt yuv420p -r 30 vcap.mp4
# 混音【基本版】：cleaned_voice + BGM(*0.22 fade out 2s) — BGM 連續不跳（別剪混音檔）
[0:a]atrim=0:L,asetpts=N/SR/TB[v];[1:a]volume=0.22,afade=t=out:st=L-2:d=2[b];[v][b]amix=inputs=2:duration=first[a]
# mux（-shortest 切齊；影像比人聲短時丟尾靜音）
ffmpeg -i vcap.mp4 -i audio_cut.m4a -map 0:v:0 -map 1:a:0 -c:v copy -c:a copy -shortest FINAL.mp4
```
**🎚️ pro 音訊升級（M103）** — 基本版的固定 `volume=0.22` 死壓會「人聲一來 BGM 不讓位」、單純 mix 又沒壓平人聲忽大忽小。改成：
```
# ① 人聲先過真壓縮器壓平動態（不是 normalizer）：
[voice]highpass=f=80,acompressor=threshold=-18dB:ratio=3:attack=15:release=250[vc]
# ② BGM 用 sidechain：人聲當 key → 一講話 BGM 自動 duck、句間浮回（VDUR=實際影片長）：
[vc]asplit=2[v1][vsc];[1:a]atrim=0:VDUR,volume=0.32,afade=t=out:st=VDUR-3:d=3[bg];
[bg][vsc]sidechaincompress=threshold=0.03:ratio=8:attack=5:release=300[bgd];
[v1][bgd]amix=inputs=2:duration=first:normalize=0,afade=t=out:st=VDUR-0.15:d=0.15[mx]
# ③ two-pass loudnorm：pass1 print_format=json 量測 → pass2 measured_*+linear=true 精準投遞 -14 LUFS
# ④ 尾長對齊：BGM/mix 淡出對齊【實際影片長 VDUR】而非音訊長 → -shortest 不會砍 BGM 在 -23dB 硬切(outro click)
```
- player-safe ship：`reencode_player_safe()`（M83 libx264/-bf0/CFR/closed-GOP）。

## 8. 🚦 交付前 QA（必跑）
```python
from capcut_helpers import final_delivery_qa
final_delivery_qa("FINAL.mp4", voice="voice_cut.wav", contact_out="qa.png", audio=True, ass="captions_cut.ass")
# M93 頻閃(blackdetect) + M95 死空檔(silencedetect) 機械驗；接觸表逐格看 M91 chrome / M92 排版 / M94 對位 / M68 字幕
# audio=True (M103) 加 4 個音訊 gate：LUFS -14±1 / 尾 0.25s RMS<-40dB(已淡靜音) / audio vs video stream |Δ|<0.4s / 末字幕 end ≤ 片長
```
全 `[OK]` + 接觸表逐格乾淨 → 才交付。對應 canon「🚦 影片交付前 QA 自檢清單」8 條。
