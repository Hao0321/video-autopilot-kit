# -*- coding: utf-8 -*-
"""Evidence-gated learning loop for published video outcomes.

Audience metrics and Hao's aesthetic preference are deliberately separate.
Patterns are promoted only with enough same-platform, same-window evidence.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from channel_tracker import (CAPTURE_TOLERANCE_DAYS, FORMATS, PLATFORMS, SNAP_WINDOWS, STATE_PATH,
                             add_video, atomic_write_json, capture_timing, due_report,
                             is_metric_number, load_state, mark_snapshot, record_metrics,
                             save_state)
from taste_model import summarize as summarize_taste


ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = ROOT.parent / "data" / "outcome_playbook.json"
TASTE_PATH = ROOT.parent / "data" / "taste_model.json"
MIN_SAMPLES = 5
STATE_FAILURES = ("STATE_MISSING", "STATE_CORRUPT")
RESERVED_METRIC_KEYS = ("captured_on",)
EXCLUDED_LIST_LIMIT = 200
EXCLUSION_REASONS = ("unknown_platform", "unknown_window", "format_unknown", "invalid_metric_value",
                     "capture_early", "capture_late", "capture_date_unknown",
                     "publish_date_unknown", "conflicting_duplicate")


def _read(path: str | Path, default) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _atomic(path: Path, payload: dict) -> None:
    atomic_write_json(path, payload, indent=2)


def _mapping(value) -> dict:
    return value if isinstance(value, dict) else {}


def _video_key(video: dict) -> str:
    """Distinct-video identity: the platform video id, else the tracked name."""
    vid = str(video.get("video_id") or "").strip()
    return vid if vid else "name:%s" % video.get("name")


def metric_rows(state: dict) -> list[dict]:
    rows = []
    for video in state.get("videos", []):
        if not isinstance(video, dict):
            continue
        snapshots = _mapping(video.get("snapshots"))
        for platform, windows in _mapping(video.get("metrics")).items():
            for window, metrics in _mapping(windows).items():
                if not isinstance(metrics, dict):
                    continue
                rows.append({
                    "video": video.get("name"), "video_key": _video_key(video),
                    "platform": platform, "window": window, "format": video.get("format"),
                    "domain": video.get("line") or "unknown", "published": video.get("published"),
                    "metrics": {k: v for k, v in metrics.items()
                                if v is not None and k not in RESERVED_METRIC_KEYS},
                    "captured_on": metrics.get("captured_on"),
                    "snapshot_done_on": _mapping(snapshots.get(window)).get("done_on"),
                    "edit_features": list(video.get("edit_features") or []),
                })
    return rows


def retention_diagnosis(metrics: dict) -> list[str]:
    notes = []
    retention = metrics.get("retention_pct")
    if is_metric_number(retention):
        if retention < 25: notes.append("retention_low_review_hook_and_dead_air")
        elif retention >= 55: notes.append("retention_strong_preserve_structure")
    viewed = metrics.get("viewed_vs_swiped_pct")
    if is_metric_number(viewed) and viewed < 60:
        notes.append("shorts_feed_stop_rate_low_review_first_frame")
    return notes


def _issue(row: dict, reason: str, metric: str | None = None, value=None) -> dict:
    note = {"video": row["video_key"], "platform": row["platform"],
            "window": row["window"], "reason": reason}
    if metric is not None:
        note["metric"] = metric
    if reason == "invalid_metric_value":
        note["value_type"] = type(value).__name__
    return note


def _exclusion(row: dict, metric: str | None = None, value=None) -> str | None:
    """Why a row (or one of its metric values) is not comparable; None when it is.

    A value's capture date is its per-field captured_on, else the window's
    snapshot done_on; without either it is never treated as on time.
    """
    if metric is None:
        if row["platform"] not in PLATFORMS:
            return "unknown_platform"
        if row["window"] not in SNAP_WINDOWS:
            return "unknown_window"
        return None if row["format"] in FORMATS else "format_unknown"
    if not is_metric_number(value):
        return "invalid_metric_value"
    stamps = row["captured_on"]
    captured = stamps.get(metric) if isinstance(stamps, dict) else stamps
    timing = capture_timing(row["published"], row["window"], captured or row["snapshot_done_on"])
    if timing == "on_time":
        return None
    return "capture_" + timing if timing in ("early", "late") else timing


def _comparable(rows: list[dict]) -> tuple[dict, list[dict]]:
    """Accepted {(platform, format, window): {metric: {video_key: value}}} plus exclusions."""
    accepted: dict = defaultdict(lambda: defaultdict(dict))
    excluded, conflicts = [], set()
    for row in rows:
        reason = _exclusion(row)
        if reason:
            excluded.append(_issue(row, reason))
            continue
        group = accepted[(row["platform"], row["format"], row["window"])]
        for key, value in row["metrics"].items():
            reason = _exclusion(row, key, value)
            if reason:
                excluded.append(_issue(row, reason, key, value))
            elif group[key].setdefault(row["video_key"], float(value)) != float(value):
                conflicts.add((row["platform"], row["format"], row["window"], key, row["video_key"]))
    for platform, fmt, window, key, video in sorted(conflicts):
        accepted[(platform, fmt, window)][key].pop(video, None)
        excluded.append({"video": video, "platform": platform, "window": window,
                         "metric": key, "reason": "conflicting_duplicate"})
    return accepted, excluded


def _group_videos(metrics: dict) -> set:
    return set().union(*metrics.values()) if metrics else set()


def _audience_patterns(accepted: dict, min_samples: int) -> list[dict]:
    patterns = []
    for (platform, fmt, window), metrics in sorted(accepted.items()):
        videos = _group_videos(metrics)
        if len(videos) < min_samples:
            continue
        summary = {key: {"median": round(statistics.median(values.values()), 4), "n": len(values)}
                   for key, values in sorted(metrics.items()) if len(values) >= min_samples}
        if summary:
            patterns.append({"platform": platform, "format": fmt, "window": window,
                             "sample_count": len(videos), "baselines": summary,
                             "status": "EVIDENCE_BASELINE"})
    return patterns


def _feature_outcomes(rows: list[dict], accepted: dict, min_samples: int) -> list[dict]:
    features: dict = {}
    for row in rows:
        features.setdefault(row["video_key"], sorted({str(f) for f in row["edit_features"]}))
    by_feature: dict = defaultdict(dict)
    for (platform, fmt, window), metrics in accepted.items():
        for video, views in metrics.get("views", {}).items():
            for feature in features.get(video, []):
                by_feature[(platform, fmt, window, feature)][video] = views
    return [{"platform": platform, "format": fmt, "window": window, "feature": feature,
             "n": len(values), "median_views": round(statistics.median(values.values()), 2),
             "status": "CORRELATION_NOT_CAUSATION"}
            for (platform, fmt, window, feature), values in sorted(by_feature.items())
            if len(values) >= min_samples]


def _taste(taste_summary: dict | None) -> tuple[dict, str]:
    """Recompute the taste summary from stored votes; a cached summary is not evidence."""
    if taste_summary is not None:
        return taste_summary, "provided"
    if not Path(TASTE_PATH).is_file():
        return {}, "missing"
    raw = _read(TASTE_PATH, None)
    try:
        return summarize_taste(raw), "recomputed"
    except (AttributeError, KeyError, TypeError, ValueError):
        return {}, "corrupt"


def _data_quality(state: dict, rows: list[dict], accepted: dict, excluded: list[dict],
                  due: dict, taste_state: str) -> dict:
    keys = [_video_key(v) for v in state.get("videos", []) if isinstance(v, dict)]
    seen, diagnosis = set(), Counter()
    for row in rows:
        ident = (row["video_key"], row["platform"], row["window"])
        if ident not in seen:
            seen.add(ident)
            diagnosis.update(retention_diagnosis(row["metrics"]))
    return {"tracked_videos": len(state.get("videos", [])), "distinct_videos": len(set(keys)),
            "duplicate_videos": sorted(k for k, n in Counter(keys).items() if n > 1),
            "metric_rows": len(rows),
            "groups": {"%s/%s/%s" % key: len(_group_videos(metrics))
                       for key, metrics in sorted(accepted.items()) if _group_videos(metrics)},
            "excluded_counts": dict(Counter(item["reason"] for item in excluded)),
            "excluded": excluded[:EXCLUDED_LIST_LIMIT],
            "excluded_truncated": len(excluded) > EXCLUDED_LIST_LIMIT,
            "taste_state": taste_state,
            "overdue_snapshots_and_actions": len(due["due"]),
            "overdue": due["due"],
            "retention_diagnoses": dict(diagnosis)}


def build_playbook(state: dict, today: date | None = None, min_samples: int = MIN_SAMPLES,
                   taste_summary: dict | None = None) -> dict:
    rows = metric_rows(state)
    accepted, excluded = _comparable(rows)
    patterns = _audience_patterns(accepted, min_samples)
    taste, taste_state = _taste(taste_summary)
    today = today or date.today()
    schedulable = dict(state)
    schedulable["videos"] = [v for v in state.get("videos", [])
                             if isinstance(v, dict) and isinstance(v.get("snapshots"), dict)]
    schedulable.setdefault("pending_actions", [])
    due = due_report(schedulable, today)
    status = "EVIDENCE_READY" if patterns else "INSUFFICIENT_EVIDENCE"
    return {
        "schema_version": 2, "updated_at": datetime.now(timezone.utc).isoformat(), "status": status,
        "evidence_policy": {"min_same_window_samples": min_samples,
                            "min_platform_samples": min_samples,
                            "baseline_group": ["platform", "format", "window"],
                            "sample_unit": "distinct_video_id",
                            "capture_tolerance_days": dict(CAPTURE_TOLERANCE_DAYS),
                            "excluded_from_baselines": list(EXCLUSION_REASONS),
                            "taste_feedback_is_not_audience_outcome": True,
                            "missing_metrics_are_unknown_not_zero": True},
        "audience_patterns": patterns,
        "feature_outcomes": _feature_outcomes(rows, accepted, min_samples),
        "taste_preferences": taste.get("top_preferences", []),
        "taste_constraints": taste.get("hard_constraints", []),
        "data_quality": _data_quality(state, rows, accepted, excluded, due, taste_state),
        "next_action": "collect_due_snapshots_without_backfilling_missing_fields" if status != "EVIDENCE_READY"
                       else "compare_only_same_platform_same_window_and_keep_testing",
    }


def _not_refreshed(status: str, state_path, output, exc: BaseException | None = None) -> dict:
    """Fail closed: say why, and leave any previous playbook untouched."""
    return {"schema_version": 2, "status": status, "state_path": str(state_path),
            "output": str(output), "output_written": False,
            "error": ("%s: %s" % (type(exc).__name__, exc))[:300] if exc else None,
            "next_action": "restore_or_create_channel_state_then_refresh"}


def refresh(state_path: str | Path = STATE_PATH, output: str | Path = OUTPUT_PATH,
            today: date | None = None) -> dict:
    try:
        state = load_state(str(state_path))
    except FileNotFoundError:
        return _not_refreshed("STATE_MISSING", state_path, output)
    except (OSError, ValueError) as exc:
        return _not_refreshed("STATE_CORRUPT", state_path, output, exc)
    result = build_playbook(state, today=today)
    _atomic(Path(output), result)
    return result


def _fixture_day(window: str, late_days: int = 0) -> str:
    return (date(2026, 7, 1) + timedelta(days=SNAP_WINDOWS[window] + late_days)).isoformat()


def _track(state: dict, name: str, fmt: str | None, window: str = "D2",
           late_days: int = 0, **metrics) -> dict:
    """Synthetic fixture: one tracked video plus metrics read relative to its due date."""
    video = add_video(state, name, "id-" + name, date(2026, 7, 1).isoformat(), "toy", fmt=fmt)
    record_metrics(state, name, "yt", window, captured_on=_fixture_day(window, late_days), **metrics)
    return video


def _selftest_baseline() -> dict:
    state = {"videos": [], "pending_actions": []}
    for i in range(4):
        _track(state, "v%d" % i, "shorts", views=100 + i)
    assert build_playbook(state, taste_summary={})["status"] == "INSUFFICIENT_EVIDENCE"
    _track(state, "v4", "shorts", views=180)
    for i in range(5):  # a field read later is merged into the same window, not replacing it
        record_metrics(state, "v%d" % i, "yt", "D2", captured_on=_fixture_day("D2"), retention_pct=40 + i)
    result = build_playbook(state, taste_summary={})
    pattern = result["audience_patterns"][0]
    assert result["status"] == "EVIDENCE_READY" and pattern["sample_count"] == 5
    assert pattern["format"] == "shorts" and set(pattern["baselines"]) == {"views", "retention_pct"}
    assert result["taste_preferences"] == []
    return state


def _selftest_identity_and_format() -> None:
    state = {"videos": [], "pending_actions": []}
    _track(state, "dup", "shorts", views=1000)
    state["videos"] += [json.loads(json.dumps(state["videos"][0])) for _ in range(4)]
    result = build_playbook(state, taste_summary={})
    quality = result["data_quality"]
    assert result["status"] == "INSUFFICIENT_EVIDENCE", "one video entered five times is one sample"
    assert quality["duplicate_videos"] == ["id-dup"] and quality["distinct_videos"] == 1
    state["videos"][1]["metrics"]["yt"]["D2"]["views"] = 999
    counts = build_playbook(state, taste_summary={})["data_quality"]["excluded_counts"]
    assert counts == {"conflicting_duplicate": 1}, counts
    state = {"videos": [], "pending_actions": []}
    for i in range(5):
        _track(state, "s%d" % i, "shorts", views=50000 + i)
        _track(state, "l%d" % i, "longform", views=800 + i)
    legacy = json.loads(json.dumps(state["videos"][0]))
    legacy.pop("format")
    legacy.update(name="legacy", video_id="id-legacy")
    state["videos"].append(legacy)
    result = build_playbook(state, taste_summary={})
    medians = {p["format"]: p["baselines"]["views"]["median"] for p in result["audience_patterns"]}
    assert medians == {"longform": 802.0, "shorts": 50002.0}, "formats are never pooled"
    assert result["data_quality"]["excluded_counts"] == {"format_unknown": 1}
    assert set(result["data_quality"]["groups"]) == {"yt/shorts/D2", "yt/longform/D2"}


def _selftest_timing_and_values() -> None:
    state = {"videos": [], "pending_actions": []}
    for i in range(5):
        _track(state, "t%d" % i, "longform", window="D7", views=1000)
    _track(state, "late", "longform", window="D7", late_days=33, views=25000)
    state["videos"][0]["metrics"]["yt"]["d7"] = {"views": 7}
    for name in ("undated", "snap"):
        del _track(state, name, "longform", window="D7", views=1000)["metrics"]["yt"]["D7"]["captured_on"]
    mark_snapshot(state, "snap", "D7", _fixture_day("D7"))
    result = build_playbook(state, taste_summary={})
    counts = result["data_quality"]["excluded_counts"]
    assert result["audience_patterns"][0]["baselines"]["views"] == {"median": 1000.0, "n": 6}
    assert counts == {"capture_late": 1, "capture_date_unknown": 1, "unknown_window": 1}, counts
    state = {"videos": [], "pending_actions": []}
    for i in range(5):
        window = _track(state, "b%d" % i, "shorts", views=100 + i)["metrics"]["yt"]["D2"]
        window.update(retention_pct=True, ctr_pct="1.2k")  # hand-edited legacy values
        window["captured_on"].update(retention_pct=_fixture_day("D2"), ctr_pct=_fixture_day("D2"))
    result = build_playbook(state, taste_summary={})
    assert set(result["audience_patterns"][0]["baselines"]) == {"views"}, "bool/text never count"
    assert result["data_quality"]["excluded_counts"] == {"invalid_metric_value": 10}
    assert {item["value_type"] for item in result["data_quality"]["excluded"]} == {"bool", "str"}
    assert not result["data_quality"]["retention_diagnoses"]


def _selftest_refresh(state: dict) -> None:
    import contextlib
    import io
    with tempfile.TemporaryDirectory(prefix="hao-outcome-test-") as td:
        path, out, other = Path(td) / "state.json", Path(td) / "out.json", Path(td) / "other.json"
        save_state(state, str(path))
        assert refresh(path, out)["status"] == "EVIDENCE_READY"
        good = out.read_bytes()
        missing = refresh(Path(td) / "missing.json", other)
        assert missing["status"] == "STATE_MISSING" and not other.exists()
        path.write_text(path.read_text(encoding="utf-8")[:200], encoding="utf-8")
        assert refresh(path, out)["status"] == "STATE_CORRUPT"
        assert out.read_bytes() == good, "a corrupt state never overwrites the previous playbook"
        with contextlib.redirect_stdout(io.StringIO()):
            code = main(["refresh", "--state", str(path), "--output", str(out)])
        assert code == 1 and out.read_bytes() == good


def _selftest_taste_recompute() -> None:
    global TASTE_PATH
    previous = TASTE_PATH
    with tempfile.TemporaryDirectory(prefix="outcome-taste-test-") as td:
        TASTE_PATH = Path(td) / "taste_model.json"
        try:
            pair = {"a": {"label": "A", "path": "a.png", "features": ["glow"]},
                    "b": {"label": "B", "path": "b.png", "features": ["f1", "f2"]}}
            stale = {"comparisons": [dict(pair, id="c1", context="general", winner="a")],
                     "summary": {"status": "LEARNED_PREFERENCES",
                                 "top_preferences": [{"feature": "glow", "rating": 1056.0, "n": 5}]}}
            TASTE_PATH.write_text(json.dumps(stale), encoding="utf-8")
            result = build_playbook({"videos": [], "pending_actions": []})
            assert result["taste_preferences"] == [], "a cached one-vote summary is not a preference"
            assert result["data_quality"]["taste_state"] == "recomputed"
            for broken in ("{broken", '{"comparisons": 7}', "[]"):
                TASTE_PATH.write_text(broken, encoding="utf-8")
                assert build_playbook({"videos": []})["data_quality"]["taste_state"] == "corrupt", broken
        finally:
            TASTE_PATH = previous


def _selftest() -> None:
    state = _selftest_baseline()
    _selftest_identity_and_format()
    _selftest_timing_and_values()
    _selftest_refresh(state)
    _selftest_taste_recompute()
    print("outcome_learning self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, OSError):
        pass
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    refresh_p = sub.add_parser("refresh"); refresh_p.add_argument("--state", default=str(STATE_PATH)); refresh_p.add_argument("--output", default=str(OUTPUT_PATH)); refresh_p.add_argument("--date")
    args = ap.parse_args(argv)
    if args.cmd == "selftest": _selftest(); return 0
    result = refresh(args.state, args.output, date.fromisoformat(args.date) if args.date else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] in STATE_FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
