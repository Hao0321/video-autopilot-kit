# video-autopilot — 規劃 / 營運手冊（Mode A/B/C 細節）

> 從 `SKILL.md` 拆出（2026-07-28 R5 token 減量）。**剪片 session 不需要讀本檔**；
> 規劃新片、跑 retrospective、查檔案結構時才讀。SKILL.md 保持極短決策路由。

---

## ⚡ Cheat Sheet — autopilot 鐵則

1. **用戶給一句題目 → 立刻跑 Mode A**，不要先問太多問題
2. **預設值（不問用戶就用）**：
   - Sign-off **Variant B (Typo Boilerplate)** — 主流 8+/36 篇
   - **🔒 片尾一律用「自由工坊」社群做結尾**（2026-07-07 Hao 定死：每支都要）—— Hao0321 Studio 彩色 outro 卡 + SUBSCRIBE 黃徽章 + **自由工坊 Discord CTA 收尾**（招牌 F-slot，Tim Pan #14 已列、現升級為每片強制項，規劃/剪輯都不可略）
   - **🔒 內容要豐富有趣、多畫面拼接**（2026-07-07 Hao 定）—— 每段旁白配多個對位畫面切換（不是一句話一個長鏡）、b-roll 種類多樣、節奏密（教學長片 cuts ≥12/min）、真材料+自生質感動畫+demo 交錯；**寧可素材過剩不要畫面單調**（承 R10「回 5-8min」＝要有足夠豐富素材撐長度，不是拉長空鏡）
   - **片長 5-8 min**（R4/R10 修正：不是砍到 2-3min）；規格二選一：主線 5-8min 真長片 or 直接 Shorts，**2-4min 橫式刪除**
   - **hook 逐秒模板（R24）**：0-5s 真值結果 cold open（禁自介/大家好/頻道 intro）→ 5-15s 本片承諾 → 15-30s 直進第一步；縮圖畫面必須 30s 內兌現；每 2-3 分鐘 1 次 1.5s flash-forward re-hook；pattern interrupt：30s 首發、之後每 75±15s（細節 → mastery.md R15-R25 + `references/editing-techniques-2026.md` §六路深研升級計畫）
   - 標題**成就前置**（反差成就第一拍、內行人設當佐證）；縮圖 signal「AI+成就」**不是遊戲/工具截圖**（R9 死因#2）；縮圖**背景壓暗/降飽和**上架前機械 checklist
   - metadata（標題+描述前125字+開頭30秒口播）**語義密集打「工具名+任務+成果」**餵 Semantic ID（R11）
   - 發文時間 **11pm 台北** 或 **3:55pm**（用戶實測）
   - YT Test & Compare **2 variants**（曝光量限制，非爆款別開 3 variants，R9-bench）並行 2 週
   - 教學頻道 KPI（Hao 校準值，R9/R10 雙指標）：**CTR 8%+（過擴圈 gate）/ 絕對 AVD ≥1:30 / 30s 留存 70%**。通用基準不在此重抄——見 `yt-algorithm-mastery/mastery.md` TL;DR；**Hao 校準值（本預設值區）優先**
   - 平台配比：**1 長片 + 標配 2-3 支高光 Shorts**（掛官方「相關影片」導回，發布 SOP 必要件非救援，R12）
   - **系列化**：固定系列名+集數、縮圖模板統一、片頭 10s 建立「第 N 集」追劇感、end screen 導下一集（R13 養 returning viewers）
   - **冷啟動純 YT-native**（不依賴外部導流，R5 使命）；主 KPI 盯 returning viewers 曲線不是單片曝光（R13）
3. **Pre-flight ≤3⭐ → fail loud**，告訴用戶題目該改不要硬做
4. **每支 video log 進 `video_log.md`**（Mode A 自動寫入；Mode B 補 outcome）
5. **發布後監控時程自動排**：48-72h（mastery Mode D）+ 1 週（mastery Mode E）。**publish checklist 追加（2026-07-09）**：day-0＝1h 內 Communities video post+pin + Shorts 入口（R18 seed）；48h 內禁 panic 換縮圖；day-7 刪 Hype CTA（R25）；day-14 Ask Studio 三問記 Log Outcome（R23）；T&C 3 變體測承諾強度跑滿 2 週（R15）→ 細節 mastery.md R15-R25
6. **用戶提到的任何 preference / 缺漏 / 規則 → 立刻寫進對應 SKILL.md** — 用戶不該講第二次
7. **🎬 畫面規劃 = script-anchored** — 不假時間戳；每個視覺 cue 錨定到 quoted text；逐句讀腳本才開始設計
8. **Edit pipeline 預設走 `capcut-agent-ops` Path D + A**（不是反射 Path C 多模板 agent）— 詳 §「Edit Pipeline」
9. **Agent spawn 上限 = 2 / task**（超過 = 換 path）— 詳 capcut-agent-ops/references/token-efficiency-lessons.md
10. **🔭 接到 raw 第一件事 = 跑 `run_full_audit()`**（2026-05-24 v3）— R1 11 維度 + M12 scene cluster + M9 hi-res frame grid 一鍵跑完，輸出 audit_report.md / json / grids → caption 配畫面從此不出錯
11. **🛣️ 接著跑 `route_content()`**（2026-05-24 v4 mass production）— 自動偵測 layout (portrait/landscape/mixed) + content type (vlog/teaching/diy) + 推薦 Path + BGM + preset family。**用戶丟任何素材都能 zero-config 開跑**
12. **🎓 Build 第一件事 = 跑 `print_pre_build_checklist(decision.content_type)`**（2026-05-25 Mode C #2 AP9 落地）— 顯示這個 content type 的 5 questions / defaults / wraps_lessons / verify_steps。**問用戶 batch 1 message 5 件事**（不要 5 次來回）+ 自動 enforce M-series（M64/M66/M68/M69/M70-M72 等）。**第一次跑 new content type 不再卡 3 輪 ship。** 已 register：`teaching_longform` / `food_vlog` / `travel_vlog` / `screen_recording_teaching`
13. **🔒 「已完成」定義 = mp4 re-exported + 3 frame visual verify pass**（Mode C #2 AP10 落地）— JSON saved/synced **不算 done**。任何 JSON edit → 自動 flag「mp4 stale，需 re-export」
14. **TIM PAN = INTEGRATE 不 REPLACE（M77/M78）**：借技法不借人格，Hao signature（不露臉/三件套/白字/voice）永遠保留。完整 3 類矩陣 SoT → `video-craft-playbook/references/tim_pan_viral_short_playbook.md` + memory `tim_pan_integration.md`
15. **📋 發布套件交付 = 純文字「可直接複製」格式（2026-07-02 Hao 定）** — 每個「貼上單位」各自獨立 fenced code block（```），讓 Hao 整塊選取直接貼：**標題（每個一塊）／整份影片說明（一塊）／Threads 正文（一塊）／Threads 留言（一塊）**。鐵則：<br>    ・**說明區塊內【不夾任何 markdown 裝飾】**（不用 `**`、`>`、`#` 標題）——YouTube 說明欄不 render markdown，貼進去會看到符號。hashtag 直接放說明結尾一行<br>    ・**章節時間戳一律用【成片真實時間】**（讀 `narration_offsets.json` beat starts 轉 m:ss），不是腳本草稿的預估時間<br>    ・Threads 正文 = 1 段不換行純 F19（無連結）；留言那則才放 YT 連結（R5）<br>    ・要 Hao 手填的（Discord 連結／發片後才有的 YT 連結）用**明顯佔位字**（如「你的 Discord 邀請連結」）不要用抽象 `[連結]`<br>    ・存成 `發布套件_可複製.md` 之外，**也直接在對話貼出來**讓 Hao 當下能複製<br>    （產出 = `發布套件.md` 策略版[標題框架/縮圖/監控] + `發布套件_可複製.md` 純貼上版，兩個都給）
16. **✍️🔒 寫任何旁白/腳本前 = 必先載入 `yt-script-style` 的 `style_profile.md` + samples，套 Hao 招牌**（直接／**工具一律用「他」物件擬人化**／我跟你們說／真的超級X／!!／particle 呢拉啦~／identity「我們不只是創作者也是開發者」／mission「帶給沒有任何 AI 基礎的人」／近期 sign-off boilerplate）。⚠️ **不分 full autopilot 還是手動/局部規劃 —— 只要產出 Hao 要唸的字，一律走 `yt-script-style` Mode D，絕不憑通用口吻寫。** Lean preference：第一版就砍 20-25% 贅詞但招牌不動。（2026-06-24 手動規劃長片旁白時**跳過這步**、用了「show 你/爛活/盲區/掛零」非 Hao 用詞 → Hao 抓到「你真的有參照我的設定嗎」。固化 **M101**）
17. **💾🔒 版本是 metadata，不是完整影片副本（M115）**：每個 job 只有 `_out/current.mp4`；修改用 candidate→`os.replace` 原子換版，歷史只追加 `.autocut-history.jsonl`。禁止 pipeline 自動建立 `v2/v3/FINAL/old/backup` 影片或資料夾。原始素材永遠唯讀；QA 綠後只清白名單 transient；里程碑只留核准／已發布、最多 2 份；跨資料夾交付同 volume 優先 hard link。

---

## 3 個 Mode

### Mode A — Plan（一句題目 → 完整 publish package）

**觸發**：「規劃我下一支X」「我想拍X 全部你來」「autopilot 一支X」「end-to-end X」「從題目到上架」

**步驟**：
1. **Pre-flight**（觸發 `yt-algorithm-mastery` Mode A）
   - Top 1% filter 評分（⭐⭐⭐⭐⭐ 5 級）
   - 若 ≤3⭐ → **立刻停下**，建議用戶改題目，列 3 個強化方向
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
   - 若 ≥5 entries 且 ≥3 outcome → 主動建議用戶接著跑 Mode C

9. **排監控時程**：
   - 48-72h: 提醒用戶觸發 Mode B + `mastery` Mode D
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
   - 用戶不必再說一次「請跑 mastery D」

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
3. 每個候選規則用 `knowledge_lifecycle.py record` 入帳；相同規則累加 support，不複製段落
4. support ≥3 且無衝突才 pinned；涉及策略預設時再提出可回復的 SKILL/domain card 更新

→ 歷史 Process Retrospective 範例仍在 `optimization_log.md`；該檔 2026-08-08 起凍結為 evidence。

---

## 🎬 Edit Pipeline（**委派給 `capcut-agent-ops`**）

**舊版（已淘汰 2026-05-23）**：Mode D 委派 `davinci-edit-agent` — DaVinci Free HEVC 不支援 + Export 無 NVENC + 用戶已改用 CapCut Pro。agent + playbook 已 archive 到 `agents/_archive/`。

**新版**：Edit pipeline 走 `capcut-agent-ops` SKILL Path A-E：

| Path | 用途 | ETA | Token |
|---|---|---|---|
| **A: Export only** | JSON patched，純 Export agent | 5-8 min | 低 |
| **B: 套單一 template + Export** | 28 caption 同花字 | 25-40 min | 中 |
| **C: 多模板 + 貼圖 + Export** | marker/main/sub 分配 | 60-90 min ⚠ daily limit | 高 |
| **D: JSON direct edit** ⭐ | 換 caption 文字 / font / size / position | <1 min | **極低** |
| **E: 純 ffmpeg** | silent vlog 接受 ffmpeg 字幕（M35 證實 vlog autopilot 真正答案）| ~90 sec | 極低 |

### 預設選擇（Mode C #1 2026-05-23 確認）

**Vlog autopilot 預設**：**Path D + Path A**（JSON edit + Export only agent）
- ❌ 不要反射 Path C（多模板 agent — 60-90 min 易撞 daily limit + Pro paywall）
- ✅ Silent vlog → 預設 Path E（ffmpeg-only 90 sec）

**Agent spawn 上限 = 2 / task**。連 2 個 agent 失敗 → 停止 spawn，改 Path D 或 user manual。

詳細 agent brief 模板：`capcut-agent-ops/references/agent-brief-template.md`

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
    _out/current.mp4（單一目前成片）
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
| 用戶 Mode B 完 | 累積 outcome；不更新預設 |
| Agent run 完寫 report | 抽候選 lesson → `knowledge_lifecycle.py record` |
| video_log ≥3 outcome | 主動「跑 Mode C？」提示 |
| video_log ≥5 outcome | 自動跑 Mode C + propose 預設值更新 |
| 連 3 篇 CTR <4% | 紅標 + 強制 mastery Mode E |
| 單 asset 用 ≥5 次 | 列「核心 asset」cheat sheet |
| 單 asset 連 3 次被改掉 | 列「候選下架」|

### 訓練 8 個維度（每 video 累積）

1. Title 框架 → CTR
2. Thumbnail variant → Test & Compare 勝率
3. 發文時間 → 24h views
4. 長度 → AVP
5. Sub-mode → Retention
6. Asset usage → 庫品質
7. Edit-time → 自動化進步
8. Storage bytes／重複副本／transient 清理量 → 生產效率

歷史維度定義見 `optimization_log.md`；新規則狀態與衝突見 `references/knowledge-lifecycle.md`。

---

## 檔案結構

```
video-autopilot/
├── SKILL.md                       ← 本檔（orchestration 邏輯）
├── video_log.md                   ← 每支影片 plan + outcome 紀錄（活的）
├── video_log_archive.md           ← 已 shipped 歷史 entry 歸檔
├── optimization_log.md            ← legacy evidence（凍結，不再直接追加）
├── knowledge_lifecycle.py          ← 新回饋去重、支持數、衝突與 pinned 晉升
├── knowledge/state.json            ← runtime 只讀的 bounded operational memory
├── storage_lifecycle.py           ← M115 current-only／原子換版／history／清理／hard-link／容量 gate
├── editorial_templates.py         ← M116 Bright Editorial bridge；公開 template_engine 為單一 SoT
├── references/                    ← 知識庫（全列；讀檔頭挑需要的）
│   ├── meta-lessons-canon.md      ← M1 起持續增補（最新編號見 canon 檔頭）+ antipatterns + Self-critique + SOP
│   ├── hao-teaching-longform-method.md ← 🎓 教學長片 10-stage 個人方法論 master（三恆定 identity）
│   ├── script-retention-2026.md   ← ✍️ M110 腳本留存 SoT（script_gate v2 詞表/節奏依據）
│   ├── editing-techniques-2026.md ← 2026 剪輯技巧（hook/pacing/re-hook 全可量化）
│   ├── editing-wave5-finecut-2026.md ← 🪡 wave5 細剪·留存·數據呈現·工具 37 條（2026-07-23）
│   ├── editing-wave6-2026.md      ← 🌊 wave6 新一波剪輯研究（2026-07-24 入庫）
│   ├── editing-craft-fundamentals.md ← 業餘→pro 基本功速查
│   ├── editing-master-techniques.md  ← master 級（Murch/配樂/二級調色/感受殘留 gate）
│   ├── niche-editing-grammar.md   ← 各題材剪輯文法
│   ├── niche-fonts-colors.md      ← Shorts 字體+配色（white-first）
│   ├── storage-lifecycle.md       ← M115 current-only／原子換版／保留政策／migration CLI
│   ├── bright-editorial-template-system.md ← M116 17 style×10 role×橫直 reflow／題材路由／開源規則
│   └── shorts_reels_2026_best_practices.md ← 直式 Shorts data-backed 規則
├── longform_maker/                ← 🎓 教學長片 ffmpeg 二代 pipeline（13 支可重用模組，支支 import 不 copy-paste）
│   ├── LONGFORM_PIPELINE.md       ← pipeline 總覽 + run 順序（剪教學長片必讀）
│   ├── script_gate.py             ← ✍️ v2 M110 腳本閘門（詞表 fail + 節奏 warn）
│   ├── word_captions.py           ← 📝 M105 字級時間字幕
│   ├── screen_clean.py            ← 🧼 M104 螢幕錄影去個資
│   ├── audio_chain.py             ← 🎚️ M103 pro 音訊鏈
│   ├── proof_stage.py 🆕          ← 📸 M107 真戰績截圖擺台 + assert_proof_sources gate
│   ├── video_handlers.py 🆕       ← 🎞️ 六 handler beat 家族（PLAN dict 即建片）
│   ├── fx_lib.py / brand_templates.py / asset_forge.py / music_engine.py
│   ├── transitions.py / grade_lib.py / thumb_template.py
│   ├── reference_impl_longform01/ ← 長片01 可重現 reference 實作（build_audio/video/final…）
│   └── _demo/                     ← self-test 產物
├── silent_vlog_maker/             ← vlog/Shorts Python pipeline helpers（21 檔）
│   ├── audit.py ⭐v3 / scene_audit.py / frame_audit.py / audit_report.py ← R1 11d + M12 cluster + M9 grids
│   ├── content_routing.py / routing.py / asset_scanner.py / checklists.py / verify.py / quality_check.py
│   ├── constants.py / text_overlay.py / effects.py / pipeline.py / helpers.py / screen_rec_cleaner.py
│   ├── shorts_template.py / shorts_captions.py / shorts_vertical.py ← 直式 Shorts
│   ├── bright_card_e2e.py         ← 真 ffmpeg 中文字卡回歸（避 Windows heredoc cp950 假綠／假紅）
│   └── __init__.py / voice_profiles.json
└── projects/
    └── registry.py                ← auto_sync_registry() 多專案 state mgmt
```

### 🚀 Mass Production Workflow（2026-05-24 v4 — 用戶丟任何素材都能 zero-config 開跑）

```python
from silent_vlog_maker import run_full_audit, route_content, print_routing_decision
from pathlib import Path

# _INBOX 制（丟哪向=剪哪向；舊 videos/current 已淘汰）：
#   橫式 → videos\_INBOX\橫式-landscape-YT長片\<N>\；直式 → videos\_INBOX\直式-vertical-Shorts-Reels\<N>\
raw_dir = Path("<project-root>/videos/_INBOX/<format>/<content-id>")

# Step 1: Full audit (R1 v3 11d + M12 scene cluster + M9 hi-res grids)
result = run_full_audit(raw_dir=raw_dir, output_dir=raw_dir / "audit", project_name="...")

# Step 2: Auto-routing — layout + content type + recommend path
decision = route_content(raw_dir)
print_routing_decision(decision)
# → 自動知道：portrait/landscape、vlog/teaching、Path E/D/A、BGM 旅遊-01.mp3、preset family landscape

# Step 3: Apply decision
from silent_vlog_maker import encode_args_for, get_preset, Overlay
args = encode_args_for("yt_shorts" if decision.layout == "portrait" else "yt_longform")
hook_preset = get_preset("title_hook", layout=decision.recommended_preset_family)
```

### 📦 v4 新模組（mass production infrastructure）

| Module | 用途 |
|---|---|
| `content_routing.py` | route_content() 自動判斷 type + layout + path + BGM + preset |
| `asset_scanner.py` | scan_all_assets() 掃 bgm/fonts/templates → 更新 index.json |
| `projects/registry.py` | auto_sync_registry() 多專案 state mgmt（current + CapCut drafts）|
| `constants.py` 升級 | ENCODE_ARGS_BY_PLATFORM (5 platforms: yt_shorts / yt_longform / ig_reels / tiktok / threads) |
| `text_overlay.py` 升級 | LANDSCAPE_PRESETS + LAYOUT_PRESETS map + get_preset(name, layout) |

### 🔭 Audit pipeline (v3)

3 大輸出（每次接到 raw 都跑）：
1. **R1 v2 — 11 維度 audit** (codec / res / fps / rotation / HDR / pix_fmt / duration + **GPS + 真實拍攝時間+TZ + camera + audio + file_size**)
2. **M12 — Scene Timeline** auto cluster（time gap > 30 min OR GPS > 1km → 新 scene）
3. **M9 / M34 — 4-frame hi-res grids per clip**（640×360 + label）

實測：49 個馬來西亞 MOV → **14 個 scene** 自動 cluster / GPS 100% coverage / 真實拍攝時間正確（修復了之前用 import time 的 bug）。
