# -*- coding: utf-8 -*-
"""Screen-recording privacy cleaner (public distribution).

Trims capture boundaries and applies fail-closed privacy checks before a recording becomes selectable.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
import os, subprocess, sys
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8")
    except Exception: pass

MIN_HEAD_TRIM = 1.0   # M104 floor：低於這個值直接 raise，防「這次應該不用吧」
MIN_TAIL_TRIM = 1.0   # PUBLIC_FIXTURE generic stop-capture safety floor


def _run(a):
    r = subprocess.run([str(x) for x in a], capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed: " + " ".join(map(str, a))[:200] + "\n" + (r.stderr or "")[-800:])
    return r


def _dur(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(f)],
                       capture_output=True, encoding="utf-8", errors="replace")
    return float((r.stdout or "0").strip() or 0)


def clean_screen_recording(src, out, crop, head_trim=1.0, tail_trim=2.0, blur=24, crf=18, fps=30,
                           canvas=(1920, 1080), blur_boxes=None):
    """螢幕錄影 → 乾淨素材（M104 機械鏈：trim 頭尾 + crop chrome + blur-pad + 去聲）。

    crop = "W:H:X:Y"（內容區，例：遊戲在瀏覽器 = "1920:930:0:100" 去上 chrome 下工作列；
           Unreal = "1920:984:0:40" 去上分頁列(公司名!)下工作列；
           ChatGPT = 只留中央生成圖欄，砍左側對話史+真名）。
    head_trim / tail_trim 秒物理移除（各 >=1.0 強制，M104：OBS 在【頭尾兩端】）。
    blur_boxes = [(x,y,w,h),...]【原始畫面座標】的定點重模糊區（UI 內文的公司名/真名，
                 例：Unreal Components 面板 header + Event Graph 麵包屑 —— crop 救不了畫面中央的字）。
    回傳 out 路徑。
    """
    if head_trim < MIN_HEAD_TRIM:
        raise ValueError(f"M104: head_trim={head_trim} < {MIN_HEAD_TRIM} — OBS 切入瞬間在 0-1s，不准降")
    if tail_trim < MIN_TAIL_TRIM:
        raise ValueError(f"M104: tail_trim={tail_trim} < {MIN_TAIL_TRIM} — 停止錄製瞬間在尾端，不准降")
    dur = _dur(src)
    usable = dur - head_trim - tail_trim
    if usable < 1.0:
        raise ValueError(f"M104: {src} 長 {dur:.2f}s，trim 頭{head_trim}+尾{tail_trim} 後剩 {usable:.2f}s 不夠用")
    W, H = canvas
    pre = "[0:v]"
    fc = ""
    if blur_boxes:   # 先在原始座標把敏感字糊掉，再 crop（座標不用換算）
        for bi, (bx, by, bw, bh) in enumerate(blur_boxes):
            fc += (f"{pre}split[bm{bi}][bs{bi}];"
                   f"[bs{bi}]crop={bw}:{bh}:{bx}:{by},gblur=sigma=14[bb{bi}];"   # gblur：小框無 chroma 半徑限制
                   f"[bm{bi}][bb{bi}]overlay={bx}:{by}[bo{bi}];")
            pre = f"[bo{bi}]"
    fc += (f"{pre}crop={crop},split[a][b];"
           f"[b]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
           f"boxblur={blur}:4,setsar=1[bg];"
           f"[a]scale={W}:-2,setsar=1[fg];"
           f"[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]")
    _run(["ffmpeg", "-v", "error", "-y", "-ss", f"{head_trim:.3f}", "-t", f"{usable:.3f}",
          "-i", str(src), "-filter_complex", fc, "-map", "[v]", "-an",
          "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-r", str(fps), str(out)])
    return str(out)


# ──────────────────────────────────────────── self-test（M97：真 ffmpeg end-to-end）
if __name__ == "__main__":
    import tempfile, shutil
    work = tempfile.mkdtemp(prefix="screenclean_selftest_")
    try:
        src = os.path.join(work, "rec.mp4")
        _run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
              "-i", "testsrc2=size=1920x1080:rate=30:duration=5.0",
              "-c:v", "libx264", "-pix_fmt", "yuv420p", src])
        out = os.path.join(work, "clean.mp4")
        clean_screen_recording(src, out, "1920:930:0:100", head_trim=1.0, tail_trim=2.0,
                               blur_boxes=[(100, 200, 300, 40)])
        d = _dur(out)
        assert abs(d - 2.0) < 0.15, f"頭尾 trim 沒生效 (dur={d}, 期望 5-1-2=2)"
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=width,height", "-of", "csv=p=0", out],
                           capture_output=True, encoding="utf-8", errors="replace")
        import re as _re
        nums = _re.findall(r"\d+", r.stdout or "")
        assert nums[:2] == ["1920", "1080"], f"canvas 不對 {nums}"
        r2 = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
                             "-show_entries", "stream=codec_name", "-of", "csv=p=0", out],
                            capture_output=True, encoding="utf-8", errors="replace")
        assert not (r2.stdout or "").strip(), "音軌沒去掉 (M29)"
        neg = 0
        for kw in ({"head_trim": 0.5}, {"tail_trim": 0.5}):
            try:
                clean_screen_recording(src, out, "1920:930:0:100", **kw)
            except ValueError:
                neg += 1
        assert neg == 2, "head/tail trim floor 該被擋下"
        print("[screen_clean selftest] OK — 頭尾trim/crop/blurpad/去聲/blur_boxes/floor 全過")
    finally:
        shutil.rmtree(work, ignore_errors=True)
