# -*- coding: utf-8 -*-
"""Tracked kinetic typography and challenge-ledger HUD facade.

This public module preserves the historical imports and CLI while delegating
presentation to :mod:`tracked_graphics_presentation` and video I/O to
:mod:`tracked_graphics_render`.  It owns only validated tracking state, the
public spec boundary, deterministic demo fixtures and command routing.

CLI examples::

    python tracked_graphics.py validate spec.json
    python tracked_graphics.py render spec.json --output tracked.mp4
    python tracked_graphics.py demo --out-dir _runtime/tracked-graphics-demo
    python tracked_graphics.py selftest
"""
from __future__ import annotations

import argparse
import json
import math
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw

from tracked_typography import (
    CURRENCY_RE,
    TEXT_PROFILES,
    font as _font,
    render_text_plate,
)
from tracked_graphics_presentation import (
    SHEEN_MATERIALS,
    _alpha_matte,
    _draw_lock_effect,
    _identity_callout_position,
    _identity_plate,
    _lock_center,
    _position_pixels,
    _sequence_matte,
    _telemetry_plate,
    _verified_sheen_matte,
    _draw_mask_sheen as _presentation_draw_mask_sheen,
    build_track_plate,
    draw_track_runtime,
)
from tracked_graphics_render import (
    _build_render_report,
    _close_alpha_writer,
    _composite_overlay,
    _mux_audio,
    _overlay_frame,
    _prepare_tracking_source,
    _start_alpha_writer,
    _write_contact_sheet,
    _render_frame_range as _render_frame_range_transaction,
    render_spec as _render_spec_transaction,
)
from tracked_graphics_validation import validate_spec as _validate_tracked_spec


MEASURED_VALUE_RE = __import__("re").compile(
    r"(?:\d[\d,.]*\s*(?:mph|km/?h|kph|m/?s|fps|kg|g|cm|mm|m|秒|公里|公尺|公斤))",
    __import__("re").I,
)


def _bbox_pixels(values: list[float], width: int,
                 height: int) -> tuple[float, float, float, float]:
    if len(values) != 4:
        raise ValueError("initial_bbox must contain x, y, width, height")
    x, y, box_width, box_height = [float(value) for value in values]
    if max(abs(x), abs(y), abs(box_width), abs(box_height)) <= 1.5:
        x, y = x * width, y * height
        box_width, box_height = box_width * width, box_height * height
    if box_width < 4 or box_height < 4:
        raise ValueError("initial_bbox is too small")
    x, y = max(0.0, x), max(0.0, y)
    return x, y, min(box_width, width - x), min(box_height, height - y)


def _new_csrt_tracker():
    if hasattr(cv2, "TrackerCSRT_create"):
        return cv2.TrackerCSRT_create()
    if hasattr(cv2, "legacy") and hasattr(cv2.legacy, "TrackerCSRT_create"):
        return cv2.legacy.TrackerCSRT_create()
    raise RuntimeError("OpenCV CSRT tracker is unavailable")


def _keyframed_bbox(config: dict[str, Any], source_time: float,
                    width: int, height: int) -> tuple[float, float, float, float]:
    """Interpolate an editorially verified object box without tracker drift."""
    rows = list(config.get("keyframes") or [])
    if not rows:
        return _bbox_pixels(config["initial_bbox"], width, height)
    rows.sort(key=lambda row: float(row["time"]))
    if source_time <= float(rows[0]["time"]):
        return _bbox_pixels(rows[0]["bbox"], width, height)
    if source_time >= float(rows[-1]["time"]):
        return _bbox_pixels(rows[-1]["bbox"], width, height)
    for left, right in zip(rows, rows[1:]):
        start, end = float(left["time"]), float(right["time"])
        if start <= source_time <= end:
            progress = (source_time - start) / max(.0001, end - start)
            progress = progress * progress * (3.0 - 2.0 * progress)
            box_a = _bbox_pixels(left["bbox"], width, height)
            box_b = _bbox_pixels(right["bbox"], width, height)
            return tuple(
                value_a + (value_b - value_a) * progress
                for value_a, value_b in zip(box_a, box_b)
            )
    return _bbox_pixels(rows[-1]["bbox"], width, height)


@dataclass
class TrackRuntime:
    """Mutable tracker state; presentation is delegated through ``draw``."""

    config: dict[str, Any]
    frame_width: int
    frame_height: int
    tracker: Any = None
    initialized: bool = False
    last_box: tuple[float, float, float, float] | None = None
    smooth_box: tuple[float, float, float, float] | None = None
    lost_frames: int = 0
    base_plate: Image.Image | None = None
    records: list[dict[str, Any]] = field(default_factory=list)

    def initialize(self, frame: np.ndarray) -> None:
        mode = str(self.config.get("tracking_mode", "csrt"))
        if mode == "keyframes":
            box = _keyframed_bbox(
                self.config, float(self.config.get("start", 0)),
                self.frame_width, self.frame_height,
            )
        else:
            box = _bbox_pixels(
                self.config["initial_bbox"], self.frame_width, self.frame_height,
            )
        if mode == "csrt":
            self.tracker = _new_csrt_tracker()
            initialized = self.tracker.init(frame, tuple(int(round(value)) for value in box))
            if initialized is False:
                raise RuntimeError(
                    "CSRT could not initialize track %s" % self.config.get("id", "track")
                )
        self.initialized = True
        self.last_box = self.smooth_box = box
        self.base_plate = build_track_plate(
            self.config, self.frame_width, self.frame_height,
        )

    def update(self, frame: np.ndarray, source_time: float, *,
               first_frame: bool = False) -> tuple[str, float]:
        if str(self.config.get("tracking_mode", "csrt")) == "keyframes":
            box = _keyframed_bbox(
                self.config, source_time, self.frame_width, self.frame_height,
            )
            self.last_box = box
            if str(self.config.get("tracking_source", "")) == "verified_keyframes":
                self.smooth_box = box
            elif self.smooth_box is None:
                self.smooth_box = box
            else:
                previous = self.smooth_box
                old_center = np.array([
                    previous[0] + previous[2] / 2,
                    previous[1] + previous[3] / 2,
                ])
                new_center = np.array([box[0] + box[2] / 2, box[1] + box[3] / 2])
                distance = float(np.linalg.norm(new_center - old_center))
                dead_band = self.frame_height * .0016
                follow = .24 if distance <= self.frame_height * .025 else .38
                if distance <= dead_band:
                    follow = 0.0
                size_follow = .14
                self.smooth_box = tuple(
                    old + (new - old) * (follow if index < 2 else size_follow)
                    for index, (old, new) in enumerate(zip(previous, box))
                )
            return "tracked", 1.0
        if first_frame:
            return "tracked", 1.0
        ok, raw = self.tracker.update(frame)
        if ok:
            raw_box = tuple(float(value) for value in raw)
            x, y, box_width, box_height = raw_box
            plausible = box_width >= 4 and box_height >= 4
            edge_slack = float(self.config.get("edge_slack", .10))
            plausible = plausible and x >= -box_width * edge_slack
            plausible = plausible and y >= -box_height * edge_slack
            plausible = plausible and x + box_width <= self.frame_width + box_width * edge_slack
            plausible = plausible and y + box_height <= self.frame_height + box_height * edge_slack
            if plausible and self.last_box is not None:
                last_x, last_y, last_width, last_height = self.last_box
                old_center = np.array([
                    last_x + last_width / 2, last_y + last_height / 2,
                ])
                new_center = np.array([
                    x + box_width / 2, y + box_height / 2,
                ])
                jump = float(np.linalg.norm(new_center - old_center))
                max_jump = self.frame_height * float(
                    self.config.get("max_center_jump_ratio", .08)
                )
                area_ratio = (box_width * box_height) / max(1.0, last_width * last_height)
                aspect_ratio = (box_width / box_height) / max(.001, last_width / last_height)
                plausible = jump <= max_jump
                plausible = plausible and .68 <= area_ratio <= 1.47
                plausible = plausible and .72 <= aspect_ratio <= 1.39
            if not plausible:
                self.lost_frames += 1
                return self._lost_status()
            self.last_box = raw_box
            self.lost_frames = 0
            if self.smooth_box is None:
                self.smooth_box = raw_box
            else:
                old_center = np.array([
                    self.smooth_box[0] + self.smooth_box[2] / 2,
                    self.smooth_box[1] + self.smooth_box[3] / 2,
                ])
                new_center = np.array([
                    raw_box[0] + raw_box[2] / 2,
                    raw_box[1] + raw_box[3] / 2,
                ])
                distance = float(np.linalg.norm(new_center - old_center))
                base_follow = float(self.config.get("smoothing_follow", .30))
                follow = (
                    min(.42, base_follow * 1.25)
                    if distance > self.frame_height * .03 else base_follow
                )
                size_follow = float(self.config.get("smoothing_size_follow", .18))
                self.smooth_box = tuple(
                    old + (new - old) * (follow if index < 2 else size_follow)
                    for index, (old, new) in enumerate(zip(self.smooth_box, raw_box))
                )
            return "tracked", 1.0
        self.lost_frames += 1
        return self._lost_status()

    def _lost_status(self) -> tuple[str, float]:
        hold = int(self.config.get("lost_hold_frames", 8))
        if self.lost_frames <= hold:
            return "hold", max(.2, 1.0 - self.lost_frames / (hold + 1))
        return "hidden", 0.0

    def active(self, source_time: float) -> bool:
        return (
            float(self.config.get("start", 0))
            <= source_time
            < float(self.config["end"])
        )

    def draw(self, overlay: Image.Image, source_time: float, opacity: float) -> None:
        draw_track_runtime(self, overlay, source_time, opacity)


def validate_spec(spec: dict[str, Any]) -> list[str]:
    """Validate against the public profiles and fail-closed evidence rules."""
    return _validate_tracked_spec(
        spec,
        text_profiles=TEXT_PROFILES,
        sheen_materials=SHEEN_MATERIALS,
        currency_re=CURRENCY_RE,
        measured_value_re=MEASURED_VALUE_RE,
    )


def _draw_mask_sheen(overlay: Image.Image, effect: dict[str, Any],
                     source_time: float, width: int, height: int,
                     frame: np.ndarray | None = None) -> None:
    """Compatibility wrapper binding presentation to verified bbox geometry."""
    _presentation_draw_mask_sheen(
        overlay, effect, source_time, width, height, frame,
        bbox_resolver=_keyframed_bbox,
    )


def _render_frame_range(cap, writer, alpha_proc, runtimes, spec, *,
                        width: int, height: int, fps: float,
                        start_frame: int, end_frame: int,
                        source_time_offset: float = 0.0) -> tuple[int, list[np.ndarray]]:
    """Compatibility wrapper preserving the historical helper signature."""
    return _render_frame_range_transaction(
        cap, writer, alpha_proc, runtimes, spec,
        width=width, height=height, fps=fps,
        start_frame=start_frame, end_frame=end_frame,
        source_time_offset=source_time_offset,
        draw_lock_effect=_draw_lock_effect,
        draw_mask_sheen=_draw_mask_sheen,
    )


def render_spec(spec: dict[str, Any], output: str | Path, *,
                alpha_output: str | Path | None = None,
                track_output: str | Path | None = None,
                qa_sheet: str | Path | None = None) -> dict[str, Any]:
    """Render through the extracted transaction while preserving the API."""
    return _render_spec_transaction(
        spec, output,
        alpha_output=alpha_output,
        track_output=track_output,
        qa_sheet=qa_sheet,
        validate_spec=validate_spec,
        runtime_factory=TrackRuntime,
        draw_lock_effect=_draw_lock_effect,
        draw_mask_sheen=_draw_mask_sheen,
    )


def _make_demo_source(path: Path, *, fps: int = 30,
                      duration: float = 2.8) -> list[tuple[float, float]]:
    width, height = 640, 360
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height),
    )
    truth = []
    for frame_index in range(round(fps * duration)):
        frame = np.full((height, width, 3), (44, 35, 29), dtype=np.uint8)
        for x in range(0, width, 40):
            cv2.line(frame, (x, 0), (x, height), (55, 47, 42), 1)
        for y in range(0, height, 40):
            cv2.line(frame, (0, y), (width, y), (55, 47, 42), 1)
        x = 62 + frame_index * 3.0
        y = 190 + math.sin(frame_index * .10) * 22
        truth.append((x + 48, y + 32))
        cv2.rectangle(
            frame, (round(x), round(y)), (round(x + 96), round(y + 64)),
            (35, 80, 224), -1,
        )
        cv2.rectangle(
            frame, (round(x + 5), round(y + 5)),
            (round(x + 91), round(y + 59)), (235, 185, 43), 4,
        )
        cv2.line(
            frame, (round(x + 10), round(y + 10)),
            (round(x + 86), round(y + 54)), (255, 255, 255), 3,
        )
        cv2.line(
            frame, (round(x + 86), round(y + 10)),
            (round(x + 10), round(y + 54)), (255, 255, 255), 3,
        )
        writer.write(frame)
    writer.release()
    return truth


def build_typography_catalog(path: str | Path) -> Path:
    """Render a review sheet proving CJK, Latin, numeric and mixed-script support."""
    samples = [
        ("挑戰成功", "neon_value_green"),
        ("LEVEL UP", "neon_value_cyan"),
        ("$300,000", "price_white"),
        ("AI 挑戰 #01", "impact_gold"),
    ]
    tile_width, tile_height = 760, 300
    sheet = Image.new("RGBA", (tile_width * 2, tile_height * 2), (10, 13, 20, 255))
    for index, (text, profile) in enumerate(samples):
        tile = Image.new("RGBA", (tile_width, tile_height), (15, 20, 31, 255))
        plate = render_text_plate(text, profile, 118, max_width=tile_width - 50)
        tile.alpha_composite(
            plate,
            ((tile_width - plate.width) // 2, (tile_height - plate.height) // 2),
        )
        ImageDraw.Draw(tile).text(
            (18, 14), profile, font=_font(profile, 20), fill=(151, 169, 195, 255),
        )
        sheet.alpha_composite(
            tile, ((index % 2) * tile_width, (index // 2) * tile_height),
        )
    output = Path(path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(output, quality=94)
    return output


def _demo_spec(source: Path) -> dict[str, Any]:
    return {
        "video": str(source), "start": 0, "end": 2.8,
        "tracked_labels": [{
            "id": "demo-object", "text": "$300,000 / 挑戰成功",
            "profile": "neon_value_green",
            "initial_bbox": [62, 190, 96, 64], "start": 0, "end": 2.8,
            "style": "telemetry_callout", "meaning": "synthetic tracked value proof",
            "panel_offset": [-.16, -.15], "pointer_target": [.5, .5],
            "anchor": "top", "evidence": "synthetic demo ground truth",
        }],
        "mask_sheens": [{
            "id": "demo-sheen", "start": .6, "end": 1.15,
            "initial_bbox": [62, 190, 96, 64],
            "keyframes": [
                {"time": .6, "bbox": [116, 188, 96, 64]},
                {"time": 1.15, "bbox": [166, 172, 96, 64]},
            ],
            "shape": "rectangle", "angle": -28, "band_width": .13,
            "target_kind": "subject_object", "contrast": .18,
            "reveal_mode": "black_to_color", "blackout_opacity": 1.0,
            "subject_class": "product", "material_profile": "plastic_product",
            "evidence": "synthetic demo object matte",
        }],
        "hud": {
            "mode": "ladder", "active_index": 0,
            "events": [
                {"time": .9, "active_index": 1},
                {"time": 1.8, "active_index": 2},
            ],
            "items": [
                {"label": "$1", "evidence": "synthetic demo", "accent": [84, 211, 255]},
                {"label": "$50K", "evidence": "synthetic demo", "accent": [255, 197, 61]},
                {"label": "$300K", "evidence": "synthetic demo", "accent": [105, 255, 113]},
            ],
        },
    }


def build_demo(out_dir: str | Path) -> dict[str, Any]:
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    source = out_dir / "source.mp4"
    truth = _make_demo_source(source)
    spec = _demo_spec(source)
    (out_dir / "spec.json").write_text(
        json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    report = render_spec(
        spec, out_dir / "tracked_graphics_demo.mp4",
        alpha_output=out_dir / "tracked_graphics_overlay.mov",
        track_output=out_dir / "tracking.json",
        qa_sheet=out_dir / "contact_sheet.jpg",
    )
    report["typography_catalog"] = str(
        build_typography_catalog(out_dir / "typography_catalog.jpg")
    )
    tracking = json.loads((out_dir / "tracking.json").read_text(encoding="utf-8"))
    records = tracking["tracks"]["demo-object"]
    errors = []
    for index, record in enumerate(records):
        if not record["bbox"]:
            continue
        x, y, width, height = record["bbox"]
        truth_x, truth_y = truth[min(index, len(truth) - 1)]
        errors.append(math.hypot(x + width / 2 - truth_x, y + height / 2 - truth_y))
    report["demo_mean_track_error_px"] = round(sum(errors) / max(1, len(errors)), 3)
    report_path = out_dir / "report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    report["report_path"] = str(report_path)
    return report


def self_test() -> None:
    assert validate_spec({"video": "missing.mp4", "start": 0, "end": 1})
    invalid = {
        "video": __file__, "start": 0, "end": 1,
        "tracked_labels": [{
            "text": "$100", "initial_bbox": [0, 0, 10, 10],
            "start": 0, "end": 1,
        }],
    }
    assert any("requires evidence" in error for error in validate_spec(invalid))
    with tempfile.TemporaryDirectory(prefix="tracked-graphics-selftest-") as temp:
        report = build_demo(temp)
        assert report["classification"] == "graphic_overlay"
        assert report["is_transition"] is False
        assert report["mask_sheens"]["matte_clip_enforced"] is True
        assert report["mask_sheens"]["full_frame_flash_possible"] is False
        assert report["mask_sheens"]["typography_target_allowed"] is False
        assert report["mask_sheens"]["reveal_modes"] == ["black_to_color"]
        assert report["tracking"]["lost_ratio"] < .15
        assert report["demo_mean_track_error_px"] < 24, report
        for name in (
            "tracked_graphics_demo.mp4", "tracked_graphics_overlay.mov",
            "tracking.json", "contact_sheet.jpg", "typography_catalog.jpg",
        ):
            assert (Path(temp) / name).stat().st_size > 1000
    invalid_text_sheen = {
        "video": __file__, "start": 0, "end": .5,
        "mask_sheens": [{
            "start": 0, "end": .4, "initial_bbox": [0, 0, 40, 40],
            "shape": "rectangle", "subject_class": "typography",
            "target_kind": "typography", "evidence": "negative fixture",
        }],
    }
    assert any(
        "never text" in error or "belongs to text effects" in error
        for error in validate_spec(invalid_text_sheen)
    )
    print("tracked_graphics self-test GREEN")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render tracked typography and challenge-ledger HUD overlays"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("spec")
    render = commands.add_parser("render")
    render.add_argument("spec")
    render.add_argument("--output", required=True)
    render.add_argument("--alpha-output", default="")
    render.add_argument("--track-output", default="")
    render.add_argument("--qa-sheet", default="")
    demo = commands.add_parser("demo")
    demo.add_argument("--out-dir", required=True)
    commands.add_parser("selftest")
    args = parser.parse_args()
    if args.command == "selftest":
        self_test()
        return 0
    if args.command == "demo":
        print(json.dumps(build_demo(args.out_dir), ensure_ascii=False, indent=2))
        return 0
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    errors = validate_spec(spec)
    if args.command == "validate":
        print(json.dumps(
            {"status": "GREEN" if not errors else "RED", "errors": errors},
            ensure_ascii=False, indent=2,
        ))
        return 0 if not errors else 1
    report = render_spec(
        spec, args.output,
        alpha_output=args.alpha_output or None,
        track_output=args.track_output or None,
        qa_sheet=args.qa_sheet or None,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
