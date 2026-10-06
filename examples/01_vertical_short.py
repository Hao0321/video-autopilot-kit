#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example 01 — build a vertical 9:16 Short end-to-end, with ZERO real footage.

This is the fastest way to see `silent_vlog_maker` actually work: it synthesizes
test clips + a test music track with ffmpeg, then runs the real pipeline
(normalize → multi-color captions → BGM at its highlight) to produce a finished
1080x1920 MP4.

Run:
    python examples/01_vertical_short.py

Needs: Python 3.9+ and `ffmpeg`/`ffprobe` on your PATH. No CapCut, no real media.
Captions use "Noto Sans TC" when it is installed; otherwise the kit requests the
CJK font it finds (Noto Sans CJK, Microsoft JhengHei, PingFang ...) so Latin and
Chinese share one face. Every caption is measured and wrapped/scaled to stay
inside the 1080x1920 text-safe area (x 108..972); one that cannot fit raises.
"""
import os
import sys
import subprocess
import tempfile

# Make `src/` importable when running this file directly from the repo.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from silent_vlog_maker import normalize_to_portrait, build_one_short  # noqa: E402


def _ff(*args):
    """Run ffmpeg/ffprobe, raising with stderr on failure."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise RuntimeError("ffmpeg failed:\n" + r.stderr[-800:])


def _probe(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-of", "default=nw=1",
         "-show_entries", "stream=codec_type,width,height", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout


def main():
    work = tempfile.mkdtemp(prefix="vak_example01_")
    print(f"[1/5] work dir: {work}")

    # --- synthesize two "raw" landscape clips (stand-ins for phone footage) ---
    raw1 = os.path.join(work, "raw1.mp4")
    raw2 = os.path.join(work, "raw2.mp4")
    _ff("-f", "lavfi", "-i", "testsrc2=size=1280x720:duration=5:rate=30",
        "-pix_fmt", "yuv420p", raw1)
    _ff("-f", "lavfi", "-i", "mandelbrot=size=1280x720:rate=30",
        "-t", "5", "-pix_fmt", "yuv420p", raw2)
    print("[2/5] synthesized 2 landscape test clips")

    # --- normalize each to upright 1080x1920 (handles rotation flags too) ---
    norm1 = os.path.join(work, "norm1.mp4")
    norm2 = os.path.join(work, "norm2.mp4")
    normalize_to_portrait(raw1, norm1)
    normalize_to_portrait(raw2, norm2)
    print("[3/5] normalized to 9:16 portrait")

    # --- synthesize a music track LONGER than the video (so it never loops) ---
    bgm = os.path.join(work, "bgm.mp3")
    _ff("-f", "lavfi", "-i", "sine=frequency=330:duration=20",
        "-af", "volume=0.6", "-q:a", "4", bgm)
    print("[4/5] synthesized a 20s test BGM")

    # --- build the Short: two 5s segments + multi-color captions + auto BGM ---
    # caps tuple: (start_s, end_s, [(text, color), ...], kind)
    # colors: w=white o=orange y=yellow r=red g=green ; kind: 'main' | 'addr'
    # Adjacent Latin blocks get a space ("video-autopilot-kit demo"), and a line
    # wider than the safe area breaks once at a word boundary before scaling.
    out = os.path.join(work, "short.mp4")
    build_one_short(
        segs=[(norm1, 0.0, 5.0), (norm2, 0.0, 5.0)],
        caps=[
            (0.3, 5.0, [("video-autopilot-kit", "g"), ("demo", "y")], "main"),
            (5.3, 9.7, [("pure ", "w"), ("ffmpeg", "o"), (" pipeline", "w")], "main"),
            (5.3, 9.7, [("no CapCut needed", "w")], "addr"),
        ],
        bgm=bgm,
        out=out,
        vol=0.42,        # BGM is the main audio (silent footage)
        bgm_start="auto",  # ride the music's highlight, not the intro
    )
    print("[5/5] built the Short")

    print("\n" + "=" * 56)
    print("DONE. Finished vertical Short:")
    print(f"  {out}")
    print("ffprobe streams (expect one 1080x1920 video + one audio):")
    print(_probe(out).strip())
    print("=" * 56)
    print("Open it in any player. Swap the synthesized clips/BGM for your own")
    print("phone footage + a music file and you have a real food/travel Short.")


if __name__ == "__main__":
    main()
