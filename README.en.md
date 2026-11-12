# 🎬 video-autopilot-kit

> Current version: v0.28.0
>
> **The architecture in one line: VA (this kit) plans, judges and checks; [Editkin](https://github.com/Hao0321/Editkin) does all rendering.**
> Material evidence → `edit-plan/v4` → audit → atomic apply → render → review → outcome learning, all governed by one
> execution contract, [`src/workflow_contract.py`](src/workflow_contract.py). As of v0.25.0 the old Python/FFmpeg
> renderers are retired (see "Retired" below).

## 🧩 Install Editkin first (required)

VA only plans and checks; **Editkin is what actually edits and renders**. Without Editkin, nothing gets
edited. Go in this order:

1. **Install Editkin**: download the Windows installer (about 1.5 GB) from
   [Editkin 0.16.0](https://github.com/Hao0321/Editkin/releases/tag/v0.16.0).
   This build is not code-signed: when you see "Windows protected your PC", click **More info** → **Run anyway**.
   → [Details](SETUP.en.md#0-1-download-and-install)
2. **Connect your AI**: on Editkin's start screen, **Edit with AI assistance** → **Connect AI assistant** →
   **Connect Claude Code** or **Connect Codex** (one-click setup). After you restart Claude Code / Codex, `/mcp`
   should list `editkin`. If you are upgrading from 0.15.0, connect once more. A hand-written MCP entry should
   add `EDITKIN_MCP_PROFILE = "va"` under its env (it saves tokens). → [Details](SETUP.en.md#0-3-connect-your-ai)
3. **Install this Kit**: download the Kit's `install_or_upgrade.py`, run
   `python install_or_upgrade.py --install-root <folder> --check`, then run it again with `--apply --install-skill`
   instead of `--check`. The Skill goes to `%USERPROFILE%\.codex\skills\video-autopilot\`, where Editkin's
   **Copy start instructions** finds it. → [Details](SETUP.en.md#0-4-install-this-kit)

Just want to try it? Editkin's built-in **simple mode needs no AI account**: add a horizontal video of someone
talking and it makes a rough cut for you.
Editkin 0.16.0 is Windows only for now and has no automatic updates. Get new versions from
[Editkin releases](https://github.com/Hao0321/Editkin/releases).

**Editkin's licence**: Editkin is **free, closed-source freeware**. Its EULA allows personal and commercial use,
perpetually (`EULA.txt` is attached to the release and in the install folder). The GPL-3.0 source is frozen at
0.15.0-preview.20261029 and is no longer updated; from 0.16.0 Editkin ships as an installer only. This kit stays
MIT and does not bundle, vendor or update Editkin.

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

| VA (this kit, MIT) | Editkin (desktop editor, free closed-source freeware, installed separately) |
|---|---|
| Per-material evidence chain: prepare → keyframes → transcript windows → semantic record | Reads media, extracts keyframes and transcripts |
| Writes `hao.video-autopilot.edit-plan/v4` with every receipt bound | Audit and one atomic apply |
| Gates for scripts, Shorts structure and captions, pacing, voice-over coverage and delivery QA | **All rendering**: motion graphics, templates, looks/filters, tracking, roto and subject matte |
| Review server, publish hub, outcome learning | Saves an editable project you can keep working on |

VA never drives Editkin directly: your AI agent (any MCP-capable agent) calls Editkin's MCP tools as
`workflow_contract.py` instructs, then hands the raw response back to the controller for verification.
One-page overview → [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## 🆕 What's new in v0.28.0

A maintenance and cleanup release with no new features; v0.27.0 had no separate release and is superseded by this
one. The execution contract (revision 6) and the workflow executable sources are unchanged. The bundled Skill changed
in two files (`SKILL.md` and the shot-selection reference): a run binds the hash of the installed `SKILL.md`, so finish
runs started on v0.26 or v0.27 before re-syncing the Skill, or start new runs afterwards.

- **Shot-selection reference trimmed to general rules**: `references/shot-selection-language.md` is now a short,
  fixed set of general shot-selection rules, and `SKILL.md` points to them. The public sync always publishes that
  fixed text and stops if anything else would be published (tested).

- **A copy can no longer overwrite the canonical Skill**: for a Skill the manifest declares canonical
  (`source_authority`), `project_kernel.py sync apply` returns `REFUSED` and writes nothing when the source is another
  copy, even with `--accept-source-conflicts`, and a copy inside the workspace is never accepted as the canonical
  Skill; `skill_sync.py sync` no longer overwrites `~/.codex/skills/video-autopilot` from another folder. New
  `project_kernel.py sync record` re-records hashes from the canonical tree itself and never copies. The stock public
  manifest declares no canonical Skill, so `project_kernel.py` behaves as before by default.
- **Manifest paths can point into a Skill**: `required_paths`, the knowledge line budgets and the source audit
  accept `@<skill-id>/<relative path>`, resolved against that Skill's folder: its canonical folder for a Skill with
  `source_authority` (kept outside the workspace), its `source` folder for a workspace-authored Skill (the public
  manifest does not use it yet).
- **Central project-root discovery**: `asset_license_governance.py` uses `project_paths.discover_project_root()`,
  falling back to the kit root.
- **Ops check on demand**: [knowledge/ops-automation.md](knowledge/ops-automation.md) now says to run
  `channel_tracker.py` when you want to know what is due, instead of scheduling a daily AI task. Stale paths are
  fixed (the state file is `data/channel_state.json`; delivery QA is `final_delivery_qa()` in `media_delivery_qa.py`).
- **Not in this release**: the work on VA's first-draft quality is still in progress and is not part of this
  release.

## 🆕 What's new in v0.27.0

Documentation and install guidance only; no code, execution contract or Skill file changed.

- **Install Editkin 0.16.0**: the install links now point to
  [Editkin 0.16.0](https://github.com/Hao0321/Editkin/releases/tag/v0.16.0) (Windows x64, marked Latest). Editkin
  is now free, closed-source freeware whose EULA allows perpetual personal and commercial use; the GPL-3.0 source
  is frozen at 0.15.0-preview.20261029.
- **Token-lean MCP profile**: Editkin's one-click **Connect AI assistant** writes `EDITKIN_MCP_PROFILE=va`; a
  hand-written Codex or Claude Code `editkin` entry should add `EDITKIN_MCP_PROFILE = "va"` under its env. Without
  it Editkin uses `compat`, about 54k tokens of tool definitions per turn, against about 4k with `va`
  (approximate, from Editkin's own profile byte budgets). → [SETUP.en.md 0-3](SETUP.en.md#0-3-connect-your-ai)
- **Editkin 0.16.0 tools worth knowing**:
  - `make_video` / `revise_video` (**experimental**, opt-in, listed in the `full` profile): one call turns
    workspace media and one sentence into a draft built only from certified items and returns one contact sheet
    and a short summary (about 2 KB or less); `revise_video` makes up to three changes per call. This lane does
    not produce the v4 receipts `workflow_contract.py` verifies; **VA's default lane is still the Editkin v4
    workflow (contract revision 6)**.
  - **Aesthetic floor**: render, `seal` and delivery approval can return `BLOCK_AESTHETIC`; READY also needs a
    visual-review rubric receipt. → [TROUBLESHOOTING.md](TROUBLESHOOTING.md#輸出被擋下block_aesthetic)

## 🆕 What's new in v0.26.0

- **The long-form flow is now in the public kit**: `python src/workflow_contract.py create-longform --session
  <session.json>` (all other flags as in `create`) creates a run where one long-form video is one Editkin
  project, one `edit-plan/v4` per chapter, one atomic set apply and one render. A session has up to 16
  chapters and 96 materials (32 per chapter); every frame in a chapter plan must stay inside that chapter's
  range, and the controller seals the plan set deterministically, rejecting any chapter file that changes
  afterwards. The DAG comes from `workflow_longform_contract.json` (revision 1); the revision-6
  `workflow_contract.json` keeps its exact bytes and the `create` and Shorts flows are unchanged.
  → [editkin-workflow-execution.md](codex-skill/video-autopilot/references/editkin-workflow-execution.md)
- **Needs an Editkin build with long-form sets**: Editkin's `get_autopilot_contract` must advertise
  `contract.longformPlanSet` (`audit_longform_plan_set` / `apply_longform_plan_set`); otherwise the run stops
  with `LONGFORM_CAPABILITY_MISSING` before any material is prepared.
- **Re-sync the Skill after upgrading**: the installed Skill must contain `workflow_longform_contract.json`
  (`install_or_upgrade.py --apply --install-skill` or `python src/release_manager.py install-skill`);
  otherwise `create-longform` stops with `LONGFORM_CONTRACT_MISSING`. Runs created before the upgrade are
  bound to the previous code and are blocked afterwards; finish them first or start a new run.

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
  `background.motion_loop`. It needs **an Editkin build that includes the Motion Library**: the
  [Editkin public preview v0.15.0-preview.20261022](https://github.com/Hao0321/Editkin/releases/tag/v0.15.0-preview.20261022)
  includes it (still a preview, so expect bugs). When a module is missing, VA records
  `NEW_MOTION_RUNTIME_REQUIRED` instead of silently falling back.
- **Vertical Shorts match the Editkin preview**: the Kit now accepts Editkin's default `kinetic` cadence, so
  vertical Shorts run end to end with this Kit version and the Editkin preview above.
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

1. **Install Editkin, connect your AI, install this Kit**: the three steps in "Install Editkin first (required)"
   above; details in [SETUP.en.md Step 0](SETUP.en.md#step-0-install-editkin-first)
2. Read **`SETUP.en.md`** → fill `templates/*.template.md` into `profiles/*.md`
   (or hand the repo to Claude / ChatGPT: *"ask me the SETUP.md questions and generate my profiles/"*)
3. `cp config.example.py config.py` → set your project, media and export paths
4. Install Python 3.9+ and ffmpeg (used by delivery QA)
5. `python src/system_health.py --quick` to validate a clean install
6. Create a run with `python src/workflow_contract.py create ...`, complete receipts step by step from `next`, then audit before apply/render

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
- Install [Editkin 0.16.0](https://github.com/Hao0321/Editkin/releases/tag/v0.16.0)
  (Windows 10/11 64-bit only for now; free closed-source freeware; not code-signed, no automatic updates) — steps
  in [SETUP.en.md Step 0](SETUP.en.md#step-0-install-editkin-first). Connect Claude Code or Codex in one click from
  Editkin's start screen; when `/mcp` lists `editkin`, you are connected. A hand-written MCP entry should add
  `EDITKIN_MCP_PROFILE = "va"` under its env
- The GPL-3.0 source in the [Editkin repo](https://github.com/Hao0321/Editkin) is frozen at
  0.15.0-preview.20261029 and does not contain the 0.16.0 changes; from 0.16.0 the source is not published
- Editkin's full Video Autopilot flow (**Copy start instructions**) must find this kit's Skill: at
  `%USERPROFILE%\.codex\skills\video-autopilot\` (where `install_or_upgrade.py --install-skill` puts it), or set
  `EDITKIN_VIDEO_AUTOPILOT_SKILL` to the absolute path of its `SKILL.md`
- Your AI agent must be able to call Editkin's MCP tools and return the receipts required by `workflow_contract.json`
- Current plan schema: `hao.video-autopilot.edit-plan/v4`; legacy schemas fail closed and can never enter audit or apply
- Motion Library effects need an Editkin build that includes the Motion Library (0.16.0 does); a missing module records `NEW_MOTION_RUNTIME_REQUIRED`

*(optional)* an AI assistant can also auto-generate your profiles from your `SETUP.md` answers.

## Philosophy

The most valuable part of a creator system is the **structure and methodology**, not one
person's private numbers. So this repo gives you the bones; you fill them with your own flesh.

## License

MIT — keep the notice and use / modify / sell freely. Editkin is a separate project: from 0.16.0 it is free,
closed-source freeware (its EULA allows perpetual personal and commercial use), and its GPL-3.0 source is frozen at
0.15.0-preview.20261029. Editkin is not bundled with this kit.

## Author

Hao0321 Studio — an open-source framework distilled from a real personal creator system.
