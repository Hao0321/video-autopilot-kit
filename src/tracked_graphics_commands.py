"""CLI and owned fixtures; application globals stay with the compatibility host."""
from __future__ import annotations

def self_test(_module_globals) -> None:
    assert _module_globals['validate_spec']({"video": "missing.mp4", "start": 0, "end": 1})
    invalid = {
        "video": _module_globals['__file__'], "start": 0, "end": 1,
        "tracked_labels": [{
            "text": "$100", "initial_bbox": [0, 0, 10, 10],
            "start": 0, "end": 1,
        }],
    }
    assert any("requires evidence" in error for error in _module_globals['validate_spec'](invalid))
    with _module_globals['tempfile'].TemporaryDirectory(prefix="tracked-graphics-selftest-") as temp:
        report = _module_globals['build_demo'](temp)
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
            assert (_module_globals['Path'](temp) / name).stat().st_size > 1000
    invalid_text_sheen = {
        "video": _module_globals['__file__'], "start": 0, "end": .5,
        "mask_sheens": [{
            "start": 0, "end": .4, "initial_bbox": [0, 0, 40, 40],
            "shape": "rectangle", "subject_class": "typography",
            "target_kind": "typography", "evidence": "negative fixture",
        }],
    }
    assert any(
        "never text" in error or "belongs to text effects" in error
        for error in _module_globals['validate_spec'](invalid_text_sheen)
    )
    print("tracked_graphics self-test GREEN")

def main(_module_globals) -> int:
    parser = _module_globals['argparse'].ArgumentParser(
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
        _module_globals['self_test']()
        return 0
    if args.command == "demo":
        print(_module_globals['json'].dumps(_module_globals['build_demo'](args.out_dir), ensure_ascii=False, indent=2))
        return 0
    spec = _module_globals['json'].loads(_module_globals['Path'](args.spec).read_text(encoding="utf-8"))
    errors = _module_globals['validate_spec'](spec)
    if args.command == "validate":
        print(_module_globals['json'].dumps(
            {"status": "GREEN" if not errors else "RED", "errors": errors},
            ensure_ascii=False, indent=2,
        ))
        return 0 if not errors else 1
    report = _module_globals['render_spec'](
        spec, args.output,
        alpha_output=args.alpha_output or None,
        track_output=args.track_output or None,
        qa_sheet=args.qa_sheet or None,
    )
    print(_module_globals['json'].dumps(report, ensure_ascii=False, indent=2))
    return 0
