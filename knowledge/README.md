# 📚 Knowledge Base — 影片製作知識庫

> 從實戰剪輯踩坑提煉的**通用心法、SOP、演算法洞察**。MIT 授權，自由取用 / 修改 / 商用。
> 個人資料（作者身份、社群、頻道數據、真實片名/地址、個人腳本風格）已全部移除 —— 這裡是**可複用的方法論**。

這是 `video-autopilot-kit` 的「心法層」：`src/` 給你工具（code helpers），`knowledge/` 給你**怎麼用得好**。

## 🏆 避坑大全（先讀這個）
- **[meta-lessons.md](meta-lessons.md)** — M1-M111 影片製作避坑大全。每一條都是「我犯過這個錯 + 永久解法」：看畫面才寫字幕、不編造、chrome/隱私洩漏、圖片排版、頻閃、句間死空檔、Shorts BGM 抓高光、忽大忽小壓平、self-test 別 mock 掉外部工具、自錄螢幕素材重錄>事後裁、Windows cp950 redirect 炸 build、長片 pro 音訊鏈(acompressor+sidechain duck+two-pass loudnorm+room-tone)+旁白加速時間軸同步、上鏡數據只用真後台截圖(M107)…**檔尾另有 §Shorts 結構教訓 S-A~S-L（機械標籤，定義以 `shorts_gate.py` 為準）＋ S-M/S-N（人工項）**

## 🤖 自動化工作流
- [autopilot-workflow.md](autopilot-workflow.md) — 一句話題目 → 完整影片套件的 9 步工作流
- [shorts-reels-best-practices.md](shorts-reels-best-practices.md) — 2026 Shorts/Reels 字幕/hook/安全區 SOP（呈現層）
- [shorts-mastery-2026.md](shorts-mastery-2026.md) — 直式短片**結構層**：片長雙峰（**平台感知**）/首刀 ≤2s/真 loop/常駐識別 + S1-S12 研究基準 + S-A~S-L 剪輯鐵則（＋ warn 級 S-O 換句節奏、人工項 S-M/S-N）+ 續看率判讀（門檻自填）
- [vertical-teardown-method.md](vertical-teardown-method.md) — **怎麼拆競品的直式短片**：可複製的量測步驟（ffmpeg scene detect 量刀速／裁字幕帶量換句速率／ASR 量語速＋踩過的坑）→ 三種節奏原型、字體由背景亂度決定、貼文骨架、CTA 型態，以及**為什麼片長死區不可跨平台套用**。附樣本邊界誠實聲明（n=7、全成功樣本、無失敗對照組）
  - 機械層 → [`../src/teardown.py`](../src/teardown.py)：`python src/teardown.py <影片檔或資料夾>` 一次跑完刀速／刀距分布／換句速率／換句÷剪點／LUFS（OCR 選配，缺了只降級不崩潰）；統計那半邊零依賴 → `python examples/06_teardown.py`
- [interview-show-playbook.md](interview-show-playbook.md) — 線上訪談節目生產線：邀約→7 件套→分軌錄製→剪輯→包裝，六條鐵則 +「合規章只能由人蓋」的閘門設計（`src/interview_autopilot.py`）

## 📊 YouTube 演算法
- [youtube-algorithm-overview.md](youtube-algorithm-overview.md) — 演算法 5 模式總覽（拍前 / 留存 / 封裝 / 數據 / 迭代）
- [youtube-algorithm-mastery.md](youtube-algorithm-mastery.md) — 深度 + MrBeast 戰術 + 留存工程 + **§2b 雙機器作戰模型**（推薦機 vs 搜尋機：形狀 / 壽命 / 判讀指標 / 兩張清單 + 用你自己 3-5 支片校準門檻的 SOP）+ **§2「48h vs day-14」判死時序**（本 kit 單一真值來源）
- [youtube-algorithm-2026.md](youtube-algorithm-2026.md) — 2026 演算法洞察（多軌創作者通用版，R15-R25）
- [ai-content-compliance.md](ai-content-compliance.md) — **AI 內容合規 R26-R38 + 發布前 10 項 checklist**：擬真判定 gate / 原創貢獻 / 防模板化 / **深偽三不（刑法級紅線）** / 語音克隆只准 clone 自己 / metadata 不洗標 / **只引用有官方出處的數字**。⚠️ 截至 2026-07 的整理，各地法規不同，商業用途請找當地專業人士
- [ai-content-compliance-sources.md](ai-content-compliance-sources.md) — 53 條分級法源（`[official]` / `[reported]` / `[speculative]`，含穩定 `§xxx-NN` 錨點）。**查證用附錄，日常不必讀**
- [teaching-niche-playbook.md](teaching-niche-playbook.md) — 教學頻道 niche 經營 playbook
- [launch-hype-sop.md](launch-hype-sop.md) — 發布 hype / 社群動員 SOP（鐵粉池槓桿）

## 📱 跨平台剪輯心法
- [video-craft-overview.md](video-craft-overview.md) — 剪輯技法總覽（4 模式 + 7 大技法）
- [video-craft-playbook.md](video-craft-playbook.md) — 跨平台 repurpose + 留存診斷
- [ig-caption-patterns.md](ig-caption-patterns.md) — IG caption / hook 公式
- [viral-short-playbook.md](viral-short-playbook.md) — 病毒短片結構

## 🎬 CapCut 自動化 SOP
- [capcut-automation-sop.md](capcut-automation-sop.md) — CapCut GUI 自動化（agent 操作 SOP）
- [capcut-agent-brief-template.md](capcut-agent-brief-template.md) — agent brief 6 區塊模板
- [capcut-text-templates.md](capcut-text-templates.md) — 花字 / 文字模板目錄
- [capcut-json-direct-edit.md](capcut-json-direct-edit.md) — CapCut draft JSON 直接編輯
- [capcut-pro-paywall-map.md](capcut-pro-paywall-map.md) — CapCut Pro paywall 地圖
- [programmatic-video-build.md](programmatic-video-build.md) — 純 ffmpeg 端到端 pipeline
- [agent-token-efficiency.md](agent-token-efficiency.md) — agent token 效率心法

## ✍️ 腳本（三支柱：語氣／觀眾語言／留存節奏）
- [script-style-framework.md](script-style-framework.md) — **支柱 1 語氣**：學「自己腳本風格」的 4-mode 框架（你填自己的 profile，不是套別人的聲音）
- [script-retention-craft.md](script-retention-craft.md) — **支柱 2＋3**：觀眾語言四層詞表**怎麼從自己的逐字稿建**（詞表隨 kit 出貨是空的，刻意的）＋ 留存節奏 craft（hook 三件套／loop 開關／payoff 密度／一口氣測試／次好開場最好壓軸）
- 填空骨架 → [`../templates/style_profile.template.md`](../templates/style_profile.template.md)（含詞表審計工作表）＋ [`../templates/audience_vocab.example.json`](../templates/audience_vocab.example.json)
- 機械層 → [`../src/longform_maker/script_gate.py`](../src/longform_maker/script_gate.py)：錄音前 `gate(text)`，觀眾語言 fail 級／節奏 warn 級

- `premium-motion-fx.md` — premium motion design: exact easing/bloom/SFX/grade parameters + the deliberately-skipped list (wave 1-3 upgrade plan).

- `viral-playbook-framework.md` — 爆款定義三層（機器點火二元判定 / ≥3× Expected Views 快篩 / CTR×AVP 雙門檻 AND）+ Shorts 等價指標 + 六站命中率系統 + **對抗驗證方法論（CONFIRMED / PLAUSIBLE / REFUTED 三級標示 + 五種攻擊 + 分級表範本）**
- `ops-automation.md` — 懶人自動化經營接線：tracker + 健檢 + 三道閘門 + 每日 AI 排程巡檢（v0.9）
