# Shorts 字體 + 配色 — niche 對照（2026-06-24 記死；2026-07-02 white-first 鐵則）

> Hao 美食/旅遊/開箱/咖啡廳/甜點 直式 Shorts 的字幕字體 + 配色。
> code 落地：`silent_vlog_maker/shorts_vertical.py` → `COLOR_VARIETY` / `NICHE_PALETTES` / `NICHE_FONTS` / `build_one_short(font=)`。
> ⚠️ **M38 鐵則**：字體**必須有繁體中文**，否則中文豆腐框。下面中文字體都已確認有繁中。

## 🔒 White-first 鐵則（2026-07-02 Hao：「字的顏色太多了，主要是白色，有重點跟重要資訊再用有色字」）

1. **底色一律白 `w`** —— 整行上色／逐重點輪播多色 = 🚫 禁止預設
2. 每支 Short 只用 **2 個非白色**：`palette[0]` = 主強調色（【重點】詞，全支同一色）、`palette[1]` = 資訊色（【重要資訊】：數字/地名/價格/菜名）
3. `NICHE_PALETTES` 語意 = 【候選強調色】不是【輪流全上】；`style_caption()` 預設 level=1（white-first），level 2 多色輪播／level 3 每字爆色 = 僅 Hao 點名才用
4. **交付前跑 `shorts_captions.audit_color_ratio(blocks)`**：有色字符 ≤35%（全支計）、非白色 ≤2 色，任一超標不交
5. 教學長片不在此列 —— 本來就 M68 純白黑框、零彩色

## 🎨 配色 v2（取代舊 iOS 硬色；Hao 回饋「太紅太橘太綠」）

| key | 名稱 | RGB | ASS（BGR）| 取代 |
|---|---|---|---|---|
| `w` | 白（base）| FFFFFF | `&H00FFFFFF&` | — |
| `r` | 珊瑚紅 | FF6B6B | `&H6B6BFF&` | 硬紅 FF3B30 |
| `o` | 杏桃橘 | FFB17A | `&H7AB1FF&` | 硬橘 FF8C00 |
| `y` | 奶油黃 | FFD23F | `&H3FD2FF&` | 硬黃 FFD60A |
| `g` | 薄荷綠 | 3FC9B0 | `&HB0C93F&` | 硬綠 30D158 |
| `b` | 天空藍 | 5AB0FF | `&HFFB05A&` | 新 |
| `p` | 泡泡粉 | FF74A8 | `&HA874FF&` | 新 |
| `v` | 葡萄紫 | A66BFF | `&HFF6BA6&` | 新 |
| `c` | 奶油白 | FFF4E6 | `&HE6F4FF&` | 新（暖白）|

> 全保留厚黑描邊（Outline 10, M96）→ 再亮再可愛也清楚不糊。亮 ≠ 髒。
> ASS = BGR 順序（RGB 反過來）。新增色記得轉 BGR。

### niche → 配色（`NICHE_PALETTES`）
| niche | 色 | 調性 |
|---|---|---|
| 美食 food | r y o g（珊瑚+黃+杏桃+薄荷）| 暖、開胃、活潑 |
| 旅遊 travel | b r y g（天空藍+珊瑚+黃+薄荷）| 清新、明亮 |
| 咖啡廳 cafe | o c v r（杏桃+奶油白+葡萄紫+珊瑚）| 溫暖、文青 |
| 甜點 dessert | p g y v（泡泡粉+薄荷+黃+葡萄紫）| 粉嫩、可愛 |
| 開箱 unboxing | b p y g（天空藍+泡泡粉+黃+薄荷）| 鮮明、有活力 |
| 玩具 toy | p y b g（泡泡粉+黃+天空藍+薄荷）| 收藏感、揭曉感 |
| AI / 教學 ai | y b g v（訊號黃+天空藍+薄荷+紫）| 黑底訊號 UI、乾淨高對比 |
| 遊戲 game | g v y p（酸綠+葡萄紫+黃+泡泡粉）| impact、高能、HUD 感 |
| DIY | o b y g（杏桃+天空藍+黃+薄荷）| 工具／施工標示感 |

## ✍️ 字體（全 Google Fonts・OFL/Apache 免費商用・有繁中）

### 中文（標題字幕用，`NICHE_FONTS`）
| 字體 | 風格 | niche | 連結 |
|---|---|---|---|
| **jf open 粉圓 (Huninn)** | 圓體可愛・台味 | 美食/甜點/開箱 | https://fonts.google.com/specimen/Huninn |
| **LXGW WenKai TC（霞鶩文楷）** | 楷體・手寫感・文青 | 旅遊/咖啡廳/甜點 | https://fonts.google.com/specimen/LXGW+WenKai+TC |
| **Noto Serif TC** | 襯線・精緻質感 | 高質感餐廳/咖啡廳 | https://fonts.google.com/specimen/Noto+Serif+TC |
| **Noto Sans TC**（預設）| 黑體・乾淨百搭 | 通用/科技/開箱 | https://fonts.google.com/specimen/Noto+Sans+TC |

程式映射補充：`toy`→Huninn；`ai/teaching/game/gaming/diy`→Noto Sans TC。
題材不只換字體與顏色：完整黑底白格、斜切框、卡型與鏡頭語法以
[`visual-art-direction-2026.md`](visual-art-direction-2026.md) 為 SoT。

> 粉圓內建 Latin = Varela Round（圓潤可愛），中英混排已 cohesive。

### 英文（純英文字卡 / 大數字用）
| 字體 | 風格 | 連結 |
|---|---|---|
| Fredoka | 圓潤可愛 | https://fonts.google.com/specimen/Fredoka |
| Poppins | 幾何乾淨 | https://fonts.google.com/specimen/Poppins |
| Baloo 2 | 厚實俏皮 | https://fonts.google.com/specimen/Baloo+2 |
| Quicksand | 輕盈圓體 | https://fonts.google.com/specimen/Quicksand |
| Pacifico | 手寫草書 | https://fonts.google.com/specimen/Pacifico |
| Anton | 超粗壓縮（大數字）| https://fonts.google.com/specimen/Anton |

## 🔧 怎麼用（✅ 2026-06-24 已落地 + 真跑驗證）
- **字體放哪**：`assets/fonts/`（各字體 Google 解壓的子夾）；要用的字重複製到 **`assets/fonts/_active/`**（扁平夾，libass 指這裡）。**不必裝 Windows**。
- **family name（libass 比對用，實測值，不能猜）**：
  - 粉圓 → **`Huninn`**（檔 Huninn-Regular.ttf；**不是**「jf open 粉圓」）
  - 文楷 → **`LXGW WenKai TC`** ✅ 實測渲染正確（楷書筆觸）
  - Noto Serif TC → **`Noto Serif TC`**；預設 → **`Noto Sans TC`**
  - 英文卡：`Anton` / `Fredoka` / `Quicksand` / `Pacifico`（**無繁中，只給純英文/數字**）
- **code 機制**：`FONTS_DIR`(指 `_active`) + `_ass_filter()` 把 fontsdir 算成**相對 workdir 路徑**塞進 ass filter
  —— ⚠️ **不能用絕對路徑**：Windows `D:` 冒號會被 filtergraph 當選項分隔，`\\:` 跳脫 ffmpeg 不吃；
  相對路徑沒冒號最穩（cwd 已在 workdir）。跨碟 fallback：複製到 workdir/_fonts。
- **呼叫**：`build_one_short(..., font="LXGW WenKai TC")`；niche 自動套 = `font=NICHE_FONTS[niche]` + 色用 `NICHE_PALETTES[niche]`（同 BGM zero-config）。
- **公開 kit 同步**：配色 v2 + 字體機制屬通用改善（無 PII），可進 video-autopilot-kit 下個 release（公開版仍舊配色 + 無 font 參數，等 Hao go 才推）。

承 M96（直式 Shorts pipeline）/ M38（字體無 glyph→豆腐框）/ M99(選曲) 家族 — 同管「Shorts 視覺品味」。
