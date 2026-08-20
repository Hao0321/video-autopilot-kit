# -*- coding: utf-8 -*-
"""Evidence-gated 2.5D subject/background parallax transition renderer.

The transition separates a photographed foreground subject with a required
per-frame matte, inpaints the background, then moves foreground and background
at different speeds.  Directional blur and restrained chromatic aberration are
limited to the transition peak.  It never substitutes a full-page template.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw

from tracked_graphics import _prepare_tracking_source


def validate_spec(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    duration = float(spec.get("duration", 0))
    if not .20 <= duration <= .45:
        errors.append("duration must be between 0.20 and 0.45 seconds")
    if str(spec.get("direction", "left")) not in {"left", "right"}:
        errors.append("direction must be left or right")
    if not str(spec.get("intent", "")).strip():
        errors.append("editorial intent is required")
    for side in ("outgoing", "incoming"):
        row = spec.get(side) or {}
        if not Path(str(row.get("video", ""))).is_file():
            errors.append(f"{side}.video does not exist")
        if float(row.get("start", -1)) < 0:
            errors.append(f"{side}.start must be non-negative")
        if str(row.get("target_kind", "subject_object")) != "subject_object":
            errors.append(f"{side}.target_kind must be subject_object")
        if not Path(str(row.get("matte_sequence_dir", ""))).is_dir():
            errors.append(f"{side}.matte_sequence_dir does not exist")
        if float(row.get("matte_sequence_fps", 0)) <= 0:
            errors.append(f"{side}.matte_sequence_fps must be positive")
        if not str(row.get("evidence", "")).strip():
            errors.append(f"{side}.evidence is required")
    if not 0.0 <= float(spec.get("chromatic_peak", .006)) <= .014:
        errors.append("chromatic_peak must be between 0 and 0.014 frame widths")
    return errors


def _load_matte(row: dict[str, Any], source_time: float,
                width: int, height: int) -> np.ndarray:
    fps = float(row["matte_sequence_fps"])
    sequence_start = float(row["matte_sequence_start"])
    index = max(0, int(math.floor((source_time - sequence_start) * fps + 1e-6)))
    path = Path(row["matte_sequence_dir"]) / f"frame_{index:06d}.png"
    if not path.is_file():
        raise RuntimeError(f"missing required transition matte: {path}")
    alpha = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if alpha is None:
        raise RuntimeError(f"could not read transition matte: {path}")
    if alpha.shape != (height, width):
        alpha = cv2.resize(alpha, (width, height), interpolation=cv2.INTER_LANCZOS4)
    return alpha.astype(np.float32) / 255.0


def _read_side(row: dict[str, Any], duration: float, temp_dir: Path) -> tuple[list[np.ndarray], list[np.ndarray], float, dict[str, Any]]:
    source = Path(row["video"]).resolve()
    start = float(row["start"])
    temp_dir.mkdir(parents=True, exist_ok=True)
    prepared, preparation = _prepare_tracking_source(source, start, duration, temp_dir)
    cap = cv2.VideoCapture(str(prepared))
    if not cap.isOpened():
        raise RuntimeError(f"could not open prepared transition side: {source}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30)
    frames: list[np.ndarray] = []
    mattes: list[np.ndarray] = []
    # The prepared clip is half-open [start, start+duration); floor matches
    # FFmpeg's frame ownership and avoids inventing a tenth frame at 0.32s/30.
    expected = max(2, int(math.floor(duration * fps + 1e-6)))
    try:
        for index in range(expected):
            ok, frame = cap.read()
            if not ok:
                break
            h, w = frame.shape[:2]
            frames.append(frame)
            mattes.append(_load_matte(row, start + index / fps, w, h))
    finally:
        cap.release()
    if len(frames) != expected:
        raise RuntimeError(f"transition side incomplete: expected {expected}, got {len(frames)}")
    return frames, mattes, fps, preparation


def _inpaint_background(frame: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    mask = np.where(alpha > .08, 255, 0).astype(np.uint8)
    radius = max(5, round(min(frame.shape[:2]) * .012))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (radius * 2 + 1, radius * 2 + 1))
    mask = cv2.dilate(mask, kernel)
    return cv2.inpaint(frame, mask, max(3, radius // 2), cv2.INPAINT_TELEA)


def _warp(image: np.ndarray, scale: float, shift_x: float, shift_y: float,
          *, border: int = cv2.BORDER_REFLECT_101) -> np.ndarray:
    h, w = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((w * .5, h * .5), 0, scale)
    matrix[0, 2] += shift_x
    matrix[1, 2] += shift_y
    return cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=border)


def _layer_frame(frame: np.ndarray, alpha: np.ndarray, *,
                 bg_scale: float, bg_shift: float,
                 fg_scale: float, fg_shift: float,
                 blur_pixels: int) -> np.ndarray:
    background = _inpaint_background(frame, alpha)
    background = _warp(background, bg_scale, bg_shift, 0)
    if blur_pixels > 1:
        kernel = max(3, blur_pixels | 1)
        background = cv2.GaussianBlur(background, (kernel, 1), 0)
    foreground = _warp(frame, fg_scale, fg_shift, 0, border=cv2.BORDER_CONSTANT)
    warped_alpha = _warp(alpha, fg_scale, fg_shift, 0, border=cv2.BORDER_CONSTANT)
    warped_alpha = np.clip(warped_alpha, 0, 1)[..., None]
    return np.clip(background.astype(np.float32) * (1 - warped_alpha) +
                   foreground.astype(np.float32) * warped_alpha, 0, 255).astype(np.uint8)


def _chromatic(frame: np.ndarray, pixels: int) -> np.ndarray:
    if pixels <= 0:
        return frame
    output = frame.copy()
    output[:, :, 2] = np.roll(frame[:, :, 2], pixels, axis=1)
    output[:, :, 0] = np.roll(frame[:, :, 0], -pixels, axis=1)
    output[:, :pixels, 0] = frame[:, :pixels, 0]
    output[:, -pixels:, 2] = frame[:, -pixels:, 2]
    return output


def _contact_sheet(frames: list[np.ndarray], path: Path) -> None:
    picks = [frames[0], frames[len(frames) // 2], frames[-1]]
    thumbs = []
    for frame in picks:
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        image.thumbnail((360, 640), Image.Resampling.LANCZOS)
        thumbs.append(image)
    sheet = Image.new("RGB", (sum(x.width for x in thumbs), max(x.height for x in thumbs)), (10, 14, 22))
    x = 0
    for label, image in zip(("OUT", "PEAK", "IN"), thumbs):
        sheet.paste(image, (x, 0))
        ImageDraw.Draw(sheet).text((x + 12, 12), label, fill=(255, 255, 255))
        x += image.width
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, quality=94)


def render(spec: dict[str, Any], output: str | Path, *,
           report_path: str | Path | None = None,
           qa_sheet: str | Path | None = None) -> dict[str, Any]:
    errors = validate_spec(spec)
    if errors:
        raise ValueError("invalid parallax transition spec: " + "; ".join(errors))
    duration = float(spec["duration"])
    direction = -1 if spec.get("direction", "left") == "left" else 1
    temp = Path(tempfile.mkdtemp(prefix="parallax-transition-"))
    try:
        out_frames, out_masks, out_fps, out_prep = _read_side(spec["outgoing"], duration, temp / "out")
        in_frames, in_masks, in_fps, in_prep = _read_side(spec["incoming"], duration, temp / "in")
        fps = min(out_fps, in_fps)
        count = min(len(out_frames), len(in_frames),
                    max(2, int(math.floor(duration * fps + 1e-6))))
        h, w = out_frames[0].shape[:2]
        if in_frames[0].shape[:2] != (h, w):
            raise RuntimeError("incoming and outgoing prepared resolutions differ")
        rendered: list[np.ndarray] = []
        max_delta = 0.0
        for index in range(count):
            t = index / max(1, count - 1)
            ease = t * t * (3 - 2 * t)
            peak = math.sin(math.pi * t) ** 2
            bg_travel = w * float(spec.get("background_travel", .075))
            fg_travel = w * float(spec.get("foreground_travel", .145))
            blur = round(w * float(spec.get("blur_peak", .018)) * peak)
            outgoing = _layer_frame(
                out_frames[index], out_masks[index],
                bg_scale=1 + .035 * ease, bg_shift=direction * -bg_travel * ease,
                fg_scale=1 + .060 * ease, fg_shift=direction * -fg_travel * ease,
                blur_pixels=blur,
            )
            incoming = _layer_frame(
                in_frames[index], in_masks[index],
                bg_scale=1 + .035 * (1 - ease), bg_shift=direction * bg_travel * (1 - ease),
                fg_scale=1 + .060 * (1 - ease), fg_shift=direction * fg_travel * (1 - ease),
                blur_pixels=blur,
            )
            # A fast parallax cut is not a dissolve.  Crossfading two isolated
            # products creates a cheap double-subject ghost.  Switch the sharp
            # foreground at the midpoint while the background carries the
            # velocity/blur, matching the editorial grammar of the reference.
            mixed = outgoing if t < .5 else incoming
            lift = float(spec.get("exposure_lift_peak", .055)) * peak
            if lift > 0:
                mixed = np.clip(mixed.astype(np.float32) * (1.0 + lift) + 255.0 * lift * .12,
                                0, 255).astype(np.uint8)
            chroma = round(w * float(spec.get("chromatic_peak", .006)) * peak)
            mixed = _chromatic(mixed, chroma)
            rendered.append(mixed)
            max_delta = max(max_delta, abs(fg_travel - bg_travel) * peak)

        frames_dir = temp / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        for index, frame in enumerate(rendered):
            cv2.imwrite(str(frames_dir / f"frame_{index:06d}.png"), frame,
                        [cv2.IMWRITE_PNG_COMPRESSION, 3])
        output = Path(output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-framerate", f"{fps:.6f}", "-i", str(frames_dir / "frame_%06d.png"),
            "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(output),
        ], check=True)
        if qa_sheet:
            _contact_sheet(rendered, Path(qa_sheet).resolve())
        lumas = [float(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean()) for frame in rendered]
        report = {
            "status": "GREEN" if min(lumas) > 3 and max_delta >= w * .035 else "REVIEW",
            "capability": "AUTO_WITH_REVIEW",
            "classification": "subject_background_parallax_transition",
            "is_full_page_template": False,
            "foreground_requires_verified_matte": True,
            "duration": round(count / fps, 4), "fps": fps, "frames": count,
            "resolution": [w, h], "output": str(output),
            "parallax_delta_peak_px": round(max_delta, 2),
            "black_frame_ratio": round(sum(value < 3 for value in lumas) / len(lumas), 4),
            "chromatic_peak_frames_only": True,
            "motion_blur_scope": "background_dominant",
            "foreground_cut_policy": "midpoint_hard_handoff_no_double_subject_dissolve",
            "source_preparation": {"outgoing": out_prep, "incoming": in_prep},
            "promotion_blocked_until": ["edge_QA_pass", "motion_taste_review", "Hao_approval"],
            "qa_sheet": str(Path(qa_sheet).resolve()) if qa_sheet else None,
        }
        if report_path:
            path = Path(report_path).resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def self_test() -> None:
    bad = {"duration": 1.0, "intent": "", "outgoing": {}, "incoming": {}}
    assert validate_spec(bad)
    print("parallax_transition self-test GREEN")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render subject/background 2.5D parallax transitions")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest")
    validate = sub.add_parser("validate")
    validate.add_argument("spec")
    run = sub.add_parser("render")
    run.add_argument("spec")
    run.add_argument("--output", required=True)
    run.add_argument("--report", default="")
    run.add_argument("--qa-sheet", default="")
    args = parser.parse_args()
    if args.command == "selftest":
        self_test()
        return 0
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    if args.command == "validate":
        errors = validate_spec(spec)
        print(json.dumps({"status": "GREEN" if not errors else "RED", "errors": errors}, ensure_ascii=False, indent=2))
        return 0 if not errors else 1
    print(json.dumps(render(spec, args.output, report_path=args.report or None,
                            qa_sheet=args.qa_sheet or None), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
