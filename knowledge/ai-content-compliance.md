> 來自 video-autopilot-kit 開源知識庫 · MIT 授權

# AI 內容合規 — R26-R38 + 發布前 10 項 checklist

> 用 AI 協作做內容的創作者，**最大的風險不是被演算法冷落，是被平台判定成 AI slop 而整個頻道死掉**。
> 這份檔案把「哪些做法官方明文歡迎、哪些是刑法級紅線」整理成 13 條可執行規則 + 一張發布前清單。
>
> 核心結論（先講答案）：**「真人自錄旁白 + AI 輔助製作 + 真實數據 + 原創實測」這條線落在官方明文的歡迎區。**
> 致命線只有三條：① 模板化量產（R28）② 擬真素材不揭露變成慣性（R26/R36）③ 深偽三不（R29，刑法級）。

---

## ⚠️ 有效期・法域・免責（讀規則前先看這段）

- **時點**：本檔是**截至 2026-07** 的整理。平台政策與法規都會過期 —— 你讀到的當下，官方條文可能已經改過。
  規則本身（判斷原則）比日期耐久，但**具體條文、日期、罰則數字請以官方現行頁面為準**。
- **法域**：法源附錄涵蓋 EU / 美國聯邦與州 / 台灣 / 中國四個法域，那是**舉例不是清單**。
  **各地法規不同**，你所在地可能更嚴、可能更寬、可能還沒有規定。
- **這不是法律意見。商業用途（接案、賣課、代客製作、任何有金流的內容）請找當地專業人士確認。**
- 本檔的規則寫成「創作者視角的建議動作」，不是義務判定。照做不保證合規，不照做也不必然違規。

**法源出處** → [ai-content-compliance-sources.md](ai-content-compliance-sources.md)（53 條分級引用，**查證用附錄，日常不必讀**）。
規則裡標「（法源 → §ytai-07）」時，在附錄 `grep '§ytai-07'` 直接跳該區塊。錨點是穩定 ID，不重排。

**分級語彙**（同附錄）：`[official]` 官方一手 ／ `[reported]` 媒體轉述 ／ `[speculative]` 查無官方出處（**永不進稿**）。

---

## 🗺️ 先做一次：你的管線曝險對照

規則之前先做這件事——**把你的製作管線逐項列出來，每項標 SAFE / WATCH / ACT**。
下面是一條典型「AI 協作教學頻道」管線的對照結果，當範例用；**你的管線不同，結論就不同**。

| # | 管線環節 | 判定 | 依據（→ 附錄錨點） |
|---|---|---|---|
| 1 | 旁白 = 本人真聲自錄，腳本 AI 依你的 voice profile 寫、你自己唸 | **SAFE** | AI 寫大綱／腳本／標題／縮圖逐字列為 production assistance 不必揭露；連「clone 自己的聲音」都明文豁免（§ytai-08）。真人錄音對 EU AI Act Art.50 零觸發（§law-01） |
| 2a | 全自動剪輯管線（ffmpeg / 腳本化 build）本身 | **SAFE** | 平台看「內容」不看「工具」（§ytai-14）；剪輯輔助屬 production assistance。唯一連動風險是**產出**變成模板量產（那是內容問題不是工具問題） |
| 2b | 真螢幕錄影 + 真後台截圖當證據（M107） | **SAFE** | 這正是官方要的「creator's original, authentic insights or perspective」最強證據（§ytai-02），也是與量產 slop 劃清界線的判別特徵（§ytai-04） |
| 2c | 合成動態背景 b-roll（漸層／粒子／motion graphics，**非擬真**） | **SAFE** | 「clearly unrealistic」與風格化動態圖形免揭露（§ytai-08）。**豁免前提 = 維持非擬真**；哪天改走 photorealistic 真實場景就升級為 ACT |
| 2d | 渲染重建的終端機／介面 demo（內容真實、形式為重建） | **WATCH** | 內容 1:1 真實時屬 infographic／production assistance 豁免；但必勾清單含「變造真實事件畫面」（§ytai-07）——若重建與實際執行不符、觀眾會誤認為原始錄屏，就踩線。**這是「內容真實性 gate」不是「揭露 gate」** |
| 3 | 不露臉 + 縮圖用真人反應臉照片 | **WATCH** | 真照片零揭露義務。watch 原因有二：(a) 有報導稱部分 faceless 頻道被連坐 demonetize（§ytai-06，非官方確認）；(b) 臉出現在縮圖 = 有被 deepfake 冒用的暴露面 → 該去啟用 likeness detection（§ytai-11） |
| 4 | AI 圖片只用靜態、非擬真；無 AI 語音／deepfake／克隆他人 | **SAFE** | 非擬真靜態圖不必勾（§ytai-08）；不做他人臉／聲克隆同時避開多國刑事法與平台政策（§law-07 §law-11 §law-08） |
| 5 | 社群貼文：AI 學語氣生成 → **本人逐篇確認才發**、正常頻率 | **SAFE** | 純文字貼文零標示義務（§plat-01）；Inauthentic Behavior 禁的是假帳號／協同造假／假互動（§plat-13）。**watch 條件**：升級成全自動無人審 + 高頻灌量 / 堆 hashtag / 圖文不符 → 進 spammy content 打擊面（§plat-10） |
| 6 | 頻道定位 = 原創實測教學（親自跑、真數據、開源工具） | **SAFE** | 判準是有無原創洞見（§ytai-02）；被終止的 16 頻道全是純量產 slop 農場（§ytai-03）。教學題材也不在 AI persona 敏感題清單（§ytai-05） |
| 7a | 系列化持續出片（同一套框架多集） | **WATCH** | 明文不可營利：「generic or unoriginal templates giving the impression of mass production」（§ytai-02）。**系列化與模板化只有一線之隔**，且執法是頻道級不是單片（§ytai-03） |
| 7b | 開源工具／公開教別人用同一套管線 | **SAFE** | 教學內容本身 = 原創創作；採用者產出的內容責任在採用者。唯一注意：**別傳播查無官方出處的數字**（§algo-10 §algo-11 §plat-05） |

> **怎麼用這張表**：8 SAFE / 3 WATCH / 0 ACT 是這條管線的結果，不是你的。
> 自己跑一遍，WATCH 的每一項都要寫出「什麼條件下它會升級成 ACT」——那句話就是你的預警線。

---

## 📋 R26-R38：十三條規則

> 編號延續**演算法 R 系列**：R15-R25 見 [`youtube-algorithm-2026.md`](youtube-algorithm-2026.md) §6
> （R1-R14 是早期實測條目，未收錄於本 kit —— 編號留空是為了不讓後面的 R 號整組平移）。
> ⚠️ **別跟 [`meta-lessons.md`](meta-lessons.md) 裡的 R1/R10/R11/R12 搞混** —— 那是**另一個 R 系列**
> （素材 pre-flight audit 規則），兩者不共用命名空間。
> 每條格式：**規則 → why（法源）→ 落地在哪個 gate**。

### R26 — 擬真判定 gate

任何 AI 生成素材入片前先問一句：**「觀眾會不會誤認為真實的人／地／事件？」**
- 會 → 上傳勾「Altered content」揭露 **+ 該段畫面加「AI 生成」字卡**
- 不會（漸層／粒子／motion graphics／明顯非寫實）→ 免

**why**：官方必勾清單的核心判準逐字就是「viewers could easily mistake for a real person, place, or event」（§ytai-07）；
平台已開始自動偵測補標，不勾也會被標，主動勾觀感較好（§ytai-10）。
**畫面字卡一個動作同時滿足 EU AI Act Art.50(4) 的可見標示與中國平台的搬運場景**（§law-01 §law-12）——一次做，三地受益。

**落地**：交付 QA gate 一項 + 上傳 SOP checklist 第 1 項。

### R27 — 每支片至少一項「可指出的原創貢獻」

親自實測 ／ 真後台數據（M107）／ 個人方法論講解 —— **寫得出一句話才准進製作**。

**why**：官方判定核心是「creator's original, authentic insights or perspective」，不是有沒有用 AI（§ytai-02）。
這是 inauthentic content 政策的**唯一免死金牌**（§ytai-01）。

**落地**：`src/longform_maker/script_gate.py` 前置——規劃階段就要填「本支原創貢獻」欄位，空白不放行。

### R28 — 系列化防模板化

同系列每集需有**結構差異 + 獨立實測數據**，禁同模板換皮量產。**寧可少出，不出模板片。**

**why**：明文打擊「giving the impression of mass production」（§ytai-02）；
16 頻道終止案證明執法是**頻道級**——一批低質影片拖累全頻道，不是單片 demonetize（§ytai-03）。

**落地**：規劃階段比對前集結構（`src/longform_maker/plan_gate.py` 的選題閘門旁邊加一條人工項）。

### R29 — 深偽三不（絕對紅線）

demo 永不用他人臉／聲 ・ 永不涉性相關合成 ・ 永不碰政治人物／候選人合成。
**連「示範這個工具能做到」都算製作。**

**why**：這一條不是平台政策，是**已生效的刑法**。台灣刑法 §319-4 不實性影像罪（5 年以下、營利 7 年以下）+
選罷法深偽條款（7 年以下 + 最高千萬罰金）（§law-11）；美國聯邦 TAKE IT DOWN Act 刑事條款已生效、
FTC 2026-05-19 起執法（§law-07）。**多數法域都有對應條文，請查你自己所在地的。**

**落地**：選題階段就擋（`plan_gate` 紅線清單），不要拖到剪輯段才發現。

### R30 — 語音克隆只准 clone 自己

自己的聲音（含 AI clone 自己）合規且免揭露；**他人／名人聲音一律禁**。

**why**：官方逐字豁免「Cloning one's own voice to create voice overs」（§ytai-08）。
反向：他人聲音克隆可被 privacy complaint 下架（§ytai-12）；若 NO FAKES Act 通過院會，
會升級為聯邦民事責任（§law-08，**尚未成法，別當已生效**）。

**落地**：素材紅線清單 + 揭露勾選 SOP（clone 自己 → 不勾）。

### R31 — AI 化身避開四類敏感題

若未來做虛擬主持人／AI persona，避開**財務／法律／健康／醫療**；現行真人旁白不受此限。

**why**：2026-07-16 生效的 YPP 條款明文不可營利「AI-generated personas to deliver information on sensitive topics」（§ytai-05）。
教工具／剪輯不在敏感題清單。

**落地**：選題階段的「形式 × 題材」矩陣檢查。

### R32 — AI 生成音樂要勾揭露

BGM 維持授權曲庫；哪天改用 AI 生成音樂，該支上傳**必勾揭露**。

**why**：「AI generated music」在必勾清單逐字列出（§ytai-07）；量產 AI 音樂另踩 inauthentic content（§ytai-13）。
授權曲庫 = 零義務。

**落地**：音訊 build 環節註記 + 上傳 checklist。

### R33 — 永不剝除 provenance / C2PA metadata 躲標籤

被自動標 = **透明標示，不是處罰**，接受即可。

**why**：三大平台都走 C2PA + 浮水印自動偵測（§plat-03 §plat-07 §plat-08）；
官方明確確認「AI 標籤不影響推薦與營利」（§ytai-10）；
「為躲標示而去除」在多州立法趨勢下有法律風險（§law-06）。
而且——**一邊教 AI 一邊洗標，是頻道公信力自殺。**

**落地**：素材處理 SOP（生成式圖像／縮圖輸出環節）。

### R34 — 社群貼文守四線

本人帳號 + **逐篇人工確認** + 正常頻率，永不升級成全自動無審高頻；
不堆 hashtag、caption 不與內容脫節、同內容不跨多帳號重發；附圖含擬真 AI → 發布時勾揭露。

**why**：「人工確認」是遠離 Inauthentic Behavior（§plat-13）與 spammy content（§plat-10）打擊面的**護城河**；
純文字 AI 貼文零標示義務（§plat-01），但擬真 AI 影音是唯一強制自行揭露條款，官方明言「may apply penalties」（§plat-02）。

**落地**：社群發文流程內建 checklist（發布前 4 問）。

### R35 — 只引用有官方出處的數字

教學口播與文件只引用**有可點出處**的數字；speculative 門檻（equal seeding、Shorts 70% 留存壓分發、
廣告 strike 制罰則）一律不進稿。

**why**：這些數字全是 SEO 內容農場自製、官方查無（§algo-10 §algo-11 §plat-05）。
教了 = 傳播錯誤資訊（[`meta-lessons.md`](meta-lessons.md) M10 違規），拿來自我診斷 = 誤判決策。
只講官方口徑（滿意度的方向性、watch-time share 判贏等）。

> 📌 **這條也是本 repo 的自我約束**：`no link, no number` —— 第三方數據沒有可點出處就不刊。
> kit 裡剩下的無出處門檻（例如 [`youtube-algorithm-mastery.md`](youtube-algorithm-mastery.md) §TL;DR 那張表、
> 其中的 Shorts「70%+ 不滑走」）都已就地標註「這不是基準，是起跑線」。**看到沒標的，那是 bug，請開 issue。**

**落地**：腳本 gate 的事實查核項 + 生成腳本時標注來源等級。

### R36 — 漏勾不恐慌，慣性不勾才致命

發現漏勾就回 Studio 補勾或申訴誤標，**不刪片重傳**。

**why**：處罰原句的關鍵詞是「**consistently** choose not to disclose」——針對慣犯，非單次失誤（§ytai-09）；
誤標可在 Studio 申訴更正（§ytai-10）。

**落地**：發布後監控 SOP（發片後 24h 檢查標籤狀態一項）。

### R37 — 每支片保持高密度「真人證據」

自己的聲音 + 自己的操作畫面 + 自己的真後台數據，**三者至少各出現一次**。

**why**：官方 2026 年度信定調 AI slop 治理 = 降低低質 AI 內容能見度（§ytai-04）；
報導面有 faceless 頻道被誤傷的案例（§ytai-06）。**真人證據密度是與 slop 的機器可辨區隔。**

**落地**：`src/capcut_helpers/delivery_qa.py` 的 `final_delivery_qa()` 人工項加「真人證據三件套」檢查。

### R38 — 一次性帳號設定 + 季度複查

- Studio 啟用 **likeness detection**（尤其臉會在縮圖出鏡的話）
- **third-party AI training 開關維持關閉**（預設就是關）
- audio 偵測上線後補登記自己的聲音

**why**：likeness detection 已開放所有 18+ 創作者，需政府 ID 驗證約 5 天，資料不用於訓練、可退出（§ytai-11）；
audio 偵測官方承諾 2026 內、截至 2026-07 未上線（§ytai-12）；training 開關見 §ytai-14。
**聲音通常是個人頻道最大的 identity 資產**，被仿聲做假教學詐騙是最現實的冒用場景。

**落地**：一次性設定任務 + 季度回顧項。

---

## ✅ 發布前 10 項合規 checklist

> 直接複製進你的發布套件模板。每項後面的括號是對應規則。

- [ ] **擬真判定**：本支是否含「可能被誤認為真實人／地／事件」的 AI 生成影像、聲音或音樂？
      有 → 上傳勾「Altered content」+ 該段畫面已加「AI 生成」字卡；全風格化／真實素材 → 免勾（R26）
- [ ] **旁白確認**：全片旁白 = 本人真聲自錄（或 clone 自己的聲音），無任何他人／合成語音（R30）
- [ ] **原創貢獻一句話**：本支的親自實測／真後台數據／個人方法論是 ＿＿＿＿＿（**寫得出來才准發**）（R27）
- [ ] **數據誠信**：戰績／proof 數字全部 = 真後台截圖（M107），無自繪；重建型 demo 內容與實際執行 1:1 相符、無美化（M10）
- [ ] **深偽三不**：全片無他人臉／聲合成、無性相關合成、無政治人物／選舉相關合成（**含 demo 示範**）（R29）
- [ ] **BGM 來源**：授權曲庫；若本支用了 AI 生成音樂 → 已勾揭露（R32）
- [ ] **數字出處**：口播與字卡數字全部有官方出處，無 speculative 門檻數字（equal seeding／Shorts 70% 留存／strike 制等）（R35）
- [ ] **系列比對**：本集 vs 前集有結構差異 + 獨立實測數據，非同模板換皮（R28）
- [ ] **metadata**：素材 metadata 未剝除；縮圖若經生成式功能處理 → 接受平台自動標籤，不洗標（R33）
- [ ] **配套社群貼文**：本人逐篇確認後才發、無 hashtag 堆疊、caption 與內容相符、附圖含擬真 AI 已勾揭露（R34）

**發布後 24h 補一項**：回 Studio 確認 AI 標籤狀態（有沒有被自動標／有沒有誤標要申訴）（R36）。

---

## 🔭 監控清單（季度掃一次就好）

政策與法規是移動目標。下面每一條**現在都不需要你做任何事**，但變了就要改 SOP：

| 監控項 | 現況（2026-07） | 變了要改什麼 |
|---|---|---|
| EU AI Act Art.50 對境外個人創作者的執法解釋 | 2026-08-02 生效，官方 FAQ 未明答域外範圍、查無執法先例（§law-03） | 若出現首批執法案例 → 重評；除非開歐盟業務實體，實務動線仍是「對平台合規」 |
| NO FAKES Act 院會表決 | 出委員會、未成法，估成法機率 27%（§law-08） | 若通過 → 他人聲音／肖像 AI 複製從平台政策問題升級為聯邦民事訴訟風險（R30 已提前合規） |
| likeness detection 擴及 audio | 官方承諾 2026 內，截至 2026-07 未上線（§ytai-12） | 上線即去 Studio 登記聲音（R38 後半） |
| 你所在法域的 AI 內容標示子法 | 多數法域仍在框架法／子法制定窗口（§law-10） | 若引入內容標示義務 → 更新上傳 SOP。**這本身是好選題**（「AI 法上路，創作者要做什麼」） |
| 美國州級強制標示的合憲性訴訟 | 一審判違憲、上訴中（§law-09） | 決定美國州級「政府強制標示」的存廢；選舉年持續不碰候選人合成內容即可 |
| Paid Hype 全球化 | 少數市場測試中，無全球日期（§algo-07） | 未在你的市場生效前不對觀眾預告；免費 Hype 已可用可測 |
| 廣告 AI 揭露罰則 | 流傳的 strike 制經查證官方無此條款（§plat-05） | 官方真出罰則條款再更新 R34 |
| YPP inauthentic content / 揭露義務條文 | 最近一波為 2026-07-16 的 AI persona 敏感題條款（§ytai-05） | **季度重讀一次現行版**（Help 1311392 / 14328491） |

---

## 🔗 相關檔案

- [ai-content-compliance-sources.md](ai-content-compliance-sources.md) — 53 條分級法源（查證用，日常不必讀）
- [viral-playbook-framework.md](viral-playbook-framework.md) — 六站命中率系統（站 1 選題就要過本檔的紅線、站 5 發布跑本檔 checklist）
- [youtube-algorithm-mastery.md](youtube-algorithm-mastery.md) — 演算法深度 playbook（§2b 雙機器作戰模型 / §2「48h vs day-14」判死時序 / retention / packaging）
- [youtube-algorithm-2026.md](youtube-algorithm-2026.md) — 2026 演算法變化（R15-R25）
- [meta-lessons.md](meta-lessons.md) — M10（不編造數字）／M107（上鏡數據只用真後台截圖）的原始教訓
