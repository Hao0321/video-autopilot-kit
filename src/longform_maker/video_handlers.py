# -*- coding: utf-8 -*-
"""Reusable long-form beat handlers (public distribution).

Provides clip, still, color, proof and concat helpers driven by a project plan.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
import os
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

FPS = 30
CRF = "19"


def run_ff(args):
    """M102-safe ffmpeg/ffprobe 執行；非 0 raise 帶 stderr 尾段。"""
    r = subprocess.run([str(x) for x in args], capture_output=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit("FFMPEG ERR\n" + " ".join(map(str, args))[:200] + "\n" + (r.stderr or "")[-700:])
    return r


def ffprobe_dur(media):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(media)], capture_output=True,
                       encoding="utf-8", errors="replace")
    return float(r.stdout.strip() or 0)


def _fwd(p):
    return str(p).replace("\\", "/")


# ---------------------------------------------------------------- handlers
def clip_to_beat(clip_mp4, dur, out, fps=FPS, crf=CRF):
    """動畫 clip → 播完後 clone 尾幀補滿 dur（初剪；fine cut 改 KB 續動）。
    hold 用 ffprobe 真實 clip 長算（示範長片 舊版硬編 dur-6.0 假設全是 6s clip —
    模組化時 AP12 self-test 抓到非 6s clip 會漏秒，已修）。"""
    cd = ffprobe_dur(clip_mp4)
    hold = max(0.0, dur - cd) + 0.2      # +0.2 保險（-t 會裁掉多的）
    run_ff(["ffmpeg", "-y", "-i", clip_mp4,
            "-vf", f"tpad=stop_mode=clone:stop_duration={hold:.2f},fps={fps},scale=1920:1080,format=yuv420p",
            "-c:v", "libx264", "-crf", crf, "-r", fps, "-an", "-t", f"{dur:.2f}", out])


def still_to_beat(png, dur, out, blurpad=True, fps=FPS, crf=CRF):
    """靜圖 → fade-in 0.4s + M92 非滿版模糊填底（blurpad=False = 已滿版合成圖直接 scale）。"""
    vf = ("split[a][b];[b]scale=1920:1080:force_original_aspect_ratio=increase,"
          "crop=1920:1080,gblur=sigma=26,eq=brightness=-0.12[bg];"
          "[a]scale=1920:1080:force_original_aspect_ratio=decrease[fg];"
          f"[bg][fg]overlay=(W-w)/2:(H-h)/2,fade=t=in:st=0:d=0.4,fps={fps},format=yuv420p") if blurpad \
        else f"scale=1920:1080,fade=t=in:st=0:d=0.4,fps={fps},format=yuv420p"
    run_ff(["ffmpeg", "-y", "-loop", "1", "-t", f"{dur:.2f}", "-i", png,
            "-vf", vf, "-c:v", "libx264", "-crf", crf, "-r", fps, "-an", out])


def broll_card_beat(broll_mp4, card_png, dur, out, fps=FPS, crf=CRF):
    """b-roll 無限 loop 動底 + 卡片 alpha fade-in overlay。"""
    run_ff(["ffmpeg", "-y", "-stream_loop", "-1", "-i", broll_mp4, "-loop", "1", "-i", card_png,
            "-filter_complex",
            f"[0:v]scale=1920:1080,fps={fps}[bg];[1:v]format=rgba,fade=t=in:st=0.2:d=0.5:alpha=1[c];"
            f"[bg][c]overlay=0:0,format=yuv420p[v]",
            "-map", "[v]", "-t", f"{dur:.2f}", "-c:v", "libx264", "-crf", crf, "-r", fps, "-an", out])


def _concat_two(a, b, out, crf=CRF, fps=FPS):
    lst = out + ".lst.txt"
    with open(lst, "w", encoding="utf-8") as fh:
        fh.write(f"file '{_fwd(a)}'\nfile '{_fwd(b)}'\n")
    run_ff(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
            "-c:v", "libx264", "-crf", crf, "-r", fps, "-pix_fmt", "yuv420p", out])


def clip_then_still(clip_mp4, still_png, dur, out, fps=FPS, crf=CRF):
    """片尾：真動畫（如 freedom_workshop.mov）原速播完 → 接靜卡填滿剩餘（hao signature §0）。"""
    cd = min(ffprobe_dur(clip_mp4), dur)
    a = out + ".a.mp4"; b = out + ".b.mp4"
    run_ff(["ffmpeg", "-y", "-i", clip_mp4, "-t", f"{cd:.2f}",
            "-vf", f"scale=1920:1080,fps={fps},format=yuv420p",
            "-c:v", "libx264", "-crf", crf, "-r", fps, "-an", a])
    rest = max(0.1, dur - cd)
    run_ff(["ffmpeg", "-y", "-loop", "1", "-t", f"{rest:.2f}", "-i", still_png,
            "-vf", f"scale=1920:1080,fade=t=in:st=0:d=0.4,fps={fps},format=yuv420p",
            "-c:v", "libx264", "-crf", crf, "-r", fps, "-an", b])
    _concat_two(a, b, out, crf, fps)


def two_still(png_a, png_b, dur, out, split_s, fps=FPS, crf=CRF):
    """同 beat 兩張滿版圖：A 撐 split_s → 切 B 撐剩餘（M87 旁白換題畫面跟著換 × M107 真截圖）。"""
    split_s = min(max(0.3, split_s), dur - 0.3)
    a = out + ".a.mp4"; b = out + ".b.mp4"
    run_ff(["ffmpeg", "-y", "-loop", "1", "-t", f"{split_s:.2f}", "-i", png_a,
            "-vf", f"scale=1920:1080,fade=t=in:st=0:d=0.4,fps={fps},format=yuv420p",
            "-c:v", "libx264", "-crf", crf, "-r", fps, "-an", a])
    run_ff(["ffmpeg", "-y", "-loop", "1", "-t", f"{dur - split_s:.2f}", "-i", png_b,
            "-vf", f"scale=1920:1080,fade=t=in:st=0:d=0.3,fps={fps},format=yuv420p",
            "-c:v", "libx264", "-crf", crf, "-r", fps, "-an", b])
    _concat_two(a, b, out, crf, fps)


HANDLERS = {
    "clip": lambda src, d, out: clip_to_beat(src, d, out),
    "still": lambda src, d, out: still_to_beat(src, d, out, blurpad=True),
    "stillfull": lambda src, d, out: still_to_beat(src, d, out, blurpad=False),
    "brollcard": lambda src, d, out: broll_card_beat(src[0], src[1], d, out),
    "clipstill": lambda src, d, out: clip_then_still(src[0], src[1], d, out),
    "twostill": lambda src, d, out: two_still(src[0], src[1], d, out, src[2]),
}


def beat_dur(offsets, bk, tail_pad=0.30):
    """beat 視覺時長 = 下一 beat start − 本 beat start（吸收換氣 gap）；末 beat = dur + tail_pad。"""
    i = int(bk[1:])
    nxt = f"b{i + 1:02d}"
    if nxt in offsets:
        return round(offsets[nxt]["start"] - offsets[bk]["start"], 3)
    return round(offsets[bk]["dur"] + tail_pad, 3)


def concat_segments(segs, out, crf=CRF, fps=FPS):
    lst = os.path.join(os.path.dirname(segs[0]), "_concat.txt")
    with open(lst, "w", encoding="utf-8") as fh:
        for s in segs:
            fh.write(f"file '{_fwd(s)}'\n")
    run_ff(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
            "-c:v", "libx264", "-crf", crf, "-r", fps, "-pix_fmt", "yuv420p", out])
    return out


def build_beats(plan, offsets, vseg_dir, out_name="video_silent.mp4", verbose=True):
    """PLAN dict + offsets → 逐 beat 產段 → concat → video_silent 路徑。
    AP12 invariant：成片時長 ≈ 末 beat start+dur+0.3（±0.5s tolerance，desync 金絲雀）。"""
    os.makedirs(vseg_dir, exist_ok=True)
    segs = []
    for bk in sorted(plan.keys()):
        kind, src = plan[bk]
        d = beat_dur(offsets, bk)
        out = os.path.join(vseg_dir, f"{bk}.mp4")
        if verbose:
            print(f"{bk} {kind} dur={d:.1f}s")
        HANDLERS[kind](src, d, out)
        segs.append(out)
    silent = os.path.join(os.path.dirname(vseg_dir.rstrip("/\\")), out_name)
    concat_segments(segs, silent)
    last = sorted(plan.keys())[-1]
    expect = offsets[last]["start"] + offsets[last]["dur"] + 0.30
    got = ffprobe_dur(silent)
    assert abs(got - expect) < 0.5, f"AP12: video_silent {got:.2f}s != 期望 {expect:.2f}s（beat 漂移）"
    return silent


# ──────────────────────────────────────────── self-test（真 ffmpeg）
if __name__ == "__main__":
    import tempfile, shutil
    from PIL import Image
    work = tempfile.mkdtemp(prefix="vidhandlers_")
    try:
        clip = os.path.join(work, "clip.mp4")
        run_ff(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=navy:s=320x180:r=30:d=2",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", clip])
        png_a = os.path.join(work, "a.png"); Image.new("RGB", (1920, 1080), (30, 20, 60)).save(png_a)
        png_b = os.path.join(work, "b.png"); Image.new("RGB", (800, 500), (60, 20, 30)).save(png_b)

        off = {"b01": {"start": 0.0, "dur": 2.7}, "b02": {"start": 3.0, "dur": 2.7},
               "b03": {"start": 6.0, "dur": 2.7}, "b04": {"start": 9.0, "dur": 2.5}}
        plan = {"b01": ("clip", clip),
                "b02": ("stillfull", png_a),
                "b03": ("twostill", (png_a, png_b, 1.5)),
                "b04": ("clipstill", (clip, png_a))}
        vseg = os.path.join(work, "vseg")
        silent = build_beats(plan, off, vseg, verbose=False)
        got = ffprobe_dur(silent)
        assert abs(got - (9.0 + 2.5 + 0.3)) < 0.5, f"時長 {got}"
        # still(blurpad) + brollcard 也各跑一次
        s2 = os.path.join(work, "s2.mp4"); still_to_beat(png_b, 1.5, s2)
        assert abs(ffprobe_dur(s2) - 1.5) < 0.2
        bc = os.path.join(work, "bc.mp4"); broll_card_beat(clip, png_a, 1.5, bc)
        assert abs(ffprobe_dur(bc) - 1.5) < 0.2
        print("[video_handlers selftest] OK — 6 handler + build_beats + AP12 invariant 全過")
    finally:
        shutil.rmtree(work, ignore_errors=True)
