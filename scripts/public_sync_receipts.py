"""Closed-world public source sync receipts; no copy orchestration."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from public_sync_inventory import PUBLIC_OWNED_PATHS, SYNC_RECEIPT_PATH, canonical_receipt_shape_errors, public_destination_required_paths, sync_expected_output_paths, validate_public_destination
from public_sync_paths import OUTPUT_HASH_SEMANTICS, _boundary_error, _output_path_boundary_rule, _output_path_boundary_violations, _text_sha256, _write_utf8

def _write_sync_receipt(
    canonical_evidence: dict[str, dict],
    repository: Path,
    copied: list[str],
) -> None:
    expected_outputs = sync_expected_output_paths()
    if len(copied) != len(set(copied)):
        raise ValueError("sync generated duplicate output paths")
    if set(copied) != expected_outputs:
        missing = sorted(expected_outputs - set(copied))
        extra = sorted(set(copied) - expected_outputs)
        raise ValueError(
            "sync output schema drifted; missing=%s extra=%s"
            % (missing[:20], extra[:20])
        )
    output_names = sorted(copied)
    outputs = {name: _text_sha256(repository / name) for name in output_names}
    public_owned = {name: outputs[name] for name in PUBLIC_OWNED_PATHS}
    inventory_text = json.dumps(
        canonical_evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    payload = {
        "schema": "video-autopilot-public-sync-receipt/v3",
        "assurance": (
            "Detects stale or accidental public-sync drift. This committed receipt is not "
            "an external signature against an attacker who can modify both code and receipt."
        ),
        "output_hash_semantics": OUTPUT_HASH_SEMANTICS,
        "canonical_inventory_sha256": hashlib.sha256(inventory_text).hexdigest(),
        "canonical_inventory": canonical_evidence,
        "output_count": len(outputs),
        "outputs": outputs,
        "public_owned": public_owned,
        "public_destination_required_paths": public_destination_required_paths(),
    }
    target = repository / SYNC_RECEIPT_PATH
    _write_utf8(target, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

def _receipt_schema_errors(payload) -> list[str]:
    expected_keys = {
        "schema", "assurance", "canonical_inventory_sha256", "canonical_inventory",
        "output_hash_semantics", "output_count", "outputs", "public_owned",
        "public_destination_required_paths",
    }
    if not isinstance(payload, dict):
        return ["sync receipt root must be an object"]
    errors: list[str] = []
    if set(payload) != expected_keys:
        errors.append("sync receipt field set mismatch")
    if payload.get("schema") != "video-autopilot-public-sync-receipt/v3":
        errors.append("unexpected sync receipt schema")
    if payload.get("output_hash_semantics") != OUTPUT_HASH_SEMANTICS:
        errors.append("unexpected sync receipt output hash semantics")
    assurance = payload.get("assurance")
    if (not isinstance(assurance, str) or "stale or accidental" not in assurance
            or "not an external signature" not in assurance):
        errors.append("sync receipt assurance boundary missing")
    inventory = payload.get("canonical_inventory")
    errors.extend(canonical_receipt_shape_errors(inventory))
    if isinstance(inventory, dict):
        normalized = json.dumps(
            inventory, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        if hashlib.sha256(normalized).hexdigest() != payload.get("canonical_inventory_sha256"):
            errors.append("canonical inventory evidence hash mismatch")
    expected_outputs = sync_expected_output_paths()
    outputs = payload.get("outputs")
    if not isinstance(outputs, dict):
        errors.append("sync receipt outputs missing")
    else:
        if set(outputs) != expected_outputs:
            errors.append("sync receipt output key set mismatch")
        if payload.get("output_count") != len(expected_outputs) or len(outputs) != len(expected_outputs):
            errors.append("sync receipt output_count mismatch")
        if any(not isinstance(value, str) or len(value) != 64
               or any(char not in "0123456789abcdef" for char in value)
               for value in outputs.values()):
            errors.append("sync receipt output hash invalid")
    expected_required = public_destination_required_paths()
    if payload.get("public_destination_required_paths") != expected_required:
        errors.append("sync receipt public destination schema drift")
    public_owned = payload.get("public_owned")
    if not isinstance(public_owned, dict) or set(public_owned) != set(PUBLIC_OWNED_PATHS):
        errors.append("sync receipt public-owned inventory mismatch")
    elif isinstance(outputs, dict):
        for relative in PUBLIC_OWNED_PATHS:
            if public_owned.get(relative) != outputs.get(relative):
                errors.append("sync receipt public-owned hash mismatch: " + relative)
    return errors

def _verify_sync_receipt(repository: Path) -> list[str]:
    target = repository / SYNC_RECEIPT_PATH
    receipt_boundary = _output_path_boundary_rule(repository, SYNC_RECEIPT_PATH)
    if receipt_boundary is not None:
        return [_boundary_error(SYNC_RECEIPT_PATH, receipt_boundary)]
    if not target.is_file():
        return [f"missing {SYNC_RECEIPT_PATH}"]
    try:
        payload = json.loads(target.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return [f"invalid {SYNC_RECEIPT_PATH}: unreadable or malformed JSON"]
    errors = _receipt_schema_errors(payload)
    outputs = payload.get("outputs")
    if not isinstance(outputs, dict):
        return errors
    expected_outputs = sync_expected_output_paths()
    boundary_violations = _output_path_boundary_violations(
        repository, expected_outputs
    )
    for relative in sorted(expected_outputs):
        if relative in boundary_violations:
            errors.append(_boundary_error(relative, boundary_violations[relative]))
            continue
        expected = outputs.get(relative)
        path = repository / relative
        if not path.is_file():
            errors.append("missing receipt output: " + relative)
        elif isinstance(expected, str):
            try:
                actual = _text_sha256(path)
            except (OSError, UnicodeError):
                errors.append("unreadable receipt output: " + relative)
            else:
                if actual != expected:
                    errors.append("receipt output hash mismatch: " + relative)
    if boundary_violations:
        # Do not pass an unsafe tree to downstream validators, which might
        # follow the same alias and surface a private resolved machine path.
        return errors
    manifest_path = repository / "release-manifest.json"
    if not manifest_path.is_file():
        manifest_path = Path(__file__).resolve().parents[1] / "release-manifest.json"
    try:
        validate_public_destination(repository, manifest_path)
    except ValueError as exc:
        errors.append(str(exc))
    return errors
