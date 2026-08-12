# Hao Video Autopilot Architecture v6.1

v6.1 把設計、模板編譯、電影工藝與動態合成整理成獨立平面。六個平面共用同一份 manifest、證據與 fail-closed QA；任何影片都不能因換片型而繞過題材語法、真實性或 Hao 審片。

## 六平面

| 平面 | 責任 | 核心輸出 |
|---|---|---|
| Control | 唯一入口、路徑、同步、發佈與健康檢查 | manifest、doctor、release report |
| Decision | 片型／題材／記憶／策略／Token 路由 | current context、規則與決策證據 |
| Design | 33 圖 DNA、元件模板、影視颶風／MrBeast 工藝、Tracking／Mask、2.5D／3D | design recipe、template program、craft/effect plan |
| Asset | 來源、授權、B-roll、音樂、SFX、motion 與可重用資產 | current asset plan、license audit |
| Execution | 長短片 build、字幕、合成、調色、輸出 | current.mp4、執行報告 |
| Evidence | 技術 QA、負面案例、人工審片、成效回填 | QUALITY_95、review、learning record |

## 主流程

```text
request
  -> Control discovers canonical root
  -> Decision compiles a bounded context packet
  -> Design routes domain + format + semantic role
       -> design_system_v6 compiles aesthetic DNA
       -> template_compiler assembles reusable components and reflows 9:16 / 16:9
       -> mediastorm_craft evidence-gates camera, cuts, sound, colour and VFX
       -> MrBeast / tracking / 3D systems enrich only evidence-ready events
  -> Asset resolves licensed footage, sound and reusable material
  -> Execution renders the approved plan
  -> Evidence blocks regressions and waits for Hao timestamp review
  -> Publish / learn / release
```

## Design plane 的六條硬界線

1. `design_system_v6.py` 只使用 33 張參考圖的匿名抽象 DNA，不打包原圖、不複製單張版式。
2. `template_compiler.py` 快取結構而非成片：不存文案、媒體或私人路徑；同片鎖定一套視覺語言、構圖依角色輪替，跨片依疲勞歷史輪替。
3. `mediastorm_craft.py` 以 clean cut 為預設；match／whip／遮擋／speed ramp／J-L cut 缺 shot-pair 或音訊證據便降級，不能把效果名稱當完成證據。
4. `mrbeast_editing_system.py` 把效果視為有資訊功能與前置證據的事件；沒有 evidence 就 clean hold。
5. `tracked_graphics.py` 的物件斜角閃光必須在追蹤 matte 內合成；它不是全畫面閃光，也不是轉場。
6. `three_d_system.py` 明確區分 2D、2.5D、true 3D 與 camera-solved composite；缺 mesh、camera solve、clean plate、光影資料時必須降級。

## 模板效率

- 結構計畫以內容安全的 hash 快取；文字、圖像、影片在渲染時才注入。
- 9:16 與 16:9 共用 design token 與元件，不共用硬裁版面。
- 一支影片鎖定 program style；角色切換只改 layout／component emphasis，防止風格跳動。
- `HOOK`、`LOWER THIRD`、`SHAPE / PLAY` 等內部標籤只有 `debug_labels=true` 才可出現。
- 真素材足夠時 template 只能當 overlay／構圖指令，不得自動插入全螢幕空卡。

## 相容入口

`AUTOPILOT_4LAYER.md` 保留舊連結，但架構真相以本檔與 `AUTOPILOT_MANIFEST.json` 為準。舊指令繼續可用；新版本只新增能力與 gate，不刪使用者素材或未知檔案。
