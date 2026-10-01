# YouTube Hype Button — 制度化發布動員 SOP

> 來自 video-autopilot-kit 開源知識庫 · MIT 授權

> YouTube Hype button 先在少數國家以 beta 形式推出、之後分批擴大（名單會變，發片前自己確認一次）。若你所在地區已開放，這是小頻道少見的演算法槓桿。
> 來源：[YouTube Blog](https://blog.youtube/news-and-events/youtube-hype/) | OutlierKit 2026 Analysis

---

## 為什麼 Hype 對小頻道是 unfair advantage

| 條件 | 為何重要 |
|---|---|
| **地理 beta** | 功能只在少數國家開放，多數創作者根本沒得用 |
| **頻道規模在合格區** | 落在 500–500K subs 區間才合格 |
| **小頻道 multiplier** | hype 對小頻道的權重比大頻道更大 |
| **可動員社群** | 有一個願意行動的鐵粉池（Discord / 群組 / 電子報），是多數人沒有的籌碼 |
| **每週 hype 上限** | 每人每週 3 次 → 鐵粉人數 × 3 = 理論週可動員的 hype 總量 |

→ 當平台 Browse 流量對長片大幅縮水時，Hype Country leaderboard 上版 = **Explore 額外曝光，繞過 Browse** 的補救路徑。

---

## Hype 規則

| 規則 | 細節 |
|---|---|
| 創作者合格 | 500 – 500K subs |
| 觀眾合格 | 任何登入用戶 |
| 每人 hype 上限 | **每週 3 次** |
| 影片合格窗口 | **上傳後 7 天內** |
| Leaderboard | 國別排行（Country leaderboard） |
| 加成 | 小頻道有 multiplier |
| 成本 | 完全免費 |

---

## 標準動員 SOP（每片發布跑一次）

### T+0（發片當下）

1. **YT 發布** → 在 community/comment 區自己 pin 一則「來幫我 hype」+ 連結到「怎麼 hype」教學
2. **社群公告頻道** 發文（範本）：
   ```
   📢 新片上架 — 來幫我 hype 上 Country leaderboard
   [影片連結]

   🔘 為什麼要 hype：你所在地區是 beta 國，hype 可以讓影片上 Country 排行，
      推給更多沒看過這個頻道的新人 — 大家直接受益
   🔘 怎麼 hype：[1 張截圖教學]
   🔘 限制：每人每週 3 次，影片 7 天內有效
   🔘 我會在社群公告達標進度
   ```
3. **其他社群管道**（群組 / 電子報）同步發（精簡版 + 連結）

### T+1h（首批反應期）

- 看公告 thread 回應數
- 個別感謝前 10 個 hype 的人（強化下次參與意願）

### T+24h（最關鍵 retention window）

- 看 YT Studio 的 1-min retention，跟**你自己的門檻**比：達標 `<fill in>` ✅ / 明顯低於 `<fill in>` ⚠️
- **達標 → 進入 T+48h 二次推力**
- **明顯低於門檻 → kill，不浪費 hype 子彈在 dead 片上**（hype 是稀缺資源）

> 📏 **這兩個門檻本檔不給數字。** 1-min retention 是後台讀數，沒有出處的具體值＝某個人的 Studio 讀數
> （規矩 → [`viral-playbook-framework.md`](viral-playbook-framework.md) 檔頭第 1 類）。
> **量法**：取近 3-5 支同型片的 1-min retention，取中位數當「達標線」、取沒被演算法接走那幾支的水位當「警戒線」。
> 樣本 <5 支就只當 checklist，別真的拿它 kill 一支片。
> **更穩的讀法是相對比較**：這支的 1-min retention 對照**你自己前幾支**是高是低 —— 動員決策看趨勢，不看絕對值。

### T+48h（Hype 第二波）

- 二次推：「retention 達標 + impressions 起飛了，最後 5 天衝 leaderboard」
- 提示「上週還沒用完 3 次的人」（hype 是週重置）

### T+7d（窗口關閉前）

- 最後 12h call：「今晚 11:59 hype 窗口關，最後一波」
- 公告達標數字 + 上 leaderboard 截圖（社群榮譽感 → 下次更願意推）

---

## 反 pattern（不要做）

| ❌ 反 pattern | Why |
|---|---|
| 每片都用同一套文案發社群 | 鐵粉會疲勞 → 參與率下降 |
| 影片 retention 明顯低於你自己的門檻還 push hype | 浪費社群子彈 + 算法看到 hype 但 retention 爛 = 反向訊號 |
| Hype 但沒在影片裡兌現質量 | 信任崩塌 — 下次發片沒人理 |
| 多片同時 push hype | 鐵粉每人每週上限 3，分散 = 哪片都不夠強 |
| 用「拜託」「求」這種語氣 | 把 hype 變成乞討 — 改成「**這對你也有好處 — 頻道更多新人 = 更多技術討論 / 社群成長**」 |

---

## 與 retention / packaging 工作流整合

- **Pre-flight（拍前 checklist）** → 確認是 hype-worthy 題目（top 1% filter 過）才動員，不浪費子彈
- **Analytics（數據判讀）** → T+24h/48h 看 retention 決定要不要二推
- **Iteration（事後迭代）** → 若 hype 推完還是冷，T+7d 換 thumbnail/title（不是再 push hype）
- **發文頻率** → 1 長片/週用 hype 最有效；多片同週 hype 會稀釋

---

## 與其他 external traffic 槓桿配合

| Channel | 時機 | 動作 |
|---|---|---|
| 主社群（Discord / 群組） | T+0 / T+48h / T+7d | Hype CTA + 影片連結 |
| 次社群（電子報 / 群組） | T+0 / T+48h | Hype CTA + 影片連結 |
| 演講 / 線下場合 | 場後 24h | 「掃 QR → 看影片 → 分享社群拿資源」（external share = 高 satisfaction 訊號） |
| 個人社群帳號（Threads / X 等） | T+0 + T+24h | 影片 highlight clip + 連結（自然觸及） |

→ Hype 是 beta 地區特權；其他 external traffic 是 cross-platform 通用

---

## 監控 + 學習

每片跑完 SOP 後，在你的 video log Outcome 區補：

```
### Hype 動員實績
- 社群公告觸及：[reach]
- 估算 hype 數：[count]
- Country leaderboard 排名：[rank or N/A]
- T+48h retention：[%]
- 來自 hype 的 impressions（YT Studio Traffic source: External）：[#]
- 學到什麼：[note]
```

累積 3–5 片後 → 跑 retrospective 比對 hype 是否真的有效（vs 沒做 hype 的對照組）。
