from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from workflow_state import (
    WorkflowError, load_contract, plan_sha256, read_json, require_list, require_mapping, require_sha,
    sha256_file, sha256_json, step_material, validated_keyframe_times, validated_transcript_policy,
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


def _frame_length(value: Any, frame_id: str, maximum: int) -> int:
    if type(value) is not int or not 0 < value <= maximum:
        raise WorkflowError(f"{frame_id} requires a verified integer byte length in 1..{maximum}; reprepare material, never guess or raise the cap")
    return value


def keyframe_batches(prepared: dict[str, Any]) -> list[list[str]]:
    """Keep source order and every frame while bounding actual image payload."""
    limits = load_contract()[0]["limits"]
    frames = require_list(prepared.get("frame_ids"), "prepared frame IDs")
    sizes = require_mapping(prepared.get("frame_bytes"), "prepared frame byte lengths; reprepare missing metadata")
    batches: list[list[str]] = []
    batch: list[str] = []
    total = 0
    for frame_id in frames:
        size = _frame_length(sizes.get(frame_id), frame_id, limits["keyframe_bytes_per_call"])
        if batch and (len(batch) == limits["keyframes_per_call"] or total + size > limits["keyframe_bytes_per_call"]):
            batches.append(batch)
            batch, total = [], 0
        batch.append(frame_id)
        total += size
    if batch:
        batches.append(batch)
    return batches


def _prepare(material: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    _status(payload, {"GREEN", "PARTIAL"})
    packet = require_mapping(payload.get("packet"), "prepare.packet")
    material_id = require_sha(packet.get("materialId"), "prepare materialId")
    job = payload.get("job")
    if job is not None:
        job = require_mapping(job, "prepare background job")
        result = require_mapping(job.get("result"), "completed prepare job result")
        if (job.get("schema") != "editkin.material-preparation-job/v1" or job.get("state") != "COMPLETED"
                or result.get("materialId") != material_id):
            raise WorkflowError("Background prepare requires a completed job bound to this material packet")
    source = require_mapping(packet.get("source"), "prepare.packet.source")
    source_sha = require_sha(source.get("sourceSha256"), "prepare sourceSha256")
    if source_sha != material["source_sha256"] or source.get("clipId") != material["clip_id"]:
        raise WorkflowError(f"Prepared source or clip binding mismatch for {material['clip_id']}")
    frames = require_list(packet.get("keyframes"), "prepare.packet.keyframes")
    kind = str(source.get("kind", "video"))
    policy_facts = {}
    if "transcript_policy" in material:
        policy = validated_transcript_policy(material["transcript_policy"])
        transcript = require_mapping(packet.get("transcript"), "bound transcript policy evidence")
        if policy == "visual-only" and (kind != "video" or transcript.get("state") != "not_applicable"):
            raise WorkflowError("Visual-only material requires a video packet with explicitly omitted transcription, never a failed ASR or audio-only packet")
        if policy == "required" and transcript.get("state") == "not_applicable":
            raise WorkflowError("Required transcription was omitted; speech analysis cannot silently become visual-only")
        policy_facts = {"transcript_policy": policy}
    if len(frames) > 12 or (not frames and kind != "audio"):
        raise WorkflowError("prepare_ai_material requires 1..12 keyframes except audio, which may have zero")
    frame_ids: list[str] = []
    frame_hashes: dict[str, str] = {}
    frame_bytes: dict[str, int] = {}
    maximum = load_contract()[0]["limits"]["keyframe_bytes_per_call"]
    for frame in frames:
        frame = require_mapping(frame, "prepared keyframe")
        frame_id = str(frame.get("id", ""))
        if not frame_id.startswith("kf-") or not frame_id[3:].isdigit():
            raise WorkflowError(f"Invalid prepared frame ID: {frame_id}")
        frame_ids.append(frame_id)
        frame_hashes[frame_id] = require_sha(frame.get("sha256"), f"{frame_id}.sha256")
        frame_bytes[frame_id] = _frame_length(frame.get("bytes"), frame_id, maximum)
    if len(set(frame_ids)) != len(frame_ids):
        raise WorkflowError("Prepared keyframe IDs are not unique")
    duration = float(source.get("duration", 0))
    if not math.isfinite(duration) or duration <= 0:
        raise WorkflowError("Prepared material duration must be positive and finite")
    selection = {}
    if "keyframe_times" in material:
        times = validated_keyframe_times(material["keyframe_times"], duration)
        analysis = require_mapping(packet.get("keyframeAnalysis"), "explicit keyframe analysis")
        samples = require_list(analysis.get("requestedSamples"), "explicit requested samples")
        if (kind != "video" or len(samples) != len(times)
                or any(require_mapping(sample, "sample").get("id") != f"kf-{i + 1}" or sample.get("time") != times[i]
                       for i, sample in enumerate(samples))):
            raise WorkflowError("Prepared keyframe sampling does not match the bound explicit request")
        evidence = {}
        by_id = {f"kf-{i + 1}": t for i, t in enumerate(times)}
        for frame in frames:
            frame_id = frame["id"]
            display = require_mapping(frame.get("display"), "explicit keyframe display receipt")
            actual = frame.get("time")
            if (frame_id not in by_id or display.get("requestedTime") != by_id[frame_id]
                    or type(actual) not in (int, float) or not math.isfinite(actual)
                    or not by_id[frame_id] - 1e-7 <= actual < duration or display.get("actualTime") != actual
                    or display.get("purpose") != "neutral-display-proxy" or display.get("transfer") != "srgb"):
                raise WorkflowError("Explicit keyframe lacks a matching normalized decoded-time receipt")
            evidence[frame_id] = {"time": actual, "requested_time": by_id[frame_id],
                                  "display_receipt_sha256": require_sha(display.get("receiptSha256"), "display receipt")}
        selection = {"keyframe_times": times, "selected_frame_evidence": evidence}
    return {"material_id": material_id, "source_sha256": source_sha, "asset_id": str(source.get("assetId", "")),
            "clip_id": material["clip_id"], "kind": kind, "duration": duration, "frame_ids": frame_ids,
            "frame_hashes": frame_hashes, "frame_bytes": frame_bytes, "cache_hit": bool(payload.get("cacheHit", False)),
            "background_job_id": job.get("jobId") if job is not None else None,
            "prepare_status": str(payload.get("status")).upper(), **selection, **policy_facts}


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
    limits = load_contract()[0]["limits"]
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
        total = 0
        for expected_id, frame, image in zip(expected_ids, frames, images):
            frame, image = require_mapping(frame, "viewed keyframe"), require_mapping(image, "keyframe image evidence")
            frame_id = str(frame.get("id", ""))
            if "selected_frame_evidence" in prepared:
                selected = prepared["selected_frame_evidence"].get(frame_id)
                display = require_mapping(frame.get("display"), "viewed explicit display receipt")
                if (selected is None or frame.get("time") != selected["time"]
                        or display.get("actualTime") != selected["time"] or display.get("requestedTime") != selected["requested_time"]
                        or display.get("receiptSha256") != selected["display_receipt_sha256"]):
                    raise WorkflowError("Viewed keyframe time/display does not match explicit preparation")
            frame_sha, image_sha = require_sha(frame.get("sha256"), "viewed frame sha256"), require_sha(image.get("sha256"), "image sha256")
            if frame_id != expected_id or frame_sha != prepared["frame_hashes"].get(frame_id) or image_sha != frame_sha:
                raise WorkflowError("Viewed keyframe metadata or image bytes do not match the prepared frame")
            size = _frame_length(image.get("bytes"), frame_id, limits["keyframe_bytes_per_call"])
            if not str(image.get("mime_type", "")).startswith("image/"):
                raise WorkflowError("Viewed keyframe image evidence is empty or not an image")
            if (prepared.get("frame_bytes", {}).get(frame_id) != size
                    or type(frame.get("bytes")) is not int or frame["bytes"] != size):
                raise WorkflowError("Viewed keyframe byte lengths do not match prepared metadata and actual image bytes")
            total += size
            observed.append(frame_id)
        if total > limits["keyframe_bytes_per_call"]:
            raise WorkflowError("Keyframe batch exceeds the actual image byte limit")
        if type(batch.get("totalImageBytes")) is not int or batch["totalImageBytes"] != total:
            raise WorkflowError("Keyframe batch totalImageBytes does not match actual images")
    if observed != prepared["frame_ids"]:
        raise WorkflowError("Viewed keyframes must cover prepared frame IDs exactly once and in order")
    return {"material_id": prepared["material_id"], "batch_count": len(batches), "frame_ids": observed}


def _context(state: dict[str, Any], step: dict[str, Any], material: dict[str, Any], payload: dict[str, Any], transport: dict[str, Any]) -> dict[str, Any]:
    from workflow_context_chain import context_progress
    return context_progress(
        state, step, material, payload, transport,
        prepared=prepared_facts(state, material),
        roots=_issued_request(step).get("calls"),
        require_complete=True,
    )




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


def semantic_transcript_evidence(state: dict[str, Any], material: dict[str, Any], segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Recreate the product's cue seals from already verified, bounded context."""
    referenced = {index for segment in segments for index in segment.get("transcriptCueIndexes", [])}
    if not referenced:
        return []
    envelope = receipt_for(state, f"context:{material['key']}")
    payload = require_mapping(envelope.get("payload"), "saved context payload")
    sealed: dict[int, dict[str, Any]] = {}
    for page in require_list(payload.get("windows"), "saved context pages"):
        context = require_mapping(require_mapping(page, "context page").get("context"), "saved context")
        transcript = require_mapping(context.get("transcript"), "saved context transcript")
        for cue in require_list(transcript.get("cues"), "saved context cues"):
            cue = require_mapping(cue, "saved cue")
            index = cue.get("index")
            if index not in referenced:
                continue
            if type(index) is not int or not isinstance(cue.get("text"), str):
                raise WorkflowError("Semantic evidence requires the exact loaded transcript cue")
            body = {"start": cue.get("start"), "end": cue.get("end"), "text": cue["text"]}
            value = {"cueIndex": index, "start": body["start"], "end": body["end"], "textSha256": plan_sha256(body)}
            if index in sealed and sealed[index] != value:
                raise WorkflowError("Overlapping context pages disagree on a referenced transcript cue")
            sealed[index] = value
    if set(sealed) != referenced:
        raise WorkflowError("Semantic receipt cites transcript bytes absent from the loaded context")
    return [sealed[index] for index in sorted(sealed)]


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
                  "locations": require_list(request.get("locations", []), "semantic request.locations"), "segments": segments,
                  "transcriptEvidence": semantic_transcript_evidence(state, material, segments)}
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
