"""Deterministic receipt-v2 fixtures shared by validator self-tests."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from security_assessment_shared import SECURITY_CONTROL_IDS, file_identity
from security_assessment_snapshot import SNAPSHOT_PROFILE, snapshot_sha256
from security_assessment_v2_bindings import authorization_projection
from security_assessment_v2_common import canonical_json_bytes, compute_plan_sha256, parse_json_object
from security_assessment_v2_evidence import (
    ADAPTER_RESULT_PROFILE,
    CALIBRATION_PROFILE,
    REQUIRED_NEGATIVE_CONTROLS,
)


def write_json(path: Path, document: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(document))
    return file_identity(path)


def evidence_record(identifier: str, path: Path, root: Path, kind: str) -> dict[str, Any]:
    return {
        "id": identifier,
        "path": path.relative_to(root).as_posix(),
        "kind": kind,
        **file_identity(path),
    }


def _fixture_engine(evidence_root: Path, now: datetime) -> dict[str, Any]:
    engine = {
        "id": "fixture-engine",
        "version": "1.2.3",
        "sourceRevision": "b" * 40,
        "artifactDigest": "sha256:" + "c" * 64,
        "adapterSha256": "d" * 64,
        "rulesSha256": "e" * 64,
        "dataSha256": None,
        "knowledgeDate": now.date().isoformat(),
        "supportUntil": (now + timedelta(days=30)).date().isoformat(),
        "fingerprintSchema": "fixture-fingerprint/v1",
        "admissionStatus": "admitted",
        "licenseDisposition": "allowed",
        "calibrationEvidenceId": "engine-calibration",
        "calibrationSha256": None,
    }
    calibration = {
        "schemaVersion": 1,
        "profile": CALIBRATION_PROFILE,
        "engineId": engine["id"],
        "engineVersion": engine["version"],
        "sourceRevision": engine["sourceRevision"],
        "artifactDigest": engine["artifactDigest"],
        "adapterSha256": engine["adapterSha256"],
        "rulesSha256": engine["rulesSha256"],
        "dataSha256": engine["dataSha256"],
        "fingerprintSchema": engine["fingerprintSchema"],
        "fixtureSetSha256": "3" * 64,
        "calibratedAt": (now - timedelta(minutes=10)).isoformat().replace("+00:00", "Z"),
        "passedNegativeControlIds": sorted(REQUIRED_NEGATIVE_CONTROLS),
    }
    calibration_path = evidence_root / "calibration.json"
    calibration_identity = write_json(calibration_path, calibration)
    engine["calibrationSha256"] = calibration_identity["sha256"]
    return engine


def valid_fixture(root: Path, now: datetime) -> dict[str, Any]:
    source_path = root / "src" / "app.py"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("print('fixture')\n", encoding="utf-8")
    source_entries = [{"path": "src/app.py", **file_identity(source_path)}]
    snapshot_digest = snapshot_sha256(source_entries)

    evidence_root = root / ".rd" / "security-evidence"
    raw_path = evidence_root / "raw.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text('{"event":"complete"}\n', encoding="utf-8")

    engine = _fixture_engine(evidence_root, now)
    calibration_path = evidence_root / "calibration.json"
    calibration_identity = file_identity(calibration_path)

    planned_check_ids = list(SECURITY_CONTROL_IDS)
    executed_check_ids = list(SECURITY_CONTROL_IDS)
    execution = {
        "inputReadOnly": True,
        "outputIsolated": True,
        "unprivileged": True,
        "shell": False,
        "runtimeSocket": False,
        "broadHomeMount": False,
        "snapshotSha256": snapshot_digest,
        "commandSha256": "f" * 64,
        "environmentSha256": "1" * 64,
        "credentialMode": "none",
        "networkMode": "disabled",
        "egressAllowlist": [],
        "limits": {
            "timeoutSeconds": 60,
            "memoryMiB": 256,
            "pids": 16,
            "outputBytes": 16_384,
            "outputFiles": 4,
            "outputDepth": 4,
        },
        "exitCode": 0,
        "successMarker": "fixture-complete",
    }
    adapter = {
        "schemaVersion": 1,
        "profile": ADAPTER_RESULT_PROFILE,
        "taskId": "secrets",
        "rawEvidenceId": "raw-secrets",
        "rawEvidenceSha256": file_identity(raw_path)["sha256"],
        "engineId": engine["id"],
        "engineVersion": engine["version"],
        "engineSourceRevision": engine["sourceRevision"],
        "engineArtifactDigest": engine["artifactDigest"],
        "fingerprintSchema": engine["fingerprintSchema"],
        "adapterSha256": engine["adapterSha256"],
        "rulesSha256": engine["rulesSha256"],
        "dataSha256": engine["dataSha256"],
        "snapshotSha256": execution["snapshotSha256"],
        "commandSha256": execution["commandSha256"],
        "environmentSha256": execution["environmentSha256"],
        "plannedCheckIds": list(planned_check_ids),
        "executedCheckIds": list(executed_check_ids),
        "exitCode": execution["exitCode"],
        "successMarker": execution["successMarker"],
        "parserState": "complete",
        "rawSourceObservationIds": [],
        "rawSourceObservationCount": 0,
        "normalizedFindings": [],
        "truncationCount": 0,
        "unparsedCount": 0,
    }
    adapter_path = evidence_root / "adapter-result.json"
    adapter_identity = write_json(adapter_path, adapter)

    manifest = {"schemaVersion": 1, "profile": SNAPSHOT_PROFILE, "entries": source_entries}
    manifest_path = evidence_root / "snapshot-manifest.json"
    manifest_identity = write_json(manifest_path, manifest)

    receipt: dict[str, Any] = {
        "schemaVersion": 2,
        "assessmentId": "fixture-security-assessment",
        "recordedAt": now.isoformat().replace("+00:00", "Z"),
        "target": {
            "product": "Fixture",
            "version": "1.0.0",
            "snapshotSha256": snapshot_digest,
            "snapshotProfile": SNAPSHOT_PROFILE,
            "snapshotManifestEvidenceId": "snapshot-manifest",
            "snapshotManifestSha256": manifest_identity["sha256"],
        },
        "authorization": {
            "targetIds": ["repo:fixture"],
            "activityTier": "local-static",
            "externalContact": False,
            "authorizedBy": None,
            "grantedAt": None,
            "expiresAt": None,
            "networkScope": [],
            "redirectPolicy": "deny",
            "proxyMode": "disabled",
            "dnsPolicy": "not-applicable",
            "credentialMode": "none",
            "capabilityBindingSha256": None,
            "destructiveActions": False,
            "limits": {"requestsPerSecond": 1, "concurrency": 1, "deadlineSeconds": 300},
            "planSha256": None,
            "authorizationEvidenceId": None,
            "authorizationEvidenceSha256": None,
        },
        "dataHandling": {
            "scannerOutput": "untrusted-data",
            "aiContext": "none",
            "rawExport": "explicit-only",
            "complianceClaim": "mapping-only-not-certification",
        },
        "plannedTaskIds": ["secrets"],
        "engines": [engine],
        "evidence": [
            {"id": "raw-secrets", "path": raw_path.relative_to(root).as_posix(), "kind": "raw", **file_identity(raw_path)},
            {"id": "adapter-result", "path": adapter_path.relative_to(root).as_posix(), "kind": "adapter-result", **adapter_identity},
            {"id": "engine-calibration", "path": calibration_path.relative_to(root).as_posix(), "kind": "calibration", **calibration_identity},
            {"id": "snapshot-manifest", "path": manifest_path.relative_to(root).as_posix(), "kind": "snapshot-manifest", **manifest_identity},
        ],
        "tasks": [{
            "id": "secrets",
            "targetId": "repo:fixture",
            "engineId": engine["id"],
            "status": "completed",
            "plannedCheckIds": list(planned_check_ids),
            "executedCheckIds": list(executed_check_ids),
            "reason": None,
            "rawFindingCount": 0,
            "findings": [],
            "rawEvidenceId": "raw-secrets",
            "evidenceIds": ["raw-secrets"],
            "adapterResultEvidenceId": "adapter-result",
            "adapterResultSha256": adapter_identity["sha256"],
            "execution": execution,
        }],
        "coverageClaim": "COMPLETE",
    }
    receipt["authorization"]["planSha256"] = compute_plan_sha256(receipt)
    return receipt


def legacy_fixture(source: dict[str, Any]) -> dict[str, Any]:
    receipt = json.loads(json.dumps(source))
    receipt["schemaVersion"] = 1
    for field in ("snapshotProfile", "snapshotManifestEvidenceId", "snapshotManifestSha256"):
        receipt["target"].pop(field)
    for field in ("planSha256", "authorizationEvidenceId", "authorizationEvidenceSha256"):
        receipt["authorization"].pop(field)
    for engine in receipt["engines"]:
        engine.pop("calibrationEvidenceId")
        engine.pop("calibrationSha256")
    for task in receipt["tasks"]:
        task.pop("adapterResultEvidenceId")
        task.pop("adapterResultSha256")
    receipt["evidence"] = [item for item in receipt["evidence"] if item["kind"] == "raw"]
    return receipt


def external_fixture(source: dict[str, Any], now: datetime, root: Path) -> dict[str, Any]:
    receipt = json.loads(json.dumps(source))
    receipt["authorization"].update({
        "activityTier": "low-impact-contact",
        "externalContact": True,
        "authorizedBy": "fixture-owner",
        "grantedAt": (now - timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
        "expiresAt": (now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
        "networkScope": ["api.example.test:443"],
        "redirectPolicy": "authorized-targets-only",
        "dnsPolicy": "revalidate-each-connection-in-scope",
    })
    receipt["tasks"][0]["execution"].update({
        "networkMode": "exact-allowlist",
        "egressAllowlist": ["api.example.test:443"],
    })
    receipt["authorization"]["planSha256"] = compute_plan_sha256(receipt)
    grant = authorization_projection(receipt, receipt["authorization"])
    grant_path = root / ".rd" / "security-evidence" / "authorization.json"
    identity = write_json(grant_path, grant)
    receipt["evidence"].append({
        "id": "authorization",
        "path": grant_path.relative_to(root).as_posix(),
        "kind": "authorization",
        **identity,
    })
    receipt["authorization"]["authorizationEvidenceId"] = "authorization"
    receipt["authorization"]["authorizationEvidenceSha256"] = identity["sha256"]
    return receipt


def read_evidence_json(receipt: dict[str, Any], root: Path, identifier: str) -> dict[str, Any]:
    record = next(item for item in receipt["evidence"] if item["id"] == identifier)
    return parse_json_object((root / record["path"]).read_bytes())


def replace_evidence_json(
    receipt: dict[str, Any],
    root: Path,
    identifier: str,
    document: dict[str, Any],
) -> str:
    record = next(item for item in receipt["evidence"] if item["id"] == identifier)
    identity = write_json(root / record["path"], document)
    record.update(identity)
    return identity["sha256"]
