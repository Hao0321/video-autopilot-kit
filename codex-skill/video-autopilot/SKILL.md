---
name: video-autopilot
description: Hao 的 YouTube 長片、YouTube Shorts 與 Instagram Reels end-to-end 自動規劃／剪輯 Skill，依片型路由腳本、視覺、剪輯、QA、手機遠端審片／審圖、發佈與成效回填；製作或更新任何視覺素材後會自動建立並驗證手機遠端入口，不需再次提醒。支援 Plan、Log Outcome、Optimize Patterns。觸發詞：「規劃下一支」「全部你來」「autopilot」「從題目到上架」「剪 N」「做素材」「素材做完」「做完給我看」「訓練美感」「學這批參考圖」「手機看不到成片」「遠端審片」「遠端看素材」「手機看生成圖」「記錄成效」「retrospective」「優化默認值」。AI 短劇／漫劇不因一般剪輯指令自動啟用，只有使用者明確要求製作或剪輯 AI 短劇時才走 drama_autopilot。
---

# Video Autopilot

目標：一句題目進來，輸出可交付影片與 publish package。**預設工作範圍是 Hao 的 YouTube 長片、YouTube Shorts 與 Instagram Reels。** 它只做 orchestration；voice 用
`yt-script-style`、策略用 `video-craft-playbook`／`yt-algorithm-mastery`、CapCut 操作用
`capcut-agent-ops`。

**AI 短劇啟用閘：** 一般的「剪片」「全部你來」「做 Reels」「做 AI 影片／廣告」都不得推定為 AI 短劇。只有使用者明確說「做／剪 AI 短劇、AI 漫劇、爽劇、某一集短劇」或明確指定 `ai_short_drama`／`drama_autopilot`，才啟用短劇流程。AI 廣告、產品片、建案片、汽車片、美食片、電影概念片或動畫測試，預設先交給 `ai-media-generator` 寫提示詞／生成素材；除非使用者另外要求剪輯，不自動進本 Skill。

AI 短劇／漫劇啟用後，題材、Series Bible、季弧、分集劇本與連載狀態先交給 `ai-short-drama`；本 Skill 從已核准的 production pack 接手生成任務佇列、逐鏡素材 QA、局部重試、story cut、輸出與發布包，不在剪輯階段任意重寫 turn 或 cliffhanger。

## 0. Token Gate（任何任務第一步）

先產生固定大小、固定檔名的執行包：

```powershell
python context_router.py route --mode build --format shorts --domain auto --topic "題目" --output-dir "工作目錄"
```

只讀 `current_context_packet.json`；需要素材決策時再讀同目錄的 `current_asset_plan.json`。前者預設
依 mode 上限 650–1,100 tokens、build 通常約 700；後者上限 1,200，而且只含排名後少量候選。不得預載整本
`meta-lessons-canon.md`、`craft-index.md` 或全部 references。只有 packet 中的 escalation trigger
成立時，先加讀一份指定 source；仍無法決定才讀 canon。相同路由覆寫同一個 current packet，
內容未變即 cache hit，不建立 `v2/v3` context。

這是預算護欄，不是美感硬編碼：安全、真實、檔案生命週期、技術 QA 與 Token 上限由 gate 鎖死；
構圖、字卡、動態、剪點、轉場與情緒節奏依素材語意和可覆寫偏好權重決定。

## 1. 片型路由

| 片型 | format | 一鍵流程 | 深讀來源（只在升級時） |
|---|---|---|---|
| 教學長片 16:9 | `longform` | `longform_maker/` | `references/hao-teaching-longform-method.md` |
| Shorts/Reels 9:16 | `shorts` | `python shorts_autopilot.py scan N` → `build N` | `references/shorts-mastery-2026.md` |
| AI 短劇／漫劇 9:16（僅明確要求） | `ai_short_drama` | `python drama_autopilot.py run --topic "題目"` | `ai-short-drama` 的 production pipeline |
| vlog／字卡片 | `vlog` | `capcut-agent-ops` Path A-E | `references/genre-editing-craft-2026.md` |
| 訪談 | `interview` | `interview_autopilot.py invite/plan/build` | `../interview-show/references/format-bible.md` |

題材由 `domain_taxonomy.py` 單一詞庫判斷；`visual_director.py` 選剪輯語法，
`editorial_templates.py` 選 style／role／aspect，16:9 與 9:16 共品牌 token、各自 reflow。
訪談預設使用 `no_face_documentary`：真 proof／真操作優先，H/G 形狀＋文字講者識別；禁人物臉、AI 頭像、剪影與 reaction face。細則按需讀 `../interview-show/references/no-face-visual-system.md`。

## 2. 永久護欄

1. M10/M34：先看高解析 frame audit，再寫字幕；未知數字、地點、菜名、戰績不猜。
2. M101：旁白先載 `yt-script-style/style_profile.md`；不把長片寫成 AI 說明書。
3. M115：原始素材唯讀；同片只原子更新 `_out/current.mp4`；版本留 metadata，不複製完整影片。
4. M116：題材先決定構圖語法；長短片共 token、不共裁切——題材差異要反映在構圖、材質、字型與鏡頭語法，不准同版式只換色。
5. M117：護欄硬、創意軟；上下文按需路由，不把記憶庫整本餵模型——新回饋先進偏好權重，跨影片仍成立的底線才升格 gate。
6. M118：素材是決策系統，不是資料夾；真來源優先、候選按需路由——依「真來源→語意 B-roll→題材 motion→字卡→clean hold」降級，不相關庫存片不得補 proof。
7. M119：字幕與文字效果分軌。Shorts 可由 `caption_director.py` 選擇性使用巨字與票券；長片逐句字幕維持 M68 白字黑底，但 Hook／轉折／Proof／Payoff 可走獨立巨型數字／關鍵字 overlay。指定為 premium hero 的固定插畫字只可使用經人眼審核的 Imagegen 素材；需要任意中英數字與逐幀 Tracking 時，改用通過 `typography_catalog.jpg`＋真片 contact sheet 人眼審核的 `tracked_graphics.py` profile。兩者都未核准時標記 `imagegen_required` 或 clean hold，不能用低品質程式字冒充 premium。這不是全域美術禁令：品牌字型感、原創 Logo、粗描邊、卡通貼紙與刻意廉價的綜藝感，均可依題材與層級使用。
8. 效果不可遮人臉、產品、操作、字幕或 proof；真素材與現場聲先於裝飾。
9. 機器通過不等於完成：全幀掃描圖、proof 對來源、字幕逐行仍須人眼確認。
10. M121：風格語言不等於侵權素材。可使用原創品牌字型感、Logo 式識別、粗描邊與卡通貼紙；只禁止未授權搬用第三方受保護檔案，不得把個人美術偏好誤寫成全域硬禁令。
11. M122：先把事件分成 camera move／edit transition／graphic transition／overlay，再命名手法。MrBeast 類美元價值階梯走「高速拉遠揭露→同方向 whip 物件替換→拉遠總覽→落點噴鈔」；美元粒子固定是 overlay，不得自動標成轉場。只有兩顆來源 shot 與實際剪點都有證據，才可宣稱 whip／match／occlusion cut。
12. M123：貼身金額／中英數字巨字與左上挑戰紀錄走 `tracked_graphics.py`，永遠分類為 overlay。Tracking 必須有真片、起始 frame、可信 `initial_bbox` 與數值證據；失追只准短 hold 後隱藏，不准猜路徑。Challenge Ledger 必須以 active/completed/upcoming 狀態更新，不能拿空白模板或網格字卡冒充紀錄。完整 spec 與 QA 讀 `references/tracked-typography-and-challenge-ledger.md`。
13. M124：交付採 Quality-95 雙層認證。`quality_corpus.py` 封鎖已知爛法，`quality_95.py` 計分；但機器綠不等於好看，未由 Hao 完成 `review_loop.py` 時間碼審片只能標 `REVIEW`，不得標 `CERTIFIED_95`。手機或電腦只是開啟審片頁的裝置。素材疲勞按最近 20 支與連續使用計算，不以 lifetime 次數永久封殺素材。完整契約讀 `references/quality-95-system.md`。
14. M125：戰鬥陀螺真偽是資料，不是每幕都要唸的裝飾。`battle_matchup` 同為 `official` 時，開場、Tracking、HUD 與發布文案只寫雙方陀螺名稱，禁止「正版／正版內戰／正版王牌戰」及底部名稱重複；只有 `official` 對 `counterfeit` 才清楚標示正版／盜版。BEYBLADE X 對戰倒數口號固定寫「3・2・1 Go Shoot！」（英文標準顯示可寫 `3, 2, 1 Go Shoot!`），「發射」只能當一般動作名詞，禁止寫成倒數口號「3・2・1 發射」。`shorts_gate.py` S-T／S-U 會 fail-closed。
15. M126：47 張使用者視覺參考已抽象成跨長短片的 Creator Aesthetic Standard。`aesthetic_score.py` 先按題材路由美術家族，Shorts 加重首幀／字體／時間動態，長片加重題材／主體整合／觀看耐久；`review_loop.py` 以十維人工評分，未達 90、任一維低於 3.5 或未完成評審均不得通過。機器只擋已知爛法，不能用測試綠燈冒充美感。完整規格讀 `references/hao-aesthetic-standard.md`。
16. M143：長片封面與影片本體分開驗收。`thumbnail_algorithm_score.py` 以點擊承諾、標題互補、片內兌現、手機可讀、焦點、情緒、對比、差異與三版本測試準備產生 `THUMBNAIL_SCORE`；這是可解釋的預發布風險分數，不是 CTR 預測。影片 Quality 95 與封面分數都 ready 才進長片發佈，實際勝負仍由 YouTube Test & Compare 的觀看時間與發布後留存判定。完整規格讀 `references/thumbnail-algorithm-score.md`。
17. M144：MrBeast 資訊能量與影視颶風電影工藝同時是每支長片、Shorts 與 Reels 的必評雙基準，不得因片型而移除任一軸。目標是同等功能、視覺完成度與節奏工藝，不是逐幀照抄。物件斜角閃白固定走 `tracked_graphics.py` 的 `mask_sheens`，是 subject-matte overlay，不是轉場；沒有可靠 bbox／polygon／alpha matte 就禁用。任何「100% 可複製」宣稱都必須對單一效果提供參考版本、素材前提、能力狀態、輸出與逐幀 QA 證據。未驗證或缺原始鏡頭／3D 資產／外掛／Roto 時必須明確降級，禁止假稱完全複現。評分讀 `references/mrbeast-and-yingshi-benchmark.md`；效果註冊與 parity gate 讀 `references/benchmark-effect-parity.md`。
18. M145：發布後所有 FB／IG／YouTube／Threads／X 的流量、推薦來源、搜尋、留存、互動、受眾與轉化證據，統一寫回 `social-post/data/*.jsonl`；`video-autopilot` 只保留 `source_content_id`、剪輯決策與發布包，不另建互相漂移的演算法記憶。平台專門 Skill 可診斷，但跨平台比較、實驗證據與規則升降級以 `social-post` 為 canonical source。同一內容各平台分開 snapshot，缺值保留 `null`，Meta 合併卡片不得冒充完整平台洞察。
19. M146：完整開源以 `https://github.com/Hao0321/video-autopilot-kit` 為唯一公開來源；通用執行核心、Codex Skill、空白模板、機械 QA、可再散布素材與方法論都需納入版本 manifest，私人影片／臉部／帳號／成效／個人偏好／local outcomes／授權未明資產永不進公開包。每版輸出 archive SHA-256＋逐檔 index＋release channel；相容版可在完整性驗證、migration 宣告與本機未改管理檔的前提下自動升級。未知檔與 protected paths 永不刪；覆蓋前備份，失敗自動回滾，重大或不相容版必須確認。舊版沒有 updater 時由公開 bootstrap installer 接手；完整契約讀公開 Skill 的 `references/open-source-release-and-upgrade.md`。
20. M147：47 張私人參考圖固定由 `design_system_v6.py` 編譯為匿名設計 DNA；每支長短片都要有 `design_system_v6` recipe，依 domain／format／role 重新排版，不准把 Shorts 當長片裁切版、不准複製單張參考構圖，也不把原圖或路徑打進公開包。細則讀 `references/design-reference-dna-v6.md`。
21. M148：物件斜角閃光是 `subject_sheen` composite overlay：光帶只存在於陀螺、車、產品或主體的追蹤 matte 內，必須同時有 matte、track/keyframes、材質 profile 與首中尾 QA；不規則物件沒有 polygon／alpha matte 就降級 clean hold。全畫面閃白、拿光帶當轉場、閃到背景一律 BLOCKED。
22. M149：3D 必須誠實分級。`three_d_system.py` 將 depth cards／tracked billboard 標 2.5D，只有 mesh＋材質＋光線或 camera solve＋鏡頭＋clean plate＋shadow plane 齊全才可標 true 3D／camera-solved composite；缺前提就輸出 `DOWNGRADED`，禁止用 2D 貼片冒充 3D。規格讀 `references/three-d-and-subject-fx.md`。
23. M150：MrBeast 只作資訊密度、視覺回報與事件文法的功能標竿。`mrbeast_editing_system.py` 只在 promise／value／state／locate／reveal／proof／payoff 等事件且證據齊全時選效果；沒有語意事件就 clean hold，連續衝擊之間保留 contrast gap。所有表面設計、資產與品牌識別必須是 Hao 原創或已授權。
24. M151：所有新模板先由 `template_compiler.py` 編譯成「題材×畫幅×語意角色」的元件計畫，再交給 Bright Editorial／長片／Shorts renderer。模板是 composition plan，不是強制插入的全螢幕場景；真素材與證據永遠優先，`HOOK`、`LOWER THIRD`、`SHAPE / PLAY` 等角色／樣式名稱只可在 debug sheet 出現。9:16 與 16:9 必須重新排版；網格只可作局部材質，不能因 AI／科技或任何題材自動當開場。結構快取不可含文案、媒體與私人路徑；同一 signature 不得連發，需依近期使用輪替 style／layout。完整規格讀 `references/template-compiler-v2.md`。
25. M152：影視颶風不只是一格人工分數；所有長短片先由 `mediastorm_craft.py` 編譯鏡頭覆蓋、節奏波、聲畫橋、調色／shot match、資訊圖形與 VFX 契約。轉場預設 `clean_cut`；match cut、cut-on-action、遮擋、whip、speed ramp、J/L-cut 都必須具備對應 shot-pair／音訊證據，否則自動降級。禁止轉場包、每剪必 whoosh、用硬疊 LUT 冒充電影感、用全螢幕模板取代可用真素材。公開作品的量化觀察必須標為 proxy／推論，不得冒充官方內部公式；完整規格讀 `references/mediastorm-craft-system.md`。
26. M154：任何全面重構、架構最佳化或 Cleanup 規則調整，先校準量測工具。先列必須抓到的失敗類型，執行 Cleanup 自測與 task-shaped 正／反 fixture；抓不到就先補 evaluator＋回歸案例。之後鎖定 evaluator SHA、`audit.config.json` SHA、schema 與 raw before report，再以相同工具比較 after。循環依賴、分層違規、parse error 與 severe 函式為 FAIL；warning-size 函式只列 REVIEW，不得為消滅提醒而機械拆分。例外必須有語意理由、最大行數與到期日，且仍保持可見。重構必須保留舊 import／CLI facade、rollback，並把決策、失敗與 transferable rule 寫入 `.rd/`；完整契約讀 `references/architecture-foundation-v6-3.md`（文件內容版本 v7.0，檔名保留相容性）。
27. M155：任何 `Build` 產生的 `current.mp4` 只有在 technical QA、Hao 審片狀態、`publish_hub.register_completed_short()`、SHA／canonical-source 覆蓋稽核與索引重建全部成功後才算交付。發佈稽核必須是 closed-world：既有包合法但仍有未註冊成片／過期包，一律 RED。已發佈包不可覆寫；未發佈包改狀態只能搬移同一包，不得產生第二包。唯一人工入口為專案根目錄 `00_發布中樞_從這裡開始.md` → `videos/_PUBLISH_HUB/START_HERE.md`，不得叫 Hao 去各集 `_out` 找成片。
28. M156：開源升級分成「受 release manifest 管理的程式碼交易」與「非破壞 workspace schema 遷移」。程式碼須校驗、備份、rollback；使用者影片／設定／憑證／分析／未知檔案永遠不被 updater 覆寫。自動 workspace migration 只新增缺失結構與可重建索引，必須 idempotent，並以 clean install、相容舊版升級、第二次 no-op、在地修改保護與 rollback fixture 驗收；未版本化 legacy 僅能明確 adoption 一次。
27. M155：大量素材製作固定走 `asset_workshop.py`。視覺層級固定為「真實專案素材→授權真實 B-roll→寫實合成／預渲染 3D→圖形 overlay→clean hold」；高資訊剪輯不等於卡通化。先讀 registry 缺口，只擴產最低覆蓋的語意角色；Imagegen 預設以 4×4 atlas 產可重組原子圖，再由工坊切圖、透明度／重複／授權／能力標示 QA、總覽審核與登錄。寫實生成物一律標 `illustrative_not_evidence`，不可冒充真地點、真商品、價格或實測；`human_review=pending` 永不進自動選擇。預渲染 3D 必須明寫固定視角，不能冒充 mesh。MrBeast／影視颶風只拆資訊功能、材質、聲畫與節奏原理，禁止照搬品牌資產。完整流程讀 `references/asset-workshop.md`。
28. M156：素材量不是品質。任何批次先做 4–8 格 taste board，Hao 未核准不得大量生成；被判定醜、錯題材或無用的 batch 必須從工作庫、manifest、preview 與衍生檔完整移除。非寫實插畫只允許旅遊／美食／咖啡，固定走日系生活雜誌、自然材質、低飽和、暖白留白與輕鬆節奏；AI／玩具／商業／科技優先真實實拍、誠實 screencast、授權 B-roll、寫實合成或 clean hold。黑底發光 VFX 預設 Screen／Add、白底暗線預設 Multiply；只有遮擋、Tracking、多層合成或交付透明需求才用 `vfx_keyer.py` 轉 Alpha，且原始 master 永不覆寫。
29. M157：手機遠端交付不得使用 `D:\...`／`C:\...` 本機路徑冒充可點網址。同 Wi‑Fi 使用 `review serve`；跨網路人工佔用終端可用 `review remote`，由 Codex 交付網址一律使用可脫離啟動 shell 的 `review remote-start`，建立帶隨機秘密路徑的臨時 HTTPS Quick Tunnel。遠端模式只串流 manifest 指向的權威媒體，不複製原圖／原片、不新增根目錄工具資料夾；產生的 session／log 只放既有 `_review`。Quick Tunnel 是臨時公開入口，電腦必須保持上線，網址不可轉傳，審完必須 `review remote-stop`。
30. M158：`review create` 同時接受單支瀏覽器可播放影片、單張 JPG／PNG／WebP／GIF／AVIF／BMP，或含圖片與影片的資料夾；資料夾以穩定相對路徑排序，遞迴最多 300 個媒體並略過 `_review`。手機頁必須提供上一個／下一個、原比例 contain 顯示、影片時間碼、每個素材「可用／重做」與留言，結果原子寫入同一 bundle 的 `review.json`。生成圖批次的人審未核准前仍維持 `human_review=pending`；素材審查不得冒充成片 Quality-95 finalize。使用者說「遠端看這支／這張／這批」時，直接建立 bundle、執行 `remote-start`、外網驗證 HTML 200 與媒體 Range 206，再只交付 HTTPS 網址。
31. M159：所有會產生或修改可視成品的任務——影片、生成圖、icon、texture、VFX plate、3D 預覽、模板、taste board 或素材批次——把「Hao 手機可打開」列為交付完成條件，不必等使用者再次說「遠端看」。完成後固定執行 `review deliver`，它必須建立 bundle、啟動秘密 HTTPS Quick Tunnel，並從公開網址驗證審查頁 200 與第一個權威媒體 Range 206；驗證失敗只能回報未完成／阻塞，禁止以本機路徑、contact sheet 或「已做好」代替。最終回覆先給手機網址，再說內容與狀態；電腦保持上線直到 Hao 說審完／停止，再執行 `remote-stop`。純程式碼、純文件與只讀 audit 沒有可視成品時不套此閘門。
32. M160：新增參考的核心不是把畫面塞滿，而是讓主標成為版面骨架。同幀最多一種 display voice＋一種 utility voice；高密度只能集中成一個衝擊群，旁邊必留安靜閱讀通道；色彩固定一個主色場＋最多兩個強調色。`arcade_pop` 僅服務遊戲／玩具／活動／音樂，`pixel_terminal` 僅作 AI／科技／資安的敘事比喻，兩者都不得取代真主體、真操作或真證據；`arcade_pop`／`pixel_terminal`／`iridescent_future` 不得同幀混搭，旅遊／美食維持安靜日系與真食物優先。
33. M161：ICON 與影片素材永久分庫。ICON 只作 UI／定位／分類／提示，不得冒充 B-roll、主體、缺片補畫面或素材覆蓋量；預設只能使用單色、純色、扁平、簡約、輪廓清楚的 `minimal_monochrome_icon`，禁止漸層、寫實陰影、假 3D、雜色、貼紙牆與風格混搭。Style／taste board 只校準方向，不能拆成一堆 ICON 後宣稱是素材。2026-08-13 的 32 個圖示化切圖由 Hao 人工評為 0／不及格，整批拒絕並禁止以相同方法重生。
34. M163：參考圖必須先標記學習角色再進設計 DNA。使用者指定為排版／位置／視覺規劃的圖固定走 `layout_only`，只學構圖、層級、圖片位置與文字位置，禁止其 placeholder 色彩、材質與動態進入美術偏好；指定為喜歡美術的圖走 `art_direction`，才學配色、字體、材質與動態。執行順序固定為「role／畫幅 → 一個構圖骨架 → 最多一個圖片位置修飾 → 文字層級 → 一個美術家族 → 材質與有理由的動態」。鈷藍類比拼貼使用單一照片動勢、黑白碎片、Xerox 網點與軌道線；虹彩字體幾何以黑灰硬分區、巨型粗黑／輪廓字與箭頭建立閱讀路徑，光譜色每幀只可落在物件、主字或幾何圓盤其中一個載體。

## 3. Build 最短流程

1. `context_router.py` 建 packet，判 mode／format／domain。
2. 掃素材：方向、解析度、幀率、音軌、GPS／個資、可用 hook 與 proof；`asset_registry.py` 從既有
   index／manifest 建 virtual registry，禁止逐檔把整庫載進 prompt。
   如果 asset plan 連續三支回報同一語意缺口，先用 `asset_workshop.py plan` 建工坊 job；不得臨時塞不相關模板。
3. 腳本與計畫：`script_gate.gate(text)`、`plan_gate.gate_plan()`。
4. 視覺：`write_visual_plan()` 自動寫入 context budget、題材 style、47 圖 `design_system_v6` recipe、證據制資訊事件、誠實 3D capability、能量波、`caption_system` 與 motion cues，並在同目錄
   原子更新 `current_asset_plan.json`（B-roll／BGM／SFX／motion／template 排名）。
5. 建立：長片走 `longform_maker/`；直式走 `shorts_autopilot.py`；計畫含 `tracked_value_label`／`challenge_ledger_hud` 時先驗證 `tracked_graphics.py` spec 再 render；需要 GUI 才進 CapCut。
6. QA：片型 gate → delivery QA → Quality-95 負面回歸 → Hao 時間碼審片；任一 `BLOCKED` 就修，不交付，未審片只可標 `REVIEW`。
7. QA 綠後 `storage_lifecycle.finalize_success()`，只清白名單可重建中間檔。
8. `publish_hub.py sync` 將長片／短片放入 `videos/_PUBLISH_HUB` 的各自獨立發佈包；同磁碟使用 hard link，不複製成片。
   長片在此之前另跑 `thumbnail_algorithm_score.py`；沒有三個可測假設或仍為 `REVISE` 時，發佈狀態維持 review。
9. 發佈後整包由 `_PUBLISH_HUB/READY` 移入 `_PUBLISH_HUB/PUBLISHED`，回填 `video_log.md`／`channel_state.json`，安排 D2／D7／D28。

交付總閘門：

```python
delivery_qa.final_delivery_qa(
    video,
    voice=voice_path,
    ass=caption_path,
    sheets_dir=qa_dir,
    profile="teaching_longform",
)
```

`video` 之後一律使用關鍵字，避免靜默 BLOCKED。

## 4. Shorts 傻瓜流程

Hao 只需把素材丟進 `_INBOX/直式-vertical-Shorts-Reels/<N>/` 後說「剪 N」：

```powershell
python shorts_autopilot.py scan N
python shorts_autopilot.py build N
```

輸出只更新 `_out/current.mp4`，QA 證據在 `_out/_qa/`。首秒兌現、片長、字幕安全區、loop、
音訊、字幕美術與 16 項規則由 `longform_maker/shorts_gate.py` 驗證；Claude 仍需看 contact sheet 與
`CAPTION_match.jpg`。Build 另產生 `_qa/QUALITY_95.json` 與 `_review/review.html`；Hao 送出時間碼後，
執行 `python review_loop.py finalize "<N>/_out/_review"` 才能取得正式 95 分認證並把問題去重回寫記憶。

手機不在同一個 Wi‑Fi 時，從專案根目錄啟動臨時 HTTPS 審片；禁止再回覆本機檔案連結：

```powershell
python scripts/hao_autopilot.py review remote-start "<N>/_out/_review"
python scripts/hao_autopilot.py review remote-status "<N>/_out/_review"
python scripts/hao_autopilot.py review remote-stop "<N>/_out/_review"
```

其他成片、單張生成圖或整批 taste board／素材資料夾走同一入口；相容媒體直接串流，不建立副本：

```powershell
python scripts/hao_autopilot.py review deliver "<影片、圖片或資料夾>" --content-id "<id>" --bundle-dir "<既有工作目錄>/_review"
```

## 4.1 AI 短劇傻瓜流程

從 canonical workspace 或已同步的 Skill 執行：

```powershell
python drama_autopilot.py run --topic "假廢物真強者，但每次亮牌都會失去一段記憶" --provider browser
```

命令自動建立專案、用 Codex 結構化產生 pilot、驗證 production pack、編譯 Seedance 任務佇列並保存斷點。`browser` executor 由目前的 Codex 依 `ai-media-generator` 操作已登入平台，逐鏡下載後呼叫 `complete --qc-passed`；任務耗盡後自動 `build`、QA 與建立 publish package。測試使用 `--provider mock`，不得把 mock 成片當正式素材。

只在登入／付費牆／敏感內容／無法自動修復或公開發布前停下；公開發布必須取得一次明確核准。完整 CLI 與恢復規則讀 `ai-short-drama/references/automation.md`。

## 5. 記憶怎麼學，才不會越學越大

- 新回饋用 `knowledge_lifecycle.py record` 入帳；scope + rule fingerprint 相同時只累加 support，不新增副本。
- 單支片主觀回饋 → 該題材／片型的 soft preference；三支以上重複、無衝突才自動 pinned。
- 與舊規則矛盾時兩邊都停止進 runtime，先界定題材／片型範圍，不用新回饋靜默覆蓋舊訓練。
- 涉及真實、安全、技術品質、容量、交付 → 寫進 gate＋self-test。
- 每次 packet 最多載 6 條 pinned rule；舊 optimization log/canon 只當 evidence/archive。
- M120：任務精確的 format/domain 記憶先於全域 core；`all` 正規化為 `*`。Token 超限只從排序尾端裁，packet 必回報 selected/trimmed，禁止 pinned 規則靜默載不到。
- 新 lesson 必須同時說明：適用範圍、反例、優先級、驗證方式與可否覆寫。

## 6. 常用檢查

```powershell
python ../../../scripts/hao_autopilot.py doctor --quick
python ../../../scripts/hao_autopilot.py knowledge
python ../../../scripts/hao_autopilot.py maintain --hash-duplicates
python context_router.py audit
python asset_registry.py audit
python asset_registry.py audit --full
python asset_workshop.py audit
python storage_lifecycle.py audit "../../../videos" --hash-duplicates
python publish_hub.py sync
python publish_hub.py audit
python system_health.py --quick
python system_health.py
python quality_corpus.py regression
python quality_95.py selftest
python project_quality_95.py --output-dir ../../../reports
python architecture_gate.py audit --output ../../../reports/ARCHITECTURE_GATE.json
```

## Visual Master（M131–M134）

- M131：審片人固定是 Hao；手機或電腦只是開啟 `_review/review.html` 的裝置。未由 Hao 完成時間碼與十維美感評分，一律只能標 `REVIEW`。
- M132：調色順序固定為輸入色彩空間辨識 → 一級校正 → 單一創意 Look → 字幕／Logo／Tracking／動態素材 → `grade_gate.py` → Hao 審片。不得硬疊 LUT，也不得讓 LUT 污染字幕與圖形。
- M133：`visual_master.py` 依長片、Shorts、Vlog、Podcast 與 AI／旅遊／美食／玩具等 domain 路由。一般強度約 0.25–0.35、題材上限 0.35–0.42、絕對上限 0.50；Log 未知 Input Transform 時 fail-closed，HLG/PQ 先正規化到 Rec.709 SDR。
- M134：Hao 參考圖提煉出的美感標準是母標準；2026 趨勢只做題材提示，不成為每支片的固定皮膚。趨勢研究有 180 天 TTL，讀 `knowledge/design_trend_radar.json`，詳細色彩契約讀 `references/color-science-and-visual-master.md`。
- M135：創意 LUT 前先走 `color_calibration_lab.py`。只有 exact camera ID＋已驗證 ColorChecker profile 能自動校正；未知機型、推測 profile、Log/HDR 不得亂套矩陣。
- M136：跨鏡頭只產生有界 shot-match 建議；waveform／vectorscope、前後 A/B 與膚色／白平衡／層次仍由 Hao 審。不能以「更鮮」自動判新版較好。
- M137：審美學習只收 Hao 的 pairwise A/B；feature 至少 5 次比較才進偏好摘要。單次修改只是一筆證據，不得升格全域規則。
- M138：觀眾成效只比同平台、同 D2/D7/D28 視窗，至少 5 支才建 baseline；缺值不補 0、相關不冒充因果，而且不得用 Hao 喜好替代觀眾結果。
- M139：資產公開採 fail-closed。授權或 provenance 不明就只隔離、不猜授權、不進社群包；私人臉部、使用者素材與 project-use-only 音樂永不公開匯出。
- M140：documentary／interview／fitness／fashion filler 是語意 B-roll，不是轉場、開場或 proof；只有缺真素材且語意相符時才用。
- M141：重混回原始素材建立新敘事，不串已燒字幕成片；冷歸檔預設只 preview，INBOX／READY／PUBLISHED 永不自動搬移或刪除。
- M142：AI 文件／提示詞／流程／多工具解說可選 `ai_evidence_canvas`：成果先行，同一證據畫布內以卡片縮放與焦點標註維持空間記憶，操作與成片則由真素材全畫面接管。它是條件式呈現文法，不是黑網格固定開場；沒有三份以上真證據、只有逐步點擊或真人口播時不得啟用。完整規格讀 `references/ai-evidence-canvas.md`。

Build 時 `write_visual_plan()` 必須產生 `color_system`。Shorts 在每個來源片段、字幕與動態素材之前套色並寫 `current_color_report.json`；長片／Vlog／Podcast 也必須先完成同一套素材層調色，再做字卡與合成。

```powershell
python visual_master.py plan --domain travel --format vlog
python visual_master.py analyze "input.mp4"
python visual_master.py build-luts --size 17
python visual_master.py selftest
python color_calibration_lab.py selftest
python outcome_learning.py refresh
python asset_license_governance.py audit
```

完整模式 A/B/C 與營運回填見 `references/autopilot-modes.md`；craft 導航見
`references/craft-index.md`；只在遇到具體問題時按導航讀一本。完整歷史與 antipattern 在
`references/meta-lessons-canon.md`，預設不載入。素材 schema、fallback、Token 與 usage 記憶見
`references/asset-intelligence-hub.md`。
成片分類、命名、題材文案查證、已發佈內容再製與 SHA-256 去重規則見
`references/publish-hub-and-remix.md`。
價值階梯、美元 overlay、運鏡、物件替換與真剪點的分層契約見 `references/camera-transition-and-value-visualization.md`。
MrBeast／影視颶風跨長短片效果能力對等、完成度證據與不可假稱 100% 的邊界見 `references/benchmark-effect-parity.md`。
全專案控制面與相容策略見 `../../../AUTOPILOT_4LAYER.md`；學習去重、衝突與晉升規則見
`references/knowledge-lifecycle.md`。
Quality-95、負面案例、素材疲勞與 Hao 人工審片見 `references/quality-95-system.md`。
跨長短片的美術家族、十維量表與題材路由見 `references/hao-aesthetic-standard.md`。
MrBeast 資訊能量、影視颶風電影工藝、物件遮罩高光與自動化分級見 `references/mrbeast-and-yingshi-benchmark.md`。
MrBeast 字體／動畫／運鏡／Tracking／Roto／3D／VFX 的源頭分類、能力真實邊界與素材工坊順序見
`references/mrbeast-production-source-map.md`；機器執行以 `knowledge/mrbeast_effect_source_map.json` 為準。
相機校準、pairwise 審美、成效證據、授權公開、缺口 B-roll、重混與冷歸檔見
`references/calibration-learning-and-license.md`。
AI 資產／提示詞／流程圖較多時的證據畫布、狀態機、動態與低 Token scene plan 見
`references/ai-evidence-canvas.md`。

## 7. 永久發佈與再製規則

- M127：所有 QA 完成的成片只能由 `publish_hub.py` 進入 `videos/_PUBLISH_HUB/READY`，先分
  `shorts / longform / remix`，每支片擁有獨立成片、`publish.json` 與可複製文案；禁止再建立散落的
  `_待發布Shorts` 或 `final_v2` 資料夾。
- M128：文案的勝負、感受與順序只取片內證據；產品、地點、功能、價格等外部資訊走
  `topic_research_catalog.json`，超過 TTL 就標 `RESEARCH_REQUIRED`。戰鬥陀螺正版對正版只寫雙方名稱；
  對非官方仿製品必須揭露身份。
- M129：已發佈單點片可回到原始素材重剪成新的集合敘事；禁止把已上字幕的 Shorts 直接串接。
  同區域／同旅程至少三站才列再製候選，並保留來源 content ID。
- M130：重複媒體只有 SHA-256 完全一致才可處理。先建立權威本，再將副本改 hard link 或在發佈包
  驗證後退休舊路徑；原始拍攝素材永不因去重自動刪除，所有動作必須留下稽核報告。
- M153：發布入口固定為 `videos/_PUBLISH_HUB/START_HERE.md`；READY 與 PUBLISHED 都只能從這裡導航。
  每包強制正好一支權威成片，`publish.json` 記錄 SHA-256 與 `artifact_revision`。同 content ID 新版若
  SHA 不同，舊成片移入 `_archive/publish-hub-retired/<UTC>/<content-id>` 並寫稽核；若 SHA 相同只退休
  多餘 hard link。`v2／FINAL／old／backup／初剪／draft` 名稱禁止進發布包。原始素材、current 與發布證據不刪。
- M162：任何「MrBeast 類效果」必須先查 `knowledge/mrbeast_effect_source_map.json` 分清 editorial、motion graphics、tracking、roto、3D、VFX、colour 與 sound；可重用單位是 editable rig／material／emitter／UI shell／source scene／SFX family，不是固定 PNG、ICON 或寫死文字。Tracking、遮罩、camera solve、occlusion、光線、最終文案、節奏與調色永遠逐鏡處理。先 clarity、單一概念與情緒，再尺度、刺激與 payoff；禁止用一直快剪、一直 Meme 冒充 MrBeast。物件光掃必須在 matte 內，美元粒子只能作金額 payoff overlay，真正 3D/VFX 需完整前提並在昂貴製作前先鎖 animatic／wireframe。每個素材家族先通過一個 motion test 與 Hao 審查才准批量擴張。
