# 教學長片 — 純 ffmpeg「kinetic 字幕卡 + 逐句對齊 b-roll」Pipeline（2026-06-24/25 建立 + 連環糾正後固化）

> Hao 的主頻道**教學長片**生產線。第一支實作 = 長片01「不會寫程式的外行人做出開源 AI 剪輯工具」。
> ⚠️ **剪任何片前先讀 `../SKILL.md` 最上面「剪片前必讀」9 條 + 本檔。** reference 實作在 `reference_impl_longform01/`。
> 這條線是「**旁白純人聲 + 逐句對齊的 b-roll/字卡/數據動畫 + 白字字幕 + 教學 BGM**」，**不是真的長片剪輯**（誠實邊界仍成立：旁白靠 Hao 錄、判斷靠人）。

## ⚠️⚠️ 2026-07-13 第二代管線（長片03）— 新片一律照這張差異表，本檔下方舊節僅供歷史對照

| 面向 | 第一代（長片01，本檔舊節/reference_impl） | **第二代（長片03 = 現行做法）** |
|---|---|---|
| 字幕切句 | `text_pipeline.py` whisper segment + MAXLEN 手切 | **`word_captions.py`**：字級時間→FIXES→停頓斷行→`build_ass(emphasize=False)`；**斷句照語意（M108）**。巨型數字／關鍵字另走 `emphasis_overlays.py`，不改逐句字幕（M119） |
| BGM | ~~crossfade 不 loop~~（❌ 這行教反，照做重現 339s 片後段靜音 bug） | **M118 選曲＋M79 全片覆蓋**：Asset Hub 先依題材／BPM／能量／近期重用選前 3 首，`bgm_paths_from_asset_plan()` 交給 `build_bgm(..., target_dur=vdur+4)` 做 playlist crossfade；仍不足才平滑 loop；`master_mix` 內建 `assert bdur>=vdur` |
| 數據/戰績畫面 | 自繪數據動畫為主 | **M107**：戰績/proof 數字＝**真後台截圖 dark-stage**（高亮圈+kicker；見長片03 `hero_real.py`）；概念示意（公式/漏斗）才自繪 |
| 場景結構 | scenes.json 每句一場景 | **PLAN dict 一 beat 一主畫面**（6 handler：clip/still/stillfull/brollcard/clipstill/twostill；`dur()`=下一 beat start−本 beat start 吸換氣 gap） |
| TRIM/LEAD_PAD | 三檔各一份 dict 手動同步 | **`offsets['_lead_pad']`+`offsets['_speed']` 單一真值**（voice_chain 寫入，下游一律讀 offsets） |
| 交付 QA | 手動呼叫 4 gate | **`final_delivery_qa(..., profile='teaching_longform')`**：強制 M103×4+M105+M108+M79 bgm-cov+M104 sheets，**缺輸入=BLOCKED**；build_final 尾端接線、不綠 SystemExit |
| 儲存／改版 | `v1/v2/FINAL` 完整副本＋交付再 copy | **M115**：只輸出 `out/current.mp4`；先 render `_work/current_candidate.mp4` 再原子換版；QA 綠後 `storage_lifecycle.finalize_success()`；交付用 `link_or_copy()`，禁止自動長出 vN 資料夾 |

> 第二代參考實作 = `videos/_planning/長片03_SocialPost/build/`（build_audio→build_captions→build_video→build_final）。完整方法論 → `../references/hao-teaching-longform-method.md`。
> **可重用模組（2026-07-23 固化，下支片 import 不 copy-paste）**：`video_handlers.py`（六 handler + `build_beats(PLAN, offsets, vseg_dir)` 內建換氣吸收 + AP12 invariant）＋ `proof_stage.py`（`stage_screenshot` 真截圖 dark-stage 擺台 + `assert_proof_sources` M107 proof gate）＋ `word_captions` / `audio_chain` 既有。**build/ 目錄禁止複製 skill 模組**（fx_lib 曾分叉，已收斂成 shim）。

---

## 0. 這支影片的「概念」（角度 = 為什麼這樣定位）

- **賣的是「成就/蛻變」不是「AI 工具 demo」** ── 照 [[project_channel_performance_baseline]]：他「90天14款」成就片 CTR 8.5% 爆 / 拉 81% 新觀眾 >> 「我把剪輯交給 AI」工具片 5.4% 普通。所以**標題/開場主打「不會寫程式的外行人做出開源工具」**，工具是可驗證的 proof，方法（多 agent 編排）才是課。
- **Recursion = 護城河**：影片本身用這條 pipeline 剪 →「這支的字幕/封面/剪輯全是工具自己生的」字面成真。
- **可信度靠真實 failure→fix**：最強 beat = 個資對抗式 5 輪驗證 11→0 抓出 20+ 個漏洞（= 公開 kit M100）。誠實講做不到：~70% 自動化 + 人 QA、長片剪輯還不會。
- **片長砍到 ~5 分**（他 audience 連 2.5min 只看 43-46%）。
- 7 個 beat：開場成就鉤子 → 為什麼想自動化 → 把 AI 當團隊 → 差點搞死的個資那關 → 第一次自己跑完 → 開源+做不到 → 收尾 CTA。
- 規劃文件：`videos/_planning/長片01_*.md`（preproduction / 純旁白腳本 / 畫面清單 / 發布套件）。

---

## 1. 架構（5 層，全純 ffmpeg / PIL，無 GUI）

```
① 旁白主聲軌  build_audio.py     7 段純人聲(對黑幕錄) → trim 死空檔 + concat + 0.35s 換氣 → master_voice.wav + offsets.json
② 逐句切點    text_pipeline.py   whisper 逐字 → 短句字幕(修 ASR 錯字) → phrases.json
              (scenes 切點)       transcript 的 segment 起點 = 場景切點 → scenes.json（每句一個場景）
③ 美術節奏    visual_director.py transcript/captions → domain＋macro 能量波＋景別組句＋J/L cut＋語意字卡／SFX JSON
④ 視覺軌      build_video.py     每個場景(=一句旁白)配對應視覺、cut 卡句尾(M87) → 拼成 master_bg.mp4
   ├ 真實 b-roll  assets/broll/transitions/（claude/team/laptop/ai/他的內容…）同 clip ≤2(M86)
   ├ 字卡        visuals.py render_card（深色開發者底 + 白字 MONO，M68）
   ├ 數據動畫    convergence_anim.py（5輪11→0）/ anim_extra.py（搜尋→0殘留、3-agent 分工）
   ├ demo 成品   phone_inset（工具吐的直式 Short）
   └ 剪輯素材    capcut-editing.mp4（我自己開 CapCut 操作 gdigrab 錄的，補「轉正/上字幕」缺口）
⑤ 字幕+混音   build_final.py     master.ass(白字+黑半透框 M68)＋可選 impact.ass(M119 獨立巨字／數字) 燒進 → 旁白 + 教學BGM(M79 loop-fill 蓋滿全片,crossfade 藏接縫—❗舊版此行誤寫「不loop」害長片03 後段靜音) → loudnorm -14
⑥ 自檢閘門    build_video.py     AP12 片長 invariant（影片==音軌，含 beat 間 gap）+ M86 重複(stock ≤2) + 交付前逐格 dense audit(M91/🚫23)
```

**run 順序（第二代）**：`write_visual_plan()`（同時產 `current_context_packet.json`＋`current_asset_plan.json`）→ `build_audio`（產 offsets.json 含 `_speed`/`_lead_pad`）→ `build_captions`（word_captions 讀 offsets）→ `build_video`（PLAN dict）→ `build_final`（`bgm_paths_from_asset_plan()`＋燒字幕＋master_mix）→ **先寫 candidate，再 `storage_lifecycle.atomic_publish(..., out/current.mp4)`** → 尾端接線 **`final_delivery_qa(..., profile='teaching_longform')` 不綠 SystemExit**（M103×4 / M105 cap-sync / **M108 斷句** / **M79 bgm-cov** / M104 sheets，缺輸入=BLOCKED）→ QA 綠才 `finalize_success()`。〔第一代順序（text_pipeline/scenes.json）僅 reference_impl 歷史對照〕

> 🎚️ **pro 音訊鏈已模組化（M103/M118）**：`voice_chain`(acompressor 壓平 + atempo 加速 + room-tone bed)、`bgm_paths_from_asset_plan`（讀中樞排名）、`build_bgm`（playlist crossfade／全片覆蓋）、`master_mix`(sidechain duck BGM + two-pass loudnorm + 尾長對齊)、`loudnorm_2pass`、`assert_sp_sync`(加速時間軸 regression guard) 全在 [`audio_chain.py`](audio_chain.py)。下支長片直接 import，**不要 copy-paste build script**。`python audio_chain.py` 跑真 ffmpeg self-test（M97）。

---

## 2. 每個 script（reference_impl_longform01/）

| script | 做什麼 | 關鍵點 / 踩過的雷 |
|---|---|---|
| `build_audio.py` | 7 段旁白 trim(speech 首尾+pad) + concat + 0.35s gap → master_voice + offsets | 死空檔靠 whisper first/last 抓 |
| `text_pipeline.py` | whisper word → 短句, 修 ASR 錯字(餵它/避坑/每剪), **首尾標點都 strip**(漏 strip 開頭逗號→字幕跑逗號) | MAXLEN 19 clause-level |
| `visuals.py` | `render_card()` 深色底+白字卡 / `bg()` 漸層+glow+dot；**MONO_TEXT=True 全白字**(M68) | bg() 用 numpy 向量化(別逐 pixel 慢) |
| `build_video.py` | **scene-driven**：scenes.json × `PLAN`(每句→token) → `scene_clip()` dispatch(卡/動畫/demo/repo/stock) → 拼 beat → master_bg。內建 M86 + AP12 自檢 | ⚠️ **zoompan 餵 looped image 會爆片長 → 單 frame + `-frames:v` 鎖**；影片要含 beat 間 gap 否則 A/V 漸不同步 |
| `build_final.py` | master.ass(白字黑框) 燒 + 旁白+BGM(N 軌 acrossfade) + loudnorm | **ASS `Format:` 欄位數必含 `Name`**，否則 Text 吃逗號 |
| `convergence_anim.py` | 5 輪收斂 11→2→3→2→0 逐 frame 動畫(白字+細 mint+畫 ✓) | 數據動畫的動=內容，非 🚫18 靜止 |
| `anim_extra.py` | 3-agent 分工 + 搜尋→0殘留 兩個動畫 | 同上 |
| `demo_builder.py` | 生「像工具吐的」直式 demo Short(暖 bokeh+多色字)，靜止 bg | demo 內字幕**可多色**(它是 Shorts 示範)；長片本身白字 |

---

## 3. 鎖死的鐵則（這次連環糾正出來的，全部已進 `../SKILL.md` 9 條 + canon 🚫17-23）

1. **🚫20 b-roll 先翻素材庫** `assets/broll/transitions/`，別憑空生合成圖。
2. **🚫21/M86 不重複**：通用 stock clip ≤2 次（editing/demo/repo 是主素材不計）；交付前跑 `audit_broll_main_ratio()`。AI 資料中心曾用 7 次被罵。
3. **🚫22/M87 逐句對齊**：每句旁白配對應畫面、cut 卡句尾，不是固定秒數亂切；換 b-roll 後跑 `audit_caption_broll_mismatch()`。
4. **🚫18 生成圖靜止**：我生的圖/字卡/終端機**不 pan/zoom/jitter**；只有「數據動畫」的動 OK；真實照片才 KenBurns。
5. **M68/🚫17/🚫19 教學長片逐句字幕 = 白字 + 黑半透底框，全程逐句、不 suppress、不多色**；
   **M119 允許上層選擇性 giant number／keyword overlay**，但不得把底層字幕變成彩色跳字。
6. **M29/M9/M10/M91 b-roll 去聲 / 看畫面 / 不編造 / 過隱私**。
7. **🚫23 用戶螢幕錄影逐格 dense audit(≤2s/格)掃整個畫面**：OBS/通知/浮動視窗常在**內容區中間**，裁邊救不了 → 看到就整段棄用。長片01 就是 repo 錄影裡浮 OBS 漏掉被罵。
8. **缺素材能自己生先自己生**：剪輯過程 = 自己開 CapCut + `ffmpeg gdigrab desktop`(GPU app 不能用 title)+ 裁工作列 → 存進 `assets/broll/`。
9. **真重點/數據展示 → 自己生有質感動畫**（非陽春卡）。
10. **交付前**：AP12 片長 invariant + M86 + M87 + dense audit 全 green 才給用戶；不要讓用戶當 QA。

---

## 4. 下次剪教學長片怎麼複用

1. Hao 對黑幕錄好分段旁白（每 beat 一段）+ 丟素材 → `_INBOX/橫式-landscape-YT長片/N/`。
2. 改 `build_audio.py` 的 `BEATS`（段檔名 + whisper speech 首尾）。
3. 跑 `text_pipeline.py` → 看 phrases/scenes，**人工核對每句**。
4. 在 `build_video.py` 寫 `PLAN`（每個 scene → 對應視覺 token），照 §3 鐵則挑（先翻素材庫、≤2、逐句對、缺的自錄/生動畫）。
5. 生需要的數據動畫（仿 convergence/anim_extra）。
6. `build_video`(自動跑 M86+AP12) → `build_final`(白字字幕+BGM) → **逐格 dense audit** → 交付。

---

## 5. 反覆運行的硬前置 + 兩個「沒附 script」的產生器（2026-06-25 審查補洞）

> ⚠️ 審查發現 reference 缺 transcript.json / scenes.json 的產生器 + 一堆魔數沒講怎麼來。這節補齊，否則照 §4 會 FileNotFound / 整段偏移。

### 5.1 環境前置（缺任一即炸）
- **PATH**：`ffmpeg` / `ffprobe`；**Python 套件**：`faster_whisper`、`PIL`、`numpy`、`fonttools`。
- **字體**（visuals.py FONTS 指這些，缺字 render_card 直接炸）：`assets/fonts/_active/` 下 `NotoSerifTC-Black.ttf` / `Huninn-Regular.ttf` / `LXGWWenKaiTC-Bold.ttf` / `Anton-Regular.ttf` / `Fredoka-SemiBold.ttf` + 系統 `C:/Windows/Fonts/msjhbd.ttc`（微軟正黑，跑字幕用）。

### 5.2 ① 產 transcript.json（whisper word-level）── reference 沒附，這是必跑的第 0 步
旁白分段 wav（narration/beatN.wav）→ faster-whisper medium、`language="zh"`、`word_timestamps=True`，輸出 schema：
```
transcript.json = { "beat1_open": {"segments":[ {"start","end","text","words":[{"w","s","e"}...]} ...]}, ... }
```
（`build_audio.py` 的 BEATS 的 `speech_first/last` = 對每段 wav 跑 whisper 後，取**第一個 word.s** 與**最後一個 word.e**；不是用猜的。）

### 5.3 ② 產 scenes.json（場景切點 = 每句旁白起點）── reference 沒附
`text_pipeline.py` 只產 phrases.json（字幕）。**scenes.json 另外產**：對每個 beat，scene 切點 = 該 beat 每個 whisper segment 的 master 起點（master = `offsets[beat].start + (seg.start - TRIM[beat])`，第一個 scene 對齊 beat 起點）；每個 scene `{i, m(master起), d(到下一句起/beat尾)}`。產法見本次 build log 的 inline script（`work/scenes.json`）。**scene.d 加總 = beat dur**（這保證影片==音軌）。

### 5.4 TRIM 三處要同步（魔數陷阱）
`build_audio.py`(LEAD_PAD=0.25) 決定每段 trim 起點 = `speech_first - 0.25`；**`build_video.py` 和 `build_final.py` 各有一份 `TRIM` dict（beat→這個 trim 起點）必須跟 build_audio 算的一致**，否則字幕/場景整段偏移。改旁白首尾秒數 = 三個地方一起改。

### 5.5 逐片要重寫的（build_video 全 hard-code 長片01）
- `NAME2OFF` / `order`：7 個 beat 名 → offsets key。
- `BR`：b-roll 檔名映射（先翻 `assets/broll/`）。
- `CARDS`：每張字卡文案（**整批重寫成新片的**）。
- `PLAN`：`{scene_i: token | [(秒,token),...]}`，**scene_i 必須 1:1 對齊 scenes.json 的 i**。
  **合法 token**：`'A:卡名'`(CARDS 的卡)｜`'X:動畫名'`(ANIM 的 conv/search/agent3…)｜`'demo'`(phone_inset 成品)｜`'community'`(社群主視覺,播結尾含 logo)｜**`'ghreadme'/'ghfiles'/'short'`**(用 `crop_browser(src,t0,seg_len=乾淨核長,top=150,bot=56)` 裁 chrome + bound 在乾淨中段的真實螢幕錄影；**top 要量不要猜**：分頁+網址+書籤列≈125px、Star≈195px，故 top=150;乾淨窗口比 dur 短就讓 seg_len loop 填,別吃尾端 OBS → 長片01 = 真 GitHub README / 檔案頁含 ★Star / 真 YT Short 成品)｜BR 的 key(claude1/team/laptop/ai/editing/game/coffee…)。<br>  ⚠️ **舊 `'repo1'/'repo2'`(crop_repo, 固定 t0/t1 不 bound 乾淨窗口) 已被 `ghreadme/ghfiles`(crop_browser+seg_len) 取代** ── 不是「因含 OBS 就整支丟」，而是 **🚫23「取乾淨中段」**：OBS 在錄影【頭尾兩端】→ `seg_len` 把擷取鎖在中段乾淨窗口，主素材(真 GitHub/Star/Short)照用。新片同理：先逐秒 dense 掃出乾淨窗口，再用 `crop_browser` bound 進去。
- `build_final.py`：`bgm_in`(選曲清單)、beat4 number-pop 的座標(`o4+(ws-t4)`)都是長片01 專屬，按新片改。
- `convergence_anim.py` / `anim_extra.py`：數據動畫內容(11→0、3-agent…)按新片重做。

### 5.6 b-roll 重複上限（統一閾值，別再 ≤1/≤2 並存）
**通用 stock 同一支 ≤2 次**（理想 ≤1，但 ~5min 片素材不夠時 ≤2 可接受）；**主素材（demo / 自錄 editing / 自己生的動畫 / 社群主視覺）不限**；**≥3 次 = 過度重複（被罵線，AI 資料中心曾 7 次）**。`build_video.py` 內建 assert：generic >2 即 fail（`MAIN_CLIPS` 排除主素材）。
