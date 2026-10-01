> 來自 video-autopilot-kit 開源知識庫 · MIT 授權

# Token Efficiency Lessons (從多版血淚教訓寫成)

> 一支短影音 vlog 曾跑了非常多版、燒掉大量 token、耗時整整一天才收斂。
> 過程中累積大量回饋與失敗，全部 anti-pattern 寫進來避免重蹈覆轍。

## 🔥 TOP 5 token 浪費 anti-patterns

### 1. 反射式 spawn agent — 50% 浪費
**錯**：用戶說 X → 立刻 spawn agent 做 X → 結果 wrong
**對**：JSON 改先試 → 改不到才 agent → agent 寫死 brief

範例：
- 套某特效到全部 caption：❌ 不要 spawn → ✅ JSON deep-copy effect material entry（花了幾個 agent 失敗才學會）
- Export：✅ agent 只做 click button + 對話框填參數（精簡模式 ≤25 calls / 3 min）
- Reverse engineer：✅ agent 套 1 個 + Ctrl+S → diff JSON 學結構

### 2. Agent report 不能 trust — verify 必跑
**錯**：Agent 回報「PASS audio fixed」→ 我信 → 結果又漏音
**對**：每次 agent 完成 → 我自己 ffmpeg verify (waveform / extracted frame)

公式：
```python
# Verify pattern after every export
subprocess.run(['ffmpeg', '-i', video, '-vn', 'audio.wav'])
subprocess.run(['ffmpeg', '-i', 'audio.wav', '-filter:v', 'showwavespic', 'wave.png'])
# Read wave.png — 連續飽和 = OK / 稀疏 spike = 漏音
```

### 3. 不要重複犯同一錯
M9 / M10 / M21 / M29 / M34 / M37 / M38 / M42 都是「我已經寫進 skill 但又犯」型 errors。

**強制 check**：spawn agent 前 / build script 前 / JSON edit 前 → **load skill references/ 對應 .md** 看清楚規則。

### 4. 細微 detail 不要硬碰 — 接受工具限制
- 某些花字 effect 是給少數英文字母設計的 → 中文長句 render 不出 → 試多個 ID 都一樣
- 文字範本 (text-template) 是 timeline object 不能套既有 segment → agent 試很久卡死
- 剪輯軟體的 Pro 功能可能有 daily limit（每日定時 reset）

**規則**：撞 3 次同問題 → 寫進 skill「fundamental limit」+ 換 path / 接受

### 5. Caption hallucination — 必先 audit footage
**M9 + M34**：寫文案前必跑 thumbnail audit
- ❌ 看用戶 N 段文案就直接配給 N 個 clip
- ✅ ffmpeg 抽 hi-res frame (640×360+) → Read 看清楚 → 對到實際畫面寫
- 經典翻車：把某段素材的 caption 配錯——畫面內容與文案對不上，多跑了幾版才發現

## 💰 Token-efficient SOP per agent type

### Export-only agent (Path A): ≤ 40 calls / 40K tokens / 3-5 min
- ✅ 把「只做 Export」的 4 個 step 寫死成一份固定 SOP，agent 照唸不自由發揮
- ✅ 不 spot check / 不 verify timeline
- ❌ 不 open_application 多次
- ❌ 不 screenshot 每步

### Apply single template (Path B): ≤ 80 calls / 80K tokens / 10-15 min
- Brief 寫死「只動 1 個 segment + Ctrl+S，不 Export」
- 完成後**我自己 diff JSON 學結構** → JSON 複製到剩下所有 segment

### Browse / explore (Path C): ≤ 50 calls / 50K tokens / 15-20 min
- Agent 截圖 + 寫 report
- 不修改 any state

## 🚦 主 Claude 決策 flow

```
用戶說 X
  ↓
能 JSON 改嗎？
  ├─ YES → 立刻 JSON edit + verify + spawn Export agent
  └─ NO  → 需要 GUI 操作
            ↓
          Brief minimal agent (≤ 25 calls)
            ↓
          完成後 ffmpeg / Python verify
            ↓
          Verify FAIL → 重 spawn? 還是接受 limit?
            ├─ 已試 3 次 → 接受 limit / 換 path / 退場
            └─ 還沒試 3 次 → spawn 一個更 focused 的
```

## ⚠️ 不要做的事 (token 殺手)

❌ 對話內 paste 大段 JSON dump（用 file 存 + 只 print summary）
❌ Background grep 跑超過 30 sec（timeout 切短）
❌ Spawn 5+ agent 同步跑（一個一個）
❌ Read full agent transcript file（規定不能讀，會炸 context）
❌ 反覆 read 同 file 多次（state cached in conversation 用 Edit 不要 re-Read）
❌ 一次 ffmpeg pipeline 處理 10+ filters（拆成 stages 出錯好 debug）
❌ 給用戶 buffet 4-5 option（TOP 1 推薦 + 1 backup max）
