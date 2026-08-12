# MrBeast × 影視颶風跨長短片效果能力對等

## 1. 必須同時套用

- 每支 YouTube 長片、Shorts 與 Reels 都必須評 `MrBeast 資訊能量` 與 `影視颶風電影工藝`。
- 加權可依片型不同，但任一軸不得歸零或被略過。
- MrBeast 檢查承諾、stakes、狀態可視化、焦點、節奏波與 payoff；影視颶風檢查拍攝動機、連續性、聲畫、色彩、光影、空間與克制。
- 強度與呈現依題材路由，禁止把兩個頻道變成每支片相同的皮膚。

## 2. `100%` 的可驗證定義

`100%` 只能用於「指定效果在指定參考版本與指定素材上的能力對等」，不代表逐幀照抄、不限素材的萬能複製，也不代表可搬用對方的 Logo、專屬設計、音樂或受保護資產。必須同時具備：

1. 真實參考影片 URL、版本與時間碼。
2. 效果分類：camera move、edit transition、graphic transition、overlay、composite、colour 或 sound。
3. 原始素材、尺寸、幀率、色彩空間、mask／track／3D／音訊需求。
4. 能力狀態、輸出檔與方法版本。
5. 首／中／尾幀、參考對照、邊緣／漂移／遮擋／爆光／音畫 QA。
6. Hao 審片確認。

缺任一項只能說「可能可做」、「已實作未驗證」或「需人工 VFX」，不得宣稱 100%。

## 3. 效果註冊 schema

```json
{
  "effect_id": "subject_mask_diagonal_sheen",
  "benchmark": "mrbeast",
  "formats": ["shorts", "longform"],
  "category": "composite_overlay",
  "status": "VERIFIED_AUTO",
  "method_version": "tracked_graphics.mask_sheen@1",
  "requirements": ["timecode", "verified_bbox_or_matte", "luma_headroom"],
  "limitations": ["irregular silhouette needs MANUAL_VFX"],
  "evidence": ["selftest", "rendered_output", "first_mid_last_frames"],
  "reviewed_by": "Hao"
}
```

| 狀態 | 含義 |
|---|---|
| `VERIFIED_AUTO` | 自動路徑已有真片、輸出、QA 與 Hao 審片 |
| `VERIFIED_MANUAL` | 可完成，但必須逐幀關鍵幀／Roto／3D／混音處理 |
| `IMPLEMENTED_UNVERIFIED` | 已有實作，但未完成真片對照與 Hao 審片 |
| `RESEARCH_REQUIRED` | 參考、分類或技法尚不足 |
| `MISSING_INPUT` | 缺原始鏡頭、多機位、clean plate、depth、track marker 或音訊 stem |
| `RIGHTS_BLOCKED` | 需搬用受保護資產才能重現；改做 Hao 原創等價語法 |
| `UNSUPPORTED` | 現有工具鏈無法達到可交付品質 |

## 4. 現有能力矩陣

| 效果家族 | 目前狀態 | 默認執行 |
|---|---|---|
| 中英數字追蹤字牌、發光數字、左上挑戰記錄、狀態 HUD | `IMPLEMENTED_UNVERIFIED` | 關鍵幀／限定 CSRT，真值證據，失追隱藏 |
| 圓形／矩形／多邊形 matte 物件斜角閃光 | `IMPLEMENTED_UNVERIFIED` | `mask_sheen`；不規則邊緣降級人工 Roto |
| 價值階梯、比例比較、計數器、美元噴發／飄落 | `RESEARCH_REQUIRED` | 值與物件真實對齊；美元只是 overlay，不是轉場 |
| 物件前後遮擋字、不規則 Roto、planar／perspective tracking | `VERIFIED_MANUAL` | 首中尾關鍵幀、matte leakage QA |
| whip pan、match-on-action、occlusion cut、速度連接 | `VERIFIED_MANUAL` | 必須有兩顆真 shot、方向與剪點證據 |
| 2.5D depth cards／tracked billboard | `IMPLEMENTED_UNVERIFIED` | `three_d_system.py` 路由並明確標 2.5D；缺 layer／planar track 就降級 clean 2D |
| product turntable／extruded type | `IMPLEMENTED_UNVERIFIED` | mesh、材質、燈光或 licensed font 齊全才輸出 Blender job；仍需真 render 與 Hao 審片 |
| camera solve、3D 視差、CG 場景擴建、流體／破壞模擬 | `MISSING_INPUT` | 需鏡頭資訊、clean plate、shadow plane、3D 資產與 renderer；不用 2D 貼片假裝 |
| 影視颶風級拍攝運鏡、燈光、鏡頭、空間與現場聲 | `MISSING_INPUT` | 拍前鏡頭設計／shot list／器材／收音。後製不能補回未拍的鏡頭 |
| 影視颶風級 J/L-cut、音橋、match cut、調色、shot matching、能量波 | `VERIFIED_MANUAL` | 使用真素材、scope、多軌音訊與人工 fine cut |

`IMPLEMENTED_UNVERIFIED` 是刻意的誠實狀態：代碼成功不等於已與目標影片 100% 對等。

## 5. 持續學習流程

1. 只收官方頻道或可驗證原始版本，記錄 URL、發布日期與時間碼。
2. 將新手法分成資訊功能、拍攝、剪輯、motion design、VFX、聲音、調色與包裝。
3. 去重後才加入效果註冊；同技法不因不同影片重複寫入記憶。
4. 先做最小真片 prototype，再做參考對照與壓力測試。
5. 通過技術 QA 不自動晉級；Hao 審片後才能變成 `VERIFIED_AUTO` 或 `VERIFIED_MANUAL`。
6. 每 90 天重溫新作品；只更新新增或改變技法，不重載全部影片。

## 6. 交付 gate

- 計畫階段分別列出兩個 benchmark 如何體現。
- 成片各自需有時間碼證據，不能只寫「參考 MrBeast／影視颶風」。
- 使用效果必須源自註冊已有能力；缺資產時在拍前補拍或轉人工 VFX，不得以廉價替代品冒充。
- 沒有視覺事件就留 clean hold；「效果全部可做」不代表「每支全部要用」。
- 只有取得 Hao 審片與對照證據的單一效果，才能宣稱已達功能對等。
