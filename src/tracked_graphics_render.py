# -*- coding: utf-8 -*-
"""Video I/O transaction for the tracked-graphics facade.

The renderer owns source preparation, frame iteration, alpha writing, final
FFmpeg composition and machine receipts.  Tracking state, spec validation and
presentation policy are injected by :mod:`tracked_graphics`, keeping this
module independent from the public facade and preventing import cycles.
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np
from PIL import Image

from challenge_hud import render_challenge_hud
from visual_master import analyze_media


def _overlay_frame(frame: np.ndarray, overlay: Image.Image) -> np.ndarray:
    background = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
    background.alpha_composite(overlay)
    return cv2.cvtColor(np.asarray(background.convert("RGB")), cv2.COLOR_RGB2BGR)


def _write_contact_sheet(frames: list[np.ndarray], output: Path, columns: int = 3) -> None:
    if not frames:
        return
    thumbnails = []
    for frame in frames:
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        image.thumbnail((480, 270), Image.Resampling.LANCZOS)
        thumbnails.append(image)
    rows = math.ceil(len(thumbnails) / columns)
    sheet = Image.new("RGB", (480 * columns, 270 * rows), (13, 17, 25))
    for index, image in enumerate(thumbnails):
        sheet.paste(image, ((index % columns) * 480, (index // columns) * 270))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def _prepare_tracking_source(source: Path, start: float, duration: float,
                             temp_dir: Path) -> tuple[Path, dict[str, Any]]:
    """Create an upright, display-referred, high-quality tracking segment."""
    analysis = analyze_media(str(source))
    if analysis.get("unknown_log"):
        raise RuntimeError(
            "unknown Log source requires an explicit input transform: " + str(source)
        )
    filters: list[str] = []
    if analysis.get("is_hdr"):
        filters.append(
            "zscale=t=linear:npl=100,format=gbrpf32le,"
            "tonemap=hable:desat=0,zscale=p=bt709:t=bt709:m=bt709:r=tv"
        )
    filters.extend(("setsar=1", "format=yuv422p10le"))
    prepared = temp_dir / "prepared_tracking_source.mov"
    command = [
        "ffmpeg", "-v", "error", "-y", "-i", str(source),
        "-ss", "%.6f" % start, "-t", "%.6f" % duration,
        "-vf", ",".join(filters), "-an", "-c:v", "prores_ks",
        "-profile:v", "3", "-pix_fmt", "yuv422p10le",
        "-metadata:s:v:0", "rotate=0", str(prepared),
    ]
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode:
        raise RuntimeError("tracking source preparation failed: " + result.stderr[-700:])
    return prepared, {
        "display_rotation_applied": True,
        "input_transfer": analysis.get("color_transfer", "unknown"),
        "hdr_to_rec709": bool(analysis.get("is_hdr")),
        "intermediate": "prores_ks_profile_3_yuv422p10le",
        "graphics_stage": "after_input_transform_before_delivery_encode",
    }


def _composite_overlay(base_video: Path, overlay_video: Path, source: Path,
                       start: float, duration: float, output: Path) -> None:
    """Composite the transparent overlay once and restore source audio."""
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-v", "error", "-y", "-i", str(base_video),
        "-i", str(overlay_video), "-ss", "%.6f" % start,
        "-t", "%.6f" % duration, "-i", str(source),
        "-filter_complex", "[0:v][1:v]overlay=shortest=1:format=auto,format=yuv420p[v]",
        "-map", "[v]", "-map", "2:a:0?", "-c:v", "libx264",
        "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        "-shortest", str(output),
    ]
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode:
        raise RuntimeError("tracked overlay composite failed: " + result.stderr[-700:])


def _mux_audio(video_only: Path, source: Path, start: float,
               duration: float, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-v", "error", "-y", "-i", str(video_only),
        "-ss", "%.6f" % start, "-t", "%.6f" % duration, "-i", str(source),
        "-map", "0:v:0", "-map", "1:a:0?", "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(output),
    ]
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode:
        raise RuntimeError("ffmpeg mux failed: " + result.stderr[-700:])


def _start_alpha_writer(path: Path, width: int, height: int, fps: float):
    path.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.Popen([
        "ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba",
        "-s", "%dx%d" % (width, height), "-r", "%.6f" % fps, "-i", "-",
        "-an", "-c:v", "qtrle", "-pix_fmt", "argb", str(path),
    ], stdin=subprocess.PIPE, stderr=subprocess.PIPE)


def _close_alpha_writer(process) -> None:
    if not process or not process.stdin:
        return
    process.stdin.close()
    stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    code = process.wait()
    if code:
        raise RuntimeError("alpha render failed: " + stderr[-700:])


def _render_frame_range(cap, writer, alpha_proc, runtimes, spec, *,
                        width: int, height: int, fps: float,
                        start_frame: int, end_frame: int,
                        source_time_offset: float = 0.0,
                        draw_lock_effect: Callable[..., None],
                        draw_mask_sheen: Callable[..., None]) -> tuple[int, list[np.ndarray]]:
    """Render a bounded frame range using injected fail-closed presentation."""
    qa_frames: list[np.ndarray] = []
    sample_every = max(1, (end_frame - start_frame) // 8)
    written = 0
    for absolute_frame in range(start_frame, end_frame):
        ok, frame = cap.read()
        if not ok:
            break
        source_time = source_time_offset + (absolute_frame - start_frame) / fps
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        for runtime in runtimes:
            if not runtime.active(source_time):
                continue
            first_frame = False
            if not runtime.initialized:
                runtime.initialize(frame)
                first_frame = True
            status, confidence = runtime.update(frame, source_time, first_frame=first_frame)
            runtime.draw(overlay, source_time, confidence)
            box = runtime.smooth_box
            runtime.records.append({
                "frame": round(source_time * fps), "time": round(source_time, 4),
                "status": status, "confidence": round(confidence, 3),
                "bbox": [round(value, 2) for value in box] if box else None,
            })
        for effect in spec.get("lock_effects", []):
            draw_lock_effect(overlay, effect, source_time, width, height)
        for effect in spec.get("mask_sheens", []):
            draw_mask_sheen(overlay, effect, source_time, width, height, frame)
        hud = spec.get("hud")
        if (hud and float(hud.get("start", start_frame / fps)) <= source_time
                < float(hud.get("end", end_frame / fps))):
            overlay.alpha_composite(render_challenge_hud((width, height), hud, source_time))
        composed = _overlay_frame(frame, overlay)
        if writer is not None:
            writer.write(composed)
        if alpha_proc and alpha_proc.stdin:
            alpha_proc.stdin.write(np.asarray(overlay, dtype=np.uint8).tobytes())
        if written % sample_every == 0:
            qa_frames.append(composed.copy())
        written += 1
    return written, qa_frames


def _tracking_report(runtimes, track_records) -> tuple[dict[str, Any], float]:
    total_updates = sum(len(records) for records in track_records.values())
    lost_updates = sum(
        1 for records in track_records.values() for item in records
        if item["status"] != "tracked"
    )
    lost_ratio = lost_updates / max(1, total_updates)
    modes = {str(runtime.config.get("tracking_mode", "csrt")) for runtime in runtimes}
    if modes == {"keyframes"}:
        engine = "verified_keyframes"
    elif "keyframes" in modes:
        engine = "hybrid_csrt_keyframes"
    else:
        engine = "opencv_csrt"
    return {
        "engine": engine, "tracks": len(runtimes),
        "updates": total_updates, "lost_or_held": lost_updates,
        "lost_ratio": round(lost_ratio, 4),
        "failure_policy": "hold_last_valid_for_limited_frames_then_hide; never_guess",
    }, lost_ratio


def _sheen_report(spec: dict[str, Any], sequence_sheens: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(spec.get("mask_sheens", [])),
        "meaning": "high-contrast diagonal material highlight or black-to-colour reveal clipped to a verified photographed subject object; never typography or a full-frame flash",
        "target_kind": "subject_object_only",
        "typography_target_allowed": False,
        "matte_clip_enforced": True,
        "full_frame_flash_possible": False,
        "material_profiles": sorted({
            str(row.get("material_profile", "generic_product"))
            for row in spec.get("mask_sheens", [])
        }),
        "matte_sources": sorted({
            str(row.get("shape", "ellipse")) for row in spec.get("mask_sheens", [])
        }),
        "reveal_modes": sorted({
            str(row.get("reveal_mode", "sheen_only"))
            for row in spec.get("mask_sheens", [])
        }),
        "sequence_receipts": [{
            "effect_id": str(row.get("id", "")),
            "status": str(row.get("matte_quality_status", "")),
            "capability": str(row.get("matte_capability", "")),
            "human_review_status": str(row.get("matte_human_review_status", "")),
            "frames": int(row.get("matte_sequence_frames", 0)),
            "fps": float(row.get("matte_sequence_fps", 0)),
            "report": str(row.get("matte_sequence_report", "")),
            "contact_sheet": str(row.get("matte_sequence_contact_sheet", "")),
            "promotion_blocked_until": list(row.get("matte_promotion_blocked_until") or []),
        } for row in sequence_sheens],
        "qa": "review start, peak and end frame; reject edge leak, drift, occlusion error or subject clipping",
    }


def _build_render_report(source: Path, output: Path, alpha_output: Path | None,
                         spec: dict[str, Any], runtimes, track_records,
                         width: int, height: int, fps: float, written: int,
                         source_preparation: dict[str, Any] | None = None) -> dict[str, Any]:
    tracking, lost_ratio = _tracking_report(runtimes, track_records)
    sequence_sheens = [
        row for row in spec.get("mask_sheens", [])
        if str(row.get("shape", "")) == "sequence"
    ]
    return {
        "status": "GREEN" if tracking["updates"] == 0 or lost_ratio <= .12 else "REVIEW",
        "classification": "graphic_overlay", "is_transition": False,
        "source": str(source), "output": str(output),
        "alpha_output": str(alpha_output) if alpha_output else None,
        "resolution": [width, height], "fps": fps,
        "frames": written, "duration": round(written / fps, 4),
        "source_preparation": source_preparation or {},
        "delivery_encode": {
            "codec": "libx264", "crf": 16, "preset": "slow", "overlay_composites": 1,
        },
        "tracking": tracking,
        "human_review": {
            "required": bool(sequence_sheens),
            "status": "PENDING" if sequence_sheens else "NOT_APPLICABLE",
            "boundary": (
                "machine GREEN validates the tracking/render candidate only; "
                "Hao approval remains required before Quality-95 certification"
            ),
        },
        "hud": {
            "enabled": bool(spec.get("hud")), "mode": (spec.get("hud") or {}).get("mode"),
            "meaning": "stateful challenge record, not decoration or transition",
        },
        "subject_locks": {
            "count": len(spec.get("lock_effects", [])),
            "meaning": "verified arena/object attention lock, never a transition",
        },
        "mask_sheens": _sheen_report(spec, sequence_sheens),
    }


def render_spec(spec: dict[str, Any], output: str | Path, *,
                alpha_output: str | Path | None = None,
                track_output: str | Path | None = None,
                qa_sheet: str | Path | None = None,
                validate_spec: Callable[[dict[str, Any]], list[str]],
                runtime_factory: Callable[[dict[str, Any], int, int], Any],
                draw_lock_effect: Callable[..., None],
                draw_mask_sheen: Callable[..., None]) -> dict[str, Any]:
    """Execute one validated render transaction and return its receipt."""
    errors = validate_spec(spec)
    if errors:
        raise ValueError("invalid tracked-graphics spec: " + "; ".join(errors))
    source = Path(spec["video"]).resolve()
    output = Path(output).resolve()
    start, end = float(spec.get("start", 0)), float(spec["end"])
    duration = end - start
    temp_dir = Path(tempfile.mkdtemp(prefix="tracked-graphics-"))
    prepared_source, source_preparation = _prepare_tracking_source(source, start, duration, temp_dir)
    cap = cv2.VideoCapture(str(prepared_source))
    if not cap.isOpened():
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError("could not open prepared tracking source")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    start_frame, end_frame = 0, round(duration * fps)
    label_configs = []
    for item in spec.get("tracked_labels", []):
        config = dict(item)
        config.setdefault("start", start)
        config.setdefault("end", end)
        label_configs.append(config)
    runtimes = [runtime_factory(config, width, height) for config in label_configs]
    track_records: dict[str, list[dict[str, Any]]] = {
        str(runtime.config.get("id", "track-%d" % index)): runtime.records
        for index, runtime in enumerate(runtimes)
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    requested_alpha = Path(alpha_output).resolve() if alpha_output else None
    overlay_video = requested_alpha or (temp_dir / "tracked_overlay.mov")
    alpha_process = _start_alpha_writer(overlay_video, width, height, fps)
    try:
        written, qa_frames = _render_frame_range(
            cap, None, alpha_process, runtimes, spec,
            width=width, height=height, fps=fps,
            start_frame=start_frame, end_frame=end_frame,
            source_time_offset=start,
            draw_lock_effect=draw_lock_effect,
            draw_mask_sheen=draw_mask_sheen,
        )
    finally:
        cap.release()
        _close_alpha_writer(alpha_process)
    if written < 1:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError("no frames were rendered")
    _composite_overlay(prepared_source, overlay_video, source, start, written / fps, output)
    report = _build_render_report(
        source, output, requested_alpha, spec, runtimes,
        track_records, width, height, fps, written, source_preparation,
    )
    if track_output:
        track_path = Path(track_output).resolve()
        track_path.parent.mkdir(parents=True, exist_ok=True)
        track_path.write_text(
            json.dumps({"report": report, "tracks": track_records}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        report["track_output"] = str(track_path)
    if qa_sheet:
        sheet_path = Path(qa_sheet).resolve()
        _write_contact_sheet(qa_frames, sheet_path)
        report["qa_sheet"] = str(sheet_path)
    shutil.rmtree(temp_dir, ignore_errors=True)
    return report
