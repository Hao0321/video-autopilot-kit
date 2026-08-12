# 自動剪輯儲存生命週期（M115）

> 單一真值：`src/storage_lifecycle.py`。本文件說明使用方式；保留數量與白名單以程式為準。

## 為什麼需要這條規則

同一支影片改字幕、配樂或字卡時，不應因一次小修改就新增一支完整 1080p／4K 影片。
`v2`、`v3`、`FINAL`、`old`、`backup` 是人工命名，不是版本控制，也不是備份策略。

## 固定結構

```text
<job>/
├── raw source files            # 唯讀；cleanup 永遠不能碰
├── _plan.py / project files    # 可重建的真相
├── _out/
│   ├── current.mp4             # 唯一目前成片
│   ├── .storage-policy.json    # 啟用時間與既有 legacy baseline
│   ├── _work/                  # candidate、cache、transient
│   └── _qa/                    # 人眼驗證證據
└── .autocut-history.jsonl      # 每輪 metadata，不存影片副本
```

## 每次修改的固定流程

1. `activate_policy(_out)`：第一次只登記既有舊檔，不移、不刪。
2. render 到 `_work/current_candidate.mp4`。
3. render 成功後用 `atomic_publish()` 原子換成 `_out/current.mp4`。
4. 跑影片 QA；紅燈保留 debug 證據，不清理。
5. QA 全綠才用 `finalize_success()` 清除明確白名單暫存並寫入 JSONL 歷史。
6. 交付到其他資料夾用 `link_or_copy()`；同磁碟優先 hard link，避免重複佔用影片容量。

## 保留政策

| 類型 | 保留量 | 規則 |
|---|---:|---|
| 原始素材 | 全保留 | 永遠不自動刪 |
| `current.mp4` | 1 | 成功 build 才原子換版 |
| visual cache | 1 | 來源沒變可重用 |
| transient | 0 | QA 綠後只清白名單 |
| metadata history | 全保留 | 每輪一行 JSONL |
| binary milestone | 最多 2 | 只允許 `approved`／`published`；第 3 份直接停止，交由人決定 |
| 啟用前 legacy | 原樣 | 只報告，不暗刪 |

單一 job 超過 4 GB 會警告並要求盤點；**容量超標本身不授權刪檔**。

## CLI

```powershell
# 唯讀容量盤點
python src/storage_lifecycle.py audit <project-root>

# 深度查完全相同的大檔（較慢）
python src/storage_lifecycle.py audit <project-root> --hash-duplicates

# 檢查輸出政策
python src/storage_lifecycle.py check <job>\_out

# cleanup 預設 dry-run；確認清單後才加 --apply
python src/storage_lifecycle.py prune <job>\_out\_work
python src/storage_lifecycle.py prune <job>\_out\_work --apply

# 同磁碟優先 hard link 交付
python src/storage_lifecycle.py deliver <job>\_out\current.mp4 <delivery>\video.mp4

# 只有核准或已發布可建立 milestone
python src/storage_lifecycle.py snapshot <job>\_out\current.mp4 <job> --label approved
```

## 禁止事項

- 禁止自動建立新的 `v2`／`v3`／`FINAL` 完整成片。
- 禁止 render 直接覆寫 `current.mp4`；半途失敗不能破壞最後可播版本。
- 禁止 wildcard 刪整個 `_work`；只能清 helper 白名單或本輪精確註冊的檔案。
- 禁止把 `_archive` 當成永久垃圾桶；搬移不會減少容量。
- 禁止容量 gate 一響就刪原始素材。

最高原則：**可重建的東西不是歷史；版本號不是備份策略。**
