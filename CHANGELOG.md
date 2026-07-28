# Changelog

All notable changes to **video-autopilot-kit** are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [0.11.0] — 2026-07-28

**A borrowed number wearing an authority label is worse than no number at all.** Four unrelated
parts of the kit turned out to be making the same mistake, so this release fixes it four times.
The Shorts gate shipped **one duration band for every platform** — but the dead zone inside it
was measured on *YouTube* Shorts, and a frame-by-frame teardown of a batch of IG/FB vertical
videos found normal-performing cuts sitting right inside that window; a rule like that doesn't
merely fail to help, it makes your cut worse, because you trust it. `script_gate` shipped a
**jargon whitelist derived from one creator's transcripts** — copy that and you are checking
*your* script against *somebody else's* audience: it waves through the words your viewers don't
know and blocks the ones they've known for years, and you believe it either way. The algorithm
playbook quoted **retention thresholds with no citable source** next to ones that had them. And
the new competitor-teardown tool's OCR reports 0.85-0.92 confidence *while being wrong*, so a
confidence threshold cannot save you from it.

So: the duration band is now **platform-aware**; the four audience word-lists now **ship empty**
with the recipe for building your own; unsourced thresholds are **flagged in place** and a
compliance knowledge base with 53 graded citations lands to enforce **no link, no number**; and
the OCR's boundaries are written into the tool itself rather than left to the reader's judgment.
The two findings that came out of that teardown ship as **a warning and a description, never a
block**, because the batch they came from was all successes with no failure control group —
uncertain knowledge reports numbers, it doesn't hand out verdicts. Nothing here removes a
capability. It removes borrowed certainty.

### Added

**Vertical-Shorts line — the band stops pretending YouTube is every platform**
- **`PLATFORM_RULES` in `src/longform_maker/shorts_gate.py`** — `yt_shorts` (13-25s, dead zone
  26-44s) / `ig_reels` / `fb_reels` (13-60s, no dead zone). Set `spec["platform"]`; omit it and
  you get `DEFAULT_PLATFORM = "yt_shorts"`, which is **byte-for-byte the v0.10 behavior**
  (`DEFAULT_RULES` is now expanded *from* that platform entry, so the table and the defaults
  cannot drift apart). The platform only supplies **defaults for the three duration keys** —
  `rules={...}` is applied afterwards and still wins per key, so you can name a platform and
  narrow its band in the same call. An unrecognized platform name is a **blocking S-B failure**,
  never a silent fallback; `merge_rules(rules, platform)` raises on it, exactly like a typo'd
  rule key. `report["platform"]` records which band was applied.
- **`S-O` caption-rhythm rule (warn level) in `shorts_gate.py`** — a median content-caption dwell
  above `cap_dwell_warn` (1.8s), or fewer than `cap_rate_warn` (30) caption changes per minute,
  produces a warning, and the report carries the two measurements (`cap_rate` / `cap_dwell`)
  whether or not it fires. Measured across the sample batch, **every single video changed
  captions faster than it changed shots** — one of them cut 5 times in 32 seconds while changing
  captions 40 times. The actionable form: when you're short on footage, let the captions carry
  the pace instead of forcing cuts. It **never blocks a build** — the batch was all successful
  videos with no failure control, and a rule that fires on every normal cut just gets ignored.
  New letter deliberately skips S-M / S-N, which the knowledge file already owns as
  human-judgment items (v0.10.0 had to fix an S-B / S-H collision caused by exactly this).
- **`knowledge/vertical-teardown-method.md`** — how to tear down a vertical video with `ffmpeg`
  alone, written so you can run it on your own competitors: scene-detection for cut rate,
  the same detector **cropped to the caption band** (at a much lower threshold) for caption-change
  rate, ASR for speech rate, and a dependency-free snippet that turns the timestamps into
  cuts/min + median gap + gap stdev + lines/min + median dwell. Includes the traps: `-v error`
  **swallows `showinfo` output** (it logs at info level on stderr, so you get an empty list and
  conclude the video has no cuts); every threshold must be hand-checked against a manually
  counted 10-second window before the numbers mean anything; and platform loudness normalization
  makes integrated-loudness readings say nothing about the author's choices. Then the findings:
  three rhythm archetypes separated by **cut-gap standard deviation** (beat-locked ≈0.03-0.32 vs
  narrative-arc ≈0.9 vs static/text-driven ≈1.5-3.4), font choice driven by **background
  busyness** rather than taste, prices as standalone display type, post skeletons (structure and
  sentence patterns only — no source text), and post length determined by where the CTA lives.
  Sample boundary stated up front: n=7, all successes, no failure control, front-of-house
  numbers only — so "coexists with success" is not "causes success".
- **`src/teardown.py` — one command turns a rival's vertical video into comparable numbers.**
  `python src/teardown.py <file-or-folder>` prints cuts/min, the cut-gap distribution
  (median + stdev + shortest), caption-change rate, the **captions÷cuts** verdict that says
  whether the clip is paced by editing or by text, and integrated loudness. **Dependency-tiered
  on purpose**: `ffmpeg`/`ffprobe` are required; `rapidocr-onnxruntime` (~25MB installed here,
  pulls in neither torch nor paddle) and `opencc-python-reimplemented` are **optional** — without
  them the tool skips caption extraction, prints the install command, and **still exits 0** with
  every rhythm number intact. ⚠️ The OCR's limits are written into the module docstring because
  they are easy to misuse: burnt-in captions read at 0.92-1.00, real-world signage at ≈ 0, and
  **a wrong read still reports 0.85-0.92 confidence**, so raising `min_conf` does not filter the
  failures. It exists to read *other people's* finished captions back out — never to generate the
  product names or prices in your own video.
- **`examples/06_teardown.py`** — three fabricated clips, no media, no `pip install`, no ffmpeg:
  two of them share an identical median cut gap and feel nothing alike (0.00 vs 1.15 stdev), and
  a 3-cut clip still reads fast because its captions carry the pace. It also prints whether the
  optional OCR packages are present and what you lose without them, so the degraded path is
  demonstrated rather than promised.
- **`IMPORT_SANITY` in `src/system_health.py`** — a third check class, listed and labelled
  separately from `TESTS` so it is never mistaken for one. Modules like `teardown` are analysis
  tools whose "correct" output cannot be asserted, so instead the health check imports them in a
  subprocess **with every optional package forced to `ImportError`** (a `sys.meta_path` blocker)
  and runs `--help`. That makes "missing optional packages degrade instead of crash" a mechanical
  guarantee rather than a claim in a docstring.

**Script line — the word-lists now ship empty, on purpose**
- **`load_vocab()` / `reset_vocab()` / `vocab_is_empty()` in `src/longform_maker/script_gate.py`,
  and `SPOKEN_OK` / `SUBSTITUTE` / `NEED_PAIR` / `HARD_BAN` now ship blank.** v0.9 shipped these
  four layers pre-filled from one creator's transcripts with a comment saying "replace these" —
  nobody replaces a list that already works. They now start empty and load from JSON:
  `load_vocab("your_audience_vocab.json")` (or a dict) returns per-layer counts, keys beginning
  with `_` are ignored so you can leave notes to yourself in the file, and matching is
  lower-cased. **An empty vocab does not block you**: term scanning is skipped and the gate
  returns a single `lang.no_vocab` warning, so the pipeline runs from day one and the table grows
  later. New words keep their lifecycle — `lang.unknown_term` warn → you grade it → it enters a
  layer.
- **`knowledge/script-retention-craft.md`** — pillars 2 and 3 of the three-pillar script model:
  how to build the four-layer vocab **from your own transcripts** (which is the only place it can
  come from), and the retention-rhythm craft the gate can't check — hook triple, open/close loop
  discipline, payoff density, the one-breath test, and saving your second-best opening for the
  end. Every number in it (60-90s, 45s, 35-40 chars, 20-25%) is labelled a **heuristic starting
  value, not a measured constant**, with the instruction to recalibrate against your own retention
  curve and to measure your real speaking rate before trusting the duration estimate at all.
- **`templates/style_profile.template.md` + `templates/audience_vocab.example.json`** — the
  cumulative counterpart to the 5-minute `voice_profile`. §5 of the template is a vocab audit
  worksheet whose output is the JSON `script_gate` eats; the JSON ships **blank by design** and
  says so in its own `_ship_state` field. The template's own rule for AI-assisted filling is the
  useful part: make the model cite which sample sentence each answer came from — **an answer with
  no citation is one it invented, delete it and ask again.**

**Algorithm line — sourced numbers only**
- **`knowledge/ai-content-compliance.md`** — 13 rules (R26-R38) plus a 10-item pre-publish
  checklist for creators who make content *with* AI: the realistic-media disclosure gate, the
  original-contribution requirement, anti-templating, **the three deepfake red lines (criminal
  liability, blocked at topic-selection time, which is where it's cheapest)**, voice cloning
  restricted to cloning yourself, no metadata laundering, and **R35: only cite numbers that have
  an official source**. Opens with an explicit validity/jurisdiction/disclaimer block — it is a
  2026-07 snapshot across four jurisdictions as *examples, not a list*, it is not legal advice,
  and commercial use warrants a local professional. Starts with a pipeline-exposure exercise
  (label each stage of *your* pipeline SAFE / WATCH / ACT) rather than rules, because the rules
  only mean something against a specific pipeline.
- **`knowledge/ai-content-compliance-sources.md`** — 53 graded citations behind those rules,
  tagged `[official]` (primary) / `[reported]` (press) / `[speculative]` (**no official source
  found — never goes into a script**), each with a stable `§xxx-NN` anchor a rule can point at.
  It's a verification appendix: `grep` the anchor when you need to check a claim, don't read it
  daily.
- **`youtube-algorithm-mastery.md` §2b — the two-machine model (recommendation vs. search).**
  The four traffic surfaces collapse into two machines because their curve shape, lifespan,
  diagnostic metrics and repair actions are all different, and reading both with one set of KPIs
  is what produces "my best-retention video got no views". Covers which machine a topic feeds,
  how to tell from the traffic mix which one picked a video up, the first keyword as the cluster
  steering wheel, and a **four-box checklist that was explicitly demoted from an equation** —
  none of its four variables was ever tested in isolation, its thresholds were regressed after
  the fact from one channel's own samples, and its effect sizes came from n=1 pairings. Every
  threshold is `<fill in>` with §2b-5 giving the SOP for deriving yours from 3-5 of your own
  videos.
- **`youtube-algorithm-mastery.md` §2 — "48h vs day-14", declared the kit's single source of
  truth for post-publish timing.** "48 hours decides everything" is retired (evaluation runs for
  weeks). The replacement is a table: day-0 feed the seed, **0-48h observe and change nothing**
  (swapping packaging inside the test window contaminates the Test & Compare sample you are
  running), day-14 run the decision tree. The one early-kill exception is the **seed-fail triad**
  — impressions stalled *and* CTR below your own ignition band *and* Browse share near zero, all
  three at once; one or two of them lit is what a slow-burning recommendation wave looks like.
  `youtube-algorithm-overview.md`, `youtube-algorithm-2026.md` R18 and `viral-playbook-framework.md`
  now all defer to this section instead of carrying three drifting copies of the deadline.

### Changed
- **`examples/04_shorts_gate.py`** — now runs the same 31s spec three ways: rejected by the
  shipped band, accepted under your own `rules=`, and accepted with **no overrides at all** by
  naming `platform="ig_reels"`. Reports print the platform, the measured caption rate/dwell, and
  gloss warnings the same way they gloss failures — so it's visible that `[WARN]` doesn't stop a
  build. Still no ffmpeg, no `pip install`, no media; still exits 0.
- **`src/shorts_autopilot.py` carries the platform end-to-end** — `scan --platform ig_reels` aims
  the auto-arranged segment lengths at that platform's band and writes `platform=` into the
  generated `_plan.py`, so `build` judges the cut by the same band the plan was designed for.
  (The two silent mismatches found while wiring this up are under **Fixed**.)
- **`knowledge/shorts-mastery-2026.md`** — S8 now carries the YouTube-only caveat and links to the
  measurements; S-B documents the platform layer; S-O added to the mechanical rules with its
  warn-only rationale; the S-A~S-O / S-M / S-N ownership note now spells out why new rules take a
  new letter.
- **`src/longform_maker/script_gate.py` self-test now runs on the shared `gate_core` shell** —
  same PASS/FAIL printing and exit code as every other gate, with the rules themselves staying in
  the file. New assertions cover the vocab lifecycle in both directions: empty vocab must scan
  nothing and emit exactly one `lang.no_vocab` warning, `load_vocab` must populate all four layers
  from a dict *and* a JSON path (ignoring `_`-prefixed keys), and **the shipped
  `audience_vocab.example.json` must both parse and still be blank** — a schema-drift guard that
  also fails loudly if anyone ever "helpfully" fills the example in.
- **`knowledge/script-style-framework.md`** — opens with a map of which of the three script
  pillars each file owns (tone here, audience language and rhythm in `script-retention-craft.md`,
  the mechanical subset in `script_gate.py`), because "sounds like me" and "keeps people watching"
  are different failures with different fixes. Sixth cheat-sheet rule added: **sounding like you
  is not the same as being ready to record.** Getting-started counts raised to ~5 samples to start
  and 10+ before the profile is stable, with the vocab audit as an explicit step.
- **`templates/voice_profile.template.md`** — relabelled the **5-minute minimum version** and
  pointed at `style_profile.template.md` as the cumulative one, so it's obvious which to reach for.
- **`knowledge/meta-lessons.md` M110** — now states *why* the four layers ship empty rather than
  just saying to build your own.
- **`knowledge/youtube-algorithm-overview.md`** — cheat sheet reordered around the two-machine
  question and the corrected timing; Mode E's swap window rewritten to defer to §2's decision
  tree; the file map now lists all six algorithm/compliance files instead of two.
- **`knowledge/youtube-algorithm-2026.md`** — R18 defers to the timing section instead of
  restating a deadline; the AI-enforcement passage is now an entry point to the compliance file
  and marks its own headline figures `[reported]`.
- **`knowledge/viral-playbook-framework.md`** — §3 expanded from a three-line grading scale into a
  runnable adversarial pass: **five attacks** to run against each of your own conclusions (sample,
  measurement window, confounds, causal direction, effect size), a fill-in grading table, and six
  common root causes. Two disciplines added — check a conclusion's grade before citing it, and
  **treat effect sizes as direction, not coefficients**. REFUTED conclusions are now explicitly
  *kept* with the data that killed them, because deleting one guarantees reinventing it.
- **`src/system_health.py`** — the new knowledge files joined `CORE_FILES`, and the report now
  prints three clearly separated classes (`TESTS` / `IMPORT_SANITY` / `CORE_FILES`) so a weaker
  guarantee never reads as a self-test.
- **`SETUP.md` / `SETUP.en.md`** — §3 gained the upgrade path from the 5-minute voice profile to
  the cumulative style profile and its vocab audit; §8 documents `platform=` as the way to pick a
  duration band without hand-writing overrides.
- **`README.md`, `README.en.md`, `knowledge/README.md`, `examples/README.md`** — module tables,
  index entries and the runnable-example list updated for the script line, the compliance files,
  the teardown tool and the platform-aware band.
- **Self-test coverage for both new Shorts rules is bidirectional** — the same 35.5s cut must be
  blocked on `yt_shorts` *and* pass on `ig_reels`/`fb_reels`; `rules=` must be able to re-narrow a
  wide platform *and* widen the default one; S-O must warn on a sparse cut *and* stay silent on a
  dense one, with each threshold overridable independently. Checking only that a rule fires cannot
  tell a working gate apart from one that blocks everything.

### Fixed

Both of these were caught before release, and both are the same shape: **a call convention that
was harmless until a new layer was inserted underneath it.** Pre-merging a rules dict was fine
while "defaults → your overrides" was the whole story; the moment `platform` slid in between the
two, handing a merged dict downstream started overwriting the very band the platform had just
chosen. Neither raised anything.

- **`shorts_autopilot.build()` would have judged every cut by the *default* platform's duration
  band, whatever `spec["platform"]` said.** It called `merge_rules()` itself and passed the result
  to `assert_shorts(spec, r)` — but the merge order is defaults → platform → your overrides, so an
  already-merged dict arrives in the *overrides* slot and clobbers the platform layer. Fixed by
  handing the caller's raw `rules=` straight through and letting the gate merge exactly once
  (`assert_shorts()` now forwards raw `rules=` too, so no caller can reintroduce it). **Why this
  class of bug is the dangerous one**: nothing crashes and nothing errors. A 35s Instagram Reel
  gets rejected for sitting in *YouTube's* dead zone, with a precise, confident, wrong explanation
  attached. A crash sends you hunting for the bug; a plausible wrong verdict sends you back to
  re-cut a video that was fine — and you never doubt the tool, because the tool never complained.
  Regression guard: a 35.5s `ig_reels` spec must survive **`assert_shorts`**, not merely
  `gate_shorts`. The original self-test only exercised the non-asserting path, which is precisely
  how a defect hides one function above the thing you tested.
- **`build()`'s post-gate QA and `REPORT.md` would have been measured against a different band
  than the gate used.** The thresholds reused after the gate were still merged *without* the
  platform, so the finished-file duration check and the generated report could quietly contradict
  the gate that had just passed the same cut — one document, two sets of numbers, no error
  anywhere. They now re-merge with `spec["platform"]`, so gate, QA and report are guaranteed to be
  quoting the same band.

### Removed

*(Removal notes name the **category** that left, never the value — a changelog that quotes the
number it just deleted becomes that number's last surviving publication.)*

- **The back-office-readout thresholds are gone from the algorithm line, and "relabelled" no
  longer counts as removed.** The weekly-KPI table in `youtube-algorithm-mastery.md` §TL;DR and
  the teaching-checkpoint retention table in §3 both shipped concrete values; the checkpoint set
  was additionally restated in `youtube-algorithm-overview.md`'s cheat sheet and in Modes B and D,
  so one edit could never have finished the job. Both tables are now `<fill in>` in all five
  places, with the regression procedure attached (split your published videos by "did the
  algorithm pick it up", read where the two groups separate). The reasoning, stated once so it
  doesn't have to be rediscovered: **CTR / AVP / retention / traffic-mix percentages are things
  only a channel's own Studio can see**, which means any specific threshold with no citable source
  *is by definition somebody's private readout, whatever label sits above it*. An earlier pass had
  left those tables in place under a "working thresholds, not public benchmarks" caption and
  treated that as sufficient — it wasn't. A weaker label on an unchanged number still gets copied.
  **Deliberately kept, and why**: §4's CTR grading band (2-4% / 4-6% / …) still prints ranges.
  It is a *scale*, not a target — it says what a number means, not what yours should be — and the
  two values you actually act on (your ignition band, your detonation band) sit right beneath it
  as `<fill in>`. It stays flagged as "direction only, no citable source"; if you find it being
  used as a pass/fail line anywhere in the kit, that's a bug — open an issue.
- **⚠️ Supersedes a claim made in 0.10.0.** That release's Removed section ends its
  `viral-playbook-framework.md` entry with "the four remaining bare numbers in §2 station 6 are
  now explicitly labelled as public 2025-2026 benchmarks rather than self-measured values."
  **Read that as a description of a bug, not of the current file.** The label was wrong — this
  repo never held a citable source for those four — and the numbers themselves were dropped, not
  relabelled; §2 station 6 now carries `<fill in>` plus the measurement recipe and says so in
  place. The 0.10.0 text is left unedited because rewriting history hides the mistake, but no
  reader should take it as the shipping state.
- **The four `script_gate` audience word-lists ship blank** (`SPOKEN_OK` / `SUBSTITUTE` /
  `NEED_PAIR` / `HARD_BAN`). What left was *one creator's* jargon grading, not the layering — the
  four-layer lifecycle is intact and `load_vocab()` fills it from your own transcripts. The
  shipped `templates/audience_vocab.example.json` is asserted blank by the self-test, so a
  well-meaning future fill-in fails loudly instead of quietly re-adopting somebody's vocabulary.
- **`youtube-algorithm-mastery.md` §2b-5 no longer ships the three-video comparison it was
  derived from** — that was a single channel's per-video analytics. The section is now the
  procedure for generating the equivalent table from 3-5 of your own videos.

## [0.10.0] — 2026-07-28

**Three isomorphic production lines.** Until now the kit answered one question: how do you
make *one long-form video* well? It now runs three lines — teaching long-form, vertical
Shorts, and an interview show — and they are deliberately built to the same shape:
**a knowledge layer (why the rules exist) → a mechanical gate (so nobody has to remember them)
→ a one-command driver**. Learn one line and you've learned all three; adding a fourth means
filling in the same three slots. The new lines also share their plumbing with the old one:
one gate shell, one set of A/V helpers, one health check.

### Added
- **`src/longform_maker/shorts_gate.py`** — vertical-Shorts mechanical gate, **pure Python**
  (no ffmpeg, no Pillow, no numpy). That is a property of *the file*, and it only survives if you
  import it flat — `sys.path` → `src/longform_maker/`, then `from shorts_gate import …`, which is
  what `examples/04_shorts_gate.py` does. `from longform_maker.shorts_gate import …` runs the
  package `__init__`, which eager-imports `fx_lib` and therefore needs numpy + Pillow; copying
  `shorts_gate.py` + `gate_core.py` out works too. Nine rules: opening identification (subject name +
  one line of "what this is"), duration band + dead zone, first-cut deadline, loop alignment
  (last segment must return to the first clip *and* land on its exact in-point), persistent
  info bar, captions bound to **segment indexes instead of hand-typed timecodes**, no caption
  on the loop segment, no caption spanning a cut, and a white-first color budget. Every number
  in `DEFAULT_RULES` is an **example calibration, not a universal law** — override per call with
  `rules={...}`; `merge_rules()` raises on an unknown key rather than silently keeping the default.
- **`src/shorts_autopilot.py`** — one-command vertical-Shorts flow that leaves exactly one
  human/AI judgment in the middle: *look at the frame and write what it says*. `scan` normalizes
  clips to 9:16, reads GPS, renders a contact sheet plus blow-ups of on-screen text, and writes a
  `_plan.py` skeleton with segments pre-ordered and the text left blank; `build` runs the gate,
  cuts the Short, then auto-QAs it (spec / duration / loudness / loop / caption-alignment frame
  grabs) into proof images and a `REPORT.md`. Needs **Pillow + numpy**; paths come from
  `VIDEO_KIT_SHORTS_INBOX` / `VIDEO_KIT_BGM_ROOT` / `VIDEO_KIT_PROJECT_ROOT`.
- **`src/interview_gate.py`** — interview planning gate (I-A…I-E): required guest fields;
  **every achievement must carry a source** — a guest with no verifiable numbers doesn't get
  booked; screenshot permissions must map to an actual achievement (otherwise the consent form
  can't describe them); at least one guest link; no `TODO` residue. Copy the file out on its own
  and it falls back to an embedded shell, so behavior is identical outside the repo.
- **`src/interview_autopilot.py`** — the interview line in three commands (`invite` → `plan` →
  `build`) and three copy-pastes. `plan` runs the guest gate *and* `plan_gate`, renders the
  seven deliverables (host script / question outline / guest prep kit / consent form / recording
  checklist / publish kit / Shorts cut list), and schedules the episode into `channel_tracker`
  (pre-call, record day, publish day, D2/D7/D28). **Compliance is deliberately not automated**:
  `plan` writes "pending review", the gate blocks on it, and you pass `--compliance-ok` yourself
  after walking your platform's AI-content policy checklist. Episode folders are generated
  **ASCII-only** so non-UTF-8 consoles don't break.
- **`templates/show_profile.template.md` + 11 templates in `templates/interview/`** — every word
  of every deliverable lives in a template; the code only substitutes `((fields))`. **Change the
  wording in the template, never in the code.** Two different safety nets, not one: a template
  field the code forgot to pass **raises** (`render()` asserts no `((field))` survives, so a
  half-rendered deliverable can't be written at all), while a *show-profile* field you simply
  haven't filled in yet renders as a visible brace-wrapped placeholder and prints a WARN naming
  it — never a plausible-looking invented value. Note the placeholder text is Chinese
  (`{你的節目名}` …); grep the output for a literal `{` rather than for an English word.
- **`knowledge/shorts-mastery-2026.md`** — the Shorts knowledge layer: duration bimodality, the
  ≤2s first cut, real loops, persistent identification, research baselines S1-S12, the twelve
  editing rules S-A…S-L (**the labels are owned by `shorts_gate.py`** — a gate message and the
  knowledge file always mean the same thing by the same letter) plus two human-judgment items
  S-M / S-N that have no assert, and how to read swipe-through rate (thresholds you calibrate
  yourself).
- **`knowledge/interview-show-playbook.md`** — the interview knowledge layer: invite → 7-doc kit
  → per-track recording → edit → packaging, six hard rules, and why the compliance stamp can only
  be applied by a human.
- **`src/longform_maker/gate_core.py`** — the shell every gate shares (`report()` /
  `make_assert()` / `selftest_runner()`): one return shape, one assert-message format, one
  self-test print style. **The rules themselves stay in each gate's own file** — not centralizing
  them is what keeps them from contaminating each other.
- **`src/av_util.py`** — the mechanical bits every autopilot needs (subprocess wrapper that
  survives non-ASCII output, utf-8 writes, ffprobe duration, frame grabs, contact-sheet tiling),
  in one place so two copies can't drift.
- **`capcut_helpers.check_caption_linebreaks()` + `word_captions.scan_line_quality()`** — M108
  as a delivery-side gate: dangling line ends, dangling line starts, split compounds and
  over-long lines are now caught in a finished `.ass` (including hand-edited or externally
  produced subtitles), using the **same constants** the generator side already enforces.
- **`capcut_helpers.check_bgm_coverage()`** — M79 as a check: finds windows where the music has
  actually stopped under the narration instead of trusting the build script.
- **`examples/04_shorts_gate.py`** — a broken cut blocked on three rules at once, the fixed cut
  passing with its caption times computed from segment indexes, then the same 31s cut accepted
  under *your own* thresholds. **No ffmpeg, no `pip install`, no media.**
- **`examples/05_interview_plan.py`** — the same fictional guest BLOCKED while one achievement
  has no source, then PASSING once it's filled in. Also no ffmpeg, no `pip install`, no media.

### Changed
- **`README.md` / `README.en.md`** — repositioned around the three production lines (each with
  its knowledge layer / gate / driver), new module-table rows for the Shorts and interview lines
  and the shared `gate_core` + `av_util` foundation, and a note that "lines" and "paths" are
  different axes: a line is *what kind of video*, a path is *how you make it*; all three lines
  run on Path 1.
- **`SETUP.md` / `SETUP.en.md`** — two new optional sections, both skippable if you don't run
  that line: **7️⃣ Interview show** (five questions: show name / host name / audience landing
  link / recording tool + fallback chain / word-for-word sign-off, plus the `CLUSTER` and
  `PLATFORMS` fields the consent form quotes verbatim) and **8️⃣ Shorts rule calibration** (which
  threshold each measurement feeds, and the two-step method — set thresholds from your best 3-5,
  then **confirm your worst 3 get blocked**; a threshold that skipped step 2 is decoration).
- **`examples/README.md`** — corrected the blanket "no `pip install` required" claim: 01 / 02 /
  04 / 05 need nothing, but `03_premium_fx.py` needs Pillow and `src/shorts_autopilot.py` needs
  Pillow + numpy; 03's ffmpeg requirement is now stated too, and 04 / 05 are marked as needing
  neither ffmpeg nor any media.
- **`src/system_health.py`** — now also runs the new self-tests (`gate_core`, `shorts_gate`,
  `av_util`, `interview_gate`, `interview_autopilot`), so a broken new line turns the single
  verdict RED like everything else.
- **`config.example.py`** — documented `VIDEO_KIT_SHORTS_INBOX` and `VIDEO_KIT_BGM_ROOT` (one
  BGM subfolder per mood, referenced from the spec so swapping the mood never touches code) plus
  `VIDEO_KIT_PLAN_ROOT` for the interview line, with the ASCII-folder-name warning.
- **`knowledge/meta-lessons.md`** — added M107 (**on-screen numbers must be real back-office
  screenshots; someone else's numbers never air without a screenshot they gave you**) and a new
  §Shorts section carrying S-A…S-L (plus the assert-free S-M / S-N), each written as symptom /
  root cause / permanent fix with the matching assert.
- **`knowledge/viral-playbook-framework.md`** — a Shorts column for the whole framework: first
  frame + first second replaces CTR (autoplay means there is no thumbnail to click and no second
  chance), swipe-through rate replaces AVP, loop rate is an **independent** dimension rather than
  a byproduct, and old Shorts hit a recommendation cliff around 28-30 days — so read KPIs inside
  that window, not after it.
- `knowledge/README.md` — indexed the two new knowledge files; `knowledge/capcut-automation-sop.md`
  and the craft/algorithm docs picked up matching cross-references.
- **Every self-claim in the repo was audited as an assertion, and the ones that no longer held
  were corrected** (a dedicated claims-only pass — see the new **M111**):
  - `README.md` / `README.en.md` — the banner said voice / strategy / community numbers are
    "all blank templates". Two thirds of that was true and the middle third was not: `knowledge/`
    **is** the author's methodology, shipped on purpose. The banner now says what is actually
    guaranteed (no account names, no analytics readouts, no personal profiles; word-lists and
    thresholds are blank or explicitly labelled examples) and states the exception out loud.
  - `knowledge/viral-short-playbook.md` — the reference channel was tagged "(illustrative)",
    which reads as *made up*. It is a real channel, deliberately unnamed. The header now says
    **anonymised, not fictional**, and the "why study it" section no longer characterises the
    channel's size in metric terms or presents its paraphrased interview quotes as citable.
  - `knowledge/shorts-mastery-2026.md` §2 — the S1-S12 table said "third-party consensus" but
    read like sourced benchmarks. It now states plainly that **this repo kept no clickable source
    for any of those numbers**, so they are hypotheses to calibrate against, not facts to quote.
  - `src/longform_maker/script_gate.py` — `SPOKEN_OK` called itself an audit of "an example
    channel"; it is one real channel's transcript audit, topic- and market-specific. Said so.
- **`knowledge/meta-lessons.md` — added M111**: sanitization *claims* need their own audit pass,
  because three failure modes survive a content scan — a removal note that quotes the thing it
  removed, a relabel passed off as a removal, and an absolute rule the file itself breaks.
  Companion to M100 (which covers scanning the content); M111 covers verifying the description.
  `M1-M110` → `M1-M111` across the docs.

### Removed
- **Author-nicknamed back-compat aliases dropped.** The keyword-map constants, the teaching
  preset keys, and the dual-tier caption helper each carried a second, author-nicknamed name
  kept for compatibility since 0.3.0. The neutral names (`EXAMPLE_BROLL_CONTENT_KEYWORDS`,
  `EXAMPLE_KEYWORD_MAP`, `PRESET_STYLES["teaching_primary"]` / `["teaching_secondary"]`,
  `apply_teaching_dual_tier`) have shipped alongside them for seven releases and are now the
  only names. If you pinned the old spelling, rename the import.
- **`subtitle_corrections.py`'s built-in dictionaries reduced to word scope.** The example
  entries were derived verbatim from one creator's own narration (including a personal sign-off
  line). The dictionaries were already **off by default** (`use_builtin_corrections=False`), so
  no default behavior changes; if you had opted in and relied on a specific entry, pass it via
  `extra_corrections={...}`.
  A later pass caught the leftovers: `CHINESE_HOMOPHONE_CORRECTIONS` still held whole *phrases*
  lifted from that same narration (a phrase-length entry reconstructs the speaker's sentence,
  not just a word), and `scan_potential_errors()` still flagged the matching patterns.
  A third pass corrected the description as much as the data: the module docstring had gone on
  listing the removed pairs in its "supported errors" bullets — **a doc line that quotes the
  entries the dict just dropped republishes them** — `PHRASE_CORRECTIONS` still carried one
  verbatim narration phrase behind an "example" comment, and the scanner still looked for the
  author's brand casing after the dict had stopped correcting it.
  **What the file now claims, precisely:** every remaining entry is **word-scoped** (no
  phrase-length entry, so nothing reconstructs a sentence) and the only phrase entry is
  synthetic; the brand / transliteration / abbreviation words are still **one speaker's real
  mishear tendencies kept as illustration**, not a neutral universal list — which is why they
  ship off by default and the docstring says so instead of calling them generic. Keep your own
  dictionary word-scoped for the same reason, and keep phrase entries in `extra_corrections`.
- **Speaker-specific vocabulary dropped from the example topic maps.** `EXAMPLE_KEYWORD_MAP`'s
  `topic_intro` shipped a real greeting/retention boilerplate as its keyword list, and two topics
  carried one product's feature vocabulary — i.e. someone's voice signature and product spec baked
  into a public constant. Replaced with neutral placeholders. Both maps are **off by default**
  (the zero-config path is filename↔caption token matching), so nothing changes unless you were
  explicitly passing `keyword_map=EXAMPLE_KEYWORD_MAP`; if you were, write your own from your
  own transcripts — that was always the intent.
- **Every per-account engagement figure dropped from `knowledge/ig-caption-patterns.md`.** The
  like / comment / share / save tables were rounded real measurements from other people's public
  Instagram accounts, carrying a disclaimer that called them synthetic — which was simply untrue.
  Both tables are gone; what remains is the ranking that actually carries the lesson (list-type
  and route-type captions out-save single-spot captions; menu+rating captions out-save everything)
  plus `<fill in>` columns for your own Insights. **The kit publishes no account's back-office
  readouts — not the author's, and least of all a third party's.** (Figures a third party has
  themselves made public, quoted with a working source link — e.g. the reference-channel row in
  `knowledge/teaching-niche-playbook.md` — are the one exception, and they stay citation-first:
  no link, no number.)
- **The ignition thresholds in `knowledge/viral-playbook-framework.md` are now `<fill in>`.**
  The two CTR bands, the AVP floor, the sub-conversion floor and the traffic-structure
  percentages read as industry benchmarks but were back-fitted from a single channel's readouts
  and carried no source. Each is replaced with the **procedure for regressing the threshold out
  of your own published videos** (split them by "did the algorithm pick it up", find where the
  two groups separate), plus a warning that a threshold derived from <5 videos is a checklist
  item, not a kill switch. The four remaining bare numbers in §2 station 6 are now explicitly
  labelled as public 2025-2026 benchmarks rather than self-measured values.
  **The old values are deliberately not restated here** — a changelog that quotes the numbers it
  just removed republishes them, and someone else's back-fitted threshold is worse than no
  threshold.
- **The IG caption "reference quotes" are now sentence-skeletons, not transcriptions.** An earlier
  pass placeholdered the *nouns* (venue, district, opening hours, floor layout) but left the
  surrounding sentences word-for-word from real posts on other people's accounts. That is the same
  leak with an extra step: **one full original sentence pasted into a search box finds the post,
  and the post carries the shop name, the address and the Plus Code.** Every hook line, closing
  line and verdict line across all three archetypes is now a `{句型}` placeholder, and the file
  states the rule explicitly so the sentences don't get filled back in. The series-title brand
  asset ("<name> in <region>"-style opening card) is likewise no longer a specific account's
  wording — pick your own; a series name *is* the account's identity.
- **The travel itinerary example in `knowledge/video-craft-playbook.md` is no longer a shooting
  list.** "N-day trip → these five kinds of spot" was a genericized copy of one real trip, and a
  fixed combination of spot types plus a trip length reads back as *where the author went*. It is
  now "one shot per point worth its own video", with a note that another person's itinerary has no
  transfer value anyway.
- **Region-pinning example platforms broadened.** The community questionnaire, the mobilization
  template and three knowledge files all named the same two chat platforms as *the* pair, which is
  a geographic tell (that pair is regionally specific) as well as one person's actual stack. They
  now read as roles — chat community / group chat / newsletter / social platforms — so an adopter
  in any market fills in their own. Same reason the country flag and the capital-city timezone
  were removed in earlier passes.
- **The reference channel behind `knowledge/viral-short-playbook.md` is no longer identifiable.**
  That file had been anonymized to "a large teaching channel (illustrative)", but the anonymization
  was only half applied: the beat table still carried the promo video's **subtitles transcribed
  word for word** plus the name of the product being sold, and `knowledge/autopilot-workflow.md`
  named the channel outright in the cheat-sheet line pointing at that same file — which un-anonymized
  everything. The caption column now describes **what each line does structurally** instead of
  quoting it, and the cross-reference is generic. Another creator's ad copy is theirs; the reusable
  part was always the beat structure, never the words.
- **The teaching-niche playbook no longer hands you someone else's signature pillars.** The
  "pick three core skills" SOP, the chapter-title list, the title-rewrite table and two hook
  examples all used the same three very specific software problems as their worked example —
  specific enough that searching one of them lands on a single channel. They are now fill-in-the-blank
  (`{功能名}怎麼開` / `修{那個常見錯誤}` / …), with a note that pillars and chapter names must come
  from **your own** search-terms report: copying another channel's pillar set means competing for
  that channel's audience with an imprecise version of their content. Same edit applied to the
  duplicate of that section in `knowledge/youtube-algorithm-2026.md`.
- **`asset_scanner.scan_bgm()` no longer classifies by one person's filename convention.** The
  BGM heuristic matched **the author's own Chinese filename prefixes** and emitted his private
  content-type labels — a rule that could only ever fire on his machine, and that produced
  category names matching nothing else in the kit. The prefix table is now the module-level
  `BGM_PREFIX_MAP` with neutral ASCII example keys, and the emitted `best_for_content_type`
  values are the **Registers the workflow actually documents** (`High-Demo` / `High-Reflective` /
  `High-Update` / `Low` / `Vlog`), so a scanned `index.json` lines up with
  `knowledge/autopilot-workflow.md`. Prefix matching is language-agnostic — put your own prefixes
  in the map. Unmatched files are no longer `"unknown"` with no trace: they get
  `content_type = "unclassified"` and the prefix itself as a tag, and `scan_all_assets()` still
  preserves whatever you edit in by hand. **If you were relying on the old CJK prefixes, add them
  as keys.**
- **`broll_audit._MAIN_PATH_HINTS` no longer carries a Chinese folder name.** One hint was a
  CJK word for "official site" — i.e. one creator's folder naming compiled into a public
  classifier, next to nine ASCII hints that no adopter's paths would miss. It is dropped
  (`website` / `product` / `demo` already cover the concept) and both the constant and M86 now
  state the actual contract: **the hints are ASCII; if your folders are named in your own
  language the segment falls to the conservative `generic` default — extend the tuple or, better,
  pass `is_main=True/False` explicitly.** Only paths containing that specific word change
  classification.
- **Internal shot IDs, asset filenames and per-video measurements pulled out of the lessons file.**
  M81 / M85 / M86 / M87 still described the bugs using the offending build's segment indexes,
  a stock clip's real filename, the raw source filename of a
  dropped asset, and that video's exact generic-vs-main second counts. Together those reconstruct
  one specific published video's b-roll layout, which is why the same class was removed from the
  Shorts lessons in an earlier pass. Each is now described by its **shape** ("the same stock clip
  placed in three different sections", "generic roughly 2:1 over main") — the rule and the fix are
  unchanged, and the mechanical checks that enforce them were never keyed to those values.
- **The last six numbers in `knowledge/viral-playbook-framework.md` §2 are gone too — and the
  label that was covering for them.** An earlier pass removed the CTR / AVP / sub-conversion
  thresholds but *kept* the seed-fail triad, the stranger-share-of-test-pool figure and four
  "other signals", **relabelled as public 2025-2026 benchmarks**. They were not: they are one
  channel's own regressed working thresholds, and this repo never carried a source link for a
  single one of them. **Relabelling private analytics as an industry benchmark is worse than
  leaving them unlabelled** — it launders a back-fitted number into something a stranger will
  trust enough to kill their own video with. All six are now `<fill in>` plus the procedure for
  regressing them out of your own published videos, and the file carries a three-class number
  policy at the top (readout-derived thresholds → `<fill in>`; relative multiples → written out,
  they're definitions not readouts; second-hand industry claims → marked "second-hand, no
  source") so the rule can be re-audited mechanically instead of trusted.
  **The removed values are deliberately not restated here**, for the same reason as above.

### Fixed
- **`final_delivery_qa()` could print `DELIVER OK` without checking anything.** Passing just
  `video` ran the picture-only checks and reported success — the audio gate, caption-sync gate
  and full-frame privacy scan had never executed. Added `profile='teaching_longform'`, which
  forces the audio / caption-sync / M108 / M79 checks on and treats a missing `voice`, `ass`, or
  `sheets_dir` as **BLOCKED** instead of green. **The signature is now keyword-only after
  `video`** — the old positional order silently bound `ass` to `contact_out` and `sheets_dir` to
  `audio`, leaving the real arguments `None`, which the profile then reported as missing: a call
  written straight from the docs would be **permanently BLOCKED, and a BLOCKED gate looks exactly
  like a gate doing its job**. Mis-calls now raise `TypeError` immediately.
- **`detect_flash()` flagged every fade-to-black transition as strobing.** The old rule ("two or
  more black segments, or any segment under 1s") meant a perfectly normal video with six
  section-boundary fades was reported as a strobe hazard → `deliver_ok=False` forever, with no
  way to tell why. `classify_flash()` now separates the two by time distribution: black segments
  closer together than `cluster_gap`, or shorter than `micro`, are real strobing and block;
  isolated dips are listed as transitions for eyeball confirmation and pass. **A false BLOCK is
  more expensive than a false pass — a gate that is always red teaches people to ignore the whole
  gate.**
- **Shorts duration guidance was self-contradicting.** The bands the craft docs used to
  recommend (20-45s / 40-55s / 15-30s) put roughly half their range inside what measurement shows
  to be a dead zone — too long to carry a gag's rhythm, too short to finish explaining anything.
  Duration is **bimodal, not one band**: `video-craft-playbook.md` and `video-craft-overview.md`
  are reconciled to 13-25s (gag / single surprise) or 45-60s (tutorial / demo) with 26-44s called
  out as dead, `shorts_gate` enforces it via `dur_min` / `dur_max` / `dur_deadzone`, and both now
  say plainly that these are **example values to recalibrate from your own videos**.

## [0.9.0] — 2026-07-25

**Ops autopilot + three-gate production line.** The kit now covers the *operations*
half of running a channel — not just making videos, but knowing what to do each day,
whether the system is healthy, and whether an idea deserves to be written at all.

### Added
- **`src/channel_tracker.py`** — hands-off ops state machine: per-video D2/D7/D28
  snapshot scheduling + owner/due pending-action tracking in a single
  `channel_state.json` (template: `examples/channel_state.example.json`).
  One command prints "what is due today". 11-check self-test.
- **`src/system_health.py`** — one-command kit health check: runs every module
  self-test + core-file existence, single GREEN/RED verdict, `--quick` mode skips
  ffmpeg-heavy tests. (Immediately paid for itself: caught a cp950 emoji crash in
  `invariants.py` during its first run.)
- **`src/longform_maker/plan_gate.py`** — planning-stage mechanical gate
  (packaging-first): frame tag, machine attribution (browse vs search), >=8
  title×thumbnail pairs (the "can't package it = you don't understand the idea yet"
  kill threshold), compliance mark, cluster keyword. FAIL = don't start writing.
- **`src/longform_maker/script_gate.py`** — pre-recording script gate v2:
  R24 cold-open rules + audience-language 4-tier vocab check (fail-level:
  hard-banned engineering jargon, English terms with native-language equivalents,
  jargon requiring a plain-language companion in the same beat) + retention-rhythm
  checks (open loop, beat length cap, momentum words, mid-video closing-tone ban,
  punch-line variance, and-then chain density). Vocab tiers are fill-in-your-own:
  derive the whitelist from your own transcripts.
- **`knowledge/viral-playbook-framework.md`** — define "viral" with your own data
  (machine-ignition binary judgment / trimmed-median Expected Views / CTR×AVP dual
  gate), the six-station hit-rate system, and the adversarial-verification
  methodology (CONFIRMED / PLAUSIBLE / REFUTED grading with a self-audit list of
  common analysis pathologies).
- **`knowledge/ops-automation.md`** — wiring guide: tracker + health + three gates
  + a daily scheduled AI patrol (with hard safety rules baked into the prompt).

### Fixed
- `capcut_helpers/invariants.py` self-test crashed on cp950 consoles (emoji in
  print) — ASCII markers now.

## [0.8.0] — 2026-07-10

**Two-path repositioning + cross-platform support.** Driven by adopter feedback: CapCut
version/encryption issues breaking draft automation, Mac users who couldn't run the
"primary" path at all, and a clear preference among adopters for the fully programmatic
pipeline. The kit now presents **two first-class paths** instead of "CapCut primary /
ffmpeg secondary".

### Added
- **`src/platform_compat.py`** — standalone Win / Mac / Linux compatibility layer
  (nothing in the kit imports *from* it circularly; `constants` / `paths` import it).
  CJK-font probing with per-platform candidate lists (Windows order preserved so
  resolution is identical to the old hardcodes; handles the macOS 15 Sequoia
  `PingFang.ttc` disappearance), CapCut/Jianying drafts-dir resolution per platform
  (`CAPCUT_USER_DATA` env override), returns `None` instead of raising so callers keep
  their own fallbacks.
- **`detect_draft_format()`** (`capcut_helpers`) — run before any draft-JSON edit:
  detects plaintext vs. AES-encrypted drafts (Jianying CN 6.0+), reports a version hint
  and whether the draft is directly editable, and accepts a project name / draft folder /
  JSON file path. `load_draft()` now raises a guided error on encrypted drafts.
- `TROUBLESHOOTING.md` — new **"CapCut version compatibility & Mac"** section: the
  per-version draft-format matrix (international 6.x-9.x plaintext, Jianying CN ≤5.9
  plaintext / 6.0+ encrypted with no official bypass), the three escape routes, Mac
  draft paths + the `draft_info.json` filename difference, Mac automation limits
  (no AppleScript dictionary → use the programmatic path), and a top-5 workflow-trap FAQ.

### Changed
- **`README.md` / `README.en.md` — two-path repositioning.** **Path 1 = Programmatic**
  (`longform_maker` + `silent_vlog_maker` + the `capcut_helpers` QA gates) is
  cross-platform (Win/Mac/Linux), CapCut-free, and the **recommended default for
  adopters**; **Path 2 = CapCut-assisted** (draft JSON + Computer Use) is Windows-first
  and version-sensitive — it's what the author personally uses, stated honestly as such.
  Added a "Which path should I use?" decision tree up top and a per-module platform
  support matrix.
- `SETUP.md` / `SETUP.en.md` — platform requirements aligned with the two-path model;
  the production section now asks which path you're on instead of assuming CapCut.

## [0.7.0] — 2026-07-09

**Premium motion engine + mechanized caption timing & screen-recording cleanup** (the biggest *visual*-quality jump in the kit so far — v0.6.0 fixed the sound, this one fixes the picture). Motivated by two shipped-video incidents (a recorder panel leaking into a delivered cut; captions drifting 2-3s from narration) plus a 6-lens research pass on what separates "clean" from "premium" motion design.

### Added
- `src/longform_maker/` — new module family for teaching long-form:
  - **`fx_lib.py`** — the premium-motion engine: easing library (`ease_out_expo`, `ease_out_quint`,
    `ease_out_back`, `smootherstep`…), stagger scheduler, per-frame film grain + vignette
    (`texture_pass`), **sub-pixel float Ken Burns** (`ken_burns_frame`, the anti-`zoompan` —
    integer-jitter-free push/pull on stills), **double-layer additive bloom** (tight 4px @60% +
    wide 16px @30%), 45° **light sweep**, and a fully **synthesized SFX kit**
    (whoosh / pop / tick / riser / hit — no audio assets needed). Real self-test.
  - **`word_captions.py`** (M105) — caption timing from **whisper word-timestamps**: auto line-break
    at real pauses (next-token onset), mishear fixes applied *before* line-breaking, dangler-aware
    wrapping, master-timeline conversion (M103 speed-aware), ASS output — plus optional
    **per-line single-keyword emphasis** (numbers-first, one hit per line, resets to white).
  - **`screen_clean.py`** (M104) — screen recordings are default-toxic: enforced **head ≥1s + tail
    trim** (recorder UI lives at *both* ends), chrome crop, blur-pad, mute, and **`blur_boxes`
    targeted blurs** for center-of-frame UI text that cropping can't save. Real ffmpeg self-test.
- `src/capcut_helpers/delivery_qa.py` — four new mechanical gates: **caption-sync spot-check**
  (whisper re-transcribe n sampled lines, char-overlap ≥0.5), **full-frame contact sheets**
  (dense ≤1.5s/frame scan — edge strips can't see center-frame floaters), **scene-pacing 3-band
  audit** (max visual-change gaps 7s/15s/30s by video section), and **dead-air detection**
  (freezedetect ∩ silencedetect; catches the classic "frozen tail + silence").
- `knowledge/meta-lessons.md`: **M104** (screen-recording cleanup, mechanized), **M105**
  (word-level caption timing, mechanized), **M106** (premium-motion wave-1: no static cards >5s,
  sub-pixel-only camera moves, counter triple — expo + fixed digit slots + landing pop with the
  **final frame asserted equal to the true value**, double bloom, SFX aligned to cuts ±50ms,
  split-tone finishing).
- `knowledge/premium-motion-fx.md` — the full wave-1/2/3 upgrade plan with exact parameters
  (easing formulas, 80ms stagger, bloom radii, adelay alignment, curves/colorbalance grade,
  ASS emphasis tags, 1.12x punch-in, chars-per-minute targets, thumbnail hard-gates) **plus a
  10-item "deliberately skipped" list** (zoompan, persistent chromatic aberration, glitch,
  luma flicker, rainbow captions, wall-to-wall overshoot…).
- `knowledge/youtube-algorithm-2026.md`: **R15-R25** — 2026 mechanics updates (Test & Compare now
  judges by watch-time-per-impression; auto-dubbing; Shorts/long-form decoupling; seed-impression
  day-0 playbook; satisfaction signals; tight-cluster browse matching; Communities posts;
  AI-carousel defense; Ask Studio retro questions; the 30s-retention gate; Hype globalization).
- `examples/03_premium_fx.py` — see the whole premium stack in ~3 seconds of output video,
  zero real media: count-up (final frame asserted true), bloom, light sweep, sub-pixel
  Ken Burns, grain/vignette, synthesized whoosh.

### Changed
- `README.md` / `README.en.md`: repo-structure table now lists `src/longform_maker/`.

## [0.6.0] — 2026-06-27

**Pro audio chain + narration-speed timeline sync** (knowledge + technique; the biggest audio-quality jump in the kit so far). Motivated by "the editing sounds amateur" + "you talk too slow" feedback — the fix is the audio, not the picture.

### Added
- `knowledge/meta-lessons.md`: **M103** — making teaching long-form narration sound *pro*:
  **acompressor** to flatten loud/soft swings (a real compressor, not a normalizer — the #1 amateur
  tell), **sidechain-ducked BGM** (voice as the key → music auto-ducks when you speak, floats back in
  the gaps; replaces a static `volume=` duck), **two-pass loudnorm** (`print_format=json` measure →
  `measured_*`+`linear=true` apply, for accurate −14 LUFS without pumping), and a continuous pink
  **room-tone bed** so the gaps aren't dead digital silence. Plus the **atempo speed-sync rule**: a
  single `speed` constant must flow through audio/visual/captions (write it to `offsets['_speed']`,
  consume as `/SP` downstream) or the timeline desyncs; and **tail-length alignment** (fade BGM/mix to
  the *actual video length*, not audio length, so `-shortest` doesn't hard-cut the BGM at ~−23 dB =
  outro click). Closes with **automated delivery gates** (M97): assert LUFS −14±1 / tail RMS<−40 dB /
  audio-vs-video stream |Δ|<0.4 s / last-caption-end ≤ duration — and extracting the chain into a
  reusable, ffmpeg-self-tested helper instead of copy-pasting it into every build script.
- `knowledge/programmatic-video-build.md`: §7 now shows the **pro mix** (voice acompressor +
  sidechain duck + two-pass loudnorm + tail-align) alongside the basic mix; §8 QA adds the
  `audio=True` / `ass=` gate call.

## [0.5.1] — 2026-06-25

**Two new field-lessons from a teaching long-form rebuild** (knowledge-only; no code change).

### Added
- `knowledge/meta-lessons.md`: **M101** — cleaning self-recorded screen footage used as b-roll.
  The reliable fix is to **re-record with the target app maximized** (covering the browser / AI
  panels / IDE beside it) and crop only the OS taskbar — not to post-crop, which clips panels and
  leaves blur bars (and the app's own UI isn't PII, so don't over-crop). Plus: the clean window can
  be in the **middle** (recorder/notification UI is often at *both* ends → dense per-second scan,
  bound extraction to the clean core); a "short" played inside a full browser page needs cropping to
  the **player rectangle** (bookmark bar + others'-videos sidebar leak otherwise); and a **low-res
  contact sheet hides chrome** — check each main-footage window at full resolution.
- `knowledge/meta-lessons.md`: **M102** — on Windows, when a build script's stdout is redirected to a
  file/pipe it defaults to **cp950**, so a `print()` containing `≤` / `✓` / emoji throws
  `UnicodeEncodeError` and kills the whole build — and only in background/scheduled runs, never
  interactively. Reconfigure stdout/stderr to UTF-8 at the top of every build script + pass
  `PYTHONIOENCODING=utf-8` to subprocesses; test once in redirect mode before shipping.
- `knowledge/programmatic-video-build.md`: §0 now carries the M101 screen-capture workflow and an
  M102 build-environment note.
- `M1-M100` → `M1-M102` across the docs (also fixed a couple of stale `M1-M99` references).

## [0.5.0] — 2026-06-23

**Getting started: runnable examples.** A new `examples/` folder with self-contained,
ffmpeg-synthesized demos, so a newcomer can watch the pipeline work end-to-end in ~60
seconds — no real footage and no CapCut required.

### Added
- `examples/01_vertical_short.py` — synthesizes two landscape test clips + a music track
  with ffmpeg, then runs the real pipeline (`normalize_to_portrait` → `build_one_short`
  with multi-color captions + BGM started at its highlight) to produce a finished
  1080x1920 MP4. Verified end-to-end.
- `examples/02_caption_broll_match.py` — pure-Python (no ffmpeg) demo of zero-config
  `auto_sequence_brolls`: name b-roll by content (`coffee.mp4`, `sunset.mov`) and each
  caption gets the matching clip, with filler for the gaps.
- `examples/README.md` + a "See it run in 60 seconds" section in both READMEs.

## [0.4.2] — 2026-06-23

- `_probe_dur()` in `delivery_qa.py` + `screen_rec_cleaner.py` now raise a clear
  `RuntimeError` on a bad/missing media file instead of an opaque `float("")` crash —
  closing the last unguarded duration probes.
- `knowledge/meta-lessons.md`: added **M100** — a single grep gate is necessary but NOT
  sufficient for public-release sanitization; you need adversarial multi-round,
  multi-angle scanning looped until a full round returns zero (distilled from the v0.4.1
  remediation). `M1-M99` → `M1-M100`.

## [0.4.1] — 2026-06-23

**Privacy hardening + the font fix that should've shipped.** A 7-agent audit of the
v0.4.0 drop found that the first sanitization pass missed a layer: hard identifiers AND
semantic-layer fingerprints survived in `knowledge/meta-lessons.md` and a few sibling docs,
and the same personal context lingered in some `src/` docstrings + the example keyword map.
All scrubbed; verified by **5 rounds of adversarial multi-agent re-scan** (hard-identifier /
semantic-fingerprint / triangulation-reconstruction / code-consistency angles) looped until a
full round returned zero, backed by a whole-repo mechanical grep gate.

### Fixed — privacy
- **`knowledge/meta-lessons.md`** — removed real identifiers that slipped through: a personal
  domain, a named real-world location + its giveaway selling-points, a real project name, real
  export filenames, an absolute user path, the author-named keyword map, a real game-project
  name, the channel's brand-keyword fingerprint, and a community-metric anecdote. Also restored
  two `#000000` hex values the prior sanitizer had corrupted (broke the caption-style spec).
- **Semantic-layer scrub** across `viral-short-playbook.md`, `ig-caption-patterns.md`,
  `teaching-niche-playbook.md`, `capcut-text-templates.md`, `agent-token-efficiency.md`,
  `capcut-agent-brief-template.md`, `capcut-automation-sop.md` — generalized author-specific
  signatures, paraphrased real posts, a personal sign-off, and one-off measured telemetry into
  neutral placeholders / clearly-labeled synthetic examples. Methodology preserved throughout.
- **`src/`** — neutralized `EXAMPLE_KEYWORD_MAP` (had real game/project/location keywords incl.
  a street address), genericized an outro-card docstring's shop+address, and removed a residual
  drive path. Author-nicknamed public symbols (the keyword-map constants, the dual-tier caption
  helper, and the teaching preset keys) renamed to neutral names (`EXAMPLE_KEYWORD_MAP`,
  `apply_teaching_dual_tier`, `teaching_*`) — back-compat aliases were kept at the time, so
  existing imports still worked. (Those aliases were dropped in 0.10.0; see below.)

### Fixed — Shorts captions ship at the right size
- **`shorts_vertical.py`** — the public kit was still shipping the *old* vertical-caption font
  (MAIN 82px / ADDR 46px), which gets cropped on a 1080-wide frame. Synced to the corrected
  values (MAIN **124px** / ADDR **58px** / heavier outline) that the private pipeline already
  used, plus the load-bearing "124px = WrapStyle=2 8-char line ceiling" note.

### Fixed — robustness + docs
- `_probe_dur()` now raises a clear error on a bad/missing media file instead of an opaque
  `could not convert string to float` (benefits `find_music_highlight` + `build_one_short`).
- `pick_bgm()` no longer silently returns a too-short track when every candidate is shorter
  than the video — it warns that the pick will loop.
- Broken cross-links repaired (`references/…` paths → flat filenames), README content table
  gains a `knowledge/` row (zh + en), `M1–M96` → `M1–M99`, duplicate `# Video Craft Playbook`
  H1 disambiguated.

## [0.4.0] — 2026-06-23

**Knowledge base drop.** The kit used to ship the *tools* (`src/` helpers) but not the
*know-how*. This release adds a `knowledge/` folder — 20 markdown docs distilling the
methodology behind the tools, with all personal data stripped (creator identity, community,
channel stats, real video titles/addresses, personal script voice → all removed). MIT.

### Added — `knowledge/`
- **`meta-lessons.md`** — M1–M99 "every mistake + permanent fix" canon (look-before-caption,
  no-fabrication, chrome/privacy leaks, image framing, strobing, dead-air, Shorts BGM
  highlight, loudness-swing compression, "self-tests that mock the external tool ship bugs"…).
- **YouTube algorithm** — overview, deep mastery (MrBeast tactics + retention engineering),
  2026 insights, teaching-niche playbook, launch-hype/community-mobilization SOP.
- **Cross-platform craft** — craft overview, playbook, IG caption patterns, viral-short
  structure, 2026 Shorts/Reels best practices.
- **CapCut automation SOP** — agent-ops SOP, brief template, text-template catalog, draft-JSON
  direct editing, Pro paywall map, pure-ffmpeg build pipeline, agent token-efficiency.
- **Script** — a framework for learning *your own* script style (you fill your own profile).

> Sanitized via a 20-agent parallel pass + a mechanical leak gate (grep) over the whole folder.

## [0.3.3] — 2026-06-23

Music intelligence for vertical Shorts — auto-pick the right track, start it at the
hook, and keep the volume even. Distilled from cutting a batch of food/travel Shorts
where ambient picks felt flat and dynamic tracks swung loud→quiet.

### Added
- **`find_music_highlight(bgm, dur)`** — Shorts BGM shouldn't start at the (boring) intro.
  Uses `ebur128` short-term loudness (S) as an energy proxy and returns the start second of
  the most energetic `dur`-length window, so the whole Short rides the chorus/drop. Wired
  into `build_one_short(bgm_start='auto')` (default). Note: do NOT add `metadata=1` to
  ebur128 — it suppresses the per-frame `t:/S:` lines this parses.
- **`beat_rate(bgm)`** — rhythmic-density proxy (ebur128 momentary-loudness peak count per
  second). Ambient tracks ~1/s, upbeat/quick-cut/vocal-chop ~2.5–3/s. Use to tell energetic
  tracks from mood pieces by measurement, not by filename guessing.
- **`pick_bgm(candidates, dur, prefer='energetic')`** — automatic track selection: from a
  list of same-theme tracks, pick the one that is **long enough (no loop)** AND **most
  energetic (highest beat_rate)**. `prefer='chill'` flips it for relaxed footage.

### Fixed
- **BGM volume "swings loud→quiet"** — `build_one_short` now compresses the BGM with
  `acompressor` so the chorus/breakdown dynamics even out (peaks pulled toward the quiet
  parts) while per-beat transients survive. `dynaudnorm`/`loudnorm` do NOT fix this
  (measured); a compressor does (≈8→4 dB loudness swing).
- **Short-track loop seam** — `build_one_short` warns when the BGM is shorter than the video
  (the `-stream_loop` seam jumps audibly = another "swing" source); use `pick_bgm` to avoid it.

## [0.3.2] — 2026-06-22

Patch: two Windows integration bugs in the v0.3.1 code that the string-only self-tests
(no real ffmpeg/ffprobe) didn't catch. Surfaced the first time the vertical-Shorts
pipeline was run end-to-end.

### Fixed
- **`build_one_short` caption burn** — the `ass=` filter value held a Windows drive-letter
  colon (`D:`), which libavfilter parses as an option separator (`original_size`), so
  caption burning always failed on a Windows absolute path. Now runs ffmpeg with `cwd` set
  to the output dir and a **relative** `ass=<basename>` (no colon). (The old first attempt
  used basenames but forgot to set cwd; the fallback used the full colon path — both broke.)
- **`_probe_wh` (M92 letterbox detection)** — `ffprobe -of csv=p=0:s=x` emits a trailing
  separator + CRLF on Windows (`1080x1920x\r`), so `split('x')` returned 3 parts and raised.
  Now parses with `re.findall(r'\d+', …)` (immune to trailing separators / CRLF).
- **self-test regression guard** — added the `1080x1920x\r` parse case to `delivery_qa`'s
  self-test.

> Lesson: a self-test that mocks out the external tool (ffmpeg/ffprobe) only exercises your
> string assembly, not whether the tool accepts the args. New pipelines need at least one
> real end-to-end run before shipping.

## [0.3.1] — 2026-06-20

Hardening + reach. Makes the v0.3.0 QA layer robust on Windows/CJK setups, adds
letterbox detection to the one-shot QA, and ships a new vertical-Shorts pipeline.

### Added
- **`detect_dead_borders(video)`** (M92) — `cropdetect` flags non-full-frame footage that
  was left with dead **letterbox/pillarbox** bars (i.e. a screenshot dropped in without the
  blurred-fill background). Wired into `final_delivery_qa` → `rep['border_flag']` + a
  `M92 border` line in the report, so the same QA pass that catches flash/dead-air now also
  catches un-filled bars. Pairs with `still_blurfill` (the fix).
- **`silent_vlog_maker/shorts_vertical.py`** (M96) — pure-ffmpeg vertical (9:16 1080×1920)
  food/travel Shorts pipeline: `normalize_to_portrait` (phone .MOV → upright 9:16, handles
  mixed −90/+90 rotation via autorotate), `build_multicolor_ass` (per-word multi-color
  emphasis captions, auto emoji-strip), `extract_gps` (read clip GPS for address lookup),
  `build_one_short` (silent footage + multi-color captions + BGM-as-lead-audio). Exported
  from `silent_vlog_maker`.

### Fixed
- **Windows cp950 crash on CJK paths** — `_run()` now forces `text=True, encoding="utf-8",
  errors="replace"` so ffmpeg/ffprobe stderr with Chinese paths no longer raises mid-QA.
- **Scientific-notation-safe ffmpeg parsers** — `silencedetect` / `blackdetect` (and the new
  `cropdetect`) timestamp regexes accept `1.2e-05`-style values (`[\d.eE+-]+`); previously a
  sci-notation timestamp silently fell through to a false `[OK]`.
- **`delivery_qa` self-test** (`python delivery_qa.py`) — regression-guards
  `build_keep_ranges` / `remap_time` / `trim_dead_air_ranges` + the sci-notation black-ts,
  silence, and cropdetect parsers. `shorts_vertical.py` ships its own ASS/emoji-strip self-test.
- **`COLOR_VARIETY` name-clash** — `silent_vlog_maker.COLOR_VARIETY` stays the constants
  7-color named palette; the vertical-Shorts BGR ASS map is reached via
  `from silent_vlog_maker.shorts_vertical import COLOR_VARIETY` (no package-level shadow).

## [0.3.0] — 2026-06-16

Ship-ready QA layer (canon M91–M95). New module `capcut_helpers/delivery_qa.py` —
**run it after every export, before you call the video done.** Distilled from an
8-round fix cycle on one teaching long-form video where each issue *should* have been
caught by the editor, not the viewer.

### Added
- **`final_delivery_qa(video, voice, contact_out)`** — one-shot pre-delivery QA:
  - **M93 flash detection** (`detect_flash`) — `blackdetect` flags footage that strobes
    (action-game combat / flashing effects) or hard brightness dips that read as flicker.
  - **M95 dead-air detection** (`detect_long_pauses`) — `silencedetect` flags 1.5s+
    inter-sentence pauses (recording dead air that drags pacing). Ignores lead-in/trailing.
  - **contact sheet** (`contact_sheet`) — one frame per ~6s, tiled — eyeball every cell for
    chrome leaks / caption-visual sync / image framing.
- **`still_blurfill(img, out, dur)`** (M92) — turn a non-full-frame image/screenshot into a
  clip: same image scaled-up + blurred as the background fill (NOT solid black bars), sharp
  image centered on top, **static** (no `zoompan` jitter).
- **M95 dead-air trim, 3-track synced** — `detect_long_pauses` → `trim_dead_air_ranges` →
  `cut_audio_segments` (voice) + `cut_video_segments` (visual) + `remap_time` (caption
  timestamps), all from the **same cut list** so audio / video / captions stay aligned.
  - ⚠️ Removing audio segments uses **`atrim`+`concat`**, NOT `aselect`+`asetpts`
    (`aselect` often doesn't actually drop audio frames — silent footgun).

### Lessons (see TROUBLESHOOTING.md → "Ship-ready QA")
- **M91** screen recordings/screenshots leak OS chrome — taskbars, file-manager sidebars
  (your drive layout!), browser tabs, **financial dashboards** — crop to the content area
  and frame-audit before using. A full-desktop recording is toxic-by-default.
- **M92** non-full-frame media → blurred-fill background (never solid bars) + static + crop.
- **M93** avoid strobing footage; run `blackdetect` before delivery.
- **M94** when narration names a concrete thing ("the timeline", "the raw files", a past
  video), show the **real** thing — beats generic stock for recognition + credibility.
- **M95** trim 3–4s recording pauses down to ~0.5s; pacing = control of silence.

## [0.2.2] — 2026-06-10

Adopter-readiness sweep (multi-agent, adversarially verified): fixed the remaining
"works on the author's machine, breaks for everyone else" landmines.

### Fixed
- **subtitle_corrections** — the author's personal mishear dict no longer force-applies.
  `use_builtin_corrections` defaults to **False** in the kit, so a stranger's legit
  "cloud computing" / "studio apartment" are NOT force-rewritten to some brand casing.
- **broll_audit.narration_broll_sync_report** — defaults keyword_map to `{}` (was a
  personal content taxonomy → strangers got a vacuous always-pass).
  Now warns loudly when content labels aren't in the map instead of silently passing.
- **caption_broll_matcher** — accepts `pathlib.Path` identifiers (the module's own
  docstring example crashed with AttributeError); Latin tokens now stem (-s/-ing/-ed) so
  "pour"↔"pouring", "sunset"↔"sunsets" align; removed the author's OBS filenames/brand.
- **broll_audit._MAIN_PATH_HINTS** — added generic English hints (main/hero/product/
  interview/tutorial/recording) so non-Chinese hero footage isn't all classified "generic"
  (which made M86 ratio falsely fail / strict-mode crash a valid edit).
- **asset_scanner** — resolves project root from `VIDEO_KIT_PROJECT_ROOT` env, lazily,
  and mkdir's the assets dir (was writing to drive root / crashing scan_all_assets on a
  fresh clone — the v0.2.0 fix only addressed import, not runtime).
- **post_export.add_outro_card** — `font_path` defaults to None → resolves a system CJK
  font at runtime (was hardcoded to the author's Windows Noto path; failed on mac/Linux
  and stock Windows).

### Docs
- TROUBLESHOOTING: `batch_normalize_broll_folder` import is from `silent_vlog_maker`
  (not capcut_helpers); the importable keyword-map constant is the one to warn against.
- SETUP: explicit `templates/` → `profiles/` rename table (stripping `.template` gave wrong
  names for 4 of 6 files).

## [0.2.1] — 2026-06-10

Fix from adopter feedback: "edited output's b-roll doesn't match the captions/audio."

### Fixed
- **Caption↔b-roll matching now works with ZERO config for any user/language.** The
  matcher previously defaulted to the original author's personal Chinese topic map, so
  a stranger's captions matched nothing → all b-roll fell to generic → nothing aligned
  with the narration. Now:
  - Functions default to **filename↔caption token overlap** (language-agnostic) — name
    your b-roll after its content (`coffee.mp4`, `studio.mp4`) and it aligns automatically.
  - `auto_sequence_brolls` tags unmatched captions by their best filename match so
    per-content clips don't collapse into one blob; short content-distinct clusters are
    no longer merged away.
  - Loud `RuntimeWarning` when most segments fail to match (tells you how to fix).
- Renamed the personal topic map to `EXAMPLE_KEYWORD_MAP` (with a back-compat alias) and
  removed the author's private OBS recording filenames / brand tokens from it.

### Added
- `TROUBLESHOOTING.md` — "why your b-roll doesn't align" + the input contract.

## [0.2.0] — 2026-06-10

Bug-fix wave from a full multi-agent pipeline audit (every fix verified with functional tests).

### Fixed
- `capcut_helpers/subtitle_corrections.py` — ASCII brand corrections now word-boundary
  matched ("clearly" no longer becomes "Claudely")
- `capcut_helpers/invariants.py` — internal `_prev_text_len` snapshot no longer leaks
  into draft JSON on the clean path
- `capcut_helpers/caption_broll_matcher.py` — auto-sequencer: inter-cluster gaps now
  filled (true no-gap coverage); consolidation no longer extends trims beyond the
  b-roll's real source duration; mismatch audit now picks the subtitle track by CJK
  character count (was: first track wins)
- `capcut_helpers/text_style.py` — CapCut SystemFont dir resolved at runtime across
  versions (was: hardcoded version dir that dangles after CapCut upgrades)
- `silent_vlog_maker/text_overlay.py` — drawtext fade alpha now uses overlay-relative
  time (overlays with t_start>0 were fully transparent)
- `silent_vlog_maker/effects.py` — kenburns_zoom_in honors portrait target_scale
  (was anamorphic-stretched); kenburns_pan_right actually pans right (expression was
  out of zoompan's valid range)
- `silent_vlog_maker/screen_rec_cleaner.py` — clean_voice_pauses wires min_silence_sec
  into silenceremove (was trimming ALL pauses); clean_screen_recording defaults now use
  the documented v3 crop values (200/80/zoom)
- `silent_vlog_maker/quality_check.py` — audio-leak check implements the documented
  LUFS rule via bgm_only flag, and loudnorm parse failures no longer report as leaks
- `silent_vlog_maker/frame_audit.py` — skips redundant ffprobe when caller already
  knows clip duration (−1 subprocess per clip)
- `silent_vlog_maker/asset_scanner.py` — project-root resolution no longer raises
  IndexError in shallow checkouts (import crashed for adopters)

### Added
- `silent_vlog_maker/shorts_captions.py` — multi-color/size Shorts captions, 3 levels,
  2026 research helpers (safe zone / chunking / active-word karaoke highlight)
- `silent_vlog_maker/shorts_template.py` — no-face viral Shorts template (niche presets,
  hook card renderer, 3 hook formulas)

## [0.1.1] — 2026-06-02

Onboarding + positioning fixes from early adopter feedback.

### Changed
- **CapCut is now correctly framed as the primary editing path; ffmpeg is secondary.**
  Requirements previously listed ffmpeg as required and CapCut as optional — inverted.
  `silent_vlog_maker` (ffmpeg) is now clearly labelled "silent vlogs + post-export only".
- **Computer Use is now documented as a hard requirement.** CapCut has no public API;
  `capcut_helpers` automation works by an AI assistant driving the CapCut GUI via Computer
  Use. README + SETUP now state this up front (it previously wasn't mentioned at all).
- **`SETUP.md` onboarding sped up.** Added a "5-minute minimum start" (3 ★required sections
  vs 3 ⭕optional), and made "let the AI interview you" the recommended low-effort path —
  so adopters can start without filling the entire questionnaire first.

### Fixed
- Removed a broken `docs/` reference in README (the folder doesn't exist).

## [0.1.0] — 2026-06-01

Initial public release — extracted + sanitized from a real, battle-tested personal
creator system into a reusable framework.

### Added
- **`src/capcut_helpers/`** — CapCut Desktop JSON automation library
  - draft I/O with 7-file sync, 4-level mute, text presets, effects swap
  - `post_export` ffmpeg helpers: voice-end trim, **BGM loop-fill (crossfade seam)**,
    player-safe re-encode, outro card
  - AI-subtitle correction dictionary
  - **b-roll audit** (`broll_audit`): generic-vs-main ratio + narration↔visual sync
  - caption↔b-roll matcher + auto-sequencer
- **`src/silent_vlog_maker/`** — ffmpeg-only pipeline utilities
  - 11-dimension raw-clip audit (GPS / capture-time / camera / audio)
  - scene clustering, hi-res frame audit, KenBurns + cinematic grade
  - screen-rec auto-cleanup, b-roll intake normalize, quality check
- **`SETUP.md`** — 6-section onboarding questionnaire (fill-your-own-data)
- **`templates/`** — voice / brand / algorithm / community / content-pipeline / context
- `config.example.py` — path config via env vars (auto-detects current user)

### Security / Privacy
- De-personalized: **no PII, no secrets, no business-sensitive data, no personal
  voice profiles**. `voice_profiles.json` ships as an empty skeleton.
- Paths auto-detect the current user (no hardcoded usernames).
- `.gitignore` excludes all media, `profiles/`, and `config.py`.

### Not included (by design)
- The original creator-specific orchestration layer (personal pipeline rules,
  brand, community config) — define your own via `templates/content_pipeline.template.md`.
