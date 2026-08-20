# 追蹤文字與 Challenge Ledger 規格

## Hao motion-review correction — 2026-08-13

- A motion proof must show one complete information arc on the authoritative edit. Do not submit a 9.6-second fragment when the current cut is longer and the payoff/effect interaction remains unseen. For Short-form P0 verification, prefer the full current cut unless the brief explicitly isolates one shot.
- Never add a persistent arena/object lock ring or centre frame merely to make a shot feel more "tracked." It competes with the Beyblade arena and obscures the subject. Default to object-attached type/arrows, edge HUD, brief subject-matte sheen, or no graphic. A centre lock is opt-in only when it communicates a verified target/state and passes a no-occlusion review.
- Contact sheets are QA evidence, not creative deliverables. Do not ask Hao to approve one as if it were another motion asset unless cross-frame consistency is the review target.

這份規格把高能挑戰影片常見的「貼住主體的立體數字」與左上角進度紀錄，落成可編輯、可驗證的系統。提煉的是資訊階層、動態與合成語法；不複製第三方字型檔、Logo、固定版式或成片素材。

## 1. 四層視覺結構

1. **字形**：厚、圓、短筆畫、清楚的內洞；中文用圓體，英文與數字用厚圓 display 字。
2. **立體**：深色粗外框加右下方擠出，不靠廉價單層陰影冒充 3D。
3. **光與材質**：三段式 bloom、上亮下深漸層、內部水平掃描紋與掠光；白價標可取消掃描紋。
4. **動態**：0.30 秒 pop/overshoot/settle，之後 1.2% 呼吸；退場 0.16 秒。動畫只強化落點，不連續抖動。

`tracked_graphics.py` 內建四個可覆寫 profile：

- `neon_value_green`：最高價值、成功、升級。
- `neon_value_cyan`：科技、規格、資訊揭露。
- `price_white`：簡明價標、箭頭 callout。
- `impact_gold`：獎勵、里程碑、勝利。

所有文字在 render 時產生，支援繁中、英文、數字與混排；不能把固定 PNG 當成「支援任何文字」。正式指定為 premium hero 前仍需看 `typography_catalog.jpg` 與真片 contact sheet，由人眼核准。

## 2. Tracking 合約

- 必須有真實來源影片、起始 frame 與人工／偵測器確認的 `initial_bbox`；不得靠語言模型猜座標。
- 預設使用 OpenCV CSRT 逐幀追蹤，再對位置與比例做自適應平滑。
- 標籤可在主體上／下／左／右，會限制在安全邊界內；`pointer: arrow` 才畫箭頭。
- 追蹤失敗時最多 hold 最後可信位置 8 幀並淡出，之後隱藏；不得繼續漂移假裝跟上。
- CSRT 即使回報成功，只要中心單幀跳動、面積／長寬比突變或框體越界超出容許值，一律視為失追；不得用更高跟隨係數追趕錯誤框。
- 高速旋轉、嚴重殘影或多個外觀近似的陀螺不使用箭頭自動追蹤；改成短暫名稱標示、HUD 或 clean hold。手持展示必須用只包住產品的緊框，不能把整隻手一起圈入。
- 貨幣、價格、數量、戰績必須有 `evidence`；沒有證據時 spec gate 直接紅燈。
- `lost_ratio <= 0.12` 才自動標 GREEN；超過即 REVIEW，需重選 bbox、切短追蹤區間或改手動 keyframe。
- 需要字被人物／物件遮住的景深效果時，另供 foreground matte；沒有 matte 時維持前景 overlay，不偽造遮擋。

Tracking 是 `graphic_overlay`，不是 camera move、edit transition 或 graphic transition。

### Telemetry callout（速度／價格／狀態追蹤框）

- `style: telemetry_callout` 時，資訊 panel、折線 connector 與主體 anchor dot 必須由同一個 tracker bbox 計算，禁止三個元件各自漂移。
- panel 可以留在安全區，但 connector 末端必須跟隨主體；主體跨過 panel 時需改 side 或隱藏，不能壓住 proof。
- `116 MPH`、價格、比分、里程等測量值必須在 `evidence` 指向真來源；沒有速度感測、畫面可驗證資訊或使用者明示資料時，只能寫名稱／狀態，不能製造假數字。
- 風格由原創暗玻璃框、細掃描紋、青色核心與克制 RGB 註冊邊組成；色散是介面材質，不准蔓延整段影片。
- 首、中、尾及最快運動點都要抽查：panel 無抖動、connector 不穿主體、anchor 無跳點、追失前已隱藏。

## 3. Challenge Ledger（左上紀錄）

Ledger 是狀態，不是裝飾：

- `current_badge`：只顯示目前物件縮圖＋數值，適合畫面已很滿。
- `ladder`：完整顯示 completed／active／upcoming 階梯；active 放大發光，completed 有完成記號，upcoming 降階。
- `events` 依時間切換 `active_index`，前一項縮小、目前項放大；不靠生成一張新圖假裝更新。
- HUD 名稱依 capsule 可用寬度自動縮字，完整名稱優先；禁止固定字級把尾字裁掉。
- 縮圖應使用當集真物件摳圖；無縮圖時才用原創幾何 icon。
- 固定在左上安全區，不遮人臉、proof、介面與字幕；直式片要另外 reflow，不照搬 16:9 尺寸。

## 4. Spec 範例

```json
{
  "video": "D:/episode/source.mp4",
  "start": 2.0,
  "end": 8.0,
  "tracked_labels": [
    {
      "id": "car-300k",
      "text": "$300,000",
      "profile": "neon_value_green",
      "initial_bbox": [0.40, 0.52, 0.18, 0.22],
      "start": 2.0,
      "end": 8.0,
      "anchor": "top",
      "evidence": "approved script + product source"
    }
  ],
  "hud": {
    "mode": "ladder",
    "active_index": 0,
    "events": [{"time": 4.2, "active_index": 1}],
    "items": [
      {"label": "$1", "thumbnail": "D:/episode/one.png", "evidence": "source"},
      {"label": "$300K", "thumbnail": "D:/episode/three.png", "evidence": "source"}
    ]
  }
}
```

```powershell
python tracked_graphics.py validate spec.json
python tracked_graphics.py render spec.json `
  --output tracked.mp4 `
  --alpha-output tracked-overlay.mov `
  --track-output tracking.json `
  --qa-sheet contact-sheet.jpg
```

輸出包含可交付 MP4、可重用 Alpha MOV、逐幀 bbox／狀態 JSON 與視覺接觸表。

## 5. 自動剪輯路由

只有下列語意才建立此 overlay：明確價格／數量比較、挑戰進度、排行榜、對戰比分、可驗證里程碑。一般逐句字幕、旅遊空鏡、美食質感鏡頭與 proof 畫面不自動加 Ledger。

降級順序：重新選可信 bbox → 縮短追蹤區間 → 人工 keyframe／固定安全位置 → clean hold。不得降級成全螢幕空白模板、無關網格或假轉場。

## 6. 戰鬥陀螺名稱與真偽標示

- 對戰計畫使用結構化 `battle_matchup.left/right.name/authenticity`；不得從標題猜真偽。
- `official` 對 `official`：開場 VS、貼身 Tracking 與左上 HUD 只寫陀螺名稱；禁止再寫「正版」「正版內戰」「正版王牌戰」。
- 名稱優先貼身 Tracking；同一段不得又在底部放一條完全相同的名稱字幕。開場 VS 可在較早時間先交代完整 matchup。
- `official` 對 `counterfeit`：雙方名稱與「正版／盜版」都要清楚，避免觀眾誤會；真偽須來自使用者或可驗證來源。
- `shorts_gate.py` S-T 對有 `battle_matchup` 的計畫 fail-closed；未提供結構化資料時不自行猜測。

## 7. 物件全黑轉彩斜角高光

- 使用 `mask_sheens`；固定分類為 subject-matte overlay，不是 flash／wipe transition。
- 陀螺等近圓產品可用人工確認的 `ellipse`；不規則物件使用 `polygon` 或外部 alpha matte。
- `initial_bbox`、首中尾 keyframe 與 `evidence` 缺一即 fail；光帶不得溢出物件到背景或手部。
- `reveal_mode: black_to_color` 的第一效果幀把 matte 內的物件壓到全黑；斜角 frontier 通過處恢復原始彩色，frontier 上再疊高對比 core＋bloom。不是把整幀降飽和，也不是文字光掃。
- 單次 0.25–0.60 秒、每次展示最多一次；掃光方向要服從物件形狀與鏡頭動勢。
- 手指、臉與背景被 matte 吃入一個像素群都算 review blocker；近圓陀螺仍需逐幀 matte 或人工確認 keyframe，不能拿鬆 bbox 當成完成 roto。
- QA 抽查全黑起點、frontier 正中、完整彩色終點與任何遮擋點。追蹤失穩、物體已過曝、邊緣 halo、遮罩太粗時直接 clean hold。
