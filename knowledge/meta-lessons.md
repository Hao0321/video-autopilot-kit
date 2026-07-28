> 來自 video-autopilot-kit 開源知識庫 · MIT 授權 —— 影片製作避坑大全（從實戰踩坑提煉的通用心法）

# Meta-Lessons Canon — M1-M111 + S-A~S-L（Shorts）+ SOP + Checklist + Antipatterns

> 從一支住宿型景點介紹 v1→v9（silent vlog 7 輪苦戰）+ 一支旅遊 vlog v1→v28（24h+ 苦戰）累積。
> SKILL.md 主檔只放 orchestration；所有 lesson detail / SOP / antipattern 在這。
>
> 2026-05-23 從 SKILL.md 拆出（原 SKILL.md 713 行 → SKILL.md 250 行 + 此檔 600+ 行）

---

## TL;DR — 5 條核心鐵則

接到「剪一支影片」請求時，**先想這 5 件事**：

1. ☠️ **不要編造數字** — 每個數字/事實必有 source（WebSearch / 用戶 / 畫面）。沒 source → 寫 generic。**「不講話 > 編造」**（M10 / M37）
2. ⛔ **先看畫面再寫文案** — `ffmpeg extract 4 frames (start/early/mid/late) hi-res 640×360` → grid → Read → 才寫對應 overlay（M9 / M21 / M34）
3. 📋 **介紹式不是記錄式** — 含定位/數字/賣點/CTA ≥3 項。沒「我們來到 X」「漫步園區」廢話（R18）
4. 🎯 **字幕統一中央偏下** y=1280-1400（Shorts）/ y=820-930（長片），不跳位（R19 / M13）
5. 🎓 **跑完先 self-critique 17 關**才能說「剪完」。任一項未過 → 還沒完（見 §「Self-Critique Checklist」）

---

## 🔭 第 0 步 — Audit Pipeline（2026-05-24 v3 新增，必跑）

**接到 raw 素材後第一件事**：跑 `silent_vlog_maker.run_full_audit()` 自動跑完 R1 + M12 + M9。

```python
from silent_vlog_maker import run_full_audit
from pathlib import Path

result = run_full_audit(
    raw_dir=Path("videos/current/raw/<topic>/"),
    output_dir=Path("videos/current/audit/"),
    project_name="Topic Name",
)
# 輸出：audit_report.md + audit_report.json + 4-frame hi-res grids per clip
```

**自動產出 3 大件**：
1. **R1 v2 — 11 維度 audit**（之前 7 維度 + GPS / 真實拍攝時間+TZ / camera model / audio codec）
   - **2026-05-24 修復 bug**：之前 `TAG:creation_time` 是 import time（錯）！改用 `TAG:com.apple.quicktime.creationdate`（真實拍攝時間 + TZ）
2. **M12 — Scene Timeline 自動 cluster**（chronological + GPS-aware）
   - Time gap > 30 min OR GPS distance > 1km → 切新場景
   - 49 MOV → 自動排成 14 個 scene（一支旅遊 vlog 實測）
   - 每 scene 標：date / period（早/中/下/晚）/ time range / GPS center / Google Maps URL
3. **M9 / M34 — Hi-res 4-frame grid per clip**
   - 每 clip 抽 start/early/mid/late 4 frames at 640×360
   - 拼大 grid（4×6 layout 每 grid 6 clip）
   - 標 yellow timestamp + filename label（Read 一次看清楚）

**配套 scene_descriptions.json cache**：
- Claude Read grid 後寫每 clip 的 `description / key_elements / text_visible / suitable_captions`
- build script 用作 ground truth（caption 配畫面正確的根本保障）

**為什麼必跑**：
- 不跑 → 11 維度 audit miss / 沒 scene 結構 / 沒看畫面 → 必踩 M9/M10/M21/M34 雷
- 某旅遊 vlog 8/18 caption 錯位的根本原因 = 跳過這步
- ETA: 49 clips ~30 sec audit + ~3-5 min frame extract

---

## 🎓 Meta-Lessons M1-M111 完整 table

> 編號 gaps (M35 / M39 / M41 / M54 / M58 / M63 / M75 / M80) = 跨 SKILL 引用佔位但本 canon 未寫 row（M35 / M75 已補在表後 deferred-rows，其他編號 = RESERVED unused）。
> M108（字幕斷句品質：尾懸掛/頭懸掛/腰斬/超長）與 M110（腳本三支柱）走**機械 gate 為主**，
> 規則本體分別住在 `src/longform_maker/word_captions.scan_line_quality()`（交付端接線 =
> `src/capcut_helpers/delivery_qa.check_caption_linebreaks()`）與 `src/longform_maker/script_gate.py`；
> 直式短片的結構教訓另立 **S-A~S-L**（標籤定義以 `src/longform_maker/shorts_gate.py` 為準）**＋ 人工項 S-M/S-N**（見本檔最後一節 §Shorts 結構教訓）。

| # | Meta-Lesson | 反規則（犯過的錯）| 正解 |
|---|---|---|---|
| **M1** | **「export 出檔」≠「剪完了」** | v1 把 raw 72s 全長 export 就說剪完 | Self-critique checklist 全過才能說「完成」|
| **M2** | **每張字幕必須有資訊密度** | 「我們來到 X」「漫步園區」「真的很漂亮」廢話 | 介紹式 — 含定位/數字/賣點/用法/價格/CTA ≥3 項 |
| **M3** | **「介紹能力」是通用技能** | 我以為景點介紹是特殊技能 | 教學 / 工具 / 開箱 / 食物全用同一套 R18 框架 |
| **M4** | **Voice profile 即使 silent vlog 也必套** | 用 Google Maps「14:42 {縣市}・{鄉鎮}」廉價字幕 | 文字也是 voice = brand 識別核心 |
| **M5** | **視覺一致性 > 多樣性** | 4 個 position 跳來跳去 | 統一 subtitle 中央偏下 y=1280-1400 |
| **M6** | **寫文案前必研究實際資訊** | 「想像」用戶 voice → 文案空洞 | WebSearch 主體賣點/數字/規格 後再寫 |
| **M7** | **Pre-flight audit 不只 codec** | 只查 codec name，沒查 HDR/rotation/UTC time | 7 維度全掃（R1 強化版）|
| **M8** | **Audit-first，不等用戶要求才整理** | 我累積到 16 處 stale refs 才 cleanup | 每 major version 後自動跑 audit |
| **M9** ⛔ | **看畫面才寫字幕（畫面驅動文案）** | v7 把三條賣點各配到一個「根本沒拍到它」的畫面上（賣點清單照抄、畫面靠想像） | 每個 clip 先 ffmpeg extract mid-frame → Read 確認實際拍到什麼 → 才能寫對應文案 |
| **M10** ☠️ | **不要 hallucinate 數字/事實（最致命）** | v8 寫了場域坪數、設施數量這類「酷數字」— WebSearch 根本沒提到，我自己編的 | 每個數字/強斷言必有 source (WebSearch 引用 或 畫面可見證據)。沒 source 寧可寫 generic 描述也不亂編 |
| **M11** 🎬 | **M9 thumbnail 看 mid-frame ≠ 看整段** | 某旅遊 vlog v1 某 clip mid-frame 是某地標，trim 0-2s 卻拍到另一畫面（鳥群）| M9 強化：trim 區間內也要看 mid-frame，多段 extract start/mid/end |
| **M12** 📚 | **混雜素材 (照片+影片) 要 chronological sort + separate audit** | 某趟旅遊 49 MOV + 60 HEIC + 2 jpg = 111 檔案，工作量 ×5 single vlog | 用 `com.apple.quicktime.creationdate` sort（不是 file `creation_time`！），分類 MOV/HEIC/jpg 分批 grid |
| **M13** 🎨 | **長片 (landscape) ≠ Shorts (portrait)** — 位置/bitrate/字級全不同 | v1 用 Shorts R19 y=1280-1400 套長片 1920×1080 → 跑出畫面外 | 長片獨立 PRESETS：tv_hook y=820 / tv_caption y=930 / Day marker 角落 56pt。**⚠️ Shorts 的 y=1280-1400 是共用帶**：地址/店名/識別這類**常駐條**（S-E）跟內容字幕搶同一塊 → 兩者 y 值必須錯開（常駐條壓到帶底 y≈1390、內容字幕留在 y≈1280-1320），否則常駐條會被逐句字幕蓋掉或疊成一團 |
| **M14** ✨ | **照片要 KenBurns 動畫** — 靜止違和 | v1 用 ffmpeg `zoompan` zoom-in 1.0→1.15 → 整片不死板 | `-loop 1 -i photo.jpg` + `zoompan=z='min(zoom+0.0012,1.15)':d=N:s=WxH:fps=30` |
| **M15** 🎭 | **綜藝字卡 ≠ informational caption** | v1 用 cyan + magenta + gold 比單一白 vibrant 10x | vibrant 多色 + 半透明黑底 + emoji 點綴 |
| **M16** 🛠️ | **選對工具 — ffmpeg drawtext ≠ 專業字幕** | 反射性選 ffmpeg → emoji 缺字 / 字體少 / 動畫弱 | 綜藝字卡 / 動畫 / emoji → CapCut Desktop + capcut-cli JSON draft |
| **M17** 📋 | **不要默認單一工具 — 先列選項給用戶選** | v1-v9 默認 ffmpeg+Python，用戶 challenge 才討論工具 | 先列 A/B/C/D 工具選項 → 讓用戶選 → commit 跑 |
| **M18** 📂 | **CapCut Desktop draft path 搬位置要 fix JSON + kill 所有 process** | capcut-cli 在某個磁碟 build → 草稿搬到另一個磁碟 → JSON 內的路徑還指著舊碟 → CapCut「媒體遺失」| (a) build 直接 chdir CapCut User Data path / 或 batch fix 7 處檔案。(b) 8-backslash Python escape。(c) `Get-Process CapCut \| Stop-Process -Force` kill 全 ~8 個 process |
| **M19** 🔤 | **capcut-cli add-text 3 大陷阱** | (1) 預設 font_path = en.ttf（英文）→ 中文壞 / (2) `--font-size 70` 是 % 不是 pt → default 15 才 normal / (3) `transform.y -1=top, +1=bottom` 跟 ffmpeg 反 | Build 後 batch fix JSON：font_path → NotoSansTC-Black.otf / size 絕對 map (70→12 56→8 50→7 40→6) / position lower-third stack |
| **M20** 💾 | **CapCut Desktop 開啟時 auto-save 覆蓋外部 JSON 修改** | build + post-fix size → user open CapCut → CapCut load → auto-save 把舊 size 寫回 file → fix 失效 | (1) Kill ALL CapCut processes 前 fix JSON / (2) Fix 後告訴用戶不要 open CapCut until I say |
| **M21** 🎬 | **trim 起始點 ≠ mid-frame，畫面對應錯（M11 升級）** | M9 mid-frame 看內容，但實際 build 用 `0-Ns` trim — clip 開頭中段結尾內容可能完全不同 | (a) build 時改從 mid 起取 / (b) 抽 start/mid/end 3 frame 看再寫 / (c) build 後讓用戶在 CapCut 手動 nudge |
| **M22** 🎯 | **HIBC 結構必跑**（Hook→Intro→Body→CTA） | 31 輪都直接 chronological dump 18 段文案 | HIBC: 0-3s Hook（50-60% drop off）/ 0-30s Intro / 30s+ Body / 末 20-30s CTA。第 1 秒可用「結果 flash 前置」curiosity |
| **M23** 🎬 | **Cut on Action + Beat Sync ≠ 固定 trim 3 秒** | 每 clip 都 trim 3-4s 固定 duration | 找 action moment 切：腳落地 / 放杯子 / 開門 + 音樂 beat drum hit = 切。主流 0.5-1s clip |
| **M24** ⚡ | **Pacing 短長 clip 交錯，每 5-7s 新 visual beat** | 固定 3s pace 太單調 | Hook flash 1-2s / Detail flash 1s / Narrative 3-4s / Photo KenBurns 2.5s / CTA breathing 4-5s |
| **M25** 🎥 | **B-roll 10 types 變化** | 只用 establishing shot | Establishing / Detail / Reaction / Cutaway / J-cut / L-cut / Montage / Match cut / Time-lapse / POV |
| **M26** 🎨 | **中文綜藝字卡 = 多字體 + 多色 + 動畫變化** | 單一 NotoSansTC-Black 全部 | 字體：思源黑體 / 未來熒黑 / 饅頭黑體 / 書法家疊圓體 / 手寫風 mix。顏色：白（說明）/ 黃（重點）/ 紅（驚）|
| **M27** 🛠️ | **CapCut 內建工具 >> programmatic 100x** | capcut-cli add-text generate basic 達不到 polish | CapCut GUI：AI Auto-Caption / 字幕模板庫 / 字體選單。**程式不會「看 footage」決定 cut on action 點** |
| **M28** 🛑 | **承認程式化生 vlog 上限 = placeholder 級** | 31 輪 programmatic 都達不到 user 期待 | 我做 init + mid-trim + BGM（programmatic 擅長）/ 用戶在 CapCut GUI 做字幕 + 微調（GUI 強項）|
| **M29** 🔇 | **B-roll 音訊一定要 strip — 自帶雜訊撞 BGM** | 31 輪沒執行自己寫的規則 — 旅遊 B-roll 自帶機場噪音 / bus 引擎 / 街頭環境音 跟 BGM 25% 撞 | CapCut 內：4-level mute (material has_audio=false + has_sound_separated=true + segment volume=0 + last_nonzero_volume=0)。ffmpeg：`-an`。Fallback：**ffmpeg force-mix BGM** 完全替換 audio |
| **M30** | ~~程式做骨架 + GUI 做字幕~~ **撤銷** | 用戶當場罵「你根本沒上字阿」→ 違反 autopilot preference | → 看 **M31** |
| **M31** 🚀 | **Autopilot preference 絕對優先 — 寧可程式 placeholder 級也不能丟 GUI 工給用戶** | 給 buffet (A/B/C) + 推薦含 30-45 min GUI 工 → 違反 autopilot 預設 | Vlog autopilot 含字幕 build 完當交付物 + 套 hierarchy (marker top gold + main mid white + sub bot yellow) + 寫 `cut-plan.md` 給用戶可選微調 |
| **M32** 🤖 | **程式碼達上限 → 召喚 computer-use agent 操作 GUI** | 用戶連罵 32 輪後說「我要的就是全自動你用 AGENT 剪片」| 觸發：(a) 連 ≥3 輪 programmatic patch 用戶仍罵 / (b) 用戶提及「全自動」「agent」。Brief 必含 6 項（draft path / 吐槽歷史 / raw / steps / Export 路徑 / 絕不問規則）。`run_in_background:true`，30-60 min |
| **M33** 🚫 | **CapCut Free 版 Pro paywall + 4px transition icon = agent 操作 blocker** | agent 68 min 後報「春日光效」「自動調整」Pro-only Export 被擋。Timeline transition icon 4px 寬，點不中 | Brief agent：(1) 只用 download icon（菱形 = Pro）/ (2) 加 transition 前先試 Export 早期偵測 / (3) Transition 微調直接 Ctrl+Z 不點 4px / (4)「自動調整 / 智能 X」一律先當 Pro |
| **M34** 🔍 | **Caption 配置前必跑 frame audit — 用戶文案 ≠ 實拍內容** | 用戶 32 輪罵醜根本原因：我把 18 段文案 chronological 配 18 個 MOV，沒看實拍 → 8/18 全錯位 | 強制 SOP：每個 MOV 抽 4 frames (0.5s / dur×1/3 / dur×2/3 / dur-0.5s) hi-res + grid + Read。以實拍為準寫 caption，不是用戶文案 fits the picture |
| **M36** 🔬 | **Audit 必須 hi-res (640×360+) — 320×180 thumb 看不出細節** | v6 漏 4 caption 錯誤（某 clip 機場 vs 飯店 / 某 clip 室內裝潢 場景誤判 / 某 clip 飲料品牌辨識錯）— 320×180 看不清招牌字 | 第一輪 thumb (320) 只 routing「indoor / outdoor / food / scene」。第二輪 hi-res (640) 任何 specific 品牌 / 地點 / 文字 / 數字必 verify。Audit grid 寫 self-question 強迫懷疑 |
| **M37** 📚 | **Cultural depth caption 不能 hallucinate 歷史 / 數字（M10 升級）** | v8 加 cultural notes 全 hallucinate：「某小吃店類型」配錯場景 / 「某族裔比例」憑空編（與實際差很多）/ 「某飲料品牌產地」誤標 / 「某紀念碑年代」誤標 | (1) Cultural note 寫前必 WebSearch 驗證 / (2) 沒驗證寫 generic（「某宵夜餐廳」「某早餐 buffet」）/ (3) 只保留可驗證 label：地名 / 通用功能 / 招牌字 / (4) 與視覺直接矛盾的絕對禁止 |
| **M38** 🚫 | **ffmpeg drawtext 不支援 emoji font fallback** | v8b 用戶看到 caption 前出現「□」豆腐字。Noto Sans TC 無 emoji glyph (⭐ 🥤 ✈️ 📸) | (1) ffmpeg pipeline caption 絕不放 emoji / (2) ASCII 替代：⭐ → ★ (U+2605 BMP) / ✈️ → 「Flight」字 / 🥤 → 「冰」 / (3) 真要彩色 emoji → CapCut sticker / (4) Build script 加 sanity check 自動 strip |
| **M40** ⛔ | **CapCut Free 套特效次數有 daily limit** | Agent 套到 5+ 特效後 Export 跳「達 daily 限制」 | 約當地 3 AM 重置（依你所在時區實測一次）/ fallback Path D JSON edit 不撞 daily |
| **M42** 🚫 | **動態文字 / sticker overlay MUST use CapCut native，NEVER ffmpeg drawtext** | 用戶要求某段素材旁加小動態字時明確規定用 CapCut，不要再用 ffmpeg | caption / 字幕 / sticker / 動態 text (彈跳/縮放) / 標題卡 → CapCut 文字 panel + 貼圖 panel。ffmpeg 仍可：audio mix / concat / scale / color grade / film grain / vignette。**用戶可見的文字 / 圖案 overlay 一律 CapCut** |
| **M43** ✍️ | **字體都給我用好看點** | 2026-05-22 用戶明確規定「字體都給我用好看點」 | 禁用：標楷體 / 細明體 / NotoSansTC-Bold (太 generic) / SmileySans-Oblique (中文 coverage 不全)。Whitelist：Vlog narrative → Noto Serif CJK Bold (放你自己的 assets/fonts/) / Marker title → CapCut 文字模板 / 動態 text → CapCut 模板 / Fallback → NotoSansTC-Black.otf |
| **M44** 🍜 | **不要憑視覺猜菜品 — 用戶實際點的才算** (2026-05-24 某支片) | v1 看外觀就 default 寫某招牌菜（用 WebSearch 店招牌的菜當預設）。實際用戶點的是另外幾道（與店招牌列的不同）。**比 M10 / M37 更隱性**：店招牌列的菜 ≠ 用戶當天點的菜 | 食記寫菜名 SOP：(1) 先 ASK 用戶「這 N 碗各是什麼」/ (2) 從 raw 抽 frame 找「桌上菜單 / 點單收據」visual evidence / (3) 沒人類來源 → 寫 generic「招牌湯麵」「拌麵」「另一道」不寫具體菜名。**絕不憑視覺特徵 default 套店招牌菜** |
| **M45** 🎬 | **美食 vlog ≠ 旅遊 vlog — 節奏 / 重點 / 句式不同** (2026-05-24 某支片) | v1 套旅遊 vlog 開場「現在時間 晚上7點 / 來某地吃某道料理」(timestamp 流水帳)。用戶當場罵「沒有介紹美食的感覺，節奏也怪怪的」 | 美食 vlog 節奏（28s 範例）：<br>**0-3s**：視覺衝擊（湯頭特寫 / 麵條夾起 / 入店反差），**不**用時間戳<br>**3-7s**：店招建立（店名 + credentials 反差，如「從外地來的」）<br>**7-12s**：第 1 道 reveal — 菜名 + 一句評價（「湯頭超鮮」）<br>**12-19s**：第 2 道 reveal — 反差句（「這碗才是本體」）<br>**19-26s**：第 3 道 climax — 強感受（「整個爆汁」）<br>**26-28s**：暗示後續（「下次想吃 X」）<br>**句式重點**：每碗一句**評價/反應**，不要堆 fact / 不要說「上桌~」中性詞 |
| **M46** 📐 | **直式 source rotation=-90 → CapCut 預設 1920×1080 canvas → letterboxed 黑邊** (2026-05-24 某支片) | capcut-cli init template 預設 canvas 1920×1080，build script 沒檢查 source rotation → final Export 1920×1080 landscape with portrait video 中間 letterboxed | 強制 SOP：build script 開頭先判 source layout → 若 layout=='portrait' → 強制 `set_canvas_portrait()` 改 canvas_config 為 1080×1920。**接受 portrait source 但 export landscape 是 hard fail**，不能讓用戶上傳 Shorts 後變方框小影片 |
| **M47** 🎨 | **「ART Comic Black White Bold」雖然 某旅遊 vlog 專案 用最多，但是 fallback default 不是 favorited** (2026-05-24 某支片) | v1 套 ART Comic Black 用戶說「太普通了」— 那是 某旅遊 vlog 專案 因為 agent #15 默認套滿 28 caption 後用戶沒一個個換而已。**最多 ≠ 最愛** | 找用戶 真正 favorited 花字：(a) 不能 mtime 猜 (證實錯誤) / (b) 不能用「某旅遊 vlog 專案 canonical state 最多次數」推 / (c) **唯一可靠：spawn agent reverse engineer 跑進 GUI 打開花字 panel → ⭐ filter → 截圖 highlighted = 用戶當下 favorited** / (d) v0.2 加 `agent-flower-discover` 專責 task：操作 + diff JSON + 寫進 text-templates-catalog.md，主 Claude 之後可直接 reference |
| **M48** 🪟 | **CapCut window-hidden 後 open_application 沒 bring to foreground** (2026-05-24 某支片 v2 agent 抓到) | Chrome read-tier 阻擋 alt+tab，CapCut process 在但 window 在 File Explorer 後面 → screenshot 看不到 CapCut | Phase 1 setup 必含 SetForegroundWindow PowerShell workaround：`Add-Type ... [Win]::SetForegroundWindow($p.MainWindowHandle)`。詳：[capcut-agent-brief-template.md](capcut-agent-brief-template.md) §M48 |
| **M49** 🔊 | **CapCut Export audio default 192 kbps（不是 brief 寫的 320k）** (2026-05-24 某支片 v2) | Brief 都寫「AAC 320 kbps」但 CapCut UI 無此選項，embedded video audio 永遠 192k | 1) Brief 寫「AAC default」更準確 / 2) 要 320k → ffmpeg post-process / 3) 192k AAC 對 YouTube/IG 完全夠（平台 transcode 到 ~128k anyway） |
| **M50** ⚡ | **Path A 實測 ≤30s short 只要 4 min（不是 8-12 min estimate）** (2026-05-24 某支片 v2) | Brief `wait(seconds=180)` 是長片設計，短片 GPU 加速 render ~3 sec 就完成 | 短片 brief 改 `wait(seconds=10)` + active screenshot check progress bar；長片（>2 min）才 180s wait（純 timing fact，不是 path 建議）|
| **M51** ✏️ | **直式 Shorts 不一定要花字 — 基礎 tab + 預設組樣式更乾淨** (2026-05-24 某支片 v2.1 用戶教) | v1/v2 都反射性套 花字 (panel-text-flower)，用戶開 v2 改用「基礎 tab」「預設組樣式」(6 個 Aa preset)。一句教訓：**「直式不一定要花體」** | 直式 Shorts 預設 path：(1) 用 `apply_text_preset()` 不是 `apply_effect_to_segment()` / (2) 字體 `剪映团子` (CapCut bundled effect_id 7598225001988246801) 不是 Noto Serif CJK Bold / (3) 預設樣式「白底黑邊」(白 fill + 0.06 黑 stroke + 無 shadow) / (4) font_size 15 是 CapCut UI native value / (5) `clear_existing_effects=True` 自動清掉舊花字 refs |
| **M52** 🎨 | **CapCut「基礎」tab JSON 結構解讀** (2026-05-24 reverse engineer 用戶 manual seg #0) | 花字 = `materials.effects[]` + `extra_material_refs[]`。基礎預設樣式 = 完全不同 path — 寫進 text material 本身 | 必改 6 處：<br>1. `material.font_path` → CapCut cache 字體 .ttf<br>2. `material.text_color / border_color / border_width / has_shadow`<br>3. `material.content.styles[].font.path`（重複設 font，CapCut 兩處 cross-check）<br>4. `material.content.styles[].size` (CapCut 15-100 範圍，**不是 ffmpeg pt**)<br>5. `material.content.styles[].fill.content.solid.color` + `.strokes[].content.solid.color` (RGB 0-1)<br>6. `segment.extra_material_refs[]` 清掉 panel-text-flower 類 refs<br>→ 已封裝為 `capcut_helpers.text_style.apply_text_preset()` |
| **M53** 🔁 | **CapCut Desktop open + 用戶 manual edit → auto-save 把 mute 改回 (M20 真實 case)** (2026-05-24 某支片 v2.1) | 用戶開 v2 改 seg #0 → CapCut 載入時 has_audio=true，auto-save 寫回 file → mute regression 0/5 | 用戶 manual edit 後**必跑** `mute_all_video_segments()` 再 sync。Workflow：用戶 manual → kill CapCut → re-apply mute → save_with_sync → re-export。Build script 加 post-user-edit hook flow |
| **M55** 🔇🚨 | **JSON 4-level mute audit 100% ≠ Export 真的 mute — CapCut Export 仍漏 B-roll 原音** (2026-05-24 某支片 v2.1 用戶罵「我不是叫你都要把背景聲音移除嗎??」) | v2.1 audit `audit_mute_state` 5/5 100% fully muted，但 ffmpeg waveform 抓出 Export 仍有 B-roll ambient（餐廳吵雜聲、人聲、餐具碰撞）混在 BGM 裡 | **ffmpeg force-mix BGM = mandatory final step**，不是 fallback。任何 CapCut Export 出來的 vlog mp4 必跑 ffmpeg post-process：(1) `-map [v]` 只取 video stream / (2) `[bgm:a]atrim+afade+volume=0.25 → [a]` BGM-only audio / (3) `-c:a aac -b:a 192k` re-encode。寫進 build pipeline 標準 final phase。`audit_mute_state` 只是 JSON state 報告 — 不是 Export 真實狀態 |
| **M56** 🍜📍 | **美食 vlog 結尾必加店家資訊 outro card（地址 + 店名 + 招牌菜）— 用戶提供 > WebSearch** (2026-05-24 某支片 v2.1) | 5 個 caption 都是菜品描述沒地址 → 觀眾想分享給朋友還要自己 google。WebSearch 抓到的地址常是錯的或老資料 — 創作者實際到店記得的地址才準，M37 強化 | 食記 vlog 預設 outro 最後 3-5 sec（不算進 main caption count）：<br>Line 1 (金 64pt)：店名 + 分店 (例「某店名 OO店」)<br>Line 2 (白 44pt)：完整地址<br>(Optional) Line 3 (白 36pt)：電話 + 營業時間<br>位置：lower-third y=h-380 / y=h-280<br>fade in 0.4s / fade out 0.5s。**M37 升級**：用戶 ground truth > WebSearch（用戶記得正確，網路 listing 常 stale）|
| **M57** ❓ | **食記 vlog build 前必 batch 問用戶 5 件事，不要猜** (2026-05-24 某支片 retrospective — 用戶嫌「太慢浪費」) | 我憑視覺猜菜品 / WebSearch 抓 stale 地址 / 假設「花字」是用戶要的 → v1 全錯後 3 次重做耗 ~50k token | Build food short 前必問（1 個 message batch 完）：<br>1. 菜品具體名稱（每碗）<br>2. 店家完整資訊（店名 + 分店 + 地址 + 電話 + 時間）<br>3. 重點 emphasis（哪道是 climax）<br>4. caption 風格偏好（basic preset / 花字 / 哪種）<br>5. BGM 偏好（你的 BGM 命名規則 / chill / 用戶提供）<br>→ 已封裝為 `silent_vlog_maker.PRE_BUILD_QUESTIONS_FOOD_VLOG` |
| **M59** 🎓 | **basic preset + 剪映团子 是所有 content type 預設，花字 only opt-in** (2026-05-25 用戶簡化) | 我先猜「教學 NO 花字 / 旅遊 OK 花字」content-type-aware → 用戶糾正：「教學的字體我到時候還會再修，你就先跟旅遊類的字體一樣」=「**全部統一 default basic preset，要花字我自己說**」 | Build 預設**所有 content_type** 用 basic preset (`white_outline_with_box` + 剪映团子)。**用戶自己在 CapCut 內 fine-tune font 是正常 workflow**，build script 只給 starting point。花字 ONLY 在用戶 explicit 說「我要花字 / flower text」才走 capcut Path B/C agent。<br>→ `should_use_flower_text(user_explicit=True)` 才 True (default False)<br>→ `recommend_caption_style()` 加 `user_wants_flower=False` flag<br>→ **實際落地（2026-05-29 canon-code drift 更正）**：spec 是 `PRE_BUILD_CHECKLIST_TEACHING_LONGFORM` / `PRE_BUILD_CHECKLIST_FOOD_VLOG` 等 checklist dict（`defaults.subtitle_style` 全非花字 basic preset），**非 `make_*_spec()` 函數**——那兩個名字從未實作，設計改用 dict + alias 表 (M59 v2) |
| **M60** 🖼️ | **OBS 螢幕錄影必裁掉上下 chrome（URL bar + Windows taskbar）— 用戶不會 hide UI 是常態** (2026-05-25 用戶明確規定) | 用戶錄產品 OBS 螢幕錄影 把 Chrome tab bar (~80 px top) + Windows 11 taskbar (~50 px bottom) 都錄進去 → 直接塞進影片很 unprofessional | **每個 screen recording 必跑 `clean_screen_recording()` post-process**：crop top 200 px + bottom 80 px + zoom 模式 (DEFAULTS_OBS_CHROME_WIN11 **v3** — v1 的 80/50/letterbox 截不乾淨且有黑邊，2026-06-10 audit 已把函數預設值 wire 到 v3)，然後 zoom 回 1920×1080。<br>→ 已封裝 `silent_vlog_maker.clean_screen_recording()` + `batch_clean_screen_recs()` |
| **M61** ✂️ | **OBS 錄影前後一定有「按開始/停止錄影」UI 過場 — 必 trim** (2026-05-25 用戶明確規定) | 用戶產品 OBS 螢幕錄影 開頭 1.5-2 sec 是 OBS 介面切過去 Chrome，結尾 3-5 sec 是切回 OBS 點停止錄影 → 影片開頭結尾 dead air | **預設 trim 前 1.5 sec + 後 4.0 sec**（per DEFAULTS_OBS_CHROME_WIN11）。若內容很短（<10 sec）trim 比例降到 0.5/1.0。<br>→ `clean_screen_recording(trim_start_sec=, trim_end_sec=)` 可調 |
| **M62** 🎙️ | **語氣瑕疵長停頓必 trim — 但「嗯啊」filler 無法自動 detect** (2026-05-25 用戶要求) | OBS 旁白「（一句話講到一半）⋯⋯⋯（才接下半句）」中間有 1-2 sec 停頓 / 偶爾「嗯」「啊」filler → 影響 pace | **silence_threshold = -30 dB / min_silence = 0.8 sec / keep_silence = 0.2 sec**（自然 pace）+ loudnorm I=-16 LUFS。<br>「嗯」「啊」**無法自動 detect**（需 Whisper word-level alignment + manual edit）→ 告訴用戶這部分要 CapCut 手動 cut，或 future 加 Whisper-based filler detection。<br>→ `silent_vlog_maker.clean_voice_pauses()` + `batch_clean_voice_tracks()` |
| **M64** 🎬 | **所有 content type build 路徑 = CapCut** (2026-05-25 用戶規定「全部都給我用剪映」) | — | **唯一 build path**：build CapCut draft → `capcut_helpers + capcut-cli` → 用戶在 CapCut Desktop 開 → 智能字幕 / 翻譯 / fine-tune / Export。ffmpeg 只作 source pre-process（M60-M62 清螢幕錄影 / 清旁白 / 抽 frame audit）+ output verify（quality_check）。**無 ffmpeg drawtext caption / outro / 任何 final overlay**（純 ffmpeg 的 Shorts pipeline 在這條路線下不留）|
| **M65** 📝 | **CapCut AI 智能字幕 4 個 workflow learnings**（2026-05-25 某支片 v1 agent 抓到）| Agent run 後抓到 4 個下次省 iteration 的 facts | (1) **雙語字幕 = single call** when 雙語 dropdown 一開始就 set 對 — 不是兩步「生成中文 → 翻譯」<br>(2) **AI default language = 英文** even for 中文 voice → 必手動切「中文」/「Chinese」<br>(3) **Export 1080p landscape ~60 sec** (GPU 加速 / 比 brief 3-5 min 估快很多)<br>(4) **字幕樣式預設白字** — 用戶自己 fine-tune 顏色 / 字型 / 位置（M59 v2 default）|
| **M66** 🔤 | **中文字幕 MUST 繁體中文 — 永遠不能簡體**（2026-05-25 用戶罵「你怎麼給我用簡體中文」明確規定）| 用戶是繁體中文 audience，CapCut AI default 出**簡體** (e.g. 「並」→「顶」/「设计」「开发」)。我沒在 brief 寫 explicit「繁體」→ agent 直接接受 default 簡體 → ship 出去 user 看到簡體罵 | **Agent brief 永遠強制**：<br>1. Step「智能字幕」選語言時 → **必選「中文（繁體）」或「Traditional Chinese」**<br>2. **Preferred fix path = Path D OpenCC Python**（不要 GUI 簡轉繁 toggle hunting）— 把這條流程寫成你自己的 SOP 檔存起來<br>3. Verify (3 layers)：JSON grep `设/计/开/发/并` count = 0 / CapCut preview screenshot 3 spot / final mp4 frame extract 確認繁體<br>4. 若見任何簡體字 → partial report 停 → 不准 Export<br>→ 寫進你的 CapCut agent 定義檔鐵則 + [capcut-agent-brief-template.md](capcut-agent-brief-template.md) Step 6 必含 |
| **M67** ⚡ | **CapCut 簡→繁: Path D OpenCC Python 5x faster than GUI** (2026-05-25 某支片 v2 agent 實證) | Agent v2 brief 寫了「找 CapCut 簡轉繁 toggle」GUI flow，agent 自己 deviated 走 Path D OpenCC 反而省 50 tool calls + 18 min | **新 default path** for 簡→繁 字幕 fix：<br>1. `pip install opencc-python-reimplemented`<br>2. `OpenCC('s2tw')` 走 JSON-direct conversion（不開 CapCut GUI）<br>3. `save_draft_with_sync(backup=True)` auto backup `.pre_s2tw_bak`<br>4. M18 sync 4 file locations<br>5. 3-layer verify (JSON / preview / final frame)<br>6. Spawn agent Path A Export only<br>→ 把這條完整 flow 寫成你自己的 SOP 檔存起來 |
| **M68** 🎬✍️ | **教學長片雙 tier 字幕【示範組】— 定好就全系列固定，但值要你自己定** (2026-05-25 某支片 v2) | 字幕外觀是**頻道識別**，不是通用最佳解 —— 每支片換一套 = 觀眾認不出你。下面是一組可直接跑起來的示範值（照抄別人的字幕長相沒有意義，換成你自己的再鎖）| **Primary subtitle（主語言）示範值**：<br>• 預設組樣式：第 3 row 第 3 個 Aa preset（白字 + 黑底）<br>• 字體：CapCut SystemFont (`C:/Users/<USERNAME>/AppData/Local/CapCut/Apps/<VERSION>/Resources/Font/SystemFont/`)<br>• text_color: `#ffffff` / border_color: `#000000` / border_width: **0.08**<br>• fill: solid white `[1,1,1]` / stroke: solid black width **0.06**<br>• **background_color: `#000000`**<br>• **background_alpha: 0.7** (= 70% 不透明度)<br>• **background_round_radius: 0.4** (= 40% 圓角)<br>• **background_height: 0.28** (= 28% 高度)<br>• has_shadow: False<br>**Secondary subtitle (英文) — 用戶 confirmed style** (2026-05-25 截圖 2)：<br>• 預設組樣式：第 1 row 第 2 個 Aa（白字 + 黑底）— 較硬挺<br>• background_alpha: **1.0** (全不透明，無透明)<br>• background_round_radius: **0.0** (直角)<br>• background_height: **0.14** (較短 box)<br>• 其他同 primary (文字白 / 黑邊 0.08 / stroke 0.06 / CapCut SystemFont)<br>→ 雙 tier 視覺主次區分：**中文柔和（圓角半透明）/ 英文硬挺（直角全不透明）**<br>→ Lock 進 `PRESET_STYLES["teaching_primary"]` + `["teaching_secondary"]`<br>→ 下次 build CapCut draft 自動 apply（M64 + M68 chain）|
| **M69** 🇨🇳🇺🇸 | **AI 智能字幕 必跑校正字典 — 頻道專有名詞常見同音誤判** (2026-05-25 用戶規定)| 某支片 v2 後用戶看 CapCut 字幕發現 AI 把品牌名/技術術語聽成同音字（例：英文品牌名被聽成相近的常見英文單字、中文術語被聽成同音的別字）。同一個專有名詞常被誤判成多種變體 | **新 helper** `apply_subtitle_corrections()` + `scan_potential_errors()` in `capcut_helpers/subtitle_corrections.py`<br>**永久 workflow 強制**：CapCut AI 智能字幕 + 翻譯做完 **必跑** corrections 再 Export：<br>```python<br>safe_kill_then_verify()  # M20<br>draft = load_draft(name)<br>stats = apply_subtitle_corrections(draft)<br>save_draft_with_sync(name, draft)<br>```<br>**Dict 永遠 grow**: 發現新錯字加進 `BRAND_CORRECTIONS` / `CHINESE_HOMOPHONE_CORRECTIONS` / `PHRASE_CORRECTIONS`<br>**抽象範例（自填自己頻道的專有名詞）**：同音英文單字 → `YourBrand` / 相近中文別字 → `YourTool` / 技術術語縮寫展開（如 `XX RN → XX Render`）。每個頻道都該維護自己的 brand-correction 字典 |
| **M70 v2** 🪟🚫 | **Agent session start 必 minimize 多個 focus-stealing apps + AttachThreadInput SetForegroundWindow** (2026-05-25 某支片 v3 / 2026-05-26 v6e agent 升級)| v1: 只 minimize Chrome → 之後檔案總管 / 其他瀏覽器 / 編輯器 / 通訊軟體 / 錄影軟體都可能 grab focus。v2: 全部 minimize + 用 AttachThreadInput 強化 SetForegroundWindow（單純 SetForegroundWindow Windows 11 對 cross-thread 有 restriction）| **每個 capcut-edit-agent session start 第一個 PowerShell command** — minimize **broader app list** + AttachThreadInput pattern:<br>```powershell<br># Minimize ALL potentially focus-stealing apps<br>$apps = @('chrome','msedge','explorer')   # ← 再補上【你自己機器上】會搶 focus 的：編輯器 / 通訊軟體 / 錄影軟體 …<br>$sig = '[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);'<br>Add-Type -MemberDefinition $sig -Name Win32 -Namespace W -PassThru \| Out-Null<br>foreach ($app in $apps) {<br>  Get-Process $app -ErrorAction SilentlyContinue \| Where-Object { $_.MainWindowHandle -ne 0 } \| ForEach-Object {<br>    [W.Win32]::ShowWindow($_.MainWindowHandle, 6)  # SW_MINIMIZE<br>  }<br>}<br>```<br>+ AttachThreadInput-based 強制前景 .ps1（讓 agent 自己生一支）for stubborn focus thieves<br>→ 寫進你的 CapCut agent 定義檔 Pre-flight checklist v2<br>→ 寫進 [capcut-agent-brief-template.md](capcut-agent-brief-template.md) Step 0「Environment cleanup」section v2<br>→ 預期省 30-50% wall-clock for any GUI agent session — v2 covers more edge cases |
| **M71 v2** 📐 | **CapCut window auto-shrinks 必 MoveWindow resize (v2: 1400×900 universal — 2026-05-26 升級)** (2026-05-25 某支片 v3 / 2026-05-26 v4 升級)| v1: Agent 把 CapCut 帶到 foreground 後，**Export dialog 自動縮到 ~136 px**。v2: v1 寫 900×650 只夠 Export dialog，editor view 看不到 timeline (AP13) → agent v4 自己 override 用 1400×900 | **`SetForegroundWindow` 完跟一個 `MoveWindow`**：<br>```powershell<br>[Win32Functions.Win32MoveWindow]::MoveWindow($capcutHwnd, 100, 100, 1400, 900, $true)<br>```<br>→ **標準 size v2: 1400×900** universal — editor view + Export dialog 都能正常顯示<br>→ ⚠️ 舊值 900×650 已 retire（AP13 教訓：brief 寫死 numeric value 必驗 universal applicability）|
| **M72** 🔒 | **CapCut Export 完成後 mp4 file lock — 必先 Copy-Item → Kill CapCut → Remove duplicate** (2026-05-25 某支片 v3 agent 報告)| Export agent 想 rename mp4 為 target filename → `Move-Item` / `Rename-Item` 全 fail（File is being used by another process）— CapCut 還握著 file handle | **Post-Export rename pattern**：<br>```powershell<br># 1. Copy first (succeeds even with lock)<br>Copy-Item "teaching-longform.mp4" "teaching-longform-v3-fixed.mp4"<br># 2. Kill CapCut (release lock)<br>Stop-Process -Name CapCut -Force -ErrorAction SilentlyContinue<br>Start-Sleep -Seconds 2<br># 3. Now safe to remove duplicate<br>Remove-Item "teaching-longform.mp4" -Force<br>```<br>→ **不要試** `Move-Item` / `Rename-Item` on freshly-exported mp4 — 永遠 fail<br>→ 寫進 [capcut-agent-brief-template.md](capcut-agent-brief-template.md) Post-Export filename 章節必含<br>→ Alternative (next time)：brief 改成「accept CapCut default filename，整個 task 結束後 main session 來 rename」|
| **M73** 🔧🔥 | **Helper code mutate text 必同步 styles[].range — 否則 render 出 GIANT 字 bug** (2026-05-26 某支片 v3 用戶看到畫面直接罵才抓到) | M69 `apply_subtitle_corrections()` 改 `cloud`→`Claude` (5→6 chars) 但 styles[].range[1] 沒同步更新。超出 range 的字元用 default fallback style 渲染 = 巨大字 + 黑色圓角 box overlay。12 個 caption 中招（Claude/Code/Studio/Render/Debug 後綴字元全爆）| **永久 fix M69b**：text mutation 後**必同步**：<br>1. `styles[].range[1] = len(new_text)` (if covered full text)<br>2. `subtitle_keywords.range` (per-keyword highlights)<br>3. `words.text` (per-character timing) — if word count changed<br>4. 任何 text-length-dependent metadata field<br>**通則 (Mode C #2 AP12)**: helper code mutate 任何 data field → MUST 同步所有 dependent metadata。寫 helper 必問：「這個 mutation 會破壞哪些 invariants？」逐一 sync。<br>→ Verify 方法: `assert all(s.get('range', [0,0])[1] == len(text) for s in styles)` build-time check |
| **M74** 🔌🐚 | **Bash tool 把 inline `powershell -Command` 中的 `$_` 吃掉 — 必用 `.ps1` 檔 + `-File` mode** (2026-05-26 某支片 v4 agent 報告) | Agent 用 `Bash('powershell -Command "... ForEach-Object { $_.MainWindowHandle }"')` → Git Bash 在 routing 時把 `$_` 解釋為 shell 變數展開為空 → PowerShell 收到的 command 缺 `$_` → ForEach-Object 行為錯誤 | **新規 — agent PowerShell 統一寫成 `.ps1` 檔再 `-File` 呼叫**：<br>```python<br>Write('temp_script.ps1', '...PowerShell script with $_, $cap, $env etc...')<br>Bash('powershell -NoProfile -File temp_script.ps1')<br>```<br>**重要**：`-ExecutionPolicy Bypass` 被 classifier 拒絕 — **不要加**。`-File` mode without `-Bypass` works fine。<br>→ 寫進你的 CapCut agent 定義檔 Phase 1 + 任何 PowerShell call 都改用 .ps1 file pattern |
| **M76** 🎤❓ | **Plan content 前必先 ask 用戶實際工作 source artifacts — 不要 assume「高大上」formal artifacts** (2026-05-26 某支片 plan 用戶罵「我根本沒寫 prompt」)| 我 plan 某支片 假設「100+ prompts」用戶會有 prompt library，user 其實是 conversational 一來一回。M10/M37/M44 同類延伸 — 「假 content 比 missing content 危險」| **新規 — pre-plan content 第一句必問**：「**你實際的 source 是什麼？**」<br>- prompt library? OR Claude.ai chat thread?<br>- 文件結構化 SOP? OR 散落的 Discord 訊息?<br>- 影片時長精算? OR raw 直覺剪?<br>**M76 觸發 keywords**：plan 階段任何「假設用戶有 X 結構化材料」前先反問。<br>**通則**：assumption-driven content brief = M10 / M37 / M44 / M76 同一根。Pipeline 第一問永遠：「**describe what you actually have，not what would be ideal**」|
| **M77** 🧬🎭 | **參考人物 reference = 借技法不借人格 — INTEGRATE with 用戶 signature 不 REPLACE** (用戶要求「應該整合不是叫我模仿」)| 把某 viral short playbook 寫成 MANDATORY default → 強迫創作者錄 silhouette / hand-on-chin pose（reference 的 F1/F2）→ 完全違反創作者既有「**你自己的品牌 outro / 訂閱提示 / 你的社群 CTA + 結尾招牌字卡**」signature（**注**：原本誤判創作者有「客廳 talking head」signature，後 M78 retract — 該創作者從不錄 talking head 也不露臉）| **新規 — reference person playbook 寫進 SKILL 時必含 integration matrix**：<br>每個 reference 技法分 3 類：<br>- ✅ **INTEGRATE** (universal craft，無人格衝突) — A 節奏 / B3-B4 視覺 / D 聲音 / E promise<br>- ⚙️ **CALIBRATE** (技法套但程度依用戶舒適區調整) — D1 LUFS、G 極端化<br>- ❌ **REPLACE** (用戶已有 signature 互斥) — reference F1 silhouette vs **你自己的品牌 outro 卡 (可無人入鏡)** / reference hand-on-chin vs **你自己的結尾招牌句字卡**<br>**通則**：reference = pattern library 不是 personality clone。用戶 voice 是 constant，technique 是 variable。寫進所有 *-perspective.md 類 SKILL 觸發要明示「**用 X 視角分析**」≠「**變成 X**」 |
| **M78** 🎥❓ | **Production setup constraints 必先 verify — 不要從 reference video 假設用戶拍攝能力 / 出鏡偏好** (2026-05-26 用戶罵「我從來沒錄過 talking head，沒露過臉」) | M76 同類延伸到 PRODUCTION 層面 — 從 reference video audit 推測創作者有 "Living room talking head outro" signature，寫進剪輯招牌 memory 檔當 canonical。創作者後來澄清**從來沒露過臉**。recommend 的 reference A1/F1/F2 全 talking head 招數整套 broken | **新規 — pre-plan content 第二句必問**（M76 是 source artifacts / M78 是 production setup）：<br>「**你能/願意錄 talking head 嗎？露臉嗎？**」<br>- 純 voice + screen rec 派 vs 露臉派<br>- 客廳 vs 工作室 vs 外景<br>- 三腳架 / 環形燈 / mic 等器材限制<br>**通則**：reference video audit 是 **assumption**，須跟用戶 verify 為 fact 後才能寫進 memory。任何「用戶有 X production capability」前必 ask。寫進 `PRE_BUILD_CHECKLIST_*` Q1 之前必含「**production setup verify**」preamble |
| **M60 v2** 🖥️🚨 | **M60 升級 MANDATORY auto-enforce — 任何 screen rec import 前必跑 `clean_screen_recording()` 否則 Chrome+taskbar 全程露出** (2026-05-26 某支片 v6c 用戶罵「我不是叫你以後我螢幕錄影上下的工具列要自動切除!!!! 寫進去 skill」) | 某次 v6 為了修內容主題 mismatch 把 42.5s 完整產品 OBS 螢幕錄影 raw re-import 取代 25.8s trimmed copy，但**沒跑 M60 crop** → 全段 t=25.5-55.5s 有 Chrome tabs + URL bar + Windows taskbar 露出。M60 規則早就寫了但 import 流程沒 enforce trigger | **永久 fix 4 處**：<br>1. `PRE_BUILD_CHECKLIST_TEACHING_LONGFORM["defaults"]["screen_rec_auto_clean_on_import"] = True` ✅<br>2. `wraps_lessons` 強調 M60 v2 ENFORCED<br>3. `verify_steps` 加 VERIFY 5b — ffmpeg 抽 OBS time frame 確認無 Chrome / taskbar<br>4. **黃金規則**：任何 raw screen rec file (.mp4 / .mov from OBS) 進 CapCut assets folder **前** 必 pipe through `clean_screen_recording(top=200, bot=80)` — 沒例外<br>**通則 (Mode C #4 候選 AP)**：規則寫進 SKILL ≠ enforced。**necessity 必須通過 helper auto-trigger，不是依賴記憶 / brief 提醒**。M60 v2 是 M60 → enforced 的升級。下次任何 lesson 必問「這條怎麼自動 enforce 不靠記」 |
| **M79 v2 (2026-06-01 修正)** 🎵🔁 | **BGM 必須 loop 填滿整支影片 — smooth crossfade 接縫，畫面還在播音樂就不能停** ⚠️ **推翻原 v1 的 no-loop 規則** (2026-06-01 用戶看 v12 後段音樂停掉罵「這邊開始音樂就沒有循環了，我不是說過要循環嗎」) | ⚠️ **我 2026-05-26 誤讀** 原話「你要配合畫面播完才行，就在繼續重播同一首」→ 當成「不要 loop」做成 **fade-out + silence**（142s 後沒音樂）。真意是：BGM 短於 video 要 **loop 填滿全片**，原始抱怨是 CapCut **硬 restart 的接縫突兀**，不是 loop 本身。BGM.mp3=142s / video~172s → 後 30s 變純人聲沒配樂 = 錯 | **永久 fix（修正版）**：<br>1. **BGM loop-fill + crossfade**：BGM source < video → loop 填滿到結尾，接縫用 **1.5s crossfade**（song-end ⨯ song-start 疊化）平滑接回，**絕不 fade-to-silence**。落地寫法：收尾腳本用 `adelay`+`afade in`+`amix(normalize=0)` 在接點做 crossfade 續播<br>2. ✅ `force_mix_bgm()` helper 已落地 (2026-06-01 audit「修」)：`loop_fill=True` (新 DEFAULT) + `_bgm_loopfill_chain()` 用 `asplit`+`acrossfade` loop 填滿（自動算 N 份 copies）+ self-test（acrossfade=YES / apad-silence=NO）；`no_loop=` 保留 deprecated alias 向後相容<br>3. `PRE_BUILD_CHECKLIST_TEACHING_LONGFORM["defaults"]`：`bgm_no_loop` → **`bgm_loop_fill: True`**<br>4. `verify_steps` VERIFY 5c 改 — 確認**全片都有 BGM**（astats 檢查 post-142 period 仍有音樂能量 + 接縫無爆音），不是「確認後段降為靜音」<br>**通則（最高層）**：「**畫面還在播，音樂就不能停**」。M79 真教訓 = **別把用戶的「接縫做好一點」誤讀成「拿掉整個功能」**（同 M78 把 signature 誤 retract 的反向錯）。聽到「重播」抱怨先問是「不要 loop」還是「loop 接縫要平滑」。CapCut audio `duration` 仍不能信，ffprobe verify source |
| **M81** 🎞️⚠️ | **Source asset fps MUST match timeline fps 才 import — 否則 CapCut frame timing 錯誤 → 播放速度 bug** (2026-05-26/27 某支片 v7b 用戶罵「有一段背景打字速度變超快」) | Stock b-roll (laptop typing / book flip / coffee / meeting) 都是 **24 fps** source，但 CapCut timeline export 是 **30 fps** → CapCut frame insertion 不順 → typing motion 看起來 ~1.25x speed up。中招的是那批外購 stock asset（占了該片一半以上的 b-roll 段） | **永久 fix 4 處**：<br>1. **黃金規則**：任何 raw asset import CapCut 前必 ffprobe `avg_frame_rate` → 若 ≠ timeline target fps (default 30) → 必 `ffmpeg -vf fps=30` 預處理<br>2. `PRE_BUILD_CHECKLIST_TEACHING_LONGFORM["defaults"]["assets_match_timeline_fps"] = True`<br>3. `verify_steps` 加 VERIFY 0b — `ffprobe -select_streams v:0 -show_entries stream=avg_frame_rate` 全 asset = 30/1<br>4. `run_full_audit()` R1 升級 — 加 fps mismatch detection alert<br>**通則 (Mode C #4 候選 AP 同 M60 v2 / M79)**：規則寫進 SKILL ≠ enforced，必須**自動化檢測 + 預處理**。M81 是 M60 v2 / M79 同類「規則→機制」升級。<br>**Source fps 常見值**：24 (cinematic stock) / 25 (PAL) / 29.97 (NTSC) / 30 (digital) / 60 (high-frame). 一律 normalize 到 timeline target (default 30) before import |
| **M82** ⏱️✂️ | **Timeline duration MUST trim to voice 真結尾 — 不能讓 video duration > voice end** (2026-05-27 某支片 v10 用戶罵「v10 結尾全部沒對到」) | CapCut timeline 預設 210.8s 但人聲只到 165.7s → 165.7-210.8s = 45 秒 b-roll 殘留 + 完全靜音 = ship blocker。看起來像「斷片」 | **永久 fix**：<br>1. ✅ **helper 落地 2026-05-29**：`capcut_helpers.post_export.detect_voice_end()`（silencedetect 找人聲真結尾）+ `trim_to_voice_end(input, output, tail_pad_sec)`（trim 到結尾 + outro pad，預設 player_safe 重編）— **已對一支實際出貨成片 smoke-test：total 171.7s / voice_end 165.4s / 6.3s silent outro，數字吻合**<br>2. `PRE_BUILD_CHECKLIST_TEACHING_LONGFORM["defaults"]["trim_timeline_to_voice_end"] = True`<br>3. `verify_steps` 加 VERIFY 0c — `silencedetect=noise=-30dB:d=2` 末段超過 5s silence = FAIL<br>4. Outro card 直接 tpad 在 voice 結束後 5-7s（不是讓 b-roll 撐到 timeline 末）<br>**通則**：timeline 長度由人聲（content）決定，不是讓素材（form）決定。Audio-driven cut，not asset-driven。寫進 audio invariants checklist |
| **M83** 📺🔢 | **Player time counter 可能跟 file PTS 對不上 — 對 PotPlayer 等 player 友善用「保守 encode profile」** (2026-05-27 某支片 v11 用戶看 PotPlayer 時間軸顯示不對 → 誤判為檔案 bug) | v11 NVENC 編 + B-frames + faststart → PotPlayer 時間 counter 顯示 01:55 但實際畫面是 t=56s 內容（offset 59s）。ffprobe PTS 正確 30fps 連續，YouTube 完全沒問題 — 是 PotPlayer 對 NVENC B-frame ordering 的 quirk | **永久 fix — 「保守 re-encode」profile 寫進 helper**：<br>1. 換 **libx264** 軟編（非 NVENC）<br>2. **`-bf 0`** 完全無 B-frames<br>3. **`-vsync cfr -r 30`** Force CFR<br>4. **Closed GOP** (`-g 30 -keyint_min 30 -sc_threshold 0`)<br>5. **不加** `-movflags +faststart`（線性 moov box 在尾）<br>6. yuv420p / BT.709 / High@L4.1<br>→ ✅ **helper 落地 2026-05-29**：`capcut_helpers.post_export.reencode_player_safe(input, output, fps=30, crf=18)`（6 點 profile 由 `_player_safe_vcodec_flags()` 單一來源管，DRY；audio `-c:a copy` 不動）。**之前 v11 是手打 ffmpeg flags — 現已固化避免下次重組（M83 自己的「規則→機制」教訓現自我兌現）**<br>**通則**：file integrity 跟 player display 是兩回事。任何 player counter / sync 異常 → 先用 ffmpeg `-ss + frame extract` 確認 file 對到再決定是否 re-encode。不要直接信 player。寫進 final-ship checklist |
| **M84** 🔍🌐 | **Cross-file 數據 / 名詞更新必須「全域 grep 收尾」— 不能只信 agent 局部 audit OR 改幾處就宣稱完成** (某次要「仔細檢查」，連掃 3 輪才把一個 config value 散落多檔的十幾處 active 殘留全清；後來該值再次變動又全域近 30 處) | 第一輪 spawn audit agent 只掃 5 個 SKILL.md 頂層，沒深入 references/ + 各 log + playbook → 漏十幾處。我卻已宣稱「全 fix 完」。同類：talking head retract 殘留、版本號 drift、品牌名改名 — 任何「同一個值散落多檔」的更新都有此風險 | **永久 SOP — cross-file 值更新 3 步**：<br>1. **先 grep 全域抓總數**：`grep -rn "舊值" skills/ memory/` 列出**所有** location（不是憑記憶列檔案）<br>2. **批次 replace**（Python UTF-8 安全 / replace_all）— 不要逐檔手改漏掉<br>3. **收尾再 grep 驗證殘留 = 0**（排除 ground-truth sample / 歷史 artifact / `_archive` / `.pyc`）<br>**配套判斷**：<br>- ✅ active 引用（動員數字 / 規格 / 預設）→ **必更新**<br>- ❌ 用戶真實腳本 sample / 歷史紀錄 cut plan → **保留原值 + 加註**（M10 不竄改 ground truth）<br>**通則（最高層 meta）**：「agent 回報完成」「我改了幾處」**≠「全域乾淨」**。宣稱 done 前的最後一步永遠是「全域 grep 驗證殘留為 0」。這是 trust-but-verify 落到 data-hygiene 層。同 M60v2/M79/M81「規則→自動機制」家族：verify 必須是機械式 grep，不是人為記憶 |
| **M85** 📦🔧 | **B-roll 素材入庫必 auto-normalize — strip audio (M29) + conform fps (M81) 固化成 helper，不靠人手動** (2026-05-29 用戶在 transitions/ 又塞 10 個 24fps + 帶 BGM 的 AI 素材，要求去音樂；發現每次新素材入庫都手動 ffmpeg) | M29 (b-roll strip audio) + M81 (fps conform) 都是已知規則，但沒有「素材入庫一鍵」helper → 每次有人丟新素材進 transitions/ 都靠我手動 ffprobe + ffmpeg strip + conform，且容易漏檔（新丟進來的那支第一次 ls 沒列到，而且**既有的舊 stock 一大半也是 24fps**，只修新檔等於沒修）| **永久 fix — helper 落地**：<br>1. `silent_vlog_maker.screen_rec_cleaner.normalize_broll_asset(path)` — 單檔智慧處理：純去音訊用 `-c:v copy -an` (無損)；fps 要改才 libx264 重編碼；已乾淨則 skip (**idempotent**)<br>2. `batch_normalize_broll_folder(folder)` — 全資料夾掃 + **M84 收尾內建** (跑完 re-grep assert `still_dirty=[]`)<br>3. 原檔自動備份 `_intake_bak/`（never_rm 可逆）<br>4. **黃金規則**：任何新 b-roll 丟進 `assets/broll/` → 跑 `batch_normalize_broll_folder()` 一行搞定，不手動<br>**通則**：「反覆手動做的 pipeline」= helper 候選。M85 是 M29+M81+M84 三規則的「執行層」整合 — 同 M60v2/M79「規則→自動機制」家族。判斷句：「這個動作我做第 3 次了嗎？」→ 是 → 固化 helper |
| **M86** 🎬⚖️ | **通用 b-roll 占比 MUST < 自己拍的主素材占比 + 同一 clip 不重複** (2026-05-30 用戶回報畫面重複、且通用素材蓋過主素材) | 某支教學長片 draft 的 b-roll 軌：**同一支通用 stock clip 被排進三個不同段落**，且通用素材的總時長**明顯超過**自己拍的主素材（generic 約 2:1 壓過 main）→ 觀眾一直看同樣的通用畫面、看不到真的東西 | **永久 fix — helper 落地**：<br>1. `broll_audit.audit_broll_main_ratio(segments, strict=)`（2026-06-01「拆」自 caption_broll_matcher.py；capcut_helpers re-export 不變）— by **timeline duration**（非 segment 數）算 main vs generic，assert `generic_s < main_s` + 抓 `repeats`（同 source clip >1 次 = 重複畫面）；`print_broll_ratio_report()` 印表<br>2. `classify_broll_role()` 路徑啟發式：transitions/broll/stock = generic；_cleaned/screen/demo/product 等 = main（未知保守歸 generic 不灌水 main；**hint 是 ASCII，自己語言命名的資料夾要自己擴充或改傳 `is_main=`**）<br>3. 修法兩槓桿：(a) 把通用段換成自己拍的主體錄影提高 main（開場與「揭曉」那種重點 beat 本來就該秀真東西而非 stock 空鏡）(b) 剩餘 generic 做**非重複 montage**（每 clip ≤1 次，新 AI 素材 + branded CTA clip 各歸位）<br>4. `PRE_BUILD_CHECKLIST_TEACHING_LONGFORM` 加 `broll_generic_under_main: True` default + `wraps_lessons` M86 + `VERIFY 6b`（→ 繼承到 `SCREEN_RECORDING_TEACHING`）<br>**通則**：b-roll 是調味、你自己拍的主體是主菜；通用素材永遠不能喧賓奪主。同 M60v2/M79/M81/M85「規則→自動機制」家族 — 機械式 assert 不靠眼睛數 |
| **M87** 🎬🔗 | **B-roll swap/重排後 MUST 重跑 caption-broll 內容比對 — 旁白同步 > 占比；占比優化不能犧牲「畫面=旁白」** (2026-05-30 用戶看 t=120「字幕跟聲音還有畫面都沒對上」) | 為了 M86 占比，我把某一段「講怎麼寫程式」旁白底下的 coding 畫面換成產品畫面 → 旁白在講寫程式但畫面是產品，語意錯位。根因：(a) M86 占比優化沒同時跑 AP15/M75 caption-broll 內容比對 (b) in-place swap 保留誤導舊檔名（檔名還寫著 coding，內容已換成產品畫面）→ 騙過 filename-keyed 的 AP15 | **永久 fix**：<br>1. **任何 b-roll swap/re-sequence 後必跑** narration↔broll 比對 — `audit_caption_broll_mismatch()` + `narration_broll_sync_report()`(M87 helper，吃顯式 content-map 不被檔名騙) + 人工 narration map（每段字幕在講什麼 vs 畫面顯示什麼）<br>2. **衝突時 AP15 內容比對 > M86 占比** — 寧可某段 generic 也要畫面對上旁白；占比用「修剪靜音尾巴(M82)」或「其他段補主素材」補救，不在語意錯的地方硬塞主素材<br>3. **in-place swap 不留誤導檔名** — 換內容就改檔名 OR 維護 content-map（M86/AP15 都靠它分類）<br>4. **演示型旁白**(「首先這是X／上面是Y／再來是Z」)= b-roll 必跟旁白節奏走，段內可拆「前段A+後段B」對齊主題切換點(一段 b-roll 不必只配一個畫面：旁白講到第二件事就在段內換到第二個畫面)<br>**通則**：M86(占比) 跟 AP15(內容對位) 是 **AND 不是 OR**，build/swap 後兩個都要 green。第一原則永遠是「畫面說的 = 旁白說的」，占比/構圖是其次 |
| **M88** 📱🎨 | **不露臉「網感」Reels/Shorts 模板 = 保留結構+爆色字幕能量、真人換 b-roll／螢幕錄影（M78 不露臉）；字幕規則 data-backed 不憑感覺** (2026-06-01 用戶「想訓練 Reels/Shorts 不同顏色大小的字」+「先做不露臉，旅遊美食也用得到」+「上網學習」) | 用戶看到的「網感模板」原型都是 talking-head 對嘴爆字幕 → 直接抄會違反 M78（創作者 從不露臉）。且早期若憑感覺做字幕（大小/位置/節奏隨意）→ 出界壓到平台按鈕區、字太小手機看不清、靜音觀看沒字幕=隱形 | **永久 fix — package 落地 `silent_vlog_maker`**：<br>1. **`shorts_template.py`**：`NETGAN_SHORTS_TEMPLATE`(face=False) 固定三段 hook/body/outro，niche 只換皮(`NETGAN_NICHE_PRESETS` 教學/旅遊/美食/理財 徽章+配色)；`render_hook_card()` 不露臉 hook 卡(b-roll 上疊爆色標題)；outro 永遠用你自己的品牌 outro 卡(M78/M77 F1 保留招牌)<br>2. **`shorts_captions.py`**：3-level 爆色字幕(clean/variety/pop) `style_caption()` + `render_caption_png()`(NotoSansTC-Black + 黑描邊)；2026 web 研究固化 → `chunk_caption()`(逐塊 2-3 詞**尊重詞邊界**) + `style_chunks_active()`(active word 高亮，78.6% 爆款特徵) + `SHORTS_SAFE_ZONE`/`safe_caption_y()`(避開上 20%+下 25%，出界 -22% watch time)<br>3. **`shorts_template.HOOK_FORMULAS`** 3 式(反差/踩雷/清單)×4 niche + `suggest_hook()`：前 3 秒=80% 完讀率變異<br>4. **reference 落地**：[shorts-reels-best-practices.md](shorts-reels-best-practices.md)(6 來源 OpusClip/Kreatli/Terra)；`__init__` 全 wire(103 exports)<br>**通則**：(a) 任何「網感/對嘴」原型先過 M78 濾鏡 → 真人換 b-roll/螢幕錄影，能量留結構與字幕不留臉；(b) 字幕參數(大小/位置/節奏) data-backed 不憑感覺，web 研究固化進 helper + 標來源；(c) 模板跨 niche 共用 = 結構固定、niche 只換徽章+配色+素材 |
| **M89** 📦🔓 | **開源/交接文件鐵則 — 主力工具定位不能反 + 隱性外部依賴必標需求 + onboarding 要有 minimum-viable 路徑** (2026-06-02 用戶開源 video-autopilot-kit 後回報 3 個洞：問卷填太久 / 別人會以為 ffmpeg 是主力 / 完全沒提醒要開 Computer Use) | 我開源時 (a) **需求清單把 ffmpeg(次要)列「必需」、CapCut(主力)列「選用」** — 主次顛倒，陌生人照做會拿次要工具當主力；根因是我順手先寫 ffmpeg 那段就讓它變預設 (b) **全篇沒提 Computer Use** — 但 CapCut 沒公開 API，整個 `capcut_helpers` 自動化都靠 AI 透過 Computer Use 操作 GUI，沒開根本跑不動 = 採用者必卡 (c) **6 區問卷要全填才能開跑** → 採用者嫌久棄坑 (d) README 引用**不存在的 `docs/`**(broken link) | **永久 SOP — publish/交接前 4 查**：<br>1. **主次定位 review**：文件要讓「主力路徑」讀起來就是 default；次要/實驗實作路徑明標「非主力、限 X 情境」。**「必需 vs 選用」清單對齊真實主力**(不是對齊我先寫好的那條)<br>2. **隱性外部依賴必置頂標需求**：工具「實際怎麼跑起來」背後的依賴(Computer Use / API key / 特定 app / 系統權限 / PATH 工具)= 硬需求。判斷句：「**拿掉這個，核心功能還能跑嗎？**」不能 → 必標<br>3. **onboarding minimum-viable 分層**：任何問卷/setup 要有「最小啟動」(★必答 vs ⭕選填) + 「丟給 AI 訪談你」低門檻路徑；**不能要求填完才給價值**<br>4. **cross-link grep 收尾(承 M84)**：publish 前 grep 所有 `docs/`/相對連結/引用資料夾是否真存在；中英雙語版同步改<br>**通則(最高層)**：開源/交接 = 把「我腦中的隱性知識」攤給陌生人。**我熟到忘了講的東西(主力是哪條、背後靠什麼跑、哪些可跳過)正是別人最會卡的**。Publish 前強制用「零基礎陌生人視角」自審 3 問：他會先用哪條路？他知道要開什麼依賴嗎？他能 5 分鐘跑起來嗎？同 M84「規則→機械式 grep 收尾」家族 |
| **M90** 🔌🌐 | **開源工具的「個人化設定」不能當 default 烤進邏輯 — 必須有零設定、語言無關的 fallback，個人資料只能當 opt-in 範例** (2026-06-10 採用者回報「自動剪輯出來畫面對不上字幕跟音檔」) | 公開 kit 的 caption-broll matcher 預設吃 `EXAMPLE_KEYWORD_MAP`(作者的個人主題:topic-1/topic-2/通用主題範例 + 連個人 OBS 錄影檔名都在裡面)。陌生採用者的字幕 match 不到任何 keyword → 全歸 generic → b-roll 按順序亂填 → **完全不跟旁白走**;非中文用戶 100% 全 miss。這是「把我的脈絡當成所有人的預設」的經典開源陷阱 | **永久 fix**：<br>1. **零設定、語言無關 fallback**：`_filename_caption_overlap()` 用「字幕文字 ↔ b-roll 檔名」共同 token(拉丁詞 + CJK 單字/bigram)對位 → 採用者只要把素材用內容命名(`coffee.mp4`)就自動對齊，不用任何設定<br>2. **個人 map 降為 opt-in 範例**：公開版 default 改 `{}`（純 filename 對位），`EXAMPLE_KEYWORD_MAP`(留 alias)，**清掉洩漏的 OBS 檔名/品牌**<br>3. **sequencer 也要 content-aware**：generic 字幕綁到各自最 match 的素材當 pseudo-topic（`__file__<id>`）→ 不會併成一坨；內容不同的短 cluster 不被 min_segment 合併<br>4. **大聲警告 + TROUBLESHOOTING**：多數片段沒對上 → `RuntimeWarning` 直接教怎麼修<br>5. **輸入合約寫清楚**：captions 要真 start_us/duration_us、b-roll 用內容命名、fps 先 conform<br>**通則**：開源工具的預設行為要對「**沒有我的資料的陌生人**」成立。任何 hardcode 的個人 keyword/路徑/品牌/檔名 = 對採用者是雜訊甚至污染。**個人化走 opt-in（傳參數/填 profile），預設走零設定通用解**。同 M89「主力定位 + 隱性依賴」家族 — 都是「我的脈絡 ≠ 採用者的預設」|
| **M91** 🖥️🔒 | **全螢幕/桌面錄影 NEVER 直接當 b-roll — 會夾帶工具列/app 面板/瀏覽器分頁(含私人後台如 金流後台)；要秀「AI 操作 app」只能用乾淨裁切的單一視窗錄影 OR 乾淨 stock 示意** (2026-06-16 用戶看 某支片 罵「我不是說過不要出現工具列嗎…甚至還出現 金流後台」) | 某支片 把一段 **74 秒全桌面 OBS 錄影** 直接塞進其中一段當「Claude 操作剪輯軟體」walkthrough → 錄到了 Windows 工具列 + Claude「Background tasks」浮動面板 + CapCut 空專案閒置 + 中間一格瀏覽器是**一個私人後台（例如金流/營收/分析儀表板）**。另一段(12s 智慧助理)同病。兩段合計逾半支片長= chrome+隱私雙重洩漏，且畫面跟旁白語意全錯(私人後台畫面 配「很多人卡住」)。根因:**為了有「真實操作畫面」就把原始全螢幕錄影整段拿來用,沒裁切沒審查** | **永久 fix(本次)**:那兩段全換乾淨 stock 蒙太奇(對位旁白 M87),完全不用桌面錄影;「操作剪輯軟體」梗改用乾淨 Claude UI stock 當示意(b-roll=示意非舉證,Claude 確有剪只是畫面太髒太空不能用,不違 M10)。**SOP 永久化**:<br>1. **任何螢幕/桌面錄影進剪輯前先過「chrome 審查」**:工具列/工作列/瀏覽器分頁列/浮動視窗/通知/其他 app = 全部不能入鏡。要用 → **裁切到只剩目標視窗的內容區** (crop 掉 taskbar 底部 + 任何側欄/面板)<br>2. **隱私掃描**:錄影裡有沒有金流後台(營收/Stripe/PayPal/Analytics)、email、檔名路徑、私訊、API key → 有 → 該段不可用或馬賽克。判斷句:「**這格截圖直接公開,我會不會後悔?**」<br>3. **優先乾淨 stock 示意**:「AI 在做某事」多數時候用乾淨 stock(Claude UI / coding / 打字)示意即可,不必用我自己的髒桌面錄影<br>4. **交付前必跑 frame-audit**:抽整片接觸表(≤6s/格)+ 原本最可疑段落密集格,**逐格肉眼確認 0 chrome / 0 私人資料**(承 M9 看畫面 + M84 機械收尾)<br>**通則**:錄影檔的「畫面範圍」是內容安全邊界。**我看到的整個螢幕 ≠ 觀眾該看到的東西**。全螢幕錄影 = 預設有毒,要嘛裁乾淨要嘛換 stock。同 M9(看畫面)+ M86/M87(b-roll 紀律)家族;隱私面向接 never_rm/開源 sanitization 同源思維。<br>**M91b 補(2026-06-16 同回踩到):刻意截「目標 app 視窗」當素材時,置頂視窗(如 Claude Desktop always-on-top 面板)會偷渡進全螢幕截圖右側 → 必須裁到「只剩目標視窗內容區」並 frame-audit;光裁底部工作列不夠,右側/浮層也要裁。本回 folder 截圖第一版就漏裁右側 Claude 面板,抽幀才抓到。PowerShell `CopyFromScreen` 截原始螢幕(不遮罩),比 computer-use screenshot(會 mask 非授權 app)更會漏 → 截完務必抽幀檢查四邊。** |
| **M92** 🖼️🌫️ | **圖片/截圖入片 3 鐵則:非滿版→模糊背景填滿、靜止不抖、截圖裁到只剩內容區(用戶招牌規則,2026-06-16「我講過了難道你忘了」)** | 我把 CapCut 時間軸 + 素材資料夾截圖剪進 某支片,犯三錯:(a)非 16:9 滿版卻用**死黑邊**(用戶要模糊背景);(b)用 ffmpeg `zoompan` 推鏡 → **pixel 抖動**(用戶「一直抖動」);(c)素材資料夾放了整個檔案總管 → **側欄磁碟機/OneDrive 路徑全露**(用戶「我的電腦畫面都露出來了」) | **永久鐵則(每次圖片/截圖入片必套)**:<br>1. **非滿版 → blurred-fill**:`[0]scale=...increase,crop=1920:1080,gblur=sigma=26,eq=brightness=-0.12[bg];[0]scale=1920:1040:decrease[fg];[bg][fg]overlay=center`。**禁死黑邊/純色邊**<br>2. **靜止不抖**:`zoompan` 會 pixel 抖 → 預設**靜止**(loop 圖,無位移);要運鏡只能用真正平滑法,不確定就靜止<br>3. **截圖裁到只剩內容區**:app 內容區/縮圖牆 only,**裁掉 OS 外框**(工具列/側欄/磁碟/路徑/標題列/其他視窗)— 承 M91,但 M91 偏「意外洩漏」,M92 偏「刻意放截圖也要裁乾淨+排版」<br>**通則**:圖片不是丟進去就好,要**排版**(滿版判斷→模糊填底)+**穩定**(不抖)+**乾淨**(只給素材本體)。同你自己的剪輯招牌「視覺技術鐵則」;這是 form 層(構圖/穩定/邊界)的創作者品味,跟 M87(內容對位)互補 |
| **M93** ⚡🌓 | **「畫面會閃」三因排查:頻閃素材(動作遊戲爆擊/strobe)、字幕盒空檔、cut 亮度落差 —— 交付前必跑 blackdetect 收尾** (2026-06-16 用戶「為什麼畫面有時候會閃」) | 某支片 三處閃:(a)用了 **某動作遊戲 b-roll**當「講到遊戲」b-roll → 暗場 + 不停閃的戰鬥特效(COMBO/爆擊/彈幕)= **本身頻閃**(blackdetect 在該段「黑↔亮」狂跳);(b)兩句字幕間 0.4s 空檔 → BorderStyle=3 黑底盒**閃掉再閃回**;(c)開場段 亮網格→暗遊戲標題→亮平台 = **亮度落差**像閃 | **永久排查 SOP(交付前)**:<br>1. **`blackdetect=d=0.05:pic_th=0.90` 跑全片** → 同一區段反覆 black_start/black_end 跳動 = 頻閃素材;單段持續偏暗 = 亮度落差<br>2. **頻閃素材換平穩段**:動作遊戲選**平台/解謎/選單**等平穩畫面,不選爆擊戰鬥;一般 strobe/閃光素材直接棄用(也是 photosensitivity 風險)<br>3. **字幕盒空檔填補**:`<0.5s` 的句間 gap → 前句 end 補到後句 start(box 連續不閃);make_ass 內建 gap-fill loop<br>4. **亮度落差**:亮→暗→亮的暗段換亮素材(或 setpts 放慢留在亮的部分);避免單一暗 clip 夾在亮 clip 間<br>**通則**:「閃」= 亮度時間軸不平滑。素材本身會閃(內容)+ 疊加層空檔(字幕盒)+ 接點落差(剪輯)三來源都要查。blackdetect 是機械收尾(同 M84 grep 家族),不靠肉眼盯整片 |
| **M94** 🎯🎥 | **旁白點名/回顧具體 artifact → 秀那個 artifact 的真實畫面,不用 generic stock 示意(showing-not-telling 的 b-roll 版)** (2026-06-16 用戶「你有沒有上一支影片的素材」+「這兩張圖你要剪進去:剪輯軟體時間軸、素材資料夾」) | 某支片 hook 點名了「我上一支影片／某個系列主題」我一開始配**隨便的 Claude/code stock** → 辨識度低、說服力弱。同理「拉時間軸/操作剪輯軟體」配隨便 code editor、「把原始素材丟給它」配綠碼雨 = 抽象示意,不是真東西 | **永久原則**:旁白**點名具體東西**就去找**那個東西的真實畫面**:<br>・「上一支影片/我做的 X」→ 該影片/專案**真實素材**(某支片:真實產品畫面 + 實際操作)<br>・「拉時間軸/操作剪輯軟體」→ **真實 CapCut 時間軸截圖**(裁乾淨+模糊填底 M92)<br>・「把原始素材丟給它」→ **真實素材資料夾**(縮圖牆)<br>・「講到遊戲」→ **真實遊戲畫面**(自我示範)<br>**判斷句**:旁白**具體**(點名某物)→ 畫面給**真實該物**;旁白**抽象**(概念)→ stock 示意可以。真實 artifact > stock 的辨識度與可信度。前提:該真實素材要過 M91(無 chrome/隱私)+ M92(排版)+ M93(不閃)。承 M87(內容對位)往上一層:不只「主題對」,而是「**同一個東西**」 |

| **M95** 🎙️✂️ | **句間死空檔(錄音停頓 3-4s)要剪到 ~0.5s — 整支同步收緊;移除音訊區段用 `atrim+concat` 不要 `aselect`** (2026-06-16 用戶「這段怎麼有停頓一陣子才接下一句」) | 某支片 人聲錄音句子之間停 **3-4 秒 × 5 處**(silencedetect 抓到 22.5/52/101/131/144s),字幕+畫面卡在那邊等 → 整支拖(162s)。第一版我用 `aselect='between(t,..)+..',asetpts=N/SR/TB` 剪音訊 → **完全沒剪掉**(164.42→164.31),害我把沒剪的原聲截斷、結尾被切 | **永久 fix**:<br>1. **silencedetect 找死空檔**:`silencedetect=noise=-30dB:d=0.6` → `>1.5s` 的句間停頓 = 死空檔,各剪到 **~0.5s**(留自然呼吸)<br>2. **音訊移除區段用 `atrim+concat`**(可靠):每個 keep-range `[0:a]atrim=a:b,asetpts=N/SR/TB[vi]` 再 `concat=n=N:v=0:a=1`。**`aselect+asetpts` 對音訊常常不真的丟 frame** → 別用<br>3. **三軌同步**:人聲(atrim)、畫面(`select='between..',setpts=N/FRAME_RATE/TB` — 這個 video 版可靠)、字幕(時間戳用同一 remap() 函數平移)= 用**同一組 cut 區間**砍,自動對齊<br>4. **BGM 重鋪不跳**:不要剪混音檔(BGM 會跳),要 `cleaned_voice + BGM(*0.22 loop + fade)` 重混 → BGM 連續<br>5. 交付前 silencedetect 複查:無 `>0.8s` 句間停頓<br>**通則**:節奏 = 沉默的控制。錄音的自然停頓 3-4s 對觀眾太長(YT 教學片句間 ~0.3-0.6s)。死空檔 = 拖。同 M82(trim 尾)家族,但 M82 剪尾、M95 剪句間。技術點:**移音訊段 atrim+concat,移影像段 select+setpts**(別混用) |

| **M96** 📱🍜 | **美食/旅遊直式 Shorts pipeline（純 ffmpeg + 多色重點字幕 + GPS 地址）— 2026-06-20 某旅遊 Short/某秘境 Short/某美食店 3 支落地** | 用戶丟 iPhone .MOV 到直式素材收件匣（本 kit 預設 `videos/_INBOX/shorts/`，可用 `VIDEO_KIT_SHORTS_INBOX` 覆寫），要美食旅遊風 Shorts、重點字不同色、放地址、菜名對位。踩 4 雷：(a)iPhone .MOV 是 1920×1080+rotation 旗標、**同批混 -90/+90**（某 clip 拿反）→ 不正規化會歪；(b)ASS inline `\c&H..&` **沒包 `{}`** → 被當文字印出；(c)emoji(⭐📍😋)在 NotoSansTC **render 成豆腐框**；(d)**菜名↔clip 配錯**(A 道/B 道對調，M9 抽幀才抓到) | **永久 pipeline（silent footage Short）**:<br>1. **旋轉正規化**:`ffmpeg -i clip -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1" -an`（ffmpeg 預設 autorotate 套 rotation 旗標 → 全部 upright 9:16；混向也統一）<br>2. **GPS→地址**:`ffprobe -show_entries format_tags=com.apple.quicktime.location.ISO6709`抽 GPS → WebSearch 反查地名+地址（用戶要放地址；GPS 海拔還能驗景點 vs 平地）<br>3. **多色重點字幕**:ASS inline color **必包 `{}`** → `COL={'o':r'{\c&H008CFF&}',...}`（BGR）；白底 + 橙黃紅綠 highlight 重點詞；NotoSansTC-Black 124px 厚黑描邊(2026-06-22「字太小」回饋從 82 放大；上限~124,WrapStyle=2 不自動換行→長句加 \N)；安全區 `\an5\pos(540,1180)` 中下（避上 384/下 1440 按鈕區）；地址 BorderStyle=3 半透明黑底小字 y≈1390<br>4. **emoji 移除**（libass+NotoSansTC 無 emoji glyph → 豆腐框；要 emoji 改 PNG sticker overlay M40）<br>5. **菜名/字幕↔clip 抽幀驗**（M9/M87；美食 Short 每 clip 一道菜，配錯就糗）<br>6. BGM 當主音（無人聲）loop+fade，vol 0.40-0.45<br>**helper 落地(2026-06-20 升套件)**:`from silent_vlog_maker import build_one_short, normalize_to_portrait, build_multicolor_ass, extract_gps` — `build_one_short()` 片段→多色字幕→配樂 pipeline;`build_multicolor_ass()` 內建 strip_emoji(M38 防呆);`normalize_to_portrait()` autorotate 處理混向(含 -90/+90)；`delivery_qa._run` 加 `encoding=utf-8`(中文路徑 crash fix)<br>**通則**:直式 Short = 正規化(旋轉/尺寸) + 多色字(包 brace) + 真資訊(GPS 地址/菜名抽幀驗)。同 M81(fps)/M88(不露臉模板)家族 |
| **M97** 🧪🎬 | **helper 的 self-test 不能 mock 掉外部工具(ffmpeg/ffprobe)— 跳過真執行 = integration bug 出貨;新 pipeline 至少跑一次真 end-to-end 才算驗證** (2026-06-22 剪一批真 Shorts 才抓到 v0.3.1 出貨的 build_one_short/_probe_wh 兩 bug) | shorts_vertical / delivery_qa 的 `__main__` self-test 只驗 ASS 生成 + regex 解析(純字串),**跳過真正的 ffmpeg 燒字 + ffprobe 探測** → v0.3.1 上架時兩條 runtime 路徑從沒跑過。真的拿去剪 Shorts 一跑就炸:(a)**build_one_short caption**:ass filter 值含 Windows 碟符冒號(`C:`/`E:`… 任何磁碟代號)被當選項分隔(original_size error);舊碼第一次嘗試用 basename 卻**忘了設 cwd**、fallback 又帶完整冒號路徑 → 兩條都壞;(b)**_probe_wh**:`ffprobe -of csv=p=0:s=x` 在 Windows 吐 `1080x1920x\r`(尾端多餘分隔+CRLF),`split('x')` 拿到 3 段 unpack 爆掉 | **永久 fix**:<br>1. **ASS 路徑**:燒字幕一律 `cwd=out目錄` + `ass=<basename>`(相對路徑,無冒號);別用完整路徑(`ass=<碟符>:/..` 的冒號必炸)<br>2. **ffprobe 數字解析**:用 `re.findall(r'\d+', stdout)` 取數字,**不 `split('x')`**(尾端分隔/CRLF 免疫)<br>3. **self-test 補 parser regression**:把踩過的真實輸出字串(`"1080x1920x\r"`)寫進 assert<br>4. **新 pipeline 驗收門檻**:純字串 self-test **不算驗證**;至少跑一次「真檔→真 ffmpeg→看成品幀」end-to-end 才能宣告 ship(這次靠剪 3 支真 Shorts 才驗到)<br>**通則**:mock 掉外部工具的 self-test 只測你的字串拼接,測不到「工具實際吃不吃這參數」。**integration bug 只有真執行抓得到**。同 M83(canon-code drift)/M84(機械收尾)家族,但這條針對「驗證盲區」 |
| **M98** 🎵🔥 | **Shorts BGM 要落在歌的「高光時刻」(副歌/drop),不是從前奏 0:00 播 —— 整支短片騎在歌最 energetic 的那段** (2026-06-22 用戶「音樂要抓高光時刻,不是每首歌都適合重頭開始播,你應該知道啦 shorts」) | 直式 Short 只有 15-25s,很多歌前 10-20s 在鋪陳/前奏,從頭播 = 把黃金秒數浪費在最無聊段落。Shorts 觀眾滑很快,BGM 一進來就要有 energy | **永久 fix(helper 落地)**:`find_music_highlight(bgm, dur)` 用 **ebur128 短期響度 S(3s 滑動 LUFS)** 當 energy proxy,滑窗找平均響度最大的 dur 秒窗 → 回起始秒;`build_one_short(..., bgm_start='auto')` 預設自動抓高光(也可給數字手動 / 0=從頭)。mux 用 `-ss {start} -stream_loop -1 -i bgm` 從高光起播 + 0.3s 快淡入(避免從歌中間硬切爆音)+ 結尾淡出。**踩雷**:ebur128 逐幀 `t:/S:` 行印在 stderr,加 `metadata=1` 反而**關掉**那些行 → 偵測別加 metadata=1。實測 3 首 BGM 都挑到比開頭響(其中一首跳過安靜前奏 -17→-13 LUFS)。**通則**:BGM 是 Shorts 的節奏引擎不是背景填充,**抓高光 = 第一秒就有能量**。承 M79(BGM 不重播)家族,管「從歌的哪裡開始」。出貨前真跑一次 mux(M97) |
| **M99** 🎚️🔊 | **BGM「忽大忽小」靠 `acompressor` 壓平,不是 dynaudnorm/loudnorm(實測無效);且 BGM 別用比影片短的曲(loop 接縫跳音也是忽大忽小)** (2026-06-23 用戶「音樂不知道為什麼忽大忽小」) | 動感 BGM(快剪/Vocal Chop)有副歌/breakdown 起伏,固定 volume 壓不掉 → 影片中段音量突然變小。我先猜是動態大套 dynaudnorm/loudnorm → **實測 swing 8.1→8.6/8.4 dB 完全沒用甚至更糟**;且當時挑的那首 BGM 只有 10-19s 比 17s 影片短 → `-stream_loop` loop 回開頭,**接縫處音樂跳掉**(某步道 swing 15.4 dB) | **永久 fix(已落地 build_one_short)**:<br>1. **壓縮器壓平動態**:`acompressor=threshold=-24dB:ratio=4:attack=15:release=200:makeup=3` → 把大聲峰壓下貼近安靜段,**但保留每拍瞬態(beat 不死)**。實測 swing 8.1→**3.9 dB**(dynaudnorm/loudnorm 都 8+,只壓縮器有效)<br>2. **選曲要 ≥ 影片長**:`_probe_dur(bgm) < total` → 警告 + 換更長的曲;**別硬 loop 短曲**(接縫跳音)。穩健做法:候選清單裡挑「夠長 + 壓縮後 swing<5」的<br>3. **驗收量化**:量成品 momentary 響度 **swing(去頭尾 fade 後 max-min)< 5 dB** 才算平;7 支實測 1.9-4.5 dB<br>4. **診斷盲區教訓**:LRA 指標看起來低(2-5 LU)會誤導你以為「已經平」→ 要看**時間軸響度曲線**才看得到中段 breakdown 的凹陷(承 M9 看畫面 → 這是「看波形」)<br>**通則**:BGM 一致性 = 壓縮(壓動態)+ 選夠長(免 loop)+ 量化驗收(swing<5)。氛圍 normalize(dynaudnorm/loudnorm)解的是「整體響度對齊」,不是「時間軸內忽大忽小」——**工具要對症**。承 M98(抓高光)家族,同管 BGM 但這條管「音量一致」|
| **M100** 🔒🧹 | **公開 release 去個資:單次 grep gate ≠ 乾淨 — 要對抗式多輪掃描(語意+三角定位角度)loop 到「整輪 0」才算收斂** | 一個 repo 過了「whole-repo grep 0 殘留」就上架,但更深的多-agent 稽核 + 數輪對抗驗證又陸續抓到 grep 抓不到的洩漏:**語意指紋**(招牌剪輯組合 / 個人 sign-off / paraphrase 過的真實貼文)、**跨檔三角定位**(職業 + 地區 + 常用論壇 + 出沒場合拼起來能反推本人)、**grep 想不到的 token**(綁定真實主題的 emoji、真實菜名/地名、來源檔名、GPS 座標、個人網域)。**單次 grep 只抓「你想得到要搜的字串」,抓不到語意層與跨檔線索** | **永久 SOP(任何公開 release 去個資)**:<br>1. **grep gate 是必要非充分** — 過了只代表你列的 token 乾淨,不代表乾淨<br>2. **對抗式多輪 × 多角度**:每輪 ≥4 個 fresh-eyes 掃描器跑**不同角度**:① 硬識別(域名/路徑/檔名/座標/版本號) ② 語意指紋(招牌/sign-off/真實貼文 paraphrase/品牌) ③ 三角定位重建(假設陌生人拼湊跨檔線索能否定位到「某個人」) ④ code/doc 一致(消毒誤傷的 hex/數值、placeholder 半替換、舊例殘留)<br>3. **loop-until-dry**:每次修完**重跑整輪**;**沒有一輪回 0 就不准 ship**<br>4. **allowlist 先寫進 brief**:刻意保留的(作者署名 / 通用工具名 / back-compat alias / 通用同音字)列清楚,免每輪重複 flag<br>5. **緊急權衡**:若舊版硬 PII 已公開,**儘早推「清掉硬 PII」的版本 > 無限追極細 niche 指紋**(niche / 職業類「窄但定位不到人」的揭露是開源工具本質,非個資)<br>**通則**:去個資是**對抗賽不是 checklist** —— 你寫 grep 時的盲區,就是洩漏藏的地方。同 M84(全域收尾)+ M91(隱私邊界)家族,管「公開前的對抗式驗證強度」|
| **M101** 🎥🧹 | **自錄/螢幕錄影當素材的乾淨化:首選「目標 app 全螢幕重錄」不是事後裁;乾淨窗口可能在【中段】(頭尾兩端都髒);裁切要量不要猜;低解析接觸表會漏 chrome** (承 M60/M61/M91,自錄剪輯軟體操作 b-roll 再踩+收斂) | 用 `ffmpeg gdigrab -i desktop` 錄剪輯軟體操作當 b-roll,整個桌面都入鏡:旁邊的 AI agent 對話面板(內部 reasoning + 你的專案資料夾名)、其他視窗、app 標題列的自動儲存時間戳全洩漏;第一版只裁一塊/只裁工作列 → 接觸表縮圖看起來乾淨、全解析單格才看到殘留。又:採用者錄的「短影音」其實是整頁瀏覽器在播(書籤列 + 左側別人影片的推薦欄全入鏡);桌面錄影的錄影軟體/通知 UI 常在【開頭和結尾兩端都有】,乾淨段在中間 | **永久 SOP**:<br>1. **首選「重錄乾淨」不是「事後裁」**:目標 app **maximize 全螢幕**(直接蓋掉旁邊所有瀏覽器/AI 面板/IDE)再錄 → 只裁 OS 工作列 → 滿版乾淨。**app 自己的 UI(剪輯軟體介面)不算個資 → 別過度裁**(過度裁切到面板、留模糊邊,觀感更差,使用者會嫌「介面又沒個資幹嘛裁」)<br>2. **退路才事後摳**:只能用既有錄影 → 裁到「只剩目標視窗/播放器的內容區」。**裁切量要量不要猜**:裁一條頂部 strip 放大看,量出 chrome 底邊與任何「要保留的 UI 元素」(如某按鈕)的實際 y,再決定 crop(1080p 瀏覽器分頁+網址+書籤列常 ~150px,不是 80)<br>3. **乾淨窗口可能在【中段】**:錄影/浮窗 UI 常**頭尾兩端都有** → 逐秒(≤0.5s/格)dense 掃整支找乾淨中段,把擷取 **bound 在中段**(取乾淨核再 loop 填),別只跳開頭<br>4. **「短影音/網頁播放器」要摳播放器框**:整頁瀏覽器播片 → 書籤列 + 側欄(別人影片縮圖=版權+洩漏)都要去 → crop 到中央播放器矩形,不是只裁 top<br>5. **低解析接觸表會漏 chrome** → **每個主素材窗口都看一張全解析單格**,別只靠 tile 縮圖(縮圖會把「整頁瀏覽器」看成「乾淨直式」)<br>**通則**:自錄螢幕素材 = 預設整桌面有毒。**能重錄乾淨就別事後補裁**;非裁不可就量(不猜)+ 找中段乾淨窗 + 全解析複查。承 M60(裁 chrome)/M61(trim 兩端)/M91(內容安全邊界)/M92(截圖裁乾淨)家族 |
| **M102** 🐍🪟 | **Windows 跑 build script:stdout redirect 到檔/pipe 預設 cp950,`print()` 含 `≤`/`✓`/emoji 會 `UnicodeEncodeError` 把整個 build 炸掉 —— 互動跑沒事、背景/排程跑才爆(最難抓)** (背景重建長片時踩) | CJK locale 的 Windows,Python stdout 不是 tty(被 redirect)時用系統 ANSI codepage(cp950),非 cp950 字元(數學符號/勾號/emoji)編不出 → 第一個含那種字的 `print` 直接 raise,build 死在「印成功訊息」那行(實際運算都跑完了,死在報喜),只有背景/redirect 跑才會踩到 | **永久 fix**:<br>1. 每個 build script 頂端:`import sys` 後 `for s in (sys.stdout, sys.stderr): try: s.reconfigure(encoding="utf-8")\n except Exception: pass`<br>2. spawn 子行程帶 `env PYTHONIOENCODING=utf-8`<br>3. 讀 ffmpeg/子行程輸出用 `subprocess.run(..., encoding="utf-8", errors="replace")`(別讓它用 cp950 去 decode 別人的 utf-8 輸出又炸一次)<br>4. **背景/排程模式至少測一次**:很多 redirect-only bug 互動跑永遠遇不到 → 上 CI/背景前先在 redirect 模式跑一遍<br>**通則**:「互動能跑」≠「背景能跑」。stdout 是不是 tty 會改 Python 預設編碼。同 M97(self-test 要真 end-to-end)家族——這條是「執行環境」盲區 |
| **M103** 🎚️⚡ | **教學長片人聲要 pro 化 = acompressor 壓平 + sidechain duck BGM + two-pass loudnorm + room-tone bed；旁白嫌「講太慢」用 atempo 加速,但加速倍率必須一顆常數貫穿三檔(音訊/畫面/字幕)否則時間軸 desync** | 舊 build:人聲只有 `highpass+dynaudnorm`(normalizer 不是壓縮器→壓不掉忽大忽小)、BGM 固定 `volume` 死壓(人聲一來不讓位)、收尾單-pass loudnorm(估計、本身又是壓縮器會 pumping)、beat 間 `anullsrc` 死數位靜音;旁白語速固定。直接在成片上 atempo 會害字幕/b-roll 全部對不上(每句壓縮了但 caption/scene 還在舊位置) | **永久 fix**:<br>**① 人聲鏈**:`highpass=f=80,acompressor=threshold=-18dB:ratio=3:attack=15:release=250,atempo={SPEED},dynaudnorm=f=200:g=6`(acompressor 是真壓縮器壓平動態;atempo 保持音高加速)<br>**② room-tone bed**:concat 後鋪全長 `anoisesrc=c=pink:a=0.0022,lowpass=1500`(~-53dB) amix → 句間不再數位零(成片 noise floor ~-54dB 非 -∞)<br>**③ sidechain duck**:`[bg][voice_sc]sidechaincompress=threshold=0.03:ratio=8:attack=5:release=300` 取代固定 volume → 一講話 BGM 自動壓低、句間浮回<br>**④ two-pass loudnorm**:pass1 `print_format=json` 量測 → pass2 帶 `measured_*+linear=true` 精準投遞(-14 LUFS、true-peak 安全);pass1 失敗 graceful fallback 單 pass<br>**⑤ 加速同步鐵則**:`speed` 寫進 `offsets['_speed']` → 畫面每 scene `dur/SP`、字幕每 phrase `(t-tr)/SP`。**一顆常數貫穿三檔=永不 desync**;片長 invariant 當金絲雀。1.06 微/1.08 明顯/1.10-1.12 快但自然<br>**⑥ 尾長對齊**:影片逐幀量化比音訊短 ~0.2s,BGM/mix 淡出對齊【實際影片長】而非音訊長 → 尾端淡到真靜音;否則 `-shortest` 砍 BGM 在 ~-23dB 硬切=outro click<br>**⑦ 自動 gate(M97)**:把上述失敗模式固化成交付前 assert(LUFS -14±1 / 尾 0.25s RMS<-40dB / audio vs video stream |Δ|<0.4s / 末字幕 end ≤ 片長);音訊鏈抽成可重用 helper + 真 ffmpeg self-test,別 copy-paste 進每支 build script<br>**通則**:「剪得爛」最常被聽出來的是**聲音**不是畫面。pro 音訊 = 壓縮(壓平)+ ducking(讓位)+ 兩段式正規化(準)+ room tone(不死靜);語速可調但**任何時間軸變形必須全管線同源一顆常數**。承 M99(acompressor 壓 BGM)→ 這條把同招用到人聲 + 加 ducking/2pass/speed;同 M95(死空檔)/M97(self-test)家族 |
| **M104** 🖥️🚨 | **螢幕錄影去個資：邊緣掃(top/bottom strip)只抓 chrome/工作列,抓不到浮在【中央】的錄影軟體面板/彈窗 → 必【全幀 dense 掃：原始素材 + 成片各一遍】;且螢幕錄影一律 trim 掉【頭 ≥1s + 尾 ≥1-2s】(錄影軟體 UI 出現在頭尾兩端)** (承 M91/M101,一支教學長片交付被抓包後收斂) | 某教學長片的 demo 素材全是螢幕錄影(OBS 類工具)。做對了兩件事(裁上下 chrome/工作列 + 邊緣掃抓到瀏覽器分頁列上的公司名)卻有致命盲區:**(a) 錄影軟體控制面板浮在畫面【正中央偏上】,裁邊救不了,而驗證只掃了 top/bottom 60px strip** → 中央面板完全沒被看到就宣告「隱私 clean」交付,觀眾一播就看到;**(b) 錄影軟體 UI 恆在【頭尾兩端】**:切進被錄視窗的瞬間在開頭 0-1s、按停止錄製的瞬間在尾端 0.5-1.5s(該專案 7/7 支素材尾端全中,只 trim 頭=尾端照樣洩漏);**(c) 公司/專案真名出現在 app UI【內文】**(元件樹 self 標記、麵包屑導航)— 在畫面中央,crop 上方分頁列救不了。根因=「逐秒掃含中央」規則本來就有,**沒讀沒跑,只跑了自己想到的邊緣掃** | **永久 fix(機械化,不靠記憶;helper 已落地)**:<br>1. **螢幕錄影進 pipeline 第一步 = `src/longform_maker/screen_clean.py` 的 `clean_screen_recording(src, out, crop=..., head_trim=1.0, tail_trim=2.0, blur_boxes=...)`** — 一個呼叫做完:trim【頭+尾】(head floor <1.0 直接 raise,不准調低)+ crop chrome + 非滿版 blur-pad + 去聲 + **`blur_boxes` 定點糊【中央 UI 內文的公司名/真名】**(crop 救不了的洩漏用定點模糊救)。**清乾淨的 asset 才是 source of truth,不靠剪輯 in-point 閃避**。`python screen_clean.py` 內建真 ffmpeg self-test<br>2. **驗證 = 全幀 dense 掃 ≤1.5s/格,【不是】只掃邊緣**:`delivery_qa.render_fullframe_sheets(video, out_dir, step=1.5)` 機械產全幀 contact sheets(`final_delivery_qa(..., sheets_dir=...)` 自動跑)→ **逐張肉眼看**。邊緣 strip 只證明「chrome/工作列沒了」,證明不了中央沒浮窗/彈窗。**原始素材掃一遍 + 成片再掃一遍**(只掃素材不掃成片=舊 build 殘留照樣出貨)<br>3. **兩種掃互補、缺一個就有盲區**:邊緣 zoom strip(放大讀小字:分頁名/網址/公司名)+ 全幀 tile(抓中央大浮窗)<br>4. **in-point floor**:任何 screen clip 剪輯 in-point 不可 <1.0s(即使已 trim,雙保險)<br>**通則**:「裁邊乾淨」≠「畫面乾淨」。浮動視窗(錄影面板/通知/彈窗)活在**內容區中央**,只有全幀掃看得到。螢幕錄影=預設有毒(M91),這條把它變【機械 trim+crop+blur + 雙掃】不可跳過的步驟。教訓本質同 M101:**規則有、沒讀沒跑 → 把規則變機械 default,別靠當下記得** |
| **M105** 📝⏱️ | **字幕逐句時間【必用 whisper word_timestamps 的字級時間】在真實停頓處自動斷行 — 絕不手動猜長句切分時間(必 drift 2-3s)** (承 M68/M87,同一支教學長片字幕漂移被抓包後收斂) | 旁白 whisper 給的是粗 segment(一段 13-15s)。為了斷成可讀字幕行,【憑感覺內插】每個子句的起訖時間 → 整個 demo 段字幕比旁白慢/快 2-3 秒。**caption↔audio 對位是觀眾最先注意到的東西**,漂 2s 就非常明顯。另兩個隱藏坑:(a) **誤聽字修正若在斷行【後】做,misheard 詞可能已被切到跨行 → regex 修不到**;(b) **停頓判定若用「上一個 word 的 end」會誤判**(whisper 的 word end 常吃掉尾音,句中被切爆) | **永久 fix(機械化;helper 已落地)**:<br>1. **字幕一律走 `src/longform_maker/word_captions.py`**:`transcribe_words(wav)`(word_timestamps=True 拿字級時間)→ `group_words(words, fixes=)`(停頓自動斷行 + 行長爆掉回溯避開懸掛字 + 誤聽 regex 修正 —— **修正在斷行【前】做**,時間用 whisper 的/文字用修正後的)→ `to_master_events(...)`(含 M103 speed 換算到 master timeline)→ `build_ass(...)`(M68 白字黑框)。`python word_captions.py` 內建 self-test<br>2. **pause 判定用【下一個 token 的 onset】**(next-token start − current end),不是只看上一個 word 的 end — 尾音被吃時才不會誤切<br>3. **別用粗 segment 再手切**:手動猜時間 = 必 drift 2-3s,沒有例外<br>4. **交付 gate 機械化**:`delivery_qa.check_caption_sync(video, ass, n=8)` 抽 n 行 → 抽該時間窗音訊 whisper 轉錄 → 字符重疊率 <0.5 = FAIL(`final_delivery_qa(..., caption_sync=True)` 自動跑,進總閘門)<br>5. **交付前 empirical 驗**:挑幾個【distinctive 字】算它的 master 時間 → 抽那格 frame(看字幕)+ 抽 1.5s 音訊窗(whisper 轉錄)→ 字幕文字==音訊字才算過<br>**通則**:逐句字幕的「句」要對到【真實講那句的時間】,不是把長 segment 平均切。承 M87(內容對位)——M87 管「畫面對主題」、M105 管「字幕對時間到字級」。同 M104 家族:**時間來源要機械(word_timestamps),不靠手感** |
| **M106** ✨🎬 | **Premium motion 波1 教訓:靜卡 >5s = 留存懸崖;推鏡一律亞像素 float(ffmpeg zoompan integer jitter 永禁);counter 三件套(expo easing + 固定字槽 + 落地 pop,【末幀必==真值】);雙層 bloom(radius 4+16);SFX 對齊 cut ±50ms = clean→premium 最大單一槓桿;成片 split-tone finishing** (資料動畫/圖卡升級波1接線後收斂) | 業餘感的來源全部可機械定位:(a) 數據卡/圖卡用 `-loop 1` 靜圖躺 5-6s → 觀眾感知「畫面死了」= 留存懸崖;(b) zoompan 推鏡 integer 座標 → pixel 抖動,不可修;(c) counter 數字用比例字寬 → 滾動時整行跳寬(業餘最明顯破綻),且末幀若是 easing 產物可能 ≠ 真值(= 編造數字,違 M10);(d) 單層 glow = 貼紙感;(e) 轉場/數字落地無聲 = 「默劇簡報」感;(f) 各 clip 各調各的色 = 拼貼感 | **永久 fix(引擎已固化 `src/longform_maker/fx_lib.py`;參數真值 → `knowledge/premium-motion-fx.md`)**:<br>1. **靜卡全滅**:每張卡逐幀 render — 先出 2x 底圖,每幀 `ken_burns_frame(src2x, t, z0=1.0, z1=1.05, ease=smootherstep)`(亞像素 AFFINE float,零抖動)+ `texture_pass(grain, vignette, seed=幀號)`;奇偶卡交替 push-in/pull-out<br>2. **counter 三件套**:`ease_out_expo` count-up + **固定字槽**(每位數槽寬 = '0'-'9' 最寬 glyph,槽內置中,逗號 0.5x 槽)+ 落地 scale pop 1.00→1.06→1.00 + glow 脈衝;**最後一幀強制 assert count == 真值**(placeholder 例:資料是 1,234,567 末幀就必須是 1,234,567 — M10 gate 寫進 code)<br>3. **雙層 additive bloom**:GaussianBlur(4) @60% + GaussianBlur(16) @30%,`ImageChops.screen` 疊回,最上層貼銳利原元素 — 單層=貼紙,雙半徑=光學鏡頭質感<br>4. **SFX 接線**:每個 cut/落地/進場事件 `adelay` 毫秒對齊 **±50ms**;SFX peak 比旁白低 6-10dB;密度 cap ≤5/分鐘 — 研究收斂:**這是 clean→premium 最大單一槓桿**<br>5. **成片 split-tone finishing**:最後一道 `curves` + `colorbalance`(陰影推冷/亮部推暖,用你的品牌色系)→ 全片「同一隻手調過色」;grain/vignette **只做一層**(幀級做過的,成片級不再疊)<br>**通則**:premium 感 = 無死幀(永遠有亞像素微動)+ 數字誠實(末幀真值)+ 聲畫同步(±50ms)+ 統一 finishing。**留存>炫技**:所有能量效果都設頻率 cap,教學正文字幕不動畫 |
| **M107** 📊🧾 | **上鏡的數據一律用【真實後台截圖】，禁自繪重建戰績圖表；他人（來賓/客戶/合作方）的數據更嚴 —— 沒有對方提供的真截圖就不上鏡** | 把手上的數字（就算是真的）重畫成漂亮的長條圖/儀表板放進片裡 → 觀眾分不出「真後台」和「我用 Python 畫的」，**自繪數字即使為真，說服力也是零**；引用別人的成績時更糟：既無法自證、又替對方擔了造假風險 | **永久 fix**：<br>1. 戰績/成長/收益鏡頭一律走 **原始後台截圖**（Studio/Analytics/儀表板原生 UI），非滿版就 `still_blurfill()` 模糊填底，不重畫<br>2. 建一份 `PROOF_DATA.md` 當單一真值來源：每個上鏡數字寫「數值＋截圖檔名＋擷取日期＋量測窗」，**片中每個數字都要能指回某一張圖**<br>3. **他人數據取得規則**：來賓/客戶的數字只有兩種下場 —— 對方給了截圖（可上鏡，並在畫面標「由 X 提供」）或沒給（**只能口述、不上鏡、不重畫**）；授權書一併寫明可公開的數據項<br>4. 交付前人工項：每個數據鏡頭逐張比對 PROOF 真截圖（`final_delivery_qa` 的 Note 已列）<br>**通則**：M10（不編造數字）管「數字對不對」，M107 管「觀眾憑什麼相信」。可信度住在**畫面的來源**，不在數字本身。 |
| **M111** 🧾🔍 | **消毒的「宣稱」本身要被稽核 —— 三種假乾淨：① 移除說明重述被移除物 ② 換標籤當成移除 ③ 絕對規則自己違反**（承 M100；第 4 輪對抗稽核的角度就是「只查宣稱」）| M100 教了「多輪多角度掃到 0」，但前幾輪都在掃**內容**，沒人去驗**檔案對自己的描述**。結果：(a) CHANGELOG 寫「把 shot ID 拿掉了」，同一句話**把 shot ID 列出來**——移除說明變成該值在 repo 裡唯一的出處；(b) 模組 docstring 的「支援哪些誤判」清單**繼續列著字典剛刪掉的詞條**，程式乾淨、文件洩漏；(c) 一份「不刊任何頻道後台讀數」的檔案，把單一頻道回歸出來的門檻**改標成「公開基準」**留在原地——標籤換了、數字沒動、還多了一層假權威；(d) 檔頭寫「合成示意」但那條 phrase 是逐字原句。**共同根因：驗證只看「內容改了沒」，沒看「描述是不是還成立」** | **永久 SOP（去個資第 N 輪必跑一個 claims-only 角度）**：<br>1. **把每一句自我宣稱當斷言測**：grep 出所有形如「已移除／已匿名／合成示意／不含任何 X／本檔不刊 Y／絕對規則 Z」的句子，**逐句去驗它現在還成不成立**<br>2. **移除說明不准重述被移除物**：寫「拿掉了什麼**類別**」不寫「拿掉的**那個值**」。判斷句：「這行字被 grep 到，會不會就是洩漏本身？」<br>3. **關鍵是 code ↔ doc 雙向**：改了常數就 grep 該常數在 docstring/README/CHANGELOG 的所有描述；**只改一邊 = 只清了一半**（承 M84 全域收尾）<br>4. **換標籤 ≠ 移除**：私有讀數改標成「公開基準／業界共識」而數字原封不動，是**更糟**的處置（照抄的人拿去判死自己）。真正的處置只有三條路：**附可點出處** ／ **改成 `<fill in>` + 量法** ／ **整條刪掉**<br>5. **絕對規則要能自我稽核**：寫下「一律／絕不／不含任何」之前先跑一次全域檢查確認自己沒違反；規則寫成**可機械複驗**的形狀（例如「第 1 類數字必須有 `<fill in>` 或出處連結」），並在檔內寫明「看到反例＝bug，請開 issue」<br>**通則**：M100 管「掃內容掃到 0」，M111 管「**檔案對自己的描述是不是真的**」。一個假的乾淨宣稱比沒有宣稱危險 —— 它會讓下一輪稽核直接跳過那個檔案。 |

### Deferred-rows (跨 SKILL 引用 placeholder lessons — 補 row)

| # | Meta-Lesson | 反規則 | 正解 |
|---|---|---|---|
| **M35** 🎬🛠️ | **ffmpeg-only silent vlog path = silent_vlog_maker SKILL 的核心** (歷史 — 2026-04 旅遊 vlog v2 落地) | 早期跑 DaVinci agent 操作 + JSON 兩條 pipeline 並存 → 太慢、太亂。silent vlog 不需 CapCut 字幕，直接 ffmpeg drawtext on b-roll = 4x 快 | **三條 path 分流**：<br>- **Path A** (CapCut Pro template，教學長片) — `capcut-agent-ops` SKILL<br>- **Path E** (silent vlog純 ffmpeg drawtext + KenBurns，旅遊) — `silent_vlog_maker` package<br>- DaVinci 已淘汰 (2026-05-23)<br>→ M35 routing 規則寫進你自己的 `profiles/content_pipeline.md`（模板：`templates/content_pipeline.template.md`）|
| **M75** 🎯🔀 | **Caption-broll content matching MUST auto-sequence build-time，不是 audit-time** (2026-05-26 Mode C #3 / 某支片 v3-v4 用戶「topic-A caption 配 book b-roll」) | 早期 caption_broll_matcher 只能 audit-post-hoc 找 mismatch，build 時還是手動排素材順序 → 人為錯（v3 topic-A caption 配 book / v4 翻書配「通用主題範例」) | **永久 fix M75 v0.1 落地**：<br>1. `caption_broll_matcher.auto_sequence_brolls()` build-time 用 `EXAMPLE_KEYWORD_MAP` (9 topics) greedy topic-clustering 把 b-roll 排好順序<br>2. `PRE_BUILD_CHECKLIST_TEACHING_LONGFORM` 加 `auto_sequence_brolls: True` default<br>3. `verify_steps` 加 VERIFY 6 — `audit_caption_broll_mismatch()` post-build assert high-severity = 0<br>4. ✅ v0.2 落地 (2026-05-29 verify): windowed look-ahead `look_ahead_window=2` / `look_ahead_decay=0.5` / `_windowed_topic` — 解 greedy local-optimum |

---

## 🚦 影片交付前 QA 自檢清單（某支片 八輪修正的總結 — 永久鐵則）

> **這份清單存在的理由**：某支片用戶來回修了 8 輪（前導逗號 → 黑框/半透明底 → 字幕反序 → 時間軸誤字 → 桌面 chrome+金流後台 → 真實素材 → 圖片抖動/沒模糊底/露電腦 → 頻閃）。**每一條都該我自己交付前抓到,不是讓用戶當我的 QA**。以後每支片 export 後、報告用戶前,機械式跑完以下:

| # | 檢查 | 機械方法 | 對應 |
|---|---|---|---|
| 1 | **內容對位** | 抽整片接觸表(≤6s/格)逐格看「旁白語意=畫面」;旁白點名具體物(上一支影片/時間軸/素材夾/你自己的網站或作品)→ 有給真實該物? | M87/M94 |
| 2 | **chrome/隱私** | 全片抽幀:0 工具列/0 app 浮動面板/0 瀏覽器/0 金流後台/0 檔名路徑/0 email;螢幕錄影截圖都裁到只剩內容區 | M91 |
| 3 | **圖片排版** | **死黑邊機械抓**:`detect_dead_borders()`(cropdetect)→ 非滿版有 letterbox 就 flag → 該段改 `still_blurfill` 模糊填底;靜止不抖(禁 zoompan)+ 裁到只剩內容區仍人工看 | M92 |
| 4 | **頻閃** | `ffmpeg -vf blackdetect=d=0.05:pic_th=0.90` 跑全片 = 乾淨? 無頻閃素材(動作遊戲爆擊)/字幕盒空檔/亮度落差 | M93 |
| 5 | **字幕** | 燒完抽幀:無前導逗號 + 中上英下不反序 + 中文半透明黑底/英文黑框 + **句內有停頓空格(不連在一起)** + 無 whisper 誤字(對逐字稿) | M68/陷阱1-3 |
| 6 | **音訊** | trim 到人聲結尾(無靜音尾) + BGM 不重播有 fade + **句間死空檔 ≤0.8s**(silencedetect 找 >1.5s 停頓剪到 ~0.5s) | M82/M79/M95 |
| 7 | **格式** | 全片 30fps CFR、player-safe encode | M81/M83 |
| 8 | **不編造** | 字幕/字卡對真實逐字稿+真實資訊,無 hallucinate | M10 |

**任一個沒過 → 還沒交付。** 這清單就是為了「不再讓用戶一個一個抓」。**機械項已落地**：`from capcut_helpers import final_delivery_qa` → 跑 M93 頻閃(blackdetect) + M95 死空檔(silencedetect) + **M92 死黑邊(cropdetect, 2026-06-20 接上)** + 接觸表；M91 chrome / M92 裁切構圖 / M94 對位 / M68 字幕仍人工逐格看接觸表。每支交付前必跑。<br>**字幕誤字(M69)也機械化**：`run_verify_steps()` 內 **VERIFY 4** 自動跑 `scan_potential_errors(draft)`(cloud→Claude / 可好→Claude 等),且該函數現為**全覆蓋標記**——任何 verify_step 沒被自動跑就標 manual + 回報 `coverage`/`uncovered`,杜絕新增驗證步驟被靜默漏掉(2026-06-20 rank2)。

---

## ⛔ M9 SOP — Content-Matched Captions（v8 最痛教訓）

**錯誤模式（某住宿型景點 v7 犯）**：
1. 讀資訊（賣點 A / 賣點 B / 賣點 C / 賣點 D / 賣點 E）
2. **想像** 8 clips 拍了什麼 → 把賣點隨便分配
3. 結果：「賣點 B」配到畫面 X / 「賣點 A」配到畫面 Y / 「賣點 C」配到畫面 Z — 視覺跟文字**完全錯位**

**正確 SOP**（M9 強制 + M34 hi-res 強化）：

```bash
# 1. 寫文案前 — extract 每 clip 4 frames hi-res
mkdir _content_check
for clip in raw/*.MOV; do
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$clip")
  for ts_frac in 0.5 0.33 0.66 0.97; do
    ts=$(python -c "print($dur * $ts_frac)")
    ffmpeg -i "$clip" -ss "$ts" -vf "scale=640:360,format=yuvj420p,drawtext=text='$(basename $clip) @${ts}s':fontcolor=yellow:fontsize=24:x=10:y=10" \
      -frames:v 1 "_content_check/$(basename $clip .MOV)_${ts_frac}.jpg"
  done
done
ffmpeg -filter_complex hstack/vstack ... _content_check/all_clips_grid.jpg

# 2. Read all_clips_grid.jpg → 用文字描述每個 clip 拍到什麼
# 3. 才寫 cut-plan — 每個 overlay 對應實際畫面內容
```

### 賣點配畫面判斷表

| 賣點 | 配 OK 畫面 | 配**不行**畫面 |
|---|---|---|
| 賣點 A：某項體驗活動 | 該活動的場地 / 道具 / 進行中畫面 | ❌ 任何純風景空鏡 |
| 賣點 B：住宿空間 | 房間外觀 / 房間內部 | ❌ 建築外的裝飾細節 |
| 賣點 C：特殊房型 | 該房型本體 | ❌ 其他設施的近景 |
| 賣點 D：整體場域規模 | 寬廣俯瞰 / 園區步道 | ✅ 場域內任一景（屬於場域一部分即可）|
| 賣點 E：某項設施 | 該設施近景 / 使用中 | ❌ 不含該設施的畫面 |

> 表裡刻意不寫實際店家的設施名。**照抄別人的賣點清單沒有意義** —— 換成你自己主體的
> 賣點與畫面再對一次；重點是「一條賣點只能配拍到它的那一格」。

**SOP 結合 R18**：
1. 看 N clip 畫面（M9）
2. 列該主體賣點（R18）
3. 賣點 ↔ 畫面 mapping
4. 無對應賣點 = 不要寫（留 B-roll 呼吸）
5. 無對應 clip = 寫 generic 但 truthful 描述

---

## ☠️ M10 SOP — Verified Facts Only（v9 最致命教訓）

**錯誤模式（某住宿型景點 v8 犯）**：
1. 跑 WebSearch 抓主體資料
2. 寫文案時**多塞** WebSearch 沒提到的「酷數字」(場域坪數 / 設施數量)
3. 用戶質疑「最好是有那麼多？」— **我憑空編造數字**
4. → 散布假資訊，傷害用戶 channel 信譽

**正確 SOP（M10 強制）**：

寫每張字幕前自問：「這個數字 / 事實在 WebSearch 結果裡嗎？」

| 來源 | 可寫 |
|---|---|
| WebSearch 結果原文引用 | ✅ |
| 用戶提供資料 | ✅ |
| 畫面可見證據（抽幀能指回去的東西）| ✅ |
| 自己「歸納 / 估算」 | ☠️ NO |
| 「印象中」「應該是」 | ☠️ NO |

**沒 source 怎麼辦？— 寫 generic 但 truthful 描述**：

| 想寫但沒 source | 改寫成 |
|---|---|
| 「佔地 N 坪（誇大坪數）」 | 「自然生態園區」 |
| 「養了 N 隻（誇大數量）」 | 「成群」/「池畔」 |
| 「全國最大」「銷量第一」「XX 指南推薦」 | 「特色」「熱門」「在地名店」 |
| 「Claude Code 比 GPT 快 10x」 | 「快速生成」「實測 N 分鐘完成」(有測過再寫) |

**核心 insight**：**「不講話 > 編造」** — 觀眾寧可看到沒數字，也不要看到假數字。

**M10 通用於所有題材**：
- 教學：別編「100x 效能提升」如果沒實測
- 開箱：別編「銷量第一」如果沒 source
- 食物：別編「米其林推薦」如果沒查到
- 旅遊：別編坪數 / 人次 / 動物數量

---

## 🚨 Pre-Delivery Self-Critique Checklist（出片前必過 17 項）

把任何 silent vlog / shorts 給用戶看之前，**自己先逐項打勾**：

```
□ 技術層
  □ R1: ffprobe 7 維度全掃過？(codec / res / fps / rotation / HDR / pix_fmt / UTC time)
  □ R10: HDR source 有跑 tonemap？(iPhone HLG → BT.709)
  □ R11: bitrate 在 8-12 Mbps 範圍內？檔案 < 60 MB for 44s?
  □ R12: subtitle 在 safe zone? (y 260-1660 / x ≤ 930)
  □ R14: timestamp 是 local time（不是 UTC）?

□ 內容層
  □ R15: 套用戶 voice profile? (Register 挑對了嗎 — High-Demo / High-Reflective / High-Update / Low / Vlog)
  □ R18: 每個 overlay 有 ≥3 個資訊要素? (定位/數字/賣點/用法/價格/CTA)
  □ R18: 有實際研究主體資訊? (WebSearch 過?)
  □ R19: subtitle 統一中央偏下位置? (沒跳來跳去?)
  □ ⛔ M9 / M34: 每個 clip 都看過 hi-res 4 frame? overlay 跟實際畫面對應? (沒亂塞賣點?)
  □ ☠️ M10 / M37: 每個數字/事實能追溯到 WebSearch 或畫面? (沒 hallucinate 坪數/數量這類編造?)

□ 視覺層
  □ R17 / M43: Noto Serif CJK Bold 或 CapCut 模板? (不是廉價系統字體)
  □ R17: cinematic curves 有套? (色彩不平淡)
  □ R12 Typography: 主標 + 副標 hierarchy 對? (字級對比)

□ 完成度層
  □ Grid verify 看過 5 個 keyframe? (主標 / 中段 / time-jump / 結尾)
  □ 沒「我覺得 OK 但其實 X」的死角?
  □ 用戶會問什麼？我能回答嗎？
```

**任一項未過 → 不能說「剪完了」**。要嘛繼續修，要嘛先告訴用戶「目前狀態 + 待強化點」。

---

## 🚨 Common Antipatterns Table（17 條 — 看到自己在做就停）

| # | Antipattern | 症狀 | 規則 |
|---|---|---|---|
| 🚫1 | 「跑完 pipeline = 剪完」 | export 出檔就回「剪完了」沒 self-critique | M1 |
| 🚫2 | 廢話流水帳 | 「我們來到 X」「漫步 X」「真的很漂亮」 | M2 / R18 |
| 🚫3 | 賣點清單硬塞畫面 | 賣點配到一個沒拍到它的畫面 | ⛔ M9 |
| 🚫4 | 編造數字 | 場域坪數 / 設施數量 WebSearch 沒提到 | ☠️ M10 |
| 🚫5 | 字幕位置跳來跳去 | 主標中央 / lower-third 左上 / 結尾底部 | R19 |
| 🚫6 | 想像主體資料 | 沒 WebSearch 就「印象中」寫文案 | M6 / M10 |
| 🚫7 | iPhone HDR 直接 encode | 沒 tonemap → 手機過曝 | R10 |
| 🚫8 | UTC 時間直接用 | EXIF UTC 06:41 標「早上 6:41」（實際下午 14:41）| R14 |
| 🚫9 | 不查 rotation | iPhone 直式被塞橫框 | R1 |
| 🚫10 | bitrate over-spec | -cq 19 → 16.6 Mbps 88MB for 44s | R11 |
| 🚫11 | 純黑邊白字 | 沒 hierarchy 沒半透明背景條 | R12+R17 |
| 🚫12 | 廉價系統字體 | 用標楷體 / 細明體 default / NotoSansTC-Bold 太 generic | R17 / M43 |
| 🚫13 | 累積 stale refs 才 cleanup | 16 處 v2/v3/v4 references 等用戶說才修 | M8 |
| 🚫14 | 看 mid-frame ≠ 看整段 | 某 clip mid-frame 是某地標，trim 0-2s 卻是另一畫面 | M11 / M21 |
| 🚫15 | 混 portrait/landscape 用同套位置 | 長片 1920×1080 套 Shorts y=1280-1400 | M13 |
| 🚫16 | 照片直接靜止 1 秒切 | 觀感超死板 → 必加 KenBurns zoom-in | M14 |
| 🚫17 | 長片用純白單色字幕 | 像 IG/TikTok 字幕 → 改 cyan/magenta/gold 綜藝感 | M15 |

**檢測**：寫每張 overlay / 跑每個 ffmpeg / 給用戶看之前，**對照這 17 點自查**。

---

## 🛤️ Universal Video Production Pipeline SOP（任何題材都跑這個）

```
Step 0  [接收] 用戶說「剪一支 X」
        ↓
Step 1  [研究] WebSearch X 的實際資料 (R18 / M6)
        ├── 列 verified facts 清單（每條標 source）(M10)
        └── 沒查到的數字/斷言 → 跑第 2 次 WebSearch
        ↓
Step 2  [素材] ffprobe raw/ 7 維度 audit (R1)
        ├── codec / resolution / fps / rotation / HDR / pix_fmt / UTC time
        ├── 偵測 HDR → 必走 tonemap (R10)
        ├── 偵測 rotation → 必走 portrait timeline
        └── 偵測 UTC → +TZ 轉 local (R14)
        ↓
Step 3  [看畫面] ⛔ ffmpeg extract 每 clip 4 frames hi-res → grid → Read (M9 / M34)
        └── 描述每個 clip 拍到什麼（用文字記錄）
        ↓
Step 4  [Voice] load_voice_profile(mode) from yt-script-style (R15)
        └── 對應 raw 內容類型: vlog / high-demo / low-diy
        ↓
Step 5  [Cut-plan] 賣點 ↔ 畫面 mapping (M9)
        ├── 每 overlay 含 ≥3 個資訊要素 (R18)
        ├── 統一中下置中位置 (R19)
        ├── 每個 fact 對照 verified 清單 (M10 / M37)
        └── 對應 voice profile 招牌 (R15)
        ↓
Step 6  [Build] 選 path：
        ├── Path D: JSON direct edit (CapCut, 最 efficient)
        ├── Path A: Export only agent
        ├── ffmpeg-only pipeline (silent vlog 首選, M35)
        └── (棄用) DaVinci agent — 已 archive
        ↓
        套 R10 tonemap / R11 spec / R12 safe zone / R13 smart cut / R17 cinematic / M14 KenBurns
        ↓
Step 7  [Render] 跑 build script
        ├── ffmpeg ~22s / capcut-cli ~30s
        └── 若 CapCut audio 不可靠 → ffmpeg force-mix BGM (M29)
        ↓
Step 8  [Verify] grid keyframes (R16)
        └── Read grid.jpg 確認 N 個關鍵點
        ↓
Step 9  ⚠️ [Self-Critique 17 關] 逐項打勾
        ├── 技術 5 / 內容 6 / 視覺 3 / 完成度 3
        └── 任一未過 → 回 Step 5 修
        ↓
Step 10 [Cleanup] Audit milestone (M8)
        ├── stale refs scan
        ├── dead code check
        └── docstring fix
        ↓
Step 11 [Deliver] 給用戶 — 預期可能 challenges
        ├── 內容對嗎？(M9 / M34 視覺對應)
        ├── 數字真嗎？(M10 / M37 source)
        ├── voice 對嗎？(R15)
        └── 位置對嗎？(R19)
```

**時間估算 (per video)**：
- Step 1-5（規劃）：~5-10 min
- Step 6-7（build）：~25 sec ffmpeg / ~30 sec capcut-cli
- Step 8-9（verify）：~2 min
- Step 10-11（deliver）：~2 min
- **總計**：~15-20 min for production-ready Shorts

**Token 估算 (per video)**：~12-15k tokens（含 WebSearch + Read grid + run script）

---

## 🎯 何時跳出「single-task tunnel vision」做 audit

| 觸發 | 動作 |
|---|---|
| 完成 v3 / v5 / v7 等 major milestone | 自動跑 audit（stale refs / dead code / DRY）|
| 用戶 challenge 1 次 | 反思「還有哪幾項類似錯誤可能存在？」|
| 用戶 challenge 2 次 | 從**單個技術修**升級到**系統規則寫入** |
| 用戶 challenge 3 次 | 寫進 SKILL meta-lessons（這份檔案）|

---

## 🎯 給未來自己的話

當你覺得「這個影片 OK 可以給用戶看」時，**先問自己**：

1. 我有跑完 17 項 self-critique？
2. 我有研究主體實際資訊 還是 在想像？
3. 我給的每張字幕，路人看完知道**這是什麼 + 能幹嘛 + 怎麼接觸**嗎？
4. 我的 voice 是用戶的 還是 generic？
5. 我有 audit 過 stale refs 嗎？
6. 我寫的數字都有 source 嗎？沒編造嗎？
7. 我用的字體是 M43 whitelist 嗎？沒用標楷體 / 細明體 default？
8. 我有沒有 reflexive 想 spawn agent？是不是該先試 Path D JSON edit？

任一個答「沒有」→ 還沒完成。

---

## Cross-references

- Pipeline implementation：`knowledge/capcut-automation-sop.md` + `knowledge/programmatic-video-build.md`
- Token efficiency anti-patterns：`knowledge/agent-token-efficiency.md`
- Agent brief 模板：`knowledge/capcut-agent-brief-template.md`

## M110 — 腳本三支柱（語氣＋觀眾語言＋留存節奏）

腳本層的三個獨立失敗軸：像不像你（voice profile）／人聽不聽得懂（觀眾語言：白名單詞表+行話分級）／看不看得下去（節奏：open loop、beat 上限、動能詞、短句打點）。三者可各自壞，錄音前用 `src/longform_maker/script_gate.py` 機械檢查（觀眾語言 fail 級、節奏 warn 級）。**詞表由你自己的逐字稿審計派生，不用別人的**——照抄別人的白名單 = 用別人的觀眾檢查你的稿子，比不檢查更糟（它會放行你觀眾聽不懂的詞、擋掉你觀眾早就熟的詞，而你還會信任它），所以 kit 出貨的四層表是**空的**。建表流程與擋不了的人工 craft → `knowledge/script-retention-craft.md`；填空骨架 → `templates/style_profile.template.md` §5。

---

## §Shorts 結構教訓（S-A ~ S-L 機械標籤 ＋ S-M / S-N 人工項）

> 直式短片**獨立編號**（S-x），跟 M 系列不衝號。知識全貌 → `knowledge/shorts-mastery-2026.md`；
> 這裡只記「症狀／根因／永久解」三段式，每條標對應的機械 assert。
> **原則**：Shorts 的失敗幾乎都不是「畫面不好看」，而是**結構錯了**（觀眾不知道在看哪裡、字幕沒資訊、時間軸配錯段）。

| # | 症狀 | 根因 | 永久解（對應 assert） |
|---|---|---|---|
| **S-A** 🔴 | 看完不知道自己看了哪裡、那是什麼 | 把任務理解成「把素材接起來加字幕」＝素材剪輯，不是**介紹一個主體** | 開場 2 秒 = **主體名大字 ＋ 一句這是什麼**；開剪前先寫一句「這支要讓觀眾記住什麼」，答不出「哪個主體＋它是什麼」不准動手。assert：首段必含 `place` + `what` 兩條字幕，且第一條含 place |
| **S-B** | 片長兩頭不沾：太長沒有梗的節奏、太短講不完一件事 | 憑感覺收在「差不多 30 秒」——正好落在雙峰之間的死區 | **片長雙峰帶，避開 26-44s 死區**：梗/單一驚奇帶或教學/demo 帶，二選一（S8）。assert：`sum(seg.dur)` 落在 `dur_min`-`dur_max`（含 `dur_max_slack`），且不得落在 `dur_deadzone`；門檻是**範例校準值**，採用者用自己的片重量 |
| **S-C** | 開頭有畫面但沒有「事情發生」 | 第一刀太晚，靜態開場 | **首刀 ≤2.0s**（2 秒法則的可執行版）。assert：`segments[0].dur <= 2.0` |
| **S-D** | 結尾接回開頭時「跳一下」，loop 不成立 | 只回到**同一支 clip** 就以為完成 loop —— 運鏡素材裡相機早已移開 | 末段須回首段同 clip **且末段結束點 == 首段起始點**（末幀==首幀）。assert：loop 端點時間戳相等，接點不掛字幕 |
| **S-E** 🔴 | 中途滑進來的觀眾不知道這是哪、怎麼找 | 地址/識別資訊做成**片尾一張卡** → 前面十幾秒的觀眾等於沒收到 | 底部半透明常駐條，**0.2s 掛到片尾**；y 值與內容字幕錯開（見 M13）。assert：缺 `addr` 直接 build 失敗 |
| **S-F** 🔴🔴 | 整組字幕**晚一段**／兩句對調／末句掉進 loop 段 | **人手算時間軸**。舊 gate 只驗「字幕不跨 cut」——每條都落在某一段【之內】，只是**落錯段**，於是全數放行（gate 綠但成片錯） | 字幕**綁 segment 索引**不綁秒數：`caps_by_seg=[(segment_index, blocks, kind)]`，時間由 `expand_caps()` 自動算（同段多條自動平分）。**人不碰時間軸 → 配錯段在結構上不可能發生**。assert：字幕來源只接受 segment 索引；另產字幕中點幀對照圖供人眼複核 |
| **S-G** | loop 接點閃一行殘字 | 內容字幕壓到 loop 段 | loop 段禁掛內容字幕。assert：末段（loop 段）字幕數 == 0 |
| **S-H** | 一條字幕橫跨剪接點：畫面已經換了，字還掛在上一段 | 字幕時間手填，跨不跨 cut 靠肉眼看 | **字幕不跨 cut**：一條字幕只能活在一個 segment 之內。assert：由 S-F 的 `expand_caps()` 在段界內配時間（兩端留 `cap_pad`、同段多條間隔 `cap_gap`）**結構性保證**——人不碰時間軸就跨不出去；塞不下就直接 raise |
| **S-I** | 畫面花、重點看不出來 | 字幕多色亂用 | **white-first**：字幕底色一律白，每支僅 ≤2 個非白色（重點=金、次要資訊=淺）。assert：非白字幕比例掃描 |
| **S-J** 🔴 | 字幕寫了等於沒寫（形如「{顏色}的那個」「{形狀}那顆」——只描述外觀，看完仍不知道那是什麼、多少錢） | 「**看**」外觀寫形容詞，而不是「**讀**」畫面上的字 | 畫面裡有標價牌/菜單/招牌 → 字幕必須是牌上的**品名＋價格**；疑似有文字的畫面先 `crop+scale` 抽高解析度幀放大讀，**讀不到就不編**（M10）。assert：掃描階段自動輸出招牌放大圖，字幕填寫以該圖為準 |
| **S-K** 🔴 | 字幕還掛著，鏡頭已經搖到別的東西上 | 運鏡片段只看了首尾幀就配字幕 | 運鏡片段**逐 0.5s 抽幀驗證鏡頭全程沒移開該主體**；移開了就把該段切短或改字幕。assert：每條字幕抽該段時間窗多幀對照圖，人眼逐條複核 |
| **S-L** 🔴 | 品名張冠李戴（A 的牌配到 B 那盤） | 取牌時取到「同畫面另一盤的牌」甚至「別段讀到的牌」 | 品名**只能取該主體正上方那張牌**；同畫面其他牌、其他段落讀到的牌一律不可套用。assert：字幕與來源招牌圖一對一綁定，跨段套用視為缺來源 |
| **S-M** ✋ | 前段觀眾看不到重點、滑掉 | 把最強畫面留到後面「壓軸」——Shorts 沒有預告的餘裕，壓軸＝沒人看到 | **最強一幀放最前**。**無 assert（人工項）**：首幀單獨輸出成圖，自問「只看這一格我會停下來嗎」，不吃自動第一格、不憑印象 |
| **S-N** ✋ | 首幀留不住人 | 用氣氛遠景/空景開場，畫面沒有視覺焦點 | 首幀用**近景高對比主體**（食物/動物/物件），或有消失點的引導線構圖。**無 assert（人工項）**：同樣把首幀出圖來看 |

**標籤權威**：**S-A~S-L 的定義以 [`src/longform_maker/shorts_gate.py`](../src/longform_maker/shorts_gate.py) 為準**，標籤與該檔的失敗訊息一一對應（gate 報 `S-B ... 死區`，查 S-B 就查到片長帶）；其中 S-A~S-I 有 assert 擋 build，S-J~S-L 是該檔【內容】層靠人看畫面。**S-M / S-N 只存在於知識檔，是人工判斷項，程式裡沒有這兩個標籤、沒有 assert** —— 兩者曾誤佔 S-B / S-H，已改為不衝突的新編號。

**通則**：S-F/S-K/S-L 是同一個病 —— **「看起來對」不等於「來源對」**。凡是靠人記憶或人手算出來的對應關係（時間軸、品名、主體），都要換成「由結構自動導出」或「有一張圖可以指回去」，否則 gate 只會驗到形式、驗不到內容。
