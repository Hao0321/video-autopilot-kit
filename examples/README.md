<!-- MIT License — Hao0321 Studio. See repo root LICENSE. -->
# Examples — see the kit actually run

These are **self-contained, runnable** demos. They synthesize their own test
media with ffmpeg (or use plain Python), so you need **no real footage and no
CapCut** to watch the pipeline work end-to-end.

## Prerequisites

- Python 3.9+
- `ffmpeg` / `ffprobe` on your `PATH` (only example 01 needs them)
- *(optional)* the **Noto Sans TC** font for the exact caption look — without it,
  libass substitutes a default font and example 01 still renders fine

No `pip install` is required: the examples add the repo's `src/` to the path
themselves.

## Run them

```bash
# 1) Build a real vertical 9:16 Short from synthesized clips + music
python examples/01_vertical_short.py
#    → prints the path to a finished 1080x1920 short.mp4 (open it in any player)

# 2) Zero-config caption ↔ b-roll matching (pure Python, no ffmpeg)
python examples/02_caption_broll_match.py
#    → shows footage auto-aligned to captions just by filename
```

## What each one shows

| File | Demonstrates | Needs ffmpeg? |
|---|---|---|
| `01_vertical_short.py` | `normalize_to_portrait` (any orientation → upright 9:16) → `build_one_short` (multi-color highlight captions + BGM started at its musical highlight, volume-evened) → a finished MP4 | yes |
| `02_caption_broll_match.py` | `auto_sequence_brolls` with **no keyword config** — name b-roll after its content (`coffee.mp4`, `sunset.mov`) and each caption gets the matching clip, with filler for the gaps | no |

## Make it yours

Swap the synthesized clips/BGM in example 01 for your own phone footage and a
music file and you have a real food/travel Short. To bias matching toward your
own topics, pass a `keyword_map` to `auto_sequence_brolls` (see
`src/capcut_helpers/caption_broll_matcher.py` and `TROUBLESHOOTING.md`) — but the
zero-config filename path works without it.

> The CapCut-driven main path (`src/capcut_helpers/`) needs CapCut Desktop + an
> AI assistant with Computer Use, so it isn't a self-running script — see the
> repo `README.md` and `SETUP.md` for that path.

- `PLAN_TEMPLATE.md` — 規劃模板（`plan_gate.py` 可驗格式，v0.9）
- `channel_state.example.json` — 經營狀態機模板（複製到 repo root 改名 `channel_state.json` 使用，v0.9）
