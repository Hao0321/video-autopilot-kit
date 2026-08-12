> → 找不到要讀哪本？[craft-index.md](craft-index.md)（六本 craft refs 導航：症狀→節路由表 + 跨檔重複主寫對照）

# 剪輯 master 級：competent → 高手中的高手（2026 深挖 round3 + 對抗驗證）

> 比 craft 基本功（→ editing-craft-fundamentals.md）更深一層：剪接的【判斷哲學】+ 最高槓桿的進階技。核心：**觀眾最後只記得『感受』，不是技術**（Murch）——這直接命中 Hao baseline『CTR 好但留存/AVP 低＝沒被感受勾住』。
>
> ⚠ **驗證註記（對抗驗證後 — 別把比喻當公式）**：① Murch Rule of Six 的百分比(51/23/10/7/5/4)是他**本人說的「修辭性優先序」非可加總演算法** → bake 成「emotion 第一、衝突時不為低階犧牲高階」的**心法**，別當數字計算。② Blink Theory / cut-rate(動作 25 vs 對白 6 /min)是**啟發式不是定律**，當情緒密度的方向錨點、不當硬門檻。③ **對 Hao 主力（M78 不露臉、螢幕教學片畫面多 UI）：film grain / teal&orange / 4-6 IRE / vignette 相關度低甚至有害**（干擾文字銳利+UI 發色偏）→ 那幾條排序自動降，主要用在美食/旅遊實拍。④ 縮圖/留存的「2.8×」「63%」類數字來自工具商部落格（利益相關），方向可信、精確值別當絕對。⑤ CapCut GUI 功能宣稱（示波器/Adjustment Layer/LUT intensity 滑桿）未實機驗證 → Hao 主走 ffmpeg 不照搬；繁中走既有 OpenCC（simp-to-trad-flow.md），定價以 app 內為準。

## 🥇 Master moves 速查（competent editor 不會、master 會）

| master move | 為什麼這是高手分水嶺 |
|---|---|
| 判斷層 vs 操作層的根本切換：每一刀問『觀眾此刻感受對不對』而非『接得順不順』(Murch Rule of Six 前2項=74% 權重) | 這是整批研究最高槓桿、且 Hao 最缺的一塊。他的 M9-M102 全是操作層『無錯誤』規則(色彩/音訊/對位/占比/字幕)——保證每一刀技術對，但保證不了整段有感受。直接命中他 baseline 真痛點：CTR 8.5%(包裝好)但 AVP 只 43%(進來沒被勾住)。把『接得順』換成『情緒對不對』是 competent→master 唯一的分水嶺，影響成片質感最大。注意:Murch 那組精確百分比(51/23/10/7/5/4)是修辭性權重不是量測值,當『優先序心法』bake、不要當演算法照算。 |
| 交付前加『感受殘留測試』gate：全片看完→閉眼→用一個情緒詞回答『我現在感覺什麼？』，答不出清晰情緒就回 emotion 層重剪(別再修技術細節) | Hao 的 delivery_qa.py 全是機械 audit(M86 占比/M87 對位/頻閃/死空檔/LUFS/PII)——全是『無錯誤』類,沒有一條檢查『有沒有感受』。這條是唯一能機械化掛上去、又直接補 AVP/留存痛點的最高層 QA。教學片目標情緒=『原來如此+我想試』、美食=『嚮往+餓』、旅遊=『嚮往』、重機=『熱血』。答不出=技術完美但片是失敗的,這正是他 43% AVP 的根因。低成本、立刻可加進現有 QA 流程。 |
| L-cut 搬到旁白+b-roll：讓畫面比旁白早 0.3-0.8 秒切到對應 b-roll(畫面領先聲音半句)，cut 不卡句尾而卡『念頭轉換/換氣』那一格(Blink Theory) | 這是對 Hao 既有 M87『cut 卡句尾、逐句對齊 b-roll』的直接 master 升級,不是重複。他現在 cut 機械卡句尾——Murch 點名這正是初學者『Dragnet 式一人講完才換』通病。改成畫面領先聲音半句+切在旁白換氣(=不露臉版的『眨眼』),接縫從僵硬變呼吸感。可寫成 helper:用 silencedetect 抓換氣點當剪接候選,b-roll 入點往前 offset 0.3-0.8s。影響流暢度直接、且接上他現有 pipeline 幾乎零成本。 |
| cut-rate ↔ 情緒密度數值錨點：AI 教學解說段保持 4-8 cuts/min(接近對白戲6)、Shorts 高能段拉到 20-25/min；別把『高留存=每5秒一刀』當鐵律套教學片 | Hao 的 memory 裡『pattern interrupt 每 X 秒』數字很多但都是『加刺激』方向,缺『該慢下來』的反向錨點。MrBeast 2024 自我反轉(放慢、呼吸、views skyrocketed)+ Murch cut-rate 數據共同推翻『狂剪=高留存』。他的 AI 教學長片是『沉澱/解說』語氣,塞滿 b-roll 換點反而焦躁趕跑觀眾——這可能正是 audience 連 3min 只看 43% 的一個原因(剪太碎=累)。可機械化:ffprobe 數 cut 數÷時長對照段落情緒,解說段超過 8/min 就標『過碎』。 |
| 轉場語意化：hard cut=同一念頭流(零距離)、dissolve 長度=心理/時間距離。教學片同概念內全 hard cut，只章節真跳轉/時間流逝才溶接 | 把轉場從『裝飾』升級成『語意』,治本他過去花大量 session 在『花字/炫炮 transition/罐頭特效』上打轉(task 史一堆 v13-v25 在套 Pro 模板特效)。一條死規則就能砍掉業餘感:同概念連續 b-roll 一律 hard cut(他美食/旅遊研究也獨立驗證『95% 硬切』),溶接只留給時間流逝(縮時)。低認知成本、跨所有 niche 適用、立刻提升質感。 |
| Eye-Trace 焦點連續(快剪時權重最高)：跨刀讓主焦點落在螢幕同區或有明確引導路徑；9:16 Shorts 焦點別在上下三分之一亂跳、教學 demo 游標/重點框跨刀對齊 | Murch 給 7% 但研究內多源指出快剪(<1s/shot)時 eye-trace 升為『唯一最重要因素』——直接命中 Hao 兩個主場景:(1)直式 Shorts 重點字幕/主體忽上忽下=眼睛累=『每刀都對但很亂』;(2)教學長片 UI/截圖切換時游標位置跨刀不對齊=觀眾迷路。這是他現有規則完全沒有的一層(他有 M68 字幕、M87 對位,但沒有『跨刀視覺焦點連續性』)。可加進 audit:抽接點前後 frame 比對主焦點座標。 |
| Repeat-Cut 收斂測試當機械 QA：關鍵接點剪完→遮 timecode→重剪 2-3 次→落點差 >1-2 frame 就標『此刀未收斂、需人工確認』 | Hao 全自動 pipeline 缺一個低成本驗證『這刀是內容必然的還是硬湊的』。這條可直接寫成 autopilot QA 點,客觀化主觀選擇困難(『這版那版都還行不知選哪個』)。對他『一句話→自動成片』的 Mode A 特別有用——機械收斂檢查比憑感覺定案更穩。屬判斷層、零美學成本。 |

## 🎬 Murch《剪輯之道》：Rule of Six + Blink Theory（剪接判斷最高層）

**Rule of Six 六準則權重表（一刀好不好的優先序評分）**  〔expert-consensus｜CapCut / ffmpeg 通用 — 這是判斷層，不是操作層。剪每一刀前心裡跑一次 6 項評分。〕
- 做法：Walter Murch 在《In the Blink of an Eye》提出每一刀都用 6 個準則打分，且權重固定：①Emotion 情緒 51% ②Story 故事推進 23% ③Rhythm 節奏 10% ④Eye-Trace 視線引導 7% ⑤2D 螢幕平面（構圖／180度線）5% ⑥3D 空間連續性 4%。關鍵：前 2 項（74%）> 後 4 項（26%）總和；emotion 一項 > 其餘 5 項相加。
- 數值/出處：精確權重：Emotion 51% / Story 23% / Rhythm 10% / Eye-Trace 7% / 2D plane 5% / 3D continuity 4%。記憶法：『情緒過半，前二佔四分之三』。教學長片應用：旁白講到關鍵 punchline 時，就算 b-roll 接點在動作中間不順（破壞 3D 4%），只要強化『恍然大悟』的情緒（51%）就該那樣切。Shorts 應用：美食那一口咬下的表情，emotion > 構圖完整，寧可裁到只剩臉。
- competent→master：解決『每一刀技術上都對、整段卻很死／很無聊／觀眾無感』——這正是 Hao 已掌握 craft 基本功後的天花板。把『接得順不順』的問句換成『這一刀讓觀眾此刻感受對不對』。也解決剪接卡關時的決策癱瘓：有了固定權重，兩個版本選哪個＝看哪個 emotion/st…

**Blink Theory 眨眼即剪接點（用演員/說話者的眨眼找這一刀的位置）**  〔expert-consensus｜CapCut（逐格看眼睛找眨眼格）/ ffmpeg（旁白片用 silencedetect/換氣點當剪接候選）〕
- 做法：Murch 剪《The Conversation》時發現：每次他決定切的那一格，Gene Hackman 幾乎都在那附近眨眼。理論：人在『一個念頭結束、轉到下一個念頭』的瞬間會眨眼——眨眼＝情緒/思緒的標點符號，而一個 cut 做的事一模一樣（結束一個 idea、開始另一個）。實作：看素材（dailies）時盯著說話者/主體的眼睛，他眨眼的那一格就是天然剪接點候選；觀眾在那一刻心理上『已經準備好接受新畫面』，所以切下去最不突兀。
- 數值/出處：操作：在 timeline 上找說話者眨眼那一格（±2 frame），優先把 cut 放這。日本研究：同一場電影觀眾的眨眼會彼此同步、也與影片同步——代表『該切的點』有生理共識。延伸：旁白片用換氣點當眨眼等價物。
- competent→master：解決教學長片『逐句對齊但接點僵硬、像 Dragnet 警匪片一人講完才換』的問題（Murch 點名的初學者通病）。對 Hao 的逐句字幕對齊 b-roll workflow 特別有用：cut 不一定卡在句尾，卡在說話者眨眼/換氣/換念頭那一格更自然。對不露…

**Cut-rate ↔ Blink-rate 對齊（用『每分鐘切幾刀』校準整段情緒密度）**  〔data-backed｜ffmpeg/ffprobe（數 cut 數）/ CapCut（看 timeline 密度）〕
- 做法：Murch 量化：動作戲約 25 cuts/min，對白戲約 6 cuts/min（美式片），而這兩個數字統計上吻合人在『激動 vs 平靜』時的自然眨眼頻率。原理：剪接速率就是『替觀眾代為眨眼』的速率——你切多快，等於告訴觀眾『此刻該多快地連續產生新念頭』。實作判斷：先定這一段的情緒溫度（高昂 or 沉澱），反推目標 cut-rate，再看自己剪出來的密度對不對。剪太碎＝逼觀眾在平靜段落狂眨眼（焦躁）；剪太疏＝高潮段落不給眨眼（悶）。
- 數值/出處：數值：動作 ~25 cuts/min、對白 ~6 cuts/min。自測：用 ffprobe 數一段的 cut 數 ÷ 時長，對照情緒溫度。AI 教學解說段建議 4-8 cuts/min（含 b-roll 換點），高光/結論段可短暫拉高製造能量。
- competent→master：解決『整段節奏感說不上哪裡怪』——量化成每分鐘刀數就能診斷。對 Hao：AI 教學長片大多是『沉澱/解說』語氣，cut-rate 應接近對白戲 6/min 而非塞滿 b-roll；Shorts 美食/重機高能段落可拉到 20+/min。直接接你 basel…

**Repeat-Cut 一致性測試（同一刀剪三次落點不同＝節奏沒抓到）**  〔expert-consensus｜CapCut（手動重剪比對）〕
- 做法：Murch 的自測法：直覺、即時地剪下一刀（他『never goes frame by frame』，靠身體感不靠逐格算），然後倒回去、不看上一次的落點、再剪一次同一刀。如果第二、三次落在不同格——代表你還沒真正『感覺到』那一刀，那個剪接點不是內容本身要求的，是你硬湊的。落點穩定收斂到同一格＝這一刀是對的。實作：關鍵接點剪完，蓋掉 timecode 重剪 2-3 次比對。
- 數值/出處：做法：剪完關鍵接點→倒回→遮住 timecode→重剪→比落點 frame。收斂（≤1-2 frame 差）＝對；發散＝該刀是湊的，重新找眨眼/換氣錨點。
- competent→master：解決『這版跟那版都還行、不知道哪個對』的選擇困難，把主觀變可驗證。對 autopilot pipeline 是個機械化 QA 點：關鍵 cut 自己重算 2 次落點，差超過幾格就標記『此刀未收斂、需人工確認』。

**Stand-Up & Conduct 站著剪、全身感節奏（情緒/rhythm 用身體判斷不用眼睛算）**  〔expert-consensus｜通用（判斷層／QA 習慣）〕
- 做法：Murch 站著剪片，把剪接比作『指揮、腦外科手術、快炒廚師』——都是站著做的工作，因為要用全身去感節奏，像 sax 手 solo 會站起來、指揮會站。判斷一刀的 rhythm（10%）對不對，不是逐格量秒數，是放著看時身體有沒有跟上（想點頭/打拍子＝對；卡頓/想快轉＝錯）。實作：判斷整段節奏時，站起來、隨畫面打拍子或數拍，用身體當測量儀。
- 數值/出處：Murch 原話精神：站著剪『因為我要感覺到場景的節奏，像 sax 手 solo 跳起來、像指揮』。交付前做法：站起來、全片一次性看完、身體想快轉的時間點記下＝rhythm 待修點。
- competent→master：解決『rhythm 這項說不清、只能憑感覺』——把它變成可重複的身體動作。對純 ffmpeg/CapCut 螢幕前久坐的剪法是個提醒：交付前站起來『全片不暫停看一遍』，身體卡住的地方就是 rhythm 出問題的地方（比逐格 audit 更快抓到悶點）。

**Eye-Trace 視線接續（讓觀眾的注視焦點跨刀不必跳，否則就是壞剪）**  〔expert-consensus｜CapCut（看前後格焦點位置）/ ffmpeg（截接點前後 frame 比對）〕
- 做法：Eye-Trace（7%）：人看畫面時眼睛會被臉、高對比、高飽和、動作吸引，落在某個焦點。剪下一刀時，如果新畫面的主焦點離前一畫面的焦點很遠，觀眾眼睛得在切後『重新找』，那一瞬的搜尋＝出戲。master 的做法：讓前一鏡的注視點與後一鏡的注視點落在螢幕大致同一區，或刻意用焦點移動引導視線到下一個重點（Murch：『我的工作是溫和地引導觀眾去看畫面的不同部分』）。實作判斷：看接點前後兩格，問『觀眾這刻在看哪？切後那東西還在附近嗎？』。
- 數值/出處：判斷：取接點前後各一格，標出主焦點（臉/高對比/動作/字幕）座標，兩者應在同區或有明確引導路徑。快剪內容（<1s/shot）eye-trace 權重應提到首要（業界 Jeff Bartsch：快剪蒙太奇裡 eye-trace 可能是『唯一最重要因素』）。Shorts 9:16：跨刀焦點別在上下三分之一間亂跳。
- competent→master：解決快剪 Shorts『每刀都對但看起來很亂很累』——通常是焦點在螢幕上亂跳，眼睛累。對 Hao 直式 Shorts 尤其重要：9:16 焦點位置（上中下）跨刀要連貫，重點字幕/主體別忽上忽下。對教學長片：截圖/UI demo 切換時，游標或重點框的位置跨…

**L-Cut 預期性反應剪接（切在反應、別切在『誰講完換誰』）**  〔expert-consensus ·常識｜CapCut（分軌錯位）/ ffmpeg（音畫分軌 offset）〕
- 做法：Murch 點名初學者通病『Dragnet 式剪法』：A 講完整句→切→B 講完整句，硬碰硬。但真實對話裡：『當對方還在講，你已經轉頭去看聽者的反應』。所以 master 在說話者『還沒講完』時就切到聽者的反應鏡（用 L-cut：前一句的聲音延續到下一畫面之下），切在反應、不切在輪到誰。原則：『在觀眾不得不開口要之前，先給他想要/需要的——既出乎意料又理所當然』。實作：聲音與畫面分軌，畫面提前或延後切到『該被看的反應』，聲音橋接過去。
- 數值/出處：L-cut/J-cut 重疊量：對白多為幾格到 1-2 秒（太長變刻意）。應用：旁白片讓畫面比旁白早 0.3-0.8s 切到對應 b-roll（畫面領先聲音），就是把 L-cut 用在 voice+b-roll。J-cut（下一段聲音先進）適合用在轉場前『預告』下一個主題。
- competent→master：解決教學長片/訪談感片段『一問一答很死、像 PPT 翻頁』。對 Hao 不露臉旁白片：等價做法是『旁白還在講 A 概念時，畫面已經切到 A 的視覺證據/結果』——畫面領先旁白半句，製造『理所當然又超前』的順暢感，這正是 L-cut 精神搬到旁白+b-rol…

**Dissolve = 情緒位移的量度（hard cut vs 溶接代表念頭轉換的『距離』）**  〔expert-consensus｜CapCut / ffmpeg（xfade 控制溶接時長）〕
- 做法：Murch 框架裡，hard cut＝兩個念頭緊鄰、瞬間切換（眨一下眼）；dissolve/溶接＝兩個念頭之間有『情緒或時間的距離』，畫面重疊的那段＝你在量度這個距離有多遠（溶得越長＝跨度越大、越夢境/回憶/時間流逝）。master 不是『想要柔和就加溶接』，而是用溶接長度精準表達『這兩個畫面在角色心理/時間上隔多遠』。
- 數值/出處：判準：cut＝零距離（同一念頭流）；dissolve 長度 ∝ 心理/時間距離。教學片：同概念內 0 溶接全 hard cut；章節跳轉才溶。Shorts：溶接只給時間流逝/縮時，其餘 hard cut。
- competent→master：解決『轉場特效亂加、什麼都套溶接/炫炮 transition』的業餘感。對 Hao：教學長片章節之間（真的有主題跳躍）才用溶接/轉場，同一概念內連續 b-roll 一律 hard cut；Shorts 高能段落幾乎全 hard cut，溶接只留給『時間流逝…

**『他們只記得感受』終局測試（交付前的最高層 QA 問句）**  〔expert-consensus｜通用（最高層判斷／QA）〕
- 做法：Murch 核心信念：觀眾最後記得的不是剪接、不是攝影、不是表演、甚至不是故事——是『他們當時的感受』（原話：『What they finally remember is… how they felt』）。這給 master 一個凌駕一切技術 audit 的終局測試：全片看完，閉眼問自己『我此刻的主導情緒是什麼？這是我要的嗎？』如果答得出一個清晰的情緒（驚嘆/被啟發/想動手做/好餓），且正是目標情緒——技術瑕疵大多可放。
- 數值/出處：交付前測試：全片一次看完→閉眼→用一個情緒詞答『我現在感覺？』→比對目標情緒。教學片目標情緒通常＝『原來如此＋我想試』；旅遊/美食＝『嚮往＋餓』；重機＝『熱血＋自由』。答不出或答錯＝回 emotion 層重剪，別再修細節。
- competent→master：直接命中 Hao 的 baseline 痛點：CTR 8.5%（包裝好）但留存/AVP 只 43%——觀眾點進來、但沒被『感受』勾住而留下。技術 audit（M86/M87 等）保證『沒錯』，但保證不了『有感受』。這條補上最後一層：交付前除了機械 QA，加…

_來源：www.studiobinder.com / www.premiumbeat.com / nofilmschool.com / www.musicbed.com / en.wikipedia.org / www.lrb.co.uk_

## 🪡 隱形剪輯 / 連戲 continuity

**Match on Action 對到幀（動作連戲剪接）**  〔expert-consensus ·常識｜通用（CapCut 在 timeline 上逐幀對齊兩 clip 的動作幀；ffmpeg 用 -ss 精確到幀切入點）〕
- 做法：在『動作進行中』剪，不在動作前後剪。具體做法：拍攝時讓兩個鏡位都『overlap 同一個動作』（如起身、開門、轉頭、舉杯）給足重疊素材；剪輯時找出動作在 A 鏡的某一幀，在 B 鏡找『同一個動作姿勢的同一幀』對接。關鍵是動作的『時機 timing + 方向 direction + 身體位置 body position』三者要對齊。
- 數值/出處：對齊 timing/direction/body-position 三軸；容差約 ±1 幀，差≥3 幀變連戲錯誤；B 鏡入點常往前抓 1-2 幀讓動作『早接』更隱形。原理=cut 在動作中時注意力被動作綁住。
- competent→master：解決同一動作換鏡位時的『跳接感 / 卡頓感』。讓兩個不同角度（或不同 take）的鏡頭接起來像一鏡到底。是『讓 cut 消失』最核心、最通用的一條。

**180 度線 / 軸線 / Screen Direction（螢幕方向一致性）**  〔expert-consensus ·常識｜通用（拍攝/選素材階段判斷，剪輯時靠順序與鏡像翻轉補救）〕
- 做法：在兩個主體（或運動方向）之間想像一條『軸線 axis of action』，所有鏡位只能待在線的『同一側 180 度半圓』內。效果：A 角色永遠在畫面左、看向右；B 角色永遠在右、看向左——大腦才信『他們在同一空間面對面』。運動物體同理：車往畫面右開，下一顆也要往右開，否則觀眾以為它掉頭。master 級：軸線不是死的，鏡頭可在線上左右滑，但不可瞬間跳到另一側。
- 數值/出處：軸線=兩主體連線 or 運動方向；所有鏡位待同一側 180°半圓；運動物體必須維持同一螢幕方向（往右→繼續往右）。
- competent→master：解決『換角度後觀眾搞不清空間關係 / 人物突然像在背對 / 移動物體像掉頭』的迷向感。是空間連戲（Rule of Six 第 6 條）的地基。

**合法跨越軸線：Buffer Shot / Neutral Shot / 鏡頭內轉向（master 級補救）**  〔expert-consensus｜CapCut 或 ffmpeg：在 timeline 插入 buffer/cutaway clip 當橋〕
- 做法：當你『不得不』跨到軸線另一側（素材就是這樣拍的）時，competent editor 會卡住或硬接造成迷向，master 有 4 種合法手段：①Buffer/Neutral shot——插一顆『正對鏡頭、無空間參照』的特寫（沒有左右指向）當緩衝，讓觀眾視覺重置方向感再接另一側；②Cutaway 遮接——切到旁觀者/物件/反應鏡頭，等切回來時觀眾對『先前螢幕方向』的記憶已淡化，新方向就被接受；③鏡頭內轉向——讓主體在『同一顆鏡頭內』當著鏡頭轉 180 度。
- 數值/出處：4 法：neutral/buffer 正對特寫無左右指向 / cutaway 等記憶衰退 / 鏡頭內當鏡轉向 / 攝影機橫越軸線。原理=記憶非連續（change blindness）讓方向約束軟化。
- competent→master：解決『素材已經越線、無法重拍』的補救——不必丟棄好鏡頭，也不造成迷向。這是 competent→master 的典型分水嶺：競手只會說『越線了不能用』，master 知道怎麼合法接。

**Eyeline Match（視線匹配）**  〔expert-consensus ·常識｜通用（選素材+順序，剪輯時判斷視線方向是否相交）〕
- 做法：角色 A 看向畫面外（如螢幕右下），下一顆就接『A 看到的東西』，且該物在畫面中的位置要符合 A 的視線角度與高度。對話場景：A 看右、B 看左，兩人視線在畫面外『相交』，大腦就拼出『他們對望、在同一房間』——即使兩人根本分開拍、不在現場。master 級數值：視線高度（eye-height）也要連戲——A 俯視看（視線往下）接到的 B 應是『被仰拍』的角度，否則高度不對會出戲；群戲中要精準對到『看的是哪個人』的水平角度。
- 數值/出處：A 看右/B 看左視線畫面外相交；eye-height 高度要連戲（俯視看→接仰拍對象）；群戲對到水平角度=看的是哪個人。
- competent→master：解決『接了反應/POV 鏡頭但觀眾不信兩人在同空間 / 不知道角色在看誰』。讓分開拍攝的素材黏成同一場景，也是 reaction shot 生效的前提。

**30 度規則（避免跳接的隱形保險）**  〔expert-consensus ·常識｜通用（多機/多 take 拍攝與選位階段）〕
- 做法：同一主體換鏡位時，兩個攝影機角度至少要差 30 度（且通常伴隨景別變化）。差不到 30 度就硬接，畫面只是『微微挪一點』，大腦讀成『同一顆鏡頭瞬間跳一下』=jump cut。master 級用法：①當你『故意』要 jump cut 的能量（vlog/Shorts 常用）就反過來『刻意違反 30 度』；②教學長片講解時若要『隱形地』換景別讓畫面有變化又不跳，就確保角度+景別雙雙跨過門檻。
- 數值/出處：角度差≥30°（多搭配景別變化）才隱形；<30° 硬接=jump cut；想要 jump cut 能量則故意違反。
- competent→master：解決『換角度卻像畫面抽搐/跳一下』的 jump cut 感。是 match on action 之外、單主體換鏡不跳的硬門檻。

**Graphic Match / 圖形匹配剪接**  〔expert-consensus｜CapCut/ffmpeg：選兩顆構圖相似 clip 對接，必要時微調 scale/position 對齊主體〕
- 做法：讓相鄰兩顆鏡頭『構圖元素強烈相似』再剪——形狀、線條、顏色、運動軌跡、主體在畫面的位置對齊——cut 就被『視覺相似性』吃掉、甚至產生意義隱喻。經典：2001 太空漫遊『骨頭拋向空中→切到外型/軌跡相同的太空衛星』，在骨頭旋轉中段切、兩者都是亮天空背景的長條形；阿拉伯的勞倫斯『吹熄火柴→切到升起的太陽』。master 級做法：對齊主體在 frame 的 X/Y 位置 + 大小 + 運動方向，並選『背景乾淨對比一致』的兩幀。
- 數值/出處：對齊形狀/顏色/軌跡/主體 X-Y 位置+大小；在運動中段切；選乾淨一致背景。2001 骨頭→衛星、Lawrence 火柴→太陽。
- competent→master：解決『轉場生硬 / 只能靠 CapCut 罐頭轉場特效』。用構圖本身過場=高級感、可壓縮時空、可植入隱喻。是『不用特效的特效』。

**Cutaway 遮接 / 隱形時間壓縮**  〔expert-consensus ·常識｜CapCut/ffmpeg：在主軌剪接縫上方疊 B-roll cutaway 蓋住跳接（=Hao M87 對位機制）〕
- 做法：切到『主動作之外』的相關鏡頭（旁觀者反應、手部特寫、物件、時鐘、環境）1-3 秒，再切回主動作『較晚的時間點』——觀眾把這當連續，看不到中間被剪掉的時間。區分：Insert=場景『內』的細節（角色的手、計時炸彈）；Cutaway=場景『外』的東西（人群反應、牆上時鐘）。
- 數值/出處：cutaway=場景外（旁觀/時鐘）vs insert=場景內細節（手/物）；時長 1-3 秒；要有觀眾本就想看的『動機』才隱形；用途=壓縮時間/藏 NG/修連戲/越線 buffer。
- competent→master：解決『剪掉中間段落造成的時間跳 / 口白接縫嘴型跳 / 要藏 NG 結巴 / 連戲穿幫』。是教學長片『去聲後接縫隱形』與『壓縮冗長過程』的主力工具。

**Walter Murch《In the Blink of an Eye》Rule of Six（決定一個 cut 好不好的優先順序）**  〔expert-consensus ·常識｜通用心法（套用在任何 cut 點決策；CapCut/ffmpeg 皆適用）〕
- 做法：判斷『該不該在這切、切得對不對』的 6 條優先級（加權，不等權）：①情緒 Emotion（51%，比下面五條加起來還重）②故事 Story（推進敘事）③節奏 Rhythm（這一刻在節奏上對不對）④Eye-trace 眼動引導（觀眾的注意力此刻在 frame 哪個位置）⑤Planarity 平面性（2D 構圖文法的連貫）⑥3D 空間連續性。Murch 鐵律：『要犧牲就從下往上犧牲』——寧可破壞空間連續（第6）也不破壞情緒（第1）。
- 數值/出處：6 條加權優先：情緒51%>故事>節奏>eye-trace>planarity>3D 空間；犧牲從低階往高階走，絕不為空間連續犧牲情緒。眨眼=念頭結束=可接受切點。
- competent→master：解決『規則互相打架時該保哪個 / 為什麼有些違規的剪接反而好看 / 到底該在哪一幀切』。把零散連戲規則整合成一套有優先級的決策系統——這是 master 的元框架。

**為什麼觀眾看不到剪接點：Attentional Theory of Cinematic Continuity（Tim Smith 認知科學）+ Edit Blindness**  〔data-backed｜通用（剪輯時對齊相鄰 clip 焦點像素位置；在預期動作瞬間下刀）〕
- 做法：master 級的『理論為什麼』：人眼/大腦根本不維持完整連續的世界表徵（change blindness 變化盲視）——所以 cut 造成的視覺斷裂只要不『搶走注意力』就偵測不到。
- 數值/出處：AToCC 三條件：cut 不奪注意力(eye-trace 焦點位置連貫)+假設存在恆常性+符合下一步預期；Edit Blindness=cut 撞眨眼/saccade(視覺抑制)或 inattentional blindness。可量化做法：對齊相鄰鏡頭視覺焦點的 X-Y 螢幕位置。
- competent→master：解決『憑感覺剪、不知道為什麼有時 cut 明顯有時隱形』。把『隱形』從玄學變成可控變量：對齊注意力焦點位置 + 順著觀眾預期切 = 可重複地讓 cut 消失。這是 competent→master 最深的一層——懂機制就能主動設計隱形。

_來源：howtofilmschool.com / help.editmentor.com / en.wikipedia.org / learnaboutfilm.com / scriptandpad.com / www.filmmakersacademy.com_

## 🎵 配樂剪輯精修（一秒變專業最大槓桿）

**Equal-Power（等功率）crossfade 接段，不要 linear — 這是「無縫接歌」的物理核心**  〔data-backed｜ffmpeg: acrossfade=d=2:c1=qsin:c2=qsin（接不同段）；CapCut 內建 crossfade 轉場已等功率〕
- 做法：把一首歌剪短／拼段時，competent editor 用 linear（直線）淡入淡出，結果接縫處兩段各掉到 -6dB → 中點音量「凹一個洞」聽得出破綻。master 用 equal-power（等功率）曲線：中點只衰減 -3dB，兩段功率和恆定，人耳完全聽不到接點。物理原因：不相關的兩段音樂（uncorrelated），功率相加而非振幅相加，所以要 -3dB 不是 -6dB。
- 數值/出處：linear 中點 -6dB（會凹洞）vs equal-power 中點 -3dB（恆定功率）。ffmpeg curve：tri=linear（預設、會凹），qsin/hsin=近等功率（接不同段用這個）。Sound on Sound + Audacity Manual 明載：相同素材用 linear，不同歌用 equal-power。
- competent→master：接段「中間音量凹一下」「聽得出兩段是拼的」「淡接處悶悶的一秒」「歌剪短後接縫不順」。

**ffmpeg acrossfade 精準接段（官方參數 + 接多段串接）**  〔data-backed｜ffmpeg acrossfade + atrim + asetpts〕
- 做法：acrossfade 的真正威力是「自動 concat + 在接縫處 crossfade」串接多段，等同 concat 但無縫。關鍵參數（官方文件）：d=（duration，覆蓋 nb_samples，直接寫秒數最直覺）；o=（overlap，預設 enabled，讓第一段尾與第二段頭重疊）；c1=/c2=（兩段各自的曲線）；inputs=n（一次串多段）。
- 數值/出處：官方參數 d（duration）覆蓋 ns；o（overlap，預設開）；c1/c2 曲線；inputs 串多段。drop 接點 d=0.1~0.3、verse 情緒接 d=1.5~3。先轉 WAV 中間檔避免 MP3 padding 爆音。範本：[0]atrim=0:18,asetpts=N/SR/TB[a];[1]atrim=60:90,asetpts=N/SR/TB[b];[a][b]acrossfade=d=0.25:c1=qsin:c2=qsin
- competent→master：「歌比片長，硬 fade out 很廉價」「想跳過冗長 verse 直接到副歌但接縫爆音」「兩首歌串成一條 BGM 接縫卡」「MP3 接點有 tick 雜音」。

**Cut on the phrase, not the beat — 在「樂句」邊界剪（4/8 小節），不是在每個 beat 上剪**  〔expert-consensus｜CapCut 手動 beat markers（tap 在句尾下拍）；ffmpeg atrim 按算出的小節秒數切〕
- 做法：competent editor 的天花板就是「卡到 beat」；master 的差距在「卡到 phrase（樂句）」。音樂以 4 小節成一句、8 小節成一段，副歌／build 幾乎都落在 8 小節邊界。剪歌（縮短／loop）一定要在整句結束、下一個『1』拍之前下刀 —— 在樂句中間切，潛意識會「覺得怪」即使說不出哪裡怪。實作：以 8 小節（或半句 4 小節）為單位 loop / 刪段，drop 永遠對到段落第一個下拍（downbeat）。
- 數值/出處：4 小節=一句，8 小節=一段；下刀點=樂句結束、下一『1』拍之前。drop 對 downbeat。120 BPM 下 8 小節≈16 秒、4 小節≈8 秒，可直接換算切點秒數。
- competent→master：「卡 beat 了但整體還是覺得鬆散」「BGM 剪短後雖然接上了但聽起來『斷句斷錯地方』」「換段落音樂感覺被打斷」。

**Music as emotional spine — 先鋪音樂（temp track）再剪畫面，讓音樂結構驅動剪輯**  〔expert-consensus ·常識｜通用工序（CapCut/ffmpeg 皆適用）：時間軸先鋪音樂再排畫面〕
- 做法：電影業標準工序：editor 先放 temp music（暫定配樂）當情緒骨架，畫面剪輯去「貼合音樂的 flow」，而不是剪完再硬塞 BGM。這顛倒了業餘的順序。Walter Murch 把剪輯排序為情緒 51% > 故事 23% > 節奏 10%（Rule of Six）—— 情緒幾乎是其他全部加起來的兩倍，而音樂是控制情緒最直接的桿。
- 數值/出處：Murch Rule of Six 權重：情緒 51% / 故事 23% / 節奏 10% / eye-trace 7% / 平面 5% / 立體空間 4%（出自《In the Blink of an Eye》）。工序：temp track 先行→畫面貼音樂。動作段 ~25 cuts/min、對話段 ~6 cuts/min（Murch）當節奏基準。
- competent→master：「片子資訊都對但就是沒有起伏／平」「BGM 像背景白噪音、沒有帶情緒」「高潮畫面沒有被音樂托起來」。

**Spotting / hit points — 把畫面關鍵事件對到音樂的『擊點』**  〔expert-consensus｜CapCut beat markers + 手動微調剪點到 frame；ffmpeg 用精確秒數對齊 overlay/cut〕
- 做法：film scoring 的 spotting session：標出 hit points（音樂該與畫面事件精準對齊的點），這些點要『數學式精算』對齊。video editor 借用：列出片中所有「該被音樂打中」的瞬間 —— logo 出現、數據揭曉、轉折金句、demo 成功那一刻、Short 的產品 reveal —— 然後移動音樂或微調剪點讓 drop/impact 正好落在那一格。
- 數值/出處：hit point 要 frame-accurate（30fps 下 1 格=33ms）。Murch 驗證法：同剪點剪三次落在同一 frame 才算抓到節奏。先列 hit list 再對音樂。
- competent→master：「reveal 跟音樂差半秒、爽感打折」「logo/數據出來時音樂沒撐住」「感覺差一點點但說不上來」。

**Tension build：riser + 高通濾波掃頻堆張力，drop 才有釋放感（build-and-release）**  〔expert-consensus｜ffmpeg highpass 自動化（highpass=f=… 配 volume 包絡）+ aecho/reverb；CapCut 音效庫 riser + 關鍵幀音量〕
- 做法：EDM/trailer 的核心動力學是 tension-and-release。
- 數值/出處：build 段 high-pass cutoff 往上掃→drop 放回全頻（先抽低頻才有爆滿）；reverb 乾→濕自動化；+8~12kHz 加空氣感。riser 通常 2–4 秒接 drop。
- competent→master：「重點來了但很平、沒有『噹』的感覺」「數據/結論揭曉沒有儀式感」「Short 的高光段不夠抓人」。

**Stop-down：drop 到完全靜默當對比 —— 全片至少 2–3 個歸零點**  〔expert-consensus｜ffmpeg：volume=0 包絡 / atrim 切出靜默段 / aselect；CapCut：音量關鍵幀拉到 0 或分割刪段〕
- 做法：trailer 編曲鐵則：一支張力片至少要有 2–3 個強 stop-down（音樂瞬間歸零到完全靜默），尤其在每一幕結尾。靜默不是『沒聲音』，是『對比』，而對比才驅動情緒 —— 在大 reveal 或標題卡前把音樂砍掉、twist 後 hold 住讓它沉澱。原理：人耳對動態範圍（最大聲↔最小聲的落差）的敏感度遠高於絕對音量；一段全力後接 0.5–1 秒靜默，下一個 impact 會「顯得更大」即使音量沒變。
- 數值/出處：trailer 標準：每片 2–3 個 stop-down，每幕結尾各一個全靜默。reveal/標題前砍音樂 0.3–1s。動態範圍對比 > 絕對音量。
- competent→master：「BGM 一路到底、整支同一個情緒高度、聽到後面麻痺」「reveal/金句沒有重量」「片子很滿但沒有呼吸」。

**選曲：BPM × Energy × 情緒對題材（不是憑感覺挑好聽的）**  〔data-backed ·常識｜曲庫 BPM/mood filter 選曲；ffprobe/曲庫 metadata 讀 BPM；先選曲再定剪輯節奏〕
- 做法：master 選曲是三維對齊不是『挑一首順耳的』。(1) BPM 對應能量／心率：60–90 內省/放鬆/夢幻（美食 mukbang、旅遊空景、重機巡航日落）；90–120 慵懶但有勁（一般 vlog、生活流）；120–150 衝刺感（重機加速、剪輯快切、AI 工具 demo 的『手速』段）。(2) Energy score（多數曲庫 0–1）對應段落強度，低能量鋪陳、高能量推高潮。
- 數值/出處：BPM 帶：60–90 內省/放鬆；90–120 慵懶有勁；120–150 衝刺（EDM/dance）。100–130 BPM=身體自動同步甜蜜區（≈輕運動心率，neuroscience entrainment）。Energy 0–1 對段落強度。曲庫（Artlist 等）可同時 filter BPM+mood+genre，範圍 20–200。
- competent→master：「選的歌好聽但跟畫面節奏對不上」「旅遊空景配快歌很燥」「demo 手速段配慢歌很拖」「不知道該選多快的歌」。

**Anticipation cut（提前剪）+ 不全卡點 —— 別把每一刀都釘死在 beat 上**  〔expert-consensus｜CapCut 手動微調剪點（不全靠 Auto Beat Sync）；ffmpeg 精確秒數錯位剪〕
- 做法：頂尖 music video editor 反而刻意『不要每刀都精準卡 beat』：在動作/揭曉前提早半秒以上進那個鏡頭，先建立場景、製造懸念，等動作正好落在音樂大點上 → 觀眾得到『先期待、後釋放』的爽感，比『動作與剪點與 beat 三者同時』更有戲。流程上他們先順著歌詞/旁白折出剪點（軟化流動），最後一遍才在 beat 上打標點（punctuation）。
- 數值/出處：提前進鏡頭 ≥0.5s 建立懸念，讓動作落在大點。兩 pass：先順歌詞/旁白語意折剪點（軟化）→ 末 pass 才在 beat 上打標點。用 syncopation 避免機械感。
- competent→master：「每刀都卡 beat 但看起來像節拍器、很死板機械」「太工整反而沒戲」「揭曉瞬間少了懸念」。

**辨識歌曲結構 + CapCut/手動 beat grid 把段落地圖化**  〔expert-consensus ·常識｜CapCut Auto Beat Sync + 手動 tap markers + snap；ffmpeg/ffprobe RMS/能量掃描找 drop〕
- 做法：重組一首歌前要先『讀懂結構』：intro（鋪陳）→ verse（敘事，能量中低）→ pre-chorus/build（上升）→ chorus/drop（高潮，能量最高、織體最厚）→ break（喘息/靜默）→ outro（收尾）。辨識訊號：drop 前常有 riser/鼓花/靜默，chorus 織體最滿、低頻最重。把這張地圖標到時間軸後，縮短就刪 verse/重複段、保留 build→drop；接 outro 收尾。
- 數值/出處：結構訊號：drop 前有 riser/靜默；chorus 織體最厚低頻最重。CapCut 右鍵 Auto Beat Sync（掃峰值自動標）+ 手動 tap beat grid（不依賴偵測）+ clip 邊緣 snap marker。縮短策略：刪 verse/重複，留 build→drop→outro。
- competent→master：「不知道一首歌哪裡是高潮、哪裡能刪」「Auto Beat Sync 抓的點不準/抓太多」「歌剪短後結構亂掉」。

_來源：www.soundonsound.com / manual.audacityteam.org / ffmpeg.org / filmdaft.com / www.vegascreativesoftware.com / www.studiobinder.com_

## 🔊 進階 Sound Design

**Sound Bridge / J-cut & L-cut（聲音先過場縫合）**  〔expert-consensus｜CapCut（分離音訊+左右錯位拖動）/ ffmpeg（afade + adelay）〕
- 做法：讓下一場的聲音先進來（J-cut，聲音領先畫面）或上一場的聲音延續到下一畫面（L-cut，聲音拖尾）。原理：耳朵的「轉場閾值」比眼睛低，先聽到下一場環境聲，視覺剪點就被「軟化」成隱形。在 NLE timeline 上音軌比視訊軌前/後伸出，形狀像 J 或 L，故得名。
- 數值/出處：J-cut：讓 B 場 ambience 提前 12–24 frames（約 0.4–0.8s @30fps）淡入；對白場景用 L-cut 讓 A 角色尾音壓到 B 畫面再收，不超過一句的尾音。CapCut：該段音訊 detach 後左右錯位，視訊不動。ffmpeg：對 ambience 用 adelay 負偏移(提早起點) + afade=t=in:d=0.6 疊在前一段尾巴。
- competent→master：competent editor 的硬切每一刀都被看見、節奏一頓一頓；master 用 J/L-cut 把視覺剪點藏在聽覺連續性底下，整支片變成一條不斷的聽覺河流。這是差距最廷錢、最常被業餘漏掉的一條——Hao 的旅遊 vlog 場景切換（夜市→廟→海）最…

**Worldizing（聲音「世界化」— Walter Murch）**  〔expert-consensus｜ffmpeg afir（convolution / IR 卷積）— 取代演算法 reverb〕
- 做法：把乾淨錄音（音樂、對白、UI 提示音）用喇叭在『真實空間』放出來，再用麥克風隔一段距離重錄，讓聲音染上該空間的反射、距離與不完美，再與原乾淨軌『並存疊在一起』（不是換掉）。Murch 在《美國風情畫》《現代啟示錄》首創，目的是讓聲音『暴露在畫面所示世界的聲學裡』。
- 數值/出處：落地版（1）網上免費庫（如 OpenAIR）抓真實空間 impulse response（隧道/教堂/房間 IR）（2）ffmpeg `afir` 把乾聲過一遍卷積（3）與乾聲混：dry 100% + wet，近景 wet 15%、遠景/空間感 wet 30–40%（wet 越高=越遠/越在那空間）。關鍵：乾軌與髒軌並存，不是取代。
- competent→master：competent editor 把任何聲音都丟乾淨的數位演算法 reverb，聽起來都『貼在玻璃上』、很塑膠；master 讓聲音真的活在那個空間裡。Hao 沒真空間重錄也能做數位版 worldizing——重機引擎聲、夜市叫賣『世界化』後才有現場感。

**Law of Two-and-a-Half / Dense Clarity（Murch 同色聲音上限）**  〔expert-consensus｜概念規則（任何 NLE / ffmpeg mix 決策皆適）〕
- 做法：Murch 在 THX-1138 發現：同一『顏色』（同類別、同概念光譜）的聲音，觀眾耳朵最多只能個別追蹤『不到三層』——1 個腳步、2 個腳步還能分辨，3 個以上大腦放棄個別分析、整組變成像一個『和弦』。他追求同時擁有 Clarity（聽得到個別元素）與 Density（聽得到整體厚度）的甜蜜點。
- 數值/出處：盤點 mix 裡的聲音『顏色』：對白=一色、腳步/Foley=一色、環境=一色、音樂=一色、SFX 重點=一色。同一色前景音 ≤2 個清晰，第 3+ 個群組化(壓低/混響/當底噪)。不同色不受此限——對白+音樂+環境可同時清楚。
- competent→master：competent editor 把 10 層音效全堆滿想顯豐富，結果糊成一坨泥；master 知道同色聲音只留 2.5 層細節、其餘打包成『一團』。Hao 的夜市/市場素材聲音層尤其受用——不是越滿越好。

**Designing FOR sound — 留白讓聲音說話（Randy Thom）**  〔expert-consensus｜剪接決策層（CapCut / ffmpeg 皆適）〕
- 做法：Skywalker Sound 的 Randy Thom 核心論點：聲音的威力不是來自『做出厲害的聲音』，而是來自畫面有沒有『留位置』給聲音。最強的聲音段落幾乎都是 POV（主觀視角）段落——鏡頭 hold 住、角色在『聽』世界、不過度剪接時，聲音才有空間變強。Alan Splet：「Sound is a heart thing」——觀眾用情緒(不是智力)解讀聲音。
- 數值/出處：Thom 具體規則：(1) 對白結束後/開始前刻意 linger 一個鏡頭給聲音呼吸。(2) 給角色『聽』的鏡頭，觀眾才被允許一起聽。(3) 同聲音『遠處 vs 近處』對比是強元素(先遠後近=拉近)。(4) 別把所有空檔塞滿——『要塞滿機智對白，那你該去寫舞台劇』。
- competent→master：competent editor 把每一秒塞滿對白/grunt/滿版音樂，聲音永遠是背景填充；master 故意在剪接上留出『角色聆聽』的鏡頭與空拍，讓一個聲音能被聽見。差距在剪接決策層，不在音軌層。Hao 教學長片：講完重點後 hold 0.5–1s 純…

**Silence as a tool — 動態範圍懸殊化（靜默當樂器）**  〔expert-consensus｜ffmpeg afade（全層淡出留 roomtone 墊底）〕
- 做法：刻意製造『接近全靜』的瞬間（保留極微的呼吸/風/電流嗡聲，不是 -inf 死寂），讓之後的音樂/重拍/揭露獲得全部衝擊力。威力來自對比：靜默給聲音『所有的力量與份量』。常放在 hook 後、戲劇性揭露後、或動作高潮收尾後。
- 數值/出處：揭露『前』0.3–0.8s 把所有前景層 afade out 到只剩 -45～-50 LUFS 的 roomtone，揭露『瞬間』重拍/音樂全進。永遠留一條極低音量 roomtone 墊著，避免聽感斷訊——不要讓『靜默』真的 0 取樣。
- competent→master：competent editor 全片 loudness 壓得一樣大聲、wall-to-wall BGM，於是沒有任何一刻有衝擊力(耳朵疲勞)；master 用『靜默→爆發』的動態落差製造記憶點。關鍵：影片『靜默』≠數位歸零(那聽起來像斷訊)，而是只剩一層…

**Risers / Impacts / Sub-drops — 重點前的張力工程**  〔data-backed｜ffmpeg / CapCut 疊 SFX 軌（riser + impact + sub）〕
- 做法：在『重點/數據揭露/轉場』之前用 riser(音高/亮度/頻率往上爬升)鋪張力，揭露瞬間用 impact(一擊脈衝)或 sub-drop(低頻下沉)落地兌現。Riser 常從低頻 60–150Hz 起、爬升到 3–10kHz；強的 build 會疊 3 種不同 riser(白噪掃頻+音高滑升+節奏加密)。
- 數值/出處：短 riser decay 2–3s、長 riser 6s；riser 起點對齊揭露前 2–4s。impact/808 短擊 ≈ 揭露 downbeat 那一 frame；sub-drop 長尾 500ms–2s decay。進階：揭露『前』一拍插入極短靜默(beat of silence)再 impact，落差最大。
- competent→master：competent editor 的重點就是字卡蹦出來、沒有聽覺事件；master 在重點前 2–4 秒就開始『聽覺倒數』，觀眾身體先被預告『大事要來』，揭露時的滿足感(payoff)翻倍。這是 Hao 教學長片『真重點/數據→有質感動畫』的聲音另一半。

**Synchresis — 聲畫焊接 / Added Value（Michel Chion）**  〔expert-consensus ·常識｜CapCut / ffmpeg frame-accurate SFX 對位〕
- 做法：Chion《Audio-Vision》核心：一個聲音與一個畫面動作『同步』出現時，大腦自動把兩者『焊』成一個不可分事件(synchresis=synchronism+synthesis)，並產生 added value——聲音把情緒/資訊『偷渡』進畫面，讓觀眾以為那資訊本來就在畫面裡。關鍵自由度：『一個榔頭畫面，一百種聲音都成立』。
- 數值/出處：每個明確視覺『事件』(字卡進場、icon 彈出、轉場、鏡頭撞擊)都焊一個 SFX 在同一 frame(±1 frame 內，越準越焊得牢)。選聲音照情緒不照寫實。沒同步點的長鏡頭反而靠 ambience 鋪底。
- competent→master：competent editor 找『正確』音效對嘴；master 知道同步點才是焊接關鍵，於是自由選『情緒對』的聲音而非『寫實』的(一拳可以是西瓜爆裂+低頻)。Hao 的 KenBurns 照片動畫、字卡彈出、UI 點擊——每個視覺事件 frame-ac…

**Foley 分層設計（不只腳步—情緒化物件聲）**  〔expert-consensus｜CapCut / ffmpeg 多層 SFX 軌疊加〕
- 做法：Foley 不是補真實，是『喚起那個聲音的感覺』。master 的 Foley 是分層的：一個動作疊多個錄音(布料摩擦+一聲悶腳步+金屬微響)，讓單一聲音飽滿可信；且帶演技——『拖拍的腳步=猶豫、外套猛甩=焦躁、手放上道具=掌控』。標準軌：腳步 L/R、布料、道具、impacts、sweeteners、roomtone。
- 數值/出處：分層公式：一個重點動作 = 主體聲(寫實) + 質感層(布料/液體/摩擦) + sweetener(誇張化情緒的一層，常 pitch 下移或加亮)，每重點動作 ≥2–3 層。close-up 把 Foley 推到前景音量、wide 鏡頭壓低=自動製造『近/遠』空間感。
- competent→master：competent editor 用單一罐頭音效一個蘿蔔一個坑；master 把『拿起咖啡杯』拆成手指接觸+杯底離桌+液體晃動三層。Hao 重機題材：引擎=低頻轟鳴+排氣脈衝+金屬機械聲分層疊出來；美食題材：『咬下』可疊脆裂+濕潤+呼氣三層 sweeten…

**Ambient Sound Bed / Room Tone 連續墊底（縫合一切）**  〔expert-consensus ·常識｜ffmpeg amix（全片 atmos bed + crossfade 換場）〕
- 做法：在所有對白/音效『底下』鋪一條連續、低於知覺門檻的環境聲(room tone / atmos)。它的真正功能是『縫合』——把來自不同 take、不同素材、剪接造成的聽覺破口全部抹平，讓拼貼變成一個連續空間。沒有它，剪點處會有微小的『空氣感跳動』洩漏剪輯痕跡。
- 數值/出處：選/生一條與場景相符的 atmos(室內=房間 tone、戶外=遠處交通+風)，全程鋪在最底層，音量比對白低 25–35dB(聽得到但不被注意)。ffmpeg amix 一條低增益 ambience loop 墊全片；跨場景換 bed 用 crossfade 0.5–1s 不要硬切。多層 atmos > 單層。
- competent→master：competent editor 剪點之間音底『一卡一卡』(每段素材底噪不同)；master 全程鋪一條統一 atmos bed，所有剪點消失。Hao 混雜素材(手機+OBS+stock b-roll)最致命的破口就在這——一條統一 bed 立刻把混雜感抹…

**聲音調音到音樂調性（Tuning SFX / Ambience to key）**  〔anecdotal｜ffmpeg rubberband / Melodyne — pitch-shift 不變速〕
- 做法：把環境聲、riser、UI 音效、甚至引擎嗡鳴用 pitch-shift 調到與背景音樂『同一個調/和聲相容的音』，讓 SFX 與配樂融成一體而非互相打架。進階：ambience 過 pitch-shifter 再進 reverb(reverb 蓋掉 pitch 假影)，整個聲景變成配樂的延伸。
- 數值/出處：找出 BGM 調(很多 stock music 標 key，或用 tuner 抓主音)。把持續性 SFX(嗡鳴、riser、wind drone)pitch-shift 到該調根音或五度；tuning 只調到所選音階/和弦的音(例：D 小調只調 D-F-A)。ffmpeg：asetrate/aresample 或 rubberband 做不變速 pitch-shift。
- competent→master：competent editor 的音效與 BGM 各彈各的、頻率打架聽起來毛躁；master 讓嗡鳴/底噪/riser 落在音樂調性上，整個 mix 瞬間『和諧』、高級感拉滿。這是電影感的隱形武器——觀眾說不出哪裡不一樣，但就是更貴。

_來源：www.studiobinder.com / spotlightfx.com / transom.org / www.filmsound.org / kottke.org / thesounddesignprocess.com_

## 🎨 進階二級調色 secondary

**Qualifier(HSL Key)圈選局部 + 三段微調順序：寬度→高低點→柔邊**  〔expert-consensus｜DaVinci Qualifier；CapCut：用『曲線-HSL』分色相通道近似（只能調單一色相不能複合 key）；ffmpeg：selectivecolor 濾鏡（仿 Photoshop 選取色彩，依 reds/yellows/greens 等色域+飽和純度調 CMYK）或 hue/colorchannelmixer〕
- 做法：二級調色的核心：不是調整整個畫面，而是用 HSL Qualifier 依『色相/飽和/亮度』把畫面某一塊（膚色、天空、某件衣服）摳出來單獨 grade，其餘不動。Noam Kroll 的職業微調順序固定：①先調 color key 的 width（色相寬度）②再調 high/low points（亮度上下界）③最後調 softness（柔邊）。摳完按 SHIFT+H 切換『選區黑白檢視 / 正常畫面』反覆確認漏沒漏。
- 數值/出處：selectivecolor 範例：ffmpeg -i in.mp4 -vf "selectivecolor=reds=.1 0 0 0:yellows=0 0 -.1 0" out.mp4（reds 加青、yellows 減黃）。CapCut HSL 曲線：選『橙』通道單獨降飽和=只壓膚色不動其他
- competent→master：competent editor 只會整片套 LUT / 拉 color wheel（一級）；master 的差距=能把『膚色暖一點但天空不動』『紅衣服改成藍但臉不變』這種選擇性局部控制。沒有 qualifier 思維，畫面永遠是一坨整體被推，無法做出職業…

**Power Window 空間圈選 + 動態追蹤(tracker)鎖臉**  〔expert-consensus｜DaVinci Power Window + Tracker；ffmpeg 近似：maskedmerge（geq 畫遮罩→把 graded 版與原版依遮罩亮度混合）；靜態圈選可用 drawbox/geq 橢圓遮罩，動態追蹤 ffmpeg 無內建（要外部追蹤或逐段 keyframe）〕
- 做法：Power Window 是『用形狀(橢圓/方/自訂貝茲)圈一塊區域』而非用顏色摳——適合天空、臉、暈影。職業關鍵兩步：①羽化(feather/softness)拉大讓圈選邊緣無縫融入（硬邊=一眼假）②人臉/移動主體必用 tracker 把 window 黏住臉移動，否則人一動 grade 就露餡。
- 數值/出處：ffmpeg maskedmerge 橢圓羽化遮罩：color=black:s=1920x1080,format=yuv444p,geq='lum=255*(1-sqrt((X-W/2)^2+(Y-H/2)^2)/sqrt((W/2)^2+(H/2)^2)):cr=128:cb=128'[mask]; 再 [原版][graded版][mask]maskedmerge。白=顯示graded、黑=顯示原版、灰=漸變羽化
- competent→master：competent editor 做局部=硬邊遮罩、人一動就穿幫；master=羽化+追蹤讓局部調整全程隱形，觀眾完全感覺不到你動過手腳。『看不出修過』才是 secondary 的最高標準。

**Shot Matching to Reference：先中性化→對比/飽和/色平衡定序 + 雙片比對 wipe**  〔expert-consensus｜DaVinci Stills Gallery + reference wipe + scopes；CapCut 無 wipe，靠並排匯出比對；ffmpeg：hstack 兩片並排比對、或 blend=difference 看差異〕
- 做法：把不同鏡頭/不同相機的素材調成一致(unified timeline)是職業調色師最耗時的工作。Mixing Light『Patrick 工作流』的固定順序：80% 情況=①設對比 ②設飽和 ③設色平衡；20% 色偏嚴重時=①先粗修色平衡 ②對比 ③飽和 ④再精修色平衡。職業鐵則：先把每顆鏡頭各自『中性化(neutralize)』再做配對——中性過的素材彼此配對『快得多、好得多』，不要拿原始狀態硬配。
- 數值/出處：ffmpeg 並排比對參考圖：ffmpeg -i shot.mp4 -i ref.png -filter_complex "[1]scale=iw/2:ih/2[r];[0][r]overlay=W-w:0" cmp.mp4。差異檢視：blend=difference（全黑=完全一致）
- competent→master：competent editor 逐顆鏡頭『各調各的好看』但放一起跳色；master=有 timeline 一致性的系統流程（先中性化再配對），且知道對比/飽和/色平衡的先後不能亂。這是『單片好看』到『整片一致』的鴻溝。

**Vectorscope 膚色線(I-line / Skin Tone Line)+ 雙 scope 配對法**  〔data-backed｜DaVinci/CapCut 內建示波器；ffmpeg：-vf vectorscope=mode=color3 與 waveform 濾鏡可即時疊在畫面上檢查〕
- 做法：Vectorscope 上約 10:30 鐘點方向有一條對角線=膚色線，物理意義=皮下血液的通用色相。所有人種的健康膚色色相都該落在這條線上或很靠近——『人種差異不在色相，在亮度(看 waveform)』。歷史上它叫 I-line（NTSC 編碼最敏感的色相軸，剛好≈膚色）。職業配對最低配置：同時開 Waveform + Vectorscope；認真做色平衡時再加 RGB Parade。
- 數值/出處：ffmpeg 疊膚色示波器檢查：ffmpeg -i in.mp4 -vf "vectorscope=mode=color3:graticule=color,format=yuv422p" -frames:v 1 scope.png（看主體膚色點是否落在 10:30 對角線）。RGB Parade 目標=暗部三通道底部齊、白部頂部齊
- competent→master：competent editor 靠肉眼判斷膚色『好像怪怪的』但說不出哪裡錯、也修不準（螢幕沒校色就完蛋）；master=用膚色線當客觀錨點，任何膚色偏綠/偏洋紅一秒看出+知道往哪推。肉眼會被環境光騙，scope 不會。

**Node / Layer 思維：serial(串) vs parallel(並) vs Layer Mixer(混合模式)**  〔expert-consensus｜DaVinci node graph；CapCut：用多層『調整圖層』堆疊近似 serial、不同圖層套混合模式近似 Layer Mixer；ffmpeg：filter_complex 的鏈接順序=天然 serial，split+blend=parallel/layer mixer〕
- 做法：職業調色的底層心智模型=node tree 的『資料流順序』。Serial node=上一個的輸出當下一個的輸入，順序決定運算先後；Parallel node=多個 node 吃同一個源、效果並聯混合；Layer Mixer=可在 node tree 內用合成模式(Screen/Multiply/Overlay)疊圖層。
- 數值/出處：ffmpeg parallel/layer mixer 心智=split 成多路各自處理再 blend 合回。範例骨架：[0]split=2[a][b];[a]curves=...[a2];[b]eq=...[b2];[a2][b2]blend=screen。順序鐵則：一級(曝光白平衡)的 eq/curves 放最前，secondary 的 selectivecolor 放中段，halation/grain 放最後或最前(依底片邏輯放最前)
- competent→master：competent editor 把所有調整堆在一個調整圖層上互相打架（降了飽和又想救某色救不回）；master=用 node/layer 把每個意圖隔離成獨立節點，可單獨開關、可調混合不互相污染，且懂『運算順序=最終結果』。這是從『一鍋亂燉』到『可控管線…

**色彩心理 / 母題色(motif color)：用單一顏色貫穿敘事 + 飽和/對比=情緒槓桿**  〔expert-consensus ·常識｜概念層→任何工具皆可執行；建一個 3-5 色的固定 palette 寫進 CapCut/ffmpeg 預設，跨片重用=signature〕
- 做法：master 級不是『teal-orange 好看就套』，而是用色彩當敘事工具。Noam Kroll 的三個情緒槓桿：①暖(橙)=邀請/柔軟，冷(藍)=臨床/生硬 ②高飽和=擴張誘人，去飽和=蕭瑟收窄(逼觀眾看構圖) ③對比直接=張力（高對比=緊繃，低對比=夢境）。進階心法=intentional subversion：故意用暖色製造虛假平靜，再被劇情翻轉。
- 數值/出處：執行=先在腦中/mood board 定情緒再調，不要機械套公式(Kroll：『follow your gut』)。signature 操作化：固定一組『暗部推某色相+亮部推互補色+某去飽和量』數值，存成 ffmpeg 預設或 CapCut 調色檔，每支片套同一組=觀眾認得出『這是你的片』
- competent→master：competent editor 把調色當『讓畫面好看的最後一步』；master 把色彩當『第二套劇本』——每個顏色都有動機(motivation)、服務角色弧線、能在觀眾無意識層面埋伏筆。這是『調得漂亮』到『調得有意義/有記憶點』的差距，也是 signa…

**Day-for-Night：中間調主導降光+冷藍偏洋紅 + 暗部單獨去飽和 + 保留實用光源**  〔expert-consensus｜DaVinci color wheels + window；CapCut 調色面板；ffmpeg：curves(降midtone)+colorbalance(推冷)+eq(去飽和)+ 對實用光源用 maskedmerge 保留〕
- 做法：把白天素材變夜晚的職業配方(Noam Kroll)：①降光以『中間調為主力』先把 midtones 大幅拉下、再降 highlights，最後把 shadows 微微提一點救暗部細節(降對比) ②色平衡『中間調推冷+微洋紅(月光感)』，亮部暗部再微調跟著冷下來——中間調做大部分工作，亮暗部只做二次精修 ③暗部若殘留過飽和的雜色，只對 shadow 區去飽和(整體再大幅去飽和，因為真實黑暗中眼睛看到的顏色很淡)。
- 數值/出處：ffmpeg 近似：curves=m='0/0 0.5/0.32 1/0.78'(壓中間調與亮部)，colorbalance=ms=-0.1:mm=0.05:mh=-0.06(中間調推藍+微洋紅)，eq=saturation=0.55(整體去飽和)。實用光源保留=先 maskedmerge 把窗戶區域用原版蓋回。Kroll 免費 day-for-night LUT 在 cinecolor.io
- competent→master：competent editor 直接整片壓暗+套藍=塑膠假夜、一坨死藍；master=中間調主導、暗部去飽和、保留實用暖光源，做出『有層次、可信』的夜。差距在『懂光在真實夜晚如何衰減+眼睛在暗處的色彩感知』而非無腦套藍。

**Halation / Glow / Bloom 底片質感：摳亮部→高斯模糊→暖紅染色→screen/lighten 疊回**  〔expert-consensus｜DaVinci(摳亮部 node 放最前+gaussian blur+紅 tint+composite Screen)；CapCut 無原生，靠複製圖層+模糊+變亮混合模式近似；ffmpeg：split+lutyuv摳亮部+gblur+colorbalance染紅+blend=screen/lighten〕
- 做法：三者要分清楚：Bloom=整張柔光暈散(夢幻)；Halation=只在『高反差亮部邊緣』的暖紅/琥珀色內暈(底片招牌的類比溫度)；Lens flare=鏡頭眩光。Halation 物理上發生在底片負片乳劑層(光穿透後從片基反射回來)，所以調色上必須放在 node tree『最前面』當作在調掃描過的負片，後面所有 grade 都會自然吃到它。
- 數值/出處：ffmpeg halation 管線：[0]split=2[base][g];[g]lutyuv='y=if(gt(val,200),val,0)'[hi](摳luma>200亮部);[hi]gblur=sigma=30:steps=4,colorbalance=rs=.3:rm=.1[glow](模糊+染暖紅);[base][glow]blend=all_mode=screen[out]。一般 glow/bloom=Zayne 配方 gblur=sigma=42:steps=6 後 blend=screen；要 halation 才加摳亮部+染紅那兩步。模糊 sigma 即 scatter、colorbalance rs 即 dye、blend 即 boost
- competent→master：competent editor 整片套個 glow 插件糊成一團(其實是 bloom 不是 halation)；master=知道 halation 只該在高反差亮部邊緣、帶暖紅、且因底片物理要放在管線最前。這是『數位味』到『可信類比底片味』的差距——也…

_來源：noamkroll.com / ayosec.github.io / hhsprings.bitbucket.io / mixinglight.com / creativevideotips.com / bramstout.nl_

## 🖼️ 縮圖 + 包裝 CTR（曝光槓桿）

**Package-Before-Produce（先包裝後生產 / 25-50 標題 × 3-5 縮圖門檻）**  〔expert-consensus｜紙筆 / Figma / Canva（拍之前，不用 CapCut）〕
- 做法：在拍攝前先把這支片的「標題+縮圖」做出來，做不出來就不要拍。具體門檻（The Packaging Doctrine）：同一個 idea 你若無法生出 3-5 個有力縮圖概念 + 25-50 個強標題，代表這 idea 還沒成熟→直接砍掉，省下整個腳本/拍攝成本。Paddy Galloway 數據：頂級創作者花 30% 時間在 ideation/packaging，小創作者只花 5%(95% 全在拍攝剪輯)——這就是曝光瓶頸的根因。
- 數值/出處：門檻：3-5 縮圖概念 + 25-50 標題才算 idea 成熟；頂級 30% vs 小創作者 5% 時間在 packaging；案例 Ian Lauer 2-3K→1M+ 純靠改包裝、Tim Gabe 縮圖改 30-40% → 單日 40x 觀看
- competent→master：Hao 的真實瓶頸=曝光低(8k)、72% 靠自推沒放量、CTR 8.5% 其實不差→問題不是縮圖醜，是『題目本身在 browse feed 沒有 click value』。先包裝會在拍之前就殺掉沒有 click value 的題目，把製作力氣集中在『點得…

**標題-縮圖 Non-Redundancy（不重複原則 / 二者各說一半）**  〔expert-consensus｜概念層（套用在縮圖+標題草稿）〕
- 做法：master 級鐵則：縮圖和標題『絕對不能說同一件事』。縮圖只用『純畫面構圖』丟出一個高張力問題(visual question)，標題只『回答剛好足夠的部分去把那個問題放更大』，兩者組成一份 contract 而非互相重複。MrBeast 版本：標題縮圖先定，後面所有內容都要服務這份『期望契約』，期望沒被滿足觀眾就跳→AVD 崩。
- 數值/出處：縮圖=單一 high-stakes visual question；標題=放大不重述；MrBeast『I Spent 50 Hours In My Front Yard』(爛)→『I Spent 50 Hours In Ketchup』(同結構換一個具體+意外的物件就點得動)；測量用 browse/home CTR 當 packaging 成績、不是 search CTR
- competent→master：competent editor 最常犯：縮圖文字 = 標題文字(資訊冗餘)，等於浪費了兩個獨立的『鉤子欄位』只用了一個。master 讓縮圖和標題像拼圖兩半，乘法疊加 curiosity 而非重複。這直接拉高 browse CTR——而 browse C…

**Information-Gap Theory（資訊缺口理論 / Curiosity Gap 的學術根）**  〔data-backed ·常識｜〕
- 做法：Curiosity gap 不是憑感覺，是 1994 年 George Loewenstein(CMU 行為經濟學家)的正式理論：好奇心=『你已知 vs 你想知』之間一個被察覺的、有邊界的缺口，運作機制跟飢餓一樣是 drive state。
- 數值/出處：Loewenstein 1994『The Psychology of Curiosity』；priming dose 機制；缺口需 specific+bounded；2024 Nature/Sci Reports 研究『headline concreteness』——太抽象的 curiosity gap 會 backfire(具體勝抽象)；一個 package 只開一個 loop
- competent→master：competent editor 把 curiosity gap 做成『標題黨/隱瞞』→點進來發現貨不對板→AVD 崩→演算法懲罰(這是 Hao 最該避免的陷阱，因為他內容是真材實料的教學)。懂 Loewenstein 才知道：正確做法是給『priming…

**Grayscale 120px Silhouette Test（灰階剪影測試 / 行動端可讀性硬規格）**  〔expert-consensus｜ffmpeg/Photoshop（灰階+downscale 自檢腳本）〕
- 做法：master 級可量化測試：把縮圖『去色成灰階 + 縮到 120px 寬』，如果主體剪影看不清楚=這張縮圖失敗，重做。原理：63% YT 觀看在手機、feed 上縮圖實際只 ~120px 寬、人腦在 ~300-600ms 內就決定看不看。規格：最多 3 個視覺元素、1 個強調色打在去飽和場景上(避免 rainbow noise)、用互補色對比(teal/orange)。
- 數值/出處：設計規格：灰階@120px 剪影可辨；≤3 視覺元素；1 強調色+去飽和背景；互補色 teal/orange；mobile 佔 63% 觀看、feed 約 120px、~300-600ms 判讀；可用 ffmpeg/Photoshop 一鍵灰階縮圖自檢
- competent→master：competent editor 在 100% 全螢幕設計縮圖→看起來很滿很美→上傳後在手機 feed 縮成 120px 糊掉沒人點。master 反過來『先在 120px 灰階設計』確保剪影成立。這是純技術硬規格、可機械驗證，正好補 Hao 已有的『非滿…

**2026 De-Clickbait：Micro-Expression > Mouth-Agape（微表情勝張嘴震驚）**  〔data-backed｜〕
- 做法：2026 的反轉趨勢。⚠️ **2026-06-30 修正**：M78「不露臉」只指影片內容；**Hao 縮圖會放自己的反應臉**（breakout「ME vs AI」9.7% CTR 已驗證）→ 這條 face 建議**直接適用 Hao 縮圖**：A/B 數據顯示『閉嘴堅定表情 / 真實微笑』比『張大嘴震驚臉』在 2026 手機 feed CTR 高 15-20%；真人微表情比純 AI 圖『長期點擊滿意度』高 22%(感覺真實=點進來不失望=演算法獎勵)。
- 數值/出處：閉嘴堅定/真笑 vs 張嘴震驚：手機 feed CTR +15-20%；真人微表情 vs 純 AI：長期點擊滿意度 +22%；2026『Proof of Human』『neo-minimalist <3 焦點』；1920×1080 標準。**→ Hao 縮圖用自己的真實反應臉（驚訝/不可置信/堅定）+ 主視覺，不是純物件/UI**（物件/UI 當輔助）。
- competent→master：competent editor 還在抄 2023 的 MrBeast 大嘴+箭頭+爆炸+紅圈(2026 已過時、且讓教學內容顯得廉價失去信任)。master 跟上 2026『authenticity is the new shock』：尤其教學/AI n…

**YT Test & Compare 統計顯著性（A/B 測試的可量化收斂門檻）**  〔data-backed ·常識｜YouTube Studio → Test & Compare〕
- 做法：YT 原生『Test & Compare』(一次 3 張縮圖)的 master 用法是『懂統計、不要太早收』。可量化門檻：每個變體至少 1,500-2,000 impressions 才可下結論(2,000-5,000/變體 達 85-95% 信心)；偵測 5% baseline CTR 的 20% 相對提升@95% 信心需 ~1,500 imp/變體；跑 7-14 天(YT 工具通常需 ~14 天收斂)。
- 數值/出處：每變體 1,500-2,000 imp 才可下結論；2k-5k/變體=85-95% 信心；跑 7-14 天、YT 工具約需 14 天；換縮圖前等 5-20k imp；Test&Compare 內部以 watch time 最佳化非純 CTR;低曝光頻道湊樣本更慢→更需先包裝
- competent→master：competent editor 看片發了 2 小時、幾百次曝光就嫌『縮圖沒用』急著換→樣本不足、純噪音、白白浪費演算法的初始推送窗口。master 知道最小樣本量、知道 browse CTR 才是 packaging 分數、知道 Test&Compare…

**Outlier-Snipe + 5×5 Concept Grid（爆款狙擊 + 概念網格 ideation SOP）**  〔expert-consensus｜紙/試算表 + 可固化進 video-autopilot ideation 步驟〕
- 做法：master 的 60-90 分鐘可重複 packaging sprint(不是靈感，是流程)：①Demand Scan(10-15m) 抓 8-12 個你 niche 最近的 outlier(數據異常爆款)，每個用一行拆解成『物件+情緒+賭注』;②Concept Grid(15m) 畫 5×5 矩陣=縮圖原型 × 標題框架=25 組配對，先不評斷全填滿;③First Cull(10m) 第一眼砍掉 60-70%(任何模糊/字太多/需要先備知識的);④。
- 數值/出處：60-90m sprint：Demand Scan(8-12 outlier,『物件+情緒+賭注』)→5×5 grid(25 配對)→First Cull 砍 60-70%→Merge→Gut Check→Hook 前 6 行;5 種縮圖原型決策樹;Galloway『80% 留主受眾 20% 實驗』『偷跨 niche 格式 ride it until they stop you』
- competent→master：competent editor 靠『等靈感』想一個標題就拍→樣本=1、沒有對照、沒學市場在點什麼。master 把 ideation 變成『先看市場 outlier 解碼成公式→量產 25 個配對→機械淘汰』的流程，命中率系統性高出一截。這也是 Gall…

_來源：blog.autonolab.com / www.colinandsamir.com / www.creatorhandbook.net / www.cmu.edu / www.sciencedirect.com / vmake.ai_

## 📝 腳本 / story-for-retention

**Re-engagement Hook（再勾住）—— 每 30-60 秒埋一個小鉤 + 第 3 / 6 分鐘大鉤**  〔data-backed｜both〕
- 做法：MrBeast 36 頁內部 memo 把 13:37（818 秒）的影片切成「分鐘格」，每位剪輯師要知道自己在做第幾分鐘。固定在 3:00 與 6:00 插入『re-engagement』段落 —— 定義是『only MrBeast can do this』的奇觀/升級，專門擋住中段跳出。
- 數值/出處：節奏數值：講話段 re-engagement hook 每 30s（長段落放寬到 30-60s）；大 re-engagement 固定 3:00 / 6:00；MrBeast 平均片長 818s。剪輯層 pattern interrupt（zoom / 字卡 / 換景）開場每 10-15s 一次，hook 穩了之後切點放寬到 25-40s。實測把這套上滿可讓 retention 從 21% → 56%。
- competent→master：中段（教學長片最致命的 2-5 分鐘）retention 緩降變斷崖；觀眾學到一半就走、AVD 拉不高。也解決『最好的料太早放完、後面變平』。

**Open Loop / Curiosity Loop 開閉（Loewenstein 資訊缺口 + Zeigarnik 效應）**  〔data-backed｜none〕
- 做法：理論根：George Loewenstein《Information Gap Theory of Curiosity》(1994) —— 好奇來自『我知道的』與『我想知道的』之間的缺口，缺口造成心理不適、逼人尋求閉合；Bluma Zeigarnik 效應 —— 未完成的事比完成的事更佔據記憶與注意力。Carnegie Mellon 研究：未解問題會拉高多巴胺，答案揭曉時學習更有獎賞感。
- 數值/出處：10-15 分鐘的片應有 5-7 個 setup-tension-payoff 迴圈。腳本技巧『先寫 payoff 再寫 setup』—— 強迫你確認影片真的有料可交付，才回頭寫『開頭的承諾』，避免開了空頭支票。過 1 分鐘留存 >65% 的頻道，後段 AVD 平均高 58%。
- competent→master：觀眾『知道結論了就走』、看完前 30 秒覺得『懂了』就跳出；單一大問題撐不過 10 分鐘的長片中段。

**Value-Per-Second / 資訊密度（Mark Rober 『每 0.25 秒都要做事』）**  〔expert-consensus ·常識｜none〕
- 做法：Mark Rober 原話：『Every second of my video is precious. If a quarter second is not doing something in my video, I will cut it out.』把這當交付前的剪輯 gate：每一句旁白、每一個鏡頭都要問『這 0.25 秒在推進什麼？（資訊/情緒/張力/笑點）』沒有就剪掉。
- 數值/出處：how-to 教學內容平均 AVD ~42%（各類目最高之一）—— 高意圖觀眾容忍高密度，所以『塞滿』對教學是優勢不是缺點。Shorts：第一亮點不可埋過 3 秒。
- competent→master：教學片『講太慢/鋪陳太久』的緩降型留存；旁白口水（嗯、然後、那我們、所以呢）拖垮密度；Shorts 前 3 秒沒亮點直接被滑掉。

**開場黃金公式：Result-First Hook（先給成品 → 再承諾教法）**  〔data-backed ·常識｜none〕
- 做法：高表現片的開場第一句直接講出一個具體、可觸摸的結果或場景，而不是自我介紹或『這支影片要講…』。教學/before-after 類最強模板：前 3 秒先放完成品（最炸的成果畫面），然後一句『我來告訴你怎麼做到的』。這個 pattern 在 0:30 平均 78% 留存 —— 因為觀眾立刻看到要拿到什麼、當場決定留下來看『怎麼做』。
- 數值/出處：『先放成品 + 我教你怎麼做』模板：0:30 平均 78% 留存。開場 5-10 秒內砍掉任何延後 value 的東西。
- competent→master：開場 0-30 秒斷崖式掉人（長片最大的單一掉點）；教學片『鋪陳完才進正題』流失沒耐心的觀眾。

**把教學步驟寫成有張力的敘事（Stakes / 失敗 / Crazy Progression，而非清單）**  〔expert-consensus｜none〕
- 做法：MrBeast memo：1-3 分鐘要『stop telling people what they will be watching and start showing them』，用『crazy progression』—— 不要卡在第一天/第一步慢慢演，而是快速跨過多個 beat 推進，讓觀眾情緒投資。敘事原則：張力給 payoff 留呼吸空間，與其『做出結果就過』，不如『早早拋出一個問題、把答案壓到後面』。
- 數值/出處：MrBeast 結構：0-1 hook、1-3 crazy progression（從 hype 轉 execution）、3-6 最精彩且最簡單的內容、長解釋段落放到後半（已建立故事投資後才容忍低刺激）。橋接句模板：『Now that you know X, here is why Y changes everything』。
- competent→master：教學片像念說明書、無聊、中段平掉；只剪『成功蒙太奇』反而沒張力留不住人；段落硬切觀眾跟丟。

**Click-to-Unpause Packaging（Paddy Galloway：把第一個 hook 放在點擊之前）**  〔expert-consensus｜none〕
- 做法：Paddy Galloway 拆 4 支爆片的共同點：縮圖都抓『動作進行中』的瞬間（drop in 中、板子拉到一半、嘴張開講話中、正在跨下一步），而非靜止擺拍。
- 數值/出處：頂尖創作者 30% 時間花在 ideation+packaging vs 小創作者 5%（其餘 95% 在拍/剪）。縮圖原則：抓 action-in-progress 而非 composed/static shot。
- competent→master：曝光有但 CTR 低（Hao baseline 已知瓶頸偏曝光/留存，但 packaging 是放大器）；靜止擺拍縮圖點擊弱；力氣全花在剪輯卻忽略點擊前的那一關。

**Retention 殺手句清單（開場前 10 秒的『勿說』黑名單）**  〔expert-consensus ·常識｜none〕
- 做法：明確列為留存死刑的句型：『Hey guys, welcome back to my channel / 別忘了按讚訂閱』『So, yeah, today I kind of wanted to go over…』『在開始之前…』『but first（先講個題外話）』『這支影片我會講…（buried lede 把最有趣的點埋到 15-20 秒後）』。這些句子的共同罪：告訴觀眾零資訊、零留下理由、把 value 往後推。
- 數值/出處：黑名單句首：『welcome back to my channel』『別忘了按讚訂閱（開頭就喊）』『So yeah, today I kind of…』『but first / 在開始之前』。buried lede = 最有趣點埋過 15-20 秒。CTA 改放在第一個 payoff 之後。
- competent→master：前 10 秒掉一大片（最高槓桿的單一掉點）；前置 like/subscribe 反而把人趕走；buried lede 讓有趣的點等不到。

**剪輯層 Pattern Interrupt 節奏（stimulate→calm→re-engage 的呼吸曲線）**  〔data-backed ·常識｜both〕
- 做法：高留存剪輯的節奏設計：開場每 10-15 秒一個視覺重置（zoom / 字卡 / 換景 / B-roll 切換），hook 穩住後把切點放寬到 25-40 秒，讓觀眾下意識舒服；整體跟著『刺激→緩和→再勾』的呼吸節奏，而非全程高速頻閃（頻閃會累、也違反 Hao 的 M93）。這是把前面『re-engagement hook（腳本層）』落到『剪輯層每一刀』的執行細則。
- 數值/出處：開場視覺重置每 10-15s；hook 後切點放寬到 25-40s；節奏 = stimulate→calm→re-engage 循環。pattern interrupt 約 25-35s 標記一個。整套上滿曾把 retention 21%→56%。
- competent→master：全程同一節奏導致中段疲乏；要嘛太密（頻閃累人）要嘛太疏（沉悶掉人）；教學講解段最容易平掉。

_來源：www.alexanderjarvis.com / air.io / www.studiolayerone.com / learn.tubeai.app / blog.neuromarket.co / scriptstorm.ai_

## 🏆 頂尖剪輯師招牌技法（案例）

**Murch 六法則：emotion > continuity（每一刀的決策階層）**  〔expert-consensus｜CapCut / ffmpeg 通用(這是決策框架不是功能)〕
- 做法：決定『要不要這一刀、剪在哪』時，按優先序檢查 6 項：①情緒(>51% 權重) ②推進故事 ③節奏對不對 ④eye-trace(觀眾視線落點) ⑤planarity(畫面平面) ⑥3D 空間連續性。Murch 名言:寧可破壞連續性也不破壞情緒真實。實作:每個 cut 自問『這刀有沒有讓觀眾「感覺」對』,若情緒對就算 jump cut 接得「不連戲」也留;若情緒不對,接得再順也砍。
- 數值/出處：Hao 教學長片套用:每段旁白結尾的 cut,先問『這句聽完觀眾的情緒是好奇/恍然/想笑哪個』再決定下一個畫面;美食 Shorts 套用:第 1 刀永遠給最強感官情緒(滋滋聲+特寫)不是流程第一步。
- competent→master：competent editor 卡在第 6 層(怕接不順/怕跳),拼命修連續性,結果片子「乾淨但無聊」。master 直接從第 1 層(情緒)倒著選,允許為情緒犧牲連戲——這是 Hao 教學長片留存掉的真因:每刀只想著資訊連貫,沒想著「這刀讓人想看下一句…

**J-cut / L-cut(split edit)— 用聲音「拉著」畫面,讓剪接隱形**  〔expert-consensus ·常識｜CapCut(音訊/視訊軌分離拖移)、ffmpeg(adelay + 偏移 concat)〕
- 做法：J-cut=下一段的「聲音」先進來、畫面後到(audio lead),製造前進感/預期;L-cut=這段聲音延續到下一畫面(audio lag),製造情緒餘韻。實作:在 CapCut 把音訊軌與視訊軌分開,聲音比畫面早 6–12 frame(J)或晚 6–12 frame(L)切。人腦追連續聲音,聲音不斷=剪接無感。
- 數值/出處：旅遊 vlog:景點 A 的環境音延續 0.5 秒到景點 B 畫面(L-cut)=接地感;教學長片:下一句旁白聲音先進、畫面 0.4 秒後才切 B-roll(J-cut)=資訊有推進感不拖。frame 數:30fps 約 8–12 frame。
- competent→master：competent editor 聲音畫面同一刀切(hard cut),每次切都有「event boundary」頓挫感,片子像 PPT 翻頁。master 永遠錯開音畫——這是把『一系列 clip』變成『一條河流』的關鍵,旅遊/教學長片最缺這個。

**Whip pan match cut — 把剪接藏在運鏡模糊裡(無縫換地點)**  〔expert-consensus｜CapCut(逐 frame 對接點)+ 拍攝端慢快門〕
- 做法：A 鏡尾端快速甩鏡(whip)製造 motion blur → B 鏡開頭也以同方向同速 whip 進入 → 剪接點切在「兩段都最模糊的那 1–2 frame」。三個必對:①方向一致 ②速度一致 ③接點的顏色/亮度相近。慢快門(降 shutter speed)增加 blur 來蓋刀口。
- 數值/出處：重機 motovlog 直式 Shorts 也吃這套:過彎甩頭/甩 GoPro → 接下個路段;Hao 拍時要刻意『多甩一下』留素材。接點對齊技巧:把兩 clip 都放到最模糊 frame,在 CapCut 逐 frame 對。
- competent→master：competent editor 用 CapCut 內建『轉場特效』硬套(觀眾一眼看出是模板)。master 是用「素材本身的運動」當轉場,看起來像一鏡到底——這是 cinematic travel 流派(Sam Kolder 系)最核心的 signatu…

**Speed ramp 速度曲線(非單一變速)— 直線加速、彎道/落點減速**  〔data-backed ·常識｜CapCut『速度→曲線』(velocity curve,非常規變速)〕
- 做法：用『速度曲線(velocity curve)』而非 CapCut 的單一『慢/快』:在一個 clip 內 0.5×→4×→1× 平滑過渡,用 Bezier handle 拉曲線讓加減速有「重量感」。公式化用法:無聊路段/長廊 4–8× 衝過去,抵達點/精彩處 ramp 回 0.5× 落地。拍攝端用高 fps(60/120)才有慢動作餘裕。
- 數值/出處：重機 motovlog:直線路段 4–6× + 引擎聲保留當節奏;旅遊:走進景點長廊 4× → 看到主景 ramp 到 0.5× + 同步 BGM drop。Hao 拍 GoPro 設 60fps 以上留變速空間。
- competent→master：competent editor 整段勻速快轉(像快進帶),觀眾無聊。master 用曲線製造『呼吸感』——加速帶過廢話、減速強調重點,這是把 30 分鐘騎車/旅程濃縮成 3 分鐘還好看的唯一方法。CapCut 多數人只按『2×』,沒碰 velocity …

**美食:overhead flatlay 文法 + 聲音「重置/替換」(ASMR 流派)**  〔data-backed ·常識｜CapCut(音效分層 + 0.3s 快剪)/ ffmpeg(音效 overlay 對齊)〕
- 做法：兩條 master 守則:①overhead(正上方俯拍)當『主文法』——85% 爆紅美食片靠俯拍特寫,腳架不動、只在切換動作(如擺盤)時推近;每個動作 clip 砍到 0.3 秒,刪掉走進走出畫面的廢格。②聲音是『重新設計』不是『錄到就好』——切菜/滋滋/倒水的 ASMR 多半在後製單獨補錄或抽換原音、貼到畫面動作上,聲音 sync 到視覺那一刻才有衝擊。
- 數值/出處：Hao 美食直式 Shorts:第一刀=最強感官(滋滋/咬下特寫)不是流程;動作 clip 統一 0.3s;後製單獨補/抬高 ASMR 音效對齊咀嚼/切下那一格。配 M96 直式正規化。
- competent→master：competent editor 用現場混亂收音 + 一個固定角度拍完。master 把『聲音當主角』獨立設計、把鏡頭語言收斂成俯拍+特寫兩種、用 0.3s 快剪堆節奏——這是 Hao 美食 Shorts 從『記錄』升級到『讓人流口水』的差距。

**Tech 教學:Fireship 流派 — jump cut 去填充詞 + punch-in 變焦保持眼球**  〔expert-consensus ·常識｜CapCut(jump cut + 關鍵格放大動畫 + SFX)/ ffmpeg(zoompan punch-in)〕
- 做法：①jump cut 把所有停頓/呼吸/『嗯』『就是』砍光 → 形成『機關槍』資訊密度;②每隔幾個 jump cut 自動套一個 punch-in(數位推近 5–15%)變換構圖,讓眼睛不死盯同一框;③重點/數據用 kinetic typography(文字動畫同步旁白逐字出現)+ SFX 音效當『資訊層』——一個音效=一個重點落點。
- 數值/出處：Hao 教學橫式長片:旁白先去填充詞砍到 machine-gun 密度;靜態說明畫面每 8–12 秒 punch-in 一次換構圖;數據/關鍵字用 M68 白字逐字動畫 + 一個 SFX 標記落點(對齊旁白那一格)。M78 不露臉更要靠這個維持眼球。
- competent→master：competent editor 字幕只是『把話打出來』、畫面一鏡到底。master 把『資訊密度』本身當節奏:刪到沒有一秒廢話 + 文字/音效成為理解的一部分(不是裝飾)。Hao 教學長片留存掉=密度不夠 + 畫面太靜,正缺這套。

**Tech 教學:MKBHD 流派 — clean B-roll 解釋抽象概念 + 不過度調色**  〔expert-consensus ·常識｜CapCut / ffmpeg + Hao 既有 caption_broll_matcher.py〕
- 做法：①腳本先寫死每個字,口白用粗體、B-roll cue 用非粗體標在旁——B-roll 的職責是『把抽象講清楚』不是填空(講到 X 就給 X 的具體畫面);②調色極簡『I promise I won't overdo the filters』,乾淨寫實 > 風格化;③節奏:口白資訊流順暢,B-roll 在『需要視覺解釋』的精準時點切入,不亂塞。
- 數值/出處：Hao 教學長片:沿用 MKBHD 腳本法(口白 vs B-roll cue 分標),每個 B-roll 綁定它要解釋的那句旁白(跑 M87 audit_caption_broll_mismatch);調色克制不堆濾鏡=tech 頻道專業感。
- competent→master：competent editor B-roll 是『有畫面就好』隨便鋪。master 讓每個 B-roll 都有明確說明任務、且精準對位到那句話(對應 Hao 的 M87 caption-broll 對位 audit)。tech 流派的 clean 不是沒…

**旅遊 cinematic:teal & orange 調色 + match cut 接地點(Sam Kolder 流派)**  〔expert-consensus ·常識｜CapCut(調色曲線 + 逐 frame match cut 對齊)/ ffmpeg(curves/colorbalance)〕
- 做法：①暖膚色推橘、暗部/天空推青(互補色高對比),但『keep it mild』保持真實別過頭;②結構上用 match cut 串地點:動作/形狀/運鏡在 A 結尾與 B 開頭對齊(如 A 鏡跳起→B 鏡落地、A 鏡的圓物→B 鏡的圓物),製造『一個動作穿越兩地』的魔法;③配 speed ramp + BGM beat drop 對齊抵達點。
- 數值/出處：Hao 旅遊直式 Shorts:teal-orange 但壓低強度(避免 M 記憶裡『太紅太橘太綠』);用 match cut 串景點(同形狀/同動作對齊)+ BGM drop 落在主景出現那刻(配 M98 find_music_highlight)。
- competent→master：competent editor 套個現成 LUT 就收工、地點之間硬切。master 的 teal-orange 是『微調保真』+ 用 match cut 讓旅程有『敘事連續性』(不是流水帳)——這是 cinematic travel 與『度假錄影』的分…

**motovlog:三層音訊混音(路噪+口白+BGM)+ 砍死時間**  〔data-backed ·常識｜CapCut(多音軌 + 音量自動化)/ ffmpeg(amix + acompressor,Hao 已有 M99)〕
- 做法：①三軌混音:引擎/路噪當『真實感底層』、口白最前、BGM 壓到 -20~-18dB 墊底(別蓋口白);引擎聲與人聲咬合別硬刪,當節奏用。②素材全丟時間軸後『慢慢砍』:刪掉所有空停、紅燈乾等、口白的『嗯/like』,B-roll 鏡頭可以很短(觀眾吸收快)。③精彩路段保留引擎聲當 BGM 的一部分。
- 數值/出處：Hao 重機直式 Shorts:BGM 固定 -18dB 墊底、引擎聲保留當節奏層、口白最前;全程砍到沒有一秒『等紅燈/直線發呆』;配 M99 acompressor 壓平 BGM 忽大忽小。
- competent→master：competent editor 三種聲音打架(BGM 蓋掉引擎、口白被路噪淹)、保留太多無聊騎行。master 是『聲音分層各司其職』+ 無情砍死時間到只剩高光——motovlog 沉悶 90% 是沒砍 + 混音亂。

_來源：www.studiobinder.com / www.techsmith.com / nofilmschool.com / pixflow.net / filmora.wondershare.com / www.tiktok.com_

## 🎯 最該內化的 must-bake
- 新增 references/murch_master_layer.md(或併入 editing_principles_canon.md):Rule of Six 優先序心法(emotion>story>rhythm>eye-trace>2D>3D,當『衝突時不為低階犧牲高階』的決策序,不是演算法權重) + Blink/換氣找剪點 + cut-rate 數值錨點 + 轉場語意化 + eye-trace 焦點連續。明確標『這是判斷層,不重複既有 craft 操作層(M9-M102)』
- 把『感受殘留測試』寫成 delivery_qa.py 新函式 emotion_residue_check():列印『全片看完閉眼答一個情緒詞,比對該 niche 目標情緒;答不出/答錯=回 emotion 層重剪而非修技術』。掛在 M86/M87 同層,但標註『這是人工 gate 非自動 pass/fail』,且必須是 build pipeline 最後一關(在所有機械 audit green 之後)
- 升級 M87:b-roll 入點預設往前 offset 0.3-0.8s(畫面領先旁白半句=L-cut),cut 候選點改用 silencedetect 換氣點而非純句尾。寫進 LONGFORM_PIPELINE + auto_sequence_brolls()。標清楚這是『Blink Theory 旁白版』升級不是推翻 M87
- 在 LONGFORM_PIPELINE + Shorts pipeline 的交付前加 cut-rate 校準 gate:ffprobe 數 cut÷時長,解說段 >8/min 標『過碎、考慮放長幾顆給呼吸』(承 MrBeast 2024 反轉 + audience 43% 痛點),高能 Shorts 段 <15/min 標『可加快』。一個 audit_cut_rate() helper
- 轉場死規則進 SKILL 鐵則:同概念內 b-roll 一律 hard cut(0 溶接)、dissolve 只給時間流逝(縮時)、章節跳轉才用轉場。跨所有 niche。直接終結過去 v13-v25 在 Pro 花字/炫炮 transition 上的反覆打轉
- 新增 audit_eyetrace_continuity():抽接點前後 frame 比對主焦點座標(臉/高對比/字幕/游標),跨刀焦點不在同區且無引導路徑就標記。優先用在直式 Shorts(焦點別上下亂跳)+ 教學 demo(游標/重點框跨刀對齊)。這是現有 QA 完全缺的一層
- Repeat-Cut 收斂測試進 autopilot QA:關鍵接點自動/半自動重算 2 次落點,差 >1-2 frame 標『未收斂需人工確認』。當 Mode A 全自動成片的客觀剪點驗證
