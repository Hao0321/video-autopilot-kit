# SETUP — Answer these to make the system *yours*

## Step 0: Install Editkin first

VA (this Kit) only plans and checks; **[Editkin](https://github.com/Hao0321/Editkin) is what actually edits
and renders**. Without Editkin, nothing gets edited. Do the five short steps below once, then set up the Kit.

> This is a **preview**: you can install it and try automatic editing, but it changes quickly and you will hit bugs.
> It is **Windows 10/11 (64-bit) only** for now. This build is **not code-signed** and has **no automatic
> updates**; download new versions from Releases yourself.

### 0-1 Download and install

1. Download the Windows installer only from Editkin's GitHub Releases page:
   - This version: [v0.15.0-preview.20261022](https://github.com/Hao0321/Editkin/releases/tag/v0.15.0-preview.20261022)
   - All versions: [Editkin releases](https://github.com/Hao0321/Editkin/releases) (a preview is not marked
     "Latest", so look for it in the list)
   - The installer is about 1.25 GB; the installed program takes about 2 GB.
2. Double-click the installer. Because it is unsigned, Windows SmartScreen shows "Windows protected your PC":
   1. Click **More info**.
   2. Click **Run anyway**.
3. Follow the installer. You can choose the install folder.
4. If Microsoft Edge WebView2 is missing (most Windows 10/11 PCs have it), the installer downloads it, which
   needs an internet connection.

### 0-2 Check the installer has not been altered (recommended)

The release page lists the installer's SHA-256. Open a terminal in your download folder and run (replace
`<installer>` with the real file name):

```bat
certutil -hashfile <installer>.exe SHA256
```

The value must match the SHA-256 on the release page exactly. **If it does not, do not run the file.**
(In PowerShell you can also use `Get-FileHash <installer>.exe -Algorithm SHA256`.)

### 0-3 Connect your AI

You need [Claude Code](https://claude.com/claude-code) or the Codex CLI installed and signed in. No API key: it
uses your own AI subscription.

1. Open Editkin. On the start screen, in **Edit with AI assistance**, click **Connect AI assistant** (連接 AI 助手).
2. Choose **Connect Claude Code** or **Connect Codex** (one-click setup).
3. Pick the **work folder** the AI may use and put the videos you want edited in it. The AI can only read and
   write inside this folder.
4. When it says the latest MCP is set up, **restart** Claude Code / Codex (or start a new session).
5. Type `/mcp`; the list should include `editkin`.

If one-click setup fails, follow the steps shown: open a terminal, paste the setup command Editkin copied, then
restart the AI.

### 0-4 Install this Kit

Editkin's **Copy start instructions** button starts the full Video Autopilot workflow (look at the footage, read
the transcript, plan, audit, apply, render). That workflow must find this Kit's Skill in one of two places:

- `%USERPROFILE%\.codex\skills\video-autopilot\` (the default)
- or the `EDITKIN_VIDEO_AUTOPILOT_SKILL` environment variable, set to the path of the Skill's `SKILL.md`

The Kit's installer puts it in the default place. Run `--check` first, then `--apply --install-skill`:

```powershell
Invoke-WebRequest https://github.com/Hao0321/video-autopilot-kit/releases/latest/download/install_or_upgrade.py -OutFile install_or_upgrade.py
python install_or_upgrade.py --install-root <folder-for-the-kit> --check
python install_or_upgrade.py --install-root <folder-for-the-kit> --apply --install-skill
```

- `--install-skill` syncs the Skill to `%USERPROFILE%\.codex\skills\video-autopilot\`.
- If a Skill that this installer **does not manage** is already there, the result shows `ADOPT_REQUIRED` and
  stops without overwriting it. Once you are sure it can be taken over, run again with `--adopt-skill`.
- If Editkin cannot find the Kit, it shows a clear message naming the missing Kit with a link to this repository.
- Without the Kit, direct requests still work, such as "use Editkin to cut the pauses from a video in my work
  folder and add captions and background music".

### 0-5 Check it all works

Try either one:

- **Simple mode (no AI account needed)**: open Editkin, and on the start screen (**Add a video — I'll edit it for
  you**, 放影片進來，我幫你剪好) choose **Horizontal video** (橫的影片) → **Choose video** (選擇影片) → pick a
  landscape video you shot yourself where someone is talking (1–10 minutes works well) → pick a type →
  **Start auto-edit** (開始自動剪輯). When you see **All done — take a look** (剪好了，你看看), Editkin itself
  works. The first time it adds captions, it downloads a speech-recognition model of about 190 MB (needs an
  internet connection, once).
- **AI connection**: ask your AI to "list Editkin's modules". It calls `list_editkin_modules`; if you get a module
  list back, the AI and Editkin are connected. If the list includes `graphic.text_motion`,
  `transition.motion_pair` and `background.motion_loop`, the Motion Library (160 effects) is available too.

**Vertical Shorts**: this Kit version accepts Editkin's default `kinetic` cadence, so vertical Shorts run end to
end with this Editkin preview.

---

## v0.25.0 quick start

```bash
python src/system_health.py --quick
python src/release_manager.py install-skill
python src/workflow_contract.py selftest
```

From v0.25.0, **VA (this kit) only plans, judges and checks; all rendering goes to
[Editkin](https://github.com/Hao0321/Editkin)** (installed separately — see Step 0 above; GPL-3.0). The old Python/FFmpeg
renderers and the optional visual asset pack are no longer needed. Personal data under
`profiles/`, `data/`, `assets/`, and `videos/` remains protected during updates.

The public kit does not pre-authorize any review identity. Explicitly configure the
actors allowed to resolve subjective review items; an empty value fails closed and
automation cannot sign on a creator's behalf:

```powershell
$env:VIDEO_AUTOPILOT_REVIEW_ACTORS='creator'
```

```bash
export VIDEO_AUTOPILOT_REVIEW_ACTORS='creator'
```

Separate multiple actors with commas. The `--actor` value is matched after trimming
surrounding whitespace and without regard to letter case.

> **This repo isn't a hand-me-down config — it's a framework + questionnaire.**
> It distills a battle-tested YouTube / short-form automation system into templates.
> You answer the questions below and it generates **your own** voice / brand / strategy
> / community files. The code is generic; **all personalization comes from your answers —
> none of the original author's private data is included.**

*(中文版見 [SETUP.md](SETUP.md))*

## 🧭 Platform requirements (read this first)

The kit has one current editing-execution path: the **Editkin v4 structured workflow**. VA owns
material evidence, `edit-plan/v4`, the gates and delivery QA; Editkin performs audit, atomic apply
and render under the same contract. There is no second editor runtime. One-page architecture →
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

- **VA (Win / Mac / Linux)**: Python 3.9+ and `ffmpeg`/`ffprobe` (used by delivery QA and teardown).
  From the repository root, run `python -m pip install -r requirements-media.txt`. CI and Release use
  the same pinned file.

  **Installing ffmpeg (one-time, all platforms):**
  | Platform | Command |
  |---|---|
  | macOS | `brew install ffmpeg` (needs [Homebrew](https://brew.sh); verify with `ffmpeg -version`) |
  | Windows | `winget install ffmpeg`, or grab a full build from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) and add it to PATH |
  | Linux | `sudo apt install ffmpeg fonts-noto-cjk` (Debian/Ubuntu; also supplies the system font required by CJK rendering/self-tests) |

  > System paths and CJK fonts on Mac/Linux are auto-detected by `src/platform_compat.py`; minimal Linux images must still install a CJK system font first.
- **Editkin (required)**: install the public preview (Windows only for now) and connect Claude Code or Codex in
  one click, as in Step 0 above. Developers can also build it from source following the Editkin README
  ([repo](https://github.com/Hao0321/Editkin); rendering needs the desktop build), start it with `npm run mcp` in
  the AI agent's (any MCP-capable agent) MCP configuration, and set `EDITKIN_VIDEO_AUTOPILOT_SKILL` to the
  absolute path of the Skill's `SKILL.md`.
  The agent calls Editkin's MCP tools and returns the receipts required by `workflow_contract.json`.
  Unknown connection or apply state fails closed into reconcile.
- **Motion Library (optional)**: rhythm scenes and brand motion need an Editkin build that includes the
  Motion Library; the [Editkin public preview](https://github.com/Hao0321/Editkin/releases/tag/v0.15.0-preview.20261022)
  includes it. When a module is missing, VA records `NEW_MOTION_RUNTIME_REQUIRED` instead of silently
  falling back to an older effect.
- **Old FFmpeg renderers**: retired in v0.25.0. If you really need them, stay on tag `v0.24.1`.

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
3. Where are your Editkin project, source-media and export paths? Is this long-form, Shorts or Reels?

→ That's enough to start editing. Voice / Algorithm / Community (4️⃣5️⃣6️⃣) can wait until you want to optimize.

**Manual route (3 steps):**
1. Copy `templates/` into `profiles/` using this mapping (not just dropping `.template`):
   `brand_profile`→`brand.md`, `voice_profile`→`voice.md`, `algorithm_context`→`algorithm.md`,
   `community_mobilization`→`community.md`, `content_pipeline`→`content_pipeline.md`, `your_context`→`your_context.md`
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
- Where do the Editkin project, source media, candidate export and QA evidence live?
- Is Editkin installed (if not, see Step 0 above), and can your AI agent call Editkin's MCP tools and return the structured
  receipts required by `workflow_contract.json`?
- Bind every real source as `CLIP_ID=SOURCE_FILE`; keep runs under
  `videos/_AUTOPILOT/editkin-v4/` inside the project, never at a drive root.
- Are `ffmpeg` and `ffprobe` on PATH? They support delivery QA and competitor measurement; they are
  not a second editor path.
- Where are your **fonts** / **BGM** / **b-roll** stored?
- (Filled into `config.py` — the example contains **no account names**)

## 5️⃣ Algorithm context → fills `profiles/algorithm.md`　⭕optional (add when you start chasing numbers)
- Your current numbers? (subs / avg views / CTR / average view duration)
- Main traffic source? (Browse / Suggested / Search / External …)
- Biggest pain point? (reach / retention / CTR …)
- (The framework gives you **which metrics to watch and how to fix them**; you fill in **your** numbers)

## 6️⃣ Community / external traffic → fills `profiles/community.md`　⭕optional (add when you mobilize a community)
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

## 8️⃣ Shorts rule calibration → select the `shorts_gate` platform and inspect thresholds　⭕optional (**only if you cut vertical Shorts**)

The current API in `src/longform_maker/shorts_gate.py` is `gate_shorts(spec)` and
`assert_shorts(spec)`, each with one argument. Duration rules come from `PLATFORM_RULES`;
module constants build the other thresholds into `_GATE_POLICY`. These are an **example
calibration, not a universal law**. Check their suitability against your own videos:

| Measure | Threshold key | Ask yourself |
|---|---|---|
| **Duration band** | `dur_min` / `dur_max` | How long are your 3-5 best Shorts? Take the range. The default keeps "gag / single surprise" at 13-25s |
| **Dead zone** | `PLATFORM_RULES[platform]["deadzone"]` | Is there a length in **neither camp**? YT defaults to 26-44s; IG/FB use `None` |
| **First cut** | `FIRST_CUT_MAX` | How many seconds before the picture must change for the first time? Measure it on your best few |
| **Non-white caption cap** | `NONWHITE_MAX_RATIO` / `NONWHITE_MAX_COLORS` | Are captions **white-first**? Measure the non-white share and number of colors |

**How to calibrate (two steps — the second is not optional):**
1. Measure your **best** 3-5 and set the thresholds from that range
2. Run your **worst** 3 through the gate and **confirm they get blocked**. A threshold that only
   passed step 1 is decoration

**Select the actual publishing platform first**: the YT dead zone does not apply to IG/FB.

```python
from shorts_gate import PLATFORM_RULES, gate_shorts, assert_shorts

spec["platform"] = "ig_reels"             # yt_shorts (default) / ig_reels / fb_reels
duration_rules = PLATFORM_RULES[spec["platform"]]
ok, rep = gate_shorts(spec)              # non-empty rep["fails"] means BLOCK
ready = assert_shorts(spec)              # call before it goes into the plan; raises AssertionError on BLOCK
```

Omitting `platform` selects `yt_shorts`; an unknown platform blocks. The current API has no
`DEFAULT_RULES`, second rules argument, or `rules=` override. Custom calibration requires a
version-controlled source change to `PLATFORM_RULES` / module constants, then reloading the
module to rebuild `_GATE_POLICY` and checking positive and negative controls. Changing a
constant after import does not update the existing policy. Do not select another platform
to bypass rules for a cut intended for YT.

**Downstream QA input contract**: `spec` is a dict. `place`, `what`, and normally `addr` are
non-empty strings; explicit `persistent_label_policy="omit"` permits missing `addr`.
`segs` is a non-empty list/tuple of `(source, in_sec, duration)`: source is a string/PathLike,
times are finite numbers, start ≥ 0, duration > 0, and bool is not a number.
`caps_by_seg` is a list/tuple of `(seg_idx, [(text, color), ...], kind)`: indexes are existing
non-negative integers and text/color/kind are strings. Optional evidence/battle/tracking
data must also have valid structure; evidence text cannot be null/bool.
Missing `segs` or `caps_by_seg`, wrong types, invalid indexes, and caption overpacking return
`(False, {"ok": False, "fails": [...], "warns": [...]})` without usable expanded captions.
`assert_shorts` still rejects with `AssertionError`; use `gate_shorts` for a report.
S-O warnings remain advisory.

Want to see the gate first? `python examples/04_shorts_gate.py` (pure Python — no ffmpeg, no
media). The knowledge behind the rules →
[`knowledge/shorts-mastery-2026.md`](knowledge/shorts-mastery-2026.md); how to measure a
competitor's cut rhythm yourself →
[`knowledge/vertical-teardown-method.md`](knowledge/vertical-teardown-method.md)
(`python src/teardown.py <file>`).

---

## 📦 What you get

| Fill in | You get |
|---|---|
| 1️⃣ Brand | Your outro signature + on-camera / no-face planning rules |
| 2️⃣ Niche | Automatic pipeline routing |
| 3️⃣ Voice | **Your** voice profile (scripts and copy in your tone) |
| 4️⃣ Production | `config.py` (your paths / fonts / BGM) |
| 5️⃣ Algorithm | An algorithm checklist (with your numbers) |
| 6️⃣ Community | An external-traffic mobilization SOP (for your communities) |
| 7️⃣ Show | `profiles/show.md` — the interview line's 7-doc kit carries your show identity |
| 8️⃣ Shorts calibration | Gate thresholds of **your own** (they block your bad cuts and pass your good ones) |

→ Then create a run with `python src/workflow_contract.py create ...`; editable timelines always go
through Editkin v4: contract → session → material evidence → plan v4 → audit → atomic apply → render →
delivery QA → human review.

---

## Why a questionnaire instead of a ready-made config?

The most valuable part of a creator system is its **structure and methodology**, not one
person's private numbers. Copying someone else's voice / strategy / community data won't
help you — it may mislead you. So this repo gives you the **skeleton**; you fill it with
your own flesh. That's what makes it truly **yours**.
