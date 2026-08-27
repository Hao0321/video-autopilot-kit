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
    """Find a private or public-kit root without adding a kernel dependency."""
    for candidate in (start.resolve(), *start.resolve().parents):
        if (candidate / "AUTOPILOT_MANIFEST.json").is_file() or (
                candidate / "release-manifest.json").is_file():
            return candidate
    raise FileNotFoundError("Cannot find an autopilot project manifest")


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
REJECTED_EFFECT_STATES = {"AWAITING_EVIDENCE", "PENDING", "REJECTED", "BLOCKED", "MISSING_EVIDENCE"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def _repair(ledger: list[dict[str, Any]], path: str, before: Any, after: Any,
            reason: str) -> None:
    ledger.append({"path": path, "before": before, "after": after,
                   "reason": reason, "reversible": True})


def _repair_transitions(plan: dict[str, Any], repairs: list[dict[str, Any]]) -> None:
    craft = plan.get("mediastorm_craft") or {}
    transitions = ((craft.get("editing") or {}).get("transitions") or [])
    for index, row in enumerate(transitions):
        missing = list(row.get("missing") or [])
        status = str(row.get("status") or "").upper()
        if missing or status not in {"READY", ""}:
            before = row.get("selected")
            if before != "clean_cut":
                row["selected"] = "clean_cut"
                row["status"] = "DOWNGRADED"
                _repair(repairs, f"mediastorm_craft.editing.transitions[{index}].selected",
                        before, "clean_cut", "unverified transition prerequisites")


def _repair_information(plan: dict[str, Any], repairs: list[dict[str, Any]]) -> None:
    info = plan.get("high_information_system") or {}
    selected, kept, newly_blocked = list(info.get("selected") or []), [], []
    for index, row in enumerate(selected):
        event = str(row.get("event") or "unknown")
        evidence = set(row.get("evidence") or [])
        required = {
            "subject_sheen": {"subject_matte", "track_or_keyframes", "material_profile", "frame_qa"},
            "black_to_color_subject_reveal": {
                "per_frame_subject_matte", "track_or_keyframes", "material_profile",
                "first_mid_last_frame_qa", "occlusion_edge_review",
            },
            "tracked_callout": {"initial_bbox_or_polygon", "track_report", "visibility_window"},
            "tracked_telemetry_callout": {
                "initial_bbox_or_polygon", "track_report", "visibility_window",
                "measured_value_evidence", "connector_anchor_shared_track",
            },
            "money_burst": {"currency_evidence", "licensed_or_generated_usd_particle_asset", "payoff_timestamp"},
        }.get(event, set())
        if not evidence or not required.issubset(evidence):
            newly_blocked.append({"index": index, "event": event,
                                  "reason": "unattended_missing_evidence",
                                  "missing": sorted(required - evidence)})
            _repair(repairs, f"high_information_system.selected[{index}]", row, None,
                    "effect cannot be verified without inventing evidence")
        else:
            kept.append(row)
    if len(kept) != len(selected):
        info["selected"] = kept
        info["blocked"] = list(info.get("blocked") or []) + newly_blocked
        info["used"] = len(kept)
        info["status"] = "SAFE_FALLBACK" if newly_blocked else info.get("status")


def _repair_three_d(plan: dict[str, Any], repairs: list[dict[str, Any]]) -> None:
    three_d = plan.get("three_d_system") or {}
    if three_d and str(three_d.get("status") or "").upper() != "READY":
        before = three_d.get("execution_enabled", True)
        three_d["execution_enabled"] = False
        if before is not False:
            _repair(repairs, "three_d_system.execution_enabled", before, False,
                    "3D route lacks production prerequisites")


def _repair_motion(plan: dict[str, Any], repairs: list[dict[str, Any]]) -> None:
    motion = plan.get("motion_assets") or {}
    cues = list(motion.get("cues") or [])
    kept_cues = []
    for index, cue in enumerate(cues):
        status = str(cue.get("status") or "").upper()
        if status in REJECTED_EFFECT_STATES:
            _repair(repairs, f"motion_assets.cues[{index}]", cue, None,
                    "motion cue has no ready evidence")
        else:
            kept_cues.append(cue)
    if len(kept_cues) != len(cues):
        motion["cues"] = kept_cues


def _repair_color(plan: dict[str, Any], repairs: list[dict[str, Any]]) -> None:
    color = plan.get("color_system") or {}
    input_status = str(color.get("input_status") or color.get("source_status") or "").upper()
    if input_status in {"BLOCK_UNKNOWN_LOG", "UNKNOWN_LOG", "UNKNOWN_INPUT_TRANSFORM"}:
        before = color.get("creative_look_enabled", True)
        color["creative_look_enabled"] = False
        color["safe_fallback"] = "neutral_normalization_only"
        if before is not False:
            _repair(repairs, "color_system.creative_look_enabled", before, False,
                    "unknown input transform; creative look disabled")


def prepare_unattended_plan(visual_plan: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return a safe copy and a reversible repair ledger, never invented evidence."""
    plan = copy.deepcopy(visual_plan)
    repairs: list[dict[str, Any]] = []
    for repairer in (_repair_transitions, _repair_information, _repair_three_d,
                     _repair_motion, _repair_color):
        repairer(plan, repairs)
    plan["unattended_preflight"] = {
        "schema_version": 1,
        "policy": "reversible-downgrade-only",
        "repairs": len(repairs),
        "human_review_required": True,
        "certification_forbidden": True,
        "prepared_at": _now(),
    }
    return plan, repairs


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
    safe, repairs = prepare_unattended_plan(plan)
    assert repairs and safe["mediastorm_craft"]["editing"]["transitions"][0]["selected"] == "clean_cut"
    assert safe["high_information_system"]["selected"] == []
    assert safe["three_d_system"]["execution_enabled"] is False and safe["motion_assets"]["cues"] == []
    qa = {"all_green": True, "hao_review": {"bundle": str(review),
          "page": str(review / "review.html")}}
    quality = {"status": "REVIEW", "dimensions": [
        {"id": "technical_delivery", "weight": 92, "points": 92},
        {"id": HUMAN_DIMENSION, "weight": 8, "points": 0}],
        "negative_regressions": [], "evidence": {"signals": {}}}
    return artifact, safe, qa, quality


def _selftest_assessment(safe: dict, qa: dict, quality: dict) -> dict:
    assessed = assess_unattended_candidate(qa, safe, quality)
    assert assessed["status"] == "AUTO_CANDIDATE"
    assert assessed["certification"] == "CREATOR_REVIEW_REQUIRED"
    assert assessed["publish_allowed"] is False and assessed["public_publish_allowed"] is False
    blocked = copy.deepcopy(quality)
    blocked["evidence"]["signals"]["battle_result_unverified"] = True
    assert assess_unattended_candidate(qa, safe, blocked)["status"] == "BLOCKED"
    return assessed


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
    backlog = root / "gaps.json"
    evidence = {"hard_blockers": [], "warnings": ["system_missing:color"]}
    recorded = record_gap_backlog(content_id="S001", artifact_sha256="abc",
                                  assessment=evidence, backlog_path=backlog)
    record_gap_backlog(content_id="S001", artifact_sha256="abc",
                       assessment=evidence, backlog_path=backlog)
    assert recorded["recorded"] == 1 and _read_json(backlog, {})["items"][0]["count"] == 1


def selftest() -> None:
    with tempfile.TemporaryDirectory(prefix="autonomy-standard-") as temporary:
        root = Path(temporary)
        artifact, safe, qa, quality = _selftest_fixture(root)
        assessed = _selftest_assessment(safe, qa, quality)
        _selftest_queue(root, artifact, qa, assessed)
        _selftest_backlog(root)
        initialized = initialize_control_state(root / "empty-queue.json", root / "empty-gaps.json")
        assert all(Path(path).is_file() for path in initialized.values())
    print("autonomy_standard self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Unattended video editing safety standard")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest")
    status = sub.add_parser("queue-status")
    status.add_argument("--queue", default=str(DEFAULT_QUEUE))
    assess = sub.add_parser("assess")
    assess.add_argument("input", help="JSON with qa, visual_plan and optional quality_report")
    args = parser.parse_args(argv)
    if args.command == "selftest":
        selftest()
        return 0
    if args.command == "queue-status":
        print(json.dumps(queue_summary(args.queue), ensure_ascii=False, indent=2))
        return 0
    payload = _read_json(Path(args.input), {})
    print(json.dumps(assess_unattended_candidate(
        payload.get("qa") or {}, payload.get("visual_plan") or {},
        payload.get("quality_report") or None), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
