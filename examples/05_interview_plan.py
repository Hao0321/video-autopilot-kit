#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example 05 — the interview guest gate, with ZERO media and ZERO pip install.

Booking a guest is where an interview show quietly goes wrong: you agree on a
date, you write the host script, and only in the edit do you notice that the
headline number the guest gave you has no source behind it. Then it is either
cut it or ship an unverifiable claim on your channel.

`interview_gate.gate_guest()` moves that discovery to *before* you record.
This script runs it twice on the same fictional guest:

  STEP 1 — an achievement whose `source` field is empty  -> BLOCKED
  STEP 2 — the exact same guest, source filled in        -> PASSES (with warnings)

Nothing here touches the network, the disk, or ffmpeg — it is plain data in,
plain verdict out, so you can read the whole gate in one sitting.

Run:
    python examples/05_interview_plan.py

Needs: Python 3.9+. No dependencies, no footage, no CapCut.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "src"))
sys.path.insert(0, SRC)

try:
    from interview_gate import gate_guest, assert_guest
except ImportError as e:
    print("=" * 68)
    print("Cannot run this example: `interview_gate` is not importable.")
    print("  reason  : %s" % e)
    print("  expected: %s" % os.path.join(SRC, "interview_gate.py"))
    print("  present : %s" % ("yes" if os.path.exists(
        os.path.join(SRC, "interview_gate.py")) else "NO (file is missing)"))
    print()
    print("`src/interview_gate.py` ships with the interview-show module.")
    print("If you are on an older checkout, pull the latest tag; if you copied")
    print("only part of `src/`, copy that file across too. This example is a")
    print("thin demo of that module -- there is deliberately no fallback copy of")
    print("the rules here, so the demo can never drift from the real gate.")
    print("=" * 68)
    raise SystemExit(1)


# ── a fictional guest (every value below is made up for the demo) ────────────
def demo_guest(source_for_achievement):
    """Same guest twice; only the achievement's source string changes."""
    return {
        "ep": "01",
        "name": "Sam Rivera (fictional demo guest)",
        "one_line": "Shipped a working app in eight weeks with no coding background",
        "start_state": "Had never written a line of code",
        "struggle": "Stuck for two weeks on the app store review process",
        "demo": "Builds a small automation live, from prompt to running script",
        "achievements": [
            ("Shipped an app that reached 1,200 downloads", source_for_achievement),
        ],
        "screenshots_ok": ["1,200 downloads"],
        "links": ["https://example.com/sam-rivera"],
        "audience": "a small personal newsletter",
    }


def show(step, guest):
    ok, rep = gate_guest(guest)
    print("-" * 68)
    print("%s -> %s" % (step, "PASS" if ok else "BLOCKED"))
    for f in rep["fails"]:
        print("   FAIL " + f)
    for w in rep["warns"]:
        print("   WARN " + w)
    if not rep["fails"] and not rep["warns"]:
        print("   (nothing to flag)")
    return ok


def main():
    print("=" * 68)
    print("interview_gate demo -- same guest, one field different")
    print("=" * 68)

    # STEP 1: the number is there, the receipt is not.
    bad = demo_guest("")
    ok1 = show("STEP 1  achievement with an empty source", bad)
    assert not ok1, "an unsourced achievement must not pass the gate"

    # The production entry point raises instead of returning, so a build script
    # that forgets to check the verdict still cannot walk past a red gate.
    try:
        assert_guest(bad)
        raise SystemExit("BUG: assert_guest let an unsourced guest through")
    except AssertionError as e:
        print("   assert_guest() raised, as it should:")
        print("   " + str(e).splitlines()[0])

    # STEP 2: same guest, now the claim points at something checkable.
    good = demo_guest("guest-supplied App Store Connect screenshot, 2026-06")
    ok2 = show("STEP 2  same achievement, source filled in", good)
    assert ok2, "a fully sourced guest should pass"
    assert assert_guest(good) is good, "assert_guest returns the guest on pass"

    print("-" * 68)
    print("Takeaway: warnings are things to fix before you hit record;")
    print("fails are things to fix before you send the invite.")
    print("Next: fill in `templates/interview/` with your own guest and rerun.")
    print("OK -- interview_gate demo passed")


if __name__ == "__main__":
    main()
