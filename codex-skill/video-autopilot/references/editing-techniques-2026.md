> → 找不到要讀哪本？[craft-index.md](craft-index.md)（六本 craft refs 導航：症狀→節路由表 + 跨檔重複主寫對照）

# 剪輯技巧 2026（上網查證 + 對抗驗證後固化）

> **現行執行契約（2026-08-27）**：本文的剪切、字幕、變速、混音與 keyframe 做法一律轉成 `hao.video-autopilot.edit-plan/v4` typed structured commands；先綁素材 evidence 與時間窗，再走 `workflow_contract.py` audit → accepted receipt → atomic apply → committed receipt → render → delivery QA → human/outcome receipt。舊 GUI 手勢或單獨 ffmpeg 命令都不是可交付狀態。

> 多來源（OpusClip/Shortimize/創作者實證 + YouTube 官方留存指標）研究 + adversarial verify 後留下的**可量化、可操作**技巧。
> 多數 data-backed；**已剔除驗證打架的 retired-GUI 定價／語言數／快捷鍵條目**。現行可執行能力以 `editorial-intelligence-contract.md`、`../workflow_contract.json` 與 Editkin capability manifest 為準。承既有 M-lessons，標「↔Mxx」。

## A. 短影音 Shorts/Reels（承 M88/M96）

- **前 3 秒 hook：2–2.5s 就交付**（留 0.5s 緩衝），最精彩畫面放**第 1 秒**（當縮圖）。不要「嗨大家歡迎回來」。在 v4 plan 寫入 frame-accurate trim／reorder command，移除片頭吸氣與空白，並斷言第一個語音字落在 0.0s；render receipt 後再以波形與首幀 QA 驗證。WHY：3 秒留存 >65% → 曝光 4-7×；50-60% 流失在前 3 秒。
- **4 種 hook 公式**：教學/工具 → **Direct Promise + 數字**（「3 個設定修好模糊 Shorts」）；娛樂 → Pattern Interrupt + 中段開場；生活/Vlog → **Question 自我辨識**（「你也覺得手機剪 Shorts 卡卡的嗎？」）。每片寫 3 個變體分時段測前 3 秒留存留贏的。
- **片長甜蜜點 15–30s**（技巧型剪到 15–20s 可達 85-95% 留存）；>45s dramatic drop。↔ Hao audience「連 3min 只看 43%」→ 短影音「寧短不長」。
- **Pacing：每 1.5–2s 一次視覺變化**（5-7 變化/10s）。沒新鏡頭就換字幕/zoom 撐 beat；jump cut 每 2-4 字切、刪吸氣停頓。WHY：爆款(1M+)均留存 ~76%，>75% 有 3× 機率推新觀眾。
- **Punch-in zoom 強調**：在 v4 plan 對目標 clip 寫 transform keyframe command：起點 scale=1.00，重點字時間 scale=1.10–1.15，進段 ease-out／落點 ease-in；猛 reveal 可用 10 frame 由 1.50 回 1.00。Audit 必須驗 bounds／safe-zone，render receipt 後抽首中末幀確認無機械抖。WHY：突 zoom +68% engagement（pattern interrupt 之首）。
- **Loop 結尾（>100% 留存=爆款層）**：①句子切半（尾巴停未完成句）②視覺連續（尾 clip 構圖/運動方向=開頭第一幀）③彩蛋 bait。WHY：autoplay 重播 = 額外完讀，rewatch+completion 是 2026 FYP 最強槓桿。
- **別把高潮埋 15–20s**（payoff 前掉 70%）→ 結果先閃 0.3s preview 再回頭講過程。
- **Micro-cut 工具箱**：B-roll flash 3 frame／text-pop 6-8 frame（~0.2s@30fps）／axis shift（下個 clip Scale +15% 移三分線）；每 5-8s 插一個。
- **Pattern interrupt 排序（ROI）**：zoom punch-in（最高）> 彈出動態字 > jump cut 刪停頓。靜態生成圖不 pan(↔🚫18)，重點數據自生有質感動畫。
- **演算法 2025-26**：APV/完讀率 > view 數；發 Shorts 看 YT Studio 留存曲線不只看 view。留存 >75% 解鎖新觀眾推送（↔ Hao 瓶頸=留存+曝光非 CTR）。

## B. 長片 YouTube（承 project_channel_performance_baseline / yt-algorithm-mastery）

- **讀留存曲線 4 標記診斷**（YT Studio > 互動程度 > 觀眾續看率，需 ≥60s 片+≥100 觀看）：① **0-30s drop ≥40%** = hook 壞或封面/標題不符 → 改開場或封面標題 ② **懸崖 cliff**（單點陡降）= 那秒有題外話/慢畫面/贊助插入 → 剪掉 ③ **spike/破 100%** = 拆解為何被重播 → 複製到他段 ④ **top moment 在後段** → 精彩往前搬。WHY：留存每 +10pp，曝光相對 +25%+。
- **留存基準（go/no-go 用）**：前 30s >75% 強／60-75% 普／**<60% = hook 不及格**；1min 節點守 **65%+**（過得了的片後段 AVD 高 58%）；2025 全片平均僅 23.7%，5-10min 片留存最好 ~31.5%。Hao 教學長片對齊 45-55% AVP。
- **開場 4 段式**：0:00-0:05 抓注意（震撼/懸念/直接秀成果）→ 0:05-0:15 講承諾（「看完你會…」）→ 0:15-0:30 建 stakes；25-35s 處塞一個 pattern interrupt。🚫 **動畫片頭 >3s**（掉 8-15%）🚫 **「嗨大家歡迎回來」**（比直接給承諾低 47% AVD）。
- **Pattern interrupt 分段節奏（非固定每 X 秒）**：開場(0-3min)每 10-15s 一變化／中段(3-7min)放寬每 25-40s 一刀／8min 後平靜+爆發交替。13-24 歲每 15-25s 換、25+ 可單鏡 20-40s。pattern interrupt 廣義=換鏡/圖卡/音效/語速變化/螢幕問句。
- **⭐MrBeast 2024 自我反轉**：放慢、讓場景呼吸、少吼、加人格、講故事、片更長 → views skyrocketed。**別把「高留存=每 5-8s 換鏡」當鐵律**套教學長片；演算法 2024 起把 satisfaction（事後 4-5 星）權重拉最高，過度刺激片留存高但滿意度低被降推。仍保留 **open loop 冷開場**（起在未解張力、不把句子講完就跳）。
- **B-roll 斷點規則（可機械 audit，↔M87/broll_audit）**：每 20-30s talking head 插一視覺斷點（螢幕錄影/stock/特寫/文字動畫）；**掃 timeline 任何 >90s 畫面沒變 → 硬塞一個 b-roll 呼吸點**；轉場剪 1-2s；從 b-roll 切回先回正面鏡頭；b-roll 當休息時加字幕/旁白維持資訊密度。
- **Chapters**（evergreen 教學靠 search 複利特別划算）：描述第一行放 00:00 起時間戳列表（第一個必 00:00），≥3 章、每章 ≥10s。
- **張力三角（封面/標題/開場）**：剪完開場檢查「前 15-30s 是否**直接視覺兌現**封面+標題承諾」；落差大 → 完成率最多掉 42%、觸及掉 30%。前 30s cliff 先別改後段，回頭對齊三角（↔ Hao「題騙肉鬆」變可執行檢查步驟）。

## C. 字幕 + 音訊（承 M68/M95/M99）

- **字幕 +12-40% 觀看時長**（靜音觀看是命脈，60% 行動觀眾無聲看）。
- **可讀性鐵則**：白字 + **2-4px 黑描邊** + **粗體 700+**（手機可讀性 +31%）；兩行內；對比 ≥4.5:1（<4.5 小螢幕讀不到直接滑走）。對比優先於美觀。
- **直式安全區**：1080×1920 → TikTok 安全 900×1492（上 108/底 320/左 60/右 120）；**字幕 Y 放 1200-1550**（避底部 320-350 死區）；Reels 底死區 310-450、右 84；跨平台同片發 → 設計給 **900×1400 置中**；簡記**避最下 20%**（↔ M96 安全區）。
- **Kinetic typography（逐字/active word）**：每個字做**獨立 text element** 才能各自控進出時機（整段動畫軌會一起動）；先把腳本標出最重要的字再對應高亮。WHY：影片訊息可記住 95%。
- **BGM 踩點**：先把 beat-analysis receipt 的峰值時間寫入 v4 plan，再讓 scene cut／轉場 command 對齊選定 beat；偵測值若需修正，修的是 plan 內 timestamp 並重跑 audit，不做無記錄的拖曳。
- **Audio ducking（↔M99）**：BGM 起播音量 — 旁白/talking-head 10-20%／教學旁白 15-25%／訪談 8-15%／純情緒 reel 50-80%。v4 plan 以 gain-envelope／sidechain command 在語音窗內壓低、結束後回復；render receipt 後以 LUFS、true peak 與 speech/gap 能量差 QA，不採信匯入預設值。
- **Fade**：每條 BGM 頭尾 0.5-2s 淡入淡出（最低成本提質感）。
- **人聲處理**：降噪**從低強度往上調**（太強變 robotic/水下）；Enhance voice；Normalize loudness。
- **響度 -14 LUFS / true peak ≤ -1 dBTP**（↔ Hao 既有）：低於 -14 會被平台對比顯小聲；人聲壓縮 2:1~4:1**別過壓**（量到 -14 但無動態會死板，該大聲的段要真大聲）。
- **SFX timing**：whoosh 配轉場長（半秒剪 → ~400-500ms），時間軸**以 1-frame 為單位**微調對視覺動作峰值；音效與動作**同幀**（早/晚都破壞流暢）。

---
**怎麼用**：剪短影音先過 A、剪教學長片先過 B、字幕/混音查 C。多數已能落到 Hao 既有模組（`silent_vlog_maker` Shorts／`longform_maker`／`media_delivery_qa.py`）；所有 intent 的 v4 command／receipt 對照見 `editorial-intelligence-contract.md` 與 `../workflow_contract.json`。

---

## 🚀 2026-07-09 六路深研升級計畫（波1接線/波2節奏/波3簽名）

> **fx_lib.py 引擎在 長片03 build/（將移植 longform_maker）；本節=參數真值來源**。六路深研合成，18 項按 rank 分三波：核心發現=fx_lib.py 引擎已齊（easing/stagger/grain/vignette/亞像素KB/SFX wav）但 animate.py 完全沒接線——anim2-7 仍是靜圖躺 5.5s、hero 無字槽無落地感、SFX 沒混音、concat 全硬切。裁決貫穿：**留存>炫技**（能量效果全設頻率 cap）、**教學清晰>特效**（正文字幕不動畫）、**三鐵則零違反**（KB 全 float、white-first 走 audit gate、counter 末幀 assert 真值）。演算法側對應新規 → `yt-algorithm-mastery/mastery.md` R15-R25。

### 波1・接線週（rank 1-9，幾乎全 low effort）——做完「乾淨→有質感」即成立

1. **靜卡全滅：anim2-7 接上 fx_lib 亞像素 Ken Burns + 質感 pass** [low]（改 `animate.py` build_still_mp4s/build_hero_mp4 + 各 anim*.py + `fx_lib.py`）— 廢 `-loop 1` 靜圖路徑改逐幀：每支 180 幀（6s@30fps），先 render 2x 底圖（3840x2160，W/H 參數化），每幀 `ken_burns_frame(src2x, t=i/179, z0=1.0, z1=1.05, pan=(0.01,0), ease=smootherstep)` + `texture_pass(im, grain=5, vig=0.14, seed=i)`；fx_lib 補 `smootherstep(t)=6t**5-15t**4+10t**3`；奇偶支交替 push-in/pull-out（1.00→1.05 / 1.05→1.00）避免七支同方向；fade-in 0.35s 保留；hold 段 tpad clone 移除（hero 4.5s hold 改 KB 慢推繼續跑）。→ 6 支數據卡從「5.5s 完全靜止」→全程亞像素呼吸，解掉『靜止>5s=留存懸崖』且零抖動（守 zoompan 鐵則）；每幀變 seed 的 grain 同時 dither 掉深紫漸層 banding。**全計畫 ROI 最高（lib 已寫好，改 ~40 行）**。
2. **Hero counter 三件套：expo easing + 固定字槽 + 落地 pop/glow（真值幀強制）** [low]（`data_anim.py` render_hero 數字排版 + `animate.py` render_hero_frames + `fx_lib.py`）— (a) fx_lib 加 `ease_out_expo(t)=1 if t>=1 else 1-2**(-10*t)`，count-up 從 ease-out-cubic 換 expo、INTRO 1.5→1.8s；(b) 主數字固定字槽 `w_slot=max(draw.textlength(d, F_NUM_210) for d in '0123456789')`，每位數固定槽內置中、逗號槽 0.5x——滾動整行不抖寬；(c) 最後一幀強制 `count_v=2706888` 真值（M10 合規 gate 寫進 assert）；(d) 落地後 +2 幀 scale pop 1.00→1.06→1.00 + 6 幀金色 glow 脈衝（opacity 0→1→0.4）。→ 數字滾動不跳寬（跳寬=業餘最明顯破綻）、落點 feel earned；hero 冷開場成全片最強 3 秒，直接餵 hook 0-5s。
3. **雙層 additive bloom 取代單層 glow（曲線+金數字+端點 dot 統一）** [low]（`data_anim.py` glow_layer/draw_curve）— 層1 `GaussianBlur(radius=4)` 亮度 60% + 層2 `GaussianBlur(radius=16)` 亮度 30%，`ImageChops.screen` 疊回、最上貼銳利原元素；draw_curve 現有單層 blur(14) 換掉；金色大數字、曲線端點 dot、章節卡數字全走同一函式；counter 落地脈衝=此 glow 的 opacity 0→1→0.4 走 6 幀。→ 單層 glow=貼紙感、雙半徑 bloom=光學鏡頭質感；深紫底+金字吃到飽，「乾淨→貴」核心視覺配方。
4. **Stagger 進場系統：chips/bullets 逐一進、雙屬性複合** [low]（`data_anim.py` chip/pill 加 progress 參數 + 各 anim*.py 渲染迴圈）— 所有卡內兄弟元素進場走 `stagger(per_ms=80, dur_ms=400)` + ease_out_quint，禁一次全貼；每元素最少雙屬性：opacity 0→1（前 50% 完成）+ translateY +24px→0（全程）、重點元素加 scale 0.95→1.0；兩張底部 chip 差 2.4 幀、bullet 每行差 3 幀、>10 元素壓進 0.8s 總窗；同組元素共用同一條 easing 曲線。→「PowerPoint 同時全出」→逐一導引視線，每卡前 1 秒幀幀有微事件；單屬性 fade-in 模板感消失。
5. **SFX 接線：adelay 毫秒對齊 cut/落地/進場（庫已有 wav，補 sub-hit）** [medium]（`fx_lib.py` +sfx_hit + build script 成片組裝/音訊混音段，接 M103 鏈）— `sfx_hit(path, dur=1.0)`：`sig=0.9*sin(2*pi*80*exp(-2.5*t)*t)*exp(-4*t)`（低頻落點）；組裝時自動生成 SFX event list：轉場 cut 幀→whoosh、金數字落地幀→hit+pop、chip/bullet 進場首幀→tick（只給首幀不逐字）；每事件 `adelay=ms|ms`（cut 幀時間x1000 − transient offset）精準 ±50ms，全部 amix 後走 M103 既有 loudnorm 鏈；電平：SFX peak 比旁白低 6-10dB；密度 cap 每分鐘 ≤5 個、同類 SFX 輪替 2-3 變體；cut 點是腳本自生 → 對齊 100% 機械化。→ 無聲轉場=默劇簡報感（業餘最大破綻）；SFX 對齊視覺 hit=研究收斂的『乾淨→premium 最大單一槓桿』，與轉場/punch-in 相乘。
6. **成片 finishing pass：split-tone + curves + grain/vignette 單層原則（不加 flicker）** [low]（build script 成片組裝最後一道 filter chain）— 最終輸出前固定 -vf：`curves=master='0/0.02 0.5/0.5 1/0.98',colorbalance=rs=0.02:bs=0.06:rh=0.04:bh=-0.04`（陰影推藍紫/亮部推暖金=品牌色變調色語言），libx264 維持 crf 18（grain 吃碼率不可調高 crf）；鐵則：grain/vignette 只做一層——Python 幀級 texture_pass 已做的 clip 成片級不再疊 noise/vignette；純 ffmpeg 段（螢幕錄影等）才補 `vignette=a=PI/5` + `noise=c0s=7:c0f=t+u`；明確不加 eq 亮度 flicker（守 M93 頻閃教訓）。→ 全片「同一隻手調過色」的一致性——premium 感一半來自這裡；深紫+金恰好就是 split-tone 冷陰影/暖亮部結構，等於免費。
7. **ASS 字幕微動態：每句 ≤1 關鍵詞變重【⚠️2026-07-13 修正：僅限 Shorts；教學長片一律 emphasize=False 全白統一，Hao 圈出金字放大重疊，長片禁變色變大小(M68)】關鍵詞變重 + 章節卡 blur-in（守 white-first/M68）** [low]（`longform_maker/word_captions.py` 生成端 + `silent_vlog_maker/shorts_captions.py::audit_color_ratio` gate）— (a) 詞表比對（工具名/真值數字/結論動詞），命中的每句最多 1 個詞包 `{\fscx112\fscy112\c&H3FD2FF&}`（品牌金 RGB 255,210,63 → ASS BGR &H3FD2FF&），其餘全白、白字黑框主體不動，全片過 audit_color_ratio gate；(b) 章節標題卡加 `{\blur16\alpha&HFF&\t(0,280,\blur0\alpha&H00&)}` blur-in 280ms；(c) 正文逐句字幕不加任何動畫（教學清晰>特效）；字級時間已由 M105 機械化，零手 key。→ 中文觀眾主閱讀面就是字幕（同音字文化）——字幕內 emphasis 的注意力轉移成本=0，比另開圖卡便宜且不搶畫面；libass 硬渲染零額外算力。
8. **Hook 逐秒模板重排：0-5s 真值 cold open → 5-15s 承諾 → 15-30s 第一步** [low]（video-autopilot SKILL.md 分鏡模板 + yt-script-style Generate 規則加一條）— 0:00 直接放成片 payoff 的 3-5s 真實 demo（hero climax 卡或跑通畫面）+ 一句結果宣言；5-15s「這支你會拿到什麼」承諾字卡；15-30s 直進第一步；禁自我介紹/『大家好』/頻道 intro；open loop 字卡：『怎麼做的？X 分鐘後你自己也能』；縮圖裡的畫面必須在前 30s 內出現（包裝承諾兌現）；QA 指標寫進 Log Outcome：30s 留存 ≥70% green、<60% 下支重排 hook。→ 30s 留存 75% 是進 Suggested 的門檻（R24）；Hao 瓶頸=留存+曝光，改一次模板支支受益。
9. **留存機械 gate 三連：scene-pacing 三段制 + freeze∩silence + interrupt 排程表** [low]（`media_delivery_qa.py` + v4 plan 分鏡 interrupt assertion + Log Outcome receipt）— (a) `ffprobe -f lavfi "movie=final.mp4,select=gt(scene\,0.2)" -show_entries frame=pts_time` 抓全部視覺變化點，相鄰間距上限：0-30s ≤7s、30s-3min ≤15s、3min+ ≤30s，超窗=red 列秒數要求補視覺；(b) `freezedetect=n=-60dB:d=3` 與 `silencedetect=noise=-35dB:d=2` 區間求交集，交集>0=red（M95 機械化）；(c) plan 加 interrupt assertion：t≈30s 首發 + 之後每 75±15s 一發（interrupt=畫面+聲音兩維度同變），QA 驗證每 90s 窗內 ≥1 個大變化；發布後 72h 把 YT Studio 留存 dip 對回 outcome receipt（閉環校準）。→ 留存懸崖幾乎都對得上『畫面沒動+聲音沒事件』；不用等 YT 數據就在交付前攔截。

### 波2・節奏結構（rank 10-15）——直攻 AVP 中段流失

10. **圖表 reveal 文法 + 累積式 build-up（reveal 綁 whisper 字級時間戳）** [medium]（`data_anim.py` draw_curve 已支援 progress、補柱狀/標註版 + 各 anim*.py state 化 + build script timestamp 綁定）— 每張數據卡改三拍：格線+軸 fade+8px 位移進場 0.3s → 停 0.2s → 數據 draw-on（曲線按弧長參數化畫 1.2-2s、線頭發光 dot 領跑；柱從 baseline 長 0.4s ease_out_quint + stagger）；reveal 完成幀直接綁 word_captions 字級 timestamp——旁白講到該數字那個 word 的 onset 幀才落地；同一論點的元素『加在同一張卡上』不切新卡：state0 骨架→+數字→+曲線→+結論標註，每個新元素 8-10 幀 alpha+slide 進場。→ 數據段從「切靜卡」→「論證在長大」（志祺式累積 build-up）；data reveal 與 narration 逐字對齊=Hao 獨有機械化槓桿——別的頻道要手 key，我們 M105 免費。
11. **Punch-in 硬切 112%（零抖動 emphasis）** [low]（build script cut 表生成段 + 各 anim*.py 雙 scale 渲染選項）— 重點句關鍵詞 onset 幀（whisper 字級定位）畫面直接跳 1.12x：Python 端同場景 render 兩個 scale（2x 素材零畫質損失），或 ffmpeg 段落級 `crop=iw/1.12:ih/1.12,scale=1920:1080:flags=lanczos`；一次到位零動畫=零抖動（完全繞開 zoompan）；回 100% 落在下一句句首；頻率：VO 講解段每 20-30s ≤1 次、只放重點字不隨機撒；可同幀讓字幕關鍵詞變金（rank 7 聯動）+ pop SFX（rank 5 聯動）。→ 等效一次『新畫面』但不用新素材，講解段每 20-30s 免費注意力重置；MrBeast 系標準款且合鐵則。
12. **轉場語意系統：wipe=換章、whip=高能、zoomin=推進、預設仍硬切** [medium]（build script concat/組裝段，取代現在 concat demuxer 全硬切）— 換章節=xfade transition=custom 軟邊斜角 wipe（`expr='st(0,(X/W+Y/H)/2);st(1,clip((ld(0)-(1-P*1.15))/0.15,0,1));A*(1-ld(1))+B*ld(1)'`，duration=0.5，offset=前段長-0.5）；高能轉場=slideleft + sendcmd 動畫 gblur whip-pan（sigma 0→26→0、sigmaV=0 只水平模糊，d=0.4）；重點推進=xfade=zoomin（需 ffmpeg 5.1+）；先跑 `ffmpeg -version` gate，5.0 以下 fallback 全硬切；頻率 cap：wipe ≤3/支、zoomin ≤2/支、其餘一律硬切；兩輸入 fps/解析度/timebase 必須一致；每個轉場綁 whoosh（rank 5）。→ 0.4-0.5s 有方向性的轉場=明確『章節換頁』訊號=段落感=留存友好；轉場+whoosh 同步後 premium 感相乘。
13. **章節數字卡 + BGM 能量曲線 + 卡重拍** [medium]（`data_anim.py` render_chapter_card + build script BGM arc + beat 對齊 + `silent_vlog_maker/pick_bgm` 升級 arc 版）— `render_chapter_card(n, title)`：深紫底 + Anton 320px 超大金數字（01/02/03，雙層 bloom）+ Huninn 64px 白章節名，0.8-1.2s，出現配 whoosh；BGM 升級 `pick_bgm_arc(chapters)`：hook 高能 → 講解段換 minimal 或同曲 `lowpass=f=2000,volume=-4dB` 悶化變奏 → reveal/outro 開回全頻寬+上揚 cue；章節交界 `acrossfade=d=1`；`librosa.beat.beat_track` 抓新段前 2s 第一個 downbeat，章節卡 pop 幀對齊 ±0.2s（中文圈『卡點』）；角落常駐 3 小圓點進度指示（目前章填金）overlay 全程。→『還剩多少』結構感直攻中段流失（AVP 瓶頸對症）；換曲/悶化本身=免費聽覺 pattern interrupt，禁單曲 loop 到底（老高反例）。
14. **靜音機械壓縮 + 字/分語速報告** [medium]（`longform_maker/build_audio`，M103 SPEED 同一組檔案）— `silencedetect=noise=-35dB:d=0.7` 抓停頓 → <0.7s 保留（呼吸感）、0.7-1.0s 壓到 0.5s、>1.0s 一律壓到 0.3s；切點用 whisper 字級時間保護不吃字尾；輸出 offset map，字幕與 cut 點全按 map 平移（M87 gate 照跑）；報告印『字/分』：腳本總字數÷成片旁白秒數，目標 240-280 字/分；<230 → M103 SPEED 調 1.08-1.15、>290 → 段落間補 0.3s 呼吸（必須有畫面事件蓋住，守 M95）；subprocess stderr 指定 encoding（M102）。→ dead-air 全自動歸零（留存圖最一致的滴血點）；語速從感覺變每支片的例行數字，長片01 加速版更順已是自家證據。
15. **Re-hook flash-forward x2 + 老高式問號卡（每章 1 次）** [medium]（build script insert_rehook + `data_anim.py` render_question_card + yt-script-style 每章問句規則）— `insert_rehook(payoff_ts, insert_ts)`：片長 ~40% 與 ~70% 處各插 1.5s 後段 payoff（`ffmpeg -ss X -t 1.5`，硬切+whoosh），腳本層預留一句『等一下你會看到…』；每章 1 次老高節拍：旁白丟問句 → 切 0.6-0.8s 問號卡（深紫底+金問號，scale 1.00↔1.02 float 呼吸逐幀渲染、BGM 不斷=非死空檔）→ 答案數字 pop + hit SFX。→ 教學片留存自然下垂在 40-60% 處，flash-forward 是該區間實證最有效的解；問號卡給『想知道』open loop，與圖卡驅動互補。

### 波3・簽名與包裝（rank 16-18）

16. **懶人包 recap 卡升級 + 來源小字標配** [low]（`anim7_recap.py` + `data_anim.py` new_canvas 加 source 參數）— outro 前 6-8s：金色『本集重點』標題 + 3 條白 bullet（每條 ≤14 全形字），逐條間隔 0.5s stagger 進場，旁白同步『幫你整理三個重點』；設計成單張截圖完整可讀（直接複用成 IG/Threads/Line 群圖）；所有數據卡左下角加 DIM 色 22px 來源小字（『資料來源：FB 專業主控台 2026-07』），做成 new_canvas 選項參數。→ recap 拉結尾滿意度（餵 survey 分發訊號）+ 中文圈『傳圖進 Line 群』分享面；來源小字在 AI 賽道直接轉信任（Hao 滿意度 98.3% 的護城河）。
17. **Light sweep 金數字收尾（hero 簽名鏡頭完成體）** [medium]（`fx_lib.py` light_sweep + `data_anim.py` render_hero 收尾 + `animate.py` 幀序安排）— `light_sweep(mask, t)`：45° 白色漸層帶（寬=字高x0.6、兩側 GaussianBlur(10) 羽化），以數字 alpha 為 mask，x 從 -w 掃到 +w，0.5s 純 linear（掃光不減速）、screen 模式峰值 opacity 50%；觸發時機：hero counter 落地+pop+glow 脈衝之後 0.3s；每支限 hero/結論卡 1-2 次。→ 平面金色瞬間讀成有反射的材質（AE CC Light Sweep 的逐幀等價物）；hero 數字=頻道識別，這是為它量身的最後一塊。
18. **縮圖 PIL 自動 gate + Test & Compare 3 變體『承諾強度』測試** [low]（縮圖 build script PIL gate + video-autopilot SKILL.md publish checklist：拍前先鎖 packaging、縮圖畫面 30s 內兌現）— 機械 gate：臉 bbox 高 ≥288px（0.40x720）、前景元素 ≤3（OpenCV 連通域粗算）、中文大字 ≤4 字且與標題字串零重複、數字字高 ≥80px、主體/背景明度對比 ≥4.5:1、自動輸出 200x113 glance 檢查圖貼進模擬 feed；每支上滿 3 變體測『承諾強度』而非風格（A=真值數字承諾、B=工具名承諾、C=結果畫面承諾），跑滿 2 週不提早收；標題預設模板=第一人稱真值轉化（『我用 X 在 Y 做到 Z』，前 12 中文字放最強承諾），負面框架只當 B 變體。→ T&C 判贏已改 watch-time-per-impression（R15）——唯一同時打『曝光 8k 天花板』與留存的包裝槓桿；表情變因實測 +42% CTR/82% 勝率。

### ⛔ 明確不做清單（skip list）

1. **ffmpeg zoompan（任何形式）** — 永久禁：integer 座標抖動不可修；所有推鏡/慢推一律走 fx_lib.ken_burns_frame 亞像素 AFFINE（已寫好）。
2. **常駐色差 / VHS / glitch 蒙太奇** — 常駐 CA=遊戲畫質劣化感（玩家都關掉的那種）、glitch 與教學可信度衝突；只保留『impact 幀 1-2 幀、≤2px、邊緣限定』版本（fx_lib.chromatic_aberration 已備、預設不開），且僅用在『翻車/出錯』語意點、每支 ≤2 次。
3. **亮度 flicker（±0.9% filmic 曝光呼吸）** — 與 M93 頻閃教訓正面對撞，收益小風險大；filmic 感全由 grain + split-tone 承擔。
4. **滿版台綜花字 / 貼圖 / emoji 轟炸** — AI 教學賽道直接砍專業感，與 premium 深紫金定位衝突；情緒標記層由『字幕關鍵詞變重 + SFX + 章節卡』承擔。再入條件：若留存數據顯示中段情緒平坦，才考慮克制版花字（白字面+彩描邊、≤4 張/支）。
5. **彩色 karaoke / 多色輪播字幕** — white-first 鐵則鎖死（2026-07-02）；字幕動態只做 blur-in/位移/每句 ≤1 金色關鍵詞，全片過 audit_color_ratio。
6. **全片 overshoot / elastic 彈跳** — 全都彈=綜藝廉價感；ease_out_back 只給 hero 金數字與結論卡（每支 ≤3 處），其餘一律 ease_out_quint/expo。
7. **MrBeast 式全程高頻快切（ASL <2.5s 全片）** — 教學長片贏家模式是『平緩 15-25s/cut + 每 2-3 分鐘一段 burst』交替；全程快切毀教學清晰且中後段疲勞，違『教學清晰>特效』。
8. **縮圖再聳動化 / clickbait** — CTR 8.5% 已達標，且 T&C 判贏改 watch-time-per-impression 後騙點自動輸；優化方向改測『承諾準確度』（R15）。
9. **Odometer 逐位滾輪數字** — count-up + 固定字槽已拿到 90% 效果；逐位滾輪 effort 高邊際小，等 hero 數字成系列簽名後再議。
10. **外部平台導流衝量（Threads/IG 導流等 growth hack）** — 2026-07-06 Hao 使命定調：只用 YT-native 五槓桿，工具/SKILL 要讓一般人打破冷啟動；外部導流=可選、Hao 點名才用（Hype 是站內按鈕不算外部，走 R25）。

---

## → wave5 深研（2026-07-23）：細剪/留存/數據呈現/2026 工具 37 條
完整規則（雙模式節奏波/J-L cut 帶數字版/句尾5-6割/30%變化率/反slideshow事件預算/count-up規格/轉場語意表/pattern interrupt 時刻表/3-frame flash…）→ [wave5 全文：editing-wave5-finecut-2026.md](editing-wave5-finecut-2026.md)。**細剪前整份讀。**
