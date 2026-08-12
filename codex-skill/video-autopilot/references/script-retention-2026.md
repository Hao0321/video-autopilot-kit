# 腳本三支柱＋留存節奏（M110 SoT）

> 2026-07-24 Hao：「以後寫腳本除了用我的語氣外，還要符合觀眾語言，要良好的節奏讓人一直看下去」
> 三支柱 = **語氣（M101 voice profile）＋觀眾語言＋留存節奏**。缺一柱的腳本不交付。
> 機械層 = `longform_maker/script_gate.py`（觀眾語言 fail 級／節奏 warn 級，self-test 36 項）。
> 本檔 = 詞表真相來源 + 不可機械化的 craft 規則（寫稿時人工套）。

---

## 支柱 2：觀眾語言（36 篇樣本逐字審計，2026-07-24 workflow 實查）

**鐵則：旁白只准用「路人 0.5 秒懂」或「Hao 樣本已驗證」的詞。** 包裝層（標題/縮圖）更嚴 → 演算法 supplement 觀眾語言鐵則。

### 詞彙四層（機械執行 in script_gate）

| 層 | 意義 | 例 |
|---|---|---|
| SPOKEN_OK | 樣本實證觀眾買單，可直接講 | AI(22篇)/Discord(7)/App(7)/OK(6)/bug(4)/YouTube/Shorts/GPT/Line/IG/Vibe Coding/VPN/Hook/Loop/CP值/XD…；GitHub=長片01-03 內容線新驗證 |
| SUBSTITUTE | **有 Hao 原生中文詞 → 英文=fail** | prompt→**提示詞**（樣本 19 篇 vs 英文 0 次）/ workflow→**流程・工作流** / demo→**示範・操作給大家看** / deploy→**部署** |
| NEED_PAIR | 可講但同 beat 要白話同伴詞 | QA↔品管・抓錯／fork↔回去改・複製／repo↔GitHub・開源・專案／debug↔修・找問題 |
| HARD_BAN | 內部工程詞永不上旁白 | assert/LUFS/pipeline/schema/regex/refactor/commit/gate… |

新詞先落 `lang.unknown_term` warn → 人工判級 → 入表。**判級標準：不是「我圈子懂不懂」，是「他樣本講過沒＋路人 0.5 秒懂不懂」。**

### Hao 的術語消化句式（樣本實抓 6 式，ghost-write 直接套）

1. **術語→超白話翻譯**：「Vibe Coding…就是出一張嘴來開發自己的APP」（#22）
2. **白話現象→最後命名**：「這個過程我們就叫做流程」（#31，教學定義式）
3. **英文功能名＋括號中譯＋能做什麼**：「Extend(延展)…可以讓影片加長，一次加長4秒」（#34）
4. **冷門詞→「他是一種…的效果」**：珮珀爾幻象（#14）
5. **縮寫→類比收尾**：「AMA…有點像Clubhouse的功能」（#27）
6. **平台黑箱→拆時間＋條件兩層**：「評分機制…大約發佈後5~8小時…看互動跟完撥率」（#35）

### 反向鐵證（樣本 0 次 = 嫌疑犯）

英文 prompt／demo／workflow／開源*／GitHub*＝舊 corpus 0 次。（*開源/GitHub 已被長片01-03 AI-coding 內容線上鏡驗證，白名單保留；其餘照 SUBSTITUTE 走。）他的英文停在**單詞層級**（bug/OK/Hook/XD），從無整句英文。

---

## 支柱 3：留存節奏（2026-07 研究 18 條收斂；13 條已機械化）

> 來源=creator-tool best practice 宣稱（PrePublish/Humble&Brag/River/Overseeros/AWAI/South Park but-therefore），數字當方向性參考非精確值。字速前提：中文口播 240-280 字/分（gate 用 260）。

### 已機械化（script_gate 自動跑，別再靠記憶）

- **R24 cold open**：前兩段禁自介打招呼、第一段要結果詞（既有）
- **Hook open loop**：前兩段要懸念訊號（更扯/連…都/其中/？）— `rhythm.hook_no_open_loop`
- **Interrupt ≤90s**：問句/數字/轉折的最大間距（既有 M95 家族）
- **Re-hook 落點 25/50/75%**：`interrupt_schedule` 自動排（8min+ 中段那發不可省）
- **Beat ≤45s**：超過要新 payoff/新視覺或拆 beat — `rhythm.beat_too_long`
- **每中段 beat 要動能詞**：但/結果/所以/直接/最X的是…或問句 — `rhythm.no_momentum`
- **前 90% 禁總結感詞**：總之/總結一下/以上就是/回顧一下 只准片尾 — `rhythm.mid_closing_tone`
- **句長高變異**：160+ 字 beat 全長句＝沒打點 — `rhythm.no_punch`（≤14 字短句=punch；Hao 長句連珠砲是招牌，門檻已校準不誤傷）
- **But/Therefore 鏈**：段首 然後/接著/再來/另外 >2/min＝流水帳 — `rhythm.andthen_chain`
- **Outro 三件套**：訂閱＋自由工坊（既有）

### 人工 craft（寫稿時套，gate 驗不了）

1. **Hook 三件套 15 秒內**：確認點擊（重述標題承諾）→ 開 curiosity loop → 一句 credibility；**hook 永遠正文寫完才回頭寫**
2. **Hook 一句一拍**：hook 段子句短打（中文 ≤15 字/拍），別用 30 字長句開場
3. **主 loop 遠距回收**：hook 埋「這個X最後我會給你完整答案」型明說懸念 → 回收放最後 1/3；**開了必關**（沒回收=詐欺感）
4. **Micro-loop 本 beat 回收**（≤2 分鐘），只有主 loop 可跨段；任何時刻至少 1 個 loop 未關（關一個前先開下一個）
5. **Payoff 密度 60-90s**：每 60-90 秒給一個可帶走的具體東西（新結論/新數字/新示範結果），不能連續兩分鐘鋪陳
6. **資訊密度呼吸**：600 字窗內 ≥6 個新概念且無例子/故事緩衝＝過載 → 插 breathing room；密集段與呼吸段交替
7. **時間錨定 micro-promise**：「接下來 30 秒你會看到它實際怎麼跑」— 把長片切成心理短衝刺（要兌現）
8. **一口氣測試**：單句 ≤35-40 字，唸不完就拆
9. **價值排序**：第二強的點開場、最強壓軸、中間由弱到強爬升
10. **結尾三步**：扣回本片 → 開新 curiosity gap 導下一支 → 只推一個動作；初稿完成整體砍 20-25%（lean 偏好）再定稿

---

## 交付流程（三支柱怎麼跑）

寫稿：載 M101 voice profile → Mode D 起稿（套上面 craft 規則+句式）→ lean 砍 20-25% →
`script_gate.gate(text)` **PASS 才交付**（語言 fail 擋死；rhythm warn 逐條人工過目，能修就修）。
腳本檔格式：旁白正文＋`>` 開頭註記行（gate 自動忽略 blockquote，不算時長不掃詞）。
