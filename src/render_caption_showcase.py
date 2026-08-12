# -*- coding: utf-8 -*-
"""用真 ffmpeg 產生長／短片字幕系統預覽。"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

from PIL import Image, ImageDraw


HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "longform_maker"))

from silent_vlog_maker.shorts_vertical import build_multicolor_ass  # noqa: E402
from emphasis_overlays import build_emphasis_overlay_ass  # noqa: E402
from word_captions import build_ass as build_spoken_ass  # noqa: E402


def _run(args, cwd=None):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError((result.stderr or "")[-700:])


def _short(out_dir):
    src = os.path.join(out_dir, "_short_bg.mp4")
    ass = os.path.join(out_dir, "shorts_caption_showcase.ass")
    out = os.path.join(out_dir, "shorts_caption_showcase.mp4")
    blocks = [
        (.20, 1.55, [("AI 快了 ", "white"), ("3 倍", "gold")], "impact"),
        (1.75, 3.05, [("第 1 步：先看結果", "white")], "ribbon"),
        (3.25, 4.55, [("只改這裡", "mint")], "float_left"),
        (4.75, 6.05, [("快 3 倍", "gold")], "float_right"),
        (6.25, 7.75, [("其他字幕保持", "white"), ("乾淨", "sky")], "sub"),
    ]
    build_multicolor_ass(blocks, ass, theme="ai")
    vf = (
        "drawgrid=w=90:h=90:t=2:c=white@0.16,"
        "drawbox=x=42:y=72:w=996:h=260:color=black@0.28:t=fill,"
        "drawbox=x=64:y=1510:w=360:h=230:color=0xFF5A36@0.92:t=fill,"
        "drawbox=x=452:y=1510:w=560:h=230:color=0x9BFF21@0.88:t=fill"
    )
    _run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
          "-i", "color=c=0x133EC8:s=1080x1920:r=30:d=8", "-vf", vf,
          "-c:v", "libx264", "-pix_fmt", "yuv420p", src])
    _run(["ffmpeg", "-v", "error", "-y", "-i", os.path.basename(src),
          "-vf", "ass=" + os.path.basename(ass), "-an", "-c:v", "libx264",
          "-crf", "19", "-pix_fmt", "yuv420p", os.path.basename(out)], cwd=out_dir)
    return out, [(.8, "SHORT / IMPACT"), (2.4, "SHORT / RIBBON"),
                 (3.9, "SHORT / FLOAT L"), (5.4, "SHORT / FLOAT R")]


def _long(out_dir):
    src = os.path.join(out_dir, "_long_bg.mp4")
    spoken = os.path.join(out_dir, "longform_spoken_captions.ass")
    impact = os.path.join(out_dir, "longform_emphasis_overlays.ass")
    out = os.path.join(out_dir, "longform_text_showcase.mp4")
    build_spoken_ass([
        (.10, 2.20, "今天直接看最後的結果"),
        (2.30, 4.35, "接著我會拆解整個做法"),
        (4.45, 6.55, "只改這個步驟就快很多"),
        (6.65, 7.85, "其他時間讓畫面呼吸"),
    ], spoken)
    build_emphasis_overlay_ass([
        {"start": .45, "end": 1.65, "text": "270萬", "mode": "number", "color": "gold"},
        {"start": 4.72, "end": 5.92, "text": "快 3 倍", "mode": "number", "color": "sky"},
    ], impact)
    vf = (
        "drawgrid=w=120:h=120:t=1:c=white@0.13,"
        "drawbox=x=80:y=80:w=1760:h=140:color=black@0.24:t=fill,"
        "drawbox=x=110:y=250:w=720:h=470:color=0x0E2D78@0.72:t=fill,"
        "drawbox=x=890:y=250:w=900:h=470:color=0x20E0A0@0.34:t=fill"
    )
    _run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
          "-i", "color=c=0x1239B5:s=1920x1080:r=30:d=8", "-vf", vf,
          "-c:v", "libx264", "-pix_fmt", "yuv420p", src])
    filters = "ass=%s,ass=%s" % (os.path.basename(spoken), os.path.basename(impact))
    _run(["ffmpeg", "-v", "error", "-y", "-i", os.path.basename(src),
          "-vf", filters, "-an", "-c:v", "libx264", "-crf", "19",
          "-pix_fmt", "yuv420p", os.path.basename(out)], cwd=out_dir)
    return out, [(1.0, "LONG / NUMBER + CLEAN CAPTION"),
                 (5.1, "LONG / PAYOFF + CLEAN CAPTION")]


def _frame(video, t, path):
    _run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", video,
          "-frames:v", "1", "-q:v", "2", path])


def _contact_sheet(out_dir, sources):
    tiles = []
    for video, samples in sources:
        for index, (t, label) in enumerate(samples):
            path = os.path.join(out_dir, "_frame_%02d.jpg" % len(tiles))
            _frame(video, t, path)
            image = Image.open(path).convert("RGB")
            image.thumbnail((620, 620))
            canvas = Image.new("RGB", (640, 680), "#111318")
            x = (640 - image.width) // 2
            y = 42 + (600 - image.height) // 2
            canvas.paste(image, (x, y))
            draw = ImageDraw.Draw(canvas)
            draw.text((24, 16), label, fill="white")
            tiles.append(canvas)
    cols = 2
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 640, rows * 680), "#08090c")
    for i, tile in enumerate(tiles):
        sheet.paste(tile, ((i % cols) * 640, (i // cols) * 680))
    out = os.path.join(out_dir, "caption_showcase_contact_sheet.jpg")
    sheet.save(out, quality=94)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=os.path.join(HERE, "_runtime", "caption-showcase"))
    args = parser.parse_args()
    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    short = _short(out_dir)
    long = _long(out_dir)
    sheet = _contact_sheet(out_dir, [short, long])
    print("short=" + short[0])
    print("long=" + long[0])
    print("sheet=" + sheet)


if __name__ == "__main__":
    main()
