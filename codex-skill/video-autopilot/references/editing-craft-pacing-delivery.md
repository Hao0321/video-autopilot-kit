# editing-craft-pacing-delivery

> PUBLIC_FIXTURE: [scope](editing-craft-fundamentals.md).

[回主索引](editing-craft-fundamentals.md)

## 導航

- [🎥 B-roll + 視覺覆蓋 Coverage](#-b-roll--視覺覆蓋-coverage)
- [🔀 轉場 Transitions](#-轉場-transitions)
- [🔤 動態圖文 + Typography](#-動態圖文--typography)
- [📖 敘事剪輯 Story Structure](#-敘事剪輯-story-structure)

## 🎥 B-roll + 視覺覆蓋 Coverage

**5-shot method 拍序列（wide → CU動作 → CU臉/主體 → OTS → 創意角度）**  〔expert-consensus｜通用〕
- 做法：對同一個動作/主題，連續拍 5 顆不同景別，每顆 hold 至少 10-15 秒（剪輯時才有料挑）：①Wide=交代『在哪』，鏡頭少移動讓觀眾定位空間 ②CU 動作=拍手/拍工具，交代『在做什麼』 ③CU 臉/主體=交代『誰』 ④Over-the-shoulder（過肩/POV）=把『誰+什麼』合在一顆 ⑤創意角度=低角/高角/反射/穿越前景，跟前 4 顆明顯不同。
- 數值：5 顆 / 每顆拍 10-15 秒（M. Rosenblum 原版至少 3 秒可用，但拍 10-15 秒留剪輯餘裕）；成片 b-roll 量 = 最終片長的 4-6 倍
- 修：整片同一個 wide：強制一個動作至少 3 種景別輪替，wide 只用來開場定位，立刻切近景

**Sequential b-roll（過程鏈）vs Illustrative b-roll（情境圖）分層用**  〔expert-consensus｜通用〕
- 做法：Inside The Edit 的二分法：①Sequential=連續動作鏈，shot-by-shot 推進一個過程（開門→走進去→坐下→打開書；或 開 terminal→打指令→跑出結果→看 log），每顆接下一顆有因果邏輯，建立『進展感』。②Illustrative=單張情境圖（城市天際線、時鐘、桌面空景）只設情緒/背景不推進敘事。
- 數值：示範段=sequential 鏈每步 1 顆；概念段=illustrative 單圖 2-5 秒
- 修：b-roll 跟旁白無關 / 像壁紙：示範段改成有因果的動作鏈，觀眾看得到『進度』而非隨機畫面

**Cut on the word — b-roll 對齊旁白關鍵字的那一幀**  〔expert-consensus｜both〕
- 做法：『Match action to meaning』：旁白講到那個名詞的同一幀切進對應 b-roll，不早不晚。剪輯具體做法：先在波形上標出關鍵字出現的時間點（Editkin v4 structured command 自動字幕可看每個詞的時間軸），把 b-roll clip 的入點對齊到那個字的起始幀。the active creator pipeline 已有 M87 caption-broll matcher，這條是它的理論依據——對齊精度要到幀，不是『大概那段』。
- 數值：切點對齊到關鍵字起始幀（30fps=±1 幀內）；插太早或太晚衝擊就消失
- 修：b-roll 跟旁白無關：每顆 b-roll 必須對應旁白此刻講的那個詞/動作，切點壓在關鍵字第一幀

**Cutaway / insert 遮跳接（hide the jump cut）**  〔expert-consensus ·常識｜both〕
- 數值：cutaway 1-3 秒、跨過剪接點兩側各留 ~0.5 秒；reaction shot 1-2 秒、情境 b-roll 2-5 秒
- 修：talking head 沒 b-roll：每個音訊/畫面剪接點上層壓一顆 1-3 秒 cutaway，跳接全部藏起來

**B-roll 時長分級：不要每 2 秒換一張**  〔data-backed ·常識｜both〕
- 做法：硬性時長表：cutaway/reaction 1-2 秒、情境 b-roll 2-5 秒、sequential 動作鏈每顆 2-4 秒。關鍵反 pattern：每 2 秒就換一張新畫面會讓影片『焦慮』、資訊來不及消化（OpusClip：高表現 Shorts 平均 2-4 秒一刀，但那是 Shorts；長片不能整片這節奏）。
- 數值：cutaway 1-2s / 情境 2-5s / 動作鏈每顆 2-4s；>8 秒無變化=補一刀；Shorts 2-4 秒一刀（長片別照搬）
- 修：整片同一個 wide（停太久無聊）+ 反向的『每 2 秒亂跳』：用時長表把節奏控在 2-5 秒帶，>8 秒補變化

**J-cut / L-cut 把 b-roll 切點藏在音訊底下（split edit）**  〔expert-consensus ·常識｜both〕
- 做法：split edit=音訊和畫面在不同時間點切。①L-cut：畫面先切到 b-roll，旁白音延續到 b-roll 上（音『拖尾』過接縫）。②J-cut：下一段旁白音先進來（audio lead / 音訊先行），畫面晚一點才切（觀眾先聽到才看到）。組合用法做無縫 b-roll 進出：L-cut 切進 b-roll（保留前段音）→ 接近 b-roll 尾巴讓新音進來（J-cut）→ 再切回主畫面。
- 數值：音訊/畫面切點錯開 ~0.3-0.8 秒；J=音先行、L=音拖尾
- 修：talking head 沒 b-roll（切換生硬）：用 J/L-cut 讓音訊跨過畫面切點，b-roll 進出像呼吸不像硬切

**Horizontal × Vertical 雙軸：b-roll 不是鋪壁紙是搭結構**  〔expert-consensus｜通用〕
- 做法：Inside The Edit 框架——每顆 b-roll 同時要對兩條軸負責：①Horizontal（時間軸 shot-flow）=這顆和前後顆有沒有組成『微故事』、有沒有進展。②Vertical（和底下旁白的情緒對位）=旁白此刻的情緒/重點，這張畫面有沒有放大它。
- 數值：每顆 b-roll 過 2 題檢查（此刻情緒？最能表達的畫面？）
- 修：b-roll 跟旁白無關：每顆都要過『情緒對位』那關，不能只是『有畫面填空』

**技術一致性：景別變、色調/解析度/光別亂變**  〔expert-consensus ·常識｜both〕
- 做法：Coverage 要『景別與角度多變』但『技術規格一致』。最 amateur 的 tell 是 b-roll 之間光線/白平衡/解析度/色調對不上（半段大太陽半段昏暗室內，觀眾立刻看出拼接）。做法：①拍時固定白平衡和曝光，不要自動 ②剪輯時所有 clip 套同一組 LUT/調色，stock b-roll 也要拉到同色溫 ③解析度/fps 統一（creator 已有 24→30fps 轉換規則，延伸到色調統一）。
- 數值：全片統一 fps（如 30）+ 同一組調色；stock/自拍/螢幕錄都拉到同色溫
- 修：混雜素材看起來像拼貼：統一白平衡/色調/解析度/fps，只讓景別和角度變化

**段落分配節奏：開頭密、中段鬆（教學長片 coverage 排程）**  〔data-backed｜通用〕
- 做法：把 coverage 密度按片段位置排：分 0-3 分鐘=高能，每 10-20 秒一個視覺變化（換角度/zoom/b-roll/cutaway）穩住鉤子；3-7 分鐘=穩定，刀少一點、多用有上下文的 sequential b-roll；之後每 60-90 秒一個 pattern interrupt（跳接/換角度/快 b-roll/上字卡圖）打斷線性流失。目標：1 分鐘留存 ~70%（強算法推送門檻）。
- 數值：0-3min 每 10-20 秒一變化；3-7min 每 25-40 秒；全程每 60-90 秒一個 pattern interrupt；1 分鐘留存目標 ~70%
- 修：整片同一個 wide / 節奏平：用位置分級排 coverage 密度，開頭 10-20 秒一變、之後 60-90 秒一個 pattern interrupt

**Editkin v4 structured command overlay track 疊 b-roll / freeze frame 操作位置**  〔expert-consensus ·常識｜Editkin v4 structured command〕
- 做法：Editkin v4 structured command：上層 track 蓋下層。①拖 b-roll/螢幕特寫到主軌『上方』的 track=overlay 層；右側面板調 Scale/Position/Rotation（PiP/facecam 縮到右上角；全幅 cutaway 拉滿）。
- 數值：上層蓋下層；建議 5 軌分層；Freeze=playhead→Freeze 鈕→拖邊調長
- 修：talking head 沒 b-roll：用 overlay 軌把 cutaway 疊在主畫面上，不用動主軌就能蓋接縫

**ffmpeg overlay：enable='between(t,a,b)' 在指定秒數疊 cutaway**  〔data-backed｜ffmpeg〕
- 做法：純 ffmpeg pipeline 把 b-roll/截圖在精確秒數疊上主畫面（螢幕錄影），用 overlay filter 的 enable timeline。①定時 cutaway 全幅蓋：`[0:v][1:v]overlay=enable='between(t,12.0,15.0)'`（第 12-15 秒蓋上 b-roll，正好藏一個剪接點）。
- 數值：overlay=enable='between(t,12.0,15.0)'；PiP 右下 overlay=W-w-20:H-h-20，scale=320:240
- 修：b-roll 跟旁白無關 + 沒 b-roll：用 between(t,a,b) 把每顆 b-roll 精確壓在旁白關鍵字的秒數上，純腳本可自動化

**B-roll 量化拍攝門檻：成片 4-6 倍、每顆 10-15 秒**  〔expert-consensus ·常識｜通用〕
- 做法：覆蓋率的源頭在拍攝端：成片 1 分鐘 → 拍 4-6 分鐘 b-roll（4-6 倍 coverage ratio）；每顆 b-roll 至少拍 10-15 秒（剪輯時才有頭尾可修、能做 J/L-cut 重疊）。拍不夠就只能整片重複同一個 wide=業餘 tell 的物理根因。
- 數值：coverage ratio 4-6×成片；每顆 b-roll ≥10-15 秒
- 修：整片同一個 wide：根因是拍太少。拍攝端強制 4-6 倍 coverage、每顆 10-15 秒，沒料剪不出 sequence

_來源：www.videomaker.com / jea.org / www.insidetheedit.com / www.visla.us / www.masterclass.com / captions.ai_

## 🔀 轉場 Transitions

**Hard cut 當主力（90%+ 切點不放任何轉場特效）**  〔expert-consensus ·常識｜Editkin v4 structured command（不放轉場即 hard cut）/ ffmpeg concat（純拼接無 xfade）〕
- 做法：預設每個剪輯點就是直接切（兩 clip 並排，中間不放任何 transition icon）。專業片 99% 時間就是 raw cut，沒有效果。原則：transition 是『例外』不是『常態』——meat and potatoes 是直切，dissolve/fade 只是『調味料』偶爾用。
- 數值：目標比例：≥90% 切點 = hard cut，≤10% 用 motivated transition。教學長片建議 100% hard cut（J/L-cut 除外，那是音訊技巧不是視覺特效）。
- 修：業餘 tell #1：每個切點都套一個轉場（cross-dissolve / 翻頁 / 星形 wipe 濫用）→ 立刻顯廉價、業餘。把 95% 切點還原成 hard cut 是最快讓片子變專業的一招。

**只用 motivated（有理由的）轉場——轉場要『有意義』才放**  〔expert-consensus｜概念規則（Editkin v4 structured command / ffmpeg 皆適用）〕
- 做法：轉場只在『敘事上有意義、幫觀眾理解場景轉換』時才用：①時間/地點大跳（換城市、換日子）②情緒/節奏明顯轉折（從喧鬧→寧靜）③遮掩兩個相似畫面之間的對齊問題 ④merge 兩段捲動/移動。問自己『這個轉場在說什麼？』答不出來就用 hard cut。直式旅遊/美食 Shorts：到了新景點 or 換一道菜，可以用 1 個 motivated transition 當段落分隔；同一場景內的連續鏡頭一律 hard cut。
- 數值：判斷句：『transitions should only be used if they mean something narratively』。把『調味料』思維貫穿全片：一支 5 分鐘片 motivated transition 控制在個位數。
- 修：業餘 tell #2：『亂用』——無理由、純為了炫技而套轉場。每個轉場都該對應一個敘事動機；沒動機=雜訊，讓觀眾分心、降低資訊感知。

**Invisible/seamless 轉場：whip pan（甩鏡）——重機/旅遊 Shorts 最好用**  〔expert-consensus｜Editkin v4 structured command Transitions 面板（運鏡類）/ 實拍甩鏡 + Premiere/AE adjustment layer〕
- 做法：拍攝端：上一鏡頭結尾快速甩鏡（橫向或縱向），下一鏡頭開頭也用『相同速度+相同方向』甩鏡進場；兩段甩鏡的 motion blur 對接，woosh 一聲合成一個無縫切。剪輯端：把第一段裁到 motion blur 開始處，第二段裁到 motion blur 快結束處，微調 in/out 點到順。沒實拍甩鏡時可用 Editkin v4 structured command Transitions 內的『運鏡/Whip』類模擬，但實拍最自然。
- 數值：長度：24fps 設 8 frame（≈0.33s）、60fps 設 20 frame（≈0.33s）。兩段甩鏡速度必須一致，差太多會穿幫。adjustment layer 覆蓋切點、前後各延伸 5 frame 給 motion blur 空間。
- 修：業餘 tell：想要『酷炫切換』就套內建星形/故障/3D 翻轉。改用 whip pan 達到同樣『有動感』但專業——因為它是 motivated（鏡頭真的在動）且 invisible。

**Invisible 轉場：物體遮擋 / match cut（圖形/動作/聲音匹配）**  〔expert-consensus｜Editkin v4 structured command（手動對齊兩 clip 的遮擋/匹配 frame，純 hard cut，不需特效）〕
- 做法：①物體遮擋(whip/pass-by)：用某物體掃過鏡頭（手、人、車、門框）填滿畫面那一兩 frame 當作切點，切到下一鏡頭。②match cut：用兩鏡頭裡形狀/動作/聲音相同的元素接（例：圓形鍋蓋切圓形太陽；倒水動作接倒咖啡動作）。這些都是『隱形』的，觀眾感覺流暢卻不會注意到剪接。美食 Shorts：用『手把菜端進畫面遮住鏡頭』當切點超自然。
- 數值：切點落在物體完全填滿畫面那 1-2 frame，或兩鏡頭動作軌跡/形狀最吻合的那一 frame。本質仍是 hard cut，不套任何 transition 特效。
- 修：業餘 tell：場景切換生硬 or 硬塞特效遮醜。match cut / 物體遮擋讓切換『有設計感』又看不出剪接痕跡，是 pro 的隱形手法。

**J-cut / L-cut（split edit 音訊先行/延後）——讓直切變『隱形』**  〔expert-consensus｜Editkin v4 structured command（音訊軌與視訊軌分別裁切錯開）/ ffmpeg（旁白人聲軌 offset）〕
- 做法：不是視覺特效，是音訊技巧：L-cut=上一鏡頭的『聲音』延續蓋到下一鏡頭畫面上；J-cut=下一鏡頭的『聲音』提前進到上一鏡頭畫面尾。做法：在 timeline 上把音訊軌的邊緣，比視訊軌的切點往後(L)或往前(J)拉幾秒，讓 A/V 不同時切。教學長片旁白：旁白講完上一段、畫面已切到下一個 demo（L-cut），或下一段旁白先進、畫面還停在上一個（J-cut），銜接超順、不會『硬切感』。
- 數值：錯開量通常 0.5-2 秒（依語句節奏）。timeline 上看起來像字母 L（音訊延伸到下個 clip 底下）或 J。完全免特效，只是錯開 A/V 切點。
- 修：業餘 tell #3：A/V 同 frame 一起切 → 感覺生硬、機械、卡。J/L-cut 模擬真實對話（人常先聽到聲音才轉頭看），讓 hard cut 也『感覺流暢』，不需任何花俏轉場就達到專業感。

**轉場長度（frame/秒）硬規則——太長=拖、太多=亂**  〔expert-consensus ·常識｜Editkin v4 structured command（選轉場→右上 Duration 輸入框，最大 5 秒）/ ffmpeg xfade（duration= 參數）〕
- 做法：設定值：①標準轉場(cut/fade)：0.5-1 秒。②複雜轉場(wipe/dissolve)：1-2 秒（依節奏）。③dissolve 電影標準：24-48 frame(≈1-2秒)。④甩鏡/快速 invisible 轉場：6-10 frame(24fps≈0.25-0.4s) 或 60fps 約 20 frame。
- 數值：fade/cut 0.5-1s；dissolve/wipe 1-2s（24-48 frame）；甩鏡 6-10 frame(24fps)/20 frame(60fps)。Editkin v4 structured command 標準轉場最大 5s（別碰上限）。太快=刺眼跳，太慢=失去注意力。
- 修：業餘 tell #4：轉場太長太多——一個翻頁拖 2 秒、每段都 cross-dissolve 1.5 秒，整片黏糊糊像幻燈片。把長度壓進規則內、數量壓到個位數，立刻變俐落。

**黑名單：星形 wipe / 翻頁 / 故障 / 3D / 心形 / cross-dissolve 濫用**  〔expert-consensus ·常識｜Editkin v4 structured command（避免 Transitions 面板的炫特效分類）/ 一鍵移除全部轉場後重評估〕
- 做法：明確不要用：星形 wipe(star wipe)→『dated, campy』顯廉價過時，只有刻意搞笑/復古才用；iris/心形/時鐘 wipe→破壞注意力、像老舊影片；翻頁(page turn)、立方體 3D 旋轉、故障(glitch) 特效當常規切點→純炫技干擾內容；cross-dissolve 每切必用→把『調味料』當『主食』。
- 數值：star wipe 明列為最該避免的『dated/campy』轉場。glitch/特效『overusing distracts from content』。教學長片 demo 切換 = 0 fancy transition。
- 修：業餘 tell #1 核心：『每個切點都套花俏轉場（星形/翻頁/cross-dissolve 濫用）』。這份黑名單直接對應這條——把這些從你的習慣移除，是最直接的『去廉價化』。

**轉場音效（whoosh）對齊——晚切點 1-2 frame，不要同幀**  〔expert-consensus｜Editkin v4 structured command（whoosh 素材放音訊軌，往後挪 1-2 frame）/ ffmpeg（adelay 1-2 frame ≈ 33-66ms@30fps）〕
- 做法：用 motivated transition(甩鏡/物體遮擋)時配 whoosh 音效，但音效不要對在切點『同一 frame』，而是切點後 1-2 frame 落下——因為人耳感知比眼睛快，同幀反而覺得不準。進階：讓音效軌跡跟畫面動向一致（物體從左進場→whoosh pan 左到右；文字橫掃→whoosh 跟著掃），賣『聲音和畫面是連動的』錯覺。Shorts 甩鏡轉場配一聲 whoosh 質感立刻升級。
- 數值：音效落點 = 視覺轉場開始後 1-2 frame（30fps≈33-66ms）。可疊 2 層 whoosh 增厚。音效 pan 方向跟物體進場方向一致。
- 修：業餘 tell：有轉場沒音效（乾巴巴）或音效對在同幀（覺得『差一點』說不上來）。晚 1-2 frame + 軌跡匹配，讓 motivated transition 真正『無縫』有衝擊力。

_來源：www.betterdevscreencasts.com / www.checksub.com / www.descript.com / www.premiumbeat.com / nofilmschool.com / www.studiobinder.com_

## 🔤 動態圖文 + Typography

**Easing 曲線：字的進出絕不用 linear，Editkin v4 structured command 改速度曲線 / ffmpeg 用 sin 而非線性插值**  〔expert-consensus｜both〕
- 做法：業餘的字是「等速」進出（Editkin v4 structured command 兩個 keyframe 預設就是 linear，ffmpeg 用 (t-t0)/dur 也是線性）→ 看起來機械、像 PPT。Pro 做法是『慢進慢出』(slow in/out)：起步慢→中間快→停前慢。
- 數值：Editkin v4 structured command：keyframe 菱形在右側 Position/Scale/Rotation/Opacity 旁；ease in/out 在 keyframe 右鍵；自訂在速度曲線/graph。入場 ease-out、出場 ease-in。ffmpeg pop：fontsize=if(lt(t\,1.3)\,48*0.7+48*0.3*sin(PI/2*(t-1.0)/0.3)\,48)
- 修：業餘 tell #1『easing 線性很機械』+『字硬切無動畫』——等速/瞬切是最一眼看穿的素人特徵

**進場/出場時長鎖 6–12 frame（0.2–0.4s），不要拖 1 秒以上的長動畫**  〔expert-consensus｜both〕
- 做法：業餘字常常動畫拖太久（緩緩飄 1–2 秒）或瞬間出現（0 frame）。Pro 的標準：『入場動畫 6–12 frame（@30fps ≈ 0.2–0.4s）』，出場同等或略短；動畫做完後『字要靜止可讀至少 0.5 秒』再退場。社群影片觀眾 ~1.7s 內就決定滑不滑，所以動畫要快、別讓人等。
- 數值：入/出場 6–12 frame (0.2–0.4s @30fps)；動畫結束後靜止 ≥0.5s。ffmpeg fade 0.3s 進+0.3s 出：alpha=if(lt(t\,1.0)\,0\,if(lt(t\,1.3)\,(t-1.0)/0.3\,if(lt(t\,4.7)\,1\,if(lt(t\,5.0)\,((5.0-t)/0.3)\,0))))
- 修：業餘 tell『字硬切無動畫』(0 frame) 與反向的『動畫拖太久很黏』——兩端都修

**Overshoot/回彈：停下前『過頭一點再回正』取代死硬煞停**  〔expert-consensus｜both〕
- 做法：業餘的字 keyframe 到目標值就停死（abrupt halt）。Pro 加 overshoot（動畫 12 原則的『跟隨/回彈』）：scale 100%→衝到 105–108%→回 100%，或位置滑超過 2–4px 再彈回，模擬真實慣性。【Editkin v4 structured command】打三個 keyframe：起點(70–80%)→過衝點(105–108%)→落點(100%)；過衝點到落點那段用 ease-out。
- 數值：overshoot 幅度 scale 105–108%（≤8–10%），3 個 keyframe（起→過衝→落），最後段 ease-out。ffmpeg bounce：sin 係數 0.3→0.4
- 修：業餘 tell『字硬切無動畫』的進階版——『機械式煞停』，pro 的字有重量感

**換預設字體：丟掉 Arial/系統黑體，中文用幾何感字體、英文用 Montserrat/Poppins/Bebas**  〔expert-consensus ·常識｜both〕
- 做法：業餘最大破綻是直接用編輯器預設 Arial / 微軟正黑。Pro 的動態圖文用『幾何感無襯線 + 有粗細變化』的字體，在動態中清晰：英文 Montserrat / Poppins / Futura / Bebas Neue；中文搭 Noto Sans TC / 思源黑體 / 粉圓（creator Shorts 已用）。
- 數值：英文 Montserrat/Poppins/Futura/Bebas Neue；中文 Noto Sans TC/思源/粉圓；字重 Bold 700+。避 script/Comic Sans/Papyrus/細體裝飾字
- 修：業餘 tell『預設字體(Arial)』——換字體是質感投報率最高、最便宜的一步

**丟掉純黑 drop shadow，改 contrast 描邊 / 半透明底板 / 微陰影**  〔expert-consensus ·常識｜both〕
- 做法：業餘的『純黑硬 drop shadow』是 2000 年代遺物，一看就過時。Pro 保證可讀性的現代做法：①白字 + 2–4px 同心黑描邊（stroke/outline，比投影乾淨）②半透明底板（black box 60–75% 不透明 + 內距 padding，字不貼邊）③真要陰影就用『微擴散柔陰影』(blur 大、offset 小、透明度低) 而非銳利偏移黑影。對比鎖 WCAG ≥4.5:1。
- 數值：白字 + 2–4px 黑描邊（borderw=3:bordercolor=black）或底板 box=1:boxcolor=black@0.6:boxborderw=20；對比 ≥4.5:1。避銳利純黑偏移陰影
- 修：業餘 tell『純黑 drop shadow』——換描邊/底板立刻去掉廉價感，同時對比更穩

**字體階層：標題/內文/強調 用『大小 + 字重 + 字距』三段分明，1.5–2 倍比例**  〔expert-consensus｜both〕
- 做法：業餘所有字一樣大、一樣粗、置中堆一起 → 沒主次、雜亂。Pro 建三層階層：①標題（最大、最粗、最重動畫）②內文/副標（小一截、subtle 進場）③強調/標籤（更小、簡單 fade）。實作比例：標題 ≈ 內文的 1.5–2 倍 px；標題用粗體+收緊字距(tracking 負一點)，內文正常字距；強調色塊只給 1–2 個關鍵字。
- 數值：三層：標題(最大最粗) / 內文(1/1.5–1/2 大小) / 強調(最小 fade)。標題 px ≈ 內文 1.5–2×；標題 tracking 收緊、內文正常；強調色只給 1–2 字
- 修：業餘 tell『字太多太滿』+『無主次』——階層讓眼睛知道先看哪

**Kinetic text 逐字/逐詞 stagger（offset 2–4 frame），不要整段一起 pop**  〔expert-consensus｜both〕
- 做法：業餘把整句當一個 block 同時出現/動。Pro 的 kinetic typography 讓字/詞依序進場，彼此 offset『2–4 frame』(每個字晚 2–4 格)，造成『流動/打字機/波浪』感，視線被牽著走。但關鍵：別每個字都加不同特效（kitchen-sink），統一一種進場、只靠時間差。每個字/詞要『獨立 text element』才能各自控時機（整段動畫軌會一起動）。
- 數值：逐字/逐詞 offset 2–4 frame (≈0.07–0.13s @30fps)；每字獨立 element；統一一種進場特效別混搭；先標關鍵字
- 修：業餘 tell『字硬切無動畫』+『整段一起動很死』——stagger 是 kinetic 感的核心

**Lower third 進出：只用 slide 或 fade（0.3–0.5s），停 3–5s，禁旋轉/彈跳/長動畫**  〔expert-consensus｜both〕
- 數值：slide 或 fade 進出 0.3–0.5s、停 3–5s；禁旋轉/彈跳/長動畫；主資訊一行最大、副一行小。ffmpeg：drawbox 底條 + drawtext x=f(t) 滑入 + enable='between(t,s,e)'

**安全邊距：所有字/圖卡縮在畫面內 5–10%，直式避最下 20%**  〔expert-consensus ·常識｜both〕
- 做法：業餘把字頂到畫面邊緣或壓在 UI（TikTok/Reels 右側按鈕、底部帳號列）上。Pro 守 title-safe：『內縮畫面外圍 10%』放字（重要圖形守 action-safe ~5%）；橫式 1920×1080 → 字保持距邊 ~96–192px。
- 數值：title-safe 內縮外圍 10%、action-safe ~5%；橫式距邊 96–192px；直式避底 20%(320–350px)+右 84–120px，字幕 Y 1200–1550。ffmpeg x=w*0.05 / y=h*0.78
- 修：業餘 tell『置中亂飄』+ 字被裁切/壓 UI——安全邊距讓版面穩定專業

**克制原則：一個元素一種動畫，砍字數，禁同時多特效堆疊**  〔expert-consensus｜both〕
- 做法：業餘把每個字加不同特效、又彈又轉又閃 + 整屏塞滿字。Pro 鐵律：『一個好動畫勝過十個同時的特效』(one well-timed scale beats ten simultaneous effects)。每個元素只挑一種主動畫(進場)；同畫面同時動的元素 ≤2–3；字數砍到每張卡 ≤6–8 字、字幕 ≤2 行。動畫要『被訊息驅動』——快動畫=能量、慢動畫=重量，別為動而動。
- 數值：一元素一動畫；同時動的元素 ≤2–3；每卡 ≤6–8 字、字幕 ≤2 行；動畫由訊息驅動(快=能量/慢=重量)；先畫 4–6 關鍵畫面 storyboard
- 修：業餘 tell『字太多太滿』+『特效 kitchen-sink 亂炸』——克制是 amateur↔pro 最大分水嶺

**進度條 / 計時器：keyframe Position 或 Scale 跑寬度（線性 OK），補時間軸視覺**  〔expert-consensus｜both〕
- 數值：前景條 Scale-X 0→100% 或 Position 左→右，跨整段，線性 OK(進度=真實);倒數=文字每秒換值。放安全區頂/底。ffmpeg drawbox 寬度隨 t

**Icon/箭頭/callout 框：用 Scale-pop(70→100% + overshoot) + ease-out 引導視線，配音效同幀**  〔expert-consensus｜both〕
- 做法：業餘用靜止紅圈/箭頭硬貼。Pro 的 callout 會『彈出』引導視線：icon/箭頭/方框從 Scale 70% + Opacity 0 → 100% + 不透明，6–8 frame ease-out，加一點 overshoot；框框可做『描邊逐漸畫出』。指向重點時箭頭從旁滑入(slide + ease-out)。
- 數值：callout Scale 70%→100% + Opacity 0→100，6–8 frame ease-out + 微 overshoot；箭頭 slide-in；pop 與 SFX(whoosh 400–500ms) 同幀對齊動作峰值
- 修：業餘 tell『靜止圖卡硬貼+無引導』——動態 callout 把觀眾眼睛帶到你要他看的地方

**Title card：標題單詞/短句 staggered reveal + 背景微動 + 留白，避免滿屏置中靜止大字**  〔expert-consensus｜both〕
- 做法：業餘 title card = 一行大字硬切置中、背景死板。Pro title card：①標題拆詞 staggered(每詞 offset 2–4 frame fade/slide-up)②背景加極緩慢 push-in(Scale 100→103% 跨 3–4s, ease) 或微粒子，讓畫面『呼吸』不死③大量留白(negative space)，字別占滿④主標 + 一行小副標建階層。
- 數值：標題拆詞 staggered(offset 2–4 frame)；背景緩 push-in Scale 100→103% 跨 3–4s ease；留白別占滿；主標+小副標；片頭 ≤3s。ffmpeg zoompan 背景緩 zoom
- 修：業餘 tell『置中亂飄/滿屏靜止大字』+『背景死板』——title card 是頻道第一印象

**字距/行距微調：標題收緊 tracking、內文放鬆行距(leading 1.2–1.5)，去掉預設鬆散感**  〔expert-consensus｜both〕
- 做法：業餘用字體預設字距行距，大標看起來鬆垮、長段行距太擠。Pro 手動調 typography 三要素：①Tracking(整體字距)：大標題稍收緊(負值)讓字團結有力，小字反而放鬆一點增可讀②Kerning(字對間距)：大標個別調掉怪空隙(尤其大寫接小寫)③Leading(行距)：多行內文設字高的 1.2–1.5 倍，太擠難讀、太鬆斷裂。中文字幕兩行間距別黏。【Editkin v4 structured command】文字→進階設定有字間距/行間距滑桿。
- 數值：大標 tracking 收緊(負)、小字放鬆；kerning 修大寫接小寫怪空隙；leading 內文 1.2–1.5×字高。Editkin v4 structured command 字間距/行間距滑桿；ffmpeg line_spacing
- 修：業餘 tell『用預設一切』的細節層——字距行距是肉眼說不出但感覺得到的精緻度

_來源：www.youtube.com / helpx.adobe.com / www.braydenblackwell.com / www.ikagency.com / trydemotion.com / www.schoolofmotion.com_

## 📖 敘事剪輯 Story Structure

**Paper Edit / 文字稿先排故事（不先碰時間軸）**  〔expert-consensus｜通用（先於 Editkin v4 structured command/ffmpeg）〕
- 做法：剪片第一步不是拖 clip，而是先把旁白/訪談逐字稿貼進文件，用顏色標出『最強的句子/畫面』，在紙上（或 Notion/txt）排出 開頭→中段→結尾 三段，group by 主題不是 group by 拍攝時間。確定紙上結構後才進 Editkin v4 structured command/ffmpeg。專業紀錄片在 90% 素材拍完、ingest、log 完才動手做 assembly，結構先活在紙上。
- 數值：三段式 paper edit；紀錄片業界在約 90% 素材到位後才開 assembly
- 修：業餘 tell #1：照拍攝/事件時間順序倒素材（『早上出發→中午吃飯→下午到景點』流水帳）。Paper edit 強迫你 by 敘事衝擊排序，不是 by 時鐘排序。

**Audio-first 鋪底（先鋪旁白+音樂+音效，後補畫面）**  〔expert-consensus｜both（Editkin v4 structured command 先鋪語音/音樂軌；ffmpeg 先 concat 旁白軌）〕
- 做法：建時間軸時先把『旁白語音軌 + 對應情緒的音樂 + 幾個音效』全部鋪好，一個 video clip 都還沒拖。這條 audio blueprint 會在你補畫面『之前』就暴露哪段太長、哪個 beat 不成立。creator 已是旁白驅動：把旁白軌當骨架，畫面是後貼的 b-roll，正好吻合。ffmpeg 做法：先 concat 旁白成完整音軌→看波形/字幕稿抓段落，再對齊 b-roll。
- 數值：順序：voiceover → music（對齊腦中能量）→ SFX → 才補 video
- 修：業餘 tell：先把畫面排死再硬塞旁白，導致節奏卡在『畫面有多長』而不是『故事要多長』，整支變平。Audio-first 讓故事節奏先成立。

**Open Loop 開放迴圈 / Cold Open（先給未解張力，再倒回開頭）**  〔data-backed｜both〕
- 做法：把片中『最有張力/最有結果』的 3-8 秒畫面剪到最前面當 cold open，刻意不解釋，然後切回開頭從頭講。教學長片版：開頭就丟一個『2 分鐘後才回答的問題』或『先給結果數字、過程後面才講』。心理機制是 Zeigarnik effect（1920s Bluma Zeigarnik）——未完成的事大腦記得更牢、會癢著要看完。
- 數值：cold open 約 3-8 秒；問題延到 ~2 分鐘才答；每 2-3 分鐘 callback 核心問題一次
- 修：業餘 tell #2：平鋪直敘、第一個畫面就是『大家好今天我們來到…』沒有懸念。Open loop 直接製造『不看完會癢』的拉力，修掉開頭無張力。

**第一分鐘是懸崖：把最強內容放最前 60 秒**  〔data-backed ·常識｜both〕
- 做法：留存曲線在開場第 1 分鐘掉最兇（MrBeast 2024 外洩製作文件原話：要把這 60 秒做成全片『最 engaging』的部分）。所以別把精華埋在中後段——把最猛的畫面/最大反差/最高 stakes 放進前 60 秒（甚至前 30 秒）。
- 數值：前 30 秒每 15-25 秒換視覺；~25-35 秒 pattern interrupt；第 1 分鐘 = 最 engaging 段
- 修：業餘 tell：開頭慢熱鋪陳（自我介紹、天氣、交通），把好東西留到後面『壓軸』。觀眾在精華出現前就走了。

**Stakes（賭注）在開場就講清楚 + 全程加碼**  〔expert-consensus｜both〕
- 做法：開頭 5-10 秒就講白『這支給你什麼 / 不看會錯過什麼（what's at stake）』。別只開頭講一次——故事是『持續升高 stakes』而不是只有一個結尾高潮（MrBeast 機制：continuous stakes-raising，不是 single climax）。
- 數值：stakes 講在前 5-10 秒；Midpoint ~50% 放 false victory/defeat；Bad Guys Close In 50-75% 疊壓力
- 修：業餘 tell #3：沒起承轉合、沒有『為什麼我要在乎』。明確 stakes + 中段轉折（false victory→close in）把平直流程變成有上下起伏的弧線。

**Tension–Release 張力-釋放波形（不是全程同一強度）**  〔expert-consensus｜both〕
- 做法：觀眾是『張力→期待→釋放』一波波被帶著走，不是一條直線。剪輯上用三個可控旋鈕調波形：① shot length（短切=建張力、長鏡=給情緒空間）② shot motion ③ music/SFX。具體節奏弧線：0-3 分緊（多視覺 reset），3-7 分穩（少切、多 contextual b-roll），8 分後混『冷靜講解 + 短爆發（reaction/數據圖）』。
- 數值：0-3min 緊 / 3-7min 穩 / 8min+ 冷靜混爆發；BGM 教學段 60-80 BPM、build 段 100-120 BPM
- 修：業餘 tell：全片同一節奏/同一音量/同一切點密度，像念稿，沒有呼吸與高低。波形化讓觀眾有被帶起伏的感覺。

**Kill Your Darlings：刪掉不推進故事的片段**  〔expert-consensus ·常識｜both〕
- 做法：規則：不是每一格拍到的都該進片，連你花最多力氣拍的也一樣——只要它不推進故事就砍。rough cut 階段要『對留/砍很狠（be ruthless）』。具體判準：每個 clip 問『拿掉它故事會斷嗎？』不會斷就刪。教學長片：刪掉『打招呼、找東西、等載入、口頭禪、重複講同一點』。
- 數值：判準：拿掉此 clip 故事是否斷掉；rough cut 階段最狠刪
- 修：業餘 tell #1 核心：全部素材照順序倒進去捨不得刪。Kill darlings 把『dump』壓成只剩推進故事的鏡頭，密度立刻 pro。

**Cut with intention：beat accent 不是 beat cut（避免機械踩拍）**  〔expert-consensus｜both〕
- 做法：別每個音樂 beat 都硬切一刀——機械踩拍會變得可預測、觀眾注意力流失。改用『beat accent』：讓畫面裡的『動作本身』落在 beat 上（例如門關上、手按下、車啟動的瞬間對拍），而不是只在 beat 上換鏡。
- 數值：beat accent（動作對拍）> beat cut（換鏡對拍）；剪點優先 cut-on-action / 句尾
- 修：業餘 tell：每拍一切的『MV 式無腦踩拍』或反過來『硬切毫無邏輯』。Intention-based cut 讓每一刀都有動作/敘事理由。

**J-cut / L-cut：音訊跨過剪點先進/後出（縫合段落）**  〔expert-consensus｜both（Editkin v4 structured command 分離音訊；ffmpeg amix/atrim overlap）〕
- 做法：J-cut＝下一段的『聲音先進來』、畫面後到（形成 J）；L-cut＝上一段的『聲音延續』、畫面先換（形成 L）。紀錄片標準做法：新場景的環境音/旁白先 0.5-1 秒進來，畫面才切過去，段落就『黏』起來不像兩個人輪流上台。Editkin v4 structured command：點 clip → 右鍵 → 『分離音訊 / Separate audio』→ 把音訊軌頭/尾拖過剪點即可做 J/L。
- 數值：音訊提前/延後約 0.5-1 秒跨過剪點；Editkin v4 structured command 右鍵『分離音訊』後拖音訊軌
- 修：業餘 tell：每段都『畫面+聲音同時硬切』，聽起來一段一段斷裂、像幻燈片。J/L cut 讓對白/段落像真實對話流動。

**Contrast & Surprise：刻意打破自己建立的節奏**  〔expert-consensus｜both〕
- 做法：在穩定節奏中『故意』放一個破格點製造記憶點：一拍靜音（cut to silence）、freeze frame 定格、提早切掉對白（cut someone off mid-sentence）、或 POV/視角突然切換。鐵則：不用多，『一個放對位置的意外就能勾住觀眾』。但 surprise 必須是故事掙來的、不是隨機特效。教學長片用法：講到關鍵數據前『全靜音 0.5 秒 + 定格』再放數據動畫，反差讓重點被記住。
- 數值：整支只需 1-2 個；手法：靜音/定格/提早切白/視角切換；必須 story-earned
- 修：業餘 tell：節奏太均勻＝沒有記憶點，看完什麼都沒留下。一個 earned surprise 製造 spike，整支有了『高光時刻』。

**Selects / String-out：先抽『最強片段』成一條 reel，再雕結構**  〔expert-consensus｜both〕
- 做法：進 assembly 前，先把每天/每主題拍到的『最好的瞬間』抽成一條 selects reel（一條只放精華的時間軸）。把這些精華串成 string-out（按敘事順序的精華骨幹）——它先讓你看清楚『這片最好的素材有哪些』，再決定怎麼排成故事。對 creator 的混雜素材（OBS 螢幕錄 + b-roll + 自錄剪輯畫面）特別有用：先各自抽 selects，避免在 100+ clip 裡盲剪。
- 數值：selects reel = 只放精華的時間軸；string-out = 按敘事序串精華骨幹（再做 assembly）
- 修：業餘 tell #1：在全部原始素材裡照順序硬剪，被爛 take 拖住。先抽 selects 等於先確定『手上的好牌』，故事是用好牌排出來的。

**三段式 Assembly → Rough Cut → Fine Cut（分階段，不一次到位）**  〔expert-consensus｜both〕
- 做法：別想一次剪到完美，分三層降低認知負荷：① Assembly（廚房水槽版/kitchen sink）——所有可用素材按故事序鋪上去，不管精細，先看 big picture『哪段成立、哪段不成立』；② Rough Cut——狠刪、重排、決定『揭露什麼、保留什麼（reveal vs hold）』、放 temp music 測情緒；③ Fine Cut——才做節奏、轉場、白字字幕(M68)、-14 LUFS、色彩。
- 數值：Assembly(全鋪)→Rough(狠刪+決定reveal/hold+temp music)→Fine(節奏/字幕/LUFS/色彩)
- 修：業餘 tell：一邊倒素材一邊加特效調色，陷在細節（mired in minutiae）但整體故事是壞的。分階段強迫『先把故事弄對，才美化』。

**Final Image 呼應 Opening（首尾 callback 收束故事）**  〔expert-consensus｜both〕
- 做法：結尾畫面/旁白刻意呼應或反轉開頭（Save the Cat：Final Image 100% mirror/contrast Opening Image 1%），讓觀眾感到『故事走了一圈、有變化』而不是『片子就這樣斷掉』。教學長片：開頭丟的問題/數字，結尾用同構圖或同句式回收（『一開始我問…現在你看』）。Vlog/Shorts：開頭那個地點/物件，結尾再拍一次帶情緒收。也順手閉合前面開的所有 open loop。
- 數值：Opening Image 在 1%、Final Image 在 100%，刻意 mirror/contrast；結尾閉合所有 open loop
- 修：業餘 tell：影片『沒有結尾就斷掉』或硬接『記得訂閱掰掰』。首尾呼應給故事一個閉環，觀眾有『走完一段』的滿足。

**B-Story / 副線（給教學長片一條人性副線）**  〔expert-consensus｜通用（腳本/旁白層）〕
- 數值：B-story 約在 22% 引入、貫穿全片，承載情感/主題副線（A-story=任務、B-story=人性）
- 修：業餘 tell：教學長片『純功能 dump』——只有步驟 1234，沒有人味、沒有『為什麼我在乎』。B-story 注入情感維度，把規格表變成故事。

_來源：www.docfilmacademy.com / nofilmschool.com / air.io / bettervideocontent.com / www.retentionrabbit.com / siliconvalleytime.com_
