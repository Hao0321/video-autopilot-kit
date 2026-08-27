> **主責／路由**：需要可機械化數值的 fine-cut、留存、數據呈現與 2026 工具時讀本文；跨檔主寫分工見 [craft refs 索引](craft-index.md)。

# 剪輯技法 wave5 深研（2026-07-23）— 細剪 / 留存 / 數據呈現 / 2026 工具
#
# 四路平行深研 37 條【可量化可落地】規則，每條含：規則(帶參數) / 落地(對應 longform_maker 模組) / 機制 / 來源。
# 定位：長片03 細剪與下支片的技法真值來源；與 editing-techniques-2026.md 六路深研互補（該檔管 hook/pacing 基準，本檔管細剪執行層）。
# 使用：細剪前整份讀；落地時照「落地」欄指的模組動手（fx_lib/transitions/music_engine/script_gate/delivery_qa 都有具體掛點）。

> **現行執行契約（2026-08-27）**：所有「落地」先編譯成 `hao.video-autopilot.edit-plan/v4` structured commands（含 evidence、時間界線、參數與品質斷言），再由 `workflow_contract.py` audit → accepted receipt → atomic apply → committed receipt → render → delivery QA → human/outcome receipt。模組或 media primitive 只能由 plan 呼叫，不能成為旁路。

## TOPIC: retention

### 1. 開場 30 秒鎖三段結構：0-5s 視覺+聲音 pattern interrupt（冷開場，比靜態開場留存 +23%）、5-15s 講出具體 payoff（15s 內給 value claim 的腳本 52% vs 44% 留存，1 分鐘點留存 +18%）、15-30s 種 information gap/證據。7 種開場死法（打招呼、頻道 bumper>3s、『這支影片我們要…』meta 話、鋪陳>10s、道歉、先要訂閱、『你有沒有想過』）全砍 = +4-10pp
落地: script_gate R24 加機械檢查：第一句 regex ban 7 種開場死法；前 15s 旁白必含 payoff 名詞。build 端：0-5s 用最強真後台截圖（M107 proof stage）+ fx_lib 雙 bloom 閃現當冷開場，5s 內至少 1 個 SFX 事件（music_engine 排點）
機制: 頭 60 秒流失 55%+，8 秒是決定窗口；開場曲線 100%→65-80% 是常態，每早 1 秒給 payoff 都直接墊高整條曲線的天花板（Hao 頻道瓶頸正是留存）
來源: prepublish.ai/guides/first-30-seconds + Retention Rabbit 2025 benchmark + virvid.ai faceless 2026

### 2. 5 秒靜止掃描 gate：全片任何 5 秒窗口內至少 1 個視覺事件（cut/zoom/字幕行變/圖表 reveal）；不露臉旁白片視覺變化目標 3-5s 一次、通用 b-roll 插入 1-2s 短切；但『大』interrupt（zoom+whoosh 級）壓在每 30-60s 一次即可 —— 30-60s 節奏的中段留存 +25%，35 歲以上觀眾被每句 zoom+whoosh 轟炸反而留存變差
落地: delivery_qa 加 static-window gate：parse build_video 的事件時間軸（b-roll 切點、KB keyframe、caption 行變、fx_lib 事件）→ 任何 ≥5s 零事件窗口 = flag；同時 cap『大 interrupt』密度 ≤2/分鐘（教學觀眾偏 35+，不學 Gen Z 2-3s 轟炸）
機制: faceless 片沒有臉部微動作當天然視覺刺激，靜止 5 秒=注意力漂走；但教學觀眾要的是資訊節奏不是特效節奏，過度剪反而掉——頻率分層（微變化密、大干擾疏）同時解兩頭
來源: etwell.studio 5-Second Rule + framesail.com faceless 3-5s + Backlinko(經 pixflow 引) 30-60s +25% + AIR Media-Tech 35+ 警告

### 3. Payoff 節拍器：每 90 秒觀眾必須拿到一個具體東西（事實/技巧/類比/小 reveal）；re-hook 每 2-3 分鐘一枚（tease『等你看到第 X 分鐘那個數字』/ 直問觀眾 / 回扣開頭懸念），且在全片 50% 與 65% 位置各排一枚 forward-hook —— >10min 片在 55-65% 處有 15% 的第二波集體出走
落地: script_gate 加 payoff 節拍檢查：用 CPS 估時，每 90-120s 旁白必須命中一個 [PAYOFF] 或 [REHOOK] 標記，缺=block；build 端 50%/65% 兩點用 brand_templates 問號卡/stat 卡做視覺化 tease（配 M106 固定字槽 counter 顯示『還剩 X 個坑』）
機制: 中段流失不是均勻滲漏是斷崖：觀眾在 50% 問自己『還要看嗎』，沒有即時給糖+預告後面更甜就走；tease 過量會被學會忽略，所以 cap 在每 2-3 分鐘
來源: framesail.com 90s payoff + 50-75% forward hooks + Retention Rabbit 55-65% exodus + rivereditor.com rehook 型態學

### 4. 章節卡 = 逃生門，要封死：章節卡上鏡 ≤2s、BGM 與旁白絕不在卡上斷（旁白 L-cut 壓卡繼續講）、每段最後一句必須是下一段的 tease 而非本段總結；中段禁用『總結/回顧/最後/以上就是』等收尾詞（只准出現在最終 30s）。留存圖上任何 ≥4pp 的 dip = 必修
落地: brand_templates 章節卡 duration 參數鎖 ≤2s；build_final 確保 music_engine 能量弧跨章節連續不歸零；script_gate 加 finalizing-words ban list（白名單=片尾）；Log Outcome mode 加『逐 dip 對時間軸、≥4pp 記錄成因』checklist
機制: 觀眾在段落邊界批量離開——section 結束的『完成感』就是離開訊號；聲音連續+語意 tease 把邊界縫起來，觀眾感覺不到可以走的節點。YT chapters 功能照留（搜尋槓桿），但片內的視覺章節卡不能製造停頓
來源: pixflow.net seam-hiding/no flat landings + foxtalkxstudio.com dip 成因 + prepublish.ai dips ≥4% 警戒線

### 5. Open loop 要視覺化釘住：開場丟的懸念必須有畫面錨——編號結構（『3 個坑』counter 卡逐段打勾）讓觀眾看得到離 payoff 多近；最強畫面先剪 1-2s 到冷開場閃現再標『稍後』；清單型內容最後一項不標號（藏住片尾位置）
落地: fx_lib 固定字槽 counter（M106 現成）改造成 step-counter overlay，每章節開頭 tick 一格；build_video 開場插 1-2s 的後段高光 flash-forward（從已渲染 scene 直接抽，零額外素材）；腳本層清單最末項去編號
機制: 純口頭 open loop 會被忘記，視覺進度標記讓『快到 payoff 了』持續可感=沉沒成本效應；藏住結尾讓觀眾無法計算『看到哪就可以走』
來源: tubebuddy.com open loop 15s+ 效果 + pixflow.net narrative loop/最後一項不編號 + overseeros.com progress markers

### 6. 靜默間隙 ≤0.5s + 句長瘦身：旁白句間 silence 全部壓到 0.5s 以下（整片縮 5-10% 時長）、平均句長 <15 英文字（中文對應 ≤22 字）——同樣內容片長變短，留存百分比機械性上升
落地: build_audio 在 M103 音訊鏈前加 gap-normalizer pass：silencedetect 抓 >0.5s 間隙 → 收緊到 0.35-0.5s（保留換氣感）；yt-script-style lean pass 已砍 20-25% 贅詞，再加句長 lint：>22 字的句子標黃要求拆句
機制: AVP 是分數：分母（片長）每省 1 秒，分子不變留存就漲——這是 Hao『AVP 33.9% 純片長問題』最便宜的直接槓桿，比加特效有效且零風險
來源: framesail.com gap normalization 0.5s + sentence <15 words 5-10% runtime cut

### 7. 結尾防衰減：最後 20s 旁白持續講話壓著 end screen 走（不留告別真空）；訂閱 CTA 移到第一個大 payoff 之後（約 25-35% 處）且 ≤5s，片尾不再乞求；最終章不出現能量下垂的 wind-down 語氣
落地: Hao 片尾三件套保留但重排：end screen 安全區最後 20s 旁白照 CPS 排滿（推薦下一支的口播理由）；script_gate 把 CTA 標記限制在 25-35% 區間一次 + 時長 ≤5s；彩色 outro 卡壓縮進這 20s 內不另佔時間
機制: 平均只有 16% 觀眾活到最後 10 秒——片尾每一秒的留存權重低但『按到下一支』的轉化權重高；CTA 放在剛收到價值的高點轉化率最高，放片尾等於對空氣講
來源: pixflow.net ending strategy + Retention Rabbit 16% 終點存活率

### 8. 上架後 48-72h 留存急救：讀 YT Studio intro 留存，30s 點存活 <70% 就用 YouTube 內建編輯器直接剪掉開場肥肉——實案：砍 27s 鋪陳（0:38→0:11 進正題）讓早期斷崖曲線變平；教學 how-to 天花板是 42.1% 平均留存（全 niche 最高），10-20min 目標帶 35-45%
落地: video-autopilot Log Outcome mode 加機械 checklist：D+2 讀 first-30s survival → <70% = 列出 YT editor trim 方案（精確到秒）給 Hao 執行；同時把 42.1%/35-45% 寫進 baseline memory 當 AVP 對照系
機制: 留存不是上架就定生死——YT 編輯器 trim 不換 URL 不損既有數據，等於免費 A/B 第二回合；Hao 長片 01 的 33.9% 距 niche 帶 35-45% 只差 1-11pp，開場 trim 是最快的追趕手段
來源: georgeblackman.substack.com Retention Review #7 實案 + Retention Rabbit 42.1% educational benchmark

SKIP: Gen Z 2-3s interrupt 轟炸節奏（Joyspace）— Hao 教學觀眾偏成人，AIR Media-Tech 實測 35+ 觀眾被每句 zoom+whoosh 反而留存更差；已折衷進 rule 2 的分層頻率 / MrBeast 式『10 cuts in 10 seconds』hyper-editing — 娛樂片文法，教學片會毀可信度與 35+ 留存；Hao 的 cuts≥12/min baseline 已是教學片合理上限 / 畫面內燒死 progress bar（SubtitleBee）— 證據弱且多為廣告/Shorts 場景；YT 播放器本身已有進度條+chapters，長片再燒一條=雜訊。改採 rule 5 的 counter 卡替代 / talking-head 換機位/臉部 punch-in 型 pattern interrupt — Hao 不露臉（M78 RETRACT），N/A；等效刺激已由 zoom/圖卡/字幕行變覆蓋 / meme 插入當 interrupt — 與 Hao 白字極簡 brand（M68/white-first）和教學調性衝突 / 拿掉 chapters 換 AVD — chapters 會因跳段拉低連續 AVD，但拉高 total watch/impression 與搜尋入口（Hao 五槓桿之一），淨值為正，保留不動；只修片內視覺章節卡（rule 4） / AI 配音 pause-tag 優化 — Retention Rabbit 實測 AI 旁白前 45s 多流失 35%，Hao 自錄真聲（M101）本身就是留存優勢，維持不變 / Shorts 15-25s loop 結尾機制 — Shorts 專屬，與長片留存無關，出界

## TOPIC: dataviz

### 1. 真截圖上鏡走 4 拍 staging：全景 1.5-2s → cue（ring/spotlight）→ punch-in 1.3-1.5x → 回全景；zoom 後定格 ≥2.5-3s 才夠手機讀清
落地: longform_maker 加 proof_stage() 序列 helper：fx_lib 亞像素 KenBurns 做 push（0.6-0.8s ease-out 到 1.35x）；zoom 前先 hold 原圖 1.5s 讓觀眾定位；配 M107 真後台截圖直接套用。delivery_qa 加 gate：proof scene zoom 段 <2.5s 就 flag
機制: 先全景再特寫防止觀眾 close-up 後迷失（full→cue→zoom→return 是 tutorial 業界標準 pattern）；新聞級 receipts 指南實測手機觀眾需要 2-3s 定格才能處理證據內容，太短=證據白放
來源: gazzetta.xyz/youtube-playbook + capcut.com zoom-effects guide

### 2. 第一張 proof 截圖必須在 0:20-0:30 內上鏡（過 trust gate），因為 55%+ 流失發生在第一分鐘
落地: script_gate（錄前 R24 機械檢查）加一條：sheets 排程裡 scene1/scene2 必含 proof asset，否則 BLOCK；Hao 的冷開場模板直接內建「真後台數字先亮相」slot
機制: 教學/賺錢類內容觀眾預設懷疑，證據出現前就走人=後面剪多好都沒用；把 receipt 提前到棄看高峰（25-35s）之前是留存+可信度雙修
來源: gazzetta.xyz/youtube-playbook + pixflow.net/blog/youtube-video-retention-editing

### 3. 數字揭示 timing = 對齊「講到那個數字的字」的 word onset：動畫在旁白唸到該元素的第一個字起跑，counter 落地必須在該句結束前，絕不能晚於字幕出現
落地: word_captions.py 已有 whisper 字級時間戳 → 直接把數字詞的 onset t 餵給 fx_lib counter/stat 卡的 enable='gte(t,X)'；驗收條件：onset ≤ 動畫開始 ≤ onset+0.3s，且 counter_end ≤ 句尾時間
機制: Data Player（arXiv 2308.04703）從 pro data video 提煉的機械規則就是「animation triggered by onset of first word of linked narration segment」；DataReel benchmark 列「動畫比字幕晚出現」為觀感頭號缺陷
來源: arXiv 2308.04703 (Data Player) + arXiv 2604.25220 (DataReel)

### 4. counter 數字動畫：時長 2-4s、ease-out 減速落地、每幀增量 ≤2% 總值（30fps 下時長 ≥1.7s 否則眼睛讀成卡頓）
落地: fx_lib M106 固定字槽 counter 把 duration 參數鎖 2.0-3.0s 預設、easing 用 expo-out；加 assert：total_value/(duration*fps) 不得讓單幀跳動超過 2% 總值，超了自動拉長 duration
機制: count-up 的「時間成本」給觀眾數字量級的體感（embodied understanding）；減速落地把重音放在最終值；每幀跳太大人眼判定為 stutter，質感直接掉回業餘
來源: videocaptions.ai/motion-elements/number-counter-animation

### 5. 證據鏡頭停留公式：3s 基底 + 每個需讀的字 0.5-0.7s；底線 13 chars/sec（Netflix 標準）；單一大數字也 ≥2.5s
落地: build_video 加 min_dwell(text) helper：scene duration = max(3 + 0.6*word_count, len(chars)/13)；stat 卡/截圖 annotation 的文字量直接算進 sheets 的 scene 秒數；delivery_qa 掃到低於公式=flag
機制: 螢幕閱讀速度只有 110-125 wpm（比紙本慢 25%）；停留不足觀眾要嘛倒帶（傷 AVD 曲線觀感）要嘛放棄理解（傷滿意度）——Hao 瓶頸正是留存
來源: ssw.com.au/rules/post-production text-timing + legibility.info + Netflix Timed Text Style Guide

### 6. 多數字對比 = 逐一揭示再併排：A counter 2-3s → B counter 2-3s → VS 併排 hold ≥2s + 差值徽章（如「8x」）在旁白講到比較詞時第三拍彈出；禁止兩個 counter 同時跑
落地: brand_templates 的 vs_card 已存在 → 加 stagger 參數：兩側 counter 的 start 分別綁各自旁白段 word onset；delta badge 用第三個 enable 時間點；一個畫面同時活動的數字動畫 ≤1
機制: DataReel 對 pro data reels 的動畫策略統計：emphasis 44.3% + suspense/延遲比較 36.4% 佔絕對主流，同步揭示只佔小頭；同時跑兩個 counter 分裂注意力，逐一揭示製造微懸念（每個揭示都是一次 re-hook）
來源: arXiv 2604.25220 (DataReel animation strategy distribution)

### 7. 證據上鏡時旁白必須「講它」且邏輯壓進一句話：主張 → 截圖顯示什麼 → 所以結論；zoom 拉回全景那 0.5-1s 重述結論一句
落地: script_gate 加 R 檢查：每個 proof b-roll 對應的旁白 block 要能 parse 出「claim→shows→so」三段；結論句在 word_captions 走重點色（palette[0]，符合 white-first ≤2 色鐵則）
機制: 長篇溯源獨白是留存殺手；「一句話邏輯」讓 receipt 讀起來是決定性的而非炫耀性的——證據自己不說話，旁白同步導讀才轉化成信任
來源: gazzetta.xyz/youtube-playbook

### 8. terminal/code demo 上鏡：字級 ≥16px（1080p 下 16-18）、行寬鎖 80-120 字元、打字段落加速 1.5-2x、驗收=手機上讀得清
落地: OBS 錄製 profile 固定 terminal/editor fontSize 16-18；screen_clean.clean_screen_recording() 後接一步：打字/等待段用 setpts=PTS/1.5~2.0 加速（手標 in/out 或偵測無旁白段）；QA 加「抽 1 幀縮到 375px 寬檢查 code 可讀」
機制: 預設 12-14px 經 YouTube 1080p 壓縮後不可讀（大量觀眾用手機看教學）；live typing = 死空檔（M95 的特化案例），加速保留真實感又不耗留存
來源: dev.to/egghead recording-a-great-coding-screencast + screenify.studio + ngram.com demo guide

### 9. dashboard/terminal 長段落的畫面變化節奏：每 5-7s 一個 micro 變化（新 highlight ring/annotation pop/zoom 一階）、每 30-60s 一次格式切換（stat 卡/B-roll/全景）——這是 shot 內變化，疊在 cuts≥12/min 之上
落地: build_video 加 rule：任何靜態截圖 scene 超過 7s 必須排一個 fx event（fx_lib ring/pop/push 二段）；delivery_qa 的 scene-pacing gate 擴充「靜態證據 >7s 無 fx = flag」；30-60s 格式切換寫進 sheets 排程模板
機制: cuts/min 只管鏡頭切換，教學片真正的留存殺手是「同一張截圖躺 20 秒」——within-shot 變化是螢幕錄影類內容維持注意力的主機制（55%+ 流失集中第一分鐘、之後每 30-60s 需 pattern interrupt reset）
來源: pixflow.net/blog/youtube-video-retention-editing

### 10. annotation 疊加順序固定 dim → ring → zoom，逐個進場、間隔 0.3-0.5s，不同時全上；spotlight dim = 目標區外亮度 -40~-60%
落地: fx_lib overlay chain 標準化：先 roundrect mask 外 brightness=-0.4（或 boxblur）、0.4s 後 3-4px 品牌色 ring 進場、再 0.4s 後亞像素 push；封成 spotlight_callout(x,y,w,h,t) 一行呼叫
機制: 當觀眾需要知道「元素在整個介面的哪裡」時 callout 優於直接 zoom；逐個進場引導視線路徑（先收攏注意力→再標定→再放大），一次全上=視覺爆炸找不到重點
來源: capcut.com zoom-effects-for-tutorial-videos + TechSmith spotlight-and-magnify

SKIP: Johnny Harris 式 GEOlayers 3/Google Earth Studio 地圖 zoom 動畫 — 依賴 After Effects 付費插件生態，ffmpeg 管線無法複製，且教學型內容用不到地理敘事；他真正可遷移的只有「push-in + 逐層 annotation」精神，已吸收進 rule 1/10 / 老高與小茉手法 — 核心是雙人 talking head 節奏+白板圖解，Hao 不露臉直接不適用；且 2026-06 網路對其影片的拆解焦點是疑似 AI 代拍的跳剪掩飾，無可正向遷移的數據呈現技法 / 志祺七七/圖文不符 資訊圖卡工廠 — 50 人團隊分工的日更產線（設計師畫卡+動畫師動態化），solo ffmpeg 管線無法複製其人力密度；公開資料查不到 per-card 秒數/數量的量化規格，只有組織論 / Screen Studio / OpusClip 自動 zoom+自動打字加速 SaaS — 付費 GUI 工具，功能可用 setpts + fx_lib 在自家管線複製（rule 8/9 已覆蓋），不引入外部依賴 / VS Code Screencast Mode 按鍵浮層 — Hao 的教學片是 agent 跑流程+旁白解說，非 live IDE 敲鍵教學，keystroke overlay 無用武之地；若未來做 live coding 再撿回（顯示時長 1.5-2.5s 的參數已留在 rule 8 來源） / 2560x1440 HiDPI 錄降 720p 的清晰度 trick — Hao 已有 OBS 1080p + M104 screen_clean crop 管線，重錄設定的邊際效益低於直接鎖字級 16-18（rule 8 已解同一痛點）

## TOPIC: tools2026

### 1. ffmpeg 直接升到 8.1 'Hoare'（2026-03-16 釋出），Windows 用 gyan.dev full build（2025-10-27 build 056 之後），一次拿到 af_whisper（build 055+ 內建 whisper.cpp）＋ vf_drawvg（build 056+ 內建 cairo）兩個新武器；升級後 build script 加機械 gate：`ffmpeg -hide_banner -filters` 必須同時 grep 到 `whisper` 和 `drawvg`，缺一 = fail-fast 不往下跑
落地: longform_maker 的 build_audio/build_video/build_final 共用一個 `check_ffmpeg_env()`（可放 fx_lib 或新 env_gate 模組），開頭跑一次 subprocess grep（記得 M102 cp950 encoding）；requirements 註記 pin『ffmpeg >= 8.1 full build』
機制: 8.0（2025-08-22）/8.1 是 ffmpeg 十年來最大改版；Hao 管線所有下游新技巧（原生 ASR QA、向量動態圖形）都建立在這兩個 filter 存在之上，env gate 殺掉『在舊版 ffmpeg 上默默跑出沒字幕/沒圖形的假綠』
來源: https://www.phoronix.com/news/FFmpeg-8.0-Released ; https://9to5linux.com/ffmpeg-8-1-hoare-multimedia-framework-brings-d3d12-h-264-av1-encoding ; https://www.gyan.dev/ffmpeg/builds/

### 2. 8.1 新 vf `drawvg`（cairo 向量繪圖 + VGS script，可用 t/w/h 表達式做動畫）接管 fx_lib 的進度條/底線/重點框/counter 裝飾層：向量 = 4K 無鋸齒、不再生成 PNG 序列中間檔；硬限制 = 每條 filtergraph 只准 1 次 drawvg 呼叫（所有向量層合併進同一份 .vgs），因為 cairo 強制 RGB 處理，每多一次 drawvg = 多一整輪 YUV↔RGB 全幀轉換
落地: fx_lib 加 `vgs_layer(template, params)`：從 brand_templates 的 .vgs 模板（進度條/underline/stat 框）填參數合成單一 .vgs，插在 filtergraph 最後 `format=yuv420p` 之前；現有亞像素KB/雙bloom 不動（那是像素級效果，drawvg 只吃『幾何圖形動畫』這塊）
機制: Hao 現在的動態裝飾若靠預渲染 PNG/複雜 drawbox 疊層，改 drawvg 後零中間檔、參數即改即渲，且表達式驅動 = 動畫時間可直接綁 word_captions 的字級時間戳（重點詞出現的那 0.1s 畫底線）
來源: https://ayosec.github.io/ffmpeg-filters-docs/8.1/ ; https://linuxiac.com/ffmpeg-8-1-brings-vulkan-compute-codecs-and-new-decoder-support/

### 3. 8.0 新 af `whisper` 定位 = 成片文字 QA gate、不是字幕來源：對 final master 跑 `-vn -af whisper=model=ggml-large-v3-turbo.bin:language=zh:queue=20:format=json:destination=qa_transcript.json:vad_model=silero-v5.1.2.bin -f null -`，把辨識文字 diff 腳本原文，抓漏剪的重錄段/漏念句；參數量化：batch QA 用 queue=20~30（大 chunk 上下文最準），vad_model 必開（防 BGM/靜音段幻覺字），large-v3-turbo GPU 約 2-3x 實時
落地: final_delivery_qa 加一個 `transcript_diff` gate：ffmpeg 一行跑出 json → python difflib 對 script sheet，容忍同音異字、超過 N 句缺失 = BLOCKED；注意 af_whisper 只有 segment 級時間，字級時間戳仍走 faster-whisper（M105 word_captions 不換引擎）
機制: Hao 現在『成片念了什麼 vs 腳本寫了什麼』只靠人耳+全幀圖掃，af_whisper 讓文字層也閉環機械化；segment 級精度不夠做字幕但綽綽有餘做 diff
來源: https://www.rendi.dev/blog/ffmpeg-8-0-part-1-using-whisper-for-native-video-transcription-in-ffmpeg ; https://webrtc.link/en/articles/ffmpeg-whisper-speech-to-text/

### 4. 字級時間戳 stack pin 死：whisperx>=3.8.6 + faster-whisper>=1.2.0 —— 3.8 系列（含 backport 線 3.7.9/3.6.2）修了『含數字/符號的詞（94.1%、$0.20、8k）拿不到對齊時間戳、被內插漂 1-3s』的 wildcard emission bug；升級後 word_captions 加 gate：輸出裡 interpolated/null 時間戳的詞數必須 = 0，wav2vec2 對齊後字級誤差 <100ms
落地: word_captions.py 的 requirements pin 版本；`check_caption_sync` 多一條 assert：任何 word 的 start/end 是 NaN 或來自線性內插 → red；Hao 的旁白全是戰績數字（M107 場景），這 bug 打的正是他最痛的詞
機制: M105 抓過『手猜長句切分漂 2-3s』，這是同一類病的引擎側殘留——數字詞在舊版對齊模型裡是黑洞；版本升級 + 機械 assert = 把最後一種漂移源殺掉
來源: https://github.com/m-bain/whisperX/releases ; https://github.com/m-bain/whisperX/issues/1334

### 5. word_captions 轉錄引擎換 faster-whisper `BatchedInferencePipeline`：batch_size=8（8GB VRAM 安全值，16GB 可 16），實測同 WER 下 ~4x 快，且 1.2.1 內建 Silero-VAD v6（比 v5 段界更準）；參數：`word_timestamps=True, vad_filter=True, batch_size=8`，模型用 large-v3-turbo（多語含中文，速度接近 distil 但不犧牲中文）
落地: word_captions.py 把 `WhisperModel(...).transcribe()` 換成 `BatchedInferencePipeline(model=...).transcribe(...)`，其餘 M108 斷句邏輯全不動；10-20min 教學長片轉錄從分鐘級壓到十秒級
機制: 轉錄快 4 倍 = 每次 build 迭代都跑得起完整 whisper pass（現在可能只在最後跑），QA 迴圈次數直接翻倍；VAD v6 順帶減少句首吸氣被算進字時間的誤差
來源: https://github.com/SYSTRAN/faster-whisper/releases ; https://pypi.org/project/faster-whisper/

### 6. auto-editor 31.3.x（2026-07 現行版，CLI/純 python）當死空檔機械預切刀：`auto-editor in.mp4 --edit audio:threshold=-30dB --margin 0.2s,0.4s --export json` 輸出 v3 timeline JSON 給自家 python 讀，不讓它直接出片；margin 不對稱是關鍵數字——切點前留 0.2s、後留 0.4s，保住呼吸尾巴不變機械槍
落地: longform_maker 加 `dead_air_carve.py`：呼叫 auto-editor 拿 JSON → 轉成自家 segment list → 現有 build_video 照 list 切；M95 dead-air gate 從『檢出報警』升級成『檢出+自動開刀』，人只 review JSON diff
機制: Hao 頻道瓶頸 = 留存，教學長片死空檔是留存第一殺手；-30dB/0.2s/0.4s 三個數字可直接進 profile 調參，且 JSON 中介 = 管線仍然 100% python 可審計
來源: https://pypi.org/project/auto-editor/ ; https://github.com/WyattBlue/auto-editor/releases

### 7. 螢幕錄影 demo 用 auto-editor 31.2+ 的區域動態偵測切無操作段：`--edit motion:threshold=2%:region=X:Y:W:H`，region 填 M104 screen_clean crop 後的內容區座標——只看軟體操作區的畫面變化，游標閃爍/通知彈窗在區外不誤判；threshold 2% 起跳，操作密集 demo 可拉到 4%
落地: screen_clean.clean_screen_recording() 之後、進 build_video 之前插 motion carve step，region 直接沿用 crop 參數（同一組數字兩用）；audio+motion 雙條件可用 31.0 的 `--edit`多 label 語法（最多 255 個）組合『沒聲音 AND 沒操作』才切
機制: 教學片最容易流失的是『畫面不動又沒話』的雙死段，單靠音量偵測會留下大量無聲但也無操作的廢秒；region 參數是 31.2 新貨，正好解掉全幀 motion 偵測在螢幕錄影上的誤判
來源: https://github.com/WyattBlue/auto-editor/releases

### 8. 管線順序鐵則：clean（M104）→ carve（auto-editor）→ transcribe（faster-whisper）→ caption（word_captions）→ QA（af_whisper diff）——任何在 whisper pass 之後對時間軸的剪動（哪怕 0.5s）= 全部字級時間戳作廢必須重跑 whisper；把這條做成機械檢查：build_final 記錄 video mtime vs 轉錄 json mtime，video 較新 = BLOCKED
落地: final_delivery_qa 加 `timestamp_freshness` gate：比對 final video 與 words.json / .ass 的產出時間鏈（或內容 hash 鏈），順序倒置直接紅燈；成本 = 幾行 python，殺掉的是最陰險的整片字幕漂移
機制: 引入 auto-editor 自動開刀後，『先轉錄後補刀』的誘惑會變大——這是 M105 漂移的新變種入口，用 mtime/hash 鏈在源頭封死，不靠記憶靠機械
來源: https://github.com/WyattBlue/auto-editor/releases ; https://github.com/m-bain/whisperX

### 9. 8.0 新 vf `colordetect` 進交付 QA：對 final master 跑一次，偵測到的實際 color range 必須 = 容器 metadata 標的 range（tv/limited 為準），不一致 = BLOCKED——range 標錯是 YouTube 上『整片發灰/死黑』最常見成因，且全幀圖掃描肉眼常看不出輕度 washed-out
落地: final_delivery_qa 加 `color_range_gate`：`ffmpeg -i final.mp4 -vf colordetect -f null -` 解析 log 輸出 vs ffprobe 的 color_range tag，兩值不等即紅；與現有全幀掃描互補（機器抓 range、人眼抓內容）
機制: Hao 的 grade_lib 6 looks + LUT 鏈一多，中間某步 full/limited 混掉的機率隨之上升；這是 8.0 才有的免費機械檢查，一行指令換一個以前只能靠肉眼+運氣的 gate
來源: https://github.com/FFmpeg/FFmpeg/blob/master/Changelog ; https://www.phoronix.com/news/FFmpeg-8.0-Released

SKIP: CapCut 2026 AI Auto-Edit / AI Effect Engine（自然語言生效果）：無 API 無 scripting、只能 GUI 內用，進不了純 ffmpeg/python 管線；且 auto-edit 的審美是通用短影音風，會蓋掉 Hao 白字/三恆定 identity（M68/M77 integrate-not-replace） / CapCut 2026 字幕引擎（100+ 語言、code-switching 即時翻譯）：字級資料鎖在 app 內導不出乾淨 JSON，Hao 的 word_captions.py + M108 斷句已機械化且更可控；教學長片線不碰 CapCut（M42 適用範圍外） / CapCut Seedream 5.0 Pro / Seedance 2.0 生成圖影（2026-07 上線）：教學片 proof/b-roll 鐵則是真截圖真錄影（M10/M107 自繪=誰會信），生成素材直接違反；且生成圖靜止規則🚫已封死這條路 / CrisperWhisper / faster_CrisperWhisper（SOTA 字級時間戳+verbatim）：訓練重心英/德語，中文旁白無增益；verbatim 保留um/uh對照稿式旁白毫無用處——Hao 是照稿念+重錄文化（M101），whisperX wildcard fix 已解決他真正的痛點 / auto-editor 31.3 內建 NVIDIA Parakeet / Apple SpeechAnalyzer 轉錄：Parakeet 無中文、SpeechAnalyzer 是 macOS-only；Hao Windows+中文旁白兩頭都不沾，轉錄繼續走 faster-whisper / stable-ts：repo 已於 2026-05-30 archive 轉唯讀——任何新依賴都不准建在上面；時間戳精修需求由 whisperX(>=3.8.6)+faster-whisper 這條活路承接 / FFmpeg 8.1 D3D12 H.264/AV1 硬編碼 + Vulkan compute codec 群：主要惠及 AMD/Intel 顯卡路徑；Hao 若走 NVENC 輸出品質/速度無實質提升，YouTube 交付的 x264 slow 檔更不受影響——升 8.1 的理由是 drawvg 不是編碼器 / AutoCut 2026-06 更新（9x 靜音分析、59x 轉錄）：Premiere/DaVinci 付費插件——Hao 已淘汰 DaVinci、教學長片不走 NLE 插件路線；同能力由開源 auto-editor CLI 覆蓋 / FFmpeg unreleased <next>（latticepal filter / 大改 AAC encoder）：還沒釋出、不進 pin；等進 8.2 正式版再評估

## TOPIC: finecut

### 1. 雙模式節奏波（教學片專用 cutting pattern）：把每個 scene 標成 fast（解說模式：每 3-5s 一個視覺事件、micro-cut 每 10-15s）或 focus（展示模式：demo/範例畫面可 hold 最長 40s 不切）— 全片交替成波形，不是恆定 cuts/min。前 30s 例外：接近連續變化（頂級創作者前 30s 平均 ~19 次 shot change）。
落地: build_video 的 scene sheet 加 pacing_mode 欄（fast|focus）；delivery_qa 的 scene-pacing gate 升級：fast 段任何靜止畫面 >4s = fail，focus 段 hold >40s = fail，且全片 mode 序列不得連續 3 個同 mode（機械檢查波形不平）。這取代「cuts≥12/min 單一目標」— 12/min 只算 fast 段的下限。
機制: AIR 分析 100 個長片頻道，top 25% AVD 頻道的共通點是 fast/slow 交替而非恆快；觀眾第一分鐘內就學會你的節奏，恆快=麻痺、恆慢=流失；focus hold 讓教學內容真的被讀懂（Hao 瓶頸=留存，AVP 43%，理解不足=跳出）。MrBeast 2024 親口放慢節奏後觀看數反升，2026 共識=pace serves story。
來源: https://air.io/en/youtube-hacks/advanced-retention-editing-cutting-patterns-that-keep-viewers-past-minute-8 ; https://www.retentionrabbit.com/blog/ultimate-guide-youtube-audience-retention ; https://www.tubefilter.com/2024/03/04/mrbeast-editing-style-number-of-cuts-per-video/

### 2. J/L-cut 帶數字版：段內 b-roll 切換全走 L-cut 邏輯（旁白=連續床、畫面自由切）且畫面提前旁白關鍵詞 3-5 frames（0.1-0.2s）進場；章節邊界改 J-cut：下一章第一句旁白提前 0.5-1.0s 壓在上一章收尾畫面上。偏移 cut 佔比 ≤30%，其餘 70% 仍卡句尾（M87 baseline）。
落地: build_final 讀 word_captions.py 的字級時間戳：b-roll offsets 契約加 lead_frames=-3~-5（畫面先到、聲音點名）；章節邊界在 voice 軌 concat 時把下章首句 start 提前 0.5-1.0s 與上章尾畫面重疊（audio_chain 已有 LEAD_PAD 契約，加 chapter_jcut_lead 參數）。check_caption_sync gate 加白名單：這些 deliberate offset 不算漂移。
機制: 聽覺先於視覺引導注意力 — J-cut 讓耳朵先宣告新主題、眼睛才確認，章節換場不產生「重開機感」；全部同步剪（straight cut）= 觀眾每次都意識到剪接點，錯開 = 剪接隱形。30% 上限防止全片糊成一片失去節拍感。
來源: https://cutfa.st/en/blog/j-cut-l-cut-audio-transition-editing-cutfast-method-2026 ; https://tokcount.com/blog/14-micro-cut-transitions-that-keep-completion-rates-above-60-percent (#3 L-Cut Quick-Hit 3-5 frames) ; https://www.techsmith.com/blog/how-to-edit-videos-l-cuts-and-j-cuts/

### 3. 句尾 5-6 割規則（Naokiman jet-cut）：句間 cut 不等最後一個音節唸完 — 尾音節發聲到 50-60% 就切進下一句；句間 gap 機械壓到 0.2-0.35s，>0.5s 的停頓全刪（每章保留 1 個刻意 dramatic pause 當對比）。
落地: audio_chain 的 silence trim 從「刪死空檔」升級成「壓縮到目標值」：偵測句尾 word 的 end timestamp（word_captions 已有字級時間），gap = next_start - prev_end，>0.35s 的裁到 0.25s；whisper 尾音節時長 ×0.55 作為裁點近似 5-6 割。dramatic pause 用 scene sheet 白名單標記跳過。
機制: 日系解說片實測的緊湊感來源：尾音收 50-60% 時聽感完整但零拖尾，比「刪整段靜音」更進一步 — 觀眾感覺 momentum 不斷。AI/自錄旁白的 >0.5s 停頓是 micro-dead-zone，全刪可縮片長 5-10% 且 perceived pace 上升（Hao 3min 片只被看 43% — 每 0.3s 拖尾累積起來就是分鐘級浪費）。
來源: https://note.com/ainoarukurashi/n/nc52c7502f37a (ナオキマン 文節尾 5-6割) ; https://fluxnote.io/guides/faceless-channel-retention-strategies-2026 (0.5s pause rule)

### 4. 同源畫面 30% 變化率：同一段螢幕錄影內的跳剪，前後 frame 必須變化 ≥30%（zoom 州切換 100%↔≥130% 或 reframe）；強調 punch-in = 100→115% 用 4 frames 快打在關鍵詞的重音子音上；zoom-out reveal = 150→100% 用 10 frames（細節→全貌）。
落地: fx_lib 加三個 preset：punch_in(scale=1.15, frames=4, anchor=word_timestamp)、reveal_out(from_scale=1.5, frames=10)、jump_guard(assert 相鄰同源 clip 的 scale 差 ≥0.3)；punch 觸發點直接吃 word_captions 的重點詞 timestamp（P/B/T/K 硬子音前 1-2 frames 下刀）。delivery_qa 加 jump_guard 掃描：同源相鄰段 scale 差 <30% = warn。
機制: 30% 規則 = 30-degree rule 的螢幕錄影版：變化不足的同源 cut 讀作 glitch 而非剪接；4-frame 快 punch 有「physical snap」動能、把視覺重音跟語音重音焊在同一拍（子音爆破+畫面跳變 = 一個 percussive beat，剪接點隱形化）。
來源: https://www.brightonwestvideo.com/blog/subscriber-nation/edit-jump-cuts-video/ (30% rule) ; https://tokcount.com/blog/14-micro-cut-transitions-that-keep-completion-rates-above-60-percent (#2 Consonant Snap 1-2f / #6 Push-In 115%/4f / #11 Zoom-Out 150→100%/10f) ; https://en.wikipedia.org/wiki/30-degree_rule

### 5. 靜態截圖反 slideshow 事件預算：每張靜圖段的動態事件數 = ceil(時長/4s)，事件三選一輪替：(a) inset zoom — 1440p 源用 2x、UI 已可讀用 1.5x、3x 只配 4K 源，zoom 過渡 350-500ms ease-in-out，落點 hold 0.8-1.2s（要讀字 1.5-2s）；(b) annotation reveal — 框/底線/highlight 卡在對應詞的字級時間戳出現，不在 shot 開頭一次全出；(c) KenBurns（已有）只算保底不算事件。zoom 事件密度上限：每 3-4s 最多 1 次。
落地: fx_lib 加 event_budget(duration) helper 回傳事件時間點；annotation reveal 走 brand_templates 的 stat 卡/lower-third 同款 drawbox+fade 管線，start_time 綁 word_captions timestamp；inset zoom 用 crop+scale+zoompan 的 350-500ms easing（現有亞像素 KB 引擎改參數即可）。delivery_qa 全幀掃描加規則：靜圖段連續 4s 無事件 = fail。
機制: 「畫面每 3-5s 要有一個視覺變化」是教學片留存底線，但關鍵是變化要資訊性（annotation 跟著旁白詞出現 = 雙通道強化，資訊留存 +65%）而不是裝飾性亂動；zoom 參數錯 200ms 或用錯 easing 就從 cinematic 變 glitch — 這組數字是 slideshow 和 pro 的分界線。
來源: https://www.screenify.studio/blog/2026-04-10-auto-zoom-screen-recording (全部 zoom 參數) ; https://fluxnote.io/guides/faceless-channel-retention-strategies-2026 (3-5s 變化 + 65% dual-channel) ; https://tokcount.com/blog/14-micro-cut-transitions-that-keep-completion-rates-above-60-percent (靜止>4s 檢查表)

### 6. 數據卡 count-up 規格：counter 動畫 2-4s、easing 收尾減速落在最終值上；per-frame 數值增量要小到不讀作跳動（jumpy 就拉長 duration）；一卡一數字；SFX 綁在 motion beat（zoom 起點/counter 落點/文字 reveal）不隨機撒。
落地: brand_templates 的 stat 卡（M106 固定字槽 counter 已有）鎖參數：duration 2.5s 預設、ease-out quad 收尾；asset_forge 的 12 個 SFX 對映表加規則欄：whoosh→zoom 起點、pop→annotation 出現、ding→counter 落點，build_final 自動按事件表插 SFX（時間戳來自 fx_lib event_budget）。
機制: 動畫化的數據狀態轉移實證提升注意力和回憶（animated transitions improve attention and recall）；減速落點製造「satisfying landing」把視線釘在最終數字上 — Hao 的 proof stage（真截圖戰績）配 count-up = 可信度×衝擊力同時最大化；SFX 綁 motion = 聽覺確認視覺事件，亂撒 = 噪音。
來源: https://www.videocaptions.ai/motion-elements/number-counter-animation ; https://www.headout.studio/numbers-in-motion-our-animated-counter-tool-for-decks-2/ ; https://pixflow.net/blog/youtube-video-retention-editing/ (SFX tied to motion beats)

### 7. 轉場語意表（機械可查）：段內一律硬切（≥90% 的接點）；章節邊界才准 1 個 motivated 轉場 — 主題/場所變=wipe/whip/slide、時間流逝（渲染中/隔天）=短 dissolve（dissolve 長度∝時間跨度）、鑽進細節=zoom-through；每章非硬切轉場 ≤1 個，且 BGM 段落切換必須跟章節轉場同幀（雙通道宣告新章）。
落地: transitions.py 已有語意轉場 cap — 補上 semantic_map dict：{chapter:"wipe|slide", time_skip:"dissolve(0.5-1s)", drill_down:"zoom_through", default:"hard_cut"}，scene sheet 的 transition 欄只准填語意名不准填效果名（強制先想意義）；music_engine 的 BGM 能量弧切換點對齊 chapter transition 時間戳（現有 beat 卡點引擎讀同一張表）。delivery_qa 數轉場：任一章 >1 個非硬切 = fail。
機制: 轉場是語法不是裝飾 — dissolve=時間、wipe=空間/主題、cut=同場景延續，用錯 = 觀眾潛意識收到錯誤訊號（以為換主題結果沒換=困惑=跳出）；音樂+視覺同幀換場 = 結構感，觀眾能感覺「進度條在走」（feeling of progress toward payoff），這是長片撐過 8 分鐘的核心。
來源: https://www.studiobinder.com/blog/types-of-editing-transitions-in-film/ ; https://www.descript.com/blog/article/video-transitions ; https://etwell.studio/blog/high-retention-editing-what-it-is-and-how-to-get-it (music at structural transitions)

### 8. Pattern interrupt 時刻表：第一個刻意 interrupt 放 25-35s；之後每 30-60s 一個 major reset（格式切換：旁白→demo/提問/case，不是換 b-roll 就算）；長片在 ~3min 和 ~6min 硬排 re-engagement peak（新 proof/轉折/payoff）；50% 進度點排一次格式大切換（第二大流失群聚點）。
落地: script_gate.py 的 R24 錄前檢查 + interrupt 排程已有骨架 — 加時刻表驗證：腳本分段標 interrupt_type 和預估時間戳，gate 檢查 25-35s / 每 30-60s / 3min / 6min / 50% 五個槽位有沒有填；build 後 delivery_qa 對照實際成片時間軸驗證落點誤差 <10s。Hao 片長 3-5min：至少 25-35s + 50% + 尾段三槽必填。
機制: 注意力在無變化時自然衰減，準時 reset = 把留存曲線的斜率一次次拉回；25-35s 是早期流失窗（前 30s 流失 >33%）的收尾防線；MrBeast 團隊 production guideline 明文 3min/6min 工程化 re-engagement——Hao 長片01 AVP 33.9% 純片長問題，這張時刻表就是留存瓶頸的直接解。
來源: https://pixflow.net/blog/youtube-video-retention-editing/ (25-35s / 30-60s) ; https://www.washingtonpost.com/technology/2024/03/30/video-editing-mrbeast-retention/ + https://vidpros.com/mrbeast-thumb-and-video-editing-style/ (3min/6min re-engagement) ; https://fluxnote.io/guides/faceless-channel-retention-strategies-2026 (50% midpoint interrupt)

### 9. 3-frame flash / 6-8 frame text-pop 微型武器：強調點用 3 frames 的 b-roll flash（閃光燈效應）；要遮爛 cut 或打重音時用單詞 text-pop 6-8 frames 佔半屏；兩者全片各 ≤2 次。
落地: fx_lib 加 flash_insert(clip, frames=3, at=word_timestamp) 和 text_pop(word, frames=7, coverage=0.5)——text-pop 走 M68 白字黑框樣式不另開多色；用量計數進 delivery_qa（>2 次 = warn，防止變 TikTok 病）。放在 proof 數字揭曉、關鍵結論兩類時刻。
機制: 3-frame 閃 = 視覺 flashbulb，觀眾意識不到內容但注意力被重置；半屏單詞 = 認知負載瞬間全轉去閱讀那個詞，cut 的瑕疵直接隱形——是「重音符號」不是「節奏本體」，超量就從 pro 變 spam，所以帶用量上限。
來源: https://tokcount.com/blog/14-micro-cut-transitions-that-keep-completion-rates-above-60-percent (#8 Text-Pop 6-8f / #10 B-Roll Flash 3f)

### 10. B-roll 兩軸定位法：每段 b-roll 先分類 sequential（過程鏈：步驟 demo，3-7s/clip 順時序排）或 illustrative（單獨意象：情緒/氛圍，垂直對齊壓在確切關鍵詞正上方）；illustrative 進場點 = 關鍵詞 timestamp，不是句子開頭。
落地: v4 plan 的 material semantics + `broll_qa.py`（M87）用兩軸 assurance：b-roll manifest 加 axis 欄（sequential|illustrative），sequential 檢查時序連貫（前 clip 出點動作方向≈後 clip 入點），illustrative 檢查進場時間 = word_captions 關鍵詞 timestamp ±0.2s（不是 caption 句首）；audit receipt 必須保存兩軸結果，render 後再以抽幀複核。
機制: 專業紀錄片剪輯的核心分野：sequential 講「流程在推進」、illustrative 講「這個詞的畫面證據」——混著排 = 觀眾抓不到敘事線；illustrative 壓在詞正上方（editors place locators at each evocative line）= 旁白跟畫面焊死，教學片的「聽到什麼就看到什麼」是理解度=留存的地基。
來源: https://www.insidetheedit.com/blog/b-roll-editing-structure (兩軸框架) ; https://riverside.com/blog/b-roll (3-7s clip 時長)

SKIP: Axis Shift（第二 clip 放大 15% + 移到三分線交點重構臉部構圖）、Hand-Drop Wipe（手遮鏡頭換場）、Mic-Tap Cut — 全是 talking-head/vlog 技巧，Hao 不露臉（M78 RETRACT）無臉可重構、無實體鏡頭可遮 / Cursor-follow 連續跟隨 zoom（viewport 持續漂移跟游標）— 暈眩風險高且 Hao 螢幕錄影已走 screen_clean crop 管線；click-triggered 離散 zoom（已納入規則 5）才適合教學片 / Glitch Skip（刪 3 frames 製造故意跳針/CD scratch 感）— chaotic energy 美學跟教學片可信度衝突，Hao 的 proof-driven 內容不能有「壞掉感」 / MrBeast 舊式 60 cuts/min 超高密度剪法 — MrBeast 本人 2024 已公開撤回（放慢後觀看反升）；教學長片需要 comprehension hold，恆定高密度反而傷留存 / 全面去呼吸聲（debreath 全刪）— Hao 自錄旁白（M101），全刪呼吸會變 AI 感/扁平；只壓 >0.5s 停頓（規則 3 已含），語意內呼吸保留 / FocuSee/Cursorful/Screen Studio 等 auto-zoom 成品工具 — Hao 有自己的 ffmpeg/python 管線，抄它們的參數（已萃取進規則 5）不抄它們的工具 / 日系テロップ多色/多位置規則（varietytelop 等）— 跟 M68 白字黑框 + white-first 鐵則直接衝突，Hao 已有更嚴格的字幕系統 / 「Coming up next」每 60-90s 口播內部鉤子 — 這是腳本層不是細剪層，且 Hao 的 script_gate/yt-script-style 已管腳本結構；細剪階段硬插會破壞 lean output 偏好 / Negative Space Jump（複製 clip 遮罩主體錯位疊影）— 需要人物主體做遮罩分離，螢幕錄影+數據卡素材無主體可分離，且 bizarre jolt 美學不符教學片
