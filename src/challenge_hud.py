# -*- coding: utf-8 -*-
"""Stateful top-left challenge ledger renderer for tracked graphics."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

from tracked_typography import font, gradient, rgba_from_mask


def _rounded_gradient(size: tuple[int, int], radius: int,
                      top: tuple[int, int, int, int], bottom: tuple[int, int, int, int],
                      outline: tuple[int, int, int, int], outline_width: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    layer = gradient(size, top[:3], bottom[:3])
    layer.putalpha(mask.point(lambda value: value * top[3] // 255))
    ImageDraw.Draw(layer, "RGBA").rounded_rectangle(
        (outline_width // 2, outline_width // 2,
         size[0] - 1 - outline_width // 2, size[1] - 1 - outline_width // 2),
        radius=radius, outline=outline, width=outline_width)
    return layer


def _thumbnail(item: dict[str, Any], size: int) -> Image.Image:
    path = Path(str(item.get("thumbnail", "")))
    if path.is_file():
        source = Image.open(path).convert("RGBA")
        source.thumbnail((size, size), Image.Resampling.LANCZOS)
        thumb = Image.new("RGBA", (size, size), (10, 24, 38, 255))
        thumb.alpha_composite(source, ((size - source.width) // 2,
                                       (size - source.height) // 2))
    else:
        accent = tuple(item.get("accent", [76, 218, 255]))
        thumb = Image.new("RGBA", (size, size), (*accent, 255))
        draw = ImageDraw.Draw(thumb, "RGBA")
        draw.ellipse((size * .18, size * .18, size * .82, size * .82),
                     fill=(8, 18, 31, 230))
        glyph = str(item.get("icon", "●"))[:1]
        glyph_font = font(glyph, round(size * .52))
        box = draw.textbbox((0, 0), glyph, font=glyph_font)
        draw.text(((size - (box[2] - box[0])) / 2 - box[0],
                   (size - (box[3] - box[1])) / 2 - box[1]),
                  glyph, font=glyph_font, fill="white")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size - 1, size - 1), radius=size // 4, fill=255)
    thumb.putalpha(mask)
    return thumb


def _active_index(hud: dict[str, Any], source_time: float) -> int:
    index = int(hud.get("active_index", 0))
    for event in sorted(hud.get("events", []), key=lambda row: float(row.get("time", 0))):
        if source_time >= float(event.get("time", 0)):
            index = int(event.get("active_index", index))
    items = hud.get("items") or []
    return min(max(0, index), max(0, len(items) - 1))


def _fit_label_font(draw: ImageDraw.ImageDraw, label: str, *, preferred_size: int,
                    minimum_size: int, max_width: int, stroke_width: int):
    """Return a font/bbox pair that cannot overflow the HUD capsule."""
    size = max(minimum_size, preferred_size)
    while True:
        label_font = font(label, size)
        bbox = draw.textbbox((0, 0), label, font=label_font, stroke_width=stroke_width)
        if bbox[2] - bbox[0] <= max_width or size <= minimum_size:
            return label_font, bbox
        size = max(minimum_size, size - max(1, round(preferred_size * .06)))


def render_challenge_hud(canvas_size: tuple[int, int], hud: dict[str, Any],
                         source_time: float) -> Image.Image:
    """Render a current badge or vertical challenge ledger at top-left."""
    width, height = canvas_size
    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    items = list(hud.get("items") or [])
    if not items:
        return canvas
    active = _active_index(hud, source_time)
    mode = str(hud.get("mode", "current_badge"))
    unit = min(width / 1080, height / 1080) * float(hud.get("scale", 1.0))

    def axis(value: Any, extent: int, fallback: float) -> int:
        number = float(fallback if value is None else value)
        return round(number * extent) if 0 <= number <= 1.5 else round(number * unit)

    left, top = axis(hud.get("left"), width, 30), axis(hud.get("top"), height, 28)
    active_h, inactive_h = round(76 * unit), round(48 * unit)
    active_w, inactive_w = round(316 * unit), round(220 * unit)
    gap = round(8 * unit)
    rows = [active] if mode == "current_badge" else list(range(len(items)))
    y = top
    for index in rows:
        is_active = index == active
        row_h, row_w = (active_h, active_w) if is_active else (inactive_h, inactive_w)
        cyan = tuple(hud.get("accent", [63, 207, 255]))
        glow = Image.new("L", canvas.size, 0)
        ImageDraw.Draw(glow).rounded_rectangle(
            (left, y, left + row_w, y + row_h), radius=row_h // 3,
            fill=190 if is_active else 70)
        glow = glow.filter(ImageFilter.GaussianBlur(max(3, round(12 * unit))))
        canvas.alpha_composite(rgba_from_mask(
            canvas.size, cyan, glow, 120 if is_active else 45))
        capsule = _rounded_gradient(
            (row_w, row_h), row_h // 3,
            (26, 62, 91, 235 if is_active else 205),
            (7, 17, 31, 240 if is_active else 210),
            (*cyan, 235 if is_active else 105),
            max(1, round((3 if is_active else 1) * unit)),
        )
        thumb_size = row_h - round(10 * unit)
        capsule.alpha_composite(_thumbnail(items[index], thumb_size),
                                (round(5 * unit), (row_h - thumb_size) // 2))
        draw = ImageDraw.Draw(capsule, "RGBA")
        tx = thumb_size + round(18 * unit)
        label = str(items[index].get("label", ""))
        preferred_size = round((36 if is_active else 24) * unit)
        stroke_width = max(1, round(2 * unit))
        label_font, bbox = _fit_label_font(
            draw, label,
            preferred_size=preferred_size,
            minimum_size=max(12, round((18 if is_active else 14) * unit)),
            max_width=max(20, row_w - tx - round(12 * unit)),
            stroke_width=stroke_width,
        )
        ty = (row_h - (bbox[3] - bbox[1])) / 2 - bbox[1]
        draw.text((tx + round(3 * unit), ty + round(4 * unit)), label,
                  font=label_font, fill=(0, 0, 0, 195),
                  stroke_width=stroke_width, stroke_fill=(0, 0, 0, 180))
        draw.text((tx, ty), label, font=label_font, fill=(255, 255, 255, 255),
                  stroke_width=stroke_width, stroke_fill=(6, 13, 23, 255))
        if index < active:
            mark_r = round(10 * unit)
            draw.ellipse((row_w - mark_r * 2 - round(10 * unit), row_h / 2 - mark_r,
                          row_w - round(10 * unit), row_h / 2 + mark_r),
                         fill=(72, 255, 149, 230))
            draw.text((row_w - mark_r * 2 - round(7 * unit),
                       row_h / 2 - mark_r * 1.15), "✓",
                      font=font("✓", round(14 * unit)), fill=(4, 31, 20, 255))
        canvas.alpha_composite(capsule, (left, y))
        y += row_h + gap
    return canvas
