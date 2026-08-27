# MrBeast 製作源頭拆解：剪輯、Graphics、Tracking、3D 與 VFX

## 導航

- P0 校準／常見誤判／製作分層
- Tracking／字體／物件斜角閃光
- 素材工坊／能力分級／效果驗收／研究證據

## Public P0 calibration

- Real footage remains primary; editable type, tracked arrows, subject-matte sheen and edge HUD are optional information layers.
- A proof must show one complete information arc on the authoritative cut.
- Centre locks are opt-in, brief and blocked when they obscure action.
- Contact sheets are QA evidence, not creative deliverables.
- PUBLIC_FIXTURE contains no private rating, date, approval or rejected project result.

## 1. 先修正最常見的誤判

- **高能量不等於一直快剪。** MrBeast 資深剪輯 Nolan Ritter 的直接說法是先清楚建立一個概念、一個情緒與規則，讓觀眾看懂尺度，之後才加混亂與刺激，最後落在記得住的 payoff。
- **主頻大量使用的是 Graphics，不等於每一個都是 VFX。** 價格字、箭頭、狀態 HUD、光掃、背景去飽和、數位推鏡，多數是編輯端的 After Effects／motion graphics composite。真正 set extension、CG 物件、camera solve、crowd/dust simulation 才進 3D／VFX。
- **成品 PNG 不是可重用系統。** 正確庫存單位是可改字 Rig、材質、粒子 emitter、UI shell、track handoff、Blender scene、SFX family。文字內容、追蹤、遮罩、光線與合成要依鏡頭重做。
- **轉場不是抽象動畫。** Yacht 的比較段落是實際 whip／快速拉遠、物件替換與 motion blur cover；美元落下是 payoff overlay；物件斜角閃光是 matte 內的 light sweep，兩者都不是轉場。

## 2. 逐層源頭判斷

| 看見的結果 | 真正源頭 | 可以預製 | 必須逐鏡完成 |
|---|---|---|---|
| 白色巨型價格字 | editable motion-graphics type rig | CJK/Latin/數字字型 fallback、深色 extrusion、pop-settle 曲線 | 文案、位置、透視、節奏 |
| 綠色發光數字＋掃描紋 | type material＋composite | emissive/bloom/scanline 材質 | 背景亮度、強度、是否 tracking |
| 箭頭跟著車或陀螺 | point/object track＋vector rig | 單色簡約箭頭、anchor contract | track、修正、遮擋、顯示區間 |
| 左上角紀錄／價值階梯 | state-driven HUD | shell、state component、thumbnail slot | 真實狀態、縮圖權利、更新時間 |
| 物件斜角閃白 | subject matte＋track＋light sweep | HDR light plate、材質 profile、composite nodes | roto、track、edge、motion blur、grain |
| 主體清楚、背景糊／退色 | roto focus isolation | blur/desat/highlight profile | 人物或物件遮罩、頭髮邊緣、shot match |
| 美元噴出／飄落 | particle graphics＋occlusion | 合規美元粒子、3-depth emitter、SFX | 發射方向、密度、前景遮擋、調色 |
| 價值比較運鏡 | camera/editorial transition | shot-pair checklist | 真實運鏡、方向、尺度、剪點、聲橋 |
| 地面光圈／世界座標標籤 | planar/object tracking | ring/label rig | surface track、透視、鏡頭畸變、遮擋 |
| 有真正厚度、陰影、反射的字／物 | 3D render | Blender 程序化場景、材質、render passes | mesh/font、light、camera、render、composite |
| CG 物件進入移動實拍 | camera-solved VFX | handoff schema、shadow catcher、multipass template | lens、solve、clean plate、geometry、light、roto |
| 沙塵、煙、群眾、破壞 | simulation VFX | 簡單 2D plate 或 simulation job schema | collider、尺度、物理 sim、camera、light、composite |
| 「很爽」的節奏 | editorial＋sound design | event taxonomy、BPM map、SFX family | 對白、音樂 phrase、build／vacuum／hit |

## 3. 三種 Tracking 不可混叫

1. **Point／object tracking**：價格、箭頭跟隨車、陀螺或人物。適合平移、縮放與有限旋轉；失去信心就隱藏或人工 keyframe，不准假追。
2. **Planar tracking**：標籤貼在螢幕、車門、地面等平面，需要 skew／perspective。不是只追 bbox 中心。
3. **3D camera tracking**：CG 物件對場景產生正確 parallax、接地與陰影。必須有 lens、camera solve、ground/shadow plane；缺任何一項就降級 2D／2.5D。

若圖形會被真人、車身或陀螺遮住，Tracking 之外還需要 **Roto／occlusion matte**。Tracking 解位置，Roto 解前後關係，兩者不能互相代替。

## 4. 字體不是找一個字型名稱就完成

MrBeast 價值字的完成感至少由五層組成：

1. 粗、圓、窄幅適中的 display glyph；
2. 可支援中文、英文與數字的 fallback stack；
3. 深色 offset/extrusion，而非只有廉價 uniform stroke；
4. 輕微傾斜、perspective 或逐字的不完全整齊；
5. 進場的 overshoot、settle、motion blur、聲音 hit；綠色版本另加 sharp core、兩級 bloom 與細 scanline。

因此素材工坊要做的是「可改字 Type Rig＋Material＋Animation」，不是生一張寫死 `$300 MILLION` 的圖片。

## 5. 物件斜角閃光的正確節點順序

`plate → subject track → alpha/polygon matte → animated diagonal luma band → material-aware blend → motion blur → edge/grain match → composite`

- 光只存在主體 matte 內；車漆、金屬陀螺、塑膠與玻璃各有不同寬度、bloom 和 blend。
- 主體被手或其他物件遮擋時要做 holdout matte。
- 無可靠 matte／track 時直接用 clean hero hold，不以全畫面白閃替代。

## 6. 素材工坊優先順序

### P0：先做可編輯 Rig（不需 Image 生圖）

- `type_rig_white_depth_v1`
- `type_material_lime_emissive_v1`
- `challenge_ledger_shell_v1`
- `value_ladder_component_v1`
- `vector_arrow_rig_mono_v1`
- `tracked_ground_ring_rig_v1`
- `light_sweep_linear_hdr_v1`
- `subject_sheen_material_profiles_v1`

### P1：真實 VFX plate／粒子

- `usd_note_particle_set_v1`＋`usd_money_emitter_v1`
- realistic dust／smoke／spark plates，黑底、白底或 alpha，先做 motion test 再批准整批
- cash flutter、UI tick、impact、riser、vacuum、mechanical SFX families（保留授權來源）

### P2：真正 3D 原始檔

- Blender bevelled/extruded CJK-Latin-numeric type scene
- product／metal／paint／plastic／glass material pack
- shadow catcher、turntable、single dolly、camera-solve handoff
- RGBA、shadow、normal/depth utility passes，不只輸出一張扁平 PNG

### P3：逐鏡高成本作業

- Roto focus isolation、複雜 occlusion、camera solve、set extension、CG replacement、crowd/dust/destruction simulation。
- 必須先鎖定 editorial animatic／wireframe；後期團隊也明確先 green-light graphic，避免把大量 3D/VFX 做錯方向。

## 7. 能力誠實分級

- `VERIFIED_AUTO`：已在真素材渲染、逐幀 QA 且 creator 通過。
- `AUTO_WITH_REVIEW`：可以自動，但 track／matte／畫面整合需要人工驗證。
- `IMPLEMENTED_UNVERIFIED`：程式或 recipe 已有，尚未完成代表鏡頭驗證。
- `SHOT_SPECIFIC_MANUAL`：本質上依鏡頭，不能以素材庫冒充完成。
- `EXTERNAL_3D_VFX`：需 Blender／Houdini／AE／Nuke 等專門管線。

## 8. 每個效果的驗收不是「有出現」

- Tracking：漂移、抖動、失鎖隱藏、遮擋。
- Roto：邊緣 chatter、halo、髮絲／透明物、holdout。
- Composite：black/white level、grain、motion blur、lens distortion、色差。
- 3D：parallax、接地、陰影方向／軟硬、反射、DOF。
- Type：中英數 glyph、邊界、safe area、核心與 bloom 的清晰度。
- Editorial：效果是否對應 promise／state／locate／proof／payoff，前後是否有 contrast gap。
- Sound：build、抽空、hit 是否服務敘事，不准每刀 whoosh。

## 9. 研究證據

- 官方逐幀樣本：[`$1 vs $100,000,000 Car!`](https://www.youtube.com/watch?v=KrLj6nc516A)、[`$1 vs $1,000,000,000 Yacht!`](https://www.youtube.com/watch?v=48h57PspBec)、[`$1 vs $1,000,000,000 Futuristic Tech!`](https://www.youtube.com/watch?v=pAnGwRiQ4-4)。
- 後期團隊直接訪談：[`Art of the Cut: Beast Games`](https://borisfx.com/blog/aotc/art-of-the-cut-beast-games/)；其中明確談到 clarity/stimulation、After Effects comps、light sweeps、Roto Brush、程序化 3D、聲音按 BPM 與 VFX handoff。
- 授權幕後：[`MrBeast Breaks Down the VFX Behind Beast Games`](https://www.youtube.com/watch?v=xLKpLgh2Kd4)。

任何未被 A/B 證據支持的推論只能標 `C`，不得寫成 MrBeast 團隊的確定做法。
