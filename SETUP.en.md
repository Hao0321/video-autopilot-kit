# SETUP — Answer these to make the system *yours*

> **This repo isn't a hand-me-down config — it's a framework + questionnaire.**
> It distills a battle-tested YouTube / short-form automation system into templates.
> You answer the questions below and it generates **your own** voice / brand / strategy
> / community files. The code is generic; **all personalization comes from your answers —
> none of the original author's private data is included.**

*(中文版見 [SETUP.md](SETUP.md))*

## 🧭 Platform requirements (read this first)

The kit has **two first-class paths** with different requirements:

- **Path 1 — Programmatic (recommended default for adopters; Win / Mac / Linux)**: just Python 3.9+ and `ffmpeg`/`ffprobe`.

  **Installing ffmpeg (one-time, all platforms):**
  | Platform | Command |
  |---|---|
  | macOS | `brew install ffmpeg` (needs [Homebrew](https://brew.sh); verify with `ffmpeg -version`) |
  | Windows | `winget install ffmpeg`, or grab a full build from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) and add it to PATH |
  | Linux | `sudo apt install ffmpeg` (Debian/Ubuntu) |

  > Common misconception: "Mac doesn't have ffmpeg" — ffmpeg is cross-platform by design, and the Mac install is actually the easiest (one brew line). "Alternatives" like MoviePy / editly call ffmpeg under the hood anyway. **No CapCut, no Computer Use.** System paths and CJK fonts on Mac/Linux are auto-detected by `src/platform_compat.py`.
- **Path 2 — CapCut-assisted (what the author personally uses; Windows-first)**: additionally needs CapCut Desktop (international edition) + your AI assistant's Computer Use. **Version-sensitive** — read the compatibility matrix in [TROUBLESHOOTING](TROUBLESHOOTING.md) before touching draft JSON.
- **On Mac** → go straight to Path 1 (there is no working equivalent of the CapCut GUI automation on Mac).

## ⚡ Fastest start (you don't have to fill it all in!)

> **Think the questionnaire is long? You don't need to finish it before starting.** Of the 8
> sections below, only **3 are ★required** — fill the rest **as you go**. 7️⃣ and 8️⃣ are
> per-production-line: skip them entirely if you're not doing interviews / Shorts.

**Recommended — let the AI interview you (least effort):**
Hand the whole repo to Claude / ChatGPT and paste:
> "Ask me only the **★required 3 sections** from `SETUP.md` first (Brand, Niche, Production) and generate my `profiles/`. Ask the optional sections later."

The AI asks one question at a time and fills the files for you — **you just answer out loud**.

**5-minute minimum (answer just these 3 to start):**
1. Channel name? **Do you show your face?** (decides whether intros/outros schedule an on-camera cue)
2. What do you make, and which platform? (tutorial/vlog…, YT long-form/Shorts/Reels)
3. **Path 1 (programmatic, cross-platform)** or **Path 2 (CapCut, Windows-first)**? Where are your asset / export paths?

→ That's enough to start editing. Voice / Algorithm / Community (4️⃣5️⃣6️⃣) can wait until you want to optimize.

**Manual route (3 steps):**
1. Copy `templates/*.template.md` → `profiles/*.md` (drop the `.template`)
2. Fill the **★required** sections (1️⃣2️⃣4️⃣) first; leave the rest blank
3. `cp config.example.py config.py` → fill in your own paths

---

## 1️⃣ Brand / Channel → generates `profiles/brand.md`　★required
- Channel name + handle? Website / main link?
- **How do you sign off?** (voice-over / title card / on-camera?) — this becomes your outro signature
- ⚠️ **Do you film talking-head / show your face?** (Important — if not, intros/outros must use b-roll + cards, never "selfie cue")
- Brand colors / preferred fonts? Subscribe-CTA placement?

## 2️⃣ Niche / Content type → routes the pipeline　★required
- What do you make? (tutorial / vlog / unboxing / review / gaming …)
- Main platform? (YT long-form / Shorts / Reels / TikTok)
- Language?

## 3️⃣ Your Voice → generates `profiles/voice.md`　⭕optional (add later when tuning scripts)
- **Paste 5–10 scripts/posts you wrote yourself** — the system learns *your* voice, not someone else's
- Your typical opener? Catchphrases? Sign-off?
- **Hard no's?** (anti-patterns — e.g. no profanity, no fake hype, no certain memes)

> Want the next step — turning "doesn't sound like me" and "my audience won't follow this"
> into things a **machine** can block? Use the cumulative version,
> `templates/style_profile.template.md`. Its §5 produces `audience_vocab.json`
> (skeleton: `templates/audience_vocab.example.json`), which
> `src/longform_maker/script_gate.py` reads to gate a script **before you record it**.
> **Those four word-lists ship empty on purpose** — they can only be audited out of your own
> transcripts, and copying someone else's means checking your script against *their* audience.
> Method → `knowledge/script-retention-craft.md`.

## 4️⃣ Production → generates `config.py`　★required
- **Which path are you on?** (see "Platform requirements" up top)
  - **Path 1 Programmatic** (recommended default; Win/Mac/Linux) — pure-code pipeline, just Python + ffmpeg, **no CapCut**
  - **Path 2 CapCut-assisted** (Windows-first) — pick this only if you want CapCut's fancy-text / cloud templates
- If Path 2: is **CapCut Desktop (international edition)** installed? ⚠️ **Does your AI assistant have Computer Use enabled?** CapCut has no public API — GUI automation works by the **AI operating the CapCut window via Computer Use** (apply templates / export); without it, it won't run. Draft-JSON editing is **version-sensitive** — run `detect_draft_format()` first and read [TROUBLESHOOTING](TROUBLESHOOTING.md)
- Where are your **fonts** / **BGM** / **b-roll** stored? Project / export paths?
- (Filled into `config.py` — the example contains **no account names**)

## 5️⃣ Algorithm context → fills `profiles/algorithm.md`
- Your current numbers? (subs / avg views / CTR / average view duration)
- Main traffic source? (Browse / Suggested / Search / External …)
- Biggest pain point? (reach / retention / CTR …)
- (The framework gives you **which metrics to watch and how to fix them**; you fill in **your** numbers)

## 6️⃣ Community / external traffic → fills `profiles/community.md`
- Which communities do you have, and how big? (chat community / group chat / newsletter / social platforms …)
- Which channels can you mobilize at launch?
- (Gives you the mobilization-SOP **structure**; your communities, your numbers)

## 7️⃣ Interview show → generates `profiles/show.md`　⭕optional (**only if you run the interview line**)

Not doing interviews? Skip the whole section — nothing else depends on it. If you are,
**every** file `src/interview_autopilot.py` renders (invite message / host script / consent
form / publish kit…) quotes these five answers. Leaving them blank doesn't break anything, but
every unfilled field renders as a **visible brace-wrapped placeholder** instead of an invented
value. Heads-up if you don't read Chinese: the placeholder text itself is Chinese
(`{你的節目名}` / `{你的名字}` / …), so **don't grep for the English word "your"** — grep the
output for a literal `{`, which catches every one of them regardless of locale. `plan` also
prints a `WARN 節目 profile 未填: …` line listing exactly which fields are still blank.

1. **What's the show called?** → goes in the consent-form title, the invite message, the opening card
2. **What do you call the host?** (real name or the name you go by) → the producing party on the
   consent form, and your self-introduction in a cold invite
3. **Which single link is the audience's landing spot?** (community / newsletter / site) →
   goes in the description and the pinned comment
4. **What do you record with?** → the requirement is **local per-track recording with raw-file
   upload**; write down the fallback chain too (main tool → video call + local record → cloud
   mixed track only as a last resort). This one goes into section 3 of
   `templates/interview/format_bible.template.md`
5. **Your sign-off, word for word?** → the host script's last beat is read from this;
   **identical in every episode is what makes it a show**

> Answers 1/2/3/5 go into `profiles/show.md` (template: `templates/show_profile.template.md`).
> Fill two more fields while you're there: `CLUSTER` (an interview is **the same topic line in a
> different format, not a new line** — use your existing topic keyword, never "interview") and
> `PLATFORMS` (every platform you'll actually publish or repost to — **the consent form quotes
> this verbatim, so an incomplete list means an incomplete release**).
>
> ⚠️ **Only a human can stamp compliance**: `plan` writes the compliance field as "pending review"
> and the gate blocks on it; you pass `--compliance-ok` yourself, after you've walked your
> platform's AI-content policy checklist. Methodology →
> [`knowledge/interview-show-playbook.md`](knowledge/interview-show-playbook.md).

## 8️⃣ Shorts rule calibration → override the `shorts_gate` thresholds　⭕optional (**only if you cut vertical Shorts**)

`DEFAULT_RULES` in `src/longform_maker/shorts_gate.py` is an **example calibration, not a
universal law** — it came from one kind of content (no-narration, single-surprise vertical
shorts). **Someone else's thresholds won't block your bad cuts, and may block your good ones.**
Recompute them from your own videos:

| Measure | Threshold key | Ask yourself |
|---|---|---|
| **Duration band** | `dur_min` / `dur_max` | How long are your 3-5 best Shorts? Take the range. The default keeps "gag / single surprise" at 13-25s |
| **Dead zone** | `dur_deadzone` | Is there a length that lands in **neither camp** (too long for a gag, too short to teach)? The default treats 26-44s as dead; set `None` if you don't want one |
| **First cut** | `first_cut_max` | How many seconds before the picture must change for the first time? Measure it on your best few |
| **Non-white caption cap** | `nonwhite_max_ratio` / `nonwhite_max_colors` | Are your captions **white-first**, with accent colors as garnish? Measure the non-white share and how many colors your best few actually used |

**How to calibrate (two steps — the second is not optional):**
1. Measure your **best** 3-5 and set the thresholds from that range
2. Run your **worst** 3 through the gate and **confirm they get blocked**. A threshold that only
   passed step 1 is decoration

**Override without editing the file** (edits make every future update a conflict) — pass a dict
with just the keys you're changing:

```python
my_rules = {"dur_min": 26.0, "dur_max": 60.0, "dur_deadzone": None}
ok, rep = gate_shorts(spec, my_rules)     # check
ready   = assert_shorts(spec, my_rules)   # call before build; raises if it fails
```

**Before you hand-write a duration override, check whether you just need a different platform**
(v0.11). The shipped dead zone was measured on **YouTube** Shorts and does not belong on IG/FB,
so the band now comes from `spec["platform"]`:

```python
spec["platform"] = "ig_reels"   # yt_shorts (default) / ig_reels / fb_reels
```

That supplies defaults for the three duration keys only, and your `rules=` still wins **per key**
— so you can name a platform *and* narrow its band in the same call. Omit `platform` and you get
`yt_shorts`, i.e. exactly the v0.10 behavior. A platform name that isn't in `PLATFORM_RULES` is a
**blocking failure**, never a quiet fallback to the default — add your own row to `PLATFORM_RULES`
instead. The one-command driver carries it end-to-end: `shorts_autopilot.py scan --platform
ig_reels` writes `platform=` into the generated `_plan.py`, so `build` grades the cut by the band
the plan was designed for.

Want to see the gate first? `python examples/04_shorts_gate.py` (pure Python — no ffmpeg, no
media). The knowledge behind the rules →
[`knowledge/shorts-mastery-2026.md`](knowledge/shorts-mastery-2026.md); how to measure a
competitor's cut rhythm yourself →
[`knowledge/vertical-teardown-method.md`](knowledge/vertical-teardown-method.md)
(`python src/teardown.py <file>`).

---

## Why a questionnaire instead of a ready-made config?

The most valuable part of a creator system is its **structure and methodology**, not one
person's private numbers. Copying someone else's voice / strategy / community data won't
help you — it may mislead you. So this repo gives you the **skeleton**; you fill it with
your own flesh. That's what makes it truly **yours**.
