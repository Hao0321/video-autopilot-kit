# -*- coding: utf-8 -*-
"""Black/white plate routing and alpha conversion for generated VFX.

Keep the source plate.  Use Screen/Add or Multiply when a blend mode is enough;
create straight-alpha media only when compositing, occlusion or tracking needs it.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from PIL import Image


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi"}


def routing(mode: str, *, needs_true_alpha: bool) -> dict:
    if mode == "black":
        return {
            "source_background": "black",
            "default": "screen_or_add",
            "convert_alpha": needs_true_alpha,
            "use_alpha_when": ["object occlusion", "tracked composite", "multi-layer overlap"],
        }
    if mode == "white":
        return {
            "source_background": "white",
            "default": "multiply_for_dark_line_art",
            "convert_alpha": needs_true_alpha,
            "use_alpha_when": ["coloured subject", "tracked composite", "export requires transparency"],
        }
    raise ValueError("mode must be black or white")


def _smooth_alpha(value: float, low: float, high: float) -> float:
    if value <= low:
        return 0.0
    if value >= high:
        return 1.0
    x = (value - low) / max(1e-6, high - low)
    return x * x * (3.0 - 2.0 * x)


def key_image(source: Path, output: Path, *, mode: str,
              threshold: float = .04, softness: float = .14) -> Path:
    image = Image.open(source).convert("RGB")
    result = Image.new("RGBA", image.size)
    keyed = []
    high = min(1.0, threshold + max(.01, softness))
    for red, green, blue in image.getdata():
        if mode == "black":
            distance = max(red, green, blue) / 255.0
            alpha = _smooth_alpha(distance, threshold, high)
            if alpha > .001:
                rgb = tuple(min(255, round(channel / alpha)) for channel in (red, green, blue))
            else:
                rgb = (0, 0, 0)
        elif mode == "white":
            distance = max(255 - red, 255 - green, 255 - blue) / 255.0
            alpha = _smooth_alpha(distance, threshold, high)
            if alpha > .001:
                rgb = tuple(max(0, min(255, round((channel - 255 * (1 - alpha)) / alpha)))
                            for channel in (red, green, blue))
            else:
                rgb = (255, 255, 255)
        else:
            raise ValueError("mode must be black or white")
        keyed.append((*rgb, round(alpha * 255)))
    result.putdata(keyed)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.save(output, optimize=True)
    return output


def video_command(source: Path, output: Path, *, mode: str,
                  threshold: float = .04, softness: float = .14) -> list[str]:
    if mode == "black":
        effect = f"lumakey=threshold=0:tolerance={threshold:.4f}:softness={softness:.4f}"
    elif mode == "white":
        effect = f"colorkey=white:similarity={threshold + softness:.4f}:blend={softness:.4f}"
    else:
        raise ValueError("mode must be black or white")
    return [
        "ffmpeg", "-y", "-i", str(source), "-vf", f"format=rgba,{effect},format=yuva444p10le",
        "-an", "-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuva444p10le",
        str(output),
    ]


def convert(source: Path, output: Path, *, mode: str,
            threshold: float = .04, softness: float = .14) -> Path:
    suffix = source.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return key_image(source, output, mode=mode, threshold=threshold, softness=softness)
    if suffix in VIDEO_SUFFIXES:
        command = video_command(source, output, mode=mode, threshold=threshold, softness=softness)
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if completed.returncode:
            raise RuntimeError((completed.stderr or completed.stdout)[-1200:])
        return output
    raise ValueError("unsupported media type: " + suffix)


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="vfx-keyer-") as temporary:
        root = Path(temporary)
        black = Image.new("RGB", (96, 64), "black")
        for x in range(28, 68):
            for y in range(16, 48):
                black.putpixel((x, y), (255, 110, 20))
        source = root / "black.png"
        output = root / "alpha.png"
        black.save(source)
        key_image(source, output, mode="black")
        result = Image.open(output).convert("RGBA")
        assert result.getpixel((0, 0))[3] == 0
        assert result.getpixel((48, 32))[3] > 250
        assert routing("black", needs_true_alpha=False)["default"] == "screen_or_add"
        assert "prores_ks" in video_command(Path("in.mp4"), Path("out.mov"), mode="white")
    print("vfx_keyer self-test GREEN")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Route or key black/white VFX plates")
    sub = parser.add_subparsers(dest="command", required=True)
    route = sub.add_parser("route")
    route.add_argument("--mode", choices=("black", "white"), required=True)
    route.add_argument("--true-alpha", action="store_true")
    key = sub.add_parser("convert")
    key.add_argument("source")
    key.add_argument("output")
    key.add_argument("--mode", choices=("black", "white"), required=True)
    key.add_argument("--threshold", type=float, default=.04)
    key.add_argument("--softness", type=float, default=.14)
    sub.add_parser("selftest")
    args = parser.parse_args(argv)
    if args.command == "route":
        print(json.dumps(routing(args.mode, needs_true_alpha=args.true_alpha), ensure_ascii=False, indent=2))
        return 0
    if args.command == "convert":
        print(convert(Path(args.source), Path(args.output), mode=args.mode,
                      threshold=args.threshold, softness=args.softness))
        return 0
    self_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
