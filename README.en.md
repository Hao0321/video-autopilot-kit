# 🎬 video-autopilot-kit

> A **framework**, not a hand-me-down config. Reusable pure-ffmpeg pipeline + CapCut
> automation code, plus a questionnaire that asks about **your** channel and turns the
> system into yours.
>
> ⚠️ **Ships with zero of the original author's private data** — voice, strategy, and
> community numbers are all **blank templates** you fill in yourself.

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
```

Needs Python 3.9+ and `ffmpeg`/`ffprobe` (only example 01 needs ffmpeg). See [`examples/README.md`](examples/README.md).

## Why this is different

Most "creator systems" either sell you **someone else's setup** (useless to you, sometimes
misleading) or stay too generic to have real methodology. This kit gives you the **skeleton**
(a battle-tested structure); `SETUP.md` **asks you questions** one section at a time, and
your answers fill it in — so it actually becomes **your** system.

## What's inside — two first-class paths

The kit has **two paths of equal standing** — not "primary vs. secondary":

| Path | Module | What | Platform |
|---|---|---|---|
| ⭐ **Path 1 — Programmatic** (recommended default for adopters) | `src/longform_maker/` | **Teaching long-form modules** — `fx_lib` premium-motion engine (sub-pixel Ken Burns / double bloom / light sweep / easing / synthesized SFX), `word_captions` word-timestamp captions (M105), `screen_clean` mechanized screen-recording cleanup (M104). Exact parameters → `knowledge/premium-motion-fx.md` | Win / Mac / Linux |
| ⭐ **Path 1 — Programmatic** | `src/silent_vlog_maker/` | **Pure ffmpeg pipeline** — vertical Shorts (multi-color captions / BGM highlight start / normalization), silent vlogs, asset cleanup | Win / Mac / Linux |
| ⭐ **Path 1 — Programmatic** | the **QA gates** in `src/capcut_helpers/` | **Mechanical pre-delivery QA** (`delivery_qa`: strobing, dead air, caption sync, full-frame scan M91-M95 / `broll_audit` ratio / `caption_broll_matcher` alignment) — pure ffmpeg/Python, **no CapCut required**; output from either path should pass this gate | Win / Mac / Linux |
| **Path 2 — CapCut-assisted** (what the author personally uses) | the rest of `src/capcut_helpers/` | **CapCut Desktop automation** — direct draft-JSON editing (draft I/O / 4-level mute / fancy text / AI-subtitle fixes) + **an AI assistant + Computer Use operating the CapCut window** (apply templates / export). **Version-sensitive** → [TROUBLESHOOTING](TROUBLESHOOTING.md) | Windows-first |
| Shared | `knowledge/` | **Video-production knowledge base** — M1-M106 pitfall compendium + algorithm + SOP + editing craft | — |
| Shared | `skills/video-autopilot/` | **Portable Codex skill specification** — image-first framing, YT_music scoring, Traditional Chinese narration, and formal MP4 QA | — |
| Shared | ▶️ `examples/` | **Self-contained runnable demos** — ffmpeg-synthesized media; see the pipeline work in 60s (no CapCut/real footage) | — |
| Shared | ⭐ `SETUP.md` | **Start here** — answer questions to make the system yours | — |
| Shared | `templates/` | Blank fill-in templates: voice / brand / algorithm / community / pipeline / context | — |
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
