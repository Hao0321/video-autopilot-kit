# Creator Visual Master：色彩、LUT、美學與趨勢契約

> **PUBLIC_FIXTURE / privacy boundary:** creator-specific reference counts, dated reviews, project metrics, local paths and private preference evidence are excluded. Calibrate defaults with creator-owned evidence.

## 核心結論

調色不是把濾鏡疊上去。正式順序固定為：辨識輸入色彩空間 → 一級校正 →
單一創意 Look → 字幕／Tracking／動態圖形 → 調色一致性 Gate → designated human review。
任何一支片最多一個創意 Look；LUT 不得同時充當 Log/HDR 轉換與風格濾鏡。

## 色彩管理

- 預設交付為 Rec.709 SDR。`visual_master.py analyze` 讀取 primaries、transfer、matrix、range。
- HLG/PQ 先透過 `zscale + tonemap` 正規化，再套 Look。
- 相機 Log 若沒有明確 Input Transform，直接 `BLOCK_UNKNOWN_LOG`，不可猜測。
- 3D LUT 採 17 點日常版或 33 點高品質版，FFmpeg 使用 tetrahedral interpolation。
- 只處理實拍／B-roll／照片，字卡、Logo、字幕、HUD、Tracking 圖形一律後合成。
- 原始素材永不覆寫；獨立套色會產生 `.grade.json`，偵測到既有 sidecar 時預設拒絕重疊。

## 強度與「霧霧的」素材

自適應強度以代表幀的對比、飽和度、平均亮度與高低光剪裁判斷。一般強度約
0.25–0.35，題材上限 0.35–0.42，絕對上限 0.50。低對比／低飽和時只小幅增加，
若高光或黑位已剪裁則自動減弱。系統不做強制高飽和、不把夜景全染藍紫、不把膚色
推橘，也不對每支影片使用同一條電影曲線。

## 題材 Look

| Profile | 用途 | 美術方向 |
|---|---|---|
| `clean_neutral` | 教學、一般內容 | 乾淨自然、輕去霧 |
| `cinematic_warm_soft` | 紀錄、電影敘事 | 暖高光、極淡冷陰影、柔和回捲 |
| `vlog_bright_clean` | 日常 Vlog | 明亮通透、保護天空與膚色 |
| `podcast_skin_neutral` | Podcast、訪談 | 膚色中性、避免髒綠與過飽和 |
| `travel_airy_local` | 旅遊、地方文化 | 通透、保留天空植被與在地色 |
| `food_warm_appetite` | 美食、咖啡 | 暖香與質地，白盤不染黃 |
| `toy_energy_clean` | 玩具、戰鬥陀螺 | 金屬塑膠更清楚，產品色不失真 |
| `ai_cobalt_crisp` | AI、科技 | 中性主畫面，極淡鈷藍冷陰影 |
| `night_neon_controlled` | 夜景、汽車 | 暗部可讀、霓虹與招牌不爆 |

## 美學與 2026 趨勢融合

creator 的 curated creator reference set所提煉出的階層、排版、色彩與主體整合仍是母標準。趨勢雷達只提供
題材路由，不當成固定皮膚：美食／旅遊可強化觸感和聲音細節；訪談／Podcast 強調真實
關係與可辨識日常；玩具 Shorts 可在單一節點使用超現實幽默；旅遊／文化以具體地方
細節取代泛用文化符號。長片只在章節與重點節點使用，Shorts 才能在首幀或 payoff 更大膽。

## 使用

```powershell
python visual_master.py plan --domain food --format short
python visual_master.py analyze "input.mp4"
python visual_master.py build-luts --size 17
python visual_master.py apply "input.mp4" "graded.mp4" --profile vlog_bright_clean
python visual_master.py selftest
```

Shorts 已在每段來源 normalize 後、字幕與動態素材前套色，並輸出
`current_color_report.json`。長片、Vlog、Podcast 在素材整理階段使用相同 `color_system`
與 LUT；成片再由 `grade_gate.py` 驗一致性，最後交給指定人工作最後審查。

## 一手依據

- ACES／OpenColorIO：色彩空間、process space、Look 與 display transform 分層。
- Blackmagic Design：balance first、color management、scopes、shot matching、node order。
- FFmpeg：`zscale`、`tonemap`、`lut3d` 與 tetrahedral interpolation。
- Adobe 2026 Creative Trends：All the Feels、Connectioneering、Surreal Silliness、Local Flavor。

來源清單和刷新日期保存在 `knowledge/design_trend_radar.json`；超過 TTL 才重新研究，
避免每支片重複上網和消耗 Token。
