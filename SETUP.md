# SETUP — 先回答這些問題，讓這套系統變成「你的」

## 步驟 0：先裝 Editkin

VA（這個 Kit）只負責規劃和檢查；**真正剪片、渲染的是 [Editkin](https://github.com/Hao0321/Editkin)**。
沒有 Editkin，什麼都剪不出來。下面 5 小步做一次就好，做完再往下設定 Kit。

> 這是**預覽版**：可以安裝、可以試自動剪輯，但還在快速修改，一定會遇到 bug。
> 目前只有 **Windows 10／11（64 位元）**；這版**沒有數位簽章**，也**沒有自動更新**，新版本要自己回 Releases 下載。

### 0-1 下載並安裝

1. 只從 Editkin 的 GitHub Releases 頁面下載 Windows 安裝檔：
   - 這一版：[v0.15.0-preview.20261022](https://github.com/Hao0321/Editkin/releases/tag/v0.15.0-preview.20261022)
   - 所有版本：[Editkin releases](https://github.com/Hao0321/Editkin/releases)（預覽版不會標成「Latest」，請在列表裡找）
   - 安裝檔約 1.25 GB，裝好後約 2 GB。
2. 雙擊安裝檔。因為沒有數位簽章，會出現藍色的「Windows 已保護您的電腦」（SmartScreen）：
   1. 點「**其他資訊**」
   2. 再點「**仍要執行**」
3. 照安裝畫面按「下一步」，可以自己選安裝位置。
4. 電腦如果沒有 Microsoft Edge WebView2（Windows 10／11 大多已經有），安裝程式會自動下載，需要網路。

### 0-2 確認安裝檔沒被改過（建議）

release 頁面有列出安裝檔的 SHA-256。在下載資料夾開終端機，執行（`<安裝檔>` 換成實際檔名）：

```bat
certutil -hashfile <安裝檔>.exe SHA256
```

顯示的值要和 release 頁面上的 SHA-256 一模一樣；**不一樣就不要執行**。
（PowerShell 也可以用 `Get-FileHash <安裝檔>.exe -Algorithm SHA256`。）

### 0-3 接上你的 AI

先準備：電腦上已安裝並登入 [Claude Code](https://claude.com/claude-code) 或 Codex CLI。不用 API key，用的是你自己的 AI 訂閱。

1. 打開 Editkin，首頁「**AI 協助剪輯**」區塊按「**連接 AI 助手**」。
2. 選「**連接 Claude Code**」或「**連接 Codex**」（一鍵設定）。
3. 選一個「**要授權給 AI 的工作資料夾**」，把要剪的影片放進這個資料夾。AI 只能讀寫這個資料夾裡的東西。
4. 看到「已設定最新版 MCP」後，**重新開啟** Claude Code／Codex（或開新的 session）。
5. 輸入 `/mcp`，清單裡要看得到 `editkin`。

一鍵設定沒成功時：照視窗上的步驟，打開終端機貼上 Editkin 已複製好的設定指令，再重新開啟 AI。

### 0-4 安裝這個 Kit

Editkin 的「**複製開工指令**」會啟動完整的 Video Autopilot 流程（看畫面、讀逐字稿、規劃、審核、套用、輸出），
這個流程要找得到本 Kit 的 Skill，位置是下面兩個之一：

- `%USERPROFILE%\.codex\skills\video-autopilot\`（預設）
- 或設定環境變數 `EDITKIN_VIDEO_AUTOPILOT_SKILL`，指到 Skill 的 `SKILL.md`

Kit 的安裝程式會幫你裝到預設位置。先 `--check` 看一次，再 `--apply --install-skill`：

```powershell
Invoke-WebRequest https://github.com/Hao0321/video-autopilot-kit/releases/latest/download/install_or_upgrade.py -OutFile install_or_upgrade.py
python install_or_upgrade.py --install-root <Kit 要放的資料夾> --check
python install_or_upgrade.py --install-root <Kit 要放的資料夾> --apply --install-skill
```

- `--install-skill` 會把 Skill 同步到 `%USERPROFILE%\.codex\skills\video-autopilot\`。
- 那裡如果已經有一份**不是這個安裝程式管理**的 Skill，結果會顯示 `ADOPT_REQUIRED` 並停下，不會覆蓋；
  確認可以接管後，再加 `--adopt-skill` 重跑。
- Editkin 找不到 Kit 時，會直接顯示訊息，寫出缺的是哪個 Kit，並附上這個 repo 的連結。
- 沒裝 Kit 時，直接請 AI「用 Editkin 把工作資料夾裡的某支影片剪掉停頓、加字幕和背景音樂」這種指定剪法一樣可以用。

### 0-5 確認全部接好了

擇一試試看：

- **簡單模式（不需要任何 AI 帳號）**：打開 Editkin，首頁「放影片進來，我幫你剪好」→ 選「**橫的影片**」→
  「**選擇影片**」挑一支你自己拍、有人講話的橫式影片（建議 1～10 分鐘）→ 選類型 →「**開始自動剪輯**」。
  看到「剪好了，你看看」就代表 Editkin 本身正常。第一次加字幕會先下載約 190 MB 的語音辨識模型（需要網路，只下載一次）。
- **AI 連線**：請你的 AI「列出 Editkin 的模組」。它會呼叫 `list_editkin_modules`；拿得到模組清單，就代表
  AI 和 Editkin 接好了。清單裡如果有 `graphic.text_motion`、`transition.motion_pair`、`background.motion_loop`，
  Motion Library（160 種效果）也可以用。

**直式 Shorts**：這版 Kit 接受 Editkin 預設的 `kinetic` 節奏，搭配這個 Editkin 預覽版，直式 Shorts 可以從頭跑到尾。

---

## v0.25.0 快速啟動

```bash
python src/system_health.py --quick
python src/release_manager.py install-skill
python src/workflow_contract.py selftest
```

v0.25.0 起，**VA（本 kit）只負責規劃、判斷與檢查；所有渲染都交給 [Editkin](https://github.com/Hao0321/Editkin)**
（另行安裝，見上方〈步驟 0〉；GPL-3.0）。舊的 Python／FFmpeg 渲染器與可選的視覺素材包都不再需要。
`profiles/`、`data/`、`assets/`、`videos/` 都受更新器保護。

公開版不預設任何人的審片身分。要讓人工審核命令可解析主觀佇列，請明確設定允許的 actor；
未設定時會 fail closed，不會讓自動化代簽：

```powershell
$env:VIDEO_AUTOPILOT_REVIEW_ACTORS='creator'
```

```bash
export VIDEO_AUTOPILOT_REVIEW_ACTORS='creator'
```

多個 actor 以逗號分隔；命令傳入的 `--actor` 必須與其中一個值相符（忽略大小寫與前後空白）。

> **這個 repo 不是要你直接套用某個人的設定，而是一個「框架 + 問卷」。**
> 它把一套實戰過的 YouTube / 短影音自動化系統抽成模板 —— 你回答下面的問題，
> 就生成**屬於你自己**的 voice / 品牌 / 策略 / 社群檔。
> 程式碼是通用的；**個人化 100% 來自你的答案，沒有任何原作者的私人數據**。

---

## 🧭 平台需求（先看這個再往下）

這個 kit 只有一條現行剪輯執行路徑：**Editkin v4 structured workflow**。VA 負責素材證據、
`edit-plan/v4`、各種閘門與交付 QA；audit、原子套用與 render 都由 Editkin 依同一份合約執行，
沒有第二套 editor runtime。架構一頁版 → [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。

- **VA（Win / Mac / Linux）**：Python 3.9+、`ffmpeg`/`ffprobe`（交付 QA 與競品拆解會用到），
  並在專案根目錄執行 `python -m pip install -r requirements-media.txt`。這份固定版本契約也是 CI 與 Release 用的同一份。

  **安裝 ffmpeg（一次搞定，三平台都有）**：
  | 平台 | 指令 |
  |---|---|
  | macOS | `brew install ffmpeg`（需 [Homebrew](https://brew.sh)；裝完 `ffmpeg -version` 驗證）|
  | Windows | `winget install ffmpeg` 或到 [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) 下載 full build 加入 PATH |
  | Linux | `sudo apt install ffmpeg fonts-noto-cjk`（Debian/Ubuntu；同時提供自測與中文輸出需要的系統字型）|

  > Mac/Linux 的系統路徑與 CJK 字型由 `src/platform_compat.py` 自動探測；極簡 Linux 映像仍須先安裝一套 CJK 系統字型。
- **Editkin（必要）**：照上方〈步驟 0〉安裝公開預覽版（目前只有 Windows）、一鍵接上 Claude Code 或 Codex。
  開發者也可以照 Editkin README 從原始碼建置（[repo](https://github.com/Hao0321/Editkin)；渲染需要桌面建置），
  在 AI agent（任何支援 MCP 的 agent）的 MCP 設定中以 `npm run mcp` 啟動 Editkin，並把
  `EDITKIN_VIDEO_AUTOPILOT_SKILL` 設成 Skill 的 `SKILL.md` 絕對路徑。
  agent 呼叫 Editkin 的 MCP 工具後依 `workflow_contract.json` 回傳 receipts。連線或 apply 狀態不明時會 fail-closed 進 reconcile。
- **Motion Library（選用）**：節奏場景與品牌 Motion 需要內含 Motion Library 的 Editkin 版本；
  [Editkin 公開預覽版](https://github.com/Hao0321/Editkin/releases/tag/v0.15.0-preview.20261022)已內含。
  缺模組時 VA 記錄 `NEW_MOTION_RUNTIME_REQUIRED`，不會默默退回舊效果。
- **舊 FFmpeg 渲染器**：v0.25.0 已退役。真的需要時請留在 tag `v0.24.1`。

---

## ⚡ 最快上手（不用一次填完！）

> **覺得問卷很長？不用全部填完才能開始。** 下面 8 區只有 **3 區是 ★必答**，其餘**邊做邊補**就好
> —— 7️⃣8️⃣ 更是「開了那條生產線才需要」，沒做訪談 / 沒做 Shorts 就整區跳過。

**推薦做法 —— 讓 AI 訪談你（最省力）：**
把整個 repo 丟給 Claude / ChatGPT，貼這句：
> 「照 `SETUP.md` 的 **★必答 3 區先問我**（品牌、Niche、製作設定），用我的答案生成 `profiles/`。其餘選填區之後再問。」

AI 會一題一題問、自動幫你填，你**只要用講的回答**，不用自己動手寫檔案。

**5 分鐘最小啟動（只回答這 3 題就能開跑）：**
1. 你的頻道叫什麼？**你會露臉嗎？**（決定開頭/結尾要不要排露臉 cue）
2. 你做什麼類型、主打哪個平台？（教學/vlog…、YT長片/Shorts/Reels）
3. 你的 Editkin 專案、素材與匯出路徑在哪？成品要長片、Shorts 還是 Reels？

→ 填完這 3 題就能開始剪。Voice / 演算法 / 社群（4️⃣5️⃣6️⃣）**之後想優化再補**。

**手動做法（3 步）：**
1. 把 `templates/` 複製成 `profiles/`，照此對照命名（不是單純去 `.template`）：
   `brand_profile`→`brand.md`、`voice_profile`→`voice.md`、`algorithm_context`→`algorithm.md`、
   `community_mobilization`→`community.md`、`content_pipeline`→`content_pipeline.md`、`your_context`→`your_context.md`
2. 先填 **★必答** 區（1️⃣2️⃣4️⃣），其餘留白
3. 複製 `config.example.py` → `config.py`，填你自己的路徑

---

## 1️⃣ 品牌 / 頻道 → 生成 `profiles/brand.md`　★必答
- 你的頻道名稱 + handle？
- 網站 / 主要連結？
- **招牌結尾怎麼收？**（口播 / 字卡 / 露臉？）這會變成你每支片的 signature outro
- ⚠️ **你會錄 talking-head / 露臉嗎？**（很重要 —— 不露臉的話，開頭/結尾規劃要改用 b-roll + 字卡，不能排「自拍 cue」）
- 品牌色 / 偏好字體？訂閱 CTA 怎麼放？

## 2️⃣ 內容類型 / Niche → 決定 pipeline 路由　★必答
- 你做什麼類型？（教學 / vlog / 開箱 / 評論 / 遊戲 …）
- 主戰場？（YT 長片 / Shorts / Reels / TikTok）
- 語言？（中 / 英 / 雙語）

## 3️⃣ 你的聲音 / Voice → 生成 `profiles/voice.md`　⭕選填（之後優化腳本再補）
- **貼 5–10 篇你「自己寫過」的腳本 / 貼文** —— 系統學的是**你的**語氣，不是套別人的
- 你的開場習慣？口頭禪？收尾方式？
- **絕對不要的詞 / 語氣？**（anti-patterns —— 例如不講髒話、不裝熟、不用某些網路用語）

> 想更進一步（把「不像你」「觀眾聽不懂」變成**機械擋得下來**的東西）：
> 用累積版 `templates/style_profile.template.md`，它的 §5 會產出
> `audience_vocab.json`（骨架：`templates/audience_vocab.example.json`），
> 給 `src/longform_maker/script_gate.py` 在錄音前擋稿。**這四層詞表隨 kit 出貨是空的**
> —— 只能從你自己的逐字稿審計出來，抄別人的等於用別人的觀眾檢查你的稿。
> 方法論 → `knowledge/script-retention-craft.md`。

## 4️⃣ 製作設定 / Production → 生成 `config.py`　★必答
- Editkin project 檔放哪裡？來源素材、candidate export、QA evidence 各放哪裡？
- Editkin 裝好了嗎（還沒的話見上方〈步驟 0〉）？你的 AI agent 能否呼叫 Editkin 的 MCP 工具，並依 `workflow_contract.json` 回傳 structured receipts？
- 每份素材都要以 `CLIP_ID=SOURCE_FILE` 綁真實 bytes；run 一律放專案內
  `videos/_AUTOPILOT/editkin-v4/`，不得在磁碟根目錄另建資料夾。
- `ffmpeg`／`ffprobe` 是否在 PATH？這是成品 QA 與競品量測需求，不是另一套 editor path。
- 你的**字體檔**放哪？**BGM** 放哪？**b-roll 庫存**放哪？
- （這些會填進 `config.py`，取代範例路徑 —— 範例**不含任何人的帳號名**）

## 5️⃣ 演算法現況 / Algorithm → 填進 `profiles/algorithm.md`　⭕選填（發片要衝數據再補）
- 你頻道現在的數字？（訂閱 / 平均觀看 / CTR / 平均觀看時長 AVD）
- 主要 traffic source？（Browse / Suggested / Search / External …）
- 最大痛點？（觸及掉 / 留存差 / CTR 低 …）
- （框架給你「**該看哪些指標、怎麼補**」的 checklist；**數字填你自己的**）

## 6️⃣ 社群 / 外部流量 / Community → 填進 `profiles/community.md`　⭕選填（要做社群動員再補）
- 你有哪些社群？各多少人？（聊天社群 / 訊息群組 / 電子報 / 社群平台 …）
- 發片時能動員的管道有哪些？
- （給你「外部流量動員 SOP」的**結構**；你的社群、你的數字）

## 7️⃣ 訪談節目 → 生成 `profiles/show.md`　⭕選填（**只有要開訪談生產線才填**）

沒有要做訪談就整區跳過，其他功能不受影響。要做的話，`src/interview_autopilot.py` 產出的
**每一份**檔案（邀約訊息 / 主持台本 / 授權書 / 發布套件…）都會引用這五個答案 ——
沒填不會壞掉，但產出檔裡會留下 `{你的…}` 佔位字樣，交出去前記得掃一遍。

1. **節目名叫什麼？** → 會出現在授權書標題、邀約訊息、開場卡
2. **主持人怎麼稱呼？**（本名或慣用稱呼）→ 授權書的製作者主體、陌生邀約的自我介紹
3. **觀眾的落點連結是哪一個？**（社群 / 電子報 / 官網 擇一為主）→ 說明欄與置頂留言會放
4. **用什麼工具錄？** → 條件是**能分軌本機錄、原檔上傳**；連備援鏈一起寫下來
   （主工具 → 視訊會議＋本機錄 → 最後才雲端混音軌）。這題填進
   `templates/interview/format_bible.template.md` 的〈三、線上錄製規格〉
5. **片尾招牌句逐字稿？** → 主持台本最後一段照著唸，**全系列每集一字不差＝節目識別**

> 前 4 題裡的 1/2/3/5 填進 `profiles/show.md`（模板：`templates/show_profile.template.md`），
> 另外還有兩個欄位順手填掉：`CLUSTER`（訪談是**同一條線換格式，不是換線** —— 填你既有的主題
> 關鍵字，不要填「訪談」）與 `PLATFORMS`（你實際會發布/轉載的平台清單 —— **授權書會逐字引用，
> 寫少了等於沒授權**）。
>
> ⚠️ **合規章只能由人蓋**：`plan` 預設把合規欄位寫成「待複核」並被閘門擋下；你自己跑過平台的
> AI 內容政策 checklist 之後，才用 `--compliance-ok` 人工簽章。方法論見
> [`knowledge/interview-show-playbook.md`](knowledge/interview-show-playbook.md)。

## 8️⃣ Shorts 規則校準 → 選擇 `shorts_gate` 平台與檢查門檻　⭕選填（**要做直式 Shorts 才需要**）

`src/longform_maker/shorts_gate.py` 的現行 API 是 `gate_shorts(spec)` 與
`assert_shorts(spec)`，都只收一個參數。片長規則來自 `PLATFORM_RULES`，其他門檻由模組常數
建立 `_GATE_POLICY`；這些是**範例校準值，不是宇宙常數**。用自己的片驗證適用性：

| 量什麼 | 對應門檻 | 怎麼問自己 |
|---|---|---|
| **片長帶** | `dur_min` / `dur_max` | 你表現最好的 3-5 支各多長？取區間。預設把「梗／單一驚奇」收在 13-25 秒 |
| **死區** | `PLATFORM_RULES[platform]["deadzone"]` | 有沒有一段長度是**兩頭不沾**的？YT 預設把 26-44 秒設成死區；IG/FB 是 `None` |
| **首刀** | `FIRST_CUT_MAX` | 開場多久內一定要有第一次畫面變化？量你最好那幾支的實際秒數 |
| **非白字上限** | `NONWHITE_MAX_RATIO` / `NONWHITE_MAX_COLORS` | 你的字幕**白字為底**、重點色只是點綴嗎？量非白字比例與顏色數 |

**校準法（兩步，缺一不可）**：
1. 拿表現**最好**的 3-5 支量出區間 → 設成門檻
2. 拿表現**最差**的 3 支跑一次 → **確認它們會被擋下**。只做第 1 步的門檻是裝飾品

**先選實際發布平台**：YT 的死區不套用到 IG/FB。

```python
from shorts_gate import PLATFORM_RULES, gate_shorts, assert_shorts

spec["platform"] = "ig_reels"             # yt_shorts（預設）/ ig_reels / fb_reels
duration_rules = PLATFORM_RULES[spec["platform"]]
ok, rep = gate_shorts(spec)              # 檢查；rep["fails"] 非空就是 BLOCK
ready = assert_shorts(spec)              # 寫進 plan 前呼叫；BLOCK 時 raise AssertionError
```

不寫 `platform` 就是 `yt_shorts`；未知平台會 BLOCK。現行 API 沒有 `DEFAULT_RULES`、
第二個 rules 參數或 `rules=` 覆寫。自訂校準需在受版本控制的來源修改 `PLATFORM_RULES`／
模組常數，並重新載入模組來重建 `_GATE_POLICY`，再跑成功與失敗對照；匯入後只改常數不會
更新已建立的 policy。不要把其他平台當成繞過 YT 規則的開關。

**下游 QA 的輸入契約**：`spec` 必須是 dict；`place`、`what` 與通常必填的 `addr`
是非空字串（明確指定 `persistent_label_policy="omit"` 時可省略 `addr`）。
`segs` 是非空 list/tuple，每列為 `(source, in_sec, duration)`：來源是字串／PathLike，
時間必須為有限數值，起點 ≥ 0、長度 > 0；bool 不算數值。`caps_by_seg` 是 list/tuple，
每列為 `(seg_idx, [(text, color), ...], kind)`，索引是存在的非負整數，文字／顏色／模式
都是字串。可選 evidence／battle／tracking 欄位也須符合結構，證據文字不能以 null／bool 代替。
缺少 `segs` 或 `caps_by_seg`、錯誤型別、非法索引與塞不下的字幕回傳
`(False, {"ok": False, "fails": [...], "warns": [...]})`，不會進入可用字幕展開結果。
`assert_shorts` 仍以 `AssertionError` 拒絕；它不是回傳報告的 API。S-O 警告仍不阻擋。

想先看閘門長怎樣：`python examples/04_shorts_gate.py`（純 Python，不用 ffmpeg、不用素材）。
背後的知識層 → [`knowledge/shorts-mastery-2026.md`](knowledge/shorts-mastery-2026.md)；
想自己量競品的節奏 → [`knowledge/vertical-teardown-method.md`](knowledge/vertical-teardown-method.md)
（`python src/teardown.py <影片檔>`）。

---

## 📦 你會得到什麼

| 填完 | 你就有 |
|---|---|
| 1️⃣ 品牌 | 你的 outro signature + 露臉/不露臉規劃規則 |
| 2️⃣ Niche | 自動 pipeline 路由 |
| 3️⃣ Voice | **你的**語氣 profile（腳本/文案套你的調）|
| 4️⃣ Production | `config.py`（你的路徑/字體/BGM）|
| 5️⃣ Algorithm | 演算法 checklist（填你的數字）|
| 6️⃣ Community | 外部流量動員 SOP（套你的社群）|
| 7️⃣ Show | `profiles/show.md` —— 訪談生產線 7 件套自動帶入你的節目識別 |
| 8️⃣ Shorts 校準 | 一份**你自己的**閘門門檻（擋得住你的爛剪法，放得過你的好剪法）|

→ 然後用 `python src/workflow_contract.py create ...` 建 run，editable timeline 一律交給 Editkin v4：
contract → session → material evidence → plan v4 → audit → atomic apply → render → 交付 QA → 真人審片。

---

## ❓ 為什麼是「問卷」不是「現成設定」？

因為一套創作系統最值錢的是**結構與方法論**，不是某個人的私人數字。
直接抄別人的 voice / 策略 / 社群數據，對你沒用，還可能誤導。
所以這個 repo 給你**骨架**，你用自己的血肉填滿 —— 這樣它才真的是**你的**系統。
