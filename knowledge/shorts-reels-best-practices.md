> 來自 video-autopilot-kit 開源知識庫 · MIT 授權

# Reels/Shorts 2026 實證最佳做法（web 學習 2026-06-01）

> data-backed，不是感覺。每條都對應自動剪輯 pipeline 的 helper。
> **本檔＝呈現層**（字幕樣式／hook 寫法／安全區）。
> **結構層（片長／首刀／loop／常駐識別／續看率判讀）→ [shorts-mastery-2026.md](shorts-mastery-2026.md)。**

## 1. 字幕風格（caption）
| 研究發現 | 數字 | 落地 helper |
|---|---|---|
| **逐塊 2-3 詞顯示 + active word 高亮**（變色/放大）= 最高影響力字幕特徵 | 78.6% 爆款會動畫字幕 | `chunk_caption()` + `style_chunks_active()` |
| 字級寧大勿小（mobile 下限 ≈24-32pt）| — | `SHORTS_SAFE_ZONE["min_font_px"]=60` |
| 粗黑 sans + 黑框/黑底 = legibility 金標準 | — | NotoSansTC-Black + 黑描邊（`render_caption_png`）|
| 字幕跟旁白同步誤差 | <100-200ms | 逐塊 reveal 照 voice timing 切 |

## 2. Hook（前 3 秒）
| 研究發現 | 數字 | 落地 |
|---|---|---|
| 前 3 秒決定一切 | **80% 完讀率變異** / 過 3 秒留 60%+ 才會被推 feed | `render_hook_card()` 0-3s |
| 3 大跨 niche viral formula | 反差宣稱 / 踩雷警告 / 清單預告 | `HOOK_FORMULAS` + `suggest_hook()` |
| hook 長度 | 10-14 字 | 寫腳本守則 |
| niche 修正 | 教學可 +5-10s / 娛樂要 1-2s 快切 | 路由時調 |

> **2s 和 3s 不矛盾，是兩件事**：
> **2 秒 = hook「落地」門檻**（結構層 S-C：第一刀必須在 2.0s 前發生，觀眾要在 2 秒內知道「這是什麼、為什麼看下去」）。
> **3 秒 = 留存「讀數」窗**（呈現層：平台用前 3 秒留存當主要排序訊號，滑掉率也在這個窗算）。
> 換句話說：**2 秒內把 hook 做完，才有機會讓 3 秒的讀數好看**。先過 2s 結構關，再談 3s 數據關。

## 3. 安全區（position）
| 研究發現 | 數字 | 落地 |
|---|---|---|
| 避開上 20%（標題/頻道）+ 下 25%（讚/留言/分享鍵）| 出界 → 觀看時數 **-22%** | `SHORTS_SAFE_ZONE` + `safe_caption_y()` |
| 字幕放中下三分之一 | caption_y≈1180 / hook 上中 central 60% | 同上 |
| 通用安全框 | 900×1400 居中於 1080×1920 | — |

## 4. 為什麼字幕非加不可
- 50-80% 短影音**靜音觀看** → 沒字幕等於隱形
- 加字幕的 Reels 前 48h reach **+15-25%**

---
## Sources
- [OpusClip — YouTube Shorts Caption Best Practices 2026](https://www.opus.pro/blog/youtube-shorts-caption-subtitle-best-practices)
- [OpusClip — Why Viral TikToks Use Captions (80.2%/78.6%)](https://www.opus.pro/blog/why-viral-tiktoks-use-captions)
- [OpusClip — Shorts Hook Formulas (3-sec holds)](https://www.opus.pro/blog/youtube-shorts-hook-formulas)
- [Terra Market — 7 Hook Formulas for 70%+ Retention](https://www.terramarketgroup.com/digital-marketing-2/short-form-video-hooks-7-formulas-for-70-retention/)
- [Kreatli — YouTube Shorts Safe Zone 2026](https://kreatli.com/guides/youtube-shorts-safe-zone)
- [Blitzcut — TikTok Caption Styles 2026](https://blitzcutai.com/blog/best-caption-style-tiktok)
