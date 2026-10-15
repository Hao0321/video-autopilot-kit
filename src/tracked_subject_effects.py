"""Tracked subject effects; one implementation behind the compatibility facade."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Callable
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


SHEEN_MATERIALS = {
    "battle_top": {
        "opacity": .62, "band_width": .13, "glow": .018,
        "secondary": .24, "core": .78, "contrast": .11,
    },
    "vehicle_paint": {
        "opacity": .76, "band_width": .09, "glow": .016,
        "secondary": .22, "core": .90, "contrast": .18,
    },
    "glass": {
        "opacity": .68, "band_width": .075, "glow": .030,
        "secondary": .46, "core": .92, "contrast": .08,
    },
    "plastic_product": {
        "opacity": .74, "band_width": .13, "glow": .021,
        "secondary": .25, "core": .91, "contrast": .17,
    },
    "generic_product": {
        "opacity": .72, "band_width": .125, "glow": .020,
        "secondary": .22, "core": .90, "contrast": .16,
    },
}

def _position_pixels(values: list[float], width: int, height: int) -> tuple[float, float]:
    x, y = float(values[0]), float(values[1])
    if max(abs(x), abs(y)) <= 1.5:
        return x * width, y * height
    return x, y

def _lock_center(effect: dict[str, Any], source_time: float,
                 width: int, height: int) -> tuple[float, float]:
    rows = list(effect.get("keyframes") or [])
    if not rows:
        return _position_pixels(effect.get("center", [.5, .53]), width, height)
    rows.sort(key=lambda row: float(row["time"]))
    if source_time <= float(rows[0]["time"]):
        return _position_pixels(rows[0]["center"], width, height)
    if source_time >= float(rows[-1]["time"]):
        return _position_pixels(rows[-1]["center"], width, height)
    for left, right in zip(rows, rows[1:]):
        start, end = float(left["time"]), float(right["time"])
        if start <= source_time <= end:
            progress = (source_time - start) / max(.0001, end - start)
            progress = progress * progress * (3.0 - 2.0 * progress)
            x1, y1 = _position_pixels(left["center"], width, height)
            x2, y2 = _position_pixels(right["center"], width, height)
            return x1 + (x2 - x1) * progress, y1 + (y2 - y1) * progress
    return _position_pixels(rows[-1]["center"], width, height)

def _draw_lock_effect(overlay: Image.Image, effect: dict[str, Any],
                      source_time: float, width: int, height: int) -> None:
    """Draw a restrained arena/object lock overlay; never a transition card."""
    start, end = float(effect.get("start", 0)), float(effect.get("end", 0))
    if not start <= source_time < end:
        return
    center_x, center_y = _lock_center(effect, source_time, width, height)
    raw_radius = float(effect.get("radius", .16))
    radius = raw_radius * min(width, height) if raw_radius <= 1.5 else raw_radius
    local_time = source_time - start
    radius *= 1.0 + .025 * math.sin(local_time * math.tau * 1.7)
    color = tuple(int(value) for value in effect.get("color", [56, 215, 255]))
    line = max(3, round(height * float(effect.get("line_width", .0035))))
    layer = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    box = (round(center_x - radius), round(center_y - radius),
           round(center_x + radius), round(center_y + radius))
    angle = (local_time * float(effect.get("rotation_speed", 82))) % 360
    draw.ellipse(box, outline=(*color, 58), width=max(2, line // 2))
    for offset in (0, 180):
        draw.arc(box, start=angle + offset, end=angle + offset + 58,
                 fill=(*color, 235), width=line)
    bracket = radius * float(effect.get("bracket_length", .24))
    gap = radius * float(effect.get("bracket_gap", .88))
    for side_x, side_y in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        x, y = center_x + side_x * gap, center_y + side_y * gap
        draw.line((x, y, x - side_x * bracket, y), fill=(*color, 220), width=line)
        draw.line((x, y, x, y - side_y * bracket), fill=(*color, 220), width=line)
    glow = layer.filter(ImageFilter.GaussianBlur(max(3, round(height * .006))))
    glow.putalpha(glow.getchannel("A").point(lambda value: round(value * .52)))
    overlay.alpha_composite(glow)
    overlay.alpha_composite(layer)

def _alpha_matte(effect: dict[str, Any], width: int, height: int,
                 frame_box: tuple[int, int, int, int],
                 frame_size: tuple[int, int]) -> Image.Image:
    raw = Image.open(str(effect["matte_path"]))
    source = raw.convert("RGBA")
    alpha = source.getchannel("A") if "A" in raw.getbands() else raw.convert("L")
    if source.size == frame_size:
        left, top, right, bottom = frame_box
        alpha = alpha.crop((left, top, right, bottom))
    if alpha.size != (width, height):
        alpha = alpha.resize((width, height), Image.Resampling.LANCZOS)
    return alpha

def _sequence_matte(effect: dict[str, Any], source_time: float,
                    width: int, height: int,
                    frame_box: tuple[int, int, int, int],
                    frame_size: tuple[int, int]) -> Image.Image:
    fps = float(effect["matte_sequence_fps"])
    sequence_start = float(effect.get("matte_sequence_start", effect.get("start", 0)))
    frame_index = max(0, int(math.floor((source_time - sequence_start) * fps + 1e-6)))
    prefix = str(effect.get("matte_sequence_prefix", "frame_"))
    digits = max(1, int(effect.get("matte_sequence_digits", 6)))
    extension = str(effect.get("matte_sequence_extension", ".png"))
    if not extension.startswith("."):
        extension = "." + extension
    path = Path(str(effect["matte_sequence_dir"])) / f"{prefix}{frame_index:0{digits}d}{extension}"
    if not path.is_file():
        raise RuntimeError(f"missing required roto matte frame: {path}")
    local_effect = dict(effect)
    local_effect["matte_path"] = str(path)
    return _alpha_matte(local_effect, width, height, frame_box, frame_size)

def _verified_sheen_matte(effect: dict[str, Any], width: int, height: int,
                          frame_box: tuple[int, int, int, int],
                          frame_size: tuple[int, int],
                          source_time: float) -> Image.Image:
    shape = str(effect.get("shape", "ellipse"))
    if shape == "alpha":
        matte = _alpha_matte(effect, width, height, frame_box, frame_size)
    elif shape == "sequence":
        matte = _sequence_matte(effect, source_time, width, height, frame_box, frame_size)
    else:
        matte = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(matte)
        inset = max(0.0, min(.35, float(effect.get("matte_inset", .025))))
        box = (round(width * inset), round(height * inset),
               round(width * (1 - inset)), round(height * (1 - inset)))
        if shape == "polygon":
            points = [(round(float(x) * width), round(float(y) * height))
                      for x, y in effect.get("polygon", [])]
            draw.polygon(points, fill=255)
        elif shape == "rectangle":
            radius = round(min(width, height) * float(effect.get("corner_radius", .08)))
            draw.rounded_rectangle(box, radius=radius, fill=255)
        else:
            draw.ellipse(box, fill=255)
    feather = max(1, round(min(width, height) * float(effect.get("matte_feather", .018))))
    return matte.filter(ImageFilter.GaussianBlur(feather))

def _subject_blackout(effect: dict[str, Any], frame: np.ndarray | None,
                      matte_alpha: np.ndarray, projection: np.ndarray,
                      center: float, sigma: float,
                      crop_box: tuple[int, int, int, int]) -> Image.Image | None:
    if str(effect.get("reveal_mode", "sheen_only")) != "black_to_color":
        return None
    left, top, width, height = crop_box
    softness = max(.08, min(1.2, float(effect.get("reveal_softness", .42))))
    edge_sigma = max(1.0, sigma * softness)
    exponent = np.clip((projection - center) / edge_sigma, -24.0, 24.0)
    revealed = 1.0 / (1.0 + np.exp(exponent))
    opacity = max(0.0, min(1.0, float(effect.get("blackout_opacity", 1.0))))
    alpha = np.clip((1.0 - revealed) * matte_alpha * opacity * 255.0, 0, 255).astype(np.uint8)
    if frame is None:
        blackout = Image.new("RGBA", (width, height), (3, 7, 12, 0))
        blackout.putalpha(Image.fromarray(alpha))
        return blackout
    crop = frame[top:top + height, left:left + width]
    grey = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    detail = np.power(grey, .78)
    dark_rgb = np.stack((detail * 20.0, detail * 25.0, detail * 31.0), axis=-1)
    blackout_rgba = np.zeros((height, width, 4), dtype=np.uint8)
    blackout_rgba[..., :3] = np.clip(dark_rgb, 0, 42).astype(np.uint8)[..., ::-1]
    blackout_rgba[..., 3] = alpha
    return Image.fromarray(blackout_rgba, "RGBA")

def _sheen_local_layer(effect: dict[str, Any], material: dict[str, float],
                       band: np.ndarray, optical_core: np.ndarray,
                       matte_alpha: np.ndarray) -> Image.Image:
    alpha = (band * .72 + optical_core * .28) * matte_alpha
    opacity = max(0.0, min(1.0, float(effect.get("opacity", material["opacity"]))))
    core = max(.01, min(1.0, float(effect.get("core", material["core"]))))
    alpha = np.clip(alpha * opacity * core * 255.0, 0, 255).astype(np.uint8)
    warm = np.array(effect.get("warm_color", [255, 246, 220]), dtype=np.float32)
    cool = np.array(effect.get("cool_color", [175, 226, 255]), dtype=np.float32)
    warm_mix = np.clip(optical_core[..., None], 0.0, 1.0)
    rgb = cool[None, None, :] * (1.0 - warm_mix) + warm[None, None, :] * warm_mix
    rgba = np.zeros((*matte_alpha.shape, 4), dtype=np.uint8)
    rgba[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    rgba[..., 3] = alpha
    return Image.fromarray(rgba)

def _draw_sheen_shoulders(overlay: Image.Image, effect: dict[str, Any],
                          material: dict[str, float], projection: np.ndarray,
                          center: float, sigma: float, band: np.ndarray,
                          matte_alpha: np.ndarray, left: int, top: int) -> None:
    contrast = max(0.0, min(.45, float(effect.get("contrast", material["contrast"]))))
    if not contrast:
        return
    shoulder_distance = sigma * float(effect.get("shoulder_distance", 1.42))
    shoulder_sigma = sigma * float(effect.get("shoulder_width", .72))
    shoulder = (
        np.exp(-.5 * ((projection - (center - shoulder_distance)) / shoulder_sigma) ** 2)
        + np.exp(-.5 * ((projection - (center + shoulder_distance)) / shoulder_sigma) ** 2)
    )
    shoulder *= np.clip(1.0 - band * .82, 0.0, 1.0)
    alpha = np.clip(shoulder * matte_alpha * contrast * 255.0, 0, 255).astype(np.uint8)
    shadow = Image.new("RGBA", (matte_alpha.shape[1], matte_alpha.shape[0]), (4, 8, 14, 0))
    shadow.putalpha(Image.fromarray(alpha))
    overlay.alpha_composite(shadow, (left, top))

def _draw_mask_sheen(overlay: Image.Image, effect: dict[str, Any],
                     source_time: float, width: int, height: int,
                     frame: np.ndarray | None = None, *,
                     bbox_resolver: Callable[[dict[str, Any], float, int, int],
                                             tuple[float, float, float, float]]) -> None:
    """Sweep a diagonal highlight only inside a verified subject matte."""
    start, end = float(effect.get("start", 0)), float(effect.get("end", 0))
    if not start <= source_time < end:
        return
    x, y, box_width, box_height = bbox_resolver(effect, source_time, width, height)
    left, top = max(0, round(x)), max(0, round(y))
    local_width = max(4, min(width - left, round(box_width)))
    local_height = max(4, min(height - top, round(box_height)))
    if local_width < 4 or local_height < 4:
        return
    frame_box = (left, top, left + local_width, top + local_height)
    matte = _verified_sheen_matte(
        effect, local_width, local_height, frame_box, (width, height), source_time,
    )
    material = SHEEN_MATERIALS[str(effect.get("material_profile", "generic_product"))]
    progress = max(0.0, min(1.0, (source_time - start) / max(.001, end - start)))
    progress = progress * progress * (3.0 - 2.0 * progress)
    grid_y, grid_x = np.mgrid[0:local_height, 0:local_width].astype(np.float32)
    angle = math.radians(float(effect.get("angle", -28.0)))
    projection = grid_x * math.cos(angle) + grid_y * math.sin(angle)
    minimum, maximum = float(projection.min()), float(projection.max())
    travel_pad = (maximum - minimum) * .20
    center = (minimum - travel_pad) + progress * ((maximum - minimum) + travel_pad * 2)
    sigma = max(
        2.0,
        min(local_width, local_height)
        * float(effect.get("band_width", material["band_width"])) * .38,
    )
    band = np.exp(-.5 * ((projection - center) / sigma) ** 2)
    secondary = float(effect.get("secondary", material["secondary"]))
    band += secondary * np.exp(-.5 * ((projection - (center - sigma * 2.15)) / (sigma * .52)) ** 2)
    matte_alpha = np.asarray(matte, dtype=np.float32) / 255.0
    blackout = _subject_blackout(
        effect, frame, matte_alpha, projection, center, sigma,
        (left, top, local_width, local_height),
    )
    if blackout is not None:
        overlay.alpha_composite(blackout, (left, top))
    optical_core = np.exp(-.5 * ((projection - center) / max(1.0, sigma * .20)) ** 2)
    local = _sheen_local_layer(effect, material, band, optical_core, matte_alpha)
    _draw_sheen_shoulders(
        overlay, effect, material, projection, center, sigma, band,
        matte_alpha, left, top,
    )
    glow_radius = max(1, round(min(local_width, local_height)
                               * float(effect.get("glow", material["glow"]))))
    glow = local.filter(ImageFilter.GaussianBlur(glow_radius))
    glow_alpha = np.asarray(glow.getchannel("A"), dtype=np.float32)
    glow.putalpha(Image.fromarray(
        np.clip(glow_alpha * matte_alpha * .45, 0, 255).astype(np.uint8)
    ))
    overlay.alpha_composite(glow, (left, top))
    overlay.alpha_composite(local, (left, top))
