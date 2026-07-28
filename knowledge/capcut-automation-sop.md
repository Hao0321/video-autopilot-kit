> 來自 video-autopilot-kit 開源知識庫 · MIT 授權

# CapCut Agent Operations — GUI 自動化 SOP（封裝 M32–M40）

> ### ⚠️ Version & platform requirements
> - **平台**：本 SOP 的 GUI 自動化為 **Windows-first**（座標/流程/paywall 地圖以 Windows CapCut 校準）。macOS 上 CapCut 無 AppleScript dictionary、UI 自繪非原生 AppKit — **Mac 建議走 Path D（JSON direct edit）/ Path E（純 ffmpeg）**，不要期待 GUI 自動化等效。詳見 `TROUBLESHOOTING.md`「CapCut version compatibility & Mac」。
> - **版本**：CapCut **國際版 6.x–9.x** 草稿為明文 JSON 可直改（8.9 親測）；中國版**剪映 6.0+** 草稿 AES 加密**不可直改**（鎖 5.9.x 或改用國際版）。改 JSON 前先跑 `capcut_helpers.detect_draft_format()` 驗明文。
> - **8.7+（Win）注意**：直改 root JSON 可能被 `template-2.tmp` / `Timelines/` 鏡像覆蓋 — 一律用 `save_draft_with_sync()`（M18 全同步）。
> - **草稿路徑**：Win `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft\`；Mac `~/Movies/CapCut/User Data/Projects/com.lveditor.draft/`（community reported — 用 `CAPCUT_USER_DATA` env override）。

> 取代每次 brief 重寫 500 行安全規則。Agent 載入此知識檔 → 讀對應 reference → token cost 砍 60%+。

CapCut Desktop GUI 操作 SOP — Computer Use agent 在 CapCut 套字體 / 模板 / 特效 / Export 的封裝知識庫。當主 Claude 要 spawn agent 跑 CapCut 時觸發載入。觸發詞：「用 CapCut 套模板」「CapCut 加字幕」「agent 剪片」「跑 CapCut」「Export v[N]」「換 CapCut 字體」。也用於診斷 — 用戶說「字醜」「沒綜藝感」「Pro paywall」要判斷可不可解。

---

## 觸發時機

| 用戶說 | 動作 |
|---|---|
| 「跑 CapCut」「agent 剪片」 | Load `capcut-agent-brief-template.md` 拉模板 |
| 「Export v[N]」「匯出」 | 走 5 分鐘最短 Export path（export-only-flow 完整版在私有 skill repo，本 kit 未含）|
| 「字醜」「換字體」「綜藝風不對」 | Load `capcut-text-templates.md` 換模板策略 |
| 「Pro paywall」「卡關」 | Load `capcut-pro-paywall-map.md` 避雷地圖 |
| 「撞 daily 限制」 | 重置時間 + fallback（daily-limits 完整版在私有 skill repo，本 kit 未含）|
| 「不要 agent / 直接改」 | Load `capcut-json-direct-edit.md` skip GUI 走 JSON |
| 「CapCut 智慧助理 / 智慧編輯助理 / 內建 AI」 | smart-edit-assistant（完整版在私有 skill repo，本 kit 未含；實測：Beta 對話式 agent，慢且未驗證，captions 仍走確定性字幕面板）|

---

## 5 個關鍵 path

### Path A: Export only（最快，最便宜）
**ETA**: 5-8 分鐘 / 約 40 tool calls / 低 token

用於：JSON 已 patched，只需開 CapCut 點 Export。
Brief 模板 → brief-export-only (完整版在私有 skill repo，本 kit 未含)

### Path B: 套單一 text template + Export
**ETA**: 25-40 分鐘 / ~140 tool calls / 中 token

用於：全部 caption 套同一花字（如 Dynamic white crayon）。
Brief 模板 → `capcut-agent-brief-template.md` Section A (single-template)

### Path C: 多模板 + 套貼圖 + Export
**ETA**: 60-90 分鐘 / ~300 tool calls / 高 token

用於：marker / main / sub 各套不同模板 + 重點段加貼圖。
Brief 模板 → `capcut-agent-brief-template.md` Section B (multi-template)
⚠️ **可能撞 daily limit（每日凌晨重置）**

### Path D: JSON direct edit（**最 efficient，沒 GUI**）
**ETA**: <1 分鐘 / 0 agent tool calls / 極低 token

用於：(1) 換 caption 文字內容（保留現有 effects）/ (2) 換 font_path 或 font_size / (3) 換 transform.y position。
**不能做**：套新模板（template_id 需要從雲端下載）/ 加貼圖。

Reference → `capcut-json-direct-edit.md`

### Path E: 純 ffmpeg（**完全跳過 CapCut**）
**ETA**: ~90 sec / 0 GUI / 極低 token

用於：用戶 OK 接受 ffmpeg drawtext 字幕（無動畫 / 無 CapCut 花字）。
Reference → 看 M35 in autopilot 主知識檔

---

## 黃金規則 — 寫進 agent brief 必含

1. **「絕對不問用戶任何問題」** — autopilot preference 鐵則
2. **「絕不點菱形💎圖示」** — Pro paywall，會在 Export 時 block
3. **「絕不動 timeline 上 transition 4px icon」** — M33 點不中，只能 Ctrl+Z
4. **「絕不開「智能 / AI / 自動 X」按鈕」** — Pro 鎖
5. **「Screenshot 經濟用」** — 起始 1 張 + 每完成 5 步 1 張 + Export 1 張，**不要 step by step screenshot**
6. **「Bash > Screenshot」** — verify 用 ffprobe / ls 直接驗證檔案，不用 screenshot
7. **「Pro paywall 早期偵測」** — 套完 5 個 effect 後試一次 Export，跳警告 → Ctrl+Z 退最後一個 → 換 free template
8. **「daily limit 撞 2 次就停」** — 不要 force retry，寫 partial report

## ✍️ M43 RULE — 字體選擇規則（不要用基本系統字）

**規定**：字體要用好看、有個性的，不要用陽春系統字。

### ❌ 禁用 / 退避字體（沒個性 / 醜）
- ~~`kaiu.ttf`~~ 標楷體（教科書感）
- ~~`mingliu.ttc`~~ 細明體 default（太細）
- ~~`NotoSansTC-Bold.otf`~~ 太 generic（除非搭配 effect / 模板）
- ~~`SmileySans-Oblique.ttf`~~ 中文 coverage 不全 → fallback 笑臉

### ✅ 好看字體 whitelist（按用途）

| 用途 | 字體 | 路徑 |
|---|---|---|
| **Vlog narrative / sub** | **Noto Serif CJK Bold** | `<專案>/assets/fonts/NotoSerifCJK-Bold.ttc` |
| **Marker title (DAY 1 / I LOVE)** | 套 CapCut 文字模板（FOOD VLOG / Coffee Time 之類）| 走 agent path |
| **Decorative dynamic text** | 套 CapCut 文字模板 速度寫 + 動畫 | 走 agent path |
| **Emergency fallback** | NotoSansTC-Black (best of system) | 系統字型目錄 / `NotoSansTC-Black.otf` |

### 找新字體 SOP

未來若嫌 `Noto Serif CJK Bold` 老氣 → 下載這些（社群驗證 vlog 用）：
- **LXGW WenKai TC**（霞鶩文楷 — 現代楷書）：`https://github.com/lxgw/LxgwWenKai-TC/releases`
- **獅尾匯潮黑**（modern marketing）
- **Justfont 金萱**（商業需 license）

下載後存到專案的 `assets/fonts/` 目錄。

### JSON edit 公式

```python
NEW_FONT = "<專案>/assets/fonts/NotoSerifCJK-Bold.ttc"
for t in d.get("materials", {}).get("texts", []):
    t["font_path"] = NEW_FONT
    co = json.loads(t["content"])
    for s in co.get("styles", []):
        s["font"] = {"path": NEW_FONT, "id": "", "cn_name": "", "tw_name": ""}
    t["content"] = json.dumps(co, ensure_ascii=False, separators=(",", ":"))
```

⚠️ 同步 3 處 JSON (M18: root × 2 + Timelines)

---

## 🚫 M42 RULE — Dynamic text / sticker overlay MUST use CapCut native, NEVER ffmpeg

**規定**：畫面上要加小動態字 / 貼圖時，一律走 CapCut native，不要用 ffmpeg。

| 任務 | ✅ 走 CapCut | ❌ 不要 ffmpeg |
|---|---|---|
| 加 caption / 字幕 | CapCut 文字 panel | ~~drawtext overlay~~ |
| 加動態 sticker (✈🍦🏨) | CapCut 貼圖 panel | ~~drawtext emoji overlay~~ |
| 動態 text overlay (彈跳 / 縮放) | CapCut 文字模板 動畫 | ~~drawtext alpha animation~~ |
| 標題卡 / outro card | CapCut 文字模板 | ~~ffmpeg color+drawtext~~ |

**ffmpeg 仍可用於**：
- ✅ Audio mix (BGM force-mix — M29 lesson)
- ✅ Video concat / trim / scale
- ✅ Color grade / film grain / vignette (cinematic post)
- ✅ Subtitle burning (僅作 .srt sidecar，CapCut 不支援時 fallback)
- ❌ **任何用戶可見的文字 / 圖案 overlay**

**Brief 模板每次加 sticker / dynamic text 必含**：「**走 CapCut native，不要 ffmpeg drawtext overlay**」

---

## 跨 brief 通用 input

每次 spawn agent brief 開頭必含這段（依實際專案替換佔位符）：

```
專案：<專案名稱>
路徑：<CapCut User Data>/Projects/com.lveditor.draft/<專案名稱>/
素材 raw：<專案>/videos/<current>/raw/<素材資料夾>/
Export 路徑：<專案>/videos/<current>/export/
BGM：<專案>/assets/bgm/<bgm 檔名>.mp3
規格：1920×1080 / 30fps / H.264 / AAC

讀知識檔：依任務 load 本 kit 對應 capcut-*.md 文件
```

---

## Token 經濟比較

| Agent run | Tool calls（量級示意）| Duration（示意）| 相對成本 |
|---|---|---|---|
| 整支剪片 from scratch | 數百 calls | 約 1 小時 | 最高 |
| 套模板 partial（撞 limit） | 上百 calls | 數十分鐘 | 中 |
| 套剩餘段 + Export | 上百 calls | 數十分鐘 | 中高 |
| Export only（純 Export） | 數十 calls | 數分鐘 | 最低 |

→ **Path A (Export only) 是 most efficient**（相對 from-scratch 可省約一個量級的 call 數與時間）。能 JSON edit 完不要 GUI 操作。

---

## 用戶診斷快速查表

| 用戶吐槽 | 真實原因 | 解法 |
|---|---|---|
| 「字醜」 | 套到兒童風 splash 模板 | 換 templates-catalog 內標記為 "vlog-friendly" 的 |
| 「沒綜藝感」 | 全部套同一模板 | 不同段套不同 — markers / 重點 / 一般 / 補充 4 套 |
| 「字幕對不上畫面」 | M9/M34 — 沒做 frame audit | 必先用 frame audit 工具看 frame |
| 「Pro paywall」 | M33 — 套到菱形 icon | Ctrl+Z 退 + 換下載 icon |
| 「撞 daily 限制」 | M40 — CapCut Free 套特效次數上限 | 每日凌晨重置，或改 Path D JSON |
| 「字體不夠多變化」 | M39 — ffmpeg drawtext 無 fallback chain | 改 CapCut Path B/C |
| 「Voiceover 缺感染力」 | M30+ — 沒做 Layer 1 | 用腳本風格 skill 寫 narration 給創作者錄 |

---

## 主 Claude 載入此知識檔的觸發

當用戶說：
- 「用 CapCut」「跑 CapCut agent」 → 直接 load 此知識檔
- 「Export」「匯出 v[N]」 → load export-only-flow（完整版在私有 skill repo，本 kit 未含）
- 「字醜 / 綜藝風 / 換字體」 → load + `capcut-text-templates.md`
- 「Pro / paywall / 卡關」 → load + `capcut-pro-paywall-map.md`

不要在 brief 內 inline 重寫所有規則。Spawn 的 agent 收到 brief 寫「讀本 kit 對應 capcut-*.md 知識檔」就好。

---

## 🆕 交付前 QA + 圖片入片 helpers (M91–M96)

`from capcut_helpers import final_delivery_qa, still_blurfill, detect_flash, detect_long_pauses, cut_audio_segments, cut_video_segments, remap_time, contact_sheet`

| helper | M-rule | 做什麼 |
|---|---|---|
| `final_delivery_qa(video, voice, contact_out)` | 🚦 | 交付前一鍵 QA：頻閃 + 死空檔 + 接觸表 |
| `detect_flash` | M93 | blackdetect 抓頻閃素材/亮度落差 |
| `classify_flash` | M93 v2 | 分開「真頻閃」與「刻意的 dip-to-black 轉場」：密集交替(<8s)或單幀爆閃(<0.12s)才擋；孤立的段落 fade 放行但列出供人眼確認。舊的「≥2 段就 flag」會把每個 fade 轉場都誤報 → gate 永遠紅 = 沒有 gate |
| `detect_long_pauses` / `cut_audio_segments` / `cut_video_segments` / `remap_time` | M95 | 句間死空檔三軌同步剪（音 atrim+concat、影 select+setpts、字幕 remap）|
| `still_blurfill` | M92 | 非滿版圖→模糊背景填滿+靜止（禁死黑邊、禁 zoompan 抖）|
| `contact_sheet` | M9/M91 | 整片接觸表逐格看 chrome/隱私 |

教訓細節 → smart-edit-assistant（ASS 字幕陷阱 + PowerShell 截窗，完整版在私有 skill repo，本 kit 未含）、`programmatic-video-build.md`（端到端 ffmpeg pipeline）。canon M91-M96 → autopilot 知識庫的 meta-lessons-canon。
