# 程式化 Motion Runtime

## 目標與邊界

這一層把公開 code-first video 工具已證明有效的能力當 benchmark，但不安裝第三方 video framework、不複製其程式碼，也不把某個框架變成專案格式。唯一真相是 `hao.motion-composition/v1`；HTML、component scene、vector scene、3D 與既有 Python 效果都只連自研 adapter。

「自研」指應用層：時間軸、component schema、動畫求值、seek contract、模板、路由、Tracking／Roto 工作流、QA 與發佈。codec、解碼、像素矩陣、字型繪製與瀏覽器標準不重造，直接使用 FFmpeg／ffprobe、OpenCV、Pillow、瀏覽器／SVG 等成熟低階引擎。

目前是可運行的 compiler／validator／dispatch contract，不宣稱已覆蓋 HyperFrames 或 Remotion 的全部 renderer、Studio、雲端渲染與外掛生態。缺少的自研 adapter 必須明列 roadmap，不得偷偷以第三方依賴補洞或假稱 parity。

## 公開能力拆解

| 公開能力 | 來源 | Hao runtime 對應 | 額外門檻 |
|---|---|---|---|
| frame-addressable composition、tracks、seek clock | [HyperFrames Composition](https://hyperframes.video/docs/concepts/composition)、[Timing and tracks](https://hyperframes.video/docs/concepts/timing-and-tracks) | 整數 frame root、z-order tracks、immutable frame contract | 禁止 wall clock，避免預覽與輸出漂移 |
| GSAP／Lottie／Three.js／Rive 等 frame adapter 概念 | [HyperFrames Frame adapters](https://hyperframes.video/docs/concepts/frame-adapters) | 自研 `hao_browser_seek`、`hao_vector_runtime`、`three_d_system` | 不引入上述框架；只實作同等 seek contract |
| CLI lint／inspect／render／doctor 與 JSON 自動化 | [HyperFrames CLI](https://hyperframes.video/docs/workflow/cli-reference) | `lint`、`inspect`、`compile`、`catalog`、`doctor`、stable exit | Quality-95、手機審片、clean fallback |
| component + current frame + composition metadata | [Remotion Fundamentals](https://www.remotion.dev/docs/the-fundamentals) | 自研 `component_scene`、variables／variants、root metadata | 不依賴 React／Remotion |
| parameterized player／editor／timeline | [Remotion Player](https://www.remotion.dev/docs/player)、[Timeline](https://timeline.remotion.dev/) | compiler graph 可供未來 UI／手機 review client 使用 | UI 不得代簽 Hao 審美結果 |
| transitions／server render／cloud render | [Remotion Transitions](https://www.remotion.dev/docs/transitions)、[Rendering](https://www.remotion.dev/docs/render) | transition adapter、renderer dispatch contract | 禁止雙主體 ghost；發佈仍走 Publish Hub |

## Canonical composition

作用域固定是全域：Shorts、Reels、長片、旅遊、美食、AI 教學、Podcast／訪談、開箱、戰鬥陀螺與未來新增題材都使用同一 runtime。題材只改 design token、component props、素材與 shot evidence，不建立另一套時間軸核心。`visual_director.write_visual_plan()` 必須為每個 build 產生 `current_composition.json` 與 `current_render_graph.json`。

必填：

- `schema`, `id`, `width`, `height`, `fps`, `duration_frames`
- `tracks[]`: `id`, `component`, `start_frame`, `duration_frames`, `z`, `props`
- Tracking／Roto／Transition／3D 額外必填 `meaning` 與 `evidence`

關鍵硬門檻：

- `subject_black_to_color_reveal` 只能 `target_kind=subject_object` 且 `reveal_mode=black_to_color`。
- `foreground_background_parallax_cut` 只能 `foreground_handoff=midpoint_hard_cut`；禁止前後景主體 cross-dissolve。
- 所有媒體與 effect spec 在 compile 前驗證存在。
- composition、asset、node、render graph 都產生 SHA-256；變體共享結構 hash，但不共享私人路徑。

## CLI

```powershell
python composition_runtime.py catalog
python composition_runtime.py lint composition.json
python composition_runtime.py inspect composition.json
python composition_runtime.py compile composition.json --output render-graph.json
python composition_runtime.py compile composition.json --variants variants.json
python composition_runtime.py doctor
python composition_runtime.py selftest
```

## 做得比通用框架更適合本專案的地方

這不是宣稱通用渲染能力已全面超越第三方；優勢是把 Hao 已訓練的剪輯規則放到 renderer 之上：題材路由、語意選鏡、Tracking／Roto 證據、物件遮罩限制、怪轉場回退、Quality-95、手機審片、發佈中樞與公開授權治理。通用工具負責「怎麼畫」，這一層同時約束「為什麼畫、能不能畫、失敗如何退」。

## 升級順序

1. Canonical compiler 與現有 Python effect adapter。
2. 已建立第一階段自研瀏覽器 seek-clock、component scene 與 vector scene adapter；下一階段補齊像素 renderer、音訊 graph 與互動式 timeline UI。
3. Player／timeline UI；只讀取 graph，不改寫學習真相。
4. 本地／CI／雲端 renderer pool；輸出必須通過同一 hash 與 QA。
5. 與 HyperFrames／Remotion frozen benchmark 比較 determinism、效能與跨機一致性；只公布量測結果，不引入其 runtime。
