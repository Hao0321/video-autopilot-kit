# -*- coding: utf-8 -*-
"""Evidence-gated per-frame subject matte builder.

The builder creates alpha sequences for photographed objects.  It is intended
for subject treatments such as a diagonal material sheen; it never masks text
and it never turns a loose bounding box into a claim of automatic rotoscoping.

The current ``round_product_grabcut`` route is suitable for short, hand-held
round products (for example a battle top) whose keyframed box has already been
verified by an editor.  Output remains ``AUTO_WITH_REVIEW`` until the sequence
passes measured leak/edge QA and Hao approves the rendered shot.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import tempfile
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from tracked_graphics import _keyframed_bbox, _prepare_tracking_source


PROFILES = {"round_product_grabcut"}


def validate_spec(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    source = Path(str(spec.get("video", "")))
    if not source.is_file():
        errors.append("video does not exist")
    start, end = float(spec.get("start", 0)), float(spec.get("end", 0))
    if end <= start:
        errors.append("end must exceed start")
    if spec.get("profile", "round_product_grabcut") not in PROFILES:
        errors.append("unknown profile")
    if str(spec.get("target_kind", "subject_object")) != "subject_object":
        errors.append("target_kind must be subject_object")
    if not isinstance(spec.get("initial_bbox"), list) or len(spec.get("initial_bbox", [])) != 4:
        errors.append("initial_bbox must be a four-value list")
    if not str(spec.get("evidence", "")).strip():
        errors.append("editor-verified bbox evidence is required")
    for index, row in enumerate(spec.get("keyframes") or []):
        if "time" not in row or not isinstance(row.get("bbox"), list) or len(row["bbox"]) != 4:
            errors.append(f"keyframes[{index}] requires time and four-value bbox")
    edge_band = float(spec.get("skin_occlusion_edge_band", .22))
    if not .05 <= edge_band <= .45:
        errors.append("skin_occlusion_edge_band must be between 0.05 and 0.45")
    return errors


def _ellipse_mask(height: int, width: int, inset: float) -> np.ndarray:
    mask = np.zeros((height, width), np.uint8)
    inset = max(0.0, min(.35, inset))
    center = (width // 2, height // 2)
    axes = (max(2, round(width * (.5 - inset))), max(2, round(height * (.5 - inset))))
    cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1, cv2.LINE_AA)
    return mask


def _ellipse_mask_at(height: int, width: int, center: tuple[float, float],
                     radius_ratio: float) -> np.ndarray:
    mask = np.zeros((height, width), np.uint8)
    cx = max(0, min(width - 1, round(center[0] * width)))
    cy = max(0, min(height - 1, round(center[1] * height)))
    ratio = max(.04, min(.49, float(radius_ratio)))
    cv2.ellipse(mask, (cx, cy),
                (max(2, round(width * ratio)), max(2, round(height * ratio))),
                0, 0, 360, 255, -1, cv2.LINE_AA)
    return mask


def _detail_seed_center(crop: np.ndarray) -> tuple[float, float]:
    """Locate the non-skin, high-detail product centre inside an approximate box."""
    height, width = crop.shape[:2]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    grey = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(grey, 65, 150).astype(np.float32) / 255.0
    saturation = hsv[:, :, 1].astype(np.float32) / 255.0
    skin = _skin_occlusion(crop, {})
    non_skin = 1.0 - skin.astype(np.float32) / 255.0 * .86
    score = (edges * .72 + saturation * .43) * non_skin
    sigma = max(7.0, min(width, height) * .062)
    score = cv2.GaussianBlur(score, (0, 0), sigma)
    # Package text and crop boundaries are common false maxima.  A soft centre
    # prior remains permissive enough for a poorly centred editorial bbox.
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    nx = (xx / max(1.0, width - 1) - .5) / .62
    ny = (yy / max(1.0, height - 1) - .5) / .72
    prior = np.exp(-.5 * (nx * nx + ny * ny))
    score *= .56 + .44 * prior
    border = max(3, round(min(width, height) * .035))
    score[:border, :] = score[-border:, :] = 0
    score[:, :border] = score[:, -border:] = 0
    cy, cx = np.unravel_index(int(np.argmax(score)), score.shape)
    return float(cx) / max(1, width - 1), float(cy) / max(1, height - 1)


def _radial_product_prior(
    crop: np.ndarray, seed_center: tuple[float, float],
    radial_hint: tuple[float, float, float] | None = None,
) -> tuple[np.ndarray | None, dict[str, float]]:
    """Find a photographed top's outer radial body near the verified seed.

    GrabCut often keeps a transparent coloured centre but drops silver outer
    blades.  A constrained Hough prior recovers the complete physical product.
    Candidates must remain close to the non-skin detail seed, which prevents
    the much larger battle-arena ring from winning.
    """
    height, width = crop.shape[:2]
    short = min(width, height)
    grey = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    grey = cv2.medianBlur(grey, 7)
    circles = cv2.HoughCircles(
        grey, cv2.HOUGH_GRADIENT, dp=1.35,
        minDist=max(24, round(short * .16)), param1=118, param2=31,
        minRadius=max(14, round(short * .13)),
        maxRadius=max(18, round(short * .46)),
    )
    # Once a disc has been verified, its normalised geometry becomes the
    # temporal prior. A missed circle must not collapse the matte to the centre
    # art and a stray arena/packaging circle must not move the reveal.
    expected = radial_hint
    sx = (expected[0] if expected else seed_center[0]) * width
    sy = (expected[1] if expected else seed_center[1]) * height
    expected_radius = (expected[2] * short) if expected else None
    best: tuple[float, tuple[float, float, float]] | None = None
    if circles is not None:
        for cx, cy, radius in circles[0]:
            distance = math.hypot(float(cx) - sx, float(cy) - sy)
            maximum_distance = short * (.18 if expected else .26)
            if distance > maximum_distance:
                continue
            radius_delta = abs(float(radius) - expected_radius) if expected_radius else 0.0
            if expected_radius and radius_delta > short * .16:
                continue
            score = float(radius) * .12 - distance * 1.10 - radius_delta * .72
            if best is None or score > best[0]:
                best = (score, (float(cx), float(cy), float(radius)))

    detected = best is not None
    if best is None and expected is None:
        return None, {"radial_prior_used": 0.0, "radial_prior_detected": 0.0}
    if best is None:
        cx, cy, radius = sx, sy, float(expected_radius)
    elif expected is None:
        cx, cy, radius = best[1]
    else:
        # Low-pass only trusted detections. The track supplies movement while
        # Hough corrects slow pose/scale changes without edge jitter.
        measured_x, measured_y, measured_radius = best[1]
        center_follow = .16
        radius_follow = .12
        cx = sx + (measured_x - sx) * center_follow
        cy = sy + (measured_y - sy) * center_follow
        radius = expected_radius + (measured_radius - expected_radius) * radius_follow
    mask = np.zeros((height, width), np.uint8)
    # Hough usually locks to the coloured/metallic inner ring, while the user
    # perceives the complete attack blade as the object. Expand to the proven
    # outer-body envelope, then subtract photographed skin below. This avoids
    # the cheap "centre sticker lights up, silver blades stay black" failure.
    # The Hough circle usually lands on the inner coloured ring.  The attack
    # blade is materially wider, but treating that wider radius as a *solid*
    # disc creates the rejected black-hole look during a reveal.  Use the
    # wider circle only as a GrabCut appearance prior; the delivered alpha is
    # still the photographed silhouette after skin removal.
    body_scale = 1.86
    cv2.circle(mask, (round(cx), round(cy)), round(radius * body_scale), 255, -1, cv2.LINE_AA)
    return mask, {
        "radial_prior_used": 1.0,
        "radial_prior_detected": 1.0 if detected else 0.0,
        "radial_prior_center_x": round(cx / max(1, width - 1), 5),
        "radial_prior_center_y": round(cy / max(1, height - 1), 5),
        "radial_prior_radius_ratio": round(radius / max(1, short), 5),
        "radial_body_scale": body_scale,
    }


def _component_at_center(binary: np.ndarray) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
    if count <= 1:
        return binary
    h, w = binary.shape
    cy, cx = h // 2, w // 2
    center_label = int(labels[cy, cx])
    if center_label == 0:
        candidates = [(int(stats[index, cv2.CC_STAT_AREA]), index) for index in range(1, count)]
        center_label = max(candidates)[1]
    return np.where(labels == center_label, 255, 0).astype(np.uint8)


def _product_components(binary: np.ndarray,
                        seed_center: tuple[float, float] = (.5, .5)) -> np.ndarray:
    """Keep the central product plus detached blades/rings, reject stray skin.

    A battle top is not one solid colour component: metallic blades and clear
    plastic rings can be disconnected by dark gaps.  Keeping only the centre
    component therefore produces the exact failure the user rejected (inner
    disc black, outer product still coloured).  Detached components are kept
    only when they are substantial and spatially centred inside the verified
    product crop.
    """
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, 8)
    if count <= 1:
        return binary
    height, width = binary.shape
    seed_x = max(0, min(width - 1, round(seed_center[0] * (width - 1))))
    seed_y = max(0, min(height - 1, round(seed_center[1] * (height - 1))))
    center_label = int(labels[seed_y, seed_x])
    output = np.zeros_like(binary)
    minimum_area = max(10, round(height * width * .0015))
    for index in range(1, count):
        area = int(stats[index, cv2.CC_STAT_AREA])
        cx, cy = [float(value) for value in centroids[index]]
        nx = (cx - seed_x) / max(1.0, width * .46)
        ny = (cy - seed_y) / max(1.0, height * .46)
        centred = nx * nx + ny * ny <= 1.0
        if index == center_label or (area >= minimum_area and centred):
            output[labels == index] = 255
    return output


def _radial_material_hull(
    crop: np.ndarray,
    radial_prior: np.ndarray,
    skin: np.ndarray,
    seed_center: tuple[float, float],
) -> np.ndarray:
    """Recover the photographed attack-ring envelope without drawing a disc.

    Silver blades are regularly dropped by GrabCut because they resemble the
    pale arena.  Inside the verified radial search area, retain saturated,
    dark, or locally detailed non-skin material, then build one conservative
    convex product envelope.  The result follows the photographed outer
    vertices while avoiding the synthetic circular black-hole failure.
    """
    height, width = crop.shape[:2]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    grey = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    laplace = cv2.convertScaleAbs(cv2.Laplacian(grey, cv2.CV_16S, ksize=3))
    material = np.where(
        (saturation >= 34) | (value <= 214) | (laplace >= 22), 255, 0
    ).astype(np.uint8)
    material = cv2.bitwise_and(material, radial_prior)
    material[skin >= 96] = 0

    close_size = max(5, round(min(width, height) * .045))
    if close_size % 2 == 0:
        close_size += 1
    close_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (close_size, close_size))
    material = cv2.morphologyEx(material, cv2.MORPH_CLOSE, close_kernel)
    material = cv2.morphologyEx(
        material, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
    )

    count, labels, stats, centroids = cv2.connectedComponentsWithStats(material, 8)
    seed_x = float(seed_center[0]) * max(1, width - 1)
    seed_y = float(seed_center[1]) * max(1, height - 1)
    maximum_distance = min(width, height) * .48
    minimum_area = max(12, round(width * height * .0012))
    points: list[np.ndarray] = []
    for index in range(1, count):
        area = int(stats[index, cv2.CC_STAT_AREA])
        cx, cy = [float(value) for value in centroids[index]]
        if area < minimum_area or math.hypot(cx - seed_x, cy - seed_y) > maximum_distance:
            continue
        ys, xs = np.where(labels == index)
        if xs.size:
            points.append(np.column_stack((xs, ys)).astype(np.int32))
    if not points:
        return np.zeros_like(radial_prior)
    hull = cv2.convexHull(np.concatenate(points, axis=0))
    output = np.zeros_like(radial_prior)
    cv2.fillConvexPoly(output, hull, 255, cv2.LINE_AA)
    output = cv2.bitwise_and(output, radial_prior)
    output[skin >= 96] = 0
    return output


def _polar_outer_silhouette(
    crop: np.ndarray,
    radial_prior: np.ndarray,
    skin: np.ndarray,
) -> np.ndarray:
    """Trace a stable photographed outer ring from radial edge evidence.

    Battle tops are radial but not perfect circles.  Sample the strongest
    plausible outer edge along many rays, smooth neighbouring radii, and fill
    that contour.  This recovers metal blades that appearance segmentation
    drops while retaining the real pentagonal/star-like outline.
    """
    height, width = crop.shape[:2]
    ys, xs = np.where(radial_prior >= 128)
    if xs.size < 16:
        return np.zeros_like(radial_prior)
    cx, cy = float(xs.mean()), float(ys.mean())
    expected = .25 * ((float(xs.max()) - float(xs.min())) +
                      (float(ys.max()) - float(ys.min())))
    grey = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    grey = cv2.GaussianBlur(grey, (5, 5), 0)
    gx = cv2.Sobel(grey, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(grey, cv2.CV_32F, 0, 1, ksize=3)
    gradient = cv2.magnitude(gx, gy)
    angles = np.linspace(0.0, math.tau, 96, endpoint=False)
    observed: list[float] = []
    low, high = expected * .73, expected * 1.10
    for angle in angles:
        radii = np.linspace(low, high, max(18, round(high - low) + 1))
        sample_x = np.clip(np.rint(cx + np.cos(angle) * radii).astype(np.int32),
                           0, width - 1)
        sample_y = np.clip(np.rint(cy + np.sin(angle) * radii).astype(np.int32),
                           0, height - 1)
        values = gradient[sample_y, sample_x]
        # Prefer visible boundaries while keeping weak/blurred sectors close
        # to the verified radial estimate instead of collapsing inward.
        proximity = np.abs(radii - expected) / max(1.0, expected)
        score = values - proximity * 72.0
        best = int(np.argmax(score))
        radius = float(radii[best]) if float(values[best]) >= 16.0 else expected
        observed.append(radius)
    raw = np.asarray(observed, dtype=np.float32)
    smooth = raw.copy()
    for index in range(len(raw)):
        neighbours = [raw[(index + offset) % len(raw)] for offset in range(-3, 4)]
        smooth[index] = float(np.median(neighbours))
    smooth = np.clip(smooth * .78 + expected * .22, low, high)
    points = np.column_stack((
        cx + np.cos(angles) * smooth,
        cy + np.sin(angles) * smooth,
    ))
    points[:, 0] = np.clip(points[:, 0], 0, width - 1)
    points[:, 1] = np.clip(points[:, 1], 0, height - 1)
    output = np.zeros_like(radial_prior)
    cv2.fillPoly(output, [np.rint(points).astype(np.int32)], 255, cv2.LINE_AA)
    output[skin >= 96] = 0
    return output


def _round_product_mask(
    crop: np.ndarray, config: dict[str, Any],
    radial_hint: tuple[float, float, float] | None = None,
) -> tuple[np.ndarray, dict[str, float]]:
    height, width = crop.shape[:2]
    seed_center = (
        (radial_hint[0], radial_hint[1]) if radial_hint is not None else
        (_detail_seed_center(crop) if config.get("auto_seed_center", True)
         else tuple(config.get("seed_center", [.5, .5])))
    )
    radial_prior, radial_metrics = (
        _radial_product_prior(crop, seed_center, radial_hint)
        if str(config.get("subject_class", "")) == "battle_top" else
        (None, {"radial_prior_used": 0.0})
    )
    # The editorial box is deliberately padded for search.  The actual top is
    # much smaller than that search area, so a near-full-crop ellipse recreates
    # the rejected look: fingers, launcher and packaging light up together.
    # Keep the GrabCut prior tight around the detected radial product centre.
    outer = _ellipse_mask_at(height, width, seed_center,
                             float(config.get("outer_radius", .325)))
    if radial_prior is not None:
        outer = cv2.bitwise_or(outer, radial_prior)
    probable = _ellipse_mask_at(height, width, seed_center,
                                float(config.get("probable_radius", .255)))
    certain = _ellipse_mask_at(height, width, seed_center,
                               float(config.get("certain_radius", .06)))

    gc = np.full((height, width), cv2.GC_BGD, np.uint8)
    gc[outer > 0] = cv2.GC_PR_BGD
    gc[probable > 0] = cv2.GC_PR_FGD
    if radial_prior is not None:
        gc[radial_prior > 0] = cv2.GC_PR_FGD
    gc[certain > 0] = cv2.GC_FGD
    bg_model = np.zeros((1, 65), np.float64)
    fg_model = np.zeros((1, 65), np.float64)
    cv2.grabCut(crop, gc, None, bg_model, fg_model,
                int(config.get("iterations", 5)), cv2.GC_INIT_WITH_MASK)
    binary = np.where((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    # Optional, evidence-scoped material ranges recover disconnected metallic
    # blades that GrabCut can classify as background.  Ranges are explicit HSV
    # bounds stored in the shot spec; this is not a universal colour guess.
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    for bounds in config.get("hsv_includes", []):
        if not isinstance(bounds, list) or len(bounds) != 6:
            continue
        lower = np.array(bounds[:3], dtype=np.uint8)
        upper = np.array(bounds[3:], dtype=np.uint8)
        material = cv2.inRange(hsv, lower, upper)
        binary = cv2.bitwise_or(binary, cv2.bitwise_and(material, outer))
    binary = cv2.bitwise_and(binary, outer)
    skin = (_skin_occlusion(crop, config)
            if config.get("exclude_skin_occlusion") is True
            else np.zeros((height, width), np.uint8))
    if radial_prior is not None:
        # Preserve only a compact verified core so transparent centre art does
        # not disappear.  Never OR the full circular prior into the delivered
        # matte: that was the source of the visible black disc around the top.
        core_radius = max(3, round(min(width, height) * .075))
        core = np.zeros_like(binary)
        core_x = max(0, min(width - 1, round(seed_center[0] * (width - 1))))
        core_y = max(0, min(height - 1, round(seed_center[1] * (height - 1))))
        cv2.circle(core, (core_x, core_y), core_radius, 255, -1, cv2.LINE_AA)
        binary = cv2.bitwise_or(binary, core)
        material_hull = _radial_material_hull(
            crop, radial_prior, skin, seed_center)
        binary = cv2.bitwise_or(binary, material_hull)
        polar_silhouette = _polar_outer_silhouette(crop, radial_prior, skin)
        binary = cv2.bitwise_or(binary, polar_silhouette)
    if config.get("exclude_skin_occlusion") is True:
        binary[skin >= 128] = 0
    binary = _product_components(binary, seed_center)

    kernel_size = max(3, round(min(width, height) * .018))
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    binary = cv2.bitwise_or(binary, certain)

    feather = max(1, round(min(width, height) * float(config.get("feather", .008))))
    if feather % 2 == 0:
        feather += 1
    alpha = cv2.GaussianBlur(binary, (feather, feather), 0)
    area_ratio = float(np.count_nonzero(binary)) / max(1, height * width)
    border = np.concatenate((binary[0], binary[-1], binary[:, 0], binary[:, -1]))
    border_ratio = float(np.count_nonzero(border)) / max(1, border.size)
    # Coverage is not a target-size contest.  A properly segmented handheld
    # product may occupy only 15-45% of the padded search crop.  Penalise only
    # implausibly tiny/huge masks and crop-border leaks.
    tiny_penalty = max(0.0, .075 - area_ratio) * 5.0
    huge_penalty = max(0.0, area_ratio - .70) * 3.0
    # A product entering from the edge or a tight CSRT crop may legitimately
    # touch part of the crop perimeter.  Penalise only broad perimeter floods;
    # ordinary partial contact is handled by the track/skin/edge checks.
    border_penalty = max(0.0, border_ratio - .32) * 3.5
    confidence = max(0.0, min(1.0,
                              1.0 - tiny_penalty - huge_penalty - border_penalty))
    return alpha, {
        "foreground_area_ratio": round(area_ratio, 5),
        "border_contact_ratio": round(border_ratio, 5),
        "confidence": round(confidence, 5),
        "seed_center": [round(seed_center[0], 5), round(seed_center[1], 5)],
        **radial_metrics,
    }


def _centroid_aligned(mask: np.ndarray) -> np.ndarray:
    moments = cv2.moments(mask)
    if abs(moments["m00"]) < 1e-6:
        return mask
    cx = moments["m10"] / moments["m00"]
    cy = moments["m01"] / moments["m00"]
    shift_x, shift_y = 127.5 - cx, 127.5 - cy
    return cv2.warpAffine(
        mask, np.float32([[1, 0, shift_x], [0, 1, shift_y]]), (256, 256),
        flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0,
    )


def _edge_chatter(contours: list[np.ndarray]) -> float:
    """Centroid-aligned silhouette-change proxy, not a parity claim.

    Hand-held objects legitimately translate inside the padded search crop.
    Measuring unaligned masks confuses that motion with a bad matte and also
    rewards a giant stationary ellipse.  Alignment isolates edge instability.
    """
    if len(contours) < 2:
        return 0.0
    changes: list[float] = []
    for left, right in zip(contours, contours[1:]):
        left, right = _centroid_aligned(left), _centroid_aligned(right)
        left_edge = cv2.Canny(left, 80, 160)
        right_edge = cv2.Canny(right, 80, 160)
        distance = cv2.distanceTransform(255 - right_edge, cv2.DIST_L2, 3)
        values = distance[left_edge > 0]
        if values.size:
            changes.append(float(np.percentile(values, 95)))
    return round(float(np.percentile(changes, 95)) if changes else 0.0, 4)


def _debug_overlay(frame: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    strength = (alpha.astype(np.float32) / 255.0 * .48)[..., None]
    tint = np.zeros_like(frame, dtype=np.float32)
    tint[:, :, 0] = 255  # cyan in BGR
    tint[:, :, 1] = 220
    out = frame.astype(np.float32) * (1.0 - strength) + tint * strength
    edges = cv2.Canny(alpha, 80, 160)
    out[edges > 0] = (30, 255, 255)
    return np.clip(out, 0, 255).astype(np.uint8)


def _skin_occlusion(crop: np.ndarray, config: dict[str, Any]) -> np.ndarray:
    """Return a conservative photographed-skin occlusion mask.

    This is only used inside an editor-verified round-product crop.  Requiring
    both HSV and YCrCb agreement keeps gold/yellow product material from being
    removed merely because it is warm.  The thresholds are configurable per
    shot and the resulting edge still requires human review.
    """
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    ycrcb = cv2.cvtColor(crop, cv2.COLOR_BGR2YCrCb)
    hsv_bounds = config.get("skin_hsv", [0, 20, 24, 24, 238, 255])
    ycrcb_bounds = config.get("skin_ycrcb", [0, 126, 70, 255, 185, 140])
    hsv_mask = cv2.inRange(
        hsv, np.array(hsv_bounds[:3], np.uint8), np.array(hsv_bounds[3:], np.uint8)
    )
    ycrcb_mask = cv2.inRange(
        ycrcb, np.array(ycrcb_bounds[:3], np.uint8), np.array(ycrcb_bounds[3:], np.uint8)
    )
    mask = cv2.bitwise_and(hsv_mask, ycrcb_mask)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    # Skin is an occluder, so a slight dilation removes colour fringing at the
    # contact edge instead of leaving a black halo on the fingertip.
    mask = cv2.dilate(mask, kernel, iterations=1)
    return cv2.GaussianBlur(mask, (5, 5), 0)


def _write_contact_sheet(frames: list[np.ndarray], path: Path) -> None:
    if not frames:
        return
    thumbs = []
    for frame in frames:
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        image.thumbnail((270, 480), Image.Resampling.LANCZOS)
        thumbs.append(image)
    columns = min(4, len(thumbs))
    rows = math.ceil(len(thumbs) / columns)
    sheet = Image.new("RGB", (columns * 270, rows * 480), (11, 15, 23))
    for index, image in enumerate(thumbs):
        sheet.paste(image, ((index % columns) * 270, (index // columns) * 480))
    sheet.save(path, quality=94)


def _collect_frame_data(
    spec: dict[str, Any], source: Path, start: float, end: float, output_dir: Path,
) -> dict[str, Any]:
    """Decode the shot once and collect aligned matte candidates and evidence."""
    temp_dir = Path(tempfile.mkdtemp(prefix="roto-matte-"))
    cap: cv2.VideoCapture | None = None
    try:
        prepared, preparation = _prepare_tracking_source(source, start, end - start, temp_dir)
        cap = cv2.VideoCapture(str(prepared))
        if not cap.isOpened():
            raise RuntimeError("could not open prepared source")
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 30)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        requested_frames = max(1, round((end - start) * fps))
        decoded_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        # ffmpeg trims on timestamp boundaries; a fractional end can therefore
        # yield one frame fewer than round(duration*fps).  The decoded clip is
        # the ground truth, not an off-by-one reason to reject a valid matte.
        expected = min(requested_frames, decoded_frames) if decoded_frames > 0 else requested_frames
        rows: list[dict[str, Any]] = []
        raw_masks: list[np.ndarray] = []
        skin_masks: list[np.ndarray] = []
        debug_frames: dict[int, np.ndarray] = {}
        sample_every = max(1, expected // 8)
        use_tracker = (str(spec.get("subject_class", "")) == "battle_top" and
                       str(spec.get("bbox_tracking", "csrt_radial")) == "csrt_radial")
        tracker = None
        tracker_updates = 0
        radial_hint: tuple[float, float, float] | None = None

        def clip_box(box):
            bx, by, bw, bh = [float(value) for value in box]
            bx = max(0.0, min(max(0.0, width - 4.0), bx))
            by = max(0.0, min(max(0.0, height - 4.0), by))
            bw, bh = max(4.0, min(width - bx, bw)), max(4.0, min(height - by, bh))
            return bx, by, bw, bh

        def crop_and_mask(frame, box):
            nonlocal radial_hint
            bx, by, bw, bh = clip_box(box)
            cix, ciy = round(bx), round(by)
            crw = max(4, min(width - cix, round(bw)))
            crh = max(4, min(height - ciy, round(bh)))
            shot = frame[ciy:ciy + crh, cix:cix + crw]
            matte, frame_metrics = _round_product_mask(shot, spec, radial_hint)
            if float(frame_metrics.get("radial_prior_used", 0)) > 0:
                radial_hint = (
                    float(frame_metrics["radial_prior_center_x"]),
                    float(frame_metrics["radial_prior_center_y"]),
                    float(frame_metrics["radial_prior_radius_ratio"]),
                )
            return cix, ciy, crw, crh, shot, matte, frame_metrics

        for frame_index in range(expected):
            ok, frame = cap.read()
            if not ok:
                break
            source_time = start + frame_index / fps
            authored = _keyframed_bbox(spec, source_time, width, height)
            tracking_status = "authored"
            tracked = None
            if tracker is not None:
                tracked_ok, raw_tracked = tracker.update(frame)
                if tracked_ok:
                    tx, ty, tw, th = clip_box(raw_tracked)
                    if tw >= 28 and th >= 28:
                        tracked = (tx, ty, tw, th)
                        tracking_status = "csrt"
                        tracker_updates += 1
            ix, iy, rw, rh, crop, local_alpha, metrics = crop_and_mask(
                frame, tracked or authored)

            # The first authored box is a search window, not the delivered
            # track.  Refine it to the segmented/radial product before CSRT is
            # initialised so the tracker follows the top rather than the hand.
            if frame_index == 0 and use_tracker:
                ys, xs = np.where(local_alpha >= 48)
                if xs.size and ys.size:
                    left, right = int(xs.min()), int(xs.max()) + 1
                    top, bottom = int(ys.min()), int(ys.max()) + 1
                    local_w, local_h = right - left, bottom - top
                    padding = float(spec.get("tracker_padding", .10))
                    px, py = local_w * padding, local_h * padding
                    refined = clip_box((ix + left - px, iy + top - py,
                                        local_w + px * 2, local_h + py * 2))
                    # Preserve the detected disc in full-frame coordinates
                    # while changing from the large authored search window to
                    # the tight tracker box. Later frames keep this stable
                    # normalised disc prior inside the moving CSRT track.
                    if radial_hint is not None:
                        full_cx = ix + radial_hint[0] * max(1, rw - 1)
                        full_cy = iy + radial_hint[1] * max(1, rh - 1)
                        full_radius = radial_hint[2] * min(rw, rh)
                        rbx, rby, rbw, rbh = refined
                        radial_hint = (
                            (full_cx - rbx) / max(1.0, rbw - 1),
                            (full_cy - rby) / max(1.0, rbh - 1),
                            full_radius / max(1.0, min(rbw, rbh)),
                        )
                    ix, iy, rw, rh, crop, local_alpha, metrics = crop_and_mask(frame, refined)
                    tracker = cv2.TrackerCSRT_create()
                    tracker.init(frame, tuple(int(round(value)) for value in refined))
                    tracking_status = "csrt_seed"
            raw_masks.append(cv2.resize(local_alpha, (256, 256), interpolation=cv2.INTER_AREA))
            skin = (_skin_occlusion(crop, spec) if spec.get("exclude_skin_occlusion") is True
                    else np.zeros(crop.shape[:2], np.uint8))
            skin_masks.append(cv2.resize(skin, (256, 256), interpolation=cv2.INTER_AREA))
            if frame_index % sample_every == 0 or frame_index == expected - 1:
                debug_frames[frame_index] = frame.copy()
            rows.append({
                "frame": frame_index, "source_time": round(source_time, 5),
                "bbox": [ix, iy, rw, rh],
                "bbox_tracking_status": tracking_status,
                "matte": str(output_dir / f"frame_{frame_index:06d}.png"), **metrics,
            })
        if len(rows) != expected:
            raise RuntimeError(f"matte sequence incomplete: expected {expected}, rendered {len(rows)}")
        # Remove single-frame tracker noise without causal lag.  Masks are
        # normalised to 256px, so resizing them into these centred-median boxes
        # preserves the photographed motion while stabilising the composite.
        if use_tracker and len(rows) >= 3:
            boxes = np.asarray([row["bbox"] for row in rows], dtype=np.float64)
            smooth = boxes.copy()
            for index in range(len(boxes)):
                left, right = max(0, index - 1), min(len(boxes), index + 2)
                smooth[index] = np.median(boxes[left:right], axis=0)
            for row, box in zip(rows, smooth):
                row["bbox"] = [round(float(value), 3) for value in clip_box(box)]
        return {
            "preparation": preparation, "fps": fps, "width": width, "height": height,
            "rows": rows, "raw_masks": raw_masks, "skin_masks": skin_masks,
            "debug_frames": debug_frames,
            "bbox_tracking_enabled": use_tracker,
            "bbox_tracking_update_ratio": round(tracker_updates / max(1, expected - 1), 5),
        }
    finally:
        if cap is not None:
            cap.release()
        shutil.rmtree(temp_dir, ignore_errors=True)


def _temporal_smooth(raw_masks: list[np.ndarray], radius: int) -> list[np.ndarray]:
    smoothed: list[np.ndarray] = []
    for index in range(len(raw_masks)):
        left = max(0, index - radius)
        right = min(len(raw_masks), index + radius + 1)
        smoothed.append(np.median(np.stack(raw_masks[left:right], axis=0), axis=0).astype(np.uint8))
    return smoothed


def _verified_disc_mask(spec: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    inset = float(spec.get("output_inset", .08))
    center = spec.get("disc_center", [.5, .5])
    cx, cy = float(center[0]), float(center[1])
    radius_x, radius_y = max(.05, .5 - inset), max(.05, .5 - inset)
    verified = np.zeros((256, 256), np.uint8)
    cv2.ellipse(
        verified, (round(cx * 256), round(cy * 256)),
        (round(radius_x * 256), round(radius_y * 256)),
        0, 0, 360, 255, -1, cv2.LINE_AA,
    )
    verified = cv2.GaussianBlur(verified, (5, 5), 0)
    edge_band = float(spec.get("skin_occlusion_edge_band", .22))
    inner = np.zeros((256, 256), np.uint8)
    cv2.ellipse(
        inner, (round(cx * 256), round(cy * 256)),
        (round(radius_x * (1.0 - edge_band) * 256),
         round(radius_y * (1.0 - edge_band) * 256)),
        0, 0, 360, 255, -1, cv2.LINE_AA,
    )
    return verified, cv2.bitwise_and(verified, cv2.bitwise_not(inner))


def _apply_output_geometry(
    spec: dict[str, Any], masks: list[np.ndarray], skin_masks: list[np.ndarray],
) -> tuple[str, list[np.ndarray]]:
    geometry = str(spec.get("output_geometry", "safe_inset_round_product"))
    if geometry == "safe_inset_round_product":
        safe = _ellipse_mask(256, 256, float(spec.get("output_inset", .10)))
        safe = cv2.GaussianBlur(safe, (5, 5), 0)
        return geometry, [safe.copy() for _ in masks]
    if geometry == "editor_verified_disc":
        verified, perimeter = _verified_disc_mask(spec)
        if spec.get("exclude_skin_occlusion") is not True:
            return geometry, [verified.copy() for _ in masks]
        return geometry, [
            cv2.bitwise_and(verified, cv2.bitwise_not(cv2.bitwise_and(skin, perimeter)))
            for skin in skin_masks
        ]
    if geometry == "segmented_silhouette":
        return geometry, masks
    raise ValueError(
        "output_geometry must be safe_inset_round_product, editor_verified_disc or segmented_silhouette"
    )


def _write_sequence(
    rows: list[dict[str, Any]], masks: list[np.ndarray], debug_sources: dict[int, np.ndarray],
    width: int, height: int, output_dir: Path,
) -> Path:
    debug_frames: list[np.ndarray] = []
    for index, (row, aligned) in enumerate(zip(rows, masks)):
        ix, iy, rw, rh = [int(value) for value in row["bbox"]]
        local_alpha = cv2.resize(aligned, (rw, rh), interpolation=cv2.INTER_LANCZOS4)
        full = np.zeros((height, width), np.uint8)
        full[iy:iy + rh, ix:ix + rw] = local_alpha
        ys, xs = np.where(full >= 48)
        if xs.size and ys.size:
            left, right = int(xs.min()), int(xs.max()) + 1
            top, bottom = int(ys.min()), int(ys.max()) + 1
            weights = full[ys, xs].astype(np.float64)
            weight_sum = max(1.0, float(weights.sum()))
            row["subject_bbox"] = [left, top, right - left, bottom - top]
            row["subject_centroid"] = [
                round(float((xs * weights).sum() / weight_sum), 3),
                round(float((ys * weights).sum() / weight_sum), 3),
            ]
            row["subject_area_ratio_in_crop"] = round(
                float(np.count_nonzero(local_alpha >= 48)) / max(1, rw * rh), 5)
        else:
            row["subject_bbox"] = None
            row["subject_centroid"] = None
            row["subject_area_ratio_in_crop"] = 0.0
        Image.fromarray(full).save(Path(row["matte"]), optimize=True)
        if index in debug_sources:
            debug_frames.append(_debug_overlay(debug_sources[index], full))
    contact_path = output_dir / "roto_contact.jpg"
    _write_contact_sheet(debug_frames, contact_path)
    return contact_path


def _coverage_policy(geometry: str) -> str:
    return {
        "safe_inset_round_product":
            "conservative stable inner material surface; excludes fingers/background",
        "editor_verified_disc":
            "complete round product surface from editor-verified keyframed box; requires edge QA",
        "segmented_silhouette": "segmented silhouette requires independent edge QA",
    }[geometry]


def _build_report(
    spec: dict[str, Any], source: Path, start: float, end: float,
    data: dict[str, Any], masks: list[np.ndarray], geometry: str,
    temporal_radius: int, contact_path: Path,
) -> dict[str, Any]:
    rows = data["rows"]
    confidence_p05 = float(np.percentile([row["confidence"] for row in rows], 5))
    verified_disc = None
    if geometry == "editor_verified_disc":
        verified_disc = {
            "center": spec.get("disc_center", [.5, .5]),
            "output_inset": float(spec.get("output_inset", .08)),
            "skin_occlusion_excluded": spec.get("exclude_skin_occlusion") is True,
            "skin_occlusion_edge_band": float(spec.get("skin_occlusion_edge_band", .22)),
            "interior_hole_policy": "forbidden; skin subtraction is perimeter-only",
        }
    edge_chatter = _edge_chatter(masks)
    valid_subject_boxes = sum(1 for row in rows if row.get("subject_bbox"))
    required_boxes = max(1, math.ceil(len(rows) * float(spec.get("minimum_subject_box_ratio", .96))))
    quality_checks = {
        "confidence_p05_ok": confidence_p05 >= float(spec.get("minimum_confidence", .55)),
        "edge_chatter_ok": edge_chatter <= float(spec.get("maximum_edge_chatter_px", 18.0)),
        "subject_box_coverage_ok": valid_subject_boxes >= required_boxes,
        "bbox_tracking_ok": (
            not data.get("bbox_tracking_enabled") or
            float(data.get("bbox_tracking_update_ratio", 0)) >=
            float(spec.get("minimum_bbox_tracking_ratio", .86))
        ),
    }
    return {
        "status": "GREEN" if all(quality_checks.values()) else "REVIEW",
        "capability": "AUTO_WITH_REVIEW",
        "promotion_blocked_until": ["independent_leak_metric_pass", "edge_QA_pass", "Hao_approval"],
        "target_kind": "subject_object", "typography_allowed": False,
        "source": str(source), "source_preparation": data["preparation"],
        "profile": spec.get("profile", "round_product_grabcut"),
        "resolution": [data["width"], data["height"]], "fps": data["fps"], "frames": len(rows),
        "sequence_start": start, "sequence_end": end,
        "confidence_p05": round(confidence_p05, 5), "output_geometry": geometry,
        "coverage_policy": _coverage_policy(geometry), "verified_disc_geometry": verified_disc,
        "temporal_smoothing_radius_frames": temporal_radius,
        "raw_aligned_silhouette_change_px_p95_at_256": _edge_chatter(data["raw_masks"]),
        "aligned_silhouette_change_px_p95_at_256": edge_chatter,
        "edge_chatter_metric_status": "PROXY_ONLY_REQUIRES_INDEPENDENT_GROUND_TRUTH",
        "quality_checks": quality_checks,
        "valid_subject_bbox_frames": valid_subject_boxes,
        "required_subject_bbox_frames": required_boxes,
        "bbox_tracking_enabled": bool(data.get("bbox_tracking_enabled")),
        "bbox_tracking_update_ratio": data.get("bbox_tracking_update_ratio"),
        "contact_sheet": str(contact_path), "frames_detail": rows,
    }


def build_sequence(spec: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    errors = validate_spec(spec)
    if errors:
        raise ValueError("invalid roto spec: " + "; ".join(errors))
    source = Path(spec["video"]).resolve()
    start, end = float(spec["start"]), float(spec["end"])
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    data = _collect_frame_data(spec, source, start, end, output_path)
    temporal_radius = max(0, min(3, int(spec.get("temporal_radius", 2))))
    smoothed = _temporal_smooth(data["raw_masks"], temporal_radius)
    geometry, masks = _apply_output_geometry(spec, smoothed, data["skin_masks"])
    contact_path = _write_sequence(
        data["rows"], masks, data["debug_frames"], data["width"], data["height"], output_path,
    )
    report = _build_report(
        spec, source, start, end, data, masks, geometry, temporal_radius, contact_path,
    )
    report_path = output_path / "roto_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["report_path"] = str(report_path)
    return report


def self_test() -> None:
    invalid = {"video": __file__, "start": 0, "end": 1,
               "initial_bbox": [0, 0, 10, 10], "target_kind": "typography"}
    errors = validate_spec(invalid)
    assert "target_kind must be subject_object" in errors
    sample = np.full((180, 180, 3), (38, 48, 64), np.uint8)
    cv2.circle(sample, (90, 90), 62, (225, 230, 238), -1, cv2.LINE_AA)
    cv2.circle(sample, (90, 90), 25, (40, 155, 230), -1, cv2.LINE_AA)
    alpha, metrics = _round_product_mask(sample, {})
    assert alpha.shape == sample.shape[:2]
    assert metrics["confidence"] >= .55, metrics
    assert alpha[90, 90] > 200 and alpha[2, 2] < 10
    assert any("skin_occlusion_edge_band must be between" in error for error in validate_spec({
        "video": __file__, "start": 0, "end": 1,
        "initial_bbox": [0, 0, 10, 10], "target_kind": "subject_object",
        "evidence": "selftest", "skin_occlusion_edge_band": .9,
    }))
    print("roto_matte self-test GREEN")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build evidence-gated photographed-subject roto mattes")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("spec")
    build.add_argument("--output-dir", required=True)
    sub.add_parser("selftest")
    args = parser.parse_args()
    if args.command == "selftest":
        self_test()
        return 0
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    print(json.dumps(build_sequence(spec, args.output_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
