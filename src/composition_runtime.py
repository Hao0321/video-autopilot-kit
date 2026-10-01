# -*- coding: utf-8 -*-
"""Deterministic, adapter-based programmatic motion composition runtime.

The runtime borrows public *capability ideas* from code-first video tools
(frame-addressable compositions, reusable components, parameterized variants,
machine-readable lint/inspect and renderer adapters), while keeping Hao's
semantic/evidence/quality gates as the source of truth.  It contains no copied
third-party source code and deliberately avoids making React or HTML the
project format.

The canonical format uses integer frames.  A compiler may target Hao's own
browser/component/vector adapters, FFmpeg/OpenCV/Pillow, or an existing Video
Autopilot effect module, but all adapters receive the same immutable frame
contract.  Third-party code-video frameworks are benchmarks, never runtime
dependencies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import shutil
import sys
from pathlib import Path
from typing import Any


SCHEMA = "hao.motion-composition/v1"
STABLE_EXIT = {"ok": 0, "generic": 1, "lint": 2, "compile": 3, "doctor": 4}
PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*\}\}")

# The registry is semantic.  The adapter is an implementation detail and can
# be replaced without changing the composition or learned editing memory.
COMPONENTS: dict[str, dict[str, Any]] = {
    "video": {"adapter": "native_media", "kind": "media"},
    "audio": {"adapter": "native_media", "kind": "media"},
    "image": {"adapter": "native_media", "kind": "media"},
    "text": {"adapter": "native_graphics", "kind": "graphic"},
    "solid": {"adapter": "native_graphics", "kind": "graphic"},
    "html_scene": {"adapter": "hao_browser_seek", "kind": "graphic"},
    "component_scene": {"adapter": "hao_component_runtime", "kind": "graphic"},
    "vector_scene": {"adapter": "hao_vector_runtime", "kind": "graphic"},
    "three_d_scene": {
        "adapter": "three_d_system", "kind": "spatial", "evidence": True,
    },
    "tracked_telemetry_callout": {
        "adapter": "tracked_graphics", "kind": "tracked", "evidence": True,
    },
    "subject_black_to_color_reveal": {
        "adapter": "tracked_graphics", "kind": "roto", "evidence": True,
    },
    "foreground_background_parallax_cut": {
        "adapter": "parallax_transition", "kind": "transition", "evidence": True,
    },
    "filter_clip": {
        "adapter": "filter_runtime", "kind": "filter", "evidence": False,
    },
    "filter_transition": {
        "adapter": "filter_runtime", "kind": "transition", "evidence": True,
    },
    "filter_subject": {
        "adapter": "filter_runtime", "kind": "roto", "evidence": True,
    },
}

ADAPTER_SOURCES = {
    "tracked_graphics": "tracked_graphics.py",
    "parallax_transition": "parallax_transition.py",
    "filter_runtime": "filter_runtime.py",
    "three_d_system": "three_d_system.py",
    "native_media": "ffmpeg",
    "native_graphics": "Pillow/FFmpeg",
    "hao_browser_seek": "browser_seek_runtime.py",
    "hao_component_runtime": "component_scene_runtime.py",
    "hao_vector_runtime": "vector_scene_runtime.py",
}


def component_catalog() -> dict[str, Any]:
    """Machine-readable catalog for agents, editors and future UI clients."""
    return {
        "schema": SCHEMA,
        "clock": "integer_frame_only",
        "components": [
            {"name": name, **rule, "source": ADAPTER_SOURCES[rule["adapter"]]}
            for name, rule in sorted(COMPONENTS.items())
        ],
        "non_negotiable_gates": [
            "semantic_meaning", "shot_or_effect_evidence", "quality_95",
            "mobile_review_for_new_visuals", "clean_fallback",
            "no_full_frame_or_typography_target_for_subject_reveal",
            "no_cross_dissolve_between_foreground_subjects",
        ],
    }


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _lookup(values: dict[str, Any], key: str) -> Any:
    current: Any = values
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(key)
        current = current[part]
    return current


def _expand(value: Any, variables: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: _expand(row, variables) for key, row in value.items()}
    if isinstance(value, list):
        return [_expand(row, variables) for row in value]
    if not isinstance(value, str):
        return value
    full = PLACEHOLDER.fullmatch(value)
    if full:
        return _lookup(variables, full.group(1))
    return PLACEHOLDER.sub(lambda match: str(_lookup(variables, match.group(1))), value)


def expand_composition(spec: dict[str, Any], overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    variables = dict(spec.get("variables") or {})
    variables.update(overrides or {})
    expanded = _expand(spec, variables)
    expanded["variables"] = variables
    return expanded


def _track_window(track: dict[str, Any]) -> tuple[int, int]:
    start = int(track.get("start_frame", 0))
    duration = int(track.get("duration_frames", 0))
    return start, start + duration


def validate(spec: dict[str, Any], base_dir: Path | None = None) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []

    def fail(code: str, path: str, message: str) -> None:
        errors.append({"severity": "error", "code": code, "path": path, "message": message})

    if spec.get("schema") != SCHEMA:
        fail("schema", "schema", f"must equal {SCHEMA}")
    if not str(spec.get("id", "")).strip():
        fail("required", "id", "non-empty id is required")
    width, height, fps = spec.get("width"), spec.get("height"), spec.get("fps")
    if not isinstance(width, int) or width < 16:
        fail("range", "width", "integer width >= 16 required")
    if not isinstance(height, int) or height < 16:
        fail("range", "height", "integer height >= 16 required")
    if not isinstance(fps, int) or not 12 <= fps <= 120:
        fail("range", "fps", "integer fps in [12,120] required")
    duration = spec.get("duration_frames")
    if not isinstance(duration, int) or duration <= 0:
        fail("range", "duration_frames", "positive integer duration_frames required")
        duration = 0
    tracks = spec.get("tracks")
    if not isinstance(tracks, list):
        fail("type", "tracks", "tracks must be a list")
        return errors
    ids: set[str] = set()
    for index, track in enumerate(tracks):
        path = f"tracks[{index}]"
        if not isinstance(track, dict):
            fail("type", path, "track must be an object")
            continue
        track_id = str(track.get("id", "")).strip()
        if not track_id:
            fail("required", path + ".id", "track id required")
        elif track_id in ids:
            fail("duplicate", path + ".id", "track id must be unique")
        ids.add(track_id)
        component = str(track.get("component", ""))
        rule = COMPONENTS.get(component)
        if rule is None:
            fail("component", path + ".component", f"unsupported component: {component}")
            continue
        start, end = _track_window(track)
        if start < 0 or int(track.get("duration_frames", 0)) <= 0 or end > duration:
            fail("window", path, "track must fit composition using integer frame bounds")
        if not isinstance(track.get("z", 0), int):
            fail("type", path + ".z", "z must be an integer")
        if rule.get("kind") in {"tracked", "roto", "transition", "spatial"}:
            if not str(track.get("meaning", "")).strip():
                fail("meaning", path + ".meaning", "semantic meaning is required")
            if rule.get("evidence") and not str(track.get("evidence", "")).strip():
                fail("evidence", path + ".evidence", "shot/effect evidence is required")
        if component == "subject_black_to_color_reveal":
            props = track.get("props") or {}
            if props.get("reveal_mode") != "black_to_color":
                fail("reveal", path + ".props.reveal_mode", "must be black_to_color")
            if props.get("target_kind") != "subject_object":
                fail("target", path + ".props.target_kind", "must target subject_object, never text/full frame")
        if component == "foreground_background_parallax_cut":
            props = track.get("props") or {}
            if props.get("foreground_handoff") != "midpoint_hard_cut":
                fail("ghosting", path + ".props.foreground_handoff", "midpoint_hard_cut required; cross-dissolve is forbidden")
        if component in {"filter_clip", "filter_transition", "filter_subject"}:
            props = track.get("props") or {}
            try:
                from filter_runtime import get_preset
                preset = get_preset(str(props.get("preset", "")))
            except (KeyError, ValueError):
                preset = None
                fail("filter_preset", path + ".props.preset", "known filter preset required")
            expected = {"filter_clip": {"grade", "temporal"},
                        "filter_transition": {"transition"},
                        "filter_subject": {"subject"}}[component]
            if preset and preset["category"] not in expected:
                fail("filter_category", path + ".props.preset",
                     f"{component} requires one of {sorted(expected)}")
            if component == "filter_transition":
                if not str(props.get("motivation", "")).strip():
                    fail("filter_motivation", path + ".props.motivation",
                         "transition filter requires an edit motivation")
                if len(props.get("sources") or []) != 2:
                    fail("filter_sources", path + ".props.sources",
                         "transition filter requires exactly two real source shots")
            if component == "filter_subject" and not str(props.get("matte", "")).strip():
                fail("filter_matte", path + ".props.matte",
                     "subject filter requires an editor-verified matte")
        if component in {"video", "audio", "image"}:
            source = str((track.get("props") or {}).get("src", ""))
            if not source:
                fail("required", path + ".props.src", "media src required")
            elif base_dir and "{{" not in source and not (base_dir / source).resolve().is_file():
                fail("missing_media", path + ".props.src", f"media not found: {source}")
        effect_spec = str((track.get("props") or {}).get("spec", ""))
        if effect_spec and base_dir and "{{" not in effect_spec and not (base_dir / effect_spec).resolve().is_file():
            fail("missing_effect_spec", path + ".props.spec", f"effect spec not found: {effect_spec}")
        for dep in track.get("depends_on") or []:
            if dep not in ids and not any(str(row.get("id")) == str(dep) for row in tracks if isinstance(row, dict)):
                fail("dependency", path + ".depends_on", f"unknown track dependency: {dep}")
    return errors


def _asset_digest(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path), "sha256": digest.hexdigest(), "bytes": path.stat().st_size}


def inspect(spec: dict[str, Any], base_dir: Path | None = None) -> dict[str, Any]:
    errors = validate(spec, base_dir)
    deps: list[dict[str, Any]] = []
    if base_dir:
        for track in spec.get("tracks") or []:
            src = str((track.get("props") or {}).get("src", ""))
            if src and "{{" not in src:
                path = (base_dir / src).resolve()
                if path.is_file():
                    deps.append(_asset_digest(path))
    return {
        "status": "GREEN" if not errors else "BLOCK",
        "schema": spec.get("schema"), "id": spec.get("id"),
        "resolution": [spec.get("width"), spec.get("height")], "fps": spec.get("fps"),
        "duration_frames": spec.get("duration_frames"),
        "duration_seconds": round(spec.get("duration_frames", 0) / max(1, spec.get("fps", 1)), 6),
        "track_count": len(spec.get("tracks") or []),
        "components": sorted({row.get("component") for row in spec.get("tracks") or [] if isinstance(row, dict)}),
        "asset_dependencies": deps,
        "composition_sha256": _sha({"spec": spec, "assets": deps}),
        "errors": errors,
    }


def compile_graph(spec: dict[str, Any], base_dir: Path | None = None) -> dict[str, Any]:
    info = inspect(spec, base_dir)
    if info["errors"]:
        raise ValueError("composition lint failed")
    nodes: list[dict[str, Any]] = []
    for track in sorted(spec["tracks"], key=lambda row: (int(row.get("z", 0)), int(row.get("start_frame", 0)), str(row["id"]))):
        rule = COMPONENTS[track["component"]]
        start, end = _track_window(track)
        node = {
            "id": track["id"], "component": track["component"],
            "adapter": rule["adapter"], "adapter_source": ADAPTER_SOURCES[rule["adapter"]],
            "frame_window": [start, end], "z": int(track.get("z", 0)),
            "depends_on": sorted(track.get("depends_on") or []),
            "props": track.get("props") or {},
            "meaning": track.get("meaning"), "evidence": track.get("evidence"),
            "node_sha256": _sha(track),
        }
        effect_spec = str(node["props"].get("spec", ""))
        output = str(node["props"].get("output", ""))
        if effect_spec and rule["adapter"] in {"tracked_graphics", "parallax_transition"}:
            executable = ADAPTER_SOURCES[rule["adapter"]]
            command = [sys.executable, f"{{{{autopilot_runtime_root}}}}/{executable}", "render", effect_spec]
            if output:
                command.extend(["--output", output])
            if node["props"].get("report"):
                command.extend([
                    "--track-output" if rule["adapter"] == "tracked_graphics" else "--report",
                    str(node["props"]["report"]),
                ])
            if node["props"].get("qa_sheet"):
                command.extend(["--qa-sheet", str(node["props"]["qa_sheet"])])
            node["execution"] = {
                "mode": "subprocess_adapter",
                "command": command,
                "cwd": "composition_base_dir",
                "preflight": ["lint", "adapter_validate", "evidence_gate"],
                "postflight": ["report_status", "quality_95", "mobile_review"],
            }
        elif rule["adapter"] == "filter_runtime":
            props = node["props"]
            output = str(props.get("output", ""))
            if track["component"] == "filter_transition":
                sources = list(props.get("sources") or [])
                command = [sys.executable, "{{autopilot_runtime_root}}/filter_runtime.py",
                           "transition", *sources, output, "--preset", str(props.get("preset", "")),
                           "--motivation", str(props.get("motivation", ""))]
                for value in props.get("transition_evidence") or []:
                    command.extend(["--evidence", str(value)])
            else:
                command = [sys.executable, "{{autopilot_runtime_root}}/filter_runtime.py",
                           "apply", str(props.get("src", "")), output,
                           "--preset", str(props.get("preset", ""))]
                if track["component"] == "filter_subject":
                    command.extend(["--matte", str(props.get("matte", ""))])
            if props.get("strength") is not None:
                command.extend(["--strength", str(props["strength"])])
            node["execution"] = {
                "mode": "subprocess_adapter", "command": command,
                "cwd": "composition_base_dir",
                "preflight": ["filter_library_validate", "one_grade_only",
                              "semantic_motivation", "matte_or_transition_evidence"],
                "postflight": ["technical_qa", "quality_95", "mobile_review"],
            }
        elif rule["adapter"] in {
                "hao_browser_seek", "hao_component_runtime", "hao_vector_runtime"}:
            node["execution"] = {
                "mode": "self_authored_renderer_adapter",
                "module": ADAPTER_SOURCES[rule["adapter"]],
                "contract": "frame_seek(frame, fps, immutable_props)",
                "low_level_engines_allowed": ["FFmpeg", "OpenCV", "Pillow", "browser"],
                "third_party_code_video_frameworks": "forbidden_as_runtime_dependency",
            }
        else:
            node["execution"] = {
                "mode": "renderer_adapter",
                "contract": "frame_seek(frame, fps, immutable_props)",
            }
        nodes.append(node)
    graph = {
        "status": "GREEN", "schema": SCHEMA, "id": spec["id"],
        "frame_contract": {
            "clock": "integer_frame_only", "first_frame": 0,
            "last_frame": spec["duration_frames"] - 1,
            "fps": spec["fps"], "wall_clock_access": "forbidden",
            "seek_event": {"frame": "int", "time": "frame/fps", "duration": "duration_frames/fps"},
        },
        "nodes": nodes, "composition_sha256": info["composition_sha256"],
        "quality_contract": {
            "semantic_evidence_gates": True, "quality_95_required": True,
            "mobile_review_required_for_new_visuals": True,
            "clean_fallback_required": True,
        },
    }
    graph["render_graph_sha256"] = _sha(graph)
    return graph


def compile_variants(spec: dict[str, Any], variants: list[dict[str, Any]], base_dir: Path | None = None) -> dict[str, Any]:
    rows = []
    for index, variables in enumerate(variants):
        expanded = expand_composition(spec, variables)
        graph = compile_graph(expanded, base_dir)
        rows.append({"index": index, "variables": variables, "graph": graph})
    structural = [{"component": n["component"], "adapter": n["adapter"], "frame_window": n["frame_window"], "z": n["z"]}
                  for n in (rows[0]["graph"]["nodes"] if rows else [])]
    return {
        "status": "GREEN", "variant_count": len(rows), "variants": rows,
        "shared_structure_sha256": _sha(structural),
        "cache_policy": "asset_sha + expanded_node_sha + frame_index; no private path or copy in structural cache",
    }


def doctor(root: Path) -> dict[str, Any]:
    required_modules = [
        "tracked_graphics.py", "parallax_transition.py", "three_d_system.py",
        "filter_runtime.py", "filter_renderers.py", "filter_primitives.py",
        "browser_seek_runtime.py", "component_scene_runtime.py", "vector_scene_runtime.py",
    ]
    checks = {
        "python": sys.version.split()[0], "platform": platform.platform(),
        "ffmpeg": shutil.which("ffmpeg"), "ffprobe": shutil.which("ffprobe"),
        "node_optional": shutil.which("node"), "npx_optional": shutil.which("npx"),
        "modules": {name: (root / name).is_file() for name in required_modules},
    }
    required_ok = bool(checks["ffmpeg"] and checks["ffprobe"] and all(checks["modules"].values()))
    return {"status": "GREEN" if required_ok else "BLOCK", "checks": checks,
            "third_party_video_framework_policy": "forbidden_as_runtime_dependency; public capabilities are benchmark inputs only"}


def self_test() -> None:
    sample = {
        "schema": SCHEMA, "id": "selftest", "width": 1080, "height": 1920,
        "fps": 30, "duration_frames": 90, "variables": {"name": "榮耀女武神"},
        "tracks": [
            {"id": "bg", "component": "solid", "start_frame": 0, "duration_frames": 90,
             "z": 0, "props": {"color": "#000"}},
            {"id": "label", "component": "text", "start_frame": 3, "duration_frames": 60,
             "z": 10, "props": {"text": "{{name}}"}},
            {"id": "reveal", "component": "subject_black_to_color_reveal",
             "start_frame": 5, "duration_frames": 19, "z": 20,
             "meaning": "reveal photographed product", "evidence": "editor verified matte",
             "props": {"target_kind": "subject_object", "reveal_mode": "black_to_color"}},
        ],
    }
    expanded = expand_composition(sample)
    assert expanded["tracks"][1]["props"]["text"] == "榮耀女武神"
    assert validate(expanded) == []
    graph = compile_graph(expanded)
    assert graph["frame_contract"]["last_frame"] == 89
    assert graph["nodes"][2]["adapter"] == "tracked_graphics"
    programmatic = json.loads(json.dumps(expanded, ensure_ascii=False))
    programmatic["tracks"].append({
        "id": "component", "component": "component_scene", "start_frame": 0,
        "duration_frames": 30, "z": 4, "props": {"scene": "inline"},
    })
    programmatic_graph = compile_graph(programmatic)
    component_node = next(row for row in programmatic_graph["nodes"] if row["id"] == "component")
    assert component_node["execution"]["mode"] == "self_authored_renderer_adapter"
    filtered = json.loads(json.dumps(expanded, ensure_ascii=False))
    filtered["tracks"].append({
        "id": "filter", "component": "filter_clip", "start_frame": 0,
        "duration_frames": 30, "z": 2,
        "props": {"preset": "scanline_focus", "src": "source.mp4",
                  "output": "filtered.mp4", "strength": 0.3},
    })
    filter_graph = compile_graph(filtered)
    filter_node = next(row for row in filter_graph["nodes"] if row["id"] == "filter")
    assert filter_node["adapter"] == "filter_runtime"
    assert "filter_runtime.py" in filter_node["execution"]["command"][1]
    broken = json.loads(json.dumps(expanded, ensure_ascii=False))
    broken["tracks"][2]["props"]["target_kind"] = "text"
    assert any(row["code"] == "target" for row in validate(broken))
    variants = compile_variants(sample, [{"name": "A"}, {"name": "B"}])
    assert variants["variant_count"] == 2 and variants["shared_structure_sha256"]
    print("composition_runtime self-test GREEN")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Hao deterministic motion-composition runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("lint", "inspect", "compile"):
        row = sub.add_parser(command)
        row.add_argument("spec")
        if command == "compile":
            row.add_argument("--variants")
            row.add_argument("--output")
    sub.add_parser("doctor")
    sub.add_parser("catalog")
    sub.add_parser("selftest")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if args.command == "selftest":
        self_test()
        return 0
    if args.command == "doctor":
        report = doctor(root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["status"] == "GREEN" else STABLE_EXIT["doctor"]
    if args.command == "catalog":
        print(json.dumps(component_catalog(), ensure_ascii=False, indent=2))
        return 0
    path = Path(args.spec).resolve()
    spec = expand_composition(_read_json(path))
    if args.command == "lint":
        errors = validate(spec, path.parent)
        print(json.dumps({"status": "GREEN" if not errors else "BLOCK", "errors": errors}, ensure_ascii=False, indent=2))
        return 0 if not errors else STABLE_EXIT["lint"]
    if args.command == "inspect":
        report = inspect(spec, path.parent)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["status"] == "GREEN" else STABLE_EXIT["lint"]
    try:
        if args.variants:
            variants = _read_json(Path(args.variants).resolve())
            report = compile_variants(_read_json(path), variants, path.parent)
        else:
            report = compile_graph(spec, path.parent)
    except (KeyError, ValueError) as exc:
        print(json.dumps({"status": "BLOCK", "error": str(exc)}, ensure_ascii=False, indent=2))
        return STABLE_EXIT["compile"]
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).resolve().write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
