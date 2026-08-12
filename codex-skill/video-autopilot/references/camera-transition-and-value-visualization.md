# MrBeast 類價值段落：運鏡、替換、剪點與 Overlay 分層

> 執行入口：`camera_transition_director.py` 的 `plan_shot_dynamics_system()`；美元粒子由
> `community/hao-motion-kit/money_burst_assets.py` 產生。檔名為相容舊呼叫保留，輸出欄位已改為
> `visual_director.shot_dynamics_system`。

## 1. 先修正最重要的分類

**美元噴發不是轉場。** 它是 `particle_overlay`，負責把抽象金額變成可見的衝擊與景深。只有畫面中真的
存在兩顆 shot、真的在前景遮擋期間剪掉，才能另外把那個剪點稱為 `occlusion_cut`。粒子飛過鏡頭、畫面
變模糊、閃白，都不能自己證明有轉場。

本系統固定分五層：

| 層 | 定義 | 例子 |
|---|---|---|
| `camera_move` | 同一 shot／同一合成空間內視點或尺度移動；沒有剪點 | 快速拉遠、推近、parallax |
| `edit_transition` | 兩顆真實 shot 間確實存在剪點 | clean cut、whip-pan cut、match-scale cut、occlusion cut |
| `graphic_transition` | 同一合成畫面裡物件或圖層被替換 | `whip_object_swap` |
| `graphic_overlay` | 附著在畫面或物件上的資訊 | 追蹤金額、標籤、箭頭 |
| `particle/impact_overlay` | 增加衝擊、材質或物理感 | 美元、紙屑、極短 impact flash |

## 2. 官方片段逐幀稽核

針對 `1 美元 vs 10 億美元的遊艇` 官方片段逐幀檢查：

1. **約 0:00.45–0:01.10**：人物站在停機坪，鏡頭高速拉遠並帶速度模糊，直接揭露完整金色遊輪。
   這是 `speed_ramped_pullback_reveal`，不是轉場。`$1 BILLION` 和美元在全貌開始落定後才進場。
2. **約 0:58.95–0:59.45**：`$50 MILLION` 物件向左甩出，峰值方向模糊後 `$300 MILLION` 從右側
   接進來。從成片可確認的是 `whip_object_swap`；若工程檔證明兩顆真 shot 在模糊峰值剪接，才升格叫
   `whip_pan_cut`。
3. **約 1:00.15–1:00.80**：從 `$300 MILLION` 連續快速拉遠，露出 `$50M/$25M/$10M/$1B`
   全部對象及貼身標籤。這是 `comparison_pullback`，不是逐項亂切。
4. **約 1:00.80 之後**：總覽落定後再出 `$1 BILLION` 美元粒子與極短曝光衝擊。這是 payoff overlay，
   不是把錢當 wipe。

## 3. 正確的 value ladder 配方

三項以上的價值比較固定走：

1. `hero_pullback_reveal`：先用近→遠尺度變化兌現最大承諾；來源沒有廣角餘量時，必須使用已核准的
   2.5D／3D 合成，否則回退 clean cut。
2. `directional_whip_object_swaps`：中間比較物件保持尺寸、重心、基準線和甩動方向一致；物件替換屬
   graphic transition，不得自動謊稱有 shot cut。
3. `comparison_pullback`：最後一個比較物件留在共享合成空間，快速拉遠讓全部對象同框；標籤必須跟物件
   綁定。
4. `impact_overlays`：畫面落定後才進短 flash、美元或紙屑；效果之後要留乾淨可讀畫面。

## 4. 固定語法與證據要求

| 語法 | 分層 | 成立條件 | 不成立時 |
|---|---|---|---|
| `speed_ramped_pullback_reveal` | camera move | 真實 wide plate 或核准合成 | clean cut 到 wide |
| `whip_object_swap` | graphic transition | 同方向、近似尺寸、同錨點 | clean replacement |
| `comparison_pullback` | camera move | 所有物件已在共享 2.5D/3D 空間 | 乾淨比較表 |
| `tracked_value_label` | graphic overlay | 標籤跟隨物件位置和比例 | 靜態但貼近物件 |
| `whip_pan_cut` | edit transition | 兩顆 shot、同方向、剪在最大模糊 | clean cut |
| `match_scale_cut` | edit transition | 兩顆 shot 的尺寸、重心、視線匹配 | clean cut |
| `occlusion_cut` | edit transition | 真前景遮擋 ≥70%，剪點確實藏在遮擋中 | 不標 transition |
| `usd_value_particles` | particle overlay | 明確美元語意；價值落點後出現 | 關閉 |

程式碼、表格、設定與 proof 預設 clean cut。強運鏡後至少一顆乾淨鏡頭；長片一般約 15 秒、Shorts 約
6 秒才安排一個強結構動作，價值階梯本身視為一個連續 cluster。

## 5. 美元粒子資產

- 母檔：`assets/money_burst/imagegen/usd-100-front-back-alpha-v1.png`，包含可辨識美元正反面。
- 輸出：QuickTime Animation `qtrle/ARGB` 真透明，不用黑底／screen 冒充 Alpha。
- `hero`：由金額字與主體附近爆發，前中後三層、翻面、拋物線、近景鈔票。
- `celebration`：由下方噴起，適合獎金、達標與結果。
- `foreground_sweep`：近鏡鈔票橫跨畫面增加景深；**資產分類仍是 overlay，不是 transition**。
- 只有 `$`、美元／美金、million／billion dollars 等明確美元語意才自動使用；其他幣別不能錯配。
- 不同用途覆寫穩定 `{aspect}_{profile}` 路徑，不建立 v2／v3。

```powershell
python community/hao-motion-kit/money_burst_assets.py render --aspect landscape --profile hero
python community/hao-motion-kit/money_burst_assets.py render --aspect portrait --profile foreground_sweep
```

## 6. 美術權限

以下都是可用選項，不是禁令：原創品牌字型感、Logo／徽章、粗描邊、卡通貼紙、刻意廉價綜藝感、金屬／
玻璃／發光／3D 字。要依題材與段落層級選擇。唯一固定邊界是不得未授權散布第三方 Logo 檔、品牌字型檔、
影片、角色與固定版式資產。

## 7. QA

1. 每個事件是否先標明 layer？沒有 layer 不可交付。
2. `particle_overlay.is_transition` 是否固定為 `false`？
3. 若寫了 `edit_transition`，能否指出兩顆來源 shot 與實際剪點？
4. whip 前後方向、尺寸、重心與物件錨點是否一致？
5. 拉遠總覽後，標籤是否貼近正確物件且不交叉？
6. 美元是否在金額落點後才出現，且幣別真的為美元？
7. proof、程式碼、UI、字幕與產品是否保持可讀？
