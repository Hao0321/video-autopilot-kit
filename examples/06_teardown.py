#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example 06 — competitor teardown math, with ZERO media, ZERO ffmpeg, ZERO pip install.

`src/teardown.py` normally runs ffmpeg over a rival's vertical short and prints
its rhythm. But the *interesting* half of that tool is pure arithmetic, and you
can read it without installing an OCR model or finding a video to point at.

So this demo skips the measuring and feeds the statistics functions three sets
of hand-written timestamps — three clips that a viewer would describe very
differently, and that the numbers separate cleanly:

  CLIP 1  metronome cut   — many cuts, all the same length
  CLIP 2  narrative arc   — same median gap, wildly different spacing
  CLIP 3  one long take   — almost no cuts, captions carrying everything

The payoff is the last column: **captions-per-minute ÷ cuts-per-minute**. When
that ratio is above 1, the thing pushing the video forward is the *text*, not
the edit — which is the practical finding, because text is free and re-shooting
is not.

Run:
    python examples/06_teardown.py

Needs: Python 3.9+. No footage, no ffmpeg, no CapCut, no OCR packages.
(That last one is the point of STEP 4 — the OCR half of the tool is optional
and the tool degrades instead of crashing when it is missing.)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "src"))
sys.path.insert(0, SRC)

try:
    from teardown import (CAPTION_DRIVEN_RATIO, OPTIONAL_PKGS, ocr_status,
                          pace_profile, rhythm_stats)
except ImportError as e:
    print("=" * 70)
    print("Cannot run this example: `teardown` is not importable.")
    print("  reason  : %s" % e)
    print("  expected: %s" % os.path.join(SRC, "teardown.py"))
    print("  present : %s" % ("yes" if os.path.exists(
        os.path.join(SRC, "teardown.py")) else "NO (file is missing)"))
    print()
    print("`src/teardown.py` imports only the standard library, so this failure")
    print("is a missing/renamed file, not a missing package. Pull the latest tag,")
    print("or copy that one file across if you took only part of `src/`.")
    print("=" * 70)
    raise SystemExit(1)


# ── three fabricated clips (every timestamp below is made up for the demo) ───
# Each tuple is: (label, duration_seconds, cut_times, caption_change_times)
CLIPS = [
    (
        "CLIP 1  metronome cut  (product/menu montage)",
        24.0,
        # a cut every 1.1s, machine-regular -- this is what cutting to a BGM
        # beat looks like in the numbers: the stdev collapses to zero.
        [round(1.1 * i, 2) for i in range(1, 22)],
        # captions turn over at roughly the same pace as the cuts
        [round(1.05 * i, 2) for i in range(1, 23)],
    ),
    (
        "CLIP 2  narrative arc  (voice-over walk-through)",
        24.0,
        # SAME median cut gap as clip 1 (1.10s), but shaped:
        # slow open (3.2 / 2.8) -> burst (0.4 / 0.5 / 0.6) -> steady 1.1s x5
        # -> one long hold (4.0) to land the ending.
        # Median alone cannot tell these two clips apart. Stdev can.
        [2.3, 5.5, 8.3, 8.7, 9.2, 9.8, 10.9, 12.0, 13.1, 14.2, 15.3, 19.3],
        [round(1.45 * i, 2) for i in range(1, 17)],
    ),
    (
        "CLIP 3  one long take  (static close-ups, text-driven)",
        24.0,
        # 3 cuts in 24 seconds. A viewer still calls this clip "fast".
        [4.0, 9.5, 21.0],
        # ...because the captions change 24 times.
        [round(1.0 * i, 2) for i in range(1, 25)],
    ),
]


def show(label, dur, cut_times, cap_times):
    p = pace_profile(cut_times, cap_times, dur)
    c, k = p["cuts"], p["captions"]
    print("-" * 70)
    print(label)
    print("  cuts      %3d in %.0fs = %5.1f/min | median gap %.2fs | stdev %.2f"
          % (c["n"], dur, c["per_min"], c["gap_median"], c["gap_stdev"]))
    print("  captions  %3d in %.0fs = %5.1f/min | median gap %.2fs | stdev %.2f"
          % (k["n"], dur, k["per_min"], k["gap_median"], k["gap_stdev"]))
    print("  -> %s" % p["verdict"])
    return p


def main():
    print("=" * 70)
    print("teardown demo -- three clips, no media, no dependencies")
    print("=" * 70)

    p1 = show(*CLIPS[0])
    p2 = show(*CLIPS[1])
    p3 = show(*CLIPS[2])

    # STEP 1 -- median gap is not enough to tell an edit style apart.
    print("-" * 70)
    print("STEP 1  Clip 1 and Clip 2 have the SAME median cut gap (%.2fs vs %.2fs)"
          % (p1["cuts"]["gap_median"], p2["cuts"]["gap_median"]))
    print("        ...but stdev %.2f vs %.2f. One is locked to a beat, the other"
          % (p1["cuts"]["gap_stdev"], p2["cuts"]["gap_stdev"]))
    print("        breathes with the sentence. Report the spread, not just the median.")
    assert p1["cuts"]["gap_median"] == p2["cuts"]["gap_median"], "demo setup: medians match"
    assert p1["cuts"]["gap_stdev"] < p2["cuts"]["gap_stdev"], "demo setup: spread differs"

    # STEP 2 -- the ratio that actually changes how you shoot.
    print("-" * 70)
    print("STEP 2  captions/cuts ratio: %.2fx / %.2fx / %.2fx  (threshold %.2fx)"
          % (p1["ratio"], p2["ratio"], p3["ratio"], CAPTION_DRIVEN_RATIO))
    print("        Clip 3 has 3 cuts and still reads fast, because 24 caption")
    print("        changes are doing the work. Practical use: when you have one")
    print("        long take and nothing to cut to, do NOT force cuts -- push the")
    print("        pace with captions (~0.7-1.2s per line) instead of re-shooting.")
    assert p3["driver"] == "captions", "a 3-cut / 24-caption clip is caption-driven"
    assert p1["driver"] == "cuts", "a 21-cut / 26-caption clip is barely cut-driven"

    # STEP 3 -- degenerate input must not explode.
    print("-" * 70)
    print("STEP 3  edge cases return a verdict instead of raising:")
    single = rhythm_stats([3.0], 24.0)
    assert single["gap_median"] is None and single["per_min"] > 0
    print("        one lone timestamp  -> per_min %.1f, gap_median None (no gap exists)"
          % single["per_min"])
    empty = pace_profile([], [1.0, 2.0], 24.0)
    assert empty["ratio"] is None and empty["driver"] == "unknown"
    print("        zero cuts detected  -> %s" % empty["verdict"])
    zero_dur = rhythm_stats([1.0, 2.0], 0)
    assert zero_dur["per_min"] == 0.0
    print("        duration 0 (bad probe) -> per_min 0.0, no ZeroDivisionError")

    # STEP 4 -- the optional half, and what you lose without it.
    print("-" * 70)
    ocr_ok, s2t_ok, hint = ocr_status()
    print("STEP 4  optional OCR packages: %s / %s"
          % ("installed" if ocr_ok else "MISSING", "installed" if s2t_ok else "MISSING"))
    if hint:
        print("        install with: %s" % hint)
        print("        Without them, `python src/teardown.py <clip>` still prints every")
        print("        number you saw above -- it only skips pulling the rival's burnt-in")
        print("        caption script back out as text. Nothing crashes, exit code is 0.")
    else:
        print("        Both present, so teardown.py will also extract caption text.")
    print("        Either way: OCR reads burnt-in captions well (0.92-1.00) and reads")
    print("        real-world signage essentially not at all -- while still reporting")
    print("        0.85-0.92 confidence when it is wrong. So never let it write product")
    print("        names, prices or specs into YOUR video. Read the frame yourself.")
    assert isinstance(ocr_ok, bool) and isinstance(s2t_ok, bool)
    assert (hint == "") == (ocr_ok and s2t_ok)
    assert all(p in ("rapidocr-onnxruntime", "opencc-python-reimplemented")
               for p in OPTIONAL_PKGS)

    print("-" * 70)
    print("Takeaway: measure the rival's spread, not just their speed; and when the")
    print("ratio says 'caption-driven', that is a shooting decision, not a trivia fact.")
    print("Next: point the real tool at a clip -> python src/teardown.py my_clip.mp4")
    print("      Method, thresholds and calibration -> knowledge/vertical-teardown-method.md")
    print("OK -- teardown demo passed")


if __name__ == "__main__":
    main()
