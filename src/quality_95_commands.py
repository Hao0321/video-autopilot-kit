"""CLI and owned fixtures; application globals stay with the compatibility host."""
from __future__ import annotations

def self_test(_module_globals) -> None:
    dimensions = {name: 1.0 for name in _module_globals['load_corpus']()["dimensions"]}
    clean = {"dimensions": dimensions, "signals": {"text_safe_area_pass": True},
             "human_review": {"completed": True},
             "aesthetic_review": {"status": "PASSED", "score": 100}}
    assert _module_globals['score_quality'](clean)["status"] == "CERTIFIED_95"
    pending = _module_globals['json'].loads(_module_globals['json'].dumps(clean))
    pending["human_review"] = {"completed": False}
    pending["dimensions"]["human_aesthetic_review"] = 0
    assert _module_globals['score_quality'](pending)["status"] == "REVIEW"
    bad = _module_globals['json'].loads(_module_globals['json'].dumps(clean))
    bad["signals"]["generic_fullscreen_card"] = True
    assert _module_globals['score_quality'](bad)["status"] == "BLOCKED"
    aesthetic_bad = _module_globals['json'].loads(_module_globals['json'].dumps(clean))
    aesthetic_bad["aesthetic_review"] = {"status": "BLOCKED", "score": 65}
    assert _module_globals['score_quality'](aesthetic_bad)["status"] == "BLOCKED"
    with _module_globals['tempfile'].TemporaryDirectory(prefix="quality-95-adapters-") as temp:
        short = _module_globals['short_evidence'](
            content_id="selftest-short",
            spec={"name": "測試", "what": "對決", "place": "競技場", "addr": "台灣",
                  "persistent_label_policy": "required"},
            ready={"caps": [(0, 1, [("開打", "white")], "hook")]},
            qa={"all_green": True, "first_frame": "first.jpg",
                "caption_sheet": "captions.jpg"},
            visual_plan={"energy_curve": [1], "sequence_plan": [
                {"cut_motivation": "action_or_information_change"}]},
            project_root=temp,
        )
        assert short["format"] == "shorts" and short["dimensions"]
        assert _module_globals['score_quality'](short)["status"] == "REVIEW"
    long = _module_globals['longform_evidence'](
        content_id="selftest-long",
        delivery_qa={
            "deliver_ok": True, "linebreaks": {"ok": True},
            "contact_sheet": "contact.jpg", "scene_pacing": {"ok": True},
        },
        visual_plan={"design_system_v6": {"compiler": "hao-design-system-v6"}},
    )
    assert long["format"] == "longform" and long["dimensions"]
    assert _module_globals['score_quality'](long)["status"] == "REVIEW"
    print("quality_95 self-test GREEN")

def main(_module_globals, argv: list[str] | None = None) -> int:
    parser = _module_globals['argparse'].ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest")
    score = sub.add_parser("score")
    score.add_argument("evidence")
    score.add_argument("--output-dir", required=True)
    score.add_argument("--agent-review", help="Artifact-bound reference review JSON; evidence must include explicit creator review_policy authorization")
    args = parser.parse_args(argv)
    if args.command == "selftest":
        _module_globals['self_test']()
        return 0
    evidence = _module_globals['_read_json'](_module_globals['Path'](args.evidence), {})
    if args.agent_review:
        evidence["agent_art_review"] = _module_globals['_read_json'](_module_globals['Path'](args.agent_review), {})
    report = _module_globals['write_report'](args.output_dir, evidence)
    print(_module_globals['json'].dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "BLOCKED" else 0
