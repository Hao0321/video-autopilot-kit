# Architecture: VA ↔ Editkin

> 中文摘要：VA（這個 kit）負責規劃、判斷與檢查；Editkin 負責所有渲染，並存成可繼續編輯的專案。
> 兩者之間只有一份執行合約：`src/workflow_contract.py` + `workflow_contract.json`。
> 安裝順序：先裝 Editkin → 接上你的 AI → 再裝這個 kit（見 [SETUP.md 步驟 0](../SETUP.md#步驟-0先裝-editkin)）。

Current as of v0.25.0.

## Installation order

Install Editkin first; without it nothing gets edited or rendered. Editkin's public preview is a Windows
installer ([v0.15.0-preview.20261022](https://github.com/Hao0321/Editkin/releases/tag/v0.15.0-preview.20261022);
all versions on the [releases page](https://github.com/Hao0321/Editkin/releases)). Next, connect your AI from
Editkin's start screen (**Edit with AI assistance** → **Connect AI assistant** → **Connect Claude Code** or
**Connect Codex**), restart the AI and check that `/mcp` lists `editkin`. Last, install this kit with
`install_or_upgrade.py --apply --install-skill`, which puts its Skill at
`%USERPROFILE%\.codex\skills\video-autopilot\` so that Editkin's full Video Autopilot flow (**Copy start
instructions**) can find it; `EDITKIN_VIDEO_AUTOPILOT_SKILL` can point at the Skill's `SKILL.md` instead.
Step by step → [SETUP.en.md, Step 0](../SETUP.en.md#step-0-install-editkin-first).

## Two programs, one contract

| | **VA** — video-autopilot-kit (this repository, MIT) | **Editkin** — desktop editor ([repo](https://github.com/Hao0321/Editkin), GPL-3.0, separate project) |
|---|---|---|
| Role | Plans, judges and checks | Renders and keeps the editable project |
| Owns | Material evidence receipts, the `edit-plan/v4` document, gates, delivery QA, review, publishing, outcome learning | Media preparation, plan audit, atomic apply, render, motion graphics, templates, looks/filters, tracking, roto and subject matte |
| Boundary in this workflow | Never renders pixels, never mutates the Editkin project directly, never signs human approval | Receives edits only through the contract's ordered steps: apply follows an accepted audit, render follows a committed apply |

An MCP-capable AI agent connects the two. The VA controller tells the agent which Editkin MCP
tool to call next and with which arguments; the agent calls it and hands the raw result back; the
controller verifies and seals the receipt. Editkin code is not bundled in this kit. Most users
install Editkin's Windows public preview (see "Installation order" above); developers can build it
from source, and its README describes the build, the `npm run mcp` server and the
`EDITKIN_VIDEO_AUTOPILOT_SKILL` setting that points at this kit's `SKILL.md`.

## The run

```text
contract → session
        → per material: prepare → keyframes → context → semantics   (materials may run in parallel)
        → route + plugin discovery                                   (parallel)
        → plan (hao.video-autopilot.edit-plan/v4)
        → audit → apply (exactly once) → render
        → visual review (human) → outcome
```

- **Source binding.** Every source file is bound as `CLIP_ID=SOURCE_FILE` and hashed (SHA-256) from
  its real bytes. Changed bytes invalidate downstream receipts.
- **Evidence before plan.** Semantics may cite only keyframes that were actually viewed or transcript
  cues that were actually loaded.
- **One plan schema.** Only `hao.video-autopilot.edit-plan/v4` may enter audit or apply; legacy
  schemas fail closed.
- **Exactly-once apply.** If an interrupted apply cannot be proven committed, the run enters
  reconcile; automatic re-apply is forbidden.
- **Human review stays human.** Green technical QA never becomes approval; machines cannot write
  approved/certified.

Runs live inside the project under `videos/_AUTOPILOT/editkin-v4/`. CLI:
`python src/workflow_contract.py` with `create`, `status`, `next`, `claim`, `complete`, `fail`,
`resume`, `verify`, `selftest` and more (`--help`).
Details → [`editkin-workflow-execution.md`](../codex-skill/video-autopilot/references/editkin-workflow-execution.md).

## What sits around the contract (VA side)

| Concern | Where |
|---|---|
| Context packets and reference routing | `src/context_router.py` |
| Rhythm-scene planning (frame-exact, certified Motion Library items, 2–5 s scenes) | `src/rhythm_templates.py` → [rhythm-scene-templates.md](../codex-skill/video-autopilot/references/rhythm-scene-templates.md) |
| Editorial 2D/3D poster-style motion planning | [editorial-hybrid-motion.md](../codex-skill/video-autopilot/references/editorial-hybrid-motion.md) |
| Script, Shorts structure/captions, pacing, voice-over coverage, packaging gates | `src/longform_maker/` (`gate_core`, `plan_gate`, `pace_gate`, `script_gate*`, `shorts_gate*`, `editkin_voiceover_gate`, `music_engine`) |
| Caption-quality scanning | `src/longform_maker/` (`word_captions`, `caption_grouping`, `caption_timeline`) |
| Delivery QA on the rendered candidate | `src/media_delivery_qa.py`, `src/delivery_media_ops.py` |
| Review server, publish hub, outcome learning | `src/review_loop.py`, `src/publish_hub.py`, `src/outcome_learning.py` |

## Motion Library boundary

Editkin's Motion Library (80 text animations, 40 transitions, 40 backgrounds) is reached only through
the Editkin modules `graphic.text_motion`, `transition.motion_pair` and `background.motion_loop`.
It needs an Editkin build that includes the Motion Library; the Editkin public preview
([v0.15.0-preview.20261022](https://github.com/Hao0321/Editkin/releases/tag/v0.15.0-preview.20261022))
includes it. VA discovers modules per session and records `NEW_MOTION_RUNTIME_REQUIRED` when one is
missing — it never silently falls back to an older effect and has no animation engine of its own.

## What is not here any more

v0.25.0 retired every Python/FFmpeg rendering path from the public kit (the silent-vlog and Shorts
renderers, the render half of `longform_maker`, and the composition, filter, 3D, template-compiler,
tracked-graphics, roto/keyer and visual-director runtimes). Editkin replaces them. The last release
that contains them is tag [`v0.24.1`](https://github.com/Hao0321/video-autopilot-kit/tree/v0.24.1);
see the [CHANGELOG](../CHANGELOG.md) for the full list.
