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

## 🚦 Ship-ready QA — 影片 ship 前自檢（v0.3.0, canon M91–M95）

每支影片 export 後、**還沒 call 它「完成」之前**，跑一次：

```python
from capcut_helpers import final_delivery_qa
final_delivery_qa("FINAL.mp4", voice="voice.wav", contact_out="qa_contact.png")
# [OK]/[WARN] 機械驗 M93 頻閃 + M95 死空檔；接觸表逐格用眼睛看 M91/M92/M94/M68
```

這套是從「同一支片被觀眾抓出 8 輪問題」提煉的 —— **每一條都該剪輯的人自己抓，不是讓觀眾抓**：

| # | 檢查 | 怎麼抓 | helper |
|---|---|---|---|
| **M91** chrome/隱私 | 螢幕錄影/截圖洩漏作業系統外框：工作列、檔案管理員側欄（你的磁碟結構！）、瀏覽器分頁、**後台金額頁（financial dashboards）** | 裁到只剩內容區 + 抽幀逐格看 | `contact_sheet` |
| **M92** 圖片排版 | 非滿版圖用了死黑邊 / `zoompan` 抖動 / 整個視窗外框 | 模糊背景填滿 + 靜止 + 裁內容區 | `still_blurfill` |
| **M93** 頻閃 | 頻閃素材（動作遊戲爆擊 / strobe）或亮度落差 | `blackdetect` 抓「黑↔亮」反覆 | `detect_flash` |
| **M94** 真實 artifact | 旁白點名具體東西（時間軸 / 原始素材 / 上一支影片）卻配 generic stock | 給**真實該物**的畫面 | — |
| **M95** 句間死空檔 | 錄音句子之間停 3–4 秒拖節奏 | `silencedetect` 抓 >1.5s；剪到 ~0.5s | `detect_long_pauses` |

**M95 三軌同步剪死空檔**（人聲 / 畫面 / 字幕用同一組 cut）：
```python
from capcut_helpers import (detect_long_pauses, trim_dead_air_ranges,
                            cut_audio_segments, cut_video_segments, remap_time)
cuts = trim_dead_air_ranges(detect_long_pauses("voice.wav"), keep=0.5)
cut_audio_segments("voice.wav", "voice_cut.wav", cuts)     # ⚠️ atrim+concat（aselect 對音訊常不剪）
cut_video_segments("visual.mp4", "visual_cut.mp4", cuts)   # select+setpts
# 字幕：每個 block.start/end = remap_time(t, cuts)
```

---

## 其他

- **播放速度怪 / 畫面卡格** → 素材 fps 跟 timeline 不符。先 `from silent_vlog_maker import batch_normalize_broll_folder; batch_normalize_broll_folder(folder)`（對齊 30fps + 去音）。
- **匯出後字幕時間軸對不上 player 顯示** → 用 `reencode_player_safe()`（player-friendly profile）。
- **CapCut 自動化沒反應** → 確認 AI 助手的 **Computer Use 有開**（CapCut 沒 API，靠 AI 操作 GUI）。見 README「需求」。
- **`import` 就報錯** → 確認用的是 v0.2.2+（早期版本在淺 checkout 會 IndexError）。
