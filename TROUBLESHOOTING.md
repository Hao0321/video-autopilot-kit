# TROUBLESHOOTING

## ❗ 剪出來的成品「畫面對不上字幕/旁白」(最常見)

**症狀**：跑 `auto_sequence_brolls()` / b-roll 自動排序後，影片裡的畫面跟旁白在講的東西不一致。

**原因**：b-roll 對位靠「字幕內容 ↔ 素材」配對。配對有兩條路：

1. **filename↔caption 對位（預設，零設定）** — 把 b-roll **用內容命名**就會自動對上：
   - ✅ `coffee-pour.mp4`、`studio-homepage.mp4`、`gameplay.mov`、`sunset-beach.mp4`
   - ❌ `IMG_0423.mp4`、`clip01.mp4`、`a3f9c.mp4`（UUID / 流水號 = 無法對位 → 亂填）
2. **keyword_map（進階，自訂主題）** — 傳你自己的主題表：
   ```python
   MY_MAP = {
       "cooking": {
           "caption_keywords": ["recipe", "cook", "ingredient", "煮", "食材"],
           "broll_keywords":   ["kitchen", "pan", "stove", "廚房"],
           "topic_label": "Cooking",
       },
   }
   auto_sequence_brolls(captions, brolls, total_us, keyword_map=MY_MAP)
   ```

> ⚠️ 不要傳內建的 `HAO_CAPTION_KEYWORD_MAP`（= `EXAMPLE_KEYWORD_MAP`）當你自己的 —— 那是原作者的主題範例（Studio / 遊戲 / 玩家系統），你的內容不會 match，反而干擾。**留空用 filename 對位，或抄它的結構寫自己的。**

### 輸入合約（input contract — 沒符合就一定對不上）

| 項目 | 要求 |
|---|---|
| **captions** | 每段要有**真實的** `start_us` / `duration_us`（從旁白時間軸來，例如 CapCut 自動字幕產生的）。沒有真時間 = 無時間軸可對齊 |
| **b-roll** | 用**內容命名**（見上）；fps 先 `batch_normalize_broll_folder()`（`from silent_vlog_maker import batch_normalize_broll_folder`）對齊 timeline（預設 30）；去掉背景音 |
| **語言** | filename 對位**語言無關**（中/英/CJK 都可）；keyword_map 才需配語言 |

### 自我診斷

```python
from capcut_helpers import match_brolls_to_captions
m = match_brolls_to_captions(captions, [b["id"] for b in brolls])
for x in m:
    print(f'{x["score"]:.2f}  {x["caption_text"][:30]!r} -> {x["best_broll"]}')
# 多數 score < 0.3 = 沒對上 → 改檔名 或 給 keyword_map
```
跑 `auto_sequence_brolls()` 時若大量片段沒對上，會直接 `RuntimeWarning` 提醒你。

---

## 其他

- **播放速度怪 / 畫面卡格** → 素材 fps 跟 timeline 不符。先 `from silent_vlog_maker import batch_normalize_broll_folder; batch_normalize_broll_folder(folder)`（對齊 30fps + 去音）。
- **匯出後字幕時間軸對不上 player 顯示** → 用 `reencode_player_safe()`（player-friendly profile）。
- **CapCut 自動化沒反應** → 確認 AI 助手的 **Computer Use 有開**（CapCut 沒 API，靠 AI 操作 GUI）。見 README「需求」。
- **`import` 就報錯** → 確認用的是 v0.2.2+（早期版本在淺 checkout 會 IndexError）。
