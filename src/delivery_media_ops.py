# -*- coding: utf-8 -*-
"""Editkin-neutral media probe and still-image preparation for delivery QA."""
from __future__ import annotations

import subprocess


def _run(args):
    # encoding 顯式 utf-8 + errors=replace：避免 Windows cp950 對中文路徑/輸出 crash
    return subprocess.run([str(a) for a in args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")

def _probe_dur(media):
    r = _run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
              '-of', 'csv=p=0', media])
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError(f"ffprobe 讀不到時長: {media}（檔案壞或非媒體檔）; stderr={r.stderr[-200:]}")
    return float(r.stdout.strip())

# ---------------------------------------------------------------- M92 圖片入片
def still_blurfill(img, out, dur, sigma=26, dim=0.12, fg_h=1040):
    """M92：非滿版圖/截圖 → clip。同圖放大模糊+稍暗當底，原圖置中清晰疊上。
    靜止（無 zoompan）＝零抖動。禁死黑邊。"""
    vf = (f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
          f"gblur=sigma={sigma},eq=brightness=-{dim}[bg];"
          f"[0:v]scale=1920:{fg_h}:force_original_aspect_ratio=decrease[fg];"
          f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,format=yuv420p[o]")
    r = _run(['ffmpeg', '-v', 'error', '-y', '-loop', '1', '-framerate', '30',
              '-t', dur, '-i', img, '-filter_complex', vf, '-map', '[o]', '-an',
              '-c:v', 'libx264', '-crf', '18', '-preset', 'medium',
              '-pix_fmt', 'yuv420p', '-r', '30', '-t', dur, out])
    if r.returncode:
        raise RuntimeError('still_blurfill failed: ' + r.stderr[-600:])
    return out

# ---------------------------------------------------------------- M95 死空檔


def _selftest():
    """Exercise probe parsing and the exact M92 command without invoking ffmpeg."""
    global _run
    original = _run
    calls = []

    class Result:
        returncode = 0
        stdout = "12.5\n"
        stderr = ""

    try:
        _run = lambda args: calls.append([str(arg) for arg in args]) or Result()
        assert _probe_dur("fixture.mp4") == 12.5
        assert still_blurfill("still.png", "out.mp4", 3.0) == "out.mp4"
        command = " ".join(calls[-1])
        assert "gblur=sigma=26" in command and "zoompan" not in command
        assert "overlay=(W-w)/2:(H-h)/2" in command and "-an" in calls[-1]
    finally:
        _run = original
    print("delivery_media_ops self-test GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
