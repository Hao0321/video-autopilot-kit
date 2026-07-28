> Part of the video-autopilot-kit open-source knowledge base · MIT license

# Premium Motion & FX Playbook — data cards, counters, SFX, finishing

> Synthesized from a six-track deep-research pass (2026-07) on what separates "clean but amateur"
> programmatic videos from premium-feeling ones. 18 upgrades in three waves, plus an explicit
> skip list. The rendering engine lives in `src/longform_maker/fx_lib.py`; caption timing comes
> from `src/longform_maker/word_captions.py` (M105); QA gates live in `src/capcut_helpers/delivery_qa.py`.
>
> Three non-negotiables run through everything:
> - **Retention > spectacle** — every high-energy effect gets a frequency cap.
> - **Teaching clarity > FX** — body captions are never animated.
> - **Zero violations of the hard rules** — Ken Burns is always sub-pixel float (no `zoompan`),
>   captions stay white-first (color-ratio audit gate), counters must land on the true value (no fabricated numbers).
>
> Algorithm-side counterparts (Test & Compare, 30s retention threshold, etc.) → `knowledge/youtube-algorithm-2026.md` (R15–R25).

---

## Wave 1 — Wiring week (rank 1–9, almost all low effort). Finishing this alone moves you from "clean" to "textured".

### 1. Kill every static card: sub-pixel Ken Burns + texture pass on all still-image cards [low]

Drop the `-loop 1` static-image path and render frame-by-frame. Per card: 180 frames (6s @ 30fps).
Render the source art at 2x first (e.g. 3840x2160, parameterize W/H), then per frame:

```python
ken_burns_frame(src2x, t=i/179, z0=1.0, z1=1.05, pan=(0.01, 0), ease=smootherstep)
texture_pass(im, grain=5, vig=0.14, seed=i)   # new grain seed every frame
```

- `smootherstep(t) = 6t**5 - 15t**4 + 10t**3`
- Alternate push-in / pull-out on odd/even cards (1.00→1.05 / 1.05→1.00) so consecutive cards don't all drift the same way.
- Keep the 0.35s fade-in; remove any `tpad`-cloned hold segments (a "hold" is just the KB slow push continuing).

Why: a card that sits fully still for >5s is a retention cliff — the frame reads as dead. Sub-pixel
float breathing fixes it with zero jitter (the `zoompan` integer-jitter ban stays absolute), and the
per-frame grain seed simultaneously dithers away gradient banding on dark backgrounds.
**Highest ROI item in the whole plan** — the library functions already exist; it's ~40 lines of wiring.

### 2. Hero counter trio: expo easing + fixed digit slots + landing pop/glow, with a true-value frame gate [low]

- (a) `ease_out_expo(t) = 1 if t >= 1 else 1 - 2**(-10*t)` for the count-up (replaces ease-out-cubic); stretch the intro count to ~1.8s.
- (b) **Fixed digit slots**: `w_slot = max(draw.textlength(d, NUM_FONT) for d in '0123456789')`; each digit centered in its own slot, comma slots at 0.5x — the rolling number never changes width (width-jitter is the single most visible amateur tell).
- (c) **The final frame is forced to the true value** — assert it in code (e.g. if the real metric is `1,234,567`, the last frame must render exactly `1234567`). An eased counter that lands on an approximation is a fabricated number.
- (d) After landing: +2 frames scale pop 1.00→1.06→1.00, then a 6-frame accent-color glow pulse (opacity 0→1→0.4).

Why: the hero number becomes the strongest 3 seconds of the video and feeds the 0–5s hook directly.

### 3. Double-layer additive bloom instead of single glow (curves, accent numbers, endpoint dots — one shared function) [low]

- Layer 1: `GaussianBlur(radius=4)` at 60% brightness.
- Layer 2: `GaussianBlur(radius=16)` at 30% brightness.
- Composite both with `ImageChops.screen`, then paste the sharp original element on top.

Route every glowing element (big accent numbers, curve endpoint dot, chapter-card digits) through
this one function; the counter's landing pulse is this bloom's opacity animated 0→1→0.4 over 6 frames.
Single-layer glow reads as a sticker; dual-radius bloom reads as lens optics. On a dark background
with a warm accent color this is the core "clean → expensive" visual recipe.

### 4. Stagger entrance system: chips/bullets enter one by one, always ≥2 animated properties [low]

- Sibling elements inside a card enter with `stagger(per_ms=80, dur_ms=400)` + `ease_out_quint`. Never all at once.
- Each element animates at least two properties: opacity 0→1 (done by 50% of the duration) + translateY +24px→0 (full duration); key elements add scale 0.95→1.0.
- Practical spacing: bottom chips ~2.4 frames apart, bullets ~3 frames per line; if a card has >10 elements, compress the whole cascade into a 0.8s window.
- Elements in the same group share one easing curve.

Why: "PowerPoint everything-appears-at-once" becomes guided eye movement; single-property fade-ins
are what make templates look like templates.

### 5. SFX wiring: `adelay` millisecond alignment to cuts / landings / entrances [medium]

- Synth low-end hit if you have no asset: `sig = 0.9 * sin(2*pi*80*exp(-2.5*t)*t) * exp(-4*t)` (~1.0s).
- Build the SFX event list mechanically from the cut plan: transition cut frame → whoosh; accent-number landing frame → hit + pop; chip/bullet entrance → tick on the **first** element only (not per element).
- Each event: `adelay=ms|ms` where ms = cut-frame time × 1000 minus the sample's transient offset — target **±50ms** accuracy. Then `amix` everything and run it through your normal loudness chain (M103).
- Levels: SFX peaks 6–10dB below narration. Density cap: ≤5 per minute; rotate 2–3 variants per SFX type.
- Since cut points are script-generated, alignment is 100% mechanical — no hand-syncing.

Why: silent transitions read as a mute slideshow — the biggest single amateur tell. Research across
sources converges on **SFX-aligned-to-visual-hits as the largest single "clean → premium" lever**,
and it multiplies with transitions and punch-ins.

### 6. Final-pass finishing: split-tone + curves + single-layer grain/vignette (no flicker) [low]

Fixed final `-vf` before encode:

```
curves=master='0/0.02 0.5/0.5 1/0.98',colorbalance=rs=0.02:bs=0.06:rh=0.04:bh=-0.04
```

- That pushes shadows cool and highlights warm — tune the values toward your own brand palette (the example assumes a cool-dark background with a warm accent).
- Keep `libx264 -crf 18` — grain eats bitrate; do not raise CRF.
- **Grain/vignette exactly once**: clips already textured per-frame in Python get nothing extra; pure-ffmpeg segments (screen recordings etc.) get `vignette=a=PI/5` + `noise=c0s=7:c0f=t+u` at this stage instead.
- Explicitly no brightness flicker / "filmic exposure breathing" (see skip list #3).

Why: half of "premium" is the whole video looking graded by one hand. A split-tone that matches your
brand's cool/warm structure makes the grade read as brand language for free.

### 7. Subtle ASS caption dynamics: ≤1 emphasized keyword per line + blur-in on chapter cards (white-first stays law) [low]

- (a) Keyword-table match (tool names / true-value numbers / conclusion verbs); at most **one** word per line gets `{\fscx112\fscy112\c&H3FD2FF&}` (that BGR value = RGB 255,210,63 — substitute your accent color). Everything else stays white-on-black-outline, and the whole file must still pass the color-ratio audit gate.
- (b) Chapter title cards get `{\blur16\alpha&HFF&\t(0,280,\blur0\alpha&H00&)}` — a 280ms blur-in.
- (c) Body captions get **no** animation (teaching clarity > FX). Word-level timing is already mechanical via whisper word timestamps (M105) — zero hand-keying.

Why: for CJK audiences the caption line is the primary reading surface, so in-caption emphasis has
zero attention-switch cost, is cheaper than a separate graphic, and libass renders it for free.

### 8. Hook second-by-second template: 0–5s true-value cold open → 5–15s promise → 15–30s first step [low]

- 0:00 — drop 3–5s of the actual payoff (hero-counter climax or the thing working) + one result statement.
- 5–15s — "here is what you'll walk away with" promise card.
- 15–30s — straight into step one.
- Banned: self-intro, "hey everyone", channel intro. Open-loop card: "How? In X minutes you'll do it yourself."
- The exact frame shown in the thumbnail must appear within the first 30s (packaging promise honored).
- Log Outcome metric: first-30s retention vs **your own 30s checkpoint** (`<fill in>` — calibrate per
  `knowledge/youtube-algorithm-mastery.md` §3). Below it = restructure the hook next video.

Why: 30s retention is the earliest signal that packaging and payoff line up, and one template change
benefits every future video. **This kit publishes no channel's analytics readings**, so the pass mark is
yours to measure, not a constant to copy — take your last 3-5 same-format uploads, read each at 30s, and
split them by whether the algorithm picked them up; the boundary is your checkpoint. Track the
video-over-video *delta* rather than an absolute number (see R24 in `knowledge/youtube-algorithm-2026.md`).

### 9. Three mechanical retention gates: scene-pacing windows + freeze∩silence + an interrupt schedule [low]

- (a) `ffprobe -f lavfi "movie=final.mp4,select=gt(scene\,0.2)" -show_entries frame=pts_time` → collect all visual-change points; max allowed gap between neighbors: **≤7s in 0–30s, ≤15s in 30s–3min, ≤30s after 3min**. Over-window = red, with the offending seconds listed.
- (b) Intersect `freezedetect=n=-60dB:d=3` with `silencedetect=noise=-35dB:d=2`; any overlap = red (frozen picture + silent audio is where retention cliffs live).
- (c) Add an "interrupt" column to the storyboard: first interrupt at t≈30s, then one every 75±15s — an interrupt changes picture **and** sound in the same beat. QA verifies every 90s window contains ≥1 major change. After publish (~72h), map the Studio retention dips back onto this schedule to close the loop.

Why: you intercept retention cliffs before upload instead of discovering them in analytics.

---

## Wave 2 — Rhythm & structure (rank 10–15): attacks mid-video drop-off directly.

### 10. Chart reveal grammar + cumulative build-up, reveal bound to word-level timestamps [medium]

- Every data card becomes three beats: grid+axes fade in with an 8px slide (0.3s) → 0.2s rest → data draw-on (curve drawn arc-length-parameterized over 1.2–2s with a glowing leader dot; bars grow from baseline over 0.4s with `ease_out_quint` + stagger).
- The reveal-complete frame is bound to the **word-level timestamp** of the number in the narration (from `word_captions.py`) — the number lands exactly when it is spoken.
- Elements supporting one argument accumulate **on the same card** instead of cutting to new cards: state0 skeleton → +number → +curve → +conclusion label, each new element entering with an 8–10 frame alpha+slide.

Why: data sections stop being "cut to static card" and become "the argument is growing" — and since
word-level alignment is mechanical here, you get for free what other channels hand-key.

### 11. Hard-cut punch-in at 112% (zero-jitter emphasis) [low]

- On the onset frame of a key word (whisper word-level locate), the frame jumps to **1.12x**. Either render the scene at two scales from 2x source art (zero quality loss), or per segment: `crop=iw/1.12:ih/1.12,scale=1920:1080:flags=lanczos`.
- Instant jump, no animation = zero jitter (bypasses `zoompan` entirely). Return to 100% on the next sentence start.
- Frequency: ≤1 per 20–30s in explanation sections; only on genuinely key words.
- Combine on the same frame with the caption keyword turning accent-colored (#7) and a pop SFX (#5).

Why: reads as a "new shot" without new footage — a free attention reset every 20–30s.

### 12. Transition semantics: wipe = chapter change, whip = high energy, zoomin = advance, default stays hard cut [medium]

- Chapter change — `xfade transition=custom` soft-edged diagonal wipe:
  `expr='st(0,(X/W+Y/H)/2);st(1,clip((ld(0)-(1-P*1.15))/0.15,0,1));A*(1-ld(1))+B*ld(1)'`, `duration=0.5`, `offset=prev_len-0.5`.
- High energy — `slideleft` + `sendcmd`-animated `gblur` whip-pan (sigma 0→26→0, `sigmaV=0` horizontal-only, d=0.4).
- Key advance — `xfade=zoomin` (needs ffmpeg 5.1+). Gate on `ffmpeg -version`; below 5.0 fall back to hard cuts everywhere.
- Frequency caps: wipe ≤3 per video, zoomin ≤2 per video, everything else hard cut. Both inputs must match fps/resolution/timebase. Every transition gets its whoosh (#5).

Why: a 0.4–0.5s directional transition is an explicit "chapter page-turn" signal — structure the viewer can feel.

### 13. Chapter number cards + BGM energy arc + beat-snapping [medium]

- `render_chapter_card(n, title)`: dark brand background + huge accent-color numeral (~320px display font, double bloom) + smaller white chapter title; 0.8–1.2s on screen, entering with a whoosh.
- BGM arc: hook = high energy → explanation = minimal track or the same track muffled (`lowpass=f=2000,volume=-4dB`) → reveal/outro = full bandwidth + rising cue. Chapter boundaries: `acrossfade=d=1`.
- Snap the chapter-card pop frame to the first downbeat within 2s of the new section (`librosa.beat.beat_track`), ±0.2s.
- Persistent corner progress indicator: 3 small dots, current chapter filled with the accent color.

Why: "how much is left" structure directly attacks mid-video drop-off, and the muffle/track-change
is a free auditory pattern interrupt. Never loop one track flat through the whole video.

### 14. Mechanical silence compression + a words-per-minute report [medium]

- `silencedetect=noise=-35dB:d=0.7` on the narration: gaps <0.7s keep (breathing); 0.7–1.0s compress to 0.5s; >1.0s compress to 0.3s.
- Cut points protected by whisper word-level times so word tails are never clipped; output an offset map, and shift captions + cut points by the same map (content-alignment gate still runs).
- Print words-per-minute: script character count ÷ final narration seconds. Target **240–280 CJK chars/min** (roughly 150–170 English wpm). Below ~230 → raise the global speed constant to 1.08–1.15 (one constant through audio/video/captions — see M103); above ~290 → insert 0.3s breathing gaps between sections, always covered by a visual event.
- Set `encoding=` explicitly on subprocess stderr reads (Windows cp950 trap, M102).

Why: dead air is the most consistent bleed-point on retention graphs; pacing goes from a feeling to a routine per-video number.

### 15. Re-hook flash-forwards x2 + a question-card beat per chapter [medium]

- `insert_rehook(payoff_ts, insert_ts)`: at ~25% / ~50% / ~75% of runtime, insert 1.5s of a later payoff (`ffmpeg -ss X -t 1.5`, hard cut + whoosh); reserve one script line — "in a minute you'll see…".
- Once per chapter: narration poses a question → cut to a 0.6–0.8s question card (dark background + accent question mark, scale breathing 1.00↔1.02 rendered per frame; BGM keeps playing so it's not dead air) → the answer number pops in with a hit SFX.

Why: tutorial retention naturally sags at 40–60% of runtime; flash-forwards are the best-evidenced
fix for exactly that zone, and the question card plants an open loop.

---

## Wave 3 — Signature & packaging (rank 16–18)

### 16. Recap card upgrade + a source-attribution line as standard [low]

- 6–8s before the outro: accent-colored "Key takeaways" title + 3 white bullets (each short enough to read at a glance), entering with a 0.5s stagger while the narration says "let me give you the three takeaways".
- Design the card to be fully readable as a single screenshot — it doubles as a share graphic for socials/messaging groups.
- Every data card gets a dim ~22px source line bottom-left ("Source: platform analytics dashboard, YYYY-MM") — make it a canvas parameter.

Why: a recap lifts end-of-video satisfaction (which feeds the survey-driven distribution signal),
and visible sourcing converts directly to trust in the AI-tools niche.

### 17. Light sweep on the hero number (signature-shot finisher) [medium]

- `light_sweep(mask, t)`: a 45° white gradient band (width = glyph height × 0.6, both edges feathered with `GaussianBlur(10)`), masked by the numeral's alpha, sweeping x from −w to +w over 0.5s, pure linear (a sweep must not decelerate), `screen` blend, peak opacity 50%.
- Trigger: 0.3s after the counter's landing pop+glow. Limit: 1–2 uses per video (hero + conclusion card only).

Why: flat accent-color numerals instantly read as reflective material — the frame-rendered
equivalent of AE's CC Light Sweep. The hero number is channel identity; this is its final piece.

### 18. Thumbnail PIL auto-gate + Test & Compare with 3 "promise-strength" variants [low]

Mechanical gate before any thumbnail ships:
- Face bbox height ≥288px (0.40 × 720) if a face is used.
- Foreground elements ≤3 (rough connected-component count).
- Big CJK text ≤4 characters (or ~3 words), with **zero** string overlap with the title.
- Number glyph height ≥80px.
- Subject/background luminance contrast ≥4.5:1.
- Auto-export a 200x113 glance-check image pasted into a simulated feed.

Test & Compare: always upload 3 variants that test **promise strength**, not style —
A = true-value number promise, B = tool-name promise, C = result-image promise. Let it run the
full ~2 weeks; don't call it early. Default title template: first-person true-value transformation
("I used X to do Z in Y"), strongest promise inside the first ~12 CJK characters (~5 words);
negative framing only as a B variant.

Why: Test & Compare now scores by watch-time-per-impression, not raw CTR (R15) — this is the one
packaging lever that attacks impression ceiling and retention at the same time.

---

## ⛔ Explicit skip list

1. **ffmpeg `zoompan` in any form** — permanently banned: integer-coordinate jitter is unfixable. Every push/slow-zoom goes through `fx_lib.ken_burns_frame` sub-pixel AFFINE.
2. **Persistent chromatic aberration / VHS / glitch montages** — persistent CA reads as degraded game footage; glitch clashes with teaching credibility. Keep only the "impact frame" version (1–2 frames, ≤2px, edges only; `fx_lib.chromatic_aberration` exists but defaults off), used only on "it broke / fail" beats, ≤2 per video.
3. **Brightness flicker (±0.9% "filmic exposure breathing")** — collides head-on with the strobe/flicker lesson (M93); tiny upside, real risk. Filmic texture comes from grain + split-tone instead.
4. **Full-screen variety-show text stickers / emoji bombardment** — kills perceived expertise in a tutorial niche and clashes with a premium dark+accent look. Emotional markup is carried by caption keywords + SFX + chapter cards. Re-entry condition: only if retention data shows a flat emotional mid-section, and then a restrained version (white face + colored outline, ≤4 per video).
5. **Colored karaoke / multi-color rotating captions** — white-first is locked law. Caption dynamics are limited to blur-in, small slides, and ≤1 accent-colored keyword per line, with the whole video passing the color-ratio audit.
6. **Overshoot / elastic bounce on everything** — everything bouncing = cheap variety-show feel. `ease_out_back` is reserved for the hero numeral and conclusion cards (≤3 uses per video); everything else uses `ease_out_quint` / `ease_out_expo`.
7. **MrBeast-style constant fast cutting (ASL <2.5s throughout)** — the winning tutorial pattern is calm 15–25s cuts alternating with a burst every 2–3 minutes. Constant fast cuts destroy teaching clarity and fatigue the mid/late sections.
8. **More sensational / clickbait thumbnails** — once your CTR sits in the "good" band of the published benchmark (see the CTR rating table in `knowledge/youtube-algorithm-mastery.md` §4 — do not borrow any single channel's actual CTR as your cutoff), the bottleneck isn't CTR; and with Test & Compare judging by watch-time-per-impression, bait loses automatically. Optimize promise **accuracy** instead (R15).
9. **Odometer per-digit rolling numbers** — count-up + fixed digit slots already delivers ~90% of the effect; per-digit rollers are high effort, marginal gain. Revisit only after the hero number is an established series signature.
10. **External-platform traffic blasts as a default growth tactic** — default to YouTube-native levers (packaging tests, retention, Shorts as entry, search, your own video cluster). External funneling is opt-in, not part of the standard pipeline. (The Hype button is on-platform and has its own playbook — R25.)
