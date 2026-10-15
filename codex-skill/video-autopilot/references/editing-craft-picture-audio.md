> **主責／路由**：症狀不明先回 [craft refs 索引](craft-index.md)；本文只主寫「業餘 tell → pro 修法」的調色、混音、節奏、B-roll、轉場、字體與敘事基本功。

# 剪輯 craft 基本功：業餘 → pro（2026 深挖 + 對抗驗證固化）

> **現行執行契約（2026-08-27）**：本文所有「拖進時間軸／面板／右鍵／關鍵幀」都只描述剪輯意圖，必須編譯成 `hao.video-autopilot.edit-plan/v4` 的 typed structured commands，並附素材 evidence、時間界線與預期效果。唯一可執行順序是 `workflow_contract.py` 的 audit → accepted audit receipt → atomic apply → committed apply receipt → render → delivery QA → human/outcome receipt；不可把 UI 動作或 ffmpeg 指令當成完成證據。

> 「有人嫌剪得爛」→ 多源研究 + adversarial verify 後，逐項「**一眼看出業餘的 tell → pro 怎麼修**」+ 數值。承既有 M68/M86/M87/M99/-14LUFS（不重述，標 ↔）。現行落地一律寫入 Editkin v4 structured command；ffmpeg 只可作 plan 內可稽核的 delivery media primitive。

## ⚡ 業餘→pro 速查表（最該先修，依觀感影響排序）

| 一眼看出剪得爛 (tell) | pro 怎麼修 |
|---|---|
| Flat / 顏色平：套了 LUT 反而更髒、層次扁 | 鎖死 5 步順序：中性化(白平衡+曝光+對比拉中性)→修個別曝光→修問題色→套 Look→最後才 LUT。correction 一定在 grading 之前。ffmpeg filter chain：colortemperature,eq,colorbalance 在前，lut3d 在後 |
| 過飽和、顏色俗豔（天空跟膚色都過火） | 飽和上限 100-120%、初版再退 10%；用 Vibrance(智慧飽和、保護已飽和區)取代全域 Saturation。ffmpeg vibrance=intensity=0.2 取代 eq=saturation=1.5 |
| Clip 間色調不一致、一刀切到下個鏡頭顏色就跳 | 用一張 hero clip 建主校正→存 preset/調整層蓋全片→逐 clip 微調。ffmpeg 把同一條 chain 或同顆 .cube 在 concat 前套到每個 segment。自動 color match 只到 60-80%，剩下手動補 |
| 整片偏黃/偏藍、白的東西不白 | 白平衡滴管點畫面中應為中性灰/白的區域(別點已 clip 的高光)；沒滴管就先 Temperature 後 Tint。日光中性約 6500K、鎢絲 3200K、螢光 4000-4500K |
| 套 LUT 一秒變過飽和、對比死硬 | 風格 LUT 強度拉到 50-70%(非轉換 LUT)；ffmpeg 無原生 intensity，用 split+blend all_opacity=0.6 混流模擬；套完 LUT 回頭重平衡曝光 |
| 陰影死黑糊成一片、亮部爆白沒細節 | 黑點留 4-6 IRE(別壓到 0)、白點到 100 IRE；eq contrast ≤~1.2；配 Waveform/RGB Parade 確認而非肉眼 |
| 素材奶灰平淡(忘了還原 log) | Log 素材(S-Log3/C-Log3/D-Log/V-Log)先套對應機型的 Log→Rec.709 轉換 LUT，且排在所有調整最底層；要 input gamut+gamma 對應正確。ffmpeg lut3d 放 chain 最前 |
| b-roll 跟旁白無關 / 像壁紙隨機鋪 | Cut on the word：旁白講到那名詞/動作的同一幀切進對應 b-roll(±1 幀內)；示範段用 sequential 因果動作鏈、概念段才用 illustrative 單圖。對應 creator 既有 M87 matcher 的理論依據 |
| 整片同一個 wide(停太久無聊) 或反向每 2 秒亂跳(焦慮) | 時長分級表：cutaway/reaction 1-2 秒、情境 b-roll 2-5 秒、動作鏈每顆 2-4 秒；任何畫面 >8 秒沒變化補一刀、連續多顆 <2 秒太碎要拉長。Shorts 2-4 秒一刀但長片別照搬 |
| 膚色橘到發假 / 套冷調後膚色發青 | 膚色落 vectorscope ~11 點鐘 I-line、左右均分；飽和控 20-50%；套完冷暖風格後 HSL 二級把膚色拉回自然。vibrance 開膚色保護 |
| 邊緣有白光暈(halo)、畫面過硬發脆、噪點被放大 | 相機端關銳化；後製只銳 luminance、半徑小、amount 低。Editkin v4 structured command 銳化滑桿 ≤20-30；ffmpeg unsharp=5:5:0.4:5:5:0.0(別動 chroma) |
| 畫面平、層次扁、主體不從背景跳出 | Teal & Orange 微量收尾：陰影推青藍 + 高光/中間調推橙(膚色本在橙帶，陰影推青讓主體跳)。當收尾微量別無腦全套；純螢幕教學片要更克制(會讓 UI 截圖發色偏) |
| 全靠肉眼調色、換螢幕/環境光就走鐘 | 配示波器：RGB Parade 看中性畫面三通道對齊、Waveform 看黑白點、Vectorscope 看膚色 I-line 與飽和不爆框。ffmpeg 無即時 scope，剪完抽 contact sheet 逐格目視一致性 |
| 人聲軌只有 dynaudnorm、沒有真正 acompressor → 旁白忽大忽小（湊近麥那句爆、轉頭那句聽不到）治不到根。實際驗證 build_audio.py 第44行 voice chain = `highpass=f=80,dynaudnorm=f=200:g=7`，acompressor 只掛在 build_final.py 的 BGM 軌（[1:a]）不是人聲。 | 在人聲軌（build_audio.py 或 master_voice 後製）串一刀 `acompressor=threshold=-16dB:ratio=3:attack=10:release=120:makeup=4`，放在 highpass 之後、dynaudnorm 之前（或直接取代 dynaudnorm）。dynaudnorm=拉平整體響度、acompressor=抓 transient 壓動態，旁白要的是後者。這是『忽大忽小』ROI 最高的單一修正。 |
| 收尾 loudnorm 是 single-pass（build_final.py 第107行 `[mx]loudnorm=I=-14:TP=-1.5:LRA=11`，無 measured_* / 無 linear=true）→ single-pass loudnorm 本身是動態壓縮器，會製造 pumping（整片忽大忽小抽動），等於一邊修動態一邊又加回新的動態。 | 改 two-pass：pass1 跑 `loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json` 抓 measured_I/TP/LRA/thresh，餵 pass2 `...:measured_I=..:measured_TP=..:measured_LRA=..:measured_thresh=..:linear=true`。linear=true 是整檔一個固定增益，動態保留不 pumping。 |
| BGM 沒有真 ducking／sidechain — build_final.py 只用 `volume=0.12`（固定 -18.4dB）+ acompressor，人聲講話時 BGM 不會自動再壓低。安靜段（beat 之間 0.35s gap）BGM 也不會回升。Memory 寫『ducking 數值表已對』與實際 code 矛盾——script 裡根本沒有 ducking。 | 上 sidechain：`[music][voice]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400:makeup=1[ducked]`，人聲一進 BGM 自動壓到 ~15-25%、停了回升。比固定 volume 精準，且靜默段音樂自然浮回填空。 |
| 去聲剪輯（when the active workflow removes speech errors）的剪接點是硬 concat（build_audio.py 用 `-c copy` concat voice+gap），沒有 room tone 補縫、也沒有 micro-crossfade → 每個被剪掉的吸氣/口誤缺口會變絕對死寂，跟前後有底噪的段落硬接會聽到『空氣消失』+ 零交越點『啪』click。 | (a) 缺口墊 -35dB room tone（錄旁白多錄 10s 環境音鋪底層）；(b) concat 改用 `acrossfade=d=0.03`（30ms）取代 `-c copy` 消 click。注意 gap.wav 現在是 `anullsrc`（純數位靜音）——這正是死寂來源，可改成極低 room tone。 |

> **PUBLIC_FIXTURE:** audio-chain defaults are configurable starters. Public docs do not
> include a private implementation folder, project loudness result, speed result or dated validation.
> Calibrate room tone, crossfade, loudness, ducking and speed from creator-owned media.

## 🎨 調色 Color

**先校色再調色 — 鎖死 5 步順序，別跳步**  〔expert-consensus｜both〕
- 做法：Pro 的鐵則順序（noamkroll / Filmsupply 一致）：①Normalize 中性化＋對 hero shot 配色（白平衡+曝光+對比拉中性）②修個別曝光（爆掉的窗、死黑）③修問題色（過飽和紅、螢光燈綠膚色）④套 Look/風格 ⑤最後才 LUT + 全片微調。
- 數值：5 步固定順序：中性化→曝光→色彩→Look→LUT；ffmpeg filter chain 順序＝校正在前、LUT 在後
- 修：「顏色平、套了濾鏡反而更髒」——自學者最常見錯誤就是把 correction 和 grading 順序搞反或省略 correction

**Clip 一致性 — 用一張 master/調整層套全片，不要逐 clip 各調各的**  〔expert-consensus｜both〕
- 做法：Editkin v4 structured command：在時間軸頂層加「調整圖層(Adjustment Layer)」蓋住所有 clip，色彩/LUT/對比只調一層→全片統一；或在色輪/HSL 面板存自訂 preset 後用「Apply to All Clips」一次套用，再逐 clip 微調。ffmpeg：把同一條校色 filter chain（或同一顆 .cube）套到所有片段，concat 前統一處理，而非每顆片各跑不同參數。
- 數值：調整層覆蓋全片 1 層；自動 color match 只到 60–80%，必須手動補完
- 修：「每顆 clip 色調不一致、一刀切到下一鏡頭顏色就跳」——inconsistent grades across cuts 是 amateur 三大 tell 之一

**白平衡修正 — 滴管點中性灰，先 Temp 後 Tint**  〔expert-consensus ·常識｜both〕
- 做法：標準手法：①先用白平衡滴管點畫面中『應該是中性灰/白』的區域（灰卡、白牆、白紙），軟體自動把該點拉中性、整張跟著校正。注意：不要點過曝的高光/燈泡（已 clip，怎麼調都沒用），要點未 clip 的淺灰。②若沒滴管：先動 Temperature（藍↔橙，平衡紅/藍通道）再動 Tint（綠↔洋紅）。
- 數值：色溫先、色調後；鎢絲 3200K / 螢光 4000–4500K / 日光中性 ~6500K；滴管別點已 clip 的高光
- 修：「整片偏黃/偏藍、白的東西不白」——白平衡沒校就是業餘最直接的一眼 tell

**綠色調 (螢光燈/Sony 機身) 修正 — Tint 往洋紅推一點點**  〔expert-consensus｜both〕
- 做法：螢光燈下或部分 Sony 機身畫面常帶綠。修法：Temp 稍微加暖 + Tint 往 magenta(洋紅)『小幅』推，邊推邊盯白色物和膚色。頑固的綠用 HSL 二級：在 HSL 面板選綠/黃綠色相，降它的飽和或位移色相。Editkin v4 structured command：調整→HSL→點綠色通道降飽和；ffmpeg：colorbalance=gm=-0.1（midtones 綠-洋紅軸往洋紅）或 hue 微調。
- 數值：Tint 往洋紅小幅推；colorbalance gm 軸 ~-0.05 到 -0.15；非 RAW 修正空間小→小步調
- 修：「室內畫面整片帶綠、膚色發青」——螢光燈綠 cast 是室內 vlog 常見業餘 tell

**Log/raw 還原 — 轉換 LUT 必須最先套，且要對的 input→output**  〔expert-consensus｜both〕
- 做法：Log 素材（S-Log3 / C-Log3 / D-Log / V-Log / F-Log…）是低對比『奶灰』的，要先套『該機型對應的 Log→Rec.709 轉換 LUT』把它還原，再做任何校色/風格。轉換 LUT 一定排在所有調整『最前面』。要選對 input gamut+gamma：例如 Canon Log2 CinemaGamut→BT709 要用對應那顆 .cube，套錯機型的轉換 LUT 顏色會歪。
- 數值：轉換 LUT = filter chain / 圖層最底；必須 input(機型 log+gamut)↔output(Rec.709) 對應正確
- 修：「素材奶灰平淡、上傳前忘了還原 log」——把 flat log 直接上傳是最大的『顏色平』元凶

**LUT 強度別開 100% — 套 50–70%，套完重平衡曝光**  〔expert-consensus｜both〕
- 做法：風格 LUT（非轉換 LUT）幾乎都是給 100% 預覽看的，全強度套會過頭（過飽和、對比過硬）。Pro 把強度拉到 50–70%。Editkin v4 structured command：載入 LUT 後直接拉『強度 intensity』滑桿到 50–70。
- 數值：LUT 強度 50–70%；ffmpeg blend all_opacity=0.5–0.7 模擬強度；套完重平衡曝光
- 修：「套了 LUT 一秒變過飽和、對比死硬」——LUT 開滿 100% 是最普遍的 amateur 過頭

**膚色保護 — vectorscope 11 點鐘 skin line，飽和 20–50%**  〔expert-consensus｜both〕
- 做法：膚色（不分人種）都應落在 vectorscope 紅(R)與黃(Yl)之間約 11 點鐘方向的『膚色線(I-line / skin tone line)』上，左右均分。檢查時用 power window / HSL qualifier 圈出臉再看 scope。膚色飽和度控在 20–50%（過了就假橙）。Pro 在套完冷暖風格後一定回頭把膚色 HSL 二級拉回自然（很多 LUT 會把膚色推成橙或洋紅）。
- 數值：膚色落 vectorscope ~11 點鐘 I-line、左右均分；膚色飽和 20–50%；vibrance 開膚色保護
- 修：「人臉橘到發假 / 套冷調後膚色發青」——unnatural skin tone 是觀眾最不能忍、一眼判業餘的 tell

**冷暖對比 (Teal & Orange) — 暖膚色 / 冷陰影分離調色**  〔expert-consensus ·常識｜both〕
- 做法：橙與青在色輪正對面（互補色），且是所有互補對裡曝光對比最高的一對，所以最『電影感』。原理：膚色本來就在橙色帶，把陰影推青/藍→膚色自然跳出背景。做法＝split toning：陰影加一點藍/青、中間調到高光加一點橙。
- 數值：陰影推青藍 + 高光/中間調推橙；橙青是最高曝光對比互補對；當微量收尾不要無腦全套
- 修：「畫面平、層次扁、主體不跳」——少了冷暖分離，畫面缺前後景分離與電影感

**避免過飽和 — 飽和退 10%，用 Vibrance 不用 Saturation**  〔data-backed ·常識｜both〕
- 做法：新手把飽和開到 150% 想要『電影感』反而最業餘；Pro 飽和上限約 100–120%，並把初版再退 10%。優先用 Vibrance（智慧飽和，只拉低飽和區、保護已飽和的膚色）而非全域 Saturation。Editkin v4 structured command：用 HSL 單通道加飽和（只加需要的色）而非整體飽和；ffmpeg：vibrance=intensity=0.2（溫和）取代 eq=saturation=1.5。
- 數值：飽和上限 100–120%、初版再退 10%；vibrance≈0.2 取代 saturation=1.5；社群平台上傳吃 15–20% 飽和
- 修：「過飽和、顏色俗豔、天空跟膚色都過火」——over-saturation 是 amateur 最典型三大 tell 之首

**避免過銳化 — 別在相機開銳化，後製只銳 luminance、小半徑**  〔expert-consensus｜both〕
- 做法：相機/手機預設會自動銳化，高反差邊緣會冒白/黑光暈(halo)＝一眼業餘（尤其大螢幕看手機素材）。原則：相機端關銳化（源頭壞了難救），需要再到後製加。後製要：①只銳亮度(luminance)通道別碰色彩 ②半徑(radius)調小→光暈更細 ③amount 調低→光暈更淡。
- 數值：只銳 luminance、半徑小、amount 低；Editkin v4 structured command 銳化滑桿 ≤20–30；ffmpeg unsharp luma_amount≈0.5 別動 chroma
- 修：「邊緣有白光暈、畫面過硬發脆、噪點被放大」——over-sharpening halo 是手機素材常見業餘 tell

**別壓死黑、別爆白 — 黑點留 4–6 IRE、白點 100 IRE**  〔expert-consensus｜both〕
- 做法：Pro 不把黑壓到 0（會丟陰影細節變『死灰/糊』），黑點留 4–6 IRE、白點到 100 IRE。Editkin v4 structured command：用曲線把最暗點稍微抬離底、最亮點貼近頂但不爆；或對比別拉太猛。ffmpeg：curves 微抬黑點（如 0/0.02 起點）、eq=contrast 別超過 ~1.2。
- 數值：黑點 4–6 IRE（別到 0）、白點 100 IRE；eq contrast ≤~1.2；配 Waveform/Parade 確認
- 修：「陰影死黑糊成一片、亮部爆白沒細節」——crushed blacks / blown highlights 是 amateur 三大 tell 之一

**用 Scope 不靠眼睛 — RGB Parade 對中性 + Vectorscope 看膚色**  〔expert-consensus｜both〕
- 做法：Pro 配色靠示波器：①RGB Parade——中性畫面三通道(R/G/B)底部(陰影)和頂部(高光)應對齊，某通道偏高就是有色偏（如 Canon 陰影偏冷→下方藍綠高→lift 加暖修）。②Vectorscope——看整體飽和有沒有爆框、膚色有沒有落 I-line。
- 數值：RGB Parade 對中性、Waveform 看黑白點、Vectorscope 看膚色 I-line + 飽和不爆框
- 修：「全靠肉眼調，換螢幕/環境光就走鐘、clip 間不一致」——ignoring scopes 是反覆出現的 amateur tell

**收尾微調 — Vignette -15~-25、Film grain 3–5%（放調整層）**  〔anecdotal｜both〕
- 做法：最後全片收尾（放在調整層/最後一顆 filter）：暗角 vignette 角落 -15 到 -25（把視線收向中央、別太黑成框）；film grain 3–5%（破除數位塑膠感、掩飾壓縮 banding，別多到變雜訊）。Editkin v4 structured command：加調整層套暗角特效+顆粒滑桿小量；ffmpeg：vignette=PI/5 配 noise=alls=8:allf=t+u（顆粒）放 chain 最後。
- 數值：Vignette 角落 -15~-25；film grain 3–5%；都放最後/調整層、小量
- 修：「畫面太乾淨塑膠感、數位 banding、視線散」——缺收尾質感層，少了成片的整合感

**ffmpeg 純命令列調色 — 一條 chain 校正→LUT→收尾**  〔expert-consensus｜ffmpeg〕
- 做法：純 ffmpeg pipeline 範例（順序＝校正在前、LUT 中、收尾後）：ffmpeg -i in.mp4 -vf "colortemperature=temperature=6500,eq=contrast=1.08:saturation=1.0:gamma=1.0,colorbalance=bs=-0.06:bh=0.06,lut3d=file=look.cube,vibrance=intensity=。
- 數值：crf 18 / preset slow / yuv420p；eq contrast 1.05–1.2；vibrance 0.15–0.2；blend all_opacity=LUT強度
- 修：「沒有 GUI 也要一致可重現的調色」——把調色寫成腳本套全片，根治 clip 間不一致

**HaldCLUT 法 — 在 Photoshop/GIMP 調好一張圖再變成全片 LUT**  〔expert-consensus｜ffmpeg〕
- 做法：不想猜 ffmpeg 數值時的 Pro hack：①產生中性 hald 圖貼到某幀畫面上→②在 Photoshop/GIMP 對這張圖做色溫/曲線/對比/色調（用熟悉的 GUI 慢慢調到滿意）→③把調好的 hald 圖當 LUT 套全片：ffmpeg -i in.mp4 -i haldclut_edited.png -filter_complex haldclut -pix_fmt yuv420p -c:v li。
- 數值：haldclutsrc=8 產生 LUT 圖；GUI 調色後 haldclut filter 套全片；crf 18 / yuv420p
- 修：「ffmpeg 數值難猜、又想全片一致」——用視覺化方式調一次套全片，根治 clip 不一致＋顏色平

_來源：noamkroll.com / www.filmsupply.com / ultra4kfilms.com / cinapex.pro / www.markstudios.com / www.tella.com_

## 🔊 音訊混音 + Sound Design（最大業餘 tell）

**4 層音軌分層 + 固定 dB 階梯（人聲 / 環境音 / SFX / 音樂）**  〔expert-consensus｜Editkin v4 structured command(每軌 Volume) / ffmpeg(volume + amix)〕
- 做法：把混音想成 4 層、每層一個固定音量帶，不要全部丟在 -100% 同一條：①人聲/旁白 = 主角，混到 -6 ~ -12 dB（網路交付靠近 -6）②關鍵 SFX(轉場/點擊/whoosh) = -12 ~ -18 dB，永遠比人聲低 ③環境音 ambience(街聲/風/咖啡廳底噪) = -18 ~ -24 dB ④音樂 BGM = -18 ~ -25 dB。鐵則：人聲永遠最大聲、其它層全部讓路。
- 數值：dialogue -6~-12dB / SFX -12~-18dB / ambience -18~-24dB / music -18~-25dB；交付整體仍收斂到 -14 LUFS
- 修：修掉『所有聲音一樣大、聽起來很亂很吵、人聲不突出』+『無環境音很乾』兩個 tell — 全軌同階 = 業餘最大破綻；分層後人聲自然浮出、片子有空間感

**人聲高通濾波 highpass 80–100Hz 去低頻轟隆**  〔expert-consensus ·常識｜ffmpeg highpass=f=80 / Editkin v4 structured command Enhance Voice〕
- 做法：人聲第一步永遠先砍 80Hz 以下：男聲基頻約 85–180Hz、女聲 165–255Hz，80Hz 以下幾乎只有冷氣/桌面震動/口爆/隆隆聲。ffmpeg：`highpass=f=80`（要更陡用 `highpass=f=85:p=2` 約 24dB/oct）。
- 數值：高通 80–100Hz，斜率 12dB/oct(p=1) 或 24dB/oct(p=2)；男聲可到 80、女聲可到 100
- 修：修掉『安靜處有低頻底噪/嗡嗡、人聲悶糊濁』— 低頻泥巴是悶糊的最大來源，砍掉立刻變透

**人聲 presence 提清晰 3–5kHz + 去悶 200–400Hz**  〔expert-consensus｜ffmpeg equalizer / Editkin v4 structured command EQ〕
- 做法：兩刀對症：①悶糊『像隔著棉被講話』→ 在 200–400Hz 輕砍 -2~-4dB（這段是 boxy/箱音）②不清楚『字咬不出來』→ 在 3–5kHz 提 +3~+6dB（presence/咬字帶）。ffmpeg 用 equalizer：`equalizer=f=300:t=q:w=1.5:g=-3, equalizer=f=4000:t=q:w=2:g=4`。
- 數值：悶: 200–400Hz 砍 -2~-4dB(Q≈1.5)；糊: 3–5kHz 提 +3~+6dB(Q≈2)。先砍再提，提別超 +6
- 修：修掉『人聲悶/糊、聽不清楚在講什麼』— 這是隔棉被感的直接解，presence 一上字就跳出來

**De-ess 去齒音 6–8kHz（窄帶壓縮）**  〔expert-consensus｜ffmpeg deesser / equalizer 6-8kHz / Editkin v4 structured command EQ〕
- 做法：『ㄙ、ㄔ、ㄕ』刺耳的嘶聲集中在 5–8kHz。ffmpeg 沒有專用 de-esser，用 sidechain 不好做，最穩是窄帶動態：先 `equalizer=f=7000:t=q:w=3:g=-4` 固定砍（簡單版），講究一點用 deesser 濾鏡（新版 ffmpeg 有 `deesser=i=0.4:m=0.5:f=0.5`，i=強度 f=頻段）。
- 數值：齒音帶 5–8kHz，窄 Q(w=3) 砍 -3~-5dB；ffmpeg deesser=i=0.3~0.5
- 修：修掉『s/ㄕ 音尖銳刺耳、戴耳機聽會痛』— 業餘提了 presence 後常順帶把齒音也放大，de-ess 把刺收回來

**人聲壓縮 acompressor 2:1~4:1 把忽大忽小壓平**  〔expert-consensus｜ffmpeg acompressor / Editkin v4 structured command Normalize loudness(近似)〕
- 做法：壓縮是『忽大忽小』的根本解，不是事後拉音量。ffmpeg：`acompressor=threshold=-18dB:ratio=3:attack=10:release=120:makeup=4`。
- 數值：ratio 2:1~4:1(旁白 3:1)、threshold -18~-12dB、attack 5–15ms、release 80–150ms、makeup +3~+5dB
- 修：修掉『音量忽大忽小、湊近麥克風那句爆掉、轉頭那句又聽不到』— 業餘最大 tell 之一，pro 靠壓縮不靠手動 keyframe 每句調

**BGM ducking 自動閃避 sidechaincompress（人聲一講就壓 BGM）**  〔expert-consensus｜ffmpeg sidechaincompress / Editkin v4 structured command 手動 keyframe〕
- 做法：讓 BGM 自動偵測人聲、人聲一出就壓下去、停了再回來，比手動 keyframe 每句調精準十倍。ffmpeg：把人聲當 sidechain：`[music][voice]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400:makeup=1[ducked]`。
- 數值：threshold 0.02–0.03、ratio 6:1~10:1(旁白 8:1)、attack 20–50ms、release 300–500ms；Editkin v4 structured command 手動壓到 15–25%
- 修：修掉『BGM 蓋過人聲、講話時音樂還很大聲聽不清』— pro 流程 BGM 永遠在人聲下方自動讓路，靜默段才放回音樂

**Noise gate 降噪閘 + 降噪『從低往上調』別過頭**  〔expert-consensus｜ffmpeg agate / afftdn / Editkin v4 structured command 降噪 + Enhance Voice〕
- 做法：句子之間的靜默段如果有底噪嘶嘶，用 noise gate 在沒講話時靜音。設定：threshold 設在『噪聲地板之上、最小聲呼吸之下』，旁白實務 -42~-45dB（軟閘）較自然，-30dB 太緊會切掉句尾；attack 1–3ms、hold 25ms（防 gate 抖動 chattering）、release 100ms。
- 數值：gate threshold -42~-45dB(軟)、attack 1–3ms、hold 25ms、release 100ms；降噪 afftdn=nr=10 起、寧弱勿強
- 修：修掉『安靜處有持續嘶嘶底噪、句子空檔聽得到環境雜訊』— 但注意 gate 用力過頭=句尾被吃、降噪過頭=水下感，兩個都是新的業餘 tell

**Room tone 補接縫（剪掉停頓後填底噪，不要真空靜默）**  〔expert-consensus｜Editkin v4 structured command(墊安靜段) / ffmpeg(底層 room tone -35dB)〕
- 做法：剪掉吸氣/口誤/廢話後，那個缺口會變成『絕對死寂』，跟前後有底噪的段落一接，耳朵立刻聽到『啪』一下的空氣消失感。解法：錄旁白時最後多錄 10 秒純環境音(room tone)，剪接後在每個被剪出的缺口墊一小段 room tone，讓底噪連續。ffmpeg：把 room tone 當一條極小聲(-30~-40dB)的底層全程鋪在人聲軌下方填縫。Editkin v4 structured command：複製一段安靜段、放到缺口、音量壓很低。
- 數值：錄旁白多錄 10s room tone；填缺口音量約 -30~-40dB；只補缺口不蓋好段
- 修：修掉『剪接點突然死寂、一段有底噪一段全黑安靜的落差感』— 這是去聲剪輯(when the active workflow removes speech errors)最容易留下的 tell，pro 用 room tone 把接縫抹平

**剪接點 crossfade 0.5–2 frame 消除『啪』聲**  〔expert-consensus｜ffmpeg acrossfade=d=0.03 / Editkin v4 structured command 接縫短 fade〕
- 做法：兩段人聲硬切時波形不在零交越點(zero-crossing)會產生 click/pop『啪』。解法：每個音訊剪接點加極短交叉淡化 0.5–2 frame（約 15–60ms），不是聽得出來的淡入淡出、只是把 click 抹掉。Editkin v4 structured command：兩 clip 接縫拖一個極短 fade，或在接縫各拉 1–2 frame fade。ffmpeg concat 時用 `acrossfade=d=0.03`（30ms）。
- 數值：人聲接縫 crossfade 15–60ms(0.5–2 frame)；BGM 頭尾 fade 0.5–2s
- 修：修掉『剪接點啪一聲、人聲段與段之間有爆音 click』— 純 ffmpeg/Editkin v4 structured command 硬 concat 最常見的 tell

**轉場音效 whoosh/SFX 與畫面動作同幀**  〔expert-consensus｜Editkin v4 structured command 音效庫 + 獨立軌對齊 / ffmpeg adelay〕
- 做法：轉場(切換/punch-in/字卡彈出)配一個 whoosh/click，但音效峰值必須跟畫面動作峰值『同一幀』— 早一幀或晚一幀都破壞流暢。做法：whoosh 長度配轉場長(半秒轉場 → ~400–500ms whoosh)，在時間軸以 1 frame 為單位微調對齊。SFX 混在 -12~-18dB(比人聲低)。Editkin v4 structured command：把 SFX 放獨立軌、放大波形、playhead 對到視覺動作最劇烈那幀貼齊。
- 數值：whoosh ~400–500ms(配轉場長)、混 -12~-18dB、峰值與動作同幀(1-frame 精度)
- 修：修掉『轉場很乾沒聲音、或音效跟畫面對不上感覺廉價』— 加了對位的 SFX 是業餘↔半專業最快的視聽質感跳級

**環境音 ambience 鋪底打破『乾』**  〔expert-consensus｜Editkin v4 structured command 最底軌 / ffmpeg amix volume -20dB〕
- 做法：純旁白+BGM 沒有空間感=乾。在 b-roll/實景段鋪一層對應的環境音底床：街拍鋪街聲、咖啡廳鋪人聲嗡嗡、戶外鋪風/鳥。混在 -18~-24dB(最底層、聽得到但不搶)。教學螢幕錄影段可不鋪(或極輕鍵盤聲)。Editkin v4 structured command：環境音放最底軌、音量壓低、頭尾 fade。ffmpeg amix 時該軌 volume 設 -20dB 左右。重點：ambience 要『連續鋪一整段』不是點綴，它的作用是底床不是 SFX。
- 數值：ambience 混 -18~-24dB、連續鋪整段、頭尾 fade；對應場景選音(街/咖啡廳/風)
- 修：修掉『畫面有實景但聲音很乾很假、像配音貼上去的』— 無環境音是 vlog/旅遊/重機題材最大的 tell，鋪一層底床立刻有臨場感

**兩段式 loudnorm 收尾 -14 LUFS / -1 dBTP（避免 pumping）**  〔data-backed ·常識｜ffmpeg loudnorm two-pass(linear=true)〕
- 做法：全部混完最後一步才做響度標準化。
- 數值：I=-14 LUFS、TP=-1 dBTP、LRA=11；務必 two-pass + linear=true，single-pass 會 pumping
- 修：修掉『整片比別人小聲被平台對比顯弱、或破音爆掉』+ 確保不會因 single-pass 製造新的 pumping 動態抽動

_來源：www.soundstripe.com / krotos.studio / sfxengine.com / podrewind.com / www.musicguymixing.com / async.com_

## ✂️ 節奏 Pacing + 剪接點

**Cut on action（在動作中切，業餘是切在動作前/後的靜止點）**  〔expert-consensus ·常識｜Editkin v4 structured command（Ctrl+B 在動作幀切 + 刪靜止頭尾）〕
- 做法：在主體『動作進行到約前 1/3』的瞬間下刀，而非動作開始前或結束後的靜止幀。動作本身（轉頭、伸手、起身、舉杯、按 Enter）會吸住觀眾視線，蓋掉接點 → 接點變『隱形』。creator 用法：教學長片從『臉部講話鏡頭』切到『螢幕錄影 demo』時，卡在手指按下按鍵或滑鼠移動的那一刻切，而不是手停住才切。30fps 下：找到動作起點幀，往後數約 3-5 幀（動作的前 1/3）下第一刀，下一個鏡頭從動作延續處接。
- 數值：下刀點=動作的前 1/3（約 dead-center 之前）；@30fps 約動作起點後 3-5 幀；剪掉動作 exit frame 後不要 linger『連幾幀都不要』否則觀眾斷掉故事。
- 修：業餘 tell #2「切點卡在動作中間或靜止點」的反面具體值：amateur 切在『手完全停住、人不動』的死點，接點很明顯像跳一下。Pro 切在動作 first-third，眼睛被動作帶過去不會注意到剪。

**J-cut（下一段聲音先進，畫面後到）**  〔expert-consensus ·常識｜Editkin v4 structured command（Detach audio + 拖音訊左緣 / 獨立音軌提早起播）；ffmpeg 用 -itsoffset 對單軌位移較麻煩，建議 Editkin v4 structured command 做〕
- 做法：把『下一個鏡頭的聲音』往前拖，讓觀眾先聽到下一段（旁白第一個字 / 螢幕錄影的點擊聲 / B-roll 環境音），約 0.5-1 秒後畫面才切過去。製造『耳朵先帶路、眼睛跟上』的順滑感，最常用在轉場與開新主題。creator 教學長片用法：講『接下來我們打開 X 工具』這句旁白還沒講完，X 工具的螢幕錄影聲音已經淡進，再過 ~24 幀畫面才切到螢幕。
- 數值：音訊提前量：對白/旁白 0.5-2 秒（@30fps = 15-60 幀）；起手值=1 秒（30 幀），再用耳朵調。超過 ~2 秒（4 秒明顯）會『聽到 A 卻看到 B』造成混亂。閉眼聽：若像自然對話無突兀跳→成功。
- 修：業餘 tell：每個鏡頭『聲音畫面同一幀一起切』→ 一刀切死、很硬、像投影片翻頁。J-cut 讓接點被聲音的提前『軟化』，是『硬切看起來很業餘』最便宜的解。

**L-cut（前一段聲音延續，畫面先切）**  〔expert-consensus ·常識｜Editkin v4 structured command（video 提早切、audio 軌延後 + fade）〕
- 做法：畫面先切到下一個鏡頭，但『前一段的聲音』還繼續墊在底下 0.5-2 秒才淡出。常用在：旁白還在講上一句、畫面已經切到 B-roll/螢幕示範；或受訪/講者的聲音蓋過反應鏡頭。creator 用法：旁白講『這個功能我超愛』還沒收尾，畫面已經切到該功能的螢幕錄影 → 資訊不斷、節奏不卡。Editkin v4 structured command：把目前 clip 的『畫面』(video) 提早切短，但音訊軌往後多留 0.5-2s 再 fade。
- 數值：音訊延後量：0.5-2 秒（@30fps = 15-60 幀），起手 1 秒；尾端配 0.3-0.5s fade out 避免突斷。一段對話/旁白盡量 J/L 短（幾幀到 1-2 秒）才自然。
- 修：同 J-cut，修『聲畫同幀硬切』。J/L 一起用＝整片接點像水流不像翻頁。也修『B-roll 一插進來資訊就斷掉、觀眾走神』——用前段旁白墊住維持資訊密度（呼應 creator b-roll 斷點規則）。

**Match on action（動作匹配剪，兩鏡頭動作對齊接）**  〔expert-consensus｜Editkin v4 structured command（逐幀 ←/→ 微調入點對齊）〕
- 做法：兩個不同鏡頭/景別拍同一個動作，剪接時讓『移動中的東西（手/頭/物件）在 A 鏡尾幀位置 = B 鏡頭幀位置』。例：講者轉頭從 wide 切 close-up，對齊轉頭中段→看不出剪、像一鏡到底。教學片可用：A 鏡手伸向鍵盤(wide)，B 鏡(螢幕特寫)手指落鍵繼續，動作接上＝無縫。@30fps：找 A 鏡動作中段幀記住手的位置，B 鏡找手在『同位置稍前』的幀當入點，必要時逐幀(←/→)微調 1-2 幀對齊。
- 數值：對齊容差：≤1-2 幀（@30fps）；移動物件在接點兩側位置須一致，否則『跳接』。屬古典剪接(Griffith)，逐幀對。
- 修：業餘 tell：景別一換動作就『跳一下/重複一次』（她好像轉了兩次頭）。Match on action 讓 wide→tight 變隱形，是 cut-on-action 的進階雙鏡版。

**Match cut / Graphic match（形狀或概念匹配剪，創意轉場）**  〔expert-consensus｜拍攝/腳本期規劃 → Editkin v4 structured command 對齊構圖硬切〕
- 做法：用兩個畫面『相似的形狀/構圖/動作/聲音』接起來製造『咦同一個東西』的驚喜或主題連結。三種：①Graphic match（圓形馬桶漩渦→眼睛；火焰→日出）②Action match（丟骨頭→太空船，即進階 match on action）③Audio match（直升機聲→吊扇聲延續過場）。
- 數值：用量：sparingly，每片 0-2 個；需前期(拍攝/腳本)規劃構圖一致；接點用 cut（非 dissolve）保留『撞』的驚喜感。
- 修：不是修業餘 tell，而是『升級到 pro 印象點』的招牌轉場。少用、有目的用（每片 0-2 次），用多了變花俏。能取代廉價的內建炫砲 transition（業餘 tell：到處用 spin/glitch 轉場）。

**踩拍剪（cut on beat，但別每拍都踩）**  〔expert-consensus ·常識｜Editkin v4 structured command（BGM 自動 Mark beats → clip 吸附 beat marker → 峰值手動微調）〕
- 做法：用 BGM 節拍當剪接格線：scene cut / 轉場 / 字卡彈出 / zoom punch / 色彩變化 對齊 beat（尤其 downbeat 第 1 拍與 drop）。creator 美食/旅遊/重機直式 Shorts montage 主力。Editkin v4 structured command：選 BGM → 自動偵測 beat（節拍標記/Mark beats）打點 → 拖 clip 邊緣吸附到 beat marker；峰值不準再手動拖到波形最高點。
- 數值：踩『downbeat（每小節第 1 拍）/ drop / 切分音』而非每拍；可先順著歌詞/句子折 cut，最後一道再把重點 cut 打在 beat 上。標題/色變/zoom 對 downbeat 最有感。
- 修：業餘 tell #1+#3「固定每 3 秒一刀 / 整片同節奏」在 Shorts 的版本＝『每拍都切』機械感。Pro 在重拍切、弱拍留，製造『鬆-緊-鬆』有機呼吸。也修『剪接點跟音樂無關、各走各的』飄移感。

**刪贅 vs 留白（剪掉 um/嗯啊/吸氣/死空檔，但留住有意義的停頓）**  〔data-backed ·常識｜Editkin v4 structured command（手動 Ctrl+B 切死空檔 / 文字稿剪輯刪 filler）；ffmpeg silencedetect 定位 + atrim（非 aselect，呼應 M95）〕
- 做法：把廢話、吸氣、口頭禪、false start、長死空檔剪掉拉緊節奏，但『刻意強調用的停頓』要留。閾值依內容類型設靜音偵測：教學/explainer 0.3-0.5s 最緊（衝留存）、solo talking-head 0.5-0.7s、podcast/對談 0.8-1.2s 保留呼吸。30 分鐘 raw 通常有 4-7 分鐘純死空檔可砍。creator 教學長片(旁白)建議 0.5s 門檻＋手動復原刻意停頓。
- 數值：靜音門檻：tutorial 0.3-0.5s / solo 0.5-0.7s(預設 0.7) / podcast 0.8-1.2s；raw 30min ≈ 4-7min 死空檔可砍；順序＝降噪→靜音→filler→手動復原刻意停頓。太緊(全砍)會 robotic、太鬆砍不夠。
- 修：業餘 tell #4「留太多廢鏡/太空」與 tell『留太多吸氣口水音 um 嗯』。但反向過度也是業餘——全砍到 0 變『機關槍喘不過氣』，所以留 emphasis 停頓。creator 既有 M95『句間死空檔』即此條的子…

**Shot length 變化（破解 metronome，建立 ASL baseline 再偏離）**  〔expert-consensus ·常識｜概念層（規劃鏡序）→ Editkin v4 structured command/ffmpeg 執行；creator 既有 pattern-interrupt 分段節奏即此條落地〕
- 做法：先定一個『平均鏡長 ASL baseline』給觀眾建立預期，再『刻意偏離』來控情緒：要緊張/高潮→把鏡頭越剪越短；要喘息/反思→放長鏡。現代片 ASL 約 4-6 秒當中性基準。creator 教學長片：開場(0-3min)鏡短(10-15s 一變化)、中段放寬(25-40s 一刀)、重點/數據處放慢讓畫面呼吸——故意非等距。算 ASL：總秒數 ÷ 總 cut 數。
- 數值：ASL 中性基準 4-6s；action/montage 2.4s（如 Bourne）甚至更短，沉穩段 13s（如 2001）；變速必綁敘事理由（隨機變速=業餘）。固定每 3s=metronome 要打破。
- 修：業餘 tell #1+#3 核心「固定每 3 秒一刀 / 整片同一節奏」。每個鏡頭同長＝像節拍器，dull、predictable。Pro＝相似節奏中夾變化(像音樂)。每次變速都要有『敘事理由』(隨機變速也是業餘 t…

**Tension build（加速剪：鏡頭漸短堆張力到高潮）**  〔expert-consensus｜Editkin v4 structured command（逐 clip 縮 trim 製遞減）＋音效升 pitch/加速 BGM〕
- 做法：在要堆張力/帶到重點 reveal 的段落，鏡頭『一個比一個短』(accelerating rhythm)，cut 越來越快逼近高潮，到 payoff 那刻可接一個長鏡或停頓『放掉』。creator 用法：教學長片帶到『最終成果/數據對比』前的 build-up，或 Shorts 結尾 reveal 前——前 3-4 個鏡頭逐步縮短(如 1.5s→1s→0.7s→0.4s)製造『要來了』。
- 數值：鏡長遞減示例 @30fps：45f(1.5s)→30f(1s)→21f(0.7s)→12f(0.4s)；fast cut 段鏡長『幾秒或更短』；高潮幀後接長鏡/停頓釋放。
- 修：業餘 tell『整片同節奏、沒有起伏、高潮跟平鋪一樣平』。加速剪給影片『往上爬』的方向感與情緒弧線，是『太平、沒記憶點』的解。也對應 creator『別把高潮埋 15-20s』——build 之外先閃 preview。

**呼吸留白（establishing / 喘息鏡，避免太碎）**  〔expert-consensus｜概念層(鏡序規劃) → Editkin v4 structured command/ffmpeg 執行；呼應 creator b-roll 呼吸點 + MrBeast 反轉教訓〕
- 做法：在密集快剪或大量資訊後，刻意給一個『長一點、安靜一點』的鏡頭讓觀眾喘息與消化(慢段、空景、講者停一下)。對應 MrBeast 2024 自我反轉：放慢、讓場景呼吸、少吼。creator 用法：教學片每講完一個重觀念，給 2-3s 畫面慢下來(成果靜態畫面 + 旁白短停)再進下一段；旅遊 Shorts 在快剪 montage 中插一個 1.5-2s 的定鏡空景。重點：留白要『有意義』(消化/情緒)，不是忘了剪的廢鏡。
- 數值：喘息鏡長 ≈ baseline ASL 的 1.5-2 倍(如 baseline 4-6s 段，喘息給 8-12s；Shorts 快剪中插 1.5-2s 定鏡)；放在密集資訊/快剪段『之後』。留白須有功能(消化/情緒)，否則就是該砍的廢鏡。
- 修：業餘 tell『太碎、全程高速無喘息、看完很累』(過度刺激片留存高但 satisfaction 低被降推)。但也別反向變『太空/廢鏡太多』——留白＝刻意、廢鏡＝沒剪掉，差在有無敘事功能。

_來源：www.videomaker.com / grokipedia.com / www.studiobinder.com / www.soundstripe.com / edicionvideopro.com / en.wikipedia.org_

