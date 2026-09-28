#!/usr/bin/env python3
"""Read-only music timing candidates for an Editkin Music MV.

The result is deliberately a *candidate* grid. It cannot establish the real
downbeat, musical phrase, lyric words, rights, or an aesthetically good cut.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import statistics
import subprocess
import tempfile
from pathlib import Path

from longform_maker.music_engine import _load_pcm, _probe_duration, detect_beats


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _extract_window(source: Path, target: Path, start: float, duration: float) -> None:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(start),
         "-i", str(source), "-t", str(duration), "-vn", "-ac", "1", "-ar", "22050",
         "-c:a", "pcm_s16le", "-y", str(target)],
        capture_output=True,
    )
    if result.returncode or not target.is_file() or target.stat().st_size < 1024:
        raise RuntimeError("AUDIO_DECODE_FAILED: " + result.stderr.decode("utf-8", "replace")[-350:])


def analyze_song(source: Path, start: float = 0, window: float = 45,
                 force_fallback: bool = False) -> dict:
    source = source.resolve(strict=True)
    if not source.is_file() or not math.isfinite(start) or not math.isfinite(window):
        raise ValueError("source, start, and window must be valid")
    if start < 0 or window < 12 or window > 60:
        raise ValueError("start must be nonnegative and window must be 12–60 seconds")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFMPEG_REQUIRED")
    song_duration = _probe_duration(source)
    if song_duration <= 0 or start >= song_duration - 12:
        raise ValueError("analysis window has fewer than 12 seconds of audio")
    window = min(window, song_duration - start)
    with tempfile.TemporaryDirectory(prefix="editkin-music-mv-") as temporary:
        excerpt = Path(temporary) / "excerpt.wav"
        _extract_window(source, excerpt, start, window)
        pcm, _ = _load_pcm(excerpt)
        rms = math.sqrt(float((pcm.astype("float64") ** 2).mean())) if pcm.size else 0.0
        if rms < 0.001:
            detected = {"bpm": 0.0, "beats": [], "confidence": "none"}
        else:
            detected = detect_beats(excerpt, force_fallback=force_fallback)

    local_beats = [float(t) for t in detected["beats"] if 0 <= float(t) < window]
    beats = [round(start + t, 4) for t in local_beats]
    intervals = [b - a for a, b in zip(beats, beats[1:])]
    median_interval = statistics.median(intervals) if intervals else 0.0
    regularity = (1 - statistics.median(abs(value - median_interval) for value in intervals) / median_interval
                  if median_interval > 0 else 0.0)
    plausible = 60 <= float(detected["bpm"]) <= 180 and len(beats) >= 8 and regularity >= 0.75
    status = "BEAT_GRID_REVIEW_REQUIRED" if plausible else "BEAT_GRID_UNAVAILABLE"
    return {
        "schema": "hao.video-autopilot.music-mv-preflight/v1",
        "status": status,
        "sourceSha256": _sha256(source),
        "sourceDurationSec": round(song_duration, 4),
        "analysisRangeSec": [round(start, 4), round(start + window, 4)],
        "algorithm": detected["confidence"],
        "bpmCandidate": float(detected["bpm"]) if plausible else None,
        "beatCandidatesSec": beats if plausible else [],
        "fourBeatBoundaryCandidatesSec": beats[::4] if plausible else [],
        "eightBeatBoundaryCandidatesSec": beats[::8] if plausible else [],
        "gridRegularity": round(regularity, 4),
        "downbeatVerified": False,
        "phraseVerified": False,
        "lyricsTranscribed": False,
        "next": "Check downbeat/phrase against the actual song and visual story; choose a sparse cut grid. Do not treat every beat as a cut or infer lyrics.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song", type=Path)
    parser.add_argument("--start", type=float, default=0)
    parser.add_argument("--window", type=float, default=45)
    parser.add_argument("--fallback", action="store_true", help="Use deterministic NumPy detector")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze_song(args.song, args.start, args.window, args.fallback)
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
