# 六領域剪輯語法（2026-08-06 六路網研入庫）

> 來源等級：**📚 網研多來源交叉**（低於 📏 自家 teardown 實測一級）。單一來源說法各段已標註。
> 產出流程：6 個並行研究 agent × 4-8 輪 WebSearch（中英雙語）× 真實來源清單（禁編造）。
> **升級路徑**：creator 丟該領域樣本到 `<samples>/` → `teardown.py` 實測 → 該節升 📏。
> 位階：本檔服從所有 creator 裁決（S-R 讀得完/一稿三發/M9/M10/S-P）——衝突時裁決贏。

---

## 遊戲短影音（精華集錦/梗剪/實況切條，直式 Shorts/Reels/TikTok）

### Hook（開場 0-2 秒）
- 爆點前置（多來源一致，中英圈都講）：把最炸的 0.5-1.5 秒畫面複製貼到片頭當預告，正片再從頭播。集錦/切條一律先給結果，不玩懸念
- 切進動作中段開場：素材原始開頭通常有 3-5 秒鋪陳，砍到只剩高潮前 1-2 秒；首幀必須「畫面正在動」，禁止靜止幀起手
- 首幀文字 hook：4-7 字大字高對比，句式=「最後1秒反殺」「這操作0.1%玩家做得到」「他還不知道…」——字造懸念、畫面給動作，靜音也要能懂
- 敘事型（GTA RP/Minecraft 劇情向）才用懸念開場：「結局你絕對想不到」+ 完整張力弧；集錦型用懸念開場=自殺
- 演算法目標：前 3 秒留存要 >70%，低於就是 hook 爛（單一來源 virvid 給的門檻數字，但「前3秒定生死」多來源一致）

### 節奏
刀速：每 2-3 秒一刀，畫面每 ≤2.5 秒要有變化（刀/縮放/新字幕擇一）。長度：集錦 15-30s（完播率 70-85% 最高）；快節奏射擊（Valorant/Apex）15-30s 極簡鋪陳；MOBA 30-60s 走「局面+開打+結果」；敘事型 60-90s（完播僅 40-55%，用故事換互動率）。TikTok 演算法在 3/10/20 秒三個 checkpoint 評估，完播 ≥75% 才大量派發（以上具體數字主要來自 Clypse 單一來源，量級與中文圈 15-60s 說法一致）。剪輯時間一半砸在前 3 秒——中英兩獨立來源同講。

### 字幕
首幀 hook 字：4-7 字、大字、高對比，放上下安全區、不擋準星/擊殺 feed/血條。字幕雙功能（DOR）：①交代情境（角色/武器/局面，一句就好）②節奏強調（擊殺數、驚嘆詞卡拍點彈出）。實況切條：全程 AI 逐字字幕再人工校對——沒字幕的切條原創度會被判低。上色：白字為主，只給結果詞/數字上色（接 creator white-first 鐵則）。梗字卡（「？？？」「壞了」「他急了」）只在反應瞬間閃 0.5-1 秒，當音效用不當旁白用。

### 結構
30s 集錦型：0-2s 爆點前置（最炸畫面+hook 大字）→ 2-5s 最小情境（一句字幕交代局面）→ 5-20s 加速鋪墊（每 2-3s 一刀，刪光走路/搜物資/重生/讀取）→ 20-27s 高潮卡 BGM drop（zoom punch+impact 音效）→ 27-30s 停在 impact 秒收（擊殺回饋/勝利畫面/實況主反應），尾幀=首幀做無縫循環（觀眾平均多看 2-3 遍）。60-90s 敘事型：懸念 hook → setup → 張力升級（每段小 payoff 接新鉤）→ 大 payoff → 反應收尾。切條型：金句/笑點前置 → 前因 → 完整梗 → 笑聲落點收。

### 剪輯手法
- Zoom punch：強拍瞬間畫面放大 5-10% 再彈回，配 impact 音效——只放拍點，全片不超過 3-4 次
- 慢動作蓄力：高潮前 0.5-1s 降速，drop 瞬間彈回原速；速度反差=爆點感（phonk 速變剪的核心）
- Beat sync：波形尖峰處下 marker 當剪輯格線，每刀落拍；進階=遊戲槍聲/擊中音對齊音樂拍點
- 梗音效：vine boom（約1秒乾聲短尾）配 zoom-in/定格/螢幕震動三選一；高級用法=爆點前 0.3s 靜音再爆（silence-to-impact）；笑聲音效墊在笑點後
- BGM 二分法：集錦=音樂主導（phonk/EDM，節拍越明顯越好剪，用免版稅曲）；切條有人聲=BGM 音量壓到 ≤15% 純音樂墊底，絕不搶話
- 循環尾：首尾同幀或同音效，讓觀眾無感重播——寫腳本時就先定首尾幀，不是剪完才補

### CTA
集錦型結尾不加口播 CTA——秒收+無縫循環本身就是留存策略，多講一句就掉完播。要 CTA 用一行字幕「還有更扯的→追蹤」壓在 impact 畫面上 ≤1 秒。切條/敘事型可用留言鉤：拋爭議問題「這波誰的鍋？」「你會怎麼打？」讓留言區吵起來。

### 常見死法
- 開頭保留原始鋪陳（走路/loading/寒暄）——50-60% 流失發生在前 3 秒
- payoff 之後還拖（賽後結算/感謝詞/再看一次回放）——end on impact，多一秒都在掉完播
- 特效與梗音效堆滿全片——zoom/boom 不放拍點=廉價感；DOR 明講 sparingly only on beat
- BGM 用有版權商業曲→黃標/下架；集錦一律免版稅或平台曲庫
- 字幕壓在準星/擊殺 feed/血條上——遊戲 UI 區=禁字區
- 片型錯配：結果一眼看懂的素材硬做敘事（或需要前因的素材硬剪集錦）——素材決定片型，先看素材再選結構
- 切條純搬運無二創（無字幕/無解說/無梗）——抖音/YT 都判低原創限流；字幕+節奏重剪+梗音效=最低二創門檻

### 來源（14）
- https://blog.eklipse.gg/beginner-guide-2/stream-hook-strategy-first-two-seconds.html
- https://clypse.ai/blog/best-tiktok-gaming-clip-length-2026
- https://clip.dor.gg/en/blog/how-to-make-gaming-montage
- https://www.opus.pro/blog/ideal-youtube-shorts-length-format-retention
- https://blitzcutai.com/blog/best-youtube-shorts-hooks-2026
- https://virvid.ai/blog/first-3-seconds-hook-faceless-shorts-2026
- https://schedulala.com/blog/youtube-shorts-editing-tips-pro-techniques
- https://www.yingyiapp.com/pages/?id=582 （影忆：直播切片极速剪辑指南）
- https://zhuanlan.zhihu.com/p/562501332 （知乎：直播切片原创度）
- https://www.opp2.com/330314.html （青瓜传媒：完播率8技巧）
- https://www.mariosomedia.com/blog/seamlessloop
- https://soundbuttons.com/blog/113/18-best-vine-boom-sound-effect-for-content-creators
- https://technosports.co.in/youtube-shorts-phonk-edit-minecraft/
- https://www.youtube.com/intl/zh-TW_hk/creators/shorts/ （YT 官方台灣創作者頁：循環播放技巧）

---

## 開箱/3C 評測直式短影音（Shorts/Reels/TikTok）

### Hook（開場 0-2 秒）
- 包裹剛到型：0-2 秒手已在撕包裹，配句式「這東西剛到，我必須給你看」；禁空景慢起手（多來源一致）
- 反直覺宣言型：「這台 X 千的打爆了 Y 萬的」— 逼觀眾同意或反駁，開口即結論（virvid + 中文來源一致）
- 視覺震撼首幀：首幀放全片最強一格 — 大數字塞滿畫面/前後對比/微距細節；60%+ 靜音觀看，首幀要無聲也能懂（virvid）
- 價格懸念型：先秀質感不說價，字卡寫「猜多少錢」，價格壓到轉換段才揭（creetr + flowering0402 結構推導）
- 直問痛點型：「為什麼大家都買錯___？」— 對同好圈直接點名選購迷思（virvid Direct Question 型）

### 節奏
每 2-3 秒一刀（多來源一致；中文來源說 3-5 秒，取 2-3 為佳）；每 2.5 秒畫面必須有變化：新鏡頭/新字/新動作（conthunt「Visual Velocity」，單一來源）。前 3 秒流失 50-60%，intro 留存目標 >70%。全片 15-45 秒甜蜜點。慢動作壓到 40-60% 給揭露瞬間、快轉 150-300% 壓縮拆箱過程（schedulala，單一來源）。每 5-7 秒放一個 pattern interrupt 重置注意力。

### 字幕
Hook 字卡 4-7 字、高對比、放中央安全區（1080x1350 中間帶，避底部/右側 UI 遮擋）。首詞就上字，不能延遲 2 秒才進（virvid）。停留時間：每 3 詞 ≥1 秒（中文約 4-8 字/卡 ≥1 秒）。規格不唸清單 — 做成 overlay + 對比條動畫，只挑 1-2 個可感知數字（續航時數/克重/價差），關鍵數字單獨上色放大。85% 靜音觀看（schedulala 稱 85%、virvid 稱 60%+，區間看待）— 全片字幕必燒。

### 結構
30-60 秒六段骨架（creetr 秒級 + flowering0402 台灣 3C 實務吻合）：0-2s hook（包裹/宣言/首幀震撼）→ 2-8s 期待段（包裝細節+ASMR 收音，不搶拍）→ 8-20s 揭露段（開箱一鏡到底+微距推鏡）→ 20-30s 真實反應（本格式的情緒核心；不露臉可用手部動作+字卡反應替代）→ 30-45s 功能實測（只演 1-2 個賣點，規格 overlay 進場）→ 40-55s 價格/優惠揭露 → 末 3-5s CTA 或接回首幀做 loop。

### 剪輯手法
- 轉盤 360 慢轉 + 微距慢推：靜態商品動感兩大來源；轉盤放素背景才能乾淨 loop，微距拍撕膜/接縫/按鍵
- whip pan / snap zoom 接場：前鏡尾快甩、後鏡頭同向起甩，在 motion blur 中切 — 開箱換配件段落專用
- ASMR 微聲音放大：撕膜/膠帶/磁吸蓋 click 全收乾淨音；B-roll 段不配旁白時把微聲音當主角（3C 保護膜=ASMR 金礦）
- 規格對比條動畫：數字逐個跳出+橫條增長，不唸稿；螢幕一次只留一組對比，一卡一個結論
- 競品 split screen：同一動作兩邊同幀起跑、兩側都上名稱標籤、一次只比一個變數（開機速度/對焦/音量）
- J-cut：下一鏡聲音先進約 0.5 秒再切畫面，段落間不斷氣（MKBHD 手法）

### CTA
價格揭露=轉換點：壓在 40-55 秒段（60 秒片）或全片約 70% 處，揭價瞬間配字卡放大+音效。末 3-5 秒單一指令：「連結在留言」或引戰式提問「你會買嗎？」「iPhone 派還是安卓派留言報到」— 同好圈站隊題最能引 comment。或不做 CTA、剪成無縫 loop 接回首幀衝重播率。

### 常見死法
- 慢起手：logo 動畫/音樂前奏/桌面空景進前 3 秒 = 直接損失一半觀眾
- 規格連唸：照 spec 表逐條唸 = 死；規格只能「演」不能「唸」，一支片最多 2 個數字
- 價格開頭講掉：懸念沒了，觀眾沒有留到 70% 的理由
- 字卡壓到 UI 區：底部/右側被讚訂閱按鈕蓋住，數字看不到等於沒放
- 硬套圈內梗：沒累積信任就用同好黑話會有假味 — niche 觀眾「聞得出假專業」（多來源一致）
- 對比不公平：兩邊不同幀起跑、一次比多個變數 → 留言區先質疑方法再質疑你
- 畫面 2.5 秒以上零變化：中段規格講解最常在這死

### 來源（15）
- https://virvid.ai/blog/first-3-seconds-hook-faceless-shorts-2026
- https://creetr.com/blog/unboxing-video-guide
- https://schedulala.com/blog/youtube-shorts-editing-tips-pro-techniques
- https://conthunt.app/blog/how-to-edit-youtube-shorts
- https://www.flowering0402.com/post/為什麼高端-3c-開箱要做「直式短影音」才賣得動？
- https://www.eleanorfilm.academy/blog/short-video-skill
- https://vidiq.com/blog/post/make-youtube-unboxing-video/
- https://www.maono.com/blogs/news/asmr-tech-unboxing-guide-tips-gear-monetization-strategies
- https://www.pippit.ai/resource/how-to-use-split-screen-video-to-compare-product-features
- https://www.descript.com/blog/article/best-split-screen-video-tools
- https://www.premiumbeat.com/blog/create-seamless-transitons-whip-pan/
- https://videohighlight.com/v/0qiXOFfMrbQ
- https://www.photoworkout.com/best-rotating-stand-for-photography/
- https://kreatli.com/guides/youtube-shorts-safe-zone
- https://www.opus.pro/blog/ideal-youtube-shorts-length-format-retention

---

## DIY/手作/改造/修理 直式短影音（Shorts/Reels/TikTok）

### Hook（開場 0-2 秒）
- 成品爆閃開場（多來源一致）：前 0-2 秒先亮完成品 wow 畫面 → 立刻跳回第一步爛材料，觀眾為了看「怎麼變的」留下來
- Before 慘況特寫：主體撐滿整個畫面開場（禁遠景空鏡），髒/破/爛越具體越好，字卡一句「這個要救活」
- 反差句式：「大部分人做X都做錯了」「別再用X方法做Y」「沒人告訴你做X的這件事」（2026 實測榜單句式，多來源）
- 好奇缺口：不先給成品——「這堆垃圾 30 秒後會變成你想不到的東西」，成品押到最後才 reveal（與成品前置二選一，依成品驚豔度決定）
- 失敗自白開場：「我失敗了三次才做出來」→ 先給挫折建立懸念，兼收真實感（方向多來源支持）

### 節奏
總長 15-45 秒最佳（社群 feed 區間，多來源）；10-30 秒可做循環結構刺激重播。每 2-3 秒一個 jump cut，畫面每 2.5 秒必須有動作/切點/新字卡（visual velocity）。縮時壓縮比：多小時流程壓 20-40x，一小時內流程壓更少（單一來源 influencers-time，但方向合理）；速度要配材料邏輯——皮革陰乾和 CNC 切削不該同速，等速硬壓觀眾感覺得出在藏 dead time。關鍵動作（第一刀、上色、收尾拋光）切回原速+原聲，全片 2-3 個原速錨點。前 3 秒留存目標 >70%，低於此 = hook 重做。

### 字幕
步驟編號字卡：「1/5 裁切」格式，數字編號要大要顯眼；一屏最多 1-2 短句，字幕塊停留 2-4 秒。hook 字卡 = 一句承諾（做什麼+多便宜/多快），≤10 字。上色規則：只 highlight 關鍵詞——材料名、數字（成本/尺寸/時間）、動詞；快節奏段落一次只上 1-3 個字（fast-read pacing）。粗體無襯線+高對比，別做字牆；長句拆成 2-3 塊依序出現。字幕是導覽不是逐字稿：每步只寫「動作+關鍵參數」，例「熱熔膠 固定 10 秒」。

### 結構
0-2s 成品閃現或 before 慘況特寫（主體滿框）→ 2-5s 材料/起點一鏡帶過+承諾字卡（「$100 改造這張桌子」）→ 5-25s 過程壓縮段：縮時當骨架、每 2-3 秒一切、步驟字卡逐步跳、2-3 個關鍵動作切回原速原聲 → 中段（約 15-20s 處）可插 1-2 秒失敗/意外 beat 當 pattern interrupt → 倒數 5 秒 reveal：轉場+SFX 進成品，before/after 同機位同光對比 → 最後 1-2s 收藏 CTA 字卡。亮點絕不能埋超過 20 秒——那之前 70% 人已滑走。

### 剪輯手法
- 縮時骨架+原速打點：全片縮時鋪底，第一刀/上膠/拋光等 2-3 個錨點鏡頭切回原速+放大原聲，做出「壓縮但誠實」的節奏
- Cover the cut：jump cut 時換機位角度或 zoom in/out 約 20%，切點多但不跳 tone（pattern interrupt 類技巧實測提升觀看 20-35%）
- Reveal 轉場三選一：whip pan（甩鏡接甩鏡）/ object swipe（物體掃過鏡頭換景）/ 手遮鏡頭；before/after 必須同機位同光同構圖，反差才炸；reveal 瞬間配一個重 SFX
- ASMR 原聲層：切割/打磨/撕膠帶聲收近收大，BGM 壓低墊底；配樂過滿蓋掉工具聲會讀起來像廣告（「戲劇性配樂配手作＝最好是諷刺、最壞是不誠實」）
- 手永遠入鏡：賣的是手作感，手要反覆出現在畫面裡，不能只拍機器和成品（單一來源但與 craft 類邏輯強一致）
- 失敗畫面保留 1-2 秒：歪掉的縫線、重擺工具、擦汗——微小不完美是真實訊號，留下建立信任；但只留 beat 不留全程（多來源方向一致）

### CTA
DIY 是「收藏型」內容——收藏權重＞讚。主 CTA：「收藏這支，下次動手直接照做」。做法：3-5 秒處先用字卡輕埋一次，成品 reveal 時再壓一次收藏字卡（只在片尾會漏掉早離場的人）。具體型句式贏過空泛型：「存起來，週末做」＞「喜歡請按讚」。系列改造片用「Part 2 修燈」預告當第二 CTA。

### 常見死法
- 打招呼慢熱：「哈囉大家今天要教…」= 必死開場，前 5 秒沒進正題就被滑
- 亮點埋太深：最精彩的變化放在 15-20 秒後，到那時 70% 觀眾已走（buried lede）
- 假壓縮：全程等速縮時把 dead time 一起壓進去，觀眾直覺感受得到在灌水
- 配樂蓋原聲：BGM 開太滿蓋掉工具聲，手作片瞬間變廣告片，ASMR 價值歸零
- 湊長度或砍過頭：塞 filler 撐秒數、或 3 分鐘的工程硬砍成 30 秒讓人看不懂步驟，兩者都殺留存
- 成品不夠 wow 還硬做成品前置：開場閃一個普通成品反而勸退——成品普通就改走好奇缺口或失敗敘事線

### 來源（16）
- https://clippie.ai/blog/video-editing-techniques-creators-2026
- https://schedulala.com/blog/youtube-shorts-editing-tips-pro-techniques
- https://framesurfer.com/blogs/how-to-get-more-views-on-youtube-shorts
- https://www.influencers-time.com/time-lapse-process-videos-briefing-craft-without-faking-it/
- https://socialk.it/en/blog/video-hooks-first-three-seconds
- https://www.selfstorming.com/guides/social-media-hooks/tiktok-video-hooks
- https://www.opus.pro/blog/instagram-reels-caption-subtitle-best-practices
- https://project-aeon.com/blogs/text-overlay-on-video-master-engaging-techniques
- https://www.reframex.ai/how-to-create-before-and-after-transformation-videos-for-reels/
- https://vidpros.com/best-transitions-for-short-form-videos/
- https://miraflow.ai/blog/youtube-shorts-mistakes-to-avoid-2026
- https://adshortsai.com/en/low-retention-on-youtube-shorts/
- https://www.digitalmarketinghandbooks.com/blog/the-role-of-ctas-in-boosting-shares-and-saves
- https://igdm.me/blog/how-to-get-more-saves-and-shares-instagram-posts
- https://yuyu-creative.tw/short-video-production
- https://storyofdream.com/short-video-making-tutorial-for-beginners/

---

## 寵物/生態觀察短影音（直式 Shorts/Reels/TikTok）

### Hook（開場 0-2 秒）
- 行為進行中開場：首幀=動物「正在做事」的動作中幀（狗衝出去/蟲正在搬獵物），配一行字幕。多來源一致：1-3 秒內定生死；TikTok 約 1.7 秒滑走（單一來源 fluxnote 數字）
- 寵物 POV 內心 OS 開場：第一句就是牠的台詞「我沒有，是牠先動手的」——擬人內心戲是 2026 寵物區最強格式（多來源一致）
- 翻案句式開場：「牠不是在X，是在Y」——用糾正常識當 hook，取代「你知道嗎」（衍生自多來源 hook 研究：驚人事實+但書結構讓停留率約 2.5 倍，topmostads 單源數字）
- 挑戰假設問句：「為什麼這隻鳥從來不落地？」——問句迫使大腦自動找答案（多來源一致）
- 紀錄片旁白反差：用 Attenborough 式莊重旁白講一隻很廢的動物，反差即笑點；無臉動物（蟲/鳥/魚）直接獲得主角感（格式已成 meme 模板，多來源）

### 節奏
互動型：全長 10-30s、甜蜜點 10-18s（fluxnote 單源數字），一支只講一個行為事件；每 5-8 秒一個小轉折/章節卡（vortexxcel 單源）。安靜觀察型：可到 25s+ 但必須 seamless loop；尾幀≈首幀讓人不自覺重看，2026 演算法 rewatch 權重加重（多來源一致）。內心 OS 節奏＝行為 beat 節奏：動物一個動作→一句短台詞→停半拍，不連珠炮。

### 字幕
內心 OS 一次一短句 ≤10-12 字，精準壓在行為瞬間（歪頭/回頭/僵住那格才出字）——短句才對得上動物「嘴型/反應」，笑點才成立（多來源一致）。擬人的度：情緒可以擬人（想睡/不爽/裝沒事），事實不能造假——經典反例：狗的「愧疚臉」其實是安撫行為，寫錯=傳錯知識（NCBI，學術多源）。生態知識當「轉折」不當「補充」：句式「牠不是在打架，是在求偶」，fact 藏在翻案裡就不說教。上色詞：動作動詞與翻案轉折詞（不是/其實/竟然）上色，一句最多 1-2 個色詞。

### 結構
0-1.5s 動作中幀+一行 hook 字（無起手式）→ 1.5-5s 建立「這隻是誰」：命名或一句人設（「這隻叫阿肥，牠有個計畫」）→ 5-20s 行為推進 2-3 個 beat，每 beat 一句 OS/一個小轉折，知識塞在第 2 個 beat 的翻案句 → 最後 2-3s 行為結果=punchline，畫面收在≈首幀構圖做 loop，或結尾一句話讓開頭台詞換了意思（narrative loop，多來源一致）。無臉動物主體感三招：開場命名、全片連續跟拍同一隻、給牠一個目標（搬家/找食/回巢）——個體敘事勝過物種科普（Willow 山獅紀錄片同一邏輯）。

### 剪輯手法
- 「隨性拍+隱形剪」：手持自然光的粗獷畫面，但刀口精準、音訊乾淨、字幕對點——2026 主流審美是看不出剪過（vortexxcel 單源但與 silent vlog 多源趨勢一致）
- 字幕行為對點剪：先看畫面找動物的反應幀（歪頭/定格/轉身），OS 字幕卡在那一格出，不是平均分佈
- 安靜觀察型：不配 BGM 或壓到極低，原生環境音（蟲鳴/水聲/踩葉聲）拉高當主角——無人聲讓觀眾自我投射，也可當背景循環看（多來源一致）
- 互動型：動作同步音效（pop/whoosh 對應撲/跳/瞪），一支 3-5 個就好
- 微距生態：手動對焦+穩定拍攝，黃金時段側光；慢動作給眼睛/口器特寫當「表情鏡頭」，配一句過程實況旁白（「牠掙扎了一下」式的逐刻敘述）
- seamless loop 收尾：剪輯時先定尾幀再回頭選首幀，兩幀構圖/位置接近到重播無感

### CTA
寵物互動型：不喊訂閱，用留言誘餌問句「你家的也會這樣嗎？」。生態觀察型：行動型一句「下次看到牠，別急著打」或系列鉤「明天看牠有沒有搬完」——追蹤動機來自想看同一隻個體的後續，不是想看你。

### 常見死法
- 起手式開場（hello大家好/今天帶大家看）——1.7 秒內就被滑掉
- 擬人過頭變錯誤資訊：把野生動物行為寫成人類劇情、暗示餵食/干預是好事——生態圈公認傷害保育認知，也踩平台不實內容線
- 說教腔收尾「大家要愛護動物喔」——知識要藏在翻案句裡，喊口號=掉讚
- 模板化混剪/搬運：中文圈多來源明言寵物賽道同質化嚴重，套模板已拿不到流量
- BGM 蓋掉動物原聲——原聲（呼嚕/振翅/咀嚼）是這個領域的 ASMR 資產
- 賣慘文案（流浪/受傷賣同情）：抖音/TikTok 確實有整理 30 條爆款套路，短期有效但傷人設且有擺拍合規風險——知道它存在，別用
- 超過 25-30s 又沒做 loop：長度撐不住就直接反映在完播

### 來源（22）
- https://fluxnote.io/guides/tiktok-pets-strategy
- https://vortexxcel.com/tiktok-editing-trends-2026/
- https://postlinkapp.com/blog/hook-examples-for-social-media-videos
- https://topmostads.com/2025/09/11/tiktok-hook-formulas-educational-content-2025/
- https://www.opus.pro/blog/youtube-shorts-hook-formulas
- https://virvid.ai/blog/looping-structure-shorts-retention-2026
- https://nealschaffer.com/youtube-shorts-looping/
- https://www.mariosomedia.com/blog/seamlessloop
- https://skinnedcartree.com/what-are-silent-vlogs.html
- https://gyre.pro/blog/the-rise-of-silent-vlogs-why-faceless-youtube-content-is-booming
- https://screenshot-media.com/culture/influencers/what-is-silent-vlogging/
- https://www.woshipm.com/operate/4649653.html（萌宠出道，戏精的是人）
- https://www.woshipm.com/operate/2237478.html（三站看百个宠物号）
- https://www.aiyingli.com/268067.html（千万播放宠物短视频运营）
- https://www.amz123.com/t/02GuO2hm（TikTok宠物30条卖惨文案——僅作風險認知）
- https://zhuanlan.zhihu.com/p/682299195（AI猫咪视频玩法拆解）
- https://vocus.cc/article/65e9d57ffd89780001ecceed（Daniel 寵物自媒體從業心得）
- https://www.parkcat.com.tw/blog/13338（貓咪短影音課：三分法構圖/行為挖人設）
- https://wildlifeforall.us/through-yellow-eyes-how-storytelling-can-challenge-dominant-narratives-about-wildlife/
- https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8614365/（擬人化與動物福利）
- https://attackofthefanboy.com/social-media/one-tiktok-creator-subjects-his-insect-victims-to-bizarre-experiments-and-preserves-their-bodies-in-a-notebook-mosquito-serial-killer/
- https://tvtropes.org/pmwiki/pmwiki.php/Main/WildlifeCommentarySpoof（Attenborough 旁白格式）

---

## 知識/教學型短影音（含 AI 工具教學、螢幕 demo 類）

### Hook（開場 0-2 秒）
- 結果先行（多源一致最強）：第 1 幀直接秀完成品/after 狀態，口白「這個效果只要 3 步」→ 觀眾想知 how 就留下。做法：先做完成版→複製專案→剪一段快速 before/after 當開場
- 三層疊加 hook：畫面變化＋大字＋一句口語同時上。單源數據稱三層比單層 3 秒留存高 3 倍（miraflow，標註單源），但「疊三元素」本身多源一致
- 反直覺句式：「你一直都用錯了」「不要再 XX」——挑戰既有認知，教學類實證常青（多源）
- TL;DR 式：開頭一句把整支結論講完（「AI 寫文案最快的方法是 X」），再展開步驟——知識類專屬，適合切條片頭補拍
- 數字承諾式：「3 個步驟」「30 秒學會」——首幀大字必須含數字＋結果詞，不含工具名（工具名放第二句）

### 節奏
長度甜蜜點 15-30s（留存常 >80%，Shortimize/OpusClip 數據）；教學類可容忍 +5-10s，35-45s 是知識片上限。刀速：口播每 3-5s 一刀；螢幕錄影靜止畫面最多 10s 必須有視覺變化（zoom/標註/字卡）。結構弧：0-3s hook → 3-5s 承諾（幾步/多久學會）→ 中段每步 5-10s → 結尾 3-5s 收。中段每個步驟切換點放 Re-hook（「第 2 步才是關鍵」）防中段流失。

### 字幕
逐字/短語跳字幕，教學類每塊 3-5 字詞、停 600-900ms；直式字高 64-88px、放中下 1/3。配色：白字為主＋每句挑 1 個關鍵詞上色（黃/紅）——「白底單詞跳色」是 2026 教學類預設款；半透明底條比純描邊更穩。字卡只放關鍵詞：數字、專有名詞、步驟 #1/#2/#3、動作指令，不放整句。多源稱跳字重點色比整句字幕看片時長 +12-25%（aividgenie/OpusClip 研究）。

### 結構
教學短片標準弧（40s 版）：0-2s 秀成品 after＋大字結果句 → 2-5s 承諾「N 步搞定」＋步驟總覽字卡一閃 → 5-32s 步驟區，每步＝步驟字卡(#1)＋螢幕 demo＋一句關鍵口白，步與步之間 Re-hook → 32-38s 成品再現＋一句回收開頭 → 38-40s CTA。切條版另補：長片切條每支只取「一個完整 idea」，選段標準＝有自己的起承合（context+progression+closure），檢驗法「你會不會把這 60 秒傳給朋友」；產量基準 10-20 分鐘長片切 6-12 支、45-60 分鐘切 12-25 支；切出後必補拍/補字新 hook，直接截斷=excerpt 不是 clip。

### 剪輯手法
- 螢幕 demo 標準式「全屏→游標指→zoom in→拉回」：全 UI 給 1-2s 定位，游標指到位，推近做動作，做完拉回再進下一步；點擊後停半拍讓觀眾讀畫面
- 點擊高亮圈＋auto-zoom 綁定：每次 click 加圓圈高亮，zoom 只在動作點用，多了反而干擾（多源提醒省著用）
- 講者/demo 比例：教學 shorts demo 為主體，講者臉只當頭尾 bookends（各 1-2s）或縮成 PIP 小窗浮在螢幕上——查無多源硬性數字比例，此為多源一致的『模式』而非公式
- 步驟字卡系統：#1/#2/#3 常駐角落或步驟切換時全屏一閃，卡上只有動作動詞＋名詞（『貼上 prompt』），讓靜音滑的人也能跟
- Before/After 三明治：開場 after、中段 process、結尾 after 再現——把成品畫面剪兩次用
- 靜止螢幕救命三招輪替：punch-in 跳 zoom、標註框/箭頭、關鍵詞字卡彈出，確保任何 10s 內畫面必有變化

### CTA
結尾 3-5s、一句指令就好（HVA 公式的 A）。知識類最有效三選一：留言關鍵詞換 prompt/模板（互動+私訊自動化）、「收藏起來照著做」（教學類收藏率=強訊號）、「追蹤看下一步」（系列切條專用，句尾接下一支的 hook 形成鉤鏈）。CTA 前先把開頭承諾的結果畫面再閃一次，兌現承諾再要行動。

### 常見死法
- Hook 後才自介/鋪背景——0-3s 流失定生死，教學類最常死在『先講為什麼重要』而不是先秀結果
- 一支塞多個重點：記不住＝不收藏不分享；一支只解一個問題（多源一致鐵則）
- 螢幕錄影長鏡頭不動：靜止 UI 超過 10s 無視覺變化必掉；但反向過度 zoom 也干擾
- 切條=直接截斷長片：沒 context 沒收尾的 excerpt 無法獨立成立，切完必補新 hook 與收束句
- 爛音訊：觀眾容忍畫面糊、不容忍音爛——demo 配音比畫質優先
- 整句字幕無重點色、對白太密無節奏點：觀眾找不到眼睛落點就滑走
- 承諾沒兌現：開頭喊『30 秒學會』結尾沒再秀一次成品，完播率與信任雙殺

### 來源（19）
- https://miraflow.ai/blog/youtube-shorts-best-practices-2026-complete-guide
- https://www.opus.pro/blog/ideal-youtube-shorts-length-format-retention
- https://www.shortimize.com/blog/youtube-shorts-retention-rate
- https://faceless.so/blog/25-hook-formulas-for-short-video-retention
- https://luminaclippers.com/blog/how-to-repurpose-long-form-video-into-clips
- https://www.fame.so/post/ultimate-podcast-clip-guide
- https://pixflow.net/blog/standalone-short-video-clips/
- https://zumie.io/guides/how-to-add-zoom-effects-to-screen-recordings
- https://poko.video/blog/cursor-zoom-effects-explained-make-screen-recordings-clearer-in-2026
- https://www.opus.pro/research/best-caption-strategy-short-form
- https://www.aividgenie.com/blog/caption-styles-that-boost-engagement
- https://blitzcutai.com/blog/best-caption-style-youtube-shorts-2026
- https://recapo.ai/zh-tw/blog/how-to-write-video-hooks/
- https://www.eleanorfilm.academy/blog/short-video-skill
- https://beingmovestrong.com/short-video-tutorial/
- https://lifemanual2024.com/article_00001/
- https://creator.hahow.in/video/video-editing/concept

---

## 通用剪輯技法（跨領域直式短影音 2026）

### Hook（開場 0-2 秒）
- 首幀三層疊 hook：畫面異常+字卡懸念+第一句話同幀上；三層對齊比單層 3 秒留存高 35-45%（OpusClip 數據）
- 決勝在 1 秒不是 3 秒：頂級 Shorts 首秒留住 70-90% 觀眾；首幀畫面本身就要讓人看懂承諾（多來源一致）
- 結果前置法：先亮成品/結局/最誇張一幕，再倒敘過程（中英來源一致：punchline first）
- 痛點開頭法：第一句直接說觀眾的痛，不自介不放 logo——50-60% 流失發生在前 3 秒（多來源）
- 第一刀落在 1.5 秒內定調節奏，讓大腦立刻知道『這片會一直動』（aibrify，單一來源但與多來源刀速一致）

### 節奏
每 1.5-2 秒一個視覺變化（cut/zoom/換字卡/鏡頭移動都算重置注意力）；爆款平均 2-3 秒一刀。每 8-12 秒放一次大 pattern interrupt（變速/靜音/大 zoom），一個案例 48%→71% 平均觀看。特效長度 0.2-0.4 秒，超過像 loading。speed ramp 最佳位置 2-4 秒處（演算法量測 commit 點）。長度：中文圈實測 15-20 秒最穩，英文圈 2026 平均 33 秒——教學型可長、情緒型壓短。

### 字幕
逐字彈出用於娛樂/觀點型；教學型用 3-5 字短句組（每句要停留夠讀完）。白字黑邊為底、關鍵詞單獨上色（黃為主流），位置下中三分之一。靜態字幕已死（多來源同句）；粗黑幾何無襯線最穩。70%+ 觀眾靜音看片，字幕=必備不是選配。動畫只用 pop/fade/逐字，字是主角才用重型 kinetic。

### 結構
0-1s 首幀三層 hook（畫面+字卡+第一句）→ 1-3s 展開承諾或結果前置 → 3s 起主體：每 1.5-2s 一視覺變化、每 8-12s 一 pattern interrupt、riser 從轉折前 1-2 秒開始推 → reveal 幀 = riser 頂點 → 最後 2-3s 二選一：(A) CTA 字卡收尾，或 (B) 尾幀直接無縫接回首幀做 loop（<15s 片優先選 B，rewatch 讓留存破 100% 進推薦層）。多段故事片：每 5-8 秒一張章節字卡硬切推進（vortexxcel，單一來源）。

### 剪輯手法
- Speed ramp：0.5x 撐半秒→瞬跳 2x，卡在節拍或動作頂點；源檔 60fps、Editkin time-remap curve + optical-flow receipt；先鋪音軌讓節拍點顯示在曲線編輯器裡再拉
- Zoom punch：關鍵詞出口瞬間 120-200% 推近臉或重點物，0.2-0.4 秒完成，疊低頻 punch/thud 音效
- Whip pan：兩鏡頭同方向同速甩、刀藏在模糊裡、疊 whoosh；直式片用水平甩（垂直甩造成不適感，多來源）
- Match cut：前後鏡頭主體形狀/位置對齊硬切，專用於 before-after、換裝、換地點
- J-cut 直式用法：下一段聲音提前 0.3-0.5 秒進、畫面後到；旁白連續不斷時換 b-roll 觀眾無感（原理多來源，直式應用為通用推論非 2026 專屬實測）
- 音效三件套：riser 頂點精準對 reveal 那一幀；每個轉場配 whoosh 但輪換 3-5 種防聽覺疲勞；整片最多 1 次『音樂突然全靜 1 拍→單詞重擊』——靜音是最大聲的 interrupt

### CTA
最後 5 秒上 CTA 字卡+口播短句同步（中文來源實測）。但 loop 型片例外：CTA 移到字幕條或置頂留言，片尾不留 outro 直接接回首幀——outro 畫面會殺 loop。CTA 只給一個動作，不要追蹤+留言+分享全都要。

### 常見死法
- 前 3 秒自我介紹/公司 logo/鋪陳 → 完播率直接崩（中英多來源同罪）
- 同一顆 whoosh 全片重複 → 觀眾大腦自動消音，轉場失效
- 特效/轉場拉超過 0.4 秒 → 觀感像 loading 畫面
- 靜音 interrupt 用超過 1 次 → 觀眾以為影片壞掉
- 過度剪輯 chaos：2026 贏面是『隨性拍+隱形剪』——手持自然光的外表、手術級刀口的內裡；炫技轉場堆疊反而掉留存
- loop 斷點明顯（能感覺到 restart）→ rewatch 紅利歸零；尾幀和首幀要同構圖同動作
- 隨機亂剪：刀要落在『意義改變』的點上，不是固定秒數機械切

### 來源（29）
- https://clippie.ai/blog/video-editing-techniques-creators-2026
- https://becreatives.co/tiktok-video-editing/
- https://vortexxcel.com/tiktok-editing-trends-2026/
- https://www.opus.pro/blog/youtube-shorts-hook-formulas
- https://www.opus.pro/blog/ideal-youtube-shorts-length-format-retention
- https://virvid.ai/blog/first-3-seconds-hook-faceless-shorts-2026
- https://virvid.ai/blog/looping-structure-shorts-retention-2026
- https://joyspace.ai/pattern-interrupt-reset-attention-span
- https://joyspace.ai/looping-hack-trick-algorithm-double-views
- https://creatorsfx.in/blog/best-sound-effects-for-reels-and-shorts
- https://myinstantplay.com/blog/transition-sound-effects-and-video-hooks-complete-guide
- https://slidycreator.com/blog/what-is-looping-video/
- https://getreeltok.com/answers/how-to-make-a-tiktok-that-loops
- https://blitzcutai.com/blog/best-caption-style-tiktok
- https://www.opus.pro/blog/best-text-animation-packs-captions-titles
- https://nofilmschool.com/how-to-do-a-whip-pan
- https://www.premiumbeat.com/blog/create-seamless-transitons-whip-pan/
- https://aibrify.com/blog/short-form-video-editing-captions-b-roll-guide
- https://aibrify.com/blog/youtube-shorts-retention-curve-playbook
- https://schedulala.com/blog/youtube-shorts-editing-tips-pro-techniques
- https://www.scooptw.com/marketersgo/493498/
- https://live.rookiesavior.net/article/details/three-minute-video-clip
- https://lifeupdate.com.tw/market-trends/2026-04-27/
- https://www.eleanorfilm.academy/blog/short-video-skill
- https://www.techsmith.com/blog/how-to-edit-videos-l-cuts-and-j-cuts/
- https://hypenest.ai/blogs/tiktok-algorithm-2026-video-hooks-retention
