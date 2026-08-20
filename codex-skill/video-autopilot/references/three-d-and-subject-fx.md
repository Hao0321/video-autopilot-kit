# 3D 與主體遮罩斜角閃光系統

## 先分清能力

- `depth_cards`、`tracked_billboard` 是 2.5D。
- `product_turntable`、`data_space`、`extruded_type` 是真 3D，但分別需要 mesh／資料／授權字型。
- `camera_solved_composite` 是實拍＋CG 合成，需要相機解算、鏡頭資料、clean plate、shadow catcher 與光線參考。
- 缺前提時 `three_d_system.py` 會輸出 `DOWNGRADED`，不得以平面縮放冒充真 3D。

## 主體全黑轉彩斜角閃光的正確定義

這是附著在「陀螺、車、產品或其他主體」上的材質高光，不是轉場：

1. 先由追蹤框／人工 keyframes 決定主體位置。
2. 圓形陀螺可用 ellipse；車、人物與不規則物件只准 verified polygon 或 alpha matte。
3. `black_to_color` 先在 local matte 內建立不透明黑層；斜向 frontier 通過後才恢復原始彩色，frontier 上包含 core band 與較弱 secondary band。
4. 黑層、彩色恢復與光帶共用同一逐幀 alpha；任何部分都不能超出 matte。opacity、band width、glow 依 `battle_top / vehicle_paint / glass / plastic_product / generic_product` 材質 profile 決定。
5. 時長建議 0.25–0.60 秒，硬上限 0.8 秒；只用於 hero reveal、勝負／價值 payoff 或重要物件第一次被看清。
6. 失追按 hold-then-hide；禁止猜路徑、禁止漏到背景、禁止全畫面閃白。

### alpha matte

`mask_sheens[].shape="alpha"` 時必須提供 `matte_path`。全畫面 alpha 會依 tracked bbox 裁切；local alpha 會縮放至 bbox。只讀 alpha，不讀 matte 圖顏色，避免藏入未知影像。

### 不規則主體

當 `subject_class` 是 `vehicle / person / irregular`，ellipse／rectangle 會被 validator 拒絕。若車身被前景、人或車門遮擋，應以分段 matte 或短 shot 使用，不能讓高光穿透遮擋物。

## 3D 路由

| route | 前提 | 主要用途 | 缺前提降級 |
|---|---|---|---|
| `depth_cards` | segmented layers | AI 文件、旅遊照片、證據叢集 | clean 2D evidence |
| `tracked_billboard` | planar track、surface reference | 平面上的標籤／證據 | tracked 2D overlay |
| `product_turntable` | mesh、材質、光線參考 | 陀螺、產品、車 | verified multiview 2D |
| `camera_solved_composite` | solve、lens、plate、shadow、light | CG 進實拍運鏡 | tracked billboard |
| `data_space` | 真資料、場景尺度 | 價值階梯、時間線、系統關係 | depth cards |
| `extruded_type` | 授權字型、核准文案 | 選擇性巨字／數字 | premium 2D type |

## 合成 QA

- 實拍素材先完成輸入轉換與一級調色，CG 再匹配黑白位與主光方向。
- 使用 shadow catcher／接觸陰影，不得漂浮；物件跨越真人或產品時必須有 occlusion matte。
- motion blur、景深、鏡頭畸變與顆粒要跟 plate 一致。
- 檢查起始、峰值、結束三幀；起始需證明物件全黑且背景未變，峰值需證明斜角 frontier 對比足夠，結束需恢復原始彩色。另查 edge leak、手指／臉污染、drift、穿幫與主體裁切。
- Blender 官方把 Shadow Catcher 定義為只接收陰影、用於簡化 CGI 與實拍合成；相機／物件追蹤必須先解算與定向。這些是本系統的能力前提，不是可跳過的裝飾步驟。
