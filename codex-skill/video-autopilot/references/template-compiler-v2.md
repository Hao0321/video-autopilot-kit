# Template Compiler v2

> **PUBLIC_FIXTURE / privacy boundary:** creator-specific reference counts, dated reviews, project metrics, local paths and private preference evidence are excluded. Calibrate defaults with creator-owned evidence.

## 目的

`template_compiler.py` 是模板選擇與組裝的唯一決策入口；
`community/hao-motion-kit/template_engine.py` 仍是 Bright Editorial 視覺渲染單一真理。
本層不複製 340 張既有模板，也不建立 v2／FINAL／old 目錄，而是輸出小型元件計畫，
讓長片、Shorts、Reels 與縮圖共用設計 DNA、各自依畫幅重排。

## 流程

1. 輸入 domain、format、semantic role、energy、subject 與近期 signatures。
2. 依 `aesthetic_standard.json` 限定可用 style family。
3. 選一個未疲勞的 layout，套入 role component registry。
4. 輸出 safe area、字行數、元件預算、motion reason 與 legacy render adapter。
5. renderer 只有在真素材不足或該 role 需要視覺化時才合成；不可因模板存在就播放。

## 元件而非成品卡

- `real_media`／`evidence_media`／`hero_subject`：內容層，永遠最大。
- `promise_type`／`metric_or_claim`／`active_step`：資訊層，一畫面一焦點。
- `source_chip`／`progress_mark`／`accent_mark`：輔助層，最多兩個強調色。
- `subject_depth`／`focus_target`／`clean_hold`：空間與時間層，防止平貼和過度剪輯。

## 效率契約

- 結構快取 key 只含 domain、format、role、style、layout、copy shape、energy band 與 subject kind。
- 快取禁止 literal copy、媒體路徑、私人路徑與輸出路徑；同結構換文案可直接 cache hit。
- 給模型的 `compact_instruction` 單計畫上限 420 字元，不再載入完整模板庫或 curated creator reference set拆解。
- 340 張 WebP 僅是可重建 preview／fallback cache，日常剪輯不批量重算。

## 疲勞與畫幅

- signature=`style:format:role:layout`；近期已用 signature 必須換 layout，必要時換 style。
- 9:16：單一大焦點、1–3 行主字、保留平台上下安全區。
- 16:9：真畫面與脈絡更耐看、1–2 行主字、graphics punctuate footage。
- 禁止把 16:9 中央裁成 9:16，也禁止把 Shorts 的滿版爆字直接鋪滿長片。

## 永久阻擋

- 播出模板角色名或樣式名。
- 用空白全螢幕卡蓋掉可用素材。
- 固定網格、HUD、黑底或同一模板當所有開場。
- 無語意動機的全螢幕轉場。
- 連續重複同 signature、同卡型或同構圖只換色。

## 驗證

```powershell
python template_compiler.py selftest
python template_compiler.py benchmark --runs 100
python visual_director.py selftest
python community/hao-motion-kit/template_engine.py selftest
```
