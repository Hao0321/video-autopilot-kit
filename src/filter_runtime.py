# -*- coding: utf-8 -*-
"""Unified, evidence-gated filter library for long-form and short-form edits."""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from filter_primitives import (apply_subject, apply_temporal,
                               composite_transition, supported_styles)
from filter_renderers import (dependencies, media_info, render_grade,
                              render_subject, render_temporal,
                              render_transition, write_report)
from filter_materials import (load_library as load_material_library,
                              resolve_material)


ROOT = Path(__file__).resolve().parent
_PROJECT_KNOWLEDGE = ROOT / "knowledge"
_PUBLIC_KNOWLEDGE = ROOT.parent / "knowledge" / "runtime"
KNOWLEDGE_ROOT = (_PROJECT_KNOWLEDGE if _PROJECT_KNOWLEDGE.exists() else
                  _PUBLIC_KNOWLEDGE)
LIBRARY_PATH = KNOWLEDGE_ROOT / "filter_library.json"
CATEGORIES = {"grade", "temporal", "transition", "subject"}
FILTER_CONTRACT = {
    "grade": "one_grade_look_only",
    "auto_policy": "manual_or_evidence",
    "fallback": "clean_cut",
    "subject": "verified_subject_matte",
}


def load_library() -> dict[str, Any]:
    return json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))


def validate_library(library: dict[str, Any] | None = None) -> list[dict[str, str]]:
    data = library or load_library()
    errors: list[dict[str, str]] = []

    def fail(code: str, path: str, message: str) -> None:
        errors.append({"code": code, "path": path, "message": message})

    if data.get("schema_version") != 1:
        fail("schema", "schema_version", "must equal 1")
    presets = data.get("presets")
    if not isinstance(presets, dict) or not presets:
        fail("required", "presets", "non-empty object required")
        return errors
    style_catalog = supported_styles()
    grade_profiles = json.loads(
        (KNOWLEDGE_ROOT / "color_grading_profiles.json").read_text(encoding="utf-8")
    )["profiles"]
    for preset_id, preset in presets.items():
        path = f"presets.{preset_id}"
        category = preset.get("category")
        if category not in CATEGORIES:
            fail("category", path + ".category", f"unsupported category: {category}")
            continue
        if not str(preset.get("label_zh", "")).strip():
            fail("label", path + ".label_zh", "label required")
        default = float(preset.get("default_strength", -1))
        ceiling = float(preset.get("max_strength", -1))
        if not 0 <= default <= ceiling <= 1:
            fail("strength", path, "require 0 <= default_strength <= max_strength <= 1")
        renderer = preset.get("renderer")
        if category == "grade":
            if renderer != "visual_master" or preset.get("profile") not in grade_profiles:
                fail("grade", path, "grade must route to an existing Visual Master profile")
        else:
            style = str(preset.get("style", ""))
            if style not in style_catalog[category]:
                fail("style", path + ".style", f"unsupported {category} style: {style}")
        if category == "transition":
            if not preset.get("requires") or not str(preset.get("motivation", "")).strip():
                fail("evidence", path, "transition requires evidence and motivation")
        if category == "subject" and "verified_subject_matte" not in (preset.get("requires") or []):
            fail("matte", path, "subject filter must require verified_subject_matte")
        if preset.get("material_required"):
            material_id = str(preset.get("material_id", ""))
            if not material_id:
                fail("material", path + ".material_id", "material_required needs material_id")
            elif material_id not in load_material_library().get("materials", {}):
                fail("material", path + ".material_id", "unknown filter material")
    return errors


def _preset_material(preset: dict[str, Any], *, allow_pending: bool = False,
                     variant: int = 0) -> tuple[np.ndarray | None, dict[str, Any] | None]:
    material_id = preset.get("material_id")
    if not material_id:
        return None, None
    result = resolve_material(str(material_id), allow_pending=allow_pending,
                              variant=variant)
    image = result.pop("image", None)
    if preset.get("material_required") and image is None:
        raise ValueError(
            f"{preset['id']} requires reviewed material {material_id}; "
            "run Imagegen, register it in Asset Workshop and obtain Hao approval"
        )
    return image, result


def catalog(category: str | None = None, domain: str | None = None) -> list[dict[str, Any]]:
    rows = []
    for preset_id, preset in load_library()["presets"].items():
        if category and preset["category"] != category:
            continue
        if domain and domain not in preset.get("domains", []):
            continue
        rows.append({"id": preset_id, **preset})
    return sorted(rows, key=lambda row: (row["category"], row["id"]))


def get_preset(preset_id: str) -> dict[str, Any]:
    preset = load_library()["presets"].get(str(preset_id))
    if preset is None:
        raise KeyError(f"unknown filter preset: {preset_id}")
    return {"id": preset_id, **preset}


def resolve_strength(preset: dict[str, Any], strength: float | None) -> float:
    value = float(preset["default_strength"] if strength is None else strength)
    return max(0.0, min(float(preset["max_strength"]), value))


def resolve_transition(preset_id: str, evidence: list[str] | set[str],
                       motivation: str, *, manual_approved: bool = False) -> dict[str, Any]:
    preset = get_preset(preset_id)
    if preset["category"] != "transition":
        raise ValueError(f"{preset_id} is not a transition filter")
    available = set(evidence or [])
    missing = [value for value in preset.get("requires", []) if value not in available]
    approved = bool(str(motivation).strip()) and (manual_approved or not missing)
    return {"requested": preset_id, "selected": preset_id if approved else "clean_cut",
            "status": "READY" if approved else "DOWNGRADED", "missing": missing,
            "motivation": str(motivation).strip(),
            "reason": preset["motivation"], "manual_approved": bool(manual_approved)}


def plan_filter_system(domain: str, format_kind: str,
                       grade_profile: str) -> dict[str, Any]:
    """Return compact candidates; this is not permission to render them."""
    temporal = [row["id"] for row in catalog("temporal", domain)][:4]
    transitions = [row["id"] for row in catalog("transition", domain)][:4]
    subjects = [row["id"] for row in catalog("subject", domain)][:4]
    return {
        "library": load_library()["library_id"], "version": load_library()["version"],
        "scope": "all_formats_all_domains", "format": format_kind, "domain": domain,
        "grade": grade_profile, "temporal_candidates": temporal,
        "transition_candidates": transitions, "subject_candidates": subjects,
        "auto_selected": [], "fallback": "clean_cut",
        "selection_rule": "manual_or_evidence; candidates are never render permission",
        "grade_rule": "one_grade_look_only; source_before_graphics",
        "subject_rule": "verified_subject_matte required",
    }


def _render_apply(args: argparse.Namespace) -> dict[str, Any]:
    preset = get_preset(args.preset)
    strength = resolve_strength(preset, args.strength)
    options = {"start": args.start, "duration": args.duration,
               "width": args.width, "height": args.height}
    if preset["category"] == "grade":
        return render_grade(args.input, args.output, preset["profile"], strength,
                            **options)
    if preset["category"] == "temporal":
        material, material_status = _preset_material(
            preset, allow_pending=bool(getattr(args, "allow_pending_materials", False)),
            variant=args.seed,
        )
        return render_temporal(args.input, args.output, preset["style"], strength,
                               seed=args.seed, material=material,
                               material_status=material_status, **options)
    if preset["category"] == "subject":
        if not args.matte:
            raise ValueError("subject filter requires --matte with an editor-verified mask")
        return render_subject(args.input, args.matte, args.output, preset["style"],
                              strength, **options)
    raise ValueError("transition filters use the transition command with two inputs")


def _render_transition(args: argparse.Namespace) -> dict[str, Any]:
    decision = resolve_transition(args.preset, args.evidence, args.motivation,
                                  manual_approved=args.manual_approved)
    if decision["selected"] == "clean_cut":
        raise ValueError("transition evidence gate downgraded to clean_cut: " +
                         ", ".join(decision["missing"]))
    preset = get_preset(args.preset)
    material, material_status = _preset_material(
        preset, allow_pending=bool(getattr(args, "allow_pending_materials", False)),
        variant=args.seed,
    )
    report = render_transition(args.outgoing, args.incoming, args.output,
                               preset["style"], resolve_strength(preset, args.strength),
                               duration=args.duration or preset["recommended_duration"],
                               width=args.width, height=args.height, seed=args.seed,
                               material=material, material_status=material_status)
    report["decision"] = decision
    return report


def _video_frame(path: str | Path, width: int, height: int,
                 fraction: float = 0.0) -> np.ndarray:
    cap = cv2.VideoCapture(str(path))
    frame_count = max(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
    target = round(max(0.0, min(1.0, fraction)) * (frame_count - 1))
    cap.set(cv2.CAP_PROP_POS_FRAMES, target)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise ValueError(f"cannot decode preview frame: {path}")
    from filter_primitives import fit_cover
    return fit_cover(frame, width, height)


def _first_frame(path: str | Path, width: int, height: int) -> np.ndarray:
    return _video_frame(path, width, height, 0.0)


def _contact_sheet(source: str | Path, output: Path, width: int = 360,
                   height: int = 640, *, allow_pending: bool = False) -> dict[str, Any]:
    base = _first_frame(source, width, height)
    rows = catalog("temporal")
    cells = []
    for index, preset in enumerate(rows):
        material, _ = _preset_material(preset, allow_pending=allow_pending,
                                       variant=321 + index)
        cell = apply_temporal(base, preset["style"], 0.5,
                              resolve_strength(preset, None), seed=321 + index,
                              material=material)
        cv2.rectangle(cell, (0, height - 42), (width, height), (12, 12, 12), -1)
        cv2.putText(cell, preset["id"], (12, height - 14), cv2.FONT_HERSHEY_SIMPLEX,
                    0.56, (255, 255, 255), 1, cv2.LINE_AA)
        cells.append(cell)
    columns = 3
    rows_count = (len(cells) + columns - 1) // columns
    sheet = np.full((rows_count * height, columns * width, 3), 24, np.uint8)
    for index, cell in enumerate(cells):
        y, x = divmod(index, columns)
        sheet[y * height:(y + 1) * height, x * width:(x + 1) * width] = cell
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), sheet, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return {"output": str(output), "presets": [row["id"] for row in rows],
            "size": [sheet.shape[1], sheet.shape[0]]}


def _clip_contact_sheet(items: list[tuple[str, Path]], output: Path,
                        width: int, height: int,
                        fraction: float = 0.0) -> dict[str, Any]:
    cells = []
    for preset_id, path in items:
        cell = _video_frame(path, width, height, fraction)
        cv2.rectangle(cell, (0, height - 42), (width, height), (12, 12, 12), -1)
        cv2.putText(cell, preset_id, (12, height - 14), cv2.FONT_HERSHEY_SIMPLEX,
                    0.56, (255, 255, 255), 1, cv2.LINE_AA)
        cells.append(cell)
    columns = 3
    row_count = (len(cells) + columns - 1) // columns
    sheet = np.full((row_count * height, columns * width, 3), 24, np.uint8)
    for index, cell in enumerate(cells):
        row, column = divmod(index, columns)
        sheet[row * height:(row + 1) * height,
              column * width:(column + 1) * width] = cell
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), sheet, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return {"output": str(output), "presets": [item[0] for item in items],
            "size": [sheet.shape[1], sheet.shape[0]]}


def _showcase_label(frame: np.ndarray, category: str, preset_id: str) -> np.ndarray:
    canvas = frame.copy()
    label = f"{category.upper()}  {preset_id}"
    font, scale, thickness = cv2.FONT_HERSHEY_SIMPLEX, 0.46, 1
    (text_width, _), _ = cv2.getTextSize(label, font, scale, thickness)
    overlay = canvas.copy()
    cv2.rectangle(overlay, (12, 14), (36 + text_width, 50), (10, 10, 10), -1)
    cv2.addWeighted(overlay, 0.72, canvas, 0.28, 0.0, canvas)
    accent = {"grade": (70, 205, 255), "temporal": (255, 188, 64),
              "transition": (96, 108, 255)}.get(category, (245, 245, 245))
    cv2.rectangle(canvas, (12, 14), (17, 50), accent, -1)
    cv2.putText(canvas, label, (25, 38), font, scale, (250, 250, 250),
                thickness, cv2.LINE_AA)
    return canvas


def _build_showcase(items: list[tuple[str, str, Path]], output: Path,
                    width: int, height: int, music: str | None) -> dict[str, Any]:
    fps = 30.0
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hao-filter-showcase-") as temp_dir:
        video_only = Path(temp_dir) / "showcase-video.mp4"
        writer = cv2.VideoWriter(str(video_only), cv2.VideoWriter_fourcc(*"mp4v"),
                                 fps, (width, height))
        if not writer.isOpened():
            raise RuntimeError("cannot open showcase video writer")
        total_frames = 0
        try:
            for category, preset_id, path in items:
                cap = cv2.VideoCapture(str(path))
                while True:
                    ok, frame = cap.read()
                    if not ok:
                        break
                    from filter_primitives import fit_cover
                    writer.write(_showcase_label(
                        fit_cover(frame, width, height), category, preset_id))
                    total_frames += 1
                cap.release()
        finally:
            writer.release()
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                   "-i", str(video_only)]
        music_path = Path(music) if music else None
        if music_path and music_path.exists():
            command.extend(["-stream_loop", "-1", "-i", str(music_path),
                            "-filter_complex", "[1:a]volume=0.13,"
                            "afade=t=in:st=0:d=0.35[a]", "-map", "0:v:0",
                            "-map", "[a]", "-shortest", "-c:a", "aac",
                            "-b:a", "160k"])
        else:
            command.append("-an")
        command.extend(["-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        str(output)])
        run = subprocess.run(command, capture_output=True, text=True,
                             encoding="utf-8", errors="replace")
        if run.returncode:
            raise RuntimeError("showcase FFmpeg failed: " + (run.stderr or "")[-800:])
    return {"output": str(output), "items": len(items),
            "duration": round(total_frames / fps, 3),
            "music": str(music_path) if music_path and music_path.exists() else None}


def _write_catalog(destination: Path, report: dict[str, Any]) -> Path:
    data = load_library()
    lines = ["# Hao Filter Library v2", "",
             "Grade、動態濾鏡、轉場與主體濾鏡共用同一註冊表。",
             "調色永遠位於 source 階段；轉場需剪輯動機或完整證據；主體濾鏡需已驗證 matte。", ""]
    for category in ("grade", "temporal", "transition", "subject"):
        lines.extend([f"## {category.title()}", ""])
        for preset in catalog(category):
            lines.append(f"- `{preset['id']}` — {preset['label_zh']}")
        lines.append("")
    path = destination / "FILTER_LIBRARY.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _render_gallery(args: argparse.Namespace) -> dict[str, Any]:
    destination = Path(args.output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"status": "GREEN", "library": load_library()["library_id"],
                              "contact_sheet": _contact_sheet(
                                  args.source, destination / "filter_contact_sheet.jpg",
                                  allow_pending=args.allow_pending_materials),
                              "grade": [], "temporal": [], "transitions": []}
    grade_items: list[tuple[str, Path]] = []
    for preset in catalog("grade"):
        output = destination / "grade" / f"{preset['id']}.mp4"
        result = render_grade(args.source, output, preset["profile"],
                              resolve_strength(preset, None), start=args.start,
                              duration=args.clip_duration, width=args.width,
                              height=args.height)
        report["grade"].append(result)
        grade_items.append((preset["id"], output))
    report["grade_contact_sheet"] = _clip_contact_sheet(
        grade_items, destination / "grade_contact_sheet.jpg",
        args.width, args.height)
    for preset in catalog("temporal"):
        material, material_status = _preset_material(
            preset, allow_pending=args.allow_pending_materials,
            variant=args.seed + len(report["temporal"]),
        )
        output = destination / "temporal" / f"{preset['id']}.mp4"
        result = render_temporal(args.source, output, preset["style"],
                                 resolve_strength(preset, None), start=args.start,
                                 duration=args.clip_duration, width=args.width,
                                 height=args.height, seed=args.seed,
                                 material=material, material_status=material_status)
        report["temporal"].append(result)
    if args.source_b:
        transition_items: list[tuple[str, Path]] = []
        for preset in catalog("transition"):
            material, material_status = _preset_material(
                preset, allow_pending=args.allow_pending_materials,
                variant=args.seed + len(report["transitions"]),
            )
            output = destination / "transitions" / f"{preset['id']}.mp4"
            result = render_transition(args.source, args.source_b, output,
                                       preset["style"], resolve_strength(preset, None),
                                       duration=preset["recommended_duration"],
                                       width=args.width, height=args.height, seed=args.seed,
                                       material=material,
                                       material_status=material_status)
            report["transitions"].append(result)
            transition_items.append((preset["id"], output))
        report["transition_contact_sheet"] = _clip_contact_sheet(
            transition_items, destination / "transition_contact_sheet.jpg",
            args.width, args.height, fraction=0.5)
    showcase_items = []
    for category in ("grade", "temporal", "transition"):
        media_folder = "transitions" if category == "transition" else category
        for preset in catalog(category):
            path = destination / media_folder / f"{preset['id']}.mp4"
            if path.exists():
                showcase_items.append((category, preset["id"], path))
    report["showcase"] = _build_showcase(
        showcase_items, destination / "current.mp4", args.width, args.height,
        args.music)
    report["catalog"] = str(_write_catalog(destination, report))
    write_report(report, destination / "gallery_report.json")
    return report


def self_test() -> None:
    errors = validate_library()
    assert not errors, errors
    frame = np.zeros((160, 96, 3), np.uint8)
    frame[:, :48] = (30, 120, 240)
    frame[:, 48:] = (210, 90, 30)
    other = np.flip(frame, axis=1).copy()
    material = np.full_like(frame, 180)
    cv2.circle(material, (48, 80), 42, (255, 180, 70), -1)
    matte = np.zeros((160, 96), np.uint8)
    cv2.circle(matte, (48, 80), 30, 255, -1)
    for style in supported_styles()["temporal"]:
        assert apply_temporal(frame, style, 0.5, 0.6,
                              material=material).shape == frame.shape
    for style in supported_styles()["transition"]:
        assert composite_transition(frame, other, style, 0.5, 0.7,
                                    material=material).shape == frame.shape
    for style in supported_styles()["subject"]:
        assert apply_subject(frame, matte, style, 0.5, 0.7).shape == frame.shape
    decision = resolve_transition("torn_paper_vertical", [], "")
    assert decision["selected"] == "clean_cut"
    decision = resolve_transition("torn_paper_vertical", [], "manual review",
                                  manual_approved=True)
    assert decision["selected"] == "torn_paper_vertical"
    counts = {category: len(catalog(category)) for category in CATEGORIES}
    assert sum(counts.values()) >= 30 and counts["transition"] >= 8
    assert dependencies()["ffmpeg"]
    print("filter_runtime self-test GREEN " + json.dumps(counts, ensure_ascii=False))


def _add_media_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--strength", type=float)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--seed", type=int, default=321)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hao unified filter library")
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list")
    listing.add_argument("--category", choices=sorted(CATEGORIES))
    listing.add_argument("--domain")
    listing.add_argument("--json", action="store_true")
    inspect_parser = sub.add_parser("inspect")
    inspect_parser.add_argument("preset")
    apply_parser = sub.add_parser("apply")
    apply_parser.add_argument("input")
    apply_parser.add_argument("output")
    apply_parser.add_argument("--preset", required=True)
    apply_parser.add_argument("--matte")
    apply_parser.add_argument("--start", type=float, default=0.0)
    apply_parser.add_argument("--duration", type=float)
    apply_parser.add_argument("--report")
    apply_parser.add_argument("--allow-pending-materials", action="store_true",
                              help="candidate preview only; never production")
    _add_media_options(apply_parser)
    transition_parser = sub.add_parser("transition")
    transition_parser.add_argument("outgoing")
    transition_parser.add_argument("incoming")
    transition_parser.add_argument("output")
    transition_parser.add_argument("--preset", required=True)
    transition_parser.add_argument("--duration", type=float)
    transition_parser.add_argument("--motivation", required=True)
    transition_parser.add_argument("--evidence", action="append", default=[])
    transition_parser.add_argument("--manual-approved", action="store_true")
    transition_parser.add_argument("--report")
    transition_parser.add_argument("--allow-pending-materials", action="store_true",
                                   help="candidate preview only; never production")
    _add_media_options(transition_parser)
    gallery = sub.add_parser("gallery")
    gallery.add_argument("source")
    gallery.add_argument("output_dir")
    gallery.add_argument("--source-b")
    gallery.add_argument("--start", type=float, default=0.0)
    gallery.add_argument("--clip-duration", type=float, default=0.7)
    gallery.add_argument("--width", type=int, default=360)
    gallery.add_argument("--height", type=int, default=640)
    gallery.add_argument("--seed", type=int, default=321)
    gallery.add_argument("--music")
    gallery.add_argument("--allow-pending-materials", action="store_true",
                         help="render unapproved Imagegen boards for Hao review only")
    sub.add_parser("selftest")
    sub.add_parser("doctor")
    args = parser.parse_args(argv)
    if args.command == "selftest":
        self_test()
        return 0
    if args.command == "doctor":
        report = {"status": "GREEN" if not validate_library() else "BLOCK",
                  "errors": validate_library(), "dependencies": dependencies(),
                  "counts": {value: len(catalog(value)) for value in CATEGORIES}}
    elif args.command == "list":
        report = catalog(args.category, args.domain)
        if not args.json:
            for row in report:
                print(f"{row['id']:<28} {row['category']:<10} {row['label_zh']}")
            return 0
    elif args.command == "inspect":
        report = get_preset(args.preset)
    elif args.command == "apply":
        report = _render_apply(args)
        if args.report:
            write_report(report, args.report)
    elif args.command == "transition":
        report = _render_transition(args)
        if args.report:
            write_report(report, args.report)
    elif args.command == "gallery":
        report = _render_gallery(args)
    else:
        raise AssertionError(args.command)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
