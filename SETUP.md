# SETUP — 先回答這些問題，讓這套系統變成「你的」

> **這個 repo 不是要你直接套用某個人的設定，而是一個「框架 + 問卷」。**
> 它把一套實戰過的 YouTube / 短影音自動化系統抽成模板 —— 你回答下面的問題，
> 就生成**屬於你自己**的 voice / 品牌 / 策略 / 社群檔。
> 程式碼是通用的；**個人化 100% 來自你的答案，沒有任何原作者的私人數據**。

---

## 🧭 平台需求（先看這個再往下）

這個 kit 有**兩條 first-class path**，需求不同：

- **Path 1 — Programmatic（推薦採用者預設；Win / Mac / Linux）**：只要 Python 3.9+ 和 `ffmpeg`/`ffprobe`。

  **安裝 ffmpeg（一次搞定，三平台都有）**：
  | 平台 | 指令 |
  |---|---|
  | macOS | `brew install ffmpeg`（需 [Homebrew](https://brew.sh)；裝完 `ffmpeg -version` 驗證）|
  | Windows | `winget install ffmpeg` 或到 [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) 下載 full build 加入 PATH |
  | Linux | `sudo apt install ffmpeg`（Debian/Ubuntu）|

  > 常見誤會：「Mac 沒有 ffmpeg」——ffmpeg 本來就是跨平台的，Mac 裝起來反而最簡單（一行 brew）。MoviePy / editly 這類「替代方案」底層其實還是在呼叫 ffmpeg。**不需要 CapCut、不需要 Computer Use**。Mac/Linux 的系統路徑與 CJK 字型由 `src/platform_compat.py` 自動探測。
- **Path 2 — CapCut-assisted（作者本人主用；Windows-first）**：額外需要 CapCut Desktop 國際版 + AI 助手的 Computer Use。**版本敏感** —— 動草稿 JSON 前先讀 [TROUBLESHOOTING](TROUBLESHOOTING.md) 的版本相容矩陣。
- **Mac 用戶** → 直接走 Path 1（CapCut 的 GUI 自動化在 Mac 上沒有可用的等效機制）。

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
3. 你走 **Path 1（純程式，跨平台）**還是 **Path 2（CapCut，Windows-first）**？素材/匯出路徑在哪？

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
- **你走哪條 path？**（見最上面「平台需求」）
  - **Path 1 Programmatic**（推薦預設；Win/Mac/Linux）—— 純程式 pipeline，只要 Python + ffmpeg，**不需要 CapCut**
  - **Path 2 CapCut-assisted**（Windows-first）—— 要用 CapCut 的花字 / 雲端模板才選這條
- 走 Path 2 的話：**CapCut Desktop 國際版**裝了嗎？⚠️ **AI 助手有開 Computer Use 嗎？** CapCut 沒有公開 API，GUI 自動化是靠 **AI 透過 Computer Use 實際操作 CapCut 視窗**（套模板 / 匯出）——沒開就跑不了。草稿 JSON 直改**版本敏感**，先跑 `detect_draft_format()` + 讀 [TROUBLESHOOTING](TROUBLESHOOTING.md)
- 你的**字體檔**放哪？**BGM** 放哪？**b-roll 庫存**放哪？專案 / 匯出路徑？
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

## 8️⃣ Shorts 規則校準 → 覆寫 `shorts_gate` 門檻　⭕選填（**要做直式 Shorts 才需要**）

`src/longform_maker/shorts_gate.py` 的 `DEFAULT_RULES` 是**範例校準值，不是宇宙常數** ——
它們來自某一種題材（無旁白、單一驚奇型的直式短片）的實測。**別人的門檻擋不住你的爛剪法，
也可能擋掉你的好剪法。** 用你自己的片重算一次：

| 量什麼 | 對應門檻 | 怎麼問自己 |
|---|---|---|
| **片長帶** | `dur_min` / `dur_max` | 你表現最好的 3-5 支各多長？取區間。預設把「梗／單一驚奇」收在 13-25 秒 |
| **死區** | `dur_deadzone` | 有沒有一段長度是**兩頭不沾**的（太長不像梗、太短不像教學）？預設把 26-44 秒設成死區；不想設就填 `None` |
| **首刀** | `first_cut_max` | 開場多久內一定要有第一次畫面變化？量你最好那幾支的實際秒數 |
| **非白字上限** | `nonwhite_max_ratio` / `nonwhite_max_colors` | 你的字幕**白字為底**、重點色只是點綴嗎？量出你最好那幾支的非白字比例與用了幾種顏色，當作上限 |

**校準法（兩步，缺一不可）**：
1. 拿表現**最好**的 3-5 支量出區間 → 設成門檻
2. 拿表現**最差**的 3 支跑一次 → **確認它們會被擋下**。只做第 1 步的門檻是裝飾品

**覆寫不用改檔**（改了檔以後更新會衝突），傳一個 dict 進去就好，只寫要改的鍵：

```python
my_rules = {"dur_min": 26.0, "dur_max": 60.0, "dur_deadzone": None}
ok, rep = gate_shorts(spec, my_rules)     # 檢查
ready   = assert_shorts(spec, my_rules)   # build 前呼叫，不過直接 raise
```

**手寫片長覆寫之前，先看看你要的是不是「換一個平台」**（v0.11）：
出貨的死區是在 **YT Shorts** 上量的，不該套到 IG/FB，所以片長帶改由 `spec["platform"]` 決定：

```python
spec["platform"] = "ig_reels"   # yt_shorts（預設）/ ig_reels / fb_reels
```

平台只提供**三個片長鍵的預設值**，你的 `rules=` 仍然**逐鍵優先** ——
可以同時指定平台又把它的帶收窄。不寫 `platform` 就是 `yt_shorts`，行為與 v0.10 完全相同。
平台名不在 `PLATFORM_RULES` 裡＝**擋下的失敗**，不會靜默沿用預設（要新平台就自己加一列）。
一鍵驅動也吃這個：`shorts_autopilot.py scan --platform ig_reels` 會把 `platform=` 寫進
產出的 `_plan.py`，`build` 就用同一組帶判片，不會前後矛盾。

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

→ 然後用 `src/` 的工具跑**你的**流程：**Path 1** = 純程式 pipeline（`longform_maker` / `silent_vlog_maker` + QA gates，跨平台）；**Path 2** = CapCut 自動化（AI + Computer Use 操作 CapCut，Windows-first）。

---

## ❓ 為什麼是「問卷」不是「現成設定」？

因為一套創作系統最值錢的是**結構與方法論**，不是某個人的私人數字。
直接抄別人的 voice / 策略 / 社群數據，對你沒用，還可能誤導。
所以這個 repo 給你**骨架**，你用自己的血肉填滿 —— 這樣它才真的是**你的**系統。
