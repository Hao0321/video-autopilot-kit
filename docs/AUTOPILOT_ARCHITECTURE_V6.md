# Hao Video Autopilot Architecture v6.0

v6 把設計與動態合成從散落規則升格成獨立平面。六個平面共用同一份 manifest、同一組證據與 fail-closed QA；任何影片都不能因換片型而繞過設計、真實性或 Hao 審片。

## 六平面

| 平面 | 責任 | 核心輸出 |
|---|---|---|
| Control | 唯一入口、路徑、同步、發佈與健康檢查 | manifest、doctor、release report |
| Decision | 片型／題材／記憶／策略／Token 路由 | current context、規則與決策證據 |
| Design | 33 圖 DNA、美感路由、資訊動態、Tracking／Mask、2.5D／3D 能力 | design recipe、effect plan、3D capability plan |
| Asset | 來源、授權、B-roll、音樂、SFX、motion 與可重用資產 | current asset plan、license audit |
| Execution | 長短片 build、字幕、合成、調色、輸出 | current.mp4、執行報告 |
| Evidence | 技術 QA、負面案例、人工審片、成效回填 | QUALITY_95、review、learning record |

## 主流程

```text
request
  -> Control discovers canonical root
  -> Decision compiles a bounded context packet
  -> Design compiles domain + format + role into one visual recipe
  -> Asset resolves licensed evidence and reusable material
  -> Execution renders only evidence-ready events
  -> Evidence blocks regressions and waits for Hao timestamp review
  -> Publish / learn / release
```

## Design plane 的四條硬界線

1. `design_system_v6.py` 只使用 33 張參考圖的匿名抽象 DNA，不打包原圖、不複製單張版式。
2. `mrbeast_editing_system.py` 把效果視為有敘事功能與前置證據的事件；沒有 evidence 就不選用。
3. `tracked_graphics.py` 的物件斜角閃光必須在追蹤 matte 內合成；它不是全畫面閃光，也不是轉場。
4. `three_d_system.py` 明確區分 2D、2.5D、true 3D 與 camera-solved composite；缺 mesh、camera solve、clean plate、光影資料時必須降級。

## 相容入口

`AUTOPILOT_4LAYER.md` 保留舊連結，但架構真相以本檔與 `AUTOPILOT_MANIFEST.json` 為準。舊指令繼續可用；新版本只新增能力與 gate，不刪使用者素材或未知檔案。
