"""Roto mask geometry; one implementation behind the compatibility facade."""
from __future__ import annotations

import math
from typing import Any
import cv2
import numpy as np


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
