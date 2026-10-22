# 🎬 video-autopilot-kit

> Current version: v0.25.0
>
> **一句話架構：VA（這個 kit）負責規劃、判斷與檢查；[Editkin](https://github.com/Hao0321/Editkin) 負責所有渲染。**
> 素材證據 → `edit-plan/v4` → audit → 原子套用 → render → 審片 → 成效學習，整條路只認一份執行合約
> [`src/workflow_contract.py`](src/workflow_contract.py)。v0.25.0 起，舊的 Python／FFmpeg 渲染器全部退役
> （見下方〈已退役〉）。

## 🧩 先裝 Editkin（必要）

VA 只負責規劃和檢查，**真正剪片、渲染的是 Editkin**。沒裝 Editkin，什麼都剪不出來。請照這個順序：

1. **安裝 Editkin**：到 [Editkin 公開預覽版 v0.15.0-preview.20261022](https://github.com/Hao0321/Editkin/releases/tag/v0.15.0-preview.20261022)
   下載 Windows 安裝檔（約 1.25 GB）。這版沒有數位簽章，出現「Windows 已保護您的電腦」時，點「其他資訊」→「仍要執行」。
   → [詳細步驟](SETUP.md#0-1-下載並安裝)
2. **接上你的 AI**：Editkin 首頁「AI 協助剪輯」→「連接 AI 助手」→「連接 Claude Code」或「連接 Codex」（一鍵設定）。
   重新開啟 Claude Code／Codex 後，`/mcp` 要看得到 `editkin`。→ [詳細步驟](SETUP.md#0-3-接上你的-ai)
3. **安裝這個 Kit**：下載 Kit 的 `install_or_upgrade.py`，先跑 `python install_or_upgrade.py --install-root <資料夾> --check`，
   再改用 `--apply --install-skill` 跑一次。Skill 會裝到 `%USERPROFILE%\.codex\skills\video-autopilot\`，
   Editkin 的「複製開工指令」就找得到它。→ [詳細步驟](SETUP.md#0-4-安裝這個-kit)

只想先試試？Editkin 內建的**簡單模式不需要任何 AI 帳號**，放一支有人講話的橫式影片就能自動粗剪。
這是**預覽版**：目前只有 Windows、沒有自動更新，一定會遇到 bug；新版本請回 [Editkin releases](https://github.com/Hao0321/Editkin/releases) 下載。

> 一套**框架式**的 YouTube／短影音自動化工具 + 方法論模板。
> 給你可續跑、可稽核的 Editkin 剪輯流程與一組品質閘門，加上一份「問卷」——
> 你回答關於**你自己頻道**的問題，它就變成屬於你的系統。
>
> ⚠️ **不含任何人的私人數據** —— 後台讀數（自己的與別人的）／個人檔案一律不進 repo（`profiles/`、`config.py` 是 gitignored 本機檔）。
> 兩類具名例外，兩類都是**公開資訊**不是私人數據：① LICENSE 與各 README 的作者署名；
> ② `knowledge/` 引用**第三方公開創作者／頻道**時會直接寫名字（例如演算法檔引用的公開戰術、
> `teaching-niche-playbook.md` 的參考頻道列），規矩是 **citation-first：沒有可點的出處連結就不給數字**。
> voice 詞表、KPI 門檻與社群欄位要嘛是**空白模板**（`<fill in>` / `______` / 產出檔的 `{你的…}` 佔位字樣），要嘛**標示為「範例值」**，你填你的。
> 反過來說：`knowledge/` 裡的方法論**是**原作者的實戰結論，那是刻意開源的部分 —— 是「怎麼想」，不是「他的數字」。

**誠實邊界**：公開控制器只涵蓋媒體素材的 Editkin 工作流程。離線測試與 CI 用的是合成 fixture，
不等於真實 Editkin 成片、第三方帳號操作或主觀美術驗收。更新由你手動執行並確認；未宣稱簽章更新或全面資安驗證。

## 🧭 架構：VA 規劃與檢查，Editkin 渲染

一次剪輯的完整路徑：

`你的素材` → **VA** 證據收據 → **VA** 寫 `edit-plan/v4` → **Editkin** audit → **Editkin** 原子套用 → **Editkin** render → **VA** 交付 QA → **你** 審片 → **VA** 發布包與成效學習

| VA（本 kit，MIT） | Editkin（桌面剪輯器，GPL-3.0，另行安裝） |
|---|---|
| 每份素材的證據鏈：prepare → 關鍵幀 → 逐字稿窗口 → 語意紀錄 | 讀素材、抽關鍵幀與逐字稿 |
| 寫 `hao.video-autopilot.edit-plan/v4`，綁齊所有收據 | audit 與一次性原子套用 |
| 腳本、Shorts 結構與字幕、節奏、旁白覆蓋、交付 QA 等閘門 | **所有渲染**：動態圖形、模板、Looks／濾鏡、追蹤、roto 與主體遮罩 |
| 審片伺服器、發布中樞、成效學習 | 存成你可以繼續手動編輯的專案檔 |

VA 不直接操作 Editkin：你的 AI agent（任何支援 MCP 的 agent）照 `workflow_contract.py` 給的下一步呼叫
Editkin 的 MCP 工具，再把原始回應交回 controller 驗證。一頁版說明 → [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。

## 🆕 v0.25.0 重點

- **節奏場景規劃器 `src/rhythm_templates.py`**：把 story JSON 加上 Editkin 當下的 Motion Library catalog，
  排成逐幀精確的場景計畫 —— 只選已認證的項目、完整覆蓋每一幀、每景 2–5 秒預算（30 秒片預設 8–12 景，
  可明確覆寫）。它只規劃與檢查，不渲染、也不改 Editkin 專案，純 Python 標準函式庫。
  → [rhythm-scene-templates.md](codex-skill/video-autopilot/references/rhythm-scene-templates.md)
- **2D／3D 混合動態海報規劃**：[editorial-hybrid-motion.md](codex-skill/video-autopilot/references/editorial-hybrid-motion.md)
  定義每景的 scene job、追蹤與遮擋分級、實際操作路徑；context router 會把「2D／3D 混合」「動態海報」類需求導到這份文件。
- **Editkin Motion Library**：160 個原創效果（80 個文字動畫、40 個轉場、40 個背景），VA 透過 Editkin 模組
  `graphic.text_motion`、`transition.motion_pair`、`background.motion_loop` 呼叫。需要**內含 Motion Library 的
  Editkin 版本**：[Editkin 公開預覽版 v0.15.0-preview.20261022](https://github.com/Hao0321/Editkin/releases/tag/v0.15.0-preview.20261022)
  已內含（仍是預覽版，會遇到 bug）。模組不存在時 VA 會記錄 `NEW_MOTION_RUNTIME_REQUIRED`，不會默默退回舊效果。
- **直式 Shorts 對齊 Editkin 預覽版**：Kit 現在接受 Editkin 預設的 `kinetic` 節奏；這版 Kit 搭配上面的 Editkin
  預覽版，直式 Shorts 可以從頭跑到尾。
- **審片伺服器安全修正**：已授權的審片儲存在寫入當下會再驗一次；讀取 request body 期間 session 過期或被撤銷，
  就無法再寫入 `review.json`。

## ▶️ 60 秒看它跑（不用素材、不用 Editkin）

```bash
python examples/02_caption_broll_match.py # Editkin v4 合約自測：完整 DAG + fail-closed 回歸
python examples/04_shorts_gate.py         # Shorts 閘門：壞剪法被擋 → 修好放行 → 換平台也放行
python examples/05_interview_plan.py      # 訪談來賓閘門：沒來源的數據在「錄影之前」就被擋下
```

只需要 Python 3.9+：不用 ffmpeg、不用 `pip install`、不用真素材。細節見 [`examples/README.md`](examples/README.md)。

## 🎬 一次 Editkin v4 run 怎麼跑

```bash
python src/workflow_contract.py create --project <你的專案.editkin.json> \
  --material clip-a=<真實素材.mp4> --material clip-b=<另一份素材.mov>
python src/workflow_contract.py next <run>              # 下一批可執行步驟（可平行的會一起列）
python src/workflow_contract.py claim <run> <step>      # 取得 token 與要呼叫的 Editkin 工具／參數
python src/workflow_contract.py complete <run> <step> --token <token> --receipt <receipt.json>
python src/workflow_contract.py verify <run>            # 交付前驗整條收據鏈
```

- 合約步驟：contract → session → 每份素材 prepare → keyframes → context → semantics → route＋plugin discovery
  → plan v4 → audit → apply → render → visual review → outcome。
- 每份素材以 `CLIP_ID=SOURCE_FILE` 綁真實 bytes（SHA-256）；run 只放專案內 `videos/_AUTOPILOT/editkin-v4/`。
- apply 中斷且無法證明已提交 → 進 reconcile（`resume --apply-resolution ...`），禁止自動重套。
- 技術 QA 全綠仍要真人審片；機器不能代填 approved／certified。

完整狀態轉移 → [`editkin-workflow-execution.md`](codex-skill/video-autopilot/references/editkin-workflow-execution.md)；
卡住時 → [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)。

## 🧱 生產線與閘門

每條線都是同一個形狀：**知識層（為什麼）→ 機械閘門（不靠記憶）→ Editkin v4 run（執行）**。

| 生產線 | 知識層 | 機械閘門 | 執行 |
|---|---|---|---|
| **教學長片** | [`script-style-framework.md`](knowledge/script-style-framework.md)、[`script-retention-craft.md`](knowledge/script-retention-craft.md)、[`premium-motion-fx.md`](knowledge/premium-motion-fx.md) | `plan_gate` → [`script_gate`](src/longform_maker/script_gate.py) → `pace_gate` → `editkin_voiceover_gate` → `final_delivery_qa(profile="teaching_longform")` | Editkin v4 run |
| **直式 Shorts／Reels** | [`shorts-mastery-2026.md`](knowledge/shorts-mastery-2026.md)、[`vertical-teardown-method.md`](knowledge/vertical-teardown-method.md) | [`shorts_gate`](src/longform_maker/shorts_gate.py)：結構與字幕規則，片長帶**依平台**（YT 死區不套到 IG/FB） | Editkin v4 run |
| **節奏場景／品牌 Motion** | [`rhythm-scene-templates.md`](codex-skill/video-autopilot/references/rhythm-scene-templates.md)、[`editorial-hybrid-motion.md`](codex-skill/video-autopilot/references/editorial-hybrid-motion.md) | `rhythm_templates.py check`：逐幀覆蓋、閱讀時間、已認證項目 | Editkin Motion Library 模組 + v4 run |
| **線上訪談** | [`interview-show-playbook.md`](knowledge/interview-show-playbook.md) | [`interview_gate`](src/interview_gate.py)（**沒來源的來賓數據不上鏡**）＋ `plan_gate` | [`interview_autopilot.py`](src/interview_autopilot.py) `invite` → `plan` 產 7 件套；剪輯走 v4 run |

- **閘門共用外殼** [`src/longform_maker/gate_core.py`](src/longform_maker/gate_core.py)：回傳結構、`assert` 訊息、self-test 印法一致；
  你自己加的閘門 import 三個函式就跟內建的行為一樣（判定規則各自留在自己的檔）。
- **經營層**：`src/channel_tracker.py` D2/D7/D28 快照排程＋待辦、`src/system_health.py` 一鍵 GREEN/RED 健檢
  → [`knowledge/ops-automation.md`](knowledge/ops-automation.md)；爆款定義框架 → [`knowledge/viral-playbook-framework.md`](knowledge/viral-playbook-framework.md)。
- ⚠️ 閘門裡的**門檻數字都是範例校準值，不是宇宙常數** —— 請用**你自己**的 3-5 支片重算（做法見 [SETUP.md](SETUP.md)「Shorts 規則校準」）。

## 📦 內容一覽

| 層 | 模組 | 做什麼 |
|---|---|---|
| **Editkin v4 controller** | `src/workflow_contract.py` + `workflow_contract.json` + `workflow_state.py`／receipts | source-byte 綁定、逐素材證據、plan v4、audit、原子 apply、render、審片與成效的可續跑 DAG |
| **節奏場景規劃** | `src/rhythm_templates.py` | story + Motion Library catalog → 逐幀精確場景計畫；`plan` / `check` |
| **Context router** | `src/context_router.py` | 每個工作只組一個小而穩定的 context packet，按需求導到對應參考文件 |
| **品質閘門** | `src/longform_maker/`：`gate_core`、`plan_gate`、`pace_gate`、`script_gate*`、`shorts_gate*`、`editkin_voiceover_gate`、`music_engine` | 包裝先行、腳本、節奏、Shorts 結構與字幕、旁白覆蓋、BGM beat 分析 |
| **字幕品質** | `src/longform_maker/`：`word_captions`、`caption_grouping`、`caption_timeline` | 依字級時間戳斷句與分組，用於字幕品質掃描 |
| **交付 QA** | `src/media_delivery_qa.py` + `src/delivery_media_ops.py` | 頻閃、死空檔、字幕同步、全幀掃描、音訊／A-V、斷句、BGM 覆蓋 |
| **審片與發布** | `src/review_loop.py`、`src/publish_hub.py`、`src/outcome_learning.py`、`src/channel_tracker.py` | 審片伺服器、唯一發布包、成效學習、D2/D7/D28 排程 |
| **訪談企劃** | `src/interview_autopilot.py` + `src/interview_gate.py` + `templates/interview/` | 邀約、主持稿、訪綱、準備包、授權、錄製 checklist、發布包與 Shorts 切條 |
| **競品量測** | [`src/teardown.py`](src/teardown.py) | 刀速、刀距分布、換句÷剪點、LUFS；OCR 選配，缺套件只降級 |
| **健檢與更新** | `src/system_health.py`、`src/release_manager.py`、`install_or_upgrade.py` | 一鍵健檢；雜湊驗證的安裝、升級與回滾 |
| **知識與合規** | `knowledge/` | 避坑原則、剪輯 craft、演算法、AI 內容合規與來源分級；索引 → [`knowledge/README.md`](knowledge/README.md) |
| **Codex Skill** | `codex-skill/video-autopilot/` | 給 AI agent 的公開 Skill 與參考文件 |
| **個人化入口** | ⭐ `SETUP.md` + `templates/` + `config.example.py` | 只填自己的 voice、品牌、素材／匯出路徑；不帶任何人的私人設定 |

套件邊界與「完整」的定義 → [`docs/OPEN_SOURCE_SUITE.md`](docs/OPEN_SOURCE_SUITE.md)。

## 🪦 已退役（v0.25.0）

這些舊機制已由 Editkin 取代，v0.25.0 起不再隨公開 kit 出貨：

- 純 FFmpeg 的 vlog／Shorts 渲染器（`src/silent_vlog_maker/`）與舊 Shorts 直出流程（`shorts_autopilot.py` 等）
- `src/longform_maker/` 的渲染半邊（動態特效、螢幕錄影清理、品牌卡、調色、轉場、素材鍛造、縮圖模板等）
- Python 合成、濾鏡、3D、模板編譯、tracked graphics、roto／keyer runtime 與舊 visual director
- 內附的 Cleanup 工具 → 改用獨立 repo [claude-skill-code-cleanup](https://github.com/Hao0321/claude-skill-code-cleanup)
- v6 架構文件、範例 01／03 與部分舊參考文件

**需要舊 FFmpeg pipeline 的人，請留在 tag [`v0.24.1`](https://github.com/Hao0321/video-autopilot-kit/tree/v0.24.1)。**
完整清單與遷移說明 → [CHANGELOG](CHANGELOG.md)。

## 🚀 快速開始

1. **先裝 Editkin、接上 AI、裝好這個 Kit**：照上方〈先裝 Editkin（必要）〉三步，細節見
   [SETUP.md 步驟 0](SETUP.md#步驟-0先裝-editkin)
2. 讀 **`SETUP.md`** → 照問題把 `templates/*.template.md` 填成 `profiles/*.md`
   （或把整個 repo 丟給 Claude / ChatGPT，說「照 SETUP.md 問我問題，幫我生成 profiles/」）
3. `cp config.example.py config.py` → 填你的專案、素材與匯出路徑
4. 裝好 Python 3.9+ 與 ffmpeg（交付 QA 用）
5. `python src/system_health.py --quick` 驗證乾淨安裝
6. `python src/workflow_contract.py create ...` 建 run，照 `next` 一步步完成收據，audit 後再 apply / render

## ♻️ 安裝、舊版升級與更新

這個 repo 把**完整可執行核心＋公開 Codex Skill＋更新／回滾系統**當作同一個產品發布。
不論你是第一次安裝，或還停在沒有 updater 的舊版，都從同一支 bootstrap 開始：

```powershell
Invoke-WebRequest https://github.com/Hao0321/video-autopilot-kit/releases/latest/download/install_or_upgrade.py -OutFile install_or_upgrade.py
python install_or_upgrade.py --install-root . --check
python install_or_upgrade.py --install-root . --apply --install-skill
```

macOS／Linux 可用：

```bash
curl -fLO https://github.com/Hao0321/video-autopilot-kit/releases/latest/download/install_or_upgrade.py
python3 install_or_upgrade.py --install-root . --check
python3 install_or_upgrade.py --install-root . --apply --install-skill
```

第一次採用舊資料夾必須明確執行 `--apply`；不能用 `--auto` 靜默接管。採用完成並建立管理檔清單後，
之後的相容版本才能以 `--auto` 套用。

**更新改為手動**：v0.24.x 的 24 小時自動檢查掛在已退役的 Shorts 入口上；v0.25.0 起沒有任何入口會自己檢查更新。
想更新時自己跑：

```bash
python install_or_upgrade.py --install-root <你的資料夾> --check
python install_or_upgrade.py --install-root <你的資料夾> --apply --install-skill   # 建議：會一併同步 Skill 與工作區結構
python src/release_manager.py auto       # 或：最多每 24 小時檢查一次，只套用相容版本
```

- 新版會比較 semver，驗證 release zip SHA-256 與逐檔 SHA-256 後才套用。
- `config.py`、`profiles/`、`projects/`、`data/`、`videos/`、`assets/`、後台成效與本機 outcome
  永遠留在你的電腦，不進公開包、不被更新器覆蓋。
- 未知自訂檔永不刪；已修改的官方管理檔在自動模式會停在 `CONFIRM_REQUIRED`。
- 新版不再出貨的官方管理檔（例如 v0.25.0 退役的模組）會先備份再移除。每次覆蓋或移除前都會建立
  `.video-autopilot/backups/<transaction>/`；需要時執行 `python src/release_manager.py rollback`。
- 透過 `install_or_upgrade.py` 安裝或升級後，會非破壞地補齊 `videos/_PUBLISH_HUB` 與根目錄發布入口；不刪除、不覆寫影片、設定或未知檔案。
- 重大／不相容版本不會靜默升級，必須由使用者確認。

完整契約見 [`open-source-release-and-upgrade.md`](codex-skill/video-autopilot/references/open-source-release-and-upgrade.md)。
開發者發布前使用 `python src/release_manager.py build --base-url <本版 GitHub release URL>`，會產生
固定 zip、`.sha256` 與 `release-channel.json`；發布時再連同根目錄的 `install_or_upgrade.py`，共上傳四件 release assets。

> 安全邊界：更新的是**相容而且驗證過的公開核心**，不是把任何人的私人影片、數據、設定或
> 授權不明素材同步給別人。完整開源與保護使用者資料必須同時成立。

## 需求

**VA（Win / Mac / Linux）**
- Python 3.9+
- `ffmpeg` / `ffprobe` 在 PATH 上（交付 QA、競品拆解會用到）
- 媒體分析依賴：`python -m pip install -r requirements-media.txt`（固定版本；CI 與正式 Release 用同一份）
- Mac/Linux：系統路徑與 CJK 字型由 `src/platform_compat.py` 自動探測（不要 hardcode 系統字型路徑）
- **不需要任何依賴就能跑的部分**：`workflow_contract.py`、`rhythm_templates.py`、範例 02／04／05。
  Shorts 閘門 `src/longform_maker/shorts_gate.py` 是純 Python —— 建議**平面 import**（把 `src/longform_maker/`
  加進 `sys.path` 再 `from shorts_gate import …`，範例 04 就是這樣寫），不經過套件 `__init__`，零依賴才確實成立。
- 訪談生產線的**訪前企劃全程純 Python** —— 產 7 件套不需要 ffmpeg 也不需要 pip 套件 → `python examples/05_interview_plan.py`
- 競品拆解 `src/teardown.py` 有**兩個選配套件**：**`rapidocr-onnxruntime`**（OCR）＋ **`opencc-python-reimplemented`**（簡轉繁）
  - **不裝會少什麼**：剪點統計（刀速／刀距分布）與 LUFS 照跑；需要 OCR 的字幕相關量測（換句速率、換句÷剪點、
    逐字稿）會跳過並印出安裝指令，**退出碼仍是 0**。
  - ⚠️ **OCR 只讀得動燒錄字幕，實景招牌幾乎讀不到，而且讀錯時信心值仍然很高 —— 門檻擋不掉。**
    所以只能拿來讀**別人**的片，**不可以**拿去自動生成你自己影片的品名／價格字幕
    → 邊界說明見 [`knowledge/vertical-teardown-method.md`](knowledge/vertical-teardown-method.md) §2-8

**Editkin**
- 一般使用者：安裝 [Editkin 公開預覽版](https://github.com/Hao0321/Editkin/releases/tag/v0.15.0-preview.20261022)
  （目前只有 Windows 10／11 64 位元；沒有數位簽章、沒有自動更新），步驟見 [SETUP.md 步驟 0](SETUP.md#步驟-0先裝-editkin)。
  在 Editkin 首頁一鍵連接 Claude Code 或 Codex，`/mcp` 看得到 `editkin` 就接好了。
- 開發者也可以照 Editkin README 從原始碼建置（[repo](https://github.com/Hao0321/Editkin)；渲染需要桌面建置，
  瀏覽器版不能輸出影片），在 agent 的 MCP 設定中以 `npm run mcp` 啟動 Editkin（細節以 Editkin README 為準）
- Editkin 的完整 Video Autopilot 流程（「複製開工指令」）要找得到本 kit 的 Skill：放在
  `%USERPROFILE%\.codex\skills\video-autopilot\`（`install_or_upgrade.py --install-skill` 會裝在這裡），
  或把 `EDITKIN_VIDEO_AUTOPILOT_SKILL` 設成 `SKILL.md` 的絕對路徑
- 你的 AI agent 要能呼叫 Editkin 的 MCP 工具，並依 `workflow_contract.json` 回傳 receipts
- 現行 plan schema：`hao.video-autopilot.edit-plan/v4`；舊 schema 一律 fail closed，不能進 audit 或 apply
- Motion Library 效果需要內含 Motion Library 的 Editkin 版本（上面的預覽版已內含）；缺模組時記錄 `NEW_MOTION_RUNTIME_REQUIRED`

*(選用)* AI 助手（Claude / ChatGPT）也能照 `SETUP.md` 自動把你的答案生成 profiles。

## 設計理念

一套創作系統最值錢的是**結構與方法論**，不是某個人的私人數字。
所以這個 repo 給你骨架，你用自己的血肉填滿。

## License

MIT — 保留標註即可自由使用 / 修改 / 商用。Editkin 是另一個專案，採 GPL-3.0，不隨本 kit 打包。

## Author

Hao0321 Studio — 從一套實戰的個人創作系統抽出來的開源框架。
