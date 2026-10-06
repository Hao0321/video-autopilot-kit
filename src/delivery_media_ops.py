# -*- coding: utf-8 -*-
"""Editkin-neutral media probe and still-image preparation for delivery QA."""
from __future__ import annotations

import math
import re
import subprocess

_SIGNAL_KEYS = ("YAVG", "UAVG", "VAVG")


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


def _has_stream(media, kind):
    """True when ``media`` carries a ``kind`` ('a' or 'v') stream; a failed probe raises."""
    r = _run(['ffprobe', '-v', 'error', '-select_streams', kind,
              '-show_entries', 'stream=index', '-of', 'csv=p=0', media])
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe stream probe failed: {media}; stderr={r.stderr[-200:]}")
    return bool(r.stdout.strip())


def _parse_db(token, floor=-200.0):
    """ffmpeg dB text -> float. '-inf' (digital silence) -> ``floor``; NaN/garbage -> None."""
    text = str(token).strip().rstrip(",").lower()
    if text in ("-inf", "-infinity"):
        return float(floor)
    try:
        value = float(text)
    except ValueError:
        return None
    if math.isnan(value):
        return None
    return float(floor) if value == float("-inf") else value


def _frame_signal_means(video, width=160):
    """Per-frame mean Y'/Cb/Cr through signalstats, as full-range 8-bit values.

    Returns ``(rows, returncode, stderr_tail)`` with rows ``[(pts_time, Y, Cb, Cr)]``
    sorted by time. The frame is area-downscaled first: means are preserved while
    long masters stay cheap. Only finite, complete rows are kept.
    """
    vf = (f"scale={width}:-2:flags=area:out_range=full,format=yuv420p,signalstats," +
          ",".join(f"metadata=mode=print:key=lavfi.signalstats.{key}" for key in _SIGNAL_KEYS))
    r = _run(['ffmpeg', '-hide_banner', '-nostats', '-i', video, '-map', '0:v:0', '-an',
              '-vf', vf, '-f', 'null', '-'])
    frames, stamp = {}, None
    for line in (r.stderr or "").splitlines():
        found = re.search(r"pts_time:(\S+)", line)
        if found:
            stamp = found.group(1)
            continue
        found = re.search(r"lavfi\.signalstats\.(YAVG|UAVG|VAVG)=(\S+)", line)
        if found and stamp is not None:
            frames.setdefault(stamp, {})[found.group(1)] = found.group(2)
    rows = []
    for stamp, values in frames.items():
        try:
            row = (float(stamp),) + tuple(float(values[key]) for key in _SIGNAL_KEYS)
        except (KeyError, ValueError):
            continue
        if all(math.isfinite(value) for value in row):
            rows.append(row)
    return sorted(rows), r.returncode, (r.stderr or "")[-300:]


# ---------------------------------------------- M93 flash math (WCAG 2.3.1 / ITU-R BT.1702 style)
def _srgb_linear(value):
    value = min(1.0, max(0.0, value))
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _frame_light(y, cb, cr):
    """Full-range mean Y'CbCr -> (relative luminance, red ratio, red metric).

    BT.709 matrix to R'G'B', sRGB EOTF to linear light, WCAG luminance weights.
    R/(R+G+B) >= 0.8 marks saturated red; max(0, R-G-B)*320 is the red-flash
    change measure."""
    luma, pb, pr = y / 255.0, (cb - 128.0) / 255.0, (cr - 128.0) / 255.0
    r, g, b = (_srgb_linear(v) for v in (luma + 1.5748 * pr,
                                          luma - 0.1873 * pb - 0.4681 * pr,
                                          luma + 1.8556 * pb))
    total = r + g + b
    return (0.2126 * r + 0.7152 * g + 0.0722 * b,
            r / total if total > 0 else 0.0, max(0.0, (r - g - b) * 320.0))


def _swings(values, delta):
    """Hysteresis zig-zag: opposing swings of at least ``delta`` in a series.

    Returns ``[[confirm_index, start_index, end_index]]``; consecutive swings
    alternate direction and a swing keeps extending while its sign holds."""
    swings, low, high, ext, sign = [], 0, 0, 0, 0
    for i in range(1, len(values)):
        value = values[i]
        if sign == 0:
            low = i if value < values[low] else low
            high = i if value > values[high] else high
            if value - values[low] >= delta or values[high] - value >= delta:
                sign = 1 if value - values[low] >= delta else -1
                swings.append([i, low if sign > 0 else high, i])
                ext = i
        elif (value - values[ext]) * sign >= 0:
            ext = swings[-1][2] = i
        elif (values[ext] - value) * sign >= delta:
            swings.append([i, ext, i])
            sign, ext = -sign, i
    return swings


def _peak_window(times, window=1.0):
    """(largest number of event times inside any half-open window, window start)."""
    best, start, first = 0, None, 0
    for last, stamp in enumerate(times):
        while stamp - times[first] >= window:
            first += 1
        if last - first + 1 > best:
            best, start = last - first + 1, times[first]
    return best, start


def flash_transitions(times, light, delta=0.1, dark=0.8, red_delta=20.0, red_sat=0.8):
    """Pure WCAG counting -> (general transition times, red transition times).

    General: opposing luminance swings >= ``delta`` (10% of the maximum relative
    luminance) whose darker end is below ``dark``. Red: swings of the red metric
    >= ``red_delta`` whose redder end is a saturated red."""
    lum = [row[0] for row in light]
    ratio = [row[1] for row in light]
    red = [row[2] for row in light]
    general = [times[c] for c, s, e in _swings(lum, delta) if min(lum[s], lum[e]) < dark]
    reds = [times[c] for c, s, e in _swings(red, red_delta)
            if ratio[s if red[s] >= red[e] else e] >= red_sat]
    return sorted(general), sorted(reds)


# ---------------------------------------------- M92 cropdetect parsing
def _crop_samples(text):
    """cropdetect log -> sorted [(t, (w, h, x, y))]; all-black samples (w/h <= 0) carry no box."""
    boxes = {}
    for m in re.finditer(r"\bt:\s*([-\d.eE+]+)[^\n]*?crop=(-?\d+):(-?\d+):(-?\d+):(-?\d+)", text):
        w, h, x, y = (int(v) for v in m.group(2, 3, 4, 5))
        try:
            stamp = round(float(m.group(1)), 3)
        except ValueError:
            continue
        if w > 0 and h > 0:
            boxes[stamp] = (w, h, x, y)
    return sorted(boxes.items())


def _border_spans(samples, width, height, tol, step):
    """Consecutive bordered samples -> [(start, end, (w, h, x, y) union box)]."""
    spans, cur = [], None
    for stamp, (w, h, x, y) in samples:
        if (width - w) > tol or (height - h) > tol:
            if cur is None:
                cur = [stamp, stamp, x, y, x + w, y + h]
            else:
                cur[1:] = [stamp, min(cur[2], x), min(cur[3], y), max(cur[4], x + w), max(cur[5], y + h)]
        elif cur is not None:
            spans.append(cur)
            cur = None
    spans += [cur] if cur is not None else []
    return [(round(a, 2), round(b + step, 2), (x2 - x1, y2 - y1, x1, y1))
            for a, b, x1, y1, x2, y2 in spans]


def _lavfi_clip(out, video, audio=None, seconds=3.0, fps=30):
    """Render a tiny deterministic lavfi fixture (self-tests only): H.264 (+ AAC) MP4."""
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', video]
    if audio:
        cmd += ['-f', 'lavfi', '-i', audio]
    cmd += ['-t', seconds, '-r', fps, '-c:v', 'libx264', '-preset', 'ultrafast',
            '-pix_fmt', 'yuv420p']
    cmd += ['-c:a', 'aac', '-b:a', '128k', '-ar', '48000'] if audio else ['-an']
    r = _run(cmd + [out])
    if r.returncode:
        raise RuntimeError('fixture render failed: ' + r.stderr[-600:])
    return out

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
        assert _has_stream("fixture.mp4", "a") is True, "stream probe must read stdout"
        Result.stdout, Result.returncode = "", 0
        assert _has_stream("fixture.mp4", "a") is False, "no stream rows = no stream"
        Result.returncode = 1
        try:
            _has_stream("fixture.mp4", "a")
        except RuntimeError:
            pass
        else:
            raise AssertionError("a failed stream probe must raise, never read as 'no stream'")
        Result.returncode, Result.stderr = 0, (
            "[Parsed_metadata_2 @ 0x1] frame:0    pts:0       pts_time:0\n"
            "[Parsed_metadata_2 @ 0x1] lavfi.signalstats.YAVG=255\n"
            "[Parsed_metadata_3 @ 0x2] frame:0    pts:0       pts_time:0\n"
            "[Parsed_metadata_3 @ 0x2] lavfi.signalstats.UAVG=128\n"
            "[Parsed_metadata_4 @ 0x3] frame:0    pts:0       pts_time:0\n"
            "[Parsed_metadata_4 @ 0x3] lavfi.signalstats.VAVG=128\n"
            "[Parsed_metadata_2 @ 0x1] frame:1    pts:512     pts_time:0.0333333\n"
            "[Parsed_metadata_2 @ 0x1] lavfi.signalstats.YAVG=nan\n"
            "[Parsed_metadata_3 @ 0x2] frame:1    pts:512     pts_time:0.0333333\n"
            "[Parsed_metadata_3 @ 0x2] lavfi.signalstats.UAVG=128\n"
            "[Parsed_metadata_4 @ 0x3] frame:1    pts:512     pts_time:0.0333333\n"
            "[Parsed_metadata_4 @ 0x3] lavfi.signalstats.VAVG=128\n"
            "[Parsed_metadata_2 @ 0x1] frame:2    pts:1024    pts_time:0.0666667\n"
            "[Parsed_metadata_2 @ 0x1] lavfi.signalstats.YAVG=16\n")
        rows, code, _tail = _frame_signal_means("fixture.mp4")
        assert code == 0 and rows == [(0.0, 255.0, 128.0, 128.0)], rows
        assert "out_range=full" in " ".join(calls[-1]), "means must be normalised to full range"
    finally:
        _run = original
    assert _parse_db("-inf") == -200.0 and _parse_db(" -12.5 ") == -12.5
    assert _parse_db("nan") is None and _parse_db("-") is None and _parse_db("inf") == float("inf")
    _selftest_signal_math()
    print("delivery_media_ops self-test GREEN")
    return 0


def _selftest_signal_math():
    """WCAG flash counting and cropdetect parsing on synthetic series (no ffmpeg)."""
    times = [i / 30.0 for i in range(60)]
    strobe = flash_transitions(times, [(float(i % 2), 1 / 3.0, 0.0) for i in range(60)])
    assert _peak_window(strobe[0])[0] > 6 and strobe[1] == [], "15 Hz strobe must exceed 3 flashes/s"
    slow = flash_transitions(times, [(float((i // 15) % 2), 1 / 3.0, 0.0) for i in range(60)])
    assert 0 < _peak_window(slow[0])[0] <= 6, "1 Hz alternation stays under the WCAG limit"
    bright = [(0.84 + 0.12 * (i % 2), 1 / 3.0, 0.0) for i in range(60)]
    assert len(_swings([row[0] for row in bright], 0.1)) > 6, "swings exist ..."
    assert flash_transitions(times, bright)[0] == [], "... but a darker end >= 0.8 is not a flash"
    red, grey = _frame_light(76.4, 85.0, 255.0), _frame_light(129.0, 128.0, 128.0)
    assert abs(red[0] - grey[0]) < 0.01 and red[1] >= 0.8, (red, grey)
    iso = flash_transitions(times, [red if i % 3 < 2 else grey for i in range(60)])
    assert iso[0] == [] and _peak_window(iso[1])[0] > 6, "red/grey strobe needs the red-flash proxy"
    assert _peak_window([0.0, 0.5, 0.99, 1.0, 1.4]) == (4, 0.5), "window is half-open [t, t+1)"
    log = "".join(f"t:{t / 4:.6f} limit:24 crop={'180:200:0:60' if t >= 4 else '180:320:0:0'}\n"
                  for t in range(2, 12)) + "t:3.000000 limit:24 crop=-178:-318:180:320\n"
    samples = _crop_samples(log)
    assert len(samples) == 10 and _border_spans(samples, 180, 320, 4, 0.25) == [(1.0, 3.0, (180, 200, 0, 60))]


if __name__ == "__main__":
    raise SystemExit(_selftest())
