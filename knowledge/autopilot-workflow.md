> 來自 video-autopilot-kit 開源知識庫 · MIT 授權

# Video Autopilot Workflow

**Meta-orchestration skill** — 串接其他 4 個 skill 跑完整 9 步工作流，讓使用者**給一句題目就拿到全套**（腳本可直接念 + 包裝 + 發佈計畫 + 監控時程 + edit pipeline 路徑）。

跟其他 skill 的關係：本 skill **不重複邏輯**，只串接呼叫：
- `yt-script-style`：voice / 腳本
- `video-craft-playbook`：跨平台廣度策略
- `yt-algorithm-mastery`：YT 算法深度 + MrBeast 戰術
- `capcut-agent-ops`：CapCut Desktop agent 操作 + Path A-E（edit pipeline）

**資料位置**：你自己 skills 目錄下的 `video-autopilot/`（相對路徑，依各人環境）

---

## ⚡ 30 秒 Quick Reminder

接到任何「剪一支影片」請求時，**先想這 5 件事**：

1. ☠️ **不要編造數字** — 每個數字/事實必有 source（WebSearch / 使用者 / 畫面）。沒 source → 寫 generic。**「不講話 > 編造」**（M10 / M37）
2. ⛔ **先看畫面再寫文案** — `ffmpeg extract 4 frames hi-res 640×360` → grid → Read → 才寫對應 overlay（M9 / M34）
3. 📋 **介紹式不是記錄式** — 含定位/數字/賣點/CTA ≥3 項，沒「我們來到 X」廢話（R18）
4. 🎯 **字幕統一中央偏下** y=1280-1400（Shorts）/ y=820-930（長片），不跳位（R19 / M13）
5. 🎓 **跑完先 self-critique 17 關** — 任一未過 → 還沒完成

**完整 M1-M103 meta-lessons + 17 條 antipatterns + Self-critique checklist + Production pipeline SOP → [`meta-lessons.md`](meta-lessons.md)**

---

## 🎯 該用哪個 skill？（5-skill 決策樹）

| 任務 | Skill |
|---|---|
| **本 skill**：一句題目 → 完整套件 | **`video-autopilot`** Mode A |
| **本 skill**：紀錄已發布影片數據 | **`video-autopilot`** Mode B |
| **本 skill**：從歷史學經驗，優化默認值 | **`video-autopilot`** Mode C |
| 細部 voice / 腳本 work | `yt-script-style` |
| 細部跨平台規劃 / 快速 packaging | `video-craft-playbook` |
| 細部 MrBeast 級 packaging / 數據 decode / iteration | `yt-algorithm-mastery` |
| **Edit pipeline**（CapCut agent / JSON / Export） | **`capcut-agent-ops`** Path A-E |

→ 使用者說「規劃我下一支X」「全部你來」「autopilot」→ **走本 skill Mode A**，自動觸發其他 skill 的對應 mode。

---

## ⚡ Cheat Sheet — autopilot 鐵則

1. **使用者給一句題目 → 立刻跑 Mode A**，不要先問太多問題
2. **預設值（不問使用者就用）**：
   - Sign-off 採用主流 boilerplate 變體（依你的歷史樣本統計最常用的那個）
   - 發文時間採用你的歷史實測最佳時段（例：晚間離峰 或 午後時段）
   - YT Test & Compare **3 variants (A/B/C) 並行 2 週**
   - 教學頻道 KPI：**沒有預設值，這一項不許 autopilot 自己填** —— [`youtube-algorithm-mastery.md`](youtube-algorithm-mastery.md) §TL;DR 那張表**整組是 `<fill in>`**，沒有可以借的起跑線。理由：CTR／AVP／留存全是**後台讀數**，任何「沒有出處的具體門檻」在定義上就是某個人的 Studio 讀數，借來就是拿別人的分佈判死自己的片。<br>**第一支片的正確做法**＝不設 KPI 門檻，只記錄讀數；**累積 3-5 支之後**用 mastery §2b-5 把門檻回歸出來（分「有被接走／沒被接走」兩堆，看分界值）。在那之前，比較的對象是**你自己上一支**，不是任何數字
   - 平台配比：**1 長片 + 1-2 支 Shorts**
3. **Pre-flight ≤3⭐ → fail loud**，告訴使用者題目該改不要硬做
4. **每支 video log 進 `video_log.md`**（Mode A 自動寫入；Mode B 補 outcome）
   —— `video_log.md` / `optimization_log.md` 是**你自己工作資料夾裡的兩個檔**（本 kit 不出貨、也不該入你的 repo）；名字你隨意，本檔一律用這兩個名字指涉它們
5. **發布後監控時程自動排**：48-72h（mastery Mode D）+ 1 週（mastery Mode E）
6. **使用者提到的任何 preference / 缺漏 / 規則 → 立刻寫進對應 SKILL.md** — 使用者不該講第二次
7. **🎬 畫面規劃 = script-anchored** — 不假時間戳；每個視覺 cue 錨定到 quoted text；逐句讀腳本才開始設計
8. **Edit pipeline 預設走 `capcut-agent-ops` Path D + A**（不是反射 Path C 多模板 agent）— 詳 §「Edit Pipeline」
9. **Agent spawn 上限 = 2 / task**（超過 = 換 path）— 詳 [agent-token-efficiency.md](agent-token-efficiency.md)
10. **🔭 接到 raw 第一件事 = 跑 `run_full_audit()`** — R1 11 維度 + M12 scene cluster + M9 hi-res frame grid 一鍵跑完，輸出 audit_report.md / json / grids → caption 配畫面從此不出錯
11. **🛣️ 接著決定 routing**（mass production）— 依 audit 結果判 layout (portrait/landscape/mixed) + content type (vlog/teaching/diy) → 選 Path + BGM + preset family。規則寫在你自己的 `profiles/content_pipeline.md`（模板：`templates/content_pipeline.template.md`），**填一次之後丟任何素材都能 zero-config 開跑**
12. **🎓 Build 第一件事 = 跑 `print_pre_build_checklist(decision.content_type)`**（Mode C #2 AP9 落地）— 顯示這個 content type 的 5 questions / defaults / wraps_lessons / verify_steps。**問使用者 batch 1 message 5 件事**（不要 5 次來回）+ 自動 enforce M-series（M64/M66/M68/M69/M70-M72 等）。**第一次跑 new content type 不再卡 3 輪 ship。** 已 register：`teaching_longform` / `food_vlog` / `travel_vlog` / `screen_recording_teaching`
13. **🔒 「已完成」定義 = mp4 re-exported + 3 frame visual verify pass**（Mode C #2 AP10 落地）— JSON saved/synced **不算 done**。任何 JSON edit → 自動 flag「mp4 stale，需 re-export」
14. **🧬 參考頻道的剪輯 pattern library = INTEGRATE 不 REPLACE（M77）** — 病毒短片 pattern library 是「素材庫」，不換創作者人格。3 類用法：<br>    ✅ **INTEGRATE (universal craft)**：A 節奏 / B3-B4 視覺 / C2-C3-C5 權威 / D2-D4 聲音 / E promise — 直接套<br>    ⚙️ **CALIBRATE (依創作者舒適區)**：B1 slogan card 用自己的色彩 palette / C1 NAMING SELF 軟尾語氣 / D1 LUFS 推 -11~-12 不 -10 / G 極端化只 thumbnail 不 audio<br>    ❌ **REPLACE → 永遠用自己的 signature**：F1 silhouette → **你自己的品牌 outro 卡（可無人入鏡，M78 — 若創作者不露臉就不錄 talking head）** / F2 hand-on-chin → **你自己的結尾招牌句字卡** / B2/C4 phone view count → 你自己的社群截圖<br>    **永遠保留**：你自己的品牌 outro / 訂閱提示 / 你的社群 CTA<br>    詳 [Viral Short Playbook integration matrix](viral-short-playbook.md) 跟你自己的剪輯招牌 memory 檔

---

## 📥 觸發 Mode A 最少需要的資訊

使用者說「規劃我下一支X」時，autopilot 至少需要：

1. **題目** — X 是什麼（例：「某工具教學」「某新功能介紹」）
2. **重點 angle**（選一個 Register）：
   - 工具 demo / 教學 → **High-Demo**（最常見）
   - 自我成就 / 反思 / 數據分享 → **High-Reflective**
   - 自家工具 bug / 更新溝通 → **High-Update**
   - 玩具 / 興趣 / DIY / 個人 → **Low** 系列
   - 旅遊紀錄 / 日常 → **Vlog**
3. **同時做 Shorts/Reels?** （Y/N — **預設 Y**）

→ 資訊不夠 → autopilot 主動反問 **1-2 個最關鍵**問題（不一次問 5 個）。

---

## 3 個 Mode

### Mode A — Plan（一句題目 → 完整 publish package）

**觸發**：「規劃我下一支X」「我想拍X 全部你來」「autopilot 一支X」「end-to-end X」「從題目到上架」

**步驟**：
1. **Pre-flight**（觸發 `yt-algorithm-mastery` Mode A）
   - Top 1% filter 評分（⭐⭐⭐⭐⭐ 5 級）
   - 若 ≤3⭐ → **立刻停下**，建議使用者改題目，列 3 個強化方向
   - 若 ≥4⭐ → 繼續

2. **跨平台規劃**（觸發 `video-craft-playbook` Mode A）
   - 平台選擇 + 配比 / 長度甜蜜帶 / 結構框架

3. **腳本生成**（觸發 `yt-script-style` Mode D）
   - 從題目 + voice profile 生草稿
   - 自動套對應 Register
   - Open loop + mini-promise + retention 結構

4. **腳本精簡**（觸發 `yt-script-style` Mode B）
   - 砍 20-25% 贅詞（lean preference）
   - 招牌密度檢查

5. **留存預檢**（觸發 `yt-algorithm-mastery` Mode B）
   - 預測 30s / 1min / 3min / 結尾 retention
   - 若預測 <教學基準 → 微調腳本

6. **Packaging War Room**（觸發 `yt-algorithm-mastery` Mode C）
   - 挑 **TOP 1 title** + 2 個 A/B 變體（不給 buffet）
   - **TOP 1 thumbnail concept** + 2 個變體（YT Test & Compare A/B/C）
   - Quality Click Ratio 紅線檢查

7. **包裝補完**（觸發 `video-craft-playbook` Mode B）
   - Description / Hashtag / Tags
   - **🎬 畫面規劃**：依 script 段落映射視覺 cue（script-anchored，不假 timestamp）

8. **寫入 `video_log.md`** 新 entry（編號自動 +1）
   - 若 ≥5 entries 且 ≥3 outcome → 主動建議使用者接著跑 Mode C

9. **排監控時程**：
   - 48-72h: 提醒使用者觸發 Mode B + `mastery` Mode D
   - 1 週: 觸發 `mastery` Mode E

**輸出格式詳見** `video_log.md` 內 `## Template for new entries`

---

### Mode B — Log Outcome（發布後紀錄 + 一鍵路由）

**觸發**：「我發了 #N 數據是 CTR X% / AVD X」「記錄 #N 的表現」「#N 結果出來了」

**步驟**：
1. 讀 `video_log.md`
2. 補對應 entry 的 outcome 欄位（發布時間 / 48h CTR / 1-min retention / 1 週 AVP / 結尾 / Traffic source）
3. Tag ✅「what worked」+ ❌「what didn't」
4. **一鍵路由 post-publish workflow**：
   - **發布後 48-72h** → 自動接 `mastery` Mode D (Analytics Decode)
   - **發布後 1 週** → 自動接 `mastery` Mode E (Iteration Engine)
   - 使用者不必再說一次「請跑 mastery D」

---

### Mode C — Optimize Patterns（從歷史學經驗）

**觸發**：「review 我的 video 表現」「最近哪些 title 公式有效」「optimize 默認值」「跑 retrospective」

**步驟**：
1. 讀 `video_log.md` 所有 entry
2. 找 pattern（≥5 outcome 才有意義；無 outcome 則跑 **Process Retrospective** 看卡關 / token / antipattern 重複）：
   - 哪些 **title 框架** CTR 最高？
   - 哪些 **thumbnail variant** 贏 Test & Compare 比例最高？
   - 哪些 **題目類型** retention 最好？
   - 哪些 **發文時間** 表現好？
   - 哪些 **長度** 段表現好？
   - 哪些 **Sub-mode** 成長最快？
3. 寫入 `optimization_log.md`
4. 若發現強 pattern → 主動 propose 更新本 SKILL.md「預設值」清單

→ Process Retrospective 範例：見 `optimization_log.md` § Mode C #1

---

## 🎬 Edit Pipeline（**委派給 `capcut-agent-ops`**）

**舊版（已淘汰）**：Mode D 委派 DaVinci edit agent — DaVinci Free HEVC 不支援 + Export 無 NVENC。該 agent 與 playbook 已淘汰，不在本 kit 內。

**新版**：Edit pipeline 走 `capcut-agent-ops` SKILL Path A-E：

| Path | 用途 | ETA | Token |
|---|---|---|---|
| **A: Export only** | JSON patched，純 Export agent | 5-8 min | 低 |
| **B: 套單一 template + Export** | 28 caption 同花字 | 25-40 min | 中 |
| **C: 多模板 + 貼圖 + Export** | marker/main/sub 分配 | 60-90 min ⚠ daily limit | 高 |
| **D: JSON direct edit** ⭐ | 換 caption 文字 / font / size / position | <1 min | **極低** |
| **E: 純 ffmpeg** | silent vlog 接受 ffmpeg 字幕（M35 證實 vlog autopilot 真正答案）| ~90 sec | 極低 |

### 預設選擇（Mode C #1 確認）

**Vlog autopilot 預設**：**Path D + Path A**（JSON edit + Export only agent）
- ❌ 不要反射 Path C（多模板 agent — 60-90 min 易撞 daily limit + Pro paywall）
- ✅ Silent vlog → 預設 Path E（ffmpeg-only 90 sec）

**Agent spawn 上限 = 2 / task**。連 2 個 agent 失敗 → 停止 spawn，改 Path D 或 user manual。

詳細 agent brief 模板：[capcut-agent-brief-template.md](capcut-agent-brief-template.md)

---

## 與其他 skill 的呼叫約定

| 步驟 | 呼叫 | 為什麼 |
|---|---|---|
| 1 Pre-flight | mastery A | Top 1% filter 是 gating |
| 2 Plan | playbook A | 跨平台廣度需要 |
| 3 Generate | script D | voice 在這個 skill |
| 4 Optimize | script B | lean 砍贅詞 |
| 5 Retention | mastery B | YT 深度 |
| 6 Packaging TOP | mastery C | MrBeast 級 |
| 7 包裝補完 | playbook B | description / hashtag |
| 8 Log | 本 skill | autopilot 持有 |
| 9 Edit | capcut-agent-ops | CapCut Path A-E |
| 10 Audit / Iterate | mastery D / E | 數據深度判讀 |

**不重複任何邏輯** — 細節都在被呼叫的 skill 裡，本 skill 只 orchestrate。

---

## 🔄 持續優化 + 訓練 closed-loop

```
[Idea] → Mode A (Plan) → publish package
              ↓
        [USER 錄 raw]
              ↓
     Edit Pipeline (capcut-agent-ops Path A-E)
              ↓
    output/long-form.mp4 + shorts.mp4
              ↓
        [USER polish + upload]
              ↓
        Mode B (Log Outcome)
              ↓
    ┌─────────┴─────────┐
    ↓                   ↓
mastery D            optimization_log.md
(48-72h)             累積 7 維度數據
    ↓                   ↓
mastery E            (≥3 outcome) 提示 Mode C
(1 週)                 ↓
                     (≥5 outcome) 自動 Mode C
                        ↓
                     Pattern → propose 更新預設值
                        ↓
                     [越用越聰明 ✨]
```

### 觸發頻率（自動）

| 事件 | 動作 |
|---|---|
| 使用者 Mode B 完 | 累積 outcome；不更新預設 |
| Agent run 完寫 report | 抽 lessons → optimization_log.md |
| video_log ≥3 outcome | 主動「跑 Mode C？」提示 |
| video_log ≥5 outcome | 自動跑 Mode C + propose 預設值更新 |
| 連 3 篇 CTR 低於**你自己的點火帶**（`<fill in>`，量法 → `youtube-algorithm-mastery.md` §4） | 紅標 + 強制 mastery Mode E |
| 單 asset 用 ≥5 次 | 列「核心 asset」cheat sheet |
| 單 asset 連 3 次被改掉 | 列「候選下架」|

### 訓練 7 個維度（每 video 累積）

1. Title 框架 → CTR
2. Thumbnail variant → Test & Compare 勝率
3. 發文時間 → 24h views
4. 長度 → AVP
5. Sub-mode → Retention
6. Asset usage → 庫品質
7. Edit-time → 自動化進步

詳：`optimization_log.md` §「持續訓練的數據維度」

---

## 檔案結構

本 kit 出貨的樣子（`src/` 給工具、`knowledge/` 給心法）：

```
video-autopilot-kit/
├── knowledge/
│   ├── autopilot-workflow.md      ← 本檔（orchestration 邏輯）
│   ├── meta-lessons.md            ← M 系列避坑大全 + antipatterns + Self-critique + SOP
│   └── …                          ← 其餘心法檔見 knowledge/README.md
└── src/silent_vlog_maker/         ← Python pipeline helpers
    ├── __init__.py                ← Top-level re-exports
    ├── constants.py               ← SAFE_ZONE / fonts / colors / TONEMAP / curves
    ├── audit.py                   ← 11 維度素材 audit（GPS + 拍攝時間 + camera + audio）
    ├── scene_audit.py             ← M12 chronological + GPS scene cluster
    ├── frame_audit.py             ← M9/M34 hi-res 640×360 frame grids + description cache
    ├── audit_report.py            ← Markdown + JSON full audit report
    ├── text_overlay.py            ← Overlay class + POSITION_PRESETS + TV_VARIETY_PRESETS
    ├── effects.py                 ← KenBurns + cinematic + xfade
    ├── pipeline.py                ← Voice loader + build_filter_complex
    ├── helpers.py                 ← Backward-compat shim
    └── voice_profiles.json        ← Voice cache
```

你自己那兩份「會長大的」記錄檔（影片 log / 優化 log）放你自己的工作資料夾，不進本 repo
（本 repo 的 `.gitignore` 已把 `profiles/` 與 `channel_state.json` 這類個人化檔排除）。

### 🚀 Mass Production Workflow（使用者丟任何素材都能 zero-config 開跑）

```python
from silent_vlog_maker import run_full_audit
from pathlib import Path

raw_dir = Path("videos/current/raw/<topic>/")

# Step 1: Full audit (11 維度 + M12 scene cluster + M9 hi-res grids)
result = run_full_audit(raw_dir=raw_dir, output_dir=Path("videos/current/audit/"), project_name="...")

# Step 2: 依 audit 結果決定 layout / content type / 走哪條 Path
#   —— 這一步綁「你自己的」內容類型與預設值，所以本 kit 不出貨硬編碼的路由器；
#      規則寫在 templates/content_pipeline.template.md（複製成 profiles/content_pipeline.md 再填）。
layout = "portrait"   # 由 audit 的 rotation / 寬高比判定

# Step 3: Apply decision
from silent_vlog_maker import encode_args_for, get_preset, Overlay
args = encode_args_for("yt_shorts" if layout == "portrait" else "yt_longform")
hook_preset = get_preset("title_hook", layout=layout)
```

### 📦 Mass production infrastructure 模組

| Module | 用途 |
|---|---|
| `templates/content_pipeline.template.md` | 你自己的內容類型 → layout / BGM / 字幕風格 / 發布前 checklist（取代綁個人規則的路由器）|
| `asset_scanner.py` | scan_all_assets() 掃 bgm/fonts/templates → 更新 index.json |
| `constants.py` 升級 | ENCODE_ARGS_BY_PLATFORM (5 platforms: yt_shorts / yt_longform / ig_reels / tiktok / threads) |
| `text_overlay.py` 升級 | LANDSCAPE_PRESETS + LAYOUT_PRESETS map + get_preset(name, layout) |

### 🔭 Audit pipeline (v3)

3 大輸出（每次接到 raw 都跑）：
1. **R1 v2 — 11 維度 audit** (codec / res / fps / rotation / HDR / pix_fmt / duration + **GPS + 真實拍攝時間+TZ + camera + audio + file_size**)
2. **M12 — Scene Timeline** auto cluster（time gap > 30 min OR GPS > 1km → 新 scene）
3. **M9 / M34 — 4-frame hi-res grids per clip**（640×360 + label）

實測：一批旅遊 MOV 素材 → 自動 cluster 成多個 scene / GPS 100% coverage / 真實拍攝時間正確（修復了之前誤用 import time 的 bug，改讀 metadata 拍攝時間）。
