"""CLI and owned fixtures; application globals stay with the compatibility host."""
from __future__ import annotations

def self_test(_module_globals) -> None:
    with _module_globals['tempfile'].TemporaryDirectory(prefix=".asset-workshop-", dir=_module_globals['PROJECT_ROOT']) as temporary:
        root = _module_globals['Path'](temporary)
        atlas = _module_globals['Image'].new("RGBA", (400, 400), (0, 0, 0, 0))
        draw = _module_globals['ImageDraw'].Draw(atlas)
        for index in range(16):
            row, column = divmod(index, 4)
            left, top = column * 100 + 20, row * 100 + 20
            draw.ellipse((left, top, left + 55 + index % 3, top + 55), fill=(10 + index * 10, 90, 220, 255))
        source = root / "atlas.png"
        atlas.save(source)
        result = _module_globals['ingest_atlas'](source, batch_id="fixture", role="japanese_lifestyle_illustration",
                              names=[f"item-{index:02d}" for index in range(16)],
                              domains=["travel"], workshop_root=root / "workshop")
        assert result["created"] == 16
        manifest = _module_globals['_read'](root / "workshop" / "manifest.json", {})
        assert len(manifest["assets"]) == 16
        assert (root / "workshop" / "catalog-preview.webp").is_file()
        _module_globals['review_asset_batch']("fixture", "approved", root / "workshop")
        manifest = _module_globals['_read'](root / "workshop" / "manifest.json", {})
        assert all(row["selectable"] and row["human_review"] == "approved"
                   for row in manifest["assets"])
    plan = _module_globals['default_plan']()
    assert not any(batch["status"] == "generated" for batch in plan["batches"])
    assert plan["gates"]["human_visual_review_required"]
    try:
        _module_globals['ingest_atlas'](source, batch_id="blocked", role="japanese_lifestyle_illustration",
                     names=[f"item-{index:02d}" for index in range(16)],
                     domains=["ai"], workshop_root=root / "blocked")
    except ValueError:
        pass
    else:
        raise AssertionError("non-real AI illustration must be blocked")
    icon = _module_globals['Image'].new("RGBA", (32, 32), (25, 25, 25, 255))
    _module_globals['_validate_minimal_icon'](icon)
    try:
        gradient = _module_globals['Image'].new("RGBA", (32, 32))
        gradient.putdata([(index * 7 % 255, 80, 160, 255) for index in range(32 * 32)])
        _module_globals['_validate_minimal_icon'](gradient)
    except ValueError:
        pass
    else:
        raise AssertionError("multicolour icon must be blocked")
    print("asset_workshop self-test GREEN")

def main(_module_globals, argv=None) -> int:
    parser = _module_globals['argparse'].ArgumentParser(description="Plan, ingest and audit reusable image assets")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    ingest = sub.add_parser("ingest-atlas")
    ingest.add_argument("source")
    ingest.add_argument("--batch-id", required=True)
    ingest.add_argument("--role", required=True, choices=sorted(_module_globals['VALID_ROLES']))
    ingest.add_argument("--names", required=True, help="comma-separated stable slugs")
    ingest.add_argument("--domains", default="general", help="comma-separated domains")
    ingest.add_argument("--rows", type=int, default=_module_globals['ROWS'])
    ingest.add_argument("--cols", type=int, default=_module_globals['COLS'])
    taste = sub.add_parser("register-taste-board")
    taste.add_argument("source")
    taste.add_argument("--id", required=True)
    taste.add_argument("--family", choices=("photoreal_production", "japanese_lifestyle_calm"), required=True)
    taste.add_argument("--domains", required=True, help="comma-separated domains")
    review = sub.add_parser("review-taste-board")
    review.add_argument("--id", required=True)
    review.add_argument("--decision", choices=("approved", "rejected", "needs_edit"), required=True)
    batch_review = sub.add_parser("review-asset-batch")
    batch_review.add_argument("--id", required=True)
    batch_review.add_argument("--decision", choices=("approved", "rejected", "needs_edit"), required=True)
    sub.add_parser("normalize-selection-gates")
    sub.add_parser("preview")
    sub.add_parser("audit")
    sub.add_parser("selftest")
    args = parser.parse_args(argv)
    if args.command == "plan":
        print(_module_globals['json'].dumps(_module_globals['write_plan'](), ensure_ascii=False, indent=2)); return 0
    if args.command == "ingest-atlas":
        result = _module_globals['ingest_atlas'](args.source, batch_id=args.batch_id, role=args.role,
                              names=[part.strip() for part in args.names.split(",") if part.strip()],
                              domains=[part.strip() for part in args.domains.split(",") if part.strip()],
                              rows=args.rows, cols=args.cols)
        print(_module_globals['json'].dumps(result, ensure_ascii=False, indent=2)); return 0
    if args.command == "register-taste-board":
        result = _module_globals['register_taste_board'](args.source, board_id=args.id, family=args.family,
                                      domains=[part.strip() for part in args.domains.split(",") if part.strip()])
        print(_module_globals['json'].dumps(result, ensure_ascii=False, indent=2)); return 0
    if args.command == "review-taste-board":
        print(_module_globals['json'].dumps(_module_globals['review_taste_board'](args.id, args.decision), ensure_ascii=False, indent=2))
        return 0
    if args.command == "review-asset-batch":
        print(_module_globals['json'].dumps(_module_globals['review_asset_batch'](args.id, args.decision), ensure_ascii=False, indent=2))
        return 0
    if args.command == "normalize-selection-gates":
        print(_module_globals['json'].dumps(_module_globals['normalize_selection_gates'](), ensure_ascii=False, indent=2))
        return 0
    if args.command == "preview":
        print(_module_globals['render_preview']()); return 0
    if args.command == "audit":
        result = _module_globals['audit'](); print(_module_globals['json'].dumps(result, ensure_ascii=False, indent=2)); return 0 if result["status"] == "GREEN" else 1
    _module_globals['self_test'](); return 0
