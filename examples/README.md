<!-- MIT License — Hao0321 Studio. See repo root LICENSE. -->
# Examples — see the kit actually run

These are **self-contained, runnable** demos. They synthesize their own test
media with ffmpeg (or use plain Python), so you need **no real footage or editor
GUI** to inspect the public planning, workflow-contract and QA layers.

## Prerequisites

- Python 3.9+
- `ffmpeg` / `ffprobe` on your `PATH` (only examples **01** and **03** need them —
  **04 / 05 / 06 run with no ffmpeg at all**)
- *(optional)* the **Noto Sans TC** font for the exact caption look — without it,
  libass substitutes a default font and example 01 still renders fine

No `pip install` is required for examples **01 / 02 / 04 / 05 / 06** — they add the repo's
`src/` to the path themselves and import nothing third-party. **04, 05 and 06 also need no
media of any kind**: they are plain data in, plain verdict out.

Two things in the repo do need packages: `03_premium_fx.py` needs **Pillow**, and the
one-command Shorts driver `src/shorts_autopilot.py` needs **Pillow + numpy** (frame-quality
analysis / contact sheets / QA proof images). The rule gate it drives,
`src/longform_maker/shorts_gate.py`, is **pure Python** — which is exactly why example 04
runs with nothing installed. Note *how* 04 imports it: it puts `src/longform_maker/` on
`sys.path` and does `from shorts_gate import …`. Import it as `longform_maker.shorts_gate`
instead and you go through the package `__init__`, which loads `fx_lib` and so needs
numpy + Pillow. Flat import (or copying `shorts_gate.py` + `gate_core.py` out) keeps the
zero-dependency promise real.

## Run them

```bash
# 1) Build a real vertical 9:16 Short from synthesized clips + music
python examples/01_vertical_short.py
#    → prints the path to a finished 1080x1920 short.mp4 (open it in any player)

# 2) Editkin v4 durable-workflow contract self-test (pure Python, no ffmpeg)
python examples/02_caption_broll_match.py
#    → walks the receipt-bound DAG and proves stale/legacy/unsafe operations are rejected

# 3) Premium motion FX on a synthetic stat card (needs Pillow + numpy + ffmpeg)
python examples/03_premium_fx.py
#    → count-up + bloom + light sweep + sub-pixel Ken Burns, in a ~3s clip

# 4) Vertical-Shorts rule gate — a broken cut blocked, then fixed (pure Python)
python examples/04_shorts_gate.py
#    → prints the gate report, then the same cut passing under your own thresholds

# 5) Interview guest gate — same guest blocked, then passing (pure Python)
python examples/05_interview_plan.py
#    → shows an unsourced guest achievement stopped *before* you record

# 6) Competitor teardown math on fabricated timestamps (pure Python)
python examples/06_teardown.py
#    → two clips with the SAME median cut gap and completely different feel,
#      plus the captions÷cuts ratio that tells you when NOT to re-shoot
```

## What each one shows

| File | Demonstrates | Needs ffmpeg? |
|---|---|---|
| `01_vertical_short.py` | `normalize_to_portrait` (any orientation → upright 9:16) → `build_one_short` (multi-color highlight captions + BGM started at its musical highlight, volume-evened) → a finished MP4 | yes |
| `02_caption_broll_match.py` | `workflow_contract.py selftest` — exercises the Editkin v4 DAG from source-byte hashing and evidence receipts through plan audit, atomic apply, render, human review and outcome; also proves legacy plans, stale evidence, uncertain apply and machine-authored human review are rejected | no |
| `03_premium_fx.py` | `longform_maker.fx_lib` — eased count-up whose final frame is *asserted* to equal the true value, double-layer bloom, light sweep, sub-pixel Ken Burns, grain + vignette, synthesized whoosh. Needs **Pillow + numpy** | yes |
| `04_shorts_gate.py` | `shorts_gate.gate_shorts` — a vertical Short that breaks 3 rules at once (duration dead zone / slow first cut / missing opening ID) is blocked, the fixed version passes and gets its caption timings computed from segment indexes, and the same 31s cut is then accepted under **your own** thresholds via `rules=`. No media, no `pip install` | no |
| `05_interview_plan.py` | `interview_gate.gate_guest` / `assert_guest` — the *same* fictional guest is BLOCKED while one achievement has no source, then PASSES once the source is filled in. No media, no `pip install` | no |
| `06_teardown.py` | `teardown.rhythm_stats` / `pace_profile` — three fabricated clips show why the median cut gap alone cannot tell a beat-locked montage from a narrative arc (identical medians, 0.00 vs 1.15 stdev), and why a 3-cut clip can still read fast. Also prints whether the tool's **optional** OCR packages are installed and what you lose without them. No media, no `pip install` | no |

## Make it yours

Swap the synthesized clips/BGM in example 01 for your own phone footage and a
music file and you have a real food/travel Short. For an editable project, use
the Editkin v4 controller described in `README.md`: bind every real source file,
complete the evidence receipts, audit an `edit-plan/v4`, then apply once and
render a review candidate. Example 02 intentionally uses disposable fixtures so
you can test those safety invariants without touching a real project.

## Also in this folder

- `PLAN_TEMPLATE.md` — the planning template `plan_gate.py` validates (v0.9)
- `channel_state.example.json` — ops state-machine template; copy it to the repo root as
  `channel_state.json` to start tracking (v0.9)
