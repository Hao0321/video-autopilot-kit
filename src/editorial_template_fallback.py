# -*- coding: utf-8 -*-
"""Redistributable procedural fallback for Bright Editorial templates.

The optional Motion Kit contains the full atlas renderer. This keeps the public
core importable and useful before that large, separately licensed pack is added.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from platform_compat import find_cjk_font

ASPECTS = {"landscape": (1920, 1080), "portrait": (1080, 1920)}
ROLES = ("background", "hook", "chapter", "quote", "stat", "compare", "steps",
         "lower_third", "end_card", "thumbnail")
STYLES = {
    "cobalt_poetry": {"label": "COBALT / POETRY", "base": (24, 66, 225), "ink": (250, 250, 244), "accent": (255, 236, 70), "second": (94, 225, 255)},
    "shape_play": {"label": "SHAPE / PLAY", "base": (249, 244, 232), "ink": (15, 16, 19), "accent": (255, 81, 47), "second": (35, 100, 238)},
    "lime_aura": {"label": "LIME / AURA", "base": (69, 196, 81), "ink": (250, 251, 239), "accent": (244, 249, 66), "second": (226, 255, 230)},
    "night_signal": {"label": "NIGHT / SIGNAL", "base": (10, 11, 16), "ink": (250, 250, 247), "accent": (230, 66, 207), "second": (53, 220, 237)},
    "cyan_lab": {"label": "CYAN / LAB", "base": (242, 250, 248), "ink": (5, 18, 22), "accent": (21, 78, 235), "second": (35, 226, 190)},
    "ai_chalk_grid": {"label": "AI / CHALK", "base": (23, 25, 29), "ink": (248, 247, 240), "accent": (255, 215, 62), "second": (91, 224, 220)},
    "travel_journal": {"label": "TRAVEL / JOURNAL", "base": (84, 177, 219), "ink": (251, 250, 240), "accent": (255, 233, 69), "second": (20, 78, 104)},
    "food_pop": {"label": "FOOD / POP", "base": (243, 193, 7), "ink": (255, 252, 239), "accent": (237, 66, 44), "second": (23, 76, 188)},
    "food_editorial": {"label": "FOOD / EDITORIAL", "base": (248, 244, 234), "ink": (19, 13, 12), "accent": (213, 24, 27), "second": (91, 17, 16)},
    "food_steam": {"label": "FOOD / STEAM", "base": (111, 48, 13), "ink": (255, 243, 215), "accent": (255, 151, 25), "second": (255, 210, 87)},
    "food_heritage": {"label": "FOOD / HERITAGE", "base": (247, 230, 192), "ink": (18, 44, 64), "accent": (194, 38, 31), "second": (25, 65, 88)},
    "matcha_fresh": {"label": "MATCHA / FRESH", "base": (64, 108, 39), "ink": (255, 250, 225), "accent": (183, 224, 49), "second": (247, 245, 220)},
    "brush_rush": {"label": "BRUSH / RUSH", "base": (181, 243, 216), "ink": (20, 30, 104), "accent": (242, 65, 62), "second": (34, 96, 228)},
    "festival_block": {"label": "FESTIVAL / BLOCK", "base": (21, 50, 226), "ink": (255, 255, 247), "accent": (255, 47, 161), "second": (99, 238, 197)},
    "electric_lab": {"label": "ELECTRIC / LAB", "base": (9, 12, 14), "ink": (250, 250, 241), "accent": (244, 232, 16), "second": (14, 218, 228)},
    "holo_future": {"label": "HOLO / FUTURE", "base": (247, 248, 250), "ink": (19, 21, 26), "accent": (133, 67, 241), "second": (27, 202, 232)},
    "morph_prism": {"label": "MORPH / PRISM", "base": (248, 248, 250), "ink": (52, 32, 130), "accent": (242, 57, 149), "second": (26, 187, 229)},
}
TOPIC_STYLE = {
    "ai": "ai_chalk_grid", "teaching": "ai_chalk_grid", "education": "cobalt_poetry",
    "food": "food_pop", "cafe": "food_editorial", "travel": "travel_journal",
    "toy": "shape_play", "product": "shape_play", "diy": "shape_play",
    "game": "night_signal", "music": "festival_block", "event": "festival_block",
    "technology": "electric_lab", "sports": "electric_lab", "business": "cyan_lab",
    "interview": "lime_aura", "documentary": "cobalt_poetry", "general": "shape_play",
}
TEMPLATE_ROOT = Path(__file__).resolve().parent.parent / "templates" / "rendered"
MANIFEST_PATH = TEMPLATE_ROOT / "manifest.json"
CATALOG_PATH = TEMPLATE_ROOT / "catalog.jpg"


def infer_topic(text: str = "") -> str:
    source = str(text or "").lower()
    rules = {
        "ai": ("ai", "人工智慧", "chatgpt", "claude", "教學"),
        "food": ("美食", "餐廳", "料理", "咖啡", "甜點", "food"),
        "travel": ("旅遊", "景點", "旅行", "travel", "vlog"),
        "toy": ("玩具", "陀螺", "開箱", "toy", "unbox"),
        "game": ("遊戲", "game", "gaming"),
        "music": ("音樂", "festival", "music"),
        "interview": ("訪談", "對談", "podcast", "interview"),
        "business": ("商業", "創業", "行銷", "business"),
    }
    scores = {key: sum(source.count(word) for word in words) for key, words in rules.items()}
    best = max(scores, key=scores.get) if scores else "general"
    return best if scores.get(best, 0) else "general"


def resolve_style(topic: str = "general", hint: str | None = None) -> dict:
    explicit = str(hint or "").strip().lower()
    if explicit and explicit not in ("auto", "none"):
        if explicit not in STYLES:
            raise ValueError("unknown style: " + explicit)
        key = explicit
    else:
        raw = str(topic or "general").lower()
        if any(word in raw for word in ("抹茶", "冰淇淋", "matcha")):
            key = "matcha_fresh"
        elif any(word in raw for word in ("傳統", "古早", "海鮮", "heritage")):
            key = "food_heritage"
        elif any(word in raw for word in ("炸", "烤", "熱騰騰", "fried", "grill")):
            key = "food_steam"
        else:
            domain = raw if raw in TOPIC_STYLE else infer_topic(raw)
            key = TOPIC_STYLE.get(domain, "shape_play")
    return {"key": key, **STYLES[key]}


def _font(size: int, bold: bool = False):
    path = find_cjk_font(["Black", "Bold", "bd"] if bold else None)
    return ImageFont.truetype(path, max(10, int(size))) if path else ImageFont.load_default()


def _fit_text(draw, text: str, max_width: int, start_size: int, minimum: int = 28):
    for size in range(start_size, minimum - 1, -4):
        font = _font(size, True)
        if draw.textbbox((0, 0), text, font=font)[2] <= max_width:
            return font
    return _font(minimum, True)


def _validated_media_paths(media_paths) -> tuple[str, ...]:
    """Return Pillow-readable media paths or fail before rendering succeeds.

    The fallback supports one to four images for hook/thumbnail photo windows.
    Empty input keeps the procedural card. Supplied missing, blank, excessive,
    or non-image inputs are errors instead of being silently omitted.
    """
    if media_paths is None:
        return ()
    raw = ((media_paths,) if isinstance(media_paths, (str, os.PathLike))
           else tuple(media_paths))
    if not raw:
        return ()
    if len(raw) > 4:
        raise ValueError("editorial templates support at most four media images")
    normalized = []
    for value in raw:
        try:
            path = os.fspath(value)
        except TypeError as exc:
            raise TypeError("editorial media paths must be path-like") from exc
        if not path:
            raise ValueError("editorial media paths must not be empty")
        if not os.path.isfile(path):
            raise FileNotFoundError("editorial media path does not name a file")
        try:
            with Image.open(path) as source:
                source.verify()
        except OSError as exc:
            raise ValueError("editorial media must be a Pillow-readable image") from exc
        normalized.append(path)
    return tuple(normalized)


def _composite_media(im: Image.Image, media_paths, box, radius: int, outline) -> int:
    paths = _validated_media_paths(media_paths)
    if not paths:
        return 0
    x0, y0, x1, y1 = map(int, box)
    width, height = max(1, x1 - x0), max(1, y1 - y0)
    gap = max(8, min(width, height) // 35)
    if len(paths) == 1:
        cells = ((x0, y0, x1, y1),)
    elif width >= height:
        cell_width = (width - gap * (len(paths) - 1)) // len(paths)
        cells = tuple((x0 + index * (cell_width + gap), y0,
                       x0 + index * (cell_width + gap) + cell_width, y1)
                      for index in range(len(paths)))
    else:
        cell_height = (height - gap * (len(paths) - 1)) // len(paths)
        cells = tuple((x0, y0 + index * (cell_height + gap), x1,
                       y0 + index * (cell_height + gap) + cell_height)
                      for index in range(len(paths)))
    for path, (left, top, right, bottom) in zip(paths, cells):
        cell_size = (max(1, right - left), max(1, bottom - top))
        with Image.open(path) as source:
            source = ImageOps.exif_transpose(source).convert("RGBA")
        if source.getchannel("A").getextrema()[0] < 250:
            photo = ImageOps.contain(
                source, cell_size, method=Image.Resampling.LANCZOS)
            position = (left + (cell_size[0] - photo.width) // 2,
                        top + (cell_size[1] - photo.height) // 2)
            im.paste(photo, position, photo)
        else:
            focus_y = (.30 if source.width * cell_size[1] < source.height * cell_size[0]
                       else .50)
            photo = ImageOps.fit(
                source.convert("RGB"), cell_size, method=Image.Resampling.LANCZOS,
                centering=(0.5, focus_y))
            mask = Image.new("L", cell_size, 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                (0, 0, cell_size[0] - 1, cell_size[1] - 1), radius=radius, fill=255)
            im.paste(photo, (left, top), mask)
        ImageDraw.Draw(im).rounded_rectangle(
            (left, top, right, bottom), radius=radius, outline=outline, width=3)
    return len(paths)


def render_background(topic: str = "general", size=(1920, 1080), style_hint=None, seed=0):
    style = resolve_style(topic, style_hint)
    width, height = size
    im = Image.new("RGB", size, style["base"])
    draw = ImageDraw.Draw(im, "RGBA")
    unit = min(width, height)
    token = int(hashlib.sha1(str(seed).encode("utf-8")).hexdigest()[:8], 16)
    for index, color in enumerate((style["accent"], style["second"], style["ink"])):
        radius = int(unit * (0.20 + index * 0.10))
        x = int((0.05 + ((token >> (index * 5)) & 15) / 20) * width)
        y = int((0.05 + ((token >> (index * 7 + 3)) & 15) / 20) * height)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*color, 38 + index * 10))
    step = max(48, unit // 14)
    for x in range(0, width, step):
        draw.line((x, 0, x, height), fill=(*style["ink"], 18), width=1)
    for y in range(0, height, step):
        draw.line((0, y, width, y), fill=(*style["ink"], 18), width=1)
    return im


def render_template(role: str, title: str = "Title", subtitle: str = "", topic: str = "general",
                    aspect: str = "landscape", style_hint=None, value="87%", items=(),
                    media_paths=(), seed=0, debug_labels: bool = False, **_kwargs):
    if role not in ROLES or aspect not in ASPECTS:
        raise ValueError("unknown template role or aspect: %s/%s" % (role, aspect))
    media_paths = _validated_media_paths(media_paths)
    if media_paths and role not in ("hook", "thumbnail"):
        raise ValueError("editorial media is supported only for hook and thumbnail roles")
    style = resolve_style(topic, style_hint)
    width, height = ASPECTS[aspect]
    im = render_background(topic, (width, height), style_hint, seed or (role, title))
    draw = ImageDraw.Draw(im, "RGBA")
    margin = int(width * 0.075)
    draw.rounded_rectangle((margin, margin, width - margin, height - margin), radius=34,
                           fill=(*style["base"], 215), outline=(*style["ink"], 125), width=3)
    media_count = 0
    if media_paths:
        if width >= height:
            photo_box = (width * .55, margin * 1.25,
                         width - margin * 1.25, height - margin * 1.25)
        else:
            photo_box = (margin * 1.25, height * .12,
                         width - margin * 1.25, height * .40)
        media_count = _composite_media(
            im, media_paths, photo_box, radius=max(18, min(width, height) // 28),
            outline=(*style["ink"], 210))
        draw = ImageDraw.Draw(im, "RGBA")
    # Internal role/style labels are useful in catalogs but must never leak into
    # a production render (for example "HOOK" or "SHAPE / PLAY").
    if debug_labels:
        draw.text((margin * 1.25, margin * 1.25), style["label"],
                  font=_font(max(22, width // 58), True), fill=style["ink"])
    headline = str(value) if role == "stat" else str(title)
    headline_size = int(min(width, height) * (0.17 if role in ("hook", "thumbnail", "stat") else 0.12))
    text_width = int(width * (0.40 if media_count and width >= height else 0.76))
    font = _fit_text(draw, headline, text_width, headline_size)
    if role == "lower_third":
        text_y = int(height * .72)
    elif media_count and height > width:
        text_y = int(height * .52)
    else:
        text_y = int(height * .42)
    draw.text((margin * 1.25, text_y), headline, font=font, fill=style["ink"], anchor="lm")
    rule_end = width * (.44 if media_count and width >= height else .53)
    draw.rectangle((margin * 1.25, text_y + int(height * .09), rule_end,
                    text_y + int(height * .105)), fill=style["accent"])
    secondary = subtitle or ("  /  ".join(str(item) for item in items[:3]))
    if secondary:
        draw.text((margin * 1.25, text_y + int(height * .16)), secondary,
                  font=_font(max(24, width // 32)), fill=style["ink"], anchor="lm")
    return im


def pick(topic: str, role: str, aspect: str = "landscape") -> dict:
    style = resolve_style(topic)
    return {"topic": infer_topic(topic), "role": role, "aspect": aspect,
            "style": style["key"], "path": None, "renderer": "procedural-fallback"}


def build_library(*_args, **_kwargs):
    return []


def build_catalog(*_args, **_kwargs):
    return str(CATALOG_PATH)


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="editorial-fallback-") as temporary:
        media_path = os.path.join(temporary, "face.png")
        Image.new("RGB", (320, 520), (238, 37, 122)).save(media_path)
        without_media = render_template(
            "hook", "媒體契約", "TEST", aspect="portrait", seed=77)
        with_media = render_template(
            "hook", "媒體契約", "TEST", aspect="portrait",
            media_paths=(media_path,), seed=77)
        assert without_media.tobytes() != with_media.tobytes()
        try:
            render_template(
                "hook", "媒體契約", aspect="portrait",
                media_paths=(os.path.join(temporary, "missing.png"),), seed=77)
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("invalid editorial media path must fail closed")
    print("editorial template fallback self-test GREEN")


if __name__ == "__main__":
    self_test()
