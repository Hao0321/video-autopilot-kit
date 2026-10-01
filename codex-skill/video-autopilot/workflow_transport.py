from __future__ import annotations

import base64
import binascii
import hashlib
import json
from typing import Any

from workflow_state import WorkflowError, require_list, require_mapping, sha256_json


def _decode_result(value: dict[str, Any], label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Decode one MCP CallToolResult while hashing, but never persisting, image bytes."""
    content = value.get("content")
    if not isinstance(content, list):
        return value, {"kind": "decoded-json", "payload_sha256": sha256_json(value), "images": []}
    if value.get("isError") is True:
        raise WorkflowError(f"{label} returned isError=true")
    decoded: dict[str, Any] | None = None
    images: list[dict[str, Any]] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text" and decoded is None and isinstance(block.get("text"), str):
            try:
                decoded = require_mapping(json.loads(block["text"]), f"{label} text JSON")
            except json.JSONDecodeError as error:
                raise WorkflowError(f"{label} text is not JSON: {error}") from error
        elif block.get("type") == "image":
            raw = block.get("data")
            if not isinstance(raw, str):
                raise WorkflowError(f"{label} image block has no base64 data")
            try:
                data = base64.b64decode(raw, validate=True)
            except (ValueError, binascii.Error) as error:
                raise WorkflowError(f"{label} image block is not valid base64") from error
            if not data:
                raise WorkflowError(f"{label} image block is empty")
            images.append({
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
                "mime_type": str(block.get("mimeType", "")),
            })
    if decoded is None:
        raise WorkflowError(f"{label} contains no JSON text block")
    return decoded, {"kind": "mcp-call-tool-result", "payload_sha256": sha256_json(decoded), "images": images}


def _call_record(value: Any, label: str, *, require_request: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    record = require_mapping(value, label)
    if "result" in record:
        request = require_mapping(record.get("request"), f"{label}.request")
        decoded, evidence = _decode_result(require_mapping(record.get("result"), f"{label}.result"), f"{label}.result")
    else:
        if require_request:
            raise WorkflowError(f"{label} must preserve the exact MCP request beside result")
        request, decoded = {}, record
        decoded, evidence = _decode_result(decoded, label)
    return decoded, {"request": request, **evidence}


def _batch_submission(submission: dict[str, Any], field: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    calls = require_list(submission.get(field), f"{field} call records")
    decoded_calls: list[dict[str, Any]] = []
    evidence_calls: list[dict[str, Any]] = []
    for index, value in enumerate(calls):
        decoded, evidence = _call_record(value, f"{field}[{index}]", require_request=True)
        decoded_calls.append(decoded)
        evidence_calls.append(evidence)
    response = {"status": submission.get("status", "GREEN"), field: decoded_calls}
    transport = {"kind": "mcp-call-batch", "call_count": len(calls), "calls": evidence_calls}
    durable = {"status": response["status"], field: evidence_calls}
    return response, transport, durable


def normalize_step_submission(template_id: str, submission: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return decoded payload, call provenance, and a durable image-redacted submission."""
    if template_id == "keyframes:{material}" and "batches" in submission:
        if str(submission.get("status", "")).upper() in {"N/A", "NOT_APPLICABLE"}:
            return submission, {"kind": "decoded-json", "call_count": 0, "calls": []}, submission
        return _batch_submission(submission, "batches")
    if template_id == "context:{material}" and "windows" in submission:
        return _batch_submission(submission, "windows")
    if template_id == "semantics:{material}":
        decoded, evidence = _call_record(submission, "semantics", require_request=True)
        transport = {"kind": evidence["kind"], "call_count": 1, "calls": [evidence]}
        return decoded, transport, {"request": evidence["request"], "result": evidence}
    decoded, evidence = _decode_result(submission, template_id)
    transport = {"kind": evidence["kind"], "call_count": 1, "calls": [evidence]}
    return decoded, transport, {"result": evidence}
