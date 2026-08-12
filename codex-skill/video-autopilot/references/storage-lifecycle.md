# 自動剪輯儲存生命週期（M115）

> SoT：`storage_lifecycle.py`。這份文件說明操作與整合；數值常數以程式為準。

## 問題定義

同一支影片改字幕、BGM 或字卡時，不應因為一次小修改就新增一支完整 1080p／4K 影片。
`v2／v3／FINAL／old／backup` 是人工命名，不是版本控制，也不是備份策略。

本專案 2026-08-08 基準盤點：

| 範圍 | 檔案 | 容量 |
|---|---:|---:|
| `videos/` | 6,796 | 13.624 GB |
| `_archive/` | 672 | 4.856 GB |
| `_planning/` | 4,080 | 4.766 GB |
| `_INBOX/` | 2,011 | 3.693 GB |
| ≥20 MB 的 SHA-256 完全重複 | 26 組 | 0.871 GB 可少佔 |

## 固定結構

```text
<job>/
├── raw source files            # 唯讀，任何 cleanup 都不能碰
├── _plan.py / project files    # 可重建真相
├── _out/
│   ├── current.mp4             # 唯一目前成片
│   ├── current_visual_plan.json
│   ├── .storage-policy.json    # policy 啟用時間＋既有 legacy baseline
│   ├── .human-qa-approved      # 長片人工 QA 完成後才建立
│   ├── _work/                  # candidate／cache／transient
│   └── _qa/                    # 人眼驗證證據
└── .autocut-history.jsonl      # 每輪 metadata；不是影片副本
```

## 改同一支片的標準流程

1. `activate_policy(_out)`：第一次只記錄既有舊檔，不移、不刪。
2. render 到 `_work/current_candidate.mp4`。
3. render 完整成功才 `atomic_publish(candidate, _out/current.mp4)`。
4. 跑影片 QA。
5. Shorts 全綠可直接 `finalize_success()`；長片還要逐張看全幀圖、字幕與 proof。
6. 長片人工項完成後建立 `_out/.human-qa-approved`，才允許 finalize。
7. finalize 只刪 helper 白名單 transient，保留 raw、current、visual cache、QA。
8. 交付到發布資料夾用 `link_or_copy()`；同 volume 不多佔一份影片空間。

## CLI

```powershell
# 唯讀容量盤點；不 hash 大檔，速度快
python .claude\skills\video-autopilot\storage_lifecycle.py audit videos

# 深度查完全相同的大檔（較慢）
python .claude\skills\video-autopilot\storage_lifecycle.py audit videos --hash-duplicates

# 檢查某 job 是否只新增 current.mp4，且無新 vN／FINAL 檔
python .claude\skills\video-autopilot\storage_lifecycle.py check <job>\_out

# 看本輪可清掉什麼；預設 dry-run
python .claude\skills\video-autopilot\storage_lifecycle.py prune <job>\_out\_work

# 確認清單後才實際清白名單 transient
python .claude\skills\video-autopilot\storage_lifecycle.py prune <job>\_out\_work --apply

# 交付；同 volume 優先 hard link
python .claude\skills\video-autopilot\storage_lifecycle.py deliver `
  <job>\_out\current.mp4 <發布資料夾>\片名.mp4

# 只有核准／已發布可建立 binary milestone；第 3 份會 fail，要求人工取捨
python .claude\skills\video-autopilot\storage_lifecycle.py snapshot `
  <job>\_out\current.mp4 <job> --label approved
```

## 保留政策

| 類型 | 保留 | 誰能觸發 |
|---|---:|---|
| 原始素材 | 全保留 | 永遠不自動刪 |
| current | 1 | 每輪成功 build 原子換版 |
| visual cache | 1 | source／片段沒變就重用 |
| transient | 0 | QA 全綠後 helper 白名單清除 |
| metadata history | 全保留 | 每輪追加一行 JSONL |
| binary milestone | 最多 2 | 只有「核准」或「已發布」；超過先人工決定 |
| legacy | 初次 baseline | 只報告；不暗刪 |

單一 job 超過 4 GB 要警告並跑 audit，但**容量超標本身不授權刪檔**。

## Pipeline 整合最小範例

```python
from storage_lifecycle import (
    activate_policy, atomic_publish, canonical_output_path,
    finalize_success, link_or_copy,
)

activate_policy(out_dir)
current = canonical_output_path(out_dir)
candidate = work_dir / "current_candidate.mp4"
render(candidate)
atomic_publish(candidate, current)

qa = run_qa(current)
if qa["all_green"]:
    finalize_success(job_dir, current, work_dir, qa,
                     registered_transients=[burned, mix_raw, mix_final])
```

## 禁止事項

- 禁止用 `v2／v3／FINAL` 自動命名新的完整成片。
- 禁止 render 直接覆寫 current；半途失敗會把唯一可播版本截壞。
- 禁止把整個 `_work` wildcard 刪掉；只能刪白名單或本輪精確註冊路徑。
- 禁止把 `_archive` 當垃圾桶一直搬；搬移不會減少容量。
- 禁止用 copy 做同 volume 交付；先試 hard link。
- 禁止因為 storage gate 超標就碰原始素材。

## 封存重複檔：固定的安全去重規則

1. 先依檔案大小分組，再逐檔計算 SHA-256；檔名相同不算證據。
2. 自動候選只能是 `videos/_archive` 內的檔案，而且同一工作根目錄外必須有
   一份 byte-identical 保留本。
3. 套用時不刪路徑：用保留本建立暫存 hard link，重新驗證 SHA-256，再以
   `os.replace` 原子替換封存副本。
4. `_INBOX`、`_planning`、`_PUBLISH_HUB`、`_待發布Shorts`、`current.mp4` 與交付檔永遠不是
   自動去重 target；只處理封存副本。
5. 同一 hard-link inode 不再計入「可回收容量」。稽核同時回報 logical bytes、
   physical bytes、hardlink saved bytes，避免重複計算。
6. hard link、雜湊複驗或路徑邊界任一失敗時，保留原檔並回報 RED；禁止 fallback
   成刪除或未驗證覆寫。

```powershell
# 先看精確 target / keeper / SHA-256
python scripts/hao_autopilot.py dedupe-archive videos

# 只對通過上述六條規則的候選套用
python scripts/hao_autopilot.py dedupe-archive videos --apply
```
