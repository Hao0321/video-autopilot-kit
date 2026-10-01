#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Example 04 — the vertical-Shorts mechanical gate, with ZERO media and ZERO deps.

A broken cut is blocked, a fixed cut passes with computed caption timings,
and a 31s cut is blocked on YouTube Shorts but passes on Instagram Reels.
The current API is gate_shorts(spec): select duration rules with platform.
Threshold calibration is a source-policy change, not a per-call rules dict.

Run: python examples/04_shorts_gate.py
Needs: Python 3.9+ only. No ffmpeg, Pillow, numpy, or real footage.
This script itself stands in for an existing clip; no video is decoded.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, os.path.join(HERE, "..", "src", "longform_maker"))

from shorts_gate import (  # noqa: E402
    DEFAULT_PLATFORM, FIRST_CUT_MAX, NONWHITE_MAX_RATIO, PLATFORM_RULES, gate_shorts,
)

CLIP = os.path.abspath(__file__)
GLOSS = {
    "S-A": "opening ID: first caption must identify the place/topic",
    "S-B": "duration outside the platform band (or inside its dead zone)",
    "S-C": "first cut too slow - something must change early",
    "S-D": "loop broken: last segment must land back on the first frame",
    "S-E": "standing info bar missing",
    "S-F": "invalid caption segment or insufficient time for its captions",
    "S-G": "caption sitting on the loop segment - keep the seam clean",
    "S-I": "white-first broken: too much colour / too many accent colours",
    "S-O": "caption rhythm: long dwell / few lines per minute (ADVISORY)",
}


def show(title, spec):
    """Run the single-argument API and print its report."""
    ok, rep = gate_shorts(spec)
    print("\n" + "=" * 64)
    print("%s -> %s" % (title, "PASS" if ok else "BLOCK"))
    print("  platform : %s" % spec.get("platform", DEFAULT_PLATFORM))
    print("  duration : %.1fs" % rep.get("dur", 0.0))
    for level in ("fails", "warns"):
        for message in rep[level]:
            code = message.split()[0].split("/")[0]
            print("  [%s] %s" % ("FAIL" if level == "fails" else "WARN", message))
            if code in GLOSS:
                print("         ^ %s" % GLOSS[code])
    if ok:
        print("  captions computed from segment indexes:")
        for start, end, blocks, kind in rep["caps"]:
            print("    %5.2f - %5.2fs %-6s %s"
                  % (start, end, kind, "".join(text for text, _color in blocks)))
    return ok, rep


def fixed():
    """Synthetic plan with short, readable captions and a clean loop."""
    return dict(
        name="short_demo_fixed", place="Pine", what="soup",
        addr="Pine | 12 Example Road",
        segs=[
            (CLIP, 4.0, 2.0), (CLIP, 8.0, 3.2), (CLIP, 12.0, 3.2),
            (CLIP, 16.0, 3.4), (CLIP, 2.4, 1.6),
        ],  # 13.4s; the final segment ends at the first segment's in-point.
        caps_by_seg=[
            (0, [("Pine", "gold")], "hook"),
            (0, [("soup", "white")], "sub"),
            (1, [("Handmade", "white")], "sub"),
            (2, [("Slow broth", "white")], "sub"),
            (3, [("USD 3", "white")], "sub"),
        ],
        bgm_folder="<your-bgm-subfolder>",
    )


def broken():
    """Three independent breaks: opening ID, first cut, and duration."""
    spec = fixed()
    spec.update(name="short_demo_broken", segs=[
        (CLIP, 4.0, 3.2), (CLIP, 8.0, 9.0), (CLIP, 20.0, 9.0),
        (CLIP, 30.0, 9.0), (CLIP, 1.0, 3.0),
    ])
    spec["caps_by_seg"] = [(0, [("Lunch", "gold")], "hook")] + spec["caps_by_seg"][2:]
    return spec


def long_format():
    """A 31.2s cut, inside the Reels band and the Shorts dead zone."""
    spec = fixed()
    spec.update(name="short_demo_long", segs=[
        (CLIP, 4.0, 2.0), (CLIP, 8.0, 9.0), (CLIP, 20.0, 9.0),
        (CLIP, 30.0, 9.6), (CLIP, 2.4, 1.6),
    ])
    return spec


def main():
    print(__doc__.strip().splitlines()[0])
    rules = PLATFORM_RULES[DEFAULT_PLATFORM]
    print("%s calibration: %.0f-%.0fs, first cut <=%.2fs, non-white <=%.0f%%"
          % (DEFAULT_PLATFORM, rules["dur_min"], rules["dur_max"],
             FIRST_CUT_MAX, NONWHITE_MAX_RATIO * 100))
    ok_bad, rep_bad = show("1) BROKEN spec", broken())
    ok_fix, _ = show("2) FIXED spec", fixed())
    ok_long, rep_long = show("3) 31s spec on yt_shorts", long_format())
    reels = long_format()
    reels["platform"] = "ig_reels"
    ok_reels, _ = show("4) same 31s spec on ig_reels", reels)
    print("\nPlatform selects PLATFORM_RULES; omitted platform means yt_shorts.")
    print("S-O warnings advise; only fails block the cut.")
    print("Calibrate policy in source and rebuild _GATE_POLICY; no per-call override.")
    bad_codes = {message.split()[0] for message in rep_bad["fails"]}
    expected = (not ok_bad and {"S-A", "S-B", "S-C"} <= bad_codes
                and ok_fix and not ok_long
                and any(message.startswith("S-B") for message in rep_long["fails"])
                and ok_reels)
    return 0 if expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
