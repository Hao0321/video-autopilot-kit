# Bright Editorial Template System（2026-08-09）

單一真理：`community/hao-motion-kit/template_engine.py`。長片與短片只共用設計 token、母版與角色語意；實際排版必須依 16:9／9:16 重排，禁止把橫版硬裁成直版。

## 1. 17 種題材構圖語法

| style | 主要題材 | 構圖任務 |
|---|---|---|
| `cobalt_poetry` | 紀錄片、教育、人物故事 | 鈷藍留白、細線、詩性敘事 |
| `shape_play` | 玩具、DIY、親子、一般產品 | 奶油白彩色幾何、手繪感 |
| `lime_aura` | 自然、健身、生活、訪談 | 有機漸層、柔亮顆粒、呼吸感 |
| `night_signal` | 遊戲、汽機車、夜間科技 | 黑底白格、霓虹與像素階梯 |
| `cyan_lab` | 商業、軟體介面、資料 proof | 白青藍模組、流程與清晰留白 |
| `ai_chalk_grid` | AI 教學、操作解說、無臉螢幕錄影 | 黑灰格線、黃白層級、撕紙與粉筆記號 |
| `travel_journal` | 旅遊、城市散策 | 天空藍、路線、照片窗、手帳 |
| `food_pop` | 大份量、促銷、第一口反應 | 高飽和黃、巨大單品舞台 |
| `food_editorial` | 名店、城市美食指南 | 白底紅黑、直排雜誌層級 |
| `food_steam` | 現炸、燒烤、熱食 | 焦糖暖木、蒸氣、現做衝擊 |
| `food_heritage` | 傳統料理、海鮮、麵食 | 米紙、朱紅、靛藍浪紋 |
| `matcha_fresh` | 抹茶、甜點、冰品 | 抹茶綠、奶油白、圓形促銷 |
| `brush_rush` | 地方文化、動作、節慶開場 | 大筆刷、斜向速度、情緒衝擊 |
| `festival_block` | 音樂節、市集、街頭活動 | 電藍桃紅、棋盤與資訊模組 |
| `electric_lab` | 資安、研究、賽事、運動科技 | 黑黃青技術舞台、數據焦點 |
| `holo_future` | 精品、新品、未來產品 | 白底虹彩玻璃、單一產品英雄 |
| `morph_prism` | 品牌概念、時尚、美妝 | 高留白、柔焦光譜形變、書刊感 |

題材先決定構圖語法，再依段落任務選角色。不得先挑喜歡的背景，再把所有內容硬塞進去。

## 2. 10 種角色

`background / hook / chapter / quote / stat / compare / steps / lower_third / end_card / thumbnail`

- 一個 frame 只承擔一個主訊息；背景不得和 footage、臉、產品或 proof 搶第一視線。
- `hook` 先兌現標題；`chapter` 只標語意轉折；`stat` 數字最大；`compare` 兩欄等權；`steps` 最多四步。
- `thumbnail` 不是影片內 hook 的截圖；必須保留人物／產品／結果素材窗與縮圖尺度可讀性。
- 使用者有真實素材時，以 `media_paths` 放入照片窗或透明去背主體；無素材才使用純圖形版本。
- `ai_chalk_grid` 的螢幕錄影固定用 contain 保留完整介面，不得為填滿照片窗而裁掉選單、按鈕或 proof。

## 3. 長片與短片

### 16:9 長片

- 以左→右資訊流、照片窗、兩欄比較、章節編號為主。
- 字卡通常 0.7–2.4 秒；複雜步驟／proof 必須依可讀性延長。
- 章節、數據、比較、流程可全畫面；lower third 不得遮字幕與產品操作區。

### 9:16 Shorts / Reels

- 標題 2–3 行內，核心詞在上半部；安全區避開平台 UI。
- 美食 editorial／heritage 可用直排，但欄序由右至左、續欄不得出裁切安全區。
- 直式不是橫式 center crop；照片窗、字幕、CTA、價格與主體要重新分區。
- pattern interrupt 由語意／能量觸發，不固定每 N 秒塞卡。

## 4. 自動路由與呼叫

```python
from editorial_templates import render_template, resolve_style

style = resolve_style("資安科技實驗室")["key"]  # electric_lab
card = render_template(
    role="stat", title="漏洞修復率", value="87%",
    topic="資安科技實驗室", aspect="landscape",
)
```

- 長片入口：`longform_maker/brand_templates.py` 的 `bright_*`／`editorial_card()`。
- Shorts 入口：`silent_vlog_maker/shorts_vertical.py::_apply_visual_plan_cards()`。
- 視覺規劃：`visual_director.py` 在 plan 寫入 `template_system.style/aspect/roles`。
- 公開素材：`community/hao-motion-kit/templates/manifest.json`。

## 5. 儲存與開源鐵則

- 母版＋參數化原始碼是 SoT；340 張 quality-92 WebP 是可重建 cache；需要 PNG 時用 `render --out current.png` 即時輸出。
- 修同一風格只覆蓋穩定路徑；局部 build 必須合併 manifest，禁止縮掉其他資產。
- 格式升級後只用 `template_engine.py cleanup-cache` 清舊 cache；它會先逐張驗證新 manifest，驗證失敗即拒絕刪除。
- 不建立 `v2/v3/FINAL/old` 模板樹；版本寫進 changelog／manifest，不複製整庫。
- 使用者參考圖只提煉色彩、層級、形狀與題材差異，不進開源包、不複製品牌、字樣或特定版式。
- 發佈前跑 `template_engine.py selftest` 與 `release_check.py`；manifest 必須是 17×10×2＝340。

## 6. 美術驗收

1. 縮小到手機寬度仍能讀主標。
2. 中文無 tofu、裁切、反向欄序或末字孤欄。
3. 主體／proof／字幕的安全區不互撞。
4. 同一題材至少有 hook、資訊、呼吸、payoff 四種視覺強度，不全片滿能量。
5. 題材差異來自構圖語法，不是同一模板換色。
6. 全片效果服務旁白與證據；可移除而不影響理解的裝飾，優先刪掉。
