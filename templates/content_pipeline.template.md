# Content Pipeline（模板）— 你的內容類型 + 發布前 checklist

> 複製成 `profiles/content_pipeline.md` 再填。
> 本 kit 不出貨綁個人規則的路由器 —— 你在這裡定義**你自己的**內容類型、預設值、發布前檢查；
> 寫 `edit-plan/v4` 前由 agent 讀這份決定 Editkin route、BGM 與模板方向。

## 你做哪些內容類型？（每種定義一組）

### 類型 A：`______`（例：教學長片 / vlog / 開箱 …）
- 平台 / 比例：`______`（YT 16:9 / Shorts 9:16 …）
- 預設 BGM：`______`（你的檔名）
- 字幕風格：`[ ] 基本  [ ] 花字`
- 開頭 hook 模式：`______`
- 結尾：用你的 `profiles/brand.md` outro

### 類型 B：`______`
- （同上）

## 發布前 checklist（通用骨架 — 加你自己的條目）
- [ ] 素材 fps 對齊 timeline（不然播放速度會跑掉）
- [ ] b-roll 已去背景音（只留你要的 BGM/旁白）
- [ ] **畫面跟旁白對得上**（你講什麼就show什麼 — 演示型內容尤其重要）
- [ ] **通用素材占比 < 你的主素材**（產品/實拍是主菜，stock 是調味）
- [ ] 通用素材不重複（同一支 clip 不要一直出現）
- [ ] BGM 短於影片時 → loop 填滿 + 平滑接縫（不要中途靜音）
- [ ] timeline 修剪到旁白真結尾（不要留空白尾巴）
- [ ] 匯出 player-safe（需要的話 libx264 + 無 B-frame）

> 上面有幾條可以用程式驗，不用靠眼睛數：主素材／通用素材比例與旁白對位見 `src/broll_qa.py`
> （`audit_broll_main_ratio` / `narration_broll_sync_report`），BGM 覆蓋、尾端靜音、A/V 與全幀掃描見
> `src/media_delivery_qa.py` 的 `final_delivery_qa`。渲染與匯出本身在 Editkin 完成。
