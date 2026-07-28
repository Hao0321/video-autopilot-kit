# CapCut Agent Brief Template

> 來自 video-autopilot-kit 開源知識庫 · MIT 授權

> Spawn computer-use agent 跑 CapCut 操作時，brief 必含這 6 區塊。  
> 從多支 vlog 專案 20+ agent spawn 經驗提煉（M32 / M33 / M40 教訓）。

---

## 🎯 何時 spawn agent（觸發條件）

| 條件 | 動作 |
|---|---|
| 連 ≥2 輪 programmatic patch 用戶仍罵 | spawn agent（**不要 spawn 第 3 次**）|
| 用戶提及「全自動」「agent」「Computer Use」 | spawn agent |
| JSON edit 無法達成（要 GUI 動 timeline / 套新模板）| spawn agent |
| Export only（JSON 已 patched） | spawn agent Path A |

**Hard cap：spawn 上限 = 2 agents / task**。連 2 個失敗 → 停止 spawn，改 Path D (JSON edit) 或 user manual。詳 `agent-token-efficiency.md`。

---

## 📋 Brief 必含 6 區塊（缺一就 spawn 失敗）

### 1. 起始狀態 + 已做了什麼

```
專案：<專案資料夾名稱>
路徑：<CapCut Projects 目錄>\<專案資料夾名稱>\
當前狀態：v<N> 已套 25 個 crayon + 3 個 gold marker，BGM 已 ffmpeg force-mix
要 agent 做：把 28 個 caption 全部改 bubble style（effect_id <effect-id>）+ Export
```

### 2. 用戶具體吐槽歷史（每條 actionable，不是抽象抱怨）

```
- v18: 要求動態文字走 CapCut native，不要用 ffmpeg drawtext → 走 CapCut sticker 不 ffmpeg drawtext
- v20: 「字醜」→ 換用戶 favorited 花字（effect_id <effect-id> ART 描邊背景樣式）
- v22: 用戶手動加 canvas_blur 11 個 portrait → 不要 JSON 覆蓋回 uniform
```

### 3. raw assets + 參考檔案路徑

```
raw：<raw 素材目錄>\（49 MOV + 60 HEIC）
Export 路徑：<export 輸出目錄>\
BGM：<bgm 目錄>\<bgm-檔名>.mp3
cut-plan：<專案目錄>/cut-plan-<專案>-v<N>.md
user canonical state backup：<專案目錄>/user_final_state/
```

### 4. 操作步驟 8-10 步（含 Hook + 字幕 + 轉場 + KenBurns + 濾鏡 + 音訊 verify + Export）

```
Step 1: 開 CapCut Desktop → load <專案> project
Step 2: Screenshot 起始狀態 → verify project loaded OK
Step 3: 文字 tab → 花字 sub-tab → ⭐ filter → 找 effect_id <effect-id>
Step 4: 套到 caption seg #0（第一段 caption）→ Ctrl+S → screenshot verify
Step 5: 若 Step 4 渲染 OK → JSON 複製 effect 到剩 27 個 caption（不要 GUI 操作 28 次）
Step 6: ⚠️ 先試一次 Export 確認 Pro paywall（套 5+ effects 後）→ 若跳警告，Ctrl+Z 退最後一個
Step 7: 套完 → Ctrl+S → 螢幕截圖 timeline 全貌
Step 8: 點 Export 按鈕 → 選 1080p 30fps H.264 / AAC default
Step 9: 等 Export 完成（不要動鼠標，CapCut 跑 background ~3-5 min）
Step 10: 螢幕截圖 Export 完成畫面 → 確認 mp4 落在 <export 輸出目錄>
```

### 5. Export 路徑 + 報告檔

```
Export 落點：<export 輸出目錄>\<專案>_v<N>.mp4
報告檔：<專案目錄>/edit-report-agent-<N>.md
報告必含：
- 起始 / 結束 timestamp
- Tool calls 數
- 卡關處（哪步停下用 Ctrl+Z 退）
- Pro paywall blocker（若有）
- daily limit 撞牆（若有）
- Final Export 檔案大小 + duration verify (ffprobe)
```

### 6. 鐵則（絕不違反）

```
1. 絕對不問用戶任何問題 — autopilot preference 鐵則
2. 絕不點菱形💎圖示 — Pro paywall，會在 Export 時 block
3. 絕不動 timeline 上 transition 4px icon — M33 點不中只能 Ctrl+Z
4. 絕不開「智能 / AI / 自動 X」按鈕 — Pro 鎖
5. Screenshot 經濟用 — 起始 1 張 + 每 5 步 1 張 + Export 1 張（不要 step by step）
6. Bash > Screenshot — verify 用 ffprobe / ls 不用 screenshot
7. Pro paywall 早期偵測 — 套 5 effects 後試一次 Export，跳警告 → Ctrl+Z 退 → 換 free template
8. daily limit 撞 2 次就停 — 不要 force retry，寫 partial report
9. 動態文字 / sticker MUST use CapCut native，NEVER ffmpeg drawtext (M42)
10. User 已 favorited 的花字（star icon）優先使用，不要 reverse engineer 不存在的
11. **Session start 第一個 PowerShell command 必 minimize 所有 Chrome window** (M70 — Chrome focus-steal 吃 50% tool calls)
12. **CapCut foreground 完一定要 MoveWindow resize 到 1400×900** (M71 v2 — 1400×900 = universal size, editor view + Export dialog 都能用；舊值 900×650 only fit Export dialog)
13. **Post-Export rename mp4 用 Copy-Item → Kill CapCut → Remove duplicate pattern** (M72 — file lock 不能 Move/Rename)
```

---

## 🔤 M66 — 中文字幕 MUST 繁體中文（永遠不能簡體）

繁體中文 audience，CapCut AI default 出**簡體**（设计/开发/纲/并）→ 用戶必罵。

**任何含 AI 字幕的 brief 必含這 3 段**：

```
Step X (智能字幕): 選語言時 → 「中文（繁體）」/「Traditional Chinese」
                    永遠不要選 default「中文」(可能是 簡體)

Step X+1 (verify): screenshot 字幕 preview，檢查指標字：
                    簡體: 设/计/开/发/纲/并/创/为/这/还/动/区/划/觉
                    繁體: 設/計/開/發/綱/並/創/為/這/還/動/區/劃/覺
                    若見簡體字 → 寫 partial report 停下，NOT Export

Step X+2 (fallback if CapCut UI 無繁體 option):
                    生成後 export 字幕 .srt → OpenCC s2tw.json 轉 → import 回 CapCut
                    或 CapCut「簡轉繁」toggle（字幕 panel 內）
```

→ 寫到 brief 第 4 區塊「操作步驟」字幕段 + 第 6 區塊「鐵則」最後一條

---

## 🚨 Brief Anti-patterns（spawn 後立刻失敗的寫法）

| Anti-pattern | 為什麼壞 | 修正 |
|---|---|---|
| 「剪一支 vlog」 | 太抽象 agent 不知做什麼 | 列具體 step 8-10 步 |
| 「修一下字幕」 | 沒指定哪些 caption / 套什麼 effect | 「caption seg #0-#27 套 effect_id X」|
| 「跑完 Export 給我」 | 沒指定 Export 路徑 / format | 列 5 區塊「Export 落點」 |
| 「有問題就停下問用戶」 | 違反 autopilot rule | 「絕不問用戶任何問題」必含鐵則 |
| 「順便加個轉場」 | 模糊 → agent 點到 Pro icon 卡關 | 列具體 transition name + 確認 free |
| 「按你判斷做」 | agent context 無 user history → 亂做 | 列吐槽歷史 + canonical state path |

---

## 💼 Spawn 參數 default

```python
Agent(
    description="<短描述 3-5 字>",
    subagent_type="general-purpose",  # 預設用 general（有 computer-use tools 子集）
    # 若需完整 Computer Use tools → 建新 capcut-edit-agent.md（見下注）
    run_in_background=True,  # 30-60 min 操作，主 Claude 同時處理其他事
    prompt="<brief 6 區塊完整內容>",
)
```

⚠️ **注**：舊 DaVinci 相關 agent brief 已 archive（DaVinci 已淘汰）。新 spawn 用 `general-purpose` agent。若想要專屬 CapCut agent（含完整 computer-use tool 集 + auto-load brief template），可建 `.claude/agents/capcut-edit-agent.md`（v0.2 規劃）。

---

## 📊 Brief 範例庫

| 用途 | 範例檔 |
|---|---|
| Export only（JSON 已 patch） | brief-export-only (完整版在私有 skill repo，本 kit 未含) |
| 套單一 template + Export | （待補：v0.2 加） |
| 多模板 + 貼圖 + Export | （待補：v0.2 加，⚠ 易撞 daily limit）|
| Template browse（用戶決策前 explore） | brief-template-browse (完整版在私有 skill repo，本 kit 未含) |

---

## 🪟 M48: CapCut window-hidden 後 SetForegroundWindow workaround

**症狀**：`open_application("CapCut")` 回 success 但 screenshot 仍是上一個 frontmost app（如 File Explorer / Chrome），CapCut 已啟動但 window hidden / behind 別人。

**根因**：Chrome 是 tier "read"（無法 alt+tab 切換）+ CapCut process 在但 window 沒 bring to foreground。

**Fix（PowerShell SetForegroundWindow Win32 API）**：

```python
Bash('''powershell -NoProfile -Command "
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Win {
    [DllImport(\"user32.dll\")] public static extern bool SetForegroundWindow(IntPtr hWnd);
}
'@;
$p = Get-Process CapCut | Where-Object {$_.MainWindowHandle -ne 0} | Select-Object -First 1;
if ($p) { [Win]::SetForegroundWindow($p.MainWindowHandle) }
"''')
wait(seconds=2)
screenshot()  # CapCut now frontmost
```

**Phase 1 setup 必跑順序**：
1. `Bash` kill stale CapCut processes (M20)
2. **`PowerShell` minimize 所有 Chrome window (M70 — Chrome focus-steal pre-flight)**
3. `open_application("CapCut")` + `wait(seconds=5)`
4. `screenshot()` → 若 frontmost 不是 CapCut → 跑 SetForegroundWindow workaround
5. **`MoveWindow` resize CapCut 到 1400×900 (M71 v2 universal)**
6. Continue 標準 load project flow

---

## 🪟 M70 — Chrome focus-steal pre-flight (必 minimize 所有 Chrome window)

**症狀**：Agent 開 CapCut 後，Chrome 在背景每秒 grab focus 一次 → 對 CapCut 任何點擊有 race / 字段點不進去 / Export filename 改不掉 → agent **吃 ~50% tool calls 戰 focus**。

**根因**：Chrome tier=read 不能被 left_click 切換，但**process 仍持續搶 focus**（auto-refresh / notification / sync etc.）。`SetForegroundWindow` to CapCut 馬上被 Chrome 搶回。

**Fix（PowerShell minimize all Chrome at session start）**：

```python
Bash('''powershell -NoProfile -Command "
$sig = '[DllImport(\\"user32.dll\\")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);';
Add-Type -MemberDefinition $sig -Name Win32ShowWindow -Namespace Win32Functions -PassThru | Out-Null;
Get-Process chrome -ErrorAction SilentlyContinue | Where-Object { \$_.MainWindowHandle -ne 0 } | ForEach-Object {
  [Win32Functions.Win32ShowWindow]::ShowWindow(\$_.MainWindowHandle, 6)  # SW_MINIMIZE = 6
};
echo 'Chrome minimized'
"''')
```

**位置**：**永遠 session start 第一個 PowerShell command**（M20 kill CapCut 之後立刻跑）。

**預期收益**：30-50% wall-clock saving for any GUI agent session（M70 是 M48 的補丁 — M48 setForegroundWindow 解決「CapCut hidden」但解決不了「Chrome 搶回 focus」）。

---

## 📐 M71 — CapCut Export dialog auto-shrinks to ~136 px → MoveWindow resize 必跑

**症狀**：Agent SetForegroundWindow 把 CapCut 帶 foreground 後，**Export dialog 自動縮到 ~136 px 寬**，所有按鈕 / 字段擠在一起 → agent 點不到 / 看不清 / 完全 unusable。

**根因**：CapCut Export dialog 有 dynamic-resize bug — `SetForegroundWindow` 觸發 resize event 但沒 layout reflow。

**Fix（PowerShell MoveWindow Win32 API）**：

```python
Bash('''powershell -NoProfile -Command "
$sig2 = '[DllImport(\\"user32.dll\\")] public static extern bool MoveWindow(IntPtr hWnd, int x, int y, int w, int h, bool repaint);';
Add-Type -MemberDefinition $sig2 -Name Win32MoveWindow -Namespace Win32Functions -PassThru | Out-Null;
$cap = Get-Process CapCut | Where-Object {\$_.MainWindowHandle -ne 0} | Select-Object -First 1;
if (\$cap) {
  [Win32Functions.Win32MoveWindow]::MoveWindow(\$cap.MainWindowHandle, 100, 100, 1400, 900, \$true)
};
echo 'CapCut resized 1400x900'
"''')
wait(seconds=1)
screenshot()  # 確認 dialog 已正常大小
```

**標準 size (M71 v2)**：**1400 × 900**（universal — editor view + Export dialog 都能正常顯示。舊值 900×650 只夠 Export dialog，editor 看不到 timeline + 預覽 — 見 AP13）。

**時機**：每次 `SetForegroundWindow` 完一定要跟一個 `MoveWindow`（不只 Export dialog — 任何 CapCut foreground call 都應該 resize）。

---

## 📐 AP13 Numeric Value Rules

寫 brief 時任何具體 numeric value (window size / wait seconds / timeout / iteration count / volume) 必含 4 件事，避免「brief 寫死 value 違反 universal applicability」(AP13):

### Numeric Value 必要 metadata

```
<NUMBER>:
  - 適用場景: e.g. "1400×900 = universal, editor view + Export dialog 都能用"
  - 反例: e.g. "900×650 只夠 Export dialog，editor 看不到 timeline"
  - agent override 條件: e.g. "if editor view 仍 cropped → 1600×1000 / 2K monitor → 1920×1080"
  - 違反 brief 鐵則否: e.g. "不違反鐵則 1 autopilot (override 不算問用戶)"
```

### Common antipatterns to avoid

| Antipattern | Fix |
|---|---|
| 「`MoveWindow 900×650`」(寫死 value 沒 context)| 「`MoveWindow 1400×900` (universal — editor + dialog 都 OK)；若 2K+ 螢幕 agent 可改 1920×1080」|
| 「`wait(seconds=180)` for Export」(固定 wait) | 「`wait(seconds=10)` 然後 screenshot 看 progress bar；長片 (>2 min) extend up to 180」|
| 「scroll 10 次」(寫死次數) | 「scroll until 找到目標 element 或 scroll 達 max 20 次」|
| 「iteration limit 5」(寫死 cap) | 「iteration cap 5 — autopilot 場景；若 user 在線可放寬 to 10」|

### Why this matters

Brief = spec，不是 code。Agent 在 runtime 可能遇到 brief 沒料到的 context（不同螢幕 size / 不同 app version / 不同 progress 速度），允許 agent 在**不違反鐵則的前提下** override numeric value 反而更穩。

**通則**：把 numeric value 想成「default + override condition」而不是「constant」。

---

## 🔒 M72 — Post-Export mp4 file lock：必先 Copy → Kill CapCut → Remove duplicate

**症狀**：Export 完成後想 rename mp4 為 target filename → `Move-Item` / `Rename-Item` 全 fail（"File is being used by another process"）— CapCut 還握著 file handle。

**根因**：CapCut Export 完 mp4 後，**仍持有 file handle 給 preview / thumbnail / index**，要等 CapCut close 才釋放。

**Fix（3-step pattern）**：

```powershell
# 1. Copy first (succeeds even with lock — read-only access works)
Copy-Item "<CapCut 預設輸出路徑>\<default-export>.mp4" `
          "<目標路徑>\<target-name>.mp4"

# 2. Kill CapCut (release lock)
Stop-Process -Name CapCut -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# 3. Now safe to remove duplicate (lock released)
Remove-Item "<CapCut 預設輸出路徑>\<default-export>.mp4" -Force
```

**❌ 永遠不要試**（這 3 個會 fail）：
- `Move-Item "Source.mp4" "Target.mp4"` — file lock
- `Rename-Item "Source.mp4" "Target.mp4"` — file lock
- `Remove-Item "Source.mp4"` 在 Kill CapCut 前 — file lock

**Alternative pattern (next time, simpler)**：brief 寫「accept CapCut default filename → 整個 agent task 結束後，main session 自己 rename」— 不要在 agent run 內 rename。

**為什麼 GUI 改 filename 也常失敗**：Export dialog 的 filename 字段 + Chrome focus-steal (M70) 常常一起 race → 字段 click 不進去 → 直接 default filename → 結束後 rename 比較穩。

---

## ⚡ Path A 實際 ETA（≤30s short）

從實測（~28s portrait short）：
- **Tool calls**: 30 (vs estimate 35-50)
- **Wall-clock**: **4 min** (vs estimate 8-12 min)
- **Export render**: ~3 sec (vs `wait(seconds=180)` placeholder — GPU acc + 短片極快)

→ 短片建議**改 `wait(seconds=10)` + active check**（screenshot 看 progress bar）取代固定 180 sec wait。長片（>2 min）仍照 180 sec。

---

## 🔊 CapCut Export 音訊 default = AAC 192 kbps（不是 320 brief 寫的）

**M49**：CapCut Export dialog UI 無「audio bitrate」選項。embedded video audio 預設 192 kbps AAC，無法在 GUI 改。

**Brief 寫「AAC 320k」是空話** — 不影響 agent run 但會誤導。新 brief 寫「AAC default（192k embedded）」更準確。

要 320k 唯一方法：ffmpeg post-process `-c:a aac -b:a 320k` 重 mix。但 192k AAC 對 vlog/short 完全夠用（YouTube 也是 transcode 到 ~128k），不需特別升。

---

## ✅ M47 verified — Effects pre-applied via JSON 無需 UI re-application

agent confirm：JSON 內 effect material entries + segment.extra_material_refs 正確 link → CapCut 載入時自動 render，**Path A agent 不需要進文字 panel 重套**。

→ 之前早期 agent 報「effect_id 空」是 misread（JSON 內 effect_id 也是 populated，render 失敗是別的原因 — 可能 schema 缺 field）。M47 用 `apply_effect_to_segment()` 18-field full schema 後問題解決。

---

## 🎓 Lessons from 20+ agent spawn

1. **Brief 太抽象 = agent 卡 28 min** — 必含具體 step
2. **不寫「絕不問用戶」= agent 停下等回應 = autopilot 失敗** — 鐵則必含
3. **Pro paywall 沒早期偵測 = 套 5+ effect 後 Export 失敗 = Ctrl+Z 退 20 次** — Step 6 必含試 Export
4. **沒列吐槽歷史 = agent 重做用戶已罵過的事** — 區塊 2 必含
5. **沒給 canonical state backup path = agent 覆蓋 user manual edit** — 區塊 3 必含
6. **Screenshot 過多 = token 爆炸 (40k+ for Export only run)** — 鐵則 5+6 必含
7. **不設 spawn cap = 連 spawn 4 個都卡關仍 spawn 第 5 個** — 主 Claude 自己守 2/task

---

## Cross-references

- Path A-E spec：見 `capcut-automation-sop.md`（完整版在私有 skill repo）
- Token efficiency anti-patterns：`agent-token-efficiency.md`
- Pro paywall 避雷地圖：`capcut-pro-paywall-map.md`
- daily-limit 重置時間 + fallback：(完整版在私有 skill repo，本 kit 未含)
- JSON direct edit Path D：`capcut-json-direct-edit.md`
- text template 套用 catalog：`capcut-text-templates.md`
