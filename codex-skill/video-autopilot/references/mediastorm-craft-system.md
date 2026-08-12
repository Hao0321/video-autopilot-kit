# 影視颶風電影工藝系統

`mediastorm_craft.py` 把影視颶風基準從一句「像它一樣流暢」改成可執行、可降級、可驗收的工藝計畫。長片與 Shorts 都要走同一組真實性規則；差別只在壓縮程度與鏡頭停留，不在是否能亂用轉場。

## 來源與事實邊界

一手來源：

- [官方後期流程：月更10期？！影视飓风用什么做视频？](https://www.bilibili.com/video/BV1mv411e7DE/)
- [官方課程介紹：影视飓风首套视频创作课程！](https://www.bilibili.com/video/BV1fm5ezEEbE/)
- [官方 YouTube 頻道](https://www.youtube.com/@mediastorm6801)

官方公開內容支持「完整後期是多工具、多環節工作流」「調色前要先有具調整空間的素材」「剪輯、音樂與音效設計是獨立工藝」。至於每一刀、每一種轉場的內部公式並未公開；本系統對公開成片的鏡頭與節奏拆解一律標為 `observable inference`，不能冒充內部 preset。

2026-08-13 對官方頻道三種題材各取前 90 秒做低解析度 histogram cut proxy：產品評測 `AGCTmwYpfhI`、訪談紀錄 `N3HwwoX_TXw`、旅遊紀錄 `_gMQLacmj7c`。三者的 proxy median shot 約為 4.04／2.14／2.30 秒，且片頭 20 秒的切點密度明顯不同。結論不是「固定每 2 秒一刀」，而是題材、proof 密度與敘事任務決定速度。

## 八個評分軸

1. 故事能量波：promise、build、breath、payoff 能否辨認。
2. 鏡頭覆蓋與運鏡動機：wide／medium／detail／reaction 是否回答同一件事。
3. 連續性與轉場動機：方向、視線、動作、尺度、位置與遮擋是否成立。
4. 聲畫整合：對白／同期／環境／foley／音樂是否有層級，J/L-cut 是否真的有乾淨音訊。
5. 調色與 shot match：input transform、曝光白平衡、鏡頭匹配、look、output transform 是否分離。
6. 資訊圖形：只解釋尺度、流程、位置、測量與比較，不搶主體。
7. VFX 合成真實性：track、matte、透視、模糊、光影、遮擋、grain 是否一致。
8. 克制與 payoff 可讀性：最重要的證據是否獲得乾淨停留。

量表位於 `knowledge/mediastorm_craft_benchmark.json`，總分 100，90 通過；任何硬 blocker 直接維持 REVIEW／BLOCKED。

## 轉場證據契約

| 手法 | 必要證據 | 缺少時 |
|---|---|---|
| clean cut | 資訊／動作／情緒改變 | 保留 clean cut |
| J-cut | incoming clean audio＋下一場聲音有動機 | clean cut |
| L-cut | outgoing clean tail＋尾音仍有語意 | clean cut |
| cut-on-action | 兩鏡 action continuation＋方向一致 | clean cut |
| match cut | subject anchor＋scale/shape＋semantic relation | clean cut |
| foreground wipe | 真前景遮擋 >70%＋出入方向一致 | clean cut |
| whip-pan cut | 兩鏡真 whip＋同方向＋motion blur cover | clean cut |
| speed-ramp cut | high-fps＋motion peak＋仍看得清主體 | cut-on-action；仍缺證據再 clean cut |
| graphic match | 共用資訊 anchor＋圖形有資訊功能 | clean cut |
| short dissolve | 時間／情緒跳躍＋低動作邊界 | clean cut |

`visual_director.py` 在只有腳本、還沒取得 shot-pair 證據的階段，會記錄 requested transition，但一律選 `clean_cut`。素材掃描與 fine-cut 階段補齊證據後，才可重新呼叫 `resolve_transition()`。

## 特效與轉場要分開

- tracked label、object sheen、美元粒子、HUD 是 overlay，不是轉場。
- 轉場必須連接兩顆真鏡頭；只有一顆 shot 就不准叫 match／whip／occlusion cut。
- 光效若只強調主體，走 tracked matte；若要藏 cut，必須同時證明 cut point、遮擋或亮度匹配。
- 3D 先走 `three_d_system.py` 的 capability gate；缺 mesh／camera／plate 就不得把 2D 貼片稱為真 3D。

## 聲音與調色

聲音優先序固定為：對白／同期 → production sound → room tone → specific foley → music。禁止每刀配 whoosh。payoff 前可以降低音樂，落點使用真 sync sound、特定 impact 或刻意靜默。

調色順序固定為：input transform → exposure／white balance → shot match → one restrained look → output transform。LUT 只是可能的 look 工具，不是修復霧感、曝光或白平衡的捷徑。

## 驗證

```powershell
python mediastorm_craft.py selftest
python visual_director.py --duration 60 --format longform --genre product
python system_health.py --quick
```

最後仍需 Hao 看成片：鏡頭動機、聲音的情緒、調色的品味與轉場「剛剛好」不能由機器綠燈代替。
