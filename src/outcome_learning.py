# -*- coding: utf-8 -*-
"""Evidence-gated learning loop for published video outcomes.

Audience metrics and Hao's aesthetic preference are deliberately separate.
Patterns are promoted only with enough same-platform, same-window evidence.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

from channel_tracker import STATE_PATH, due_report


ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = ROOT.parent / "data" / "outcome_playbook.json"
TASTE_PATH = ROOT.parent / "data" / "taste_model.json"
MIN_SAMPLES = 5


def _read(path: str | Path, default) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    candidate = path.with_suffix(path.suffix + ".candidate")
    candidate.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(candidate, path)


def metric_rows(state: dict) -> list[dict]:
    rows = []
    for video in state.get("videos", []):
        for platform, windows in (video.get("metrics") or {}).items():
            for window, metrics in (windows or {}).items():
                if not isinstance(metrics, dict):
                    continue
                rows.append({
                    "video": video.get("name"), "platform": platform, "window": window,
                    "domain": video.get("line") or "unknown", "published": video.get("published"),
                    "metrics": {k: v for k, v in metrics.items() if v is not None},
                    "edit_features": list(video.get("edit_features") or []),
                })
    return rows


def retention_diagnosis(metrics: dict) -> list[str]:
    notes = []
    retention = metrics.get("retention_pct")
    if isinstance(retention, (int, float)):
        if retention < 25: notes.append("retention_low_review_hook_and_dead_air")
        elif retention >= 55: notes.append("retention_strong_preserve_structure")
    viewed = metrics.get("viewed_vs_swiped_pct")
    if isinstance(viewed, (int, float)) and viewed < 60:
        notes.append("shorts_feed_stop_rate_low_review_first_frame")
    return notes


def build_playbook(state: dict, today: date | None = None, min_samples: int = MIN_SAMPLES,
                   taste_summary: dict | None = None) -> dict:
    rows = metric_rows(state)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row["platform"], row["window"])].append(row)
    patterns = []
    for (platform, window), group in sorted(groups.items()):
        if len(group) < min_samples:
            continue
        numeric = defaultdict(list)
        for row in group:
            for key, value in row["metrics"].items():
                if isinstance(value, (int, float)):
                    numeric[key].append(float(value))
        summary = {key: {"median": round(statistics.median(values), 4), "n": len(values)}
                   for key, values in numeric.items() if len(values) >= min_samples}
        if summary:
            patterns.append({"platform": platform, "window": window,
                             "sample_count": len(group), "baselines": summary,
                             "status": "EVIDENCE_BASELINE"})
    feature_outcomes = []
    by_feature: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in rows:
        views = row["metrics"].get("views")
        if not isinstance(views, (int, float)):
            continue
        for feature in row["edit_features"]:
            by_feature[(row["platform"], row["window"], str(feature))].append(float(views))
    for (platform, window, feature), values in sorted(by_feature.items()):
        if len(values) >= min_samples:
            feature_outcomes.append({"platform": platform, "window": window, "feature": feature,
                                     "n": len(values), "median_views": round(statistics.median(values), 2),
                                     "status": "CORRELATION_NOT_CAUSATION"})
    taste = (_read(TASTE_PATH, {}).get("summary", {})
             if taste_summary is None else taste_summary)
    today = today or date.today()
    schedulable = dict(state)
    schedulable["videos"] = [v for v in state.get("videos", []) if isinstance(v.get("snapshots"), dict)]
    schedulable.setdefault("pending_actions", [])
    due = due_report(schedulable, today)
    diagnosis = Counter(note for row in rows for note in retention_diagnosis(row["metrics"]))
    status = "EVIDENCE_READY" if patterns else "INSUFFICIENT_EVIDENCE"
    return {
        "schema_version": 1, "updated_at": datetime.now(timezone.utc).isoformat(), "status": status,
        "evidence_policy": {"min_same_window_samples": min_samples,
                            "min_platform_samples": min_samples,
                            "taste_feedback_is_not_audience_outcome": True,
                            "missing_metrics_are_unknown_not_zero": True},
        "audience_patterns": patterns, "feature_outcomes": feature_outcomes,
        "taste_preferences": taste.get("top_preferences", []),
        "taste_constraints": taste.get("hard_constraints", []),
        "data_quality": {"tracked_videos": len(state.get("videos", [])),
                         "metric_rows": len(rows), "groups": {f"{p}/{w}": len(g) for (p, w), g in groups.items()},
                         "overdue_snapshots_and_actions": len(due["due"]),
                         "overdue": due["due"],
                         "retention_diagnoses": dict(diagnosis)},
        "next_action": "collect_due_snapshots_without_backfilling_missing_fields" if status != "EVIDENCE_READY"
                       else "compare_only_same_platform_same_window_and_keep_testing",
    }


def refresh(state_path: str | Path = STATE_PATH, output: str | Path = OUTPUT_PATH,
            today: date | None = None) -> dict:
    state = _read(state_path, {"videos": [], "pending_actions": []})
    result = build_playbook(state, today=today)
    _atomic(Path(output), result)
    return result


def _selftest() -> None:
    state = {"videos": [], "pending_actions": []}
    for i in range(4):
        state["videos"].append({"name": f"v{i}", "line": "toy", "metrics": {"yt": {"D2": {"views": 100+i}}}})
    assert build_playbook(state, taste_summary={})["status"] == "INSUFFICIENT_EVIDENCE"
    state["videos"].append({"name": "v4", "line": "toy", "metrics": {"yt": {"D2": {"views": 180, "retention_pct": 58}}}})
    result = build_playbook(state, taste_summary={})
    assert result["status"] == "EVIDENCE_READY" and result["audience_patterns"][0]["sample_count"] == 5
    assert result["taste_preferences"] == []
    with tempfile.TemporaryDirectory(prefix="hao-outcome-test-") as td:
        path = Path(td) / "state.json"; path.write_text(json.dumps(state), encoding="utf-8")
        assert refresh(path, Path(td) / "out.json")["status"] == "EVIDENCE_READY"
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
