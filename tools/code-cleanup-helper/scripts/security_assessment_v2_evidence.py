"""Validate calibration and adapter-result evidence for receipt v2."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from security_assessment_shared import (
    DIGEST_RE,
    SHA256_RE,
    TERMINAL_COMPLETE,
    FailureSink,
    closed_fields,
    string_list,
    timestamp,
)
from security_assessment_v2_common import load_json_evidence


CALIBRATION_PROFILE = "cleanup-security-calibration/v1"
ADAPTER_RESULT_PROFILE = "cleanup-security-adapter-result/v1"
MAX_CALIBRATION_BYTES = 1024 * 1024
MAX_ADAPTER_RESULT_BYTES = 2 * 1024 * 1024
MAX_CALIBRATION_AGE = timedelta(days=30)
MAX_SOURCE_OBSERVATIONS = 1_024
REQUIRED_NEGATIVE_CONTROLS = frozenset({
    "known-finding-detected",
    "malformed-output-rejected",
    "truncated-output-rejected",
    "parser-crash-rejected",
    "source-drop-rejected",
    "duplicate-source-rejected",
})


def _bound_record(
    owner: dict[str, Any],
    evidence: dict[str, dict[str, Any]],
    *,
    id_field: str,
    sha_field: str,
    expected_kind: str,
    fail: FailureSink,
    code: str,
) -> dict[str, Any] | None:
    evidence_id = owner.get(id_field)
    record = evidence.get(evidence_id.casefold()) if isinstance(evidence_id, str) else None
    expected_sha = owner.get(sha_field)
    if (
        not isinstance(record, dict)
        or not isinstance(expected_sha, str)
        or not SHA256_RE.fullmatch(expected_sha)
        or record.get("sha256") != expected_sha
        or record.get("kind") != expected_kind
    ):
        fail(code, "evidence reference is not bound to its exact digest")
        return None
    return record


def validate_calibrations(
    root: Path,
    engines: dict[str, dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
    recorded: datetime,
    fail: FailureSink,
) -> None:
    for engine in engines.values():
        if engine.get("admissionStatus") != "admitted":
            continue
        record = _bound_record(
            engine,
            evidence,
            id_field="calibrationEvidenceId",
            sha_field="calibrationSha256",
            expected_kind="calibration",
            fail=fail,
            code="calibration-binding",
        )
        document = load_json_evidence(
            record,
            root,
            expected_kind="calibration",
            max_bytes=MAX_CALIBRATION_BYTES,
            fail=fail,
            code="calibration-binding",
        ) if record else None
        if document is None:
            continue
        closed_fields(document, {
            "schemaVersion", "profile", "engineId", "engineVersion", "sourceRevision", "artifactDigest",
            "adapterSha256", "rulesSha256", "dataSha256", "fingerprintSchema",
            "fixtureSetSha256", "calibratedAt", "passedNegativeControlIds",
        }, "calibration", fail)
        expected_identity = {
            "engineId": engine.get("id"),
            "engineVersion": engine.get("version"),
            "sourceRevision": engine.get("sourceRevision"),
            "artifactDigest": engine.get("artifactDigest"),
            "adapterSha256": engine.get("adapterSha256"),
            "rulesSha256": engine.get("rulesSha256"),
            "dataSha256": engine.get("dataSha256"),
            "fingerprintSchema": engine.get("fingerprintSchema"),
        }
        if document.get("schemaVersion") != 1 or document.get("profile") != CALIBRATION_PROFILE:
            fail("calibration-profile", "calibration evidence uses an unsupported profile")
        if any(document.get(field) != value for field, value in expected_identity.items()):
            fail("calibration-identity-drift", "calibration evidence differs from engine identity")
        fixture_sha = document.get("fixtureSetSha256")
        if not isinstance(fixture_sha, str) or not SHA256_RE.fullmatch(fixture_sha):
            fail("calibration-fixture-binding", "calibration fixture set needs an exact digest")
        controls = string_list(
            document.get("passedNegativeControlIds"),
            "calibration.passedNegativeControlIds",
            fail,
        )
        if {item.casefold() for item in controls} != REQUIRED_NEGATIVE_CONTROLS:
            fail("calibration-controls", "calibration must pass the validator-owned negative controls")
        calibrated = timestamp(document.get("calibratedAt"))
        if calibrated is None or calibrated > recorded or recorded - calibrated > MAX_CALIBRATION_AGE:
            fail("calibration-age", "calibration evidence is outside its accepted time window")


def _nonnegative_count(value: Any, fail: FailureSink, code: str) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SOURCE_OBSERVATIONS:
        fail(code, "adapter result count is outside validator bounds")
        return None
    return value


def _validate_normalized_sources(
    document: dict[str, Any],
    task: dict[str, Any],
    raw_ids: list[str],
    fail: FailureSink,
) -> None:
    normalized = document.get("normalizedFindings")
    if not isinstance(normalized, list) or len(normalized) > MAX_SOURCE_OBSERVATIONS:
        fail("adapter-normalized-findings", "adapter normalized finding ledger is invalid")
        return
    task_findings = task.get("findings") if isinstance(task.get("findings"), list) else []
    expected_finding_ids = {
        item.get("id").casefold()
        for item in task_findings
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    normalized_finding_ids: set[str] = set()
    assigned: Counter[str] = Counter()
    for index, raw in enumerate(normalized):
        if not isinstance(raw, dict):
            fail("adapter-normalized-findings", "adapter normalized finding entry is invalid")
            continue
        closed_fields(raw, {"findingId", "sourceObservationIds"}, f"normalized[{index}]", fail)
        finding_id = raw.get("findingId")
        if not isinstance(finding_id, str) or not finding_id:
            fail("adapter-normalized-findings", "adapter normalized finding ID is invalid")
            continue
        key = finding_id.casefold()
        if key in normalized_finding_ids:
            fail("adapter-normalized-duplicate", "adapter repeats a normalized finding ID")
        normalized_finding_ids.add(key)
        source_ids = string_list(
            raw.get("sourceObservationIds"),
            f"normalized[{index}].sourceObservationIds",
            fail,
        )
        assigned.update(item.casefold() for item in source_ids)
    raw_keys = {item.casefold() for item in raw_ids}
    if normalized_finding_ids != expected_finding_ids:
        fail("adapter-finding-drift", "adapter normalized finding IDs differ from the task ledger")
    if set(assigned) != raw_keys:
        fail("adapter-source-drop", "adapter did not account for every raw source observation")
    if any(count != 1 for count in assigned.values()):
        fail("adapter-source-duplicate", "adapter assigned a raw source observation more than once")


def validate_adapter_results(
    root: Path,
    tasks: Any,
    engines: dict[str, dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
    fail: FailureSink,
) -> None:
    if not isinstance(tasks, list):
        return
    used_raw: set[str] = set()
    used_adapter: set[str] = set()
    for task in tasks:
        if not isinstance(task, dict):
            continue
        executed = task.get("executedCheckIds")
        was_executed = isinstance(executed, list) and bool(executed)
        raw_evidence_id = task.get("rawEvidenceId")
        adapter_id = task.get("adapterResultEvidenceId")
        if not was_executed:
            if adapter_id is not None or task.get("adapterResultSha256") is not None:
                fail("adapter-unexecuted", "unexecuted task cannot claim adapter-result evidence")
            continue
        if isinstance(raw_evidence_id, str):
            raw_key = raw_evidence_id.casefold()
            if raw_key in used_raw:
                fail("raw-evidence-reused", "raw evidence cannot satisfy multiple tasks")
            used_raw.add(raw_key)
        if isinstance(adapter_id, str):
            adapter_key = adapter_id.casefold()
            if adapter_key in used_adapter:
                fail("adapter-evidence-reused", "adapter evidence cannot satisfy multiple tasks")
            used_adapter.add(adapter_key)
        record = _bound_record(
            task,
            evidence,
            id_field="adapterResultEvidenceId",
            sha_field="adapterResultSha256",
            expected_kind="adapter-result",
            fail=fail,
            code="adapter-result-binding",
        )
        document = load_json_evidence(
            record,
            root,
            expected_kind="adapter-result",
            max_bytes=MAX_ADAPTER_RESULT_BYTES,
            fail=fail,
            code="adapter-result-binding",
        ) if record else None
        if document is None:
            continue
        closed_fields(document, {
            "schemaVersion", "profile", "taskId", "rawEvidenceId",
            "rawEvidenceSha256", "engineId", "engineVersion", "engineSourceRevision",
            "engineArtifactDigest", "fingerprintSchema",
            "adapterSha256", "rulesSha256", "dataSha256",
            "snapshotSha256", "commandSha256", "environmentSha256",
            "plannedCheckIds", "executedCheckIds", "exitCode", "successMarker",
            "parserState",
            "rawSourceObservationIds", "rawSourceObservationCount",
            "normalizedFindings", "truncationCount", "unparsedCount",
        }, "adapter-result", fail)
        engine_id = task.get("engineId")
        engine = engines.get(engine_id.casefold()) if isinstance(engine_id, str) else None
        raw_record = evidence.get(raw_evidence_id.casefold()) if isinstance(raw_evidence_id, str) else None
        expected_identity = {
            "taskId": task.get("id"),
            "rawEvidenceId": raw_evidence_id,
            "rawEvidenceSha256": raw_record.get("sha256") if isinstance(raw_record, dict) else None,
            "engineId": engine_id,
            "engineVersion": engine.get("version") if engine else None,
            "engineSourceRevision": engine.get("sourceRevision") if engine else None,
            "engineArtifactDigest": engine.get("artifactDigest") if engine else None,
            "fingerprintSchema": engine.get("fingerprintSchema") if engine else None,
            "adapterSha256": engine.get("adapterSha256") if engine else None,
            "rulesSha256": engine.get("rulesSha256") if engine else None,
            "dataSha256": engine.get("dataSha256") if engine else None,
        }
        if document.get("schemaVersion") != 1 or document.get("profile") != ADAPTER_RESULT_PROFILE:
            fail("adapter-result-profile", "adapter result uses an unsupported profile")
        if any(document.get(field) != value for field, value in expected_identity.items()):
            fail("adapter-result-identity-drift", "adapter result differs from task, raw, or engine identity")
        execution = task.get("execution") if isinstance(task.get("execution"), dict) else {}
        expected_execution = {
            "snapshotSha256": execution.get("snapshotSha256"),
            "commandSha256": execution.get("commandSha256"),
            "environmentSha256": execution.get("environmentSha256"),
            "plannedCheckIds": task.get("plannedCheckIds"),
            "executedCheckIds": task.get("executedCheckIds"),
            "exitCode": execution.get("exitCode"),
            "successMarker": execution.get("successMarker"),
        }
        if any(document.get(field) != value for field, value in expected_execution.items()):
            fail(
                "adapter-execution-drift",
                "adapter result differs from the exact task execution provenance",
            )
        raw_ids = string_list(
            document.get("rawSourceObservationIds"),
            "adapter-result.rawSourceObservationIds",
            fail,
            allow_empty=True,
        )
        raw_count = _nonnegative_count(document.get("rawSourceObservationCount"), fail, "adapter-source-count")
        if raw_count is not None and raw_count != len(raw_ids):
            fail("adapter-source-count", "raw source observation count differs from its ID ledger")
        _validate_normalized_sources(document, task, raw_ids, fail)
        truncation = _nonnegative_count(document.get("truncationCount"), fail, "adapter-truncation")
        unparsed = _nonnegative_count(document.get("unparsedCount"), fail, "adapter-unparsed")
        parser_state = document.get("parserState")
        if parser_state not in {"complete", "partial", "crashed"}:
            fail("adapter-parser-state", "adapter parser state is unsupported")
        if task.get("status") in TERMINAL_COMPLETE and (
            parser_state != "complete" or truncation != 0 or unparsed != 0
        ):
            fail("adapter-parser-incomplete", "complete task has partial, crashed, truncated, or unparsed adapter output")
