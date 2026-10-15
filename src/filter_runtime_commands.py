"""CLI and owned fixtures; application globals stay with the compatibility host."""
from __future__ import annotations

def self_test(_module_globals) -> None:
    errors = _module_globals['validate_library']()
    assert not errors, errors
    frame = _module_globals['np'].zeros((160, 96, 3), _module_globals['np'].uint8)
    frame[:, :48] = (30, 120, 240)
    frame[:, 48:] = (210, 90, 30)
    other = _module_globals['np'].flip(frame, axis=1).copy()
    material = _module_globals['np'].full_like(frame, 180)
    _module_globals['cv2'].circle(material, (48, 80), 42, (255, 180, 70), -1)
    matte = _module_globals['np'].zeros((160, 96), _module_globals['np'].uint8)
    _module_globals['cv2'].circle(matte, (48, 80), 30, 255, -1)
    for style in _module_globals['supported_styles']()["temporal"]:
        assert _module_globals['apply_temporal'](frame, style, 0.5, 0.6,
                              material=material).shape == frame.shape
    for style in _module_globals['supported_styles']()["transition"]:
        assert _module_globals['composite_transition'](frame, other, style, 0.5, 0.7,
                                    material=material).shape == frame.shape
    for style in _module_globals['supported_styles']()["subject"]:
        assert _module_globals['apply_subject'](frame, matte, style, 0.5, 0.7).shape == frame.shape
    decision = _module_globals['resolve_transition']("torn_paper_vertical", [], "")
    assert decision["selected"] == "clean_cut"
    decision = _module_globals['resolve_transition']("torn_paper_vertical", [], "manual review",
                                  manual_approved=True)
    assert decision["selected"] == "torn_paper_vertical"
    counts = {category: len(_module_globals['catalog'](category)) for category in _module_globals['CATEGORIES']}
    assert sum(counts.values()) >= 30 and counts["transition"] >= 8
    assert _module_globals['dependencies']()["ffmpeg"]
    print("filter_runtime self-test GREEN " + _module_globals['json'].dumps(counts, ensure_ascii=False))

def main(_module_globals, argv: list[str] | None = None) -> int:
    parser = _module_globals['argparse'].ArgumentParser(description="Hao unified filter library")
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list")
    listing.add_argument("--category", choices=sorted(_module_globals['CATEGORIES']))
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
    _module_globals['_add_media_options'](apply_parser)
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
    _module_globals['_add_media_options'](transition_parser)
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
        _module_globals['self_test']()
        return 0
    if args.command == "doctor":
        report = {"status": "GREEN" if not _module_globals['validate_library']() else "BLOCK",
                  "errors": _module_globals['validate_library'](), "dependencies": _module_globals['dependencies'](),
                  "counts": {value: len(_module_globals['catalog'](value)) for value in _module_globals['CATEGORIES']}}
    elif args.command == "list":
        report = _module_globals['catalog'](args.category, args.domain)
        if not args.json:
            for row in report:
                print(f"{row['id']:<28} {row['category']:<10} {row['label_zh']}")
            return 0
    elif args.command == "inspect":
        report = _module_globals['get_preset'](args.preset)
    elif args.command == "apply":
        report = _module_globals['_render_apply'](args)
        if args.report:
            _module_globals['write_report'](report, args.report)
    elif args.command == "transition":
        report = _module_globals['_render_transition'](args)
        if args.report:
            _module_globals['write_report'](report, args.report)
    elif args.command == "gallery":
        report = _module_globals['_render_gallery'](args)
    else:
        raise AssertionError(args.command)
    print(_module_globals['json'].dumps(report, ensure_ascii=False, indent=2))
    return 0
