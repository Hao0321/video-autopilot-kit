# Knowledge Lifecycle

## 目標

讓自動剪輯真的累積經驗，但不把每次「改一下」都永久塞進 prompt。資料分四層：

| 層 | 內容 | Runtime 是否載入 |
|---|---|---|
| Evidence | 單次回饋、成效、edit report | 否 |
| State | 去重後的規則、支持數、衝突 | 只選相關項 |
| Pinned card | 已被反覆證明且無衝突的 6 條內規則 | 是 |
| Archive | 舊 canon、optimization log、季度 video log | 只有人工追查 |

## 晉升規則

1. 新回饋先以 soft rule 入帳；相同 scope + rule 會累加支持，不新增副本。
2. 支持數達 3 且沒有矛盾才自動 pinned。安全、真實、容量等硬規則可經明確審核直接 pin。
3. 新規則若與既有規則衝突，兩者都暫停進 runtime，直到人工決定適用範圍或 supersede。
4. 每次 context 只選片型與題材相符的前 6 條，總 digest 必須低於 900 tokens。
5. `optimization_log.md` 保留成歷史證據；新訓練不再直接往該長檔追加。

## 指令

```powershell
python scripts/hao_autopilot.py knowledge
python scripts/hao_autopilot.py learn --scope "shorts/food" --format shorts --domain food --rule "入口先給成品斷面" --evidence "Shorts 21 完播率改善"

# video_log 接近 800 行時：先預覽，再套用；完整段落先進 archive，主檔才縮小
python scripts/hao_autopilot.py knowledge --rotate-video-log
python scripts/hao_autopilot.py knowledge --rotate-video-log --apply
```

若同一規則在不同影片再次成立，重跑同一指令即可累加；系統用 fingerprint 去重。完整歷史仍可追溯，runtime 只拿小卡。

`rotate-video-log` 只移動完整的舊 `## #NNN` 記錄；封存帶內容 SHA，重跑不重複。`optimization_log.md`、`meta-lessons-canon.md` 與 archive 都標為 legacy freeze，不參與日常 Token，也不和現行規則競爭 SoT。
