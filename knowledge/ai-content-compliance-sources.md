> 來自 video-autopilot-kit 開源知識庫 · MIT 授權

# AI 內容合規 — 法源出處附錄（53 條分級引用）

> ⚠️ **這是查證用附錄，日常合規檢查不需要讀本檔。**
> 規則本體（R26-R38 + 發布前 10 項 checklist + 管線曝險對照 + 監控清單）
> → [ai-content-compliance.md](ai-content-compliance.md)
>
> **用法**：規則裡標「（法源 → sources §ytai-07）」時，`grep '§ytai-07'` 直接跳該區塊，不必整檔載入。
> 錨點在本檔是**穩定 ID**：條目內容會隨法規更新改寫，但編號不重排、不回收。

## ⚖️ 有效期與適用範圍（讀任何一條之前先看）

- **時點**：本檔是**截至 2026-07** 的整理。法規與平台政策會過期，官方條文也可能在你讀到的當天已經改過。
- **法域**：下面的 law 區塊涵蓋 **EU / 美國聯邦與州 / 台灣 / 中國** 四個法域，是**舉例不是清單** ——
  你所在地的規定不一定相同，可能更嚴也可能還沒有。
- **這不是法律意見**。商業用途（接案、賣課、代客製作、任何有金流的內容）請找**當地**專業人士確認。
- 每條的「行動」欄位是**通用創作者視角的建議動作**，不是義務判定。

## 🏷️ 分級標記

| 標記 | 意義 | 可以怎麼用 |
|---|---|---|
| `[official]` | 官方一手條文 / 公告 / 法規原文 | 可引用、可寫進影片、可當決策依據 |
| `[reported]` | 媒體轉述，官方未逐案確認 | 可參考，引用時標明「據報導」 |
| `[speculative]` | 查無官方出處（多為 SEO 內容農場自製） | **永不進稿**，也不拿來自我診斷 |

> ⚠️ **鐵則（承 [`meta-lessons.md`](meta-lessons.md) M10）**：`[speculative]` 區塊裡的數字
> （equal seeding／Shorts 70% 分發門檻／Meta strike 制罰則）是**反面教材**，收錄它們的目的是
> 「教你認出這類數字」，不是拿來用。教學內容引用了查無實據的數字 = 傳播錯誤資訊。

---

## 區塊索引（53 條：law 13 / algo 12 / platforms 13 / ytai 15）

**TOPIC: law（法規層：EU AI Act / 美國聯邦與州 / 台灣 / 中國）**

- `§law-01` [official] EU AI Act Art. 50 透明義務
- `§law-02` [official] 執委會 FAQ：自然人「純個人、非專業」使用 AI 的排除範圍
- `§law-03` [speculative] EU 對「非歐盟個人創作者」的域外管轄
- `§law-04` [official] 執委會《Code of Practice on Transparency of AI-Generated Content》
- `§law-05` [reported] YouTube 對偵測到的擬真 AI 影片自動加標
- `§law-06` [official] 加州 SB 942《AI Transparency Act》（經 AB 853 修正）
- `§law-07` [official] 美國聯邦 TAKE IT DOWN Act
- `§law-08` [official] NO FAKES Act（未成法）
- `§law-09` [official] 美國州級選舉 deepfake 立法遭遇第一修正案反攻
- `§law-10` [official] 台灣《人工智慧基本法》
- `§law-11` [official] 台灣兩條已生效的刑事紅線（刑法 §319-4 / 選罷法深偽條款）
- `§law-12` [official] 中國《人工智能生成合成内容标识办法》
- `§law-13` [official] 總結：「現在就做 vs 只需監控」分層

**TOPIC: algo（YouTube 演算法近月變化）**

- `§algo-01` [official] 搜尋 filter 全面改版（Shorts 專屬 filter / Popularity）
- `§algo-02` [official] 執行長 2026 年度信：治理 AI slop 列為年度優先
- `§algo-03` [official] BrandConnect 退役 → Creator Partnerships（AI 媒合）
- `§algo-04` [official] 「Ask YouTube」對話式搜尋上線
- `§algo-05` [official] I/O 2026 兩項 AI 內容機制（Shorts Remix / likeness detection）
- `§algo-06` [reported] Test & Compare 完全體（標題 / 縮圖 / 組合三種測試）
- `§algo-07` [reported] Hype 2026 演進（Paid Hype 測試 / 類別排行榜）
- `§algo-08` [reported] Communities 桌面版 + 官方內部實驗數據
- `§algo-09` [official] 【null finding】觀看數定義 2026 無變更
- `§algo-10` [speculative] 【警示】「equal seeding／演算法偏愛新頻道」
- `§algo-11` [speculative] 【警示】Shorts 量化門檻（70% 留存壓分發等）
- `§algo-12` [official] 【null finding】YPP 門檻/分潤 2026 無新政策

**TOPIC: platforms（Meta / TikTok / C2PA 跨平台標示）**

- `§plat-01` [official] Meta「AI info」標籤只涵蓋圖片/影片/音訊
- `§plat-02` [official] Meta 唯一的「強制自行揭露」條款（擬真影音）
- `§plat-03` [official] Meta 自動標示機制 = 讀 C2PA + IPTC metadata
- `§plat-04` [official] 廣告版 AI 標示
- `§plat-05` [speculative] 【警示】流傳的 Meta 廣告「strike 制」罰則
- `§plat-06` [official] TikTok：擬真 AIGC 必須標示
- `§plat-07` [official] TikTok 的 C2PA 自動標示與隱形浮水印
- `§plat-08` [official] C2PA 工具鏈自動夾帶（生成式影像工具）
- `§plat-09` [speculative] 部分設計工具的 C2PA 支援狀況查無官方說明
- `§plat-10` [official] FB 打擊面①（spammy content）
- `§plat-11` [official] FB 打擊面②（unoriginal content / AI slop）
- `§plat-12` [official] FB 打擊面③（Rewarding Original Creators）
- `§plat-13` [official] Meta「Inauthentic Behavior」政策現行版

**TOPIC: ytai（YouTube AI 政策：營利 / 揭露 / 肖像 / 音樂）**

- `§ytai-01` [official] YPP「repetitious」→「inauthentic content」更名
- `§ytai-02` [official] Help 頁現行逐字標準（original creation）
- `§ytai-03` [reported] 2026-01 依 inauthentic content 政策終止 16 個頻道
- `§ytai-04` [official] 年度信把「managing AI slop」列為 2026 優先
- `§ytai-05` [official] YPP 三類不可營利（含 AI persona 敏感題）
- `§ytai-06` [reported] 附帶傷害：faceless 頻道被連坐的報導
- `§ytai-07` [official] 揭露義務【必勾】官方逐字清單
- `§ytai-08` [official] 揭露義務【不必勾】官方逐字清單
- `§ytai-09` [official] 不揭露的處罰官方原句（consistently）
- `§ytai-10` [official] 「不勾也會被標」：自動偵測補標
- `§ytai-11` [official] 肖像偵測（likeness detection）完整時間線
- `§ytai-12` [official] 語音克隆：偵測範圍與現行救濟
- `§ytai-13` [official] AI 音樂三條邊界
- `§ytai-14` [official] 第三方 AI 工具邊界 + third-party training 開關
- `§ytai-15` [official] 「真人旁白 + AI 輔助」官方定位

---

# 附錄：研究底稿（逐條含時間 / 影響 / 行動 / 來源）

# TOPIC: law

## §law-01 [official] EU AI Act Art. 50 透明義務（chatbot 揭露、deepfake 標示 Art.50(4)、公共利益 AI 文本標示）2026-08-02 全面適用，未被 Digital Omnibus 延後；Omnibus（歐洲議會 2026-06-16、理事會 2026-06-29 通過）只給「2026-08-02 前已上市的 AI 系統」的 Art.50(2) 機器可讀浮水印義務 4 個月寬限至 2026-12-02——那是工具商（provider）義務，不是創作者義務
時間: 2026-08-02 生效（Omnibus 寬限條款待官方公報刊登）
影響: 違反 Art.50 罰則上限 €15M 或全球營業額 3%（對 SME 按比例）。對 AI 協作教學頻道：創作者身分是 deployer，deployer 義務只有兩塊——(a) deepfake（像真實人/物/地/事件、看起來像真的合成影音）要在首次接觸時清楚標示；(b) 以告知公眾為目的發布的 AI 生成文本要揭露。一般 AI 生成 b-roll／示意動畫／明顯非寫實的插圖不在 50(4) 範圍；自己真人錄音的旁白完全不觸發；但 AI 語音克隆（像特定真人的聲音）落入 deepfake 定義
行動: 建立 SOP：影片內凡出現「像真人臉／真人聲的 AI 合成段落」（含示範 AI 換臉、語音克隆的教學 demo），畫面上打可見標示（如「AI 生成」角標）+ 勾 YouTube 的 altered/synthetic content 揭露。教學/評測性質的 demo 若屬明顯創作/示範情境，可用不干擾觀看的輕量標示（Art.50(4) 藝術/創作例外允許）。「真聲錄音 + 真截圖」型工作流本身幾乎不觸發義務
來源: https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act ；Omnibus 通過與寬限：https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/

## §law-02 [official] 歐盟執委會官方 FAQ 明確劃線：自然人「純個人、非專業」使用 AI（例如生成 deepfake 發社群）不受 AI Act 管（Art.2(10) 排除）；但若屬「經常性經濟活動或自由業」則構成 deployer、負標示義務。有營利的頻道（廣告分潤／接案／賣課）會被認定為專業活動
時間: FAQ 由執委會發布（2026 上半年），義務 2026-08-02 起
影響: 已營利的頻道 = professional deployer，不能靠「我是個人創作者」豁免；但義務範圍仍僅限 deepfake 與公共利益文本（見上條），不是「所有 AI 輔助內容都要標」
行動: 把「這段是否為 deepfake 性質（像真實人事物且可能被誤認為真）」加入交付前 QA checklist 一條；非 deepfake 的 AI 輔助剪輯／腳本／字幕不需標示
來源: https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act

## §law-03 [speculative] EU 對「非歐盟個人創作者」的域外管轄：AI Act 依 Art.2(1)(c) 及於第三國 provider/deployer「其 AI 系統之輸出在歐盟境內被使用」；但執委會 FAQ 並未明確回答「上傳到全球平台、歐盟人看得到」是否就構成 in-scope，法界解讀分歧，且對境外個人創作者的跨境執法實務上缺乏機制——目前查無任何對非歐盟個人創作者的執法先例或指引
時間: 2026-08-02 起理論上適用；官方解釋缺位（截至 2026-07）
影響: 境外創作者的實際風險不是被歐盟罰，而是**平台端代執行**：平台為了自身 DSA/AI Act 合規會強化標示與偵測，未揭露的合成內容可能被自動貼標或處分。合規動線實際上是「對平台合規」而非「對布魯塞爾合規」
行動: 不需為 EU 做額外法律動作；把力氣放在誠實使用平台的揭露工具。若未來設立歐盟業務實體（賣課給歐盟、設歐盟公司）再重新評估
來源: Art.2 條文：https://artificialintelligenceact.eu/article/50/ ；域外部分官方 FAQ 未明答（本次查證確認缺位）；法界討論：https://www.hsfkramer.com/notes/ip/2026-03/transparency-obligations-for-ai-generated-content-under-the-eu-ai-act-from-principle-to-practice

## §law-04 [official] 執委會 2026-06-10 發布《Code of Practice on Transparency of AI-Generated Content》（自願性），把 Art.50 落成實作規範：機器可讀標記（C2PA／浮水印）+ deepfake 可見標示的具體做法；發布後由執委會與 AI Board 評估其適足性
時間: 2026-06-10 發布（official）；配套義務 2026-08-02 起
影響: 這份 Code 主要給 AI 工具商和平台簽署遵循，創作者不用簽；但它決定了你用的工具之後輸出檔會內嵌什麼 metadata，以及平台怎麼讀取——也就是「平台代履行」的技術底座
行動: monitoring 即可；製作教學內容時可把「工具會自動嵌浮水印、平台會自動讀取」當成選題（對 AI 教學頻道反而是題材機會）
來源: https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content

## §law-05 [reported] YouTube 2026-05-27 宣布：對偵測到「significant photorealistic AI」的影片自動加 AI 標示（即使創作者沒勾揭露），標示位置從說明欄移到播放器正下方（長片）／畫面疊層（Shorts）；偵測讀 C2PA metadata + SynthID 浮水印
時間: 2026-05-27 宣布並開始推行（媒體轉述官方公告）
影響: 對 AI 教學頻道是雙面刃：(1) 用 AI 工具做的 demo 素材可能被自動貼標，且標示現在很顯眼；(2) 自己誠實勾揭露的創作者不受額外處分，被系統「抓到沒揭露」的觀感較差
行動: 上傳流程 SOP 加一步——影片含寫實向 AI 生成畫面／聲音就主動勾「altered or synthetic content」揭露，別等系統自動標；教學 demo 段落順手在畫面加「AI 生成示範」字卡（同時滿足 EU 可見標示）
來源: https://techcrunch.com/2026/05/27/youtube-will-now-automatically-label-ai-videos/ ；https://variety.com/2026/digital/news/youtube-ai-video-labels-automatic-detection-1236758865/（官方 blog 原文未直接取得，故標 reported）

## §law-06 [official] 加州 SB 942《AI Transparency Act》經 AB 853（2025-10-13 簽署）修正：生效日從 2026-01-01 延到 2026-08-02（刻意對齊 EU AI Act）；義務主體是 covered provider（月活 >100 萬的公開 GenAI 系統開發商）——須提供免費 AI 偵測工具 + 內嵌 latent watermark；2027-01-01 起 large online platform 須偵測並向用戶顯示內容中的 provenance data；2028 起及於拍攝裝置製造商
時間: 2025-10-13 簽署；2026-08-02 生效（provider 義務）；2027-01-01（平台義務）
影響: 對個人創作者零直接義務——這是管 AI 工具商和平台的法。間接影響：你用的美系 AI 工具 2026-08 後輸出會帶 provenance metadata，平台 2027 起會把它顯示出來
行動: 不需動作，但注意一點：後製流程不要刻意剝除素材的 provenance metadata（轉檔／壓縮的正常流失不算，但「為了躲標示而去除」在多州立法趨勢下有風險）
來源: https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202520260AB853 ；解讀：https://www.troutmanprivacy.com/2025/10/california-ai-transparency-act-amendments-signed-into-law/

## §law-07 [official] 美國聯邦 TAKE IT DOWN Act：2025-05-19 簽署成法（刑事條款即時生效），平台端 notice-and-removal 義務 2026-05-19 起由 FTC 執法——收到有效通報後 48 小時內下架非自願親密影像（含 AI deepfake），違者每件民事罰款 $53,088
時間: 2025-05-19 成法；2026-05-19 平台合規大限已到、FTC 已開始執法
影響: 對教學頻道兩面：(1) 紅線——任何教學 demo 都不可用真人（含公眾人物）臉／聲生成親密或性暗示內容，這在美國是聯邦刑事罪；(2) 保護——若你本人被人做成 deepfake NCII，可向任何美系平台發通報，48 小時內必須下架
行動: 把「demo 素材不用真人做任何性相關合成」寫入內容紅線；同時知道自己有 48 小時下架救濟管道
來源: https://www.lw.com/en/insights/president-trump-signs-take-it-down-act-into-law ；FTC 執法起跑：https://www.wiley.law/alert-May-19-Deadline-for-TAKE-IT-DOWN-Act-Compliance-Is-Your-Company-Prepared

## §law-08 [official] NO FAKES Act（聯邦聲音／肖像數位替身財產權 + 通知下架制，2026 版新增 DMCA 式 counter-notice 反通知程序）：2026-05-20 重新提出（S.4591 / H.R.8915），2026-06-18 參院司法委員會全票通過送院會——**尚未成法**，截至 2026-07 查無院會表決；GovTrack 估成法機率 27%
時間: 2026-06-18 出委員會；院會表決未定（截至 2026-07）
影響: 若通過：未經授權的 AI 名人聲音／肖像複製將有聯邦民事責任，平台接獲通知須下架。對 AI 教學頻道最相關的是「示範語音克隆工具」類內容——用名人聲音做 demo 的風險會從平台政策問題升級成聯邦訴訟風險
行動: monitoring（尚未生效，勿當已生效處理）；但現在起養成習慣：語音克隆 demo 只用自己的聲音，不用名人／他人聲音當示範素材
來源: https://www.congress.gov/bill/119th-congress/senate-bill/4591 ；https://www.hklaw.com/en/insights/publications/2026/06/senate-judiciary-committee-advances-legislation-to-protect-name

## §law-09 [official] 美國州級「強制標示／下架選舉 deepfake」立法遭遇第一修正案反攻：加州 AB 2839（選舉 deepfake 禁令）2024-10-02 被聯邦法院初步禁制、2025-08 被判違憲；AB 2655（要求平台標示／下架選舉深偽）也被駁回（Section 230 先占）；加州上訴第九巡迴中（2026-01-12 提上訴狀、2026-03-11 對造答辯，未判）
時間: 2025-08 一審判違憲（official）；上訴審理中（截至 2026-07 未決）
影響: 說明美國「政府強制標示 AI 內容」的執法前景高度不確定，實際約束創作者的仍是平台政策而非州法。對非政治型教學頻道直接影響趨近於零
行動: 純 monitoring；唯一注意：美國選舉年別碰候選人相關的 AI 合成內容 demo，各州仍有 20+ 部選舉深偽法且個案有效性不一
來源: https://www.techpolicy.press/tracker/kohls-v-bonta/ ；https://clearinghouse.net/case/46692/

## §law-10 [official] 台灣《人工智慧基本法》：2025-12-23 三讀，2026-01-14 公布同日施行，全 20 條，中央主管機關 = 國科會。定位是框架法／政策宣示——對個人創作者零直接義務、零罰則；第 5 條「高風險應用應明確標示注意事項或警語」義務落在被認定為高風險的 AI 產品／系統（開發商端）；第 16 條要求主管機關建立與國際介接的 AI 風險分類框架；第 18 條要求各部會於施行後 2 年內（至 2028-01）完成配套法規制修
時間: 2026-01-14 公布施行（official，全國法規資料庫 H0160093）
影響: 該法域的創作者現在沒有任何 AI 內容標示的法定義務——基本法沒規定，風險分類框架和子法都還沒出。真正會影響創作者的是未來 2 年內陸續出爐的子法
行動: monitoring：追蹤風險分類框架草案與子法動態（2026-2028 窗口）。**這本身是 AI 教學頻道的好選題**（「AI 法上路，創作者到底要做什麼」——答案是目前什麼都不用，反直覺有流量）
來源: https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=H0160093 ；https://moda.gov.tw/press/press-releases/18316

## §law-11 [official] 台灣「現在就已生效、踩了就中」的兩條既有紅線：(1) 刑法 §319-4 不實性影像罪（2023-02-10 生效）——以電腦合成／深偽製作或散布他人不實性影像，5 年以下有期徒刑，意圖營利 7 年以下；(2) 選罷法深偽條款（2023-06 修正生效）——散布候選人／被罷免人之深度偽造聲音影像犯誹謗罪者 7 年以下，營利加重至二分之一並得併科 200 萬-1000 萬罰金
時間: 刑法 2023-02-10 生效；選罷法 2023-06 生效（皆已施行中）
影響: 對 AI 教學頻道的直接約束：示範換臉／語音克隆工具時，(a) 絕不能用任何真人做性相關合成（連「示範它能做到」都構成製作）；(b) 選舉期間不碰政治人物深偽 demo。**這是刑法不是平台政策**——平台申訴救不了
行動: 內容紅線清單加兩條——深偽 demo 只用自己或已授權對象、且不涉性與選舉。**其他法域多半有對應條文，請查你自己所在地的**
來源: 刑法 §319-4：https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode=C0000001&flno=319-4 ；https://www.moj.gov.tw/2204/2795/2796/163177/post ；選罷法修正：https://www.cna.com.tw/news/aipl/202305260209.aspx

## §law-12 [official] 中國《人工智能生成合成内容标识办法》（網信辦等四部門）2025-09-01 施行：AI 生成內容須加顯式標識（用戶可感知的文字／聲音／圖形）+ 隱式標識（metadata 內嵌服務商代碼等）；平台須查驗並對疑似 AI 內容加「疑似AI生成」標記；任何人不得刪除、篡改、隱匿標識。義務主體是境內服務提供者、平台與發布者——境外創作者無直接義務，但內容被搬運到中國平台時，搬運者與平台承擔標示責任
時間: 2025-03-14 發布、2025-09-01 施行（已生效）
影響: 對境外創作者的連帶影響（可略）：影片被搬運後，含 AI 段落的內容大概率被自動打「疑似AI生成」標；若影片內建清楚的 AI 段落聲明（字卡／口播），被搬運後較不易被誤判為刻意隱匿
行動: 順手即可：教學影片中 AI demo 段落保留畫面內字卡聲明（與 EU／YouTube 動作合一，**一個動作三地受益**）；不必為此做任何額外動作
來源: https://www.cac.gov.cn/2025-03/14/c_1743654685899683.htm ；施行報導：http://www.news.cn/legal/20250901/a12108b0b10249e5bae4435269e40c91/c.html

## §law-13 [official] 總結「現在就做 vs 只需監控」分層（供合規決策直接取用）：**現在就做** = ①上傳 SOP 勾平台的 altered/synthetic 揭露（別等自動偵測抓）②寫實向 AI 段落畫面加「AI 生成」字卡（一次滿足 EU、YouTube、中國搬運三場景）③內容紅線：深偽 demo 不用他人臉聲、不涉性、不涉選舉（台灣刑法／選罷法 + 美 TAKE IT DOWN 已全部生效）。**只需監控** = EU 對境外個人執法動態、NO FAKES 院會表決、加州 Kohls v. Bonta 上訴、台灣子法窗口（2026-2028）
時間: 彙整時點 2026-07
影響: 「真人聲錄音 + 真截圖 + 不做換臉／克隆內容」型工作流與所有已生效法規天然相容——合規成本趨近於零，新增動作只有揭露勾選 + 字卡兩項
行動: 把 3 個「現在就做」寫進交付前 checklist；4 個監控項設季度回顧
來源: 本檔各條之官方來源綜合（EU FAQ／全國法規資料庫／Congress.gov／CAC／FTC）

# TOPIC: algo

## §algo-01 [official] YouTube 搜尋 filter 全面改版：Type 新增「Shorts」專屬 filter、「Sort by」改名「Prioritize」、「View count」改名「Popularity」（改為綜合觀看數 + watch time 等 relevance 訊號）、移除「Last Hour」與「Sort by Rating」、時長 filter 改為「Under 3 minutes」+ 新增「3–20 minutes」檔
時間: 2026-01-08 官方宣布，1 月起陸續生效
影響: **Shorts SEO 第一次成為真實入口**：觀眾可只搜 Shorts → 教學 Shorts 的標題／前 3 秒關鍵字直接吃搜尋流量。「Popularity」摻入 watch time 代表搜尋排序不再純看觀看數，小頻道高留存教學片在搜尋面更有機會。「3–20 min」檔正好罩住教學長片主力時長
行動: (1) Shorts 標題開始做關鍵字化（不只 hook）；(2) 長片維持 3-20 分鐘區間內、留存優先；(3) 不必再追「最新一小時」時效打法，該 filter 已死
來源: 9to5Google 2026-01-08（含官方聲明引文）https://9to5google.com/2026/01/08/youtube-search-filters/

## §algo-02 [official] YouTube 執行長 2026 年度信：明列「治理 AI slop」為年度優先事項——AI 內容強制標示 + 移除違規合成媒體；同時公布 12 月單月 100 萬+ 頻道每日使用官方 AI 創作工具、Shorts 日觀看 200B、將把 image posts 等格式直接整合進推薦 feed
時間: 2026-01-21 發布（官方 blog）
影響: 對 AI 協作教學頻道是雙面：官方 AI 工具使用被正面看待，但「AI slop」打擊代表低人味、量產感的 AI 內容會被壓分發。image posts 進 feed = 社群貼文分發面變大
行動: (1) 每支含擬真 AI 生成畫面的影片老實勾 altered content 揭露；(2) 內容持續強調「人的方法論 + 真實後台數據」（[`meta-lessons.md`](meta-lessons.md) M107）與 slop 劃清界線；(3) 社群貼文（含圖片貼文）可以當額外分發面認真經營
來源: https://blog.youtube/inside-youtube/the-future-of-youtube-2026/ ；CNBC 2026-01-21

## §algo-03 [official] BrandConnect 退役 → 改為「YouTube Creator Partnerships」：AI 依受眾相似度／自然品牌提及／訂閱成長自動媒合品牌與創作者，入口內建 Studio（創作者端）+ 廣告後台（品牌端），涵蓋 3M+ YPP 創作者
時間: 2026-03-23~26 NewFronts 官方宣布
影響: 品牌合作從「自己找」變「被 AI 匹配」——小教學頻道若有清楚 niche + 自然工具提及，反而容易被撈到。變現面變化，不直接動自然分發
行動: 進 YPP 後在 Studio 留意入口；影片保持清楚的工具名口播與描述欄標註（= 給匹配系統的訊號），不用改變內容策略
來源: https://blog.youtube/news-and-events/youtube-creator-partnerships-newfronts-2026/ ；Tubefilter 2026-03

## §algo-04 [official] 「Ask YouTube」對話式搜尋上線：自然語言複雜查詢 + 追問，AI 從長片與 Shorts 內容中彙整出結果片段回給使用者
時間: 2026-05-19 官方宣布；初期限特定地區 18+ Premium 會員，官方稱將擴大
影響: **教學內容是對話式搜尋最大受益題材**。AI 要能從你影片裡抽出答案段落 → 結構清楚、口播明確講出問題與答案的影片會被優先引用；含糊閒聊型吃虧
行動: 長片維持章節化 + 每段開頭一句明確「這段解決什麼問題」；描述欄與字幕保持精準關鍵字——**字幕檔就是 AI 檢索的原料**
來源: https://blog.youtube/news-and-events/youtube-news-google-io-2026/

## §algo-05 [official] I/O 2026 兩項 AI 內容機制：(1) 生成模型進 Shorts Remix／官方創作工具——他人可對 eligible Shorts 下 prompt 改場景／置入自己，成品帶數位浮水印 + metadata 回連原片，創作者可 opt-out visual remix；(2) Likeness detection（AI 冒用臉／聲偵測管理工具）開放給所有 18+ 創作者
時間: 2026-05-19 官方宣布
影響: 你的 Shorts 可能被別人 AI remix（帶回連 = 額外曝光管道，但也可能被改到失真）；likeness 工具對不露臉頻道影響小，但**聲音 + 頻道名被 AI 冒用做假教學詐騙**的風險現在有官方工具管
行動: (1) 決定 remix 立場：教學 Shorts 建議先不 opt-out（回連 = 免費入口），發現被改壞再關；(2) 到 Studio 登記 likeness detection——用聲音出鏡的頻道值得開
來源: https://blog.youtube/news-and-events/youtube-news-google-io-2026/

## §algo-06 [reported] Test & Compare 完全體：從「只能測 3 張縮圖」擴為「標題 only／縮圖 only／標題+縮圖組合」三種測試、各最多 3 變體，判贏仍以 watch-time share（每曝光帶來的觀看時長份額），結果分 Winner / Performed Same / Inconclusive
時間: 官方 2025-07-14 宣布小比例測試 → 多家工具商回報 2025-12 全球開放
影響: 包裝槓桿從縮圖戰升級為完整包裝戰：標題黨 vs 資訊型標題終於可以機械驗證，且**判準是 watch-time share 不是裸 CTR**——點了不看 = 輸
行動: 每支新長片上片時直接跑「標題 + 縮圖組合」測試取代單測縮圖；測試期 1-2 週，排進發片後監控 SOP。注意：全球開放的具體日期是工具商／媒體回報，官方原文只確認功能存在與逐步擴大
來源: 官方宣布：Social Media Today 2025-07-14（引官方聲明）；全球開放時間：vidIQ / thumbnailtest / TubeBuddy 2025-12 回報

## §algo-07 [reported] Hype 2026 演進：部分市場測試「Paid Hype」（粉絲付費加購 hype 點數、創作者分潤）；另新增類別排行榜、hype 按鈕移到影片下方、免費 hype 擴至更多國家。全球免費版 2025-08-26 已上線（39 國、<50 萬訂閱可被 hype、每人每週 3 次）
時間: 免費全球版 2025-08-26 官方；Paid Hype 測試 2026 進行中、無官方全球日期
影響: <50 萬訂閱的教學頻道全部在可被 hype 範圍。Hype 排行榜 = Explore 內的獨立分發面，粉絲動員可換真曝光
行動: 這是**平台原生**槓桿（非外部導流）：片尾／置頂留言可加一句 hype 提示測一次成效；Paid Hype 未在你的市場生效前不要對觀眾預告
來源: TechCrunch 2025-08-26（全球版）；官方 Help：support.google.com/youtube/answer/15509925

## §algo-08 [reported] Communities 桌面版可用 + 可在 Studio 管理與版務；官方內部實驗（2025-09）稱開啟 Communities 的頻道平均貼文曝光與讚數上升——這是目前唯一一筆官方口徑的「Communities 影響分發」數據
時間: 全員開放 2025-06-17 官方宣布；桌面版與管理工具 2025 下半年～2026 陸續補齊
影響: **官方實驗只證明「貼文面互動／曝光」提升，沒有任何官方說法稱開 Communities 會提升影片推薦分發**——不要把兩者混為一談
行動: 當「站內輕互動面」低成本開著即可（貼文曝光紅利照拿）；**別基於「開 Communities 助推影片」做決策**——查無此官方依據
來源: 官方宣布：blog.youtube / ppc.land 2025-06-17；實驗數據：官方轉述（工具商 2025-09 引用）

## §algo-09 [official] 【null finding】觀看數／瀏覽量定義 2026 年 1-7 月查無任何新變更。唯一近期變更仍是 2025-03-31 的 Shorts views 改制（每次播放／重播／滑過都算 view、舊定義改名 engaged views 且仍是獲利與分發參考）
時間: 多輪搜尋截至 2026-07，官方 Help（view metrics 頁）無 2026 改版
影響: 數據對帳可以放心：後台 views／engaged views 口徑 2026 全年至今穩定，跨月比較不需折算
行動: 案例研究與後台截圖引用數字照現行口徑即可；Shorts 引用時繼續分清 views vs engaged views 兩個數字
來源: YouTube Help view metrics 文件（無變更）+ 2026 各媒體僅重述 2025-03 改制

## §algo-10 [speculative] 【警示】流傳的「新一代系統下每支影片 equal seeding、小頻道與大頻道同起跑線」「新頻道 2026 被主動 push」說法——**查無任何官方來源**。官方可考的仍是舊機制：新片先給依 metadata／觀看歷史選出的小樣本測試受眾，表現好再擴圈，加上 Hype 這類明示的小頻道扶持面
時間: 2026 上半年 SEO 農場文大量流傳；無官方出處
影響: 若把「equal seeding」當真會誤判：以為片差也能被公平測到 → 其實包裝 + 前 30 秒差就沒有第二輪
行動: 策略照舊（seed day-0 打法 + Hype + 搜尋面），**不要基於「演算法偏愛新頻道」調整任何 SOP**
來源: 流傳源：多家 SEO 部落格 2026 文章；官方查證：無（官方 blog 與 Creator Insider 皆無此說法）

## §algo-11 [speculative] 【警示】流傳的 Shorts 量化門檻——「留存 70% 以下壓全頻道分發」「首 30-60 分鐘不達標就停推」「swipe-away rate 是第一過濾器」等具體數字——**全部查無官方出處**，是第三方部落格自行歸納。官方已證實的只有 2025 的 Shorts／長片脫鉤與滿意度方向
時間: 2026 年 1-7 月間各 SEO 文章流傳；無官方公告
影響: 這些數字若寫進教學影片會變成「教了查無實據的東西」（M10 違規）；拿來自我診斷也會誤判。**kit 內任何出現「Shorts 70%」的表格都屬於這一類，已在原檔標註「無出處」**
行動: 教學內容與自家 Shorts 診斷都不要引用這些具體門檻數字；要講就講官方口徑（滿意度、swipe 行為的方向性影響），**不給假精確數**。續看率門檻請按 [`viral-playbook-framework.md`](viral-playbook-framework.md) §1b 的方法用自己的 3-5 支片校準
來源: 流傳源：多家短影音 SEO 部落格 2026 文章；官方查證：無

## §algo-12 [official] 【null finding】YPP 獲利門檻／演算法分潤 2026 年 1-7 月查無新政策。流傳的「2026 降門檻到 500 訂閱」實為 2023-06 舊制（500 訂／3 片／3000 小時或 3M Shorts views 的 fan-funding 先行層）；分潤仍 55%（長片）/45%（Shorts）
時間: 多輪搜尋截至 2026-07 無官方新公告
影響: 獲利合規面 2026 至今無新紅線；AI 內容相關的合規重心在「揭露義務 + AI slop 治理」而非 YPP 條款本身
行動: 維持現行揭露與原創性做法即可，不需因流傳的「2026 新門檻」文章改任何東西
來源: YouTube Help YPP 資格頁（無 2026 變更註記）；2026 各文章經比對均為 2023 舊制重寫

# TOPIC: platforms

## §plat-01 [official] Meta「AI info」標籤只涵蓋圖片／影片／音訊，**純文字貼文完全不在標示範圍**——AI 生成的文字貼文目前既不會被自動標、也沒有自行標示義務
時間: 2024-05 起全面滾動（前身「Made with AI」），2024-07-01 改名「AI info」；至今（2026-07）官方頁面仍只寫 video/audio/image
影響: 「AI 學我的語氣寫貼文 → 本人確認後發布」這種模式在 Meta 現行標示政策下零標示義務、零觸發風險
行動: 純文字 AI 貼文照發，不需加任何 AI 揭露；但若貼文附圖是 AI 生成，另見 §plat-03 / §plat-08
來源: Meta Transparency Center「Labeling AI Content」(transparency.meta.com/governance/tracking-impact/labeling-ai-content/) + about.fb.com 2024-04-05「Our Approach to Labeling AI-Generated Content」

## §plat-02 [official] Meta 唯一的「強制自行揭露」條款：發布「photorealistic video 或 realistic-sounding audio」且為數位生成／改造的 organic 內容時，必須用揭露工具標示，原文明言「we may apply penalties if they fail to do so」（未定義具體罰則）
時間: 2024-02-06 公布（2025-04-01 更新）；2026-02 官方文重申此條仍現行有效
影響: **只有做「擬真 AI 影片／擬真 AI 語音」上 FB/IG 才踩到強制揭露線**；文字與非擬真圖像不在此列。教學頻道若示範 AI 語音克隆成品發 FB，該支內容就需標
行動: 凡上傳擬真 AI 影音到 Meta 平台，發布時主動勾 AI 揭露；一般貼文不受影響
來源: about.fb.com/news/2024/02/labeling-ai-generated-images-on-facebook-instagram-and-threads/ + about.fb.com/news/2026/02/meta-prepares-for-2026-us-midterms/

## §plat-03 [official] Meta 自動標示機制 = 讀 C2PA + IPTC metadata（industry-shared signals），偵測到即自動掛「AI info」；合作偵測對象含多家主流 AI 工具商的輸出。2024-09-12 起「僅 AI 編輯（非整張生成）」的內容標籤收進三點選單不直接露出
時間: 2024-05 起；2024-09-12 標籤位置調整；持續運作至今
影響: 上傳的圖／片只要帶 AI metadata 就會被標，創作者無法拒絕；但輕度 AI 編輯的標籤已改為藏在選單內，視覺衝擊小
行動: 了解機制即可：**被自動標 ≠ 違規 ≠ 處罰**，只是透明標示；不要為了躲標籤去洗 metadata 再宣稱純人工（誠信風險大於標籤本身）
來源: about.fb.com 2024-02 文（點名 C2PA/IPTC 與合作工具商）+ 2024-04 文（2024-09-12 更新段）

## §plat-04 [official] 廣告版 AI 標示：Meta「About this ad」統一入口上線，用 Meta 生成式 AI 工具製作／大改的廣告自動掛 AI info；重大編輯或出現 photorealistic 真人時標籤直接放「Sponsored」旁。2026-06-01 更新：開始對偵測到「第三方 AI 工具」製作的廣告加註更多資訊
時間: 2025-02-03 公布 rollout；2026-06-01 官方更新擴大第三方偵測
影響: 若日後投廣告推頻道且素材用 AI 做，會被自動標——這是偵測型標示，官方文未寫廣告主未揭露的罰則
行動: 投放 AI 素材廣告時預期會有標籤，不影響投放資格；政治／社會議題廣告另有強制揭露，教學頻道通常不涉及
來源: about.fb.com/news/2025/02/gen-ai-transparency-metas-ads-products/（含 2026-06-01 update）

## §plat-05 [speculative] 【警示】多篇行銷部落格宣稱「2026-03 起 Meta 對所有廣告主強制 AI 揭露、違規 = strike → 24h 帳號凍結 → 停權、未揭露 AI 佔 14% 廣告拒登」——**此套具體罰則在官方來源完全查不到**，數字疑為 SEO 內容農場自製
時間: 傳聞指向 2026-03 生效；查證日 2026-07 官方無此條款
影響: 若把這套「strike 制」當真會過度自我設限；但也不能反向解讀為零風險——官方僅確認偵測 + 標示機制存在
行動: 合規決策只依官方已確認條款（§plat-01~04）；**別引用第三方部落格的罰則數字進教學內容**
來源: 查證比對：多家行銷部落格宣稱 vs about.fb.com + transparency.meta.com 全文無對應條款

## §plat-06 [official] TikTok：創作者必須標示「realistic AIGC」（擬真人物／場景／聲音的 AI 生成或大幅改造內容）；**AI 輔助文字（腳本、caption、hashtag）不在標示範圍**。未標的擬真 AIGC：可自動補標、限流或移除；「即使有標仍有害」的 AIGC（誤導性深偽等）直接禁
時間: 標示義務 2023-09 起；社群守則 2025-09-13 大改版重寫
影響: 講稿 AI 寫 = 不用標；但示範 AI 生成的擬真畫面／配音就要開官方 AIGC 標籤
行動: 上 TikTok 的內容凡含擬真 AI 影音元素，發布時開內建 AI-generated 標籤；純錄屏教學 + 真人聲音不用
來源: TikTok Newsroom「New labels for disclosing AI-generated content」(2023-09) + Community Guidelines Integrity & Authenticity

## §plat-07 [official] TikTok 是 C2PA 自動標示最深的平台：2024-05-09 成為第一個實作 Content Credentials 的影音平台（自動讀他平台 AI metadata 補標籤）；後續加入 C2PA、測試不可移除的隱形浮水印、推出「Manage topics」讓用戶自調 AIGC 出現量；官方稱累計已標 1.3B+ 支影片
時間: 2024-05-09 首發；隱形浮水印 + Manage topics 於 2025 下半年公布
影響: 在 TikTok「不標讓系統抓」的空間趨近零——用 AI 工具產出的素材帶 metadata 就會被自動標，且浮水印讓轉存洗標失效
行動: 直接主動標，別賭偵測漏網；教學內容可把「平台自動偵測」當賣點講
來源: TikTok Newsroom「Partnering with our industry to advance AI transparency」(2024-05-09) + Newsroom AIGC 透明度更新

## §plat-08 [official] C2PA 工具鏈自動夾帶：主流生成式影像工具（如 Adobe Firefly 系的 generative fill / text to image）「一律自動」在匯出檔嵌 Content Credentials（官方明文），上傳 Meta/TikTok 即觸發自動 AI 標籤——2024 已有攝影師僅用 generative fill 除塵就被標「Made with AI」的實例（Meta 因此在 2024-09 調整標籤位置）
時間: 自動嵌入 = 該工具上線起持續至今；誤標事件 2024 年中廣泛報導
影響: 做縮圖／素材時只要碰過生成式功能，輸出檔就帶 AI metadata；社群貼文附圖會被自動掛 AI info（藏選單內），不是處罰但要有心理準備
行動: 接受標籤即可（最乾淨）；若整張圖其實非 AI 主體，可改用未動用生成功能的流程輸出。**切勿一邊教 AI 一邊洗 metadata 裝純人工**
來源: helpx.adobe.com「Content Credentials for assets generated with Adobe Firefly」+ Meta 2024-09-12 標籤調整（about.fb.com 2024-04 文更新段）

## §plat-09 [speculative] 部分設計工具（如 Canva）：截至查證日**查無**公開支援 C2PA / Content Credentials 的官方聲明——其原生輸出目前應不會夾帶觸發平台標籤的 AI metadata；但若把已含 credentials 的素材匯入再輸出，metadata 是否殘留無官方說明
時間: 查證日 2026-07；官方無相關公告可考
影響: 這類工具做的縮圖被自動標的機率低；但這是「查無」不是「官方保證不標」，且平台偵測模型（非 metadata 路徑）仍可能標擬真 AI 圖
行動: 把此條當**查證缺口**而非豁免依據；教學內容提到某工具時別斷言「絕對不會被標」
來源: C2PA 官方會員名單／該工具官網檢索無果（負面查證）；對照其他設計工具有官方 C2PA 支援

## §plat-10 [official] FB 打擊面①（spammy content）：長 caption + 超量 hashtag、圖文無關 caption、多帳號大量重發同內容、協同假互動 → 只推給既有粉絲（觸及砍）+ 取消營利資格；**官方文通篇未提「用 AI 寫貼文」或「排程工具」本身**
時間: 2025-04-24 官方公布，已生效
影響: 打的是**行為模式**（灌 hashtag／洗量／假互動），不是 AI 產文這件事。單帳號 + 人工審核 + 正常頻率不在打擊面
行動: 貼文別堆 hashtag、caption 要與內容相關、同內容別跨多帳號重發
來源: about.fb.com/news/2025/04/cracking-down-spammy-content-facebook/

## §plat-11 [official] FB 打擊面②（unoriginal content / AI slop）：重複轉發他人內容不加轉化 = 降觸及 + demonetize；2025 上半年制裁 50 萬個 spammy 帳號、移除 1,000 萬個冒充大創作者的帳號。針對的是內容農場式搬運（含 AI 量產搬運），官方定義原創 = 自己拍／製作或有意義加值
時間: 2025-07-14 官方公布，數月內逐步 rollout
影響: AI 幫你寫「你自己的」原創貼文完全不在此定義的打擊面；AI 量產搬運別人內容才是靶心
行動: 維持原創（自己的經驗／教學／語氣），**AI 只當寫作工具不當內容來源**
來源: about.fb.com 2025-07-14 公告（CNBC 2025-07-14、Forbes 2025-07-15 同步報導）

## §plat-12 [official] FB 打擊面③（2026 最新）：「Rewarding Original Creators」——原創內容獲分發獎勵，反覆發非原創者降 reach/Reels 曝光 + demonetize，可申訴；2025 全年共移除 2,000 萬+ 冒充帳號。方向 = 獎勵原創、追殺搬運與冒充，**仍未把「AI 輔助創作」或「排程發文」列為違規**
時間: 2026-03-13 官方公布生效
影響: 2026 年執法主軸確認：**AI 不是罪名，「非原創 + 冒充 + 洗量」才是**。用 AI 學自己語氣寫自己的內容 = 原創，甚至受此政策保護（防別人搬運你）
行動: 無需改變現有模式；若內容被搬運可用官方的原創歸屬機制申訴
來源: about.fb.com/news/2026/03/rewarding-original-creators-on-facebook/

## §plat-13 [official] Meta「Inauthentic Behavior」政策現行版（合規邊界總結）：禁止的是假帳號、隱瞞真實身分、跨帳號協同造假、假互動——在「本人真實帳號」上用 AI 寫貼文、用官方排程工具發布，**皆不在禁止清單**。「AI 學語氣生成 → 本人逐篇確認 → 本人帳號發布」這模式在 2026-07 現行所有條款下合規；四條紅線 = 擬真 AI 影音要標（§plat-02）、別洗 hashtag／圖文不符（§plat-10）、別搬運（§plat-11/12）、別多帳號協同
時間: 政策頁最後更新 2025-12-11；查證日 2026-07
影響: 「每篇人工確認」讓這套流程遠離自動化濫用的灰區；這也是教學頻道可以放心公開教的流程
行動: 保留「人工確認才發布」步驟當作**合規護城河**；避免升級成「全自動無人審發布 + 高頻」——那才開始接近 spam 行為特徵
來源: transparency.meta.com/policies/community-standards/inauthentic-behavior/（updated 2025-12-11）+ Account Integrity 政策頁

# TOPIC: ytai

## §ytai-01 [official] YPP「repetitious content」正式更名為「inauthentic content」：明確化 mass-produced／repetitive 內容不可營利（官方強調是澄清非新政策，reused content 政策不變）
時間: 2025-07-15 生效（2025-07-09 公告）
影響: 教學頻道若每支有真人旁白 + 原創教學結構 = 不在打擊範圍；但若未來量產模板化影片（同結構換皮）會踩線
行動: 維持每支影片有可指出的原創觀點 + 真人旁白；避免同模板大量複製產出
來源: YouTube Help support.google.com/youtube/answer/1311392（2026-07 讀取現行版）+ TechCrunch 2025-07-09 + 官方 Head of Editorial 說明影片

## §ytai-02 [official] Help 頁現行逐字標準：內容須「Be your original creation」且「Not be mass-produced, generic, repetitive, or manipulative」；明文點名不可營利：「AI-generated content made with generic or unoriginal templates giving the impression of mass production without adding the creator's original, authentic insights or perspective」
時間: 現行條文（2026-07 讀取）
影響: **判定核心 = 有沒有「creator's original, authentic insights or perspective」，不是有沒有用 AI**
行動: 每支影片確保可指出的原創貢獻：親自實測、真後台數據（M107）、個人方法論講解——這些都是官方認的 authentic insights
來源: YouTube Help support.google.com/youtube/answer/1311392（原文逐字）

## §ytai-03 [reported] 2026-01 YouTube 依 inauthentic content 政策終止 16 個頻道（合計 35M 訂閱／4.7B 觀看／估年收 $10M）；查無官方逐案公告，屬媒體報導
時間: 2026-01（The Next Web 2026-06-15 報導；多家媒體同數字）
影響: 證明執行是**頻道級（channel-level）死刑**不是單片 demonetize；但被終止的全是純量產 AI slop 頻道，非 AI 輔助教學頻道
行動: 不需恐慌，但注意頻道級判定意味**一批低質影片會拖累全頻道**——別為衝量上模板片
來源: thenextweb.com/news/youtube-ai-slop-crackdown-faceless-creators-collateral-damage（2026-06-15）

## §ytai-04 [official] 年度信把「managing AI slop」列為 2026 優先：加強 spam/clickbait/repetitive 偵測、降低低質 AI 內容能見度、標籤不足時直接移除違規合成內容；同時揭露 >100 萬頻道每日使用官方 AI 創作工具
時間: 2026-01-21 發布（CNBC / THR / Variety 同日報導官方信）
影響: 官方定調 2026 =「AI 工具歡迎、AI slop 打擊」雙軌；低質 AI 內容將被**降能見度**（不只 demonetize）
行動: 把「這支片的人味證據」當交付 gate（真截圖／真實測／真人聲）
來源: 官方 2026 年度信；CNBC 2026-01-21、Hollywood Reporter、Variety 報導

## §ytai-05 [official] YPP 政策再澄清，三類不可營利：(1) generic/repetitive（用 AI/CGI/模板易量產、變化少）(2) unsatisfying/off-putting（情緒操弄型）(3) **AI persona 講敏感題（金融／法律／健康／醫療）**。官方 Trust & Safety 負責人經官方頻道說明：目標是防 content farming，AI 用於 high-quality content 可「enhance creativity」
時間: 2026-07-16 生效（條文已上 Help 頁，含「AI-generated personas to deliver information on sensitive topics」段落）
影響: 教 AI 工具／剪輯教學不在敏感題清單；真人旁白完全不受 AI persona 條款影響
行動: 若未來想做虛擬主持人／AI 化身形式，避開財務／法律／健康／醫療題材；教學題照常
來源: YouTube Help 1311392 現行條文 + Creator Insider + techcrunch.com/2026/07/20/youtube-clarifies-policies-around-ai-slop-and-upsetting-videos/

## §ytai-06 [reported] 附帶傷害：媒體與創作者報告演算法轉向偏好真人出鏡，部分**從未用 AI** 的 faceless 頻道被 demonetize（監測以頻道近期上傳 pattern 判定，報導稱約看最近 30 支）；另有研究稱新帳號前 500 推薦中 21% 為 AI slop——皆非官方確認
時間: 2026 上半年（The Next Web 2026-06-15 彙整）
影響: 有真人聲 + 真螢幕操作 + 真後台截圖的頻道，與 faceless 純 AI 頻道特徵明顯區隔；但「不露臉」本身被降權的說法值得留意（不露臉是很多創作者的既定策略）
行動: 持續在片中放高密度「真人證據」（自己的聲音、自己的操作、自己的數據）；追蹤自家曝光數據若無故驟降再評估
來源: The Next Web 2026-06-15（創作者訪談）；平台未證實

## §ytai-07 [official] 揭露義務【必勾】官方逐字清單：「AI generated music」／「AI generated extra footage of a real place」／讓真人看似說了沒說的話・給了沒給的建議／變造真實事件畫面／逼真但未發生的場景（龍捲風逼近真實城市、公眾人物偷竊、真人被捕）。**核心判準 =「viewers could easily mistake for a real person, place, or event」**
時間: 政策 2024-03-18 上線，現行版 2026-07 讀取無變
影響: 對教學頻道最實際的雷：若用 AI 生成「逼真的真實地點／真實人物」b-roll 必須勾；擬真 AI 音樂也在必勾清單
行動: 合成 b-roll 若走 photorealistic 真實場景路線 → 上傳時勾「Altered content」；風格化 motion graphics 則不用
來源: YouTube Help support.google.com/youtube/answer/14328491（原文逐字，2026-07 讀取）

## §ytai-08 [official] 揭露義務【不必勾】官方逐字清單：明顯不真實（獨角獸／全動畫裡的 AI 飛彈）／美顏・調色・特效濾鏡／「Production assistance, like using generative AI tools to create or improve a video outline, script, thumbnail, title, or infographic」／「Caption creation」／銳化・升頻・修復・音訊修復／「Idea generation」／**「Cloning one's own voice to create voice overs or dubs」**／遊戲畫面／AI 延伸背景模擬移動
時間: 現行條文（2026-07 讀取）
影響: 典型的 AI 協作教學管線幾乎全落在官方明文豁免區：AI 寫稿人唸 = production assistance、AI 剪輯 = production assistance、自動字幕 = caption creation、風格化動態背景 = not realistic、**甚至 clone 自己的聲音都明文不必勾**
行動: 「真人自錄旁白 + 螢幕錄影 + 風格化動畫」= 零揭露義務；唯一要勾的情況 = 擬真 AI 影像／AI 音樂入片
來源: YouTube Help support.google.com/youtube/answer/14328491（原文逐字）

## §ytai-09 [official] 不揭露的處罰官方原句：「Creators who **consistently** choose not to disclose this information may be subject to manual application of a label, or penalties from YouTube, including removal of content or suspension from the YouTube Partner Program」——關鍵詞 consistently = 針對慣犯，非單次失誤即殺
時間: 現行條文（2026-07 讀取）
影響: 單次漏勾不會直接被停 YPP，但持續不勾會
行動: 把「是否含擬真合成內容 → 要不要勾」加進上傳 checklist 一行即可
來源: YouTube Help support.google.com/youtube/answer/14328491（原文逐字）

## §ytai-10 [official] 揭露改為「不勾也會被標」：平台開始自動偵測並自動上 AI 標籤（讀 C2PA metadata + SynthID 浮水印 + 內部偵測）；官方自家生成工具與 C2PA 標記全生成內容的標籤永久不可移除；**官方同時確認：AI 標籤本身不影響推薦與營利資格**；誤標可在 Studio 申訴更正
時間: 2026-05-27 官方宣布、5 月起漸進 rollout
影響: 誠實成本降低：反正會被偵測，主動勾比被動被標好看；也官方背書「有 AI 標籤 ≠ 降權」
行動: 凡有擬真 AI 素材一律主動勾；用官方生成工具做的素材要有「標籤永久」的心理準備
來源: techcrunch.com/2026/05/27/youtube-will-now-automatically-label-ai-videos/ + Variety 2026-05-27

## §ytai-11 [official] 肖像偵測（likeness detection）完整時間線：2024-12 試點 → 2025-09-16 宣布開放全 YPP 創作者 → 2025-10-21 起分批啟用 → 2026-03-10 擴及公職人員／記者 → 2026-04-21 擴及名人 → 2026-05 中擴及所有 18+ 用戶。功能 = 掃描 AI 變造／生成的你的臉，配對後可提 privacy 移除請求或版權請求；需政府 ID + 自拍影片驗證，**資料不用於訓練生成模型，可隨時退出刪資料**
時間: 2025-09-16 至 2026-05（各節點如上）
影響: 已在 YPP 的創作者可（也建議）啟用，防他人用你的臉做 deepfake 詐騙內容
行動: 到 Studio 啟用 likeness detection（18+、頻道 Owner/Manager、ID 驗證約 5 天）
來源: blog.youtube/news-and-events/expanding-likeness-detection-civic-leaders-journalists/（2026-03-10）+ Help support.google.com/youtube/answer/16440338

## §ytai-12 [official] 語音克隆：偵測目前僅臉部，官方 Help 原句「We're working to extend likeness detection to audio in 2026」（截至 2026-07 尚未上線）；被仿聲者現行救濟 = privacy complaint 流程（2024-06 起接受「realistically simulates you」的移除請求）；音樂夥伴另有 2023-11-14 起的合成歌聲下架機制。注意：**偵測 ≠ 必移除**——parody/satire／公共利益內容可能保留，逐案人工審
時間: audio 偵測 = 2026 官方承諾未上線；privacy 流程現行有效
影響: 用 AI 模仿他人聲音（歌手／名人）= 高風險可被下架；**clone 自己的聲音做旁白 = 明文合規且不必揭露**（§ytai-08）
行動: 永不用他人聲音克隆；沿用自己的聲音（含 clone 自己）完全合規。audio 偵測上線後去登記自己的聲音
來源: YouTube Help 16440338（原文）+ 官方 blog 2023-11-14（音樂夥伴機制）

## §ytai-13 [official] AI 音樂：可上傳可營利，但三條邊界：(a) 擬真 AI 音樂在必揭露清單（Help 逐字「AI generated music」）；(b) 量產 AI 音樂頻道踩 inauthentic content（2026 有音樂頻道被 demonetize 的報導）；(c) 模仿真實歌手聲音可被音樂夥伴要求下架
時間: (a)(c) = 現行官方條文；(b) 執行案例 = 2026 陸續報導
影響: BGM 若用 AI 生成放進教學片：技術上屬「AI generated music」→ 保守做法是勾揭露；用授權曲庫 BGM 則無此問題
行動: BGM 維持授權曲庫；若哪天用 AI 生成 BGM，上傳勾 altered/synthetic 一格了事
來源: 官方：Help 14328491；報導：多家分發商 2026 文章（Content ID 收緊部分僅 reported）

## §ytai-14 [official] 第三方 AI 工具邊界：**平台政策看「內容」不看「工具」**——用第三方 AI 工具（語音／音樂／影像／寫作）本身不違規，揭露與營利義務相同適用；另一方向：2024-12-16 起 Studio 有「third-party AI training」開關，你可選擇是否允許第三方 AI 公司用你的影片訓練（**預設關閉**）
時間: 訓練開關 2024-12-16 上線；工具中立原則 = 現行條文一貫
影響: 用 AI 協作剪輯／寫稿完全不構成違規要素；你的影片預設不被第三方拿去訓練
行動: 無需動作；若在意可檢查 Studio 設定確認 third-party training 維持關閉
來源: YouTube Help（third-party AI trainability, support.google.com/youtube/answer/15509945）+ 官方 2024-12 公告

## §ytai-15 [official] 「真人旁白 + AI 輔助」官方定位 = 明確 OK，有三層官方依據：(1) Help 營利頁允許例逐字「Content that expresses your unique creative voice, like using AI to visualize a unique character and narrative you invented」「Content that utilizes creative tools to assist in delivering a unique, well-researched, or creative narrative」；(2) 揭露頁把 AI 寫稿／大綱／縮圖／字幕／剪輯輔助全列為不必揭露的 production assistance；(3) 官方口徑三連：2025-07「not a crackdown on AI, channels using AI remain eligible」→ 2026-01 年度信歡迎 AI 工具 → 2026-07-16「AI can enhance creativity」
時間: 條文現行（2026-07 讀取）；官方表態 2025-07 / 2026-01 / 2026-07-16
影響: 「AI 寫稿人唸 + AI 剪輯 + 合成動態背景 + 螢幕錄影教學」= 官方明文安全區，**前提是有 creator 原創洞見**。唯一沒有的東西 = 官方從未承諾「用了真人旁白就免死」——判準始終是整體原創價值，不是配了人聲的量產片就安全
行動: 合規現狀 = 綠燈照常產出；守住三條線：不量產模板片、擬真 AI 素材就勾揭露、AI persona 不碰財務／法律／健康／醫療
來源: YouTube Help 1311392 + 14328491（原文逐字）+ TechCrunch 2025-07-09 / 2026-07-20 + 2026-01 年度信

---

→ 規則本體（R26-R38 + 發布前 checklist）回 [ai-content-compliance.md](ai-content-compliance.md)
