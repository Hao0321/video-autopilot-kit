# 實驗字體與動態海報：2D／3D 混合構圖

適用於明確要求的品牌 Motion、動態海報、編輯設計式 2D／3D 合成；不是所有影片的配色或效果預設。先讀本卡，再按需讀 [3D 與追蹤前提](three-d-and-subject-fx.md)、[節奏編排](rhythm-scene-templates.md)。本卡是 VA agent 可讀的操作規格，屬 **intent_only** 規劃資料，不是 Editkin 已登錄模組、可執行 v4 plan 或美術認證。

## 視覺目標

把海報的字級、圖形、材質與留白變成有空間關係的動態構圖。主字、3D 主體、局部資訊與線條共同設計，不能先做孤立幾何慢轉，再在上方加一行文字。單純換配色、增加 fps、堆模板或加 Glitch 都不能解決構圖缺乏特色。

- 配色有主次。下表是此方向的起點；跨景變換背景主色、字色、材質與明暗比例，保留共同識別；不用同一比例填滿每景，也不隨機切回螢光色。

  | 起點 | 背景 | 字 | 紙 | 主色 | 輔色 | 主次 |
  |---|---|---|---|---|---|---|
  | paper_cobalt | `#F2F0E9` | `#101114` | `#F2F0E9` | `#174FED` | `#83CCFF` | 紙白底、墨黑字、鈷藍物件或緞帶 |
  | navy_electric | `#070B24` | `#F2F0E9` | `#F2F0E9` | `#2437FF` | `#B7C0D4` | 深色體積、電光藍主體、克制的白與灰 |
  | ice_ink | `#C9E4F5` | `#101114` | `#F2F0E9` | `#123DFF` | `#64738F` | 冷淡底、密實黑字、少量集中的藍 |

- 字體有層級：巨型主字、少量可讀資訊與微型排版。裁切、斜排、字形碎片與疊壓是有意義的構圖；關鍵文案仍有完整可讀窗口。微型字只承載真資訊，不能把 debug 標籤燒成裝飾。
- 表面有差異：紙、霧面、深色體積、條紋／半色調與光邊可按題材混合。參考中的鏡面、柔光或折射若引擎做不到，就記缺口；普通銀灰色塊不能宣稱 chrome／PBR。
- 空間有用途：透視、前後遮擋、物件／相機相對運動或形變至少服務一個視覺動詞，例如穿過、翻轉揭露、包裹或重新組合。3D 主體與 2D 疊層需在同一景同時成立，不能只交替播放純 2D 與純 3D。
- 景與景有不同想法：改變視覺動詞、空間組織、字體版位、鏡頭與材質關係。相鄰兩景只換文案／底色／同款旋轉不算有特色。是否好看由完整動態審查決定，不用「特效數量」打分。

## 每景先填 scene job

依當片語意設計每一景，不能把同一組種子固定連播。交給 prepare 前，每景必須記：

| 欄位 | 要填的內容 |
|---|---|
| `id / purpose / copy` | 唯一 id、觀眾此刻看懂什麼、真實且可讀的文字 |
| `frameRange / activeWindow` | 整數 timeline frame、素材 source window、進場／動作峰值／閱讀／離場的時間 |
| `palette / typography / layout` | 色彩角色與主次、指定字型／字重、16:9 或 9:16 個別排版與完整閱讀區 |
| `world / camera / action` | 真 mesh／2.5D 分級、物件 id、尺寸、材質能力、光線、相機和動作因果 |
| `anchors` | `screen`、`authored_world` 或 `image_track`；對應物件／clip、局部座標、時鐘與證據；未知值保持 null |
| `layers` | 背景 → 世界內後層 → 3D → 附著的 2D → 螢幕前層；各層的 motion item/revision、進退時機及合成方式 |
| `occlusion` | `always_front` 的設計意圖，或真 depth／matte 證據；未具遮罩不能寫「穿到物件後方」 |
| `transition / sound` | 與前後景的形狀、運動或節奏關係；選擇性 Split Flap／Glitch／閃光及音效理由 |
| `evidence / readiness` | source、權利、當次能力、prepare receipt、缺口；未完成欄位使此景停在 planning |

一景內可有快揭露、慣性動作與乾淨閱讀，避免所有圖層同時進／同時停。2D 不必全都追蹤：主標可留在 screen space，局部標記依物件動。要附著的圖文必須使用相同 frame clock、相機與已驗證 anchor；不能靠眼估幾個不同座標假裝跟上。

30 秒預設仍為 8–12 個有內容的景；最新明確要求 15 景時保留 `sceneCountOverride`。不要機械等分去壓縮閱讀；用 source active window 消除各模板頭尾空段。長短片需重新排版與節奏規劃，共用配色不代表裁切同一畫面。

## 追蹤、遮擋與能力分級

1. **`screen`**：固定螢幕座標，不能稱物件追蹤。
2. **`authored_world`**：自製 3D 物件已有逐幀 transform，由同一相機投影已知 local anchor。需 object id、camera id、transform/source identity、實際 projection receipt；這是已知動畫座標綁定，不是影像追蹤或 camera solve。現有 renderer 沒有匯出這個 binding 時，記 `WORLD_ANCHOR_INTEGRATION_REQUIRED`，不能先猜座標當已完成。
3. **`image_track`**：實拍／已渲染影片由 verified clip、起始 frame 和 normalized ROI 進行真正追蹤。結果含 confidence、lost/held、source identity 與時間範圍。失追短 hold 後隱藏，重遮擋要重取可信資料；不得憑補間猜出看不見的軌跡。
4. **camera solve／遮擋**：只有對應 solve、鏡頭資料、depth／逐幀 matte 證據齊全才宣稱。普通 bbox 追蹤不提供相機解算、3D 遮擋或材質照明。沒有可靠證據就改為誠實的前層設計，或暫留規劃缺口。

## VA 實際操作路徑

1. 建立當次 context packet 並讀本卡；原始回饋與參考來源存在專案私有工作區。參考只抽象配色、層級、構圖和動作語法，不直接搬海報、字標或未授權圖片。地區名稱只是風格線索，不能據此認定參考作者國籍。
2. `list_editkin_modules` 查當次文字、場景、overlay；`list_mesh_3d_templates` 查 3D 開放狀態。讀 manifest/input/revision，不能把規劃用的種子名直接填成 `moduleId`／`variantId`。未知／withdrawn 記 `NEW_MOTION_RUNTIME_REQUIRED` 或 `NATIVE_3D_TEMPLATE_REQUIRED`。
3. 現有可用模組用 `prepare_editkin_module` 的真 schema。原創 2D scene/source 用 `prepare_original_motion_scene_2d`／`prepare_original_motion_source`，依當次原創來源契約取得實際收據；不把它們宣稱成通用 3D 合成入口。
4. 真影像追蹤用 `prepare_autopilot_motion_track({projectPath,clipId,initialTime,label,rect:{x,y,width,height}})`。`initialTime` 單位與 clip/source clock 先查當次工具契約，rect 由實際影像驗證，不能留空硬送。此工具只 prepare，不修改專案；把回傳的 `add_motion_track` 精確命令、`tracking_masks` 與對應 design beat 一起綁回 v4。圖文另從 `list_creative_presets` 選追蹤相容的真 preset，再寫受審核的 `add_motion_graphic`；不能假設所有圖文都支援追蹤。world anchor 不冒用此入口。
5. 沒有可用 native family 的已授權研發，仍可用 Editkin 自己的 Motion Library／mesh renderer 做隔離 source test，保留原始可編輯 scene、source pin、font／rights、render receipt。它不會因此變成原生 VA 可編輯模板；不可改寫凍結庫、私自啟用撤回模板，或用別的引擎冒充已整合。
6. 準備結果接同一份 v4 plan：來源、design/inference、圖層、tracking 與效能預算完整 → `audit_autopilot_plan` accepted → `apply_autopilot_plan` 一次 atomic apply → 以 committed revision render。禁止把本卡直接當 plan apply，或手造 accepted receipt。
7. 先做少量不同構圖的實際動態測試，對照同一參考看空間、流暢、附著／遮擋、字體閱讀、材質與每景特色。技術 decode、漂移與幀率另驗。創作者尚未審過就保留 `ART_PENDING_REVIEW`，不批量擴張或進正式預設。

## 學習邊界

景數、60 fps、Split Flap／Glitch、mesh 景與閃光的數量都不等於品質；同一編排只換配色不算修好，多加幾個 3D 景也不能宣稱完成。此方向是有範圍的暫定偏好，實際成片需再次審查。工具測試只證明 VA 能找回規格與識別操作缺口，不能證明新效果已達標。
