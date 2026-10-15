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


from roto_mask_geometry import (
    _ellipse_mask,
    _ellipse_mask_at,
    _detail_seed_center,
    _radial_product_prior,
    _component_at_center,
    _product_components,
    _radial_material_hull,
    _polar_outer_silhouette,
    _round_product_mask,
    _centroid_aligned,
    _edge_chatter,
    _skin_occlusion,
)


def _debug_overlay(frame: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    strength = (alpha.astype(np.float32) / 255.0 * .48)[..., None]
    tint = np.zeros_like(frame, dtype=np.float32)
    tint[:, :, 0] = 255  # cyan in BGR
    tint[:, :, 1] = 220
    out = frame.astype(np.float32) * (1.0 - strength) + tint * strength
    edges = cv2.Canny(alpha, 80, 160)
    out[edges > 0] = (30, 255, 255)
    return np.clip(out, 0, 255).astype(np.uint8)


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
