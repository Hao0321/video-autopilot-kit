from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from workflow_state import (
    WorkflowError, plan_sha256, read_json, require_list, require_mapping, require_sha,
    sha256_file, sha256_json, step_material,
)


def receipt_for(state: dict[str, Any], step_id: str) -> dict[str, Any]:
    record = state["steps"][step_id].get("receipt")
    if not record:
        raise WorkflowError(f"Step has no receipt: {step_id}")
    path = Path(state["run_dir"]) / record["path"]
    envelope = require_mapping(read_json(path), f"receipt {step_id}")
    if sha256_file(path) != record["file_sha256"]:
        raise WorkflowError(f"Receipt file hash mismatch: {step_id}")
    return envelope


def prepared_facts(state: dict[str, Any], material: dict[str, Any]) -> dict[str, Any]:
    return require_mapping(receipt_for(state, f"prepare:{material['key']}").get("facts"), "prepare receipt facts")


def semantic_facts(state: dict[str, Any], material: dict[str, Any]) -> dict[str, Any]:
    return require_mapping(receipt_for(state, f"semantics:{material['key']}").get("facts"), "semantics receipt facts")


def _status(payload: dict[str, Any], allowed: set[str] | None = None) -> str:
    value = str(payload.get("status", "")).upper()
    if value not in (allowed or {"GREEN"}):
        raise WorkflowError(f"Receipt status {value or '<missing>'} is not allowed")
    return value


def _issued_request(step: dict[str, Any]) -> dict[str, Any]:
    claim = require_mapping(step.get("claim"), "active claim")
    instruction = require_mapping(claim.get("instruction"), "claim instruction")
    request = require_mapping(instruction.get("request"), "claim request")
    if sha256_json(request) != claim.get("request_sha256"):
        raise WorkflowError("Claim request provenance hash is corrupt")
    return request


def _prepare(material: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    _status(payload, {"GREEN", "PARTIAL"})
    packet = require_mapping(payload.get("packet"), "prepare.packet")
    material_id = require_sha(packet.get("materialId"), "prepare materialId")
    source = require_mapping(packet.get("source"), "prepare.packet.source")
    source_sha = require_sha(source.get("sourceSha256"), "prepare sourceSha256")
    if source_sha != material["source_sha256"] or source.get("clipId") != material["clip_id"]:
        raise WorkflowError(f"Prepared source or clip binding mismatch for {material['clip_id']}")
    frames = require_list(packet.get("keyframes"), "prepare.packet.keyframes")
    kind = str(source.get("kind", "video"))
    if len(frames) > 12 or (not frames and kind != "audio"):
        raise WorkflowError("prepare_ai_material requires 1..12 keyframes except audio, which may have zero")
    frame_ids: list[str] = []
    frame_hashes: dict[str, str] = {}
    for frame in frames:
        frame = require_mapping(frame, "prepared keyframe")
        frame_id = str(frame.get("id", ""))
        if not frame_id.startswith("kf-") or not frame_id[3:].isdigit():
            raise WorkflowError(f"Invalid prepared frame ID: {frame_id}")
        frame_ids.append(frame_id)
        frame_hashes[frame_id] = require_sha(frame.get("sha256"), f"{frame_id}.sha256")
    if len(set(frame_ids)) != len(frame_ids):
        raise WorkflowError("Prepared keyframe IDs are not unique")
    duration = float(source.get("duration", 0))
    if not math.isfinite(duration) or duration <= 0:
        raise WorkflowError("Prepared material duration must be positive and finite")
    return {"material_id": material_id, "source_sha256": source_sha, "asset_id": str(source.get("assetId", "")),
            "clip_id": material["clip_id"], "kind": kind, "duration": duration, "frame_ids": frame_ids,
            "frame_hashes": frame_hashes, "cache_hit": bool(payload.get("cacheHit", False)),
            "prepare_status": str(payload.get("status")).upper()}


def _keyframes(state: dict[str, Any], step: dict[str, Any], material: dict[str, Any], payload: dict[str, Any], transport: dict[str, Any]) -> dict[str, Any]:
    prepared = prepared_facts(state, material)
    batches = require_list(payload.get("batches"), "keyframes.batches")
    if not prepared["frame_ids"]:
        if str(payload.get("status", "")).upper() not in {"N/A", "NOT_APPLICABLE"} or batches:
            raise WorkflowError("Audio with zero keyframes requires an empty N/A keyframe receipt")
        return {"material_id": prepared["material_id"], "batch_count": 0, "frame_ids": [], "not_applicable": True}
    _status(payload)
    calls = require_list(transport.get("calls"), "keyframes transport.calls")
    expected_calls = require_list(_issued_request(step).get("calls"), "keyframes issued calls")
    if not batches or len(calls) != len(batches) or len(calls) != len(expected_calls):
        raise WorkflowError("Keyframe result count does not match every issued MCP batch")
    observed: list[str] = []
    for expected_call, batch, call in zip(expected_calls, batches, calls):
        expected_call = require_mapping(expected_call, "issued keyframe call")
        if expected_call.get("tool") != "view_material_keyframes":
            raise WorkflowError("Issued keyframe call names the wrong MCP tool")
        expected_request = require_mapping(expected_call.get("arguments"), "issued keyframe arguments")
        call = require_mapping(call, "keyframe call evidence")
        request = require_mapping(call.get("request"), "keyframe MCP request")
        expected_ids = [str(item) for item in require_list(expected_request.get("frameIds"), "issued frameIds")]
        if request != expected_request or request.get("materialId") != prepared["material_id"]:
            raise WorkflowError("Keyframe MCP request does not exactly match the issued batch")
        batch = require_mapping(batch, "keyframe batch")
        _status(batch)
        if batch.get("materialId") != prepared["material_id"]:
            raise WorkflowError("Keyframe batch materialId does not match prepare receipt")
        frames = require_list(batch.get("frames"), "keyframe batch.frames")
        if not 1 <= len(frames) <= 4:
            raise WorkflowError("Every view_material_keyframes batch must contain 1..4 frames")
        images = require_list(call.get("images"), "keyframe MCP image evidence")
        if len(images) != len(frames) or len(frames) != len(expected_ids):
            raise WorkflowError("Every viewed frame requires exactly one MCP image content block")
        for expected_id, frame, image in zip(expected_ids, frames, images):
            frame, image = require_mapping(frame, "viewed keyframe"), require_mapping(image, "keyframe image evidence")
            frame_id = str(frame.get("id", ""))
            frame_sha, image_sha = require_sha(frame.get("sha256"), "viewed frame sha256"), require_sha(image.get("sha256"), "image sha256")
            if frame_id != expected_id or frame_sha != prepared["frame_hashes"].get(frame_id) or image_sha != frame_sha:
                raise WorkflowError("Viewed keyframe metadata or image bytes do not match the prepared frame")
            if not str(image.get("mime_type", "")).startswith("image/") or int(image.get("bytes", 0)) <= 0:
                raise WorkflowError("Viewed keyframe image evidence is empty or not an image")
            observed.append(frame_id)
    if observed != prepared["frame_ids"]:
        raise WorkflowError("Viewed keyframes must cover prepared frame IDs exactly once and in order")
    return {"material_id": prepared["material_id"], "batch_count": len(batches), "frame_ids": observed}


def _context(state: dict[str, Any], step: dict[str, Any], material: dict[str, Any], payload: dict[str, Any], transport: dict[str, Any]) -> dict[str, Any]:
    _status(payload)
    prepared = prepared_facts(state, material)
    windows = require_list(payload.get("windows"), "context.windows")
    calls = require_list(transport.get("calls"), "context transport.calls")
    expected_calls = require_list(_issued_request(step).get("calls"), "issued context calls")
    if not windows or len(calls) != len(windows) or len(calls) != len(expected_calls):
        raise WorkflowError("Context result count does not match every issued MCP window")
    normalized: list[dict[str, Any]] = []
    cue_indexes: set[int] = set()
    for expected_call, response, call in zip(expected_calls, windows, calls):
        expected_call = require_mapping(expected_call, "issued context call")
        if expected_call.get("tool") != "get_material_context":
            raise WorkflowError("Issued context call names the wrong MCP tool")
        expected = require_mapping(expected_call.get("arguments"), "issued context arguments")
        request = require_mapping(require_mapping(call, "context call evidence").get("request"), "context MCP request")
        if request != expected:
            raise WorkflowError("Context MCP request does not exactly match the issued bounded window")
        response = require_mapping(response, "context window response")
        _status(response)
        context = require_mapping(response.get("context"), "context window")
        if context.get("materialId") != prepared["material_id"] or require_sha(context.get("sourceSha256"), "context sourceSha256") != material["source_sha256"]:
            raise WorkflowError("Context material or source binding mismatch")
        window = require_mapping(context.get("window"), "context.window")
        start, end = float(window.get("start", -1)), float(window.get("end", -1))
        if (not all(map(math.isfinite, (start, end))) or start < 0 or end <= start
                or end > float(prepared["duration"]) + 1e-6
                or abs(start - float(request.get("start", -1))) > 1e-6 or abs(end - float(request.get("end", -1))) > 1e-6):
            raise WorkflowError("Context response window is invalid or does not match its MCP request")
        max_cues = request.get("maxCues")
        if not isinstance(max_cues, int) or not 1 <= max_cues <= 200:
            raise WorkflowError("Context MCP request maxCues must be 1..200")
        transcript = require_mapping(context.get("transcript"), "context.transcript")
        cues = require_list(transcript.get("cues", []), "context.transcript.cues")
        if len(cues) > max_cues:
            raise WorkflowError("Context window exceeds its bounded cue limit")
        for cue in cues:
            index = require_mapping(cue, "context transcript cue").get("index")
            if not isinstance(index, int) or index < 0:
                raise WorkflowError("Context transcript cue has no stable non-negative index")
            cue_indexes.add(index)
        normalized.append({"start": start, "end": end, "cue_count": len(cues), "has_more": bool(transcript.get("hasMore", False))})
    return {"material_id": prepared["material_id"], "windows": normalized,
            "total_cues_loaded": len(cue_indexes), "cue_indexes": sorted(cue_indexes)}


def _normalized_segment(segment: dict[str, Any]) -> dict[str, Any]:
    result = {"start": segment.get("start"), "end": segment.get("end"), "summary": segment.get("summary"),
              "subjects": require_list(segment.get("subjects", []), "segment.subjects"),
              "actions": require_list(segment.get("actions", []), "segment.actions"),
              "objects": require_list(segment.get("objects", []), "segment.objects")}
    if "emotion" in segment: result["emotion"] = segment["emotion"]
    result.update({"importance": segment.get("importance"),
                   "evidenceFrameIds": require_list(segment.get("evidenceFrameIds", []), "segment.evidenceFrameIds"),
                   "transcriptCueIndexes": require_list(segment.get("transcriptCueIndexes", []), "segment.transcriptCueIndexes")})
    if "uncertainty" in segment: result["uncertainty"] = segment["uncertainty"]
    return result


def _semantics(state: dict[str, Any], material: dict[str, Any], payload: dict[str, Any], transport: dict[str, Any]) -> dict[str, Any]:
    _status(payload)
    prepared = prepared_facts(state, material)
    receipt = require_mapping(payload.get("receipt"), "semantics.receipt")
    if receipt.get("schema") != "hao.editkin.material-semantics/v1" or receipt.get("materialId") != prepared["material_id"]:
        raise WorkflowError("Unexpected or mismatched material semantics receipt")
    if require_sha(receipt.get("sourceSha256"), "semantic sourceSha256") != material["source_sha256"]:
        raise WorkflowError("Semantic receipt source hash does not match bound source")
    calls = require_list(transport.get("calls"), "semantics transport.calls")
    if len(calls) != 1:
        raise WorkflowError("Semantic completion requires exactly one preserved MCP call")
    request = require_mapping(require_mapping(calls[0], "semantic call evidence").get("request"), "semantic MCP request")
    if request.get("materialId") != prepared["material_id"] or require_sha(request.get("sourceSha256"), "semantic request sourceSha256") != material["source_sha256"]:
        raise WorkflowError("Semantic MCP request does not match the prepared material")
    for field in ("overallTopic", "contentType", "language"):
        text = str(request.get(field, "")).strip()
        if not text or "TODO" in text.upper(): raise WorkflowError(f"Semantic MCP request field {field} was not completed")
    viewed = set(receipt_for(state, f"keyframes:{material['key']}")["facts"]["frame_ids"])
    loaded_cues = set(receipt_for(state, f"context:{material['key']}")["facts"]["cue_indexes"])
    segments: list[dict[str, Any]] = []
    for raw in require_list(request.get("segments"), "semantic request.segments"):
        segment = require_mapping(raw, "semantic segment")
        frame_ids = set(str(item) for item in require_list(segment.get("evidenceFrameIds", []), "segment.evidenceFrameIds"))
        cue_values = require_list(segment.get("transcriptCueIndexes", []), "segment.transcriptCueIndexes")
        if any(not isinstance(item, int) or item < 0 for item in cue_values): raise WorkflowError("Semantic cue evidence must use non-negative integer indexes")
        cue_ids = set(cue_values)
        start, end = float(segment.get("start", -1)), float(segment.get("end", -1))
        if not frame_ids and not cue_ids: raise WorkflowError("Every semantic segment requires viewed frame or loaded transcript evidence")
        if not frame_ids.issubset(viewed) or not cue_ids.issubset(loaded_cues): raise WorkflowError("Semantic segment cites evidence that this workflow did not view")
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start or end > float(prepared["duration"]) + 1e-6:
            raise WorkflowError("Semantic segment is outside the prepared material duration")
        segments.append(_normalized_segment(segment))
    if int(receipt.get("segmentCount", 0)) != len(segments) or not segments:
        raise WorkflowError("Semantic receipt segment count does not match the evidence-backed request")
    normalized = {"schema": "hao.editkin.material-semantics/v1", "materialId": request["materialId"],
                  "sourceSha256": request["sourceSha256"], "overallTopic": request["overallTopic"],
                  "contentType": request["contentType"], "language": request["language"],
                  "people": require_list(request.get("people", []), "semantic request.people"),
                  "locations": require_list(request.get("locations", []), "semantic request.locations"), "segments": segments}
    semantic_sha = plan_sha256(normalized)
    if require_sha(receipt.get("semanticReceiptSha256"), "semanticReceiptSha256") != semantic_sha:
        raise WorkflowError("Semantic receipt hash does not bind the preserved evidence-backed MCP request")
    return {"material_id": prepared["material_id"], "source_sha256": material["source_sha256"],
            "asset_id": prepared["asset_id"], "clip_id": material["clip_id"],
            "semantic_receipt_sha256": semantic_sha, "segment_count": len(segments)}


def validate_material_payload(state: dict[str, Any], step: dict[str, Any], payload: dict[str, Any], transport: dict[str, Any]) -> dict[str, Any]:
    material = step_material(state, step)
    validators = {
        "prepare:{material}": lambda: _prepare(material, payload),
        "keyframes:{material}": lambda: _keyframes(state, step, material, payload, transport),
        "context:{material}": lambda: _context(state, step, material, payload, transport),
        "semantics:{material}": lambda: _semantics(state, material, payload, transport),
    }
    return validators[step["template_id"]]()
