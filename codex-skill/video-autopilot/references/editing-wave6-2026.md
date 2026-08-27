> **主責／路由**：需要音訊時間軸、疊加層動畫語法與教學結構規格時讀本文；跨檔主寫分工見 [craft refs 索引](craft-index.md)。

# 剪輯技法 wave6 深研（2026-07-24）— 聲音設計 / 視覺語法 / 教學結構

三路平行深研 31 條（聲音設計 W6A 9 條 / 視覺語法 W6B 10 條 / 教學結構 W6C 12 條），每條含：規則(帶參數) / 落地(機械化 gate 設計) / 來源 / dedupe（對 wave5 37 條與既有 refs 的查重結論）。
定位：與 editing-wave5-finecut-2026.md（細剪/留存/數據呈現/工具 37 條）互補零重複——wave5 管細剪執行層，本檔補三個 wave5 沒碰的維度：音訊時間軸（密度/頻譜/聲像）、疊加層動畫語法（轉場執行/kinetic 字/圖表 motion/時長階梯）、教學型結構（demo 速度/章節/錄製遙測/EDL 工作流）。
數字警語：來源多為業界 best-practice 宣稱與少量 benchmark（Munch 1,000 片研究 / TimeBolt F1 / NN/g 感知窗），閾值類數字（YAVG>40、ramp≤2 次、10s 窗口 ≥3 SFX）是方向性起始值，實測後校準。
使用：混音/細剪/發布前整份讀；落地照「落地(機械化)」欄指的模組動手；檔尾「落地優先序」決定動工順序。

> **現行執行契約（2026-08-27）**：所有機械化落地都必須是 `hao.video-autopilot.edit-plan/v4` typed structured command，綁 evidence／時間窗／參數／品質斷言；`workflow_contract.py` 依序產生 audit、atomic apply、render、delivery QA 與 human/outcome receipts。禁止直接改舊 editor 草稿或只以輸出檔存在判定成功。

## 快查表（31 條一行索引）

| 編號 | 一句話 | 落地掛點 | 機械 gate |
|------|--------|----------|-----------|
| W6A-1 | 每章 SFX 只綁 3-4 個重點 moment，10s 窗口 ≥3 個=過量 | build_final SFX 插入表 density gate | ✅ |
| W6A-2 | 同類 SFX 備 2-3 變體輪替，同檔 <20s 重播必變化 | asset_forge SFX 對映表 variants 欄 | ✅ |
| W6A-3 | 方向性轉場 SFX pan 對齊視覺運動，無方向事件置中 | transitions.py semantic_map + pan 曲線 | ✅ |
| W6A-4 | BGM 頻譜否決：含 vocal 直接換、1-4kHz 織體要稀疏 | BGM 入庫 gate（bandpass astats / demucs） | ◐ warn+人工試聽 |
| W6A-5 | BGM 常駐挖 2-5kHz voice pocket EQ，與 sidechain 互補 | master_mix filtergraph 檢查 | ✅ |
| W6A-6 | SFX 帶內三層：impact -12 > whoosh -15 > click -18dB | SFX 插入表 category→gain 欄 | ✅ |
| W6A-7 | 音訊 interrupt 五型放 decision points（25-35s 必有一個） | scene sheet audio_interrupt 欄 + QA | ✅ |
| W6A-8 | SFX 一律 48kHz WAV + manifest 記來源授權，缺項 BLOCKED | sfx_manifest.json + final_delivery_qa | ✅ |
| W6A-9 | montage 鎖單一 cadence（2/4-beat 網格），段內不混用 | music_engine beat grid 驗 cut interval | ✅ |
| W6B-1 | 轉場方向鎖+剪點卡峰值幀+9-15f 時長+SFX 同幀 | transitions.py 擴欄 + delivery_qa | ✅ |
| W6B-2 | kinetic 字每章 ≤1、進場 ≤300ms、靜止 hold ≥1.5s | fx_lib text preset + brand_templates | ✅ |
| W6B-3 | 圖表三刪：3-5 資料點/1 強調色/標題改結論句 | brand_templates chart 卡 + audit_color_ratio | ◐ 弱檢+人工 |
| W6B-4 | 圖表類型→motion 語意對照表 + 軸先進場 build 順序 | fx_lib chart_build() semantic dict | ✅ |
| W6B-5 | 混剪亮度連續：相鄰 scene YAVG 差 >40 flag、UI 白 ≤235 | delivery_qa luma_continuity + grade_lib assert | ◐ flag+人工判 |
| W6B-6 | b-roll 遞減節奏 0.7x/顆→payoff 最長 hold，全片 ≤2 次 | build_video montage_ramp() helper | ✅ |
| W6B-7 | callout 不遮 action 區（IOU=0）、一次一個、≤5s | fx_lib callout bbox assert | ◐ assert+掃描人工 |
| W6B-8 | zoom 在旁白關鍵詞 onset 前完全 settle（導航先落地） | fx_lib zoom assert + word_captions 時間戳 | ✅ |
| W6B-9 | 動畫時長三級階梯 150-300/250-400/400-600ms + 退場 ease-in | fx_lib/brand_templates DURATION_LADDER | ✅ |
| W6B-10 | 文字動畫 pattern 白名單（sequential/morph/enter-exit），flicker 禁用 | brand_templates 模板庫結構性禁用 | ✅ |
| W6C-1 | demo 三速語意表 1x/2-4x/8-12x，cut>speed 優先序 | video_handlers/screen_clean speed_map 欄 | ✅（吃 W6C-8 log） |
| W6C-2 | 之字剪 timelapse：1x↔Nx 卡句界 + 加速 >1.5x 疊速度徽章 | build_video demo handler + fx_lib speed_badge | ✅（需 handler 擴充） |
| W6C-3 | 等待段三選一（硬切/timelapse/PiP cutaway），禁原速空播 | screen_clean wait classifier + scene sheet 欄 | ✅（吃 W6C-8 log） |
| W6C-4 | 非臉 PiP 規格：同比例 1/9 面積、固定角落、不遮字幕 | video_handlers pip() handler | ✅ |
| W6C-5 | YT 章節命名 4-8 詞/關鍵字前置/禁劇透/首內容章節 ≥30s | 發布套件生成器 title lint | ✅ |
| W6C-6 | 章節數量隨片長：3-5min 壓 3-4 個，8-10min 才 5-7 個 | 章節生成器 n_chapters 公式 | ✅ |
| W6C-7 | click 遙測→auto-zoom keyframe 演算法藍圖（開源克隆群萃取） | input_logger 後處理→fx_lib keyframe | ✅（需新模組） |
| W6C-8 | 錄製即遙測：input_logger 記輸入真值，不事後視覺猜 | 新模組 input_logger.py（三個下游消費者） | ✅（需新模組） |
| W6C-9 | build/tool 教學片開場必含 ≤30s 成品運行實錄 | scene sheet lint + script_gate BLOCK | ✅ |
| W6C-10 | screencast=B-roll 主從律 + 錄製紀律三條（游標/GUI 連續） | 錄製 checklist + delivery_qa joint-diff | ◐ 紀律人工+SSIM gate |
| W6C-11 | 偵測層波形優先、決策層 LLM、剪輯決策=可 diff 的 EDL | 新模組 edl_diff.py + LLM 建議層 | ◐ diff 機械+人審 |
| W6C-12 | 章節=檢索資產：auto 當底稿手動覆蓋，D+1 查 SERP 收錄 | 發布 checklist 第 4 動作 + Log Outcome 巡檢 | ◐ lint 機械+人工巡檢 |

## TOPIC: audio（W6A 聲音設計 9 條）

### W6A-1. SFX 事件預算（density cap）：每章初排只在 3-4 個最重要 moment 綁 SFX（數據 reveal/章節轉場/UI 確認三類優先），回聽覺得空才補；『每個 cut 都配 whoosh』或任一 10s 窗口出現 ≥3 個 SFX 事件 = 過量，砍到只剩落在重點上的。
落地(機械化): build_final 的 SFX 插入表（asset_forge 對映表輸出）跑 density gate：(1) 滑動 10s 窗口 SFX 事件數 ≥3 = warn；(2) SFX 事件數 / cut 數 >0.5 = fail（whoosh 貼滿 cut 的特徵）；(3) 每章 SFX 數 <2 = 提示可能太空。
來源: https://sfxengine.com/blog/common-sound-design-mistakes-in-video-editing ; https://videoeditingsfx.com/how-to-use-sound-effects-in-video-editing/ ; https://www.editorskeys.com/blogs/news/the-ultimate-guide-to-sound-design-in-video-editing
dedupe: wave5 #6 stat 卡管『SFX 綁哪』（whoosh→zoom/pop→annotation/ding→counter 不隨機撒）、master-techniques 管『同時併發層數 ≤2（color of sound）』，都沒有『全片/每分鐘 SFX 總量上限』；本條補時間軸密度預算這個缺口。

### W6A-2. 同一 SFX 檔防重複輪替：同類事件（whoosh/pop/ding）各備 2-3 個變體檔輪替使用；同一檔案兩次使用間隔 <20s 時必須換變體或做 ±2-3 半音 pitch-shift / ±10% duration 微變，聽感重複 = 業餘 tell。
落地(機械化): SFX 插入表 group by 檔名：相鄰兩次同檔使用 timestamp 差 <20s 且無 pitch/duration 參數差 = warn；asset_forge 的 12-SFX 對映表每個 slot 檢查 variants 欄 ≥2 檔。
來源: https://www.krotosaudio.com/how-to-design-whoosh-sound-effects/ ; https://www.asoundeffect.com/game-audio-immersion/ ; https://pixflow.net/blog/cinematic-whoosh-sound-effects/
dedupe: 既有 12-SFX 對映表只管『事件類型→聲音類別』，wave1-5 從未處理『同一取樣重複播放的聽感疲勞』；游戲音訊的 variation/rotation 概念首次入庫。

### W6A-3. Whoosh 方向性 pan 對齊視覺運動：有方向的視覺事件（wipe/slide/whip 轉場、KenBurns 推移）配同方向 stereo pan 自動化（畫面 L→R = pan 左→右掃過），無方向事件（pop/ding/counter 落點）一律置中不 pan。
落地(機械化): transitions.py 的 semantic_map 已帶方向資訊 → SFX 插入時附 pan 曲線參數（ffmpeg stereotools/pan filter）；QA 掃描：wipe/slide 類事件的 SFX 無 pan 參數 = warn、pop/ding 類帶 pan = warn。
來源: https://www.krotosaudio.com/how-to-design-whoosh-sound-effects/ ; https://www.dl-sounds.com/whoosh-sound-effects/
dedupe: master-techniques 的 synchresis 只焊『時間』（±1 frame）、techniques-2026 C 只管『同幀 timing』；聲像空間維度（pan 與視覺運動向量對齊）wave1-5 完全沒碰。

### W6A-4. BGM 選曲頻譜否決條件（vocal + 中頻密度）：教學旁白片 BGM 必須 instrumental（含哼唱/vocal chop 都不行），且 1-4kHz 人聲頻段織體要稀疏（鋼琴/pad/低頻 groove 優於密集電吉他/銅管/synth lead）——頻譜打架 sidechain 救不了，選曲階段直接換。
落地(機械化): BGM 入庫 gate：ffmpeg 對候選曲跑 bandpass(1000-4000Hz) astats RMS 與全頻 RMS 比值，>0.45 = warn 要人工試聽；進階用 demucs 抽 vocal stem，stem 能量 >-40dBFS = 含人聲直接 fail。
來源: https://www.masteringbox.com/learn/frequency-masking ; https://protunesone.com/blog/top-tips-for-balancing-voiceovers-with-background-music-in-videos/ ; https://theproducerschool.com/blogs/music-production/frequency-masking-explained-complete-guide-for-producers
dedupe: master-techniques 選曲管 BPM×Energy×mood 三維、hao-teaching-method 管題材命名映射、fundamentals 管混音層級 dB——全是『音量/情緒』維度；『頻譜相容性當否決條件』是新維度。

### W6A-5. BGM 常駐 EQ voice pocket：除 sidechain duck 外，BGM 軌常駐挖一個 2-5kHz、-3~-4dB、寬 Q 的 dip（voice pocket），讓人聲清晰度靠頻譜讓位而非只靠音量壓——duck 可從 ratio 8:1 收斂、BGM 存在感更連續不抽動。
落地(機械化): master_mix filtergraph 檢查 music chain 含 equalizer=f≈3000:t=q:w≈2:g=-3~-4；效果驗證接既有 af_whisper transcript_diff gate：加 pocket 後錯字率不得上升。
來源: https://protunesone.com/blog/top-tips-for-balancing-voiceovers-with-background-music-in-videos/ ; https://www.soundgym.co/blog/item?id=four-ways-to-fix-frequency-masking-in-your-mix
dedupe: fundamentals 已有 sidechaincompress（寬頻音量閃避）與人聲 de-esser（7kHz 砍嘶聲），但對 BGM 軌的『常駐頻譜雕刻』wave1-5 沒有；本條與 sidechain 是互補不重複（頻域 vs 時域）。

### W6A-6. SFX 類內音量分層（felt not heard）：SFX 帶（-12~-18dB 既有規則）內再分層：impact/重點 punch 佔上端（≈-12dB）、whoosh 中段（≈-15dB）、UI click/tap 壓最低端（≈-18dB，貼近『感覺到而非聽到』）；螢幕錄影教學的滑鼠/鍵盤確認音尤其要小而脆。
落地(機械化): SFX 插入表加 category→gain 欄位：QA 驗 click 類 gain ≤ whoosh 類 gain -3dB、impact 類 ≥ whoosh 類 +3dB；違反排序 = warn。
來源: https://www.storyblocks.com/resources/blog/pump-youtube-videos-stock-sfx ; https://videoeditingsfx.com/how-to-use-sound-effects-in-video-editing/ ; https://krotos.studio/blog/how-to-balance-music-and-sound-effects
dedupe: editing-craft-fundamentals L113 只給 SFX 整類 -12~-18dB 一個籠統帶；類內三層排序（impact>whoosh>click）與教學片 UI 音的特別處理是新細分。

### W6A-7. 音訊層 pattern interrupt 類型庫 + decision-point 放置：音訊 interrupt 五型（BGM 驟停/tempo-能量 shift/SFX 對 cut punch/旁白語速驟變/音樂→靜默 drop）當獨立武器用，放在 decision points：25-35s 新觀眾游離點放第一個、問題揭露/before-after 對比/教學最易卡關的步驟前各一——不必與視覺 interrupt 同時，單獨用成本最低。
落地(機械化): scene sheet 加 audio_interrupt 欄（五型 enum）：QA 檢查 25-35s 窗口內 ≥1 個音訊層事件（BGM 切換/音量斷點/SFX），每章 ≥1 個 audio_interrupt 標記且落在標記的 decision point ±2s。
來源: https://joyspace.ai/pattern-interrupt-reset-attention-span ; https://lightningim.com/digital-tools/12-powerful-pattern-interrupt-video-editing-techniques-that-boost-engagement/ ; https://edicionvideopro.com/en/editing-for-platforms-video-marketing/pattern-interrupts-tiktok-retention-guide/
dedupe: wave5 #2 的 pattern interrupt 全管『視覺』事件頻率、master 的 stop-down 只管『全靜默 2-3 次』一型；本條給音訊 interrupt 的完整類型清單＋語意放置點（25-35s/卡關步驟），且明確『音訊可獨立於視覺』。

### W6A-8. SFX 資產規格 + 授權台帳：SFX 一律 48kHz WAV 入庫（不收 MP3 轉檔），每檔在 sfx_manifest.json 記來源＋授權型態（Pixabay/Zapsplat=免費商用、Uppbeat 免費層需 attribution、Epidemic/Artlist=訂閱期內 clear、Freesound 逐檔查 CC 條款），發布 gate 掃 manifest 缺項。
落地(機械化): ffprobe 掃 assets/sfx/：sample_rate≠48000 或 codec≠pcm_s16le/s24le = warn；manifest 每檔必有 source+license 兩欄，任一缺 = BLOCKED（併入 final_delivery_qa）。
來源: https://pixabay.com/blog/posts/free-and-high-quality-sound-effects-for-video-edit-453/ ; https://sendshort.ai/guides/sfx-libraries/ ; https://uppbeat.io/blog/sound-effects/free-sound-effects-websites
dedupe: refs 有 BGM 命名映射與 12-SFX 對映表（用途層），從未管『檔案技術規格』與『授權可追溯性』；訂閱到期後舊片 claim 風險也是首次入庫的營運知識。

### W6A-9. Montage cut cadence 一致性（2-beat / 4-beat 網格）：b-roll/montage 段先選定一種 cadence 再剪：2-beat 網格＝社群感標準（120BPM→每 1s 一刀）、4-beat＝沉穩 cinematic（→每 2s）、1-beat 只留給高潮衝刺段；同一段內不混用兩種以上 cadence，微偏 beat 的 cut 觀眾說不出哪裡怪但整段顯得 sloppy。
落地(機械化): music_engine 已產 beat grid → montage cut list 驗每個 cut interval ∈ {1,2,4}×beat_duration ±1 frame；同段內出現 ≥3 種 interval 值 = cadence 混用 warn。
來源: https://echowave.io/tools/beat-sync/ ; https://bitcut.app/blog/beat-sync-video-editing ; https://clipmusic.ai/blog/bpm-video-editing-guide
dedupe: techniques-2026 C 只說『scene cut 對齊 beat』（對不對齊）、master-techniques 的 phrase-cutting 管『剪音樂本身』的 4/8 小節、anticipation cut 管『刻意不卡』的例外；本條管『卡哪些 beat』——cadence 選擇與段內一致性是缺口。

## TOPIC: visual（W6B 視覺語法 10 條）

### W6B-1. 章節 motion 轉場執行規格（方向鎖+剪點）：wave5 語意表決定『何時用』，本條管『怎麼做』：(a) 任何 whip/slide/wipe 轉場，出點與入點動勢必須同方向同速（左出=左進），剪點卡在 blur/位移峰值幀；(b) 合成轉場時長鎖 0.3-0.5s（30fps 約 9-15 frames），與 whoosh SFX 同幀（SFX 長度=轉場長度）；(c) 全片前進方向統一一個（如一律右→左），只有『回扣開頭/回顧』才准反方向——方向本身變成語法訊號；(d) dissolve 之外的轉場一律不疊加（一次一種效果）。
落地(機械化): transitions.py 的 semantic_map 每個 entry 加 direction 與 duration_frames 欄；build_final 檢查全片非硬切轉場 direction 一致（白名單=標記 callback 的轉場）；delivery_qa 驗轉場 duration 在 9-15f 內、SFX 起點與轉場起點同幀（±1f）。
來源: nofilmschool.com/how-to-do-a-whip-pan（方向/速度一致、剪在 blur 處）+ studiobinder.com transitions guide + filmdaft.com scene transitions；時長與 SFX 同幀承 editing-techniques-2026 既有 whoosh 400-500ms 條
dedupe: wave5 finecut#7 只管語意映射（何時 wipe/dissolve/zoom-through），未給方向/剪點/時長執行參數；niche-grammar 旅遊 whip pan 是實拍甩鏡（blur length 50-100），本條是 ffmpeg 合成轉場的執行規格——互補不重複

### W6B-2. Kinetic typography 克制規格（emphasis 動畫層）：動態字只做單一重點詞、不動整句：每章節 ≤1 個 kinetic moment；動畫必須快速 resolve 到靜止可讀狀態——進場 200-300ms ease-out，之後靜止 hold ≥1.5s 才可退場；理解不得依賴動畫時序（動畫被跳過也要讀得懂=靜態 fallback 完整）；多元素（如 3 行清單）進場 stagger：視訊層用 100-150ms/元素（UI 級 30-60ms 在 30fps 只有 1-2 frames、人眼讀不到）；只動位置/縮放，不動色彩（M68 白字鐵則不破）。
落地(機械化): fx_lib 的 text emphasis preset 鎖 enter≤300ms/hold≥1.5s；brand_templates 清單卡 stagger 參數預設 120ms；delivery_qa 數每章 kinetic moment >1 = warn（與 finecut#9 text-pop 計數器共用）。
來源: digitalsilk.com kinetic typography 2026（one clear moment per section／resolve quickly／理解不依賴動畫）+ nngroup.com animation-duration（100-500ms 感知窗）+ fluent2.microsoft.design motion（stagger 30-60ms 為 UI 基準，視訊放大）
dedupe: wave5 finecut#9 的 text-pop 6-8f 是『半屏 flash 武器』限 ≤2/片；本條管常規 emphasis 動畫的進場/settle/stagger 規格——不同層級；niche-fonts-colors 管色彩不管動畫；M68 管樣式本條管運動

### W6B-3. 圖表上鏡三刪鐵則（remove to improve for video）：任何圖表上鏡前強制三刪：(a) 資料點砍到 3-5 個（top10 排名只留 top3-5，其餘併『其他』或刪）；(b) 色彩=1 個強調色打在焦點元素、其餘全灰/淡藍（正好落在 Hao white-first ≤2 色鐵則內）；(c) 圖例刪除改 direct label、副標刪除；且圖表標題必須改寫成結論句（『X 比 Y 貴 8 倍』而非『X 與 Y 價格比較』）。理由：影片觀眾要同時吸收 shapes/colors/text 三軸，任一軸過載整張卡就白放。
落地(機械化): brand_templates chart 卡模板鎖 max_series=5、palette 強制 [強調色, 灰]；script_gate 的 asset checklist 加『chart 標題含比較詞/數字/結論動詞』檢查（regex 弱檢+人工確認）；delivery_qa 全幀掃描時檢查 chart 幀色彩數 ≤2（audit_color_ratio 現成可掛）。
來源: onlinejournalismblog.com 2026-06-23（Paul Bradshaw, Birmingham City University data journalism：remove to improve／top3-5／單強調色／標題=story）
dedupe: 全新——wave5 dataviz 管 counter/vs-card/dwell/annotation 順序，完全沒管圖表本身的簡化設計；M10 管數字真實性不管呈現密度

### W6B-4. 圖表動畫語意對照表 + build 順序：圖表類型決定 motion 類型（錯配=語意訊號錯誤）：折線圖=左→右 wipe（時間軸方向）、長條圖=從基線垂直長出、排名演變=timelapse/bar race、單一大數=counter（規格承 finecut#6）、聚焦對比=highlight+其餘 fade。build 順序固定：軸+格線+結論句標題先進場（0.3-0.5s）→ hold 0.5s 建立座標系 → data 依旁白逐段 reveal（timing 承 dataviz#3 word onset）→ 數值標籤在該元素落地後才出現；一個畫面同時只動一個 chart 元素。
落地(機械化): fx_lib 加 chart_build() semantic dict：{line:'wipe_lr', bar:'grow_baseline', rank:'race', big_num:'counter', focus:'highlight_fade'}；scene sheet 的 chart 欄只准填圖表類型、動畫自動查表（同 finecut#7 的『填語意不填效果』哲學）；delivery_qa 驗 axis 進場時間 < 首個 data 元素進場時間 ≥0.5s。
來源: onlinejournalismblog.com 2026-06-23（wipe/reveal/zoom/highlight/counter/timelapse 技法-用途對照）+ provideocoalition.com creating-animated-graphs（axes→grid→write-on 順序）+ flourish.studio animated-charts（staged reveal + annotation）
dedupe: wave5 dataviz#3/#4/#6 管 counter timing 與禁雙 counter；本條是『哪種圖配哪種 motion』的語意映射＋整卡 build 順序——映射表全新，單活動元素原則是 dataviz#6 的推廣

### W6B-5. 混剪亮度連續性 gate（螢幕錄影×實拍）：教學長片混用 sRGB 螢幕錄影與 iPhone 實拍（M3 tonemap 後）時：(a) 螢幕錄影永不套 look/LUT（色準鐵則），只准亮度微調；(b) 校色方向=相機素材向 UI 靠攏，不反向動 UI；(c) 相鄰 scene 跨 source 的平均亮度差過大=白閃感：ffmpeg signalstats 抽每 scene YAVG，相鄰 scene 差 >40（0-255 標度，約 15%）= flag（起始閾值，實測後調）；(d) UI 白背景收在 tv range 235 以內不觸頂，與 colordetect range gate（tools#9）互補——range 管 metadata、本條管實際亮度連續性。
落地(機械化): delivery_qa 加 luma_continuity gate：per-scene `signalstats` YAVG → 相鄰差 >40 列清單給人工判；grade_lib 加 assert：輸入 source type=screen_recording 時禁走 look chain。
來源: midlandsinbusiness.com color-grading for course creators（mixed footage 先拉同 baseline、correct first grade second）+ forum.videohelp.com / cined.com gamma-shift threads（full/limited 與白位漂移成因）
dedupe: canon M3 已有 iPhone HDR tonemap 濾鏡鏈（不重複）；canon 已標教學片❌套 grade look；wave5 tools#9 colordetect 管 range metadata 一致——本條管『跨 source 亮度連續性』的機械檢查，全新縫隙

### W6B-6. B-roll 遞減節奏（acceleration into reveal）：通往 payoff/proof 揭曉的 b-roll/montage 串用遞減 shot 長製造動能：3-5 顆 clip 時長單調遞減（如 3s→2s→1.5s→1s，比例 ~0.7x/顆），payoff 落地那顆反而給全序列最長 hold（≥3s，接 proof stage 4 拍或 counter）——『加速→突然靜止』=張力→兌現。全片此 ramp ≤2 次（開場冷開場前奏 + 最大 payoff 前），濫用=失效。
落地(機械化): build_video 加 montage_ramp(clips, start=3.0, ratio=0.7, payoff_hold=3.0) helper 自動算時長序列；delivery_qa 驗標記為 ramp 的段落 clip 時長嚴格遞減且 payoff hold ≥3s、全片 ramp 計數 ≤2。
來源: fiveable.me pacing-rhythm-editing（progressively shorten approaching peak, hold at climax）+ capcut.com music-video-pacing（setup→acceleration→release→pause→reveal 波形）
dedupe: wave5 finecut#1 雙模式節奏波管 scene 級 fast/focus 交替、finecut#10 管 b-roll 3-7s 常態時長——本條是單一 sequence 內的微觀遞減曲線＋payoff hold 反轉，新層級

### W6B-7. Callout 位置語法（dead-space + 不遮 action）：callout/標註卡的位置鐵則：(a) 永不遮住 action 區（游標當前位置、正被講解的 UI 元件、zoom 目標框）；(b) 固定放 dead space——畫面空白區或邊緣三分線交點；(c) 一次一個 callout（第二個進場前第一個必須已退場）；(d) 停留時長：下限=dwell 公式（dataviz#5），上限 5s（超過=改拆兩張或改旁白講）；(e) 同一支片 callout 樣式只用一套（框+箭頭+標籤同一款式重複使用=品牌一致）。
落地(機械化): fx_lib 的 spotlight_callout/annotation 呼叫加 bbox 衝突 assert：callout bbox 與 zoom 目標 bbox / 游標座標 IOU 必須=0；build_video 檢查同時 active 的 callout 數 ≤1；delivery_qa 全幀掃描抽 callout 幀人工確認無遮擋。
來源: techsmith.com/learn camtasia annotations（placement near content or edges、default 5s、sparing use）+ keystrokelearning.com.au camtasia annotations guide（clutter detracts、one at a time 精神）
dedupe: niche-grammar callout 條管進場 fade 200-300ms 與『標籤短』；wave5 dataviz#10 管 dim→ring→zoom 疊加順序——位置衝突檢查、單一 active、5s 上限、樣式單一化是新的機械檢查點

### W6B-8. Zoom settle-before-read（導航動畫先於閱讀需求落地）：zoom 是導航不是強調：zoom 動畫必須在觀眾需要讀/理解目標區之前完全 settle——zoom 結束幀 ≤ 旁白唸到該元素關鍵詞的 word onset（zoom 移動中文字不可讀，晚到/過衝/持續漂移=三大業餘 tell）。與 dataviz#3 形成互補雙則：強調型動畫（counter/underline）在 onset『起跑』、導航型動畫（zoom/pan）在 onset 前『落地』。zoom 起點=onset − zoom時長(350-500ms) − 緩衝 0.2s。
落地(機械化): fx_lib zoom event 加 assert：zoom_end_t ≤ keyword_onset_t（word_captions 字級時間戳現成）；build_video 排程時自動回推 zoom 起點=onset−0.55~0.7s；delivery_qa 掃 zoom 段與對應旁白詞的時序關係，晚到 = flag。
來源: screenbuddy.xyz screen-recording-with-zoom-effects 2026（a good zoom lands and settles before the viewer needs to read or interpret；tie zooms to the script）+ smoothcapture.app zoom guide（每 ~10s 靜態需一視覺變化，與既有 5-7s 條相容）
dedupe: niche-grammar 管 zoom 倍率/時長/頻率（2x/350-500ms/每3-4s一次）；wave5 dataviz#3 管『強調動畫在 onset 起跑』——本條管『導航動畫在 onset 前落地』的相反向時序約束，全新且直接可 assert

### W6B-9. 疊加層動畫時長階梯（統一 duration hierarchy + 退場 easing）：所有疊加層動畫時長按元素尺寸分三級統一：微元素（ring/underline/badge）150-300ms、卡片級（stat 卡/callout/地名卡）250-400ms、全畫面級（章節卡/背景切換）400-600ms；>600ms 的裝飾動畫一律砍（NN/g：>400-600ms 開始感覺拖）。easing 方向鐵則：進場 ease-out（快進慢停）、退場 ease-in（慢啟快走）、位移類 ease-in-out——進退場曲線不對稱是 pro 質感的隱形來源；全片同級元素時長一致（同款 ring 一律同 duration）=系統感。
落地(機械化): fx_lib/brand_templates 建 DURATION_LADDER dict {micro:(150,300), card:(250,400), full:(400,600)}，所有 overlay 呼叫帶 size_class 查表；delivery_qa 掃事件表：同 size_class 內 duration 變異 >20% = warn、任一裝飾動畫 >600ms = flag。
來源: nngroup.com animation-duration（100-500ms 感知窗、>400ms 嫌慢）+ m1.material.io duration-easing（mobile 300ms 基準、複雜全屏 375ms+）+ blog.pixelfreestudio.com data-viz animation（200-500ms optimal）
dedupe: niche-grammar 有散點數值（zoom 350-500ms、callout fade 200-300ms）——本條把散點統一成三級階梯＋補『退場 ease-in』與『同級一致性』兩個未覆蓋維度，是 consolidation+extension 不是重複

### W6B-10. 文字動畫 pattern 語意白名單（教學片版）：kinetic typography 的 7 種 pattern 對教學長片做語意映射白名單：sequential reveal（逐項出現）=清單/步驟、morphing（A 字變 B 字）=『概念轉換/before→after』專用、enter&exit=常規 emphasis（承 W6B-2 規格）；黑名單：flickering（閃爍）與 hypnotizing（迷幻循環）教學片全面禁用——與 proof-driven 可信度直接衝突；create&destroy 限 hook 段 ≤1 次。pattern 錯用（步驟清單用 morphing）=觀眾收到錯誤結構訊號。
落地(機械化): brand_templates 文字動畫模板庫只建白名單 pattern（sequential/morph/enter_exit），黑名單根本不進庫=結構性禁用；scene sheet 文字動畫欄填語意名（list/transform/emphasis）查表，同 finecut#7 哲學。
來源: digitalsilk.com kinetic-typography 2026（7 pattern 分類：morphing/enter-exit/create-destroy/sequential/textures/flickering/hypnotizing + 各自用途）+ ikagency.com kinetic typography guide 2026
dedupe: 全新——現有檔只有 M68 樣式鐵則與 finecut#9 text-pop 武器，沒有文字動畫 pattern 的語意分類；與 W6B-2（規格）分工：2 管 timing、10 管 pattern 選型

## TOPIC: structure（W6C 教學結構 12 條）

### W6C-1. 示範段落三速語意表（1x/2-4x/8-12x + cut-first）：demo 畫面速度分三層且各有語意：(a) 1x 實速＝只留給「正在被旁白教的那個動作」；(b) 打字/例行操作＝2-4x（觀眾讀 code 的速度遠快於打字速度，Screen Studio 級工具的預設做法就是自動偵測 typing 段加速）；(c) 等待類（install/build/AI 生成/render）＝8-12x timelapse 或直接硬切（開發者實務上限約 12x，再高畫面讀作噪訊）。優先序鐵則＝cut > speed：純游標閃爍/純等待段「剪掉」優於「加速」（egghead 官方指南：cut blinking cursors, 打字能貼上就貼上不要現場打）。任何一段 demo 不得全程單一速度。
落地(機械化): video_handlers/screen_clean 加 speed_map 欄（segment_type→factor：narrated=1.0/typing=2.0-4.0/wait=8-12 或 cut）；typing/wait 判定吃 W6C-8 的輸入遙測 log（無 log 時 fallback：auto-editor motion+audio 雙條件）；delivery_qa 加 gate：任一 demo scene 全長單一速度且 >20s = flag。
來源: dev.to/egghead recording-a-great-coding-screencast + screen.studio/guide/speed-up-typing-segments + avdi.codes (virtuouscode) Faster-More-Intense 12x 上限實務
dedupe: wave5 dataviz#8 只有『打字段 1.5-2x』單點；本條升級成三層語意表＋cut>speed 優先序＋12x 上限，字級/行寬部分不重複

### W6C-2. 之字剪 timelapse（1x↔加速交替 + 旁白驅動速度包絡 + 加速透明標示）：長 demo 禁止一段恆速 timelapse 到底，走之字形：1x 進場（讓觀眾看清「開始做什麼」）→ ramp 到 Nx →回 1x 收在結果/payoff 揭曉那一刻；速度切換點必須卡在旁白句界，不落在句中。主從關係＝旁白是母帶：audio 比畫面快→畫面剪短或截段；audio 比畫面慢→畫面加速或插 hold（neteye 2026 螢幕錄影 retime 準則）。凡 setpts 加速 >1.5x 的段落，疊小型速度徽章（『2x』『8x』）或 elapsed 計時角標——AI agent demo 若隱藏等待時間會造成『瞬間完成』的擬真誤導，與 R26-R38 揭露原則同源。
落地(機械化): build_video 的 demo handler 支援 per-sub-segment setpts，速度切換點 snap 到 word_captions 句尾時間戳（現成字級時間）；fx_lib 加 speed_badge(factor, t_in, t_out) drawtext helper，build 時凡 factor>1.5 自動插入；delivery_qa 掃：速度切換點距最近句界 >0.3s = flag。
來源: neteye-blog.com 2026-02 Part 20 task-based screencast（retime-to-voiceover 準則）+ bandicam timelapse 慣例 + Hao 自家 ai-policy-compliance-2026 擬真揭露推導
dedupe: wave5 無任何 speed-ramp/之字剪條目；tools2026#6 只管『切掉』死空檔不管『加速呈現』；與 retention#4 章節縫合互補不重疊

### W6C-3. 等待段三選一（不准原速播等待）：長時間跑程（AI 生成中/安裝中/渲染中）上鏡一律三選一，禁止原速空播：(a) 硬切＋結果揭曉＋elapsed 標示（『3 分鐘後』字卡）——適合等待本身無資訊量；(b) timelapse＋旁白講解『底下正在發生什麼』——把 dead time 變教學時間，適合過程有可講的原理；(c) cutaway 到下一個概念卡/預告，等待畫面縮成角落 PiP 繼續跑——適合要保留『真的在跑』的可信度證據。timelapse 以 checkpoint 思維壓縮（每 5-10s 抽格），比連續錄再加速的 dead time 更少。
落地(機械化): screen_clean 後加 wait-segment classifier：內容區低 motion + 無鍵擊 + 無旁白 →標 wait；scene sheet 加 wait_treatment 欄（cut|timelapse|pip_cutaway）強制填；delivery_qa 掃成片：任何 >8s 的低變化+無旁白窗口且無 treatment 標記 = fail。
來源: shotomatic.com screen-recording-vs-screenshot-timelapse + podfeet screencasting best practices + docsie.io screen-recording 2026
dedupe: wave5 tools2026#6/7 管『機械偵測+切除』；本條管『敘事處理決策』（切/縮時/切走+PiP 三路），是偵測之後的下一層，不重複

### W6C-4. PiP 規格（不露臉頻道版）：臉 cam PiP 對 Hao 為 N/A（M78 不露臉；業界『露臉錄影互動 3x』的資料點有意識放棄，identity 優先）。但 PiP 本身保留三用途：等待中程序縮角（接 W6C-3c）、terminal 疊在瀏覽器成果上的雙源對照、before 縮角疊 after 全景。規格：PiP 與主畫面同長寬比（1920x1080 主畫面配 640x360 PiP ≈ 1/9 面積）、固定角落、邊距一致、絕不遮字幕安全區與主內容關鍵 UI；同一支片 PiP 位置不游移（換位置=換語意）。
落地(機械化): video_handlers 加 pip(main, inset, corner, scale=1/3) handler：overlay 座標固定四角枚舉+邊距常數+可選 2px 描邊；delivery_qa 加 gate：PiP bounding box 與 ASS 字幕行 bounding box 重疊 = fail；同支片 corner 參數必須唯一。
來源: recmaster.net make-picture-in-picture-video（同比例 640x360 慣例）+ atomisystems ActivePresenter PiP 教程（避遮擋原則）+ screenify.studio 2026-04 webcam overlay（3x 露臉數據＝放棄項）
dedupe: wave5 全 37 條無 PiP/multi-source 條目；SKIP 清單裡的 talking-head 技巧是臉部構圖類，與本條非臉 PiP 不同物

### W6C-5. YT 章節命名規格（留存+CTR 雙修）：章節有實測正效益：Munch 對 1,000+ 支影片分析＝有章節的 like-to-view 比高 2.18-2.8x；<20min 影片互動率 2.96% vs 無章節 1.25%；教學/how-to 類受益最大（可重看、可分段再入場）。命名規格：每個章節標題 4-8 個詞、關鍵字放頭、禁劇透式命名（用『為什麼 X 有效』不用『答案是 X』——保住看下去的理由）、每章標題唯一（禁 Part 1/2 式佔位名）。0:00 章節＝hook 本身（YT 硬性要求首戳記 0:00），第一個「內容章節」邊界 ≥30s——不讓章節列表把 hook 變成可跳過段。
落地(機械化): 發布套件生成器：從 offsets.json beat 名產章節 → 加 title lint（詞數 4-8/關鍵字在前 2 詞/劇透詞黑名單：『答案』『結論是』『最後就是』/重名檢查）；chapter[1].start ≥30s assert。
來源: influencermarketinghub.com youtube-chapters-key-moments（Munch 2024 研究數據+命名原則）+ blackhatworld chapters-timestamps 實測討論（hook 後 30-45s 放首個內容章節）
dedupe: 10-stage §7 只有『用 offsets 回填真實時間戳』一句；wave5 retention#4 管片內視覺章節卡；命名規格/互動數據/首章節位置全為新增

### W6C-6. 章節數量×片長適配：章節對留存的效果隨片長翻轉：10-15min 以上長片章節幫留存（觀眾快速找到要的段落→不直接跳出）；短片（<5min）章節反而誘發跳段提早離開。Hao 目前 3-5min 帶：章節壓到最少 3-4 個（YT key moments 最低門檻＝≥3 個戳記、每章 ≥10s、首戳 0:00），定位是搜尋/key moments 檢索資產而非導航；未來 8-10min 片再放到 5-7 個。評估章節成效盯 session 級指標（returning viewers/總觀看），不盯連續 AVD——章節天然壓 AVD 但抬總量，與 wave5 已裁定的『chapters 淨值為正』一致。
落地(機械化): 章節生成器加規則：n_chapters = clamp(3, beats, floor(duration_min/1.5))；duration<4min 且非搜尋主打題 → 只出 0:00+2 個大段；每章 duration ≥10s assert。Log Outcome mode 增章節後 returning viewers 對照欄。
來源: blackhatworld chapters-timestamps 討論（片長翻轉效應）+ influencermarketinghub（session-level metrics 判準+內容類型 trade-off）
dedupe: wave5 retention SKIP 段已裁定『不拿掉 chapters』但未給數量/片長公式；本條補公式與門檻，不重複裁定

### W6C-7. Auto-zoom 演算法藍圖（開源 Screen Studio 克隆群萃取）：2025-26 開源自動 zoom 工具（openscreen/screenize/recordly/open-recorder）收斂出同一套演算法：①錄製期以 uiohook 級 hook 記錄 click/cursor/keystroke 遙測（120fps），座標歸一化 0-1 做解析度無關；②每個 click 生成一個 zoom region（可配 zoom 深度/持續時間/zoom 間最小間隔——鄰近 click 合併，防 zoom 抽搐）；③zoom 期間的鏡頭跟隨用 Catmull-Rom spline 內插 cursor 軌跡 + smootherStep（Perlin）easing；④keyframe 取樣 50ms 間隔+1% 位移閾值（低於閾值不記，防冗餘抖動）；⑤進階版按活動類型（typing/clicking/scrolling/dragging）規劃不同 zoom 級別而非一律 click-zoom。
落地(機械化): 自研管線落地：demo 錄製時跑 pynput 平行 logger 出 events.json（見 W6C-8）→ 後處理腳本按②合併 click 簇（min_interval 2-3s、M104 content-region 外的 click 直接丟）→ 生成 fx_lib 亞像素 KenBurns 的 zoom keyframe 序列（zoom 級別接 wave5 finecut#5 的 1.5x/2x 參數）；cursor 跟隨先不做（暈眩風險，wave5 已 SKIP cursor-follow），只取『click→離散 zoom keyframe 自動生成』這半套。
來源: github.com/siddharthvaddem/openscreen PR#67（Catmull-Rom/smootherStep/50ms/1%/uiohook 全參數）+ github.com/syi0808/screenize（activity-based 規劃）+ github.com/WizardofTryout/recordly + github.com/imbhargav5/open-recorder（click telemetry→auto zoom）
dedupe: wave5 finecut#5/dataviz#10 給的是 zoom『參數』（350-500ms/1.5x）且假設人工排点；本條是『從遙測自動生成 keyframe』的演算法，供給側全新；cursor-follow 維持 wave5 SKIP 裁定不翻案

### W6C-8. 錄製即遙測（capture-time instrumentation，2026 auto-edit 生態的共同底座）：2026 自動剪輯工具的共同架構解：剪輯智慧來自『錄製當下記錄的輸入遙測』（click/keystroke/window 事件時間戳），不是事後對像素做視覺分析——Screen Studio 系全靠 capture-time telemetry 才能準確偵測 typing 段與 zoom 目標；coding timelapse 工具（programming_timelapse）更進一步在錄製期只在有打字時抽格，輸出即已加速、零後製。原則：能在錄製期拿到的 ground truth（誰在打字/點了哪/等了多久），絕不留到後製用 motion 偵測猜。
落地(機械化): `longform_maker/input_logger.py`：pynput 記錄 {t, type: key|click|scroll, pos} 隨 OBS 同啟同停 → events.json 與錄影檔同名存放；事件檔以 source hash 綁進 material evidence receipt，供 W6C-1 speed_map、W6C-7 zoom keyframe、W6C-3 wait classifier 產 v4 commands；QA：events.json 時長 vs 錄影時長差 >2s = audit BLOCK／重錄警告。
來源: github.com/jason-shepherd/programming_timelapse（typing-triggered capture）+ github.com/imbhargav5/open-recorder（click telemetry 生 zoom）+ screen.studio typing auto-detect
dedupe: wave5 tools2026#7 用 auto-editor motion 偵測＝事後猜；本條是上游架構原則（錄製期記真值），motion 偵測降級為無 log 時的 fallback——互補不衝突

### W6C-9. 成品先行 30 秒 demo 開場（build/tool 教學片結構）：coding/工具教學片的冷開場慣例＝先播「做完的東西真的在動」的 ≤30s demo run，再回頭從零教——egghead 對講師的第一課就是『你的第一支 screencast 是一個 30 秒 demo』；觀眾在承諾時間成本前要先看到終點長什麼樣。對 Hao：現有冷開場=戰績數字截圖（M107 proof），本條補第二種開場資產＝『成品運行畫面』——教 skill/pipeline 的片，開場除數字外要有 1-2s 成品跑起來的實錄（agent 跑完/影片產出瞬間），兩者可疊用（數字卡+運行畫面）。
落地(機械化): scene sheet lint：video_type=tutorial/build 的專案，b01 必含 asset_role=result_demo 的素材（實錄 mp4，非靜圖），缺 = script_gate 前置 BLOCK；與 wave5 retention#5 的 flash-forward 機制共用實作（從後段已渲染 scene 抽 1-2s）。
來源: howtoegghead.com/instructor/getting-started/30-second-demo + dev.to/egghead recording-a-great-coding-screencast
dedupe: wave5 retention#1 要求 15s 內 value claim、dataviz#2 要求 0:20-0:30 首張 proof 截圖——都是『主張/戰績』；本條是『成品運行實錄』第三種開場資產，且與 retention#5 flash-forward 實作合流不另起爐灶

### W6C-10. Screencast=B-roll 主從律 + 錄製紀律三條：任務型 screencast 的 2026 教程共識：螢幕錄影一律當 B-roll 對待——錄時不收音、旁白另錄、由旁白決定時間軸，demo 畫面被 retime 去配旁白而非反過來（與 Hao voice-first/offsets.json 中樞完全同構＝外部驗證）。新增三條錄製紀律：①動作與動作之間滑鼠停在固定位置不亂飄（否則加速段游標亂跳）；②滑鼠移動刻意放慢（加速後才自然）；③相鄰錄製段的 GUI 狀態必須銜接（視窗位置/開的分頁一致），剪點兩側畫面狀態跳變=觀眾察覺剪接。
落地(機械化): `longform_maker` 的 demo 錄製 checklist 加三條（錄 Editkin UI 示範時，gdigrab 前先歸位游標）；`media_delivery_qa.py` 加 joint-diff 檢查：demo 段拼接點前後各抽 1 幀做 SSIM，內容區差異 >30% 且非刻意轉場 = BLOCK。檢查結果綁 render artifact SHA 並寫入 delivery receipt，不能只留 console flag。
來源: neteye-blog.com 2026-02 Part 20 task-based screencast（B-roll 準則+滑鼠紀律+GUI 連續性全出自此）
dedupe: 10-stage 已是 voice-first（驗證非新增）；三條錄製紀律與 joint-diff gate 為全新——wave5 無任何『錄製期紀律』條目，M104 screen_clean 只管錄後清理

### W6C-11. AI 輔助剪輯工作流 2026 定位：pre-edit 層 + 文字化 EDL + 波形優先：產業收斂成三層：①pre-edit 層（同步/轉錄/切靜音/素材整理）在進剪輯軟體前跑完，2-6 小時人工前置壓到分鐘級；②文字即剪輯介面（transcript 刪一句=時間軸剪一段）+ LLM agent 讀 transcript 提出剪輯策略、輸出 EDL，spoken-word 內容 rough cut 時間 -60~70%；③但靜音/廢話偵測的 benchmark 打臉純 AI 路線：波形優先的 TimeBolt F1=90.6% 最高（0.01s 精度），轉錄式的 Descript/Gling 留下 448 個贅詞+171s 靜音或 600+ 漏切+誤切，需 52min 人工返修/小時。結論：偵測層用波形（自家 auto-editor 路線正確），決策層才用 LLM/文字；所有剪輯決策表達成可 diff 的文字/JSON（EDL），人審 diff 不審時間軸。
落地(機械化): 把 Hao 管線正式定調為 text-based EDL 系統：scene sheet + offsets.json + auto-editor JSON 已是 EDL——補一個 edl_diff.py：任何重剪以 JSON diff 呈現給人審（哪些段被切/加速/重排一目了然）；可選 LLM pass：讀 transcript 提『可砍段落』候選清單寫進 EDL 註記欄，只建議不執行。
來源: timebolt.io ai-video-editor-showdown-long-form-accuracy-test（F1 benchmark）+ cutback.video ai-video-editing-in-2026 + digen.ai best-automated-ai-video-editing-2026（Quick Cut 2026-02/LLM→EDL）+ cutsio.com text-based workflow
dedupe: wave5 tools2026#6 已選 auto-editor+JSON 中介；本條新增＝benchmark 證據（波形>轉錄式）、三層架構定位、edl_diff 人審機制、LLM 建議層——工具選擇不變、增加架構論證與審計介面

### W6C-12. 章節=檢索資產：manual 標籤壓過 auto-chapters：章節的第二身份是 Google/YT 搜尋檢索資產：手動章節標籤在 Google 索引（key moments/SeekToAction）優先權高於 YT 自動章節，正確流程＝開自動章節當底稿→手動改寫覆蓋（不是關掉、也不是照單全收）；教學類章節帶來 replayability（觀眾回來重看特定段）→ 對 Hao 搜尋槓桿（CTR 7.1% 最強入口）直接加成。發布後 24h 檢查 key moments 是否被 Google 收錄（搜標題看 SERP），與現有 R36『查 YT 自動標籤』併成同一次巡檢。
落地(機械化): 發布 checklist（10-stage §7 Studio 三動作）加第 4 動作：貼手動章節（W6C-5 lint 過的版本）+ 確認說明欄 timestamp 格式合規（0:00 起始/≥3 條/每章 ≥10s）；Log Outcome D+1 巡檢項加『SERP key moments 收錄』勾選欄。
來源: influencermarketinghub.com youtube-chapters-key-moments（manual>auto 索引優先/SeekToAction）+ gyre.pro youtube-video-chapters 2026
dedupe: 10-stage §7 發布三動作無章節項；R36 只查 AI 自動標籤；wave5 無搜尋面章節條目——純新增，且落點併入既有巡檢不加新流程

## 落地優先序（31 條分三堆）

### 堆一：已可掛進現有 helper 的機械 gate（改現有模組/加參數即落地，19 條）

- W6A-1 SFX density gate（build_final SFX 插入表）
- W6A-2 SFX 變體輪替檢查（asset_forge 對映表 variants 欄）
- W6A-3 方向性 pan（transitions.py semantic_map 已有方向資訊）
- W6A-5 voice pocket EQ（master_mix filtergraph + af_whisper transcript_diff 驗證）
- W6A-6 SFX 類內 gain 排序（插入表 category→gain 欄）
- W6A-7 audio_interrupt 欄 + 25-35s 窗口檢查（scene sheet + QA）
- W6A-8 SFX 規格/授權 manifest gate（ffprobe + final_delivery_qa BLOCKED）
- W6A-9 cadence 網格驗證（music_engine beat grid 現成）
- W6B-1 轉場方向/時長/SFX 同幀 gate（transitions.py 擴欄 + delivery_qa）
- W6B-2 kinetic 字 timing 鎖（fx_lib preset 參數鎖）
- W6B-4 chart_build() 語意查表（fx_lib 新 dict，哲學同 finecut#7）
- W6B-6 montage_ramp() helper（build_video 加函式）
- W6B-8 zoom settle assert（word_captions 字級時間戳現成）
- W6B-9 DURATION_LADDER 查表（fx_lib/brand_templates dict）
- W6B-10 文字動畫白名單模板庫（黑名單不進庫=結構性禁用）
- W6C-4 pip() handler（video_handlers 加函式 + ASS bbox gate）
- W6C-5 章節 title lint（發布套件生成器）
- W6C-6 n_chapters 公式（章節生成器 clamp 規則）
- W6C-9 result_demo 開場 lint（scene sheet + script_gate BLOCK，與 retention#5 flash-forward 共用實作）

### 堆二：需新模組（input_logger 底座先建，6 條）

建置順序：W6C-8 → W6C-1/3/7 →（獨立）W6C-2、W6C-11

- W6C-8 input_logger.py（新模組，pynput 遙測底座——一個模組餵三個下游消費者，先建）
- W6C-1 speed_map 三速判定（吃 input_logger；無 log fallback auto-editor 雙條件）
- W6C-3 wait classifier + wait_treatment 欄（吃 input_logger）
- W6C-7 click 遙測→zoom keyframe 後處理腳本（吃 input_logger，輸出接 fx_lib KenBurns）
- W6C-2 之字剪 demo handler（build_video per-sub-segment setpts + fx_lib speed_badge，改動較大）
- W6C-11 edl_diff.py（新模組，JSON diff 人審介面 + 可選 LLM 建議層）

### 堆三：機械只能 flag/守邊界，核心判斷留人工 craft（6 條）

- W6A-4 BGM 頻譜否決（bandpass RMS gate 機械 warn 可先掛；最終取捨靠人工試聽；demucs 進階版屬堆二延伸）
- W6B-3 圖表三刪（audit_color_ratio 守色數、regex 弱檢標題——但『刪到剩什麼』『結論句怎麼寫』是設計判斷）
- W6B-5 亮度連續性（YAVG 差 >40 機械 flag，白閃感最終人眼判；閾值實測後校準）
- W6B-7 callout 位置（bbox IOU assert 機械，遮擋與 dead space 選位最終靠全幀掃描人工確認）
- W6C-10 錄製紀律三條（靠 checklist 養成習慣；joint-diff SSIM 只能事後抓 GUI 不連續）
- W6C-12 SERP key moments 收錄巡檢（lint 機械、D+1 搜尋確認人工，併入既有 R36 巡檢）
