<!-- MIT License — Hao0321 Studio. See repo root LICENSE. -->
# Examples — see the kit actually run

These are **self-contained, runnable** demos of VA, the planning-and-checking half of the kit.
They need **no real footage, no ffmpeg and no Editkin**: each one feeds plain data or disposable
fixtures in and prints a verdict out. Rendering is Editkin's job (see
[`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)), so none of these examples produce a video.

## Prerequisites

- Python 3.9+
- Nothing else. No `pip install`: every example adds the repo's `src/` to the path itself and
  imports nothing third-party.

The Shorts rule gate, `src/longform_maker/shorts_gate.py`, is **pure Python** — which is exactly why
example 04 runs with nothing installed. Note *how* 04 imports it: it puts `src/longform_maker/` on
`sys.path` and does `from shorts_gate import …`. That flat import (or copying `shorts_gate.py` +
`shorts_gate_validation.py` + `gate_core.py` out) bypasses the package `__init__`, so the
zero-dependency promise stays true.

## Run them

```bash
# 2) Editkin v4 durable-workflow contract self-test
python examples/02_caption_broll_match.py
#    → walks the receipt-bound DAG and proves stale/legacy/unsafe operations are rejected

# 4) Vertical-Shorts rule gate — a broken cut blocked, then fixed
python examples/04_shorts_gate.py
#    → prints BLOCK/PASS reports, then the same 31s cut blocked on YT and accepted on IG

# 5) Interview guest gate — same guest blocked, then passing
python examples/05_interview_plan.py
#    → shows an unsourced guest achievement stopped *before* you record
```

Examples 01 (FFmpeg vertical Short) and 03 (Python premium FX) were retired in v0.25.0 together with
the renderers they demonstrated. They remain available on tag `v0.24.1`.

## What each one shows

| File | Demonstrates |
|---|---|
| `02_caption_broll_match.py` | `workflow_contract.py selftest` — exercises the Editkin v4 DAG from source-byte hashing and evidence receipts through plan audit, atomic apply, render, human review and outcome; also proves legacy plans, stale evidence, uncertain apply and machine-authored human review are rejected. Uses temporary fixtures, never a real project |
| `04_shorts_gate.py` | `shorts_gate.gate_shorts(spec)` — a vertical Short that breaks 3 rules at once (duration dead zone / slow first cut / missing opening ID) is blocked, the fixed version passes with caption timings computed from segment indexes, and the same 31s cut is blocked on `yt_shorts` but accepted on `ig_reels` using `PLATFORM_RULES` |
| `05_interview_plan.py` | `interview_gate.gate_guest` / `assert_guest` — the *same* fictional guest is BLOCKED while one achievement has no source, then PASSES once the source is filled in |

> `06_teardown.py` was removed in v0.25.0 (it was already broken). To measure a competitor's video,
> run the tool directly: `python src/teardown.py <video-or-folder>` (needs ffmpeg; OCR is optional).

## Make it yours

For a real edit, use the Editkin v4 controller described in the [README](../README.md): bind every
real source file, complete the evidence receipts, audit an `edit-plan/v4`, then apply once and
render a review candidate in Editkin. Example 02 intentionally uses disposable fixtures so you can
test those safety invariants without touching a real project. For Shorts, check your spec with the
same `gate_shorts(spec)` call example 04 uses before it goes into the plan.

## Also in this folder

- `PLAN_TEMPLATE.md` — the planning template `plan_gate.py` validates
- `channel_state.example.json` — ops state-machine template; copy it to the repo root as
  `channel_state.json` to start tracking
