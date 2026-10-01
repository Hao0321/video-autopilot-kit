# -*- coding: utf-8 -*-
"""長片選擇性巨字／數字 overlay。

逐句字幕仍由 word_captions.py 負責並固定白字黑底；本模組只畫 hook、轉折、
proof 數字與 payoff 的短暫上層文字。兩層分離，避免長片整支像跳字卡拉 OK。
"""
from __future__ import annotations

import os
import subprocess
import tempfile


COLORS = {
    "white": "&H00FFFFFF&",
    "gold": "&H003FD2FF&",
    "sky": "&H00FFB05A&",
    "mint": "&H00B0C93F&",
    "coral": "&H006B6BFF&",
    "pink": "&H00A874FF&",
    "orange": "&H007AB1FF&",
}


def _ts(t):
    h = int(float(t) // 3600)
    m = int(float(t) % 3600 // 60)
    s = float(t) % 60
    return "%d:%02d:%05.2f" % (h, m, s)


def _header(font):
    return f"""[Script Info]
Title: creator Longform Selective Impact
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: NUMBER,{font},232,&H00FFFFFF,&H00101014,&H50000000,-1,0,0,0,100,100,1,0,1,14,8,5,80,80,0,1
Style: KEYWORD,{font},166,&H00FFFFFF,&H00101014,&H50000000,-1,0,0,0,100,100,2,0,1,12,7,5,100,100,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _tags(index, shadow=False):
    x = 976 if shadow else 960
    y_base = 360 if index % 2 == 0 else 440
    y = y_base + (14 if shadow else 0)
    angle = -2 if index % 2 == 0 else 2
    return (r"{\an5\pos(%d,%d)\frz%d\fad(70,120)\fscx68\fscy68"
            r"\t(0,160,\fscx112\fscy112)\t(160,310,\fscx100\fscy100)}"
            % (x, y, angle))


def build_emphasis_overlay_ass(overlays, out_path, font="Noto Sans TC"):
    """overlays 直接吃 visual_plan.caption_system.emphasis_overlays。"""
    lines = [_header(font)]
    for index, overlay in enumerate(overlays or []):
        mode = str(overlay.get("mode", "keyword"))
        if mode not in {"number", "keyword"}:
            raise AssertionError("unknown longform overlay mode %r" % mode)
        text = str(overlay.get("text", "")).replace("\n", r"\N")
        if not text or len(text.replace(" ", "")) > 10:
            raise AssertionError("longform overlay must be 1-10 chars")
        color = str(overlay.get("color", "gold"))
        if color not in COLORS:
            raise AssertionError("unknown longform overlay color %r" % color)
        start, end = float(overlay["start"]), float(overlay["end"])
        if end <= start:
            raise AssertionError("longform overlay end must exceed start")
        style = "NUMBER" if mode == "number" else "KEYWORD"
        shadow = _tags(index, shadow=True) + r"{\c&H00111116&}" + text
        body = _tags(index) + r"{\c" + COLORS[color] + "}" + text
        lines.append("Dialogue: 0,%s,%s,%s,,0,0,0,,%s" % (_ts(start), _ts(end), style, shadow))
        lines.append("Dialogue: 2,%s,%s,%s,,0,0,0,,%s" % (_ts(start), _ts(end), style, body))
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return out_path


def _self_test():
    overlays = [
        {"start": .3, "end": 1.5, "text": "12K PUBLIC_FIXTURE", "mode": "number", "color": "gold"},
        {"start": 2.0, "end": 3.1, "text": "真的有效", "mode": "keyword", "color": "sky"},
    ]
    with tempfile.TemporaryDirectory(prefix="long-impact-") as temp_dir:
        ass = os.path.join(temp_dir, "impact.ass")
        video = os.path.join(temp_dir, "src.mp4")
        build_emphasis_overlay_ass(overlays, ass)
        body = open(ass, encoding="utf-8").read()
        assert "Style: NUMBER" in body and body.count("Dialogue:") == 4
        made = subprocess.run([
            "ffmpeg", "-v", "error", "-y", "-f", "lavfi",
            "-i", "color=c=0x173F8F:s=1920x1080:r=30:d=4",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", video,
        ], capture_output=True, text=True)
        assert made.returncode == 0, made.stderr[-300:]
        burned = subprocess.run([
            "ffmpeg", "-v", "error", "-i", "src.mp4", "-vf", "ass=impact.ass",
            "-frames:v", "30", "-f", "null", "-",
        ], cwd=temp_dir, capture_output=True, text=True)
        assert burned.returncode == 0, burned.stderr[-300:]
    print("longform emphasis overlay self-test OK")


if __name__ == "__main__":
    _self_test()
