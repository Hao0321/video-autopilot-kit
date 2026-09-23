"""Compose security-assessment validators into one stable evaluation API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
from typing import Any

from security_assessment_registry import (
    validate_authorization,
    validate_engines,
    validate_evidence,
    validate_header,
)
from security_assessment_shared import (
    TARGET_IDENTITY_PROFILE,
    TARGET_PRODUCT_MAX_CHARS,
    TARGET_PRODUCT_MAX_UTF8_BYTES,
    TARGET_VERSION_MAX_CHARS,
    TARGET_VERSION_MAX_UTF8_BYTES,
    SECURITY_CONTROL_IDS,
    SECURITY_CONTROL_PROFILE,
    document_structure_within_limits,
    redact_sensitive_values,
    safe_target_identity,
    string_list,
    timestamp,
)
from security_assessment_tasks import validate_security_control_coverage, validate_tasks
from security_assessment_snapshot import SNAPSHOT_PROFILE
from security_assessment_v2_bindings import validate_v2_bindings
from security_assessment_v2_common import canonical_sha256, target_identity_sha256


REPORT_CODE_RE = re.compile(r"^[a-z0-9-]{1,80}$")
EMPTY_TARGET_REPORT = {
    "identityProfile": None,
    "identitySha256": None,
    "snapshotSha256": None,
}
MAX_RECEIPT_AGE = timedelta(hours=24)


def _report_finding(status: str, code: str) -> dict[str, str]:
    safe_code = code if REPORT_CODE_RE.fullmatch(code) else "validation-error"
    message = (
        "security assessment validation failed"
        if status == "FAIL"
        else "security assessment coverage is incomplete"
    )
    return {"status": status, "code": safe_code, "message": message}


def input_error_report(code: str = "receipt-structure-limit") -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "receiptSchemaVersion": None,
        "recordedAt": None,
        "ageSeconds": None,
        "status": "BLOCK",
        "target": {**EMPTY_TARGET_REPORT, "snapshotProfile": None, "snapshotVerified": False},
        "authorization": {
            "externalContact": None,
            "planSha256": None,
            "frozenGrantSha256": None,
        },
        "coverage": {
            "claim": "PARTIAL",
            "plannedTasks": 0,
            "terminalStatusCounts": {},
            "openFindings": 0,
        },
        "controlCoverage": {
            "profile": None,
            "requiredControlIdsSha256": None,
            "requiredControls": 0,
            "targetCount": 0,
            "requiredCells": 0,
            "plannedCells": 0,
            "executedCells": 0,
        },
        "checked": {"engines": 0, "evidence": 0},
        "findings": [_report_finding("FAIL", code)],
    }


def _safe_target(target: dict[str, Any], schema_version: int, snapshot_verified: bool) -> dict[str, Any]:
    product = target.get("product")
    version = target.get("version")
    snapshot = target.get("snapshotSha256")
    identity_valid = (
        safe_target_identity(
            product,
            max_chars=TARGET_PRODUCT_MAX_CHARS,
            max_utf8_bytes=TARGET_PRODUCT_MAX_UTF8_BYTES,
        )
        and safe_target_identity(
            version,
            max_chars=TARGET_VERSION_MAX_CHARS,
            max_utf8_bytes=TARGET_VERSION_MAX_UTF8_BYTES,
        )
    )
    identity_sha = (
        target_identity_sha256(product, version)
        if identity_valid and isinstance(product, str) and isinstance(version, str)
        else None
    )
    return {
        "identityProfile": TARGET_IDENTITY_PROFILE if identity_sha is not None else None,
        "identitySha256": identity_sha,
        "snapshotSha256": (
            snapshot
            if isinstance(snapshot, str) and re.fullmatch(r"[0-9a-f]{64}", snapshot)
            else None
        ),
        "snapshotProfile": (
            SNAPSHOT_PROFILE
            if schema_version == 2 and target.get("snapshotProfile") == SNAPSHOT_PROFILE
            else None
        ),
        "snapshotVerified": snapshot_verified if schema_version == 2 else False,
    }


def evaluate(
    document: dict[str, Any],
    root: Path,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not isinstance(document, dict) or not document_structure_within_limits(document):
        return input_error_report()
    failures: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    recorded_findings: set[tuple[str, str]] = set()

    def fail(code: str, message: str, **details: Any) -> None:
        del message, details
        key = ("FAIL", code)
        if key not in recorded_findings:
            recorded_findings.add(key)
            failures.append(_report_finding(*key))

    def gap(code: str, message: str, **details: Any) -> None:
        del message, details
        key = ("NOT_CHECKED", code)
        if key not in recorded_findings:
            recorded_findings.add(key)
            gaps.append(_report_finding(*key))

    raw_schema_version = document.get("schemaVersion")
    schema_version = raw_schema_version if raw_schema_version in {1, 2} else 1
    target, recorded = validate_header(document, fail, current, schema_version)
    authorization = validate_authorization(document.get("authorization"), recorded, fail, schema_version)
    raw_tasks = document.get("tasks") if isinstance(document.get("tasks"), list) else []
    referenced_engines = {
        task.get("engineId").casefold()
        for task in raw_tasks
        if isinstance(task, dict) and isinstance(task.get("engineId"), str)
    }
    engines = validate_engines(
        document.get("engines"),
        recorded,
        current,
        fail,
        gap,
        schema_version,
        referenced_engines if schema_version == 2 else None,
    )
    evidence = validate_evidence(document.get("evidence"), root, fail, schema_version)
    planned = string_list(document.get("plannedTaskIds"), "plannedTaskIds", fail)
    coverage_complete, open_findings, status_counts = validate_tasks(
        document.get("tasks"), planned, target, authorization, engines, evidence, fail, gap, schema_version
    )
    planned_controls, executed_controls = validate_security_control_coverage(
        document.get("tasks"), authorization.get("targetIds"), fail, gap, schema_version
    )
    target_count = (
        len(authorization.get("targetIds", []))
        if raw_schema_version == 2 and isinstance(authorization.get("targetIds"), list)
        else 0
    )
    v2_metadata = {"snapshotVerified": False, "frozenGrantSha256": None, "planSha256": None}
    if raw_schema_version == 1:
        gap("legacy-unbound-security-receipt", "receipt v1 lacks promotion-grade live bindings")
    elif raw_schema_version == 2:
        if current - recorded > MAX_RECEIPT_AGE:
            gap("stale-security-receipt", "receipt exceeds the validator-owned maximum age")
        v2_metadata = validate_v2_bindings(
            document,
            root,
            target,
            authorization,
            engines,
            evidence,
            recorded,
            fail,
        )
    expected_claim = "COMPLETE" if coverage_complete else "PARTIAL"
    if document.get("coverageClaim") != expected_claim:
        fail(
            "false-coverage-claim",
            "coverageClaim does not match the closed-world task ledger",
            expected=expected_claim,
            observed=document.get("coverageClaim"),
        )

    status = "BLOCK" if failures else "NOT_CHECKED" if gaps else "GREEN"
    findings = [*failures, *gaps]
    if not findings:
        findings = [{
            "status": "PASS",
            "code": "security-assessment-current",
            "message": "all planned checks have current, bounded, authorized evidence and no open findings",
        }]
    report = {
        "schemaVersion": 1,
        "receiptSchemaVersion": raw_schema_version if raw_schema_version in {1, 2} else None,
        "recordedAt": None,
        "ageSeconds": None,
        "status": status,
        "target": _safe_target(target, schema_version, bool(v2_metadata["snapshotVerified"])),
        "authorization": {
            "externalContact": (
                authorization.get("externalContact")
                if isinstance(authorization.get("externalContact"), bool)
                else None
            ),
            "planSha256": v2_metadata["planSha256"],
            "frozenGrantSha256": v2_metadata["frozenGrantSha256"],
        },
        "coverage": {
            "claim": expected_claim,
            "plannedTasks": len(planned),
            "terminalStatusCounts": dict(sorted(status_counts.items())),
            "openFindings": open_findings,
        },
        "controlCoverage": {
            "profile": SECURITY_CONTROL_PROFILE if raw_schema_version == 2 else None,
            "requiredControlIdsSha256": (
                canonical_sha256(list(SECURITY_CONTROL_IDS))
                if raw_schema_version == 2
                else None
            ),
            "requiredControls": len(SECURITY_CONTROL_IDS) if raw_schema_version == 2 else 0,
            "targetCount": target_count,
            "requiredCells": len(SECURITY_CONTROL_IDS) * target_count,
            "plannedCells": planned_controls,
            "executedCells": executed_controls,
        },
        "checked": {"engines": len(engines), "evidence": len(evidence)},
        "findings": findings,
    }
    source_recorded = timestamp(document.get("recordedAt"))
    if source_recorded is not None:
        report["recordedAt"] = source_recorded.isoformat().replace("+00:00", "Z")
        report["ageSeconds"] = max(0, int((current - source_recorded).total_seconds()))
    return redact_sensitive_values(report)
