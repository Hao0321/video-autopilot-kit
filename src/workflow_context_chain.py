"""Bounded, exact-request transcript page chains; no MCP execution or state mutation."""
from __future__ import annotations
import math
from workflow_state import WorkflowError, require_mapping, require_list, require_sha, sha256_json

def context_progress(state, step, material, payload, transport, *, prepared, roots, require_complete=False):
    if payload.get("status") != "GREEN": raise WorkflowError("Context status must be GREEN")
    prepared = require_mapping(prepared, "prepared material facts")
    roots = require_list(roots, "issued context calls")
    responses = require_list(payload.get("windows"), "context windows")
    calls = require_list(transport.get("calls"), "context calls")
    if len(responses) != len(calls) or not roots: raise WorkflowError("Context evidence count mismatch")
    position, loaded, summaries, next_calls = 0, set(), [], []
    for root in roots:
        if root.get("tool") != "get_material_context": raise WorkflowError("Wrong context tool")
        initial = require_mapping(root.get("arguments"), "context root arguments")
        if initial.get("afterCueIndex") != -1 or initial.get("maxTokens") != 600 or initial.get("maxCues") != 200:
            raise WorkflowError("Context claim predates revision 3; restart run")
        cursor, pages, remaining, terminal = -1, 0, None, False
        while position < len(calls):
            expected = {**initial, "afterCueIndex": cursor}
            request = require_mapping(calls[position].get("request"), "context request")
            if request != expected: raise WorkflowError("Context request does not match derived cursor/window")
            response = require_mapping(responses[position], "context response")
            if response.get("status") != "GREEN": raise WorkflowError("Context page not GREEN")
            context = require_mapping(response.get("context"), "context")
            if context.get("materialId") != prepared["material_id"] or require_sha(context.get("sourceSha256"), "source") != material["source_sha256"]:
                raise WorkflowError("Context material or source binding mismatch")
            if context.get("window") != {"start": initial["start"], "end": initial["end"]}:
                raise WorkflowError("Context window mismatch")
            if not (0 <= initial["start"] < initial["end"] <= float(prepared["duration"]) + 1e-6):
                raise WorkflowError("Context window outside material")
            budget = require_mapping(context.get("budget"), "context budget")
            estimate = budget.get("estimatedTokens")
            if budget.get("maxTokens") != 600 or type(estimate) not in (int, float) or not math.isfinite(estimate) or not 0 <= estimate <= 600:
                raise WorkflowError("Context page token budget exceeded or missing")
            transcript = require_mapping(context.get("transcript"), "transcript")
            if transcript.get("state") not in {"ready", "not_applicable"}: raise WorkflowError("Transcript not ready")
            cues = require_list(transcript.get("cues"), "cues")
            more, count = transcript.get("hasMore"), transcript.get("remainingWindowCues")
            if type(more) is not bool or type(count) is not int or count < 0 or more != (count > 0): raise WorkflowError("Invalid remaining context count")
            if transcript.get("returnedCues") != len(cues) or len(cues) > 200: raise WorkflowError("Invalid returned context count")
            if remaining is not None and remaining != len(cues) + count: raise WorkflowError("Context page chain skipped cues")
            if transcript["state"] == "not_applicable" and (cues or more): raise WorkflowError("N/A transcript contains cues")
            for cue in cues:
                index = cue.get("index")
                if type(index) is not int or index <= cursor: raise WorkflowError("Context cue cursor must strictly increase")
                start, end = cue.get("start"), cue.get("end")
                if type(start) not in (int,float) or type(end) not in (int,float) or not math.isfinite(start) or not math.isfinite(end) or not start < end or not (start < initial["end"] and end > initial["start"]): raise WorkflowError("Context cue outside window")
                cursor = index; loaded.add(index)
            if more and (not cues or transcript.get("nextCueIndex") != cursor): raise WorkflowError("Context cursor cannot progress")
            if not more and transcript.get("nextCueIndex") is not None: raise WorkflowError("Terminal context has continuation cursor")
            remaining = count; position += 1; pages += 1
            if pages > 2048 or (pages == 2048 and more): raise WorkflowError("Context page budget exhausted")
            if not more: terminal = True; break
        summaries.append({"start": initial["start"], "end": initial["end"], "pages": pages, "has_more": not terminal})
        if not terminal:
            next_calls.append({"tool": "get_material_context", "arguments": {**initial, "afterCueIndex": cursor}})
            # Subsequent windows cannot precede completion of this chain.
            next_calls.extend(roots[len(summaries):])
            break
    if position != len(calls): raise WorkflowError("Unexpected context pages after terminal windows")
    complete = not next_calls
    if require_complete and not complete: raise WorkflowError("Context incomplete: continue pages before completion")
    return {"material_id": prepared["material_id"], "windows": summaries, "total_cues_loaded": len(loaded), "cue_indexes": sorted(loaded), "complete": complete, "next_calls": next_calls, "evidence_sha256": sha256_json({"payload": payload, "transport": transport})}
