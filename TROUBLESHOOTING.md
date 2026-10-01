# TROUBLESHOOTING

## Editkin run 卡住、畫面對不上旁白

Editkin 是本 kit 唯一現行剪輯執行合約。不要跳過素材理解，也不要用檔名、舊成片或
generic stock 猜內容。每份來源素材都必須依序完成：

`prepare_ai_material` → `view_material_keyframes` → `get_material_context` →
`record_material_semantics`

其中 semantics 至少引用一個本次真正看過的 keyframe 或 transcript cue。多份素材可以
有界平行，但同一份素材不可跳步。若畫面錯配，先查三件事：

1. `--material CLIP_ID=SOURCE_FILE` 是否綁到真實 source bytes，而不是 proxy／舊輸出。
2. semantics receipt 的 `evidenceFrameIds`／`transcriptCueIndexes` 是否真的支持該段摘要。
3. `edit-plan/v4` 是否綁齊全部 material／semantic receipts；缺一份就不應進 audit。

```bash
python scripts/hao_autopilot.py workflow status <run>
python scripts/hao_autopilot.py workflow next <run>
python scripts/hao_autopilot.py workflow verify <run>
```

run 預設只放在專案內 `videos/_AUTOPILOT/editkin-v4/`。不要在磁碟根目錄另建工作資料夾。

---

## Plan audit 被拒絕

常見原因：

- schema 不是 `hao.video-autopilot.edit-plan/v4`。v1–v3 只可匯入／檢視，不能 apply。
- plan hash、Skill hash、knowledge hash、workflow contract hash 或 plugin manifest 漂移。
- project revision 已被其他編輯修改；舊 audit receipt 不可套到新 revision。
- source 路徑相同但 bytes 已換檔；controller 會以 SHA-256 判 drift，不信舊 metadata。
- plugin discovery 後又改了候選集合，卻沿用舊 audit receipt。

修法不是手改 receipt。回到 `next`，讓受影響的下游步驟失效並重新產生 plan，再跑
`audit_autopilot_plan`。audit 前 plugin 只能 discovery／compile，不能先修改專案。

---

## Apply 中斷後不知道有沒有成功

這是刻意 fail-closed。`apply_autopilot_plan` 是一次原子提交；若連線或程序中斷後無法
證明 committed，run 必須進入 reconcile，禁止自動重套，否則可能把同一批 edit 做兩次。

```bash
# 已確認沒有提交
python scripts/hao_autopilot.py workflow resume <run> --apply-resolution not-applied

# 已找到 committed receipt
python scripts/hao_autopilot.py workflow resume <run> \
  --apply-resolution committed --receipt <receipt.json>
```

不要刪 state 檔重開來繞過 reconcile；那會丟失 exactly-once 證據。

---

## Render 完但手機仍看到舊版

render 只會產 candidate 與 artifact hash，不會因為「檔案存在」就自動升格 current。
依序確認：

1. apply receipt 是 committed，且 render 綁到 `projectRevisionAfter`。
2. 技術 QA 已全綠。
3. candidate 已走原子 promotion，手機入口指向 current，而不是舊快取或 `_work`。
4. 人工審片事件由真人寫入；機器不得代填 approved／certified。

若手機端快取，先比對 artifact SHA-256；hash 不同才是入口／快取問題，hash 相同則手機
看到的就是目前 current。

---

## Ship-ready QA — 成品交付前自檢

Editkin render 後、還沒稱為「完成」前，跑 editor-neutral QA：

```python
from media_delivery_qa import final_delivery_qa

report = final_delivery_qa(
    "current_candidate.mp4",
    voice="voice_cut.wav",
    ass="captions_cut.ass",
    sheets_dir="qa/fullframe",
    contact_out="qa/contact.png",
    profile="teaching_longform",
)
assert report["deliver_ok"]
```

從 repo root 執行時把 `src/` 加到 `PYTHONPATH`，或直接用專案既有 runner。教學長片的
`profile="teaching_longform"` 會強制 voice、ASS、full-frame sheets；缺任一項直接
BLOCKED，避免只傳一支 MP4 得到假綠。

| Gate | 要抓的問題 |
|---|---|
| M91 / M104 | 工作列、瀏覽器分頁、錄影浮窗、私人後台；全幀掃描圖必須真人逐張看 |
| M92 | 死黑邊、截圖外框、非滿版圖片未做 blurred fill |
| M93 | 真頻閃；孤立 dip-to-black 只列為人工確認 |
| M94 | 旁白點名具體 artifact 卻用了 generic stock |
| M95 | 句間長停頓；人聲、畫面、字幕必須用同一組 cuts 重映射 |
| M103–M105 | loudness、尾端靜音、A/V sync、字幕不溢出、字幕對真實語音 |
| M108 / M79 | 斷句品質、BGM 全片覆蓋 |

QA 全綠仍不等於人工審片完成。機器不得替真人標記 certified。

---

## 常見環境問題

- **`delivery_media_ops` import 失敗**：確認 `src/media_delivery_qa.py` 與
  `src/delivery_media_ops.py` 來自同一 release；不要混用半套升級。
- **`ffmpeg` / `ffprobe` 找不到**：把兩者放進 `PATH`，重開 terminal 後跑
  `ffmpeg -version` 與 `ffprobe -version`。
- **播放速度怪／卡格**：素材先 normalize 到 timeline target fps；不要把 24/25/29.97
  當作 30fps metadata 直接塞入。
- **Windows 背景執行遇到 cp950**：Python stdout/stderr 與 subprocess 明確設 UTF-8；
  不要讓非 ASCII log 在 redirect 時炸掉。
- **player 顯示時間與實際 PTS 不同**：先用 ffprobe／抽幀確認檔案，再決定是否用
  conservative CFR player-safe re-encode；不要只信單一播放器計時器。

完整狀態轉移與續跑規則見
[`codex-skill/video-autopilot/references/editkin-workflow-execution.md`](codex-skill/video-autopilot/references/editkin-workflow-execution.md)。
