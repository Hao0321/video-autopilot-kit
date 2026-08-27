# 🎬 video-autopilot-kit

> **v0.15.0 / architecture 6.1**: long-form, Shorts and Reels share an efficient template compiler
> and evidence-gated cinematic craft. Camera, edit, sound, color, VFX and transitions fall back to a clean cut when shot evidence is missing. The 33-reference design DNA, tracking, Quality-95 review, publishing packages, outcome learning and safe updates for long-form,
> Shorts and Reels. Run `python src/system_health.py --quick` to validate a clean install. Personal
> media and analytics never enter the release.

> A **framework**, not a hand-me-down config. A durable Editkin `edit-plan/v4` workflow,
> reproducible media/QA tools, plus a questionnaire that asks about **your** channel and turns the
> system into yours.
>
> ⚠️ **Ships with nobody's private data** — no analytics readouts (the author's least of all), no
> personal profiles (`profiles/` and `config.py` are gitignored local files). Two named exceptions,
> both **public** information rather than private data: the author's byline in LICENSE and the
> READMEs, and **third-party creators/channels named in `knowledge/`** (public tactics quoted in
> the algorithm files, the reference-channel rows in `teaching-niche-playbook.md`) — those stay
> **citation-first: no link, no number**. Voice word-lists, KPI
> thresholds and community fields are either **blank templates** (`<fill in>`, `______`, or a
> brace-wrapped `{…}` placeholder in generated output) or explicitly **labelled as example
> values** for you to replace.
> The flip side, stated plainly: `knowledge/` **is** the author's own hard-won methodology —
> that part is deliberately open-sourced. It is *how to think*, not *his numbers*.

*(中文版見 [README.md](README.md))*

## 🧭 Current editing execution

- **One editor contract**: Editkin v4 (material evidence → plan → audit → atomic apply → render).
- Python/ffmpeg are cross-platform analysis, normalization and QA support, not a second editor path.
- Legacy GUI/draft-JSON/Path A-E documents are benchmark-only history, never a fallback.

## ▶️ See it run in 60 seconds (no real media)

Want to see it actually move first? `examples/` has self-contained, runnable demos —
they synthesize test media with ffmpeg or exercise the Editkin v4 contract with disposable fixtures:

```bash
python examples/01_vertical_short.py      # synthesized clips → a finished 1080x1920 Short
python examples/02_caption_broll_match.py # Editkin v4 contract: full DAG + fail-closed regression checks
python examples/04_shorts_gate.py         # Shorts gate: broken cut blocked → fixed → accepted under YOUR thresholds → accepted on another platform
python examples/05_interview_plan.py      # interview gate: an unsourced guest number stopped *before* you record
python examples/06_teardown.py            # teardown math: medians lie, stdev doesn't, and captions/cuts is a shooting decision
```

Needs Python 3.9+. **04 / 05 / 06 need no ffmpeg at all** (pure Python, zero `pip install`, zero
media); 01 needs `ffmpeg`/`ffprobe` and 03 additionally needs Pillow + numpy. See
[`examples/README.md`](examples/README.md).

## Why this is different

Most "creator systems" either sell you **someone else's setup** (useless to you, sometimes
misleading) or stay too generic to have real methodology. This kit gives you the **skeleton**
(a battle-tested structure); `SETUP.md` **asks you questions** one section at a time, and
your answers fill it in — so it actually becomes **your** system.

## 🆕 New in v0.12.0 — borrowed numbers, evicted

This release **removes no capability. It removes borrowed certainty.** Four unrelated parts of
the kit were making the same mistake: a number nobody measured, wearing an authority label, is
worse than no number at all — because you trust it.

- **The Shorts duration band is platform-aware.** Its dead zone was measured on **YouTube**
  Shorts; applied to IG/FB it blocks cuts that perform perfectly well. Pick a band with
  `spec["platform"]` (`rules=` still wins per key); an unknown platform name is a **blocking
  failure**, never a silent fallback.
- **The script gate's four audience word-lists now ship empty.** Jargon grading can only be
  audited out of **your own** transcripts — copy someone else's whitelist and you are checking
  your script against their audience. An empty vocab doesn't block you (one warning, that's it);
  `load_vocab()` loads yours.
- **A compliance layer + a "no link, no number" rule for the algorithm line** —
  [`knowledge/ai-content-compliance.md`](knowledge/ai-content-compliance.md) (R26-R38 + a 10-item
  pre-publish checklist) with 53 graded citations. Thresholds with no findable official source are
  now flagged in place instead of sitting next to sourced ones.
- **New tool [`src/teardown.py`](src/teardown.py)** — one command turns a rival's vertical video
  into comparable numbers (cuts/min, cut-gap median + stdev, caption rate, captions÷cuts, LUFS).
  OCR is **optional**: without it the tool skips caption extraction and still exits 0.

Full list (including two silent-failure fixes) → [CHANGELOG](CHANGELOG.md).

## Three **isomorphic** production lines (since v0.10)

This kit used to answer one question: "how do I make **one long-form video** well?" It now
runs three production lines — deliberately built in **the same shape**:
**a knowledge layer (why) → a mechanical gate (so nobody has to remember) → a one-command driver**.
Learn one and you've learned all three; adding a fourth (podcast? course series?) means
filling in the same three slots.

| Line | Knowledge layer (why) | Mechanical gate (blocks early) | One-command driver |
|---|---|---|---|
| **Teaching long-form** | `knowledge/premium-motion-fx.md` + `knowledge/meta-lessons.md` + the three script pillars ([`script-style-framework.md`](knowledge/script-style-framework.md) / [`script-retention-craft.md`](knowledge/script-retention-craft.md)) | `plan_gate` → [`script_gate`](src/longform_maker/script_gate.py) (audience language fails, rhythm warns) → `delivery_qa(profile='teaching_longform')` | the `src/longform_maker/` modules |
| **Vertical Shorts** | [`knowledge/shorts-mastery-2026.md`](knowledge/shorts-mastery-2026.md) + [`knowledge/vertical-teardown-method.md`](knowledge/vertical-teardown-method.md) (how to measure competitors' cuts) | [`src/longform_maker/shorts_gate.py`](src/longform_maker/shorts_gate.py) — nine blocking structure/caption rules + an S-O caption-rhythm warning; the duration band is **platform-aware** (the YouTube dead zone is not applied to IG/FB), **pure Python** | [`src/shorts_autopilot.py`](src/shorts_autopilot.py) — `scan` → write captions *from what's on screen* → `build` (with automatic QA proof images) |
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

## What's inside — one Editkin-first execution path

All three production lines (long-form / Shorts / interview) share the same Editkin v4 contract.
Public Python/ffmpeg modules provide planning, media preparation and QA; they are not a second
editor runtime.

| Layer | Module | What | Platform |
|---|---|---|---|
| **Editkin durable controller** | `src/workflow_contract.py` + `workflow_state.py` + receipts | Source-byte binding, per-material evidence, `edit-plan/v4`, audit, atomic apply, render, human review and outcome as a resumable DAG | Editkin-supported environment |
| **Long-form planning/media support** | `src/longform_maker/` | Premium motion, word-timestamp captions, screen cleanup, script and pacing gates; produces inputs for the Editkin plan | Win / Mac / Linux |
| **Shorts / vlog support** | `src/shorts_autopilot.py` + `src/silent_vlog_maker/` | 9:16 scan, contact sheets, normalization, Shorts gate, BGM and caption support | Win / Mac / Linux |
| **Interview planning** | `src/interview_autopilot.py` + `src/interview_gate.py` + `templates/interview/` | Invite, host script, questions, prep, consent, recording checklist, publish kit and Shorts cuts; unsourced claims are blocked before recording | Win / Mac / Linux |
| **Script / competitor measurement** | `src/longform_maker/script_gate.py` + [`src/teardown.py`](src/teardown.py) | Audience-language/retention gates plus cut rate, gap distribution, captions÷cuts and LUFS; OCR is optional and degrades cleanly | Win / Mac / Linux |
| **Editor-neutral QA** | `src/media_delivery_qa.py` + `src/delivery_media_ops.py` | Flash, dead air, caption sync, full-frame scan, audio/A-V, line breaks, BGM coverage and blurred-fill image preparation | Win / Mac / Linux |
| **Knowledge and compliance** | `knowledge/` | M-series pitfalls, editing craft, algorithms, AI-content compliance and graded sources; index → [`knowledge/README.md`](knowledge/README.md) | — |
| **Self-contained examples** | ▶️ `examples/` | Synthesized-media demos plus an Editkin v4 contract self-test; no real footage required | — |
| **Personalization** | ⭐ `SETUP.md` + `templates/` + `config.example.py` | Your voice, brand, material/export paths; no private settings from anyone else | — |

> Legacy editor GUI, draft JSON and Path A-E have retired from the public execution surface.
> Historical incidents remain in `knowledge/meta-lessons.md` as **benchmark-only**, never fallback.

### Platform support

| Module | Windows | macOS / Linux |
|---|---|---|
| Planning, media preparation, gates and QA | ✅ | ✅ (system paths & CJK fonts auto-detected by `src/platform_compat.py`) |
| Editkin structured execution | Per Editkin release support matrix | Per Editkin release support matrix |

## Quick start

1. Read **`SETUP.md`** → fill `templates/*.template.md` into `profiles/*.md`
   (or hand the repo to Claude / ChatGPT: *"ask me the SETUP.md questions and generate my profiles/"*)
2. `cp config.example.py config.py` → set Editkin project, media, candidate, QA and export paths
3. Install Python + ffmpeg; connect editable-timeline work to an Editkin structured-tool environment
4. Create a run with `python scripts/hao_autopilot.py workflow ...`, complete receipts from `next`, then audit before apply/render

## Install, upgrade old copies, and keep iterating (v0.14)

The repository now releases the complete executable core, public Codex Skill, updater, migrations
and rollback contract together. Fresh installs and pre-updater legacy copies use the same bootstrap:

When an old folder does not contain the bootstrap yet, download this one public file first. Future
compatible releases can iterate automatically only after that explicit one-time adoption:

```powershell
Invoke-WebRequest https://github.com/Hao0321/video-autopilot-kit/releases/latest/download/install_or_upgrade.py -OutFile install_or_upgrade.py
python install_or_upgrade.py --install-root . --check
python install_or_upgrade.py --install-root . --apply --install-skill
```

```bash
curl -fLO https://github.com/Hao0321/video-autopilot-kit/releases/latest/download/install_or_upgrade.py
python3 install_or_upgrade.py --install-root . --check
python3 install_or_upgrade.py --install-root . --apply --install-skill
```

Legacy adoption always requires explicit `--apply`; `--auto` cannot silently take ownership of a
non-empty unmanaged folder. Automatic updates begin only after a managed-file ledger exists.

```bash
python install_or_upgrade.py --install-root <your-folder> --check
python install_or_upgrade.py --install-root <your-folder> --apply --install-skill
```

- A release is applied only after the archive SHA-256 and every indexed file hash verify.
- The `shorts_autopilot.py` production entrypoint checks at most once every 24 hours and auto-applies only a
  compatible release, then re-execs once before continuing. You can still run `python src/release_manager.py auto` manually. `publish_hub.py` stays a pure delivery service so the updater and workspace migrator cannot form a reverse dependency cycle.
- Since v0.19, install/compatible upgrade non-destructively initializes `videos/_PUBLISH_HUB` and the root publishing shortcut, then registers existing `*/_out/current.mp4` artifacts with hardlinks. It never deletes or overwrites media, config, or unknown files.
- `config.py`, `profiles/`, `projects/`, `data/`, `videos/`, `assets/`, analytics and local outcomes
  stay local and are never overwritten by the updater.
- Unknown custom files are never removed. An automatic update stops with `CONFIRM_REQUIRED` when a
  managed file has local edits.
- Every replacement is backed up under `.video-autopilot/backups/<transaction>/`; use
  `python src/release_manager.py rollback` to restore it.
- Major or compatibility-window-breaking releases always require confirmation.

See the full contract in
[`codex-skill/video-autopilot/references/open-source-release-and-upgrade.md`](codex-skill/video-autopilot/references/open-source-release-and-upgrade.md).
Maintainers build the deterministic zip, `.sha256` and `release-channel.json` assets with
`python src/release_manager.py build --base-url <this version's GitHub release URL>`.

The suite boundary and definition of complete public functionality are documented in
[`docs/OPEN_SOURCE_SUITE.md`](docs/OPEN_SOURCE_SUITE.md).

## Requirements

**Public planning / media preparation / QA (Win / Mac / Linux)**
- Python 3.9+
- `ffmpeg` / `ffprobe` on PATH
- Reproducible Python/ffmpeg support; editable timelines always use the Editkin v4 contract
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
- The competitor teardown tool `src/teardown.py` has **two optional packages** (nothing else in
  the kit wants them): **`rapidocr-onnxruntime`** (measured here at roughly 25MB installed;
  it does not pull in torch or paddle) and
  **`opencc-python-reimplemented`** (simplified→traditional Chinese).
  - **What you lose without them**: only the step that pulls a rival's burnt-in captions back
    out as text. Cuts per minute, gap median/stdev, caption rate, the captions÷cuts verdict and
    LUFS **all still run, and the exit code is still 0** — the tool prints the install command
    and moves on.
  - OCR installed but not opencc → the script is still extracted, just not converted (you get a
    mix of simplified and traditional characters).
  - The statistics half (`rhythm_stats` / `pace_profile`) is **pure Python**, no ffmpeg either
    → `python examples/06_teardown.py`
  - ⚠️ **OCR only reads burnt-in captions (0.92-1.00). On real-world signage accuracy is ≈ 0 —
    and it still reports 0.85-0.92 confidence when it is wrong, so a confidence threshold cannot
    save you.** Use it to read *other people's* videos; never to auto-generate the product names
    or prices in your own → boundaries in
    [`knowledge/vertical-teardown-method.md`](knowledge/vertical-teardown-method.md) §2-8

**Editkin structured execution**
- An Editkin-supported client/server environment that returns receipts required by `workflow_contract.json`
- Current plan schema: `hao.video-autopilot.edit-plan/v4`; v1–v3 are import/view only
- Unknown apply state must reconcile; technical QA still requires real human review, never machine-authored certification

*(optional)* an AI assistant can also auto-generate your profiles from your `SETUP.md` answers.

## Philosophy

The most valuable part of a creator system is the **structure and methodology**, not one
person's private numbers. So this repo gives you the bones; you fill them with your own flesh.

## License

MIT — keep the notice and use / modify / sell freely.

## Author

Hao0321 Studio — an open-source framework distilled from a real personal creator system.
