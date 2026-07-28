#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example 04 — the vertical-Shorts mechanical gate, with ZERO media and ZERO deps.

`longform_maker/shorts_gate.py` turns "the rules for cutting a Short" into asserts
that fire at build time, so nobody has to remember them. This demo runs the gate
three times:

    1) a BROKEN spec  → 3 blocking failures (duration dead zone / slow first cut /
                        missing opening ID)
    2) the FIXED spec → passes, and the gate hands back caption times it computed
                        from segment indexes (you never hand-type timecodes)
    3) YOUR OWN band  → the same 31s spec that the default rules reject, accepted
                        after overriding the thresholds — because the shipped
                        numbers are an EXAMPLE calibration, not a universal law
    4) ANOTHER PLATFORM → the same 31s spec again, this time accepted with no
                        overrides at all, just `platform="ig_reels"`: the 26-44s
                        dead zone is a YouTube-Shorts calibration and blocking it
                        everywhere would be a FALSE block

Note the S-O line in the reports: it is a **warning, not a failure**. Warnings
tell you something and let the build through; only `[FAIL]` stops it.

Run:
    python examples/04_shorts_gate.py

Needs: Python 3.9+ only. **No ffmpeg, no Pillow, no numpy, no real footage** —
this file uses itself as the stand-in "clip" so the gate's file-exists check has
something real to look at. (The one-command driver `src/shorts_autopilot.py` does
need ffmpeg + Pillow + numpy; the gate itself never does.)
"""
import os
import sys

# Make `src/` (and the gate's own folder) importable when run straight from the repo.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, os.path.join(HERE, "..", "src", "longform_maker"))

from shorts_gate import DEFAULT_RULES, gate_shorts  # noqa: E402

# The gate checks that every segment file really exists. No footage needed for a
# demo — point every segment at this script itself.
CLIP = os.path.abspath(__file__)

# The gate reports in Chinese; the S-x code in front of each message is the
# language-neutral key. Glossed here so this demo reads in either language.
GLOSS = {
    "S-A": "opening ID: first segment needs place/topic + one line of what-is-this",
    "S-B": "duration outside the band (or inside the dead zone)",
    "S-C": "first cut too slow - something must change early",
    "S-D": "loop broken: last segment must land back on the first frame",
    "S-E": "standing info bar missing",
    "S-F": "caption bound to a segment that does not exist",
    "S-G": "caption sitting on the loop segment - keep the seam clean",
    "S-I": "white-first broken: too much colour / too many accent colours",
    "S-O": "caption rhythm: lines sit too long / too few lines per minute (ADVISORY)",
}


def show(title, spec, rules=None):
    """Run the gate once and print a human-readable report."""
    ok, rep = gate_shorts(spec, rules)
    print("\n" + "=" * 64)
    print("%s  ->  %s" % (title, "PASS" if ok else "FAIL"))
    print("=" * 64)
    print("  platform : %s" % rep.get("platform", "?"))
    print("  duration : %.1fs" % rep.get("dur", 0.0))
    if rep.get("cap_rate") is not None:
        print("  captions : %.1f lines/min, median dwell %.2fs"
              % (rep["cap_rate"], rep["cap_dwell"]))
    for level in ("fails", "warns"):
        for msg in rep[level]:
            code = msg.split()[0].split("/")[0]
            print("  [%s] %s" % ("FAIL" if level == "fails" else "WARN", msg))
            if code in GLOSS:
                print("         ^ %s: %s" % (code, GLOSS[code]))
    if ok:
        print("  captions the gate computed from segment indexes:")
        for st, en, blocks, kind in rep["caps"]:
            print("    %5.2f - %5.2fs  %-6s %s"
                  % (st, en, kind, "".join(t for t, _c in blocks)))
    return ok, rep


def broken():
    """Three rule breaks at once — each one alone is enough to block the build."""
    return dict(
        name="short_demo_broken",
        place="Riverside Market",
        what="a 40-year-old noodle stall",
        addr="Riverside Market | 12 Example Road",
        segs=[
            (CLIP, 4.0, 3.2),    # S-C: first cut 3.2s — way past the 2s rule
            (CLIP, 8.0, 9.0),
            (CLIP, 20.0, 9.0),
            (CLIP, 30.0, 9.0),
            (CLIP, 1.0, 3.0),    # loop segment: ends at 4.0s == first segment's in-point
        ],                       # S-B: 33.2s total lands in the dead zone
        caps_by_seg=[
            # S-A: only ONE caption on segment 0 — the "what is this" line is missing
            (0, [("Riverside Market", "gold")], "hook"),
            (1, [("hand-pulled every morning", "white")], "sub"),
            (2, [("the broth simmers 8 hours", "white")], "sub"),
            (3, [("USD 3 a bowl", "white")], "sub"),
        ],
        bgm_folder="<your-bgm-subfolder>",
    )


def fixed():
    """Same footage plan, all three breaks repaired."""
    return dict(
        name="short_demo_fixed",
        place="Riverside Market",
        what="a 40-year-old noodle stall",
        addr="Riverside Market | 12 Example Road",
        segs=[
            (CLIP, 4.0, 2.0),    # first cut now 2.0s
            (CLIP, 8.0, 3.2),
            (CLIP, 12.0, 3.2),
            (CLIP, 16.0, 3.4),
            (CLIP, 2.4, 1.6),    # loop: 2.4 + 1.6 = 4.0 == first segment's in-point
        ],                       # 13.4s total — inside the band
        caps_by_seg=[
            (0, [("Riverside Market", "gold")], "hook"),      # who/where
            (0, [("a 40-year-old noodle stall", "white")], "sub"),   # what is this
            (1, [("hand-pulled every morning", "white")], "sub"),
            (2, [("the broth simmers 8 hours", "white")], "sub"),
            (3, [("USD 3 a bowl", "white")], "sub"),
        ],
        bgm_folder="<your-bgm-subfolder>",
    )


def long_format():
    """A 31s cut: legal for some formats, rejected by the shipped example band."""
    spec = fixed()
    spec["name"] = "short_demo_long"
    spec["segs"] = [
        (CLIP, 4.0, 2.0),
        (CLIP, 8.0, 9.0),
        (CLIP, 20.0, 9.0),
        (CLIP, 30.0, 9.6),
        (CLIP, 2.4, 1.6),
    ]
    return spec


def main():
    print(__doc__.strip().splitlines()[0])
    print("shipped example calibration: %.0f-%.0fs band, first cut <=%.1fs, "
          "non-white captions <=%.0f%%"
          % (DEFAULT_RULES["dur_min"], DEFAULT_RULES["dur_max"],
             DEFAULT_RULES["first_cut_max"], DEFAULT_RULES["nonwhite_max_ratio"] * 100))

    ok_bad, rep_bad = show("1) BROKEN spec (default rules)", broken())
    ok_fix, _ = show("2) FIXED spec (default rules)", fixed())

    # Same 31s spec, three times: rejected by the example band, accepted by your
    # own thresholds, and accepted again by simply declaring another platform.
    show("3a) 31s spec (default rules)", long_format())
    my_rules = {"dur_min": 26.0, "dur_max": 60.0, "dur_deadzone": None}
    ok_long, _ = show("3b) 31s spec (YOUR calibration: %s)" % my_rules, long_format(), my_rules)

    reels = long_format()
    reels["platform"] = "ig_reels"       # no `rules=` at all — just say where it ships
    ok_reels, _ = show("4) same 31s spec, platform='ig_reels' (no overrides)", reels)

    print("\n" + "-" * 64)
    print("Recap")
    print("-" * 64)
    print("  broken spec blocked by %d rules: %s"
          % (len(rep_bad["fails"]),
             ", ".join(f.split()[0] for f in rep_bad["fails"])))
    print("  fixed spec passes and returns caption timings it derived itself")
    print("  the SAME 31s cut passes once you supply your own band")
    print("  ...and passes with no overrides at all once you name the platform:")
    print("  the 26-44s dead zone is a YouTube-Shorts number, not a law of nature")
    print("  S-O is a WARN, never a block - a rule that fires on every normal cut")
    print("  gets ignored, so caption rhythm reports itself instead of judging you")
    print()
    print("Make it yours: the numbers in DEFAULT_RULES came from one genre's")
    print("measurements. Re-calibrate on YOUR 3-5 best performing Shorts, pass the")
    print("result as `rules=` (see src/longform_maker/shorts_gate.py), and confirm")
    print("your 3 worst ones still get blocked.")

    # Exit non-zero if the demo itself stopped behaving as documented.
    return 0 if (not ok_bad and ok_fix and ok_long and ok_reels) else 1


if __name__ == "__main__":
    raise SystemExit(main())
