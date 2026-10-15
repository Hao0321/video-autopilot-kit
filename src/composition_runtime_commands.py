"""CLI and owned fixtures; application globals stay with the compatibility host."""
from __future__ import annotations

def self_test(_module_globals) -> None:
    sample = {
        "schema": _module_globals['SCHEMA'], "id": "selftest", "width": 1080, "height": 1920,
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
    expanded = _module_globals['expand_composition'](sample)
    assert expanded["tracks"][1]["props"]["text"] == "榮耀女武神"
    assert _module_globals['validate'](expanded) == []
    graph = _module_globals['compile_graph'](expanded)
    assert graph["frame_contract"]["last_frame"] == 89
    assert graph["nodes"][2]["adapter"] == "tracked_graphics"
    programmatic = _module_globals['json'].loads(_module_globals['json'].dumps(expanded, ensure_ascii=False))
    programmatic["tracks"].append({
        "id": "component", "component": "component_scene", "start_frame": 0,
        "duration_frames": 30, "z": 4, "props": {"scene": "inline"},
    })
    programmatic_graph = _module_globals['compile_graph'](programmatic)
    component_node = next(row for row in programmatic_graph["nodes"] if row["id"] == "component")
    assert component_node["execution"]["mode"] == "self_authored_renderer_adapter"
    filtered = _module_globals['json'].loads(_module_globals['json'].dumps(expanded, ensure_ascii=False))
    filtered["tracks"].append({
        "id": "filter", "component": "filter_clip", "start_frame": 0,
        "duration_frames": 30, "z": 2,
        "props": {"preset": "scanline_focus", "src": "source.mp4",
                  "output": "filtered.mp4", "strength": 0.3},
    })
    filter_graph = _module_globals['compile_graph'](filtered)
    filter_node = next(row for row in filter_graph["nodes"] if row["id"] == "filter")
    assert filter_node["adapter"] == "filter_runtime"
    assert "filter_runtime.py" in filter_node["execution"]["command"][1]
    broken = _module_globals['json'].loads(_module_globals['json'].dumps(expanded, ensure_ascii=False))
    broken["tracks"][2]["props"]["target_kind"] = "text"
    assert any(row["code"] == "target" for row in _module_globals['validate'](broken))
    variants = _module_globals['compile_variants'](sample, [{"name": "A"}, {"name": "B"}])
    assert variants["variant_count"] == 2 and variants["shared_structure_sha256"]
    print("composition_runtime self-test GREEN")

def main(_module_globals) -> int:
    parser = _module_globals['argparse'].ArgumentParser(description="Hao deterministic motion-composition runtime")
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
    root = _module_globals['Path'](_module_globals['__file__']).resolve().parent
    if args.command == "selftest":
        _module_globals['self_test']()
        return 0
    if args.command == "doctor":
        report = _module_globals['doctor'](root)
        print(_module_globals['json'].dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["status"] == "GREEN" else _module_globals['STABLE_EXIT']["doctor"]
    if args.command == "catalog":
        print(_module_globals['json'].dumps(_module_globals['component_catalog'](), ensure_ascii=False, indent=2))
        return 0
    path = _module_globals['Path'](args.spec).resolve()
    spec = _module_globals['expand_composition'](_module_globals['_read_json'](path))
    if args.command == "lint":
        errors = _module_globals['validate'](spec, path.parent)
        print(_module_globals['json'].dumps({"status": "GREEN" if not errors else "BLOCK", "errors": errors}, ensure_ascii=False, indent=2))
        return 0 if not errors else _module_globals['STABLE_EXIT']["lint"]
    if args.command == "inspect":
        report = _module_globals['inspect'](spec, path.parent)
        print(_module_globals['json'].dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["status"] == "GREEN" else _module_globals['STABLE_EXIT']["lint"]
    try:
        if args.variants:
            variants = _module_globals['_read_json'](_module_globals['Path'](args.variants).resolve())
            report = _module_globals['compile_variants'](_module_globals['_read_json'](path), variants, path.parent)
        else:
            report = _module_globals['compile_graph'](spec, path.parent)
    except (KeyError, ValueError) as exc:
        print(_module_globals['json'].dumps({"status": "BLOCK", "error": str(exc)}, ensure_ascii=False, indent=2))
        return _module_globals['STABLE_EXIT']["compile"]
    payload = _module_globals['json'].dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        _module_globals['Path'](args.output).resolve().write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0
