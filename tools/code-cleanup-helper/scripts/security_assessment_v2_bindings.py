"""Cross-record plan, grant, ownership, snapshot, and evidence bindings for v2."""

from __future__ import annotations

from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from security_assessment_network import canonical_network_destination
from security_assessment_shared import SHA256_RE, FailureSink, closed_fields, safe_identity_text
from security_assessment_snapshot import validate_snapshot
from security_assessment_v2_common import compute_plan_sha256, load_json_evidence
from security_assessment_v2_evidence import validate_adapter_results, validate_calibrations


EVIDENCE_ROOT = (".rd", "security-evidence")
MAX_AUTHORIZATION_EVIDENCE_BYTES = 256 * 1024


def _evidence_under_fixed_root(
    evidence: dict[str, dict[str, Any]],
    fail: FailureSink,
) -> None:
    for record in evidence.values():
        path = record.get("path")
        parts = PurePosixPath(path).parts if isinstance(path, str) else ()
        if tuple(part.casefold() for part in parts[:2]) != EVIDENCE_ROOT:
            fail("v2-evidence-root", "v2 evidence must stay under the validator-owned evidence root")


def authorization_projection(
    document: dict[str, Any],
    authorization: dict[str, Any],
) -> dict[str, Any]:
    raw_scope = authorization.get("networkScope")
    canonical_scope: list[str] = []
    if isinstance(raw_scope, list):
        for value in raw_scope:
            canonical, error = canonical_network_destination(value)
            canonical_scope.append(canonical if not error and canonical is not None else "[invalid]")
    return {
        "schemaVersion": 1,
        "assessmentId": document.get("assessmentId"),
        "planSha256": authorization.get("planSha256"),
        "targetIds": sorted(authorization.get("targetIds", []), key=str.casefold),
        "activityTier": authorization.get("activityTier"),
        "externalContact": True,
        "networkScope": sorted(canonical_scope, key=str.casefold),
        "authorizedBy": authorization.get("authorizedBy"),
        "grantedAt": authorization.get("grantedAt"),
        "expiresAt": authorization.get("expiresAt"),
        "redirectPolicy": authorization.get("redirectPolicy"),
        "proxyMode": authorization.get("proxyMode"),
        "dnsPolicy": authorization.get("dnsPolicy"),
        "credentialMode": authorization.get("credentialMode"),
        "capabilityBindingSha256": authorization.get("capabilityBindingSha256"),
        "destructiveActions": authorization.get("destructiveActions"),
        "limits": authorization.get("limits"),
    }


def _validate_plan(
    document: dict[str, Any],
    target: dict[str, Any],
    authorization: dict[str, Any],
    fail: FailureSink,
) -> bool:
    observed = authorization.get("planSha256")
    expected = compute_plan_sha256(document, target=target, authorization=authorization)
    if not isinstance(observed, str) or not SHA256_RE.fullmatch(observed) or observed != expected:
        fail("authorization-plan-drift", "authorization does not bind the exact task and engine plan")
        return False
    return True


def _validate_authorization_evidence(
    root: Path,
    document: dict[str, Any],
    authorization: dict[str, Any],
    evidence: dict[str, dict[str, Any]],
    fail: FailureSink,
) -> str | None:
    evidence_id = authorization.get("authorizationEvidenceId")
    expected_sha = authorization.get("authorizationEvidenceSha256")
    if authorization.get("externalContact") is not True:
        if evidence_id is not None or expected_sha is not None:
            fail("unexpected-authorization-evidence", "local assessment cannot claim external grant evidence")
        return None
    record = evidence.get(evidence_id.casefold()) if isinstance(evidence_id, str) else None
    if (
        not isinstance(record, dict)
        or record.get("kind") != "authorization"
        or not isinstance(expected_sha, str)
        or not SHA256_RE.fullmatch(expected_sha)
        or record.get("sha256") != expected_sha
    ):
        fail("authorization-evidence-binding", "external contact lacks exact frozen authorization evidence")
        return None
    grant = load_json_evidence(
        record,
        root,
        expected_kind="authorization",
        max_bytes=MAX_AUTHORIZATION_EVIDENCE_BYTES,
        fail=fail,
        code="authorization-evidence-binding",
    )
    if grant is None:
        return None
    closed_fields(grant, {
        "schemaVersion", "assessmentId", "planSha256", "targetIds",
        "activityTier", "externalContact", "networkScope", "authorizedBy",
        "grantedAt", "expiresAt", "redirectPolicy", "proxyMode", "dnsPolicy",
        "credentialMode", "capabilityBindingSha256", "destructiveActions", "limits",
    }, "authorization-evidence", fail)
    expected = authorization_projection(document, authorization)
    if grant != expected or not safe_identity_text(grant.get("authorizedBy"), max_chars=200):
        fail("authorization-evidence-drift", "frozen authorization differs from the live receipt grant")
        return None
    return expected_sha


def _evidence_references(
    document: dict[str, Any],
    target: dict[str, Any],
    authorization: dict[str, Any],
    engines: dict[str, dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
    fail: FailureSink,
) -> None:
    references: Counter[str] = Counter()

    def add(value: Any) -> None:
        if isinstance(value, str):
            references[value.casefold()] += 1

    add(target.get("snapshotManifestEvidenceId"))
    add(authorization.get("authorizationEvidenceId"))
    for engine in engines.values():
        add(engine.get("calibrationEvidenceId"))
    task_owner: dict[str, int] = {}
    tasks = document.get("tasks") if isinstance(document.get("tasks"), list) else []
    for task_index, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue
        add(task.get("adapterResultEvidenceId"))
        ids = task.get("evidenceIds") if isinstance(task.get("evidenceIds"), list) else []
        for evidence_id in ids:
            add(evidence_id)
            if isinstance(evidence_id, str):
                key = evidence_id.casefold()
                prior = task_owner.get(key)
                if prior is not None and prior != task_index:
                    fail("evidence-owner-conflict", "one evidence record cannot be owned by multiple tasks")
                task_owner[key] = task_index
    if set(references) != set(evidence):
        fail("evidence-ownership", "evidence registry must exactly equal referenced evidence ownership")
    if any(count != 1 for count in references.values()):
        fail("evidence-owner-conflict", "every evidence record must have exactly one owner")


def validate_v2_bindings(
    document: dict[str, Any],
    root: Path,
    target: dict[str, Any],
    authorization: dict[str, Any],
    engines: dict[str, dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
    recorded_at: Any,
    fail: FailureSink,
) -> dict[str, Any]:
    _evidence_under_fixed_root(evidence, fail)
    snapshot_valid = validate_snapshot(root, target, evidence, fail)
    plan_valid = _validate_plan(document, target, authorization, fail)
    grant_sha = _validate_authorization_evidence(root, document, authorization, evidence, fail)
    validate_calibrations(root, engines, evidence, recorded_at, fail)
    validate_adapter_results(root, document.get("tasks"), engines, evidence, fail)
    _evidence_references(document, target, authorization, engines, evidence, fail)
    return {
        "snapshotVerified": snapshot_valid,
        "frozenGrantSha256": grant_sha,
        "planSha256": authorization.get("planSha256") if plan_valid else None,
    }
