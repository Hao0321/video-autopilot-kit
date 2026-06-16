# Changelog

All notable changes to **video-autopilot-kit** are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

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
  "cloud computing" / "the crowd" / "studio apartment" are NOT rewritten to Claude/Studio.
- **broll_audit.narration_broll_sync_report** — defaults keyword_map to `{}` (was the
  author's studio/gamehall/player/coding taxonomy → strangers got a vacuous always-pass).
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
