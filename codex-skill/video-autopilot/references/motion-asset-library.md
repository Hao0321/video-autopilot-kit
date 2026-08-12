# Hao Motion Asset Library

> 24 支 1080p／30fps 原創動態素材：12 種功能 × landscape／portrait。
> 視覺語言＝Hao Signal Grid：黑底白格、都市拼貼、斜切、halftone、訊號線與少量題材色；不複製任何遊戲角色、Logo 或 UI 資產。

另有可獨立開源的 `community/hao-motion-kit/`：18 題材 × 背景／字卡底／Overlay／轉場 × 橫直式＝144 支。自動 selector 會優先挑「題材完全相符」的社群包素材，再退回通用包。

## 唯一入口

- Manifest：`assets/broll/motion/manifest.json`
- 題材 Manifest：`community/hao-motion-kit/manifest.json`
- 社群包總覽：`community/hao-motion-kit/showreel.mp4`
- 社群包預覽：`community/hao-motion-kit/preview.jpg`
- 預覽：`assets/broll/motion/hao_motion_pack_preview.jpg`
- 動態總覽：`assets/broll/motion/hao_motion_pack_showreel.mp4`（12 類各 1.2 秒）
- AI 視覺母版：`assets/broll/generated/_sources/hao_urban_collage_master_v1.png`
- 自動選片：`motion_asset_pack.choose_asset(role, aspect, energy, domain, exclude=())`
- Cinematic Wave 已自動寫入：`visual_plan.json → motion_assets.cues`
- Shorts renderer 已實際套用 overlay／transition；background 僅在沒有更好 footage 時人工或 pipeline 明確啟用。

## 12 種素材

| 類型 | ID | 主要用途 |
|---|---|---|
| Background | `urban_collage_signal` | Hook、章節字卡、講解空檔 |
| Background | `perspective_grid_rush` | build-up、速度感、payoff 前 |
| Background | `halftone_orbit` | 數據、資訊卡、呼吸段 |
| Background | `signal_blueprint` | AI 教學、流程、商業圖解 |
| Overlay | `focus_hud` | 聚焦產品、數字、操作區 |
| Overlay | `speed_streaks` | 動作、旅遊移動、遊戲、揭曉 |
| Overlay | `scan_sweep` | AI 介面、規格、分析與 proof |
| Overlay | `kinetic_marks` | 字幕段的邊緣節奏設計 |
| Transition | `diagonal_slash` | 高能章節切換 |
| Transition | `grid_shutter` | 模組、列表、步驟切換 |
| Transition | `signal_glitch` | 錯誤／反轉；全片最多一次 |
| Transition | `paper_flash` | 美食、旅遊、開箱的輕快 reveal |

## 調用

```python
from motion_asset_pack import choose_asset, plan_asset_cues

overlay = choose_asset("overlay", aspect="portrait", energy=.82, domain="food")
# overlay["path"] / overlay["blend_mode"] / overlay["usage"]
# 會優先回傳 food_overlay，而不是通用 speed_streaks。
```

```powershell
python motion_asset_pack.py pick --role overlay --aspect portrait --energy 0.82 --domain food
python motion_asset_pack.py build --aspect all
```

## 使用鐵則

1. 真實 footage、產品、人物、proof 永遠優先；Background 只補沒有更好畫面的段落。
2. Overlay 用 Screen，opacity 建議 20–55%，不可壓字幕、臉、產品或證據。
3. 一支短片 overlay 最多 2 顆、transition 最多 2 顆；高能效果後留乾淨鏡頭。
4. `signal_glitch` 全片最多一次；同素材不可連續使用。
5. 出場點由語意轉折與 Cinematic Wave 決定，禁止固定每 N 秒塞效果。
6. AI 母版不做整張 KenBurns；只動畫化格線、掃描、HUD、色塊等設計圖層。

## 重新生成

`asset_forge.py` 已串接 `build_motion_pack()`；單獨重建本包用：

```powershell
python motion_asset_pack.py build --aspect all
```
