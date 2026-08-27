# 🎬 video-autopilot-kit

> Current version: v0.23.0
>
> **v0.23.0／架構 7.0**：長片／Shorts／Reels 共用自研 composition runtime、Imagegen-first 材質閘門、證據式電影工藝、統一濾鏡庫與唯一發布中樞；
> 38 組調色／動態／轉場／主體濾鏡、33 圖設計 DNA、Tracking、Quality-95 審片、發佈包、成效學習與安全自動更新都在同一套公開版。沒有鏡頭證據時仍會退回乾淨切鏡。
> 執行 `python src/system_health.py --quick` 可驗證乾淨安裝；個人媒體與成效資料不會進 release。

> 一套**框架式**的 YouTube / 短影音自動化工具 + 方法論模板。
> 給你 Editkin `edit-plan/v4` 可續跑剪輯流程、可重現的素材／QA 工具，加上一份「問卷」——
> 你回答關於**你自己頻道**的問題，它就變成屬於你的系統。
>
> ⚠️ **不含任何人的私人數據** —— 後台讀數（自己的與別人的）／個人檔案一律不進 repo（`profiles/`、`config.py` 是 gitignored 本機檔）。
> 兩類具名例外，兩類都是**公開資訊**不是私人數據：① LICENSE 與各 README 的作者署名；
> ② `knowledge/` 引用**第三方公開創作者／頻道**時會直接寫名字（例如演算法檔引用的公開戰術、
> `teaching-niche-playbook.md` 的參考頻道列），規矩是 **citation-first：沒有可點的出處連結就不給數字**。
> voice 詞表、KPI 門檻與社群欄位要嘛是**空白模板**（`<fill in>` / `______` / 產出檔的 `{你的…}` 佔位字樣），要嘛**標示為「範例值」**，你填你的。
> 反過來說：`knowledge/` 裡的方法論**是**原作者的實戰結論，那是刻意開源的部分 —— 是「怎麼想」，不是「他的數字」。

## 🧭 現行剪輯執行方式

- **唯一 editor contract**：Editkin v4（素材證據 → plan → audit → atomic apply → render）。
- Python／ffmpeg 是跨平台的素材分析、正規化與 QA 支援層，不是另一套 editor path。
- 舊 GUI／草稿 JSON／Path A-E 文件只保留為 benchmark-only 歷史，不是 fallback。

## ▶️ 60 秒看它跑（不用真素材）

想先看它**真的會動**？`examples/` 裡有自包含、可直接跑的 demo —— 用 ffmpeg 合成測試素材，或以 disposable fixture 驗證 Editkin v4 contract，不需要任何真實影片：

```bash
python examples/01_vertical_short.py      # 合成素材 → 完整 1080x1920 直式 Short
python examples/02_caption_broll_match.py # Editkin v4 contract：完整 DAG + fail-closed 回歸測試
python examples/04_shorts_gate.py         # 直式 Shorts 閘門：壞剪法被擋 → 修好放行 → 換你的門檻放行 → 換平台也放行
python examples/05_interview_plan.py      # 訪談來賓閘門：沒來源的數據在「錄影之前」就被擋下
python examples/06_teardown.py            # 競品拆解數學：中位數騙人、標準差不騙人、換句÷剪點是拍攝決策
```

需求：Python 3.9+。**04 / 05 / 06 連 ffmpeg 都不用**（純 Python、零 `pip install`、零素材）；01 需要
`ffmpeg`/`ffprobe`，03 另需 Pillow + numpy。細節見 [`examples/README.md`](examples/README.md)。

## 🎛️ 統一濾鏡庫

同一套 registry 同時供長片、Shorts 與 Reels 使用；不是把 LUT、全螢幕
模板和轉場混成一類。調色只能套一次且必須先於字幕／圖卡，轉場必須有
剪輯動機或證據，主體濾鏡必須提供已驗證遮罩。

```bash
python src/filter_runtime.py list
python src/filter_runtime.py inspect torn_paper_vertical
python src/filter_runtime.py apply input.mp4 output.mp4 --preset vlog_bright_clean
python src/filter_runtime.py transition a.mp4 b.mp4 out.mp4 \
  --preset torn_paper_vertical --motivation "章節翻頁" --manual-approved
python src/filter_runtime.py gallery a.mp4 review/filter-library --source-b b.mp4
```

完整分類、合成契約與 QA 規則見
[`filter-library.md`](codex-skill/video-autopilot/references/filter-library.md)。

## 為什麼不一樣

市面上的「creator 系統」要嘛賣你**某個人的設定**（抄了對你沒用、還可能誤導），
要嘛太通用沒有方法論。這個 kit 給你**骨架**（經實戰的結構），
`SETUP.md` 一區一區**問你問題**，用你的答案填滿它 —— 這樣它才真的是**你的**系統。

## 🆕 v0.12.0 新增 — 把「借來的數字」清出去

這一版**沒有拿掉任何功能，拿掉的是借來的把握**。四個地方犯的是同一種錯：
一個沒人量過的數字，掛上權威標籤，比沒有數字更糟 —— 因為你會信它。

- **Shorts 片長帶改平台感知** —— 死區是在 **YT Shorts** 上量出來的，套到 IG/FB 會擋掉正常的剪法。
  改用 `spec["platform"]` 選帶（`rules=` 仍逐鍵優先）；平台名打錯是**擋下的失敗**，不是靜默 fallback
- **腳本 gate 的四層詞表改成出貨即空** —— 行話分級只能從**你自己的逐字稿**審計出來；
  照抄別人的白名單 = 用別人的觀眾檢查你的稿。空表不擋你（只回一條 warn），`load_vocab()` 載你自己的
- **演算法線補上合規層＋「沒出處就不引用」** —— [`knowledge/ai-content-compliance.md`](knowledge/ai-content-compliance.md)（R26-R38 ＋ 發布前 10 項 checklist）
  ＋ 53 條分級法源；查無官方出處的門檻數字就地標記，不再與有出處的並排
- **新工具 [`src/teardown.py`](src/teardown.py)** —— 一個指令把競品直式短片拆成可比較的數字（刀速／刀距分布／換句速率／換句÷剪點／LUFS）；
  OCR 是**選配**，沒裝只跳過字幕抽取、退出碼仍是 0

完整清單（含兩個靜默失敗修復）→ [CHANGELOG](CHANGELOG.md)。

## 三條**同構**的生產線（v0.10 起）

以前這個 kit 只回答一件事：「怎麼把**一支長片**做好。」現在是三條生產線 ——
而且刻意長成**同一個形狀**：**知識層（為什麼這樣做）→ 機械閘門（不靠任何人記得）→ 一鍵驅動（幾個指令跑完）**。
學會一條就等於學會三條；要加第四條（Podcast？教程系列？）也照這個骨架接。

| 生產線 | 知識層（為什麼） | 機械閘門（擋在前面） | 一鍵驅動 |
|---|---|---|---|
| **教學長片** | `knowledge/premium-motion-fx.md`＋[`production-safety-principles.md`](knowledge/production-safety-principles.md)＋腳本三支柱 [`script-style-framework.md`](knowledge/script-style-framework.md)／[`script-retention-craft.md`](knowledge/script-retention-craft.md) | `plan_gate` → [`script_gate`](src/longform_maker/script_gate.py)（觀眾語言 fail／節奏 warn）→ `delivery_qa(profile='teaching_longform')` | `src/longform_maker/` 各模組 |
| **直式 Shorts** | [`knowledge/shorts-mastery-2026.md`](knowledge/shorts-mastery-2026.md)＋[`knowledge/vertical-teardown-method.md`](knowledge/vertical-teardown-method.md)（怎麼量競品） | [`src/longform_maker/shorts_gate.py`](src/longform_maker/shorts_gate.py)　九條結構／字幕規則擋出片 ＋ S-O 換句節奏 warn；**片長帶平台感知**（YT 的死區不套用到 IG/FB），**純 Python** | [`src/shorts_autopilot.py`](src/shorts_autopilot.py)　`scan` → 看畫面填字 → `build`（含自動 QA 驗證圖） |
| **線上訪談** | [`knowledge/interview-show-playbook.md`](knowledge/interview-show-playbook.md) | [`src/interview_gate.py`](src/interview_gate.py)　I-A~I-E：**沒來源的來賓數據不上鏡** | [`src/interview_autopilot.py`](src/interview_autopilot.py)　`invite` → `plan`（產 7 件套）→ `build` |

- **閘門共用外殼** [`src/longform_maker/gate_core.py`](src/longform_maker/gate_core.py) —— 回傳結構 / `assert` 訊息 / self-test 印法一致，
  你自己加的閘門 import 三個函式就跟內建的行為一模一樣（**判定規則各自留在自己的檔**，不集中才不會互相污染）
- **經營層**（v0.9 起）：`src/channel_tracker.py` D2/D7/D28 快照排程＋待辦、`src/system_health.py` 一鍵 GREEN/RED 健檢
  → 接線指南 [`knowledge/ops-automation.md`](knowledge/ops-automation.md)；爆款定義框架 [`knowledge/viral-playbook-framework.md`](knowledge/viral-playbook-framework.md)
- ⚠️ 兩道閘門裡的**門檻數字都是範例校準值，不是宇宙常數** —— Shorts 片長帶 / 首刀秒數 / 非白字上限請用**你自己**的 3-5 支片重算
  （做法見 [SETUP.md](SETUP.md) 的「Shorts 規則校準」）

## 內容 —— 單一 Editkin-first 執行路徑

三條生產線（長片 / Shorts / 訪談）共用同一個 Editkin v4 執行合約。公開 Python／ffmpeg
模組負責規劃、素材處理與 QA；它們不構成第二套 editor runtime。

| 層 | 模組 | 是什麼 | 平台 |
|---|---|---|---|
| **Editkin durable controller** | `src/workflow_contract.py` + `workflow_state.py` + receipts | source-byte binding、逐素材 evidence、`edit-plan/v4`、audit、atomic apply、render、真人審片與 outcome 的可續跑 DAG | Editkin 支援環境 |
| **長片規劃／素材支援** | `src/longform_maker/` | premium motion、word-timestamp captions、screen cleanup、腳本與節奏 gates；輸出提供 Editkin plan 使用 | Win / Mac / Linux |
| **Shorts / vlog 支援** | `src/shorts_autopilot.py` + `src/silent_vlog_maker/` | 9:16 掃描、接觸表、素材正規化、Shorts gate、BGM／字幕支援 | Win / Mac / Linux |
| **訪談企劃** | `src/interview_autopilot.py` + `src/interview_gate.py` + `templates/interview/` | 邀約、主持稿、訪綱、準備包、授權、錄製 checklist、發布包與 Shorts 切條；無來源數據在錄製前阻擋 | Win / Mac / Linux |
| **腳本／競品量測** | `src/longform_maker/script_gate.py` + [`src/teardown.py`](src/teardown.py) | 觀眾語言／留存擋稿，以及刀速、刀距分布、換句÷剪點、LUFS；OCR 選配、缺套件只降級 | Win / Mac / Linux |
| **Editor-neutral QA** | `src/media_delivery_qa.py` + `src/delivery_media_ops.py` | 頻閃、死空檔、caption-sync、全幀掃描、audio/A-V、字幕斷句、BGM coverage、blurred-fill 圖片準備 | Win / Mac / Linux |
| **知識與合規** | `knowledge/` | M-series 避坑、剪輯 craft、演算法、AI 內容合規與來源分級；索引 → [`knowledge/README.md`](knowledge/README.md) | — |
| **自包含示例** | ▶️ `examples/` | 合成素材 demo + Editkin v4 contract self-test，不需真素材 | — |
| **個人化入口** | ⭐ `SETUP.md` + `templates/` + `config.example.py` | 只填自己的 voice、品牌、素材／匯出路徑；不帶任何人的私人設定 | — |

> 舊 editor GUI、草稿 JSON、Path A-E 與維護者事故紀錄不進公開執行面；公開版只提供
> [`production-safety-principles.md`](knowledge/production-safety-principles.md) 的通用安全原則。

### Platform support

| 模組 | Windows | macOS / Linux |
|---|---|---|
| 規劃、素材處理、gates、QA | ✅ | ✅（路徑／字型由 `src/platform_compat.py` 探測） |
| Editkin structured execution | 依 Editkin release 支援矩陣 | 依 Editkin release 支援矩陣 |

## 🚀 快速開始

1. 讀 **`SETUP.md`** → 照問題把 `templates/*.template.md` 填成 `profiles/*.md`
   （或把整個 repo 丟給 Claude / ChatGPT，說「照 SETUP.md 問我問題，幫我生成 profiles/」）
2. `cp config.example.py config.py` → 填你的 Editkin project、素材、candidate、QA 與匯出路徑
3. 裝好 Python + ffmpeg；editable timeline 連上 Editkin structured tool environment
4. 用 `python scripts/hao_autopilot.py workflow ...` 建 run，依 `next` 完成 receipts，audit 後再 apply / render

## ♻️ 安裝、舊版升級與自動迭代

這個 repo 現在把**完整可執行核心＋公開 Codex Skill＋更新／回滾系統**當作同一個產品發布。
不論你是第一次安裝，或還停在沒有 updater 的舊版，都從同一支 bootstrap 開始：

舊版資料夾沒有這支程式時，只要先下載這一個公開檔（之後的相容版才可自動迭代）：

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
未來相容、帶 migration 宣告且本機管理檔未改動的版本才可自動升級。

```bash
python install_or_upgrade.py --install-root <你的資料夾> --check
python install_or_upgrade.py --install-root <你的資料夾> --apply --install-skill
```

- 新版會比較 semver，驗證 release zip SHA-256 與逐檔 SHA-256 後才套用。
- `shorts_autopilot.py` 生產入口每 24 小時最多自動檢查一次；只有相容版本能自動升級，更新後會重新啟動一次再執行。也可手動跑 `python src/release_manager.py auto`。`publish_hub.py` 保持純交付服務，避免 updater／workspace migrator 形成反向循環。
- v0.19 起，安裝／相容升級後會非破壞地補齊 `videos/_PUBLISH_HUB` 與根目錄發布入口，並把既有 `*/_out/current.mp4` 以 hardlink 註冊為發布包；不刪除、不覆寫影片、設定或未知檔案。
- `config.py`、`profiles/`、`projects/`、`data/`、`videos/`、`assets/`、後台成效與本機 outcome
  永遠留在你的電腦，不進公開包、不被更新器覆蓋。
- 未知自訂檔永不刪；已修改的官方管理檔在自動模式會停在 `CONFIRM_REQUIRED`。
- 每次覆蓋前建立 `.video-autopilot/backups/<transaction>/`；需要時執行
  `python src/release_manager.py rollback`。
- 重大／不相容版本不會靜默升級，必須由使用者確認。

完整契約見 [`codex-skill/video-autopilot/references/open-source-release-and-upgrade.md`](codex-skill/video-autopilot/references/open-source-release-and-upgrade.md)。
開發者發布前使用 `python src/release_manager.py build --base-url <本版 GitHub release URL>`，會產生
固定 zip、`.sha256` 與 `release-channel.json`；發布時再連同根目錄的
`install_or_upgrade.py`，共上傳四件 release assets。

> 安全邊界：自動迭代的是**相容而且驗證過的公開核心**，不是把任何人的私人影片、數據、設定或
> 授權不明素材同步給別人。完整開源與保護使用者資料必須同時成立。
> 套件邊界與「完整」定義見 [`docs/OPEN_SOURCE_SUITE.md`](docs/OPEN_SOURCE_SUITE.md)。

## 需求

**公開規劃／素材處理／QA（Win / Mac / Linux）**
- Python 3.9+
- `ffmpeg` / `ffprobe`（在 PATH 上）
- 完整媒體 runtime：`python -m pip install -r requirements-media.txt`（固定版本的
  **Pillow + numpy + opencv-contrib-python-headless**）
- 可重現的 Python／ffmpeg 支援層；editable timeline 一律透過 Editkin v4 contract
- Mac/Linux：系統路徑與 CJK 字型由 `src/platform_compat.py` 自動探測（不要 hardcode 系統字型路徑）
- Pillow / numpy 用於畫面分析、字卡、動態、色彩與 QA 驗證圖；OpenCV contrib
  用於 tracked graphics / roto 的 CSRT 追蹤。CI 與正式 Release 共用同一份依賴契約。
  規則閘門 `src/longform_maker/shorts_gate.py` **這個檔案本身**是純 Python（連 ffmpeg 都不用），
  只想用閘門就不必裝任何東西 → `python examples/04_shorts_gate.py`。
  ⚠️ 但**要平面 import**（把 `src/longform_maker/` 加進 `sys.path` 再 `from shorts_gate import …`，
  範例 04 就是這樣寫的）；走 `from longform_maker.shorts_gate import …` 會經過套件 `__init__`，
  那裡會載入 `fx_lib`（需要 numpy + Pillow）。或直接把 `shorts_gate.py` + `gate_core.py` 複製走。
- 訪談生產線（`src/interview_autopilot.py` / `src/interview_gate.py`）的**訪前企劃全程純 Python**
  —— 產 7 件套不需要 ffmpeg 也不需要 pip 套件；ffmpeg 只有錄完 `build` 才用得到
  → `python examples/05_interview_plan.py`
- 競品拆解 `src/teardown.py` 有**兩個選配套件**（其餘功能都不需要它們）：
  **`rapidocr-onnxruntime`**（本機實測裝完約 25MB 量級，不拉 torch/paddle）＋ **`opencc-python-reimplemented`**（簡轉繁）
  - **不裝會少什麼**：只少「把對方燒錄字幕自動抽成逐字稿」這一段。刀速／刀距分布／
    換句速率／換句÷剪點判讀／LUFS **全部照跑，退出碼仍是 0**，工具會印出安裝指令。
  - 只裝 OCR 沒裝 opencc → 逐字稿照抽，只是不做簡轉繁（會混雜簡體字）。
  - 統計那一半（`rhythm_stats` / `pace_profile`）是**純 Python**，連 ffmpeg 都不用
    → `python examples/06_teardown.py`
  - ⚠️ **OCR 只讀得動燒錄字幕（0.92-1.00），實景招牌準確率 ≈ 0，而且讀錯時信心值仍有
    0.85-0.92 —— 門檻擋不掉。** 所以它只能拿來讀**別人**的片，
    **不可以**拿去自動生成你自己影片的品名／價格字幕
    → 邊界說明見 [`knowledge/vertical-teardown-method.md`](knowledge/vertical-teardown-method.md) §2-8

**Editkin structured execution**
- Editkin 支援的 client/server 環境，能依 `workflow_contract.json` 回傳 receipts
- 現行 plan schema：`hao.video-autopilot.edit-plan/v4`；v1–v3 只可匯入／檢視
- apply 狀態不明時必 reconcile；技術 QA 之後仍須真人審片，機器不得代填 certified

*(選用)* AI 助手（Claude / ChatGPT）也能照 `SETUP.md` 自動把你的答案生成 profiles。

## 設計理念

一套創作系統最值錢的是**結構與方法論**，不是某個人的私人數字。
所以這個 repo 給你骨架，你用自己的血肉填滿。

## License

MIT — 保留標註即可自由使用 / 修改 / 商用。

## Author

Hao0321 Studio — 從一套實戰的個人創作系統抽出來的開源框架。

