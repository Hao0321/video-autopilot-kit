# Hao Signal Grid — 自動剪輯美術與節奏 SoT（2026-08-08）

> 目標：把「安全但像簡報」升級成「有導演意圖的頻道美術」。靈感取自高對比城市 UI、
> 街頭印刷、漫畫資訊層級與現代 motion graphics；**不複製《絕區零》的 logo、角色、素材、
> UI 畫面或特定版式**。成品必須可辨識為 Hao 自己的 Signal Grid。

## 研究結論 → 可執行規則

1. **世界觀先於特效**：HoYoverse 對《絕區零》「獨特感」的官方訪談把來源指向生活經驗、
   graphic/UI 細節與一致性。落地：所有片型共用黑底白格、索引線、編號與斜切框；題材只換 accent。
2. **B-roll 要加意義**：Adobe 將 B-roll 的作用定為建立場景、平順轉場與增加意義。落地：
   `visual_grammar` 先決定該拍／該找什麼，不允許拿抽象背景代替對應畫面。
3. **Motion graphics 要傳意，不是填空**：文字＋設計元素的運動用來娛樂或解釋資訊。
   落地：`visual_director` 只在語意轉折、步驟、數據、價格與 payoff 插卡。
4. **留存校準而非固定刀速**：YouTube 官方建議從 retention 找慢 intro、混亂解說與不自然 jump cut。
   落地：每題材有 shot range，但發布後仍以 D2/D7/D28 retention 回灌，不把「每 2 秒一刀」當真理。

## 視覺 DNA（所有題材不變）

- 近黑底＋低對比白線格；中央乾淨、裝飾待在邊緣。
- 白字為主；每支只用 1 主 accent＋1 資訊色。
- 斜切角、城市索引、兩位數編號、短 micro-label。
- 高能事件後至少留一個乾淨鏡頭；glitch 全片最多一次。
- 字卡底可以低頻呼吸／格線跑光；**字本身不 jitter、不連續彈跳**。
- 真畫面永遠優先。背景 loop 只用於章節卡、解說空檔、資料／步驟視覺，不可連續鋪滿。

## 題材包

| key | 色彩 | 鏡頭語法 | 卡型 |
|---|---|---|---|
| `ai` | signal yellow + cyan | 真操作→局部放大→步驟／證據 | code / steps / proof / question |
| `food` | coral + butter yellow | 全景→製作動作→極近特寫→入口 payoff | price / taste / menu / verdict |
| `travel` | sky blue + orange | 地標→人作比例尺→移動 POV→細節 | location / route / note / chapter |
| `toy` | bubble pink + yellow | 包裝懸念→拆封→零件微距→完成旋轉 | spec / detail / score / question |
| `game` | acid lime + purple | 爆點前置→前因→操作→impact 秒收 | impact / stat / tip / versus |
| `diy` | orange + blue | 成品爆閃→before→縮時＋原速錨點→after | materials / steps / warning / result |
| `cafe` | cream + mauve | 空間→沖煮／切面→質地微距→安靜收尾 | menu / texture / note / verdict |

另有 `documentary`、`interview`、`automotive`、`fitness`、`fashion`、`architecture`、
`business`、`nature`、`music`、`product` 十套延伸色彩與領域語法。完整的第一鏡、景別組句、
聲音主角與禁忌見 [`cinematic-wave-and-domain-grammar-2026.md`](cinematic-wave-and-domain-grammar-2026.md)。

## 程式入口

- `art_direction.py`
  - `infer_theme(text, hint="auto")`
  - `render_background(..., variant="signal_grid")`
  - `render_title_card(...)`
  - `decorate_frame(...)`
- `visual_director.py`
  - `infer_domain(text, hint="auto")`：判斷怎麼剪；與 theme（長什麼樣）分離。
  - `plan_visual_rhythm(duration, captions, genre, seed, format, context_text)`
  - `write_visual_plan(path, ...)`
- `longform_maker/brand_templates.py`
  - 所有卡片新增 `theme=`；`title_card()` 是新主標入口。
- `shorts_autopilot.py build N`
  - 自動從 `SPEC.niche`／題目／字幕／BGM 推斷 theme，套繁中字體並輸出
    `<name>_visual_plan.json`；中段語意事件會在句首硬切插入 0.4–0.8 秒全屏 Signal Grid 字卡，
    片頭與 loop 尾幀不動。舊 `_plan.py` 沒 `niche` 仍可用。
- `longform_maker/asset_forge.py`
  - `signal_grid.mp4`／`editorial_panels.mp4`；raw frame 直接 pipe ffmpeg，零暫存 PNG。

## 使用節奏

1. 先跑素材 audit，字幕與真畫面對位。
2. 以 transcript/captions 跑 `visual_director`，得到 macro 能量波、meso 景別組句、micro 字卡／聲音事件表。
3. 對每個事件選對應真素材；真的缺畫面才用題材卡或 Signal Grid。
4. 高能卡只留 0.44–0.82 秒；章節／步驟依閱讀量延長。
5. 成片跑原有 QA，再人眼看：是否太吵、是否遮主體、是否有一段連續 8 秒沒有資訊變化。

## 參考來源（2026-08-08 查）

- HoYoverse：`https://zenless.hoyoverse.com/en-us/news/123577`
- YouTube 官方 retention 指標：`https://blog.youtube/creator-and-artist-stories/master-these-4-metrics/`
- Adobe B-roll：`https://www.adobe.com/creativecloud/video/discover/b-roll.html`
- Adobe Motion Graphics：`https://www.adobe.com/uk/creativecloud/animation/discover/motion-graphics.html`
