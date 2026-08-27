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
| b-roll 跟旁白無關 / 像壁紙隨機鋪 | Cut on the word：旁白講到那名詞/動作的同一幀切進對應 b-roll(±1 幀內)；示範段用 sequential 因果動作鏈、概念段才用 illustrative 單圖。對應 Hao 既有 M87 matcher 的理論依據 |
| talking head / 旁白剪接點露出 jump cut | 剪接點上層 overlay 壓一顆 1-3 秒 cutaway 跨過接縫(兩側各留 ~0.5 秒)，搭 J/L-cut 更順。Hao 不露臉版：每次音軌剪掉一句的接縫壓螢幕特寫蓋住突兀切換 |
| 整片同一個 wide(停太久無聊) 或反向每 2 秒亂跳(焦慮) | 時長分級表：cutaway/reaction 1-2 秒、情境 b-roll 2-5 秒、動作鏈每顆 2-4 秒；任何畫面 >8 秒沒變化補一刀、連續多顆 <2 秒太碎要拉長。Shorts 2-4 秒一刀但長片別照搬 |
| 膚色橘到發假 / 套冷調後膚色發青 | 膚色落 vectorscope ~11 點鐘 I-line、左右均分；飽和控 20-50%；套完冷暖風格後 HSL 二級把膚色拉回自然。vibrance 開膚色保護 |
| 邊緣有白光暈(halo)、畫面過硬發脆、噪點被放大 | 相機端關銳化；後製只銳 luminance、半徑小、amount 低。Editkin v4 structured command 銳化滑桿 ≤20-30；ffmpeg unsharp=5:5:0.4:5:5:0.0(別動 chroma) |
| 畫面平、層次扁、主體不從背景跳出 | Teal & Orange 微量收尾：陰影推青藍 + 高光/中間調推橙(膚色本在橙帶，陰影推青讓主體跳)。當收尾微量別無腦全套；純螢幕教學片要更克制(會讓 UI 截圖發色偏) |
| 全靠肉眼調色、換螢幕/環境光就走鐘 | 配示波器：RGB Parade 看中性畫面三通道對齊、Waveform 看黑白點、Vectorscope 看膚色 I-line 與飽和不爆框。ffmpeg 無即時 scope，剪完抽 contact sheet 逐格目視一致性 |
| 人聲軌只有 dynaudnorm、沒有真正 acompressor → 旁白忽大忽小（湊近麥那句爆、轉頭那句聽不到）治不到根。實際驗證 build_audio.py 第44行 voice chain = `highpass=f=80,dynaudnorm=f=200:g=7`，acompressor 只掛在 build_final.py 的 BGM 軌（[1:a]）不是人聲。 | 在人聲軌（build_audio.py 或 master_voice 後製）串一刀 `acompressor=threshold=-16dB:ratio=3:attack=10:release=120:makeup=4`，放在 highpass 之後、dynaudnorm 之前（或直接取代 dynaudnorm）。dynaudnorm=拉平整體響度、acompressor=抓 transient 壓動態，旁白要的是後者。這是『忽大忽小』ROI 最高的單一修正。 |
| 收尾 loudnorm 是 single-pass（build_final.py 第107行 `[mx]loudnorm=I=-14:TP=-1.5:LRA=11`，無 measured_* / 無 linear=true）→ single-pass loudnorm 本身是動態壓縮器，會製造 pumping（整片忽大忽小抽動），等於一邊修動態一邊又加回新的動態。 | 改 two-pass：pass1 跑 `loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json` 抓 measured_I/TP/LRA/thresh，餵 pass2 `...:measured_I=..:measured_TP=..:measured_LRA=..:measured_thresh=..:linear=true`。linear=true 是整檔一個固定增益，動態保留不 pumping。 |
| BGM 沒有真 ducking／sidechain — build_final.py 只用 `volume=0.12`（固定 -18.4dB）+ acompressor，人聲講話時 BGM 不會自動再壓低。安靜段（beat 之間 0.35s gap）BGM 也不會回升。Memory 寫『ducking 數值表已對』與實際 code 矛盾——script 裡根本沒有 ducking。 | 上 sidechain：`[music][voice]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400:makeup=1[ducked]`，人聲一進 BGM 自動壓到 ~15-25%、停了回升。比固定 volume 精準，且靜默段音樂自然浮回填空。 |
| 去聲剪輯（Hao 工作流必做）的剪接點是硬 concat（build_audio.py 用 `-c copy` concat voice+gap），沒有 room tone 補縫、也沒有 micro-crossfade → 每個被剪掉的吸氣/口誤缺口會變絕對死寂，跟前後有底噪的段落硬接會聽到『空氣消失』+ 零交越點『啪』click。 | (a) 缺口墊 -35dB room tone（錄旁白多錄 10s 環境音鋪底層）；(b) concat 改用 `acrossfade=d=0.03`（30ms）取代 `-c copy` 消 click。注意 gap.wav 現在是 `anullsrc`（純數位靜音）——這正是死寂來源，可改成極低 room tone。 |

> ✅ **上表 4 個音訊修正已全部落地 + 驗證（2026-06-26，canon M103）**，code 在 `longform_maker/reference_impl_longform01/`（行號已變，別照舊行號改）：① 人聲鏈加 `acompressor`（build_audio）② 收尾 `loudnorm` 改 two-pass `linear=true`（build_final）③ BGM 改 `sidechaincompress` 人聲 key（build_final，取代固定 volume=0.12）④ 全程 `anoisesrc` pink room-tone bed amix（build_audio，取代死靜 anullsrc）。實測：LUFS -14.07 / peak -1.36 無爆 / noise floor -54dB（非 -∞）/ ducking speech -17 vs gap -24dB。**另**：旁白加速 `SPEED` 常數貫穿三檔（offsets["_speed"] → video scene /SP + 字幕 /SP），1.08x 把 5:04→4:42，AP12 invariant 當 desync 金絲雀。詳見 M103。

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
- 修：修掉『剪接點突然死寂、一段有底噪一段全黑安靜的落差感』— 這是去聲剪輯(Hao 工作流必做)最容易留下的 tell，pro 用 room tone 把接縫抹平

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
- 做法：在主體『動作進行到約前 1/3』的瞬間下刀，而非動作開始前或結束後的靜止幀。動作本身（轉頭、伸手、起身、舉杯、按 Enter）會吸住觀眾視線，蓋掉接點 → 接點變『隱形』。Hao 用法：教學長片從『臉部講話鏡頭』切到『螢幕錄影 demo』時，卡在手指按下按鍵或滑鼠移動的那一刻切，而不是手停住才切。30fps 下：找到動作起點幀，往後數約 3-5 幀（動作的前 1/3）下第一刀，下一個鏡頭從動作延續處接。
- 數值：下刀點=動作的前 1/3（約 dead-center 之前）；@30fps 約動作起點後 3-5 幀；剪掉動作 exit frame 後不要 linger『連幾幀都不要』否則觀眾斷掉故事。
- 修：業餘 tell #2「切點卡在動作中間或靜止點」的反面具體值：amateur 切在『手完全停住、人不動』的死點，接點很明顯像跳一下。Pro 切在動作 first-third，眼睛被動作帶過去不會注意到剪。

**J-cut（下一段聲音先進，畫面後到）**  〔expert-consensus ·常識｜Editkin v4 structured command（Detach audio + 拖音訊左緣 / 獨立音軌提早起播）；ffmpeg 用 -itsoffset 對單軌位移較麻煩，建議 Editkin v4 structured command 做〕
- 做法：把『下一個鏡頭的聲音』往前拖，讓觀眾先聽到下一段（旁白第一個字 / 螢幕錄影的點擊聲 / B-roll 環境音），約 0.5-1 秒後畫面才切過去。製造『耳朵先帶路、眼睛跟上』的順滑感，最常用在轉場與開新主題。Hao 教學長片用法：講『接下來我們打開 X 工具』這句旁白還沒講完，X 工具的螢幕錄影聲音已經淡進，再過 ~24 幀畫面才切到螢幕。
- 數值：音訊提前量：對白/旁白 0.5-2 秒（@30fps = 15-60 幀）；起手值=1 秒（30 幀），再用耳朵調。超過 ~2 秒（4 秒明顯）會『聽到 A 卻看到 B』造成混亂。閉眼聽：若像自然對話無突兀跳→成功。
- 修：業餘 tell：每個鏡頭『聲音畫面同一幀一起切』→ 一刀切死、很硬、像投影片翻頁。J-cut 讓接點被聲音的提前『軟化』，是『硬切看起來很業餘』最便宜的解。

**L-cut（前一段聲音延續，畫面先切）**  〔expert-consensus ·常識｜Editkin v4 structured command（video 提早切、audio 軌延後 + fade）〕
- 做法：畫面先切到下一個鏡頭，但『前一段的聲音』還繼續墊在底下 0.5-2 秒才淡出。常用在：旁白還在講上一句、畫面已經切到 B-roll/螢幕示範；或受訪/講者的聲音蓋過反應鏡頭。Hao 用法：旁白講『這個功能我超愛』還沒收尾，畫面已經切到該功能的螢幕錄影 → 資訊不斷、節奏不卡。Editkin v4 structured command：把目前 clip 的『畫面』(video) 提早切短，但音訊軌往後多留 0.5-2s 再 fade。
- 數值：音訊延後量：0.5-2 秒（@30fps = 15-60 幀），起手 1 秒；尾端配 0.3-0.5s fade out 避免突斷。一段對話/旁白盡量 J/L 短（幾幀到 1-2 秒）才自然。
- 修：同 J-cut，修『聲畫同幀硬切』。J/L 一起用＝整片接點像水流不像翻頁。也修『B-roll 一插進來資訊就斷掉、觀眾走神』——用前段旁白墊住維持資訊密度（呼應 Hao b-roll 斷點規則）。

**Match on action（動作匹配剪，兩鏡頭動作對齊接）**  〔expert-consensus｜Editkin v4 structured command（逐幀 ←/→ 微調入點對齊）〕
- 做法：兩個不同鏡頭/景別拍同一個動作，剪接時讓『移動中的東西（手/頭/物件）在 A 鏡尾幀位置 = B 鏡頭幀位置』。例：講者轉頭從 wide 切 close-up，對齊轉頭中段→看不出剪、像一鏡到底。教學片可用：A 鏡手伸向鍵盤(wide)，B 鏡(螢幕特寫)手指落鍵繼續，動作接上＝無縫。@30fps：找 A 鏡動作中段幀記住手的位置，B 鏡找手在『同位置稍前』的幀當入點，必要時逐幀(←/→)微調 1-2 幀對齊。
- 數值：對齊容差：≤1-2 幀（@30fps）；移動物件在接點兩側位置須一致，否則『跳接』。屬古典剪接(Griffith)，逐幀對。
- 修：業餘 tell：景別一換動作就『跳一下/重複一次』（她好像轉了兩次頭）。Match on action 讓 wide→tight 變隱形，是 cut-on-action 的進階雙鏡版。

**Match cut / Graphic match（形狀或概念匹配剪，創意轉場）**  〔expert-consensus｜拍攝/腳本期規劃 → Editkin v4 structured command 對齊構圖硬切〕
- 做法：用兩個畫面『相似的形狀/構圖/動作/聲音』接起來製造『咦同一個東西』的驚喜或主題連結。三種：①Graphic match（圓形馬桶漩渦→眼睛；火焰→日出）②Action match（丟骨頭→太空船，即進階 match on action）③Audio match（直升機聲→吊扇聲延續過場）。
- 數值：用量：sparingly，每片 0-2 個；需前期(拍攝/腳本)規劃構圖一致；接點用 cut（非 dissolve）保留『撞』的驚喜感。
- 修：不是修業餘 tell，而是『升級到 pro 印象點』的招牌轉場。少用、有目的用（每片 0-2 次），用多了變花俏。能取代廉價的內建炫砲 transition（業餘 tell：到處用 spin/glitch 轉場）。

**踩拍剪（cut on beat，但別每拍都踩）**  〔expert-consensus ·常識｜Editkin v4 structured command（BGM 自動 Mark beats → clip 吸附 beat marker → 峰值手動微調）〕
- 做法：用 BGM 節拍當剪接格線：scene cut / 轉場 / 字卡彈出 / zoom punch / 色彩變化 對齊 beat（尤其 downbeat 第 1 拍與 drop）。Hao 美食/旅遊/重機直式 Shorts montage 主力。Editkin v4 structured command：選 BGM → 自動偵測 beat（節拍標記/Mark beats）打點 → 拖 clip 邊緣吸附到 beat marker；峰值不準再手動拖到波形最高點。
- 數值：踩『downbeat（每小節第 1 拍）/ drop / 切分音』而非每拍；可先順著歌詞/句子折 cut，最後一道再把重點 cut 打在 beat 上。標題/色變/zoom 對 downbeat 最有感。
- 修：業餘 tell #1+#3「固定每 3 秒一刀 / 整片同節奏」在 Shorts 的版本＝『每拍都切』機械感。Pro 在重拍切、弱拍留，製造『鬆-緊-鬆』有機呼吸。也修『剪接點跟音樂無關、各走各的』飄移感。

**刪贅 vs 留白（剪掉 um/嗯啊/吸氣/死空檔，但留住有意義的停頓）**  〔data-backed ·常識｜Editkin v4 structured command（手動 Ctrl+B 切死空檔 / 文字稿剪輯刪 filler）；ffmpeg silencedetect 定位 + atrim（非 aselect，呼應 M95）〕
- 做法：把廢話、吸氣、口頭禪、false start、長死空檔剪掉拉緊節奏，但『刻意強調用的停頓』要留。閾值依內容類型設靜音偵測：教學/explainer 0.3-0.5s 最緊（衝留存）、solo talking-head 0.5-0.7s、podcast/對談 0.8-1.2s 保留呼吸。30 分鐘 raw 通常有 4-7 分鐘純死空檔可砍。Hao 教學長片(旁白)建議 0.5s 門檻＋手動復原刻意停頓。
- 數值：靜音門檻：tutorial 0.3-0.5s / solo 0.5-0.7s(預設 0.7) / podcast 0.8-1.2s；raw 30min ≈ 4-7min 死空檔可砍；順序＝降噪→靜音→filler→手動復原刻意停頓。太緊(全砍)會 robotic、太鬆砍不夠。
- 修：業餘 tell #4「留太多廢鏡/太空」與 tell『留太多吸氣口水音 um 嗯』。但反向過度也是業餘——全砍到 0 變『機關槍喘不過氣』，所以留 emphasis 停頓。Hao 既有 M95『句間死空檔』即此條的子…

**Shot length 變化（破解 metronome，建立 ASL baseline 再偏離）**  〔expert-consensus ·常識｜概念層（規劃鏡序）→ Editkin v4 structured command/ffmpeg 執行；Hao 既有 pattern-interrupt 分段節奏即此條落地〕
- 做法：先定一個『平均鏡長 ASL baseline』給觀眾建立預期，再『刻意偏離』來控情緒：要緊張/高潮→把鏡頭越剪越短；要喘息/反思→放長鏡。現代片 ASL 約 4-6 秒當中性基準。Hao 教學長片：開場(0-3min)鏡短(10-15s 一變化)、中段放寬(25-40s 一刀)、重點/數據處放慢讓畫面呼吸——故意非等距。算 ASL：總秒數 ÷ 總 cut 數。
- 數值：ASL 中性基準 4-6s；action/montage 2.4s（如 Bourne）甚至更短，沉穩段 13s（如 2001）；變速必綁敘事理由（隨機變速=業餘）。固定每 3s=metronome 要打破。
- 修：業餘 tell #1+#3 核心「固定每 3 秒一刀 / 整片同一節奏」。每個鏡頭同長＝像節拍器，dull、predictable。Pro＝相似節奏中夾變化(像音樂)。每次變速都要有『敘事理由』(隨機變速也是業餘 t…

**Tension build（加速剪：鏡頭漸短堆張力到高潮）**  〔expert-consensus｜Editkin v4 structured command（逐 clip 縮 trim 製遞減）＋音效升 pitch/加速 BGM〕
- 做法：在要堆張力/帶到重點 reveal 的段落，鏡頭『一個比一個短』(accelerating rhythm)，cut 越來越快逼近高潮，到 payoff 那刻可接一個長鏡或停頓『放掉』。Hao 用法：教學長片帶到『最終成果/數據對比』前的 build-up，或 Shorts 結尾 reveal 前——前 3-4 個鏡頭逐步縮短(如 1.5s→1s→0.7s→0.4s)製造『要來了』。
- 數值：鏡長遞減示例 @30fps：45f(1.5s)→30f(1s)→21f(0.7s)→12f(0.4s)；fast cut 段鏡長『幾秒或更短』；高潮幀後接長鏡/停頓釋放。
- 修：業餘 tell『整片同節奏、沒有起伏、高潮跟平鋪一樣平』。加速剪給影片『往上爬』的方向感與情緒弧線，是『太平、沒記憶點』的解。也對應 Hao『別把高潮埋 15-20s』——build 之外先閃 preview。

**呼吸留白（establishing / 喘息鏡，避免太碎）**  〔expert-consensus｜概念層(鏡序規劃) → Editkin v4 structured command/ffmpeg 執行；呼應 Hao b-roll 呼吸點 + MrBeast 反轉教訓〕
- 做法：在密集快剪或大量資訊後，刻意給一個『長一點、安靜一點』的鏡頭讓觀眾喘息與消化(慢段、空景、講者停一下)。對應 MrBeast 2024 自我反轉：放慢、讓場景呼吸、少吼。Hao 用法：教學片每講完一個重觀念，給 2-3s 畫面慢下來(成果靜態畫面 + 旁白短停)再進下一段；旅遊 Shorts 在快剪 montage 中插一個 1.5-2s 的定鏡空景。重點：留白要『有意義』(消化/情緒)，不是忘了剪的廢鏡。
- 數值：喘息鏡長 ≈ baseline ASL 的 1.5-2 倍(如 baseline 4-6s 段，喘息給 8-12s；Shorts 快剪中插 1.5-2s 定鏡)；放在密集資訊/快剪段『之後』。留白須有功能(消化/情緒)，否則就是該砍的廢鏡。
- 修：業餘 tell『太碎、全程高速無喘息、看完很累』(過度刺激片留存高但 satisfaction 低被降推)。但也別反向變『太空/廢鏡太多』——留白＝刻意、廢鏡＝沒剪掉，差在有無敘事功能。

_來源：www.videomaker.com / grokipedia.com / www.studiobinder.com / www.soundstripe.com / edicionvideopro.com / en.wikipedia.org_

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
- 做法：『Match action to meaning』：旁白講到那個名詞的同一幀切進對應 b-roll，不早不晚。剪輯具體做法：先在波形上標出關鍵字出現的時間點（Editkin v4 structured command 自動字幕可看每個詞的時間軸），把 b-roll clip 的入點對齊到那個字的起始幀。Hao pipeline 已有 M87 caption-broll matcher，這條是它的理論依據——對齊精度要到幀，不是『大概那段』。
- 數值：切點對齊到關鍵字起始幀（30fps=±1 幀內）；插太早或太晚衝擊就消失
- 修：b-roll 跟旁白無關：每顆 b-roll 必須對應旁白此刻講的那個詞/動作，切點壓在關鍵字第一幀

**Cutaway / insert 遮跳接（hide the jump cut）**  〔expert-consensus ·常識｜both〕
- 做法：talking head 或旁白剪掉一段（卡詞、停頓、刪冗句）會留下跳接，用 cutaway 蓋住接縫：在 Editkin v4 structured command 把 b-roll 放上層 overlay track（上層蓋下層），長度 1-3 秒，跨過剪接點，觀眾看不到下層的 jump。Hao 不露臉版：每次旁白音軌剪掉一句的接縫處，上面壓一顆螢幕特寫/b-roll cutaway 蓋住音訊的突兀切換（搭 J/L-cut 更順）。
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
- 做法：Coverage 要『景別與角度多變』但『技術規格一致』。最 amateur 的 tell 是 b-roll 之間光線/白平衡/解析度/色調對不上（半段大太陽半段昏暗室內，觀眾立刻看出拼接）。做法：①拍時固定白平衡和曝光，不要自動 ②剪輯時所有 clip 套同一組 LUT/調色，stock b-roll 也要拉到同色溫 ③解析度/fps 統一（Hao 已有 24→30fps 轉換規則，延伸到色調統一）。
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
- 做法：業餘最大破綻是直接用編輯器預設 Arial / 微軟正黑。Pro 的動態圖文用『幾何感無襯線 + 有粗細變化』的字體，在動態中清晰：英文 Montserrat / Poppins / Futura / Bebas Neue；中文搭 Noto Sans TC / 思源黑體 / 粉圓（Hao Shorts 已用）。
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
- 做法：不露臉頻道靠 lower third 補『誰在說/這是什麼』。業餘的 lower third 會旋轉、彈跳、動很久搶戲。Pro 規則：進場用『單純 slide-in（從左滑入或從下推上）或 fade』，時長 0.3–0.5s；停留 3–5s 讓人讀完；出場對稱退場。主資訊一行（speaker/標籤）字最大，副資訊一行小字。背景條可留極微動態增加質感，但別超過主體。
- 數值：slide 或 fade 進出 0.3–0.5s、停 3–5s；禁旋轉/彈跳/長動畫；主資訊一行最大、副一行小。ffmpeg：drawbox 底條 + drawtext x=f(t) 滑入 + enable='between(t,s,e)'
- 修：業餘 tell『字硬切無動畫』+『動畫炫技搶戲』——lower third 要安靜、可讀、不露臉的資訊支柱

**安全邊距：所有字/圖卡縮在畫面內 5–10%，直式避最下 20%**  〔expert-consensus ·常識｜both〕
- 做法：業餘把字頂到畫面邊緣或壓在 UI（TikTok/Reels 右側按鈕、底部帳號列）上。Pro 守 title-safe：『內縮畫面外圍 10%』放字（重要圖形守 action-safe ~5%）；橫式 1920×1080 → 字保持距邊 ~96–192px。
- 數值：title-safe 內縮外圍 10%、action-safe ~5%；橫式距邊 96–192px；直式避底 20%(320–350px)+右 84–120px，字幕 Y 1200–1550。ffmpeg x=w*0.05 / y=h*0.78
- 修：業餘 tell『置中亂飄』+ 字被裁切/壓 UI——安全邊距讓版面穩定專業

**克制原則：一個元素一種動畫，砍字數，禁同時多特效堆疊**  〔expert-consensus｜both〕
- 做法：業餘把每個字加不同特效、又彈又轉又閃 + 整屏塞滿字。Pro 鐵律：『一個好動畫勝過十個同時的特效』(one well-timed scale beats ten simultaneous effects)。每個元素只挑一種主動畫(進場)；同畫面同時動的元素 ≤2–3；字數砍到每張卡 ≤6–8 字、字幕 ≤2 行。動畫要『被訊息驅動』——快動畫=能量、慢動畫=重量，別為動而動。
- 數值：一元素一動畫；同時動的元素 ≤2–3；每卡 ≤6–8 字、字幕 ≤2 行；動畫由訊息驅動(快=能量/慢=重量)；先畫 4–6 關鍵畫面 storyboard
- 修：業餘 tell『字太多太滿』+『特效 kitchen-sink 亂炸』——克制是 amateur↔pro 最大分水嶺

**進度條 / 計時器：keyframe Position 或 Scale 跑寬度（線性 OK），補時間軸視覺**  〔expert-consensus｜both〕
- 做法：不露臉教學長片靠進度條/倒數補『現在到哪』。做法：一條矩形(底色)+一條彩色前景條，前景用 keyframe 把 Scale-X 從 0→100% 或 Position 由左拉到右，跨整段時間軸。進度條這種『資訊量計』用線性反而正確(等速=真實進度)，不必 ease。倒數計時器同理用文字 + 每秒換值（或現成 timer 模板）。放畫面頂或底安全區。
- 數值：前景條 Scale-X 0→100% 或 Position 左→右，跨整段，線性 OK(進度=真實);倒數=文字每秒換值。放安全區頂/底。ffmpeg drawbox 寬度隨 t
- 修：補『不露臉頻道缺視覺』——進度感/節奏感的低成本動態圖文

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
- 做法：建時間軸時先把『旁白語音軌 + 對應情緒的音樂 + 幾個音效』全部鋪好，一個 video clip 都還沒拖。這條 audio blueprint 會在你補畫面『之前』就暴露哪段太長、哪個 beat 不成立。Hao 已是旁白驅動：把旁白軌當骨架，畫面是後貼的 b-roll，正好吻合。ffmpeg 做法：先 concat 旁白成完整音軌→看波形/字幕稿抓段落，再對齊 b-roll。
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
- 做法：進 assembly 前，先把每天/每主題拍到的『最好的瞬間』抽成一條 selects reel（一條只放精華的時間軸）。把這些精華串成 string-out（按敘事順序的精華骨幹）——它先讓你看清楚『這片最好的素材有哪些』，再決定怎麼排成故事。對 Hao 的混雜素材（OBS 螢幕錄 + b-roll + 自錄剪輯畫面）特別有用：先各自抽 selects，避免在 100+ clip 裡盲剪。
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
- 做法：Save the Cat 在約 22% 引入 B-story——通常是承載『情感/主題』的副線，和主線(A-story=任務/教學)交織。對 Hao 不露臉的 AI 教學長片，B-story 可以是：『我為什麼踩這個坑 / 這工具怎麼改變我的工作流 / 一個具體的個人小故事』穿插在純功能教學之間，讓觀眾有情感黏著、不只是看 spec。
- 數值：B-story 約在 22% 引入、貫穿全片，承載情感/主題副線（A-story=任務、B-story=人性）
- 修：業餘 tell：教學長片『純功能 dump』——只有步驟 1234，沒有人味、沒有『為什麼我在乎』。B-story 注入情感維度，把規格表變成故事。

_來源：www.docfilmacademy.com / nofilmschool.com / air.io / bettervideocontent.com / www.retentionrabbit.com / siliconvalleytime.com_
