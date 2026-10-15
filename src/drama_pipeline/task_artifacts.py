"""Public workflow component (public distribution).

Configurable source-only workflow implementation; no creator data or live capability proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any
from .media_contract_bridge import lint_bound_receipt, load_task_job
from .store import ProjectStore, sha256_file, utc_now


def _preflight_artifact(path: Path, source_hash: str) -> None:
    if path.exists() and (not path.is_file() or sha256_file(path) != source_hash):
        raise ValueError(f"refusing to overwrite different canonical artifact: {path}")


def _copy_artifact_once(source: Path, destination: Path, expected_hash: str) -> None:
    if source == destination:
        if sha256_file(source) != expected_hash:
            raise ValueError(f"canonical artifact changed during persistence: {source}")
        return
    if destination.exists():
        if not destination.is_file() or sha256_file(destination) != expected_hash:
            raise ValueError(f"refusing late overwrite of different canonical artifact: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, raw = tempfile.mkstemp(
        prefix=destination.name + ".", suffix=".tmp", dir=destination.parent
    )
    os.close(handle)
    temporary = Path(raw)
    try:
        shutil.copy2(source, temporary)
        if sha256_file(temporary) != expected_hash:
            raise ValueError(f"canonical artifact changed during persistence: {source}")
        try:
            # Atomic no-clobber publish. Unlike os.replace(), a concurrently
            # created user file can never be overwritten.
            os.link(temporary, destination)
        except FileExistsError:
            if not destination.is_file() or sha256_file(destination) != expected_hash:
                raise ValueError(
                    f"refusing late overwrite of different canonical artifact: {destination}"
                )
    finally:
        if temporary.exists():
            temporary.unlink()


def _load_locked_submission(artifact_root, receipt_path, store, task):
    job = load_task_job(store, task)
    receipt_source = receipt_path.expanduser().resolve()
    if not receipt_source.is_file():
        raise FileNotFoundError(f"media receipt is missing: {receipt_source}")
    receipt_bytes = receipt_source.read_bytes()
    try:
        receipt = json.loads(receipt_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"media receipt is not valid UTF-8 JSON: {receipt_source}: {exc}") from exc
    if not isinstance(receipt, dict):
        raise ValueError("media receipt must be a JSON object")
    submitted_root = artifact_root.expanduser().resolve()
    if not submitted_root.is_dir():
        raise FileNotFoundError(f"artifact_root is missing or not a directory: {submitted_root}")
    lint_bound_receipt(job, receipt, artifact_root=submitted_root)
    return job, receipt_source, receipt_bytes, receipt, submitted_root


def _validate_locked_media_sources(job, probe, receipt, receipt_source, source, submitted_root):
    actual_video_hash = sha256_file(source)
    video_artifact = next(
        (item for item in receipt.get("outputs", []) if item.get("kind") == "video"),
        None,
    )
    if not isinstance(video_artifact, dict) or video_artifact.get("sha256") != actual_video_hash:
        raise ValueError("receipt video SHA-256 does not match the actual submitted source file")
    receipt_artifact = next(
        (item for item in receipt.get("outputs", []) if item.get("kind") == "receipt"),
        None,
    )
    prompt_artifact = next(
        (item for item in receipt.get("outputs", []) if item.get("kind") == "prompt"),
        None,
    )
    if not isinstance(receipt_artifact, dict) or not isinstance(prompt_artifact, dict):
        raise ValueError("succeeded canonical receipt requires receipt and prompt output metadata")

    source_artifacts: dict[str, tuple[dict[str, Any], Path]] = {}
    seen_uris: set[str] = set()
    for artifact in receipt.get("outputs", []):
        uri = str(artifact["uri"])
        if uri in seen_uris:
            raise ValueError(f"receipt output URIs must be unique: {uri}")
        seen_uris.add(uri)
        artifact_source = (submitted_root / uri).resolve()
        try:
            artifact_source.relative_to(submitted_root)
        except ValueError as exc:
            raise ValueError(f"receipt artifact escapes artifact_root: {uri}") from exc
        source_artifacts[artifact["kind"]] = (artifact, artifact_source)

    if source != source_artifacts["video"][1]:
        raise ValueError("submitted video must be the exact video artifact under --artifact-root")
    if receipt_source != source_artifacts["receipt"][1]:
        raise ValueError("--receipt must be the exact receipt artifact under --artifact-root")
    locked_duration = float(job["segment"]["duration_seconds"])
    actual_duration = float(probe.get("duration") or 0)
    if abs(actual_duration - locked_duration) > max(0.5, locked_duration * 0.04):
        raise ValueError(
            f"actual video duration {actual_duration:g}s does not match locked segment "
            f"duration {locked_duration:g}s"
        )
    return actual_video_hash, source_artifacts, locked_duration


def _persist_locked_artifacts(source_artifacts, store):
    persisted: dict[str, Path] = {
        kind: store.artifact(str(artifact["uri"]))
        for kind, (artifact, _source_path) in source_artifacts.items()
    }
    if len(set(persisted.values())) != len(persisted):
        raise ValueError("canonical receipt artifacts must use distinct project paths")
    artifact_records: list[dict[str, Any]] = []
    # Validate every destination before making any mutation, then copy all evidence.
    for kind, (artifact, artifact_source) in source_artifacts.items():
        digest = sha256_file(artifact_source)
        _preflight_artifact(persisted[kind], digest)
        artifact_records.append(
            {"kind": kind, "uri": artifact["uri"], "sha256": digest}
        )
    artifact_hashes = {item["kind"]: item["sha256"] for item in artifact_records}
    for kind, (_artifact, artifact_source) in source_artifacts.items():
        _copy_artifact_once(artifact_source, persisted[kind], artifact_hashes[kind])
    return persisted, artifact_records


def _complete_locked_task(
    store: ProjectStore,
    queue: dict[str, Any],
    task: dict[str, Any],
    source: Path,
    probe: dict[str, Any],
    receipt_path: Path | None,
    artifact_root: Path | None,
    *,
    qc_passed: bool,
    note: str,
    cost: float | None,
) -> dict[str, Any]:
    if receipt_path is None:
        raise ValueError("real locked_media_job completion requires --receipt")
    if artifact_root is None:
        raise ValueError("real locked_media_job completion requires --artifact-root")
    if not qc_passed:
        raise ValueError("Visual/audio QC must pass before completing a real generation task")
    job, receipt_source, receipt_bytes, receipt, submitted_root = _load_locked_submission(artifact_root, receipt_path, store, task)

    actual_video_hash, source_artifacts, locked_duration = _validate_locked_media_sources(job, probe, receipt, receipt_source, source, submitted_root)

    persisted, artifact_records = _persist_locked_artifacts(source_artifacts, store)

    destination = persisted["video"]
    persisted_receipt = persisted["receipt"]
    persisted_prompt = persisted["prompt"]
    if sha256_file(destination) != actual_video_hash:
        raise RuntimeError("persisted video hash changed during copy")
    if persisted_receipt.read_bytes() != receipt_bytes:
        raise RuntimeError("persisted receipt bytes changed during copy")
    # This second pass binds the immutable receipt to the actual project artifacts
    # that the editor will consume, not merely the submitted/download directory.
    lint_bound_receipt(job, receipt, artifact_root=store.root)

    task["expected_path"] = store.relative(destination)
    task["status"] = "complete"
    task["result"] = {
        "file": str(destination),
        "video_sha256": actual_video_hash,
        "provider": receipt["provider"],
        "model_id": receipt["model_id"],
        "qc_passed": True,
        "mock": False,
        "note": note,
        "cost": cost,
        "probe": probe,
        "job_path": task["job_path"],
        "job_sha256": task["job_sha256"],
        "receipt_id": receipt["receipt_id"],
        "receipt_file": str(persisted_receipt),
        "receipt_sha256": sha256_file(persisted_receipt),
        "prompt_file": str(persisted_prompt),
        "prompt_sha256": sha256_file(persisted_prompt),
        "canonical_video_uri": source_artifacts["video"][0]["uri"],
        "submitted_artifact_root": str(submitted_root),
        "verified_artifact_root": str(store.root),
        "artifacts": artifact_records,
        "language_verification": receipt["language_verification"],
        "completed_at": utc_now(),
    }
    store.save_queue(queue)
    store.log("locked_media_job_completed", {"task_id": task["id"], "result": task["result"]})
    return task
