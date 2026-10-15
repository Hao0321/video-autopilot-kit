#!/usr/bin/env python3
"""Creator-neutral public transforms for references and runtime knowledge."""
from __future__ import annotations

import json
import re

from public_privacy_legacy import (
    PUBLIC_FIXTURE,
    _between,
    _generalize_identity,
    _generalize_project_ids,
    _genre_copy_reference as _legacy_genre_copy_reference,
    _lf,
)


from public_privacy_reference_starters import (
    PUBLIC_BOUNDARY,
    PUBLIC_UNATTENDED_AUTONOMY,
    _unattended_autonomy,
    _mark_markdown,
    _replace_local_paths,
    _reference_base,
    PUBLIC_EDITING_MASTER,
    PUBLIC_AESTHETIC_STANDARD,
    _editing_master,
    _aesthetic_standard,
    PUBLIC_ASSET_WORKSHOP,
    _asset_workshop,
    PUBLIC_P0_CALIBRATION,
    _mrbeast_source_map,
    PUBLIC_TRACKING_CALIBRATION,
    _tracked_typography,
)


def _color_science(text: str) -> str:
    public = _reference_base(text)
    public = re.sub(r"(?m)^# creator 視覺大師", "# Creator Visual Master", public)
    public = public.replace("creator 人工審片", "designated human review")
    public = public.replace("交給 creator 審片", "交給指定人工作最後審查")
    return _editing_craft_boundary_link(_mark_markdown(public))


PUBLIC_NICHE_FONTS = '''# Shorts typography and color routing
> **PUBLIC_FIXTURE / privacy boundary:** no private palette verdict, dated feedback,
> local font inventory or maintainer preference; projects supply reviewed tokens.
## Semantic color roles
| Token | Purpose |
|---|---|
| `<TEXT_PRIMARY>` | normal captions with verified contrast |
| `<ACCENT_FACT>` | a price, measurement, place or key fact |
| `<ACCENT_ACTION>` | a single action or state change |
| `<SURFACE>` | restrained support panel when footage contrast varies |
| `<DANGER>` | verified warning or destructive action only |
## Routing and QA
- Start with one text color and one accent; add a role only when it carries distinct information. Test representative bright, dark and textured frames.
- Select fonts by language coverage, license, weight range, renderer support and small-screen legibility; use at most one display and one utility family with deterministic fallbacks.
- Niche is an input to tone, not a fixed palette. Map the brief to qualities such as warm, technical, playful, restrained or documentary, then choose project tokens.
- Verify family resolution, glyph fallback, line breaks, clipping, safe areas, dwell, contrast and color conversion on the final render.
- Record selected font files and tokens in the project receipt for reproducible rerenders.
'''
def _niche_fonts(_: str) -> str:
    return PUBLIC_NICHE_FONTS


PUBLIC_W6_PIP = '''### W6C-4. PiP profile contract
PiP face policy comes from the active project profile. No-face, face-cam, terminal comparison,
before/after and waiting-state PiP are separate semantic roles. Keep a stable corner, matching
aspect, safe margins and no overlap with captions or the active UI. PUBLIC_FIXTURE does not
encode a maintainer face preference or channel result.'''

PUBLIC_W6_CHAPTERS = '''### W6C-6. Chapter count by duration
Choose chapter count from duration, search intent and navigation value. Meet platform syntax,
keep titles unique and review whether chapters help the creator's own comparable releases.
PUBLIC_FIXTURE contains no maintainer duration band, channel baseline or prescribed count.'''

PUBLIC_W6_DEMO = '''### W6C-9. Result-first demo opening
For build/tool tutorials, a short verified result demo may establish the endpoint before the
walkthrough. Its duration and proof mix come from the brief and source evidence, not another
creator's opening pattern or project history.'''

PUBLIC_W6_SCREENCAST = '''### W6C-10. Screencast as B-roll
Record clean source video and drive timing from the approved narration or task structure.
Keep pointer movement intentional, preserve GUI continuity across cuts and retime only with
transparent evidence. The active profile decides whether live narration or separate voice is used.'''

PUBLIC_W6_EDL = '''### W6C-11. Auditable assisted-edit workflow
Pre-edit may synchronize, transcribe, detect silence and organize media. Decisions become a
diffable EDL/JSON proposal; waveform and transcript evidence remain inspectable, and automation
does not apply a cut before audit. PUBLIC_FIXTURE carries no private time-savings claim.'''

PUBLIC_W6_SEARCH = '''### W6C-12. Chapters as retrieval assets
Use auto chapters as a draft, then verify and rewrite labels from the approved script. Inspect
platform search/key-moment behavior after publishing with the creator's own evidence window.
PUBLIC_FIXTURE contains no private CTR, ranking or publishing result.'''


def _wave6(text: str) -> str:
    # Replace private sections before the generic base pass.  The base pass
    # deliberately drops appearance-policy lines, and one legacy section uses
    # that policy in its heading; running it first would erase the anchor.
    public = _replace_local_paths(
        _generalize_project_ids(_generalize_identity(_lf(text)))
    )
    for start, end, replacement in (
        ("### W6C-4.", "### W6C-5.", PUBLIC_W6_PIP),
        ("### W6C-6.", "### W6C-7.", PUBLIC_W6_CHAPTERS),
        ("### W6C-9.", "### W6C-10.", PUBLIC_W6_DEMO),
        ("### W6C-10.", "### W6C-11.", PUBLIC_W6_SCREENCAST),
        ("### W6C-11.", "### W6C-12.", PUBLIC_W6_EDL),
        ("### W6C-12.", "## 落地優先序", PUBLIC_W6_SEARCH),
    ):
        public = _between(public, start, end, replacement)
    public = re.sub(
        r"(?m)^\| W6C-4 \|.*$",
        "| W6C-4 | PiP face policy and placement come from the active project profile | profile + safe-area gate | ◐ review |",
        public,
    )
    return _mark_markdown(_reference_base(public))


PUBLIC_AUDIO_FIXTURE = '''> **PUBLIC_FIXTURE:** audio-chain defaults are configurable starters. Public docs do not
> include a private implementation folder, project loudness result, speed result or dated validation.
> Calibrate room tone, crossfade, loudness, ducking and speed from creator-owned media.'''


def _editing_craft(text: str) -> str:
    public = _reference_base(text)
    public = re.sub(r"(?m)^> ✅ \*\*上表 4 個音訊修正.*$", PUBLIC_AUDIO_FIXTURE, public)
    public = public.replace("creator 工作流必做", "when the active workflow removes speech errors")
    public = public.replace("creator pipeline", "the active creator pipeline")
    return _mark_markdown(public)


def _editing_craft_boundary_link(public: str) -> str:
    return public.replace(PUBLIC_BOUNDARY,
        "> PUBLIC_FIXTURE: [scope](editing-craft-fundamentals.md).")


def _editing_craft_part(text: str) -> str:
    return _editing_craft_boundary_link(_editing_craft(text))


def _native_reel_public_reference(_: str) -> str:
    return '''# Native graphic direction and public runtime boundaries

> PUBLIC_FIXTURE: generic planning guidance; no private scene, review permission,
> installed runtime or rendered-art approval is distributed here.

## Navigation

- Direction inputs and source evidence
- Runtime verification and review

## Direction inputs and source evidence

The public `native_graphic_direction.py` helper normalizes explicit direction
into design recipes. It does not edit an engine project or prove a renderer.
Use footage, narration and a brief that the creator owns. Give every visual
element a visible information task, a bounded source range and adequate reading
time. Keep text hierarchy, whitespace, color roles, edges and occlusion explicit.
Distinguish animation speed, duration, scale target and media playback speed.

The public workflow adapter handles the media route in contract revision 6 and
edit-plan v4. Private original-source, painted-revision and long-form controller
extensions are outside that adapter. Source files and fixtures must not be
presented as installed capabilities. See [workflow execution](editkin-workflow-execution.md)
and the [release contract](open-source-release-and-upgrade.md).

## Runtime verification and review

Discover the actual engine tools and require their current contract before an
edit. Apply an accepted plan atomically, reconcile uncertain completion and
render the committed revision. Bind review and outcome to the same artifact.
The creator's current review policy selects the reviewer; public examples do
not grant an agent permission to approve another creator's work.

Inspect complete dynamic sections at the target viewing size, including source
meaning, motion, crop, glyph edges, audio and reading holds. Synthetic tests,
source metadata and brief demonstrations do not certify a complete film,
reference-level art or competitor parity. A perspective plane is 2.5D; true
geometry needs its own implementation and evidence.
'''


PUBLIC_CRAFT_INDEX = '''# Editing craft index
> **PUBLIC_FIXTURE / privacy boundary:** reusable methods only; private signatures,
> review history, outcomes and exclusions stay in the local profile/evidence ledger.
## Read by task
| Task | Primary reference | Supporting reference |
|---|---|---|
| opening, retention and pacing | `editing-master-techniques.md` | `editing-wave5-finecut-2026.md` |
| continuity, audio and color | `editing-craft-fundamentals.md` | `color-science-and-visual-master.md` |
| tracked type and motion evidence | `tracked-typography-and-challenge-ledger.md` | `editing-wave6-2026.md` |
| asset generation and registration | `asset-workshop.md` | `template-compiler-v2.md` |
| short-form structure and QA | `shorts-mastery-2026.md` | `competitor-vertical-teardown-2026.md` |
| typography and color tokens | `niche-fonts-colors.md` | `hao-aesthetic-standard.md` |
| genre-specific routing | `genre-editing-craft-2026.md` | `genre-copy-grammar-2026.md` |
## Application order
1. Establish the claim, audience promise and evidence available in the project.
2. Choose the smallest relevant method set from the table above.
3. Compile a diffable plan with provenance/confidence, audit it, render and run delivery QA.
4. Require designated human review, then log comparable outcomes locally; promote only repeated evidence.
Project truth and platform requirements outrank style. Missing footage, transcript cues, rights or capability create an explicit hold, never a guessed substitution.
'''
def _craft_index(_: str) -> str:
    return PUBLIC_CRAFT_INDEX


def _template_compiler(text: str) -> str:
    return _editing_craft_boundary_link(_mark_markdown(_reference_base(text)))


PUBLIC_WAVE5 = '''# Fine-cut and retention craft
> **PUBLIC_FIXTURE / privacy boundary:** no maintainer outcome, private benchmark,
> dated correction, local sample or tool decision; numeric gates use project evidence.
## Fine-cut pass order
1. **Truth pass:** align every claim, caption and graphic with approved evidence.
2. **Story pass:** remove duplicated setup, preserve causality and make the payoff legible.
3. **Continuity pass:** check action, eyeline, screen direction, ambience and GUI state.
4. **Rhythm pass:** vary density around comprehension needs; do not cut on a fixed timer.
5. **Polish/delivery:** add only motivated sound, motion, color and type; render, inspect representative frames, audit audio and verify the artifact.
## Retention, evidence and audio
- Fulfil the packaging promise early; use questions, contrast, progress, proof and payoff as semantic interrupts, with comprehension holds after dense information.
- Bind each number/state to a source and time range. Tracking starts verified and hides on lost confidence; comparisons use matched scales, units and windows.
- Dialogue leads; preserve room tone/crossfades. Caption timing follows approved word timestamps and readable dwell, then passes line-break, safe-area, glyph and contrast QA.
- Store release conditions and measurement windows locally. One result is an observation; defaults stay reviewable and reversible until repeated evidence supports promotion.
'''
def _wave5(_: str) -> str:
    return PUBLIC_WAVE5


PUBLIC_AUTOPILOT_MODES = '''# Video Autopilot operating modes
> **PUBLIC_FIXTURE / privacy boundary:** no personal voice/CTA, local project ID,
> outcome baseline, dated verdict or retired-editor history; projects configure modes.
## Mode A — Plan
Input a topic, source inventory and targets. Produce an evidence-aware brief, script/shot/edit plan, packaging options, review contract and publish checklist. Required sources, rights and truth constraints must resolve before render.
## Mode B — Log outcome
Record release, platform, duration band, packaging variant, measurement window and available metrics locally. Preserve missing values as unknown.
## Mode C — Optimize patterns
Compare compatible releases only. Propose a reversible default with evidence, counterexamples and review condition; human approval is required.
## Build transaction
1. Bind the project contract, source hashes, knowledge version and output target.
2. Prepare bounded media evidence and derive semantics without mutating source files.
3. Audit a structured proposal, atomically apply one accepted plan, render and run technical QA.
4. Deliver the authoritative artifact for secure remote review, persist the receipt and publish only after approval.
Original media stays read-only; intermediates are disposable; current output updates atomically; history stores metadata/receipts. Private profiles, tokens, paths and ledgers are excluded. Missing capability creates a bounded hold and cannot bypass audit.
'''
def _autopilot_modes(_: str) -> str:
    return PUBLIC_AUTOPILOT_MODES


PUBLIC_COMPETITOR_TEARDOWN = '''# Vertical-video teardown method
> **PUBLIC_FIXTURE / privacy boundary:** no private sample inventory, source-account
> list, dated snapshot or verdict; retain only lawfully accessible project evidence.
## Research contract
1. Define platform, niche, duration band, audience intent and observation window.
2. Record a public source locator, capture date, visible interaction fields and uncertainty.
3. Separate observed facts from editorial inference; never estimate hidden analytics.
4. Compare matched cohorts and preserve weak/negative examples to reduce survivorship bias.
## Shot-level schema
For each segment record time range, shot role, subject, framing, motion, text role, caption dwell, transition, audio cue, claim evidence and confidence. Derive cut/information density and semantic interrupts.
## Analysis lenses
- **Opening:** first comprehensible promise, proof and unresolved question.
- **Pacing:** variation, comprehension holds and whether cuts follow meaning or action.
- **Typography:** hierarchy, safe-area use, line length, contrast and motion semantics.
- **Audio:** dialogue priority, music structure, effects and intentional silence.
- **Payoff:** whether the ending resolves the promise and supports an optional loop.
Extract functions, not identity. Rebuild with original layout, typography, assets and voice. Patterns stay hypotheses until tested against comparable creator-owned outcomes; never promise results.
Return an evidence table, uncertainty list, reusable hypotheses, blocked claims and a small experiment plan. Do not redistribute captured media, private notes or source lists.
'''
def _competitor_reference(_: str) -> str:
    return PUBLIC_COMPETITOR_TEARDOWN


def _genre_copy_reference(text: str) -> str:
    return _mark_markdown(_reference_base(_legacy_genre_copy_reference(text)))


PUBLIC_GENRE_EDITING = '''# Genre editing craft
> **PUBLIC_FIXTURE / privacy boundary:** reusable routes only; no preference profile,
> private source set, outcome, local path, appearance rule or dated review.
## Route by viewer job
| Viewer job | Editorial spine | Visual priority | Audio priority |
|---|---|---|---|
| learn a process | result → steps → verification | readable actions and proof | clear explanation |
| evaluate a product | claim → test → trade-off | matched comparisons | neutral continuity |
| experience a place | orientation → detail → reflection | location truth and sensory detail | natural ambience |
| understand a story | setup → change → consequence | causality and character state | motivated perspective |
| follow a challenge | rule → progress → obstacle → payoff | state and progress clarity | escalating contrast |
| watch an interview | premise → answer → evidence → implication | speaker/context clarity | speech continuity |
## Shared craft rules
- Establish the viewer job and packaging promise before selecting a genre style.
- Prefer verified footage and clean holds over unrelated generic B-roll.
- Use graphics for state, comparison, location or explanation, never decoration alone.
- Keep transitions motivated by movement, shape, time, place or narrative change.
- Let density follow comprehension and block unsupported claims at plan/render stages.
Each project may set tone, palette, typography, narration and pacing with local evidence and review. When rules conflict, viewer job, source truth and accessibility win.
Audit opening promise, evidence coverage, continuity, caption readability, audio intelligibility, rights, delivery and human approval. Log matched outcomes before proposing a default.
'''
def _genre_editing_reference(_: str) -> str:
    return PUBLIC_GENRE_EDITING


PUBLIC_SHORTS_MASTERY = '''# Short-form video mastery
> **PUBLIC_FIXTURE / privacy boundary:** no private channel samples, source locations,
> results, dated feedback or preference; thresholds are project configuration.
## Define the promise
Write one sentence naming what the viewer will understand, feel or see resolved. Bind opening, captions and payoff to it; narrow the promise when footage cannot support it.
## Segment contract
Each segment records source, valid time range, subject, role, claim evidence, caption, audio role and transition intent. Captions bind to segments and never guess unreadable facts.
## Opening
- Make the subject and value legible immediately with a verified close or clear state.
- Avoid logo-only lead-ins, unexplained atmosphere and promises whose proof appears too late.
- Cut on change in action, information or perspective; validate phone-sized with sound on/off.
## Pacing and loops
- Use shot changes, caption changes and audio beats as separate rhythm channels.
- Alternate density with comprehension holds. A loop is optional, preserves join continuity and never hides a false claim; calls to action follow the brief.
## Captions and graphics
- Use short, spoken-language lines with verified dwell, contrast, safe area and glyph coverage.
- Highlight semantic roles only. Persistent facts use a dedicated layer; generated telemetry, reconstructed signs and decorative UI are not evidence.
Duration, safe areas, metadata, music rights and link behavior are platform-specific; do not reuse one platform's heuristic as another's hard gate.
## QA and learning
1. Audit source/claim alignment, caption timing, continuity, audio and delivery settings.
2. Render the authoritative candidate and inspect opening, densest beat, payoff and loop join.
3. Require designated human approval, log comparable outcomes locally and promote only repeated matched evidence with reversible defaults.
'''
def _shorts_mastery(_: str) -> str:
    return PUBLIC_SHORTS_MASTERY


def _cleanup_changelog(text: str) -> str:
    return _mark_markdown(_replace_local_paths(text))


def _quality_corpus(text: str) -> str:
    data = json.loads(_lf(text))
    for case in data.get("negative_cases", []):
        if case.get("id") == "design-dna-not-compiled":
            case["message"] = "視覺計畫未經 creator-configured reference-set DNA 路由；需補題材、角色與畫幅 reflow。"
        elif case.get("id") == "unapproved-imagegen-selected":
            case["message"] = "Imagegen 生成物在 creator approval 前必須 human_review=pending、selectable=false；不得進正式渲染或自動路由。"
    data["public_distribution"] = "PUBLIC_FIXTURE: creator-specific review evidence is excluded."
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _design_trend_radar(text: str) -> str:
    data = json.loads(_lf(text))
    rules = list(data.get("hao_fusion_rules") or [])
    if len(rules) < 2:
        raise ValueError("design trend radar requires its compatibility rule list")
    rules[1] = "Creator-configured aesthetic hierarchy, typography and color discipline remain the base standard."
    data["hao_fusion_rules"] = rules
    data["public_distribution"] = "PUBLIC_FIXTURE: no private profile attribution or review outcome."
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


SANITIZERS = {
    "codex-skill/video-autopilot/references/unattended-autonomy-standard.md": _unattended_autonomy,
    "codex-skill/video-autopilot/references/editing-master-techniques.md": _editing_master,
    "codex-skill/video-autopilot/references/hao-aesthetic-standard.md": _aesthetic_standard,
    "codex-skill/video-autopilot/references/asset-workshop.md": _asset_workshop,
    "codex-skill/video-autopilot/references/mrbeast-production-source-map.md": _mrbeast_source_map,
    "codex-skill/video-autopilot/references/tracked-typography-and-challenge-ledger.md": _tracked_typography,
    "codex-skill/video-autopilot/references/color-science-and-visual-master.md": _color_science,
    "codex-skill/video-autopilot/references/niche-fonts-colors.md": _niche_fonts,
    "codex-skill/video-autopilot/references/editing-wave6-2026.md": _wave6,
    "codex-skill/video-autopilot/references/editing-craft-fundamentals.md": _editing_craft,
    "codex-skill/video-autopilot/references/editing-craft-picture-audio.md": _editing_craft_part,
    "codex-skill/video-autopilot/references/editing-craft-pacing-delivery.md": _editing_craft_part,
    "codex-skill/video-autopilot/references/native-reel-scenes.md": _native_reel_public_reference,
    "codex-skill/video-autopilot/references/craft-index.md": _craft_index,
    "codex-skill/video-autopilot/references/template-compiler-v2.md": _template_compiler,
    "codex-skill/video-autopilot/references/editing-wave5-finecut-2026.md": _wave5,
    "codex-skill/video-autopilot/references/autopilot-modes.md": _autopilot_modes,
    "codex-skill/video-autopilot/references/competitor-vertical-teardown-2026.md": _competitor_reference,
    "codex-skill/video-autopilot/references/genre-copy-grammar-2026.md": _genre_copy_reference,
    "codex-skill/video-autopilot/references/genre-editing-craft-2026.md": _genre_editing_reference,
    "codex-skill/video-autopilot/references/shorts-mastery-2026.md": _shorts_mastery,
    "knowledge/runtime/quality_corpus.json": _quality_corpus,
    "knowledge/runtime/design_trend_radar.json": _design_trend_radar,
    "tools/code-cleanup-helper/CHANGELOG.md": _cleanup_changelog,
}
