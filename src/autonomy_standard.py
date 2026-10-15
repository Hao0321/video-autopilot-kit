# -*- coding: utf-8 -*-
"""Fail-closed unattended editing standard and central review queue (public distribution).

Allows reversible unattended work while keeping subjective approval and publishing human-owned.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def _discover_root(start: Path) -> Path:
    """Use the shared workspace registry for both private and public layouts."""
    from project_paths import discover_project_root
    return discover_project_root(start)


ROOT = _discover_root(Path(__file__).resolve().parent)
DEFAULT_QUEUE = ROOT / "videos" / "_PUBLISH_HUB" / "_STATE" / "hao_review_queue.json"
DEFAULT_GAP_BACKLOG = ROOT / "videos" / "_PUBLISH_HUB" / "_STATE" / "autonomy_gap_backlog.json"
HUMAN_DIMENSION = "human_aesthetic_review"
HARD_FALSE_SIGNALS = {
    "authenticity_claim_has_evidence",
    "battle_result_verified",
    "privacy_cleared",
    "rights_cleared",
    "text_safe_area_pass",
}
HARD_TRUE_SIGNALS = {
    "privacy_risk",
    "rights_blocked",
    "truth_unresolved",
    "source_provenance_missing",
    "battle_result_unverified",
    "generic_fullscreen_card",
    "grid_used_as_default_opener",
    "template_role_label_visible",
    "unmotivated_geometric_transition",
    "subject_sheen_leaks_outside_matte",
    "subject_sheen_used_as_transition",
    "subject_reveal_not_full_black_at_start",
    "subject_reveal_restores_outside_matte",
    "tracked_telemetry_drift_or_jitter",
    "tracked_telemetry_value_without_evidence",
    "parallax_double_subject_ghost",
    "parallax_matte_halo",
    "parallax_transition_missing_real_shot_pair",
    "parallax_chromatic_aberration_persistent",
    "fake_3d_claim",
}
from autonomy_plan_repairs import (
    REJECTED_EFFECT_STATES,
    _now,
    _repair,
    _repair_transitions,
    _repair_information,
    _repair_three_d,
    _repair_motion,
    _repair_color,
    prepare_unattended_plan,
)


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".autonomy-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, TypeError):
        return copy.deepcopy(default)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _machine_coverage(quality: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in quality.get("dimensions", []) if row.get("id") != HUMAN_DIMENSION]
    possible = sum(float(row.get("weight") or 0) for row in rows)
    earned = sum(float(row.get("points") or 0) for row in rows)
    return {"earned": round(earned, 2), "possible": round(possible, 2),
            "ratio": round(earned / possible, 4) if possible else 0.0,
            "human_dimension_excluded": True}


def _quality_payload(qa: dict[str, Any], quality_report: dict[str, Any] | None) -> dict[str, Any]:
    if quality_report:
        return quality_report
    summary = qa.get("quality_95") or {}
    report = Path(str(summary.get("report") or ""))
    return _read_json(report, summary) if report.is_file() else summary


def _review_bundle_exists(review: Any) -> bool:
    if not isinstance(review, dict):
        return False
    page = Path(str(review.get("page") or ""))
    bundle = Path(str(review.get("bundle") or ""))
    return page.is_file() and (bundle / "manifest.json").is_file()


def _hard_risks(qa: dict[str, Any], quality: dict[str, Any]) -> list[str]:
    signals = dict(((quality.get("evidence") or {}).get("signals") or {}))
    risks = []
    for key in sorted(HARD_TRUE_SIGNALS):
        if signals.get(key) is True or qa.get(key) is True:
            risks.append(key)
    for key in sorted(HARD_FALSE_SIGNALS):
        if signals.get(key) is False or qa.get(key) is False:
            risks.append(key)
    for row in quality.get("negative_regressions", []):
        if str(row.get("severity") or "").upper() == "BLOCK":
            risks.append("quality_block:" + str(row.get("id") or "unknown"))
    rights = str(qa.get("asset_rights_status") or "").upper()
    if rights in {"UNKNOWN", "BLOCKED", "MISSING"}:
        risks.append("asset_rights_status:" + rights)
    return sorted(set(risks))


def assess_unattended_candidate(qa: dict[str, Any], visual_plan: dict[str, Any],
                                quality_report: dict[str, Any] | None = None) -> dict[str, Any]:
    """Classify one built artifact without confusing automation with taste."""
    quality = _quality_payload(qa, quality_report)
    coverage = _machine_coverage(quality)
    technical_green = bool(qa.get("all_green") is True or qa.get("deliver_ok") is True)
    quality_status = str(quality.get("status") or
                         (qa.get("quality_95") or {}).get("status") or "REVIEW").upper()
    systems = {
        "high_information": (visual_plan.get("high_information_system") or {}).get("system") ==
                            "hao-high-information-editing-v1",
        "mediastorm": (visual_plan.get("mediastorm_craft") or {}).get("system") ==
                      "hao-mediastorm-craft-v1",
        "design": bool(visual_plan.get("design_system_v6")),
        "color": bool(visual_plan.get("color_system")),
    }
    risks = _hard_risks(qa, quality)
    hard_block = (not technical_green or quality_status == "BLOCKED" or bool(risks))
    review_ready = _review_bundle_exists(qa.get("hao_review"))
    candidate = (not hard_block and review_ready and all(systems.values()) and
                 coverage["ratio"] >= .95)
    status = "BLOCKED" if hard_block else ("AUTO_CANDIDATE" if candidate else "REVIEW_QUEUED")
    warnings = []
    if not review_ready:
        warnings.append("review_bundle_missing")
    warnings.extend("system_missing:" + name for name, present in systems.items() if not present)
    if coverage["ratio"] < .95:
        warnings.append("machine_coverage_below_95pct")
    return {
        "schema_version": 1,
        "status": status,
        "technical_green": technical_green,
        "machine_coverage": coverage,
        "systems": systems,
        "hard_blockers": risks + ([] if technical_green else ["technical_qa_red"]),
        "warnings": warnings,
        "human_review_required": True,
        "certification": "CREATOR_REVIEW_REQUIRED",
        "publish_allowed": False,
        "public_publish_allowed": False,
        "safe_next_step": "fix_blockers" if hard_block else "central_review_queue",
        "assessed_at": _now(),
    }


class _QueueLock:
    def __init__(self, queue: Path, timeout: float = 10.0) -> None:
        self.path = queue.with_suffix(queue.suffix + ".lock")
        self.timeout = timeout
        self.fd: int | None = None

    def __enter__(self) -> "_QueueLock":
        deadline = time.monotonic() + self.timeout
        self.path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                self.fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self.fd, f"{os.getpid()}\n".encode("ascii"))
                return self
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"review queue lock timed out: {self.path}")
                time.sleep(.02)

    def __exit__(self, *_args: Any) -> None:
        if self.fd is not None:
            os.close(self.fd)
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


def enqueue_review(*, content_id: str, format: str, artifact: str | Path,
                   autonomy: dict[str, Any], review_bundle: dict[str, Any] | None,
                   queue_path: str | Path = DEFAULT_QUEUE) -> dict[str, Any]:
    media = Path(artifact).resolve()
    if not media.is_file():
        raise FileNotFoundError(media)
    queue = Path(queue_path).resolve()
    digest = _sha256(media)
    with _QueueLock(queue):
        state = _read_json(queue, {"schema_version": 1, "items": []})
        items = list(state.get("items") or [])
        active = [row for row in items if row.get("content_id") == content_id and
                  row.get("state") in {"OPEN", "BLOCKED"}]
        same = next((row for row in active if row.get("artifact_sha256") == digest), None)
        if same:
            same["updated_at"] = _now()
            same["autonomy"] = autonomy
            same["review_bundle"] = review_bundle or {}
            result = {"action": "IDEMPOTENT", "item": same}
        else:
            for row in active:
                row["state"] = "SUPERSEDED"
                row["superseded_at"] = _now()
            revision = 1 + max((int(row.get("revision") or 0) for row in items
                                if row.get("content_id") == content_id), default=0)
            item = {
                "queue_id": f"{content_id}-r{revision}-{digest[:10]}",
                "content_id": content_id,
                "format": format,
                "revision": revision,
                "state": "BLOCKED" if autonomy.get("status") == "BLOCKED" else "OPEN",
                "priority": "P0" if autonomy.get("status") == "BLOCKED" else
                            ("P1" if autonomy.get("status") == "AUTO_CANDIDATE" else "P2"),
                "artifact": str(media),
                "artifact_sha256": digest,
                "autonomy": autonomy,
                "review_bundle": review_bundle or {},
                "created_at": _now(),
                "updated_at": _now(),
            }
            items.append(item)
            result = {"action": "ENQUEUED", "item": item}
        state.update(updated_at=_now(), items=items)
        _atomic_json(queue, state)
    return {**result, "queue": str(queue)}


REVIEW_ACTORS_ENV = "VIDEO_AUTOPILOT_REVIEW_ACTORS"


def _configured_review_actors() -> set[str]:
    """Return the explicitly configured review actors; an empty set fails closed."""
    raw = os.environ.get(REVIEW_ACTORS_ENV, "")
    return {value.strip().casefold() for value in raw.split(",") if value.strip()}


def resolve_review(queue_id: str, *, actor: str, decision: str,
                   queue_path: str | Path = DEFAULT_QUEUE) -> dict[str, Any]:
    actor_name = str(actor).strip()
    if not actor_name or actor_name.casefold() not in _configured_review_actors():
        raise PermissionError(
            f"Actor is not authorized to resolve the subjective review queue; "
            f"configure {REVIEW_ACTORS_ENV} with a comma-separated allowlist"
        )
    queue = Path(queue_path).resolve()
    with _QueueLock(queue):
        state = _read_json(queue, {"schema_version": 1, "items": []})
        item = next((row for row in state.get("items", []) if row.get("queue_id") == queue_id), None)
        if not item:
            raise KeyError(queue_id)
        item.update(state="RESOLVED", decision=str(decision), resolved_by=actor_name,
                    resolved_at=_now(), updated_at=_now())
        state["updated_at"] = _now()
        _atomic_json(queue, state)
    return item


def queue_summary(queue_path: str | Path = DEFAULT_QUEUE) -> dict[str, Any]:
    queue = Path(queue_path).resolve()
    state = _read_json(queue, {"schema_version": 1, "items": []})
    items = list(state.get("items") or [])
    counts = {name: sum(row.get("state") == name for row in items)
              for name in ("OPEN", "BLOCKED", "SUPERSEDED", "RESOLVED")}
    return {"queue": str(queue), "counts": counts,
            "active": [row for row in items if row.get("state") in {"OPEN", "BLOCKED"}]}


def initialize_control_state(queue_path: str | Path = DEFAULT_QUEUE,
                             backlog_path: str | Path = DEFAULT_GAP_BACKLOG) -> dict[str, str]:
    """Create empty control ledgers so publishing navigation never has dead links."""
    paths = (Path(queue_path).resolve(), Path(backlog_path).resolve())
    for path in paths:
        with _QueueLock(path):
            if not path.exists():
                _atomic_json(path, {"schema_version": 1, "updated_at": _now(), "items": []})
    return {"review_queue": str(paths[0]), "gap_backlog": str(paths[1])}


def record_gap_backlog(*, content_id: str, artifact_sha256: str,
                       assessment: dict[str, Any],
                       backlog_path: str | Path = DEFAULT_GAP_BACKLOG) -> dict[str, Any]:
    """Persist deduplicated capability gaps; never promote them into rules."""
    path = Path(backlog_path).resolve()
    raw_gaps = list(assessment.get("hard_blockers") or []) + list(assessment.get("warnings") or [])
    gaps = sorted(set(str(value) for value in raw_gaps if value))
    if not gaps:
        return {"backlog": str(path), "recorded": 0, "status": "NO_GAPS"}
    with _QueueLock(path):
        state = _read_json(path, {"schema_version": 1, "items": []})
        by_gap = {str(row.get("gap")): row for row in state.get("items") or []}
        for gap in gaps:
            row = by_gap.setdefault(gap, {"gap": gap, "observations": [],
                                          "promotion": "EVIDENCE_REQUIRED"})
            key = f"{content_id}:{artifact_sha256}:{gap}"
            if not any(item.get("key") == key for item in row["observations"]):
                row["observations"].append({"key": key, "content_id": content_id,
                                             "artifact_sha256": artifact_sha256,
                                             "observed_at": _now()})
            row["count"] = len(row["observations"])
            row["priority"] = "P0" if gap in assessment.get("hard_blockers", []) else (
                "P1" if row["count"] >= 3 else "P2")
            row["next_step"] = (
                "add failing fixture and detector before implementation"
                if row["count"] >= 3 else "collect more independent examples")
        state.update(updated_at=_now(), items=sorted(by_gap.values(), key=lambda row: (
            {"P0": 0, "P1": 1, "P2": 2}.get(row.get("priority"), 3), row["gap"])))
        _atomic_json(path, state)
    return {"backlog": str(path), "recorded": len(gaps), "status": "UPDATED"}


def assess_and_enqueue(*, content_id: str, format: str, artifact: str | Path,
                       qa: dict[str, Any], visual_plan: dict[str, Any],
                       quality_report: dict[str, Any] | None = None,
                       queue_path: str | Path = DEFAULT_QUEUE,
                       backlog_path: str | Path = DEFAULT_GAP_BACKLOG) -> dict[str, Any]:
    assessment = assess_unattended_candidate(qa, visual_plan, quality_report)
    queued = enqueue_review(content_id=content_id, format=format, artifact=artifact,
                            autonomy=assessment, review_bundle=qa.get("hao_review"),
                            queue_path=queue_path)
    backlog = record_gap_backlog(
        content_id=content_id, artifact_sha256=queued["item"]["artifact_sha256"],
        assessment=assessment, backlog_path=backlog_path)
    return {**assessment, "queue": queued, "gap_backlog": backlog}


def _selftest_fixture(root: Path) -> tuple[Path, dict, dict, dict]:
    from autonomy_standard_commands import _selftest_fixture as _implementation
    return _implementation(globals(), root)


def _selftest_assessment(safe: dict, qa: dict, quality: dict) -> dict:
    from autonomy_standard_commands import _selftest_assessment as _implementation
    return _implementation(globals(), safe, qa, quality)


def _selftest_queue(root: Path, artifact: Path, qa: dict, assessed: dict) -> None:
    queue = root / "queue.json"
    first = enqueue_review(content_id="S001", format="shorts", artifact=artifact,
                           autonomy=assessed, review_bundle=qa["hao_review"], queue_path=queue)
    again = enqueue_review(content_id="S001", format="shorts", artifact=artifact,
                           autonomy=assessed, review_bundle=qa["hao_review"], queue_path=queue)
    assert first["action"] == "ENQUEUED" and again["action"] == "IDEMPOTENT"
    artifact.write_bytes(b"revision-two")
    changed = enqueue_review(content_id="S001", format="shorts", artifact=artifact,
                             autonomy=assessed, review_bundle=qa["hao_review"], queue_path=queue)
    assert changed["item"]["revision"] == 2
    errors: list[str] = []
    def worker(identifier: str) -> None:
        try:
            media = root / f"{identifier}.mp4"; media.write_bytes(identifier.encode("utf-8"))
            enqueue_review(content_id=identifier, format="shorts", artifact=media,
                           autonomy=assessed, review_bundle=qa["hao_review"], queue_path=queue)
        except Exception as exc:  # pragma: no cover
            errors.append(str(exc))
    threads = [threading.Thread(target=worker, args=(f"S10{i}",)) for i in range(4)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert not errors and queue_summary(queue)["counts"]["OPEN"] == 5

    previous = os.environ.pop(REVIEW_ACTORS_ENV, None)
    try:
        try:
            resolve_review(changed["item"]["queue_id"], actor="creator",
                           decision="approve", queue_path=queue)
        except PermissionError:
            pass
        else:
            raise AssertionError("an empty actor allowlist must fail closed")

        os.environ[REVIEW_ACTORS_ENV] = "  CREATOR  "
        resolved = resolve_review(changed["item"]["queue_id"], actor=" creator ",
                                  decision="approve", queue_path=queue)
        assert resolved["state"] == "RESOLVED" and resolved["resolved_by"] == "creator"

        second = next(row for row in queue_summary(queue)["active"]
                      if row["content_id"] != "S001")
        os.environ[REVIEW_ACTORS_ENV] = "reviewer, EDITOR"
        resolved_second = resolve_review(second["queue_id"], actor=" editor ",
                                         decision="approve", queue_path=queue)
        assert resolved_second["resolved_by"] == "editor"

        os.environ[REVIEW_ACTORS_ENV] = "creator,reviewer"
        try:
            resolve_review(next(row["queue_id"] for row in queue_summary(queue)["active"]),
                           actor="bot", decision="approve", queue_path=queue)
        except PermissionError:
            pass
        else:
            raise AssertionError("an unconfigured bot must not resolve creator review")
    finally:
        if previous is None:
            os.environ.pop(REVIEW_ACTORS_ENV, None)
        else:
            os.environ[REVIEW_ACTORS_ENV] = previous


def _selftest_backlog(root: Path) -> None:
    from autonomy_standard_commands import _selftest_backlog as _implementation
    return _implementation(globals(), root)


def selftest() -> None:
    from autonomy_standard_commands import selftest as _implementation
    return _implementation(globals())


def main(argv: list[str] | None = None) -> int:
    from autonomy_standard_commands import main as _implementation
    return _implementation(globals(), argv)


if __name__ == "__main__":
    raise SystemExit(main())
