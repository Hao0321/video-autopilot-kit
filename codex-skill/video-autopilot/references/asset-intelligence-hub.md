# Asset Intelligence Hub

## 目標

素材不是「越多越好」的資料夾，而是可搜尋、可解釋、可回饋、可攜且不重複分析的決策系統。
中樞只建立 metadata 與穩定 plan，不搬動、不複製、不刪除 B-roll、音樂、SFX 或模板。

```text
既有 manifests／indexes
  ├─ assets/index.json（人工看過的 B-roll 語意、SFX）
  ├─ assets/bgm/*/bgm_index.json（BPM／RMS／時長）
  ├─ assets/broll/motion/manifest.json（私版 motion）
  └─ community/hao-motion-kit manifests（開源 motion／templates）
                 ↓
          asset_registry.py
                 ↓
        current_asset_plan.json
                 ↓
     Editkin v4 plan → audit → atomic apply → render receipt／人工確認／usage commit
```

## 單一來源與可攜路徑

- 原始 manifest 仍是 SoT；Registry 是每次啟動時建立的 virtual view，不再維護第二份巨型 catalog。
- plan 內只准專案相對路徑；renderer 執行時才解析 absolute path。
- `transitions/` 中歷史上被誤放的庫存 B-roll 仍判為 `role=broll`；只有 motion manifest 明確標記的
  transition 才是轉場。暫不改檔名，避免破壞舊 draft。
- 未看過的檔案只標 `inventory`，不可覆蓋 `assets/index.json` 已人工看首幀的 desc／tags。

## 分級 fallback（固定順序）

1. 專案真素材／proof：數字、地點、價格、規格、實測必須回來源。
2. 語意相符 B-roll：題材、畫幅、語意、能量與近期重用共同排名。
3. 題材 motion：沒有可靠實景時補講解、呼吸與章節，不冒充現場。
4. Editorial card：用已驗證文字承接資訊缺口。
5. Clean hold／安全重構：寧可乾淨停留，也不塞不相關庫存片。

任何 `source_required=true` 的 cue，中央庫存都不能取代 proof。

## 排名與記憶

- B-roll：語意 overlap＋domain＋aspect＋energy－近期重用。
- BGM：domain＋BPM／energy＋情緒＋足長－近期重用；優先讀既有 `bgm_index.json`，不重跑 ffmpeg。
- SFX：cue／family＋domain Foley＋energy－近期重用。缺少真正 Foley 時明列 `missing_foley`，不假裝通用
  whoosh 是滋滋聲、引擎聲或布料聲。
- 規劃不寫記憶；只有 renderer 或人工確定「真的用了」才執行 `commit`。歷史超過門檻時把舊事件彙總成
  count／last_used，只保留近期 1,200 筆事件，避免 metadata 無限長大。

## Token 合約

- AI 只讀 `current_context_packet.json`＋`current_asset_plan.json`。
- Asset plan 最多抽樣 6 個 cue、每 cue 最多 2 個 B-roll＋1 個 SFX，音樂最多 3 首。
- 預設 Asset plan 上限 1,800 estimated tokens；超標會縮成 4 cue／每 cue 1 候選。
- 不把 800+ 筆 registry、完整 manifest 或逐檔 ffprobe 結果塞進 prompt。

## 音樂策略

- 單曲足長：`single_track`，避免 loop 接縫。
- 長片超過單曲：`playlist_crossfade`，由前 3 名建立能量段落，不用硬 loop 第一首。
- `vocal_presence` 尚未分析者在 mix stage 標示人工／機械相容性檢查，不虛構「無人聲」。

## 健康與開源

`audit` 的硬錯誤：可選路徑不存在、canonical path 為 absolute、ID 重複、完全沒有 B-roll／BGM。

一般素材的 license／provenance 缺口先列 warning，因私人素材不等於可開源；12 個程式生成 SFX 已有
`assets/sfx/manifest.json` 與 48 kHz PCM 格式聲明，但授權仍是 `pending-owner-choice`。`--release` 另檢查
`community/hao-motion-kit` 的授權與來源。SFX full audit 另鎖 48 kHz PCM。

目前應持續補強的真 B-roll 題材：玩具、紀錄片、訪談、健身、時尚。Domain motion 與模板已有覆蓋，
但不能被計成真實 footage 覆蓋。

## 指令

```powershell
python asset_registry.py plan --topic "Claude AI 教學" --format shorts --duration 35 --output-dir job
python asset_registry.py audit
python asset_registry.py audit --full
python asset_registry.py audit --release
python asset_registry.py migrate-index --write
python asset_registry.py commit job/current_asset_plan.json --content-id "video-2026-001"
```

`visual_director.write_visual_plan()` 會自動在同一輸出資料夾建立 stable asset plan，並只把候選數、
音樂路徑、策略、Token 與 cache hit 摘要寫回 visual plan。

專案 `.claude/skills/video-autopilot` 是唯一 canonical source；安裝版只由
`python skill_sync.py sync` 做 additive sync。它不刪安裝版多餘檔案，也不複製 runtime／demo／媒體／
log state；`system_health.py` 會檢查宣告的程式與文件是否 drift。
