"""Canonical hashing and bounded JSON-evidence helpers for receipt v2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from security_assessment_network import canonical_network_destination
from security_assessment_shared import (
    FailureSink,
    MAX_INTEGER_ABS,
    TARGET_IDENTITY_PROFILE,
    document_structure_within_limits,
    read_bytes_bounded,
    safe_path,
)


class DuplicateJsonKey(ValueError):
    """Raised when a security evidence object contains duplicate keys."""


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKey
        result[key] = value
    return result


def _bounded_parse_int(value: str) -> int:
    """Reject oversized integer tokens before constructing an unbounded Python int."""
    digits = value[1:] if value.startswith("-") else value
    if not digits or len(digits) > 19:
        raise ValueError("integer token is outside validator bounds")
    parsed = int(value, 10)
    if abs(parsed) > MAX_INTEGER_ABS:
        raise ValueError("integer token is outside validator bounds")
    return parsed


def _reject_non_integer_number(_value: str) -> float:
    raise ValueError("non-integer JSON numbers are not accepted")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def target_identity_sha256(product: str, version: str) -> str:
    """Hash exact validated identity fields under a domain-separated profile."""
    return canonical_sha256({
        "profile": TARGET_IDENTITY_PROFILE,
        "product": product,
        "version": version,
    })


def parse_json_object(raw: bytes) -> dict[str, Any]:
    document = json.loads(
        raw.decode("utf-8-sig"),
        object_pairs_hook=_closed_object,
        parse_int=_bounded_parse_int,
        parse_float=_reject_non_integer_number,
        parse_constant=_reject_non_integer_number,
    )
    if not isinstance(document, dict) or not document_structure_within_limits(document):
        raise ValueError("JSON root or structure is invalid")
    return document


def load_json_evidence(
    record: dict[str, Any] | None,
    root: Path,
    *,
    expected_kind: str,
    max_bytes: int,
    fail: FailureSink,
    code: str,
) -> dict[str, Any] | None:
    if not isinstance(record, dict) or record.get("kind") != expected_kind:
        fail(code, "referenced evidence has the wrong kind")
        return None
    candidate, error = safe_path(root, record.get("path"))
    if error or candidate is None or not candidate.is_file():
        fail(code, "referenced evidence path is invalid")
        return None
    try:
        raw, identity = read_bytes_bounded(candidate, max_bytes=max_bytes)
        if identity != {"bytes": record.get("bytes"), "sha256": record.get("sha256")}:
            fail(code, "referenced evidence identity has drifted")
            return None
        document = parse_json_object(raw)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError, RecursionError):
        fail(code, "referenced evidence is not bounded canonical JSON")
        return None
    return document


def _canonical_scope(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        canonical, error = canonical_network_destination(value)
        result.append(canonical if not error and canonical is not None else "[invalid]")
    return sorted(result, key=str.casefold)


def plan_payload(
    document: dict[str, Any],
    *,
    target: dict[str, Any] | None = None,
    authorization: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target = target if isinstance(target, dict) else document.get("target", {})
    authorization = (
        authorization if isinstance(authorization, dict) else document.get("authorization", {})
    )
    raw_engines = document.get("engines") if isinstance(document.get("engines"), list) else []
    engines = []
    for raw in raw_engines:
        if not isinstance(raw, dict):
            continue
        engines.append({
            "id": raw.get("id"),
            "version": raw.get("version"),
            "sourceRevision": raw.get("sourceRevision"),
            "artifactDigest": raw.get("artifactDigest"),
            "adapterSha256": raw.get("adapterSha256"),
            "rulesSha256": raw.get("rulesSha256"),
            "dataSha256": raw.get("dataSha256"),
            "fingerprintSchema": raw.get("fingerprintSchema"),
        })
    raw_tasks = document.get("tasks") if isinstance(document.get("tasks"), list) else []
    tasks = []
    for raw in raw_tasks:
        if not isinstance(raw, dict):
            continue
        checks = raw.get("plannedCheckIds") if isinstance(raw.get("plannedCheckIds"), list) else []
        tasks.append({
            "id": raw.get("id"),
            "targetId": raw.get("targetId"),
            "engineId": raw.get("engineId"),
            "plannedCheckIds": sorted(checks, key=lambda item: str(item).casefold()),
        })
    target_ids = authorization.get("targetIds")
    return {
        "schemaVersion": 1,
        "assessmentId": document.get("assessmentId"),
        "target": {
            "product": target.get("product"),
            "version": target.get("version"),
            "snapshotSha256": target.get("snapshotSha256"),
            "snapshotProfile": target.get("snapshotProfile"),
        },
        "authorization": {
            "targetIds": sorted(target_ids, key=str.casefold) if isinstance(target_ids, list) else [],
            "activityTier": authorization.get("activityTier"),
            "externalContact": authorization.get("externalContact"),
            "networkScope": _canonical_scope(authorization.get("networkScope")),
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
        },
        "engines": sorted(engines, key=lambda item: str(item.get("id")).casefold()),
        "tasks": sorted(tasks, key=lambda item: str(item.get("id")).casefold()),
    }


def compute_plan_sha256(
    document: dict[str, Any],
    *,
    target: dict[str, Any] | None = None,
    authorization: dict[str, Any] | None = None,
) -> str:
    return canonical_sha256(plan_payload(document, target=target, authorization=authorization))
