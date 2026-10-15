"""Hash-verified public workflow receipt reads."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from workflow_primitives import WorkflowError, read_json, require_mapping, sha256_file

def receipt_for(state: dict[str, Any], step_id: str) -> dict[str, Any]:
    record = state["steps"][step_id].get("receipt")
    if not record:
        raise WorkflowError(f"Step has no receipt: {step_id}")
    path = Path(state["run_dir"]) / record["path"]
    envelope = require_mapping(read_json(path), f"receipt {step_id}")
    if sha256_file(path) != record["file_sha256"]:
        raise WorkflowError(f"Receipt file hash mismatch: {step_id}")
    return envelope
