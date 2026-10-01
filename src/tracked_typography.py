# -*- coding: utf-8 -*-
"""Editable high-energy typography plates for tracked video graphics."""
from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from platform_compat import find_cjk_font

try:
    from project_paths import asset_path
except ImportError:  # imported from a caller that has not added the skill directory yet
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from project_paths import asset_path

FONT_DIR = asset_path("fonts", "_active")
CURRENCY_RE = re.compile(
    r"(?:[$＄€£¥￥]\s*[\d,.]+)|(?:[\d,.]+\s*(?:美元|美金|萬元|萬|億元|億|元|塊|million|billion|m|b))",
    re.I,
)
CJK_RE = re.compile(r"[\u3400-\u9fff]")

TEXT_PROFILES: dict[str, dict[str, Any]] = {
    "neon_value_green": {
        "fill_top": (245, 255, 196), "fill_bottom": (112, 255, 66),
        "outline": (24, 55, 22), "extrusion": (8, 22, 10),
        "glow": (78, 255, 58), "highlight": (247, 255, 220),
        "scanlines": True, "font_scale": .105, "depth": .095,
    },
    "neon_value_cyan": {
        "fill_top": (245, 255, 255), "fill_bottom": (72, 218, 255),
        "outline": (13, 36, 65), "extrusion": (6, 15, 29),
        "glow": (47, 199, 255), "highlight": (255, 255, 255),
        "scanlines": True, "font_scale": .100, "depth": .090,
    },
    "price_white": {
        "fill_top": (255, 255, 255), "fill_bottom": (238, 238, 231),
        "outline": (8, 8, 10), "extrusion": (0, 0, 0),
        "glow": (255, 255, 255), "highlight": (255, 255, 255),
        "scanlines": False, "font_scale": .105, "depth": .075,
    },
    "impact_gold": {
        "fill_top": (255, 255, 224), "fill_bottom": (255, 184, 38),
        "outline": (61, 33, 7), "extrusion": (24, 12, 3),
        "glow": (255, 191, 36), "highlight": (255, 255, 244),
        "scanlines": False, "font_scale": .105, "depth": .095,
    },
    "warning_red": {
        "fill_top": (255, 244, 232), "fill_bottom": (255, 67, 86),
        "outline": (72, 8, 18), "extrusion": (29, 3, 9),
        "glow": (255, 42, 75), "highlight": (255, 255, 245),
        "scanlines": True, "font_scale": .100, "depth": .092,
    },
}


def font(text: str, size: int) -> ImageFont.FreeTypeFont:
    preferred = FONT_DIR / ("Huninn-Regular.ttf" if CJK_RE.search(text) else "Fredoka-SemiBold.ttf")
    path = str(preferred) if preferred.is_file() else find_cjk_font(
        ["Black", "Bold", "Semibold"] if not CJK_RE.search(text) else ["Bold", "TC", "CJK"]
    )
    if not path:
        raise FileNotFoundError(
            "missing redistributable/system CJK font; install Noto Sans CJK/TC or add a licensed font under assets/fonts/_active"
        )
    return ImageFont.truetype(str(path), max(12, int(size)))


def gradient(size: tuple[int, int], top: tuple[int, int, int],
             bottom: tuple[int, int, int]) -> Image.Image:
    height = max(1, size[1])
    row = np.zeros((height, 1, 4), dtype=np.uint8)
    for y in range(height):
        progress = y / max(1, height - 1)
        row[y, 0, :3] = [round(a + (b - a) * progress) for a, b in zip(top, bottom)]
        row[y, 0, 3] = 255
    return Image.fromarray(np.repeat(row, size[0], axis=1))


def rgba_from_mask(size: tuple[int, int], color: tuple[int, int, int],
                   mask: Image.Image, opacity: int = 255) -> Image.Image:
    layer = Image.new("RGBA", size, (*color, 0))
    if opacity != 255:
        mask = mask.point(lambda value: value * opacity // 255)
    layer.putalpha(mask)
    return layer


def _shift(mask: Image.Image, dx: int, dy: int) -> Image.Image:
    output = Image.new("L", mask.size, 0)
    output.paste(mask, (int(dx), int(dy)))
    return output


def render_text_plate(text: str, profile_name: str, font_px: int,
                      *, max_width: int | None = None) -> Image.Image:
    """Render an original editable high-energy text plate with alpha."""
    if profile_name not in TEXT_PROFILES:
        raise ValueError("unknown text profile %r" % profile_name)
    text = str(text or "").strip()
    if not text:
        raise ValueError("text must not be empty")
    profile = TEXT_PROFILES[profile_name]
    text_font = font(text, font_px)
    outline = max(4, round(font_px * .055))
    depth = max(4, round(font_px * profile["depth"]))
    glow_pad = max(18, round(font_px * .30))
    bbox = text_font.getbbox(text, stroke_width=outline)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    width, height = text_w + glow_pad * 2 + depth, text_h + glow_pad * 2 + depth
    x, y = glow_pad - bbox[0], glow_pad - bbox[1]
    inner = Image.new("L", (width, height), 0)
    ImageDraw.Draw(inner).text((x, y), text, font=text_font, fill=255)
    if CJK_RE.search(text):
        inner = inner.filter(ImageFilter.MaxFilter(max(3, (round(font_px * .035) // 2) * 2 + 1)))
    stroke = inner.filter(ImageFilter.MaxFilter(outline * 2 + 1))
    plate = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    for radius, opacity in ((font_px * .22, 55), (font_px * .11, 90), (font_px * .045, 120)):
        halo = stroke.filter(ImageFilter.GaussianBlur(max(1, radius)))
        plate.alpha_composite(rgba_from_mask(plate.size, profile["glow"], halo, opacity))
    for offset in range(depth, 0, -2):
        plate.alpha_composite(rgba_from_mask(
            plate.size, profile["extrusion"], _shift(stroke, offset, offset), 255))
    plate.alpha_composite(rgba_from_mask(plate.size, profile["outline"], stroke, 255))
    fill = gradient(plate.size, profile["fill_top"], profile["fill_bottom"])
    fill.putalpha(inner)
    plate.alpha_composite(fill)
    upper = ImageChops.subtract(inner, _shift(inner, 0, max(2, font_px // 32)))
    lower = ImageChops.subtract(inner, _shift(inner, 0, -max(2, font_px // 32)))
    plate.alpha_composite(rgba_from_mask(plate.size, profile["highlight"], upper, 205))
    plate.alpha_composite(rgba_from_mask(plate.size, profile["outline"], lower, 105))
    if profile["scanlines"]:
        lines = Image.new("L", plate.size, 0)
        draw = ImageDraw.Draw(lines)
        step = max(5, font_px // 16)
        for line_y in range(0, height, step):
            draw.line((0, line_y, width, line_y), fill=165, width=max(1, round(step * .34)))
        lines = ImageChops.multiply(lines, inner)
        plate.alpha_composite(rgba_from_mask(plate.size, profile["outline"], lines, 92))
    if max_width and plate.width > max_width:
        ratio = max_width / plate.width
        plate = plate.resize((max_width, max(1, round(plate.height * ratio))),
                             Image.Resampling.LANCZOS)
    return plate


def _ease_out_back(progress: float) -> float:
    progress = max(0.0, min(1.0, progress)) - 1.0
    return 1.0 + 2.70158 * progress ** 3 + 1.70158 * progress ** 2


def animate_text_plate(base: Image.Image, local_t: float, duration: float,
                       profile_name: str) -> Image.Image:
    """Pop/settle, breathe and light-sweep animation for one plate."""
    del profile_name  # Animation is profile-neutral; retained for stable public API.
    enter = min(1.0, max(0.0, local_t / .30))
    scale = .68 + .32 * _ease_out_back(enter)
    if local_t > .30:
        scale *= 1.0 + .012 * math.sin(local_t * math.tau * 1.25)
    opacity = min(1.0, max(0.0, local_t / .09))
    if duration > 0 and local_t > duration - .16:
        opacity *= max(0.0, (duration - local_t) / .16)
    resized = base.resize((max(1, round(base.width * scale)),
                           max(1, round(base.height * scale))), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", base.size, (0, 0, 0, 0))
    canvas.alpha_composite(resized, ((base.width - resized.width) // 2,
                                     (base.height - resized.height) // 2))
    alpha = canvas.getchannel("A")
    sweep_x = round(-base.width * .25 + base.width * 1.5 * ((local_t * .55) % 1.0))
    band = Image.new("L", base.size, 0)
    ImageDraw.Draw(band).polygon([
        (sweep_x - base.width * .10, 0), (sweep_x, 0),
        (sweep_x + base.width * .16, base.height), (sweep_x + base.width * .06, base.height),
    ], fill=120)
    band = ImageChops.multiply(
        band.filter(ImageFilter.GaussianBlur(max(2, base.width * .012))), alpha)
    canvas.alpha_composite(rgba_from_mask(base.size, (255, 255, 255), band, 72))
    if opacity < 1:
        canvas.putalpha(canvas.getchannel("A").point(lambda value: round(value * opacity)))
    return canvas


def animate_identity_plate(base: Image.Image, local_t: float, duration: float) -> Image.Image:
    """Restrained tracked-label motion: quick settle, one sheen, no breathing.

    Identity labels need to feel attached to a photographed object.  A large
    elastic pop and perpetual scale pulse make the typography look like a
    floating sticker, so this path uses a short 94→100% settle and a single
    material glint during the entrance only.
    """
    enter = min(1.0, max(0.0, local_t / .18))
    eased = 1.0 - (1.0 - enter) ** 3
    scale = .94 + .06 * eased
    opacity = min(1.0, max(0.0, local_t / .07))
    if duration > 0 and local_t > duration - .12:
        opacity *= max(0.0, (duration - local_t) / .12)
    resized = base.resize((max(1, round(base.width * scale)),
                           max(1, round(base.height * scale))), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", base.size, (0, 0, 0, 0))
    canvas.alpha_composite(resized, ((base.width - resized.width) // 2,
                                     (base.height - resized.height) // 2))
    if local_t <= .34:
        alpha = canvas.getchannel("A")
        sweep_x = round(-base.width * .18 + base.width * 1.36 * min(1.0, local_t / .34))
        band = Image.new("L", base.size, 0)
        ImageDraw.Draw(band).polygon([
            (sweep_x - base.width * .07, 0), (sweep_x, 0),
            (sweep_x + base.width * .11, base.height),
            (sweep_x + base.width * .04, base.height),
        ], fill=118)
        band = ImageChops.multiply(
            band.filter(ImageFilter.GaussianBlur(max(2, base.width * .009))), alpha)
        canvas.alpha_composite(rgba_from_mask(base.size, (255, 255, 255), band, 66))
    if opacity < 1:
        canvas.putalpha(canvas.getchannel("A").point(lambda value: round(value * opacity)))
    return canvas
