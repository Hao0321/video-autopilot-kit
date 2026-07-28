#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example 02 — zero-config caption ↔ b-roll auto-sequencing (pure Python, no ffmpeg).

The kit's b-roll matcher needs NO keyword config to work: as long as you name
your b-roll files after their content (coffee.mp4 / sunset.mov / ramen.mp4), it
aligns each caption to the best-matching clip by shared words — so the footage
follows what the narration/caption is actually talking about.

Run:
    python examples/02_caption_broll_match.py

Needs: Python 3.9+ only. No ffmpeg, no CapCut, no real media.
"""
import os
import sys

try:                      # cp950 console 保險：非 ASCII 不該讓 demo 崩潰
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# `caption_broll_matcher.py` is self-contained (no package imports), so we load it
# directly off the path — works on any OS without installing CapCut.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src", "capcut_helpers"))

import caption_broll_matcher as cbm  # noqa: E402

S = 1_000_000  # microseconds per second helper


def main():
    # What the narration / on-screen captions say, in order.
    captions = [
        {"text": "Best coffee in town",          "start_us": 0 * S, "duration_us": 4 * S},
        {"text": "Golden hour sunset by the sea", "start_us": 4 * S, "duration_us": 4 * S},
        {"text": "A steaming bowl of ramen",      "start_us": 8 * S, "duration_us": 4 * S},
    ]

    # Your b-roll pool — just NAMED AFTER THE CONTENT. No keyword map needed.
    brolls = [
        {"id": "coffee.mp4", "source_duration_us": 6 * S},
        {"id": "sunset.mov", "source_duration_us": 6 * S},
        {"id": "ramen.mp4",  "source_duration_us": 6 * S},
        {"id": "street.mp4", "source_duration_us": 6 * S},  # generic filler
    ]

    total_us = 12 * S
    print("Zero-config matching (keyword_map=None -> filename vs caption tokens):\n")

    assignments = cbm.auto_sequence_brolls(
        captions, brolls, total_duration_us=total_us, keyword_map=None
    )
    cbm.print_sequence_plan(assignments, total_duration_us=total_us)

    print("\nNotice: 'coffee' caption → coffee.mp4, 'sunset' → sunset.mov, "
          "'ramen' → ramen.mp4 —")
    print("all without any configuration. Name your clips by content and the")
    print("footage follows the narration. (For non-matching captions it falls")
    print("back to filler so the timeline still has no gaps.)")


if __name__ == "__main__":
    main()
