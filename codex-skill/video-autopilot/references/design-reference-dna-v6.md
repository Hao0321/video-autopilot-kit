# Hao Design System v6：33 張參考圖的可執行 DNA

這份文件是 `knowledge/design_reference_dna.json` 的人類導航，不存原圖、不存私人路徑，也不重製可識別版式。33 張圖逐張拆成構圖、層級、色彩、字體、材質、動態翻譯、適用角色與反例；實際規劃由 `design_system_v6.py` 編譯成小型 recipe。

## 母規則

1. 每幀只有一個英雄焦點：主體、結果、數字或一句承諾只能有一個先被看見。
2. 先用比例建立層級：大／小、密／疏、亮／暗，再補線條、顆粒、掃描紋與 microtype。
3. 亮不等於亂：一個主色場＋一至兩個強調色；題材決定色，不同題材不能同版只換色。
4. 主體要進入空間：以遮擋、景深、接觸陰影、共享光向或文字前後層整合，禁止平貼。
5. 動態要保留靜態層級：只可揭露、比較、解釋、定位或兌現，不可因為模板有動畫就播放。
6. 長短片共 DNA、不共裁切：9:16 加重首幀與單一大焦點；16:9 保留脈絡、觀看耐久與更多真實畫面。
7. 網格是資訊表面，不是開場理由；HUD、票券、緞帶、波浪、筆刷、3D 都是條件式語彙。

## 十個家族

| 家族 | 核心 | 適合 | 禁忌 |
|---|---|---|---|
| `cobalt_editorial` | 鈷藍／白、極端字級、編輯留白、照片切片 | 紀錄、訪談、旅遊、章節 | 把整本雜誌塞進一幀 |
| `shape_play` | 暖紙、幾何互鎖、Riso 顆粒、手繪線 | 玩具、DIY、輕鬆解說 | 隨機幾何轉場 |
| `luminous_organic` | 萊姆光體、柔粒、呼吸留白 | 自然、健身、訪談沉澱 | 高頻跳動、污染膚色 |
| `night_signal` | 黑場、局部霓虹、掃描顆粒、技術微字 | 遊戲、車、運動、夜景 | 全片廉價發光、網格開場 |
| `travel_scrapbook` | 真照片、紙張、路線、在地手繪 | 旅遊、城市、文化 | 假地點資訊、每鏡頭明信片化 |
| `food_hero` | 超大料理主體、單色舞台、食慾材質、巨字 | 美食、咖啡、價格與份量 | 背景搶食物、假蒸氣 |
| `brush_culture` | 巨大筆觸、斜向能量、事件色塊 | 文化、音樂、玩具對決 | 表面化文化符號、每剪一筆刷 |
| `cobalt_lime_ui` | 鈷藍萊姆、證據卡、箭頭、選取標記 | AI、科技、商業、流程 | 假操作、假警報、常駐 HUD |
| `iridescent_future` | 玻璃／虹彩 3D 主體、白舞台、黑字 | 科技、精品、產品、3D | 沒有 mesh 卻假稱 3D、過曝失輪廓 |
| `ticket_ribbon` | 票券、緞帶、曲面文字、舞台深度 | 活動、音樂、時間線、引言 | 無關鏡頭間拿緞帶當 wipe |

## 編譯規則

- 一次只選一個 primary family，最多一個 support family。
- 一個 recipe 需聲明 domain、format、role、subject、energy。
- role 限定為 `first_frame / chapter / proof / comparison / process / payoff / thumbnail / lower_third / breath`。
- `first_frame` 有真素材時由真結果／衝突先出；`chapter` 不能用空白全屏模板蓋掉可用素材；`proof` 的實證必須最大；`payoff` 要最乾淨且停最久。
- 當 accent 超過兩色、同時焦點超過一個、或 primary family 與題材不符，直接 fail-closed。

## 長短片 reflow

- Shorts：英雄約佔畫面 38–68%，1–3 行字，microtype 極少；0.18–0.45 秒進場後必須有可讀 hold。
- 長片：英雄約佔畫面 24–52%，1–2 行主字；圖形只做節點標點，真實畫面與聲音需維持連續脈絡。
- 任何 16:9 到 9:16 的轉換都要重新安排焦點、字級與遮擋，中央裁切不算 reflow。

## QA

- `design_system_v6.py selftest` 驗 33 筆、匿名化、家族完整性與題材路由。
- 每支片輸出 `design_system_v6` recipe；`quality_95.py` 將 `design_dna_compiled=false` 標 REVIEW。
- Hao 人工審片仍以十維美感量表驗證；機械路由不能冒充美感完成。
