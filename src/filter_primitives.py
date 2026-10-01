# -*- coding: utf-8 -*-
"""Frame-local primitives for Hao Filter Library.

These functions are deterministic and deliberately contain no file I/O.  The
runtime owns decoding/muxing while this module owns pixels, masks and easing.
"""
from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def smoothstep(value: float) -> float:
    x = clamp01(value)
    return x * x * (3.0 - 2.0 * x)


def fit_cover(frame: np.ndarray, width: int, height: int) -> np.ndarray:
    """Resize and centre-crop without stretching."""
    source_h, source_w = frame.shape[:2]
    scale = max(width / max(1, source_w), height / max(1, source_h))
    resized = cv2.resize(frame, (max(width, round(source_w * scale)),
                                 max(height, round(source_h * scale))),
                         interpolation=cv2.INTER_LANCZOS4)
    y = max(0, (resized.shape[0] - height) // 2)
    x = max(0, (resized.shape[1] - width) // 2)
    return resized[y:y + height, x:x + width].copy()


def blend(base: np.ndarray, effected: np.ndarray, strength: float) -> np.ndarray:
    return cv2.addWeighted(base, 1.0 - clamp01(strength), effected,
                           clamp01(strength), 0.0)


def _fit_material(material: np.ndarray | None, frame: np.ndarray) -> np.ndarray | None:
    if material is None or not isinstance(material, np.ndarray) or material.size == 0:
        return None
    if material.ndim == 2:
        material = cv2.cvtColor(material, cv2.COLOR_GRAY2BGR)
    return fit_cover(material, frame.shape[1], frame.shape[0])


def _screen(base: np.ndarray, plate: np.ndarray, strength: float) -> np.ndarray:
    a = base.astype(np.float32) / 255.0
    b = plate.astype(np.float32) / 255.0
    screened = 1.0 - (1.0 - a) * (1.0 - b)
    return blend(base, np.clip(screened * 255.0, 0, 255).astype(np.uint8), strength)


def _multiply(base: np.ndarray, plate: np.ndarray, strength: float) -> np.ndarray:
    a = base.astype(np.float32) / 255.0
    b = plate.astype(np.float32) / 255.0
    multiplied = a * (0.36 + b * 0.64)
    return blend(base, np.clip(multiplied * 255.0, 0, 255).astype(np.uint8), strength)


def _gray_bgr(frame: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def _halftone(frame: np.ndarray, cell: int = 9) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    small_w = max(1, frame.shape[1] // cell)
    small_h = max(1, frame.shape[0] // cell)
    values = cv2.resize(gray, (small_w, small_h), interpolation=cv2.INTER_AREA)
    canvas = np.full(gray.shape, 245, dtype=np.uint8)
    yy, xx = np.ogrid[:cell, :cell]
    centre = (cell - 1) / 2.0
    distances = np.sqrt((xx - centre) ** 2 + (yy - centre) ** 2)
    for y in range(small_h):
        y0 = y * cell
        if y0 >= canvas.shape[0]:
            break
        for x in range(small_w):
            x0 = x * cell
            if x0 >= canvas.shape[1]:
                break
            radius = (1.0 - float(values[y, x]) / 255.0) * cell * 0.52
            tile = (distances <= radius).astype(np.uint8) * 235
            h = min(cell, canvas.shape[0] - y0)
            w = min(cell, canvas.shape[1] - x0)
            canvas[y0:y0 + h, x0:x0 + w] -= tile[:h, :w]
    return cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)


def _bloom(frame: np.ndarray, sigma: float = 10.0, threshold: int = 175) -> np.ndarray:
    bright = np.maximum(frame.astype(np.int16) - threshold, 0).astype(np.uint8)
    blur = cv2.GaussianBlur(bright, (0, 0), sigmaX=max(1.0, sigma))
    return cv2.addWeighted(frame, 1.0, blur, 0.7, 0.0)


def _chromatic_shift(frame: np.ndarray, pixels: int) -> np.ndarray:
    if pixels <= 0:
        return frame.copy()
    b, g, r = cv2.split(frame)
    r = np.roll(r, pixels, axis=1)
    b = np.roll(b, -pixels, axis=1)
    return cv2.merge((b, g, r))


def _scanlines(frame: np.ndarray, phase: int, opacity: float) -> np.ndarray:
    overlay = frame.copy()
    overlay[(np.arange(frame.shape[0]) + phase) % 4 == 0, :] = 0
    return cv2.addWeighted(frame, 1.0, overlay, clamp01(opacity), 0.0)


def _warm_matrix(frame: np.ndarray) -> np.ndarray:
    matrix = np.array([[0.78, 0.06, 0.08],
                       [0.05, 0.92, 0.08],
                       [0.03, 0.12, 1.08]], dtype=np.float32)
    return np.clip(frame.astype(np.float32) @ matrix.T, 0, 255).astype(np.uint8)


def _cool_documentary(frame: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8)).apply(l)
    graded = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
    graded[:, :, 0] = np.clip(graded[:, :, 0].astype(np.int16) + 8, 0, 255)
    return cv2.addWeighted(_gray_bgr(graded), 0.18, graded, 0.82, 0.0)


def apply_temporal(frame: np.ndarray, style: str, progress: float,
                   strength: float, seed: int = 0,
                   material: np.ndarray | None = None) -> np.ndarray:
    """Apply one time-aware single-shot filter to a BGR frame."""
    p = clamp01(progress)
    s = clamp01(strength)
    pulse = math.sin(math.pi * p) ** 2
    plate = _fit_material(material, frame)
    if style == "mono_halftone":
        effected = blend(frame, _halftone(frame, 9), s)
        return _multiply(effected, plate, 0.22 * s) if plate is not None else effected
    if style == "xerox_pulse":
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        xerox = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                      cv2.THRESH_BINARY, 15, 5)
        effected = blend(frame, cv2.cvtColor(xerox, cv2.COLOR_GRAY2BGR), s * (0.75 + 0.25 * pulse))
        return _multiply(effected, plate, 0.30 * s) if plate is not None else effected
    if style == "scanline_focus":
        scanned = _scanlines(frame, round(p * 12), 0.22 + 0.18 * pulse)
        y = round((frame.shape[0] - 1) * p)
        cv2.line(scanned, (0, y), (frame.shape[1], y), (255, 245, 185), 3)
        return blend(frame, scanned, s)
    if style == "chromatic_impact":
        return blend(frame, _chromatic_shift(frame, max(1, round(18 * s * pulse))), s * pulse)
    if style == "blur_snap":
        amount = max(0.0, 1.0 - smoothstep(p))
        blurred = cv2.GaussianBlur(frame, (0, 0), sigmaX=1.0 + 14.0 * amount)
        return blend(frame, blurred, s * amount)
    if style == "warm_memory":
        memory = _bloom(_warm_matrix(frame), 7.0, 180)
        return blend(frame, memory, s)
    if style == "cool_documentary":
        return blend(frame, _cool_documentary(frame), s)
    if style == "high_key_bloom":
        lifted = cv2.convertScaleAbs(frame, alpha=1.03, beta=6)
        return blend(frame, _bloom(lifted, 12.0, 170), s)
    if style == "film_grain_soft":
        rng = np.random.default_rng(seed + round(p * 10000))
        noise = rng.normal(0, 8, frame.shape[:2]).astype(np.float32)
        grain = frame.astype(np.float32) + noise[:, :, None]
        effected = blend(frame, np.clip(grain, 0, 255).astype(np.uint8), s)
        return _multiply(effected, plate, 0.12 * s) if plate is not None else effected
    if style == "ink_monochrome":
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        ink = cv2.bilateralFilter(gray, 7, 45, 45)
        edges = cv2.Canny(ink, 55, 135)
        paper = cv2.cvtColor(255 - edges, cv2.COLOR_GRAY2BGR)
        paper = cv2.addWeighted(paper, 0.72, _gray_bgr(frame), 0.28, 0)
        effected = blend(frame, paper, s)
        return _multiply(effected, plate, 0.22 * s) if plate is not None else effected
    if style == "cmyk_offset":
        effected = blend(frame, _chromatic_shift(frame, max(2, round(12 * s * pulse))), s)
        return _multiply(effected, plate, 0.18 * s) if plate is not None else effected
    if style == "analog_print_soft":
        if plate is None:
            raise ValueError("analog_print_soft requires approved print material")
        printed = _multiply(frame, plate, 0.36 * s)
        printed = _chromatic_shift(printed, max(1, round(3 * pulse * s)))
        return blend(frame, printed, s)
    if style == "optical_prism_glint":
        if plate is None:
            raise ValueError("optical_prism_glint requires approved optical material")
        glint = _screen(frame, plate, (0.10 + 0.38 * pulse) * s)
        return blend(frame, glint, 0.72)
    if style == "washi_paper_soft":
        if plate is None:
            raise ValueError("washi_paper_soft requires approved washi material")
        paper = _multiply(frame, plate, 0.22 * s)
        lifted = cv2.convertScaleAbs(paper, alpha=1.015, beta=3)
        return blend(frame, lifted, s)
    raise KeyError(f"unknown temporal style: {style}")


def tear_alpha(width: int, height: int, progress: float, style: str,
               seed: int = 321) -> tuple[np.ndarray, np.ndarray]:
    """Return incoming alpha plus a soft fibrous edge band."""
    p = smoothstep(progress)
    rng = np.random.default_rng(seed)
    ys = np.arange(height, dtype=np.float32)
    noise = (np.sin(ys * 0.031 + 0.7) * 8.0 +
             np.sin(ys * 0.087 + 2.1) * 4.0 +
             rng.normal(0, 1.2, height))
    xx = np.arange(width, dtype=np.float32)[None, :]
    if style in {"torn_paper_vertical", "halftone_rip_reveal", "torn_paper_split"}:
        half = p * width * 0.58
        centre = width * 0.5 + noise[:, None]
        distance = np.abs(xx - centre)
        alpha = np.clip((half - distance + 3.0) / 6.0, 0.0, 1.0)
        edge = ((distance >= max(0.0, half - 13.0)) &
                (distance <= half + 13.0)).astype(np.float32)
    elif style == "torn_paper_diagonal":
        yy = np.arange(height, dtype=np.float32)[:, None]
        boundary = (-width * 0.3 + p * width * 1.6 +
                    yy * 0.26 + noise[:, None])
        alpha = np.clip((boundary - xx + 4.0) / 8.0, 0.0, 1.0)
        edge = (np.abs(boundary - xx) <= 14.0).astype(np.float32)
    else:
        threshold = p * 255.0
        field = cv2.GaussianBlur(rng.integers(0, 256, (height, width), np.uint8),
                                (0, 0), sigmaX=22)
        field = cv2.normalize(field, None, 0, 255, cv2.NORM_MINMAX)
        alpha = np.clip((threshold - field.astype(np.float32) + 12.0) / 24.0, 0.0, 1.0)
        edge = ((np.abs(field.astype(np.float32) - threshold)) <= 14.0).astype(np.float32)
    return alpha.astype(np.float32), cv2.GaussianBlur(edge, (0, 0), 1.4)


def _paper_edge(frame: np.ndarray, edge: np.ndarray, strength: float,
                material: np.ndarray | None = None) -> np.ndarray:
    paper = np.full_like(frame, (235, 242, 247))
    plate = _fit_material(material, frame)
    if plate is not None:
        luminance = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        fibre = cv2.GaussianBlur(luminance, (0, 0), 0.8)[:, :, None]
        paper = np.clip(paper.astype(np.float32) * (0.80 + fibre * 0.24),
                        0, 255).astype(np.uint8)
    shadow = cv2.GaussianBlur(edge, (0, 0), 8.0)[:, :, None]
    result = frame.astype(np.float32) * (1.0 - shadow * 0.24 * strength)
    band = edge[:, :, None] * clamp01(strength)
    return np.clip(result * (1.0 - band) + paper.astype(np.float32) * band, 0, 255).astype(np.uint8)


def composite_transition(outgoing: np.ndarray, incoming: np.ndarray, style: str,
                         progress: float, strength: float, seed: int = 321,
                         material: np.ndarray | None = None) -> np.ndarray:
    p = clamp01(progress)
    s = clamp01(strength)
    if style.startswith("torn_paper") or style == "halftone_rip_reveal":
        alpha, edge = tear_alpha(outgoing.shape[1], outgoing.shape[0], p, style, seed)
        revealed = _halftone(incoming, 8) if style == "halftone_rip_reveal" else incoming
        mixed = (outgoing.astype(np.float32) * (1.0 - alpha[:, :, None]) +
                 revealed.astype(np.float32) * alpha[:, :, None]).astype(np.uint8)
        return _paper_edge(mixed, edge, s, material)
    if style == "ink_bleed_reveal":
        plate = _fit_material(material, outgoing)
        if plate is None:
            raise ValueError("ink_bleed_reveal requires approved ink material")
        field = 1.0 - cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        field = cv2.GaussianBlur(field, (0, 0), 1.6)
        threshold = 1.08 - p * 1.42
        alpha = np.clip((field - threshold + 0.16) / 0.32, 0.0, 1.0)
        if p > 0.72:
            alpha = np.maximum(alpha, smoothstep((p - 0.72) / 0.28))
        edge = cv2.morphologyEx((alpha * 255).astype(np.uint8), cv2.MORPH_GRADIENT,
                                np.ones((7, 7), np.uint8)).astype(np.float32) / 255.0
        mixed = outgoing * (1.0 - alpha[:, :, None]) + incoming * alpha[:, :, None]
        ink = np.zeros_like(mixed)
        mixed = mixed * (1.0 - edge[:, :, None] * 0.5) + ink * edge[:, :, None] * 0.5
        return np.clip(mixed, 0, 255).astype(np.uint8)
    if style == "film_burn_cut":
        alpha = smoothstep((p - 0.36) / 0.28)
        mixed = cv2.addWeighted(outgoing, 1.0 - alpha, incoming, alpha, 0)
        plate = _fit_material(material, outgoing)
        if plate is None:
            raise ValueError("film_burn_cut requires approved light-leak material")
        peak = math.sin(math.pi * p) ** 5
        return _screen(mixed, plate, peak * s * 0.78)
    if style == "prism_flash_cut":
        plate = _fit_material(material, outgoing)
        if plate is None:
            raise ValueError("prism_flash_cut requires approved optical material")
        alpha = smoothstep((p - 0.34) / 0.32)
        mixed = cv2.addWeighted(outgoing, 1.0 - alpha, incoming, alpha, 0)
        peak = math.sin(math.pi * p) ** 7
        flashed = _screen(mixed, plate, peak * s * 0.88)
        return cv2.convertScaleAbs(flashed, alpha=1.0, beta=round(42 * peak * s))
    if style == "lens_blur_cut":
        alpha = smoothstep(p)
        mixed = cv2.addWeighted(outgoing, 1.0 - alpha, incoming, alpha, 0)
        sigma = 1.0 + 20.0 * math.sin(math.pi * p) ** 2 * s
        return cv2.GaussianBlur(mixed, (0, 0), sigmaX=sigma)
    if style == "chromatic_whip_cut":
        cut = outgoing if p < 0.5 else incoming
        direction = 1 if p < 0.5 else -1
        shift = round(direction * (1.0 - abs(p - 0.5) * 2.0) * outgoing.shape[1] * 0.08 * s)
        moved = np.roll(cut, shift, axis=1)
        return _chromatic_shift(moved, max(1, round(abs(shift) * 0.08)))
    if style == "luma_fade":
        gray = cv2.cvtColor(incoming, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        alpha = np.clip((p - (1.0 - gray) * 0.55) / 0.45, 0.0, 1.0)
        mixed = outgoing * (1.0 - alpha[:, :, None]) + incoming * alpha[:, :, None]
        return np.clip(mixed, 0, 255).astype(np.uint8)
    raise KeyError(f"unknown transition style: {style}")


def apply_subject(frame: np.ndarray, matte: np.ndarray, style: str,
                  progress: float, strength: float) -> np.ndarray:
    mask = matte.astype(np.float32)
    if mask.ndim == 3:
        mask = cv2.cvtColor(mask.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
    mask = np.clip(mask / 255.0, 0.0, 1.0)
    mask3 = mask[:, :, None]
    p = clamp01(progress)
    s = clamp01(strength)
    if style == "subject_black_to_color":
        subject = np.zeros_like(frame) if p < 0.42 else frame.copy()
        if 0.34 <= p <= 0.72:
            x = round((p - 0.34) / 0.38 * (frame.shape[1] + 240)) - 120
            sheen = np.zeros(mask.shape, np.uint8)
            cv2.line(sheen, (x - 90, frame.shape[0]), (x + 90, 0), 255, 70)
            sheen = cv2.GaussianBlur(sheen, (0, 0), 22).astype(np.float32) / 255.0
            subject = np.clip(subject.astype(np.float32) + sheen[:, :, None] * 190 * mask3,
                              0, 255).astype(np.uint8)
        return np.clip(frame * (1.0 - mask3 * s) + subject * (mask3 * s), 0, 255).astype(np.uint8)
    if style == "subject_halftone":
        subject = _halftone(frame, 8)
        return blend(frame, np.clip(frame * (1.0 - mask3) + subject * mask3, 0, 255).astype(np.uint8), s)
    if style == "subject_outline_pulse":
        binary = (mask * 255).astype(np.uint8)
        edge = cv2.morphologyEx(binary, cv2.MORPH_GRADIENT, np.ones((9, 9), np.uint8))
        overlay = frame.copy()
        color = (70, 255, 175)
        overlay[edge > 0] = color
        return blend(frame, overlay, s * (0.55 + 0.45 * math.sin(math.pi * p) ** 2))
    if style == "subject_color_isolation":
        gray = _gray_bgr(frame)
        isolated = gray * (1.0 - mask3) + frame * mask3
        return blend(frame, isolated.astype(np.uint8), s)
    raise KeyError(f"unknown subject style: {style}")


def supported_styles() -> dict[str, list[str]]:
    return {
        "temporal": ["mono_halftone", "xerox_pulse", "scanline_focus",
                     "chromatic_impact", "blur_snap", "warm_memory",
                     "cool_documentary", "high_key_bloom", "film_grain_soft",
                     "ink_monochrome", "cmyk_offset", "analog_print_soft",
                     "optical_prism_glint", "washi_paper_soft"],
        "transition": ["torn_paper_vertical", "torn_paper_diagonal",
                       "torn_paper_split", "halftone_rip_reveal",
                       "ink_bleed_reveal", "film_burn_cut", "lens_blur_cut",
                       "chromatic_whip_cut", "luma_fade", "prism_flash_cut"],
        "subject": ["subject_black_to_color", "subject_halftone",
                    "subject_outline_pulse", "subject_color_isolation"],
    }
