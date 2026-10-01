"""
silent_vlog_maker.quality_check — Verify an Editkin-rendered final mp4.

Extracted from old shorts_pipeline before M64 deletion.
Just verifies output mp4 is sound (audio clean / outro present / resolution).
"""
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def verify_output(mp4_path: Path, expected_outro: bool = True,
                  bgm_only: bool = False) -> dict:
    """Auto-verify a finished mp4. Returns issues dict — empty means clean.

    Catches:
    - M55: B-roll audio leak — LRA > 5 = suspicious;
      bgm_only=True 時加驗 Integrated LUFS > -22（純 BGM silent vlog 才適用——
      含人聲成品約 -11~-12 LUFS，不能用 -22 線，否則永遠誤報）
    - M56: outro card present (snapshot at end - 2 sec, check non-trivial frame size)
    - M46: portrait/landscape sanity

    Args:
        mp4_path: final mp4 from the receipt-bound Editkin render
        expected_outro: True if mp4 should have outro card → verify visible
        bgm_only: True = 無口播 silent vlog（追加 -22 LUFS 上限檢查）

    Returns:
        {
          'audio_clean': bool, 'audio_integrated_lufs': float, 'audio_lra_lu': float,
          'outro_present': bool, 'duration_sec': float, 'resolution': (w, h),
          'issues': list[str],
        }
    """
    issues = []
    result = {"issues": issues}

    # 1. Probe duration / resolution
    # ⚠️ M102：Windows 下 text=True 預設用 cp950 解 stderr，遇 UTF-8 路徑(直式/中文)會 crash。
    #    所有擷取文字的 subprocess 一律顯式 encoding="utf-8", errors="replace"。
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=width,height:format=duration", "-of", "default=nw=1",
         str(mp4_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    width = height = 0
    duration = 0.0
    for line in probe.stdout.splitlines():
        if line.startswith("width="):
            width = int(line.split("=")[1])
        elif line.startswith("height="):
            height = int(line.split("=")[1])
        elif line.startswith("duration="):
            duration = float(line.split("=")[1])
    result["resolution"] = (width, height)
    result["duration_sec"] = duration

    # 2. Audio loudness check
    loud = subprocess.run(
        ["ffprobe", "-v", "error", "-i", str(mp4_path),
         "-show_entries", "stream=codec_type", "-of", "csv=p=0"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    has_audio = "audio" in loud.stdout

    if has_audio:
        loud2 = subprocess.run(
            ["ffmpeg", "-hide_banner", "-i", str(mp4_path),
             "-af", "loudnorm=print_format=summary", "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        integrated = -99.0
        lra = -99.0
        for line in loud2.stderr.splitlines():
            if "Input Integrated" in line:
                try:
                    integrated = float(line.split(":")[1].strip().split()[0])
                except (ValueError, IndexError):
                    pass
            elif "Input LRA" in line:
                try:
                    lra = float(line.split(":")[1].strip().split()[0])
                except (ValueError, IndexError):
                    pass
        result["audio_integrated_lufs"] = integrated
        result["audio_lra_lu"] = lra
        # parse 失敗(-99 哨兵)單獨回報，不再誤判成 leak；LUFS 上限只在 bgm_only
        # 模式驗（含人聲成品 -11~-12 LUFS 本來就 > -22）（2026-06-10 audit）
        parse_ok = lra > -90 and integrated > -90
        if not parse_ok:
            result["audio_clean"] = False
            issues.append("loudnorm parse failed — audio leak check inconclusive (NOT a confirmed leak)")
        else:
            result["audio_clean"] = lra <= 5.0 and (not bgm_only or integrated <= -22.0)
            if not result["audio_clean"]:
                issues.append(
                    f"M55 LIKELY AUDIO LEAK — LRA {lra:.1f} LU (clean ≤ 5)"
                    + (f" / LUFS {integrated:.1f} (bgm_only clean ≤ -22)" if bgm_only else "")
                    + "."
                )

    # 3. Outro card visibility
    if expected_outro and duration > 5:
        outro_frame_t = duration - 2.0
        tmp_frame = mp4_path.parent / "_verify_outro_frame.png"
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-ss", str(outro_frame_t), "-i", str(mp4_path),
             "-frames:v", "1", str(tmp_frame)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if tmp_frame.exists():
            frame_size = tmp_frame.stat().st_size
            result["outro_present"] = frame_size > 30_000
            if not result["outro_present"]:
                issues.append(
                    f"M56 LIKELY NO OUTRO — frame at t={outro_frame_t:.1f}s is only {frame_size} bytes"
                )
            tmp_frame.unlink(missing_ok=True)
        else:
            issues.append(f"M56 — frame extract at t={outro_frame_t} failed")
            result["outro_present"] = False
    else:
        result["outro_present"] = None

    # 4. Resolution sanity
    if width == 0 or height == 0:
        issues.append("Resolution probe failed")

    return result


def _selftest() -> None:
    probe = SimpleNamespace(stdout="width=1080\nheight=1920\nduration=12.5\n", stderr="", returncode=0)
    audio = SimpleNamespace(stdout="", stderr="", returncode=0)
    with patch("subprocess.run", side_effect=[probe, audio]):
        result = verify_output(Path("fixture.mp4"), expected_outro=False)
    assert result["resolution"] == (1080, 1920)
    assert result["duration_sec"] == 12.5
    assert result["issues"] == []

    empty = SimpleNamespace(stdout="", stderr="", returncode=1)
    with patch("subprocess.run", side_effect=[empty, empty]):
        broken = verify_output(Path("missing.mp4"), expected_outro=False)
    assert "Resolution probe failed" in broken["issues"]
    print("quality_check self-test GREEN")


if __name__ == "__main__":
    _selftest()
