"""Promotion-focused adversarial fixtures for security receipt v2."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from security_assessment_evaluator import evaluate
from security_assessment_shared import file_identity
from security_assessment_snapshot import snapshot_sha256
from security_assessment_v2_bindings import authorization_projection
from security_assessment_v2_common import compute_plan_sha256, parse_json_object
from security_assessment_v2_fixtures import (
    external_fixture,
    read_evidence_json,
    replace_evidence_json,
    valid_fixture,
)


def _has_code(report: dict[str, Any], code: str) -> bool:
    return any(item["code"] == code for item in report["findings"])


def _fresh(now: datetime) -> tuple[tempfile.TemporaryDirectory[str], Path, dict[str, Any]]:
    temporary = tempfile.TemporaryDirectory(prefix="cleanup-security-v2-negative-")
    root = Path(temporary.name)
    return temporary, root, valid_fixture(root, now)


def _adapter_case(
    now: datetime,
    mutator: Callable[[dict[str, Any], dict[str, Any]], None],
) -> dict[str, Any]:
    temporary, root, receipt = _fresh(now)
    try:
        adapter = read_evidence_json(receipt, root, "adapter-result")
        mutator(adapter, receipt)
        digest = replace_evidence_json(receipt, root, "adapter-result", adapter)
        receipt["tasks"][0]["adapterResultSha256"] = digest
        return evaluate(receipt, root, now=now)
    finally:
        temporary.cleanup()


def _calibration_case(
    now: datetime,
    mutator: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    temporary, root, receipt = _fresh(now)
    try:
        calibration = read_evidence_json(receipt, root, "engine-calibration")
        mutator(calibration)
        digest = replace_evidence_json(receipt, root, "engine-calibration", calibration)
        receipt["engines"][0]["calibrationSha256"] = digest
        return evaluate(receipt, root, now=now)
    finally:
        temporary.cleanup()


def _refresh_grant(receipt: dict[str, Any], root: Path) -> None:
    receipt["authorization"]["planSha256"] = compute_plan_sha256(receipt)
    grant = authorization_projection(receipt, receipt["authorization"])
    digest = replace_evidence_json(receipt, root, "authorization", grant)
    receipt["authorization"]["authorizationEvidenceSha256"] = digest


def _assert_json_number_rejections() -> None:
    for raw in (
        b'{"value":1.0}',
        b'{"value":1e3}',
        b'{"value":NaN}',
        b'{"value":Infinity}',
        b'{"value":-Infinity}',
        b'{"value":9223372036854775808}',
        ('{"value":' + ('9' * 10_000) + '}').encode("ascii"),
    ):
        try:
            parse_json_object(raw)
        except (ValueError, json.JSONDecodeError):
            pass
        else:
            raise AssertionError("non-integer or oversized JSON number was accepted")


def _assert_target_and_snapshot_rejections(now: datetime) -> None:
    temporary, root, receipt = _fresh(now)
    try:
        for field, invalid_identity in (
            ("product", " Cafe"),
            ("product", "Cafe\u0301"),
            ("product", "Fixture\u202e"),
            ("product", "Fixture\u0000"),
            ("product", "password=never-reflect-this"),
            ("product", "界" * 171),
            ("version", "界" * 86),
        ):
            broken = json.loads(json.dumps(receipt))
            broken["target"][field] = invalid_identity
            broken["authorization"]["planSha256"] = compute_plan_sha256(broken)
            report = evaluate(broken, root, now=now)
            assert report["status"] == "BLOCK" and _has_code(report, "target-identity"), report
            assert invalid_identity not in json.dumps(report, ensure_ascii=False)
    finally:
        temporary.cleanup()

    for mutation, code in (("add", "snapshot-file-added"), ("change", "snapshot-file-changed"), ("remove", "snapshot-file-missing")):
        temporary, root, receipt = _fresh(now)
        try:
            source = root / "src" / "app.py"
            if mutation == "add":
                (root / "src" / "added.py").write_text("added\n", encoding="utf-8")
            elif mutation == "change":
                source.write_text("changed\n", encoding="utf-8")
            else:
                source.unlink()
            report = evaluate(receipt, root, now=now)
            assert report["status"] == "BLOCK" and _has_code(report, code), report
        finally:
            temporary.cleanup()

    if os.name == "nt":
        temporary, root, receipt = _fresh(now)
        stream_path = Path(str(root / "src" / "app.py") + ":security-regression")
        try:
            try:
                stream_path.write_bytes(b"hidden stream must invalidate the snapshot")
            except OSError:
                pass
            else:
                report = evaluate(receipt, root, now=now)
                assert report["status"] == "BLOCK" and _has_code(
                    report, "snapshot-alternate-stream"
                ), report
        finally:
            try:
                stream_path.unlink()
            except OSError:
                pass
            temporary.cleanup()

    temporary, root, receipt = _fresh(now)
    try:
        (root / "src" / "app.py").unlink()
        manifest = read_evidence_json(receipt, root, "snapshot-manifest")
        manifest["entries"] = []
        receipt["target"]["snapshotManifestSha256"] = replace_evidence_json(
            receipt, root, "snapshot-manifest", manifest,
        )
        empty_snapshot = snapshot_sha256([])
        receipt["target"]["snapshotSha256"] = empty_snapshot
        receipt["tasks"][0]["execution"]["snapshotSha256"] = empty_snapshot
        adapter = read_evidence_json(receipt, root, "adapter-result")
        adapter["snapshotSha256"] = empty_snapshot
        receipt["tasks"][0]["adapterResultSha256"] = replace_evidence_json(
            receipt, root, "adapter-result", adapter,
        )
        receipt["authorization"]["planSha256"] = compute_plan_sha256(receipt)
        report = evaluate(receipt, root, now=now)
        assert report["status"] == "BLOCK" and _has_code(report, "snapshot-empty"), report
    finally:
        temporary.cleanup()


def _assert_freshness_and_plan_rejections(now: datetime) -> None:
    old_now = now - timedelta(hours=25)
    temporary, root, receipt = _fresh(old_now)
    try:
        report = evaluate(receipt, root, now=now)
        assert report["status"] == "NOT_CHECKED" and _has_code(report, "stale-security-receipt"), report
    finally:
        temporary.cleanup()

    temporary, root, receipt = _fresh(now)
    try:
        shallow = json.loads(json.dumps(receipt))
        shallow["tasks"][0]["plannedCheckIds"] = ["working-tree"]
        shallow["tasks"][0]["executedCheckIds"] = ["working-tree"]
        adapter = read_evidence_json(shallow, root, "adapter-result")
        original_adapter = json.loads(json.dumps(adapter))
        adapter["plannedCheckIds"] = ["working-tree"]
        adapter["executedCheckIds"] = ["working-tree"]
        shallow["tasks"][0]["adapterResultSha256"] = replace_evidence_json(
            shallow, root, "adapter-result", adapter,
        )
        shallow["authorization"]["planSha256"] = compute_plan_sha256(shallow)
        report = evaluate(shallow, root, now=now)
        assert report["status"] == "BLOCK" and _has_code(
            report, "security-control-plan"
        ), report
        replace_evidence_json(receipt, root, "adapter-result", original_adapter)

        uncovered_target = json.loads(json.dumps(receipt))
        uncovered_target["authorization"]["targetIds"].append("repo:uncovered")
        uncovered_target["authorization"]["planSha256"] = compute_plan_sha256(
            uncovered_target
        )
        report = evaluate(uncovered_target, root, now=now)
        assert report["status"] == "BLOCK" and _has_code(
            report, "security-control-plan"
        ), report

        receipt["engines"][0]["supportUntil"] = "9999-12-31"
        report = evaluate(receipt, root, now=now)
        assert report["status"] == "BLOCK" and _has_code(report, "engine-support-horizon"), report

        manual = json.loads(json.dumps(receipt))
        manual["engines"][0]["supportUntil"] = (now + timedelta(days=30)).date().isoformat()
        manual["engines"][0]["licenseDisposition"] = "manual-review"
        report = evaluate(manual, root, now=now)
        assert report["status"] == "NOT_CHECKED" and _has_code(report, "engine-license-review"), report

        expanded = json.loads(json.dumps(manual))
        expanded["engines"][0]["licenseDisposition"] = "allowed"
        expanded["tasks"][0]["plannedCheckIds"].append("history")
        report = evaluate(expanded, root, now=now)
        assert report["status"] == "BLOCK" and _has_code(report, "authorization-plan-drift"), report

        adapter_drift = json.loads(json.dumps(manual))
        adapter_drift["engines"][0]["licenseDisposition"] = "allowed"
        adapter_drift["tasks"][0]["adapterResultSha256"] = "0" * 64
        report = evaluate(adapter_drift, root, now=now)
        assert report["status"] == "BLOCK" and _has_code(report, "adapter-result-binding"), report

        calibration_drift = json.loads(json.dumps(manual))
        calibration_drift["engines"][0]["licenseDisposition"] = "allowed"
        calibration_drift["engines"][0]["calibrationSha256"] = "0" * 64
        report = evaluate(calibration_drift, root, now=now)
        assert report["status"] == "BLOCK" and _has_code(report, "calibration-binding"), report
    finally:
        temporary.cleanup()


def _assert_external_authorization_rejections(now: datetime) -> None:
    temporary, root, receipt = _fresh(now)
    try:
        external = external_fixture(receipt, now, root)
        missing_grant = json.loads(json.dumps(external))
        missing_grant["authorization"]["authorizationEvidenceId"] = None
        missing_grant["authorization"]["authorizationEvidenceSha256"] = None
        missing_grant["evidence"] = [item for item in missing_grant["evidence"] if item["kind"] != "authorization"]
        report = evaluate(missing_grant, root, now=now)
        assert report["status"] == "BLOCK" and _has_code(report, "authorization-evidence-binding"), report

        expired = json.loads(json.dumps(external))
        expired["authorization"]["expiresAt"] = (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
        report = evaluate(expired, root, now=now)
        assert report["status"] == "BLOCK" and _has_code(report, "authorization-window"), report

        outside = json.loads(json.dumps(external))
        outside["tasks"][0]["execution"]["egressAllowlist"] = ["outside.example.test:443"]
        report = evaluate(outside, root, now=now)
        assert report["status"] == "BLOCK" and _has_code(report, "unauthorized-egress"), report

        canonical = json.loads(json.dumps(external))
        canonical["authorization"]["networkScope"] = ["HTTPS://API.EXAMPLE.TEST/scan"]
        _refresh_grant(canonical, root)
        report = evaluate(canonical, root, now=now)
        assert report["status"] == "GREEN", report

        for metadata in ("169.254.169.254:80", "http://169.254.169.254/latest", "metadata.google.internal:80", "http://metadata.google.internal/x"):
            unsafe = json.loads(json.dumps(external))
            unsafe["authorization"]["networkScope"] = [metadata]
            unsafe["tasks"][0]["execution"]["egressAllowlist"] = [metadata]
            report = evaluate(unsafe, root, now=now)
            assert report["status"] == "BLOCK" and _has_code(report, "unsafe-network-scope"), report

        broad = json.loads(json.dumps(external))
        broad["authorization"]["networkScope"] = ["192.0.2.0/24"]
        report = evaluate(broad, root, now=now)
        assert report["status"] == "BLOCK" and _has_code(report, "broad-network-scope"), report
    finally:
        temporary.cleanup()


def _assert_adapter_rejections(now: datetime) -> None:
    report = _adapter_case(now, lambda adapter, _receipt: adapter.update({"rawSourceObservationIds": ["obs-1"], "rawSourceObservationCount": 1}))
    assert report["status"] == "BLOCK" and _has_code(report, "adapter-source-drop"), report
    report = _adapter_case(now, lambda adapter, _receipt: adapter.update({"parserState": "partial", "truncationCount": 1}))
    assert report["status"] == "BLOCK" and _has_code(report, "adapter-parser-incomplete"), report
    report = _adapter_case(now, lambda adapter, _receipt: adapter.update({"parserState": "crashed"}))
    assert report["status"] == "BLOCK" and _has_code(report, "adapter-parser-incomplete"), report

    for field, replacement in (
        ("snapshotSha256", "2" * 64),
        ("commandSha256", "2" * 64),
        ("environmentSha256", "2" * 64),
        ("plannedCheckIds", ["different-plan"]),
        ("executedCheckIds", []),
        ("exitCode", 7),
        ("successMarker", "different-marker"),
    ):
        report = _adapter_case(
            now,
            lambda adapter, _receipt, field=field, replacement=replacement: adapter.update(
                {field: replacement}
            ),
        )
        assert report["status"] == "BLOCK" and _has_code(report, "adapter-execution-drift"), report

    def duplicate_source(adapter: dict[str, Any], receipt: dict[str, Any]) -> None:
        receipt["tasks"][0].update({
            "status": "findings", "rawFindingCount": 1,
            "findings": [{
                "id": "finding-1", "ruleId": "fixture.rule", "fingerprint": "sha256:" + "4" * 64,
                "severity": "high", "confidence": "high", "location": {"path": "src/app.py", "line": 1},
                "evidenceIds": ["raw-secrets"], "status": "open",
            }],
        })
        adapter.update({
            "rawSourceObservationIds": ["obs-1"], "rawSourceObservationCount": 1,
            "normalizedFindings": [{"findingId": "finding-1", "sourceObservationIds": ["obs-1", "obs-1"]}],
        })

    report = _adapter_case(now, duplicate_source)
    assert report["status"] == "BLOCK" and _has_code(report, "adapter-source-duplicate"), report

    def self_approved_disposition(
        adapter: dict[str, Any], receipt: dict[str, Any]
    ) -> None:
        receipt["tasks"][0].update({
            "status": "findings", "rawFindingCount": 1,
            "findings": [{
                "id": "finding-1", "ruleId": "fixture.rule",
                "fingerprint": "sha256:" + "4" * 64,
                "severity": "critical", "confidence": "high",
                "location": {"path": "src/app.py", "line": 1},
                "evidenceIds": ["raw-secrets"], "status": "false_positive",
                "resolution": {
                    "owner": "receipt-author", "reason": "self-approved",
                    "evidenceIds": ["raw-secrets"],
                },
            }],
        })
        adapter.update({
            "rawSourceObservationIds": ["obs-1"],
            "rawSourceObservationCount": 1,
            "normalizedFindings": [{
                "findingId": "finding-1", "sourceObservationIds": ["obs-1"],
            }],
        })

    report = _adapter_case(now, self_approved_disposition)
    assert report["status"] == "NOT_CHECKED" and _has_code(
        report, "finding-disposition-untrusted"
    ), report

    report = _calibration_case(now, lambda calibration: calibration["passedNegativeControlIds"].pop())
    assert report["status"] == "BLOCK" and _has_code(report, "calibration-controls"), report


def _assert_partial_task_handling(now: datetime) -> None:
    for terminal_status in ("timed_out", "cancelled"):
        temporary, root, receipt = _fresh(now)
        try:
            task = receipt["tasks"][0]
            task.update({"status": terminal_status, "reason": "bounded interruption"})
            task["execution"].update({"exitCode": None, "successMarker": None})
            adapter = read_evidence_json(receipt, root, "adapter-result")
            adapter.update({"parserState": "partial", "exitCode": None, "successMarker": None})
            digest = replace_evidence_json(receipt, root, "adapter-result", adapter)
            task["adapterResultSha256"] = digest
            receipt["coverageClaim"] = "PARTIAL"
            report = evaluate(receipt, root, now=now)
            assert report["status"] == "NOT_CHECKED" and _has_code(report, "security-task-not-complete"), report
        finally:
            temporary.cleanup()

    temporary, root, receipt = _fresh(now)
    try:
        receipt["authorization"]["credentialMode"] = "read-only-task-scoped"
        receipt["authorization"]["capabilityBindingSha256"] = "5" * 64
        receipt["authorization"]["planSha256"] = compute_plan_sha256(receipt)
        assert receipt["tasks"][0]["execution"]["credentialMode"] == "none"
        report = evaluate(receipt, root, now=now)
        assert report["status"] == "GREEN", report
    finally:
        temporary.cleanup()


def _assert_evidence_integrity_rejections(now: datetime) -> None:
    temporary, root, receipt = _fresh(now)
    try:
        raw_record = next(item for item in receipt["evidence"] if item["id"] == "raw-secrets")
        raw_path = root / raw_record["path"]
        raw_path.write_bytes(b"{")
        raw_record.update(file_identity(raw_path))
        report = evaluate(receipt, root, now=now)
        assert report["status"] == "BLOCK" and _has_code(report, "adapter-result-identity-drift"), report

        reused = json.loads(json.dumps(receipt))
        reused["tasks"].append({**json.loads(json.dumps(reused["tasks"][0])), "id": "secrets-2"})
        reused["plannedTaskIds"].append("secrets-2")
        reused["authorization"]["planSha256"] = compute_plan_sha256(reused)
        report = evaluate(reused, root, now=now)
        assert report["status"] == "BLOCK" and _has_code(report, "raw-evidence-reused"), report
    finally:
        temporary.cleanup()

    temporary, root, receipt = _fresh(now)
    try:
        unused_path = root / ".rd" / "security-evidence" / "unused.log"
        unused_path.write_text("unused\n", encoding="utf-8")
        receipt["evidence"].append({"id": "unused", "path": ".rd/security-evidence/unused.log", "kind": "log", **file_identity(unused_path)})
        report = evaluate(receipt, root, now=now)
        assert report["status"] == "BLOCK" and _has_code(report, "evidence-ownership"), report

        output_files = json.loads(json.dumps(receipt))
        output_files["evidence"] = [item for item in output_files["evidence"] if item["id"] != "unused"]
        output_files["tasks"][0]["execution"]["limits"]["outputFiles"] = 1
        report = evaluate(output_files, root, now=now)
        assert report["status"] == "BLOCK" and _has_code(report, "execution-output-files"), report

        output_bytes = json.loads(json.dumps(output_files))
        output_bytes["tasks"][0]["execution"]["limits"].update({"outputFiles": 4, "outputBytes": 1})
        report = evaluate(output_bytes, root, now=now)
        assert report["status"] == "BLOCK" and _has_code(report, "execution-output-bytes"), report

        unused_engine = json.loads(json.dumps(output_files))
        extra = json.loads(json.dumps(unused_engine["engines"][0]))
        extra["id"] = "unused-engine"
        extra["supportUntil"] = "2000-01-01"
        unused_engine["engines"].append(extra)
        unused_engine["authorization"]["planSha256"] = compute_plan_sha256(unused_engine)
        report = evaluate(unused_engine, root, now=now)
        assert report["status"] == "BLOCK" and _has_code(report, "unused-engine"), report
        assert not _has_code(report, "stale-engine-knowledge"), report
    finally:
        temporary.cleanup()

    for evidence_id, owner_field, code in (
        ("adapter-result", "adapterResultSha256", "adapter-result-binding"),
        ("engine-calibration", "calibrationSha256", "calibration-binding"),
        ("snapshot-manifest", "snapshotManifestSha256", "snapshot-manifest-binding"),
    ):
        temporary, root, receipt = _fresh(now)
        try:
            record = next(item for item in receipt["evidence"] if item["id"] == evidence_id)
            path = root / record["path"]
            path.write_bytes(b'{"duplicate":1,"duplicate":2}')
            identity = file_identity(path)
            record.update(identity)
            if evidence_id == "adapter-result":
                receipt["tasks"][0][owner_field] = identity["sha256"]
            elif evidence_id == "engine-calibration":
                receipt["engines"][0][owner_field] = identity["sha256"]
            else:
                receipt["target"][owner_field] = identity["sha256"]
            report = evaluate(receipt, root, now=now)
            assert report["status"] == "BLOCK" and _has_code(report, code), report
        finally:
            temporary.cleanup()


def run_v2_negative_tests(now: datetime) -> None:
    _assert_json_number_rejections()
    _assert_target_and_snapshot_rejections(now)
    _assert_freshness_and_plan_rejections(now)
    _assert_external_authorization_rejections(now)
    _assert_adapter_rejections(now)
    _assert_partial_task_handling(now)
    _assert_evidence_integrity_rejections(now)
