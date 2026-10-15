"""CLI and owned fixtures; application globals stay with the compatibility host."""
from __future__ import annotations

def _selftest_fixture(_module_globals, root: Path) -> tuple[Path, dict, dict, dict]:
    artifact = root / "current.mp4"
    artifact.write_bytes(b"gold-render")
    review = root / "_review"
    review.mkdir()
    (review / "review.html").write_text("review", encoding="utf-8")
    (review / "manifest.json").write_text("{}", encoding="utf-8")
    plan = {"design_system_v6": {"compiler": "hao-design-system-v6"},
            "color_system": {"profile": "clean"},
            "mediastorm_craft": {"system": "hao-mediastorm-craft-v1", "editing": {
                "transitions": [{"selected": "cut_on_action", "status": "DOWNGRADED",
                                 "missing": ["action_peak"]}]}},
            "high_information_system": {"system": "hao-high-information-editing-v1",
                "selected": [{"event": "subject_sheen", "evidence": ["subject_matte"]}],
                "blocked": [], "used": 1}, "three_d_system": {"status": "DOWNGRADED"},
            "motion_assets": {"cues": [{"id": "bad", "status": "AWAITING_EVIDENCE"}]}}
    safe, repairs = _module_globals['prepare_unattended_plan'](plan)
    assert repairs and safe["mediastorm_craft"]["editing"]["transitions"][0]["selected"] == "clean_cut"
    assert safe["high_information_system"]["selected"] == []
    assert safe["three_d_system"]["execution_enabled"] is False and safe["motion_assets"]["cues"] == []
    qa = {"all_green": True, "hao_review": {"bundle": str(review),
          "page": str(review / "review.html")}}
    quality = {"status": "REVIEW", "dimensions": [
        {"id": "technical_delivery", "weight": 92, "points": 92},
        {"id": _module_globals['HUMAN_DIMENSION'], "weight": 8, "points": 0}],
        "negative_regressions": [], "evidence": {"signals": {}}}
    return artifact, safe, qa, quality

def _selftest_assessment(_module_globals, safe: dict, qa: dict, quality: dict) -> dict:
    assessed = _module_globals['assess_unattended_candidate'](qa, safe, quality)
    assert assessed["status"] == "AUTO_CANDIDATE"
    assert assessed["certification"] == "CREATOR_REVIEW_REQUIRED"
    assert assessed["publish_allowed"] is False and assessed["public_publish_allowed"] is False
    blocked = _module_globals['copy'].deepcopy(quality)
    blocked["evidence"]["signals"]["battle_result_unverified"] = True
    assert _module_globals['assess_unattended_candidate'](qa, safe, blocked)["status"] == "BLOCKED"
    return assessed

def _selftest_queue(_module_globals, root: Path, artifact: Path, qa: dict, assessed: dict) -> None:
    queue = root / "queue.json"
    first = _module_globals['enqueue_review'](content_id="S001", format="shorts", artifact=artifact,
                           autonomy=assessed, review_bundle=qa["hao_review"], queue_path=queue)
    again = _module_globals['enqueue_review'](content_id="S001", format="shorts", artifact=artifact,
                           autonomy=assessed, review_bundle=qa["hao_review"], queue_path=queue)
    assert first["action"] == "ENQUEUED" and again["action"] == "IDEMPOTENT"
    artifact.write_bytes(b"revision-two")
    changed = _module_globals['enqueue_review'](content_id="S001", format="shorts", artifact=artifact,
                             autonomy=assessed, review_bundle=qa["hao_review"], queue_path=queue)
    assert changed["item"]["revision"] == 2
    errors: list[str] = []
    def worker(identifier: str) -> None:
        try:
            media = root / f"{identifier}.mp4"; media.write_bytes(identifier.encode("utf-8"))
            _module_globals['enqueue_review'](content_id=identifier, format="shorts", artifact=media,
                           autonomy=assessed, review_bundle=qa["hao_review"], queue_path=queue)
        except Exception as exc:  # pragma: no cover
            errors.append(str(exc))
    threads = [_module_globals['threading'].Thread(target=worker, args=(f"S10{i}",)) for i in range(4)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert not errors and _module_globals['queue_summary'](queue)["counts"]["OPEN"] == 5
    try:
        _module_globals['resolve_review'](changed["item"]["queue_id"], actor="bot", decision="approve", queue_path=queue)
    except PermissionError:
        pass
    else:
        raise AssertionError("automation must not resolve Hao's review")

def _selftest_backlog(_module_globals, root: Path) -> None:
    backlog = root / "gaps.json"
    evidence = {"hard_blockers": [], "warnings": ["system_missing:color"]}
    recorded = _module_globals['record_gap_backlog'](content_id="S001", artifact_sha256="abc",
                                  assessment=evidence, backlog_path=backlog)
    _module_globals['record_gap_backlog'](content_id="S001", artifact_sha256="abc",
                       assessment=evidence, backlog_path=backlog)
    assert recorded["recorded"] == 1 and _module_globals['_read_json'](backlog, {})["items"][0]["count"] == 1

def selftest(_module_globals) -> None:
    with _module_globals['tempfile'].TemporaryDirectory(prefix="autonomy-standard-") as temporary:
        root = _module_globals['Path'](temporary)
        artifact, safe, qa, quality = _module_globals['_selftest_fixture'](root)
        assessed = _module_globals['_selftest_assessment'](safe, qa, quality)
        _module_globals['_selftest_queue'](root, artifact, qa, assessed)
        _module_globals['_selftest_backlog'](root)
        initialized = _module_globals['initialize_control_state'](root / "empty-queue.json", root / "empty-gaps.json")
        assert all(_module_globals['Path'](path).is_file() for path in initialized.values())
    print("autonomy_standard self-test GREEN")

def main(_module_globals, argv: list[str] | None = None) -> int:
    parser = _module_globals['argparse'].ArgumentParser(description="Unattended video editing safety standard")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest")
    status = sub.add_parser("queue-status")
    status.add_argument("--queue", default=str(_module_globals['DEFAULT_QUEUE']))
    assess = sub.add_parser("assess")
    assess.add_argument("input", help="JSON with qa, visual_plan and optional quality_report")
    args = parser.parse_args(argv)
    if args.command == "selftest":
        _module_globals['selftest']()
        return 0
    if args.command == "queue-status":
        print(_module_globals['json'].dumps(_module_globals['queue_summary'](args.queue), ensure_ascii=False, indent=2))
        return 0
    payload = _module_globals['_read_json'](_module_globals['Path'](args.input), {})
    print(_module_globals['json'].dumps(_module_globals['assess_unattended_candidate'](
        payload.get("qa") or {}, payload.get("visual_plan") or {},
        payload.get("quality_report") or None), ensure_ascii=False, indent=2))
    return 0
