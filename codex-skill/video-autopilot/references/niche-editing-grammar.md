> → 找不到要讀哪本？[craft-index.md](craft-index.md)（六本 craft refs 導航：症狀→節路由表 + 跨檔重複主寫對照）

# 各題材剪輯文法：業餘 → pro（Hao 題材：美食/旅遊/重機/教學長片/軟體 demo）

> 每個題材有自己的剪輯文法。承 craft 基本功（→ editing-craft-fundamentals.md）+ 既有 M96 直式 Shorts pipeline。

## 🍜 美食

**前 3 秒開場放「最高光的動作鏡頭」(sizzle/起鍋/拉絲/淋醬)**  〔data-backed｜both〕
- 做法：別用 logo / 標題卡 / 慢慢介紹開場。第一幀就丟你整支片最誘人的瞬間：油下鍋的 sizzle、起鍋熱氣、牽絲、淋醬糖漿流下。CapCut: 把這顆 clip 拖到時間軸最前面當冷開場，不加轉場直接進。Shorts 用 extreme close-up 或正上方俯拍兩種角度最強。
- 數值：TikTok for Business：63% 高表現影片在前 3 秒就 hook；前 3 秒留存 >85% 的片總觀看是 <60% 的 2.8 倍。把高光放在 0:00-0:01，不要等到第 5 秒
- 修：業餘 tell：開頭 2-3 秒在『大家好今天要吃』或店門口空景 → 還沒看到食物觀眾已滑走

**高光時刻不要被 BGM / 旁白蓋掉 — 留真實食物原聲**  〔data-backed｜both〕
- 做法：sizzle、咬下脆聲、刀切聲、煮沸冒泡 這幾顆『satisfying 瞬間』時，把 BGM 音量壓下去（CapCut 關鍵幀把音樂從 -14dB 降到 -28dB ~ 靜音 0.5-1.5 秒），讓食物原聲衝到前面。這幾秒人聲旁白也讓位。ffmpeg：對 BGM 軌用 volume 加 enable 區間表達式壓低，食物軌維持原音量。
- 數值：Oxford 實驗心理學家 Charles Spence 的 Ig Nobel 研究：洋芋片的咀嚼聲被放大後，受試者覺得『更新鮮更好吃』；sizzle 會觸發 Pavlov 制約食慾。聲音和畫面一樣重要，這幾秒讓聲音當主角
- 修：業餘 tell：全程 BGM 蓋台 + 旁白不停，最該被聽見的 sizzle/脆聲被音樂淹沒 → 觀眾沒被勾起食慾

**ASMR / Foley 補聲：實拍收不到的聲音事後補**  〔expert-consensus｜both〕
- 做法：現場若收不到乾淨的 sizzle/脆聲/淋醬聲（環境吵、麥太遠），事後補音效。CapCut: 音訊→音效素材庫 搜『sizzle / 油炸 / 咬 / 倒水 / 切』對齊畫面動作放上去。ffmpeg: 用 -itsoffset 或 adelay 把音效精準對齊到動作幀。對位原則：聲音起點壓在動作發生的那一幀，不是動作前後。
- 數值：Foley 與 ASMR 觸發點重疊（敲、刮、脆、刷）；專業 foley 甚至用培根錄『下雨聲』。對位容差建議 ≤1 影格（30fps 約 33ms），人耳對 A/V 不同步很敏感
- 修：業餘 tell：畫面在 sizzle 但聲音是悶的環境音或乾脆沒聲 → 缺了食物片最核心的『沉浸感』

**高速拍攝 + 慢動作只用在『重點美味瞬間』**  〔expert-consensus ·常識｜both〕
- 做法：拍攝端：糖漿/醬汁淋下、牽絲、起鍋熱氣、咬下 這幾顆用 120fps 或 240fps 拍。後製降到 25%(120fps→4x 慢)。剪輯端只對『誘人瞬間』慢，重複勞動(攪拌/等水滾)反而加速。CapCut: 變速→曲線變速做 speed ramp（正常→慢→正常）。ffmpeg: setpts=4.0*PTS 把片段拉慢 4 倍（音訊配 atempo 或直接靜音改鋪音效）。
- 數值：120fps→25% 速度=4x 慢動作；沒有高速素材就 60fps→50%(2x)。慢動作要乾淨必須拍攝端高 fps，不是後製硬拉。牽絲低角度往上拍(low-to-high)更壯觀
- 修：業餘 tell：①全片同一速度毫無節奏起伏 ②該慢的牽絲一閃而過、不該慢的攪拌拖很長 ③用 30fps 硬拉慢變格頓格(jitter)

**Cut on action：刀切/夾起/翻面 在動作中途換角度**  〔expert-consensus ·常識｜both〕
- 做法：同一個動作(切菜、夾起、翻面、淋醬)拍 2 個以上角度，剪接點切在『動作進行到一半』那一幀，不是動作停下來才切。例：刀往下切到一半 → 切到另一角度接著切完。觀眾眼睛在追蹤運動，會自動把兩顆當成連續，cut 變隱形。CapCut: 兩顆 clip 對齊動作幀後直接硬切，不加轉場。
- 數值：幾乎每個 cut 都該發生在 mid-action。動作鏡頭間用 cut on action 而非等停頓，flow 明顯更順。95% 用硬切(straight cut)，避免無謂轉場
- 修：業餘 tell：每顆鏡頭都『等動作完全結束、手收回、靜止』才切下一顆 → 節奏拖沓、一頓一頓很卡

**三幕結構：成品 reveal 先勾 → 製作過程 → 收尾 plating/咬下**  〔expert-consensus ·常識｜both〕
- 做法：開頭先閃一下『完成的成品 hero shot』勾食慾(1-2 秒) → 中段製作過程(壓縮、保留關鍵動作) → 結尾完整 reveal：擺盤、淋最後一道醬、撒料、或鏡頭外咬一口。成品 reveal 是全片情緒最高點，給它最足的時間和最好的光。
- 數值：結構=beginning(含成品 clip)/middle(製作)/end(plating+收尾動作如淋醬撒料或咬一口)。盤上的醬汁拉線當天然視覺引導線
- 修：業餘 tell：①完全沒有『先給成品』的勾子，觀眾不知道在期待什麼 ②結尾草草結束沒有 reveal 高潮，食慾沒被滿足就斷掉

**Hero / Beauty shot：給成品一顆專屬定鏡 + 慢推**  〔expert-consensus｜both〕
- 做法：成品最美的那一盤拍一顆乾淨定鏡：穩(不手抖)、淺景深、暖光、熱氣明顯。後製加極輕緩慢 push-in(放大 100%→105%，3-4 秒)製造『凝視感』。CapCut: 縮放關鍵幀做緩推。ffmpeg: zoompan 做極慢 Ken Burns(注意你的 M-rule：靜態生成圖不 pan，但實拍成品鏡可緩推)。
- 數值：hero food=端上桌的最終造型，專業會花數小時 styling。緩推幅度 5% 內、3-4 秒，避免變成廉價放大
- 修：業餘 tell：成品鏡跟其他鏡一樣快閃過去、手持晃動、平光無立體感 → 最該炫的主角沒被當主角

**暖色調白平衡：往琥珀色靠，食物才『熱』『香』**  〔expert-consensus ·常識｜both〕
- 做法：調色把白平衡往暖推。拍攝端鎢絲燈約 3200-3400K；若數位調色，色溫往 +(暖) 拉一點點讓金黃焦色(Maillard)更跳。CapCut: 調節→色溫往右(暖)、飽和度小幅+、對比+。ffmpeg: eq=saturation=1.1:contrast=1.05,colorbalance 或 curves 把紅/黃微提。原則：先校白平衡讓白色(盤/米)中性，再套暖向 LUT，且只用『一張』LUT 別疊。
- 數值：專業美食攝影約 95% 的片都會『加暖』；鎢絲約 3400K，棚拍閃燈 WB 設 6000K+ 偏暖。飽和度小幅微調即可，過飽=業餘。一張 LUT 調強度，不疊
- 修：業餘 tell：①冷藍調(室內白光沒校)讓食物看起來冷掉、不新鮮 ②飽和拉爆變塑膠假色 ③疊多張 LUT 過曝失真

**鏡頭多樣性：俯拍 + extreme close-up 為主，外加 establishing**  〔expert-consensus ·常識｜both〕
- 做法：美食最有效兩角度：①正上方俯拍(看全貌、擺盤、整個鍋面) ②extreme close-up(看質地、熱氣、油泡、絲)。再補一顆 wide/establishing 交代場景。剪輯時 wide→medium→close 推進，或在 close 與俯拍間切。同一場景至少 3 種景別輪替，避免一鏡到底。
- 數值：俯拍 + extreme close-up 是 TikTok 美食最有效的兩個角度。ECU 放大質地與『有意義的瞬間』，強化觀眾與主體連結
- 修：業餘 tell：整支片一個固定中景(medium)從頭到尾、機位不動 → 單調、看不到食物細節質地、沒有『電影感』其實是缺景別

**Beat sync：cut 點對齊 BGM 節拍**  〔expert-consensus ·常識｜CapCut〕
- 做法：CapCut: BGM 拖進時間軸→右鍵『節拍(Beat Detection)』自動生成節拍點→把每顆 clip 的剪接點吸附到節拍點上。快歌用 Flash/Camera Shake 轉場壓在重拍、慢歌用 Cross Fade/Blur。對美食：把『淋醬落下』『咬下』『起鍋』這些動作高光剛好壓在重拍上最爽。
- 數值：CapCut 內建 Beat Detection 自動標拍點。快歌重拍上切換、慢歌用溶接。仍維持 95% 硬切，轉場只點綴
- 修：業餘 tell：cut 點和音樂各走各的、節奏對不上 → 看起來『鬆』『沒在點上』，少了專業片的律動感

**Aggressive trimming：砍掉每個無聊幀，b-roll 蓋 jump cut**  〔expert-consensus ·常識｜both〕
- 做法：最關鍵的 pro 技法=狠剪。每顆 clip 只留『有事發生』的部分，動作開始前後的死時間全砍。口播留白、卡詞、重複動作(攪拌等水滾)全切掉或加速。產生的 jump cut 用 b-roll(食材特寫、熱氣、環境)蓋過去。節奏寧快勿慢。
- 數值：Aggressive trimming 被點名為最重要技法；95% 用硬切無轉場；jump cut 用 b-roll 遮蓋兼增加視覺資訊。你已有的 M86/M87 b-roll 占比+對位規則正好接這條
- 修：業餘 tell：每顆 clip 前後都拖著 1-2 秒死時間、口播充滿 emm/留白、過程一刀未剪照實放 → 整片拖沓冗長，這是業餘 vs pro 最大的單一差距

**口播/反應鏡(M78 不露臉版)：用手、咬下後的反應聲、字幕代替臉**  〔expert-consensus｜both〕
- 做法：M78 不露臉，但『反應』還是要有，靠：①咬下後鏡頭外的『嗯～』『酥脆聲』 ②手的動作特寫(掰開、夾起、沾醬) ③字幕打出反應/形容詞(脆、爆汁、燙、會牽絲)。把『主觀體驗』傳達出去，而不是只有客觀製作流程。
- 數值：結尾常見收法=鏡頭外咬一口(bite off camera)。脆度/口感靠聲音+字幕傳達(crispy lasagna 邊緣的脆聲會讓人想煮)。配合你 niche 多色字幕(脆/爆汁 等關鍵詞上色)
- 修：業餘 tell(對不露臉頻道)：全片只有冷冰冰的製作流程、沒有任何『好不好吃/什麼口感』的主觀反饋 → 觀眾無法代入食慾

**店家資訊 outro：地址/店名/營業時間 + GPS 可點**  〔anecdotal ·常識｜both〕
- 做法：美食探店片結尾固定一張資訊卡：店名、地址、營業時間、價位/招牌菜。直式 Shorts 配合你既有 M96(GPS 地址+多色字)。CapCut: 文字+底色塊(別純白字飄在亮背景，加半透明黑底框=你的 M68 風格)。資訊卡停留 ≥3 秒讓人截圖。背景可放成品 hero shot 緩推。
- 數值：資訊卡停留 ≥3 秒(可截圖);你的 M96 已有美食/旅遊直式 Shorts 的 GPS 地址+多色字規範,直接沿用。資訊卡=outro,不要放片頭擋住食物
- 修：業餘 tell：探店片看完不知道是哪家店、地址要去哪找 → 觀眾想去也沒法收藏，浪費了轉換

**熱氣 / 牽絲 / 油泡 = 視覺『新鮮燙』訊號，剪輯要保留並放大**  〔expert-consensus ·常識｜both〕
- 做法：起鍋熱氣、牽絲、糖漿光澤、油泡冒泡、金黃焦色(Maillard) 是『現做、熱、香』的視覺訊號，是美食片的貨幣。剪輯時：①這些瞬間優先給慢動作 ②背光/逆光讓熱氣可見(拍攝端) ③別把這幾顆剪太短。CapCut 調色微提對比+暖色讓焦色和光澤更跳。
- 數值：視覺 hook 公認最強清單：cheese pull、golden crust(Maillard)、steam、glossy sauce、color contrast。逆光/背光讓蒸氣現形是拍攝端關鍵
- 修：業餘 tell：把熱氣/牽絲/油泡的瞬間當普通鏡頭一閃而過、或調色調冷讓光澤消失 → 食物看起來冷掉、不誘人

_來源：www.marketeze.ai / insights.ttsvibes.com / www.theglobeandmail.com / asmr.education / artlist.io / www.adorama.com_

## ✈️ 旅遊

**Establishing shot 開場錨點（wide → 內容）**  〔expert-consensus｜both〕
- 做法：每換一個地點，先放 2-4 秒的寬景/廣角（或空拍）建立 sense of place，之後才接細節 b-roll。CapCut：把最廣的那顆拖到該段最前面；ffmpeg pipeline：在地點段落 concat 順序排 wide 在第一顆。Shorts 因為短，establishing 壓到 1-1.5 秒或直接跟 hook 重疊。
- 數值：establishing 2-4 秒（長片）/ 1-1.5 秒（Shorts）；廣角焦段 ~25-30mm 等效避免變形
- 修：業餘 tell：一開始就丟特寫/手持晃動，觀眾不知道你在哪、為什麼要看 → 情緒上很『平』。沒有 wide 錨點 = clip dump 流水帳。

**Wide–Medium–Detail 三段式覆蓋（同一個 idea 三種景別）**  〔expert-consensus｜both〕
- 做法：每個場景/idea 都用 wide(交代環境)→medium(動作)→close-up/detail(手、食物、紋理) 至少三顆。剪接時 75% 用特寫、靠 wide 開場 + medium 過渡。detail 顆要『短』：夠看清就切，不拖。CapCut/ffmpeg 都是排序問題，先把每段素材標 W/M/D 再排。
- 數值：raw b-roll 約 75% 應為特寫；detail 顆 0.5-1.5 秒即切
- 修：業餘 tell：整段都同一景別（全是手持中景或全是 wide），畫面沒有節奏與輕重，看起來像監視器。沒有特寫 = 觀眾跟地點/食物沒有情感連結。

**故事弧三幕（setup→discovery→resolution）取代時間順序**  〔expert-consensus｜通用〕
- 做法：別照拍攝時間排（早上→中午→晚上流水帳）。改成：setup 介紹地點+期待 → discovery 發生什麼+意外驚喜 → resolution 收尾（一餐/一個景/感想/離開）形成 closure。剪輯前先寫這三段大綱，再把素材塞進去，而不是邊剪邊硬湊。
- 數值：前 2 分鐘每 30 秒要有一個『有趣的事』發生；2 分鐘後可拉到每 45-60 秒，但絕不超過
- 修：業餘最大 tell：把 vlog 當『把看起來好看的隨機畫面湊一起』→ 視覺 OK 但情緒平、沒有讓人看下去的理由；以及『突兀結尾』沒有收尾感。

**音樂驅動 montage：先選曲 → 對拍切（cut on beat）**  〔data-backed｜both〕
- 做法：先選好曲再剪，不是先剪再硬配樂。旅遊 montage 用 90-120 BPM、ASL(平均鏡頭長度) 3-6 秒；要更燃的冒險段用 120-140+ BPM、ASL 1-3 秒。在每個重拍下切鏡。
- 數值：Cut 間隔 = 60/BPM 秒（如 120BPM=每 0.5 秒一拍，切在 1/2/4 拍）；moderate montage ASL 3-6s / fast ASL 1-3s
- 修：業餘 tell：鏡頭長度亂、配樂與畫面各走各的，montage 沒有律動；或音樂一段段忽快忽慢跟畫面對不上 → 顯得『沒在剪、只是接』。

**Match cut 接不同地點（動作/形狀/顏色/運動方向）**  〔expert-consensus｜both〕
- 做法：用前一顆的元素無縫接到下一個地點：①動作 match（A 走出畫面右 → B 在別處走進畫面同方向）②形狀/graphic match（圓盤食物 → 圓形地標）③顏色 match（火 → 夕陽 → 沙漠）④運動方向一致。剪接時把兩顆『動作對齊』的那一幀對切。CapCut/ffmpeg 都是精準對齊出入幀。
- 數值：兩顆運動速度要相近；切點對齊『動作中點』那一幀
- 修：業餘 tell：地點之間用生硬硬切或預設炫炮轉場（星形、翻頁），打斷沉浸感。match cut 讓跳地點像『一鏡到底』，是旅遊片最常用的 pro 招。

**Whip pan / walk-through 隱藏剪接點轉場**  〔expert-consensus｜both〕
- 做法：A 顆結尾甩鏡（或加方向性模糊）+ B 顆開頭同方向甩鏡，剪在最模糊那幀 → 兩地點看起來像一鏡轉過去。後製做法：對兩顆交界加 adjustment layer 方向模糊 Blur Length 50-100、方向對齊甩鏡角度（水平=90°）；或把鏡尾速度拉 500-4000% 製造模糊。CapCut 有甩動/whip 轉場預設可直接套；ffmpeg 用 tblend + 速度拉伸近似。
- 數值：方向模糊 Blur Length 50-100；速度拉伸 500-4000%；兩邊甩速要一致
- 修：業餘 tell：每次換鏡都看得到生硬切點，或濫用 CapCut 內建花俏轉場（爆炸、愛心）顯得 cheap。whip pan 是『藏剪接』讓能量連續。

**Hyperlapse / 縮時：拍攝間隔 + 後製抽幀**  〔data-backed｜ffmpeg〕
- 做法：縮時拍：交通等快動 1-2 秒/張、夕陽等慢變 5-10 秒/張；hyperlapse(移動縮時) 間隔 5-12 秒、新手 15 秒、最少 120 張。全手動（曝光+白平衡+對焦鎖死）。
- 數值：timelapse 最少 300 張(=10s@30fps)；hyperlapse 最少 120 張、間隔 5-12s；ffmpeg 抽幀 select mod(n,N) + setpts=N/FRAME_RATE/TB
- 修：業餘 tell：把長段無聊移動（走廊、車程、排隊）用 1x 正常速度播 → 拖沓。縮時/hyperlapse 把『過程』壓成 2-5 秒節奏點，是旅遊片提速神器。

**速度斜坡 speed ramp（慢→快→慢 引導視線）**  〔expert-consensus｜CapCut〕
- 做法：穿過長廊/隧道時加速、到達目的地時放慢，引導觀眾走完一段旅程。CapCut：選片段→『速度』→『曲線』→自訂或用 Hero/Montage/Jump Cut 預設，可加最多 10 個速度點（垂直=倍率、水平=時間）。要 freeze：在凍結前先放慢→停住→之後加速，做出戲劇停頓。
- 數值：CapCut 曲線最多 10 個速度點；預設 Hero/Montage/Bullet/Jump Cut
- 修：業餘 tell：所有片段都同一速度播放，沒有快慢起伏 → 平板無張力。speed ramp 是讓畫面『有呼吸』的 pro 手法。

**自然聲(NAT sound) 鋪底 + 音樂/旁白分層混音**  〔expert-consensus ·常識｜both〕
- 做法：每個地點都錄幾分鐘環境音(市場、海浪、人聲)鋪在音樂底下，scene 之間才『黏』得起來。混音層級：旁白/對話 -18 至 -9 dB；音樂 -18 至 -22 dB（且比旁白低約 15-20 dB）；環境音存在但不搶。旁白進來時對音樂/環境音做 ducking 自動降。ffmpeg 用 sidechaincompress 做閃避、acompressor 壓平忽大忽小(M99)。
- 數值：對話 -18~-9dB；音樂 -18~-22dB 且比旁白低 15-20dB；每地點錄數分鐘 wild track
- 修：業餘 tell：①整片只有一條 BGM、沒有任何現場聲 → 假、像幻燈片 ②音樂蓋過旁白、或環境音忽大忽小。NAT sound 是『沉浸感』與真實感的關鍵，pro 一定鋪。

**J-cut / L-cut 聲音先行橋接（split edit）**  〔expert-consensus｜both〕
- 做法：J-cut：下一個 scene 的聲音先進來(畫面還停在上一顆)，當作預告把觀眾拉過去；L-cut：上一 scene 的聲音延續到下一顆畫面。CapCut/ffmpeg：把音軌與視訊軌錯開（音訊提前或延後 0.5-1 秒），不要每次都音畫同切。用來當地點之間的『聽覺橋』，不用字卡也能引導。
- 數值：音訊提前/延後約 0.5-1 秒；對話或地點轉場最常用
- 修：業餘 tell：每一刀音畫同時硬切 → 一頓一頓很機械。J/L cut 讓 scene 之間像水流過去，是紀錄片/旅遊片把『接』變成『流』的核心。

**地名字卡（animated location title / 動畫地圖 pin）**  〔expert-consensus ·常識｜CapCut〕
- 做法：每換地點打一張乾淨的地名卡：地名 + 可選地址/GPS，配紅色地圖 pin 滑入的 kinetic typography，簡約線條風。CapCut 套 location title 模板或自己做（淡入 + 輕微位移，0.3-0.5 秒進場）；旅遊 Shorts 記憶 M96 已要求多色字 + GPS 地址。字卡只停 1.5-2.5 秒就淡出，別擋畫面。
- 數值：字卡停留 1.5-2.5 秒；進場動畫 0.3-0.5 秒；含地名+地址/GPS
- 修：業餘 tell：①完全沒標地名，觀眾看一堆漂亮畫面但不知在哪、無法收藏行程 ②或用醜的預設字體置中硬擺、不動。乾淨動畫地名卡是旅遊片『資訊感 + 質感』的標配。

**Shorts 開場 0.4 秒鉤子 + pattern interrupt 每 2-3 秒**  〔data-backed ·常識｜通用〕
- 做法：直式旅遊 Shorts 第一幀就放最美的目的地揭露(destination reveal)，砍掉所有 intro/logo/自我介紹。每 2-3 秒一個 pattern interrupt：jump cut、推拉 zoom、字幕跳出、音效。滿版 9:16，非滿版的素材用模糊填底(記憶鐵則)。目標留存 ≥75% 才容易被推給新觀眾。
- 數值：觀眾約 0.4 秒決定去留；pattern interrupt 每 2-3 秒；viral Shorts 平均留存 ~76%，>75% 推新觀眾機率 3 倍
- 修：業餘 tell：①前 3 秒在『嗨大家好今天來到…』→ 0.4 秒就被滑掉 ②節奏太慢、一顆鏡頭停太久。Shorts 是注意力戰場，第一幀沒鉤子 = 死。

**拍攝端 180° 快門 + 穩定，餵剪輯素材的品質地基**  〔expert-consensus｜通用〕
- 做法：拍片時快門 = 幀率 2 倍（24fps→1/48、30fps→1/60）得到自然動態模糊，畫面才『電影感』而非過銳像監視器。走路移動鏡頭要穩(gimbal 或慢推 zoom 取代手持快走)；要靜止鏡就完全靜止。這層決定剪輯素材好不好剪。
- 數值：24fps→1/48s、30fps→1/60s（快門=2×幀率）；移動鏡用 gimbal 或慢推
- 修：業餘 tell：①手持邊走邊拍狂晃 → 看了暈、剪不順 ②快門太快畫面死銳、移動有頻閃感。Pro 慢的片會把 establishing 拉長；amateur 把晃動當『臨場感』其實是缺陷。

**色彩調性統一（多機/多時段一致的 look）**  〔expert-consensus｜both〕
- 做法：全片套同一組色彩風格，跨不同相機/不同時段拉到視覺一致，並做一個反映該地點氛圍的調色(暖=東南亞市場、冷藍=北歐)。CapCut 套同一個濾鏡/調整參數到所有片段或用調整圖層；ffmpeg 用 eq/curves/LUT 統一。冒險片可配快剪+time remap 提能量。
- 數值：同一 LUT/濾鏡套全片；按地點定調（暖/冷）
- 修：業餘 tell：每顆鏡頭顏色不一(這顆偏黃那顆偏藍)，一看就知道沒調色、像把素材直接倒出來。統一 look 是『一支作品』vs『一堆檔案』的差別。

_來源：www.musicbed.com / shumwayvideo.com / store.hollyland.com / artlist.io / www.flexclip.com / www.premiumbeat.com_

## 🏍️ 重機/motovlog

**拍攝端先設 Linear + Horizon Leveling(HL),不要靠後期掰直地平線**  〔expert-consensus｜GoPro(Hero9+,最佳 Hero12/13)〕
- 做法：錄影前進 GoPro 設定 → FOV 選 Linear,再開 Horizon Leveling/Lock。Hero9-11 是 Linear+Leveling(地平線可校正到約 ±45°);Hero12/13 升級成 360 Horizon Lock。這會同時(1)去掉魚眼把直線拉直(2)過彎壓車時地平線維持水平,只有車身/車架在傾。
- 數值：FOV=Linear(約 90°),地平線校正 ±45°(Hero11-)/360°(Hero12+);Wide=120°、SuperView=最寬約 170° 留給純動作不留給 cinematic
- 修：業餘 tell:魚眼桶狀變形(直牆/地平線是彎的)+ 過彎時整個畫面跟著歪一邊,看起來像隨手 raw 直出

**穩定要選對:in-camera HyperSmooth(輕鬆)vs Gyroflow(pro 級,但要關機內穩定錄)**  〔expert-consensus｜GoPro HyperSmooth / Gyroflow(免費)〕
- 做法：兩條路二選一,不能混:(A)省事路線—錄影開 HyperSmooth(Hero8+),靠機內裁邊+陀螺儀補償,直接出片。(B)pro 路線—錄影時關掉 HyperSmooth、但開 GPS 選項(GoPro 的 GPS 模式同時錄 GYRO 資料),回家用 Gyroflow 讀陀螺儀資料做穩定。關鍵:用 Gyroflow 一定要錄影時關 HyperSmooth,否則陀螺儀資料對不上畫面。
- 數值：Gyroflow Smoothness 設 50-70 最自然(過高會飄/果凍);先用官方可列印校正圖建好 lens profile 再穩定
- 修：業餘 tell:畫面一路抖/路面震動全進畫面(沒開穩定或 mount 鬆);或反過來 HyperSmooth 開太死產生不自然『黏』果凍感

**風切聲:硬體先擋(海綿罩/下巴架/頭盔內收音),不要只靠後期救**  〔expert-consensus ·常識｜GoPro + 海綿風罩 / Media Mod / 頭盔內 mic〕
- 做法：依優先序:(1)GoPro mic 套泡棉海綿風罩(GoPro Media Mod 風罩 / Hero5-7 Windslayer)—最快最有效。(2)把相機從盔頂改裝到下巴架(chin mount),用頭/盔身當天然擋風牆。(3)真要乾淨人聲就把 mic 收進頭盔內、裝在下巴桿、朝頰墊、外加 deadcat 防風—社群實測『風切基本消失還收得到車聲』。
- 數值：盔頂 mount → 改下巴 mount;頭盔內 mic 朝頰墊 + deadcat;低靈敏度 mic > 高靈敏度
- 修：業餘 tell:整段『呼呼呼』風切糊掉人聲與引擎,後期再強的降噪都救不回

**錄 RAW Audio Low 拿到無壓縮 .wav 旁檔,把音訊救援留到後期**  〔expert-consensus｜GoPro(Protune)〕
- 做法：進 Protune → RAW Audio 設 Low(最小處理),GoPro 會替每支影片另存一個無壓縮 .wav 旁檔。Low 對音訊只做最少處理,最適合拿回後期自己降噪/EQ/混音。機內 Wind Noise Reduction 開 Auto 當保險,但真正的處理交給後期。這是 pro motovlog 收音工作流的起點:先拿到乾淨原料。
- 數值：Protune ON → RAW Audio = Low(非 High/Off);Wind Noise Reduction = Auto
- 修：業餘 tell:用機內已壓縮/已過度處理的音訊去後期再降噪,結果越救越糊、金屬感

**ffmpeg 風切/底噪鏈:highpass + lowpass + afftdn/anlmdn 一條鏈打掉風聲保住人聲引擎**  〔data-backed｜ffmpeg〕
- 做法：對 motovlog 音軌跑頻段裁切 + 頻域/非局部均值降噪。風切能量集中在低頻,先 highpass 砍掉;高頻嘶聲用 lowpass 收尾;寬頻底噪用 afftdn(FFT 頻域)或 anlmdn(非局部均值,針對風切更準)。
- 數值：highpass f=100Hz(人聲可 80-120);lowpass f=10000Hz;afftdn nr=12dB nf=-50dB(預設)、開 tn 追蹤;anlmdn s=0.008 p=2ms(針對風切)
- 修：業餘 tell:風切『呼呼』底噪整段在、或亂套一鍵降噪把人聲也吃掉變水下/機器人聲

**引擎聲是賣點要保留,但用 sidechain ducking 讓人聲/BGM 一講話就壓下去**  〔data-backed｜ffmpeg(sidechaincompress / acompressor)〕
- 做法：motovlog 的引擎聲是氛圍賣點別整段壓死;改用側鏈壓縮做自動避讓:人聲/BGM 當 sidechain 觸發源,一有人聲就把引擎/BGM 那軌壓低,話講完自動放回。ffmpeg 用 `sidechaincompress`(以另一軌的能量為門檻壓本軌),比手 K volume keyframe 乾淨。承 Hao 既有 M99:BGM 忽大忽小先用 acompressor 壓平再混。
- 數值：sidechaincompress 觸發源=人聲軌;引擎/BGM 被壓軌做 ducking;收尾 loudnorm I=-14(YT);承 M99 acompressor 先壓平 BGM
- 修：業餘 tell:引擎/BGM 整段同音量蓋過人聲,或人聲忽大忽小要一直手調—聽起來沒做混音

**用 intercom/外錄音訊取代相機音訊:clap + 補油門 rev 對軌**  〔expert-consensus｜Sena 50S / 外錄(Bluetooth intercom)+ 剪輯軟體〕
- 做法：pro 流程把人聲講解獨立錄(Sena 50S 藍牙直接錄音 / 外錄器),回後期跟 GoPro 畫面同步取代糊掉的相機音。同步招:開錄後先『拍手 clap』再『補一下油門 rev』製造音波尖峰,後期把兩軌的尖峰對齊。每個 cut 之間音軌做極短 crossfade(避免『喀』的爆音/click)。
- 數值：同步=clap + engine rev 製造 spike 對齊;每個 cut 間加極短 crossfade 消 click/pop
- 修：業餘 tell:人聲糊在風切裡聽不清、或剪接處『喀喀』爆音(沒做音訊淡接)

**依音樂節拍剪 + 速度斜坡(speed ramp)做過彎/加速的動感**  〔expert-consensus ·常識｜CapCut(Speed → Curve)〕
- 做法：選 clip → Speed → Curve,套預設 Montage / Bullet / Jump Cut,或選 Customized 自己拉曲線:把點往上拉=加速、往下拉到起始線下=慢動作。典型 motovlog 用法—直線路段加速、過彎/招牌瞬間慢下來,且把『速度切換點』卡在音樂節拍/重拍上。若速度轉換不順,點曲線下方 Smooth slow-mo → 選 Optical Flow 補幀。
- 數值：CapCut 預設 Montage/Bullet/Jump Cut;Optical Flow 補幀;拍攝 48/60/120fps 供慢動作;速度切點卡重拍
- 修：業餘 tell:整段等速直出沒節奏、慢動作卡頓掉幀、剪點跟音樂無關亂切

**23.976/24fps 出片做電影感,但慢動作素材要高 fps 來源**  〔anecdotal｜GoPro 拍攝 + 剪輯時間軸〕
- 做法：想脫離『action cam 直出感』走 cinematic:成片時間軸/輸出走 23.976 或 24fps(電影幀率,自帶動態模糊與電影感);需要慢動作的鏡頭則用 60/120fps 拍,放進 24fps 時間軸做 conform 慢放。社群進階做法甚至把無反相機固定在油箱包/車身拍 cinematic 鏡頭,跟 POV action cam 鏡頭交替剪。
- 數值：成片 23.976/24fps;慢放素材 60/120fps;A 機 action cam POV + B 機無反車身 cinematic 交切
- 修：業餘 tell:全片 GoPro 60fps 平板直出『太數位、太銳利』沒有電影味

**多角度切換(第一視角 POV ↔ 車身/外掛機位)維持節奏**  〔expert-consensus ·常識｜多 GoPro / 機位規劃 + 剪輯〕
- 做法：別整片只有一顆盔頂 POV。規劃 2-3 個機位交切:盔頂/下巴 chin(第一視角)、車身(油箱包、後搖臂、車尾)、定點/手持外拍(路過的他拍)。剪輯時每個機位卡在不同節奏點切換,讓觀眾不疲勞。配合上面的 clap+rev 把多機音畫同步。
- 數值：機位:chin POV + 油箱包/後搖臂/車尾車身機 + 定點外拍;切點對齊音樂節奏
- 修：業餘 tell:單一盔頂機位一鏡到底十幾分鐘、視角無變化,觀眾留存掉

**時速/地點 telemetry overlay 燒進畫面(GPS 速度、路徑、G force)**  〔expert-consensus｜Telemetry Overlay / RaceRender / DashWare / GoPro Quick〕
- 做法：錄影時開 GoPro GPS。後期用 Telemetry Overlay(社群評價 UI/功能優於 RaceRender)讀 GoPro 內嵌 GPS 資料,生成時速表(2D 經緯或 3D 含垂直)、GPS 路徑圖(可上速度/海拔色彩漸層)、G force 等儀表,輸出透明 overlay 疊回畫面。RaceRender/DashWare 是賽車/motovlog 老牌專用工具。
- 數值：錄影開 GPS;Telemetry Overlay > RaceRender(UI/功能);儀表:speedometer 2D/3D、GPS path 速度/海拔漸層、G force
- 修：業餘 tell:純畫面沒任何數據脈絡—觀眾不知道多快/在哪,少了 motovlog 招牌的速度沉浸感

**片長/留存:狠剪掉直線無事段落,別 raw 直出十幾分鐘**  〔expert-consensus ·常識｜通用(剪輯軟體)+ 承 Hao M86/M87 對位邏輯〕
- 做法：業餘最大 tell 不是技術是『沒剪』。把長直線無事、等紅燈、重複路段砍掉,只留有事件/有風景/有轉折的段落,用 speed ramp 把過場壓縮。承 Hao 既有規則:b-roll/montage 占比別蓋過主鏡(M86),且畫面要對上正在講的內容(M87)。風切糊掉的段落就當 b-roll、蓋 BGM 或旁白講過去(社群公認的救援法)。
- 數值：砍直線無事/等紅燈/重複路段;過場用 ramp 壓縮;噪段降為 b-roll+BGM/旁白;承 M86 占比 + M87 對位
- 修：業餘 tell:十幾分鐘 raw 直出、節奏拖沓無剪輯、觀眾前 30 秒就滑掉

**魚眼後期補救(來源是 Wide/SuperView 或不支援 Linear 的格式時)**  〔expert-consensus｜GoPro Player / Filmora / ffmpeg(lenscorrection)〕
- 做法：如果素材已是 Wide/SuperView,或拍的是 4K/Time Lapse 等不支援機內 Linear 的格式,後期去畸變:GoPro Player 內建 lens 校正、Filmora/VideoProc 有 GoPro lens correction profile;ffmpeg 可用 `lenscorrection` filter(k1/k2 桶狀失真係數,負值往內拉直)逐步試。
- 數值：ffmpeg lenscorrection k1/k2(負值校桶狀);GoPro Player / Filmora lens profile;會裁邊→拍攝留裕度
- 修：業餘 tell:直牆/地平線彎曲的魚眼感,且沒在拍攝端用 Linear 補救

_來源：havecamerawilltravel.com / community.gopro.com / dronevideohub.com / docs.gyroflow.xyz / repairit.wondershare.com / storytellertech.com_

## 🎓 教學長片(不露臉)

**螢幕錄影分辨率/縮放保命：錄製來源 ≥1440p 並開 HiDPI/Retina 2x**  〔expert-consensus ·常識｜OBS / 通用〕
- 做法：錄製端就決定畫質：螢幕錄影來源最少 1080p，理想 1440p 或 4K，並確認系統縮放是 HiDPI/Retina（Mac Retina 2x / Windows 顯示縮放 100% 但實體高解析）。原因=後製要 zoom 進 2x 才不會糊。ffmpeg 端若必須放大來源，先 scale 到大尺寸再 zoompan（見下條）。
- 數值：來源 ≥1080p（理想 1440p/4K）；zoom 倍率上限受來源限制：1440p 來源 zoom 2x OK、3x 開始看到像素、4K 才撐得起 3x
- 修：業餘 tell #1：錄 720p 放 1080p 時間軸→文字糊；或錄了卻無法 zoom（一放大就馬賽克）。720p 來源 zoom 2x 等於看 360p。

**重點處 punch-in zoom：2x、進場 350–500ms、ease-in-out、停留 ≥600ms**  〔expert-consensus｜CapCut / both〕
- 做法：在旁白講到關鍵 UI / 按鈕 / 數值的那一刻 zoom 進去。標準倍率 2x（200%）；1440p 來源用 2x、UI 本來就大用 1.5x、來源 4K 才用到 3x。進場動畫 350–500ms（不要 200ms 那種啪一下的硬切），緩動曲線用 ease-in-out（不是 ease-out）。
- 數值：倍率 2x（1.5x 細緻/3x 限 4K）；進場 350–500ms；停留 800ms–1.2s（文字 1.5–2s）；最短停留 600ms；緩動 ease-in-out
- 修：業餘 tell #2：全程滿版不 zoom，按鈕只有 80px 寬，手機上根本看不到在點哪→cognitive load 爆掉、觀眾走人（這是螢幕錄影最致命也最常見的錯）。也修『硬切 zoom』『zoom 太快暈』。

**zoom 頻率天花板：最快每 3–4 秒一次，不要連環 zoom**  〔expert-consensus｜both〕
- 做法：zoom 是調味料不是主食。同一段不要 zoom 超過『每 3–4 秒一次』，否則觀眾跟不上、會暈（mobile/大螢幕會誘發 vestibular discomfort 動暈）。原則：每個 zoom 都要有理由（旁白強調某詞、點某按鈕、出現數據），不要固定間隔機械式 zoom——固定間隔的 robotic zoom 正是 AI 自動工具的廉價 tell。混合工作流：自動 zoom 鋪底，關鍵時刻手動補。
- 數值：上限：最快每 3–4 秒 1 次；zoom 由語意/點擊觸發，非固定間隔
- 修：業餘 tell #3：要嘛完全不 zoom，要嘛學壞範例瘋狂 zoom／固定節拍 zoom→『一看就是自動生成』『暈到關掉』。pro 的 zoom 是 contextual，跟旁白語意綁定。

**ffmpeg 平滑 zoom：先 scale 到超大解析再 zoompan，否則抖**  〔expert-consensus｜ffmpeg〕
- 做法：ffmpeg 的 zoompan 直接用在影片上會一格一格跳（jerky），因為 zoom 量被 round 成整數像素。修法=先 upscale 到很大的中間解析度再縮放回來，給 zoompan 足夠像素內插。
- 數值：中間 scale=8000:-1；z 增量 ~0.0008/格；影片 zoompan 需 d=1；s= 設成輸出尺寸
- 修：業餘 tell #7：ffmpeg 自幹 zoom 一格一格抖（jittery / shaky）——沒做 upscale 那步的人都會踩。修掉『DIY zoom 比不 zoom 還醜』。

**游標平滑（cursor smoothing）：Bezier 內插把抖動游標變絲滑**  〔expert-consensus｜通用〕
- 做法：原始游標軌跡是高頻抖動的折線，pro 工具（Screen Studio / Rapidemo / Screenify）把原始游標點降到 4–5 個控制點，再用 Bezier 曲線內插＋移動平均濾波，畫出有自然加減速的滑順路徑。Screen Studio 是錄製時高頻記錄游標座標、export 時才套 Bezier。實作：平滑強度一根滑桿，預設中間值對多數內容剛好——往『自然』少平滑、往『電影感』多平滑。
- 數值：原始點降到 4–5 控制點＋Bezier 內插＋moving-average；平滑強度滑桿預設中間
- 修：業餘 tell #4：游標亂飛、抖、在畫面上鬼畫符→分散注意力、看起來很隨便。pro 的游標是平滑、有目的的移動。

**點擊回饋 + 快捷鍵 overlay：ripple/glow + keystroke 顯示**  〔expert-consensus ·常識｜通用〕
- 做法：每次點擊加一個會快速淡出的視覺指示：擴散圈（expanding ring）/ 漣漪（ripple）/ 微光（glow），顏色＋大小可調，動畫要『快速淡出』不要黏在畫面。按快捷鍵時用 keystroke overlay 把按下的鍵顯示在角落（例：⌘+Shift+P），這樣不用每個快捷鍵都口頭念。進階：Cursor Spotlight 把游標周圍以外的區域變暗/模糊，強制聚焦。
- 數值：點擊：ripple/ring 快速淡出；快捷鍵：角落 keystroke overlay；可選 Cursor Spotlight 暗化周邊
- 修：業餘 tell #5：點了東西但畫面沒反應指示，觀眾要猜你到底點了哪個；快捷鍵全靠嘴講、跟不上。修掉『不知道他在點什麼』。

**乾淨取景：圓角＋陰影＋漸層背景襯底，桌面/書籤/通知全清**  〔expert-consensus｜both〕
- 做法：錄製前：關通知（Do Not Disturb）、隱藏書籤列、關無關 app/分頁、清桌面圖示。後製：螢幕錄影不要貼滿版，縮到 ~90% 放在一個帶漸層/純色/品牌色的襯底上，加圓角＋柔和陰影（Screen Studio 風格的『虛擬相機 + padding + shadow』）。padding 給一致的留白，整支片用同一套背景模板＝品牌一致性。
- 數值：螢幕內容縮到 ~90% + 圓角 + 柔陰影 + 漸層/品牌色襯底；一致 padding；錄前開勿擾
- 修：業餘 tell：滿版露出個人檔案/書籤/通知跳出來→分散注意又顯得沒準備。pro 的畫面是 framed、有呼吸的留白。

**砍靜默/口誤做 jump cut，但教學片要留呼吸不能切太碎**  〔data-backed ·常識｜both〕
- 做法：用 jump cut 砍掉 um/ah/停頓/口誤/重複，把鬆散口播壓成資訊密集的節奏（工具：TimeBolt / SavvyCut / FireCut / Descript 自動砍 silence；常見預設砍 >3 秒的停頓，教學片可放寬到留 0.3–0.5s 句間呼吸）。但關鍵分寸：教學要『呼吸感』，不能像 vlog 那樣機關槍式硬切——深入解釋用長 take，提節奏才用快切。
- 數值：砍 >0.3–0.5s 靜默（vlog 風 >3s）；長講段每 30–60s 一個 pattern interrupt；解釋段留長 take
- 修：業餘 tell：上傳未剪原檔（一堆停頓口誤）；或反過來切太碎變機關槍、教學跟不上。修掉『拖沓』和『碎到無法吸收』兩端。

**每 15–25 秒一個視覺斷點（留存節拍器）**  〔data-backed｜both〕
- 做法：每 15–25 秒讓畫面換點東西：zoom / b-roll / 圖卡 / cutaway / 動畫 / 換 UI 視角。當斷點剛好落在旁白的重點或『金句』上，會給觀眾一個多巴胺微獎勵、把人黏住。對你這種不露臉的片，斷點來源主要是：punch-in zoom、概念動畫圖解、UI b-roll overlay、章節轉場卡。把這當『節拍器』排：拉一條時間軸，標出每段旁白重點，重點處放斷點。
- 數值：每 15–25 秒一個視覺變化；斷點對齊旁白重點/金句
- 修：業餘 tell：畫面長時間靜止不變（同一個全螢幕講 2 分鐘）→觀眾 30 秒內放空走人（視覺單調是留存殺手）。

**概念用動畫圖解，不要硬講：A-roll 旁白 + B-roll UI/動畫疊加**  〔expert-consensus｜both〕
- 做法：抽象概念（流程、架構、資料流、比較）不要只靠嘴講＋看靜止 UI——做動畫圖解。教學片結構＝A-roll（你的旁白/主敘事線）+ B-roll（螢幕錄影、UI 動畫、文字 callout、stock、概念動畫）。Asana 那類 pro 做法：在螢幕錄影上『疊』UI 動畫，旁白講到哪、對應的箭頭/高亮/圖塊就動到哪。真重點/數據要自生『有質感的動畫』（非陽春字卡），靜態生成圖務必靜止不亂 pan。
- 數值：A-roll=旁白；B-roll=UI動畫/callout/概念動畫；步驟用 sequential sync（先講後演）
- 修：業餘 tell：對著靜止 UI 硬講抽象概念，觀眾腦補不出來；或塞一張靜態圖就帶過。pro 用動態圖解降低理解成本。

**旁白與畫面精準同步：cut 卡句尾、b-roll 對齊講到的那句**  〔expert-consensus ·常識｜both〕
- 做法：每句旁白對齊它在講的畫面：講到某功能，畫面就 zoom/切到那個功能；b-roll 換點落在句尾不是句中。對你已有 M87（caption_broll_mismatch audit）＋逐句對齊規則完全吻合——把同一套用到教學長片：拉時間軸把旁白逐句斷句，每句配一個畫面動作（zoom/切UI/圖卡），cut 一律卡在句尾停頓。錯位（旁白已經講下一步、畫面還停在上一步）是最傷理解的 bug。
- 數值：cut 卡句尾停頓；每句旁白配一個對應畫面動作；跑 M87 對位 audit
- 修：業餘 tell：旁白和畫面各走各的——嘴上講 A、畫面停在 B，觀眾要同時 decode 兩條不同步的線→放棄。修掉『跟不上』。

**YouTube 章節（chapters）+ 章節標題當小標題鉤子**  〔data-backed ·常識｜通用〕
- 做法：在影片描述用時間戳建章節（00:00 起、每段一個時間戳＋標題）。反直覺但有效：給人跳轉反而看更久（找到要的段落＝good abandonment，2026 演算法不罰），且每個章節標題＝一個獨立小標題，可以寫得有懸念（不是『步驟二』而是『這步 90% 人做錯』）。教學長片配合每段一個視覺斷點，章節邊界就是天然轉場卡的位置。
- 數值：描述放時間戳章節；標題寫成懸念小標；good abandonment 不被演算法罰
- 修：業餘 tell：一鏡到底沒章節，觀眾找不到重點段落只能整支硬啃或直接關。pro 用章節降低導航成本＝提高停留。

**開頭 5–15 秒就給結果/重點，守住第一分鐘**  〔data-backed ·常識｜通用〕
- 做法：55% 觀眾在 60 秒前流失，平均 8 秒就決定去留。教學片開頭別鋪陳『大家好今天要教...』——5–15 秒內直接給：成品長怎樣 / 最後會學到什麼 / 最反直覺的那個重點。把最強的洞見/成果前置，能讓 30 秒留存拉高 15–20 個百分點。第一分鐘留存 >65% 的片，平均觀看時長高 58%。
- 數值：5–15s 內給結果/重點；前置強洞見可拉高 30s 留存 15–20pp；首分鐘 >65% 留存→AVD 高 58%
- 修：業餘 tell：開頭冗長自我介紹/廢話暖場→『The Cliff』前 15–30 秒陡降然後躺平＝hook 失敗。修掉開頭流失。

**教學片留存基準＋片長對照（拿來自評）**  〔data-backed｜通用〕
- 做法：用這套數字判斷自己剪得好不好（不是憑感覺）：教學/how-to 內容健康留存 45–55%（教育類本來就是留存最高的 niche，平均 42.1%，遠勝 vlog ~21.5%）。依片長健康平均觀看百分比：<5 分 50–70%、5–15 分 40–55%、15–30 分 30–45%、>30 分 25–35%。中點留存 >40% 算健康；若比預期陡降＝pacing 有問題該回去找哪段太拖/太碎。
- 數值：how-to 健康 45–55%；<5min 50–70%/5–15min 40–55%/15–30min 30–45%/>30min 25–35%；中點 >40% 健康
- 修：業餘 tell：不看留存曲線、不知道哪段在掉，盲剪。pro 用基準＋曲線形狀做 retention surgery 針對性修補。

_來源：autozoom.app / www.screenify.studio / screen.studio / www.opus.pro / www.screenstory.io / usercomp.com_

## 💻 軟體/AI demo

**Click-triggered 自動 zoom（每次點擊就拉近）**  〔expert-consensus｜both〕
- 做法：核心模型：每個滑鼠 click = 一個 zoom keyframe。zoom 在「互動之前/當下」拉近，不是事後才拉。Screen Studio (mac) / FocuSee / Rapidemo (Win) 錄完自動套，每個 click 在時間軸生成可調 keyframe。
- 數值：放大倍率 1.5x（UI 本來就大時）/ 2x（1440p 來源的 sweet spot）；3x 會糊/壓迫除非 4K 來源。zoom-in 時長 200ms（快狠 snappy）~350-500ms（電影感，ease-in-out）。click 後 hold：文字少 0.8-1.2s、表單/錯誤訊息等文字多 1.5-2s，最低 0.6s（低於會被當成 glitch）。預設 hold ~1.2s。
- 修：業餘整段 1x 全螢幕硬錄 → 手機上 4px 按鈕/小字看不到、觀眾不知道你在點哪。zoom 把關鍵 UI 放大到可讀。

**zoom 頻率上限（避免 pinball 暈眩）**  〔expert-consensus｜both〕
- 做法：限制 zoom 密度：每 3-4 秒最多 zoom 一次，不要每個小動作都拉。轉場到新區域前先 zoom out 回 1x 再移動，不要在放大狀態下橫移。3 分鐘片 zoom 段別超過 ~45-60 個。
- 數值：上限 1 zoom / 3-4 秒；ease 曲線 ≥500ms + 倍率降到 1.5x 給動態敏感觀眾；橫向捲動內容 + zoom = double-motion 暈眩，禁用。
- 修：業餘「學會 zoom 後到處亂 zoom」→ 畫面像彈珠台 (pinball machine) 一直彈進彈出，觀眾跟不上、看到頭暈。

**Cursor 平滑化（把抖動手變絲滑）**  〔expert-consensus｜both〕
- 做法：raw cursor 座標套 moving-average filter + bezier 插值，把 15 個中間點縮成 4-5 控制點。Screen Studio / Screenify 錄製時即時做、可事後調強度。
- 數值：平滑強度：20-30% 去微震（給動作本來就穩的人）/ 40-60% 一般教學（最通用）/ 70-90% 行銷片但會變機器人。回應延遲 50-100ms 即時感、150-250ms 更戲劇但有 lag。Rubber-banding 就降強度。修「點擊脫節」把平滑降到 40-50%。
- 修：業餘「游標亂飄、急停急衝、手抖微震」→ 一看就是沒剪過的生錄。pro 的游標是有意圖的滑行。

**用 30fps 錄而非 60fps（反直覺）**  〔expert-consensus｜both〕
- 做法：UI 螢幕錄影錄 30fps 反而比 60fps 看起來更平滑——因為 60fps 抓到更多游標微調的中間幀，把手抖放大。除非有快速動畫/遊戲才上 60fps。Export：UI 內容 30fps、快動作 60fps。
- 數值：錄製 + Export 一般 UI demo = 30fps；只有 fast motion 才 60fps。Export 1080p bitrate 8-12 Mbps、1440p 15-25 Mbps、H.264/H.265。
- 修：業餘以為 fps 越高越專業 → 60fps 反而暴露每一格的游標微抖。

**Ease 曲線（禁用 linear 機器人運動）**  〔expert-consensus｜both〕
- 做法：每個 zoom/移動的 keyframe 插值改 Ease 或 Smooth，不要 linear。Screen Studio 右鍵 keyframe 設 Ease/Smooth。CapCut 關鍵幀預設 linear→改曲線。ffmpeg zoompan 用非線性表達式或分段 setpts/easing 取代等速 'pzoom+0.001'。
- 數值：建議 ease-in-out 500ms+ 取代 snappy 200ms ease-out；倍率限 1.5x 比 2x/3x 更穩。
- 修：業餘 snap-zoom-snap、等速推進 → 機械、廉價、跳。pro 全部 ease-in-out。

**Click 視覺回饋（ripple/pulse）**  〔expert-consensus ·常識｜both〕
- 做法：每次點擊加一個擴散環/脈衝，讓觀眾看到「你剛剛點了這裡」。FocuSee 內建 8 種 click effect、Screenify 有 S/M/L ripple。CapCut 可在 click 點位疊一個圓環貼紙 + 縮放 keyframe 做 ripple。ffmpeg 用 drawbox/overlay 一個淡入淡出的環在 click 座標。
- 數值：ripple 樣式：向外擴散環或出現後淡出的圈；尺寸 S/M/L 可調；色彩 + 動畫時長可設。步驟教學（要被複製）最該開。
- 修：業餘「畫面突然跳轉但沒人知道為什麼」→ 觀眾錯過互動瞬間、無法跟著複製步驟。

**游標加大 + idle 自動隱藏**  〔expert-consensus｜both〕
- 做法：標準游標只有 ~12px 箭頭，錄製時放大讓手機觀眾看得到；shake-to-locate 找游標時放大 3-4x。不互動時自動隱藏游標減少干擾。FocuSee/Screen Studio 內建 auto-hide idle cursor。
- 數值：游標放大到比原生大（手機相容）；標準 12px → 找游標時 3-4x；idle 自動隱藏。
- 修：業餘游標在繁忙畫面消失、手機上看不到 → 觀眾找不到焦點；閒置游標停在畫面中央擋內容。

**Spotlight / dim 聚光（複雜介面用）**  〔expert-consensus｜both〕
- 做法：把游標周圍一圈保持亮、其餘畫面壓暗，強迫視線到游標。IDE/設計工具/試算表這種繁忙介面用。Screenify spotlight radius 80-300px、dim 不透明度 40-90%。ffmpeg 可用一個中央透明、四周半透明黑的 overlay PNG 跟著游標座標走。
- 數值：光圈半徑 80px-300px；變暗不透明度 40%-90%。適用 IDE、設計工具、試算表這類複雜介面；簡單頁面不需要。
- 修：業餘在塞滿元件的 IDE/dashboard 裡觀眾完全不知道看哪 → spotlight 強制聚焦。

**加速/跳過無聊等待段（loading、慢操作）**  〔expert-consensus ·常識｜both〕
- 做法：錄的時候照自然節奏錄（慢載入、打錯字、找分頁都留著），事後再清。兩種壓縮時間：(1) 變速——loading spinner 用 4x-20x 快轉或直接砍。(2) jump cut——10 秒走廊每 2 秒跳 30 幀，幾分之一時間講完。CapCut 選段右鍵變速 / 拆分刪除。ffmpeg：砍段用 trim+concat，變速用 setpts=PTS/N（影像）+ atempo（音）。
- 數值：loading/spinner 不留 1x；長操作每 2 秒跳 30 幀做 jump cut；但「跳掉的動作會讓觀眾看不懂流程」時別跳（如關鍵安裝步驟）。
- 修：業餘「沒人想看 spinner 轉 8 秒」整段 1x 留著 → 拖、悶、掉觀眾。pro 把死等壓成 1-2 秒或直接消失。

**去靜音/死空檔（旁白型 demo 收緊節奏）**  〔data-backed ·常識｜both〕
- 做法：自動偵測靜音段切掉，留 padding 不要切到字頭字尾。CapCut 沒原生但可手動拆分刪段；DaVinci/Premiere/Final Cut 有 silence slicer；TimeBolt/Recut 一鍵。ffmpeg 用 silencedetect 找段再 trim+concat（注意 Hao 的 M95：句間死空檔要 atrim 不要 aselect）。
- 數值：靜音門檻依環境調（家用環境 -35dB 比 -60dB 實際，太低會漏掉 room tone 之上的真靜音）；padding：教學/解說 0.3-0.5s（最大化節奏）；高能片左 40ms 右 80ms；一般左 80-120ms 右 150-200ms 讓句子收尾自然不被切爆。
- 修：業餘旁白一堆呃、長停頓、慢吞吞 → 慢節奏 + 長沉默是 tutorial 掉觀眾頭號原因。

**Callout / 箭頭 / 步驟編號疊層**  〔expert-consensus ·常識｜both〕
- 做法：在 UI 上疊 callout 框、箭頭、step number、feature label，不暫停流程就引導視線。CapCut：素材庫加箭頭/框貼紙 + 文字 + 縮放/淡入 keyframe。ffmpeg：drawbox 畫框、overlay 箭頭 PNG、drawtext 標籤，用 enable='between(t,a,b)' 控制出現時段。配合 zoom 在同一處更有效。
- 數值：callout 用在指特定按鈕/欄位；step number 配多步驟流程；標籤短（feature label 不寫長句）。框/箭頭淡入 ~200-300ms 不要硬跳。
- 修：業餘「滑鼠指過去但沒指示」→ 觀眾不知道該看哪個元件。箭頭/框直接點出特定 UI 元素。

**Clean 錄製（去 chrome / 通知 / 雜亂）**  〔expert-consensus ·常識｜both〕
- 做法：錄前：關所有 app 跟分頁、隱藏桌面圖示、開 Do Not Disturb/專注模式關通知、用乾淨瀏覽器 profile（無書籤無擴充）、字體先放大 2-4 點。mac 隱藏桌面圖示：defaults write com.apple.finder CreateDesktop false && killall Finder。
- 數值：字體比平常大 2-4 點（1080p 播放不會小到看不到）；解析度至少 1920x1080、YouTube 最佳 2560x1440；避免非標準原生解析度（如 1512x982）造成縮放糊。
- 修：業餘畫面有別的 app、私訊跳出、書籤列暴露隱私、桌面一堆圖示 → 一看就不專業 + 漏個資。

**Before/After 倒敘結構（先給結果再回頭講怎麼做）**  〔data-backed｜both〕
- 做法：pro demo 先秀結果——做好的 dashboard、跑起來的自動化、生成的報告——再倒回去講怎麼達成。等於把 before/after 套在軟體 demo 上。剪輯上：開頭 5-10 秒放「成品畫面 + 漂亮數據」當 hook，再進步驟。
- 數值：前 30 秒是留存決勝點，frontload 成品 + 高價值視覺 + hook。mid-funnel demo 甜蜜長度 60-120 秒。
- 修：業餘從第一步流水帳講到最後 → 觀眾不知道終點長怎樣、沒理由看下去。先給 payoff 才有動機。

**節奏對齊講解（cut/zoom 卡在旁白句點）**  〔expert-consensus ·常識｜both〕
- 做法：畫面動作（zoom、cut、callout 出現）對齊旁白講到的點，不要畫面講 A 旁白講 B。Hao 既有 M87 b-roll 對位 + 「cut 卡句尾」直接適用 demo：zoom 進某 UI 的瞬間 = 旁白正好念到那功能名。
- 數值：zoom-in 對齊旁白提到該元件的那一刻；hold 時長配合念完該句（文字多給 1.5-2s 讓人邊聽邊讀）。
- 修：業餘畫面跟旁白各走各的 → 觀眾要同時消化兩條不同步資訊，累、容易跳出。

**鍵盤快捷鍵 overlay（coding/軟體 demo）**  〔expert-consensus｜both〕
- 做法：把按下的按鍵即時顯示在畫面角落，觀眾才學得到 workflow。mac KeyCastr、Linux Screenkey、Win 有 Carnac/KeyCastow 等。CapCut/ffmpeg 事後也可 drawtext 在按鍵時段疊上鍵名。
- 數值：顯示所有按下的鍵；放角落不擋主內容；coding demo 必開。
- 修：業餘「畫面突然全選/跳轉但沒人知道按了什麼」→ 觀眾無法複製你的快捷操作。

**裝置外框 + 背景 padding（去裸錄感）**  〔expert-consensus｜both〕
- 做法：把螢幕錄影放進瀏覽器外框/筆電/手機 bezel，四周加品牌色漸層或純深色 padding，不要滿版裸貼。Screen Studio/FocuSee 內建 mockup + gradient 背景。CapCut 縮小主畫面 + 圓角 + 底層漸層；ffmpeg pad + overlay 圓角遮罩（接 Hao M92 非滿版→模糊填底/裁到只剩內容區）。
- 數值：背景用品牌色漸層/mesh gradient/純深色 + padding；圓角 + 陰影增加層次；不要把錄影頂滿整個 frame。
- 修：業餘滿版裸錄、四邊頂死 → 平、廉價、沒設計感。外框 + padding 立刻像 SaaS 官方 demo。

**克制式剪輯（少即是多，別炫技）**  〔expert-consensus ·常識｜both〕
- 做法：目標式微調而非滿屏特效：剪掉頭尾摸索、砍步驟間死空氣、刪口誤、段落間用 fade/cross-dissolve。過量 jump cut + 花俏轉場反而像業餘。Hao 既有「教學長片字幕白字黑框不多色」同理——demo 也走克制。
- 數值：段落間 fade/cross-dissolve；避免每個 cut 都加閃光轉場；transition 只在真的換主題時用。
- 修：業餘以為加越多特效/轉場越專業 → 雜亂、廉價、分散注意。pro 是 subtle, purposeful。

_來源：www.screenify.studio / screen.studio / creatomate.com / one-rec.com / focusee.imobie.com / zight.com_
