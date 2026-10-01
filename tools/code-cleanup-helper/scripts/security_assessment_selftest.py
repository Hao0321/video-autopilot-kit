"""Deterministic positive, compatibility, and boundary tests for the validator."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import security_assessment_registry as registry
import security_assessment_snapshot as snapshot
from security_assessment_evaluator import evaluate, input_error_report
from security_assessment_shared import (
    MAX_EVIDENCE_COUNT,
    MAX_LIST_ITEMS,
    MAX_NESTING_DEPTH,
    MAX_RECEIPT_BYTES,
    MAX_STRING_CHARS,
    SECURITY_CONTROL_IDS,
    SECURITY_CONTROL_PROFILE,
    TARGET_IDENTITY_PROFILE,
    file_identity,
    relative_path,
    safe_path,
)
from security_assessment_v2_common import (
    canonical_sha256,
    compute_plan_sha256,
    parse_json_object,
    target_identity_sha256,
)
from security_assessment_v2_fixtures import external_fixture, legacy_fixture, valid_fixture
from security_assessment_v2_negative_tests import run_v2_negative_tests


def _has_code(report: dict[str, Any], code: str) -> bool:
    return any(item["code"] == code for item in report["findings"])


def _assert_valid_and_identity_cases(
    valid: dict[str, Any],
    root: Path,
    now: datetime,
) -> None:
    assert SECURITY_CONTROL_IDS == (
        "security.scan-scope",
        "security.scan-coverage",
        "security.scanner-provenance",
        "security.finding-normalization",
        "security.engine-admission",
        "security.adapter-integrity",
    )
    assert canonical_sha256(list(SECURITY_CONTROL_IDS)) == (
        "7c3406d164220d916ad5aaea331629ed663c58029210cf61b11073cd5abe6100"
    )
    valid_report = evaluate(valid, root, now=now)
    assert valid_report["status"] == "GREEN", valid_report
    assert valid_report["receiptSchemaVersion"] == 2
    assert valid_report["recordedAt"] == "2026-09-04T12:00:00Z"
    assert valid_report["ageSeconds"] == 0
    assert valid_report["target"] == {
        "identityProfile": TARGET_IDENTITY_PROFILE,
        "identitySha256": target_identity_sha256("Fixture", "1.0.0"),
        "snapshotSha256": valid["target"]["snapshotSha256"],
        "snapshotProfile": "cleanup-security-input/v1",
        "snapshotVerified": True,
    }
    assert "Fixture" not in json.dumps(valid_report, ensure_ascii=False)
    assert "1.0.0" not in json.dumps(valid_report, ensure_ascii=False)
    assert valid_report["authorization"] == {
        "externalContact": False,
        "planSha256": valid["authorization"]["planSha256"],
        "frozenGrantSha256": None,
    }
    assert valid_report["controlCoverage"] == {
        "profile": SECURITY_CONTROL_PROFILE,
        "requiredControlIdsSha256": canonical_sha256(list(SECURITY_CONTROL_IDS)),
        "requiredControls": 6,
        "targetCount": 1,
        "requiredCells": 6,
        "plannedCells": 6,
        "executedCells": 6,
    }

    legacy = evaluate(legacy_fixture(valid), root, now=now)
    assert legacy["status"] == "NOT_CHECKED", legacy
    assert _has_code(legacy, "legacy-unbound-security-receipt")
    assert legacy["target"]["identitySha256"] == target_identity_sha256("Fixture", "1.0.0")

    unicode_identity = json.loads(json.dumps(valid))
    unicode_identity["target"].update({"product": "自由工坊 🧪", "version": "版本-一"})
    unicode_identity["authorization"]["planSha256"] = compute_plan_sha256(unicode_identity)
    unicode_report = evaluate(unicode_identity, root, now=now)
    assert unicode_report["status"] == "GREEN", unicode_report
    assert unicode_report["target"]["identitySha256"] == target_identity_sha256(
        "自由工坊 🧪", "版本-一",
    )
    unicode_serialized = json.dumps(unicode_report, ensure_ascii=False)
    assert "自由工坊" not in unicode_serialized and "版本-一" not in unicode_serialized

    identity_plan_drift = json.loads(json.dumps(unicode_identity))
    identity_plan_drift["target"]["product"] = "另一個產品"
    report = evaluate(identity_plan_drift, root, now=now)
    assert report["status"] == "BLOCK" and _has_code(report, "authorization-plan-drift"), report


def _assert_rejections_and_paths(valid: dict[str, Any], root: Path, now: datetime) -> None:
    def rejected(mutator: Callable[[dict[str, Any]], None], code: str) -> None:
        broken = json.loads(json.dumps(valid))
        mutator(broken)
        report = evaluate(broken, root, now=now)
        assert report["status"] == "BLOCK", report
        assert _has_code(report, code), report

    rejected(lambda value: value["tasks"].clear(), "missing-planned-task")
    rejected(lambda value: value["tasks"][0]["executedCheckIds"].clear(), "false-complete-task")
    rejected(lambda value: value["tasks"][0]["execution"].update({"successMarker": None}), "false-provider-success")
    rejected(lambda value: value["tasks"][0]["execution"].update({"inputReadOnly": False}), "unsafe-execution-isolation")
    rejected(lambda value: value["engines"][0].update({"version": "latest"}), "engine-identity")
    rejected(lambda value: value["evidence"][0].update({"sha256": "0" * 64}), "stale-security-evidence")
    rejected(lambda value: value.update({"snippet": "redacted-but-forbidden"}), "security-evidence-sensitive")
    rejected(lambda value: value["authorization"].update({"destructiveActions": True}), "destructive-activity")
    rejected(lambda value: value["authorization"].update({"targetIds": ["repo:*"]}), "target-id")
    rejected(lambda value: value["evidence"][0].update({"path": ".rd/security-evidence/raw.jsonl:ads"}), "unsafe-evidence-path")
    rejected(lambda value: value["evidence"][0].update({"path": ".rd/security-evidence/raw\n.jsonl"}), "unsafe-evidence-path")

    assert safe_path(root, ".rd/security-evidence/raw.jsonl:ads")[0] is None
    assert safe_path(root, ".rd/security-evidence/raw\u0001.jsonl")[0] is None
    for unsafe in (
        "src/file. ", "src/file.", "src/CON.txt", "src/a<b", "src/a:b",
        "src/COM¹.txt", "src/LPT².log", "src/CONIN$", "src/CONOUT$",
    ):
        assert not relative_path(unsafe), unsafe

    link_paths = [root / "broken-link", root / "loop-a", root / "loop-b"]
    try:
        link_paths[0].symlink_to(root / "missing-target")
        link_paths[1].symlink_to("loop-b")
        link_paths[2].symlink_to("loop-a")
    except (OSError, NotImplementedError):
        pass
    else:
        for link in link_paths:
            assert safe_path(root, link.name)[0] is None, link
    finally:
        for link in link_paths:
            try:
                link.unlink()
            except OSError:
                pass


class _OverLimitScan:
    def __init__(self) -> None:
        self.count = 0

    def __enter__(self) -> "_OverLimitScan":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def __iter__(self) -> "_OverLimitScan":
        return self

    def __next__(self) -> object:
        self.count += 1
        if self.count > snapshot.MAX_SNAPSHOT_OBJECTS + 1:
            raise AssertionError("snapshot enumeration exceeded its pre-sort bound")
        return object()


def _assert_snapshot_object_bound(root: Path) -> None:
    scan = _OverLimitScan()
    original_scandir = snapshot.os.scandir
    snapshot_failures: list[str] = []
    snapshot.os.scandir = lambda _directory: scan
    try:
        assert snapshot._live_entries(
            root,
            lambda code, _message, **_details: snapshot_failures.append(code),
        ) is None
    finally:
        snapshot.os.scandir = original_scandir
    assert scan.count == snapshot.MAX_SNAPSHOT_OBJECTS + 1
    assert snapshot_failures == ["snapshot-object-limit"]


def _assert_evidence_and_coverage_cases(
    valid: dict[str, Any],
    root: Path,
    now: datetime,
) -> None:
    empty_path = root / ".rd" / "security-evidence" / "empty.jsonl"
    empty_path.write_bytes(b"")
    empty_evidence = json.loads(json.dumps(valid))
    empty_evidence["evidence"][0].update({"path": ".rd/security-evidence/empty.jsonl", **file_identity(empty_path)})
    report = evaluate(empty_evidence, root, now=now)
    assert report["status"] == "BLOCK" and _has_code(report, "empty-evidence"), report

    excess_evidence = json.loads(json.dumps(valid))
    prototype = excess_evidence["evidence"][0]
    excess_evidence["evidence"] = [
        {**prototype, "id": f"evidence-{index}"}
        for index in range(MAX_EVIDENCE_COUNT + 1)
    ]
    report = evaluate(excess_evidence, root, now=now)
    assert report["status"] == "BLOCK" and _has_code(report, "evidence-count-limit"), report

    second_path = root / ".rd" / "security-evidence" / "second.jsonl"
    second_path.write_text('{"event":"second"}\n', encoding="utf-8")
    aggregate = json.loads(json.dumps(valid))
    aggregate["evidence"].append({
        "id": "raw-second", "path": ".rd/security-evidence/second.jsonl",
        "kind": "raw", **file_identity(second_path),
    })
    original_limit = registry.MAX_TOTAL_EVIDENCE_BYTES
    registry.MAX_TOTAL_EVIDENCE_BYTES = aggregate["evidence"][0]["bytes"]
    try:
        report = evaluate(aggregate, root, now=now)
    finally:
        registry.MAX_TOTAL_EVIDENCE_BYTES = original_limit
    assert report["status"] == "BLOCK" and _has_code(report, "evidence-total-limit"), report

    partial = json.loads(json.dumps(valid))
    partial["tasks"][0].update({
        "status": "not_tested", "executedCheckIds": [], "reason": "engine unavailable",
        "rawEvidenceId": None, "evidenceIds": [], "adapterResultEvidenceId": None,
        "adapterResultSha256": None, "execution": None,
    })
    partial["evidence"] = [item for item in partial["evidence"] if item["kind"] not in {"raw", "adapter-result"}]
    partial["coverageClaim"] = "PARTIAL"
    report = evaluate(partial, root, now=now)
    assert report["status"] == "NOT_CHECKED" and _has_code(report, "security-task-not-complete"), report

    claimed_execution = json.loads(json.dumps(valid))
    claimed_execution["tasks"][0].update({"status": "failed", "reason": "incomplete result"})
    claimed_execution["coverageClaim"] = "PARTIAL"
    report = evaluate(claimed_execution, root, now=now)
    assert report["status"] == "NOT_CHECKED", report
    assert report["controlCoverage"]["executedCells"] == 0, report
    assert _has_code(report, "security-control-not-executed"), report

    zero_checks = json.loads(json.dumps(partial))
    zero_checks["tasks"][0]["plannedCheckIds"] = []
    zero_checks["authorization"]["planSha256"] = compute_plan_sha256(zero_checks)
    report = evaluate(zero_checks, root, now=now)
    assert report["status"] == "BLOCK" and _has_code(report, "security-control-plan"), report


def _assert_privacy_and_structure_cases(
    valid: dict[str, Any],
    root: Path,
    now: datetime,
) -> None:
    external = external_fixture(valid, now, root)
    report = evaluate(external, root, now=now)
    assert report["status"] == "GREEN", report
    assert report["authorization"]["externalContact"] is True
    assert report["authorization"]["frozenGrantSha256"] == external["authorization"]["authorizationEvidenceSha256"]

    reflection = json.loads(json.dumps(valid))
    reflection["ATTACKER_FIELD_NEVER_REFLECT"] = "ATTACKER_VALUE_NEVER_REFLECT"
    reflection["plannedTaskIds"] = ["ATTACKER_ID_NEVER_REFLECT"]
    reflection["tasks"][0]["id"] = "ATTACKER_ID_NEVER_REFLECT"
    reflection["target"]["version"] = "password=ATTACKER_TARGET_NEVER_REFLECT"
    serialized = json.dumps(evaluate(reflection, root, now=now), ensure_ascii=False)
    for marker in (
        "ATTACKER_FIELD_NEVER_REFLECT", "ATTACKER_VALUE_NEVER_REFLECT",
        "ATTACKER_ID_NEVER_REFLECT", "ATTACKER_TARGET_NEVER_REFLECT",
    ):
        assert marker not in serialized, serialized

    oversized_string = json.loads(json.dumps(valid))
    oversized_string["target"]["product"] = "x" * (MAX_STRING_CHARS + 1)
    assert _has_code(evaluate(oversized_string, root, now=now), "receipt-structure-limit")
    oversized_list = json.loads(json.dumps(valid))
    oversized_list["plannedTaskIds"] = ["x"] * (MAX_LIST_ITEMS + 1)
    assert _has_code(evaluate(oversized_list, root, now=now), "receipt-structure-limit")
    nested: dict[str, Any] = {"leaf": True}
    for _ in range(MAX_NESTING_DEPTH + 1):
        nested = {"next": nested}
    excessive_depth = json.loads(json.dumps(valid))
    excessive_depth["extra"] = nested
    assert _has_code(evaluate(excessive_depth, root, now=now), "receipt-structure-limit")


def _assert_input_and_cli_boundaries(root: Path) -> None:
    try:
        parse_json_object(b'{"duplicate":1,"duplicate":2}')
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate JSON keys must be rejected")
    input_error = input_error_report("receipt-invalid")
    assert input_error["status"] == "BLOCK"
    assert input_error["target"] == {
        "identityProfile": None,
        "identitySha256": None,
        "snapshotSha256": None,
        "snapshotProfile": None,
        "snapshotVerified": False,
    }

    cli = Path(__file__).with_name("check_security_assessment.py")
    duplicate_receipt = root / ".rd" / "duplicate-receipt.json"
    duplicate_receipt.write_bytes(b'{"schemaVersion":2,"schemaVersion":2}')
    child = subprocess.run(
        [sys.executable, str(cli), str(root), "--receipt", ".rd/duplicate-receipt.json", "--format", "json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert child.returncode == 1 and json.loads(child.stdout)["status"] == "BLOCK", child
    oversized_receipt = root / ".rd" / "oversized-receipt.json"
    oversized_receipt.write_bytes(b"{" + b" " * MAX_RECEIPT_BYTES + b"}")
    child = subprocess.run(
        [sys.executable, str(cli), str(root), "--receipt", ".rd/oversized-receipt.json", "--format", "json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert child.returncode == 1 and json.loads(child.stdout)["status"] == "BLOCK", child
    child = subprocess.run([sys.executable, str(cli)], capture_output=True, text=True, check=False)
    assert child.returncode == 2, child


def run_self_test() -> None:
    now = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory(prefix="cleanup-security-assessment-") as raw:
        root = Path(raw)
        valid = valid_fixture(root, now)
        _assert_valid_and_identity_cases(valid, root, now)
        _assert_rejections_and_paths(valid, root, now)
        _assert_snapshot_object_bound(root)
        _assert_evidence_and_coverage_cases(valid, root, now)
        _assert_privacy_and_structure_cases(valid, root, now)
        _assert_input_and_cli_boundaries(root)

    run_v2_negative_tests(now)
