# 🎬 video-autopilot-kit

> Current version: v0.25.0
>
> **The architecture in one line: VA (this kit) plans, judges and checks; [Editkin](https://github.com/Hao0321/Editkin) does all rendering.**
> Material evidence → `edit-plan/v4` → audit → atomic apply → render → review → outcome learning, all governed by one
> execution contract, [`src/workflow_contract.py`](src/workflow_contract.py). As of v0.25.0 the old Python/FFmpeg
> renderers are retired (see "Retired" below).

> A **framework**, not a hand-me-down config. A resumable, auditable Editkin editing workflow
> and a set of quality gates, plus a questionnaire that asks about **your** channel and turns the
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

**Honest limits**: the public controller covers Editkin workflows for media material only. Offline
tests and CI use synthetic fixtures; they are not real Editkin renders, third-party account
operations or subjective art approval. Updates are run and confirmed by you; signed updates and
full security assurance are not claimed.

## 🧭 Architecture: VA plans and checks, Editkin renders

The full path of one edit:

`your media` → **VA** evidence receipts → **VA** writes `edit-plan/v4` → **Editkin** audit → **Editkin** atomic apply → **Editkin** render → **VA** delivery QA → **you** review → **VA** publish package and outcome learning

| VA (this kit, MIT) | Editkin (desktop editor, GPL-3.0, installed separately) |
|---|---|
| Per-material evidence chain: prepare → keyframes → transcript windows → semantic record | Reads media, extracts keyframes and transcripts |
| Writes `hao.video-autopilot.edit-plan/v4` with every receipt bound | Audit and one atomic apply |
| Gates for scripts, Shorts structure and captions, pacing, voice-over coverage and delivery QA | **All rendering**: motion graphics, templates, looks/filters, tracking, roto and subject matte |
| Review server, publish hub, outcome learning | Saves an editable project you can keep working on |

VA never drives Editkin directly: your AI agent (any MCP-capable agent) calls Editkin's MCP tools as
`workflow_contract.py` instructs, then hands the raw response back to the controller for verification.
One-page overview → [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## 🆕 What's new in v0.25.0

- **Rhythm-scene planner `src/rhythm_templates.py`**: turns a story JSON plus Editkin's current Motion
  Library catalog into a frame-exact scene plan — certified items only, every frame covered, a 2–5 s
  budget per scene (8–12 scenes by default for a 30 s video, explicitly overridable). It only plans and
  checks; it never renders or mutates an Editkin project, and it uses the Python standard library only.
  → [rhythm-scene-templates.md](codex-skill/video-autopilot/references/rhythm-scene-templates.md)
- **Editorial 2D/3D poster-style motion planning**:
  [editorial-hybrid-motion.md](codex-skill/video-autopilot/references/editorial-hybrid-motion.md) defines
  the per-scene job, tracking/occlusion tiers and the actual operating path. The context router now
  routes 2D/3D hybrid and motion-poster requests to it.
- **Editkin Motion Library**: 160 original effects (80 text animations, 40 transitions, 40 backgrounds),
  called through the Editkin modules `graphic.text_motion`, `transition.motion_pair` and
  `background.motion_loop`. It needs **an Editkin build that includes the Motion Library**; a public
  preview is being prepared separately — watch [Editkin releases](https://github.com/Hao0321/Editkin/releases).
  When a module is missing, VA records `NEW_MOTION_RUNTIME_REQUIRED` instead of silently falling back.
- **Review server security fix**: an authorised review save is re-checked at commit time. A session that
  expires or is revoked while the request body is being read can no longer write `review.json`.

## ▶️ See it run in 60 seconds (no media, no Editkin)

```bash
python examples/02_caption_broll_match.py # Editkin v4 contract: full DAG + fail-closed regression checks
python examples/04_shorts_gate.py         # Shorts gate: broken cut blocked → fixed → accepted on another platform
python examples/05_interview_plan.py      # interview gate: an unsourced guest number stopped *before* you record
```

Python 3.9+ only: no ffmpeg, no `pip install`, no real footage. See [`examples/README.md`](examples/README.md).

## 🎬 How one Editkin v4 run goes

```bash
python src/workflow_contract.py create --project <your-project.editkin.json> \
  --material clip-a=<real-source.mp4> --material clip-b=<another-source.mov>
python src/workflow_contract.py next <run>              # next ready steps (parallel ones are listed together)
python src/workflow_contract.py claim <run> <step>      # get a token plus the Editkin tool and arguments to call
python src/workflow_contract.py complete <run> <step> --token <token> --receipt <receipt.json>
python src/workflow_contract.py verify <run>            # verify the whole receipt chain before delivery
```

- Contract steps: contract → session → per-material prepare → keyframes → context → semantics →
  route + plugin discovery → plan v4 → audit → apply → render → visual review → outcome.
- Every source is bound as `CLIP_ID=SOURCE_FILE` to its real bytes (SHA-256); runs live inside the
  project under `videos/_AUTOPILOT/editkin-v4/`.
- If apply is interrupted and the commit cannot be proven, the run enters reconcile
  (`resume --apply-resolution ...`); automatic re-apply is forbidden.
- Green technical QA still requires real human review; a machine cannot write approved/certified.

Full state transitions → [`editkin-workflow-execution.md`](codex-skill/video-autopilot/references/editkin-workflow-execution.md);
when stuck → [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md).

## 🧱 Production lines and gates

Every line has the same shape: **knowledge layer (why) → mechanical gate (so nobody has to remember) → Editkin v4 run (execution)**.

| Line | Knowledge layer | Mechanical gate | Execution |
|---|---|---|---|
| **Teaching long-form** | [`script-style-framework.md`](knowledge/script-style-framework.md), [`script-retention-craft.md`](knowledge/script-retention-craft.md), [`premium-motion-fx.md`](knowledge/premium-motion-fx.md) | `plan_gate` → [`script_gate`](src/longform_maker/script_gate.py) → `pace_gate` → `editkin_voiceover_gate` → `final_delivery_qa(profile="teaching_longform")` | Editkin v4 run |
| **Vertical Shorts/Reels** | [`shorts-mastery-2026.md`](knowledge/shorts-mastery-2026.md), [`vertical-teardown-method.md`](knowledge/vertical-teardown-method.md) | [`shorts_gate`](src/longform_maker/shorts_gate.py): structure and caption rules; the duration band is **platform-aware** (the YouTube dead zone is not applied to IG/FB) | Editkin v4 run |
| **Rhythm scenes / brand motion** | [`rhythm-scene-templates.md`](codex-skill/video-autopilot/references/rhythm-scene-templates.md), [`editorial-hybrid-motion.md`](codex-skill/video-autopilot/references/editorial-hybrid-motion.md) | `rhythm_templates.py check`: frame coverage, reading time, certified items | Editkin Motion Library modules + v4 run |
| **Interview show** | [`interview-show-playbook.md`](knowledge/interview-show-playbook.md) | [`interview_gate`](src/interview_gate.py) (**a guest number with no source never airs**) + `plan_gate` | [`interview_autopilot.py`](src/interview_autopilot.py) `invite` → `plan` renders the 7-doc kit; the edit is a v4 run |

- **Shared gate shell** — [`src/longform_maker/gate_core.py`](src/longform_maker/gate_core.py) gives every gate the same
  return shape / `assert` message / self-test output. Your own gate imports three functions and behaves
  exactly like the built-ins (the rules themselves stay in each gate's own file).
- **Ops layer**: `src/channel_tracker.py` D2/D7/D28 snapshot scheduling + pending actions,
  `src/system_health.py` one-command GREEN/RED health check → [`knowledge/ops-automation.md`](knowledge/ops-automation.md);
  define-viral-with-your-own-data framework → [`knowledge/viral-playbook-framework.md`](knowledge/viral-playbook-framework.md).
- ⚠️ Every threshold in those gates is an **example calibration, not a universal law** — recompute them
  from **your own** 3-5 best videos (how-to in [SETUP.en.md](SETUP.en.md), "Shorts rule calibration").

## 📦 What's inside

| Layer | Module | What it does |
|---|---|---|
| **Editkin v4 controller** | `src/workflow_contract.py` + `workflow_contract.json` + `workflow_state.py`/receipts | Source-byte binding, per-material evidence, plan v4, audit, atomic apply, render, review and outcome as a resumable DAG |
| **Rhythm-scene planning** | `src/rhythm_templates.py` | Story + Motion Library catalog → frame-exact scene plan; `plan` / `check` |
| **Context router** | `src/context_router.py` | One small, stable context packet per job; routes requests to the matching reference |
| **Quality gates** | `src/longform_maker/`: `gate_core`, `plan_gate`, `pace_gate`, `script_gate*`, `shorts_gate*`, `editkin_voiceover_gate`, `music_engine` | Packaging-first, script, pacing, Shorts structure and captions, voice-over coverage, BGM beat analysis |
| **Caption quality** | `src/longform_maker/`: `word_captions`, `caption_grouping`, `caption_timeline` | Word-timestamp line breaking and grouping for caption-quality scanning |
| **Delivery QA** | `src/media_delivery_qa.py` + `src/delivery_media_ops.py` | Flash, dead air, caption sync, full-frame scan, audio/A-V, line breaks, BGM coverage |
| **Review and publishing** | `src/review_loop.py`, `src/publish_hub.py`, `src/outcome_learning.py`, `src/channel_tracker.py` | Review server, one publish package per video, outcome learning, D2/D7/D28 scheduling |
| **Interview planning** | `src/interview_autopilot.py` + `src/interview_gate.py` + `templates/interview/` | Invite, host script, questions, prep, consent, recording checklist, publish kit and Shorts cuts |
| **Competitor measurement** | [`src/teardown.py`](src/teardown.py) | Cut rate, gap distribution, captions÷cuts and LUFS; OCR is optional and degrades cleanly |
| **Health and updates** | `src/system_health.py`, `src/release_manager.py`, `install_or_upgrade.py` | One-command health check; hash-verified install, upgrade and rollback |
| **Knowledge and compliance** | `knowledge/` | Pitfall principles, editing craft, algorithms, AI-content compliance and graded sources; index → [`knowledge/README.md`](knowledge/README.md) |
| **Codex Skill** | `codex-skill/video-autopilot/` | The public Skill and references for AI agents |
| **Personalization** | ⭐ `SETUP.md` + `templates/` + `config.example.py` | Your voice, brand, material/export paths; no private settings from anyone else |

The suite boundary and definition of "complete" → [`docs/OPEN_SOURCE_SUITE.md`](docs/OPEN_SOURCE_SUITE.md).

## 🪦 Retired in v0.25.0

Editkin replaces these, and they no longer ship with the public kit:

- The pure-FFmpeg vlog/Shorts renderer (`src/silent_vlog_maker/`) and the old Shorts direct pipeline (`shorts_autopilot.py` and friends)
- The render half of `src/longform_maker/` (motion effects, screen-recording cleanup, brand cards, grading, transitions, asset forging, thumbnail templates and similar)
- The Python composition, filter, 3D, template-compiler, tracked-graphics, roto/keyer runtimes and the legacy visual director
- The bundled Cleanup tool → use its own repo, [claude-skill-code-cleanup](https://github.com/Hao0321/claude-skill-code-cleanup)
- The v6 architecture doc, examples 01/03 and some legacy references

**If you need the old FFmpeg pipelines, stay on tag [`v0.24.1`](https://github.com/Hao0321/video-autopilot-kit/tree/v0.24.1).**
Full list and migration notes → [CHANGELOG](CHANGELOG.md).

## Quick start

1. Read **`SETUP.en.md`** → fill `templates/*.template.md` into `profiles/*.md`
   (or hand the repo to Claude / ChatGPT: *"ask me the SETUP.md questions and generate my profiles/"*)
2. `cp config.example.py config.py` → set your project, media and export paths
3. Install Python 3.9+ and ffmpeg; set up Editkin (built from source today — see "Requirements") and let your AI agent call its MCP tools
4. `python src/system_health.py --quick` to validate a clean install
5. Create a run with `python src/workflow_contract.py create ...`, complete receipts step by step from `next`, then audit before apply/render

## Install, upgrade old copies, and update

The repository releases the complete executable core, public Codex Skill, updater, migrations
and rollback contract together. Fresh installs and pre-updater legacy copies use the same bootstrap:

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
non-empty unmanaged folder. Later compatible releases can be applied with `--auto` only after a
managed-file ledger exists.

**Updates are now manual.** In v0.24.x the 24-hour automatic check ran from the retired Shorts
entry point; from v0.25.0 nothing checks for updates on its own. To update, run:

```bash
python install_or_upgrade.py --install-root <your-folder> --check
python install_or_upgrade.py --install-root <your-folder> --apply --install-skill   # recommended: also syncs the Skill and workspace layout
python src/release_manager.py auto       # or: checks at most once per 24 hours, applies compatible releases only
```

- A release is applied only after the archive SHA-256 and every indexed file hash verify.
- `config.py`, `profiles/`, `projects/`, `data/`, `videos/`, `assets/`, analytics and local outcomes
  stay local and are never overwritten by the updater.
- Unknown custom files are never removed. An automatic update stops with `CONFIRM_REQUIRED` when a
  managed file has local edits.
- Managed files that a new release no longer ships (such as the modules retired in v0.25.0) are
  backed up and then removed. Every replacement or removal is backed up under
  `.video-autopilot/backups/<transaction>/`; use `python src/release_manager.py rollback` to restore it.
- After an install or upgrade through `install_or_upgrade.py`, `videos/_PUBLISH_HUB` and the root
  publishing shortcut are initialized non-destructively. Media, config and unknown files are never deleted or overwritten.
- Major or compatibility-window-breaking releases always require confirmation.

See the full contract in
[`open-source-release-and-upgrade.md`](codex-skill/video-autopilot/references/open-source-release-and-upgrade.md).
Maintainers build the deterministic zip, `.sha256` and `release-channel.json` with
`python src/release_manager.py build --base-url <this version's GitHub release URL>`, then
publish those three together with the root `install_or_upgrade.py` as four release assets.

> Safety boundary: what updates is a **compatible, verified public core** — never anyone's private
> footage, data, settings or media of unclear licence. A complete open-source release and protecting
> user data must both hold.

## Requirements

**VA (Win / Mac / Linux)**
- Python 3.9+
- `ffmpeg` / `ffprobe` on PATH (used by delivery QA and teardown)
- Media-analysis dependencies: `python -m pip install -r requirements-media.txt` (version-pinned; CI and
  the release workflow consume the same file)
- Mac/Linux: system paths and CJK fonts are auto-detected by `src/platform_compat.py` (don't hardcode system font paths)
- **Runs with no dependencies at all**: `workflow_contract.py`, `rhythm_templates.py` and examples 02/04/05.
  The Shorts gate `src/longform_maker/shorts_gate.py` is pure Python — import it **flat** (put
  `src/longform_maker/` on `sys.path` and `from shorts_gate import …`, as example 04 does) so you don't go
  through the package `__init__` and the zero-dependency promise really holds.
- The interview line is **pure Python for the entire pre-production stage** — rendering the 7-doc kit needs
  no ffmpeg and no pip packages → `python examples/05_interview_plan.py`
- The competitor teardown tool `src/teardown.py` has **two optional packages**: **`rapidocr-onnxruntime`**
  (OCR) and **`opencc-python-reimplemented`** (simplified→traditional Chinese).
  - **What you lose without them**: cut statistics (cuts per minute, gap distribution) and LUFS still run;
    the caption-based measurements that need OCR (caption rate, the captions÷cuts verdict, the extracted
    script) are skipped with an install hint, **and the exit code is still 0**.
  - ⚠️ **OCR only reads burnt-in captions; on real-world signage it reads almost nothing, and it still
    reports high confidence when it is wrong, so a confidence threshold cannot save you.** Use it to read
    *other people's* videos; never to auto-generate the product names or prices in your own → boundaries in
    [`knowledge/vertical-teardown-method.md`](knowledge/vertical-teardown-method.md) §2-8

**Editkin**
- Editkin is currently public as **source** ([repo](https://github.com/Hao0321/Editkin)); official downloads have not
  been released yet and will be announced on [Editkin releases](https://github.com/Hao0321/Editkin/releases). To use it
  now, build it from source following the Editkin README (rendering needs the desktop build; the browser build
  cannot export video).
- Connecting your agent: start Editkin with `npm run mcp` in your agent's MCP configuration and set
  `EDITKIN_VIDEO_AUTOPILOT_SKILL` to the absolute path of this kit's `codex-skill/video-autopilot/SKILL.md`
  (the Editkin README is authoritative for the details)
- Your AI agent must be able to call Editkin's MCP tools and return the receipts required by `workflow_contract.json`
- Current plan schema: `hao.video-autopilot.edit-plan/v4`; legacy schemas fail closed and can never enter audit or apply
- Motion Library effects need an Editkin build that includes the Motion Library; a missing module records `NEW_MOTION_RUNTIME_REQUIRED`

*(optional)* an AI assistant can also auto-generate your profiles from your `SETUP.md` answers.

## Philosophy

The most valuable part of a creator system is the **structure and methodology**, not one
person's private numbers. So this repo gives you the bones; you fill them with your own flesh.

## License

MIT — keep the notice and use / modify / sell freely. Editkin is a separate project under GPL-3.0 and is not bundled with this kit.

## Author

Hao0321 Studio — an open-source framework distilled from a real personal creator system.
