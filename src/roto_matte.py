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


def _product_components(binary: np.ndarray) -> np.ndarray:
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
    center_label = int(labels[height // 2, width // 2])
    output = np.zeros_like(binary)
    minimum_area = max(10, round(height * width * .0015))
    for index in range(1, count):
        area = int(stats[index, cv2.CC_STAT_AREA])
        cx, cy = [float(value) for value in centroids[index]]
        nx = (cx - width * .5) / max(1.0, width * .48)
        ny = (cy - height * .5) / max(1.0, height * .48)
        centred = nx * nx + ny * ny <= 1.0
        if index == center_label or (area >= minimum_area and centred):
            output[labels == index] = 255
    return output


def _round_product_mask(crop: np.ndarray, config: dict[str, Any]) -> tuple[np.ndarray, dict[str, float]]:
    height, width = crop.shape[:2]
    outer = _ellipse_mask(height, width, float(config.get("outer_inset", .025)))
    probable = _ellipse_mask(height, width, float(config.get("probable_inset", .075)))
    certain = _ellipse_mask(height, width, float(config.get("certain_inset", .28)))

    gc = np.full((height, width), cv2.GC_BGD, np.uint8)
    gc[outer > 0] = cv2.GC_PR_BGD
    gc[probable > 0] = cv2.GC_PR_FGD
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
    binary = _product_components(binary)

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
    confidence = max(0.0, min(1.0, 1.0 - abs(area_ratio - .62) * 1.4 - border_ratio * 2.0))
    return alpha, {
        "foreground_area_ratio": round(area_ratio, 5),
        "border_contact_ratio": round(border_ratio, 5),
        "confidence": round(confidence, 5),
    }


def _edge_chatter(contours: list[np.ndarray]) -> float:
    """Aligned 256px silhouette-change proxy, not a parity claim."""
    if len(contours) < 2:
        return 0.0
    changes: list[float] = []
    for left, right in zip(contours, contours[1:]):
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
    hsv_bounds = config.get("skin_hsv", [0, 28, 28, 19, 205, 255])
    ycrcb_bounds = config.get("skin_ycrcb", [0, 132, 76, 255, 178, 132])
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
        expected = max(1, round((end - start) * fps))
        rows: list[dict[str, Any]] = []
        raw_masks: list[np.ndarray] = []
        skin_masks: list[np.ndarray] = []
        debug_frames: dict[int, np.ndarray] = {}
        sample_every = max(1, expected // 8)
        for frame_index in range(expected):
            ok, frame = cap.read()
            if not ok:
                break
            source_time = start + frame_index / fps
            x, y, w, h = _keyframed_bbox(spec, source_time, width, height)
            ix, iy = max(0, round(x)), max(0, round(y))
            rw, rh = max(4, min(width - ix, round(w))), max(4, min(height - iy, round(h)))
            crop = frame[iy:iy + rh, ix:ix + rw]
            local_alpha, metrics = _round_product_mask(crop, spec)
            raw_masks.append(cv2.resize(local_alpha, (256, 256), interpolation=cv2.INTER_AREA))
            skin = (_skin_occlusion(crop, spec) if spec.get("exclude_skin_occlusion") is True
                    else np.zeros(crop.shape[:2], np.uint8))
            skin_masks.append(cv2.resize(skin, (256, 256), interpolation=cv2.INTER_AREA))
            if frame_index % sample_every == 0 or frame_index == expected - 1:
                debug_frames[frame_index] = frame.copy()
            rows.append({
                "frame": frame_index, "source_time": round(source_time, 5),
                "bbox": [ix, iy, rw, rh],
                "matte": str(output_dir / f"frame_{frame_index:06d}.png"), **metrics,
            })
        if len(rows) != expected:
            raise RuntimeError(f"matte sequence incomplete: expected {expected}, rendered {len(rows)}")
        return {
            "preparation": preparation, "fps": fps, "width": width, "height": height,
            "rows": rows, "raw_masks": raw_masks, "skin_masks": skin_masks,
            "debug_frames": debug_frames,
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
    return {
        "status": "GREEN" if confidence_p05 >= float(spec.get("minimum_confidence", .55)) else "REVIEW",
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
        "aligned_silhouette_change_px_p95_at_256": _edge_chatter(masks),
        "edge_chatter_metric_status": "PROXY_ONLY_REQUIRES_INDEPENDENT_GROUND_TRUTH",
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
