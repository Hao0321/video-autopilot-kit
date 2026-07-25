# Changelog

All notable changes to **video-autopilot-kit** are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

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
  drive path. Author-nicknamed public symbols (`HAO_*_MAP`, `apply_hao_teaching_dual_tier`,
  `hao_teaching_*` preset keys) renamed to neutral names (`EXAMPLE_KEYWORD_MAP`,
  `apply_teaching_dual_tier`, `teaching_*`) — **back-compat aliases kept**, so existing imports
  still work.

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
  (not capcut_helpers); warn-against name is `HAO_CAPTION_KEYWORD_MAP` (the importable one).
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
