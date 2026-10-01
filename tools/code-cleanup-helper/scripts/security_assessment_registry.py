"""Validate receipt identity, authorization, engine, and evidence registries."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import re
from typing import Any

from security_assessment_network import canonical_network_destination
from security_assessment_shared import (
    ACTIVITY_TIERS,
    AUTH_LIMIT_FIELDS,
    BoundedFileError,
    DIGEST_RE,
    LICENSE_DISPOSITIONS,
    MAX_EVIDENCE_COUNT,
    MAX_EVIDENCE_BYTES,
    MAX_TOTAL_EVIDENCE_BYTES,
    REVISION_RE,
    SHA256_RE,
    TARGET_PRODUCT_MAX_CHARS,
    TARGET_PRODUCT_MAX_UTF8_BYTES,
    TARGET_VERSION_MAX_CHARS,
    TARGET_VERSION_MAX_UTF8_BYTES,
    FailureSink,
    GapSink,
    bounded_limits,
    closed_fields,
    file_identity,
    iso_date,
    link_like,
    safe_path,
    safe_identity_text,
    safe_target_identity,
    sensitive_receipt_content,
    string_list,
    timestamp,
)


TARGET_ID_RE = re.compile(r"^[a-z][a-z0-9+.-]{0,31}:[A-Za-z0-9][A-Za-z0-9._/@+-]{0,255}$")
MAX_ENGINE_SUPPORT_HORIZON = timedelta(days=90)


def _canonical_network_list(
    values: list[str],
    fail: FailureSink,
) -> list[str]:
    canonical_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        canonical, error = canonical_network_destination(value)
        if error == "metadata":
            fail("unsafe-network-scope", "network scope contains a metadata destination")
            continue
        if error or canonical is None:
            fail("invalid-network-destination", "network scope contains a non-canonical destination")
            continue
        if canonical.startswith("cidr:"):
            fail("broad-network-scope", "network authorization requires discrete host and port destinations")
            continue
        if canonical in seen:
            fail("duplicate-network-destination", "network scope contains equivalent duplicate destinations")
            continue
        seen.add(canonical)
        canonical_values.append(canonical)
    return canonical_values


def validate_header(
    document: dict[str, Any],
    fail: FailureSink,
    now: datetime,
    schema_version: int,
) -> tuple[dict[str, Any], datetime]:
    if document.get("schemaVersion") != schema_version:
        fail("schema-version", "schemaVersion is unsupported")
    closed_fields(document, {
        "schemaVersion", "assessmentId", "recordedAt", "target", "authorization",
        "dataHandling", "plannedTaskIds", "engines", "evidence", "tasks",
        "coverageClaim",
    }, "receipt", fail)
    if not isinstance(document.get("assessmentId"), str) or not document["assessmentId"].strip():
        fail("assessment-id", "assessmentId must be a non-empty string")
    recorded = timestamp(document.get("recordedAt"))
    if recorded is None:
        fail("recorded-at", "recordedAt must be an RFC 3339 timestamp with timezone")
        recorded = now
    elif recorded > now:
        fail("future-receipt", "recordedAt cannot be in the future")

    target = document.get("target")
    if not isinstance(target, dict):
        fail("target", "target must be an object")
        target = {}
    target_fields = {"product", "version", "snapshotSha256"}
    if schema_version == 2:
        target_fields.update({
            "snapshotProfile", "snapshotManifestEvidenceId", "snapshotManifestSha256",
        })
    closed_fields(target, target_fields, "target", fail)
    identity_limits = {
        "product": (TARGET_PRODUCT_MAX_CHARS, TARGET_PRODUCT_MAX_UTF8_BYTES),
        "version": (TARGET_VERSION_MAX_CHARS, TARGET_VERSION_MAX_UTF8_BYTES),
    }
    for field, (max_chars, max_utf8_bytes) in identity_limits.items():
        if not safe_target_identity(
            target.get(field),
            max_chars=max_chars,
            max_utf8_bytes=max_utf8_bytes,
        ):
            fail(
                "target-identity",
                f"target.{field} must be a bounded NFC Unicode identity",
                location=f"target.{field}",
            )
    if not isinstance(target.get("snapshotSha256"), str) or not SHA256_RE.fullmatch(target["snapshotSha256"]):
        fail("target-snapshot", "target.snapshotSha256 must be lowercase SHA-256")

    handling = document.get("dataHandling")
    expected_handling = {
        "scannerOutput": "untrusted-data",
        "rawExport": "explicit-only",
        "complianceClaim": "mapping-only-not-certification",
    }
    if not isinstance(handling, dict):
        fail("data-handling", "dataHandling must be an object")
    else:
        closed_fields(handling, {"scannerOutput", "aiContext", "rawExport", "complianceClaim"}, "dataHandling", fail)
        for field, expected in expected_handling.items():
            if handling.get(field) != expected:
                fail("unsafe-data-handling", f"dataHandling.{field} must be {expected}", location=f"dataHandling.{field}")
        if handling.get("aiContext") not in {"none", "redacted-summary-only"}:
            fail("unsafe-ai-context", "raw scanner output must not enter model context")

    sensitive = sensitive_receipt_content(document)
    if sensitive:
        fail(
            "security-evidence-sensitive",
            "receipt contains forbidden raw/sensitive fields or values",
            locations=sorted(set(sensitive)),
        )
    return target, recorded


def validate_authorization(
    value: Any,
    recorded: datetime,
    fail: FailureSink,
    schema_version: int,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail("authorization", "authorization must be an object")
        return {}
    authorization_fields = {
        "targetIds", "activityTier", "externalContact", "authorizedBy", "grantedAt",
        "expiresAt", "networkScope", "redirectPolicy", "proxyMode", "dnsPolicy",
        "credentialMode", "capabilityBindingSha256", "destructiveActions", "limits",
    }
    if schema_version == 2:
        authorization_fields.update({
            "planSha256", "authorizationEvidenceId", "authorizationEvidenceSha256",
        })
    closed_fields(value, authorization_fields, "authorization", fail)
    target_ids = string_list(value.get("targetIds"), "authorization.targetIds", fail)
    if any(not TARGET_ID_RE.fullmatch(item) or "*" in item for item in target_ids):
        fail("target-id", "authorization target IDs must use the strict type:value grammar")
    tier = value.get("activityTier")
    external = value.get("externalContact")
    if tier not in ACTIVITY_TIERS:
        fail("activity-tier", "authorization.activityTier is unsupported")
    if not isinstance(external, bool):
        fail("external-contact", "authorization.externalContact must be boolean")
        external = False
    if value.get("destructiveActions") is not False:
        fail("destructive-activity", "security assessment cannot authorize destructive actions")
    if value.get("credentialMode") not in {"none", "read-only-task-scoped"}:
        fail("credential-mode", "credentials must be absent or read-only and task-scoped")
    binding = value.get("capabilityBindingSha256")
    if value.get("credentialMode") == "read-only-task-scoped":
        if not isinstance(binding, str) or not SHA256_RE.fullmatch(binding):
            fail("credential-binding", "task-scoped credentials need a non-secret capability binding hash")
    elif binding is not None:
        fail("credential-binding", "credential-free scans must not declare a capability binding")

    raw_network_scope = string_list(
        value.get("networkScope"), "authorization.networkScope", fail, allow_empty=True
    )
    network_scope = _canonical_network_list(raw_network_scope, fail)
    if value.get("redirectPolicy") not in {"deny", "authorized-targets-only"}:
        fail("redirect-policy", "redirects must be denied or revalidated against authorized targets")
    if value.get("proxyMode") != "disabled":
        fail("ambient-proxy", "ambient proxy inheritance must be disabled")
    bounded_limits(value.get("limits"), AUTH_LIMIT_FIELDS, "authorization.limits", fail)

    if external:
        if tier == "local-static":
            fail("activity-tier", "external contact cannot use local-static activity tier")
        if not network_scope:
            fail("missing-network-scope", "external contact needs an exact network scope")
        if value.get("dnsPolicy") != "revalidate-each-connection-in-scope":
            fail("dns-policy", "external contact must revalidate resolved addresses on each connection")
        if not isinstance(value.get("authorizedBy"), str) or not value["authorizedBy"].strip():
            fail("missing-authorization", "external contact needs an explicit authorizer identity")
        granted, expires = timestamp(value.get("grantedAt")), timestamp(value.get("expiresAt"))
        if granted is None or expires is None or not granted <= recorded <= expires:
            fail("authorization-window", "recorded scan must occur inside the explicit grant window")
    else:
        if tier != "local-static" or network_scope:
            fail("local-scope-drift", "non-network assessment must be local-static with empty networkScope")
        if value.get("dnsPolicy") != "not-applicable":
            fail("dns-policy", "local-static assessment must mark DNS policy not-applicable")
    return {**value, "targetIds": target_ids, "networkScope": network_scope}


def validate_engines(
    value: Any,
    recorded: datetime,
    now: datetime,
    fail: FailureSink,
    gap: GapSink,
    schema_version: int,
    referenced_ids: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list) or not value:
        fail("engines", "engines must be a non-empty array")
        return {}
    engines: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(value):
        label = f"engines[{index}]"
        if not isinstance(raw, dict):
            fail("invalid-engine", f"{label} must be an object")
            continue
        engine_fields = {
            "id", "version", "sourceRevision", "artifactDigest", "adapterSha256",
            "rulesSha256", "dataSha256", "knowledgeDate", "supportUntil",
            "fingerprintSchema", "admissionStatus", "admissionReason",
            "licenseDisposition",
        }
        if schema_version == 2:
            engine_fields.update({"calibrationEvidenceId", "calibrationSha256"})
        closed_fields(raw, engine_fields, label, fail)
        engine_id = raw.get("id")
        if not isinstance(engine_id, str) or not engine_id:
            fail("engine-id", f"{label}.id is required")
            continue
        key = engine_id.casefold()
        if key in engines:
            fail("duplicate-engine", "engine IDs must be case-insensitively unique", engineId=engine_id)
        if schema_version == 2 and referenced_ids is not None and key not in referenced_ids:
            fail("unused-engine", "v2 receipt contains an engine outside the exact task plan")
            continue
        engines[key] = raw
        for field in ("version", "fingerprintSchema"):
            observed = raw.get(field)
            if not isinstance(observed, str) or not observed.strip() or observed.casefold() == "latest":
                fail("engine-identity", f"{label}.{field} must be an exact non-moving identity", engineId=engine_id)
        if not isinstance(raw.get("sourceRevision"), str) or not REVISION_RE.fullmatch(raw["sourceRevision"]):
            fail("engine-revision", f"{label}.sourceRevision must be an exact 40-64 hex revision", engineId=engine_id)
        if not isinstance(raw.get("artifactDigest"), str) or not DIGEST_RE.fullmatch(raw["artifactDigest"]):
            fail("engine-artifact-digest", f"{label}.artifactDigest must be sha256:<lowercase hex>", engineId=engine_id)
        for field in ("adapterSha256", "rulesSha256"):
            if not isinstance(raw.get(field), str) or not SHA256_RE.fullmatch(raw[field]):
                fail("engine-provenance", f"{label}.{field} must be lowercase SHA-256", engineId=engine_id)
        data_sha = raw.get("dataSha256")
        if data_sha is not None and (not isinstance(data_sha, str) or not SHA256_RE.fullmatch(data_sha)):
            fail("engine-provenance", f"{label}.dataSha256 must be null or lowercase SHA-256", engineId=engine_id)
        knowledge, support = iso_date(raw.get("knowledgeDate")), iso_date(raw.get("supportUntil"))
        if knowledge is None or support is None or knowledge > recorded.date() or support < knowledge:
            fail("engine-knowledge-window", f"{label} has an invalid knowledge/support window", engineId=engine_id)
        elif schema_version == 2 and support - knowledge > MAX_ENGINE_SUPPORT_HORIZON:
            fail("engine-support-horizon", "engine support horizon exceeds the validator-owned cap", engineId=engine_id)
        elif support < now.date():
            gap("stale-engine-knowledge", "engine knowledge support window has expired", engineId=engine_id)
        admission = raw.get("admissionStatus")
        if admission not in {"admitted", "unadmitted"}:
            fail("engine-admission", f"{label}.admissionStatus is unsupported", engineId=engine_id)
        elif admission == "unadmitted" and (not isinstance(raw.get("admissionReason"), str) or not raw["admissionReason"].strip()):
            fail("engine-admission", "unadmitted engine needs a reason", engineId=engine_id)
        if raw.get("licenseDisposition") not in LICENSE_DISPOSITIONS:
            fail("engine-license", f"{label}.licenseDisposition is unsupported", engineId=engine_id)
        elif raw.get("licenseDisposition") == "manual-review":
            gap("engine-license-review", "engine license disposition still requires manual review", engineId=engine_id)
    return engines


def validate_evidence(
    value: Any,
    root: Path,
    fail: FailureSink,
    schema_version: int,
) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list):
        fail("evidence", "evidence must be an array")
        return {}
    if len(value) > MAX_EVIDENCE_COUNT:
        fail("evidence-count-limit", "evidence registry exceeds the verifier count ceiling")
        return {}
    evidence: dict[str, dict[str, Any]] = {}
    path_keys: set[str] = set()
    total_bytes = 0
    for index, raw in enumerate(value):
        label = f"evidence[{index}]"
        if not isinstance(raw, dict):
            fail("invalid-evidence", f"{label} must be an object")
            continue
        closed_fields(raw, {"id", "path", "kind", "bytes", "sha256"}, label, fail)
        evidence_id = raw.get("id")
        if not isinstance(evidence_id, str) or not evidence_id:
            fail("evidence-id", f"{label}.id is required")
            continue
        key = evidence_id.casefold()
        if key in evidence:
            fail("duplicate-evidence", "evidence IDs must be case-insensitively unique", evidenceId=evidence_id)
            continue
        evidence[key] = raw
        candidate, error = safe_path(root, raw.get("path"))
        if error or candidate is None:
            fail("unsafe-evidence-path", error or "invalid evidence path", evidenceId=evidence_id)
            continue
        path_key = str(candidate).casefold()
        if path_key in path_keys:
            fail("duplicate-evidence-path", "one evidence file cannot satisfy multiple evidence IDs", evidenceId=evidence_id)
            continue
        path_keys.add(path_key)
        if not candidate.exists():
            fail("missing-evidence", "declared security evidence file is missing", evidenceId=evidence_id)
            continue
        if link_like(candidate) or not candidate.is_file():
            fail("unsafe-evidence-path", "security evidence must be a regular non-symlink file", evidenceId=evidence_id)
            continue
        remaining_bytes = MAX_TOTAL_EVIDENCE_BYTES - total_bytes
        expected = {"bytes": raw.get("bytes"), "sha256": raw.get("sha256")}
        try:
            identity = file_identity(
                candidate,
                max_bytes=min(MAX_EVIDENCE_BYTES, remaining_bytes),
                require_nonempty=True,
            )
        except BoundedFileError as error:
            if error.reason == "empty":
                fail("empty-evidence", "security evidence must contain at least one byte", evidenceId=evidence_id)
            elif error.reason == "too-large" and remaining_bytes < MAX_EVIDENCE_BYTES:
                fail("evidence-total-limit", "security evidence exceeds the aggregate byte ceiling")
            elif error.reason == "too-large":
                fail("evidence-too-large", "security evidence exceeds the verifier byte ceiling", evidenceId=evidence_id)
            else:
                fail("evidence-read", "security evidence could not be read within bounds", evidenceId=evidence_id)
            continue
        except OSError:
            fail("evidence-read", "security evidence could not be read within bounds", evidenceId=evidence_id)
            continue
        total_bytes += identity["bytes"]
        if (
            isinstance(expected["bytes"], bool)
            or not isinstance(expected["bytes"], int)
            or expected["bytes"] <= 0
            or expected["bytes"] > MAX_EVIDENCE_BYTES
            or not isinstance(expected["sha256"], str)
            or not SHA256_RE.fullmatch(expected["sha256"])
        ):
            fail("invalid-evidence-identity", "evidence needs exact positive bytes and lowercase SHA-256", evidenceId=evidence_id)
        elif identity != expected:
            fail("stale-security-evidence", "live evidence bytes no longer match the receipt", evidenceId=evidence_id)
        kinds = {"raw", "normalized", "log", "manifest"}
        if schema_version == 2:
            kinds.update({"snapshot-manifest", "authorization", "calibration", "adapter-result"})
        if raw.get("kind") not in kinds:
            fail("evidence-kind", f"{label}.kind is unsupported", evidenceId=evidence_id)
    return evidence
