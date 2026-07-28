# 🎬 video-autopilot-kit

> A **framework**, not a hand-me-down config. Reusable pure-ffmpeg pipeline + CapCut
> automation code, plus a questionnaire that asks about **your** channel and turns the
> system into yours.
>
> ⚠️ **Ships with nobody's private data** — no account names, no analytics readouts, no personal
> profiles (`profiles/` and `config.py` are gitignored local files). Voice word-lists, KPI
> thresholds and community fields are either **blank templates** (`<fill in>`, `______`, or a
> brace-wrapped `{…}` placeholder in generated output) or explicitly **labelled as example
> values** for you to replace.
> The flip side, stated plainly: `knowledge/` **is** the author's own hard-won methodology —
> that part is deliberately open-sourced. It is *how to think*, not *his numbers*.

*(中文版見 [README.md](README.md))*

## 🧭 Which path should I use? (3-second decision tree)

- **On Mac / Linux?** → **Path 1 Programmatic** (pure code, cross-platform, no CapCut)
- **Want CapCut effects / fancy text / cloud templates?** → **Path 2 CapCut-assisted** (Windows-first; **version-sensitive** — read the compatibility matrix in [TROUBLESHOOTING](TROUBLESHOOTING.md) first)
- **Just want full automation with no GUI?** → **Path 1 Programmatic**

## ▶️ See it run in 60 seconds (no CapCut, no real media)

Want to see it actually move first? `examples/` has self-contained, runnable demos —
they synthesize test media with ffmpeg, so you need no real footage and no CapCut:

```bash
python examples/01_vertical_short.py      # synthesized clips → a finished 1080x1920 Short
python examples/02_caption_broll_match.py # zero-config: name b-roll by content, captions auto-align
python examples/04_shorts_gate.py         # Shorts gate: a broken cut blocked → fixed → re-accepted under YOUR thresholds
python examples/05_interview_plan.py      # interview gate: an unsourced guest number stopped *before* you record
```

Needs Python 3.9+. **04 / 05 need no ffmpeg at all** (pure Python, zero `pip install`, zero
media); 01 needs `ffmpeg`/`ffprobe` and 03 additionally needs Pillow + numpy. See
[`examples/README.md`](examples/README.md).

## Why this is different

Most "creator systems" either sell you **someone else's setup** (useless to you, sometimes
misleading) or stay too generic to have real methodology. This kit gives you the **skeleton**
(a battle-tested structure); `SETUP.md` **asks you questions** one section at a time, and
your answers fill it in — so it actually becomes **your** system.

## 🆕 New in v0.10.0 — three **isomorphic** production lines

This kit used to answer one question: "how do I make **one long-form video** well?" It now
runs three production lines — deliberately built in **the same shape**:
**a knowledge layer (why) → a mechanical gate (so nobody has to remember) → a one-command driver**.
Learn one and you've learned all three; adding a fourth (podcast? course series?) means
filling in the same three slots.

| Line | Knowledge layer (why) | Mechanical gate (blocks early) | One-command driver |
|---|---|---|---|
| **Teaching long-form** | `knowledge/premium-motion-fx.md` + `knowledge/meta-lessons.md` | `plan_gate` → `script_gate` → `delivery_qa(profile='teaching_longform')` | the `src/longform_maker/` modules |
| **Vertical Shorts** | [`knowledge/shorts-mastery-2026.md`](knowledge/shorts-mastery-2026.md) | [`src/longform_maker/shorts_gate.py`](src/longform_maker/shorts_gate.py) — nine structure/caption rules (the remaining three need human eyes), **pure Python** | [`src/shorts_autopilot.py`](src/shorts_autopilot.py) — `scan` → write captions *from what's on screen* → `build` (with automatic QA proof images) |
| **Interview show** | [`knowledge/interview-show-playbook.md`](knowledge/interview-show-playbook.md) | [`src/interview_gate.py`](src/interview_gate.py) — I-A…I-E: **a guest number with no source never airs** | [`src/interview_autopilot.py`](src/interview_autopilot.py) — `invite` → `plan` (renders the 7-doc kit) → `build` |

- **Shared gate shell** — [`src/longform_maker/gate_core.py`](src/longform_maker/gate_core.py) gives every gate the same
  return shape / `assert` message / self-test output. Your own gate imports three functions and behaves
  exactly like the built-ins (**the rules themselves stay in each gate's own file** — not centralizing them
  is what keeps them from contaminating each other).
- **Ops layer** (since v0.9): `src/channel_tracker.py` D2/D7/D28 snapshot scheduling + pending actions,
  `src/system_health.py` one-command GREEN/RED health check → wiring guide
  [`knowledge/ops-automation.md`](knowledge/ops-automation.md); define-viral-with-your-own-data framework
  [`knowledge/viral-playbook-framework.md`](knowledge/viral-playbook-framework.md)
- ⚠️ Every threshold in those gates is an **example calibration, not a universal law** — recompute the
  Shorts duration band / first-cut deadline / non-white caption cap from **your own** 3-5 best videos
  (how-to in [SETUP.en.md](SETUP.en.md), "Shorts rule calibration").

## What's inside — two first-class paths

The kit has **two paths of equal standing** — not "primary vs. secondary":

> This is a **different axis** from the three production lines above: a *line* is what kind of
> video you're making (long-form / Shorts / interview); a *path* is how you make it (pure code
> vs. CapCut). All three lines can run on Path 1.

| Path | Module | What | Platform |
|---|---|---|---|
| ⭐ **Path 1 — Programmatic** (recommended default for adopters) | `src/longform_maker/` | **Teaching long-form modules** — `fx_lib` premium-motion engine (sub-pixel Ken Burns / double bloom / light sweep / easing / synthesized SFX), `word_captions` word-timestamp captions (M105), `screen_clean` mechanized screen-recording cleanup (M104). Exact parameters → `knowledge/premium-motion-fx.md` | Win / Mac / Linux |
| ⭐ **Path 1 — Programmatic** | `src/silent_vlog_maker/` | **Pure ffmpeg pipeline** — vertical Shorts (multi-color captions / BGM highlight start / normalization), silent vlogs, asset cleanup | Win / Mac / Linux |
| ⭐ **Path 1 — Programmatic** (v0.10) | `src/shorts_autopilot.py` + `src/longform_maker/shorts_gate.py` | **Vertical-Shorts line** — `scan` normalizes to 9:16, builds a contact sheet and a `_plan.py` skeleton → you (or an AI) **write captions from what's on screen** → `build` runs the gate, cuts the Short, and renders QA proof images. The gate itself is pure Python (not even ffmpeg) | Win / Mac / Linux |
| ⭐ **Path 1 — Programmatic** (v0.10) | `src/interview_autopilot.py` + `src/interview_gate.py` + `templates/interview/` | **Interview-show line** — guest facts in, out come the invite message / host script / question outline / guest prep kit / consent form / recording checklist / publish kit / Shorts cut list, all rendered from templates; an unsourced guest number is blocked *before* the recording date | Win / Mac / Linux |
| ⭐ **Path 1 — Programmatic** (v0.10) | `src/longform_maker/gate_core.py`, `src/av_util.py` | **Shared foundation** — one shell for every gate (report / assert / self-test) plus the mechanical bits every autopilot needs (subprocess wrapper / ffprobe duration / frame grabs / contact sheets) | Win / Mac / Linux |
| ⭐ **Path 1 — Programmatic** | the **QA gates** in `src/capcut_helpers/` | **Mechanical pre-delivery QA** (`delivery_qa`: strobing, dead air, caption sync, full-frame scan M91-M95 / `broll_audit` ratio / `caption_broll_matcher` alignment) — pure ffmpeg/Python, **no CapCut required**; output from either path should pass this gate | Win / Mac / Linux |
| **Path 2 — CapCut-assisted** (what the author personally uses) | the rest of `src/capcut_helpers/` | **CapCut Desktop automation** — direct draft-JSON editing (draft I/O / 4-level mute / fancy text / AI-subtitle fixes) + **an AI assistant + Computer Use operating the CapCut window** (apply templates / export). **Version-sensitive** → [TROUBLESHOOTING](TROUBLESHOOTING.md) | Windows-first |
| Shared | `knowledge/` | **Video-production knowledge base** — M1-M111 pitfall compendium + algorithm + SOP + editing craft | — |
| Shared | ▶️ `examples/` | **Self-contained runnable demos** — ffmpeg-synthesized media; see the pipeline work in 60s (no CapCut/real footage) | — |
| Shared | ⭐ `SETUP.md` | **Start here** — answer questions to make the system yours | — |
| Shared | `templates/` | Blank fill-in templates: voice / brand / algorithm / community / pipeline / context. v0.10 adds `show_profile` (your show's settings) and the 11 interview deliverable templates in `templates/interview/` — **change the wording in the template, never in the code** | — |
| Shared | `config.example.py` | Path config (env vars; **no account names** — auto-detects current user) | — |

> **Honest note**: the original author's private workflow runs mostly on **Path 2 (CapCut)** —
> but that's because his assets, templates, and muscle memory live in CapCut. Most open-source
> adopters **should start with Path 1**: cross-platform, no CapCut dependency, immune to CapCut
> version churn, fully reproducible. Move up to Path 2 when you need CapCut's fancy-text /
> cloud templates.

### Platform support

| Module | Windows | macOS |
|---|---|---|
| Programmatic (`longform_maker` / `silent_vlog_maker` / QA gates) | ✅ | ✅ (system paths & CJK fonts auto-detected by `src/platform_compat.py`; same on Linux) |
| CapCut draft-JSON direct editing (`capcut_helpers` draft I/O) | ✅ verified locally | ⚠️ paths supported (`CAPCUT_USER_DATA` env override + `detect_draft_format()`), automation untested on Mac |
| Computer Use GUI automation (templates / export) | ✅ | ❌ (CapCut for Mac has no AppleScript dictionary; see the Mac section in [TROUBLESHOOTING](TROUBLESHOOTING.md)) |

## Quick start

1. Read **`SETUP.md`** → fill `templates/*.template.md` into `profiles/*.md`
   (or hand the repo to Claude / ChatGPT: *"ask me the SETUP.md questions and generate my profiles/"*)
2. `cp config.example.py config.py` → set your asset / export paths (CapCut paths only needed for Path 2)
3. Pick a path: **Path 1** runs with just Python + ffmpeg; **Path 2** additionally needs CapCut Desktop + your AI assistant's Computer Use (see Requirements)
4. Use the tools in `src/`

## Requirements

**Path 1 — Programmatic (recommended default for adopters; Win / Mac / Linux)**
- Python 3.9+
- `ffmpeg` / `ffprobe` on PATH
- **No CapCut, no Computer Use** — the whole pipeline is reproducible code
- Mac/Linux: system paths and CJK fonts are auto-detected by `src/platform_compat.py` (don't hardcode system font paths)
- The only module that needs pip packages is **`src/shorts_autopilot.py`** (one-command
  vertical-Shorts flow): **Pillow + numpy**, for frame-quality analysis, contact sheets
  and QA proof images. The rule gate itself, `src/longform_maker/shorts_gate.py`, is
  **pure Python** (not even ffmpeg) — run it dependency-free with
  `python examples/04_shorts_gate.py`.
  ⚠️ That guarantee is about **the file**, so import it **flat**: put `src/longform_maker/` on
  `sys.path` and `from shorts_gate import …` (what example 04 does), or copy `shorts_gate.py` +
  `gate_core.py` out. Importing it as `longform_maker.shorts_gate` runs the package `__init__`,
  which eager-imports `fx_lib` and therefore needs numpy + Pillow.
- The interview line (`src/interview_autopilot.py` / `src/interview_gate.py`) is **pure Python for
  the entire pre-production stage** — rendering the 7-doc kit needs no ffmpeg and no pip packages;
  ffmpeg only enters at `build`, after you've recorded → `python examples/05_interview_plan.py`

**Path 2 — CapCut-assisted (what the author personally uses; Windows-first, version-sensitive)**
- **CapCut Desktop, international edition** (Pro is better) — editing / captions / templates happen here. ⚠️ **Version-sensitive**: direct draft-JSON editing has a per-version compatibility matrix (Jianying CN 6.0+ drafts are encrypted and cannot be edited directly) — read [TROUBLESHOOTING](TROUBLESHOOTING.md) first and verify with `detect_draft_format()`
- **AI assistant + Computer Use** (Claude Desktop / Claude Code, etc.) — required for GUI automation (cloud templates / export); **there is no working equivalent on Mac** (see the Mac section in TROUBLESHOOTING)
- Python 3.9+ and `ffmpeg` / `ffprobe` — for post-export: BGM loop / trim-to-voice-end / player-safe re-encode

*(optional)* an AI assistant can also auto-generate your profiles from your `SETUP.md` answers.

## Philosophy

The most valuable part of a creator system is the **structure and methodology**, not one
person's private numbers. So this repo gives you the bones; you fill them with your own flesh.

## License

MIT — keep the notice and use / modify / sell freely.

## Author

Hao0321 Studio — an open-source framework distilled from a real personal creator system.
